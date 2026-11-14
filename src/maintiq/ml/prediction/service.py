"""Single-record prediction engine with explainability integration.

The :class:`PredictionService` loads trained :class:`~maintiq.ml.training.pipeline.ModelPipeline`
artefacts from the model registry, validates single input records against the
canonical schema, runs inference, and (optionally) explains the prediction using
the exact same model and record via :func:`maintiq.ml.explainability.explain_local`.

Explanations are optional and never block a prediction: when no explainability
backend is available the prediction is still returned with a clear error note.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from maintiq.core.exceptions import ModelError, ModelNotFoundError, PredictionError
from maintiq.data.schema import CANONICAL_PREDICTIVE_INPUTS, DatasetSchema
from maintiq.ml.explainability import ExplanationResult, explain_local
from maintiq.ml.training.pipeline import ModelPipeline, PredictionResult


@dataclass
class PredictionOutcome:
    """Outcome of a prediction request, with an optional explanation.

    The prediction is always populated. ``explanation`` is populated only when an
    explainability backend could produce one; otherwise ``explanation_error``
    holds the reason and the application can continue without explanations.
    """

    prediction: PredictionResult
    explanation: ExplanationResult | None = None
    explanation_error: str | None = None


class PredictionService:
    """Single-record inference engine for trained MaintiQ pipelines."""

    def __init__(
        self,
        registry: Any | None = None,
        schema: DatasetSchema | None = None,
    ):
        self.registry = registry
        self.schema = schema or DatasetSchema()

    # ---------------------------------------------------------------- loading

    def load_model(self, model_name: str, version: str | None = None) -> ModelPipeline:
        """Load a fitted pipeline from the model registry.

        When ``version`` is None the latest registered version is used.
        Raises ``ModelNotFoundError`` when the model or version is absent and
        ``ModelHashMismatchError`` when the artefact checksum fails.
        """
        if self.registry is None:
            raise PredictionError("No model registry configured; cannot load model.")
        if not self.registry.model_exists(model_name):
            raise ModelNotFoundError(f"Model {model_name!r} is not registered.")
        versions = self.registry.list_versions(model_name)
        if not versions:
            raise ModelNotFoundError(f"No versions registered for model {model_name!r}.")
        version = version or versions[-1]
        record = self.registry.get_version(model_name, version)
        artifact_path = self.registry.get_artifact_path(model_name, version)
        pipeline = ModelPipeline.load(artifact_path)
        pipeline.model_version = record.get("version", version)
        return pipeline

    # ------------------------------------------------------------- validation

    def _validate_record(self, input_record: Any) -> pd.DataFrame:
        """Normalise a dict/Series/DataFrame into a validated single-row frame."""
        if isinstance(input_record, dict):
            frame = pd.DataFrame([input_record])
        elif isinstance(input_record, pd.Series):
            frame = pd.DataFrame([input_record.to_dict()])
        elif isinstance(input_record, pd.DataFrame):
            if len(input_record) != 1:
                raise PredictionError("input_record must contain exactly one row.")
            frame = input_record.copy()
        else:
            raise PredictionError(
                "input_record must be a dict, pandas Series, or single-row DataFrame."
            )

        missing = [c for c in CANONICAL_PREDICTIVE_INPUTS if c not in frame.columns]
        if missing:
            raise PredictionError(
                f"Input record missing required columns: {missing}. "
                f"Expected {list(CANONICAL_PREDICTIVE_INPUTS)}."
            )
        return frame

    def _out_of_distribution_warnings(
        self,
        pipeline: ModelPipeline,
        frame: pd.DataFrame,
    ) -> list[str]:
        """Surface category/domain drift without blocking inference."""
        warnings: list[str] = []
        try:
            unknown = pipeline.preprocessor.detect_unknown_categories(frame)
            for column, values in unknown.items():
                warnings.append(
                    f"Unseen {column} category value(s) {values}; encoded as all-zeros."
                )
        except Exception:
            pass
        for column, (minimum, maximum) in self.schema.numeric_domains.items():
            if column not in frame.columns:
                continue
            series = pd.to_numeric(frame[column], errors="coerce").dropna()
            if minimum is not None and bool((series < minimum).any()):
                warnings.append(
                    f"Column '{column}' contains values below domain minimum {minimum}."
                )
            if maximum is not None and bool((series > maximum).any()):
                warnings.append(
                    f"Column '{column}' contains values above domain maximum {maximum}."
                )
        return warnings

    # --------------------------------------------------------------- predict

    def predict(self, pipeline: ModelPipeline, input_record: Any) -> PredictionResult:
        """Run single-record inference on ``pipeline`` for ``input_record``.

        Validates the input record, applies out-of-distribution checks, then
        returns a :class:`PredictionResult` with class, score and threshold.
        """
        if not pipeline.is_fitted:
            raise ModelError("Pipeline has not been fitted. Train or load a model first.")

        frame = self._validate_record(input_record)
        warnings = self._out_of_distribution_warnings(pipeline, frame)

        proba = pipeline.predict_proba(frame)
        pos_idx = 1
        if hasattr(pipeline.estimator, "classes_"):
            classes = list(pipeline.estimator.classes_)
            if 1 in classes:
                pos_idx = classes.index(1)
            else:
                pos_idx = len(classes) - 1
        score = float(np.asarray(proba, dtype=float)[0, pos_idx])
        predicted = int(pipeline.predict(frame)[0])

        return PredictionResult(
            predicted_class=predicted,
            score=score,
            threshold=float(pipeline.threshold),
            model_name=pipeline.model_name,
            model_version=pipeline.model_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_validated=True,
            out_of_distribution_warnings=warnings,
            explanation_available=False,
        )

    # ------------------------------------------------------- predict and explain

    def predict_and_explain(
        self,
        pipeline: ModelPipeline,
        input_record: Any,
        background_data: Any = None,
        method: str = "auto",
    ) -> PredictionOutcome:
        """Predict and explain a single record using the same model and record.

        Runs :meth:`predict`, then calls :func:`explain_local` with the fitted
        pipeline and the exact input record so the explanation is grounded in the
        same transformation and inference path. The explanation backend receives
        ``background_data`` as both the SHAP reference sample and the LIME
        training reference when provided.

        Explanation failures are captured in ``explanation_error`` and never
        cause the prediction to fail.
        """
        prediction = self.predict(pipeline, input_record)
        explanation: ExplanationResult | None = None
        explanation_error: str | None = None
        try:
            explanation = explain_local(
                pipeline,
                input_record,
                method=method,
                background_data=background_data,
                training_data=background_data,
            )
        except Exception as exc:  # explanation is optional; never fail the prediction
            explanation_error = f"{type(exc).__name__}: {exc}"

        return PredictionOutcome(
            prediction=prediction,
            explanation=explanation,
            explanation_error=explanation_error,
        )


__all__ = ["PredictionOutcome", "PredictionService"]
