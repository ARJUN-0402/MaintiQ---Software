"""Model Performance page: metrics and charts for a registered model version."""

from __future__ import annotations

from typing import Any, ClassVar

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton

from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.canvas import MatplotlibCanvas
from maintiq.ui.widgets.metric_card import MetricCard


class ModelPerformancePage(BasePage):
    """Evaluation metrics and charts for a selected model version."""

    METRIC_COLUMNS: ClassVar[list[str]] = ["metric", "value"]

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Model Performance")
        self.set_subtitle(
            "Evaluation metrics for a registered model version (from its training run)."
        )

        controls = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(220)
        self._version_combo = QComboBox()
        self._version_combo.setMinimumWidth(120)
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("primary")
        controls.addWidget(QLabel("Model:"))
        controls.addWidget(self._model_combo)
        controls.addWidget(QLabel("Version:"))
        controls.addWidget(self._version_combo)
        controls.addWidget(self.btn_refresh)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        cards = QGridLayout()
        cards.setSpacing(10)
        self.card_accuracy = MetricCard("Accuracy", "--")
        self.card_precision = MetricCard("Precision", "--")
        self.card_recall = MetricCard("Recall", "--")
        self.card_f1 = MetricCard("F1", "--")
        self.card_roc_auc = MetricCard("ROC-AUC", "--")
        for index, card in enumerate(
            (
                self.card_accuracy,
                self.card_precision,
                self.card_recall,
                self.card_f1,
                self.card_roc_auc,
            )
        ):
            cards.addWidget(card, 0, index)
        self._content_layout.addLayout(cards)

        self._canvas = MatplotlibCanvas(width=6, height=4)
        self._content_layout.addWidget(QLabel("Confusion matrix (at training threshold)"))
        self._content_layout.addWidget(self._canvas, 1)

        self._meta = QLabel()
        self._meta.setWordWrap(True)
        self._meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._content_layout.addWidget(self._meta)

        self._content_layout.addStretch()

        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        self.btn_refresh.clicked.connect(self._load)

    # ---------------------------------------------------------------- models

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

    # ---------------------------------------------------------------- load

    def _load(self) -> None:
        model = self._model_combo.currentText()
        version = self._version_combo.currentText() or None
        if not model:
            self.show_error("Select a model first.")
            return
        self.btn_refresh.setEnabled(False)
        self.clear_banner()

        def work() -> dict[str, Any]:
            record = (
                self.service.registry.get_version(model, version)
                if version
                else self.service.registry.get_latest(model)
            )
            return {"record": record}

        def on_result(task_result: TaskResult) -> None:
            self.btn_refresh.setEnabled(True)
            record = task_result.result["record"]
            metrics = record.get("metrics") or {}
            self.card_accuracy.set_value(_fmt(metrics.get("accuracy")))
            self.card_precision.set_value(_fmt(metrics.get("precision")))
            self.card_recall.set_value(_fmt(metrics.get("recall")))
            self.card_f1.set_value(_fmt(metrics.get("f1")))
            self.card_roc_auc.set_value(_fmt(metrics.get("roc_auc")))
            self._meta.setText(
                f"Version {record.get('version')} · created {record.get('created_at', '')[:19]} · "
                f"threshold {record.get('threshold') if record.get('threshold') is not None else 'n/a'}"
            )
            self._draw_confusion_matrix(metrics)

        def on_error(message: str) -> None:
            self.btn_refresh.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "load_performance",
            work,
            started_message="Loading model metrics…",
            on_result=on_result,
            on_error=on_error,
        )

    def _draw_confusion_matrix(self, metrics: dict[str, Any]) -> None:
        try:
            tn = int(metrics.get("true_negatives", 0) or 0)
            fp = int(metrics.get("false_positives", 0) or 0)
            fn = int(metrics.get("false_negatives", 0) or 0)
            tp = int(metrics.get("true_positives", 0) or 0)
        except (TypeError, ValueError):
            return
        figure = self._canvas.figure
        figure.clear()
        ax = figure.add_subplot(111)
        matrix = [[tn, fp], [fn, tp]]
        im = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Negative", "Positive"])
        ax.set_yticklabels(["Negative", "Positive"])
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("True class")
        threshold = metrics.get("threshold")
        ax.set_title(f"Confusion matrix (threshold={threshold})")
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
        figure.colorbar(im, ax=ax, label="Count")
        figure.tight_layout()
        self._canvas.canvas.draw_idle()


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
