"""Tests for the ApplicationService orchestration layer."""

from pathlib import Path

import pandas as pd
import pytest

from maintiq.core.exceptions import MaintiQError, RegistryError
from maintiq.data.import_workflow import ImportOutcome
from maintiq.services import ApplicationService


class _StubImport:
    def __init__(self, frame=None, source="source.csv"):
        self.frame = frame
        self.source = source
        self.calls = []

    def import_dataset(self, path):
        self.calls.append(path)
        return ImportOutcome(
            accepted=self.frame is not None,
            load_result=None,
            validation=None,
            errors=[] if self.frame is not None else ["no data"],
        )

    @property
    def active_frame(self):
        return self.frame

    @property
    def has_active_dataset(self):
        return self.frame is not None

    def predictive_input_frame(self):
        return self.frame

    def target_series(self):
        return pd.Series([0, 1, 0, 1], name="machine_failure") if self.frame is not None else None


class _StubTrainer:
    def __init__(self, result=None):
        self.result = result or _FakeTrainingResult()
        self.calls = []

    def train_model(
        self, model_name, frame=None, target=None, threshold=None, cancelled_check=None
    ):
        self.calls.append((model_name, frame is not None, target is not None, threshold))
        return self.result


class _FakeTrainingResult:
    model_name = "gradient_boosting"
    model_version = "v1"
    metrics = None
    artifact_path = None
    training_duration_seconds = 1.0
    cancelled = False


class _StubRegistry:
    def __init__(self):
        self.models = {"gradient_boosting": None}
        self.versions = {"gradient_boosting": ["v1"]}
        self.deleted_models = []
        self.deleted_versions = []

    def model_exists(self, model_name):
        return model_name in self.models

    def list_models(self):
        return sorted(self.models.keys())

    def list_versions(self, model_name):
        return self.versions.get(model_name, [])

    def get_version(self, model_name, version):
        return {"version": version}

    def get_artifact_path(self, model_name, version):
        return None

    def delete_model(self, model_name):
        self.deleted_models.append(model_name)
        if model_name not in self.models:
            raise RegistryError(f"Model {model_name!r} not found.")
        del self.models[model_name]
        self.versions.pop(model_name, None)
        return 1

    def delete_version(self, model_name, version):
        self.deleted_versions.append((model_name, version))
        if model_name not in self.models:
            raise RegistryError(f"Model {model_name!r} not found.")


class _StubPrediction:
    def __init__(self, outcome=None):
        self.outcome = outcome or _FakeOutcome()
        self.calls = []

    def load_model(self, model_name, version=None):
        self.calls.append((model_name, version))
        return _FakePipeline()

    def predict_and_explain(self, pipeline, input_record, background_data=None, method="auto"):
        self.calls.append((input_record, background_data, method))
        return self.outcome


class _FakePipeline:
    is_fitted = True
    model_name = "gradient_boosting"
    model_version = "v1"


class _FakePredictionResult:
    predicted_class = 1
    score = 0.8
    threshold = 0.5
    model_name = "gradient_boosting"
    model_version = "v1"
    input_validated = True
    out_of_distribution_warnings: tuple[str, ...] = ()
    explanation_available = False


class _FakeOutcome:
    prediction = _FakePredictionResult()
    explanation = None
    explanation_error = None


class _StubReport:
    def __init__(self, path="report.json"):
        self.path = path
        self.calls = []

    def export_json(self, **kwargs):
        self.calls.append(kwargs)
        return Path(self.path)

    def export_csv(self, threshold_result=None, output_path=None):
        self.calls.append(("csv", threshold_result, output_path))
        return Path(output_path or "threshold.csv")

    def export_png(
        self,
        y_true=None,
        scores=None,
        metrics=None,
        comparison_result=None,
        threshold_result=None,
        output_dir=None,
    ):
        self.calls.append(("png", y_true, scores, metrics, output_dir))
        return [Path(output_dir or "figures") / "chart.png"]


def _make_frame():
    return pd.DataFrame(
        {
            "type": ["L", "M", "H", "L"],
            "air_temperature_k": [298.0, 300.0, 302.0, 299.0],
            "process_temperature_k": [302.0, 305.0, 308.0, 303.0],
            "rotational_speed_rpm": [1400.0, 1500.0, 1600.0, 1450.0],
            "torque_nm": [40.0, 50.0, 60.0, 45.0],
            "tool_wear_min": [50.0, 100.0, 150.0, 75.0],
        }
    )


def test_import_dataset_delegates():
    stub_import = _StubImport(frame=_make_frame())
    app = ApplicationService(import_service=stub_import)
    outcome = app.import_dataset("data.csv")
    assert stub_import.calls == ["data.csv"]
    assert outcome.accepted is True


def test_train_model_uses_active_dataset_when_not_supplied():
    frame = _make_frame()
    stub_import = _StubImport(frame=frame)
    stub_trainer = _StubTrainer()
    app = ApplicationService(import_service=stub_import, trainer=stub_trainer)
    result = app.train_model("random_forest")

    assert result is stub_trainer.result
    assert len(stub_trainer.calls) == 1
    name, frame_given, target_given, threshold = stub_trainer.calls[0]
    assert name == "random_forest"
    assert frame_given is True
    assert target_given is True
    assert threshold is None


def test_train_model_supplies_frame_and_target():
    frame = _make_frame()
    target = pd.Series([0, 1, 0, 1], name="machine_failure")
    stub_import = _StubImport(frame=None)
    stub_trainer = _StubTrainer()
    app = ApplicationService(import_service=stub_import, trainer=stub_trainer)
    app.train_model("xgboost", frame=frame, target=target, threshold=0.7)

    name, frame_given, target_given, threshold = stub_trainer.calls[0]
    assert name == "xgboost"
    assert frame_given is True
    assert target_given is True
    assert threshold == 0.7


def test_train_model_no_active_dataset_raises():
    stub_import = _StubImport(frame=None)
    stub_trainer = _StubTrainer()
    app = ApplicationService(import_service=stub_import, trainer=stub_trainer)
    with pytest.raises(MaintiQError):
        app.train_model("gradient_boosting")


def test_list_models_and_version_delegate():
    stub_registry = _StubRegistry()
    app = ApplicationService(registry=stub_registry)
    assert app.list_models() == ["gradient_boosting"]
    assert app.model_exists("gradient_boosting") is True
    assert app.model_exists("absent") is False
    assert app.list_versions("gradient_boosting") == ["v1"]


def test_predict_delegates_and_uses_same_record():
    stub_prediction = _StubPrediction()
    app = ApplicationService(prediction_service=stub_prediction)
    record = {
        "type": "L",
        "air_temperature_k": 298.0,
        "process_temperature_k": 302.0,
        "rotational_speed_rpm": 1400.0,
        "torque_nm": 40.0,
        "tool_wear_min": 50.0,
    }
    bg = _make_frame()
    outcome = app.predict(
        "gradient_boosting", record, version="v1", background_data=bg, method="lime"
    )

    # load_model was invoked, then predict_and_explain with the same record.
    assert ("gradient_boosting", "v1") in stub_prediction.calls
    assert stub_prediction.calls[-1] == (record, bg, "lime")
    assert outcome.prediction.predicted_class == 1
    assert outcome.prediction.score == 0.8


def test_export_report_delegates():
    stub_report = _StubReport()
    app = ApplicationService(report_service=stub_report)
    path = app.export_report(metrics=None, model_name="gradient_boosting")
    assert str(path) == "report.json"
    assert stub_report.calls[0]["model_name"] == "gradient_boosting"


def test_export_csv_delegates():
    stub_report = _StubReport()
    app = ApplicationService(report_service=stub_report)
    result = object()
    path = app.export_csv(result, output_path="threshold.csv")
    assert str(path) == "threshold.csv"
    assert stub_report.calls[-1][0] == "csv"
    assert stub_report.calls[-1][1] is result


def test_export_png_delegates():
    stub_report = _StubReport()
    app = ApplicationService(report_service=stub_report)
    y_true = [0, 1]
    scores = [0.1, 0.9]
    metrics = object()
    written = app.export_png(y_true, scores, metrics, output_dir="figures")
    assert len(written) == 1
    assert stub_report.calls[-1][0] == "png"
    assert stub_report.calls[-1][1] == y_true
    assert stub_report.calls[-1][2] == scores
    assert stub_report.calls[-1][3] is metrics


def test_delete_model_delegates():
    stub_registry = _StubRegistry()
    app = ApplicationService(registry=stub_registry)
    removed = app.delete_model("gradient_boosting")
    assert removed == 1
    assert stub_registry.deleted_models == ["gradient_boosting"]


def test_delete_model_missing_raises():
    stub_registry = _StubRegistry()
    app = ApplicationService(registry=stub_registry)
    with pytest.raises(RegistryError):
        app.delete_model("absent")


def test_delete_version_delegates():
    stub_registry = _StubRegistry()
    app = ApplicationService(registry=stub_registry)
    app.delete_version("gradient_boosting", "v1")
    assert stub_registry.deleted_versions == [("gradient_boosting", "v1")]
