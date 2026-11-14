"""Tests for the dataset loader."""

import copy

import pandas as pd

from maintiq.config import get_config
from maintiq.data.loader import _CANDIDATE_ENCODINGS, DatasetLoader
from maintiq.data.schema import DatasetSchema

_GOOD_ROWS = [
    {
        "UDI": 1,
        "Product ID": "L001",
        "Type": "L",
        "Air temperature [K]": 298.1,
        "Process temperature [K]": 305.2,
        "Rotational speed [rpm]": 1380,
        "Torque [Nm]": 38.5,
        "Tool wear [min]": 40,
        "Machine failure": 0,
        "TWF": 0,
        "HDF": 0,
        "PWF": 0,
        "OSF": 0,
        "RNF": 0,
    },
    {
        "UDI": 2,
        "Product ID": "M002",
        "Type": "M",
        "Air temperature [K]": 308.4,
        "Process temperature [K]": 315.0,
        "Rotational speed [rpm]": 1500,
        "Torque [Nm]": 45.0,
        "Tool wear [min]": 120,
        "Machine failure": 1,
        "TWF": 0,
        "HDF": 0,
        "PWF": 0,
        "OSF": 0,
        "RNF": 1,
    },
]


def _write_csv(tmp_path, name, rows, encoding="utf-8"):
    path = tmp_path / name
    pd.DataFrame(rows).to_csv(path, index=False, encoding=encoding)
    return path


def _fresh_rows():
    return copy.deepcopy(_GOOD_ROWS)


def test_valid_csv_loading(tmp_path):
    """Valid AI4I-style CSV loads with source column names preserved."""
    path = _write_csv(tmp_path, "good.csv", _fresh_rows())
    loader = DatasetLoader(max_bytes=get_config().max_import_bytes)
    result = loader.load(path)

    assert not result.errors
    assert result.frame is not None
    assert len(result.frame) == 2
    assert result.encoding_used in _CANDIDATE_ENCODINGS
    assert "Type" in result.frame.columns
    assert "Machine failure" in result.frame.columns


def test_missing_columns(tmp_path):
    """Missing required columns produce an actionable validation error."""
    row = {k: v for k, v in _GOOD_ROWS[0].items() if k != "Machine failure"}
    path = _write_csv(tmp_path, "missing.csv", [row])
    loader = DatasetLoader()
    load_result, validation = loader.load_and_validate(path)

    assert load_result.frame is not None
    assert validation is not None
    assert not validation.is_valid
    assert any("Missing required columns" in e for e in validation.errors)


def test_wrong_target_type(tmp_path):
    """Non-binary target values produce a validation error."""
    rows = _fresh_rows()
    rows[0]["Machine failure"] = 2
    path = _write_csv(tmp_path, "target.csv", rows)
    loader = DatasetLoader()
    _, validation = loader.load_and_validate(path)

    assert validation is not None
    assert not validation.is_valid
    assert any("Target column" in e for e in validation.errors)


def test_invalid_category(tmp_path):
    """Unexpected Type values produce a validation error."""
    rows = _fresh_rows()
    rows[0]["Type"] = "X"
    path = _write_csv(tmp_path, "category.csv", rows)
    loader = DatasetLoader()
    _, validation = loader.load_and_validate(path)

    assert validation is not None
    assert not validation.is_valid
    assert any("unexpected categories" in e for e in validation.errors)


def test_missing_values(tmp_path):
    """Missing values are reported as warnings, not errors, and rows are not dropped."""
    rows = _fresh_rows()
    rows[0]["Torque [Nm]"] = None
    path = _write_csv(tmp_path, "missing_vals.csv", rows)
    loader = DatasetLoader()
    _, validation = loader.load_and_validate(path)

    assert validation is not None
    assert validation.is_valid  # missing values are warnings, not errors
    assert any("missing value" in w.lower() for w in validation.warnings)
    # Rows are not silently removed.
    assert len(loader.load(path).frame) == 2


def test_duplicate_rows(tmp_path):
    """Duplicate rows are reported as warnings and not removed."""
    path = _write_csv(tmp_path, "dups.csv", [*_fresh_rows(), _fresh_rows()[0]])
    loader = DatasetLoader()
    _, validation = loader.load_and_validate(path)

    assert validation is not None
    assert validation.duplicate_row_count == 1
    assert any("duplicate" in w.lower() for w in validation.warnings)
    assert len(loader.load(path).frame) == 3


def test_cp1252_encoded_file_loads_via_fallback(tmp_path):
    """A non-UTF-8 CSV decodes via the cp1252/latin-1 fallback encodings."""
    path = tmp_path / "cp1252.csv"
    path.write_text("Type,Air temperature [K]\nL,\xff\xfe\n", encoding="cp1252")
    loader = DatasetLoader()
    result = loader.load(path)

    assert not result.errors
    assert result.frame is not None
    assert result.encoding_used in ("cp1252", "latin-1")


def test_empty_file(tmp_path):
    """An empty file reports a clear error."""
    path = tmp_path / "empty.csv"
    path.write_bytes(b"")
    loader = DatasetLoader()
    result = loader.load(path)

    assert result.frame is None
    assert result.errors


def test_nonnumeric_numeric_field(tmp_path):
    """Non-numeric data in a numeric field produces a validation error."""
    rows = _fresh_rows()
    rows[0]["Torque [Nm]"] = "not_a_number"
    path = _write_csv(tmp_path, "nonnumeric.csv", rows)
    loader = DatasetLoader()
    _, validation = loader.load_and_validate(path)

    assert validation is not None
    assert not validation.is_valid
    assert any("non-numeric" in e for e in validation.errors)


def test_failure_mode_leakage_exclusion(tmp_path):
    """Failure-mode indicators are present in source but excluded from prediction."""
    path = _write_csv(tmp_path, "leak.csv", _fresh_rows())
    loader = DatasetLoader(schema=DatasetSchema())
    _load_result, validation = loader.load_and_validate(path)

    assert validation is not None
    assert validation.is_valid
    # Excluded columns are flagged but do not invalidate the file.
    assert any("excluded from prediction" in w for w in validation.warnings)
