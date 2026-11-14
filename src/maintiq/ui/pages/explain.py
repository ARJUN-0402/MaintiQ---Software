"""Explain Prediction page: global importance and local contributions."""

from __future__ import annotations

from typing import Any, ClassVar

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton

from maintiq.ml.explainability import ExplanationResult, explain_local
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.table_view import TableView


class ExplainPage(BasePage):
    """Global and local explanations for the last prediction."""

    COLUMNS: ClassVar[list[str]] = ["feature", "label", "contribution", "abs_contribution"]

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Explain Prediction")
        self.set_subtitle("Model-behaviour interpretations, not causal diagnoses.")

        select_row = QHBoxLayout()
        self._method_combo = QComboBox()
        self._method_combo.addItems(["auto", "lime", "shap"])
        self._method_combo.setToolTip(
            "Explanation backend. SHAP is unavailable when its native extension is blocked."
        )
        self.btn_explain = QPushButton("Explain selected record")
        self.btn_explain.setObjectName("primary")
        select_row.addWidget(QLabel("Backend:"))
        select_row.addWidget(self._method_combo)
        select_row.addWidget(self.btn_explain)
        select_row.addStretch()
        self._content_layout.addLayout(select_row)

        self._local_table = TableView(self.COLUMNS)
        self._content_layout.addWidget(QLabel("Local contributions (this record)"))
        self._content_layout.addWidget(self._local_table)

        self._global_table = TableView(["feature", "label", "importance"])
        self._content_layout.addWidget(
            QLabel("Global feature importance (SHAP mean |contribution|)")
        )
        self._content_layout.addWidget(self._global_table)

        self._meta = QLabel()
        self._meta.setWordWrap(True)
        self._meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._content_layout.addWidget(self._meta)

        self._disclaimer = QLabel(
            "Explanation reflects how the model used input features for this prediction. "
            "It is not a causal diagnosis or a maintenance instruction."
        )
        self._disclaimer.setWordWrap(True)
        self._disclaimer.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self._content_layout.addWidget(self._disclaimer)

        self._content_layout.addStretch()

        self.btn_explain.clicked.connect(self._run_explanation)

        self._record: dict[str, Any] | None = None
        self._outcome = None
        self._background_frame = None

    # ---------------------------------------------------------------- context

    def set_prediction_context(self, record: dict[str, Any], outcome) -> None:
        self._record = record
        self._outcome = outcome
        if outcome is not None and outcome.explanation is not None:
            self._render_local(outcome.explanation)
            score = outcome.explanation.score
            score_text = f"{score:.4f}" if score is not None else "n/a"
            self._meta.setText(
                f"Method: {outcome.explanation.method} | model: {outcome.explanation.model_name} "
                f"{outcome.explanation.model_version or ''} | "
                f"predicted class: {outcome.explanation.predicted_class} | score: {score_text}"
            )
        else:
            self._local_table.set_rows([])
            self._meta.setText("Run an explanation to see local contributions.")

    def on_shown(self) -> None:
        try:
            self._background_frame = self.service.active_frame
        except Exception:
            self._background_frame = None
        if self._background_frame is None:
            self.show_info("Import a dataset to enable background sampling for explanations.")

    # ---------------------------------------------------------------- explanation

    def _run_explanation(self) -> None:
        if self._record is None:
            self.show_error("No prediction record available. Make a prediction first.")
            return
        if self._background_frame is None:
            self.show_error("Import a dataset to use as explanation background data.")
            return
        method = self._method_combo.currentText()
        self.btn_explain.setEnabled(False)
        self.clear_banner()
        self._local_table.set_rows([])

        def work() -> ExplanationResult:
            pipeline = self.service.prediction_service.load_model(
                self._outcome.prediction.model_name,
                version=self._outcome.prediction.model_version,
            )
            return explain_local(
                pipeline,
                self._record,
                method=method,
                background_data=self._background_frame,
                training_data=self._background_frame,
            )

        def on_result(task_result: TaskResult) -> None:
            result = task_result.result
            self._render_local(result)
            score = result.score
            score_text = f"{score:.4f}" if score is not None else "n/a"
            self._meta.setText(
                f"Method: {result.method} | model: {result.model_name} "
                f"{result.model_version or ''} | predicted class: {result.predicted_class} | "
                f"score: {score_text}"
            )
            self.btn_explain.setEnabled(True)

        def on_error(message: str) -> None:
            self.show_error(message)
            self.btn_explain.setEnabled(True)

        self.run_task(
            "explain",
            work,
            started_message="Computing explanation…",
            on_result=on_result,
            on_error=on_error,
        )

    def _render_local(self, result: ExplanationResult) -> None:
        rows = [
            {
                "feature": item.get("feature", ""),
                "label": item.get("label", ""),
                "contribution": f"{item.get('contribution', 0.0):+.4f}",
                "abs_contribution": f"{item.get('abs_contribution', 0.0):.4f}",
            }
            for item in (result.contributions or [])[:15]
        ]
        self._local_table.set_rows(rows)

        global_rows = [
            {
                "feature": item.get("feature", ""),
                "label": item.get("label", ""),
                "importance": f"{item.get('importance', 0.0):.4f}",
            }
            for item in (result.global_importance or [])[:15]
        ]
        self._global_table.set_rows(global_rows)
