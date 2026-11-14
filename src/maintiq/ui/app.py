"""Application bootstrap: QApplication creation, styling, and main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from maintiq import __version__
from maintiq.config import APP_TITLE, get_config
from maintiq.services import ApplicationService
from maintiq.ui.main_window import MainWindow
from maintiq.ui.styles import APP_STYLESHEET


def _build_fallback_icon() -> QIcon:
    """Draw a simple application icon so the window is never icon-less."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#0ea5e9"))
    painter.setPen(QPen(QColor("#0369a1"), 2))
    painter.drawRoundedRect(4, 4, 56, 56, 10, 10)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    return QIcon(pixmap)


def _application_icon() -> QIcon:
    icon_path = Path(get_config().paths.assets_dir) / "icons" / "app.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return _build_fallback_icon()


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication (offscreen-safe for headless runs)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or [])
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MaintiQ Project")
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(_application_icon())
    app.setStyleSheet(APP_STYLESHEET)
    return app


def run(argv: list[str] | None = None, service: ApplicationService | None = None) -> int:
    """Launch the native desktop application and run its event loop.

    ``service`` may be injected (for example a stubbed service in tests or
    embedding scenarios); otherwise a live :class:`ApplicationService` is used.
    """
    app = create_application(argv)
    if service is None:
        service = ApplicationService()
    window = MainWindow(service)
    window.show()
    return app.exec()


def main() -> int:
    """Console-script entry point for the desktop application."""
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
