"""Reporting and export service for evaluation outputs.

Supports JSON metrics/model comparison export, CSV threshold-analysis export
and PNG chart export. Exports are written atomically where practical and
filenames are sanitised to prevent path traversal.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

import numpy as np

from maintiq import __version__
from maintiq.config import get_config
from maintiq.core.exceptions import ReportError
from maintiq.ml.evaluation.charts import (
    plot_confusion_matrix,
    plot_fp_fn_tradeoff,
    plot_model_comparison,
    plot_precision_recall_curve,
    plot_roc_curve,
    plot_threshold_vs_metric,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_filename(name: str) -> str:
    """Sanitise a filename, rejecting path traversal attempts."""
    if ".." in name or name.startswith("/") or "\\" in name:
        raise ReportError(f"Unsafe filename: {name!r}")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not safe or safe in (".", ".."):
        raise ReportError(f"Unsafe filename: {name!r}")
    return safe


def _validate_output_path(output_dir: Path, output_path: Path) -> Path:
    """Ensure ``output_path`` resolves within ``output_dir``."""
    resolved = output_path.resolve()
    root = output_dir.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReportError(f"Output path escapes report directory: {output_path}") from exc
    return resolved


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text to ``path`` atomically via a sibling temp file."""
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
        except OSError:  # pragma: no cover - best effort cleanup
            pass
        raise


class ReportService:
    """Exports evaluation results to JSON, CSV and PNG."""

    def __init__(self, output_dir: str | Path | None = None):
        if output_dir is None:
            config = get_config()
            output_dir = config.paths.reports_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- JSON

    def export_json(
        self,
        metrics: Any = None,
        comparison_result: Any = None,
        threshold_result: Any = None,
        model_name: str | None = None,
        model_version: str | None = None,
        dataset_fingerprint: str | None = None,
        target_column: str | None = None,
        feature_columns: list[str] | None = None,
        split_settings: dict[str, Any] | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        """Export evaluation results to a JSON file.

        Includes MaintiQ version, model info, dataset fingerprint, target
        definition, features, split details, metrics and warnings.
        """
        report: dict[str, Any] = {
            "maintiq_version": __version__,
            "created_at": _utc_now_iso(),
            "model": {
                "name": model_name,
                "version": model_version,
            },
            "dataset": {
                "fingerprint": dataset_fingerprint,
                "target_column": target_column,
                "feature_columns": feature_columns,
            },
            "split": split_settings,
            "threshold_selection": (
                threshold_result.to_dict() if threshold_result is not None else None
            ),
            "metrics": metrics.to_dict() if metrics is not None else None,
            "comparison": (comparison_result.to_dict() if comparison_result is not None else None),
            "warnings": [
                "MaintiQ is an academic decision-support prototype.",
                "Model outputs are not certified industrial diagnoses.",
                "Qualified human review is required before deployment.",
            ],
        }

        if output_path is None:
            stem = _sanitize_filename(model_name or "evaluation")
            output_path = self.output_dir / f"{stem}_report.json"
        output_path = Path(output_path)
        output_path = _validate_output_path(self.output_dir, output_path)

        _atomic_write_text(output_path, json.dumps(report, indent=2, sort_keys=True))
        return output_path

    # ---------------------------------------------------------------- CSV

    def export_csv(
        self,
        threshold_result: Any,
        output_path: str | Path | None = None,
    ) -> Path:
        """Export threshold-analysis results to a CSV file."""
        if output_path is None:
            output_path = self.output_dir / "threshold_analysis.csv"
        output_path = Path(output_path)
        output_path = _validate_output_path(self.output_dir, output_path)

        tmp_path = output_path.with_name(output_path.name + ".tmp")
        try:
            with open(tmp_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "threshold",
                        "precision",
                        "recall",
                        "f1",
                        "false_positives",
                        "false_negatives",
                        "true_positives",
                        "true_negatives",
                        "specificity",
                    ]
                )
                for r in threshold_result.results:
                    writer.writerow(
                        [
                            r.threshold,
                            r.precision,
                            r.recall,
                            r.f1,
                            r.false_positives,
                            r.false_negatives,
                            r.true_positives,
                            r.true_negatives,
                            r.specificity,
                        ]
                    )
            os.replace(tmp_path, output_path)
        except BaseException:
            try:
                tmp_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
            except OSError:  # pragma: no cover - best effort cleanup
                pass
            raise
        return output_path

    # ---------------------------------------------------------------- PNG

    def export_png(
        self,
        y_true: Any,
        scores: Any,
        metrics: Any,
        comparison_result: Any = None,
        threshold_result: Any = None,
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """Export all evaluation charts as PNG files.

        Returns the list of written file paths. Skips ROC/PR charts when a
        single target class is present.
        """
        if output_dir is None:
            output_dir = self.output_dir / "figures"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        y_true = np.asarray(y_true).astype(int)
        scores = np.asarray(scores, dtype=float)
        classes = np.unique(y_true)
        binary = classes.size >= 2

        written: list[Path] = []

        # Model metric comparison.
        if comparison_result is not None:
            p = output_dir / "model_comparison.png"
            plot_model_comparison(comparison_result, output_path=str(p))
            written.append(p)

        # Confusion matrix.
        p = output_dir / "confusion_matrix.png"
        plot_confusion_matrix(metrics, output_path=str(p))
        written.append(p)

        # ROC and precision-recall curves (binary only).
        if binary:
            p = output_dir / "roc_curve.png"
            plot_roc_curve(y_true, scores, output_path=str(p))
            written.append(p)

            p = output_dir / "precision_recall_curve.png"
            plot_precision_recall_curve(y_true, scores, output_path=str(p))
            written.append(p)

        # Threshold analysis.
        if threshold_result is not None:
            p = output_dir / "threshold_vs_metric.png"
            plot_threshold_vs_metric(threshold_result, output_path=str(p))
            written.append(p)

            p = output_dir / "fp_fn_tradeoff.png"
            plot_fp_fn_tradeoff(threshold_result, output_path=str(p))
            written.append(p)

        return written
