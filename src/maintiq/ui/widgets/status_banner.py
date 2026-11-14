"""Status banner: dismissible info/warning/error/success message strip."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class StatusBanner(QFrame):
    """A non-modal status strip shown above page content."""

    def __init__(
        self, kind: str = "info", message: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statusBanner")
        self.setProperty("kind", kind)
        self._kind = kind

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._text = QLabel(message)
        self._text.setObjectName("statusBannerText")
        self._text.setWordWrap(True)
        layout.addWidget(self._text, 1)

        self._dismiss = QPushButton("Dismiss")
        self._dismiss.setObjectName("dismissButton")
        self._dismiss.setMaximumWidth(80)
        self._dismiss.clicked.connect(self.hide)
        layout.addWidget(self._dismiss)

        self._apply_style()

    def _apply_style(self) -> None:
        backgrounds = {
            "info": "#164e63",
            "warning": "#7c2d12",
            "error": "#7f1d1d",
            "success": "#14532d",
        }
        borders = {
            "info": "#2dd4bf",
            "warning": "#fb923c",
            "error": "#fca5a5",
            "success": "#4ade80",
        }
        kind = self._kind
        self.setStyleSheet(
            f"""
            QFrame#statusBanner#{kind} {{
                background-color: {backgrounds[kind]};
                border: 1px solid {borders[kind]};
                border-radius: 6px;
                color: inherit;
            }}
            QLabel#statusBannerText {{ color: inherit; font-size: 12px; }}
            """
        )
        self.style().unpolish(self)
        self.style().polish(self)

    def set_message(self, kind: str, message: str) -> None:
        self._kind = kind
        self._text.setText(message)
        self.setProperty("kind", kind)
        self._apply_style()
        self.show()

    def clear(self) -> None:
        self._text.setText("")
        self.hide()
