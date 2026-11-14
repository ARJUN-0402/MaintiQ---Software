# MaintiQ User Guide

**MaintiQ v0.2.0** — Industrial Failure Prediction with Explainable Artificial Intelligence
Academic predictive-maintenance decision-support prototype using the AI4I 2020 dataset.

> **MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark
> dataset. Predictions and explanations are model outputs, not certified industrial
> diagnoses or maintenance instructions. Qualified human review is required.**

## 1. What MaintiQ does

MaintiQ is a native Windows desktop application (PySide6) that:

- Imports and validates the AI4I 2020 Predictive Maintenance CSV.
- Trains and compares four classifiers: Logistic Regression, Random Forest,
  Gradient Boosting, and XGBoost.
- Evaluates models (accuracy, precision, recall, F1, ROC-AUC, confusion matrix,
  and supporting metrics) and analyses decision thresholds.
- Explains predictions with SHAP and LIME where those libraries are available in
  the runtime environment.
- Exports reports (JSON, CSV, PNG charts).
- Stores datasets, models, the registry, logs, settings, and reports under your
  per-user application data folder (`%LOCALAPPDATA%\MaintiQ`), never inside the
  protected installation directory.

## 2. Prerequisites

- Windows 10 or Windows 11 (64-bit).
- No Python installation is required on the end-user machine — the packaged
  `MaintiQ.exe` bundles the Python runtime and dependencies.

## 3. Installation

Run the installer `MaintiQ-Setup.exe` and follow the prompts:

- Installs to `%ProgramFiles%\MaintiQ` (per-machine).
- Creates a Start Menu shortcut and, optionally, a desktop shortcut.
- An uninstaller is available via Start Menu or Settings > Apps.

For a portable install, unzip/run `MaintiQ-Portable\MaintiQ.exe` from the
portable build folder (no installation required).

## 4. First launch

Open MaintiQ from the Start Menu shortcut or run `MaintiQ.exe`. The main window
opens with a sidebar (Dashboard, Predict Failure, Explain Prediction, Dataset
Explorer, EDA / Visualisation, Model Performance, Threshold Analysis, Model
Training, Model Registry, Reports and Downloads, Settings, About / Project
Limitations) and a persistent academic-prototype notice banner.

The application starts untrained: no dataset is imported and no model is
registered. Import the AI4I 2020 CSV and train a model before predicting.

## 5. Getting the AI4I 2020 dataset

The AI4I 2020 Predictive Maintenance Dataset is **not bundled** in MaintiQ
(and no default trained model is shipped). Obtain it from the UCI Machine
Learning Repository (AI4I 2020 Predictive Maintenance Dataset) and save it as a
CSV file, then import it in MaintiQ:

1. Open **Dataset Explorer**.
2. Click **Import CSV** and select your AI4I CSV file.
3. MaintiQ validates the file (required columns, valid categories, missing
   values, duplicates, size limit of 200 MB). Imported files are treated as
   untrusted — no formulas or macros are executed.
4. On success, the dataset becomes the active dataset and its profile is shown.

Expected predictive columns: `Type`, `Air temperature [K]`, `Process temperature
[K]`, `Rotational speed [rpm]`, `Torque [Nm]`, `Tool wear [min]`, and target
`Machine failure`. Columns `UDI`, `Product ID`, and failure-mode indicators
(`TWF`, `HDF`, `PWF`, `OSF`, `RNF`) are excluded from model input.

## 6. Training a model

Open **Model Training**:

1. Select a candidate model (Logistic Regression, Random Forest, Gradient
   Boosting, XGBoost).
2. Start training. Training runs on a background worker; progress is shown and
   training can be cancelled safely. The UI never freezes.
3. On completion, the pipeline is saved and registered (version v1, v2, …) with
   its artefact SHA-256 hash and metadata (parameters, metrics, feature list,
   split settings, timestamp).

The final holdout test set is evaluated after training; results feed the Model
Performance and Threshold Analysis pages.

## 7. Predicting failure for one machine

Open **Predict Failure**:

1. Select a registered model and version.
2. Enter the six attributes: machine type, air temperature, process temperature,
   rotational speed, torque, tool wear.
3. Click **Predict**.
4. The result shows the predicted class, model-estimated score, threshold
   (default 0.50), model name/version, and any out-of-distribution range warning
   when inputs fall outside the training-data range.
5. Optionally request a SHAP/LIME explanation. Explanations describe which
   features drove the prediction and always carry the non-causal disclaimer.

Scores are model-estimated failure probabilities, not calibrated real-world
risk.

## 8. Evaluation, thresholds, and model comparison

- **Model Performance:** metrics and ROC/precision-recall charts for the
  evaluated model version, with dataset/model/split context.
- **Threshold Analysis:** false-positive/false-negative trade-offs across the
  threshold grid; the recommended threshold (default: maximise validation F1)
  with its selection basis stated. Thresholds are never tuned on the holdout
  test set.
- **Model Performance comparison:** side-by-side comparison of all four
  candidates on identical partitions; unavailable models are reported explicitly.

## 9. Reports and exports

Open **Reports and Downloads**:

1. Choose a report type: model evaluation metrics (JSON), dataset profile (JSON),
   threshold analysis (CSV), evaluation charts (PNG), or export all (bundle).
2. Choose an output location via the native file dialog.
3. Click **Export**. Success or failure is shown only after the export completes.

Exports use atomic writes, sanitized filenames, and path-traversal prevention.
Every report containing predictions or explanations includes the academic
prototype disclaimer. Exported charts are generated from the same chart-ready
data used in the GUI.

## 10. Model Registry

Open **Model Registry** to list registered model versions, inspect metadata
(metrics, parameters, artefact path, SHA-256, timestamps), and select the active
model version. Selected versions can be deleted (single version or entire model)
with confirmation; artefact files on disk are left intact.

## 11. Settings

Configure the default model and threshold. Settings are validated and persisted
in the user-writable application-data directory.

## 12. About / Project Limitations

Shows project title, version, academic purpose, dataset source, and the full
prototype limitation notice: MaintiQ does not diagnose real machinery, connect to
factory systems, or present model outputs as certified advice.

## 13. Troubleshooting

| Problem | Likely cause / action |
|---------|----------------------|
| Application will not launch | Unsigned `.exe` builds may be blocked by Windows Smart App Control. Use an EV code-signed installer or follow your administrator's policy bypass procedure. |
| SHAP explanations unavailable | `sklearn.cluster` native extensions may be blocked by Windows Application Control. LIME explanations still work where `lime` is importable. The app reports this explicitly. |
| Import rejected | Check required columns, binary target, valid `Type` values (`L`/`M`/`H`), missing values, duplicates, and file size (< 200 MB). |
| No model available to predict | Import a dataset and train a model first (Model Training). |
| Out-of-distribution warning | Input values fall outside training-data ranges; treat the score with caution — it is not clamped or silently adjusted. |
| Export fails | Check output folder write permissions and disk space; file names are sanitized automatically. |

## 14. Support statement

This is an academic prototype, not a production system. All predictions and
explanations require qualified human review. See `docs/MODEL_CARD.md`,
`docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, `docs/FEATURE_ENGINEERING.md`,
and `IMPLEMENTATION_STATUS.md` for implementation details.
