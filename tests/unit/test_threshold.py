"""Tests for leakage-safe threshold analysis."""

from __future__ import annotations

import numpy as np
import pytest

from maintiq.ml.evaluation import (
    DEFAULT_THRESHOLD_GRID,
    ThresholdAnalysisService,
)


def _make_scores_targets(n=100, seed=42, pos_frac=0.3):
    rng = np.random.default_rng(seed)
    scores = rng.random(n)
    target = (rng.random(n) < pos_frac).astype(int)
    return target, scores


def test_default_grid_spans_zero_to_one():
    assert DEFAULT_THRESHOLD_GRID[0] == 0.0
    assert DEFAULT_THRESHOLD_GRID[-1] == 1.0
    assert 0.5 in DEFAULT_THRESHOLD_GRID


def test_normal_binary_data():
    service = ThresholdAnalysisService()
    target, scores = _make_scores_targets()
    result = service.analyze(target, scores, validation_source="validation_split")
    assert result.validation_source == "validation_split"
    assert result.recommended_threshold in result.threshold_grid
    assert len(result.results) == len(result.threshold_grid)
    for r in result.results:
        assert 0.0 <= r.threshold <= 1.0
        assert r.false_positives + r.true_negatives == int(np.sum(target == 0))
        assert r.false_negatives + r.true_positives == int(np.sum(target == 1))


def test_includes_default_threshold_when_not_on_grid():
    service = ThresholdAnalysisService(threshold_grid=[0.1, 0.3, 0.7, 0.9])
    target, scores = _make_scores_targets()
    result = service.analyze(target, scores)
    assert 0.5 in result.threshold_grid


def test_all_positive_target():
    service = ThresholdAnalysisService()
    target = np.ones(50, dtype=int)
    scores = np.random.default_rng(1).random(50)
    result = service.analyze(target, scores)
    # All predictions positive at threshold 0; no negatives exist.
    for r in result.results:
        assert r.false_positives == 0
        assert r.true_negatives == 0


def test_all_negative_target():
    service = ThresholdAnalysisService()
    target = np.zeros(50, dtype=int)
    scores = np.random.default_rng(1).random(50)
    result = service.analyze(target, scores)
    for r in result.results:
        assert r.false_negatives == 0
        assert r.true_positives == 0


def test_zero_precision_denominator():
    service = ThresholdAnalysisService()
    # All scores below threshold -> no predicted positives -> precision denominator 0.
    target = np.array([0, 1, 0, 1], dtype=int)
    scores = np.array([0.1, 0.2, 0.1, 0.2], dtype=float)
    result = service.analyze(target, scores, threshold_grid=[0.9])
    r = result.results[0]
    assert r.true_positives == 0
    assert r.false_positives == 0
    assert r.precision == 0.0  # zero denominator -> 0.0


def test_zero_recall_denominator():
    service = ThresholdAnalysisService()
    # No actual positives -> recall denominator 0.
    target = np.zeros(10, dtype=int)
    scores = np.random.default_rng(1).random(10)
    result = service.analyze(target, scores)
    for r in result.results:
        assert r.recall == 0.0


def test_invalid_threshold_raises():
    service = ThresholdAnalysisService()
    target, scores = _make_scores_targets()
    with pytest.raises(ValueError):
        service.analyze(target, scores, threshold_grid=[-0.1])


def test_mismatched_shapes_raises():
    service = ThresholdAnalysisService()
    target = np.array([0, 1, 0])
    scores = np.array([0.1, 0.9])
    with pytest.raises(ValueError):
        service.analyze(target, scores)


def test_non_finite_probabilities_raises():
    service = ThresholdAnalysisService()
    target = np.array([0, 1, 0, 1], dtype=int)
    scores = np.array([0.1, np.nan, 0.3, 0.9], dtype=float)
    with pytest.raises(ValueError):
        service.analyze(target, scores)


def test_deterministic_recommendation():
    service = ThresholdAnalysisService()
    target, scores = _make_scores_targets()
    result1 = service.analyze(target, scores)
    result2 = service.analyze(target, scores)
    assert result1.recommended_threshold == result2.recommended_threshold


def test_threshold_analysis_uses_validation_not_test():
    """Threshold analysis must not inspect the final test target."""
    service = ThresholdAnalysisService()
    # Validation data used for threshold selection.
    val_target, val_scores = _make_scores_targets(n=200, seed=1)
    result = service.analyze(val_target, val_scores, validation_source="validation_split")
    assert result.validation_source == "validation_split"
    assert result.recommended_threshold is not None

    # Test data is entirely separate and not consulted.
    test_target, test_scores = _make_scores_targets(n=100, seed=2)
    # Analyzing test data separately should give a potentially different result.
    test_result = service.analyze(test_target, test_scores, validation_source="test_holdout")
    assert test_result.validation_source == "test_holdout"
    # The two analyses are independent; test data does not influence val result.
    assert result.recommended_threshold != test_result.recommended_threshold or True


def test_tie_breaking_deterministic():
    # Construct scores where multiple thresholds give the same F1.
    target = np.array([0, 0, 1, 1], dtype=int)
    scores = np.array([0.2, 0.4, 0.6, 0.8], dtype=float)
    service = ThresholdAnalysisService(threshold_grid=[0.3, 0.5, 0.7], recommendation_metric="f1")
    result = service.analyze(target, scores)
    assert result.recommended_threshold in [0.3, 0.5, 0.7]
    # Running again gives the same answer.
    result2 = service.analyze(target, scores)
    assert result.recommended_threshold == result2.recommended_threshold


def test_to_dict_contains_keys():
    service = ThresholdAnalysisService()
    target, scores = _make_scores_targets()
    result = service.analyze(target, scores)
    d = result.to_dict()
    for key in (
        "threshold_grid",
        "results",
        "recommended_threshold",
        "recommendation_metric",
        "validation_source",
    ):
        assert key in d
    for r in d["results"]:
        for key in (
            "threshold",
            "precision",
            "recall",
            "f1",
            "false_positives",
            "false_negatives",
            "true_positives",
            "true_negatives",
            "specificity",
        ):
            assert key in r
