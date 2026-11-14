"""Model comparison service for the four candidate classifiers.

Compares Logistic Regression, Random Forest, Gradient Boosting and XGBoost using
identical data partitions and metric definitions. Unavailable models are
reported with an explicit status and reason rather than fabricating results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maintiq.config import SUPPORTED_MODELS
from maintiq.core.exceptions import ModelError
from maintiq.ml.evaluation.service import ClassificationMetrics
from maintiq.ml.training import ModelTrainer, TrainingResult
from maintiq.ml.training.factory import DEFAULT_PARAMS, model_display_name

COMPARISON_WARNING = (
    "Benchmark results are for academic model selection only and do not "
    "establish production industrial reliability. Qualified human review is "
    "required before deploying any model in a maintenance context."
)


@dataclass
class ModelComparisonResult:
    """Outcome for a single candidate model in a comparison."""

    model_name: str
    display_name: str
    status: str  # "success", "unavailable", "failed"
    reason: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    artifact_path: str | None = None
    model_version: str | None = None
    metrics: ClassificationMetrics | None = None
    error: str | None = None
    training_duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "display_name": self.display_name,
            "status": self.status,
            "reason": self.reason,
            "config": self.config,
            "artifact_path": self.artifact_path,
            "model_version": self.model_version,
            "metrics": self.metrics.to_dict() if self.metrics is not None else None,
            "error": self.error,
            "training_duration_seconds": self.training_duration_seconds,
        }


@dataclass
class ComparisonResult:
    """Outcome of comparing candidate models."""

    results: list[ModelComparisonResult]
    selected_metric: str
    best_model: str | None
    warning: str = field(default_factory=lambda: COMPARISON_WARNING)

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": [r.to_dict() for r in self.results],
            "selected_metric": self.selected_metric,
            "best_model": self.best_model,
            "warning": self.warning,
        }

    def successful(self) -> list[ModelComparisonResult]:
        return [r for r in self.results if r.status == "success"]

    def by_metric(self, metric: str) -> list[ModelComparisonResult]:
        """Return successful results sorted by ``metric`` descending."""
        ordered = []
        for result in self.successful():
            if result.metrics is not None:
                value = getattr(result.metrics, metric, None)
                if value is not None:
                    ordered.append((value, result))
        ordered.sort(key=lambda item: item[0], reverse=True)
        return [result for _, result in ordered]


class ComparisonService:
    """Compares candidate classifiers on identical data partitions."""

    def __init__(
        self,
        trainer: ModelTrainer | None = None,
        selected_metric: str = "f1",
    ):
        self.trainer = trainer or ModelTrainer()
        self.selected_metric = selected_metric

    def compare(
        self,
        frame: Any,
        target: Any,
        model_names: tuple[str, ...] = SUPPORTED_MODELS,
    ) -> ComparisonResult:
        """Compare candidate models on the same train/test partition.

        Each model is trained and evaluated using the same trainer instance
        (same random seed and test size), ensuring identical data partitions.
        """
        results: list[ModelComparisonResult] = []

        for model_name in model_names:
            display_name = model_display_name(model_name)
            try:
                training_result: TrainingResult = self.trainer.train_model(
                    model_name=model_name,
                    frame=frame,
                    target=target,
                )

                if training_result.cancelled:
                    results.append(
                        ModelComparisonResult(
                            model_name=model_name,
                            display_name=display_name,
                            status="failed",
                            reason="Training was cancelled.",
                        )
                    )
                    continue

                results.append(
                    ModelComparisonResult(
                        model_name=model_name,
                        display_name=display_name,
                        status="success",
                        config=dict(DEFAULT_PARAMS.get(model_name, {})),
                        artifact_path=str(training_result.artifact_path)
                        if training_result.artifact_path is not None
                        else None,
                        model_version=training_result.model_version,
                        metrics=training_result.metrics,
                        training_duration_seconds=training_result.training_duration_seconds,
                    )
                )
            except ImportError as exc:
                results.append(
                    ModelComparisonResult(
                        model_name=model_name,
                        display_name=display_name,
                        status="unavailable",
                        reason=f"Dependency not importable: {exc}",
                        error=str(exc),
                    )
                )
            except ModelError as exc:
                results.append(
                    ModelComparisonResult(
                        model_name=model_name,
                        display_name=display_name,
                        status="failed",
                        reason=str(exc),
                        error=str(exc),
                    )
                )
            except Exception as exc:  # surface as failed result
                results.append(
                    ModelComparisonResult(
                        model_name=model_name,
                        display_name=display_name,
                        status="failed",
                        reason=f"Unexpected error: {type(exc).__name__}",
                        error=str(exc),
                    )
                )

        best_model = self._select_best(results)
        return ComparisonResult(
            results=results,
            selected_metric=self.selected_metric,
            best_model=best_model,
        )

    def _select_best(self, results: list[ModelComparisonResult]) -> str | None:
        """Select the best model by the configured metric, never by accuracy alone."""
        successful = [r for r in results if r.status == "success" and r.metrics is not None]
        if not successful:
            return None

        metric = self.selected_metric
        best_value = None
        best_model = None
        for result in successful:
            value = getattr(result.metrics, metric, None)
            if value is None:
                continue
            if best_value is None or value > best_value:
                best_value = value
                best_model = result.model_name
        return best_model
