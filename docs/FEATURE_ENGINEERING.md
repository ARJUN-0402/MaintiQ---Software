# Feature Engineering — MaintiQ

Engineered features required by the MaintiQ synopsis, implemented in
`src/maintiq/ml/features/transformer.py` as a single scikit-learn-compatible
transformer (`FeatureEngineeringTransformer`) so training and prediction use
identical formulas.

## Engineered features

| Feature | Formula | Unit | Notes |
|---|---|---|---|
| `temperature_diff` | `process_temperature_k - air_temperature_k` | K | Difference between process and air temperature. |
| `power_kw` | `torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000` | kW | Derived mechanical power estimate from torque (Nm) and rotational speed (rpm). |
| `wear_rate` | `tool_wear_min / 253.0` | normalised (≈0..1) | Normalised wear **proxy**, not a wear-per-time rate. A single snapshot has no elapsed-time denominator, so a true wear rate cannot be computed. `253.0` is the documented AI4I ``Tool wear [min]`` range. |
| `torque_normalized` | `torque_nm / max_torque_train` | normalised | `max_torque_train` is learned only from the training partition by a fitted transformer and persisted with the model. No test-data leakage. Zero/invalid reference falls back to 1.0. |
| `temp_wear_interaction` | `temperature_diff * tool_wear_min` | K·min | Interaction between temperature difference and tool wear. |

## Fitting behaviour

* `fit` learns `max_torque_train` from the training data passed to it **only**.
* The fitted transformer is bundled inside each model pipeline (Phase 4), so
  inference applies exactly the training-time transformation.
* `transform` appends the five engineered features to the six raw predictive
  inputs and returns all eleven columns.
* Unknown `Type` values are not a concern here (Type is categorical and passed
  through; encoding happens in preprocessing).

## Edge cases

* Zero torque or zero rotational speed → `power_kw` is 0.0.
* Zero or invalid `max_torque_train` → reference falls back to 1.0 so
  `torque_normalized` is 0.0 rather than undefined.
* Missing required columns or non-finite numeric values raise
  `FeatureEngineeringError` with an actionable message.

## Formulas in metadata

`FeatureEngineeringTransformer.formulas()` and `.metadata()` return the
formula, unit, and limitation description for every engineered feature; these
are recorded in model metadata (Phase 4) and reports (Phase 9).
