# Data Dictionary — MaintiQ

Source: AI4I 2020 Predictive Maintenance Dataset (UCI Machine Learning Repository).
This dictionary documents the canonical schema used internally by MaintiQ.

## Canonical schema

All internal code uses the canonical names below. Source CSV headers are mapped
to canonical names at the data boundary (see `src/maintiq/data/schema.py`).

| Canonical name | Source header (AI4I 2020) | Type | Values / domain | Unit | Role |
|---|---|---|---|---|---|
| `type` | `Type` | Categorical | `L`, `M`, `H` | category | Predictive input |
| `air_temperature_k` | `Air temperature [K]` | Numeric | > 0 | Kelvin (K) | Predictive input |
| `process_temperature_k` | `Process temperature [K]` | Numeric | > 0 | Kelvin (K) | Predictive input |
| `rotational_speed_rpm` | `Rotational speed [rpm]` | Numeric | > 0 | rpm | Predictive input |
| `torque_nm` | `Torque [Nm]` | Numeric | >= 0 | Nm | Predictive input |
| `tool_wear_min` | `Tool wear [min]` | Numeric | >= 0 | minutes | Predictive input |
| `machine_failure` | `Machine failure` | Binary | `0` / `1` | flag | Target |

## Excluded columns (never predictive inputs)

| Source column | Reason for exclusion |
|---|---|
| `UDI` | Unique identifier; not predictive |
| `Product ID` | Identifier; not predictive |
| `TWF` | Target-derived failure-mode indicator (Tool Wear Failure) |
| `HDF` | Target-derived failure-mode indicator (Heat Dissipation Failure) |
| `PWF` | Target-derived failure-mode indicator (Power Failure) |
| `OSF` | Target-derived failure-mode indicator (Overstrain Failure) |
| `RNF` | Target-derived failure-mode indicator (Random Failure) |

Target-derived failure-mode columns are excluded to prevent target leakage.

## Engineered features

Implemented by `src/maintiq/ml/features/` (Phase 3). Documented in
`docs/FEATURE_ENGINEERING.md`:

| Feature | Formula | Unit | Notes |
|---|---|---|---|
| `temperature_diff` | `process_temperature_k - air_temperature_k` | K | - |
| `power_kw` | `torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000` | kW | Mechanical power estimate |
| `wear_rate_proxy` | `tool_wear_min / 253.0` | normalised | Normalised wear proxy, not a temporal rate |
| `torque_normalized` | `torque_nm / max_torque_train` | normalised | Reference learned from training data only |
| `temp_wear_interaction` | `temperature_diff * tool_wear_min` | K·min | - |

## Validation rules

- Required columns: all predictive inputs plus `Machine failure`.
- `Type` must be one of `L`, `M`, `H`.
- `Machine failure` must be binary `0`/`1`.
- Numeric inputs must be numeric and within physically meaningful domains
  (temperatures > 0, speed > 0, torque/tool wear >= 0).
- Duplicate rows and missing values are reported but not silently removed.

## Import policy

- Imported CSV files are treated as untrusted input.
- Maximum import size: 200 MB.
- No formulas, macros, scripts, or embedded content are executed.
- The original imported file is preserved; it is not silently modified.
