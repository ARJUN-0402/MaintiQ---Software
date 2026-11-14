"""Tests for application configuration and path resolution."""

from maintiq.config import AppConfig


def test_config_resolves_configured_paths():
    """Configuration resolves all configured paths as Path objects."""
    config = AppConfig()
    paths = config.paths

    assert isinstance(paths.project_root, __import__("pathlib").Path)
    assert paths.package_dir.name == "maintiq"
    assert paths.assets_dir.name == "assets"
    assert paths.datasets_dir.name == "datasets"
    assert paths.icons_dir.name == "icons"
    assert paths.docs_dir.name == "docs"
    assert paths.scripts_dir.name == "scripts"
    assert paths.packaging_dir.name == "packaging"
    assert paths.config_dir.name == "config"
    assert paths.tests_dir.name == "tests"


def test_user_data_paths_are_writable_location():
    """User-data directories are distinct from the install/source tree."""
    config = AppConfig()
    assert config.paths.app_data_dir != config.paths.project_root
    assert str(config.paths.app_data_dir).endswith("MaintiQ") or ".maintiq" in str(
        config.paths.app_data_dir
    )
    for attr in (
        "user_datasets_dir",
        "model_dir",
        "registry_dir",
        "logs_dir",
        "reports_dir",
        "settings_dir",
    ):
        assert getattr(config.paths, attr).is_relative_to(config.paths.app_data_dir)


def test_config_defaults():
    """Configuration defaults match the project specification."""
    config = AppConfig()
    assert config.title == "MaintiQ"
    assert config.version == "0.2.0"
    assert config.random_seed == 42
    assert config.default_threshold == 0.5
    assert "xgboost" in config.supported_models
    assert "logistic_regression" in config.supported_models
    assert config.target_column == "Machine failure"
