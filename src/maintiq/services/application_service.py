"""Application service orchestrating import, training, prediction and reporting.

This is the high-level service layer that ties together the data import
workflow, model training/registry, single-record prediction (with optional
explanation) and reporting. It is dependency-injectable so each component can
be stubbed in tests or swapped by the GUI (phase 8).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from maintiq.config import get_config
from maintiq.core.exceptions import MaintiQError
from maintiq.data.import_workflow import ImportOutcome, ImportWorkflowService
from maintiq.ml.prediction.service import PredictionOutcome, PredictionService
from maintiq.ml.training import ModelRegistry, ModelTrainer
from maintiq.ml.training.trainer import TrainingResult
from maintiq.reporting.service import ReportService


@dataclass
class ApplicationService:
    """Orchestrates import, training, prediction, explanation and reporting.

    All components are optional and default to live implementations backed by
    the configured user-data directories. Pass stubs/mocks in tests.
    """

    import_service: ImportWorkflowService | None = None
    trainer: ModelTrainer | None = None
    registry: ModelRegistry | None = None
    prediction_service: PredictionService | None = None
    report_service: ReportService | None = None

    def __post_init__(self) -> None:
        config = get_config()
        config.ensure_runtime_directories()
        if self.import_service is None:
            self.import_service = ImportWorkflowService()
        if self.registry is None:
            self.registry = ModelRegistry(
                registry_path=config.paths.registry_dir / "registry.json",
                model_dir=config.paths.model_dir,
            )
        if self.trainer is None:
            self.trainer = ModelTrainer(registry=self.registry)
        if self.prediction_service is None:
            self.prediction_service = PredictionService(registry=self.registry)
        if self.report_service is None:
            self.report_service = ReportService()

    # ---------------------------------------------------------------- import

    def import_dataset(self, path: str | Path) -> ImportOutcome:
        """Load and validate a CSV, marking it as the active dataset."""
        return self.import_service.import_dataset(path)

    @property
    def active_frame(self) -> pd.DataFrame | None:
        return self.import_service.active_frame

    @property
    def has_active_dataset(self) -> bool:
        return self.import_service.has_active_dataset()

    # ---------------------------------------------------------------- train

    def train_model(
        self,
        model_name: str,
        frame: pd.DataFrame | None = None,
        target: pd.Series | None = None,
        threshold: float | None = None,
        cancelled_check: Any = None,
        progress_callback: Any = None,
    ) -> TrainingResult:
        """Train ``model_name`` on the active dataset (or supplied data).

        When ``frame``/``target`` are None the active imported dataset is used.
        Returns a :class:`TrainingResult` and registers the artefact.
        """
        if frame is None or target is None:
            frame = self.import_service.predictive_input_frame()
            target = self.import_service.target_series()
            if frame is None or target is None:
                raise MaintiQError(
                    "No active dataset. Import a dataset first or supply frame/target."
                )
        kwargs = {
            "model_name": model_name,
            "frame": frame,
            "target": target,
            "threshold": threshold,
            "cancelled_check": cancelled_check,
        }
        if progress_callback is not None:
            kwargs["progress_callback"] = progress_callback
        return self.trainer.train_model(**kwargs)

    def list_models(self) -> list[str]:
        return self.registry.list_models()

    def model_exists(self, model_name: str) -> bool:
        return self.registry.model_exists(model_name)

    def list_versions(self, model_name: str) -> list[str]:
        return self.registry.list_versions(model_name)

    # --------------------------------------------------------------- predict

    def predict(
        self,
        model_name: str,
        input_record: Any,
        version: str | None = None,
        background_data: Any = None,
        method: str = "auto",
    ) -> PredictionOutcome:
        """Load ``model_name`` (version or latest) and predict/explain ``input_record``.

        The explanation runs ``explain_local`` on the same pipeline and record.
        """
        pipeline = self.prediction_service.load_model(model_name, version=version)
        return self.prediction_service.predict_and_explain(
            pipeline,
            input_record,
            background_data=background_data,
            method=method,
        )

    # -------------------------------------------------------------- reporting

    def export_report(
        self,
        metrics: Any = None,
        model_name: str | None = None,
        model_version: str | None = None,
        dataset_fingerprint: str | None = None,
        target_column: str | None = None,
        feature_columns: list[str] | None = None,
        split_settings: dict[str, Any] | None = None,
        output_path: str | Path | None = None,
    ) -> Path:
        """Export a JSON evaluation report atomically."""
        return self.report_service.export_json(
            metrics=metrics,
            model_name=model_name,
            model_version=model_version,
            dataset_fingerprint=dataset_fingerprint,
            target_column=target_column,
            feature_columns=feature_columns,
            split_settings=split_settings,
            output_path=output_path,
        )

    def export_csv(
        self,
        threshold_result: Any,
        output_path: str | Path | None = None,
    ) -> Path:
        """Export threshold-analysis results to a CSV file."""
        return self.report_service.export_csv(
            threshold_result=threshold_result,
            output_path=output_path,
        )

    def export_png(
        self,
        y_true: Any,
        scores: Any,
        metrics: Any,
        comparison_result: Any = None,
        threshold_result: Any = None,
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """Export all evaluation charts as PNG files.

        Returns the list of written file paths.
        """
        return self.report_service.export_png(
            y_true=y_true,
            scores=scores,
            metrics=metrics,
            comparison_result=comparison_result,
            threshold_result=threshold_result,
            output_dir=output_dir,
        )

    # ---------------------------------------------------------------- registry

    def delete_model(self, model_name: str) -> int:
        """Remove all version records for ``model_name``.

        Returns the number of version records removed.
        """
        return self.registry.delete_model(model_name)

    def delete_version(self, model_name: str, version: str) -> None:
        """Remove a single version record for ``model_name``."""
        self.registry.delete_version(model_name, version)


__all__ = ["ApplicationService"]
