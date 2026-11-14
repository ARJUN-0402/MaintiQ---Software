"""Cross-service integration tests for ApplicationService delegation.

Verifies that ApplicationService correctly delegates to its components
(import, training/registry, prediction, reporting) and that the active-dataset
fallback works end to end.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import MaintiQError, ModelNotFoundError
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.prediction import PredictionService
from maintiq.ml.prediction.service import PredictionOutcome
from maintiq.ml.preprocessing import Preprocessor, split_train_test
from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier
from maintiq.ml.training.pipeline import ModelPipeline
from maintiq.ml.training.registry import ModelRegistry
from maintiq.services.application_service import ApplicationService


def _make_frame(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=n),
            "air_temperature_k": rng.uniform(290, 310, size=n),
            "process_temperature_k": rng.uniform(295, 315, size=n),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=n),
            "torque_nm": rng.uniform(30, 60, size=n),
            "tool_wear_min": rng.uniform(0, 200, size=n),
        }
    )


def _make_target(n: int = 80) -> pd.Series:
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < 0.3).astype(int), name="machine_failure")


def test_application_service_delegates_import_train_predict_report(tmp_path):
    """ApplicationService delegates import, train, predict and report to components."""
    service = ApplicationService()

    import_service = MagicMock()
    trainer = MagicMock()
    registry = MagicMock()
    prediction_service = MagicMock()
    report_service = MagicMock()

    service.import_service = import_service
    service.trainer = trainer
    service.registry = registry
    service.prediction_service = prediction_service
    service.report_service = report_service

    frame = _make_frame()
    target = _make_target()

    import_service.import_dataset.return_value.accepted = True
    service.import_dataset("some.csv")
    import_service.import_dataset.assert_called_once_with("some.csv")

    import_service.predictive_input_frame.return_value = frame
    import_service.target_series.return_value = target
    trainer.train_model.return_value = MagicMock(model_name="random_forest", model_version="v1")
    service.train_model("random_forest")
    trainer.train_model.assert_called_once()
    kwargs = trainer.train_model.call_args.kwargs
    assert kwargs["model_name"] == "random_forest"
    assert kwargs["frame"] is frame
    assert kwargs["target"] is target

    pipeline = MagicMock()
    prediction_service.load_model.return_value = pipeline
    prediction_service.predict_and_explain.return_value = MagicMock(spec=PredictionOutcome)
    service.predict("random_forest", {"type": "L"}, version="v1", method="lime")
    prediction_service.load_model.assert_called_once_with("random_forest", version="v1")
    prediction_service.predict_and_explain.assert_called_once()

    report_service.export_json.return_value = Path(tmp_path / "report.json")
    service.export_report(metrics=None, model_name="random_forest", model_version="v1")
    report_service.export_json.assert_called_once()


def test_application_service_train_requires_active_dataset():
    """train_model without active dataset or supplied data raises MaintiQError."""
    service = ApplicationService(
        import_service=MagicMock(),
        trainer=MagicMock(),
    )
    service.import_service.predictive_input_frame.return_value = None
    service.import_service.target_series.return_value = None
    with pytest.raises(MaintiQError):
        service.train_model("logistic_regression")


def test_application_service_predict_delegates_version():
    """predict forwards the requested version to the prediction service."""
    service = ApplicationService()
    service.prediction_service = MagicMock()
    service.registry = MagicMock()
    service.registry.list_versions.return_value = ["v1", "v2"]
    service.prediction_service.load_model.return_value = MagicMock()
    service.prediction_service.predict_and_explain.return_value = MagicMock(spec=PredictionOutcome)

    service.predict("random_forest", _make_frame(1).iloc[0].to_dict())
    service.prediction_service.load_model.assert_called_once_with("random_forest", version=None)


def test_registry_delete_then_load_raises(tmp_path):
    """Deleting a model from the registry makes it unloadable."""
    frame = _make_frame()
    target = _make_target()
    train_frame, _test_frame, train_target, _test_target = split_train_test(
        frame, target, test_size=0.25, random_state=42
    )[:4]
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=FeatureEngineeringTransformer(),
    )
    pipeline.fit(train_frame, train_target)
    artifact_path = tmp_path / "model.joblib"
    pipeline.save(artifact_path)

    registry = ModelRegistry(registry_path=tmp_path / "registry.json", model_dir=tmp_path)
    version = registry.register(
        model_name="gradient_boosting",
        artifact_path=artifact_path,
        metrics=None,
        parameters=None,
        split_settings=None,
        dataset_fingerprint=None,
        feature_columns=None,
        target_column=None,
        library_versions=None,
        threshold=None,
    )

    service = PredictionService(registry=registry)
    loaded = service.load_model("gradient_boosting", version=version)
    assert loaded.is_fitted

    removed = registry.delete_model("gradient_boosting")
    assert removed == 1
    assert registry.model_exists("gradient_boosting") is False
    with pytest.raises(ModelNotFoundError):
        service.load_model("gradient_boosting", version=version)
