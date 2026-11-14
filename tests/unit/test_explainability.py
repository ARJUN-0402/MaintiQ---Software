"""Tests for the SHAP/LIME explainability service.

SHAP and LIME are optional dependencies. In this environment both are
importable, so both code paths are exercised end-to-end on a small fitted
pipeline. The SHAP-unavailable behaviour is covered by monkeypatch-driven
tests in tests/unit/test_explainability_optional.py. No explanations are
fabricated.
"""

import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from maintiq.core.exceptions import ExplanationError
from maintiq.ml.explainability import (
    DependencyStatus,
    ExplanationResult,
    _background_sample,
    _build_feature_labels,
    explain_global,
    explain_local,
    explain_with_lime,
    explain_with_shap,
    explainability_status,
    lime_status,
    require_lime,
    require_shap,
    shap_status,
)
from maintiq.ml.features.transformer import REQUIRED_COLUMNS, FeatureEngineeringTransformer
from maintiq.ml.preprocessing import Preprocessor
from maintiq.ml.training.pipeline import ModelPipeline

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _make_frame() -> pd.DataFrame:
    """Small synthetic binary dataset with the required predictive columns."""
    rows = [
        {
            "type": "L",
            "air_temperature_k": 298.0,
            "process_temperature_k": 302.0,
            "rotational_speed_rpm": 1200.0,
            "torque_nm": 30.0,
            "tool_wear_min": 10.0,
        },
        {
            "type": "M",
            "air_temperature_k": 300.0,
            "process_temperature_k": 308.0,
            "rotational_speed_rpm": 1500.0,
            "torque_nm": 45.0,
            "tool_wear_min": 60.0,
        },
        {
            "type": "H",
            "air_temperature_k": 302.0,
            "process_temperature_k": 310.0,
            "rotational_speed_rpm": 1800.0,
            "torque_nm": 60.0,
            "tool_wear_min": 120.0,
        },
        {
            "type": "L",
            "air_temperature_k": 299.0,
            "process_temperature_k": 303.0,
            "rotational_speed_rpm": 1300.0,
            "torque_nm": 35.0,
            "tool_wear_min": 20.0,
        },
        {
            "type": "M",
            "air_temperature_k": 301.0,
            "process_temperature_k": 309.0,
            "rotational_speed_rpm": 1600.0,
            "torque_nm": 50.0,
            "tool_wear_min": 80.0,
        },
        {
            "type": "H",
            "air_temperature_k": 303.0,
            "process_temperature_k": 311.0,
            "rotational_speed_rpm": 1900.0,
            "torque_nm": 70.0,
            "tool_wear_min": 150.0,
        },
        {
            "type": "L",
            "air_temperature_k": 297.0,
            "process_temperature_k": 301.0,
            "rotational_speed_rpm": 1100.0,
            "torque_nm": 25.0,
            "tool_wear_min": 5.0,
        },
        {
            "type": "M",
            "air_temperature_k": 300.0,
            "process_temperature_k": 307.0,
            "rotational_speed_rpm": 1400.0,
            "torque_nm": 40.0,
            "tool_wear_min": 40.0,
        },
        {
            "type": "H",
            "air_temperature_k": 304.0,
            "process_temperature_k": 312.0,
            "rotational_speed_rpm": 2000.0,
            "torque_nm": 80.0,
            "tool_wear_min": 200.0,
        },
        {
            "type": "L",
            "air_temperature_k": 298.0,
            "process_temperature_k": 304.0,
            "rotational_speed_rpm": 1250.0,
            "torque_nm": 32.0,
            "tool_wear_min": 15.0,
        },
    ]
    frame = pd.DataFrame(rows)
    frame["Machine failure"] = [0, 0, 1, 0, 1, 1, 0, 0, 1, 0]
    return frame


def _fit_pipeline(frame: pd.DataFrame) -> ModelPipeline:
    target = frame["Machine failure"]
    inputs = frame[list(REQUIRED_COLUMNS)]
    pipeline = ModelPipeline(
        model_name="logistic_regression",
        estimator=LogisticRegression(max_iter=2000),
        preprocessor=Preprocessor(),
        feature_transformer=__import__(
            "maintiq.ml.features", fromlist=["FeatureEngineeringTransformer"]
        ).FeatureEngineeringTransformer(),
    )
    pipeline.fit(inputs, target)
    pipeline.model_version = "v1"
    return pipeline


# --------------------------------------------------------------------------- #
# Status / availability
# --------------------------------------------------------------------------- #


def test_shap_status_reports_available():
    status = shap_status()
    assert status.name == "shap"
    assert status.available is True
    assert status.version is not None


def test_lime_status_reports_available():
    status = lime_status()
    assert status.name == "lime"
    assert status.available is True


def test_explainability_status_shape():
    status = explainability_status()
    assert set(status.keys()) == {"shap", "lime"}


def test_require_shap_returns_module():
    module = require_shap()
    assert module is not None
    assert hasattr(module, "KernelExplainer")


def test_require_lime_returns_module():
    module = require_lime()
    assert module is not None


# --------------------------------------------------------------------------- #
# SHAP: unavailable in this environment
# --------------------------------------------------------------------------- #


def test_explain_with_shap_returns_result():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    background = _make_frame()[list(REQUIRED_COLUMNS)]
    result = explain_with_shap(pipeline, record, background_data=background)

    assert isinstance(result, ExplanationResult)
    assert result.available is True
    assert result.method == "shap"
    assert result.disclaimer
    assert result.model_name == "logistic_regression"
    assert result.model_version == "v1"
    assert result.threshold == 0.5
    assert result.predicted_class in (0, 1)
    assert 0.0 <= result.score <= 1.0
    assert result.input_record == record
    assert len(result.contributions) > 0
    for item in result.contributions:
        assert "feature" in item
        assert "label" in item
        assert "contribution" in item
        assert "abs_contribution" in item
    assert result.feature_labels


def test_explain_with_shap_raises_without_background():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    with pytest.raises(ExplanationError):
        explain_with_shap(pipeline, record)


# --------------------------------------------------------------------------- #
# LIME: end-to-end (available in this environment)
# --------------------------------------------------------------------------- #


def test_explain_with_lime_returns_result():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    training = _make_frame()[list(REQUIRED_COLUMNS)]
    result = explain_with_lime(pipeline, record, training_data=training)

    assert isinstance(result, ExplanationResult)
    assert result.available is True
    assert result.method == "lime"
    assert result.disclaimer
    assert result.model_name == "logistic_regression"
    assert result.model_version == "v1"
    assert result.threshold == 0.5
    assert result.predicted_class in (0, 1)
    assert 0.0 <= result.score <= 1.0
    assert result.input_record == record
    assert len(result.contributions) > 0
    for item in result.contributions:
        assert "feature" in item
        assert "label" in item
        assert "contribution" in item
        assert "abs_contribution" in item
    assert result.feature_labels


def test_explain_with_lime_maps_feature_labels():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    training = _make_frame()[list(REQUIRED_COLUMNS)]
    result = explain_with_lime(pipeline, record, training_data=training)

    labelled = {item["feature"]: item["label"] for item in result.contributions}
    assert labelled.get("num__air_temperature_k") == "Air temperature [K]"
    assert labelled.get("num__torque_nm") == "Torque [Nm]"
    assert any("Machine type:" in label for label in labelled.values())


def test_explain_with_lime_requires_training_data():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    with pytest.raises(ExplanationError):
        explain_with_lime(pipeline, record)


def test_explain_with_lime_rejects_missing_columns():
    pipeline = _fit_pipeline(_make_frame())
    bad_record = {"air_temperature_k": 300.0}  # missing type and others
    with pytest.raises(ExplanationError):
        explain_with_lime(pipeline, bad_record, training_data=_make_frame()[list(REQUIRED_COLUMNS)])


def test_explain_with_lime_rejects_unfitted_pipeline():
    pipeline = ModelPipeline(
        model_name="logistic_regression",
        estimator=LogisticRegression(),
        preprocessor=Preprocessor(),
        feature_transformer=FeatureEngineeringTransformer(),
    )
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    with pytest.raises(ExplanationError):
        explain_with_lime(pipeline, record, training_data=_make_frame()[list(REQUIRED_COLUMNS)])


# --------------------------------------------------------------------------- #
# explain_local fallback
# --------------------------------------------------------------------------- #


def test_explain_local_lime_succeeds():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    training = _make_frame()[list(REQUIRED_COLUMNS)]
    result = explain_local(pipeline, record, method="lime", training_data=training)
    assert result.available is True
    assert result.method == "lime"


def test_explain_local_prefers_shap_when_available():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    training = _make_frame()[list(REQUIRED_COLUMNS)]
    # SHAP is available in this environment, so auto prefers SHAP.
    result = explain_local(
        pipeline, record, method="auto", background_data=training, training_data=training
    )
    assert result.available is True
    assert result.method == "shap"


def test_explain_local_no_backend():
    pipeline = _fit_pipeline(_make_frame())
    record = {
        "type": "M",
        "air_temperature_k": 300.0,
        "process_temperature_k": 308.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 45.0,
        "tool_wear_min": 60.0,
    }
    with pytest.raises(ExplanationError):
        explain_local(pipeline, record, method="shap")


# --------------------------------------------------------------------------- #
# explain_global: SHAP available here
# --------------------------------------------------------------------------- #


def test_explain_global_returns_result():
    pipeline = _fit_pipeline(_make_frame())
    background = _make_frame()[list(REQUIRED_COLUMNS)]
    result = explain_global(pipeline, background_data=background)

    assert result.available is True
    assert result.method == "shap"
    assert len(result.global_importance) > 0
    for item in result.global_importance:
        assert "feature" in item
        assert "label" in item
        assert "importance" in item
    assert result.feature_labels


# --------------------------------------------------------------------------- #
# Helper unit tests
# --------------------------------------------------------------------------- #


def test_build_feature_labels_known_and_unknown():
    names = ["num__air_temperature_k", "cat__type__M", "num__unknown_feature"]
    labels = _build_feature_labels(names)
    assert labels["num__air_temperature_k"] == "Air temperature [K]"
    assert labels["cat__type__M"] == "Machine type: M"
    assert labels["num__unknown_feature"] == "num__unknown_feature"
    custom = _build_feature_labels(names, feature_labels={"num__unknown_feature": "Custom label"})
    assert custom["num__unknown_feature"] == "Custom label"


def test_background_sample_bounded_and_deterministic():
    frame = _make_frame()[list(REQUIRED_COLUMNS)]
    small = _background_sample(frame, max_size=5)
    assert len(small) == 5
    # deterministic: same seed -> same rows
    again = _background_sample(frame, max_size=5)
    pd.testing.assert_frame_equal(small, again)
    # larger than data returns all
    full = _background_sample(frame, max_size=1000)
    assert len(full) == len(frame)
    # empty raises
    with pytest.raises(ExplanationError):
        _background_sample(frame.iloc[0:0], max_size=10)


def test_dependency_status_to_dict():
    status = DependencyStatus(name="shap", available=False, reason="boom")
    d = status.to_dict()
    assert d == {"name": "shap", "available": False, "version": None, "reason": "boom"}
