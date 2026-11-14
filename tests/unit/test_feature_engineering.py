"""Formula-level tests for feature engineering with hand-calculated values."""

import math

import numpy as np
import pandas as pd
import pytest

from maintiq.core.exceptions import FeatureEngineeringError
from maintiq.ml.features import (
    OUTPUT_COLUMNS,
    POWER_KW,
    TEMP_WEAR_INTERACTION,
    TEMPERATURE_DIFF,
    TORQUE_NORMALIZED,
    WEAR_RATE,
    FeatureEngineeringTransformer,
    power_kw,
)


def _row(**overrides):
    base = {
        "type": "L",
        "air_temperature_k": 300.0,
        "process_temperature_k": 310.0,
        "rotational_speed_rpm": 1500.0,
        "torque_nm": 60.0,
        "tool_wear_min": 253.0,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def test_all_engineered_features_present():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row())
    assert list(out.columns) == list(OUTPUT_COLUMNS)
    assert set(OUTPUT_COLUMNS).issubset(set(out.columns))


def test_temperature_diff():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row())
    assert out.iloc[0][TEMPERATURE_DIFF] == pytest.approx(10.0)


def test_power_kw_hand_calculated():
    # 60 Nm * 1500 rpm * (2*pi/60) / 1000
    expected = 60.0 * 1500.0 * (2.0 * math.pi / 60.0) / 1000.0
    assert power_kw(60.0, 1500.0) == pytest.approx(expected)
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row())
    assert out.iloc[0][POWER_KW] == pytest.approx(expected, rel=1e-9)


def test_power_kw_zero_torque_and_speed():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row(torque_nm=0.0, rotational_speed_rpm=0.0))
    assert out.iloc[0][POWER_KW] == 0.0


def test_wear_rate_is_normalised_proxy():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row())
    assert out.iloc[0][WEAR_RATE] == pytest.approx(253.0 / 253.0)
    assert out.iloc[0][WEAR_RATE] == pytest.approx(1.0)


def test_torque_normalized_learned_from_fit_only():
    # Fit on a frame whose max torque is 100, then transform a row with 50 Nm.
    train = pd.DataFrame(
        [
            {
                "type": "M",
                "air_temperature_k": 300.0,
                "process_temperature_k": 310.0,
                "rotational_speed_rpm": 1500.0,
                "torque_nm": 100.0,
                "tool_wear_min": 100.0,
            }
        ]
    )
    transformer = FeatureEngineeringTransformer()
    transformer.fit(train)
    assert transformer.max_torque_train == pytest.approx(100.0)
    out = transformer.transform(_row(torque_nm=50.0))
    assert out.iloc[0][TORQUE_NORMALIZED] == pytest.approx(0.5)


def test_torque_normalized_safe_when_max_torque_zero():
    train = pd.DataFrame(
        [
            {
                "type": "L",
                "air_temperature_k": 300.0,
                "process_temperature_k": 310.0,
                "rotational_speed_rpm": 1500.0,
                "torque_nm": 0.0,
                "tool_wear_min": 10.0,
            }
        ]
    )
    transformer = FeatureEngineeringTransformer()
    transformer.fit(train)
    # Falls back to reference 1.0 so normalised torque is 0.0, not inf.
    assert transformer.max_torque_train == 1.0
    out = transformer.transform(_row(torque_nm=60.0))
    assert out.iloc[0][TORQUE_NORMALIZED] == pytest.approx(60.0 / 1.0)


def test_temp_wear_interaction():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    out = transformer.transform(_row())
    assert out.iloc[0][TEMP_WEAR_INTERACTION] == pytest.approx(10.0 * 253.0)


def test_missing_columns_raises():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    bad = _row().drop(columns=["torque_nm"])
    with pytest.raises(FeatureEngineeringError):
        transformer.transform(bad)


def test_non_finite_values_raise():
    transformer = FeatureEngineeringTransformer()
    transformer.fit(_row())
    bad = _row(air_temperature_k=np.nan)
    with pytest.raises(FeatureEngineeringError):
        transformer.transform(bad)


def test_transform_before_fit_raises():
    with pytest.raises(FeatureEngineeringError):
        FeatureEngineeringTransformer().transform(_row())


def test_train_inference_use_identical_transformer():
    train = pd.DataFrame(
        [
            {
                "type": "L",
                "air_temperature_k": 300.0,
                "process_temperature_k": 310.0,
                "rotational_speed_rpm": 1500.0,
                "torque_nm": 60.0,
                "tool_wear_min": 253.0,
            },
            {
                "type": "M",
                "air_temperature_k": 305.0,
                "process_temperature_k": 315.0,
                "rotational_speed_rpm": 1600.0,
                "torque_nm": 80.0,
                "tool_wear_min": 120.0,
            },
        ]
    )
    transformer = FeatureEngineeringTransformer()
    train_out = transformer.fit_transform(train)
    single_out = transformer.transform(train.iloc[[0]])
    pd.testing.assert_series_equal(train_out.iloc[0], single_out.iloc[0])


def test_formulas_and_metadata_documented():
    formulas = FeatureEngineeringTransformer.formulas()
    assert TEMPERATURE_DIFF in formulas
    assert POWER_KW in formulas
    assert WEAR_RATE in formulas
    assert TORQUE_NORMALIZED in formulas
    assert TEMP_WEAR_INTERACTION in formulas
    metadata = FeatureEngineeringTransformer.metadata()
    assert "proxy" in metadata[WEAR_RATE]["description"].lower()
    assert "training" in metadata[TORQUE_NORMALIZED]["description"].lower()
