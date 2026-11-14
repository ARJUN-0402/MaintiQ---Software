"""Settings page: local user preferences persisted to the app-data directory."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
)

from maintiq.config import DEFAULT_THRESHOLD, SUPPORTED_MODELS, get_config
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.widgets.metric_card import MetricCard

SETTINGS_FILENAME = "app_settings.json"


class SettingsPage(BasePage):
    """Local settings: default model and threshold, persisted in user app data."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Settings")
        self.set_subtitle("Local configuration persisted under %LOCALAPPDATA%\\MaintiQ\\settings.")

        group = QGroupBox("Preferences")
        form = QFormLayout(group)

        self._default_model = QComboBox()
        self._default_model.addItems([m.replace("_", " ").title() for m in SUPPORTED_MODELS])
        self._default_threshold = QDoubleSpinBox()
        self._default_threshold.setRange(0.0, 1.0)
        self._default_threshold.setDecimals(2)
        self._default_threshold.setSingleStep(0.05)
        self._default_threshold.setValue(DEFAULT_THRESHOLD)

        form.addRow("Default model", self._default_model)
        form.addRow("Default threshold", self._default_threshold)
        self._content_layout.addWidget(group)

        self.btn_save = QPushButton("Save settings")
        self.btn_save.setObjectName("primary")
        self.btn_reset = QPushButton("Reset to defaults")
        actions = QHBoxLayout()
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_reset)
        actions.addStretch()
        self._content_layout.addLayout(actions)

        self.card_path = MetricCard("Settings file", str(self._settings_path()))
        self._content_layout.addWidget(self.card_path)

        self._content_layout.addStretch()

        self.btn_save.clicked.connect(self._save)
        self.btn_reset.clicked.connect(self._reset)

        self._load()

    # ---------------------------------------------------------------- persistence

    def _settings_path(self) -> Path:
        return get_config().paths.settings_dir / SETTINGS_FILENAME

    def _load(self) -> None:
        path = self._settings_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        model = data.get("default_model")
        if model in SUPPORTED_MODELS:
            self._default_model.setCurrentText(model.replace("_", " ").title())
        threshold = data.get("default_threshold")
        if threshold is not None:
            try:
                self._default_threshold.setValue(float(threshold))
            except (TypeError, ValueError):
                pass

    def _save(self) -> None:
        data = {
            "default_model": self._model_key(),
            "default_threshold": float(self._default_threshold.value()),
        }
        path = self._settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
            os.replace(tmp_path, path)
            self.show_success("Settings saved.")
        except OSError as exc:
            self.show_error(f"Could not save settings: {exc}")

    def _reset(self) -> None:
        self._default_model.setCurrentIndex(0)
        self._default_threshold.setValue(DEFAULT_THRESHOLD)
        self.show_info("Defaults restored (not saved until you click Save).")

    def _model_key(self) -> str:
        return self._default_model.currentText().replace(" ", "_").lower()
