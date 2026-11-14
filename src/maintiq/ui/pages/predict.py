"""Predict Failure page: single-record inference through a registered model."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QPushButton

from maintiq.ml.prediction import PredictionOutcome
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.form_input import PredictionInputForm
from maintiq.ui.widgets.metric_card import MetricCard


class PredictPage(BasePage):
    """Single-record machine-failure prediction form."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Predict Failure")
        self.set_subtitle("Enter machine attributes and run inference on a registered model.")

        self._form = PredictionInputForm()
        self._content_layout.addWidget(self._form)

        # Model / version selection.
        select_row = QHBoxLayout()
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(220)
        self._version_combo = QComboBox()
        self._version_combo.setMinimumWidth(120)
        self._refresh_models = QPushButton("Refresh models")
        self._refresh_models.setMaximumWidth(120)
        select_row.addWidget(QLabel("Model:"))
        select_row.addWidget(self._model_combo)
        select_row.addWidget(QLabel("Version:"))
        select_row.addWidget(self._version_combo)
        select_row.addWidget(self._refresh_models)
        select_row.addStretch()
        self._content_layout.addLayout(select_row)

        # Action row.
        action_row = QHBoxLayout()
        self.btn_predict = QPushButton("Predict failure")
        self.btn_predict.setObjectName("primary")
        self.btn_predict.setMinimumWidth(160)
        self.btn_explain = QPushButton("Explain this prediction")
        self.btn_explain.setObjectName("accent")
        self.btn_explain.setEnabled(False)
        self.btn_explain.setMinimumWidth(160)
        action_row.addWidget(self.btn_predict)
        action_row.addWidget(self.btn_explain)
        action_row.addStretch()
        self._content_layout.addLayout(action_row)

        # Result area.
        self._result_grid = QGridLayout()
        self._result_grid.setSpacing(10)
        self.card_class = MetricCard("Predicted class", "--")
        self.card_score = MetricCard("Failure score", "--")
        self.card_threshold = MetricCard("Threshold", "--")
        self.card_model = MetricCard("Model / version", "--")
        for index, card in enumerate(
            (self.card_class, self.card_score, self.card_threshold, self.card_model)
        ):
            self._result_grid.addWidget(card, 0, index)
        self._content_layout.addLayout(self._result_grid)

        self._warnings = QLabel()
        self._warnings.setWordWrap(True)
        self._warnings.setStyleSheet("color: #fca5a5; font-size: 12px;")
        self._content_layout.addWidget(self._warnings)

        self._notice = QLabel(
            "MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark "
            "dataset. The score is a model output, not a certified failure probability; "
            "qualified human review is required."
        )
        self._notice.setWordWrap(True)
        self._notice.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self._content_layout.addWidget(self._notice)

        self._content_layout.addStretch()

        # Wiring.
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        self._refresh_models.clicked.connect(self._load_models)
        self.btn_predict.clicked.connect(self._run_prediction)
        self.btn_explain.clicked.connect(self._explain_last)

        self._last_outcome: PredictionOutcome | None = None
        self._last_record: dict[str, Any] | None = None
        self._background_frame = None

    # ---------------------------------------------------------------- model list

    def on_shown(self) -> None:
        self._load_models()
        try:
            frame = self.service.active_frame
            self._background_frame = frame
        except Exception:
            self._background_frame = None

    def _load_models(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        try:
            models = self.service.list_models()
            self._model_combo.addItems(models)
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
                self.show_error(f"Could not list versions for {model}: {exc}")
        self._version_combo.blockSignals(False)

    # ---------------------------------------------------------------- prediction

    def _run_prediction(self) -> None:
        model = self._model_combo.currentText()
        if not model:
            self.show_error("Select a trained model first.")
            return
        record = self._form.values()
        self._last_record = record
        version = self._version_combo.currentText() or None
        self.btn_predict.setEnabled(False)
        self.clear_banner()
        self.card_class.set_value("Working…")
        self.card_score.set_value("—")
        self.card_threshold.set_value("—")
        self.card_model.set_value(model)

        def work() -> PredictionOutcome:
            return self.service.predict(
                model, record, version=version, background_data=self._background_frame
            )

        def on_result(task_result: TaskResult) -> None:
            result = task_result.result
            self._last_outcome = result
            prediction = result.prediction
            self.card_class.set_value(str(prediction.predicted_class))
            self.card_score.set_value(
                f"{prediction.score:.4f}" if prediction.score is not None else "n/a"
            )
            self.card_threshold.set_value(f"{prediction.threshold:.2f}")
            self.card_model.set_value(
                f"{prediction.model_name} {prediction.model_version or ''}".strip()
            )
            warnings = prediction.out_of_distribution_warnings or []
            self._warnings.setText(
                "Out-of-distribution warnings: " + "; ".join(warnings)
                if warnings
                else "Input within observed domain."
            )
            self.btn_predict.setEnabled(True)
            self.btn_explain.setEnabled(True)
            if result.explanation_error:
                self.show_warning(f"Explanation unavailable: {result.explanation_error}")
            else:
                self.clear_banner()

        def on_error(message: str) -> None:
            self.show_error(message)
            self.btn_predict.setEnabled(True)

        self.run_task(
            "predict",
            work,
            started_message="Running inference…",
            on_result=on_result,
            on_error=on_error,
        )

    def _explain_last(self) -> None:
        if self._last_record is None or self._last_outcome is None:
            self.show_error("No prediction result to explain yet.")
            return
        window = self.window()
        pages = getattr(window, "_page_widgets", None) if window is not None else None
        if pages is None or "explain" not in pages:
            self.show_error("Explain page is not available.")
            return
        target = pages["explain"]
        if hasattr(target, "set_prediction_context"):
            target.set_prediction_context(self._last_record, self._last_outcome)
        window._navigate_to("explain")
