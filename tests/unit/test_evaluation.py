"""Tests for the evaluation service metrics."""

import numpy as np
import pandas as pd

from maintiq.ml.evaluation import ClassificationMetrics, EvaluationService


def test_perfect_predictions():
    service = EvaluationService()
    y_true = pd.Series([0, 0, 1, 1], name="machine_failure")
    scores = np.array([0.1, 0.2, 0.8, 0.9])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    metrics = service.evaluate(Pipeline(), None, y_true, threshold=0.5)
    assert metrics.accuracy == 1.0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.roc_auc == 1.0
    assert metrics.true_positives == 2
    assert metrics.true_negatives == 2


def test_all_wrong_predictions():
    service = EvaluationService()
    y_true = pd.Series([0, 0, 1, 1], name="machine_failure")
    scores = np.array([0.9, 0.8, 0.2, 0.1])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    metrics = service.evaluate(Pipeline(), None, y_true, threshold=0.5)
    assert metrics.accuracy == 0.0
    assert metrics.true_positives == 0
    assert metrics.true_negatives == 0
    assert metrics.false_positives == 2
    assert metrics.false_negatives == 2


def test_single_class_roc_auc_none():
    service = EvaluationService()
    y_true = pd.Series([1, 1, 1, 1], name="machine_failure")
    scores = np.array([0.9, 0.8, 0.7, 0.6])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    metrics = service.evaluate(Pipeline(), None, y_true, threshold=0.5)
    assert metrics.roc_auc is None
    assert metrics.recall == 1.0


def test_threshold_shifts_predictions():
    service = EvaluationService()
    y_true = pd.Series([0, 1, 1, 0], name="machine_failure")
    scores = np.array([0.4, 0.6, 0.55, 0.45])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    loose = service.evaluate(Pipeline(), None, y_true, threshold=0.4)
    strict = service.evaluate(Pipeline(), None, y_true, threshold=0.7)
    # At threshold 0.4 all four predicted positive; at 0.7 none.
    assert loose.true_positives == 2
    assert strict.true_positives == 0


def test_to_dict_contains_keys():
    service = EvaluationService()
    y_true = pd.Series([0, 1], name="machine_failure")
    scores = np.array([0.2, 0.8])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    metrics = service.evaluate(Pipeline(), None, y_true, threshold=0.5)
    d = metrics.to_dict()
    for key in (
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "true_negatives",
        "false_positives",
        "false_negatives",
        "true_positives",
        "threshold",
        "n_samples",
        "n_positive",
    ):
        assert key in d


def test_returns_classification_metrics_instance():
    service = EvaluationService()
    y_true = pd.Series([0, 1], name="machine_failure")
    scores = np.array([0.2, 0.8])

    class Pipeline:
        estimator = type("E", (), {"classes_": np.array([0, 1])})()

        def predict_proba(self, frame):
            return np.column_stack([1.0 - scores, scores])

    result = service.evaluate(Pipeline(), None, y_true, threshold=0.5)
    assert isinstance(result, ClassificationMetrics)
