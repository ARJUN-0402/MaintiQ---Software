"""Tests for writable runtime directory creation."""

import maintiq.config as config_module
from maintiq.config import get_config


def test_runtime_directories_can_be_created_safely(tmp_path, monkeypatch):
    """Writable runtime directories are created under the app-data directory."""
    # Point the user-data directory at a temporary location.
    fake_app_data = tmp_path / "AppData" / "Local" / "MaintiQ"
    monkeypatch.setattr(config_module, "_user_data_dir", lambda: fake_app_data)

    config = get_config()
    created = config.ensure_runtime_directories()

    expected = [
        config.paths.app_data_dir,
        config.paths.user_datasets_dir,
        config.paths.model_dir,
        config.paths.registry_dir,
        config.paths.logs_dir,
        config.paths.reports_dir,
        config.paths.settings_dir,
    ]
    assert created == expected
    for directory in expected:
        assert directory.is_dir()
    # App-data dir is not inside the source/install tree.
    assert not fake_app_data.is_relative_to(config.paths.project_root)
