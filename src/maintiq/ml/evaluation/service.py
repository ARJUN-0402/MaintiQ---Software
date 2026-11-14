"""Model evaluation: threshold-aware classification metrics computed on the
held-out test partition only.

All metrics are JSON-safe primitives: undefined values (for example ROC-AUC
with a single target class, or zero-division rates) are reported as ``None``
rather than NaN or Infinity, which are not valid JSON numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


def _json_safe_float(value: float | None) -> float | None:
    """Return ``value`` as a JSON-safe float, or ``None`` for NaN/Infinity."""
    if value is None:
        return None
    value = float(value)
    if np.isnan(value) or np.isinf(value):
        return None
    return value


@dataclass
class ClassificationMetrics:
    """Threshold-dependent and threshold-independent classification metrics.

    Undefined metrics (for example ROC-AUC with a single target class, or a
    rate with a zero denominator) are reported as ``None`` with a documented
    zero-division policy: rates with a zero denominator are ``0.0``.
    """

    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None
    true_negatives: int
    false_positives: int
    false_negatives: int
    true_positives: int
    threshold: float
    n_samples: int
    n_positive: int
    specificity: float | None = None
    balanced_accuracy: float | None = None
    fpr: float | None = None
    fnr: float | None = None
    average_precision: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": _json_safe_float(self.accuracy),
            "precision": _json_safe_float(self.precision),
            "recall": _json_safe_float(self.recall),
            "f1": _json_safe_float(self.f1),
            "roc_auc": _json_safe_float(self.roc_auc),
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_positives": self.true_positives,
            "threshold": self.threshold,
            "n_samples": self.n_samples,
            "n_positive": self.n_positive,
            "specificity": _json_safe_float(self.specificity),
            "balanced_accuracy": _json_safe_float(self.balanced_accuracy),
            "fpr": _json_safe_float(self.fpr),
            "fnr": _json_safe_float(self.fnr),
            "average_precision": _json_safe_float(self.average_precision),
        }


def _safe_divide(numerator: float, denominator: float) -> float:
    """Divide with a documented zero-division policy: return 0.0 on zero denom."""
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return tn, fp, fn, tp


def _roc_auc_score(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    """Rank-based ROC AUC (Mann-Whitney U statistic). Returns None if a single
    class is present."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    classes = np.unique(y_true)
    if classes.size < 2:
        return None
    positives = scores[y_true == 1]
    negatives = scores[y_true == 0]
    if positives.size == 0 or negatives.size == 0:
        return None
    comparison = positives[:, None] > negatives[None, :]
    ties = positives[:, None] == negatives[None, :]
    score = float(np.sum(comparison)) + 0.5 * float(np.sum(ties))
    return score / (positives.size * negatives.size)


def _average_precision_score(y_true: np.ndarray, scores: np.ndarray) -> float | None:
    """Average precision (area under the precision-recall curve).

    Returns None when a single target class is present.
    """
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    classes = np.unique(y_true)
    if classes.size < 2:
        return None
    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y_true[order]
    n_pos = int(np.sum(y_true == 1))
    if n_pos == 0:
        return None
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)
    recall = tp_cum / float(n_pos)
    # Step interpolation: AP = sum((R_n - R_{n-1}) * P_n).
    recall_prev = np.concatenate([[0.0], recall[:-1]])
    ap = float(np.sum((recall - recall_prev) * precision))
    return ap


def _positive_scores(scores: np.ndarray, estimator: Any) -> tuple[np.ndarray, int | None]:
    """Extract positive-class scores from predict_proba output.

    Returns ``(positive_scores, positive_index)``. The positive class is
    identified by inspecting ``estimator.classes_`` for class ``1``; if absent,
    the last column is used. Never assumes column index 1 is positive without
    inspection.
    """
    scores = np.asarray(scores, dtype=float)
    if scores.ndim == 1:
        return scores, None
    if scores.ndim != 2:
        raise ValueError(
            f"predict_proba returned an array with {scores.ndim} dimensions; expected 1D or 2D."
        )
    positive_index: int | None = None
    if hasattr(estimator, "classes_"):
        classes = list(estimator.classes_)
        if 1 in classes:
            positive_index = classes.index(1)
    if positive_index is None:
        positive_index = scores.shape[1] - 1
    return scores[:, positive_index], positive_index


def _validate_threshold(threshold: float) -> float:
    threshold = float(threshold)
    if not (0.0 <= threshold <= 1.0):
        raise ValueError(f"Threshold must be within [0, 1], got {threshold}.")
    return threshold


class EvaluationService:
    """Computes classification metrics for a trained pipeline on held-out data."""

    def evaluate(
        self,
        pipeline: Any,
        frame: Any,
        target: Any,
        threshold: float = 0.5,
    ) -> ClassificationMetrics:
        """Evaluate ``pipeline`` on ``frame``/``target`` at ``threshold``.

        The threshold is applied explicitly to the positive-class probabilities;
        the pipeline's default-threshold ``predict()`` is never used.
        """
        threshold = _validate_threshold(threshold)
        y_true = np.asarray(target).astype(int)
        if y_true.ndim != 1:
            raise ValueError(f"Target must be a 1D array, got shape {y_true.shape}.")
        scores = pipeline.predict_proba(frame)
        positive_scores, _positive_index = _positive_scores(scores, pipeline.estimator)
        if positive_scores.shape[0] != y_true.shape[0]:
            raise ValueError(
                f"Score count {positive_scores.shape[0]} does not match target "
                f"count {y_true.shape[0]}."
            )
        if not np.all(np.isfinite(positive_scores)):
            raise ValueError("Prediction scores contain non-finite values (NaN/Infinity).")

        return self._compute_metrics(y_true, positive_scores, threshold)

    def evaluate_scores(
        self,
        y_true: Any,
        scores: Any,
        threshold: float = 0.5,
        estimator: Any = None,
    ) -> ClassificationMetrics:
        """Compute metrics directly from true labels and positive-class scores.

        Useful for threshold analysis on validation scores where no pipeline
        is available.
        """
        threshold = _validate_threshold(threshold)
        y_true = np.asarray(y_true).astype(int)
        if y_true.ndim != 1:
            raise ValueError(f"Target must be a 1D array, got shape {y_true.shape}.")
        scores = np.asarray(scores, dtype=float)
        if scores.ndim != 1:
            raise ValueError(f"Scores must be a 1D array, got shape {scores.shape}.")
        if scores.shape[0] != y_true.shape[0]:
            raise ValueError(
                f"Score count {scores.shape[0]} does not match target count {y_true.shape[0]}."
            )
        if not np.all(np.isfinite(scores)):
            raise ValueError("Prediction scores contain non-finite values (NaN/Infinity).")

        return self._compute_metrics(y_true, scores, threshold)

    def _compute_metrics(
        self, y_true: np.ndarray, positive_scores: np.ndarray, threshold: float
    ) -> ClassificationMetrics:
        y_pred = (positive_scores >= threshold).astype(int)

        tn, fp, fn, tp = _confusion_matrix(y_true, y_pred)
        n_samples = int(y_true.size)
        n_positive = int(np.sum(y_true == 1))

        accuracy = _safe_divide(tp + tn, n_samples)
        precision = _safe_divide(tp, tp + fp)
        recall = _safe_divide(tp, tp + fn)
        f1 = _safe_divide(2 * tp, 2 * tp + fp + fn)
        roc_auc = _roc_auc_score(y_true, positive_scores)
        average_precision = _average_precision_score(y_true, positive_scores)

        specificity = _safe_divide(tn, tn + fp)
        balanced_accuracy = _safe_divide(recall + specificity, 2.0)
        fpr = _safe_divide(fp, fp + tn)
        fnr = _safe_divide(fn, fn + tp)

        return ClassificationMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            roc_auc=roc_auc,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            true_positives=tp,
            threshold=float(threshold),
            n_samples=n_samples,
            n_positive=n_positive,
            specificity=specificity,
            balanced_accuracy=balanced_accuracy,
            fpr=fpr,
            fnr=fnr,
            average_precision=average_precision,
        )
