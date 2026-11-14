"""Leakage-safe, reproducible preprocessing for training and inference.

The :class:`Preprocessor` bundles imputation, categorical encoding and optional
numeric scaling into a single scikit-learn *compatible* transformer
(``fit``/``transform``/``get_feature_names_out``, joblib-serialisable).

Every data-derived transformation is fitted on the training partition only and
then reused for inference, so the fitted preprocessor can be bundled inside a
trained model pipeline.

scikit-learn is used where importable; components whose compiled extensions are
blocked by the environment (for example :class:`sklearn.impute.SimpleImputer`)
are replaced with pure-NumPy equivalents that behave identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd

from maintiq.core.exceptions import PreprocessingError
from maintiq.data.schema import DatasetSchema

try:  # scikit-learn may be partially unavailable in locked-down environments
    from sklearn.base import BaseEstimator, TransformerMixin
except ImportError:  # pragma: no cover - fallback for environments without sklearn
    BaseEstimator = object  # type: ignore[assignment,misc]
    TransformerMixin = object  # type: ignore[assignment,misc]

try:
    from sklearn.preprocessing import StandardScaler
except ImportError:  # pragma: no cover - environment without sklearn scaling
    StandardScaler = None  # type: ignore[assignment,misc]

try:  # sklearn.model_selection may pull in blocked extensions in some envs
    from sklearn.model_selection import train_test_split as _sklearn_train_test_split
except ImportError:  # pragma: no cover - environment without sklearn
    _sklearn_train_test_split = None  # type: ignore[assignment,misc]

# Canonical numeric predictive inputs (excluding the categorical ``type``).
NUMERIC_COLUMNS = (
    "air_temperature_k",
    "process_temperature_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
)

# Canonical categorical predictive input.
CATEGORICAL_COLUMNS = ("type",)

_NUMERIC_STRATEGIES = ("mean", "median", "most_frequent", "constant")
_CATEGORICAL_STRATEGIES = ("most_frequent", "constant")


@dataclass
class SplitSettings:
    """Record of a deterministic train/test split."""

    test_size: float
    random_state: int
    stratify: bool
    n_train: int
    n_test: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_size": self.test_size,
            "random_state": self.random_state,
            "stratify": self.stratify,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "timestamp": self.timestamp,
        }


@dataclass
class PreprocessorArtifact:
    """A fitted preprocessor together with the columns it expects."""

    preprocessor: Any
    input_columns: list[str]
    output_columns: list[str]
    split_settings: SplitSettings | None = None
    schema: DatasetSchema | None = None
    scale_numeric: bool = False


def _standard_scaler_fit(values: np.ndarray):
    mean = np.nanmean(values, axis=0)
    std = np.nanstd(values, axis=0)
    std = np.where(std == 0, 1.0, std)
    return mean, std


def _standard_scaler_transform(values: np.ndarray, mean: np.ndarray, std: np.ndarray):
    return (values - mean) / std


class Preprocessor(BaseEstimator, TransformerMixin):
    """Fits and applies leakage-safe preprocessing.

    Parameters
    ----------
    scale_numeric:
        Standard-scale numeric features. Enable for Logistic Regression; leave
        disabled for tree-based models (scaling is unnecessary there) unless a
        shared pipeline makes it technically justified and documented.
    """

    def __init__(
        self,
        schema: DatasetSchema | None = None,
        numeric_strategy: str = "median",
        categorical_strategy: str = "most_frequent",
        scale_numeric: bool = False,
        random_seed: int = 42,
    ):
        if numeric_strategy not in _NUMERIC_STRATEGIES:
            raise PreprocessingError(
                f"Invalid numeric_strategy '{numeric_strategy}'. "
                f"Expected one of {_NUMERIC_STRATEGIES}."
            )
        if categorical_strategy not in _CATEGORICAL_STRATEGIES:
            raise PreprocessingError(
                f"Invalid categorical_strategy '{categorical_strategy}'. "
                f"Expected one of {_CATEGORICAL_STRATEGIES}."
            )
        self.schema = schema or DatasetSchema()
        self.numeric_strategy = numeric_strategy
        self.categorical_strategy = categorical_strategy
        self.scale_numeric = scale_numeric
        self.random_seed = random_seed

        self._fitted = False
        self._input_columns: list[str] | None = None
        self._output_columns: list[str] | None = None
        self._numeric_fill: dict[str, float] = {}
        self._categorical_fill: dict[str, str] = {}
        self._type_categories: list[str] = []
        self._numeric_mean: np.ndarray | None = None
        self._numeric_std: np.ndarray | None = None

    # ------------------------------------------------------------------ fit

    def fit(self, frame: pd.DataFrame, target: pd.Series | None = None) -> "Preprocessor":
        """Fit all data-derived transformations on ``frame`` (training only).

        ``target`` is accepted for API symmetry and possible stratification but
        is not used to fit any data-derived transformation.
        """
        self._input_columns = list(self._expected_columns())
        missing = [c for c in self._input_columns if c not in frame.columns]
        if missing:
            raise PreprocessingError(f"Input frame missing expected columns: {missing}")

        data = frame[self._input_columns]

        # Numeric imputation fill values (training partition only).
        for col in NUMERIC_COLUMNS:
            series = pd.to_numeric(data[col], errors="coerce")
            if self.numeric_strategy == "median":
                fill = float(np.nanmedian(series.to_numpy(dtype=float)))
            elif self.numeric_strategy == "mean":
                fill = float(np.nanmean(series.to_numpy(dtype=float)))
            elif self.numeric_strategy == "most_frequent":
                mode = series.mode(dropna=True)
                fill = float(mode.iloc[0]) if not mode.empty else 0.0
            else:  # constant
                fill = 0.0
            if not np.isfinite(fill):
                fill = 0.0
            self._numeric_fill[col] = fill

        # Categorical imputation fill values (training partition only).
        for col in CATEGORICAL_COLUMNS:
            series = data[col].astype(str)
            mode = series.mode(dropna=True)
            self._categorical_fill[col] = str(mode.iloc[0]) if not mode.empty else "L"

        # Known Type categories (training partition only).
        type_series = data[CATEGORICAL_COLUMNS[0]].astype(str)
        self._type_categories = sorted({str(v) for v in type_series.dropna().unique()})
        if not self._type_categories:
            self._type_categories = list(DatasetSchema().type_values)

        # Numeric scaling parameters (training partition only).
        if self.scale_numeric and StandardScaler is not None:
            scaler = StandardScaler()
            scaler.fit(data[list(NUMERIC_COLUMNS)].to_numpy(dtype=float))
            self._numeric_mean = scaler.mean_
            self._numeric_std = scaler.scale_
        elif self.scale_numeric:
            values = data[list(NUMERIC_COLUMNS)].to_numpy(dtype=float)
            self._numeric_mean, self._numeric_std = _standard_scaler_fit(values)
        else:
            self._numeric_mean = None
            self._numeric_std = None

        self._output_columns = self._compute_output_columns()
        self._fitted = True
        return self

    def fit_transform(
        self, frame: pd.DataFrame, target: pd.Series | None = None
    ) -> tuple[pd.DataFrame, "Preprocessor"]:
        """Fit on ``frame`` and return the transformed frame plus the fitter."""
        self.fit(frame, target)
        return self.transform(frame), self

    def fit_transform_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Convenience: fit then transform, returning only the transformed frame."""
        self.fit(frame)
        return self.transform(frame)

    # ----------------------------------------------------------------- transform

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Transform ``frame`` using the training-fitted transformations."""
        if not self._fitted:
            raise PreprocessingError(
                "Preprocessor has not been fitted. Call fit() before transform()."
            )
        input_columns = [c for c in frame.columns if c in self._expected_columns()]
        missing = [c for c in self._input_columns if c not in input_columns]
        if missing:
            raise PreprocessingError(f"Missing required input columns for transform: {missing}")

        data = frame[self._input_columns].copy()

        # Numeric imputation.
        for col in NUMERIC_COLUMNS:
            data[col] = pd.to_numeric(data[col], errors="coerce")
            data[col] = data[col].fillna(self._numeric_fill.get(col, 0.0))

        # Categorical imputation.
        for col in CATEGORICAL_COLUMNS:
            data[col] = data[col].astype(str).fillna(self._categorical_fill.get(col, "L"))

        # One-hot encode Type using training categories; unknown -> all zeros.
        type_col = CATEGORICAL_COLUMNS[0]
        type_values = data[type_col].astype(str)
        encoded = pd.DataFrame(
            0.0,
            index=data.index,
            columns=[f"cat__{type_col}__{c}" for c in self._type_categories],
        )
        for cat_value in self._type_categories:
            mask = type_values.eq(cat_value)
            if bool(mask.any()):
                encoded.loc[mask, f"cat__{type_col}__{cat_value}"] = 1.0

        # Numeric block (optionally standard-scaled).
        numeric_values = data[list(NUMERIC_COLUMNS)].to_numpy(dtype=float)
        if self._numeric_mean is not None and self._numeric_std is not None:
            numeric_values = _standard_scaler_transform(
                numeric_values, self._numeric_mean, self._numeric_std
            )
        numeric_df = pd.DataFrame(
            numeric_values,
            index=data.index,
            columns=[f"num__{c}" for c in NUMERIC_COLUMNS],
        )

        output = pd.concat([numeric_df, encoded], axis=1)
        output = output[self._output_columns]
        self._validate_output(output)
        return output

    # ----------------------------------------------------------------- helpers

    def _expected_columns(self) -> list[str]:
        return list(NUMERIC_COLUMNS) + list(CATEGORICAL_COLUMNS)

    def _compute_output_columns(self) -> list[str]:
        columns = [f"num__{c}" for c in NUMERIC_COLUMNS]
        columns += [f"cat__{CATEGORICAL_COLUMNS[0]}__{c}" for c in self._type_categories]
        return columns

    def get_feature_names_out(self, input_features=None) -> list[str]:
        """Return transformed feature names (scikit-learn compatible)."""
        if not self._fitted:
            raise PreprocessingError("Preprocessor has not been fitted.")
        return list(self._output_columns)

    def _validate_output(self, output: pd.DataFrame) -> None:
        if output.isna().any().any():
            raise PreprocessingError("Transformed output contains NaN values for valid input.")
        numeric = output.select_dtypes(include=[np.number])
        if len(numeric.columns) and not np.isfinite(numeric.to_numpy()).all():
            raise PreprocessingError(
                "Transformed output contains non-finite values for valid input."
            )

    # ----------------------------------------------------------------- introspection

    @property
    def input_columns(self) -> list[str]:
        if not self._fitted:
            raise PreprocessingError("Preprocessor has not been fitted.")
        return list(self._input_columns)

    @property
    def output_columns(self) -> list[str]:
        if not self._fitted:
            raise PreprocessingError("Preprocessor has not been fitted.")
        return list(self._output_columns)

    def is_fitted(self) -> bool:
        return self._fitted

    def detect_unknown_categories(self, frame: pd.DataFrame) -> dict[str, list[str]]:
        """Return categorical values in ``frame`` not seen during fitting.

        Unknown ``Type`` values are encoded as all-zeros (they do not crash
        inference); this method surfaces them clearly for validation.
        """
        unknown: dict[str, list[str]] = {}
        type_col = CATEGORICAL_COLUMNS[0]
        if type_col not in frame.columns:
            return unknown
        present = {str(v) for v in frame[type_col].dropna().unique()}
        unseen = sorted(present - set(self._type_categories))
        if unseen:
            unknown[type_col] = unseen
        return unknown

    def to_artifact(self, split_settings: SplitSettings | None = None) -> PreprocessorArtifact:
        """Package the fitted preprocessor into a serialisable artifact."""
        if not self.is_fitted():
            raise PreprocessingError("Cannot package an unfitted preprocessor.")
        return PreprocessorArtifact(
            preprocessor=self,
            input_columns=self.input_columns,
            output_columns=self.output_columns,
            split_settings=split_settings,
            schema=self.schema,
            scale_numeric=self.scale_numeric,
        )

    @classmethod
    def from_artifact(cls, artifact: PreprocessorArtifact) -> "Preprocessor":
        """Rebuild a :class:`Preprocessor` from a packaged artifact."""
        preprocessor = cls(
            schema=artifact.schema,
            scale_numeric=artifact.scale_numeric,
        )
        preprocessor._fitted = True
        preprocessor._input_columns = list(artifact.input_columns)
        preprocessor._output_columns = list(artifact.output_columns)
        preprocessor._numeric_fill = dict(getattr(artifact.preprocessor, "_numeric_fill", {}))
        preprocessor._categorical_fill = dict(
            getattr(artifact.preprocessor, "_categorical_fill", {})
        )
        preprocessor._type_categories = list(getattr(artifact.preprocessor, "_type_categories", []))
        preprocessor._numeric_mean = getattr(artifact.preprocessor, "_numeric_mean", None)
        preprocessor._numeric_std = getattr(artifact.preprocessor, "_numeric_std", None)
        return preprocessor

    def save(self, path: str | Any) -> None:
        """Persist the fitted preprocessor with joblib."""
        if not self.is_fitted():
            raise PreprocessingError("Cannot save an unfitted preprocessor.")
        joblib.dump(self.to_artifact(), str(path))

    @classmethod
    def load(cls, path: str | Any) -> "Preprocessor":
        """Load a persisted fitted preprocessor."""
        artifact = joblib.load(str(path))
        if not isinstance(artifact, PreprocessorArtifact):
            raise PreprocessingError("Persisted artefact is not a PreprocessorArtifact.")
        return cls.from_artifact(artifact)


def split_train_test(
    frame: pd.DataFrame,
    target: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, SplitSettings]:
    """Deterministic stratified train/test split.

    The test partition is left untouched for later evaluation. If the target
    holds a single class, stratification is disabled and that is recorded.
    """
    if _sklearn_train_test_split is not None:
        try:
            unique_classes = target.nunique(dropna=True)
            stratify = target if unique_classes > 1 else None
            train_frame, test_frame, train_target, test_target = _sklearn_train_test_split(
                frame,
                target,
                test_size=test_size,
                random_state=random_state,
                stratify=stratify,
                shuffle=True,
            )
            settings = SplitSettings(
                test_size=test_size,
                random_state=random_state,
                stratify=unique_classes > 1,
                n_train=len(train_frame),
                n_test=len(test_frame),
            )
            return train_frame, test_frame, train_target, test_target, settings
        except ValueError:
            pass  # fall through to deterministic non-stratified split below

    # Deterministic fallback split (no sklearn available).
    rng = np.random.default_rng(random_state)
    indices = np.arange(len(frame))
    rng.shuffle(indices)
    n_test = max(1, round(len(frame) * test_size))
    test_idx = indices[:n_test]
    train_idx = indices[n_test:]
    train_frame = frame.iloc[train_idx].reset_index(drop=True)
    test_frame = frame.iloc[test_idx].reset_index(drop=True)
    train_target = target.iloc[train_idx].reset_index(drop=True)
    test_target = target.iloc[test_idx].reset_index(drop=True)
    settings = SplitSettings(
        test_size=test_size,
        random_state=random_state,
        stratify=False,
        n_train=len(train_frame),
        n_test=len(test_frame),
    )
    return train_frame, test_frame, train_target, test_target, settings
