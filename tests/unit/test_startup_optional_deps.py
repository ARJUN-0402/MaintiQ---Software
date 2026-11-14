"""Tests for desktop/startup import safety under optional dependency failures."""

import importlib
import os
from pathlib import Path
import subprocess
import sys
import time


def test_module_entrypoint_starts():
    """`python -m maintiq` launches the GUI without requiring blocked optional ML deps."""
    root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    proc = subprocess.Popen(
        [sys.executable, "-m", "maintiq"],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(4)
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise AssertionError(f"GUI exited immediately: stdout={stdout} stderr={stderr}")
    finally:
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        assert "Traceback" not in (stderr or ""), stderr


def test_import_ml_package_does_not_import_shap(monkeypatch):
    """Importing maintiq.ml must not eagerly import shap/lime explainers."""
    real_import = __import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "shap" or name.startswith("shap."):
            raise AssertionError("maintiq.ml must not eagerly import shap")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded)
    # Reloading is safest to detect eager imports; keep scope local.
    import maintiq.ml  # noqa: PLC0415

    importlib.reload(maintiq.ml)
