"""CSV dataset loader with safe encoding and error handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from maintiq.config import get_config
from maintiq.data.schema import DatasetSchema
from maintiq.data.validator import ValidationResult, validate_frame

# Encodings tried in order when reading an imported CSV. Imported CSVs are
# treated as untrusted text; no formulas, macros, or embedded content are
# ever executed.
_CANDIDATE_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


@dataclass
class LoadResult:
    """Outcome of loading a dataset CSV."""

    frame: pd.DataFrame | None = None
    source_path: Path | None = None
    encoding_used: str | None = None
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


class DatasetLoader:
    """Loads a CSV dataset with safe encoding fallback and useful error messages."""

    def __init__(self, schema: DatasetSchema | None = None, max_bytes: int | None = None):
        self.schema = schema or DatasetSchema()
        config = get_config()
        self.max_bytes = max_bytes if max_bytes is not None else config.max_import_bytes

    def load(self, path: str | Path) -> LoadResult:
        """Load ``path`` into a DataFrame.

        The returned frame keeps original source column names; canonical mapping
        is applied by the schema/validation layer. The source file is never
        modified.
        """
        result = LoadResult()
        file_path = Path(path)

        if not file_path.exists():
            result.errors.append(f"File not found: {file_path}")
            return result
        if not file_path.is_file():
            result.errors.append(f"Path is not a file: {file_path}")
            return result

        try:
            file_size = file_path.stat().st_size
        except OSError as exc:
            result.errors.append(f"Unable to read file size for {file_path}: {exc}")
            return result

        if file_size > self.max_bytes:
            result.errors.append(
                f"File too large ({file_size / (1024 * 1024):.1f} MB). "
                f"Maximum import size is {self.max_bytes / (1024 * 1024):.1f} MB."
            )
            return result
        if file_size == 0:
            result.errors.append(f"File is empty: {file_path}")
            return result

        last_error: Exception | None = None
        for encoding in _CANDIDATE_ENCODINGS:
            try:
                frame = pd.read_csv(file_path, encoding=encoding)
                result.frame = frame
                result.source_path = file_path
                result.encoding_used = encoding
                return result
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except pd.errors.EmptyDataError:
                result.errors.append(f"File contains no data: {file_path}")
                return result
            except Exception as exc:
                result.errors.append(f"Failed to parse {file_path}: {exc}")
                return result

        result.errors.append(
            f"Unable to decode {file_path} using tried encodings "
            f"({', '.join(_CANDIDATE_ENCODINGS)}). Last error: {last_error}"
        )
        return result

    def load_and_validate(self, path: str | Path) -> tuple[LoadResult, ValidationResult | None]:
        """Load ``path`` and validate it against the schema.

        Returns the load result and, when loading succeeded, a validation result.
        """
        load_result = self.load(path)
        if load_result.frame is None or load_result.errors:
            return load_result, None
        validation = validate_frame(load_result.frame, self.schema)
        return load_result, validation
