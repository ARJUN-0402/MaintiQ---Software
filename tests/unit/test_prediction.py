"""Tests for the PredictionService (single-record inference + explanation)."""

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import ModelError, PredictionError
from maintiq.ml.explainability import ExplanationResult
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.prediction import PredictionOutcome, PredictionService
from maintiq.ml.preprocessing import Preprocessor, split_train_test
from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier
from maintiq.ml.training.pipeline import ModelPipeline
from maintiq.ml.training.registry import ModelRegistry


def _make_frame(n=80):
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


def _make_target(n=80, pos_frac=0.3):
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < pos_frac).astype(int), name="machine_failure")


def _fit_pipeline(frame=None, target=None, model_name="gradient_boosting"):
    frame = _make_frame() if frame is None else frame
    target = _make_target() if target is None else target
    train_frame, _test_frame, train_target, _test_target = split_train_test(
        frame, target, test_size=0.25, random_state=42
    )[:4]
    pipeline = ModelPipeline(
        model_name=model_name,
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=FeatureEngineeringTransformer(),
    )
    pipeline.fit(train_frame, train_target)
    return pipeline, train_frame


def test_predict_returns_structured_result():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "L",
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    result = service.predict(pipeline, record)

    assert isinstance(
        result,
        __import__("maintiq.ml.training.pipeline", fromlist=["PredictionResult"]).PredictionResult,
    )
    assert result.predicted_class in (0, 1)
    assert 0.0 <= result.score <= 1.0
    assert result.threshold == 0.5
    assert result.model_name == "gradient_boosting"
    assert result.input_validated is True
    assert result.explanation_available is False
    assert result.out_of_distribution_warnings == []


def test_predict_before_fit_raises():
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=FeatureEngineeringTransformer(),
    )
    service = PredictionService()
    with pytest.raises(ModelError):
        service.predict(pipeline, _make_frame(1).iloc[0].to_dict())


def test_predict_invalid_input_raises():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    with pytest.raises(PredictionError):
        service.predict(pipeline, {"type": "L"})  # missing numeric columns


def test_predict_multi_row_raises():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    with pytest.raises(PredictionError):
        service.predict(pipeline, _make_frame(5))


def test_predict_series_input():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    record = _make_frame(1).iloc[0]
    result = service.predict(pipeline, record)
    assert result.predicted_class in (0, 1)


def test_predict_out_of_distribution_warning():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "X",  # unseen category
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    result = service.predict(pipeline, record)
    assert any("Unseen type" in w for w in result.out_of_distribution_warnings)
    assert result.predicted_class in (0, 1)


def test_predict_domain_warning():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "L",
        "air_temperature_k": -5.0,  # below domain minimum 0
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    result = service.predict(pipeline, record)
    assert any("air_temperature_k" in w for w in result.out_of_distribution_warnings)


def test_predict_and_explain_without_background_is_outcome():
    pipeline, _ = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "L",
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    outcome = service.predict_and_explain(pipeline, record)

    assert isinstance(outcome, PredictionOutcome)
    assert isinstance(
        outcome.prediction,
        __import__("maintiq.ml.training.pipeline", fromlist=["PredictionResult"]).PredictionResult,
    )
    # No background data available and SHAP is unavailable in this env, so
    # explanation should be absent with a clear error rather than crashing.
    assert outcome.explanation is None
    assert outcome.explanation_error is not None
    assert outcome.prediction.predicted_class in (0, 1)


def test_predict_and_explain_with_lime_background():
    pipeline, train_frame = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "L",
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    outcome = service.predict_and_explain(
        pipeline, record, background_data=train_frame, method="lime"
    )

    assert isinstance(outcome.explanation, ExplanationResult)
    assert outcome.explanation.available is True
    assert outcome.explanation.method == "lime"
    assert outcome.explanation.predicted_class == outcome.prediction.predicted_class
    assert outcome.explanation.score == outcome.prediction.score
    assert outcome.explanation_error is None
    assert len(outcome.explanation.contributions) > 0


def test_predict_and_explain_prefers_shap_when_available():
    pipeline, train_frame = _fit_pipeline()
    service = PredictionService()
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 305.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 50.0,
        "tool_wear_min": 100.0,
    }
    # method="auto": SHAP available in this environment, so SHAP is used.
    outcome = service.predict_and_explain(
        pipeline, record, background_data=train_frame, method="auto"
    )
    assert outcome.explanation is not None
    assert outcome.explanation.available is True
    assert outcome.explanation.method == "shap"
    assert outcome.explanation_error is None


def test_load_model_with_real_registry(tmp_path):
    pipeline, _ = _fit_pipeline()
    artifact_path = tmp_path / "model.joblib"
    pipeline.save(artifact_path)

    registry = ModelRegistry(registry_path=tmp_path / "registry.json", model_dir=tmp_path)
    version = registry.register(
        model_name="gradient_boosting",
        artifact_path=artifact_path,
        metrics={"accuracy": 0.8},
        parameters={},
        split_settings={},
        dataset_fingerprint="fp",
        feature_columns=["type"],
        target_column="machine_failure",
        library_versions={},
        threshold=0.5,
    )

    service = PredictionService(registry=registry)
    loaded = service.load_model("gradient_boosting", version=version)
    assert loaded.is_fitted
    assert loaded.model_name == "gradient_boosting"
    assert loaded.model_version == version
    assert loaded.predict(_make_frame(5)).shape == (5,)


def test_load_model_latest_version(tmp_path):
    pipeline, _ = _fit_pipeline()
    artifact_path = tmp_path / "model.joblib"
    pipeline.save(artifact_path)

    registry = ModelRegistry(registry_path=tmp_path / "registry.json", model_dir=tmp_path)
    registry.register(
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
    loaded = service.load_model("gradient_boosting")  # version defaults to latest
    assert loaded.model_version == "v1"


def test_load_model_missing_raises(tmp_path):
    registry = ModelRegistry(registry_path=tmp_path / "registry.json", model_dir=tmp_path)
    service = PredictionService(registry=registry)
    with pytest.raises(ModelError):
        service.load_model("gradient_boosting")


def test_load_model_no_registry_raises():
    service = PredictionService(registry=None)
    with pytest.raises(PredictionError):
        service.load_model("gradient_boosting")
