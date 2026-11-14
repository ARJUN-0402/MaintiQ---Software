"""Tests for the import workflow service."""

import pandas as pd

from maintiq.data.import_workflow import ImportWorkflowService
from maintiq.data.loader import DatasetLoader
from maintiq.data.schema import DatasetSchema

_GOOD_ROW = {
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


def _service_with_loader(loader):
    return ImportWorkflowService(loader=loader, schema=DatasetSchema())


def test_import_valid_dataset_accepted(tmp_path):

    path = tmp_path / "good.csv"
    pd.DataFrame([_GOOD_ROW]).to_csv(path, index=False)
    service = _service_with_loader(DatasetLoader())
    outcome = service.import_dataset(path)

    assert outcome.accepted
    assert service.has_active_dataset()
    assert service.active_source == path
    assert outcome.profile is not None
    assert outcome.profile["row_count"] == 1


def test_import_invalid_dataset_not_accepted(tmp_path):

    path = tmp_path / "bad.csv"
    # Missing target column.
    row = {k: v for k, v in _GOOD_ROW.items() if k != "Machine failure"}
    pd.DataFrame([row]).to_csv(path, index=False)
    service = _service_with_loader(DatasetLoader())
    outcome = service.import_dataset(path)

    assert not outcome.accepted
    assert not service.has_active_dataset()
    assert outcome.errors


def test_failed_import_keeps_previous_active(tmp_path):

    good = tmp_path / "good.csv"
    pd.DataFrame([_GOOD_ROW]).to_csv(good, index=False)
    bad = tmp_path / "bad.csv"
    row = {k: v for k, v in _GOOD_ROW.items() if k != "Machine failure"}
    pd.DataFrame([row]).to_csv(bad, index=False)

    service = _service_with_loader(DatasetLoader())
    service.import_dataset(good)
    assert service.has_active_dataset()

    outcome = service.import_dataset(bad)
    assert not outcome.accepted
    # Previous active dataset remains untouched.
    assert service.has_active_dataset()
    assert service.active_source == good


def test_predictive_input_frame_excludes_identifiers_and_failure_modes(tmp_path):

    path = tmp_path / "good.csv"
    pd.DataFrame([_GOOD_ROW]).to_csv(path, index=False)
    service = _service_with_loader(DatasetLoader())
    service.import_dataset(path)

    inputs = service.predictive_input_frame()
    assert inputs is not None
    assert list(inputs.columns) == [
        "type",
        "air_temperature_k",
        "process_temperature_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
    ]
    assert "udi" not in inputs.columns
    assert "product_id" not in inputs.columns
    assert "twf" not in inputs.columns


def test_target_series(tmp_path):

    path = tmp_path / "good.csv"
    pd.DataFrame([_GOOD_ROW]).to_csv(path, index=False)
    service = _service_with_loader(DatasetLoader())
    service.import_dataset(path)

    target = service.target_series()
    assert target is not None
    assert int(target.iloc[0]) == 0
