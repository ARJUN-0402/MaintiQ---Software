"""Validation results and the DatasetValidator."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from maintiq.data.schema import DatasetSchema


@dataclass
class ValidationResult:
    """Structured outcome of dataset validation.

    Validation never modifies the source frame. Problems are reported so the
    caller (or the later preprocessing pipeline) can decide how to handle them.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    missing_value_counts: dict[str, int] = field(default_factory=dict)
    duplicate_row_count: int = 0
    column_types: dict[str, str] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class DatasetValidator:
    """Validates an imported dataset against the AI4I schema contract."""

    def __init__(self, schema: DatasetSchema | None = None):
        self.schema = schema or DatasetSchema()

    def validate(self, frame: pd.DataFrame) -> ValidationResult:
        """Run all validation checks on ``frame`` without modifying it."""
        result = ValidationResult(
            is_valid=True,
            row_count=len(frame),
            column_count=len(frame.columns),
            column_types={str(col): str(dtype) for col, dtype in frame.dtypes.items()},
        )

        self._check_empty(frame, result)
        self._check_required_columns(frame, result)
        if not result.is_valid:
            return result  # Stop early; further checks need the required columns.

        self._check_duplicate_rows(frame, result)
        self._check_missing_values(frame, result)
        self._check_target(frame, result)
        self._check_categories(frame, result)
        self._check_numeric_domains(frame, result)
        self._check_excluded_columns_not_used(frame, result)

        return result

    def _check_empty(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        if frame.empty or len(frame.columns) == 0:
            result.add_error("The dataset is empty or contains no columns.")

    def _check_required_columns(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        required = set(self.schema.required_source_columns())
        present = set(frame.columns)
        missing = sorted(required - present)
        if missing:
            result.add_error(
                "Missing required columns: "
                + ", ".join(missing)
                + ". Ensure the AI4I CSV includes the predictive inputs and target."
            )

    def _check_duplicate_rows(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        duplicates = int(frame.duplicated().sum())
        result.duplicate_row_count = duplicates
        if duplicates:
            result.add_warning(
                f"{duplicates} duplicate row(s) detected. Rows are not removed automatically."
            )

    def _check_missing_values(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        missing = frame.isna().sum()
        result.missing_value_counts = {
            str(col): int(count) for col, count in missing.items() if count > 0
        }
        total_missing = int(missing.sum())
        if total_missing:
            result.add_warning(
                f"{total_missing} missing value(s) detected across "
                f"{len(result.missing_value_counts)} column(s). Missing values are not imputed automatically."
            )

    def _check_target(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        source_target = self.schema.source_for(self.schema.target_column)
        if source_target is None or source_target not in frame.columns:
            return  # Already reported as a missing required column.
        target = frame[source_target]
        invalid = target.dropna().apply(lambda v: v not in (0, 1, "0", "1", True, False))
        if bool(invalid.any()):
            result.add_error(
                f"Target column '{source_target}' contains invalid values. "
                "Expected binary 0/1 (Machine failure)."
            )

    def _check_categories(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        source_type = self.schema.source_for("type")
        if source_type is None or source_type not in frame.columns:
            return
        unexpected = (
            frame[source_type].dropna().apply(lambda v: str(v) not in self.schema.type_values)
        )
        if bool(unexpected.any()):
            got = sorted({str(v) for v in frame[source_type].dropna().unique()})
            result.add_error(
                f"Column '{source_type}' contains unexpected categories: {got}. "
                f"Expected {list(self.schema.type_values)}."
            )

    def _check_numeric_domains(self, frame: pd.DataFrame, result: ValidationResult) -> None:
        for column, (minimum, maximum) in self.schema.numeric_domains.items():
            source = self.schema.source_for(column)
            if source is None or source not in frame.columns:
                continue
            series = pd.to_numeric(frame[source], errors="coerce")
            non_numeric = frame[source].notna() & series.isna()
            if bool(non_numeric.any()):
                result.add_error(
                    f"Column '{source}' contains non-numeric data. Numeric values are required."
                )
                continue
            invalid = series.dropna()
            if minimum is not None:
                below = bool((invalid < minimum).any())
                if below:
                    result.add_error(
                        f"Column '{source}' contains values below the minimum {minimum}."
                    )
            if maximum is not None:
                above = bool((invalid > maximum).any())
                if above:
                    result.add_error(
                        f"Column '{source}' contains values above the maximum {maximum}."
                    )

    def _check_excluded_columns_not_used(
        self, frame: pd.DataFrame, result: ValidationResult
    ) -> None:
        """Informational: confirm excluded columns are present in the source but flagged."""
        present_excluded = []
        for canonical in self.schema.excluded_columns:
            source = self.schema.source_for(canonical)
            column = source if source is not None else canonical
            if column in frame.columns:
                present_excluded.append(column)
        if present_excluded:
            result.add_warning(
                "Failure-mode / identifier columns present in source and excluded from prediction: "
                + ", ".join(sorted(present_excluded))
            )


def validate_frame(frame: pd.DataFrame, schema: DatasetSchema | None = None) -> ValidationResult:
    """Convenience function validating ``frame`` against the schema."""
    return DatasetValidator(schema).validate(frame)
