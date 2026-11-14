"""Tests for the reporting service."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import ReportError
from maintiq.ml.evaluation import (
    EvaluationService,
    ThresholdAnalysisService,
)
from maintiq.reporting import ReportService


def _make_metrics():
    service = EvaluationService()
    y_true = pd.Series([0, 0, 1, 1, 0, 1], name="machine_failure")
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    return service.evaluate(Pipeline(), None, y_true, threshold=0.5)


def _make_threshold_result():
    service = ThresholdAnalysisService()
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    return service.analyze(y_true, scores)


def test_export_json(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    metrics = _make_metrics()
    path = reporter.export_json(
        metrics=metrics,
        model_name="random_forest",
        model_version="v1",
        dataset_fingerprint="abc123",
        target_column="machine_failure",
        feature_columns=["type", "air_temperature_k"],
    )
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["maintiq_version"] == "0.2.0"
    assert data["model"]["name"] == "random_forest"
    assert data["model"]["version"] == "v1"
    assert data["dataset"]["fingerprint"] == "abc123"
    assert data["metrics"]["accuracy"] == metrics.accuracy
    assert "warnings" in data


def test_export_json_atomic(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    metrics = _make_metrics()
    path = tmp_path / "report.json"
    reporter.export_json(metrics=metrics, output_path=path)
    assert path.exists()
    # No leftover temp files.
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_export_json_unsafe_filename_rejected(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    metrics = _make_metrics()
    with pytest.raises(ReportError):
        reporter.export_json(metrics=metrics, output_path="../outside.json")


def test_export_csv(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    threshold_result = _make_threshold_result()
    path = reporter.export_csv(threshold_result)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "threshold" in content
    assert "precision" in content
    assert "f1" in content


def test_export_csv_atomic(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    threshold_result = _make_threshold_result()
    path = tmp_path / "threshold.csv"
    reporter.export_csv(threshold_result, output_path=path)
    assert path.exists()
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_export_png(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    metrics = _make_metrics()
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    written = reporter.export_png(y_true, scores, metrics)
    assert len(written) >= 1
    for p in written:
        assert p.exists()
        assert p.suffix == ".png"


def test_export_png_one_class_skips_roc_pr(tmp_path):
    reporter = ReportService(output_dir=tmp_path)
    metrics = _make_metrics()
    y_true = np.ones(10, dtype=int)
    scores = np.random.default_rng(1).random(10)
    written = reporter.export_png(y_true, scores, metrics)
    names = [p.name for p in written]
    assert "roc_curve.png" not in names
    assert "precision_recall_curve.png" not in names
    assert "confusion_matrix.png" in names
