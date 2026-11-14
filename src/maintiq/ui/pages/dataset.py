"""Dataset Explorer page: CSV import, validation and dataset profile."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton

from maintiq.config import get_config
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult
from maintiq.ui.widgets.table_view import TableView


class DatasetExplorerPage(BasePage):
    """Dataset import, validation and profiling page."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Dataset Explorer")
        self.set_subtitle(
            "Import a CSV, validate it against the AI4I schema, and inspect its profile."
        )

        # Import controls.
        controls = QHBoxLayout()
        self.btn_import = QPushButton("Import CSV…")
        self.btn_import.setObjectName("primary")
        self.btn_clear = QPushButton("Clear dataset")
        self.btn_clear.setMaximumWidth(120)
        self.lbl_source = QLabel("No dataset loaded")
        self.lbl_source.setStyleSheet("color: #94a3b8; font-size: 12px;")
        controls.addWidget(self.btn_import)
        controls.addWidget(self.btn_clear)
        controls.addStretch()
        controls.addWidget(self.lbl_source)
        self._content_layout.addLayout(controls)

        # Profile summary.
        self.lbl_profile = QLabel()
        self.lbl_profile.setWordWrap(True)
        self.lbl_profile.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self._content_layout.addWidget(self.lbl_profile)

        # Validation messages.
        self.lbl_validation = QLabel()
        self.lbl_validation.setWordWrap(True)
        self.lbl_validation.setStyleSheet("color: #fca5a5; font-size: 12px;")
        self._content_layout.addWidget(self.lbl_validation)

        # Field list.
        self._fields_table = TableView(["column", "type", "non-null", "unique"])
        self._content_layout.addWidget(QLabel("Fields (canonical names)"))
        self._content_layout.addWidget(self._fields_table)

        self._content_layout.addStretch()

        self.btn_import.clicked.connect(self._choose_file)
        self.btn_clear.clicked.connect(self._clear)

    # ---------------------------------------------------------------- import

    def import_path(self, path: str) -> None:
        """Import ``path`` (called from the main window file dialog)."""
        self.btn_import.setEnabled(False)
        self.clear_banner()
        self.lbl_validation.setText("")

        def work():
            return self.service.import_dataset(path)

        def on_result(task_result: TaskResult) -> None:
            outcome = task_result.result
            self.btn_import.setEnabled(True)
            if outcome.accepted:
                self.show_success(f"Dataset imported: {outcome.load_result.source_path}")
                self.lbl_source.setText(str(outcome.load_result.source_path))
                self._render_profile(outcome.profile or {})
                self._render_validation(outcome.validation)
                self.show_info("Dataset accepted and marked active.")
            else:
                self.show_error("Import rejected — see validation errors below.")
                messages = "\n".join(outcome.errors) if outcome.errors else "Unknown import error."
                self.lbl_validation.setText(messages)

        def on_error(message: str) -> None:
            self.btn_import.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "import_dataset",
            work,
            started_message="Validating dataset…",
            on_result=on_result,
            on_error=on_error,
        )

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import dataset CSV",
            str(get_config().paths.user_datasets_dir),
            "CSV files (*.csv);;All files (*)",
        )
        if path:
            self.import_path(path)

    def _clear(self) -> None:
        self.service.import_service.clear_active_dataset()
        self.lbl_source.setText("No dataset loaded")
        self.lbl_profile.setText("")
        self.lbl_validation.setText("")
        self._fields_table.set_rows([])
        self.show_info("Active dataset cleared.")

    # ---------------------------------------------------------------- rendering

    def _render_profile(self, profile: dict) -> None:
        lines = []
        for key, label in (
            ("rows", "Rows"),
            ("columns", "Columns"),
            ("missing_values", "Missing values"),
            ("duplicate_rows", "Duplicate rows"),
        ):
            value = profile.get(key)
            if value is not None:
                lines.append(f"{label}: {value}")
        target = profile.get("target_distribution")
        if isinstance(target, dict):
            parts = ", ".join(f"{k}={v}" for k, v in target.items())
            lines.append(f"Target balance: {parts}")
        self.lbl_profile.setText("  |  ".join(lines) if lines else "Profile unavailable.")

    def _render_validation(self, validation) -> None:
        if validation is None:
            self.lbl_validation.setText("Validation not performed.")
            return
        errors = getattr(validation, "errors", None) or []
        warnings = getattr(validation, "warnings", None) or []
        parts = []
        if errors:
            parts.append("Errors: " + "; ".join(str(e) for e in errors))
        if warnings:
            parts.append("Warnings: " + "; ".join(str(w) for w in warnings))
        if not parts:
            parts.append("Dataset is valid.")
        self.lbl_validation.setText("  ".join(parts))

    def set_fields(self, columns: list[str]) -> None:
        rows = [{"column": column, "type": "", "non-null": "", "unique": ""} for column in columns]
        self._fields_table.set_rows(rows)
