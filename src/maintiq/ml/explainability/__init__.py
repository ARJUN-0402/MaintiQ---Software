"""SHAP and LIME explainability services.

All imports are lazy and optional so blocked native dependencies (e.g. SHAP
pulling in ``sklearn.cluster`` extensions under Windows Application Control)
do not affect application startup or non-explainability workflows.

Explanations describe model behaviour; they are never causal claims and must
never be fabricated when the underlying library is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import numpy as np
import pandas as pd

from maintiq.config import RANDOM_SEED
from maintiq.core.exceptions import ExplanationError, MaintiQError, ModelError
from maintiq.ml.features.transformer import REQUIRED_COLUMNS


@dataclass
class DependencyStatus:
    """Availability of an optional explainability dependency."""

    name: str
    available: bool
    version: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.available,
            "version": self.version,
            "reason": self.reason,
        }


@dataclass
class ExplanationResult:
    """Structured result for a local or global explanation request."""

    method: str
    available: bool
    contributions: list[dict[str, Any]] = field(default_factory=list)
    reason: str | None = None
    disclaimer: str = (
        "Explanation reflects model behaviour for this input; it is not a "
        "causal diagnosis or maintenance instruction."
    )
    model_name: str | None = None
    model_version: str | None = None
    threshold: float | None = None
    input_record: dict[str, Any] | None = None
    predicted_class: int | str | None = None
    score: float | None = None
    global_importance: list[dict[str, Any]] = field(default_factory=list)
    feature_labels: dict[str, str] = field(default_factory=dict)


# Human-readable labels for the transformed (processed) feature names that the
# fitted estimators actually consume. Categorical one-hot columns are labelled
# dynamically in :func:`_build_feature_labels`.
_NUMERIC_LABELS: dict[str, str] = {
    "num__air_temperature_k": "Air temperature [K]",
    "num__process_temperature_k": "Process temperature [K]",
    "num__rotational_speed_rpm": "Rotational speed [rpm]",
    "num__torque_nm": "Torque [Nm]",
    "num__tool_wear_min": "Tool wear [min]",
}

# Maximum number of reference samples used to build an explainer background.
# Kept small so SHAP KernelExplainer and LIME remain responsive.
_DEFAULT_BACKGROUND_SIZE = 100


def _probe_import(module_name: str) -> tuple[Any | None, str | None]:
    try:
        module = import_module(module_name)
        return module, None
    except Exception as exc:  # optional dependency: import-time or DLL policy failure
        return None, f"{type(exc).__name__}: {exc}"


def shap_status() -> DependencyStatus:
    """Return SHAP availability without importing it at application startup."""
    module, reason = _probe_import("shap")
    if module is None:
        return DependencyStatus(name="shap", available=False, reason=reason)
    return DependencyStatus(
        name="shap",
        available=True,
        version=getattr(module, "__version__", None),
    )


def lime_status() -> DependencyStatus:
    """Return LIME availability without importing it at application startup."""
    module, reason = _probe_import("lime")
    if module is None:
        return DependencyStatus(name="lime", available=False, reason=reason)
    return DependencyStatus(
        name="lime",
        available=True,
        version=getattr(module, "__version__", None),
    )


def explainability_status() -> dict[str, DependencyStatus]:
    """Report availability of optional explainability backends."""
    return {"shap": shap_status(), "lime": lime_status()}


def require_shap() -> Any:
    """Import and return SHAP, or raise a clear :class:`ExplanationError`."""
    status = shap_status()
    if not status.available:
        raise ExplanationError(
            "SHAP is unavailable in this environment. "
            f"Reason: {status.reason}. "
            "The application can continue without SHAP explanations."
        )
    return import_module("shap")


def require_lime() -> Any:
    """Import and return LIME, or raise a clear :class:`ExplanationError`."""
    status = lime_status()
    if not status.available:
        raise ExplanationError(
            "LIME is unavailable in this environment. "
            f"Reason: {status.reason}. "
            "The application can continue without LIME explanations."
        )
    return import_module("lime")


# --------------------------------------------------------------------------- #
# Pipeline helpers
# --------------------------------------------------------------------------- #


def _positive_class_index(estimator: Any) -> int:
    """Return the column index of the positive class (value 1 when present)."""
    classes = list(getattr(estimator, "classes_", [0, 1]))
    if 1 in classes:
        return classes.index(1)
    return len(classes) - 1


def _validate_input_columns(frame: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ExplanationError(
            f"Input record missing required columns: {missing}. Expected {list(REQUIRED_COLUMNS)}."
        )


def _as_single_row_frame(input_record: Any) -> pd.DataFrame:
    """Normalise a dict/Series/DataFrame into a single-row DataFrame."""
    if isinstance(input_record, dict):
        return pd.DataFrame([input_record])
    if isinstance(input_record, pd.Series):
        return pd.DataFrame([input_record.to_dict()])
    if isinstance(input_record, pd.DataFrame):
        if len(input_record) != 1:
            raise ExplanationError("input_record must contain exactly one row.")
        return input_record
    raise ExplanationError("input_record must be a dict, pandas Series, or single-row DataFrame.")


def _as_dataframe(reference_data: Any) -> pd.DataFrame:
    if isinstance(reference_data, pd.DataFrame):
        return reference_data
    if isinstance(reference_data, dict):
        return pd.DataFrame([reference_data])
    raise ExplanationError("reference data must be a pandas DataFrame or dict.")


def _processed_frame(pipeline: Any, raw_frame: pd.DataFrame) -> pd.DataFrame:
    """Transform a raw input frame into the processed feature frame the estimator sees.

    Runs feature engineering then preprocessing, mirroring
    :meth:`ModelPipeline._engineer`, using only public pipeline components.
    """
    if not pipeline.is_fitted:
        raise ModelError("ModelPipeline has not been fitted. Train or load a model first.")
    engineered = pipeline.feature_transformer.transform(raw_frame)
    processed = pipeline.preprocessor.transform(engineered)
    return processed


def _background_sample(
    processed_frame: pd.DataFrame,
    max_size: int = _DEFAULT_BACKGROUND_SIZE,
    random_seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Return a deterministic, bounded reference sample for explainer background data."""
    n = len(processed_frame)
    if n == 0:
        raise ExplanationError("Reference data is empty; cannot build explainer background.")
    if n <= max_size:
        return processed_frame.reset_index(drop=True)
    rng = np.random.default_rng(random_seed)
    indices = np.sort(rng.choice(n, size=max_size, replace=False))
    return processed_frame.iloc[indices].reset_index(drop=True)


def _build_feature_labels(
    feature_names: list[str], feature_labels: dict[str, str] | None = None
) -> dict[str, str]:
    """Map transformed feature names to human-readable labels."""
    labels: dict[str, str] = {}
    for name in feature_names:
        if name in _NUMERIC_LABELS:
            labels[name] = _NUMERIC_LABELS[name]
        elif name.startswith("cat__type__"):
            cat_value = name.split("cat__type__", 1)[1]
            labels[name] = f"Machine type: {cat_value}"
        else:
            labels[name] = name
    if feature_labels:
        labels.update(feature_labels)
    return labels


def _prediction_summary(pipeline: Any, record: pd.DataFrame) -> tuple[int | str, float]:
    """Return (predicted_class, score) for the positive class of a single record."""
    proba = pipeline.predict_proba(record)
    pos_idx = _positive_class_index(pipeline.estimator)
    score = float(np.asarray(proba, dtype=float)[0, pos_idx])
    predicted = int(pipeline.predict(record)[0])
    return predicted, score


# --------------------------------------------------------------------------- #
# SHAP
# --------------------------------------------------------------------------- #


def explain_with_shap(
    pipeline: Any,
    input_record: Any,
    background_data: Any = None,
    feature_labels: dict[str, str] | None = None,
    max_evals: int = 1000,
    background_size: int = _DEFAULT_BACKGROUND_SIZE,
) -> ExplanationResult:
    """Return a local SHAP explanation for a single prediction.

    Uses a model-agnostic :class:`shap.KernelExplainer` over the positive-class
    probability so it works with every supported estimator, including the
    pure-NumPy Gradient Boosting fallback. ``background_data`` is required as
    the SHAP reference distribution; without it no explanation can be produced.

    Raises :class:`ExplanationError` when SHAP cannot be imported or when the
    pipeline/reference data cannot be prepared. No fabricated explanation is
    ever returned.
    """
    require_shap()  # raises ExplanationError when SHAP is unavailable
    import shap  # noqa: PLC0415 - lazy optional import

    record = _as_single_row_frame(input_record)
    _validate_input_columns(record)

    if background_data is None:
        raise ExplanationError(
            "SHAP requires background_data (a reference sample of training rows) "
            "to build the explainer. Provide background_data or use explain_local "
            "with an available backend."
        )
    bg_frame = _as_dataframe(background_data)
    try:
        _validate_input_columns(bg_frame)
        processed_bg = _processed_frame(pipeline, bg_frame)
        processed_record = _processed_frame(pipeline, record)
    except MaintiQError as exc:
        if isinstance(exc, ExplanationError):
            raise
        raise ExplanationError(f"Cannot prepare input for SHAP explanation: {exc}") from exc

    background_array = _background_sample(processed_bg, max_size=background_size).to_numpy(
        dtype=float
    )
    record_array = processed_record.to_numpy(dtype=float).ravel().reshape(1, -1)

    feature_names = list(pipeline.preprocessor.get_feature_names_out())
    labels = _build_feature_labels(feature_names, feature_labels)
    pos_idx = _positive_class_index(pipeline.estimator)

    def model_fn(x: np.ndarray) -> np.ndarray:
        proba = pipeline.estimator.predict_proba(np.asarray(x, dtype=float))
        return np.asarray(proba, dtype=float)[:, pos_idx]

    explainer = shap.KernelExplainer(model_fn, background_array)
    shap_values = explainer.shap_values(record_array, nsamples=max_evals)
    values = np.asarray(shap_values, dtype=float).reshape(-1)

    contributions = [
        {
            "feature": feature_names[i],
            "label": labels.get(feature_names[i], feature_names[i]),
            "contribution": float(values[i]),
            "abs_contribution": float(abs(values[i])),
        }
        for i in range(len(feature_names))
    ]
    contributions.sort(key=lambda item: -item["abs_contribution"])

    predicted, score = _prediction_summary(pipeline, record)

    return ExplanationResult(
        method="shap",
        available=True,
        contributions=contributions,
        model_name=getattr(pipeline, "model_name", None),
        model_version=getattr(pipeline, "model_version", None),
        threshold=float(pipeline.threshold),
        input_record=record.iloc[0].to_dict(),
        predicted_class=predicted,
        score=score,
        feature_labels=labels,
    )


# --------------------------------------------------------------------------- #
# LIME
# --------------------------------------------------------------------------- #


def explain_with_lime(
    pipeline: Any,
    input_record: Any,
    training_data: Any = None,
    feature_labels: dict[str, str] | None = None,
    num_features: int | None = None,
) -> ExplanationResult:
    """Return a local LIME tabular explanation for a single prediction.

    Builds a :class:`lime.lime_tabular.LimeTabularExplainer` over the processed
    feature space using the same feature order and preprocessing logic the
    fitted model expects. ``training_data`` is required as the reference sample;
    without it no explanation can be produced.

    Raises :class:`ExplanationError` when LIME cannot be imported or when the
    pipeline/reference data cannot be prepared. No fabricated explanation is
    ever returned.
    """
    require_lime()  # raises ExplanationError when LIME is unavailable
    from lime.lime_tabular import LimeTabularExplainer  # noqa: PLC0415 - lazy optional import

    record = _as_single_row_frame(input_record)
    _validate_input_columns(record)

    if training_data is None:
        raise ExplanationError(
            "LIME requires training_data (a reference sample of training rows) "
            "to build the tabular explainer. Provide training_data or use "
            "explain_local with an available backend."
        )
    train_frame = _as_dataframe(training_data)
    try:
        _validate_input_columns(train_frame)
        processed_train = _processed_frame(pipeline, train_frame)
        processed_record = _processed_frame(pipeline, record)
    except MaintiQError as exc:
        if isinstance(exc, ExplanationError):
            raise
        raise ExplanationError(f"Cannot prepare input for LIME explanation: {exc}") from exc

    feature_names = list(pipeline.preprocessor.get_feature_names_out())
    labels = _build_feature_labels(feature_names, feature_labels)
    classes = list(getattr(pipeline.estimator, "classes_", [0, 1]))
    class_names = [str(c) for c in classes]
    pos_label_idx = _positive_class_index(pipeline.estimator)

    explainer = LimeTabularExplainer(
        processed_train.to_numpy(dtype=float),
        feature_names=feature_names,
        class_names=class_names,
        discretize_continuous=False,
        random_state=RANDOM_SEED,
    )

    num_features = num_features if num_features is not None else len(feature_names)
    explanation = explainer.explain_instance(
        processed_record.to_numpy(dtype=float).ravel(),
        lambda x: pipeline.estimator.predict_proba(np.asarray(x, dtype=float)),
        num_features=num_features,
        labels=(pos_label_idx,),
    )

    as_list = explanation.as_list(label=pos_label_idx)
    contributions = [
        {
            "feature": name,
            "label": labels.get(name, name),
            "contribution": float(weight),
            "abs_contribution": float(abs(weight)),
        }
        for name, weight in as_list
    ]
    contributions.sort(key=lambda item: -item["abs_contribution"])

    predicted, score = _prediction_summary(pipeline, record)

    return ExplanationResult(
        method="lime",
        available=True,
        contributions=contributions,
        model_name=getattr(pipeline, "model_name", None),
        model_version=getattr(pipeline, "model_version", None),
        threshold=float(pipeline.threshold),
        input_record=record.iloc[0].to_dict(),
        predicted_class=predicted,
        score=score,
        feature_labels=labels,
    )


# --------------------------------------------------------------------------- #
# Convenience entry points
# --------------------------------------------------------------------------- #


def explain_local(
    pipeline: Any,
    input_record: Any,
    method: str = "auto",
    background_data: Any = None,
    training_data: Any = None,
    feature_labels: dict[str, str] | None = None,
    **kwargs: Any,
) -> ExplanationResult:
    """Explain a single prediction, trying backends in preference order.

    ``method`` may be ``"auto"`` (SHAP then LIME), ``"shap"``, or ``"lime"``.
    Raises :class:`ExplanationError` if no backend can produce an explanation.
    """
    methods = ["shap", "lime"] if method == "auto" else [method]
    last_error: str | None = None
    for backend in methods:
        try:
            if backend == "shap":
                return explain_with_shap(
                    pipeline,
                    input_record,
                    background_data=background_data,
                    feature_labels=feature_labels,
                    **kwargs,
                )
            if backend == "lime":
                return explain_with_lime(
                    pipeline,
                    input_record,
                    training_data=training_data,
                    feature_labels=feature_labels,
                    num_features=kwargs.get("num_features"),
                    **{k: v for k, v in kwargs.items() if k != "num_features"},
                )
        except ExplanationError as exc:
            last_error = str(exc)
            continue
    raise ExplanationError(
        f"No explainability backend could produce an explanation ({'; '.join(methods)}). "
        f"Last error: {last_error}. The application can continue without explanations."
    )


def explain_global(
    pipeline: Any,
    background_data: Any,
    method: str = "shap",
    feature_labels: dict[str, str] | None = None,
    background_size: int = _DEFAULT_BACKGROUND_SIZE,
) -> ExplanationResult:
    """Return a global feature-importance explanation.

    Uses mean absolute SHAP values across the bounded background sample when
    SHAP is available. Falls back to LIME only when explicitly requested; LIME
    is inherently local and does not produce a natural global importance, so a
    clear error is raised if SHAP is unavailable.
    """
    if method not in ("shap", "auto"):
        raise ExplanationError(
            "Global explanations are only supported via SHAP. LIME is local-only."
        )
    require_shap()  # raises ExplanationError when SHAP is unavailable
    import shap  # noqa: PLC0415 - lazy optional import

    bg_frame = _as_dataframe(background_data)
    try:
        _validate_input_columns(bg_frame)
        processed_bg = _processed_frame(pipeline, bg_frame)
    except MaintiQError as exc:
        if isinstance(exc, ExplanationError):
            raise
        raise ExplanationError(
            f"Cannot prepare background data for global explanation: {exc}"
        ) from exc
    background_array = _background_sample(processed_bg, max_size=background_size).to_numpy(
        dtype=float
    )

    feature_names = list(pipeline.preprocessor.get_feature_names_out())
    labels = _build_feature_labels(feature_names, feature_labels)
    pos_idx = _positive_class_index(pipeline.estimator)

    def model_fn(x: np.ndarray) -> np.ndarray:
        proba = pipeline.estimator.predict_proba(np.asarray(x, dtype=float))
        return np.asarray(proba, dtype=float)[:, pos_idx]

    explainer = shap.KernelExplainer(model_fn, background_array)
    shap_values = explainer.shap_values(background_array)
    values = np.asarray(shap_values, dtype=float)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    mean_abs = np.mean(np.abs(values), axis=0)

    importance = [
        {
            "feature": feature_names[i],
            "label": labels.get(feature_names[i], feature_names[i]),
            "importance": float(mean_abs[i]),
        }
        for i in range(len(feature_names))
    ]
    importance.sort(key=lambda item: -item["importance"])

    return ExplanationResult(
        method="shap",
        available=True,
        global_importance=importance,
        model_name=getattr(pipeline, "model_name", None),
        model_version=getattr(pipeline, "model_version", None),
        feature_labels=labels,
    )


__all__ = [
    "DependencyStatus",
    "ExplanationResult",
    "explain_global",
    "explain_local",
    "explain_with_lime",
    "explain_with_shap",
    "explainability_status",
    "lime_status",
    "require_lime",
    "require_shap",
    "shap_status",
]
