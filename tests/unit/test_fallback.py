"""Tests for the pure-NumPy gradient-boosting fallback classifier."""

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import ModelError
from maintiq.ml.training._fallback import GradientBoostingFallbackClassifier


def _make_frame(n=100):
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "f0": rng.uniform(0, 10, size=n),
            "f1": rng.uniform(0, 10, size=n),
            "f2": rng.uniform(0, 10, size=n),
        }
    )


def _make_target(n=100, pos_frac=0.3):
    rng = np.random.default_rng(3)
    return pd.Series((rng.random(n) < pos_frac).astype(int), name="machine_failure")


def test_fit_predict_binary():
    clf = GradientBoostingFallbackClassifier(n_estimators=20, learning_rate=0.1, random_seed=42)
    x = _make_frame(100).to_numpy(dtype=float)
    y = _make_target(100).to_numpy()
    clf.fit(x, y)
    assert len(clf.estimators_) == 20
    preds = clf.predict(x)
    assert preds.shape == (100,)
    assert set(np.unique(preds)).issubset({0, 1})


def test_predict_proba_shape_and_range():
    clf = GradientBoostingFallbackClassifier(n_estimators=10, random_seed=42)
    x = _make_frame(50).to_numpy(dtype=float)
    y = _make_target(50).to_numpy()
    clf.fit(x, y)
    proba = clf.predict_proba(x)
    assert proba.shape == (50, 2)
    assert np.all((proba >= 0.0) & (proba <= 1.0))
    assert np.allclose(proba.sum(axis=1), 1.0)


def test_single_class_raises():
    clf = GradientBoostingFallbackClassifier(n_estimators=5, random_seed=42)
    x = _make_frame(20).to_numpy(dtype=float)
    y = np.zeros(20, dtype=int)
    with pytest.raises(ModelError):
        clf.fit(x, y)


def test_deterministic():
    x = _make_frame(60).to_numpy(dtype=float)
    y = _make_target(60).to_numpy()
    c1 = GradientBoostingFallbackClassifier(n_estimators=15, random_seed=1)
    c2 = GradientBoostingFallbackClassifier(n_estimators=15, random_seed=1)
    c1.fit(x, y)
    c2.fit(x, y)
    np.testing.assert_array_equal(c1.predict(x), c2.predict(x))
    np.testing.assert_allclose(c1.predict_proba(x), c2.predict_proba(x))
