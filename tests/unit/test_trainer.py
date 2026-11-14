"""Tests for the ModelTrainer orchestration."""

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import ModelError
from maintiq.ml.training import ModelTrainer


def _make_frame(n=60):
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


def _make_target(n=60, pos_frac=0.3):
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < pos_frac).astype(int), name="machine_failure")


class _FakeRegistry:
    def __init__(self):
        self.registered = []

    def register(self, **kwargs):
        self.registered.append(kwargs)
        return "v1"


def _trainer_with_tmp_dir(tmp_path):
    trainer = ModelTrainer(random_seed=42, test_size=0.25)
    trainer.model_dir = tmp_path
    return trainer


def test_train_model_returns_result(tmp_path):
    trainer = _trainer_with_tmp_dir(tmp_path)
    result = trainer.train_model(
        model_name="gradient_boosting",
        frame=_make_frame(60),
        target=_make_target(60),
    )
    assert result.model_name == "gradient_boosting"
    assert result.cancelled is False
    assert result.metrics is not None
    assert "accuracy" in result.metrics.to_dict()
    assert result.training_duration_seconds is not None
    assert result.artifact_path is not None


def test_train_model_writes_artifact(tmp_path):
    trainer = _trainer_with_tmp_dir(tmp_path)
    result = trainer.train_model(
        model_name="gradient_boosting",
        frame=_make_frame(60),
        target=_make_target(60),
    )
    assert result.artifact_path.exists()


def test_train_model_with_registry(tmp_path):
    registry = _FakeRegistry()
    trainer = ModelTrainer(registry=registry, random_seed=42, test_size=0.25)
    trainer.model_dir = tmp_path
    result = trainer.train_model(
        model_name="random_forest",
        frame=_make_frame(60),
        target=_make_target(60),
    )
    assert result.model_version == "v1"
    assert len(registry.registered) == 1
    assert registry.registered[0]["model_name"] == "random_forest"


def test_train_model_unsupported_raises(tmp_path):
    trainer = _trainer_with_tmp_dir(tmp_path)
    with pytest.raises(ModelError):
        trainer.train_model(
            model_name="not_a_model",
            frame=_make_frame(20),
            target=_make_target(20),
        )


def test_train_model_cancelled(tmp_path):
    trainer = _trainer_with_tmp_dir(tmp_path)
    result = trainer.train_model(
        model_name="gradient_boosting",
        frame=_make_frame(60),
        target=_make_target(60),
        cancelled_check=lambda: True,
    )
    assert result.cancelled is True
    assert result.metrics is None


def test_all_supported_models_train(tmp_path):
    trainer = _trainer_with_tmp_dir(tmp_path)
    for model_name in (
        "logistic_regression",
        "random_forest",
        "gradient_boosting",
        "xgboost",
    ):
        result = trainer.train_model(
            model_name=model_name,
            frame=_make_frame(60),
            target=_make_target(60),
        )
        assert result.cancelled is False
        assert result.metrics is not None
        assert result.artifact_path.exists()
