# Model Card — MaintiQ v0.2.0

## Model details

- **Project:** MaintiQ — Industrial Failure Prediction with Explainable Artificial Intelligence
- **Package:** `maintiq` (version `0.2.0`)
- **Purpose:** Academic decision-support prototype that predicts the binary `Machine failure` target from six operational sensor readings and explains model behaviour with SHAP and LIME where those optional dependencies are available.
- **Intended audience:** Students, instructors, and academic reviewers (Uttaranchal University BCA project scope). Not a certified industrial diagnostic product.
- **License:** MIT

## Intended use

Predict whether a machine will fail (`Machine failure = 1` vs `0`) based on:

- Machine type (`L`, `M`, `H`)
- Air temperature [K]
- Process temperature [K]
- Rotational speed [rpm]
- Torque [Nm]
- Tool wear [min]

The tool is desktop-based, offline after installation, and designed for single-record, human-reviewed decision support. Qualified human review is required before acting on any output.

## Do not use for

- Diagnosing real machinery or issuing maintenance instructions.
- Live factory telemetry, PLC, SCADA, or MES integration (none is implemented).
- Claims that benchmark results guarantee real factory performance.
- Calibrated real-world failure probabilities (scores are model estimates, not calibrated risks).
- Causal interpretation of SHAP/LIME contributions (they describe model behaviour, not causation).

## Training setup

- **Dataset:** AI4I 2020 Predictive Maintenance Dataset (UCI Machine Learning Repository). The dataset is **not bundled** in the repository; the user imports it via CSV (`assets/datasets/` is the sample location, currently empty).
- **Candidate models:** Logistic Regression, Random Forest, Gradient Boosting, XGBoost. Gradient Boosting uses a preserved pure-NumPy fallback (`GradientBoostingFallbackClassifier`) when the scikit-learn gradient-boosting native extension is unavailable.
- **Split:** stratified train/test split, random seed 42, untouched final holdout set evaluated after model selection.
- **Preprocessing:** training-fitted imputation, encoding (`handle_unknown` for unseen `Type` categories), and scaling, bundled inside each model pipeline with joblib.
- **Feature engineering:** `temperature_diff`, `power_kw`, `wear_rate_proxy` (normalised wear proxy, `tool_wear_min / 253.0`, not a temporal rate), `torque_normalized` (reference `max_torque` learned from training data only), `temp_wear_interaction`.
- **Class imbalance:** addressed with model-appropriate weights (e.g. XGBoost `scale_pos_weight`) computed from the training partition only — never from holdout data.
- **Model registry:** JSON-backed registry with monotonic versioning (v1, v2, …), per-model artefact SHA-256 hashes verified before load, atomic writes, path-traversal prevention.

## Evaluation

Evaluation runs on the untouched final holdout set and reports: accuracy, precision, recall, F1, ROC-AUC (null for single-class targets), confusion matrix (TN/FP/FN/TP), specificity, balanced accuracy, FPR, FNR, and average precision. Threshold analysis is leakage-safe: thresholds are chosen from validation scores only (never the test set), with deterministic tie-breaking and F1 maximisation as the default recommendation objective. Model comparison runs all four estimators on identical partitions; unavailable models are reported with an explicit status and reason.

No benchmark metrics or training results are claimed without the real AI4I dataset; automated tests use clearly labelled synthetic fixtures.

## Explainability

- **SHAP:** model-agnostic `shap.KernelExplainer` over the positive-class probability; works with all four estimators including the Gradient Boosting fallback. Raises a clear error when SHAP is unavailable (e.g. when `sklearn.cluster` native extensions are blocked by Windows Application Control/Smart App Control); never fabricates explanations.
- **LIME:** `lime.lime_tabular.LimeTabularExplainer` over the processed feature space; works end-to-end where `lime` is importable.
- Every explanation carries a non-causal disclaimer and describes model name/version, input record, predicted class, score, and threshold.

## Caveats and limitations

- Academic prototype using benchmark data; results are not certified industrial diagnoses.
- SHAP/LIME availability depends on the runtime environment (native `.pyd` extensions may be blocked by Windows security policies). The application reports unavailability explicitly and continues without explanations.
- Unsigned executable builds may be blocked by Windows Smart App Control; distribution requires an EV code-signed executable/installer or end-user bypass of the policy block.
- No default trained model is shipped; the user imports data and trains a model before predicting.
- Thresholds and metrics are analytical choices, not certified industrial settings.

## Version history

| Version | Date | Notes |
|---------|------|-------|
| 0.2.0 | 2026-11-14 | Version bump 0.1.0 → 0.2.0 (pyproject.toml, package metadata, installer script). Release documentation updated. No machine-learning functionality changed. Remaining limitations: code-signing certificate pending, Inno Setup installer compilation pending, clean-machine Smart App Control testing pending. |
| 0.1.0 | 2026-11-14 | Initial release: dataset ingestion, preprocessing, feature engineering, four-model training with registry, evaluation and threshold analysis, SHAP/LIME explanations, prediction engine, PySide6 desktop GUI, reports/exports, PyInstaller portable build and Inno Setup installer configuration. |
