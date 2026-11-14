"""Leakage-safe threshold analysis for binary classification.

Threshold selection uses validation scores only. The final held-out test set is
never consulted when choosing a threshold, preventing data leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from maintiq.ml.evaluation.service import EvaluationService

DEFAULT_THRESHOLD_GRID = [round(v, 2) for v in np.linspace(0.0, 1.0, 21).tolist()]
DEFAULT_RECOMMENDATION_METRIC = "f1"
DEFAULT_THRESHOLD = 0.5


@dataclass
class ThresholdResult:
    """Metrics for a single candidate threshold."""

    threshold: float
    precision: float | None
    recall: float | None
    f1: float | None
    false_positives: int
    false_negatives: int
    true_positives: int
    true_negatives: int
    specificity: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "specificity": self.specificity,
        }


@dataclass
class ThresholdAnalysisResult:
    """Outcome of threshold analysis on validation scores."""

    threshold_grid: list[float]
    results: list[ThresholdResult]
    recommended_threshold: float
    recommendation_metric: str
    validation_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold_grid": self.threshold_grid,
            "results": [r.to_dict() for r in self.results],
            "recommended_threshold": self.recommended_threshold,
            "recommendation_metric": self.recommendation_metric,
            "validation_source": self.validation_source,
        }


def _default_tiebreak(
    candidates: list[tuple[float, float]], reference: float = DEFAULT_THRESHOLD
) -> float:
    """Break ties deterministically: closest to ``reference``, then lowest."""
    best_threshold = None
    best_distance = None
    for threshold, _metric in candidates:
        distance = abs(threshold - reference)
        if (
            best_threshold is None
            or distance < best_distance
            or (distance == best_distance and threshold < best_threshold)
        ):
            best_threshold = threshold
            best_distance = distance
    return best_threshold


class ThresholdAnalysisService:
    """Selects a classification threshold using validation scores only."""

    def __init__(
        self,
        threshold_grid: list[float] | None = None,
        recommendation_metric: str = DEFAULT_RECOMMENDATION_METRIC,
        default_threshold: float = DEFAULT_THRESHOLD,
    ):
        self.threshold_grid = (
            sorted(threshold_grid) if threshold_grid is not None else list(DEFAULT_THRESHOLD_GRID)
        )
        self.recommendation_metric = recommendation_metric
        self.default_threshold = default_threshold
        self._evaluator = EvaluationService()

    def analyze(
        self,
        y_true: Any,
        y_scores: Any,
        threshold_grid: list[float] | None = None,
        include_default: bool = True,
        validation_source: str = "validation_split",
    ) -> ThresholdAnalysisResult:
        """Analyze candidate thresholds on validation data.

        ``y_true`` and ``y_scores`` must come from a validation partition only;
        the final held-out test set must never be passed here.
        """
        y_true = np.asarray(y_true).astype(int)
        y_scores = np.asarray(y_scores, dtype=float)
        if y_true.ndim != 1 or y_scores.ndim != 1:
            raise ValueError("y_true and y_scores must be 1D arrays.")
        if y_true.shape[0] != y_scores.shape[0]:
            raise ValueError(
                f"Score count {y_scores.shape[0]} does not match target count {y_true.shape[0]}."
            )

        grid = sorted(threshold_grid) if threshold_grid is not None else list(self.threshold_grid)
        if include_default and self.default_threshold not in grid:
            grid = sorted({*grid, self.default_threshold})

        results: list[ThresholdResult] = []
        for threshold in grid:
            metrics = self._evaluator.evaluate_scores(y_true, y_scores, threshold=threshold)
            results.append(
                ThresholdResult(
                    threshold=threshold,
                    precision=metrics.precision,
                    recall=metrics.recall,
                    f1=metrics.f1,
                    false_positives=metrics.false_positives,
                    false_negatives=metrics.false_negatives,
                    true_positives=metrics.true_positives,
                    true_negatives=metrics.true_negatives,
                    specificity=metrics.specificity,
                )
            )

        recommended = self._recommend(results)
        return ThresholdAnalysisResult(
            threshold_grid=grid,
            results=results,
            recommended_threshold=recommended,
            recommendation_metric=self.recommendation_metric,
            validation_source=validation_source,
        )

    def _recommend(self, results: list[ThresholdResult]) -> float:
        """Recommend the threshold maximizing the configured metric.

        Tie-breaking is deterministic: closest to the default threshold, then
        the lowest threshold. Returns the default threshold if no valid metric
        values exist.
        """
        metric = self.recommendation_metric
        valid: list[tuple[float, float]] = []
        for result in results:
            value = getattr(result, metric, None)
            if value is not None and np.isfinite(value):
                valid.append((result.threshold, float(value)))

        if not valid:
            return self.default_threshold

        best_value = max(v for _, v in valid)
        candidates = [(t, v) for t, v in valid if v == best_value]
        return _default_tiebreak(candidates, self.default_threshold)
