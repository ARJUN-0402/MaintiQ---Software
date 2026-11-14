"""Base page: common behaviour for all MaintiQ page widgets.

Pages are thin presentation layers. They hold a reference to the application
service, submit long-running work through a shared task runner, and render
results through widgets and status banners. Pages never contain model-training
logic themselves; training is orchestrated by the application service.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from maintiq.services import ApplicationService
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.status_banner import StatusBanner
from maintiq.ui.worker import TaskRunner


class BasePage(QWidget):
    """Base class for MaintiQ pages."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._runner = TaskRunner()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(12)

        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        self._layout.addWidget(self._title)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("pageSubtitle")
        self._layout.addWidget(self._subtitle)

        self._banner = StatusBanner(kind="info", message="")
        self._banner.clear()
        self._layout.addWidget(self._banner)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._layout.addWidget(self._content, 1)

        self._empty = QLabel("No data available.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #64748b; font-size: 14px; padding: 40px;")
        self._empty.hide()
        self._content_layout.addWidget(self._empty)

    # ---------------------------------------------------------------- helpers

    @property
    def service(self) -> ApplicationService:
        return self._service

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_subtitle(self, text: str) -> None:
        self._subtitle.setText(text)

    def show_info(self, message: str) -> None:
        self._banner.set_message("info", message)

    def show_warning(self, message: str) -> None:
        self._banner.set_message("warning", message)

    def show_error(self, message: str) -> None:
        self._banner.set_message("error", message)

    def show_success(self, message: str) -> None:
        self._banner.set_message("success", message)

    def clear_banner(self) -> None:
        self._banner.clear()

    def show_empty(self, message: str = "No data available.") -> None:
        self._empty.setText(message)
        self._empty.show()

    def hide_empty(self) -> None:
        self._empty.hide()

    def add_content(self, widget) -> None:
        self._content_layout.addWidget(widget)

    def run_task(
        self,
        task_id: str,
        fn,
        *,
        started_message: str | None = None,
        on_result: Callable[[TaskResult], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> str:
        """Submit ``fn`` to the background thread pool.

        Convenience wrapper around :class:`maintiq.ui.worker.TaskRunner` that
        also toggles the empty-state visibility and shows started/finished
        messages when provided.
        """

        def on_started(_task_id: str) -> None:
            self.hide_empty()
            if started_message:
                self.show_info(started_message)

        def on_done(task_id: str) -> None:
            if on_finished is not None:
                on_finished()

        return self._runner.submit(
            fn,
            task_id=task_id,
            on_started=on_started,
            on_result=on_result,
            on_error=on_error or (lambda message: self.show_error(message)),
            on_finished=on_done,
        )

    def on_shown(self) -> None:
        """Optional hook called when the page becomes visible."""
