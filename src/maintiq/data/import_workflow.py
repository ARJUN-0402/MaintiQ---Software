"""Import workflow service: accepts a user-selected CSV, validates it, and
tracks the active dataset without mutating the source file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from maintiq.data.loader import DatasetLoader, LoadResult
from maintiq.data.profiler import DatasetProfiler
from maintiq.data.schema import DatasetSchema
from maintiq.data.validator import ValidationResult


@dataclass
class ImportOutcome:
    """Outcome of an import workflow attempt."""

    accepted: bool
    load_result: LoadResult
    validation: ValidationResult | None = None
    profile: dict | None = None
    errors: list[str] = field(default_factory=list)


class ImportWorkflowService:
    """Coordinates dataset import, validation, and active-dataset state."""

    def __init__(
        self,
        loader: DatasetLoader | None = None,
        profiler: DatasetProfiler | None = None,
        schema: DatasetSchema | None = None,
    ):
        self.schema = schema or DatasetSchema()
        self.loader = loader or DatasetLoader(schema=self.schema)
        self.profiler = profiler or DatasetProfiler(schema=self.schema)
        self._active_frame: pd.DataFrame | None = None
        self._active_source: Path | None = None
        self._active_validation: ValidationResult | None = None

    @property
    def active_frame(self) -> pd.DataFrame | None:
        """The currently active validated dataset, or None."""
        return self._active_frame

    @property
    def active_source(self) -> Path | None:
        """Path to the active dataset source file, or None."""
        return self._active_source

    @property
    def active_validation(self) -> ValidationResult | None:
        """Validation result for the active dataset, or None."""
        return self._active_validation

    def has_active_dataset(self) -> bool:
        return self._active_frame is not None

    def import_dataset(self, path: str | Path) -> ImportOutcome:
        """Load and validate a CSV; if valid, mark it as the active dataset.

        On failure the previously active dataset (if any) is left untouched.
        """
        load_result, validation = self.loader.load_and_validate(path)
        outcome = ImportOutcome(
            accepted=False,
            load_result=load_result,
            validation=validation,
        )

        if load_result.frame is None:
            outcome.errors = list(load_result.errors)
            return outcome

        if validation is None:
            outcome.errors.append("Validation could not be performed.")
            return outcome

        if not validation.is_valid:
            outcome.errors = list(validation.errors)
            return outcome

        # Accept: mark as active. Source columns are renamed to their canonical
        # internal names so the rest of the application works with a stable
        # schema. The original source file is not modified.
        frame = load_result.frame
        rename_map = {}
        for column in frame.columns:
            canonical = self.schema.canonical_for(str(column))
            if canonical is not None:
                rename_map[column] = canonical
        frame = frame.rename(columns=rename_map)

        self._active_frame = frame
        self._active_source = Path(load_result.source_path) if load_result.source_path else None
        self._active_validation = validation
        outcome.accepted = True
        outcome.profile = self.profiler.profile_as_dict(frame)
        return outcome

    def clear_active_dataset(self) -> None:
        """Clear the active dataset without touching any source files."""
        self._active_frame = None
        self._active_source = None
        self._active_validation = None

    def predictive_input_frame(self) -> pd.DataFrame | None:
        """Return only the canonical predictive input columns of the active frame.

        Identifiers (UDI, Product ID) and failure-mode indicators (TWF, HDF,
        PWF, OSF, RNF) are excluded.
        """
        if self._active_frame is None:
            return None
        available = [c for c in self.schema.feature_columns if c in self._active_frame.columns]
        if not available:
            return None
        return self._active_frame[available].copy()

    def target_series(self) -> pd.Series | None:
        """Return the target series of the active frame, or None."""
        if self._active_frame is None:
            return None
        # The active frame uses canonical column names.
        if self.schema.target_column not in self._active_frame.columns:
            return None
        return self._active_frame[self.schema.target_column].copy()
