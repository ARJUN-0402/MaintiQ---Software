"""Reports and Downloads page: export metrics and dataset reports to disk."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from maintiq.config import get_config
from maintiq.services import ApplicationService
from maintiq.ui.pages.base import BasePage
from maintiq.ui.signals import TaskResult


class ReportsPage(BasePage):
    """Generate and export reports (JSON metrics, dataset profile, PNG charts)."""

    def __init__(self, service: ApplicationService, parent=None) -> None:
        super().__init__(service, parent)
        self.set_title("Reports and Downloads")
        self.set_subtitle(
            "Export evaluation metrics, dataset profiles, threshold analysis "
            "and evaluation charts to JSON/CSV/PNG files."
        )

        controls = QHBoxLayout()
        self._type_combo = QComboBox()
        self._type_combo.addItems(
            [
                "Model evaluation metrics (JSON)",
                "Dataset profile (JSON)",
                "Threshold analysis (CSV)",
                "Evaluation charts (PNG)",
                "Export all (bundle)",
            ]
        )
        self._type_combo.setMinimumWidth(260)
        self.btn_export = QPushButton("Export to file…")
        self.btn_export.setObjectName("primary")
        controls.addWidget(QLabel("Report type:"))
        controls.addWidget(self._type_combo)
        controls.addWidget(self.btn_export)
        controls.addStretch()
        self._content_layout.addLayout(controls)

        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(220)
        self._version_combo = QComboBox()
        self._version_combo.setMinimumWidth(120)
        selector = QHBoxLayout()
        selector.addWidget(QLabel("Model:"))
        selector.addWidget(self._model_combo)
        selector.addWidget(QLabel("Version:"))
        selector.addWidget(self._version_combo)
        selector.addStretch()
        self._content_layout.addLayout(selector)

        self._last_threshold_result = None
        self._evaluation_data: dict[str, object] | None = None

        self._content_layout.addStretch()

        self.btn_export.clicked.connect(self._run_export)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

    def on_shown(self) -> None:
        self._load_models()

    def set_threshold_result(self, result) -> None:
        self._last_threshold_result = result
        self.show_info("Threshold analysis result ready for export.")

    def set_evaluation_data(
        self,
        y_true=None,
        scores=None,
        metrics=None,
        comparison_result=None,
        threshold_result=None,
    ) -> None:
        """Store evaluation results so charts can be exported from this page."""
        self._evaluation_data = {
            "y_true": y_true,
            "scores": scores,
            "metrics": metrics,
            "comparison_result": comparison_result,
            "threshold_result": threshold_result,
        }
        if threshold_result is not None:
            self._last_threshold_result = threshold_result
        self.show_info("Evaluation data ready for chart export.")

    def _load_models(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        try:
            self._model_combo.addItems(self.service.list_models())
        except Exception as exc:
            self.show_error(f"Could not list models: {exc}")
        self._model_combo.blockSignals(False)
        self._on_model_changed()

    def _on_model_changed(self) -> None:
        self._version_combo.blockSignals(True)
        self._version_combo.clear()
        model = self._model_combo.currentText()
        if model:
            try:
                versions = self.service.list_versions(model)
                self._version_combo.addItems(versions)
                if versions:
                    self._version_combo.setCurrentIndex(len(versions) - 1)
            except Exception as exc:
                self.show_error(f"Could not list versions: {exc}")
        self._version_combo.blockSignals(False)

    def _default_name(self, report_type: str) -> str:
        return {
            "Model evaluation metrics (JSON)": "model_metrics_report.json",
            "Dataset profile (JSON)": "dataset_profile_report.json",
            "Threshold analysis (CSV)": "threshold_analysis.csv",
            "Evaluation charts (PNG)": "evaluation_charts",
            "Export all (bundle)": "maintiQ_export",
        }[report_type]

    def _run_export(self) -> None:
        report_type = self._type_combo.currentText()

        if report_type == "Export all (bundle)":
            default_dir = str(get_config().paths.reports_dir)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            default_name = f"{self._default_name(report_type)}_{stamp}"
            dir_path = QFileDialog.getExistingDirectory(self, "Choose export folder", default_dir)
            if not dir_path:
                return
            output_root = Path(dir_path) / default_name
            self._run_export_bundle(output_root)
            return

        default_name = self._default_name(report_type)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export report",
            str(get_config().paths.reports_dir / default_name),
        )
        if not path:
            return

        self.btn_export.setEnabled(False)
        self.clear_banner()

        def work() -> str:
            output_path = Path(path)
            if report_type == "Dataset profile (JSON)":
                frame = self.service.active_frame
                if frame is None:
                    raise RuntimeError("No active dataset. Import a dataset first.")
                profile = self.service.import_service.profiler.profile_as_dict(frame)
                return str(
                    self.service.report_service.export_json(
                        metrics=profile,
                        model_name=None,
                        model_version=None,
                        dataset_fingerprint=None,
                        output_path=output_path,
                    )
                )
            if report_type == "Threshold analysis (CSV)":
                result = self._last_threshold_result
                if result is None:
                    raise RuntimeError(
                        "No threshold analysis result available. Run threshold analysis first."
                    )
                return str(self.service.report_service.export_csv(result, output_path=output_path))
            if report_type == "Evaluation charts (PNG)":
                data = self._evaluation_data
                if data is None or data.get("y_true") is None or data.get("scores") is None:
                    raise RuntimeError("No evaluation data available. Run evaluation first.")
                metrics = data.get("metrics")
                if metrics is None:
                    raise RuntimeError("No evaluation metrics available for chart export.")
                written = self.service.report_service.export_png(
                    y_true=data["y_true"],
                    scores=data["scores"],
                    metrics=metrics,
                    comparison_result=data.get("comparison_result"),
                    threshold_result=data.get("threshold_result"),
                    output_dir=output_path.parent,
                )
                names = ", ".join(p.name for p in written)
                return f"Wrote {len(written)} chart(s): {names}"

            model = self._model_combo.currentText()
            version = self._version_combo.currentText() or None
            if not model:
                raise RuntimeError("Select a model first.")
            record = (
                self.service.registry.get_version(model, version)
                if version
                else self.service.registry.get_latest(model)
            )
            metrics = record.get("metrics") or {}
            return str(
                self.service.report_service.export_json(
                    metrics=metrics,
                    model_name=model,
                    model_version=record.get("version"),
                    dataset_fingerprint=record.get("dataset_fingerprint"),
                    output_path=output_path,
                )
            )

        def on_result(task_result: TaskResult) -> None:
            self.btn_export.setEnabled(True)
            self.show_success(f"Report exported to {task_result.result}")

        def on_error(message: str) -> None:
            self.btn_export.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "export_report",
            work,
            started_message="Generating report…",
            on_result=on_result,
            on_error=on_error,
        )

    def _run_export_bundle(self, output_root: Path) -> None:
        output_root.mkdir(parents=True, exist_ok=True)

        def work() -> list[str]:
            written: list[str] = []

            # JSON metrics report for latest model (if any).
            try:
                models = self.service.list_models()
                if models:
                    latest = models[0]
                    record = self.service.registry.get_latest(latest)
                    metrics = record.get("metrics") or {}
                    self.service.report_service.export_json(
                        metrics=metrics,
                        model_name=latest,
                        model_version=record.get("version"),
                        dataset_fingerprint=record.get("dataset_fingerprint"),
                        output_path=output_root / "model_metrics_report.json",
                    )
                    written.append("model_metrics_report.json")
            except Exception:
                pass

            # Threshold analysis CSV.
            if self._last_threshold_result is not None:
                self.service.report_service.export_csv(
                    self._last_threshold_result,
                    output_path=output_root / "threshold_analysis.csv",
                )
                written.append("threshold_analysis.csv")

            # Evaluation charts PNG.
            data = self._evaluation_data
            if data is not None and data.get("y_true") is not None:
                self.service.report_service.export_png(
                    y_true=data["y_true"],
                    scores=data["scores"],
                    metrics=data.get("metrics"),
                    comparison_result=data.get("comparison_result"),
                    threshold_result=data.get("threshold_result"),
                    output_dir=output_root / "charts",
                )
                written.append("charts/")

            # Dataset profile JSON.
            frame = self.service.active_frame
            if frame is not None:
                profile = self.service.import_service.profiler.profile_as_dict(frame)
                self.service.report_service.export_json(
                    metrics=profile,
                    model_name=None,
                    model_version=None,
                    dataset_fingerprint=None,
                    output_path=output_root / "dataset_profile_report.json",
                )
                written.append("dataset_profile_report.json")

            if not written:
                raise RuntimeError(
                    "Nothing to export. Import a dataset, run evaluation, "
                    "or register a model first."
                )
            return written

        def on_result(task_result: TaskResult) -> None:
            self.btn_export.setEnabled(True)
            items = "\n".join(f"  • {name}" for name in task_result.result)
            self.show_success(f"Export bundle written to {output_root}\n{items}")

        def on_error(message: str) -> None:
            self.btn_export.setEnabled(True)
            self.show_error(message)

        self.run_task(
            "export_report_bundle",
            work,
            started_message="Creating export bundle…",
            on_result=on_result,
            on_error=on_error,
        )
