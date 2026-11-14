# MaintiQ Architecture

## Overview

MaintiQ follows a clean, layered architecture:

```
Presentation/UI (PySide6) → Application Services → Domain/ML Services → Data and Model Artefacts
```

UI code is strictly separated from data science and business logic. Long-running
training and explanation calculations run on background workers so the UI never
freezes.

## Layers

### Presentation/UI (`src/maintiq/ui`)
PySide6 `QMainWindow` with modular page widgets (dashboard, prediction,
explanation, dataset explorer, EDA, model performance, threshold analysis,
training, registry, reports, settings, about). Pages are thin and delegate to
application services.

### Application Services (`src/maintiq/services`)
Orchestration services for dataset overview, EDA, training, evaluation,
prediction, registry access, and reporting. Independent of PySide6.

### Domain/ML Services (`src/maintiq/ml`, `src/maintiq/domain`)
- `ml/preprocessing` — leakage-safe imputation, encoding, scaling pipelines
- `ml/features` — synopsis feature engineering (temperature_diff, power_kw,
  wear_rate_proxy, torque_normalized, temp_wear_interaction)
- `ml/training` — model factory, stratified training, registry persistence
- `ml/evaluation` — metrics, confusion matrix, ROC/PR, threshold analysis
- `ml/prediction` — single-record inference engine
- `ml/explainability` — SHAP and LIME explanation services
- `domain` — typed business entities and value objects

### Data (`src/maintiq/data`)
Dataset schema, loading, validation, profiling, and import workflow.

### Registry (`src/maintiq/registry`)
JSON model registry with schema versioning, unique version IDs, artefact SHA-256
hashes, atomic writes, and hash verification before load.

### Core (`src/maintiq/core`)
Typed configuration, logging (rotating file handler), custom exceptions, path
resolution.

## Data flow

1. User imports a CSV via the Dataset Explorer (or services API).
2. Dataset is validated against the AI4I schema; identifiers (`UDI`, `Product ID`)
   and failure-mode indicators (`TWF`, `HDF`, `PWF`, `OSF`, `RNF`) are excluded
   from predictive input.
3. Preprocessing + feature engineering transformers are fit on the training
   partition only and bundled inside each model pipeline.
4. One of four classifiers (logistic regression, random forest, gradient
   boosting, XGBoost) is trained with stratified splits and a fixed seed.
5. The pipeline is saved with Joblib and registered in the local JSON registry
   with an artefact hash.
6. Evaluation and threshold analysis run on the untouched final holdout set.
7. Predictions flow a single record through the saved pipeline; SHAP/LIME
   explanations are produced on demand.
8. Reports (dataset, EDA, performance, threshold, prediction, explanation,
   registry) are exported as CSV/JSON/PNG/HTML/PDF.

## Paths

Writable runtime data (datasets, models, registry, logs, settings, reports) is
stored under the per-user application-data directory (`%LOCALAPPDATA%\MaintiQ`
on Windows), never inside a protected installation directory.

## Safety

Imported CSVs are treated as untrusted. No arbitrary Joblib/pickle loading.
Model artefacts are verified by SHA-256 before loading. The academic prototype
notice is displayed in the UI and in every generated report.
