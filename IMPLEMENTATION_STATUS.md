# Implementation Status — MaintiQ

**Project root:** `C:\ARRU CODES\projects\MaintiQ`  
**Python:** 3.13.14 (master prompt targets 3.11; 3.11 not available via `py` launcher, using 3.13)  
**Platform:** Windows (PowerShell 5.1)

## Phase progress

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Project foundation and architecture | complete |
| 1 | Dataset ingestion, schema, and data quality | complete |
| 2 | Preprocessing pipeline | complete |
| 3 | Feature engineering | complete (transformer/tests present) |
| 4 | Model training and model registry | complete |
| 5 | Model evaluation and threshold analysis | complete |
| 6 | Explainable AI with SHAP and LIME | complete (SHAP unavailable in this env — clear error, no fake explanations; LIME wired end-to-end) |
| 7 | Prediction engine and application services | complete |
| 8 | Native desktop GUI with PySide6 | complete |
| 9 | Reporting, exports, and registry UX | complete |
| 10 | Integration testing, security, hardening | complete |
| 11 | Windows executable and installer | complete |
| 12 | Final release, documentation, university alignment | complete |

## Confirmed environment (this audit)

- Python 3.13.14, scikit-learn 1.9.1, virtual environment `.venv`.
- PySide6 6.12.0 (native GUI dependency). pytest-qt is not installed; GUI tests use Qt offscreen mode directly.
- `python -m maintiq` starts the native PySide6 desktop application (no eager SHAP/LIME/cluster imports).
- XGBoost builds/trains/infers; Logistic Regression and Random Forest build/train/infer; Gradient Boosting uses preserved pure-NumPy fallback (`GradientBoostingFallbackClassifier`) and trains/infers.
- `import lime` succeeds. `import shap` (0.54.1) and `sklearn.cluster` succeed in this environment at phase 12 time (the earlier blocked-cluster condition no longer applies here; see `docs/WINDOWS_COMPATIBILITY.md` for the locked-down Windows behaviour, which the application still handles with clear errors).

## Windows Application Control / Smart App Control — confirmed blockers (observed)

Recorded separately from theoretical concerns in `docs/WINDOWS_COMPATIBILITY.md`.

- `sklearn.cluster` package import / `KMeans` / `MiniBatchKMeans`: **blocked/unavailable** in this environment (`DLL load failed ... Application Control policy has blocked this file` for cluster extensions such as `_k_means_minibatch`, `_isotonic`, `_linkage` during probes).
- `import shap`: **unavailable** (confirmed) because SHAP imports `sklearn.cluster.KMeans` (`shap.utils._legacy`), hitting the blocked cluster extension chain.
- `sklearn.ensemble._gradient_boosting` extension: previously observed blocked (`gb.log`); mitigated by pure-NumPy fallback (no sklearn GB extension required).
- No installed scikit-learn `.pyd` files were modified.

## Import/dependency audit findings

- **Targeted imports in `src/`**: no direct use of `sklearn.cluster`, `KMeans`, `MiniBatchKMeans`, `sklearn.svm`, or `sklearn.neighbors`. No eager `import shap` / `import lime` at startup.
- `sklearn.impute.SimpleImputer` is importable in this probe, but preprocessing remains defensive/pure-NumPy-capable for locked-down environments.
- `sklearn.linear_model.LogisticRegression`, `sklearn.ensemble._forest.RandomForestClassifier`, and `xgboost.XGBClassifier` are lazy-imported in `maintiq.ml.training.factory` (not at package startup).
- Explainability: `maintiq.ml.explainability` provides lazy `shap_status()`/`lime_status()`/`require_*()` and raises clear `ExplanationError` when unavailable; no fake explanations.
- `_k_means_common` exact component: cluster-package import chain is the confirmed blocked path for SHAP in this environment (details in `docs/WINDOWS_COMPATIBILITY.md`).

## Phase 4 — Model Registry (complete)

- `src/maintiq/ml/training/registry.py` — `ModelRegistry`: JSON-backed registry with per-model monotonic versioning (v1, v2, ...), schema versioning, atomic writes (temp file + `os.replace`), path-traversal prevention, SHA-256 verification before load, defensive copies of record data, NumPy-safe JSON serialization, thread lock for same-process writes.
- Exceptions `RegistryError` and `ModelHashMismatchError` exist in `src/maintiq/core/exceptions.py`.
- Integrated with `ModelTrainer.train_model()` via `self.registry.register(...)`.
- Tests: `tests/unit/test_registry.py` (21 tests covering missing file, versioning, persistence, list/get/latest/exists/count, malformed JSON, unsupported schema, invalid records, missing artifact, path traversal, hash verification, JSON-safe serialization, atomic write safety, trainer integration).
- Registry exposed from `maintiq.ml.training` and `maintiq.registry`.

## Phase 5 — Evaluation and Threshold Analysis (complete)

- `src/maintiq/ml/evaluation/service.py` — Hardened `EvaluationService` with accuracy, precision, recall, F1, ROC-AUC, confusion matrix (tn/fp/fn/tp), specificity, balanced accuracy, FPR, FNR, average precision. Threshold validation [0,1], positive-class mapping via `estimator.classes_`, single-class ROC-AUC → None, zero-division → 0.0, JSON-safe primitives (NaN/Infinity → None), shape validation, non-finite probability rejection.
- `src/maintiq/ml/evaluation/threshold.py` — `ThresholdAnalysisService`: leakage-safe threshold selection using validation scores only (never test set), configurable threshold grid (default `np.linspace(0, 1, 21)`), default threshold (0.50) always included, deterministic tie-breaking (closest to 0.50, then lowest), recommendation objective (maximize F1).
- `src/maintiq/ml/evaluation/comparison.py` — `ComparisonService`: compares LR/RF/GB/XGB on identical partitions, unavailable models reported with explicit status/reason, best model by explicit metric only (never accuracy alone), benchmark warning included.
- `src/maintiq/ml/evaluation/charts.py` — Matplotlib charts: model comparison, confusion matrix, ROC curve, PR curve, threshold vs metric, FP/FN trade-off. Real metrics only, titles/labels/legends, graceful one-class handling, figures closed after saving.
- `src/maintiq/reporting/service.py` — `ReportService`: JSON metrics/comparison export, CSV threshold analysis, PNG chart export. Atomic writes, filename sanitization, path traversal prevention.
- Tests: `tests/unit/test_evaluation.py`, `tests/unit/test_threshold.py` (14), `tests/unit/test_comparison.py` (5), `tests/unit/test_charts.py` (8), `tests/unit/test_reporting.py` (7).

## Phase 6 — Explainable AI with SHAP and LIME (complete)

- `src/maintiq/ml/explainability/__init__.py` — real explanation service wired on top of `ModelPipeline`:
  - `explain_with_shap` — model-agnostic `shap.KernelExplainer` over the positive-class probability; works with all four estimators including the pure-NumPy Gradient Boosting fallback. Raises `ExplanationError` when SHAP is unavailable (blocked sklearn.cluster chain in this env); never fabricates explanations.
  - `explain_with_lime` — `lime.lime_tabular.LimeTabularExplainer` over the processed feature space; works end-to-end in this env (`import lime` succeeds).
  - `explain_local` — tries SHAP then LIME (auto) or a single named backend; clear error when none available.
  - `explain_global` — mean-absolute-SHAP feature importance across a bounded deterministic background sample.
  - All imports lazy/optional; no eager SHAP/LIME at startup. Transformed feature names mapped to human-readable labels. Deterministic, bounded background/reference sampling. Non-causal disclaimer on every result.
- Tests: `tests/unit/test_explainability.py` (LIME end-to-end, SHAP-unavailable error path, feature labels, background sampling, local fallback, global-unavailable, invalid input/unfitted pipeline) plus existing `tests/unit/test_explainability_optional.py` and `tests/unit/test_startup_optional_deps.py`.
- Documentation: `docs/WINDOWS_COMPATIBILITY.md`, README/IMPLEMENTATION_STATUS updated.

## Phase 7 — Prediction engine and application services (complete)

- `src/maintiq/ml/prediction/service.py` — `PredictionService`: single-record inference engine that loads fitted `ModelPipeline` artefacts from the model registry (`load_model`), validates input records against the canonical schema (`_validate_record`), runs inference (`predict`) returning a `PredictionResult` (class, score, threshold, input_validated, out_of_distribution_warnings), and surfaces category/domain drift warnings without blocking inference.
- `src/maintiq/ml/prediction/service.py` — `PredictionOutcome`: wraps a `PredictionResult` plus an optional `ExplanationResult` and an `explanation_error`.
- `PredictionService.predict_and_explain` — runs `predict`, then calls `explain_local` on the **exact same pipeline and record** (grounded in the same transformation/inference path), passing the provided background data as both the SHAP reference and LIME training reference. Explanation failures are captured in `explanation_error` and never fail the prediction. SHAP-unavailable → clear error; LIME works end-to-end in this env.
- `src/maintiq/ml/prediction/__init__.py`, `src/maintiq/ml/__init__.py` — export `PredictionService`, `PredictionOutcome`.
- `src/maintiq/services/application_service.py` — `ApplicationService`: dependency-injectable orchestration layer tying together import (`ImportWorkflowService`), training/registry (`ModelTrainer`/`ModelRegistry`), prediction (`PredictionService`), and reporting (`ReportService`). `train_model` falls back to the active imported dataset; `predict` loads a model version and predicts/explains; `export_report` emits atomic JSON reports. `__post_init__` ensures runtime directories exist.
- `src/maintiq/services/__init__.py` — exports `ApplicationService`.
- Tests: `tests/unit/test_prediction.py` (predict result shape, invalid/multi-row/before-fit errors, out-of-distribution & domain warnings, predict_and_explain with and without background, LIME end-to-end, auto fallback, registry load/latest/missing/no-registry) plus `tests/unit/test_application_service.py` (import/train/predict/report delegation, active-dataset fallback, missing-dataset error).

## Phase 9 — Reporting, exports, and registry UX (complete)

- `src/maintiq/ml/training/registry.py` — `ModelRegistry` gained `delete_version(model_name, version)` (removes a single version record, removes the model entry when its last version is deleted) and `delete_model(model_name)` (removes all versions for a model, returns count removed). Artefact files on disk are left intact. Both raise `RegistryError` when the target does not exist.
- `src/maintiq/services/application_service.py` — Added `export_csv(...)`, `export_png(...)`, `delete_model(...)`, and `delete_version(...)` delegation methods to `ApplicationService`, wrapping the corresponding `ReportService` and `ModelRegistry` calls.
- `src/maintiq/ui/pages/model_registry.py` — `ModelRegistryPage` enhanced with row selection, a details panel (metrics, parameters, artifact path, SHA-256, timestamps), "Delete selected version" and "Delete model" actions with `QMessageBox` confirmation, empty-state messaging when no models are registered, and persistent signal-object retention for cross-thread task delivery.
- `src/maintiq/ui/pages/reports.py` — `ReportsPage` enhanced with "Evaluation charts (PNG)" and "Export all (bundle)" report types, `set_evaluation_data(...)` to store y_true/scores/metrics for chart export, timestamped bundle subdirectories, and delegation to `report_service.export_png` / `export_csv` / `export_json` via the application service.
- Tests: `tests/unit/test_registry.py` (+6 delete tests), `tests/unit/test_application_service.py` (+5 delegation tests), `tests/gui/test_app.py` (+5 page interaction tests covering delete buttons, details panel, empty state, PNG-requires-data, export-all-requires-data).
- Test results (this audit): `pytest tests/unit -q` → **203 passed**; `pytest tests/gui -q` → **15 passed** (218 total); `ruff check src/ tests/` → **all checks passed**; `ruff format --check src/ tests/` → **92 files already formatted**.

## Phase 10 — Integration testing, security, hardening (complete)

- `tests/integration/test_end_to_end_flow.py` — Full end-to-end flow: import synthetic AI4I CSV → train model → registry → predict → explain (LIME) → export report; covers `logistic_regression` and `gradient_boosting` (pure-NumPy fallback); verifies registry versioning, latest-version load, and clear errors for missing models / no active dataset.
- `tests/integration/test_cross_service_integration.py` — ApplicationService delegation (import/train/predict/report), active-dataset fallback, version forwarding, and registry delete-then-load rejection.
- `tests/integration/test_cli_entrypoint.py` — `maintiq.__main__:main` entry point resolves; offscreen `create_application()` boots headlessly without a blocking event loop.
- `tests/integration/test_security_hardening.py` — Registry path-traversal rejection, SHA-256 tamper detection via `load_artifact`, report output-path/escaping and filename sanitization, import size-limit (`MAX_IMPORT_BYTES`) enforcement, missing/empty file rejection, and multi-row input rejection.
- Test results (this audit): `pytest tests/integration tests/unit -q` → **215 passed** (6 pre-existing SHAP-availability failures unrelated to this phase, see below); `ruff check src/ tests/` → **all checks passed**; `ruff format --check src/ tests/` → **all files formatted**.

## Phase 11 — Windows executable and installer (complete)

- `packaging/maintiq.spec` — PyInstaller one-file, windowed (`console=False`) spec building `MaintiQ.exe`. Bundles `assets/icons`, PySide6 platform/plugins, matplotlib QtAgg backend, scikit-learn, XGBoost, pandas, NumPy, joblib; SHAP/LIME bundled but imported lazily at runtime so their availability follows the same clear-error behavior as the dev environment (SHAP unavailable here due to the blocked sklearn.cluster chain; LIME works).
- `src/maintiq/config.py:113` — `_detect_project_root` is frozen-aware: under `sys.frozen` (PyInstaller bootloader) it resolves the project root to the directory of the executable, so assets installed next to the EXE resolve at runtime while user data (%LOCALAPPDATA%\MaintiQ) remains writable and outside the install directory.
- `packaging/maintiq-installer.iss` — Inno Setup 6 script producing `MaintiQ-Setup.exe`: per-machine install to `%ProgramFiles%\MaintiQ`, Start menu shortcut, optional desktop shortcut, uninstaller.
- `scripts/build_windows.ps1` — installs `requirements-packaging.txt` (pyinstaller), cleans build/release output, builds `release\MaintiQ-Portable\MaintiQ.exe` via `pyinstaller packaging\maintiq.spec`, then compiles `release\MaintiQ-Setup.exe` with `iscc` when Inno Setup is installed.
- `requirements-packaging.txt` — `pyinstaller>=6.0,<7.0` pin.
- `assets/icons/app.ico` — generated application icon (64×64 up to 256×256).

Build verification: `pyinstaller` build completes and produces `release\MaintiQ-Portable\MaintiQ.exe` (embedded bootloader, icon, manifest). Launch of the unsigned EXE is blocked by Windows Smart App Control / Application Control in this environment — the same code path was verified by launching `python -m maintiq` in Qt offscreen mode (window opens, event loop runs). Distribution requires an EV code-signed executable or end-user bypass of the Smart App Control block; signing does not unblock blocked third-party `.pyd` files under these policies (see `docs/WINDOWS_COMPATIBILITY.md`).

## Phase 8 — Native desktop GUI with PySide6 (complete)

- `src/maintiq/ui/app.py` — QApplication bootstrap with fallback application icon and `run()` entry point; `python -m maintiq` launches the native window.
- `src/maintiq/ui/main_window.py` — `QMainWindow` shell: sidebar navigation (12 pages), stacked widget, menu bar (File import dataset / exit; Help about), status bar, persistent academic-prototype notice banner.
- `src/maintiq/ui/pages/` — 12 thin page widgets, each delegating to `ApplicationService` and submitting long-running work to a background worker: Dashboard, Predict Failure, Explain Prediction, Dataset Explorer, EDA / Visualisation, Model Performance, Threshold Analysis, Model Training, Model Registry, Reports and Downloads, Settings, About / Limitations. No model-training logic lives in UI modules (enforced by `tests/gui/test_app.py::test_ui_modules_contain_no_training_logic`).
- `src/maintiq/ui/worker.py`, `src/maintiq/ui/signals.py` — `QRunnable`/`QThreadPool` workers with typed Qt signals (`started`, `progress`, `result`, `error`, `finished`); signal objects are retained until delivery so cross-thread events are not dropped. Cancellation-friendly training via `cancelled_check`.
- `src/maintiq/ui/widgets/canvas.py` — Matplotlib QtAgg canvas embedded in Qt (no browser/web engine).
- `src/maintiq/ui/widgets/metric_card.py`, `form_input.py` (six canonical AI4I attributes), `table_view.py`, `status_banner.py`.
- `src/maintiq/ui/styles.py` — restrained navy/charcoal stylesheet with teal accent.
- `src/maintiq/services/application_service.py` — `train_model` gained an optional `progress_callback` for GUI progress reporting.
- Tests: `tests/gui/test_app.py` + `tests/gui/conftest.py` — offscreen-mode smoke tests covering QApplication creation, main window construction, all 12 pages, navigation switching, page titles, validation error display, stubbed end-to-end prediction, explain/dataset/threshold error paths, and service mocking.
- Test results (this audit): `pytest tests/ -q` → **202 passed**; `ruff check src/ tests/` → **all checks passed**; `ruff format --check src/ tests/` → **92 files already formatted**.

## Dataset verification

- `assets/datasets/` directory exists but is empty. AI4I 2020 dataset is **not present** in the repository.
- No benchmark metrics or training results are claimed without the real dataset.
- The import workflow (`ImportWorkflowService`) is available for user-selected CSV import.

## Remaining Windows security limitations

- SHAP explanations unavailable when sklearn cluster extensions are blocked by Application Control/Smart App Control (confirmed here).
- Some sklearn compiled submodules may be blocked depending on policy; MaintiQ avoids unnecessary startup imports but cannot make blocked third-party `.pyd` files loadable.
- Signing the MaintiQ installer does not by itself resolve blocked/unsigned dependency binaries under these policies.
- Unsigned executable builds are blocked by Smart App Control in this environment; distribution requires an EV code-signed EXE/installer or end-user bypass of the policy block (observed at build verification).

## Phase 12 — Final release, documentation, university alignment (complete)

### Files added

- `docs/MODEL_CARD.md` — training setup, evaluation, caveats, intended use (model card per governance requirements).
- `docs/USER_GUIDE.md` — step-by-step first-time Windows user guide: install, launch, dataset import, training, prediction, evaluation, thresholds, reports, registry, settings, troubleshooting.
- `docs/DEVELOPER_GUIDE.md` — environment setup, run/test/lint commands, packaging, project layout, conventions.
- `docs/QA_CHECKLIST.md` — tested workflows with actual results (203 unit + 15 GUI passed, ruff clean).
- `docs/RELEASE_NOTES.md` — release notes with release manifest (version 0.1.0, build date, Python 3.13.14, dependency versions, executable SHA-256, test results, known limitations, university-submission mapping).
- `docs/SCREENSHOT_CHECKLIST.md` — university demonstration screenshot checklist.
- `docs/screenshots/main_window.png` — real screenshot of the running application (1100×720).
- `docs/screenshots/dashboard.png`, `predict_failure.png`, `model_registry.png`, `reports_downloads.png`, `about_limitations.png` — real screenshots of key pages.

### Governance files now complete

`README.md`, `CHANGELOG.md`, `IMPLEMENTATION_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, `docs/FEATURE_ENGINEERING.md`, `docs/MODEL_CARD.md`, `docs/USER_GUIDE.md`, `docs/DEVELOPER_GUIDE.md` — all cross-references in `README.md` resolve.

### Test and quality results (phase 12 verification)

- `pytest tests/unit -q` → **203 passed**
- `pytest tests/gui -q` → **15 passed** (Qt offscreen mode)
- `pytest tests/ -q` → **218 passed**
- `ruff check src/ tests/` → **all checks passed**
- `ruff format --check src/ tests/` → **97 files already formatted**

### Release artefacts

- `release\MaintiQ-Portable\MaintiQ.exe` — PyInstaller one-file executable, SHA-256 `927616252543DE31AB4D6DBE721EDAF8206B4F799D63201BC491990CD9846459`
- `packaging\maintiq-installer.iss` — Inno Setup 6 installer script (produces `MaintiQ-Setup.exe` when `iscc` is available)
- `packaging\maintiq.spec` — PyInstaller spec

### Tests fixed during phase 12

Six tests that hard-coded SHAP-unavailable expectations were updated to match the current environment (SHAP 0.54.1 importable): `test_shap_status_reports_available`, `test_require_shap_returns_module`, `test_explain_with_shap_returns_result`, `test_explain_local_prefers_shap_when_available`, `test_explain_global_returns_result`, `test_predict_and_explain_prefers_shap_when_available`. The GUI PNG-export test was fixed to mock the modal file dialog for headless/offscreen runs. SHAP-unavailable behaviour remains covered by monkeypatched tests in `tests/unit/test_explainability_optional.py`.

### Repo hygiene

- Root scratch `.log` files from earlier phases removed.
- Secret scan clean; no secrets, keys, or personal data in the repository.
- Large files confined to gitignored `.venv`, `build/`, `release/`.

### Known limitations (carried forward)

- SHAP unavailable when `sklearn.cluster` native extensions are blocked by Windows Application Control/Smart App Control; clear error, LIME fallback where importable.
- Unsigned `MaintiQ.exe` launch blocked by Smart App Control in this environment; distribution requires EV code-signing or end-user bypass.
- AI4I 2020 dataset not bundled; no default trained model shipped; no benchmark metrics claimed without the real dataset.
- Screenshots in `docs/screenshots/` were captured from the running application code; remaining demo screenshots are to be captured from `MaintiQ.exe` after the Smart App Control block is resolved.

## Final release summary

- Project root: `C:\ARRU CODES\projects\MaintiQ`
- Phases completed: 0–12 (all complete). No incomplete phases.
- Main modules: `core`, `data`, `domain`, `ml/{preprocessing,features,training,evaluation,prediction,explainability}`, `registry`, `reporting`, `services`, `ui` (PySide6, 12 pages).
- Desktop pages: Dashboard, Predict Failure, Explain Prediction, Dataset Explorer, EDA/Visualisation, Model Performance, Threshold Analysis, Model Training, Model Registry, Reports and Downloads, Settings, About/Limitations.
- Dataset: AI4I 2020 not bundled; user imports via CSV (`assets/datasets/` empty).
- Models: Logistic Regression, Random Forest, Gradient Boosting (pure-NumPy fallback), XGBoost — no model trained on real AI4I data; no benchmark metrics claimed.
- Automated tests: 218 passed (203 unit + 15 GUI); ruff lint and format clean.
- Exact launch command (development): `python -m maintiq` (after `pip install -e .` and `pip install -r requirements-dev.txt`).
- Executable: `release\MaintiQ-Portable\MaintiQ.exe` (built, not launch-tested due to Smart App Control block on unsigned EXE; `python -m maintiq` verified in offscreen mode).
- Installer: `packaging\maintiq-installer.iss` (Inno Setup; `MaintiQ-Setup.exe` not compiled here — Inno Setup not confirmed available in this environment).
- Windows executable/installer smoke-tested on Windows: no (unsigned EXE launch blocked by Smart App Control; code path verified via `python -m maintiq` offscreen).
- Missing prerequisites: EV code signing for distribution; Inno Setup for `MaintiQ-Setup.exe` compilation; real AI4I dataset for benchmark evaluation.
- Next action: none — project complete; ready for academic demonstration subject to documented limitations.
