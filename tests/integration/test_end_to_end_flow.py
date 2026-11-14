"""End-to-end integration tests for the full MaintiQ flow.

Covers: import dataset → train model → model registry → predict → explain →
export report. These tests exercise the real components end to end using a
synthetic AI4I-style dataset (no real AI4I CSV is required).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import MaintiQError, ModelNotFoundError
from maintiq.ml.prediction import PredictionService
from maintiq.ml.training.registry import ModelRegistry
from maintiq.services.application_service import ApplicationService


def _make_ai4i_csv(tmp_path, n: int = 140) -> str:
    """Write a synthetic AI4I-style CSV using source column names."""
    rng = np.random.default_rng(11)
    frame = pd.DataFrame(
        {
            "Type": rng.choice(list("LMH"), size=n),
            "Air temperature [K]": rng.uniform(290, 310, size=n),
            "Process temperature [K]": rng.uniform(295, 315, size=n),
            "Rotational speed [rpm]": rng.uniform(1200, 1600, size=n),
            "Torque [Nm]": rng.uniform(30, 60, size=n),
            "Tool wear [min]": rng.uniform(0, 200, size=n),
            "Machine failure": (rng.random(n) < 0.3).astype(int),
            "UDI": range(1, n + 1),
            "Product ID": [f"P{i:04d}" for i in range(1, n + 1)],
            "TWF": np.zeros(n, dtype=int),
            "HDF": np.zeros(n, dtype=int),
            "PWF": np.zeros(n, dtype=int),
            "OSF": np.zeros(n, dtype=int),
            "RNF": np.zeros(n, dtype=int),
        }
    )
    csv_path = tmp_path / "ai4i_sample.csv"
    frame.to_csv(csv_path, index=False)
    return str(csv_path)


def _record() -> dict:
    return {
        "type": "L",
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }


def test_import_train_registry_predict_explain_report_flow(tmp_path):
    """Full end-to-end flow: import → train → registry → predict → explain → report."""
    csv_path = _make_ai4i_csv(tmp_path)
    service = ApplicationService()
    # Clean slate: remove any previously persisted model so versioning is
    # deterministic (the real user-data registry persists across test runs).
    if service.model_exists("logistic_regression"):
        service.registry.delete_model("logistic_regression")

    # 1. Import dataset (source columns renamed to canonical internally).
    outcome = service.import_dataset(csv_path)
    assert outcome.accepted is True
    assert service.has_active_dataset is True
    assert service.active_frame is not None
    assert "machine_failure" in service.active_frame.columns

    # 2. Train a model on the active dataset.
    result = service.train_model("logistic_regression")
    assert result.model_name == "logistic_regression"
    assert result.model_version is not None
    assert result.metrics is not None

    # 3. Model registry contains the trained model.
    assert service.model_exists("logistic_regression") is True
    versions = service.list_versions("logistic_regression")
    assert "v1" in versions
    latest = service.registry.get_latest("logistic_regression")
    assert latest["model_name"] == "logistic_regression"
    assert latest["version"] == "v1"

    # 4. Load model and predict + explain (LIME available in this env).
    train_frame = service.import_service.predictive_input_frame()
    outcome = service.predict(
        "logistic_regression",
        _record(),
        background_data=train_frame,
        method="lime",
    )
    assert outcome.prediction.predicted_class in (0, 1)
    assert 0.0 <= outcome.prediction.score <= 1.0
    assert outcome.prediction.input_validated is True
    assert outcome.explanation is not None
    assert outcome.explanation.available is True
    assert outcome.explanation.method == "lime"
    assert outcome.explanation_error is None

    # 5. Export an evaluation report.
    report_path = service.export_report(
        metrics=None,
        model_name="logistic_regression",
        model_version="v1",
    )
    assert report_path.exists()
    assert report_path.suffix == ".json"


def test_gradient_boosting_fallback_end_to_end(tmp_path):
    """End-to-end flow using the pure-NumPy Gradient Boosting fallback."""
    csv_path = _make_ai4i_csv(tmp_path, n=100)
    service = ApplicationService()
    if service.model_exists("gradient_boosting"):
        service.registry.delete_model("gradient_boosting")
    assert service.import_dataset(csv_path).accepted is True

    result = service.train_model("gradient_boosting")
    assert result.model_name == "gradient_boosting"
    assert result.model_version is not None

    assert service.model_exists("gradient_boosting") is True
    train_frame = service.import_service.predictive_input_frame()
    outcome = service.predict(
        "gradient_boosting",
        _record(),
        background_data=train_frame,
        method="lime",
    )
    assert outcome.prediction.predicted_class in (0, 1)
    assert outcome.explanation is not None
    assert outcome.explanation.available is True


def test_load_missing_model_raises(tmp_path):
    """Loading an unregistered model raises a clear error (isolated registry)."""
    registry = ModelRegistry(registry_path=tmp_path / "registry.json", model_dir=tmp_path)
    service = PredictionService(registry=registry)
    with pytest.raises(ModelNotFoundError):
        service.load_model("logistic_regression")


def test_predict_without_active_dataset_raises(tmp_path):
    """Training without an active dataset raises a clear error."""
    service = ApplicationService()
    with pytest.raises(MaintiQError):
        service.train_model("logistic_regression")
