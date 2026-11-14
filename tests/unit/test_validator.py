"""Tests for the dataset validator."""

import pandas as pd

from maintiq.data.validator import DatasetValidator, ValidationResult

_BASE_ROW = {
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
}


def _frame(rows):
    return pd.DataFrame(rows)


def test_valid_frame_passes():
    validator = DatasetValidator()
    result = validator.validate(_frame([_BASE_ROW]))
    assert result.is_valid
    assert not result.errors


def test_missing_columns_fails():
    validator = DatasetValidator()
    row = {k: v for k, v in _BASE_ROW.items() if k != "Machine failure"}
    result = validator.validate(_frame([row]))
    assert not result.is_valid
    assert any("Missing required columns" in e for e in result.errors)


def test_empty_frame_fails():
    validator = DatasetValidator()
    result = validator.validate(pd.DataFrame())
    assert not result.is_valid


def test_invalid_target_fails():
    validator = DatasetValidator()
    row = dict(_BASE_ROW, **{"Machine failure": 2})
    result = validator.validate(_frame([row]))
    assert not result.is_valid
    assert any("Target column" in e for e in result.errors)


def test_invalid_category_fails():
    validator = DatasetValidator()
    row = dict(_BASE_ROW, **{"Type": "X"})
    result = validator.validate(_frame([row]))
    assert not result.is_valid
    assert any("unexpected categories" in e for e in result.errors)


def test_missing_values_warning_only():
    validator = DatasetValidator()
    row = dict(_BASE_ROW, **{"Torque [Nm]": None})
    result = validator.validate(_frame([row]))
    assert result.is_valid
    assert result.missing_value_counts.get("Torque [Nm]") == 1
    assert any("missing value" in w.lower() for w in result.warnings)


def test_duplicate_rows_warning_only():
    validator = DatasetValidator()
    result = validator.validate(_frame([_BASE_ROW, _BASE_ROW]))
    assert result.is_valid
    assert result.duplicate_row_count == 1
    assert any("duplicate" in w.lower() for w in result.warnings)


def test_nonnumeric_numeric_field_fails():
    validator = DatasetValidator()
    row = dict(_BASE_ROW, **{"Torque [Nm]": "abc"})
    result = validator.validate(_frame([row]))
    assert not result.is_valid
    assert any("non-numeric" in e for e in result.errors)


def test_impossible_numeric_values_fail():
    validator = DatasetValidator()
    row = dict(_BASE_ROW, **{"Rotational speed [rpm]": -100})
    result = validator.validate(_frame([row]))
    assert not result.is_valid


def test_excluded_columns_flagged():
    validator = DatasetValidator()
    result = validator.validate(_frame([_BASE_ROW]))
    assert result.is_valid
    assert any("excluded from prediction" in w for w in result.warnings)


def test_validation_result_is_structured():
    result = ValidationResult(is_valid=True)
    result.add_error("e1")
    result.add_warning("w1")
    assert result.is_valid is False
    assert result.errors == ["e1"]
    assert result.warnings == ["w1"]
