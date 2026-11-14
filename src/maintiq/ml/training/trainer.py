"""Model training orchestration: splitting, class-imbalance handling, fitting,
artefact persistence and metadata capture for the four candidate classifiers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import importlib
from typing import Any

import numpy as np
import pandas as pd

from maintiq.config import SUPPORTED_MODELS, get_config
from maintiq.core.exceptions import ModelError
from maintiq.ml.evaluation.service import EvaluationService
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.preprocessing import Preprocessor, split_train_test
from maintiq.ml.training.factory import (
    XGBOOST,
    build_model,
    model_display_name,
)
from maintiq.ml.training.pipeline import ModelPipeline


@dataclass
class TrainingResult:
    """Outcome of a training run."""

    model_name: str
    model_version: str | None = None
    artifact_path: Any = None
    metrics: dict[str, float] | None = None
    training_duration_seconds: float | None = None
    split_settings: Any = None
    dataset_fingerprint: str | None = None
    library_versions: dict[str, str] | None = None
    cancelled: bool = False


class ModelTrainer:
    """Trains a candidate classifier on the training partition and saves it.

    The preprocessor and feature transformer are fitted on the training
    partition only and bundled inside the persisted pipeline. The final
    holdout test set is never used during training.
    """

    def __init__(
        self,
        registry: Any | None = None,
        random_seed: int = 42,
        test_size: float = 0.2,
        progress_callback: Callable[[str], None] | None = None,
    ):
        config = get_config()
        self.registry = registry
        self.random_seed = random_seed
        self.test_size = test_size
        self.default_threshold = config.default_threshold
        self.progress_callback = progress_callback or (lambda _msg: None)
        self.model_dir = config.paths.model_dir

    # ---------------------------------------------------------------- train

    def train_model(
        self,
        model_name: str,
        frame: pd.DataFrame,
        target: pd.Series,
        class_weight: str | None = "balanced",
        threshold: float | None = None,
        cancelled_check: Callable[[], bool] | None = None,
    ) -> TrainingResult:
        """Train ``model_name`` on ``frame``/``target`` and persist the pipeline.

        ``cancelled_check``, if provided, is called between stages; if it
        returns True the run aborts cleanly without corrupting artefacts.
        """
        if model_name not in SUPPORTED_MODELS:
            raise ModelError(
                f"Unsupported model '{model_name}'. Expected {list(SUPPORTED_MODELS)}."
            )
        if cancelled_check and cancelled_check():
            return TrainingResult(model_name=model_name, cancelled=True)

        self.progress_callback(f"splitting data for {model_name}")
        train_frame, test_frame, train_target, test_target, split_settings = split_train_test(
            frame, target, test_size=self.test_size, random_state=self.random_seed
        )

        if cancelled_check and cancelled_check():
            return TrainingResult(model_name=model_name, cancelled=True)

        dataset_fingerprint = self._fingerprint(frame)

        # Class-imbalance handling, calculated from the training partition only.
        scale_pos_weight = None
        if model_name == XGBOOST:
            scale_pos_weight = self._scale_pos_weight(train_target)

        self.progress_callback(f"building {model_display_name(model_name)} configuration")
        model_config = build_model(
            model_name,
            random_seed=self.random_seed,
            class_weight=class_weight,
            scale_pos_weight=scale_pos_weight,
        )

        self.progress_callback(f"fitting {model_display_name(model_name)}")
        start = datetime.now(timezone.utc)

        preprocessor = Preprocessor(
            random_seed=self.random_seed,
            scale_numeric=(model_name == "logistic_regression"),
        )
        feature_transformer = FeatureEngineeringTransformer()

        pipeline = ModelPipeline(
            model_name=model_name,
            estimator=model_config.estimator,
            preprocessor=preprocessor,
            feature_transformer=feature_transformer,
            threshold=threshold if threshold is not None else self.default_threshold,
        )
        pipeline.fit(train_frame, train_target)

        if cancelled_check and cancelled_check():
            return TrainingResult(model_name=model_name, cancelled=True)

        duration = (datetime.now(timezone.utc) - start).total_seconds()

        # Evaluate once on the untouched holdout partition.
        evaluator = EvaluationService()
        metrics = evaluator.evaluate(
            pipeline,
            test_frame,
            test_target,
            threshold=pipeline.threshold,
        )

        library_versions = self._library_versions()
        pipeline.dataset_fingerprint = dataset_fingerprint
        pipeline.library_versions = library_versions

        artifact_path = self._artifact_path(model_name)
        pipeline.save(artifact_path)

        self.progress_callback(f"registering {model_display_name(model_name)}")
        model_version = None
        if self.registry is not None:
            model_version = self.registry.register(
                model_name=model_name,
                artifact_path=artifact_path,
                metrics=metrics,
                parameters=model_config.params,
                split_settings=split_settings,
                dataset_fingerprint=dataset_fingerprint,
                feature_columns=list(preprocessor.input_columns),
                target_column="machine_failure",
                library_versions=library_versions,
            )

        self.progress_callback(f"completed {model_display_name(model_name)}")
        return TrainingResult(
            model_name=model_name,
            model_version=model_version,
            artifact_path=artifact_path,
            metrics=metrics,
            training_duration_seconds=duration,
            split_settings=split_settings,
            dataset_fingerprint=dataset_fingerprint,
            library_versions=library_versions,
        )

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _fingerprint(frame: pd.DataFrame) -> str:
        """Deterministic SHA-256 fingerprint of a data frame."""
        return sha256(
            pd.util.hash_pandas_object(frame, index=False).to_numpy().tobytes()
        ).hexdigest()

    @staticmethod
    def _scale_pos_weight(target: pd.Series) -> float | None:
        """Positive/negative weight ratio for XGBoost, from training only."""
        values = target.to_numpy()
        if values.size == 0:
            return None
        n_neg = float(np.sum(values == 0))
        n_pos = float(np.sum(values == 1))
        if n_pos == 0:
            return 1.0
        return n_neg / n_pos

    def _artifact_path(self, model_name: str) -> Any:
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in model_name)
        return self.model_dir / f"{safe_name}.joblib"

    @staticmethod
    def _library_versions() -> dict[str, str]:
        versions: dict[str, str] = {}
        versions["python"] = __import__("sys").version
        versions["pandas"] = getattr(pd, "__version__", "unknown")
        versions["numpy"] = getattr(np, "__version__", "unknown")
        for module_name in ("sklearn", "xgboost", "maintiq"):
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                versions[module_name] = "unknown"
                continue
            versions[module_name] = getattr(module, "__version__", "unknown")
        return versions
