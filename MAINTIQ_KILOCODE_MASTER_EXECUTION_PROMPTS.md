# MaintiQ — Complete KiloCode Master Execution Prompt Pack

**Project:** MaintiQ  
**Project title:** Industrial Failure Prediction with Explainable Artificial Intelligence  
**Target:** Native Windows desktop application with an offline-capable `.exe` and installer  
**Academic basis:** The uploaded Uttaranchal University BCA project synopsis for MaintiQ  
**Execution style:** Build and verify the project phase by phase, without requiring a new prompt from the user after every phase.

---

# 0. HOW TO USE THIS FILE

1. Open the **new, empty project workspace** in KiloCode. Prefer a new folder named `MaintiQ-Desktop` so the existing MaintiQ repository is not overwritten.
2. Give KiloCode the **Master Execution Prompt** in Section 1 and make sure this file is available in the workspace as `MAINTIQ_KILOCODE_MASTER_EXECUTION_PROMPTS.md`.
3. Let KiloCode execute the phases in order. It must not skip acceptance checks or claim a phase is complete when tests fail.
4. If KiloCode reaches a tool, context, or execution limit, it must save its progress in `IMPLEMENTATION_STATUS.md` and stop with the exact continuation instruction. Resume by giving it the continuation prompt in Section 2.

The prompts below are deliberately detailed. They are intended to be used as a single project execution specification. KiloCode should implement them incrementally, not paste all code into one enormous file.

---

# 1. MASTER EXECUTION PROMPT — COPY THIS INTO KILOCODE

You are the lead software architect, Python desktop engineer, machine-learning engineer, QA engineer, and Windows packaging engineer for **MaintiQ**.

Your task is to build MaintiQ from scratch as a professionally structured, locally running Windows desktop application and deliver a tested Windows executable and installer. This file is the complete implementation specification. Read the entire file before changing the workspace. Execute Phases 0 through 12 in order.

## 1.1 Project definition

**Name:** MaintiQ  
**Full title:** Industrial Failure Prediction with Explainable Artificial Intelligence  
**Purpose:** An academic machine-learning-based predictive-maintenance decision-support prototype that predicts the binary `Machine failure` target using the AI4I 2020 Predictive Maintenance Dataset and explains model behaviour.

The application must support:

- Dataset loading, inspection, and validation.
- Input validation and data preprocessing.
- Feature engineering.
- Four candidate classifiers: Logistic Regression, Random Forest, Gradient Boosting, and XGBoost.
- Model evaluation using accuracy, precision, recall, F1-score, ROC-AUC, confusion matrix, and useful supporting metrics.
- Decision-threshold analysis.
- SHAP and LIME explanations where supported by the selected model.
- Single-record machine-failure prediction.
- Model metadata and model registry.
- Dataset, EDA, performance, threshold, prediction, and explanation reports.
- A native desktop graphical user interface.
- Offline application operation after installation, with no runtime dependency on a browser or hosted service.
- Windows executable packaging and a Windows installer.

## 1.2 Academic and safety boundaries — mandatory

The uploaded university synopsis is the source of truth for project scope. Preserve its core problem definition, objectives, dataset, target, candidate models, modules, reports, and limitations.

The application is an **academic prototype using benchmark data**. It is not a certified industrial diagnostic product. It must not:

- Claim to diagnose real machinery.
- Claim that benchmark results guarantee real factory performance.
- Connect to, control, or send commands to machinery.
- Claim live factory telemetry, PLC, SCADA, or MES integration.
- Present SHAP or LIME contributions as causal explanations.
- Present a model score as a guaranteed or calibrated real-world failure probability unless calibration is actually implemented and verified.
- Give maintenance instructions as if they were safety-certified.

Display a clear notice in the application and in generated reports: **“MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark dataset. Predictions and explanations are model outputs, not certified industrial diagnoses or maintenance instructions. Qualified human review is required.”**

The synopsis identifies these primary predictive inputs: `Type`, `Air temperature [K]`, `Process temperature [K]`, `Rotational speed [rpm]`, `Torque [Nm]`, and `Tool wear [min]`. The target is `Machine failure`. Exclude `UDI`, `Product ID`, and failure-mode indicator columns such as `TWF`, `HDF`, `PWF`, `OSF`, and `RNF` from predictive input features. Do not use target-derived or failure-mode columns as model inputs.

The synopsis names these engineered features: `temperature_diff`, `power`, `wear_rate`, `torque_normalized`, and `temp_wear_interaction`. Implement and document exact formulas consistently for training and inference. In particular:

- `temperature_diff = process_temperature - air_temperature`.
- `power_kw = torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000` when the source units are Nm and rpm. If the application retains the synopsis name `power`, document the unit and formula clearly.
- `wear_rate` cannot be a true time-based rate from a single snapshot because no elapsed-time denominator is supplied. Implement it only as a clearly documented **normalized wear proxy**, for example `tool_wear_min / 253.0` based on the documented AI4I feature range. Never describe it as an observed wear-per-time rate.
- `torque_normalized` must be calculated without test-data leakage. Prefer a train-fitted transformer using a training-only reference value, and persist that fitted transformer inside the model pipeline.
- `temp_wear_interaction = temperature_diff * tool_wear_min`.

If the dataset's actual column names differ, map the source columns explicitly and retain the canonical internal names. Document all formulas in code, tests, model metadata, and the user/developer documentation.

## 1.3 Technology decisions

Use the following stack unless a genuine compatibility issue requires a documented alternative:

- Python 3.11, 64-bit, as the initial supported build environment.
- PySide6 for the native desktop GUI.
- Pandas and NumPy for tabular data.
- Scikit-learn for preprocessing, pipelines, models, metrics, and validation.
- XGBoost for the XGBoost classifier.
- SHAP and LIME for model explanations.
- Matplotlib for desktop charts and exported figures. Plotly may be used for offline HTML report output only if it does not create a runtime browser dependency.
- Joblib for trusted, locally generated model-pipeline serialization.
- Pytest for automated tests.
- Ruff for linting and formatting checks.
- PyInstaller for application packaging.
- Inno Setup for a Windows installer when available.

Do not use Streamlit as the desktop UI. Do not use a web server, cloud service, mandatory account, API key, hosted database, or network connection in the normal application workflow. The desktop application must launch as a native Qt application.

Use a clean architecture:

`Presentation/UI → Application Services → Domain/ML Services → Data and Model Artefacts`

Keep UI code separate from data science and business logic. Use typed, testable modules. Use background workers for long-running training and explanation calculations so the UI does not freeze.

## 1.4 Workspace safety

- Inspect the workspace before modifying it.
- Do not delete, overwrite, or restructure an existing unrelated repository.
- Prefer creating `MaintiQ-Desktop` in the current workspace if the workspace is not already the dedicated new project directory.
- Do not copy old project artefacts blindly. This is a clean rebuild.
- Do not commit, push, publish, or upload anything to a remote repository unless explicitly requested.
- Do not put secrets, access tokens, or private data in source control.
- Do not fabricate datasets, model results, test results, screenshots, or completed features.
- If an optional tool (such as Inno Setup) is not installed, create the necessary configuration and clearly report the remaining local prerequisite rather than pretending the installer was built.

## 1.5 Execution workflow

Execute every phase in this file in order:

1. Read the phase prompt and inspect the current code.
2. Implement only that phase's scope, while keeping earlier interfaces stable.
3. Add or update automated tests.
4. Run the relevant tests and quality checks.
5. Fix failures before marking the phase complete.
6. Update `IMPLEMENTATION_STATUS.md` with changed files, implemented features, commands run, test results, known limitations, and the next phase.
7. Record a suggested Git commit message, but do not create commits or push unless requested.
8. Continue to the next phase automatically when the phase acceptance criteria pass. Do not ask the user to approve every phase.

Never mark a phase “complete” if its acceptance criteria are not met. If blocked by missing dataset access, unavailable installer tooling, or an environment limitation, implement the safest useful fallback, record the limitation, and continue where possible. Do not invent missing evidence.

If you hit a context or tool limit, save the exact state and next actions to `IMPLEMENTATION_STATUS.md`, then stop. Do not discard unfinished work.

## 1.6 Required project governance files

Maintain these files throughout development:

- `README.md` — project overview, setup, run instructions, features, architecture, limitations.
- `IMPLEMENTATION_STATUS.md` — phase tracker, completed work, test evidence, blockers, next action.
- `CHANGELOG.md` — meaningful implementation changes by phase.
- `docs/ARCHITECTURE.md` — architecture and module responsibilities.
- `docs/DATA_DICTIONARY.md` — source fields, target, exclusions, units, transformations.
- `docs/FEATURE_ENGINEERING.md` — exact formulas, units, fitting behaviour, and limitations.
- `docs/MODEL_CARD.md` — training setup, evaluation, caveats, and intended use.
- `docs/USER_GUIDE.md` — install, launch, workflow, imports, predictions, reports, troubleshooting.
- `docs/DEVELOPER_GUIDE.md` — environment, commands, tests, packaging, project layout.

## 1.7 Definition of done

The project is complete only when:

- All phases 0–10 pass their relevant tests and acceptance criteria.
- A user can install and launch the desktop application without installing Python separately.
- The application can use the AI4I dataset locally and can clearly guide the user to import the CSV if it is not bundled.
- Training, evaluation, prediction, explainability, and report generation work end to end.
- The app handles missing or incompatible model artefacts without crashing.
- The build is tested on Windows, or the exact limitation is clearly disclosed if the current environment is not Windows.
- A PyInstaller distribution is generated and smoke-tested.
- A `MaintiQ-Setup.exe` installer is generated and smoke-tested when Inno Setup is available.
- Documentation accurately distinguishes implemented features from future enhancements.

Now read and execute Sections 3–15 of this file in sequence.

---

# 2. CONTINUATION PROMPT — USE ONLY IF KILOCODE STOPS MIDWAY

Read `MAINTIQ_KILOCODE_MASTER_EXECUTION_PROMPTS.md` and `IMPLEMENTATION_STATUS.md` completely. Inspect the current workspace and Git status before making changes. Resume from the first incomplete or failed phase. Do not repeat completed work unnecessarily, do not skip failed acceptance checks, and do not overwrite existing work. Continue executing the remaining phases in order. Update `IMPLEMENTATION_STATUS.md` after each phase. Do not push or publish anything. If a blocker remains, implement a safe fallback where possible and document it accurately.

---

# 3. PHASE 0 — PROJECT FOUNDATION AND ARCHITECTURE

## Prompt

Establish the project foundation. Do not implement model training or the GUI yet.

### Tasks

1. Create a clean Python package and modular directory structure. Use `src/` layout where practical.
2. Create at least the following structure, adjusting names only when there is a clear architectural reason:

```text
MaintiQ-Desktop/
├── src/
│   └── maintiq/
│       ├── __init__.py
│       ├── app/
│       ├── core/
│       ├── data/
│       ├── domain/
│       ├── services/
│       ├── ml/
│       │   ├── preprocessing/
│       │   ├── features/
│       │   ├── training/
│       │   ├── evaluation/
│       │   ├── prediction/
│       │   └── explainability/
│       ├── registry/
│       ├── reporting/
│       └── ui/
├── assets/
│   ├── icons/
│   └── datasets/
├── config/
├── docs/
├── scripts/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── gui/
├── packaging/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .gitignore
├── README.md
├── CHANGELOG.md
└── IMPLEMENTATION_STATUS.md
```

3. Create centralized typed configuration for application name/version, supported models, random seed, default threshold, dataset locations, model storage, logs, reports, and app-data directories.
4. Use `pathlib.Path`. Do not use hard-coded absolute developer paths.
5. Separate development paths from user-data paths. For installed Windows use an appropriate per-user location such as `%LOCALAPPDATA%\MaintiQ` for writable datasets, models, registry, logs, settings, and reports. Never attempt to write generated files into a protected installation directory.
6. Create logging with a rotating file handler and useful log levels. Avoid logging full input records or sensitive information.
7. Create custom exception types for expected application errors.
8. Create package metadata and dependency groups. Pin compatible version ranges or constraints; do not pin unverified versions. Include only dependencies actually used.
9. Add `.gitignore` entries for virtual environments, caches, build outputs, secrets, local logs, temporary files, and generated user artefacts. Do not accidentally ignore source files or required small assets.
10. Create an initial test suite for configuration, paths, logging initialization, and package imports.
11. Create the first architecture description in `docs/ARCHITECTURE.md`.
12. Add initial README instructions for a Windows developer environment using Python 3.11.

### Engineering rules

- Use type hints and clear docstrings.
- Use dataclasses or small typed configuration objects where appropriate.
- Avoid giant modules, circular imports, unnecessary global state, and business logic in `main.py`.
- Keep imports side-effect-light.
- Do not create placeholder implementations that pretend a feature exists.

### Acceptance criteria

- The package imports successfully.
- Configuration resolves all configured paths.
- Writable runtime directories can be created safely.
- Logging can initialize and write a test message.
- `pytest` passes.
- `ruff check .` passes, or any narrowly scoped exception is documented.
- README and `IMPLEMENTATION_STATUS.md` are updated.

Suggested commit message: `chore: initialize MaintiQ desktop architecture`

---

# 4. PHASE 1 — DATASET INGESTION, SCHEMA, AND DATA QUALITY

## Prompt

Implement a robust dataset layer for the AI4I 2020 Predictive Maintenance Dataset. Do not train models yet.

### Dataset contract

Canonical predictive inputs:

- `Type` — categorical machine type, expected values `L`, `M`, `H`.
- `Air temperature [K]`.
- `Process temperature [K]`.
- `Rotational speed [rpm]`.
- `Torque [Nm]`.
- `Tool wear [min]`.

Target:

- `Machine failure` — binary target.

Exclude from predictive inputs:

- `UDI`.
- `Product ID`.
- Failure mode labels/indicators (`TWF`, `HDF`, `PWF`, `OSF`, `RNF`) and any other target-derived fields.

### Tasks

1. Implement a dataset schema module with canonical field names, source-to-canonical mapping, expected types, categorical values, target definition, exclusions, and unit descriptions.
2. Implement `DatasetLoader` for CSV loading with safe encoding/error handling and useful error messages.
3. Implement `DatasetValidator` to check required columns, duplicates, empty files, missing values, invalid types, unexpected categories, invalid target values, and impossible numeric values.
4. Do not silently delete rows or columns. Report detected problems and apply cleaning only in the later configured preprocessing pipeline.
5. Implement `DatasetProfiler` to calculate row/column counts, data types, missing-value counts, duplicate counts, numeric summaries, category counts, and target distribution.
6. Implement an import workflow service that can accept a user-selected CSV path and validate it before marking it as the active dataset.
7. Add a clear UI-independent API so the future desktop UI can call the data layer.
8. If the official dataset is available from the supplied workspace or can be obtained from the UCI source named in the synopsis, verify the file and include it only if redistribution terms permit. Never fabricate a replacement dataset. If not available, implement the import workflow and document how the user can obtain the official dataset.
9. Use a small synthetic dataframe only inside tests; label it clearly as test data and never present it as AI4I benchmark data.
10. Create/update `docs/DATA_DICTIONARY.md`.

### Security and reliability

- Treat imported CSV files as untrusted input.
- Limit unreasonable file sizes where practical and show clear validation errors.
- Do not execute formulas, macros, scripts, or embedded content from imported data.
- Preserve the original imported file; use application-managed copies or references according to a documented policy.

### Tests

Test valid CSV loading, missing columns, wrong target type, invalid category, missing values, duplicate rows, bad encoding, empty file, nonnumeric data in numeric fields, and failure-mode leakage exclusion.

### Acceptance criteria

- Valid AI4I-style data loads and reports a structured profile.
- Invalid files fail with actionable messages rather than an uncaught traceback.
- Predictive input selection excludes identifiers and failure-mode indicators.
- Dataset summary is deterministic for the same input.
- `pytest` and `ruff check .` pass.
- Update status and documentation.

Suggested commit message: `feat: implement dataset ingestion and validation`

---

# 5. PHASE 2 — PREPROCESSING PIPELINE

## Prompt

Implement leakage-safe, reproducible preprocessing for training and inference. Do not build the desktop GUI yet.

### Tasks

1. Build preprocessing with Scikit-learn-compatible transformers and pipelines.
2. Separate raw input columns from target and excluded columns.
3. Handle missing numeric values using an explicitly configured training-fitted imputation strategy. Handle categorical values using an appropriate most-frequent or explicit unknown-category strategy.
4. Encode `Type` using a fitted categorical encoder with `handle_unknown` behaviour that does not crash inference on an unseen category. Surface unknown categories clearly in validation.
5. Scale numeric features for Logistic Regression where appropriate. Tree-based models should not receive unnecessary scaling unless a shared pipeline makes it technically justified and documented.
6. Fit every imputer, encoder, scaler, and data-derived transformation on the training partition only. Do not fit preprocessing on the complete dataset before splitting.
7. Keep preprocessing bundled with the trained estimator so inference uses exactly the training-time transformation.
8. Add deterministic stratified train/test splitting with a configurable random seed. Keep a final holdout set untouched during model selection. Record split settings.
9. Provide clear APIs for `fit_transform` during training and `transform` during inference.
10. Implement feature-name tracking so evaluation and explainability can identify transformed columns.
11. Avoid oversampling the test set. Do not add SMOTE by default. Handle class imbalance using model-appropriate weights or training-only methods in the model-training phase.
12. Add serialization tests for a fitted preprocessing pipeline.

### Tests

Test missing-value handling, categorical encoding, unknown category behaviour, train/test separation, deterministic splits, pipeline serialization/deserialization, transformed column consistency, and absence of excluded columns.

### Acceptance criteria

- The same saved pipeline can transform training-style and single-record inference inputs consistently.
- No preprocessing object is fitted using holdout/test data.
- Transform output contains no unexpected NaN or infinite values for valid supported input.
- All tests and lint checks pass.
- Document preprocessing decisions and known limitations.

Suggested commit message: `feat: add leakage-safe preprocessing pipeline`

---

# 6. PHASE 3 — FEATURE ENGINEERING

## Prompt

Implement the engineered features required by the MaintiQ synopsis. Keep formulas in one reusable, testable transformer so training and prediction cannot drift apart.

### Required engineered features

1. `temperature_diff = process_temperature_k - air_temperature_k`.
2. `power_kw = torque_nm * rotational_speed_rpm * (2 * pi / 60) / 1000`. Document that this is a derived mechanical power estimate based on torque and rotational speed units.
3. `wear_rate_proxy = tool_wear_min / 253.0`. This is a normalized wear proxy, not a temporal rate. If the internal feature is named `wear_rate` for synopsis alignment, its documentation and UI label must explain the proxy limitation.
4. `torque_normalized = torque_nm / max_torque_train`, where `max_torque_train` is learned only from the training data by a fitted transformer. Handle zero or invalid reference values safely.
5. `temp_wear_interaction = temperature_diff * tool_wear_min`.

### Tasks

- Implement a Scikit-learn-compatible feature-engineering transformer with `fit`, `transform`, and feature-name support.
- Use canonical internal column names and map them to source dataset names at the data boundary.
- Preserve raw predictive features when useful; do not discard information without documenting the reason.
- Validate required columns and numeric domains before calculating derived fields.
- Handle inference rows and small test frames correctly.
- Record formulas, units, assumptions, and the training-fitted reference values in model metadata.
- Ensure feature engineering runs inside the model pipeline and is fitted only on each training fold/partition.
- Add formula-level unit tests with hand-calculated expected values.

### Acceptance criteria

- All five required engineered feature concepts are implemented and documented.
- Train and inference paths use the identical transformer implementation.
- The training-fitted torque normalization reference is not derived from the holdout set.
- Edge cases (zero torque, zero speed, missing columns, non-finite values) are handled predictably.
- Tests and lint checks pass.

Suggested commit message: `feat: implement predictive maintenance feature engineering`

---

# 7. PHASE 4 — MODEL TRAINING AND MODEL REGISTRY

## Prompt

Implement reproducible training for all four classifiers and a reliable local model registry. Use the preprocessing and feature-engineering pipelines from the previous phases.

### Required models

1. Logistic Regression.
2. Random Forest Classifier.
3. Gradient Boosting Classifier.
4. XGBoost Classifier.

### Tasks

1. Create a model factory that constructs models from validated configuration rather than scattered hard-coded parameters.
2. Use stratified train/test partitioning and reproducible random seeds.
3. Preserve an untouched final holdout test set. Use stratified cross-validation on the training partition for model selection when practical.
4. Account for class imbalance. For example, use class weights where supported and calculate XGBoost `scale_pos_weight` from the training partition only. Do not calculate imbalance weights using the holdout test data.
5. Keep the preprocessing and feature-engineering transformers inside each model's fitted pipeline.
6. Capture training duration, model parameters, library versions, dataset fingerprint, split seed, split proportions, feature list, target name, and training timestamp.
7. Expose training progress and cancellation-friendly boundaries for later GUI integration.
8. Save each completed pipeline using Joblib to the application-managed model directory.
9. Implement a JSON model registry with schema versioning, unique model version IDs, model name, artifact path, timestamp, parameters, metrics (when available), data fingerprint, feature list, and status.
10. Write registry updates atomically (temporary file followed by safe replacement). Handle malformed registry JSON gracefully without silently destroying it.
11. Calculate and store SHA-256 hashes for generated model artefacts. Verify hashes before loading registry-managed artefacts.
12. Only load model files created by the local application. Treat Joblib/pickle files from untrusted locations as unsafe; do not offer arbitrary model-file loading.
13. Provide a service to list registered models, inspect metadata, retrieve the active model, and select a model version.
14. Keep the registry metadata separate from large fitted artefacts.
15. Add a reproducible training script/CLI command for developers.

### Important evaluation boundary

Model fitting and cross-validation may use the training partition only. The final test partition must be evaluated after model selection and must not be repeatedly used to tune model parameters or thresholds.

### Tests

Test model factory configuration, one small training run per estimator, deterministic behaviour where supported, registry creation/update, atomic-write failure safety, artefact hash checking, missing artefacts, corrupted registry, and model load rejection on hash mismatch.

### Acceptance criteria

- All four estimators can be trained on a test fixture without leakage.
- Each trained pipeline can be saved and loaded.
- Registry metadata correctly points to the artifact and verifies its hash.
- No model is advertised as trained on AI4I data unless the real AI4I dataset was actually used.
- Training failures are reported clearly and do not corrupt existing models or the registry.
- All tests and lint checks pass.

Suggested commit message: `feat: train candidate models and add model registry`

---

# 8. PHASE 5 — MODEL EVALUATION AND THRESHOLD ANALYSIS

## Prompt

Implement evaluation and threshold analysis using saved model pipelines. Ensure the final holdout test set is evaluated only after training/model selection is complete.

### Required evaluation outputs

- Accuracy.
- Precision.
- Recall / sensitivity.
- F1-score.
- ROC-AUC where probability scores are available.
- Confusion matrix (TN, FP, FN, TP).

Also add useful imbalance-aware supporting measures such as specificity, balanced accuracy, and PR-AUC where technically supported. Label extra metrics clearly; do not replace the required metrics.

### Tasks

1. Implement a single evaluation service that accepts a fitted model pipeline, test data, true target, and threshold.
2. Safely handle models without `predict_proba`; use decision scores where appropriate for ranking metrics, or mark unavailable metrics as unavailable rather than fabricating a value.
3. Implement threshold sweeps on model scores, for example 0.05 to 0.95 at a documented step size, and calculate confusion matrix and metrics at each threshold.
4. Display the trade-off between false positives and false negatives. Do not imply that one threshold is universally best.
5. Provide configurable threshold-selection criteria for analysis (for example, highest F1 or a recall target with a stated precision constraint). Clearly label these as analytical choices, not certified industrial settings.
6. Do not optimize thresholds on the final holdout test data and then report those same data as unbiased evaluation. Use a validation partition or cross-validated training scores to choose a threshold; evaluate the chosen threshold once on the untouched holdout.
7. Create chart-ready data structures for ROC, precision-recall, confusion matrix, model comparison, and threshold curves.
8. Save metric summaries and evaluation metadata in JSON/CSV formats.
9. Store the evaluated model version, dataset fingerprint, split seed, threshold, and evaluation timestamp with results.
10. Include class imbalance and the meaning of false negatives in the evaluation documentation.

### Tests

Test metric calculations against known small arrays, confusion matrix ordering, threshold boundaries, missing probability support, single-class edge cases, ROC-AUC unavailable conditions, and prevention of test-set threshold tuning.

### Acceptance criteria

- Required metrics and confusion matrix are correct on controlled test examples.
- Threshold analysis produces reproducible values and labels the threshold-selection basis.
- Test-set leakage is prevented by service design and documented.
- Metrics are linked to the correct model version and dataset fingerprint.
- Tests and lint checks pass.

Suggested commit message: `feat: add model evaluation and threshold analysis`

---

# 9. PHASE 6 — EXPLAINABLE AI WITH SHAP AND LIME

## Prompt

Implement SHAP and LIME explanations for supported local MaintiQ model pipelines. Explanations must be framed as model-behaviour interpretations, never as causal proof.

### Tasks

1. Implement an explanation service independent of the GUI.
2. Support global explanation outputs such as feature importance/summary views where the selected model and explainer support them.
3. Support a local explanation for a single prediction.
4. Implement SHAP explainer selection based on model compatibility. Use a model-appropriate explainer or a documented model-agnostic fallback where necessary.
5. Implement LIME tabular explanations using the same feature order and preprocessing logic expected by the model.
6. Ensure explanations describe the exact model version, input record, target class, and threshold used for the displayed prediction.
7. Convert transformed feature names back to understandable feature labels where possible. Keep mappings explicit and testable.
8. Add background/reference sample selection that is deterministic and bounded in size for performance.
9. Run expensive calculations outside the GUI thread when later integrated.
10. Handle unsupported model/explainer combinations with a friendly “not available for this model” message rather than crashing.
11. Persist exportable explanation values and metadata where appropriate; avoid saving unnecessary raw personal data.
12. Explain that contribution values show how the model used features for a prediction and do not establish causation.

### Tests

Test explainer initialization, feature order consistency, local explanation output shape, global explanation output shape where supported, deterministic background sampling, invalid input handling, unsupported-model behaviour, and the non-causal explanation disclaimer.

### Acceptance criteria

- SHAP and LIME can explain a supported fitted model pipeline on a small test dataset.
- Explanation feature labels map correctly to model inputs.
- UI-independent explanation APIs return structured data and chart-ready values.
- Errors are handled gracefully and the disclaimer is present.
- Tests and lint checks pass.

Suggested commit message: `feat: add SHAP and LIME explainability services`

---

# 10. PHASE 7 — PREDICTION ENGINE AND APPLICATION SERVICES

## Prompt

Build the stable application service layer for single-record inference and orchestration. The GUI will be added in Phase 8.

### Supported input fields

- Machine type: `L`, `M`, or `H`.
- Air temperature in Kelvin.
- Process temperature in Kelvin.
- Rotational speed in rpm.
- Torque in Nm.
- Tool wear in minutes.

### Tasks

1. Implement a typed prediction input model and validation service.
2. Validate required fields, numeric types, finite values, valid machine type, and basic physically meaningful domains (for example, positive rotational speed and non-negative torque/tool wear).
3. Compare values with the training-data ranges when available. If values are outside the observed range, show an out-of-distribution warning; do not silently clamp them or imply the model is reliable outside its training distribution.
4. Retrieve the selected trusted registry model and verify its artefact hash before loading.
5. Apply the exact saved preprocessing and feature-engineering pipeline.
6. Return predicted class, model score/probability if supported, threshold, model name/version, timestamp, input validation warnings, and a user-friendly explanation of what the score represents.
7. Use “model-estimated score” or “model-estimated failure probability” according to the model output; do not call it a calibrated real-world risk unless calibration has been built and verified.
8. Ensure threshold handling is explicit and consistent. The displayed predicted class must agree with the configured threshold and displayed score.
9. Provide an optional explanation request that calls the Phase 6 service using the exact same model and record.
10. Implement application services for dataset overview, EDA, training, evaluation, prediction, registry access, and reporting orchestration.
11. Keep services independent of PySide6 so they can be tested without launching the UI.
12. Add a local in-memory prediction history for the current session only unless a durable history feature is explicitly justified. Do not persist personal data by default.

### Tests

Test valid and invalid inputs, range warnings, missing active model, hash mismatch, score-threshold consistency, unknown model version, end-to-end inference using a tiny fitted fixture, and service independence from UI imports.

### Acceptance criteria

- A valid single input can flow through the saved model pipeline and return a structured result.
- Invalid input produces an actionable validation error.
- Score, threshold, class, and selected model version are consistent.
- No browser, cloud service, or network call is required for inference.
- Tests and lint checks pass.

Suggested commit message: `feat: implement local prediction engine and application services`

---

# 11. PHASE 8 — NATIVE DESKTOP GUI WITH PYSIDE6

## Prompt

Build the native Windows desktop interface using PySide6. The UI must call the application services from previous phases; do not duplicate ML logic in widgets.

### Visual direction

Create a polished, professional industrial analytics application. Use a restrained palette (navy/charcoal, neutral surfaces, one teal or blue accent), consistent spacing, readable typography, clear status indicators, and sensible empty/loading/error states. Avoid excessive gradients, decorative widgets, and clutter. The UI should look like a serious desktop decision-support tool.

### Main navigation/pages

1. Dashboard.
2. Predict Failure.
3. Explain Prediction.
4. Dataset Explorer.
5. EDA / Visualisation.
6. Model Performance.
7. Threshold Analysis.
8. Model Training.
9. Model Registry.
10. Reports and Downloads.
11. Settings.
12. About / Project Limitations.

### Page requirements

**Dashboard**
- Show whether a dataset is loaded, whether models are available, the selected model/version, last training/evaluation information if available, and quick navigation.
- Do not invent KPIs when there is no trained model or dataset.

**Predict Failure**
- Provide input controls for all six supported attributes.
- Validate before prediction.
- Show the predicted class, score, threshold, model/version, range warnings, and academic limitation notice.
- Provide a clear action to request SHAP/LIME explanation after a prediction.

**Explain Prediction**
- Show global and local explanation views supported by the selected model.
- Explain positive/negative contribution direction in plain language where the explainer output supports it.
- Include the non-causal disclaimer.

**Dataset Explorer**
- Allow CSV import, validation, dataset profile, field list, missing-value and duplicate summaries, and target balance.
- Never silently replace the active dataset on a failed import.

**EDA / Visualisation**
- Display clear distributions and relationships for relevant numeric variables and target categories.
- Avoid misleading chart scales and show labels/units.

**Model Performance**
- Show the required metrics, confusion matrix, ROC and precision-recall curves where available, and model comparison.
- Display the dataset/model/split context for each result.

**Threshold Analysis**
- Show false-positive and false-negative trade-offs across thresholds.
- Let the user inspect thresholds but explain the chosen threshold basis.

**Model Training**
- Provide model selection and training controls.
- Run training in a worker thread or background task; show progress and allow safe cancellation if feasible.
- Do not freeze the interface.

**Model Registry**
- List model versions and their metadata, metrics, creation time, and active status.
- Allow selecting an existing trusted model version.

**Reports and Downloads**
- Allow users to choose report type and export location.
- Show success/failure messages only after the export actually completes.

**Settings**
- Provide sensible local configuration such as default model and threshold.
- Validate settings and persist them in a user-writable application directory.

**About / Limitations**
- Display project title, version, academic purpose, dataset source, and full prototype limitation notice.

### GUI engineering requirements

- Use a `QMainWindow` with modular page widgets and reusable components.
- Keep page widgets thin; use service classes for operations.
- Use `QThread`, `QRunnable`, or an equivalent safe worker pattern for long-running work. Communicate results/errors through Qt signals.
- Embed Matplotlib figures with Qt-compatible canvases.
- Use native file dialogs for CSV import and report export.
- Add progress, empty, success, warning, and error states.
- Make layouts resize correctly and support standard Windows scaling.
- Ensure keyboard navigation and visible labels are usable.
- Do not require QtWebEngine or a browser for core functionality.
- Create a single application entry point and set a proper application icon where assets are available.
- Provide clean shutdown behaviour and avoid orphan worker threads.

### Tests

- Add GUI smoke tests using Qt's offscreen mode where practical.
- Test application startup, navigation creation, page construction, validation error display, and service injection/mocking.
- Test that UI modules do not contain model-training logic.

### Acceptance criteria

- The application launches as a native Qt desktop window.
- All required pages exist and connect to actual services or clearly labelled empty states.
- Prediction and dataset import workflows function end to end.
- Long-running training/explanation does not freeze the UI.
- No browser or internet access is required for normal operations.
- Tests and lint checks pass.

Suggested commit message: `feat: build native PySide6 desktop interface`

---

# 12. PHASE 9 — REPORTING, EXPORTS, AND REGISTRY UX

## Prompt

Complete the reporting and export system and integrate it with the desktop UI.

### Required reports

1. Dataset overview report.
2. Exploratory data analysis report.
3. Model comparison/performance report.
4. Confusion matrix and ROC/precision-recall figures where available.
5. Threshold analysis report.
6. Single prediction report.
7. SHAP explanation report.
8. LIME explanation report.
9. Model registry/model information report.

### Supported output formats

- CSV for tabular data.
- JSON for structured metrics/metadata.
- PNG for figures.
- HTML for navigable local report output if useful.
- PDF for a concise formatted report.

### Tasks

1. Implement a reporting service independent of Qt widgets.
2. Create consistent report templates with project name, generation time, selected dataset fingerprint, model/version, metric definitions, threshold, and relevant limitations.
3. Include the academic prototype disclaimer in every report type where predictions or explanations are presented.
4. Ensure reports do not contain excluded failure-mode columns as model inputs or accidentally expose unnecessary raw dataset rows.
5. Export figures from the same chart-ready data used by the GUI to avoid inconsistent results.
6. Use clear units and explain metrics, class imbalance, false negatives, and false positives.
7. Implement safe file naming, output directory selection, and clear error handling for permission or disk-space errors.
8. Make PDF generation deterministic and ensure pages do not clip charts or text.
9. Connect report generation to the Reports UI page and prediction/explanation pages.
10. Ensure export actions run in background workers when generation may take noticeable time.
11. Add tests for each report format, file existence, content metadata, disclaimer presence, and error handling.

### Acceptance criteria

- Required report types can be generated from valid data/results.
- Files open or parse correctly in their respective formats.
- Reports contain correct model/dataset metadata and limitations.
- Export failures are communicated honestly and do not crash the application.
- Tests and lint checks pass.

Suggested commit message: `feat: add MaintiQ report generation and exports`

---

# 13. PHASE 10 — INTEGRATION TESTING, SECURITY, AND HARDENING

## Prompt

Perform end-to-end integration, improve robustness, and close quality gaps. Do not add unrelated features.

### Test coverage

Create or complete:

- Unit tests for schema, data validation, preprocessing, feature engineering, registry, training configuration, metrics, threshold logic, prediction, explainability adapters, report generation, and settings.
- Integration test for `CSV → validation → preprocessing/features → training → evaluation → model registry → prediction → explanation → report` using a small deterministic test fixture.
- GUI smoke tests for launch, navigation, import, prediction validation, and report workflow using mocks where appropriate.
- Packaging preflight tests for required assets and importable modules.

### Security and reliability requirements

1. Validate imported files and user inputs.
2. Do not execute imported content.
3. Do not load arbitrary external Joblib/pickle files.
4. Verify hashes of locally registered model artefacts.
5. Write JSON/settings/report files atomically where practical.
6. Do not store secrets in the repository.
7. Do not log raw user-entered records unless necessary and explicitly documented.
8. Show user-friendly errors and record diagnostic details in local logs.
9. Handle missing dataset, missing model, corrupted registry, invalid settings, permission errors, and failed report writes without application crashes.
10. Ensure the app remains usable when SHAP or LIME cannot explain a particular model.
11. Ensure Qt background workers are shut down safely.
12. Include the academic/safety notice prominently.

### Quality checks

- Run the full `pytest` suite.
- Run `ruff check .` and the configured formatter check.
- Run type checking if configured; fix meaningful issues rather than suppressing broadly.
- Check dependency consistency and remove unused packages.
- Check for circular imports and oversized modules.
- Run a manual workflow checklist and save it in `docs/QA_CHECKLIST.md`.
- Add GitHub Actions CI for Windows and Python 3.11 if the project uses GitHub. CI should install dependencies and run tests/lint. Do not expose secrets.

### Acceptance criteria

- All automated tests pass, or all remaining failures are clearly identified with evidence and are not hidden.
- The end-to-end integration workflow succeeds on the test fixture.
- The UI handles missing/corrupt resources gracefully.
- Documentation accurately states the test coverage and any limitations.

Suggested commit message: `test: harden MaintiQ application and integration workflows`

---

# 14. PHASE 11 — WINDOWS EXECUTABLE AND INSTALLER

## Prompt

Package the completed application for Windows. Do not begin packaging until Phases 0–10 are implemented and the full test suite passes.

### Packaging strategy

Use **PyInstaller `onedir`** as the default packaging strategy. Package the executable and its dependencies into a folder, then use Inno Setup to create a user-friendly installer. This is generally more maintainable for a Qt + scientific Python application than forcing every dependency into one large one-file executable.

Expected outputs:

```text
release/
├── MaintiQ-Portable/
│   ├── MaintiQ.exe
│   └── required packaged runtime files...
└── MaintiQ-Setup.exe
```

### Tasks

1. Create a reproducible Windows build script, such as `scripts/build_windows.ps1`.
2. Create and maintain a PyInstaller spec file. Include PySide6 Qt plugins, Matplotlib data, XGBoost runtime files, SHAP/LIME dependencies, package resources, icons, and any other required hidden imports/data discovered through build testing.
3. Use the actual application entry point. Set the executable name to `MaintiQ.exe` and apply the application icon if available.
4. Ensure writable runtime data is stored under the user's application-data directory, not inside the installed program directory.
5. Include only necessary default assets. Do not accidentally bundle developer virtual environments, tests, caches, raw temporary files, or secrets.
6. Add version information and application metadata where possible.
7. Create an Inno Setup `.iss` file in `packaging/` that installs the PyInstaller output, creates Start Menu and optional desktop shortcuts, supports uninstall, and preserves user-generated data on uninstall unless the user explicitly chooses to remove it.
8. Include the academic prototype notice in the installer/user documentation.
9. Ensure no Python installation is required on the target end-user machine.
10. Ensure the normal application workflow works offline after installation. Dataset import may be performed from a local CSV; do not require a runtime download.
11. Generate a release manifest with app version, build date, Python version, dependency versions, and artifact hashes.
12. Do not include untrusted prebuilt model pickle files. If a default trained model is bundled, it must have been produced by the project's own reproducible training process on the verified AI4I dataset and its provenance must be documented. Otherwise, launch with an untrained state and guide the user to import data/train a model.

### Build and smoke tests

- Build on Windows if the current environment is Windows.
- Run the packaged `MaintiQ.exe` on the build machine.
- Verify the main window opens, navigation works, local paths resolve, and the app can load its dataset/model state.
- Test a basic prediction if a verified trained model is included.
- Test report export to a user-writable folder.
- Test installation and uninstallation using Inno Setup if available.
- Test that user data is not unexpectedly deleted by an application upgrade/uninstall.
- If the current environment is not Windows, create build scripts/spec/installer configuration and explain that a native Windows build and runtime smoke test must be run on Windows. Do not claim a Windows executable was tested when it was not.

### Acceptance criteria

- A working PyInstaller distribution is created on a supported Windows environment.
- `MaintiQ.exe` starts without requiring a separately installed Python runtime.
- `MaintiQ-Setup.exe` is created and tested when Inno Setup is available.
- All required Qt/scientific runtime files are included.
- User data paths are writable and persistent.
- Build limitations are clearly documented.

Suggested commit message: `build: package MaintiQ for Windows`

---

# 15. PHASE 12 — FINAL RELEASE, DOCUMENTATION, AND UNIVERSITY ALIGNMENT

## Prompt

Prepare the final release and academic handover. Do not invent implementation details or claim features that do not exist in the finished code.

### Tasks

1. Complete `README.md` with project purpose, features, screenshots, supported environment, installation, launch, dataset import, training, prediction, evaluation, explainability, report export, troubleshooting, and limitations.
2. Complete `docs/USER_GUIDE.md` with a step-by-step guide for a first-time Windows user.
3. Complete `docs/DEVELOPER_GUIDE.md` with environment creation, install commands, run commands, test commands, lint commands, and packaging commands.
4. Complete `docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, `docs/FEATURE_ENGINEERING.md`, and `docs/MODEL_CARD.md` from the actual implementation.
5. Create `docs/QA_CHECKLIST.md` with tested workflows and actual results.
6. Create `docs/RELEASE_NOTES.md` and a release manifest.
7. Create a screenshot checklist for the university demonstration. Only include real screenshots captured from the built application.
8. Ensure the final project documentation maps features to the synopsis requirements:
   - Introduction/objectives.
   - Technology and hardware/software requirements.
   - Problem definition and functional/non-functional requirements.
   - Level 0, Level 1, Level 2 DFDs, conceptual ER diagram, and class diagram where required for the report.
   - Modules, process logic, data structures, and reports.
   - Security mechanisms.
   - Future scope.
   - Bibliography.
9. Ensure diagrams describe the actual implemented architecture. Mark conceptual entities or future capabilities as conceptual/proposed, not implemented.
10. Include the academic prototype limitation consistently.
11. Check the repository for temporary files, generated secrets, accidental local user data, and unnecessary large files.
12. Produce a final release summary with:
    - Features actually implemented.
    - Models actually trained and on what data.
    - Evaluation evidence.
    - Automated test results.
    - Executable/installer paths.
    - Windows build/test environment.
    - Known limitations and future work.
    - Exact steps to run the app.

### University-alignment rules

- Keep the project appropriate for a BCA-level academic submission while demonstrating sound engineering practice.
- Preserve the synopsis's AI4I benchmark scope, binary failure-prediction objective, four candidate algorithms, SHAP/LIME, evaluation metrics, threshold analysis, reporting, and stated limitations.
- Do not claim live industrial integration, real factory validation, certified diagnostics, enterprise authentication, or production deployment unless those features are genuinely implemented and verified.
- Keep references to the UCI AI4I 2020 dataset and the official library/documentation sources actually used.

### Final acceptance criteria

- Documentation matches code.
- All automated checks pass.
- The release artefacts exist and are verified.
- The Windows build/test status is stated truthfully.
- The final handover contains exact run/install instructions and the project is ready for demonstration subject to the documented limitations.

Suggested commit message: `docs: finalize MaintiQ release and academic handover`

---

# 16. REQUIRED COMMANDS AND EXPECTED DEVELOPER WORKFLOW

KiloCode should adapt commands to the actual chosen environment and record the exact commands it runs. A typical Windows PowerShell workflow is:

```powershell
# From the MaintiQ-Desktop project root
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt

# Run the application (once Phase 8 exists)
python -m maintiq

# Tests and quality checks
pytest
ruff check .
ruff format --check .

# Windows build (once Phase 11 exists)
.\scripts\build_windows.ps1
```

If PowerShell blocks activation, document the safe current-session command or use the virtual environment's Python executable directly. Do not weaken the machine-wide execution policy.

---

# 17. FINAL RESPONSE REQUIRED FROM KILOCODE

At the end of the work, provide a concise but evidence-based completion report with:

1. Project root path.
2. Phases completed and any incomplete phases.
3. Main modules and desktop pages implemented.
4. Actual dataset used and whether it is bundled or user-imported.
5. Models trained and actual evaluation results, only if training was genuinely performed.
6. Automated test count and pass/fail status.
7. Lint/type-check status.
8. Exact launch command for development.
9. Exact path to `MaintiQ.exe` if built.
10. Exact path to `MaintiQ-Setup.exe` if built.
11. Whether the executable and installer were smoke-tested on Windows.
12. Any missing prerequisites, known defects, or important limitations.
13. The next action required from the user, if anything remains.

Do not report success based only on files being generated. Report only what was actually executed and verified.

---

**End of MaintiQ KiloCode Master Execution Prompt Pack.**
