"""Evaluation visualisations using matplotlib (the project's charting stack).

All charts are computed from real metrics and arrays; no placeholder or
synthetic performance values are used. Figure handles are closed after saving
to avoid memory leaks. Plotting code is separate from evaluation calculations
and UI code.
"""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from maintiq.config import get_config


def _ensure_figures_dir() -> str:
    """Return the configured reports/figures directory, creating it if needed."""
    config = get_config()
    figures_dir = config.paths.reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    return str(figures_dir)


def _save_figure(fig: plt.Figure, output_path: str) -> str:
    """Save a figure to ``output_path`` and close the figure handle."""
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def _roc_curve_points(y_true: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute ROC curve points (FPR, TPR) from scores sorted by threshold."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y_true[order]
    n_pos = int(np.sum(y_true == 1))
    n_neg = int(np.sum(y_true == 0))
    if n_pos == 0 or n_neg == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    tpr = tp_cum / float(n_pos)
    fpr = fp_cum / float(n_neg)
    tpr = np.concatenate([[0.0], tpr])
    fpr = np.concatenate([[0.0], fpr])
    return fpr, tpr


def _pr_curve_points(y_true: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute precision-recall curve points from scores sorted by threshold."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    order = np.argsort(-scores, kind="mergesort")
    y_sorted = y_true[order]
    n_pos = int(np.sum(y_true == 1))
    if n_pos == 0:
        return np.array([0.0, 1.0]), np.array([0.0, 1.0])
    tp_cum = np.cumsum(y_sorted == 1)
    fp_cum = np.cumsum(y_sorted == 0)
    precision = tp_cum / np.maximum(tp_cum + fp_cum, 1)
    recall = tp_cum / float(n_pos)
    precision = np.concatenate([[1.0], precision])
    recall = np.concatenate([[0.0], recall])
    return recall, precision


# ------------------------------------------------------------------ charts


def plot_model_comparison(comparison_result: Any, output_path: str | None = None) -> str:
    """Bar chart of the selected metric across compared models."""
    successful = comparison_result.successful()
    if not successful:
        raise ValueError("No successful model results to plot.")

    metric = comparison_result.selected_metric
    names = [r.display_name for r in successful]
    values = []
    for r in successful:
        m = r.metrics
        if m is not None:
            values.append(getattr(m, metric, 0.0) or 0.0)
        else:
            values.append(0.0)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, values, color="#4c78a8", edgecolor="black")
    ax.set_ylabel(metric.upper())
    ax.set_title(f"Model Comparison — {metric.upper()}")
    ax.set_ylim(0, 1.0)
    for bar, value in zip(bars, values, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.02,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", alpha=0.3)

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/model_comparison_{metric}.png"
    return _save_figure(fig, output_path)


def plot_confusion_matrix(metrics: Any, output_path: str | None = None) -> str:
    """Heatmap of the confusion matrix (tn, fp, fn, tp)."""
    tn = metrics.true_negatives
    fp = metrics.false_positives
    fn = metrics.false_negatives
    tp = metrics.true_positives

    matrix = [[tn, fp], [fn, tp]]
    labels = ["Negative", "Positive"]

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted class")
    ax.set_ylabel("True class")
    ax.set_title(f"Confusion Matrix (threshold={metrics.threshold})")

    for i in range(2):
        for j in range(2):
            ax.text(
                j,
                i,
                str(matrix[i][j]),
                ha="center",
                va="center",
                color="white" if matrix[i][j] > max(tn, fp, fn, tp) / 2 else "black",
                fontsize=14,
                fontweight="bold",
            )

    plt.colorbar(im, ax=ax, label="Count")

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/confusion_matrix.png"
    return _save_figure(fig, output_path)


def plot_roc_curve(y_true: Any, scores: Any, output_path: str | None = None) -> str:
    """ROC curve when both target classes are present."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    classes = np.unique(y_true)
    if classes.size < 2:
        raise ValueError("ROC curve requires both target classes to be present.")

    fpr, tpr = _roc_curve_points(y_true, scores)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color="#4c78a8", linewidth=2, label="ROC curve")
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Chance")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/roc_curve.png"
    return _save_figure(fig, output_path)


def plot_precision_recall_curve(y_true: Any, scores: Any, output_path: str | None = None) -> str:
    """Precision-recall curve when both target classes are present."""
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores, dtype=float)
    classes = np.unique(y_true)
    if classes.size < 2:
        raise ValueError("Precision-recall curve requires both target classes to be present.")

    recall, precision = _pr_curve_points(y_true, scores)

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(recall, precision, color="#e45756", linewidth=2, label="PR curve")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower left")
    ax.grid(alpha=0.3)

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/precision_recall_curve.png"
    return _save_figure(fig, output_path)


def plot_threshold_vs_metric(threshold_result: Any, output_path: str | None = None) -> str:
    """Line chart of precision, recall and F1 versus threshold."""
    thresholds = [r.threshold for r in threshold_result.results]
    precision = [r.precision if r.precision is not None else 0.0 for r in threshold_result.results]
    recall = [r.recall if r.recall is not None else 0.0 for r in threshold_result.results]
    f1 = [r.f1 if r.f1 is not None else 0.0 for r in threshold_result.results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, precision, marker="o", label="Precision", color="#4c78a8")
    ax.plot(thresholds, recall, marker="o", label="Recall", color="#e45756")
    ax.plot(thresholds, f1, marker="o", label="F1-score", color="#54a24b")
    ax.axvline(
        threshold_result.recommended_threshold,
        color="gray",
        linestyle="--",
        label=f"Recommended ({threshold_result.recommended_threshold:.2f})",
    )
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Score")
    ax.set_title("Threshold vs Metric Analysis")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(alpha=0.3)

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/threshold_vs_metric.png"
    return _save_figure(fig, output_path)


def plot_fp_fn_tradeoff(threshold_result: Any, output_path: str | None = None) -> str:
    """Line chart of false positives and false negatives versus threshold."""
    thresholds = [r.threshold for r in threshold_result.results]
    fps = [r.false_positives for r in threshold_result.results]
    fns = [r.false_negatives for r in threshold_result.results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(thresholds, fps, marker="o", label="False Positives", color="#e45756")
    ax.plot(thresholds, fns, marker="o", label="False Negatives", color="#72b7b2")
    ax.axvline(
        threshold_result.recommended_threshold,
        color="gray",
        linestyle="--",
        label=f"Recommended ({threshold_result.recommended_threshold:.2f})",
    )
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Count")
    ax.set_title("False Positive / False Negative Trade-off")
    ax.set_xlim(0, 1)
    ax.legend()
    ax.grid(alpha=0.3)

    if output_path is None:
        output_path = f"{_ensure_figures_dir()}/fp_fn_tradeoff.png"
    return _save_figure(fig, output_path)
