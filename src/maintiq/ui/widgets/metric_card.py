"""Metric card: a large value with a small label, used on the dashboard."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """A styled card displaying one headline metric value."""

    def __init__(self, label: str, value: str = "--", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setObjectName("cardLabel")
        self._value = QLabel(value)
        self._value.setObjectName("cardValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def value(self) -> str:
        return self._value.text()

    def set_label(self, label: str) -> None:
        self._label.setText(label)
