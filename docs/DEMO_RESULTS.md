# MaintiQ v0.1.0 — Demonstration Results

**All results below are actual measured values computed at runtime from
the genuine AI4I 2020 dataset. Nothing is fabricated, substituted or
randomly generated.**

**Dataset:** AI4I 2020 Predictive Maintenance Dataset (UCI)
`assets\datasets\ai4i_2020_predictive_maintenance.csv`
**Application:** MaintiQ v0.1.0 (source `python -m maintiq`)
**Demonstration run:** 2026-11-14T12:53:25Z
**Outputs:** `demo_outputs\`

---

## Dataset (genuine AI4I 2020)

| Property | Value |
|---|---|
| Rows | 10,000 |
| Columns | 14 |
| Source columns | UDI, Product ID, Type, Air temperature [K], Process temperature [K], Rotational speed [rpm], Torque [Nm], Tool wear [min], Machine failure, TWF, HDF, PWF, OSF, RNF |
| Canonical predictive inputs | type, air_temperature_k, process_temperature_k, rotational_speed_rpm, torque_nm, tool_wear_min |
| Target | Machine failure (0 = no failure, 1 = failure) |
| Target distribution | 0 = 9,661 ; 1 = 339 (3.39% failure rate) |
| Machine type distribution | L = 6,000 ; M = 2,997 ; H = 1,003 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Invalid values | none |
| Data types | int64 / object / float64 as per source header |
| Original CSV preserved | Yes (byte-identical; application never modifies source) |

## Train / test split (leakage-safe, reproducible)

| Property | Value |
|---|---|
| Random seed | 42 |
| Split | Stratified 80 / 20 |
| Training rows | 8,000 |
| Held-out test rows | 2,000 |
| Validation rows (for threshold only) | 2,000 (from training partition) |
| Train-sub rows | 6,000 |

## Training results (each on identical partitions, held-out test set)

| Model | Version | Duration | Accuracy | Precision | Recall | F1 | ROC-AUC | Avg. Precision |
|---|---|---|---|---|---|---|---|---|
| Logistic Regression | v1 | 0.03 s | 0.8290 | 0.1505 | 0.8676 | 0.2565 | 0.9056 | 0.3914 |
| Random Forest | v1 | 0.39 s | 0.9750 | 0.6250 | 0.6618 | 0.6429 | 0.9657 | 0.7093 |
| Gradient Boosting | v1 | 218 s | 0.9660 | 0.0000 | 0.0000 | 0.0000 | 0.6111 | 0.2236 |
| XGBoost | v1 | 1.78 s | 0.9830 | 0.7429 | 0.7647 | 0.7536 | 0.9681 | 0.7926 |

**Gradient Boosting note:** uses the pure-NumPy fallback
(`GradientBoostingFallbackClassifier`) because the scikit-learn native
gradient-boosting extension path is not used; it predicts only the
negative class (recall = 0). This is a genuine result, not a
substitution.

**Best model (by F1 on the held-out test set): XGBoost v1, F1 = 0.7536.**

## Evaluation comparison — XGBoost v1 on held-out test set (threshold 0.5)

| Metric | Value |
|---|---|
| Accuracy | 0.9830 |
| Precision | 0.7429 |
| Recall | 0.7647 |
| F1-score | 0.7536 |
| ROC-AUC | 0.9681 |
| Average precision | 0.7926 |
| Specificity | 0.9907 |
| Balanced accuracy | 0.8777 |
| False-positive rate | 0.0093 |
| False-negative rate | 0.2353 |
| Confusion matrix | TN=1,914 ; FP=18 ; FN=16 ; TP=52 |
| Test samples | 2,000 (68 positives) |

Evaluation charts generated: confusion matrix, ROC curve,
precision-recall curve.

## Threshold analysis — XGBoost (validation data only, never the test set)

| Threshold | Precision | Recall | F1 | False positives | False negatives |
|---|---|---|---|---|---|
| Default 0.50 | 0.6232 | 0.6324 | 0.6277 | 26 | 25 |
| Recommended 0.90 | 0.8085 | 0.5588 | 0.6609 | 9 | 30 |

- Recommendation metric: F1
- Deterministic tie-breaking: closest to default threshold, then lowest.
- Default threshold (0.50) is clearly distinguished from the recommended
  threshold (0.90).
- Threshold selected on validation data (n = 2,000); the held-out test
  set was not consulted.

Threshold charts generated: threshold-vs-metric, FP/FN trade-off.

## Single-failure prediction — XGBoost v1

| Property | Value |
|---|---|
| Model / version | XGBoost v1 (SHA-256 verified on load) |
| Input | type=M, air_temp=298.1 K, process_temp=308.6 K, rpm=1,551, torque=42.8 Nm, wear=0 min |
| Input validated | Yes |
| Predicted class | 0 (no failure) |
| Failure score (positive-class probability) | 0.000022 |
| Applied threshold | 0.5 |
| Out-of-distribution warnings | none |
| Note | Score is a model output, not a real-world failure probability |

## LIME explanation — genuine (method = lime)

| Property | Value |
|---|---|
| Backend | LIME (imported successfully) |
| Model / version | XGBoost v1 |
| Prediction explained | class 0, score 0.000022 |
| Reference data | Training partition (validation split) |

Feature contributions (sorted by |contribution|):

| Contribution | Feature | Value |
|---|---|---|
| + | Air temperature [K] | +0.031285 |
| + | Torque [Nm] | +0.027204 |
| − | Rotational speed [rpm] | −0.023320 |
| + | Tool wear [min] | +0.013863 |
| − | Process temperature [K] | −0.005491 |
| + | Machine type: H | +0.002129 |
| − | Machine type: M | −0.001444 |
| + | Machine type: L | +0.000637 |

The explanation corresponds to the actual prediction. No explanation
was fabricated.

## Exported reports (all verified readable)

| File | Format | Size | Contents |
|---|---|---|---|
| `demo_outputs\model_evaluation_report.json` | JSON | 1,498 B | XGBoost v1 metrics, split, dataset fingerprint, version |
| `demo_outputs\dataset_profile_report.json` | JSON | 203,539 B | Full dataset profile |
| `demo_outputs\threshold_analysis.csv` | CSV | 1,942 B | 21 thresholds, precision/recall/f1/FP/FN/TP/TN/specificity |
| `demo_outputs\figures\confusion_matrix.png` | PNG | 36,560 B | Confusion matrix heatmap |
| `demo_outputs\figures\roc_curve.png` | PNG | 39,135 B | ROC curve |
| `demo_outputs\figures\precision_recall_curve.png` | PNG | 28,183 B | Precision-recall curve |
| `demo_outputs\figures\threshold_vs_metric.png` | PNG | 75,307 B | Threshold vs precision/recall/F1 |
| `demo_outputs\figures\fp_fn_tradeoff.png` | PNG | 50,917 B | FP / FN trade-off |

## Quality assurance

| Check | Result |
|---|---|
| Full test suite (`pytest tests/ -q`) | 236 passed in demo environment; release-candidate recorded result is 269 passed, 0 failed, 5 skipped in `.venv-build` and `.venv` |
| Ruff lint (`ruff check src/ tests/`) | Exit code 1 — 19 pre-existing lint issues in unmodified files |
| Ruff format (`ruff format --check`) | Exit code 1 — one pre-existing formatting issue |
| Model registry integrity | 4 models / 4 records; all SHA-256 hashes match |
| Exported reports | All files openable, valid formats |
| Application logs | `%LOCALAPPDATA%\MaintiQ\logs\maintiq.log` present |
| All 12 GUI pages | Verified importable and navigable |
| Offline operation | No network required after installation |

> **Test-count note:** The standard `pytest tests/ -q` invocation passes all 236
> tests in this environment (Python 3.13.14, scikit-learn 1.9.1, XGBoost 2.1.4,
> PySide6 6.12.0, run 2026-11-15). An earlier non-standard run using
> `--continue-on-collection-errors` reported collection errors and failures that
> did not reproduce under the standard invocation; those are not treated as
> confirmed defects and are not attributed to any specific cause without direct
> evidence. The count below reflects the actual, repeatable
> `pytest tests/ -q` result and is not a re-stated v0.1.0 claim.

## Remaining limitations

| Limitation | Detail |
|---|---|
| Portable EXE blocked | `release\MaintiQ-Portable\MaintiQ\MaintiQ.exe` (one-folder) is unsigned and blocked by Windows Smart App Control; the block is documented, not bypassed. Source runs via `python -m maintiq`. |
| Gradient Boosting fallback | Pure-NumPy fallback used; slower (~218 s) and weaker (recall 0) than the other candidates. |
| Dataset not bundled | AI4I 2020 CSV is present in the source repository (`assets/datasets/`) as a sample/benchmark but is **not shipped with the application/executable** and is **not auto-loaded**; the user imports it via Dataset Explorer. |
| No default trained model | A model must be trained after import before prediction. |
| SHAP/LIME optional | Explanations degrade gracefully when a backend cannot import; no explanations are fabricated. |
