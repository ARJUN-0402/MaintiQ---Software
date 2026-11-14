"""Model Registry page: list registered model versions and their metadata."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton

from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.table_view import TableView

COLUMNS = ["model", "version", "accuracy", "f1", "roc_auc", "threshold", "created_at", "artifact"]


class ModelRegistryPage(BasePage):
    """Browse the local model registry (JSON-backed, SHA-256 verified artefacts).

    Supports refreshing the listing, selecting a version to inspect its details,
    and deleting individual versions or whole models.
    """

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Model Registry")
        self.set_subtitle(
            "Registered model versions with metrics, timestamps and artefact references. "
            "Artefacts are verified by SHA-256 before loading."
        )

        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("primary")
        controls.addWidget(self.btn_refresh)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        self._table = TableView(COLUMNS)
        self._table.setSelectionBehavior(self._table.SelectionBehavior.SelectRows)
        self._content_layout.addWidget(self._table)

        # Selection-dependent action controls.
        action_controls = QHBoxLayout()
        self.btn_delete_version = QPushButton("Delete selected version")
        self.btn_delete_version.setObjectName("danger")
        self.btn_delete_version.setEnabled(False)
        self.btn_delete_model = QPushButton("Delete model")
        self.btn_delete_model.setObjectName("danger")
        self.btn_delete_model.setEnabled(False)
        action_controls.addWidget(self.btn_delete_version)
        action_controls.addWidget(self.btn_delete_model)
        action_controls.addStretch()
        self._content_layout.addLayout(action_controls)

        # Details panel for the selected version.
        self._details = QLabel()
        self._details.setWordWrap(True)
        self._details.setTextInteractionFlags(
            self._details.textInteractionFlags()
            | self._details.textInteractionFlags().TextSelectableByMouse
        )
        self._details.setStyleSheet(
            "color: #cbd5e1; font-size: 12px; background: #0f172a; "
            "border: 1px solid #1e293b; border-radius: 6px; padding: 8px;"
        )
        self._details.hide()
        self._content_layout.addWidget(self._details)

        self._meta = QLabel()
        self._meta.setWordWrap(True)
        self._meta.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._content_layout.addWidget(self._meta)

        self._content_layout.addStretch()

        self.btn_refresh.clicked.connect(self._load)
        self.btn_delete_version.clicked.connect(self._delete_selected_version)
        self.btn_delete_model.clicked.connect(self._delete_selected_model)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        self._selected_model: str | None = None
        self._selected_version: str | None = None

    def on_shown(self) -> None:
        self._load()

    def _load(self) -> None:
        self.btn_refresh.setEnabled(False)
        self.btn_delete_version.setEnabled(False)
        self.btn_delete_model.setEnabled(False)
        self._details.hide()
        self._selected_model = None
        self._selected_version = None
        self.clear_banner()

        def work() -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for model_name in self.service.list_models():
                for version in self.service.list_versions(model_name):
                    record = self.service.registry.get_version(model_name, version)
                    metrics = record.get("metrics") or {}
                    rows.append(
                        {
                            "model": model_name,
                            "version": record.get("version", ""),
                            "accuracy": _fmt(metrics.get("accuracy")),
                            "f1": _fmt(metrics.get("f1")),
                            "roc_auc": _fmt(metrics.get("roc_auc")),
                            "threshold": (
                                f"{float(record.get('threshold')):.2f}"
                                if record.get("threshold") is not None
                                else "—"
                            ),
                            "created_at": str(record.get("created_at", ""))[:19],
                            "artifact": record.get("artifact_path", ""),
                        }
                    )
            return rows

        def on_result(task_result: TaskResult) -> None:
            self.btn_refresh.setEnabled(True)
            rows = task_result.result
            self._table.set_rows(rows)
            if not rows:
                self.show_empty("No registered models. Train a model to appear here.")
                self._meta.setText("0 models, 0 version records.")
            else:
                self.hide_empty()
                models = self.service.list_models()
                total = sum(len(self.service.list_versions(name)) for name in models)
                self._meta.setText(f"{len(models)} models, {total} version records.")

        def on_error(message: str) -> None:
            self.btn_refresh.setEnabled(True)
            self.show_error(message)

        self.run_task("load_registry", work, on_result=on_result, on_error=on_error)

    def _on_selection_changed(self) -> None:
        selected = self._table.selectedItems()
        self.btn_delete_version.setEnabled(False)
        self.btn_delete_model.setEnabled(False)
        self._details.hide()
        self._selected_model = None
        self._selected_version = None
        if not selected:
            return
        row = self._table.currentRow()
        if row < 0:
            return
        model_item = self._table.item(row, 0)
        version_item = self._table.item(row, 1)
        if not model_item or not version_item:
            return
        self._selected_model = model_item.text()
        self._selected_version = version_item.text()
        self.btn_delete_version.setEnabled(True)
        self.btn_delete_model.setEnabled(True)
        self._show_details(self._selected_model, self._selected_version)

    def _show_details(self, model_name: str, version: str) -> None:
        try:
            record = self.service.registry.get_version(model_name, version)
        except Exception as exc:
            self.show_error(f"Could not load version details: {exc}")
            return
        metrics = record.get("metrics") or {}
        parameters = record.get("parameters") or {}
        lines = [
            f"Model: {model_name}",
            f"Version: {record.get('version')}",
            f"Created: {record.get('created_at')}",
            f"Threshold: {record.get('threshold')}",
            f"Dataset fingerprint: {record.get('dataset_fingerprint')}",
            f"Target column: {record.get('target_column')}",
            f"Artifact: {record.get('artifact_path')}",
            f"SHA-256: {record.get('sha256')}",
            "",
            "Metrics:",
        ]
        lines.extend(
            f"  {key}: {metrics[key]}"
            for key in ("accuracy", "precision", "recall", "f1", "roc_auc", "average_precision")
            if key in metrics
        )
        lines.append("")
        lines.append("Parameters:")
        for key, value in parameters.items():
            lines.append(f"  {key}: {value}")
        self._details.setText("\n".join(lines))
        self._details.show()

    def _confirm(self, title: str, message: str) -> bool:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        return dialog.exec() == QMessageBox.StandardButton.Yes

    def _delete_selected_version(self) -> None:
        if not self._selected_model or not self._selected_version:
            return
        if not self._confirm(
            "Delete version",
            f"Delete version {self._selected_version!r} of model "
            f"{self._selected_model!r}? This cannot be undone.",
        ):
            return
        self._run_delete(self._selected_model, self._selected_version, is_model=False)

    def _delete_selected_model(self) -> None:
        if not self._selected_model:
            return
        versions = self.service.list_versions(self._selected_model)
        if not self._confirm(
            "Delete model",
            f"Delete model {self._selected_model!r} and all {len(versions)} "
            "version records? This cannot be undone.",
        ):
            return
        self._run_delete(self._selected_model, None, is_model=True)

    def _run_delete(self, model_name: str, version: str | None, *, is_model: bool) -> None:
        self.btn_delete_version.setEnabled(False)
        self.btn_delete_model.setEnabled(False)
        self.clear_banner()

        def work() -> None:
            if is_model:
                self.service.delete_model(model_name)
            else:
                assert version is not None
                self.service.delete_version(model_name, version)

        def on_result(_task_result: TaskResult) -> None:
            kind = "model" if is_model else "version"
            self.show_success(f"{kind.capitalize()} {model_name!r} deleted.")
            self._load()

        def on_error(message: str) -> None:
            self.btn_delete_version.setEnabled(True)
            self.btn_delete_model.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "delete_registry_entry",
            work,
            on_result=on_result,
            on_error=on_error,
        )


def _fmt(value: Any) -> str:
    if value is None:
        return "--"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
