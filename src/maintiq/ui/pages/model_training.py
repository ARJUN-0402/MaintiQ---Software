"""Model Training page: train a candidate classifier on the active dataset."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit

from maintiq.config import SUPPORTED_MODELS
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.metric_card import MetricCard


class _TrainingProgress(QObject):
    message = Signal(str)


class ModelTrainingPage(BasePage):
    """Train a candidate model on the active dataset in a background worker."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Model Training")
        self.set_subtitle(
            "Train Logistic Regression, Random Forest, Gradient Boosting or XGBoost "
            "on the active dataset. Training runs off the UI thread."
        )

        controls = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.addItems([m.replace("_", " ").title() for m in SUPPORTED_MODELS])
        self._model_combo.setMinimumWidth(240)
        self.btn_train = QPushButton("Train model")
        self.btn_train.setObjectName("primary")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setEnabled(False)
        controls.addWidget(QLabel("Model:"))
        controls.addWidget(self._model_combo)
        controls.addWidget(self.btn_train)
        controls.addWidget(self.btn_cancel)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.hide()
        self._content_layout.addWidget(self._progress)

        self.lbl_stage = QLabel("Idle")
        self.lbl_stage.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._content_layout.addWidget(self.lbl_stage)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(160)
        self._content_layout.addWidget(self._log)

        cards = QHBoxLayout()
        self.card_version = MetricCard("Model version", "--")
        self.card_accuracy = MetricCard("Accuracy", "--")
        self.card_f1 = MetricCard("F1", "--")
        self.card_duration = MetricCard("Duration (s)", "--")
        for card in (self.card_version, self.card_accuracy, self.card_f1, self.card_duration):
            cards.addWidget(card)
        self._content_layout.addLayout(cards)

        self._content_layout.addStretch()

        self.btn_train.clicked.connect(self._run_training)
        self.btn_cancel.clicked.connect(self._cancel)

        self._cancelled = False
        self._progress_sink = _TrainingProgress()
        self._progress_sink.message.connect(self._on_progress)

    # ---------------------------------------------------------------- training

    def _model_key(self) -> str:
        return self._model_combo.currentText().replace(" ", "_").lower()

    def _run_training(self) -> None:
        self._cancelled = False
        self.btn_train.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._progress.show()
        self._log.clear()
        self.lbl_stage.setText("Starting…")
        for card in (self.card_version, self.card_accuracy, self.card_f1, self.card_duration):
            card.set_value("--")

        model_key = self._model_key()

        def cancelled_check() -> bool:
            return self._cancelled

        def work() -> dict[str, Any]:
            result = self.service.train_model(
                model_key,
                cancelled_check=cancelled_check,
                progress_callback=self._progress_sink.message.emit,
            )
            return {
                "model_name": result.model_name,
                "model_version": result.model_version,
                "metrics": result.metrics or {},
                "duration": result.training_duration_seconds,
                "cancelled": result.cancelled,
            }

        def on_result(task_result: TaskResult) -> None:
            self.btn_train.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self._progress.hide()
            result = task_result.result
            if result["cancelled"]:
                self.lbl_stage.setText("Cancelled.")
                self.show_warning("Training was cancelled.")
                return
            self.lbl_stage.setText("Completed.")
            self.card_version.set_value(str(result["model_version"] or "—"))
            metrics = result["metrics"]
            self.card_accuracy.set_value(_fmt(metrics.get("accuracy")))
            self.card_f1.set_value(_fmt(metrics.get("f1")))
            self.card_duration.set_value(
                f"{result['duration']:.1f}" if result["duration"] is not None else "—"
            )
            self.show_success(
                f"Trained {result['model_name']} (version {result['model_version']})."
            )

        def on_error(message: str) -> None:
            self.btn_train.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self._progress.hide()
            self.lbl_stage.setText("Failed.")
            self.show_error(message)

        self.run_task(
            "train_model",
            work,
            started_message=f"Training {model_key}…",
            on_result=on_result,
            on_error=on_error,
        )

    def _cancel(self) -> None:
        self._cancelled = True
        self.btn_cancel.setEnabled(False)
        self.lbl_stage.setText("Cancelling…")

    def _on_progress(self, message: str) -> None:
        self.lbl_stage.setText(message)
        self._log.append(message)


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
