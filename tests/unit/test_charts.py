"""Tests for evaluation charts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from maintiq.ml.evaluation import (
    ComparisonResult,
    EvaluationService,
    ModelComparisonResult,
    ThresholdAnalysisService,
    plot_confusion_matrix,
    plot_fp_fn_tradeoff,
    plot_model_comparison,
    plot_precision_recall_curve,
    plot_roc_curve,
    plot_threshold_vs_metric,
)


def _make_metrics():
    service = EvaluationService()
    y_true = pd.Series([0, 0, 1, 1, 0, 1], name="machine_failure")
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    return service.evaluate(Pipeline(), None, y_true, threshold=0.5)


def test_plot_confusion_matrix(tmp_path):
    metrics = _make_metrics()
    output = tmp_path / "cm.png"
    plot_confusion_matrix(metrics, output_path=str(output))
    assert output.exists()


def test_plot_roc_curve(tmp_path):
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    output = tmp_path / "roc.png"
    plot_roc_curve(y_true, scores, output_path=str(output))
    assert output.exists()


def test_plot_roc_curve_one_class_raises(tmp_path):
    y_true = np.ones(10, dtype=int)
    scores = np.random.default_rng(1).random(10)
    output = tmp_path / "roc_one_class.png"
    with pytest.raises(ValueError):
        plot_roc_curve(y_true, scores, output_path=str(output))


def test_plot_precision_recall_curve(tmp_path):
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    output = tmp_path / "pr.png"
    plot_precision_recall_curve(y_true, scores, output_path=str(output))
    assert output.exists()


def test_plot_precision_recall_curve_one_class_raises(tmp_path):
    y_true = np.ones(10, dtype=int)
    scores = np.random.default_rng(1).random(10)
    output = tmp_path / "pr_one_class.png"
    with pytest.raises(ValueError):
        plot_precision_recall_curve(y_true, scores, output_path=str(output))


def test_plot_threshold_vs_metric(tmp_path):
    service = ThresholdAnalysisService()
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    result = service.analyze(y_true, scores)
    output = tmp_path / "threshold.png"
    plot_threshold_vs_metric(result, output_path=str(output))
    assert output.exists()


def test_plot_fp_fn_tradeoff(tmp_path):
    service = ThresholdAnalysisService()
    y_true = np.array([0, 0, 1, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7], dtype=float)
    result = service.analyze(y_true, scores)
    output = tmp_path / "fp_fn.png"
    plot_fp_fn_tradeoff(result, output_path=str(output))
    assert output.exists()


def test_plot_model_comparison(tmp_path):
    metrics = _make_metrics()
    result_model = ModelComparisonResult(
        model_name="random_forest",
        display_name="Random Forest",
        status="success",
        metrics=metrics,
    )
    comparison = ComparisonResult(
        results=[result_model],
        selected_metric="f1",
        best_model="random_forest",
    )
    output = tmp_path / "comparison.png"
    plot_model_comparison(comparison, output_path=str(output))
    assert output.exists()
