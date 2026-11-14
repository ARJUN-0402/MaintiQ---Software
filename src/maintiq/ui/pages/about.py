"""About / Project Limitations page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from maintiq import __academic_notice__, __description__, __title__, __version__
from maintiq.ui.pages.base import BasePage


class AboutPage(BasePage):
    """Project identity, academic purpose and limitation notice."""

    def __init__(self, service=None, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("About / Limitations")
        self.set_subtitle("MaintiQ — academic decision-support prototype.")

        self._content_layout.addWidget(QLabel(f"<b>{__title__}</b>"))
        self._content_layout.addWidget(QLabel(f"Version: {__version__}"))
        self._content_layout.addWidget(QLabel(__description__))

        notice = QLabel(__academic_notice__)
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #fde68a; font-size: 13px; padding: 10px;")
        self._content_layout.addWidget(notice)

        limitations = QLabel(
            "<b>Limitations:</b>"
            "<ul>"
            "<li>Trained only on the AI4I 2020 benchmark dataset; results do not guarantee real factory performance.</li>"
            "<li>SHAP explanations are unavailable when Windows Application Control blocks sklearn cluster extensions; LIME is used instead.</li>"
            "<li>Scores are model-estimated probabilities, not calibrated real-world failure risks.</li>"
            "<li>Explanations describe model behaviour; they are not causal diagnoses or maintenance instructions.</li>"
            "<li>The application does not connect to machinery, PLCs, SCADA, or MES systems.</li>"
            "<li>Qualified human review is required before any maintenance decision.</li>"
            "</ul>"
        )
        limitations.setWordWrap(True)
        limitations.setTextFormat(Qt.TextFormat.RichText)
        self._content_layout.addWidget(limitations)

        stack = QLabel(
            "<b>Technology:</b> Python, PySide6, scikit-learn, XGBoost, LIME, pandas, NumPy, matplotlib, joblib. "
            "Offline-capable after installation; no browser or network required for normal operation."
        )
        stack.setWordWrap(True)
        stack.setTextFormat(Qt.TextFormat.RichText)
        self._content_layout.addWidget(stack)

        self._content_layout.addStretch()
