"""Pytest configuration for MaintiQ GUI smoke tests.

Qt is forced into offscreen mode so the native windowing tests run headlessly
on this Windows machine. A single QApplication lives for the whole session.
"""

from __future__ import annotations

from collections.abc import Generator
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QElapsedTimer, QThreadPool
from PySide6.QtWidgets import QApplication
import pytest


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """Session-scoped QApplication for offscreen GUI tests."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def process_until_idle(qapp: QApplication):
    """Return a callable that delivers queued Qt signals until idle."""

    def _run(timeout_ms: int = 5000) -> None:
        QThreadPool.globalInstance().waitForDone(timeout_ms)
        timer = QElapsedTimer()
        timer.start()
        while timer.elapsed() < timeout_ms:
            qapp.processEvents()
            time.sleep(0.01)
            if QThreadPool.globalInstance().activeThreadCount() == 0:
                break

    return _run
