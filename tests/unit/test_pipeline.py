"""Tests for the ModelPipeline bundling preprocessing, features and estimator."""

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import ModelError
from maintiq.ml.features import FeatureEngineeringTransformer
from maintiq.ml.preprocessing import Preprocessor, split_train_test
from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier
from maintiq.ml.training.pipeline import ModelPipeline


def _make_frame(n=80):
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


def _make_target(n=80, pos_frac=0.3):
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < pos_frac).astype(int), name="machine_failure")


def _make_pipeline():
    return ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=None,
    )


def _feature_transformer():
    return FeatureEngineeringTransformer()


def test_fit_predict_end_to_end(tmp_path):
    frame = _make_frame(80)
    target = _make_target(80)
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=_feature_transformer(),
    )
    pipeline.fit(frame, target)
    assert pipeline.is_fitted

    preds = pipeline.predict(frame)
    assert preds.shape == (80,)
    assert set(np.unique(preds)).issubset({0, 1})

    proba = pipeline.predict_proba(frame)
    assert proba.shape == (80, 2)
    assert np.all((proba >= 0.0) & (proba <= 1.0))


def test_predict_before_fit_raises():
    pipeline = _make_pipeline()
    with pytest.raises(ModelError):
        pipeline.predict(_make_frame(10))


def test_predict_proba_before_fit_raises():
    pipeline = _make_pipeline()
    with pytest.raises(ModelError):
        pipeline.predict_proba(_make_frame(10))


def test_save_load_round_trip(tmp_path):
    frame = _make_frame(60)
    target = _make_target(60)
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=_feature_transformer(),
    )
    pipeline.fit(frame, target)
    before = pipeline.predict_proba(frame)

    path = tmp_path / "pipeline.joblib"
    artifact = pipeline.save(path)
    assert artifact.model_name == "gradient_boosting"
    assert artifact.threshold == 0.5

    loaded = ModelPipeline.load(path)
    assert loaded.is_fitted
    after = loaded.predict_proba(frame)
    np.testing.assert_array_equal(before, after)
    np.testing.assert_array_equal(loaded.predict(frame), pipeline.predict(frame))


def test_threshold_controls_predictions():
    frame = _make_frame(60)
    target = _make_target(60)
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=_feature_transformer(),
        threshold=0.9,
    )
    pipeline.fit(frame, target)
    proba = pipeline.predict_proba(frame)
    expected = (proba[:, 1] >= 0.9).astype(int)
    np.testing.assert_array_equal(pipeline.predict(frame), expected)


def test_split_then_fit_holds_out_test():
    frame = _make_frame(80)
    target = _make_target(80)
    train_frame, test_frame, train_target, _test_target, _ = split_train_test(
        frame, target, test_size=0.25, random_state=42
    )
    pipeline = ModelPipeline(
        model_name="gradient_boosting",
        estimator=GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42),
        preprocessor=Preprocessor(random_seed=42),
        feature_transformer=_feature_transformer(),
    )
    pipeline.fit(train_frame, train_target)
    # Fitted on training only; transforming held-out works and is finite.
    proba = pipeline.predict_proba(test_frame)
    assert np.isfinite(proba).all()
    assert proba.shape[0] == len(test_frame)
