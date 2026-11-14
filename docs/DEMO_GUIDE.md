# MaintiQ v0.1.0 — Demonstration Guide

**Purpose:** Step-by-step user actions for executing the complete
end-to-end predictive-maintenance demonstration (all ten checkpoints)
on the genuine AI4I 2020 dataset. Intended for the BCA capstone viva
and technical evaluation.

**Application:** `release\MaintiQ-Portable\MaintiQ.exe` (source
equivalent: `python -m maintiq` from the repository).

**Dataset:** AI4I 2020 Predictive Maintenance Dataset (UCI), imported
by the user — it is **not bundled** with the application.

Source: https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset

---

## Prerequisites

- Windows 10 / 11
- The repository at `C:\ARRU CODES\projects\MaintiQ`
- Python virtual environment `.venv` with dependencies installed
- The genuine AI4I CSV downloaded to `assets\datasets\ai4i_2020_predictive_maintenance.csv`

> The portable `MaintiQ.exe` is unsigned and is blocked by Windows
> Smart App Control on this machine. The block is **documented**, not
> bypassed. The same implementation runs via `python -m maintiq`.

---

## Checkpoint 1 — Launch MaintiQ.exe

**User actions:**

1. Open a PowerShell terminal in the repository root.
2. Activate the environment:
   ```
   .\.venv\Scripts\Activate.ps1
   ```
3. Launch the application (offscreen-safe for headless/CI; omit
   `QT_QPA_PLATFORM` on a normal desktop):
   ```
   set QT_QPA_PLATFORM=offscreen
   python -m maintiq
   ```
   Or double-click `release\MaintiQ-Portable\MaintiQ.exe` where Smart
   App Control policy permits.

**Verify:**
- Window opens with title `MaintiQ v0.1.0`; no startup exceptions.
- Sidebar shows all 12 navigation pages: Dashboard, Predict Failure,
  Explain Prediction, Dataset Explorer, EDA / Visualisation, Model
  Performance, Threshold Analysis, Model Training, Model Registry,
  Reports and Downloads, Settings, About / Limitations.
- Fonts render (Segoe UI, dark theme); no white chart backgrounds
  (matplotlib canvas themed to the dark UI).
- Dashboard displays application status (dataset, models, selected
  model, last training).
- SHAP / LIME unavailability does not crash the app; it is reported
  explicitly and the app continues.

---

## Checkpoint 2 — Import AI4I 2020 dataset

**User actions:**

1. Obtain the official AI4I 2020 CSV from the UCI repository link
   above (do not fabricate or modify it).
2. In the application: **File > Import dataset** (`Ctrl+O`) or the
   Dataset Explorer page, then select the CSV.
3. Confirm the import is accepted.

**Verify:**
- CSV import works; expected columns recognised (`Type`, `Air
  temperature [K]`, `Process temperature [K]`, `Rotational speed
  [rpm]`, `Torque [Nm]`, `Tool wear [min]`, `Machine failure`).
- Data types correct.
- Original CSV preserved (byte-identical — the application never
  modifies the source file).
- Dataset metadata recorded (profile + validation).

---

## Checkpoint 3 — Inspect dataset and data quality

**User actions:** Open the Dataset Explorer page and review the
dataset profile; generate the profile report via Reports and Downloads.

**Verify and display:**
- Rows and columns (10,000 × 14 on the AI4I 2020 dataset).
- Column names and data types.
- Missing values (none on the genuine dataset).
- Duplicate records (none on the genuine dataset).
- Unique values (Type: L/M/H).
- Target distribution (Machine failure: 0 = 9,661, 1 = 339).
- Descriptive statistics for numeric columns.
- Invalid values / validation warnings.

Output: a genuine dataset profile report (JSON).

---

## Checkpoint 4 — Explore distributions and visualisations

**User actions:** Open the **EDA / Visualisation** page and click
**Refresh charts**.

**Verify:**
- Air temperature, process temperature, rotational speed, torque and
  tool wear histograms.
- Machine type distribution.
- Machine failure class distribution (target balance).
- Each chart has a meaningful title, axis labels and a readable
  legend; charts render on dark backgrounds (no white chart
  backgrounds in the dark application).

---

## Checkpoint 5 — Train all four candidate models

**User actions:** Open **Model Training**. For each candidate, select
the model and start training:

1. Logistic Regression
2. Random Forest
3. Gradient Boosting
4. XGBoost

**Verify:**
- Consistent train/test split (stratified 80/20, seed 42).
- Reproducible random seed.
- Leakage-safe preprocessing (fitted on training partition only).
- Correct feature engineering
  (`temperature_diff`, `power_kw`, `wear_rate`, `torque_normalized`,
  `temp_wear_interaction`).
- Training progress reported; cancellation behaviour available.
- Model artefact persistence (joblib) and model registry integration
  (monotonic versioning v1, v2, … with SHA-256 hashes).
- Record actual training duration and outcome per classifier.
- No failed model is silently substituted.

---

## Checkpoint 6 — Compare evaluation metrics

**User actions:** Open **Model Performance** to view the comparison
table, ROC curves, precision-recall curves and confusion matrices.

**Verify (all on the same held-out test partition):**
- Accuracy, precision, recall, F1-score, ROC-AUC, average precision,
  specificity, balanced accuracy, confusion matrix, FPR, FNR.
- Model comparison table; ROC curves; precision-recall curves;
  confusion matrices.
- Best model identified under the selected criterion (F1).
- No metrics invented; undefined values reported as absent.

---

## Checkpoint 7 — Analyse classification thresholds

**User actions:** Open **Threshold Analysis**.

**Verify:**
- Threshold-based classification on validation data (never the held-out
  test set).
- Precision/recall trade-off, false-positive and false-negative counts,
  F1 comparison.
- Recommended threshold (F1-based, deterministic tie-breaking).
- Default threshold (0.5) clearly distinguished from the recommended
  threshold.

---

## Checkpoint 8 — Predict a machine failure

**User actions:** Open **Predict Failure**. Select the registered model
and version, enter the six attributes:

- Machine type
- Air temperature
- Process temperature
- Rotational speed
- Torque
- Tool wear

Then run inference.

**Verify:**
- Input validation.
- Preprocessing and feature-engineering consistency with training.
- Model loading from registry (SHA-256 verified).
- Predicted class, model score, applied threshold.
- Out-of-distribution warnings.
- The score is a model output, **not** a real-world failure
  probability.

---

## Checkpoint 9 — Generate a LIME explanation

**User actions:** From the prediction result, run **Explain** (LIME).

**Verify:**
- Model and version selection (same model used for the prediction).
- Training reference data used as the LIME background sample.
- Correct feature order matching the processed feature space.
- Feature contribution values, with positive and negative
  contributions.
- Explanation visualisation.
- Explanation corresponds to the actual prediction.
- If LIME fails: report the exact dependency/runtime error — no
  fabricated explanation.

---

## Checkpoint 10 — Export project reports

**User actions:** Open **Reports and Downloads**. Select each report
type and an output location:

1. Dataset profile (JSON)
2. Model evaluation metrics (JSON)
3. Threshold analysis (CSV)
4. Evaluation charts (PNG)
5. Combined report bundle (where supported)

**Verify:**
- Correct filenames.
- Valid output formats (JSON / CSV / PNG).
- Accurate model version metadata.
- Correct dataset provenance.
- Files can be opened after exporting.

---

## After all checkpoints (Quality assurance)

- Run the full unit, integration and GUI test suite (`pytest tests/ -q`).
- Run Ruff (`ruff check src/ tests/`) and format check
  (`ruff format --check src/ tests/`).
- Verify model registry integrity (SHA-256 of each artefact).
- Verify exported report contents.
- Check application logs (`%LOCALAPPDATA%\MaintiQ\logs\maintiq.log`).
- Verify all 12 GUI pages.
- Confirm offline operation (no network required after installation).
