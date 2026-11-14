"""Dashboard page: application status and quick actions."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton

from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.widgets.metric_card import MetricCard


class DashboardPage(BasePage):
    """High-level status summary with quick navigation actions."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Dashboard")
        self.set_subtitle("System status, data and model availability at a glance.")

        cards = QGridLayout()
        cards.setSpacing(10)

        self.card_dataset = MetricCard("Dataset", "Not loaded")
        self.card_models = MetricCard("Registered models", "0")
        self.card_selected = MetricCard("Selected model", "None")
        self.card_last = MetricCard("Last training", "None")

        for index, card in enumerate(
            (self.card_dataset, self.card_models, self.card_selected, self.card_last)
        ):
            cards.addWidget(card, 0, index)

        self._content_layout.addLayout(cards)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_import = QPushButton("Import dataset")
        self.btn_import.setObjectName("primary")
        self.btn_train = QPushButton("Train a model")
        self.btn_predict = QPushButton("Predict failure")
        self.btn_reports = QPushButton("Reports")
        for button in (self.btn_import, self.btn_train, self.btn_predict, self.btn_reports):
            actions.addWidget(button)
        actions.addStretch()
        self._content_layout.addLayout(actions)

        self._content_layout.addStretch()

    def on_shown(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            frame = self.service.active_frame
            self.card_dataset.set_value("Loaded" if frame is not None else "Not loaded")
            if frame is not None:
                self.card_dataset.set_value(f"Loaded ({len(frame)} rows)")

            models = self.service.list_models()
            self.card_models.set_value(str(len(models)))
        except Exception as exc:  # dashboard must not crash on service issues
            self.card_dataset.set_value("Error")
            self.card_models.set_value("Error")
            self.show_error(f"Could not read status: {exc}")
