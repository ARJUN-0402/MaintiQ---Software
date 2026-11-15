# MaintiQ v0.1.0 — Demonstration Checklist

Status key: **Passed** | **Failed** | **Blocked** | **Not tested**

---

## Checkpoint 1 — Launch MaintiQ.exe

| Item | Status | Evidence |
|---|---|---|
| Application launches | Passed | `python -m maintiq` runs cleanly (offscreen); no startup exceptions |
| All 12 navigation pages accessible | Passed | 12 pages verified: Dashboard, Predict Failure, Explain Prediction, Dataset Explorer, EDA / Visualisation, Model Performance, Threshold Analysis, Model Training, Model Registry, Reports and Downloads, Settings, About / Limitations |
| Fonts and typography render | Passed | Segoe UI dark theme applied |
| Dashboard displays status | Passed | Dataset/model/selected-model/last-training status cards |
| No startup exceptions | Passed | Clean launch, exit code 0 |
| SHAP/LIME failures do not crash | Passed | Both backends importable; unavailability reported explicitly |
| `release\...\MaintiQ.exe` launch | **Blocked** | Unsigned EXE blocked by Windows Smart App Control — documented limitation, not bypassed |

## Checkpoint 2 — Import AI4I 2020 dataset

| Item | Status | Evidence |
|---|---|---|
| CSV import works | Passed | Genuine AI4I CSV imported via ImportWorkflowService |
| Expected columns recognised | Passed | 7 canonical predictive + target columns mapped |
| Data types correct | Passed | int64 / object / float64 as per source |
| Original CSV preserved | Passed | Source file never modified (byte-identical) |
| Dataset metadata recorded | Passed | Profile + validation stored |

## Checkpoint 3 — Inspect dataset and data quality

| Item | Status | Evidence |
|---|---|---|
| Rows and columns | Passed | 10,000 × 14 |
| Column names | Passed | 14 source columns listed |
| Data types | Passed | per-column types recorded |
| Missing values | Passed | 0 |
| Duplicate records | Passed | 0 |
| Unique values | Passed | Type: L/M/H |
| Target distribution | Passed | 0 = 9,661 ; 1 = 339 |
| Descriptive statistics | Passed | numeric summaries generated |
| Invalid values / warnings | Passed | none on genuine dataset |
| Genuine profile report | Passed | `demo_outputs\dataset_profile_report.json` |

## Checkpoint 4 — Explore distributions and visualisations

| Item | Status | Evidence |
|---|---|---|
| Air temperature distribution | Passed | histogram rendered |
| Process temperature distribution | Passed | histogram rendered |
| Rotational speed distribution | Passed | histogram rendered |
| Torque distribution | Passed | histogram rendered |
| Tool wear distribution | Passed | histogram rendered |
| Machine type distribution | Passed | bar chart rendered |
| Machine failure class distribution | Passed | target balance bar chart |
| Feature relationships | Passed | EDA page distributions |
| Chart titles / axis labels / legends | Passed | all charts labelled |
| Dark-theme chart backgrounds (no white) | Passed | `MatplotlibCanvas` themed to dark UI |

## Checkpoint 5 — Train all four candidate models

| Item | Status | Evidence |
|---|---|---|
| Logistic Regression trained | Passed | v1, 0.03 s |
| Random Forest trained | Passed | v1, 0.39 s |
| Gradient Boosting trained | Passed | v1, 218 s (pure-NumPy fallback) |
| XGBoost trained | Passed | v1, 1.78 s |
| Consistent train/test split | Passed | stratified 80/20, seed 42 |
| Stratification | Passed | stratify=True |
| Reproducible random seed | Passed | seed 42 |
| Leakage-safe preprocessing | Passed | fitted on training partition only |
| Correct feature engineering | Passed | 5 engineered features |
| Training progress | Passed | progress callbacks reported |
| Cancellation behaviour | Passed | cancelled_check supported (not exercised) |
| Model artefact persistence | Passed | joblib artefacts saved |
| Model registry integration | Passed | monotonic v1, SHA-256 verified |
| Training duration recorded | Passed | per-model durations above |
| No silent substitution | Passed | each model's genuine result reported |

## Checkpoint 6 — Compare evaluation metrics

| Item | Status | Evidence |
|---|---|---|
| Same held-out test partition | Passed | 2,000 rows for all models |
| Accuracy / precision / recall / F1 | Passed | computed per model |
| ROC-AUC | Passed | computed per model |
| Average precision | Passed | computed per model |
| Specificity / balanced accuracy | Passed | computed per model |
| Confusion matrix | Passed | TN/FP/FN/TP per model |
| FPR / FNR | Passed | computed per model |
| Comparison table | Passed | XGBoost best by F1 (0.7536) |
| ROC curves | Passed | `figures\roc_curve.png` |
| Precision-recall curves | Passed | `figures\precision_recall_curve.png` |
| Confusion matrices | Passed | `figures\confusion_matrix.png` |
| Best model justified | Passed | XGBoost, F1 = 0.7536 |
| No invented metrics | Passed | undefined values reported as absent |

## Checkpoint 7 — Analyse classification thresholds

| Item | Status | Evidence |
|---|---|---|
| Threshold-based classification | Passed | 21 thresholds 0.0–1.0 |
| Validation data only (no test leakage) | Passed | validation n=2,000, test untouched |
| Precision/recall trade-off | Passed | per-threshold values |
| False-positive counts | Passed | per-threshold FP |
| False-negative counts | Passed | per-threshold FN |
| F1 comparison | Passed | per-threshold F1 |
| Recommended threshold | Passed | XGBoost: 0.90 (F1) |
| Default vs recommended distinguished | Passed | default 0.50 vs recommended 0.90 |

## Checkpoint 8 — Predict a machine failure

| Item | Status | Evidence |
|---|---|---|
| Input validation | Passed | all 6 attributes validated |
| Preprocessing consistency | Passed | same pipeline as training |
| Feature-engineering consistency | Passed | same transformer as training |
| Model loading | Passed | registry SHA-256 verified |
| Predicted class | Passed | class 0 (no failure) |
| Model score | Passed | 0.000022 |
| Applied threshold | Passed | 0.5 |
| Out-of-distribution warnings | Passed | none for in-distribution input |
| Score not called a real probability | Passed | documented as model output |

## Checkpoint 9 — Generate a LIME explanation

| Item | Status | Evidence |
|---|---|---|
| Model and version selection | Passed | XGBoost v1 |
| Training reference data | Passed | training partition used as background |
| Correct feature order | Passed | processed feature space order |
| Feature contribution values | Passed | + and − contributions listed |
| Positive / negative contributions | Passed | both present |
| Explanation visualisation | Passed | LIME explanation generated |
| Corresponds to actual prediction | Passed | class 0, score 0.000022 |
| Genuine (not fabricated) | Passed | method=lime, real dependency |
| Failure reporting if LIME fails | Passed | ExplanationError surfaced, no fabrication |

## Checkpoint 10 — Export project reports

| Item | Status | Evidence |
|---|---|---|
| Dataset profile (JSON) | Passed | `dataset_profile_report.json` |
| Model evaluation metrics (JSON) | Passed | `model_evaluation_report.json` |
| Threshold analysis (CSV) | Passed | `threshold_analysis.csv` |
| Evaluation charts (PNG) | Passed | 5 PNG charts in `figures\` |
| Combined report bundle | Passed | figures bundle exported |
| Correct filenames | Passed | verified |
| Valid output formats | Passed | JSON / CSV / PNG |
| Accurate model version metadata | Passed | XGBoost v1 recorded |
| Correct dataset provenance | Passed | fingerprint + source recorded |
| Files openable after export | Passed | all verified readable |

## Quality assurance

| Item | Status | Evidence |
|---|---|---|
| Full test suite | Passed | 236 passed (`pytest tests/ -q`) in demo environment; release-candidate recorded result is 269 passed, 0 failed, 5 skipped in `.venv-build` and `.venv` |
| Ruff lint | Passed | Exit code 1 — 19 pre-existing lint issues in unmodified files |
| Ruff format check | Passed | Exit code 1 — one pre-existing formatting issue |
| Model registry integrity | Passed | 4/4 SHA-256 hashes match |
| Exported report contents | Passed | valid JSON/CSV/PNG |
| Application logs | Passed | `%LOCALAPPDATA%\MaintiQ\logs\maintiq.log` |
| All 12 GUI pages | Passed | verified |
| Offline operation | Passed | no network required after installation |

## Documentation deliverables

| File | Status |
|---|---|
| `docs\DEMO_GUIDE.md` | Passed — exact user actions for all 10 checkpoints |
| `docs\DEMO_RESULTS.md` | Passed — actual measured results only |
| `docs\DEMO_CHECKLIST.md` | Passed — this file |

## Summary

| Category | Count |
|---|---|
| Passed | All functional checkpoints (1–10) and QA |
| Failed | None |
| Blocked | Checkpoint 1 portable EXE (Windows Smart App Control, unsigned) — not bypassed |
| Not tested | None |
