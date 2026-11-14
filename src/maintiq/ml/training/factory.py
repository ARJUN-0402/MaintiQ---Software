"""Model factory: constructs candidate classifiers from validated configuration.

The factory centralises model construction so parameters are not scattered
through the codebase. scikit-learn estimators are used when importable; the
Gradient Boosting estimator has a pure-NumPy fallback for environments where
its compiled extension is unavailable (for example under a Windows Application
Control policy that blocks unsigned ``.pyd`` files).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from maintiq.config import SUPPORTED_MODELS
from maintiq.core.exceptions import ModelError

LOGISTIC_REGRESSION = "logistic_regression"
RANDOM_FOREST = "random_forest"
GRADIENT_BOOSTING = "gradient_boosting"
XGBOOST = "xgboost"

# Default hyperparameters per model. These are reproducible starting points,
# not claims of optimal industrial settings.
DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    LOGISTIC_REGRESSION: {"max_iter": 2000},
    RANDOM_FOREST: {"n_estimators": 100},
    GRADIENT_BOOSTING: {"n_estimators": 50, "learning_rate": 0.1},
    XGBOOST: {"n_estimators": 100, "max_depth": 6, "verbosity": 0},
}


@dataclass
class ModelConfiguration:
    """Resolved configuration for a single candidate model."""

    name: str
    estimator: Any
    params: dict[str, Any]
    supports_class_weight: bool
    supports_scale_pos_weight: bool


def _set_random_state(params: dict[str, Any], random_seed: int) -> None:
    """Set ``random_state`` on estimators that accept it."""
    params.setdefault("random_state", random_seed)


def build_model(
    model_name: str,
    random_seed: int = 42,
    params: dict[str, Any] | None = None,
    class_weight: str | None = None,
    scale_pos_weight: float | None = None,
) -> ModelConfiguration:
    """Build a classifier for ``model_name`` from validated configuration.

    ``class_weight`` is applied to estimators that support it (logistic
    regression, random forest). ``scale_pos_weight`` is applied to XGBoost and
    is calculated from the training partition only by the caller.
    """
    if model_name not in SUPPORTED_MODELS:
        raise ModelError(
            f"Unsupported model '{model_name}'. Expected one of {list(SUPPORTED_MODELS)}."
        )

    resolved = dict(DEFAULT_PARAMS.get(model_name, {}))
    resolved.update(params or {})

    supports_class_weight = False
    supports_scale_pos_weight = False

    if model_name == LOGISTIC_REGRESSION:
        from sklearn.linear_model import LogisticRegression  # noqa: PLC0415

        _set_random_state(resolved, random_seed)
        if class_weight:
            resolved["class_weight"] = class_weight
        supports_class_weight = True
        estimator = LogisticRegression(**resolved)

    elif model_name == RANDOM_FOREST:
        from sklearn.ensemble._forest import RandomForestClassifier  # noqa: PLC0415

        _set_random_state(resolved, random_seed)
        if class_weight:
            resolved["class_weight"] = class_weight
        supports_class_weight = True
        estimator = RandomForestClassifier(**resolved)

    elif model_name == XGBOOST:
        from xgboost import XGBClassifier  # noqa: PLC0415

        _set_random_state(resolved, random_seed)
        if scale_pos_weight is not None:
            resolved["scale_pos_weight"] = scale_pos_weight
        supports_scale_pos_weight = True
        estimator = XGBClassifier(**resolved)

    elif model_name == GRADIENT_BOOSTING:
        from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier  # noqa: PLC0415

        estimator = GradientBoostingFallbackClassifier(
            n_estimators=resolved.get("n_estimators", 50),
            learning_rate=resolved.get("learning_rate", 0.1),
            random_seed=random_seed,
        )

    else:  # pragma: no cover - guarded by the supported-models check above
        raise ModelError(f"No builder registered for model '{model_name}'.")

    return ModelConfiguration(
        name=model_name,
        estimator=estimator,
        params=resolved,
        supports_class_weight=supports_class_weight,
        supports_scale_pos_weight=supports_scale_pos_weight,
    )


def model_display_name(model_name: str) -> str:
    """Return a human-readable display name for a model key."""
    from maintiq.config import MODEL_DISPLAY_NAMES  # noqa: PLC0415

    return MODEL_DISPLAY_NAMES.get(model_name, model_name)
