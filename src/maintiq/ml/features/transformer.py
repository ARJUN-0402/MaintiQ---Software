"""Feature engineering for the MaintiQ predictive-maintenance prototype.

Implements the engineered features required by the MaintiQ synopsis in a single
reusable, scikit-learn-compatible transformer so that training and prediction
cannot drift apart:

* ``temperature_diff = process_temperature_k - air_temperature_k``
* ``power_kw = torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000``
* ``wear_rate = tool_wear_min / 253.0``  (normalised wear *proxy*, not a rate)
* ``torque_normalized = torque_nm / max_torque_train``  (reference from fit only)
* ``temp_wear_interaction = temperature_diff * tool_wear_min``

Raw predictive features are preserved. The torque-normalisation reference
(``max_torque_train``) is learned only from the data passed to ``fit`` (the
training partition), never from the holdout set.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from maintiq.core.exceptions import FeatureEngineeringError

try:  # scikit-learn is partially importable in locked-down environments
    from sklearn.base import BaseEstimator, TransformerMixin
except ImportError:  # pragma: no cover - environment without scikit-learn
    BaseEstimator = object  # type: ignore[assignment,misc]
    TransformerMixin = object  # type: ignore[assignment,misc]

# Canonical predictive input columns required by feature engineering.
REQUIRED_COLUMNS = (
    "type",
    "air_temperature_k",
    "process_temperature_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
)

# Documented normalisation denominator for the wear-rate proxy (AI4I
# documented ``Tool wear [min]`` range is approximately 0..253).
WEAR_RATE_DENOMINATOR = 253.0

# Output column names.
TEMPERATURE_DIFF = "temperature_diff"
POWER_KW = "power_kw"
WEAR_RATE = "wear_rate"
TORQUE_NORMALIZED = "torque_normalized"
TEMP_WEAR_INTERACTION = "temp_wear_interaction"

ENGINEERED_COLUMNS = (
    TEMPERATURE_DIFF,
    POWER_KW,
    WEAR_RATE,
    TORQUE_NORMALIZED,
    TEMP_WEAR_INTERACTION,
)

OUTPUT_COLUMNS = REQUIRED_COLUMNS + ENGINEERED_COLUMNS

# Mechanical power constant: (2 * pi / 60) converts rpm to rad/s; /1000 W->kW.
POWER_CONSTANT = (2.0 * math.pi / 60.0) / 1000.0


def power_kw(torque_nm: float, rotational_speed_rpm: float) -> float:
    """Mechanical power estimate in kW from torque (Nm) and speed (rpm)."""
    return float(torque_nm) * float(rotational_speed_rpm) * POWER_CONSTANT


class FeatureEngineeringTransformer(BaseEstimator, TransformerMixin):
    """Computes the synopsis engineered features.

    ``fit`` learns the ``max_torque_train`` reference from the training
    partition only. ``transform`` appends the engineered features to the raw
    predictive inputs and returns a DataFrame.
    """

    def __init__(self, copy: bool = True):
        self.copy = copy
        self._fitted = False
        self._max_torque_train: float | None = None
        self._input_columns: list[str] | None = None

    # ------------------------------------------------------------------ fit

    def fit(self, frame: pd.DataFrame, y: Any = None) -> "FeatureEngineeringTransformer":
        """Learn data-derived references (``max_torque_train``) from ``frame``.

        ``frame`` must contain only the predictive input columns. ``y`` is
        accepted for scikit-learn pipeline compatibility and ignored.
        """
        self._validate_columns(frame)
        self._input_columns = list(REQUIRED_COLUMNS)

        torque = pd.to_numeric(frame["torque_nm"], errors="coerce").to_numpy(dtype=float)
        finite_torque = torque[np.isfinite(torque)]
        if finite_torque.size == 0:
            max_torque = 1.0
        else:
            max_torque = float(np.max(finite_torque))
        if not np.isfinite(max_torque) or max_torque == 0.0:
            # Zero or invalid reference: fall back to 1.0 so normalisation is
            # safe (every normalised torque becomes 0.0) rather than crashing.
            max_torque = 1.0
        self._max_torque_train = max_torque
        self._fitted = True
        return self

    # ---------------------------------------------------------------- transform

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Append engineered features to the raw predictive inputs."""
        if not self._fitted:
            raise FeatureEngineeringError(
                "FeatureEngineeringTransformer has not been fitted. Call fit() before transform()."
            )
        self._validate_columns(frame)
        source = frame.copy(deep=self.copy) if self.copy else frame

        air = pd.to_numeric(source["air_temperature_k"], errors="coerce")
        process = pd.to_numeric(source["process_temperature_k"], errors="coerce")
        speed = pd.to_numeric(source["rotational_speed_rpm"], errors="coerce")
        torque = pd.to_numeric(source["torque_nm"], errors="coerce")
        wear = pd.to_numeric(source["tool_wear_min"], errors="coerce")

        self._validate_finite(air, "air_temperature_k")
        self._validate_finite(process, "process_temperature_k")
        self._validate_finite(speed, "rotational_speed_rpm")
        self._validate_finite(torque, "torque_nm")
        self._validate_finite(wear, "tool_wear_min")

        source[TEMPERATURE_DIFF] = process - air
        source[POWER_KW] = torque * speed * POWER_CONSTANT
        source[WEAR_RATE] = wear / WEAR_RATE_DENOMINATOR
        source[TORQUE_NORMALIZED] = torque / self._max_torque_train
        source[TEMP_WEAR_INTERACTION] = source[TEMPERATURE_DIFF] * wear

        return source[list(OUTPUT_COLUMNS)]

    def fit_transform(self, frame: pd.DataFrame, y: Any = None) -> pd.DataFrame:
        """Fit on ``frame`` then transform it, returning only the result."""
        self.fit(frame, y)
        return self.transform(frame)

    # ---------------------------------------------------------------- introspection

    def get_feature_names_out(self, input_features: Any = None) -> list[str]:
        """Return the names of all output columns (scikit-learn compatible)."""
        if not self._fitted:
            raise FeatureEngineeringError("FeatureEngineeringTransformer has not been fitted.")
        return list(OUTPUT_COLUMNS)

    @property
    def max_torque_train(self) -> float:
        """The training-fitted torque normalisation reference."""
        if not self._fitted:
            raise FeatureEngineeringError("FeatureEngineeringTransformer has not been fitted.")
        return self._max_torque_train

    @classmethod
    def formulas(cls) -> dict[str, str]:
        """Human-readable formulas for the engineered features."""
        return {
            TEMPERATURE_DIFF: "process_temperature_k - air_temperature_k",
            POWER_KW: (
                "torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000 "
                "(mechanical power estimate, kW)"
            ),
            WEAR_RATE: (
                f"tool_wear_min / {WEAR_RATE_DENOMINATOR} "
                "(normalised wear *proxy*, not a wear-per-time rate)"
            ),
            TORQUE_NORMALIZED: (
                "torque_nm / max_torque_train (max_torque_train learned from "
                "training data only; no test-data leakage)"
            ),
            TEMP_WEAR_INTERACTION: "temperature_diff * tool_wear_min",
        }

    @classmethod
    def metadata(cls) -> dict[str, dict[str, str]]:
        """Formula, unit and limitation metadata for every engineered feature."""
        return {
            TEMPERATURE_DIFF: {
                "formula": "process_temperature_k - air_temperature_k",
                "unit": "K",
                "description": "Difference between process and air temperature.",
            },
            POWER_KW: {
                "formula": "torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000",
                "unit": "kW",
                "description": (
                    "Derived mechanical power estimate from torque (Nm) and rotational speed (rpm)."
                ),
            },
            WEAR_RATE: {
                "formula": f"tool_wear_min / {WEAR_RATE_DENOMINATOR}",
                "unit": "normalised (0..1 approx.)",
                "description": (
                    "Normalised wear proxy based on the documented AI4I tool-wear "
                    "range. NOT an observed wear-per-time rate (no elapsed-time "
                    "denominator is supplied by a single snapshot)."
                ),
            },
            TORQUE_NORMALIZED: {
                "formula": "torque_nm / max_torque_train",
                "unit": "normalised",
                "description": (
                    "Torque normalised by a reference learned from training data "
                    "only; no test-data leakage."
                ),
            },
            TEMP_WEAR_INTERACTION: {
                "formula": "temperature_diff * tool_wear_min",
                "unit": "K * min",
                "description": "Interaction between temperature difference and tool wear.",
            },
        }

    # ------------------------------------------------------------------ helpers

    def _validate_columns(self, frame: pd.DataFrame) -> None:
        missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise FeatureEngineeringError(f"Feature engineering requires columns: {missing}")

    def _validate_finite(self, series: pd.Series, name: str) -> None:
        values = series.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise FeatureEngineeringError(
                f"Column '{name}' contains non-finite values. Feature engineering "
                "requires finite numeric inputs."
            )
