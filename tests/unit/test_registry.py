"""Tests for the local JSON-based ModelRegistry."""

from __future__ import annotations

import json
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import (
    ModelHashMismatchError,
    RegistryError,
)
from maintiq.ml.training import ModelRegistry, ModelTrainer
from maintiq.ml.training.registry import SCHEMA_VERSION


def _write_joblib(path, payload=None):
    if payload is None:
        payload = {"dummy": "artefact"}
    joblib.dump(payload, str(path))
    return path


def _make_registry(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path = model_dir / "registry.json"
    return ModelRegistry(registry_path=registry_path, model_dir=model_dir), model_dir


def _make_artifact(model_dir, name="model.joblib"):
    path = model_dir / name
    _write_joblib(path)
    return path


# --------------------------------------------------------------------------- empty state


def test_missing_registry_file_creates_empty_state(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    assert not registry.registry_path.exists()
    assert registry.list_models() == []
    assert registry.count_models() == 0
    assert registry.count_records() == 0


# --------------------------------------------------------------------------- registration / versioning


def test_registration_and_version_increment(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    v1 = registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert v1 == "v1"

    v2 = registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert v2 == "v2"

    assert registry.list_versions("logistic_regression") == ["v1", "v2"]
    assert registry.count_records() == 2


def test_version_increment_across_different_models(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    art_a = _make_artifact(model_dir, "a.joblib")
    art_b = _make_artifact(model_dir, "b.joblib")

    registry.register(model_name="a", artifact_path=art_a, metrics={}, parameters={})
    registry.register(model_name="b", artifact_path=art_b, metrics={}, parameters={})
    registry.register(model_name="a", artifact_path=art_a, metrics={}, parameters={})

    assert registry.list_versions("a") == ["v1", "v2"]
    assert registry.list_versions("b") == ["v1"]


# --------------------------------------------------------------------------- persistence / reload


def test_persistence_across_reload(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = _make_artifact(model_dir)

    registry = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    registry.register(
        model_name="random_forest",
        artifact_path=artifact,
        metrics={"accuracy": 0.85},
        parameters={"n_estimators": 100},
        random_seed=42,
    )

    reloaded = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    assert reloaded.list_models() == ["random_forest"]
    assert reloaded.list_versions("random_forest") == ["v1"]
    latest = reloaded.get_latest("random_forest")
    assert latest["version"] == "v1"
    assert latest["metrics"]["accuracy"] == 0.85


def test_reload_replaces_in_memory_state(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="xgboost",
        artifact_path=artifact,
        metrics={"accuracy": 0.8},
        parameters={"n_estimators": 100},
        random_seed=42,
    )
    registry.register(
        model_name="xgboost",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"n_estimators": 200},
        random_seed=42,
    )
    assert registry.count_records() == 2

    registry.reload()
    assert registry.count_records() == 2
    assert registry.list_versions("xgboost") == ["v1", "v2"]


# --------------------------------------------------------------------------- list / get / latest / exists / count


def test_list_get_latest_exists_count(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    assert registry.model_exists("logistic_regression") is False
    assert registry.version_exists("logistic_regression", "v1") is False

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    assert registry.model_exists("logistic_regression") is True
    assert registry.version_exists("logistic_regression", "v1") is True
    assert registry.version_exists("logistic_regression", "v9") is False
    assert registry.count_models() == 1
    assert registry.count_records() == 1

    record = registry.get_version("logistic_regression", "v1")
    assert record["version"] == "v1"
    assert record["model_name"] == "logistic_regression"
    assert record["record_id"] == "logistic_regression-v1"

    latest = registry.get_latest("logistic_regression")
    assert latest["version"] == "v1"

    with pytest.raises(RegistryError):
        registry.get_version("logistic_regression", "v9")

    with pytest.raises(RegistryError):
        registry.get_latest("nonexistent")


def test_get_version_returns_defensive_copy(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    record = registry.get_version("logistic_regression", "v1")
    record["metrics"]["accuracy"] = 999.0  # mutate the copy

    original = registry.get_version("logistic_regression", "v1")
    assert original["metrics"]["accuracy"] == 0.9


# --------------------------------------------------------------------------- malformed JSON / schema / records


def test_malformed_json_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_unsupported_schema_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"schema_version": "9.9", "models": {}}), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_missing_schema_version_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"models": {}}), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_invalid_record_shape_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "models": {
            "logistic_regression": {
                "display_name": "Logistic Regression",
                "versions": [{"version": "v1"}],  # missing required fields
            }
        },
    }
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


# --------------------------------------------------------------------------- missing artifact


def test_register_missing_artifact_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    missing = model_dir / "does_not_exist.joblib"

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=missing,
            metrics={},
            parameters={},
        )


# --------------------------------------------------------------------------- path safety


def test_path_traversal_rejected(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    # A relative path containing ".." escapes the model directory.
    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path="../escape.joblib",
            metrics={},
            parameters={},
        )


def test_outside_directory_absolute_path_rejected(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    outside = tmp_path / "outside" / "escape.joblib"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(outside)

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=outside,
            metrics={},
            parameters={},
        )


# --------------------------------------------------------------------------- hash verification


def test_artifact_hash_verification_on_load(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir, "hashed.joblib")

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    loaded = registry.load_artifact("logistic_regression", "v1", trusted=True)
    assert loaded == {"dummy": "artefact"}


def test_hash_mismatch_after_artifact_modification(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir, "mutable.joblib")

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    # Modify the artefact after registration so the stored hash no longer matches.
    artifact.write_text("tampered", encoding="utf-8")

    with pytest.raises(ModelHashMismatchError):
        registry.load_artifact("logistic_regression", "v1", trusted=True)


# --------------------------------------------------------------------------- JSON-safe serialization


def test_json_safe_metric_serialization(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    metrics = {
        "accuracy": np.float64(0.9),
        "precision": np.float64(0.85),
        "count": np.int64(5),
        "flag": np.bool_(True),
        "nested": {"inner": np.float64(0.5)},
    }

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics=metrics,
        parameters={"random_state": np.int32(42)},
        random_seed=42,
    )

    record = registry.get_version("logistic_regression", "v1")
    assert record["metrics"]["accuracy"] == 0.9
    assert record["metrics"]["precision"] == 0.85
    assert record["metrics"]["count"] == 5
    assert record["metrics"]["flag"] is True
    assert record["metrics"]["nested"]["inner"] == 0.5
    assert isinstance(record["metrics"]["accuracy"], float)
    assert isinstance(record["metrics"]["count"], int)
    assert isinstance(record["parameters"]["random_state"], int)


def test_unsupported_json_value_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=artifact,
            metrics={"accuracy": 0.9},
            parameters={"callable_obj": len},  # arbitrary object, not JSON-safe
            random_seed=42,
        )


# --------------------------------------------------------------------------- atomic write safety


def test_atomic_write_failure_does_not_corrupt_previous_registry(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = _make_artifact(model_dir)

    registry = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert registry.count_records() == 1

    # Force the atomic write to fail on the next registration.
    with patch.object(registry, "_persist", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            registry.register(
                model_name="random_forest",
                artifact_path=artifact,
                metrics={"accuracy": 0.8},
                parameters={"n_estimators": 100},
                random_seed=42,
            )

    # Previous state must be intact on disk.
    recovered = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    assert recovered.count_records() == 1
    assert recovered.list_models() == ["logistic_regression"]


# --------------------------------------------------------------------------- trainer integration


def test_trainer_registers_model(tmp_path):
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=60),
            "air_temperature_k": rng.uniform(290, 310, size=60),
            "process_temperature_k": rng.uniform(295, 315, size=60),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=60),
            "torque_nm": rng.uniform(30, 60, size=60),
            "tool_wear_min": rng.uniform(0, 200, size=60),
        }
    )
    target = pd.Series((rng.random(60) < 0.3).astype(int), name="machine_failure")

    registry, model_dir = _make_registry(tmp_path)

    trainer = ModelTrainer(registry=registry, random_seed=42, test_size=0.25)
    trainer.model_dir = model_dir
    result = trainer.train_model(
        model_name="random_forest",
        frame=frame,
        target=target,
    )

    assert result.cancelled is False
    assert result.model_version == "v1"
    assert result.artifact_path is not None
    assert registry.model_exists("random_forest")
    assert registry.version_exists("random_forest", "v1")

    latest = registry.get_latest("random_forest")
    assert latest["metrics"]["accuracy"] == result.metrics.accuracy
    assert latest["feature_columns"] is not None
    assert latest["library_versions"] is not None
    assert latest["dataset_fingerprint"] is not None


def test_trainer_registry_failure_reported(tmp_path):
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=60),
            "air_temperature_k": rng.uniform(290, 310, size=60),
            "process_temperature_k": rng.uniform(295, 315, size=60),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=60),
            "torque_nm": rng.uniform(30, 60, size=60),
            "tool_wear_min": rng.uniform(0, 200, size=60),
        }
    )
    target = pd.Series((rng.random(60) < 0.3).astype(int), name="machine_failure")

    registry, model_dir = _make_registry(tmp_path)

    trainer = ModelTrainer(registry=registry, random_seed=42, test_size=0.25)
    trainer.model_dir = model_dir

    # Make registry.register raise so integration failure is surfaced.
    with patch.object(registry, "register", side_effect=RegistryError("write failed")):
        with pytest.raises(RegistryError):
            trainer.train_model(
                model_name="random_forest",
                frame=frame,
                target=target,
            )


# --------------------------------------------------------------------------- deletion


def test_delete_version_removes_single_record(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        random_seed=42,
    )
    assert registry.list_versions("logistic_regression") == ["v1", "v2"]

    registry.delete_version("logistic_regression", "v1")
    assert registry.list_versions("logistic_regression") == ["v2"]
    assert registry.count_records() == 1
    assert registry.model_exists("logistic_regression")


def test_delete_version_last_record_removes_model(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    assert registry.list_versions("logistic_regression") == ["v1"]

    registry.delete_version("logistic_regression", "v1")
    assert registry.list_versions("logistic_regression") == []
    assert not registry.model_exists("logistic_regression")
    assert registry.count_models() == 0


def test_delete_version_missing_raises(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    with pytest.raises(RegistryError):
        registry.delete_version("logistic_regression", "v1")


def test_delete_version_unknown_model_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    with pytest.raises(RegistryError):
        registry.delete_version("random_forest", "v1")


def test_delete_model_removes_all_versions(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        random_seed=42,
    )
    registry.register(
        model_name="random_forest",
        artifact_path=artifact,
        metrics={"accuracy": 0.88},
        random_seed=42,
    )
    assert registry.count_models() == 2
    assert registry.count_records() == 3

    removed = registry.delete_model("logistic_regression")
    assert removed == 2
    assert registry.list_models() == ["random_forest"]
    assert registry.count_models() == 1
    assert registry.count_records() == 1


def test_delete_model_missing_raises(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    with pytest.raises(RegistryError):
        registry.delete_model("absent")
