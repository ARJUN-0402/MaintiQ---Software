"""Tests for the dataset profiler."""

import json

import pandas as pd

from maintiq.data.profiler import DatasetProfiler

_ROWS = [
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


def _frame():
    return pd.DataFrame(_ROWS)


def test_profile_counts_and_types():
    profile = DatasetProfiler().profile(_frame())
    assert profile.row_count == 2
    assert profile.column_count == 14
    assert profile.column_types["Type"] == "object"
    assert profile.missing_value_counts == {}
    assert profile.duplicate_row_count == 0


def test_profile_target_distribution():
    profile = DatasetProfiler().profile(_frame())
    assert profile.target_distribution == {"0": 1, "1": 1}


def test_profile_numeric_summaries():
    profile = DatasetProfiler().profile(_frame())
    assert "Air temperature [K]" in profile.numeric_summaries
    summary = profile.numeric_summaries["Air temperature [K]"]
    assert summary["min"] == 298.1
    assert summary["max"] == 308.4


def test_profile_is_deterministic():
    p1 = DatasetProfiler().profile(_frame())
    p2 = DatasetProfiler().profile(_frame())
    assert p1.numeric_summaries == p2.numeric_summaries
    assert p1.category_counts == p2.category_counts
    assert p1.target_distribution == p2.target_distribution


def test_profile_as_dict_is_json_serialisable():
    profile_dict = DatasetProfiler().profile_as_dict(_frame())
    json.dumps(profile_dict)  # should not raise
