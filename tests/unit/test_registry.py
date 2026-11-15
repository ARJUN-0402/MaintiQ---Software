"""Tests for the local JSON-based ModelRegistry."""

from __future__ import annotations

import json
from pathlib import Path, PurePath
import sys
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import (
    ModelHashMismatchError,
    RegistryError,
    ReportError,
)
from maintiq.ml.training import ModelRegistry, ModelTrainer
from maintiq.ml.training.registry import (
    SCHEMA_VERSION,
    _active_store_package_identity,
    _resolve_under_root,
    _store_package_from_path,
    _strip_windows_store_virtualization,
)
from maintiq.reporting.service import _validate_output_path


def _write_joblib(path, payload=None):
    if payload is None:
        payload = {"dummy": "artefact"}
    joblib.dump(payload, str(path))
    return path


def _make_registry(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path = model_dir / "registry.json"
    return ModelRegistry(registry_path=registry_path, model_dir=model_dir), model_dir


def _make_artifact(model_dir, name="model.joblib"):
    path = model_dir / name
    _write_joblib(path)
    return path


# --------------------------------------------------------------------------- empty state


def test_missing_registry_file_creates_empty_state(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    assert not registry.registry_path.exists()
    assert registry.list_models() == []
    assert registry.count_models() == 0
    assert registry.count_records() == 0


# --------------------------------------------------------------------------- registration / versioning


def test_registration_and_version_increment(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    v1 = registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert v1 == "v1"

    v2 = registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert v2 == "v2"

    assert registry.list_versions("logistic_regression") == ["v1", "v2"]
    assert registry.count_records() == 2


def test_version_increment_across_different_models(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    art_a = _make_artifact(model_dir, "a.joblib")
    art_b = _make_artifact(model_dir, "b.joblib")

    registry.register(model_name="a", artifact_path=art_a, metrics={}, parameters={})
    registry.register(model_name="b", artifact_path=art_b, metrics={}, parameters={})
    registry.register(model_name="a", artifact_path=art_a, metrics={}, parameters={})

    assert registry.list_versions("a") == ["v1", "v2"]
    assert registry.list_versions("b") == ["v1"]


# --------------------------------------------------------------------------- persistence / reload


def test_persistence_across_reload(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = _make_artifact(model_dir)

    registry = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    registry.register(
        model_name="random_forest",
        artifact_path=artifact,
        metrics={"accuracy": 0.85},
        parameters={"n_estimators": 100},
        random_seed=42,
    )

    reloaded = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    assert reloaded.list_models() == ["random_forest"]
    assert reloaded.list_versions("random_forest") == ["v1"]
    latest = reloaded.get_latest("random_forest")
    assert latest["version"] == "v1"
    assert latest["metrics"]["accuracy"] == 0.85


def test_reload_replaces_in_memory_state(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="xgboost",
        artifact_path=artifact,
        metrics={"accuracy": 0.8},
        parameters={"n_estimators": 100},
        random_seed=42,
    )
    registry.register(
        model_name="xgboost",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"n_estimators": 200},
        random_seed=42,
    )
    assert registry.count_records() == 2

    registry.reload()
    assert registry.count_records() == 2
    assert registry.list_versions("xgboost") == ["v1", "v2"]


# --------------------------------------------------------------------------- list / get / latest / exists / count


def test_list_get_latest_exists_count(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    assert registry.model_exists("logistic_regression") is False
    assert registry.version_exists("logistic_regression", "v1") is False

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    assert registry.model_exists("logistic_regression") is True
    assert registry.version_exists("logistic_regression", "v1") is True
    assert registry.version_exists("logistic_regression", "v9") is False
    assert registry.count_models() == 1
    assert registry.count_records() == 1

    record = registry.get_version("logistic_regression", "v1")
    assert record["version"] == "v1"
    assert record["model_name"] == "logistic_regression"
    assert record["record_id"] == "logistic_regression-v1"

    latest = registry.get_latest("logistic_regression")
    assert latest["version"] == "v1"

    with pytest.raises(RegistryError):
        registry.get_version("logistic_regression", "v9")

    with pytest.raises(RegistryError):
        registry.get_latest("nonexistent")


def test_get_version_returns_defensive_copy(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    record = registry.get_version("logistic_regression", "v1")
    record["metrics"]["accuracy"] = 999.0  # mutate the copy

    original = registry.get_version("logistic_regression", "v1")
    assert original["metrics"]["accuracy"] == 0.9


# --------------------------------------------------------------------------- malformed JSON / schema / records


def test_malformed_json_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_unsupported_schema_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"schema_version": "9.9", "models": {}}), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_missing_schema_version_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"models": {}}), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


def test_invalid_record_shape_raises(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "models": {
            "logistic_regression": {
                "display_name": "Logistic Regression",
                "versions": [{"version": "v1"}],  # missing required fields
            }
        },
    }
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RegistryError):
        ModelRegistry(registry_path=registry_path, model_dir=model_dir)


# --------------------------------------------------------------------------- missing artifact


def test_register_missing_artifact_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    missing = model_dir / "does_not_exist.joblib"

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=missing,
            metrics={},
            parameters={},
        )


# --------------------------------------------------------------------------- path safety


def test_path_traversal_rejected(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    # A relative path containing ".." escapes the model directory.
    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path="../escape.joblib",
            metrics={},
            parameters={},
        )


def test_outside_directory_absolute_path_rejected(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    outside = tmp_path / "outside" / "escape.joblib"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(outside)

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=outside,
            metrics={},
            parameters={},
        )


def test_valid_artifact_under_model_dir_accepted(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = model_dir / "valid_model.joblib"
    _write_joblib(artifact)

    version = registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert version == "v1"
    record = registry.get_version("logistic_regression", "v1")
    assert record["artifact_path"] == "valid_model.joblib"


def test_symlink_escape_rejected(tmp_path, monkeypatch):
    registry, model_dir = _make_registry(tmp_path)
    # Create a symlink outside the model directory pointing to a fake artefact.
    escape_target = tmp_path / "escape" / "escape.joblib"
    escape_target.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(escape_target)
    symlink_path = model_dir / "symlink.joblib"
    try:
        symlink_path.symlink_to(escape_target)
    except OSError:
        pytest.skip("Symlink creation requires developer mode or administrator privileges")

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=symlink_path,
            metrics={},
            parameters={},
        )


def test_double_traversal_rejected(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    # Multiple levels of ".." traversal.
    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path="../../../escape.joblib",
            metrics={},
            parameters={},
        )


def test_resolve_under_root_direct(tmp_path):
    """Direct unit test of _resolve_under_root with valid and invalid paths."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Valid: direct child of model_dir.
    artifact = model_dir / "model.joblib"
    _write_joblib(artifact)
    resolved, relative = _resolve_under_root(model_dir, artifact)
    assert resolved == artifact.resolve()
    assert str(relative) == str(PurePath("model.joblib"))

    # Valid: relative path under model_dir.
    _, relative2 = _resolve_under_root(model_dir, "subdir/model.joblib")
    assert str(relative2) == str(PurePath("subdir/model.joblib"))

    # Invalid: path traversal via "..".
    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, "../escape.joblib")

    # Invalid: absolute path outside model_dir.
    outside = tmp_path / "outside" / "escape.joblib"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(outside)
    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, outside)


# --------------------------------------------------------------------------- Windows Store path virtualization security


def _active_package_identity() -> str | None:
    """Return the active Windows Store package identity, or None if not Store Python."""
    return _active_store_package_identity()


def _make_virtualized_path(localappdata: Path, package_identity: str, *segments: str) -> Path:
    """Build a Windows Store virtualized path: {LOCALAPPDATA}\\Packages\\{pkg}\\LocalCache\\Local\\{rest}."""
    return localappdata / "Packages" / package_identity / "LocalCache" / "Local" / Path(*segments)


def test_active_package_identity_is_non_empty_when_store_python():
    """When running under Windows Store Python, the package identity is discoverable."""
    identity = _active_package_identity()
    if identity is None:
        pytest.skip("Not running under Windows Store Python")
    assert isinstance(identity, str)
    assert len(identity) > 0


def test_strip_virtualization_legitimate_windows_store_path(monkeypatch, tmp_path):
    """A legitimate Windows Store virtualized MaintiQ path is normalized correctly."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    virtualized = _make_virtualized_path(
        localappdata, package_identity, "MaintiQ", "models", "model.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)

    expected = localappdata / "MaintiQ" / "models" / "model.joblib"
    assert stripped == expected


def test_strip_virtualization_fake_package_rejected(monkeypatch, tmp_path):
    """A path with a fake package identity is NOT stripped — mandatory adversarial case."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    # Mandatory adversarial case: fake package mapped into trusted model directory
    adversarial = _make_virtualized_path(
        localappdata, "FakePackage", "MaintiQ", "models", "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)

    # Must NOT be stripped — package identity doesn't match active interpreter
    assert stripped == adversarial


def test_strip_virtualization_unrelated_package_rejected(monkeypatch, tmp_path):
    """A path with another real-looking but unrelated package identity is not stripped."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    unrelated = "Microsoft.WindowsStore_8wekyb3d8bbwe"
    if unrelated == package_identity:
        unrelated = "Some.Other.Package_abc123"

    virtualized = _make_virtualized_path(
        localappdata, unrelated, "MaintiQ", "models", "model.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)

    assert stripped == virtualized


def test_strip_virtualization_packages_under_maintiq_rejected(monkeypatch, tmp_path):
    """Packages appearing under MaintiQ (not directly under LOCALAPPDATA) is not stripped."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    adversarial = (
        localappdata
        / "MaintiQ"
        / "Packages"
        / package_identity
        / "LocalCache"
        / "Local"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)

    assert stripped == adversarial


def test_strip_virtualization_extra_segment_before_localcache_rejected(monkeypatch, tmp_path):
    """Extra segment between package identity and LocalCache is not stripped."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    virtualized = (
        localappdata
        / "Packages"
        / package_identity
        / "ExtraSegment"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "file.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)

    assert stripped == virtualized


def test_strip_virtualization_missing_local_segment_rejected(monkeypatch, tmp_path):
    """Missing duplicated Local segment after LocalCache means no stripping."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    virtualized = (
        localappdata
        / "Packages"
        / package_identity
        / "LocalCache"
        / "MaintiQ"
        / "models"
        / "file.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)

    assert stripped == virtualized


def test_strip_virtualization_nonexistent_adversarial_rejected(monkeypatch, tmp_path):
    """Structurally valid virtualized path is stripped even if it doesn't exist;
    containment check still rejects paths outside the trusted root."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    # Path doesn't exist on disk but matches the valid structure — it IS stripped.
    adversarial = _make_virtualized_path(
        localappdata, package_identity, "nonexistent", "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)

    expected = localappdata / "nonexistent" / "outside.joblib"
    assert stripped == expected

    # But a path outside the trusted model directory is still rejected by _resolve_under_root.
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, adversarial)


def test_strip_virtualization_multiple_segments_rejected(monkeypatch, tmp_path):
    """Multiple virtualization-like segments are not stripped unless first is active package."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    # First segment is a fake package — should not strip anything
    virtualized = (
        localappdata
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "Packages"
        / package_identity
        / "LocalCache"
        / "Local"
        / "file.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)

    assert stripped == virtualized


def test_resolve_under_root_legitimate_virtualized_path(monkeypatch, tmp_path):
    """Legitimate Windows Store virtualized path inside model directory is accepted."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    model_dir = localappdata / "MaintiQ" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = model_dir / "model.joblib"
    _write_joblib(artifact)

    # Virtualized path: {LOCALAPPDATA}\\Packages\\{pkg}\\LocalCache\\Local\\MaintiQ\\models\\model.joblib
    virtualized = _make_virtualized_path(
        localappdata, package_identity, "MaintiQ", "models", "model.joblib"
    )

    resolved, relative = _resolve_under_root(model_dir, virtualized)
    assert resolved == artifact.resolve()
    assert str(relative) == str(PurePath("model.joblib"))


def test_resolve_under_root_adversarial_virtualized_path(monkeypatch, tmp_path):
    """Adversarial virtualized path with fake package escapes model directory — rejected."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Build: {LOCALAPPDATA}\\Packages\\FakePackage\\LocalCache\\Local\\models\\outside.joblib
    # where models is NOT under the trusted model_dir
    adversarial = _make_virtualized_path(localappdata, "FakePackage", "models", "outside.joblib")

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, adversarial)


def test_resolve_under_root_relative_traversal_still_rejected(tmp_path):
    """Relative ../ traversal remains rejected regardless of virtualization helper."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, "../escape.joblib")


def test_resolve_under_root_absolute_outside_still_rejected(tmp_path):
    """Absolute path outside model directory remains rejected."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside" / "escape.joblib"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(outside)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, outside)


def test_resolve_under_root_sibling_prefix_still_rejected(tmp_path):
    """Sibling directory with similar prefix remains rejected."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    sibling = tmp_path / "models2" / "escape.joblib"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(sibling)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, sibling)


# --------------------------------------------------------------------------- Fail-closed normalization tests


def test_strip_virtualization_no_identity_no_normalization(monkeypatch, tmp_path):
    """Fail-closed: when no verified identity exists, structural paths are not stripped."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    # Structurally valid virtualized path but no identity → must NOT be stripped.
    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial


def test_strip_virtualization_fake_package_with_identity(monkeypatch, tmp_path):
    """Fake package identity is rejected even when an identity is known."""
    monkeypatch.setattr(
        "maintiq.ml.training.registry._active_store_package_identity", lambda: "Real.Package_abc123"
    )
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial


def test_strip_virtualization_incorrect_localcache_position_rejected(monkeypatch, tmp_path):
    """Packages followed by wrong segment (not LocalCache) is not stripped."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    virtualized = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / package_identity
        / "WrongSegment"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "file.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)
    assert stripped == virtualized


def test_strip_virtualization_missing_local_segment_rejected_fail_closed(monkeypatch, tmp_path):
    """Missing Local segment after LocalCache means no stripping (fail-closed)."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    virtualized = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / package_identity
        / "LocalCache"
        / "MaintiQ"
        / "models"
        / "file.joblib"
    )
    stripped = _strip_windows_store_virtualization(virtualized)
    assert stripped == virtualized


def test_resolve_under_root_nonexistent_adversarial_rejected_fail_closed(monkeypatch, tmp_path):
    """Nonexistent adversarial virtualized path is rejected when identity unavailable."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Structurally valid virtualized path but no identity → not stripped →
    # containment check rejects because it's outside model_dir.
    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "models"
        / "outside.joblib"
    )

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, adversarial)


# --------------------------------------------------------------------------- Reporting service path validation


def test_reporting_output_path_virtualization_rejected(tmp_path):
    """Reporting output path cannot exploit virtualization normalization."""
    output_dir = tmp_path / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output path outside reports dir — must be rejected
    outside = tmp_path / "models" / "report.json"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("{}")

    with pytest.raises(ReportError):
        _validate_output_path(output_dir, outside)


def test_reporting_output_path_fake_package_virtualized_rejected(monkeypatch, tmp_path):
    """Reporting output path with fake package virtualization is rejected."""
    package_identity = _active_package_identity()
    if package_identity is None:
        pytest.skip("Not running under Windows Store Python")

    localappdata = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(localappdata))

    output_dir = localappdata / "MaintiQ" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Virtualized path with fake package: {LOCALAPPDATA}\\Packages\\FakePackage\\LocalCache\\Local\\MaintiQ\\reports\\report.json
    virtualized_outside = _make_virtualized_path(
        localappdata, "FakePackage", "MaintiQ", "reports", "report.json"
    )

    with pytest.raises(ReportError):
        _validate_output_path(output_dir, virtualized_outside)


# --------------------------------------------------------------------------- hash verification


def test_artifact_hash_verification_on_load(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir, "hashed.joblib")

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    loaded = registry.load_artifact("logistic_regression", "v1", trusted=True)
    assert loaded == {"dummy": "artefact"}


def test_hash_mismatch_after_artifact_modification(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir, "mutable.joblib")

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )

    # Modify the artefact after registration so the stored hash no longer matches.
    artifact.write_text("tampered", encoding="utf-8")

    with pytest.raises(ModelHashMismatchError):
        registry.load_artifact("logistic_regression", "v1", trusted=True)


# --------------------------------------------------------------------------- JSON-safe serialization


def test_json_safe_metric_serialization(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    metrics = {
        "accuracy": np.float64(0.9),
        "precision": np.float64(0.85),
        "count": np.int64(5),
        "flag": np.bool_(True),
        "nested": {"inner": np.float64(0.5)},
    }

    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics=metrics,
        parameters={"random_state": np.int32(42)},
        random_seed=42,
    )

    record = registry.get_version("logistic_regression", "v1")
    assert record["metrics"]["accuracy"] == 0.9
    assert record["metrics"]["precision"] == 0.85
    assert record["metrics"]["count"] == 5
    assert record["metrics"]["flag"] is True
    assert record["metrics"]["nested"]["inner"] == 0.5
    assert isinstance(record["metrics"]["accuracy"], float)
    assert isinstance(record["metrics"]["count"], int)
    assert isinstance(record["parameters"]["random_state"], int)


def test_unsupported_json_value_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)

    with pytest.raises(RegistryError):
        registry.register(
            model_name="logistic_regression",
            artifact_path=artifact,
            metrics={"accuracy": 0.9},
            parameters={"callable_obj": len},  # arbitrary object, not JSON-safe
            random_seed=42,
        )


# --------------------------------------------------------------------------- atomic write safety


def test_atomic_write_failure_does_not_corrupt_previous_registry(tmp_path):
    registry_path = tmp_path / "models" / "registry.json"
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = _make_artifact(model_dir)

    registry = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        parameters={"max_iter": 2000},
        random_seed=42,
    )
    assert registry.count_records() == 1

    # Force the atomic write to fail on the next registration.
    with patch.object(registry, "_persist", side_effect=OSError("disk full")):
        with pytest.raises(OSError):
            registry.register(
                model_name="random_forest",
                artifact_path=artifact,
                metrics={"accuracy": 0.8},
                parameters={"n_estimators": 100},
                random_seed=42,
            )

    # Previous state must be intact on disk.
    recovered = ModelRegistry(registry_path=registry_path, model_dir=model_dir)
    assert recovered.count_records() == 1
    assert recovered.list_models() == ["logistic_regression"]


# --------------------------------------------------------------------------- trainer integration


def test_trainer_registers_model(tmp_path):
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=60),
            "air_temperature_k": rng.uniform(290, 310, size=60),
            "process_temperature_k": rng.uniform(295, 315, size=60),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=60),
            "torque_nm": rng.uniform(30, 60, size=60),
            "tool_wear_min": rng.uniform(0, 200, size=60),
        }
    )
    target = pd.Series((rng.random(60) < 0.3).astype(int), name="machine_failure")

    registry, model_dir = _make_registry(tmp_path)

    trainer = ModelTrainer(registry=registry, random_seed=42, test_size=0.25)
    trainer.model_dir = model_dir
    result = trainer.train_model(
        model_name="random_forest",
        frame=frame,
        target=target,
    )

    assert result.cancelled is False
    assert result.model_version == "v1"
    assert result.artifact_path is not None
    assert registry.model_exists("random_forest")
    assert registry.version_exists("random_forest", "v1")

    latest = registry.get_latest("random_forest")
    assert latest["metrics"]["accuracy"] == result.metrics.accuracy
    assert latest["feature_columns"] is not None
    assert latest["library_versions"] is not None
    assert latest["dataset_fingerprint"] is not None


def test_trainer_registry_failure_reported(tmp_path):
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=60),
            "air_temperature_k": rng.uniform(290, 310, size=60),
            "process_temperature_k": rng.uniform(295, 315, size=60),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=60),
            "torque_nm": rng.uniform(30, 60, size=60),
            "tool_wear_min": rng.uniform(0, 200, size=60),
        }
    )
    target = pd.Series((rng.random(60) < 0.3).astype(int), name="machine_failure")

    registry, model_dir = _make_registry(tmp_path)

    trainer = ModelTrainer(registry=registry, random_seed=42, test_size=0.25)
    trainer.model_dir = model_dir

    # Make registry.register raise so integration failure is surfaced.
    with patch.object(registry, "register", side_effect=RegistryError("write failed")):
        with pytest.raises(RegistryError):
            trainer.train_model(
                model_name="random_forest",
                frame=frame,
                target=target,
            )


# --------------------------------------------------------------------------- deletion


def test_delete_version_removes_single_record(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        random_seed=42,
    )
    assert registry.list_versions("logistic_regression") == ["v1", "v2"]

    registry.delete_version("logistic_regression", "v1")
    assert registry.list_versions("logistic_regression") == ["v2"]
    assert registry.count_records() == 1
    assert registry.model_exists("logistic_regression")


def test_delete_version_last_record_removes_model(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    assert registry.list_versions("logistic_regression") == ["v1"]

    registry.delete_version("logistic_regression", "v1")
    assert registry.list_versions("logistic_regression") == []
    assert not registry.model_exists("logistic_regression")
    assert registry.count_models() == 0


def test_delete_version_missing_raises(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    with pytest.raises(RegistryError):
        registry.delete_version("logistic_regression", "v1")


def test_delete_version_unknown_model_raises(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    with pytest.raises(RegistryError):
        registry.delete_version("random_forest", "v1")


def test_delete_model_removes_all_versions(tmp_path):
    registry, model_dir = _make_registry(tmp_path)
    artifact = _make_artifact(model_dir)
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.9},
        random_seed=42,
    )
    registry.register(
        model_name="logistic_regression",
        artifact_path=artifact,
        metrics={"accuracy": 0.92},
        random_seed=42,
    )
    registry.register(
        model_name="random_forest",
        artifact_path=artifact,
        metrics={"accuracy": 0.88},
        random_seed=42,
    )
    assert registry.count_models() == 2
    assert registry.count_records() == 3

    removed = registry.delete_model("logistic_regression")
    assert removed == 2
    assert registry.list_models() == ["random_forest"]
    assert registry.count_models() == 1
    assert registry.count_records() == 1


def test_delete_model_missing_raises(tmp_path):
    registry, _model_dir = _make_registry(tmp_path)
    with pytest.raises(RegistryError):
        registry.delete_model("absent")


# --------------------------------------------------------------------------- Frozen-runtime fail-closed normalization


def test_frozen_runtime_no_identity_no_normalization(monkeypatch, tmp_path):
    """Frozen runtime without verified Store identity performs no normalization."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial


def test_frozen_runtime_build_provenance_not_normalized(monkeypatch, tmp_path):
    """Build interpreter from Store Python does not authorize normalization in frozen runtime."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    # Even if the build machine had Store Python, frozen runtime has sys.frozen=True
    # and no WindowsApps path in sys.executable/_base_executable/sys.base_prefix.
    # Identity must be None → no normalization.
    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial


def test_frozen_runtime_fake_package_rejected(monkeypatch, tmp_path):
    """Fake package candidate is unchanged and rejected by containment."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "FakePackage"
        / "LocalCache"
        / "Local"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, stripped)


def test_frozen_runtime_unrelated_package_rejected(monkeypatch, tmp_path):
    """Candidate under unrelated package directory is unchanged and rejected."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    adversarial = (
        tmp_path
        / "AppData"
        / "Local"
        / "Packages"
        / "Microsoft.WindowsStore_8wekyb3d8bbwe"
        / "LocalCache"
        / "Local"
        / "MaintiQ"
        / "models"
        / "outside.joblib"
    )
    stripped = _strip_windows_store_virtualization(adversarial)
    assert stripped == adversarial

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, stripped)


def test_frozen_runtime_normal_path_accepted(tmp_path):
    """Normal path inside trusted directory is accepted (no identity needed for containment)."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact = model_dir / "model.joblib"
    _write_joblib(artifact)

    resolved, relative = _resolve_under_root(model_dir, artifact)
    assert resolved == artifact.resolve()
    assert str(relative) == str(PurePath("model.joblib"))


def test_frozen_runtime_absolute_outside_rejected(tmp_path):
    """Absolute path outside model directory is rejected."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside" / "escape.joblib"
    outside.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(outside)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, outside)


def test_frozen_runtime_relative_traversal_rejected(tmp_path):
    """Relative traversal is rejected."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, "../escape.joblib")


def test_frozen_runtime_sibling_prefix_rejected(tmp_path):
    """Similar-prefix sibling directory is rejected."""
    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    sibling = tmp_path / "models2" / "escape.joblib"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    _write_joblib(sibling)

    with pytest.raises(RegistryError):
        _resolve_under_root(model_dir, sibling)


def test_frozen_runtime_reporting_output_path_rejected(monkeypatch, tmp_path):
    """Reporting output path with fake package virtualization is rejected when no identity."""
    monkeypatch.setattr("maintiq.ml.training.registry._active_store_package_identity", lambda: None)

    output_dir = tmp_path / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    outside = tmp_path / "models" / "report.json"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("{}")

    with pytest.raises(ReportError):
        _validate_output_path(output_dir, outside)


# --------------------------------------------------------------------------- Identity source validation


def test_active_store_package_identity_frozen_returns_none():
    """Frozen application returns None for package identity (no Windows Store provenance)."""
    if not getattr(sys, "frozen", False):
        pytest.skip("Not running in frozen context")

    assert _active_store_package_identity() is None


def test_identity_source_sys_executable_not_store():
    """sys.executable of frozen app does not contain WindowsApps."""
    if not getattr(sys, "frozen", False):
        pytest.skip("Not running in frozen context")

    assert _store_package_from_path(Path(sys.executable)) is None


def test_identity_source_sys_base_executable_not_store():
    """sys._base_executable of frozen app does not contain WindowsApps."""
    if not getattr(sys, "frozen", False):
        pytest.skip("Not running in frozen context")

    base_exe = getattr(sys, "_base_executable", None)
    if base_exe:
        assert _store_package_from_path(Path(base_exe)) is None


def test_identity_source_sys_base_prefix_not_store():
    """sys.base_prefix of frozen app does not contain WindowsApps."""
    if not getattr(sys, "frozen", False):
        pytest.skip("Not running in frozen context")

    assert _store_package_from_path(Path(sys.base_prefix)) is None
