"""Threshold Analysis page: false-positive / false-negative trade-offs across thresholds."""

from __future__ import annotations

from typing import Any

import numpy as np
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from maintiq.ml.evaluation.threshold import ThresholdAnalysisService
from maintiq.ml.prediction.service import PredictionService
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.canvas import MatplotlibCanvas
from maintiq.ui.widgets.table_view import TableView

COLUMNS = [
    "threshold",
    "precision",
    "recall",
    "f1",
    "false_positives",
    "false_negatives",
    "true_positives",
    "true_negatives",
]


class ThresholdPage(BasePage):
    """Threshold sweep on model scores (exploratory; computed on imported data)."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Threshold Analysis")
        self.set_subtitle(
            "False-positive / false-negative trade-off across thresholds. "
            "Computed on the imported dataset for exploration only — not a certified threshold."
        )

        controls = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(220)
        self._version_combo = QComboBox()
        self._version_combo.setMinimumWidth(120)
        self.btn_analyze = QPushButton("Analyse thresholds")
        self.btn_analyze.setObjectName("primary")
        controls.addWidget(QLabel("Model:"))
        controls.addWidget(self._model_combo)
        controls.addWidget(QLabel("Version:"))
        controls.addWidget(self._version_combo)
        controls.addWidget(self.btn_analyze)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        self.lbl_recommended = QLabel("Recommended threshold: --")
        self.lbl_recommended.setStyleSheet("font-weight: 700; color: #7dd3fc;")
        self._content_layout.addWidget(self.lbl_recommended)

        self._table = TableView(COLUMNS)
        self._content_layout.addWidget(self._table)

        charts = QHBoxLayout()
        self._canvas_metric = MatplotlibCanvas(width=5, height=3.5)
        self._canvas_tradeoff = MatplotlibCanvas(width=5, height=3.5)
        charts.addWidget(self._canvas_metric, 1)
        charts.addWidget(self._canvas_tradeoff, 1)
        self._content_layout.addLayout(charts)

        self._content_layout.addStretch()

        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.btn_analyze.clicked.connect(self._run_analysis)

    def on_shown(self) -> None:
        self._load_models()

    def _load_models(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        try:
            self._model_combo.addItems(self.service.list_models())
        except Exception as exc:
            self.show_error(f"Could not list models: {exc}")
        self._model_combo.blockSignals(False)
        self._on_model_changed()

    def _on_model_changed(self) -> None:
        self._version_combo.blockSignals(True)
        self._version_combo.clear()
        model = self._model_combo.currentText()
        if model:
            try:
                versions = self.service.list_versions(model)
                self._version_combo.addItems(versions)
                if versions:
                    self._version_combo.setCurrentIndex(len(versions) - 1)
            except Exception as exc:
                self.show_error(f"Could not list versions: {exc}")
        self._version_combo.blockSignals(False)

    def _run_analysis(self) -> None:
        model = self._model_combo.currentText()
        version = self._version_combo.currentText() or None
        if not model:
            self.show_error("Select a model first.")
            return
        try:
            frame = self.service.active_frame
            target = self.service.import_service.target_series()
        except Exception as exc:
            self.show_error(f"Could not read active dataset: {exc}")
            return
        if frame is None or target is None:
            self.show_error("Import a dataset with a target column first.")
            return

        self.btn_analyze.setEnabled(False)
        self.clear_banner()
        self._table.set_rows([])

        def work() -> dict[str, Any]:
            registry = self.service.registry
            pipeline = PredictionService(registry=registry).load_model(model, version=version)
            scores = np.asarray(pipeline.predict_proba(frame), dtype=float)
            classes = list(getattr(pipeline.estimator, "classes_", [0, 1]))
            positive_index = classes.index(1) if 1 in classes else scores.shape[1] - 1
            positive_scores = scores[:, positive_index]
            y_true = np.asarray(target).astype(int)
            if positive_scores.shape[0] != y_true.shape[0]:
                raise ValueError("Score count does not match target count.")
            sweep = ThresholdAnalysisService().analyze(y_true, positive_scores)
            return {"sweep": sweep}

        def on_result(task_result: TaskResult) -> None:
            self.btn_analyze.setEnabled(True)
            sweep = task_result.result["sweep"]
            rows = [
                {
                    "threshold": f"{r.threshold:.2f}",
                    "precision": _fmt(r.precision),
                    "recall": _fmt(r.recall),
                    "f1": _fmt(r.f1),
                    "false_positives": r.false_positives,
                    "false_negatives": r.false_negatives,
                    "true_positives": r.true_positives,
                    "true_negatives": r.true_negatives,
                }
                for r in sweep.results
            ]
            self._table.set_rows(rows)
            self.lbl_recommended.setText(
                f"Recommended threshold: {sweep.recommended_threshold:.2f} "
                f"(maximizes {sweep.recommendation_metric})"
            )
            self._draw_charts(sweep)
            self.show_success("Threshold analysis complete.")

        def on_error(message: str) -> None:
            self.btn_analyze.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "threshold_analysis",
            work,
            started_message="Sweeping thresholds…",
            on_result=on_result,
            on_error=on_error,
        )

    def _draw_charts(self, sweep) -> None:
        thresholds = [r.threshold for r in sweep.results]
        precision = [r.precision if r.precision is not None else 0.0 for r in sweep.results]
        recall = [r.recall if r.recall is not None else 0.0 for r in sweep.results]
        f1 = [r.f1 if r.f1 is not None else 0.0 for r in sweep.results]
        fps = [r.false_positives for r in sweep.results]
        fns = [r.false_negatives for r in sweep.results]

        figure = self._canvas_metric.figure
        figure.clear()
        ax = figure.add_subplot(111)
        ax.plot(thresholds, precision, marker="o", label="Precision", color="#0ea5e9")
        ax.plot(thresholds, recall, marker="o", label="Recall", color="#fb923c")
        ax.plot(thresholds, f1, marker="o", label="F1-score", color="#34d399")
        ax.axvline(
            sweep.recommended_threshold,
            color="gray",
            linestyle="--",
            label=f"Recommended ({sweep.recommended_threshold:.2f})",
        )
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Score")
        ax.set_title("Threshold vs Metric")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        figure.tight_layout()
        self._canvas_metric.canvas.draw_idle()

        figure2 = self._canvas_tradeoff.figure
        figure2.clear()
        ax2 = figure2.add_subplot(111)
        ax2.plot(thresholds, fps, marker="o", label="False Positives", color="#fb923c")
        ax2.plot(thresholds, fns, marker="o", label="False Negatives", color="#22d3ee")
        ax2.axvline(
            sweep.recommended_threshold,
            color="gray",
            linestyle="--",
            label=f"Recommended ({sweep.recommended_threshold:.2f})",
        )
        ax2.set_xlabel("Threshold")
        ax2.set_ylabel("Count")
        ax2.set_title("FP / FN Trade-off")
        ax2.set_xlim(0, 1)
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3)
        figure2.tight_layout()
        self._canvas_tradeoff.canvas.draw_idle()


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
