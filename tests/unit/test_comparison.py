"""Tests for the ComparisonService."""

from __future__ import annotations

import numpy as np
import pandas as pd

from maintiq.core.exceptions import ModelError
from maintiq.ml.evaluation import ClassificationMetrics, ComparisonService
from maintiq.ml.training import TrainingResult


class _FakeTrainer:
    """Stand-in trainer that returns canned TrainingResult outcomes."""

    def __init__(self, outcomes: dict[str, TrainingResult | Exception]):
        self.outcomes = outcomes
        self.called = []

    def train_model(self, model_name, frame, target, **kwargs):
        self.called.append(model_name)
        outcome = self.outcomes.get(model_name)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _make_frame(n=40):
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "type": rng.choice(list("LMH"), size=n),
            "air_temperature_k": rng.uniform(290, 310, size=n),
            "process_temperature_k": rng.uniform(295, 315, size=n),
            "rotational_speed_rpm": rng.uniform(1200, 1600, size=n),
            "torque_nm": rng.uniform(30, 60, size=n),
            "tool_wear_min": rng.uniform(0, 200, size=n),
        }
    )


def _make_target(n=40, pos_frac=0.3):
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < pos_frac).astype(int), name="machine_failure")


def _make_success_result(model_name, f1):
    return TrainingResult(
        model_name=model_name,
        model_version="v1",
        artifact_path=None,
        metrics=None,
    )


def _metrics(f1_value):
    return ClassificationMetrics(
        accuracy=0.8,
        precision=0.8,
        recall=0.8,
        f1=f1_value,
        roc_auc=0.85,
        true_negatives=4,
        false_positives=1,
        false_negatives=1,
        true_positives=4,
        threshold=0.5,
        n_samples=10,
        n_positive=5,
    )


def test_all_success_selects_best_by_metric():
    frame = _make_frame()
    target = _make_target()

    outcomes = {
        "logistic_regression": TrainingResult(
            model_name="logistic_regression",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.70),
        ),
        "random_forest": TrainingResult(
            model_name="random_forest",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.85),
        ),
        "gradient_boosting": TrainingResult(
            model_name="gradient_boosting",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.60),
        ),
        "xgboost": TrainingResult(
            model_name="xgboost",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.75),
        ),
    }
    trainer = _FakeTrainer(outcomes)
    service = ComparisonService(trainer=trainer, selected_metric="f1")
    result = service.compare(frame, target)

    assert result.best_model == "random_forest"
    assert result.selected_metric == "f1"
    assert len(result.successful()) == 4
    assert result.warning is not None
    assert "industrial reliability" in result.warning

    sorted_results = result.by_metric("f1")
    assert sorted_results[0].model_name == "random_forest"
    assert sorted_results[0].metrics.f1 == 0.85


def test_partial_failure():
    import_import_error = ImportError("xgboost not available")

    outcomes = {
        "logistic_regression": TrainingResult(
            model_name="logistic_regression",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.70),
        ),
        "random_forest": TrainingResult(
            model_name="random_forest",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.85),
        ),
        "gradient_boosting": TrainingResult(
            model_name="gradient_boosting",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.60),
        ),
        "xgboost": import_import_error,
    }
    trainer = _FakeTrainer(outcomes)
    service = ComparisonService(trainer=trainer, selected_metric="f1")
    result = service.compare(frame=_make_frame(), target=_make_target())

    statuses = {r.model_name: r.status for r in result.results}
    assert statuses["xgboost"] == "unavailable"
    assert statuses["logistic_regression"] == "success"
    assert result.best_model == "random_forest"
    assert len(result.successful()) == 3


def test_no_model_success():
    outcomes = {
        "logistic_regression": ImportError("sklearn unavailable"),
        "random_forest": ImportError("sklearn unavailable"),
        "gradient_boosting": ImportError("fallback unavailable"),
        "xgboost": ImportError("xgboost unavailable"),
    }
    trainer = _FakeTrainer(outcomes)
    service = ComparisonService(trainer=trainer, selected_metric="f1")
    result = service.compare(frame=_make_frame(), target=_make_target())

    assert result.best_model is None
    assert len(result.successful()) == 0
    assert all(r.status == "unavailable" for r in result.results)


def test_model_error_status():
    outcomes = {
        "logistic_regression": ModelError("bad model config"),
        "random_forest": TrainingResult(
            model_name="random_forest",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.85),
        ),
        "gradient_boosting": TrainingResult(
            model_name="gradient_boosting",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.60),
        ),
        "xgboost": TrainingResult(
            model_name="xgboost",
            model_version="v1",
            artifact_path=None,
            metrics=_metrics(0.75),
        ),
    }
    trainer = _FakeTrainer(outcomes)
    service = ComparisonService(trainer=trainer, selected_metric="f1")
    result = service.compare(frame=_make_frame(), target=_make_target())

    statuses = {r.model_name: r.status for r in result.results}
    assert statuses["logistic_regression"] == "failed"
    assert result.best_model == "random_forest"


def test_to_dict_contains_keys():
    trainer = _FakeTrainer({})
    service = ComparisonService(trainer=trainer, selected_metric="f1")
    result = service.compare(frame=_make_frame(), target=_make_target())
    d = result.to_dict()
    for key in ("results", "selected_metric", "best_model", "warning"):
        assert key in d
        for r in d["results"]:
            for key in (
                "model_name",
                "display_name",
                "status",
                "config",
                "metrics",
            ):
                assert key in r
