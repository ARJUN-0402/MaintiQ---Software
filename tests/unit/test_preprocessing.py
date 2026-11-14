"""Tests for the preprocessing pipeline."""

import copy

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import PreprocessingError
from maintiq.ml.preprocessing import (
    NUMERIC_COLUMNS,
    Preprocessor,
    split_train_test,
)


def _make_frame(n=20):
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


def _make_target(n=20):
    rng = np.random.default_rng(3)
    return pd.Series(rng.integers(0, 2, size=n), name="machine_failure")


def test_missing_value_handling():
    """Missing numeric values are imputed; missing categorical uses most frequent."""
    frame = _make_frame(10)
    frame.loc[0, "torque_nm"] = np.nan
    frame.loc[1, "type"] = np.nan
    target = _make_target(10)

    preprocessor = Preprocessor(random_seed=42)
    transformed, _ = preprocessor.fit_transform(frame, target)

    assert not transformed.isna().any().any()
    assert "type" not in transformed.columns or transformed.shape[1] > 0


def test_categorical_encoding():
    """Type is one-hot encoded into separate columns."""
    frame = _make_frame(10)
    target = _make_target(10)
    preprocessor = Preprocessor(random_seed=42)
    transformed, _ = preprocessor.fit_transform(frame, target)

    cat_cols = [c for c in transformed.columns if c.startswith("cat__")]
    assert len(cat_cols) == 3  # L, M, H
    assert set(cat_cols) == {"cat__type__L", "cat__type__M", "cat__type__H"}
    # Each row has exactly one active category.
    row_sums = transformed[cat_cols].sum(axis=1)
    assert (row_sums == 1.0).all()


def test_unknown_category_does_not_crash():
    """Unseen Type values are encoded as all-zeros and surfaced by detection."""
    train = _make_frame(10)
    target = _make_target(10)
    preprocessor = Preprocessor(random_seed=42)
    preprocessor.fit(train, target)

    inference = copy.deepcopy(train)
    inference.loc[0, "type"] = "Z"  # unseen category

    unknown = preprocessor.detect_unknown_categories(inference)
    assert unknown == {"type": ["Z"]}

    transformed = preprocessor.transform(inference)
    assert not transformed.isna().any().any()
    # The unseen row has all category columns equal to zero.
    cat_cols = [c for c in transformed.columns if c.startswith("cat__")]
    assert (transformed.loc[0, cat_cols] == 0.0).all()


def test_train_test_separation():
    """The preprocessor is fitted on the training partition only."""
    frame = _make_frame(40)
    target = _make_target(40)
    train_frame, test_frame, _, _, _ = split_train_test(
        frame, target, test_size=0.25, random_state=42
    )

    preprocessor = Preprocessor(random_seed=42)
    preprocessor.fit(train_frame, None)

    # Median imputation learned from training data.
    assert preprocessor.is_fitted()
    train_median = train_frame[list(NUMERIC_COLUMNS)].median()
    for col in NUMERIC_COLUMNS:
        assert preprocessor._numeric_fill[col] == pytest.approx(float(train_median[col]))

    # Transforming the holdout works without refitting.
    transformed_test = preprocessor.transform(test_frame)
    assert not transformed_test.isna().any().any()


def test_deterministic_splits():
    """Same seed produces the same split; different seed differs."""
    frame = _make_frame(40)
    target = _make_target(40)

    t1 = split_train_test(frame, target, test_size=0.25, random_state=42)
    t2 = split_train_test(frame, target, test_size=0.25, random_state=42)
    t3 = split_train_test(frame, target, test_size=0.25, random_state=99)

    pd.testing.assert_frame_equal(t1[0], t2[0])
    pd.testing.assert_series_equal(t1[2], t2[2])
    assert not t1[0].equals(t3[0])
    assert t1[4].n_train == t2[4].n_train
    assert t1[4].n_test == t2[4].n_test


def test_split_holds_out_test():
    """Train and test partitions are disjoint and together cover the data."""
    frame = _make_frame(40)
    target = _make_target(40)
    train_frame, test_frame, _, _, settings = split_train_test(
        frame, target, test_size=0.25, random_state=42
    )
    assert len(train_frame) + len(test_frame) == len(frame)
    assert settings.n_train + settings.n_test == len(frame)
    assert settings.test_size == 0.25
    assert settings.random_state == 42
    assert settings.stratify is True


def test_pipeline_serialization_round_trip(tmp_path):
    """A fitted preprocessor can be saved and loaded and transforms consistently."""
    frame = _make_frame(20)
    target = _make_target(20)
    preprocessor = Preprocessor(random_seed=42, scale_numeric=True)
    preprocessor.fit(frame, target)
    transformed_before = preprocessor.transform(frame)

    path = tmp_path / "preprocessor.joblib"
    preprocessor.save(path)

    loaded = Preprocessor.load(path)
    transformed_after = loaded.transform(frame)

    pd.testing.assert_frame_equal(transformed_before, transformed_after)
    assert loaded.output_columns == preprocessor.output_columns
    assert loaded.input_columns == preprocessor.input_columns


def test_transformed_column_consistency():
    """Transformed columns are stable across train-style and single-record frames."""
    frame = _make_frame(20)
    target = _make_target(20)
    preprocessor = Preprocessor(random_seed=42)
    preprocessor.fit(frame, target)

    single = frame.iloc[[0]].copy()
    full_out = preprocessor.transform(frame)
    single_out = preprocessor.transform(single)

    assert list(full_out.columns) == list(single_out.columns)
    assert len(single_out) == 1


def test_excluded_columns_absent():
    """Excluded identifier / failure-mode columns are never part of preprocessing."""
    frame = _make_frame(10)
    frame["udi"] = range(10)
    frame["product_id"] = [f"P{i}" for i in range(10)]
    frame["twf"] = 0
    target = _make_target(10)

    preprocessor = Preprocessor(random_seed=42)
    preprocessor.fit(frame, target)
    transformed = preprocessor.transform(frame)

    for excluded in ("udi", "product_id", "twf", "hdf", "pwf", "osf", "rnf"):
        assert excluded not in transformed.columns
    # Only transformed predictive features remain.
    assert set(transformed.columns) == set(preprocessor.output_columns)


def test_transform_before_fit_raises():
    frame = _make_frame(5)
    preprocessor = Preprocessor(random_seed=42)
    with pytest.raises(PreprocessingError):
        preprocessor.transform(frame)


def test_no_nan_or_inf_for_valid_input():
    frame = _make_frame(20)
    target = _make_target(20)
    preprocessor = Preprocessor(random_seed=42)
    transformed, _ = preprocessor.fit_transform(frame, target)

    numeric = transformed.select_dtypes(include=[np.number])
    assert np.isfinite(numeric.to_numpy()).all()
    assert not transformed.isna().any().any()


def test_scale_numeric_flag():
    """Numeric scaling is optional and documented via scale_numeric."""
    frame = _make_frame(10)
    target = _make_target(10)
    unscaled = Preprocessor(scale_numeric=False, random_seed=42)
    unscaled.fit(frame, target)
    scaled = Preprocessor(scale_numeric=True, random_seed=42)
    scaled.fit(frame, target)

    # Scaled output has approximately zero mean per numeric feature.
    num_cols = [c for c in scaled.output_columns if c.startswith("num__")]
    scaled_means = scaled.transform(frame)[num_cols].mean()
    for mean in scaled_means:
        assert abs(mean) < 1e-6

    unscaled_means = unscaled.transform(frame)[
        [c for c in unscaled.output_columns if c.startswith("num__")]
    ].mean()
    assert any(abs(m) > 1e-6 for m in unscaled_means)
