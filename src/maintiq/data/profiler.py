"""Dataset profiler producing a deterministic summary of a loaded frame."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from maintiq.data.schema import DatasetSchema


@dataclass
class DatasetProfile:
    """Deterministic profile of a dataset frame."""

    row_count: int = 0
    column_count: int = 0
    columns: list[str] = field(default_factory=list)
    column_types: dict[str, str] = field(default_factory=dict)
    missing_value_counts: dict[str, int] = field(default_factory=dict)
    duplicate_row_count: int = 0
    numeric_summaries: dict[str, dict[str, float]] = field(default_factory=dict)
    category_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    target_distribution: dict[str, int] = field(default_factory=dict)


class DatasetProfiler:
    """Calculates dataset summaries that are deterministic for the same input."""

    def __init__(self, schema: DatasetSchema | None = None):
        self.schema = schema or DatasetSchema()

    def profile(self, frame: pd.DataFrame) -> DatasetProfile:
        """Build a deterministic profile of ``frame``."""
        profile = DatasetProfile(
            row_count=len(frame),
            column_count=len(frame.columns),
            columns=[str(c) for c in frame.columns],
            column_types={str(c): str(dtype) for c, dtype in frame.dtypes.items()},
            missing_value_counts={
                str(c): int(count) for c, count in frame.isna().sum().items() if int(count) > 0
            },
            duplicate_row_count=int(frame.duplicated().sum()),
        )

        for column in frame.columns:
            series = frame[column]
            if pd.api.types.is_numeric_dtype(series):
                desc = series.describe()
                profile.numeric_summaries[str(column)] = {
                    "count": float(desc["count"]),
                    "mean": float(desc["mean"]),
                    "std": float(desc["std"]),
                    "min": float(desc["min"]),
                    "25%": float(desc["25%"]),
                    "50%": float(desc["50%"]),
                    "75%": float(desc["75%"]),
                    "max": float(desc["max"]),
                }
            elif isinstance(series.dtype, pd.CategoricalDtype) or str(series.dtype) == "object":
                counts = series.value_counts(dropna=False)
                profile.category_counts[str(column)] = {str(k): int(v) for k, v in counts.items()}

        target_source = self.schema.source_for(self.schema.target_column)
        if target_source and target_source in frame.columns:
            target_counts = frame[target_source].value_counts(dropna=False)
            profile.target_distribution = {str(k): int(v) for k, v in target_counts.items()}

        return profile

    def profile_as_dict(self, frame: pd.DataFrame) -> dict:
        """Return the profile as a plain dictionary (JSON-serialisable)."""
        profile = self.profile(frame)
        return {
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "columns": profile.columns,
            "column_types": profile.column_types,
            "missing_value_counts": profile.missing_value_counts,
            "duplicate_row_count": profile.duplicate_row_count,
            "numeric_summaries": profile.numeric_summaries,
            "category_counts": profile.category_counts,
            "target_distribution": profile.target_distribution,
        }
