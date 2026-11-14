"""Tests for optional explainability dependencies and startup safety.

These tests must not fabricate explanations. SHAP may be unavailable in locked-
down Windows environments (e.g. sklearn.cluster extensions blocked); the
application must report that clearly and continue.
"""

import pytest

from maintiq.core.exceptions import ExplanationError
from maintiq.ml.explainability import (
    explain_with_lime,
    explain_with_shap,
    explainability_status,
    lime_status,
    require_lime,
    require_shap,
    shap_status,
)


def test_import_maintiq_does_not_require_shap_or_cluster():
    """Application package import stays safe even if SHAP/cluster are blocked."""
    import importlib  # noqa: PLC0415

    module = importlib.import_module("maintiq")
    assert module.__title__ == "MaintiQ"


def test_explainability_status_reports_both_backends():
    status = explainability_status()
    assert set(status.keys()) == {"shap", "lime"}
    assert status["shap"].name == "shap"
    assert status["lime"].name == "lime"
    assert isinstance(status["shap"].available, bool)
    assert isinstance(status["lime"].available, bool)


def test_shap_unavailable_raises_clear_error(monkeypatch):
    from maintiq.ml import explainability  # noqa: PLC0415

    monkeypatch.setattr(
        explainability,
        "shap_status",
        lambda: explainability.DependencyStatus(
            name="shap", available=False, reason="ImportError: blocked"
        ),
    )
    with pytest.raises(ExplanationError) as exc:
        require_shap()
    assert "SHAP is unavailable" in str(exc.value)
    with pytest.raises(ExplanationError):
        explain_with_shap(object(), object())


def test_lime_unavailable_raises_clear_error(monkeypatch):
    from maintiq.ml import explainability  # noqa: PLC0415

    monkeypatch.setattr(
        explainability,
        "lime_status",
        lambda: explainability.DependencyStatus(
            name="lime", available=False, reason="ImportError: missing"
        ),
    )
    with pytest.raises(ExplanationError) as exc:
        require_lime()
    assert "LIME is unavailable" in str(exc.value)
    with pytest.raises(ExplanationError):
        explain_with_lime(object(), object())


def test_lime_status_probe_structure():
    status = lime_status()
    assert status.name == "lime"
    if not status.available:
        assert status.reason


def test_shap_status_probe_structure():
    status = shap_status()
    assert status.name == "shap"
    if not status.available:
        assert status.reason
