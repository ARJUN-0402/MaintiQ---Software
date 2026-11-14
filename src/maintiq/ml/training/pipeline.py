"""A trained model pipeline bundling preprocessing, feature engineering and
the estimator, so inference applies exactly the training-time transformation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd

from maintiq.core.exceptions import ModelError
from maintiq.data.schema import DatasetSchema
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.preprocessing import Preprocessor

PREDICTION_COLUMN = "machine_failure"


@dataclass
class PredictionResult:
    """Structured result of a single-record prediction."""

    predicted_class: int | str
    score: float | None
    threshold: float
    model_name: str
    model_version: str | None
    timestamp: str
    input_validated: bool
    out_of_distribution_warnings: list[str] = field(default_factory=list)
    explanation_available: bool = False


@dataclass
class ModelPipelineArtifact:
    """Serialisable bundle of everything needed for inference."""

    model_name: str
    model_version: str | None
    preprocessor: Any
    feature_transformer: Any
    estimator: Any
    feature_columns: list[str]
    target_column: str
    threshold: float
    trained_at: str
    dataset_fingerprint: str | None = None
    library_versions: dict[str, str] | None = None
    schema: DatasetSchema | None = None


class ModelPipeline:
    """Bundles a fitted preprocessor, feature transformer and estimator.

    Inference runs ``preprocessor.transform`` then
    ``feature_transformer.transform`` then ``estimator.predict / predict_proba``.
    """

    def __init__(
        self,
        model_name: str,
        estimator: Any,
        preprocessor: Preprocessor,
        feature_transformer: FeatureEngineeringTransformer,
        threshold: float = 0.5,
        model_version: str | None = None,
        dataset_fingerprint: str | None = None,
        library_versions: dict[str, str] | None = None,
    ):
        self.model_name = model_name
        self.estimator = estimator
        self.preprocessor = preprocessor
        self.feature_transformer = feature_transformer
        self.threshold = float(threshold)
        self.model_version = model_version
        self.dataset_fingerprint = dataset_fingerprint
        self.library_versions = library_versions or {}
        self._fitted = False

    # ------------------------------------------------------------------ fit

    def fit(self, frame: pd.DataFrame, target: pd.Series) -> "ModelPipeline":
        """Fit feature transformer, preprocessor and estimator in sequence.

        The feature transformer is fitted on the raw training frame (it learns
        ``max_torque_train``), then the preprocessor is fitted on the engineered
        training frame (imputation/scaling references). The estimator is fitted
        on the fully processed training frame. The holdout set is never touched.
        """
        self.feature_transformer.fit(frame)
        engineered = self.feature_transformer.transform(frame)
        self.preprocessor.fit(engineered, target)
        processed = self.preprocessor.transform(engineered)
        self.estimator.fit(processed.to_numpy(dtype=float), target.to_numpy())
        self._fitted = True
        return self

    # --------------------------------------------------------------- predict

    def _engineer(self, frame: pd.DataFrame) -> np.ndarray:
        if not self._fitted:
            raise ModelError("ModelPipeline has not been fitted.")
        engineered = self.feature_transformer.transform(frame)
        processed = self.preprocessor.transform(engineered)
        return processed.to_numpy(dtype=float)

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        scores = self.estimator.predict_proba(self._engineer(frame))
        return np.asarray(scores, dtype=float)

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        scores = self.predict_proba(frame)
        positive_index = 1
        if hasattr(self.estimator, "classes_"):
            classes = list(self.estimator.classes_)
            if 1 in classes:
                positive_index = classes.index(1)
            else:
                positive_index = len(classes) - 1
        return (scores[:, positive_index] >= self.threshold).astype(int)

    def _to_artifact(self) -> ModelPipelineArtifact:
        if not self._fitted:
            raise ModelError("Cannot package an unfitted pipeline.")
        return ModelPipelineArtifact(
            model_name=self.model_name,
            model_version=self.model_version,
            preprocessor=self.preprocessor,
            feature_transformer=self.feature_transformer,
            estimator=self.estimator,
            feature_columns=list(self.preprocessor.input_columns),
            target_column="machine_failure",
            threshold=self.threshold,
            trained_at=datetime.now(timezone.utc).isoformat(),
            dataset_fingerprint=self.dataset_fingerprint,
            library_versions=self.library_versions,
        )

    def save(self, path: str | Any) -> ModelPipelineArtifact:
        """Persist the trained pipeline with joblib and return its artifact."""
        artifact = self._to_artifact()
        joblib.dump(artifact, str(path))
        return artifact

    @classmethod
    def load(cls, path: str | Any) -> "ModelPipeline":
        """Load a persisted trained pipeline."""
        artifact = joblib.load(str(path))
        if not isinstance(artifact, ModelPipelineArtifact):
            raise ModelError("Persisted artefact is not a ModelPipelineArtifact.")
        pipeline = cls(
            model_name=artifact.model_name,
            estimator=artifact.estimator,
            preprocessor=artifact.preprocessor,
            feature_transformer=artifact.feature_transformer,
            threshold=artifact.threshold,
            model_version=artifact.model_version,
            dataset_fingerprint=artifact.dataset_fingerprint,
            library_versions=artifact.library_versions,
        )
        pipeline._fitted = True
        return pipeline

    @property
    def is_fitted(self) -> bool:
        return self._fitted
