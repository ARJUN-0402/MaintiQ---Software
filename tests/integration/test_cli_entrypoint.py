"""CLI entry-point integration tests.

Verifies that the ``maintiq`` console script / ``python -m maintiq`` entry
point resolves, imports cleanly, and can bootstrap a QApplication in offscreen
mode without launching a blocking event loop.
"""

from __future__ import annotations

import importlib
import os

import pytest

from maintiq.__main__ import main
import maintiq.ui.app as ui_app


@pytest.fixture(autouse=True)
def _offscreen():
    """Force Qt offscreen platform for any GUI bootstrap in this module."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    yield


def test_main_entry_point_resolves():
    """The console-script entry point ``maintiq = maintiq.__main__:main`` resolves."""
    module = importlib.import_module("maintiq.__main__")
    assert callable(module.main)
    assert callable(ui_app.run)


def test_main_returns_zero_with_stubbed_run():
    """main() returns 0 when the event-loop run is stubbed (no blocking)."""
    real_run = ui_app.run
    try:
        ui_app.run = lambda argv=None, service=None: 0
        assert main() == 0
    finally:
        ui_app.run = real_run


def test_create_application_offscreen_does_not_crash():
    """create_application() builds a QApplication in offscreen mode headlessly."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = ui_app.create_application([])
    assert app is not None
    assert app.applicationName() == "MaintiQ"
