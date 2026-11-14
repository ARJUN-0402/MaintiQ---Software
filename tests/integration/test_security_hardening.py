"""Security hardening integration tests.

Exercises security boundaries at the integration level: path-traversal
prevention in the registry and reporting layer, import size limits, and input
validation rejection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from maintiq.config import MAX_IMPORT_BYTES
from maintiq.core.exceptions import ModelError, PredictionError, RegistryError, ReportError
from maintiq.data.loader import DatasetLoader
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.prediction import PredictionService
from maintiq.ml.preprocessing import Preprocessor
from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier
from maintiq.ml.training.pipeline import ModelPipeline
from maintiq.ml.training.registry import ModelRegistry
from maintiq.reporting.service import ReportService


def _make_pipeline(tmp_path, model_name="gradient_boosting"):
    rng = np.random.default_rng(5)
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
    pipeline = ModelPipeline(
        model_name=model_name,
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=FeatureEngineeringTransformer(),
    )
    pipeline.fit(frame, target)
    return pipeline


def test_registry_rejects_path_traversal_artifact(tmp_path):
    """Registering an artefact outside the model directory raises RegistryError."""
    registry = ModelRegistry(
        registry_path=tmp_path / "registry.json", model_dir=tmp_path / "models"
    )
    (tmp_path / "models").mkdir()
    outside = tmp_path / "outside.joblib"
    outside.write_text("not a model")
    with pytest.raises(RegistryError):
        registry.register(
            model_name="m",
            artifact_path=str(outside),
            metrics=None,
            parameters=None,
            split_settings=None,
            dataset_fingerprint=None,
            feature_columns=None,
            target_column=None,
            library_versions=None,
            threshold=None,
        )


def test_registry_hash_mismatch_on_tampered_artefact(tmp_path):
    """Tampering with the stored artefact hash triggers ModelError on load."""
    registry = ModelRegistry(
        registry_path=tmp_path / "registry.json", model_dir=tmp_path / "models"
    )
    (tmp_path / "models").mkdir()
    pipeline = _make_pipeline(tmp_path)
    artifact_path = tmp_path / "models" / "model.joblib"
    pipeline.save(artifact_path)
    version = registry.register(
        model_name="m",
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
    # Corrupt the stored SHA-256 (not the artefact file) so the hash check fails.
    registry._data["models"]["m"]["versions"][-1]["sha256"] = "0" * 64
    registry._persist()
    with pytest.raises(ModelError):
        registry.load_artifact("m", version, trusted=True)


def test_report_service_rejects_traversing_output_path(tmp_path):
    """ReportService rejects output paths that escape the reports directory."""
    service = ReportService(output_dir=tmp_path / "reports")
    with pytest.raises(ReportError):
        service.export_json(
            metrics=None,
            model_name="m",
            output_path=str(tmp_path / "reports" / ".." / "escape.json"),
        )


def test_report_service_rejects_unsafe_filename(tmp_path):
    """ReportService rejects unsafe filenames (backslashes, dot-dot)."""
    service = ReportService(output_dir=tmp_path / "reports")
    with pytest.raises(ReportError):
        service.export_json(
            metrics=None,
            output_path=str(tmp_path / "reports" / "..\\..\\evil.json"),
        )


def test_import_enforces_maximum_file_size(tmp_path):
    """DatasetLoader rejects files exceeding MAX_IMPORT_BYTES."""
    loader = DatasetLoader(max_bytes=MAX_IMPORT_BYTES)
    oversized = tmp_path / "oversized.csv"
    oversized.write_bytes(b"x" * (MAX_IMPORT_BYTES + 1))
    result = loader.load(oversized)
    assert result.frame is None
    assert any("too large" in e.lower() for e in result.errors)


def test_import_rejects_missing_and_empty_files(tmp_path):
    """DatasetLoader reports missing files and empty files as errors."""
    loader = DatasetLoader()
    missing = loader.load(tmp_path / "does_not_exist.csv")
    assert missing.frame is None
    assert any("not found" in e.lower() for e in missing.errors)

    empty = tmp_path / "empty.csv"
    empty.write_text("")
    result = loader.load(empty)
    assert result.frame is None
    assert any("empty" in e.lower() for e in result.errors)


def test_prediction_rejects_multiframe_input(tmp_path):
    """PredictionService rejects multi-row input records."""
    pipeline = _make_pipeline(tmp_path)
    service = PredictionService()
    multi = pd.DataFrame(
        {
            "type": ["L", "M"],
            "air_temperature_k": [298.0, 300.0],
            "process_temperature_k": [302.0, 305.0],
            "rotational_speed_rpm": [1400.0, 1500.0],
            "torque_nm": [40.0, 50.0],
            "    tool_wear_min": [50.0, 100.0],
        }
    )
    with pytest.raises(PredictionError):
        service.predict(pipeline, multi)
