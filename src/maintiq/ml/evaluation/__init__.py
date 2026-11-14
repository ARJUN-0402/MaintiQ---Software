"""Model evaluation and threshold analysis."""

from maintiq.ml.evaluation.charts import (
    plot_confusion_matrix,
    plot_fp_fn_tradeoff,
    plot_model_comparison,
    plot_precision_recall_curve,
    plot_roc_curve,
    plot_threshold_vs_metric,
)
from maintiq.ml.evaluation.comparison import (
    ComparisonResult,
    ComparisonService,
    ModelComparisonResult,
)
from maintiq.ml.evaluation.service import ClassificationMetrics, EvaluationService
from maintiq.ml.evaluation.threshold import (
    DEFAULT_THRESHOLD_GRID,
    ThresholdAnalysisResult,
    ThresholdAnalysisService,
    ThresholdResult,
)

__all__ = [
    "DEFAULT_THRESHOLD_GRID",
    "ClassificationMetrics",
    "ComparisonResult",
    "ComparisonService",
    "EvaluationService",
    "ModelComparisonResult",
    "ThresholdAnalysisResult",
    "ThresholdAnalysisService",
    "ThresholdResult",
    "plot_confusion_matrix",
    "plot_fp_fn_tradeoff",
    "plot_model_comparison",
    "plot_precision_recall_curve",
    "plot_roc_curve",
    "plot_threshold_vs_metric",
]
