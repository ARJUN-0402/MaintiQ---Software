"""Centralised typed configuration for MaintiQ.

All paths are expressed with ``pathlib.Path``. There are two classes of paths:

* *Installation paths* — the packaged application directory (read-only at runtime
  on a typical Windows install).
* *User-data paths* — writable per-user application data located under
  ``%LOCALAPPDATA%\\MaintiQ`` on Windows (or an equivalent user-writable location
  on other platforms). Datasets, models, registry, logs, settings and reports all
  live here so generated artefacts are never written into a protected install
  directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import sys

APP_TITLE = "MaintiQ"
APP_VERSION = "0.2.0"
RANDOM_SEED = 42
DEFAULT_THRESHOLD = 0.5

# Canonical model keys supported by the project.
SUPPORTED_MODELS = ("logistic_regression", "random_forest", "gradient_boosting", "xgboost")

# Default candidate model display names.
MODEL_DISPLAY_NAMES = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
    "xgboost": "XGBoost",
}

# AI4I 2020 dataset expectations.
DATASET_FILENAME = "ai4i_2020_predictive_maintenance.csv"
TARGET_COLUMN = "Machine failure"

# Maximum import size in bytes (200 MB). Imported CSVs are treated as untrusted.
MAX_IMPORT_BYTES = 200 * 1024 * 1024


def _user_data_dir() -> Path:
    """Return the per-user writable application-data directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_TITLE
        return Path.home() / "AppData" / "Local" / APP_TITLE
    # Linux/macOS fallback.
    return Path.home() / f".{APP_TITLE.lower()}"


@dataclass(frozen=True)
class Paths:
    """Application path configuration."""

    # Root of the source tree (repository root). Resolved at import time.
    project_root: Path
    src_dir: Path
    package_dir: Path
    assets_dir: Path
    datasets_dir: Path
    icons_dir: Path
    docs_dir: Path
    scripts_dir: Path
    packaging_dir: Path
    config_dir: Path
    tests_dir: Path

    # Writable user-data directories.
    app_data_dir: Path
    user_datasets_dir: Path
    model_dir: Path
    registry_dir: Path
    logs_dir: Path
    reports_dir: Path
    settings_dir: Path

    @classmethod
    def resolve(cls, project_root: Path | None = None) -> "Paths":
        """Build the full path configuration from the project root."""
        root = project_root or _detect_project_root()
        src_dir = root / "src"
        package_dir = src_dir / "maintiq"

        app_data_dir = _user_data_dir()

        return cls(
            project_root=root,
            src_dir=src_dir,
            package_dir=package_dir,
            assets_dir=root / "assets",
            datasets_dir=root / "assets" / "datasets",
            icons_dir=root / "assets" / "icons",
            docs_dir=root / "docs",
            scripts_dir=root / "scripts",
            packaging_dir=root / "packaging",
            config_dir=root / "config",
            tests_dir=root / "tests",
            app_data_dir=app_data_dir,
            user_datasets_dir=app_data_dir / "datasets",
            model_dir=app_data_dir / "models",
            registry_dir=app_data_dir / "registry",
            logs_dir=app_data_dir / "logs",
            reports_dir=app_data_dir / "reports",
            settings_dir=app_data_dir / "settings",
        )


def _detect_project_root() -> Path:
    """Detect the repository root from this file's location.

    When the application is frozen (PyInstaller executable), ``__file__`` no
    longer points at the source tree, so fall back to the directory containing
    the executable so assets installed next to the EXE remain resolvable.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    title: str = APP_TITLE
    version: str = APP_VERSION
    random_seed: int = RANDOM_SEED
    default_threshold: float = DEFAULT_THRESHOLD
    supported_models: tuple[str, ...] = SUPPORTED_MODELS
    target_column: str = TARGET_COLUMN
    dataset_filename: str = DATASET_FILENAME
    max_import_bytes: int = MAX_IMPORT_BYTES
    paths: Paths = field(default_factory=lambda: Paths.resolve())

    def ensure_runtime_directories(self) -> list[Path]:
        """Create all writable runtime directories and return them."""
        directories = [
            self.paths.app_data_dir,
            self.paths.user_datasets_dir,
            self.paths.model_dir,
            self.paths.registry_dir,
            self.paths.logs_dir,
            self.paths.reports_dir,
            self.paths.settings_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        return directories


_CONFIG: AppConfig | None = None


def get_config() -> AppConfig:
    """Return the singleton application configuration."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = AppConfig()
    return _CONFIG
