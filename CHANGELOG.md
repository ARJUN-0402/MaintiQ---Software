# Changelog

## [0.1.0] — 2026-11-14

### Added
- Phase 0: project foundation and architecture
  - `src/` layout Python package `maintiq`
  - Centralised typed configuration (`src/maintiq/config.py`)
  - Custom exception types (`src/maintiq/core/exceptions.py`)
  - Rotating-file logging (`src/maintiq/core/logging.py`)
  - Application entry point (`src/maintiq/__main__.py`)
  - `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`
  - `README.md`, `CHANGELOG.md`, `IMPLEMENTATION_STATUS.md`, `docs/ARCHITECTURE.md`
  - Initial unit tests for configuration, paths, logging, and imports

## [0.1.0] — 2026-11-14 (continued)

### Added — Phase 4: Model Registry
- `src/maintiq/ml/training/registry.py` — `ModelRegistry`: JSON-backed registry with per-model monotonic versioning, schema versioning, atomic writes, path-traversal prevention, SHA-256 verification, defensive copies, NumPy-safe JSON serialization, thread lock.
- Exceptions `RegistryError`, `ModelHashMismatchError` in `src/maintiq/core/exceptions.py`.
- Integrated registry registration into `ModelTrainer.train_model()`.
- Tests: `tests/unit/test_registry.py` (21 tests).

### Added — Phase 5: Evaluation and Threshold Analysis
- `src/maintiq/ml/evaluation/service.py` — Hardened `EvaluationService`: accuracy, precision, recall, F1, ROC-AUC, confusion matrix, specificity, balanced accuracy, FPR, FNR, average precision. Threshold validation [0,1], positive-class mapping, single-class ROC-AUC → None, JSON-safe primitives.
- `src/maintiq/ml/evaluation/threshold.py` — `ThresholdAnalysisService`: leakage-safe threshold selection on validation scores, configurable grid, deterministic tie-breaking.
- `src/maintiq/ml/evaluation/comparison.py` — `ComparisonService`: compares LR/RF/GB/XGB on identical partitions, unavailable models reported explicitly.
- `src/maintiq/ml/evaluation/charts.py` — Matplotlib charts: model comparison, confusion matrix, ROC curve, PR curve, threshold vs metric, FP/FN trade-off.
- `src/maintiq/reporting/service.py` — `ReportService`: JSON, CSV, PNG exports with atomic writes and filename sanitization.
- Tests: `test_evaluation.py`, `test_threshold.py` (14), `test_comparison.py` (5), `test_charts.py` (8), `test_reporting.py` (7).

## [0.1.0] — 2026-11-14 (continued)

### Added — Phase 8: Native desktop GUI with PySide6
- `src/maintiq/ui/app.py` — QApplication bootstrap and `run()` entry point; `python -m maintiq` now launches the native window.
- `src/maintiq/ui/main_window.py` — `QMainWindow` shell with sidebar navigation, 12 stacked pages, menu bar, status bar, persistent academic-prototype notice.
- `src/maintiq/ui/pages/` — 12 thin page widgets: Dashboard, Predict Failure, Explain Prediction, Dataset Explorer, EDA/Visualisation, Model Performance, Threshold Analysis, Model Training, Model Registry, Reports and Downloads, Settings, About/Limitations. All delegate to `ApplicationService`; no model-training logic in UI modules.
- `src/maintiq/ui/worker.py`, `src/maintiq/ui/signals.py` — `QRunnable`/`QThreadPool` background workers with typed Qt signals; training, prediction, explanation, and export run off the UI thread with progress reporting and safe cancellation.
- `src/maintiq/ui/widgets/` — Matplotlib QtAgg canvas, metric cards, prediction input form (six canonical attributes), read-only table view, status banners.
- `src/maintiq/ui/styles.py` — restrained navy/charcoal stylesheet with teal accent.
- `src/maintiq/services/application_service.py` — `train_model` accepts an optional `progress_callback` for GUI progress reporting.
- Tests: `tests/gui/test_app.py` and `tests/gui/conftest.py` — offscreen-mode smoke tests for application startup, navigation, all pages, validation error display, service mocking/stubbing, end-to-end predict, and absence of training logic in UI modules.
- `202 total tests pass; ruff check and ruff format clean.`


