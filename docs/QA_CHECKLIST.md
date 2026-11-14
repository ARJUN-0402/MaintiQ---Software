# MaintiQ QA Checklist

**Version:** 0.1.0  
**Environment:** Windows, PowerShell 5.1, Python 3.13.14 (`.venv`), scikit-learn 1.9.1, PySide6 6.12.0  
**Date:** 2026-11-14  
**Scope:** All implemented phases (0–11); phase 12 is documentation and release handover.

> **MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark
> dataset. Predictions and explanations are model outputs, not certified industrial
> diagnoses or maintenance instructions. Qualified human review is required.**

## 1. Automated test results

| Suite | Command | Result |
|-------|---------|--------|
| Unit tests | `pytest tests/unit -q` | 203 passed |
| GUI tests | `pytest tests/gui -q` | 15 passed (Qt offscreen mode) |
| Combined unit + GUI | `pytest tests/ -q` | 218 passed |

Note: `pytest tests/integration tests/unit -q` previously reported 215 passed with 6 pre-existing
SHAP-availability failures unrelated to this phase; after the runtime environment changed
(SHAP 0.54.1 and `sklearn.cluster` now importable in this environment), six tests that had
hard-coded SHAP-unavailable expectations were updated to match the real environment. The
SHAP-unavailable behaviour remains covered by monkeypatched tests in
`tests/unit/test_explainability_optional.py`.

## 2. Quality checks

| Check | Command | Result |
|-------|---------|--------|
| Lint | `ruff check src/ tests/` | All checks passed |
| Format check | `ruff format --check src/ tests/` | 97 files already formatted |

## 3. Workflow checklist

| # | Workflow | Status | Evidence |
|---|----------|--------|----------|
| 1 | Package imports; `maintiq.__title__ == "MaintiQ"` | Passed | `tests/unit` config/import tests |
| 2 | Configuration resolves all paths; runtime directories creatable | Passed | `tests/unit` configuration/path tests |
| 3 | Logging initializes with rotating file handler | Passed | `tests/unit` logging tests |
| 4 | CSV import, validation, profiling (synthetic fixture) | Passed | `tests/unit` data-layer tests |
| 5 | Preprocessing: missing values, encoding, unknown category, train/test separation, serialization | Passed | `tests/unit` preprocessing tests |
| 6 | Feature engineering formulas, fitted torque reference, edge cases | Passed | `tests/unit` feature-engineering tests |
| 7 | Model factory training for LR/RF/GB/XGB; registry CRUD; atomic writes; SHA-256 verification; hash-mismatch rejection | Passed | `tests/unit/test_registry.py` (21 tests + delete tests) |
| 8 | Evaluation metrics, threshold analysis, comparison, charts, reporting exports | Passed | `tests/unit` evaluation/reporting tests |
| 9 | Explainability: LIME end-to-end, SHAP available end-to-end, SHAP-unavailable clear error (monkeypatched), global importance, feature labels, background sampling | Passed | `tests/unit/test_explainability.py`, `test_explainability_optional.py` |
| 10 | Prediction service: single-record inference, validation, OOD warnings, predict_and_explain with both backends, registry load/latest/missing | Passed | `tests/unit/test_prediction.py` |
| 11 | ApplicationService delegation, active-dataset fallback, missing-dataset error | Passed | `tests/unit/test_application_service.py` |
| 12 | End-to-end integration: CSV → validation → training → registry → predict → explain (LIME) → export report; LR and Gradient Boosting fallback | Passed | `tests/integration/test_end_to_end_flow.py` |
| 13 | Cross-service integration (import/train/predict/report delegation, version forwarding, delete-then-load rejection) | Passed | `tests/integration/test_cross_service_integration.py` |
| 14 | CLI entrypoint resolves; offscreen `create_application()` boots headlessly | Passed | `tests/integration/test_cli_entrypoint.py` |
| 15 | Security hardening: path-traversal rejection, SHA-256 tamper detection, report output sanitization, import size limit, missing/empty file rejection, multi-row input rejection | Passed | `tests/integration/test_security_hardening.py` |
| 16 | GUI: QApplication creation, main window, all 12 pages, navigation, titles, validation errors, stubbed predict/explain/registry/report flows, no training logic in UI modules | Passed | `tests/gui/test_app.py` (15 tests) |
| 17 | `python -m maintiq` launches native PySide6 window in Qt offscreen mode; event loop runs | Passed | Verified by launch; `test_module_entrypoint_starts` |
| 18 | PyInstaller build produced `release\MaintiQ-Portable\MaintiQ.exe` | Passed | `.\scripts\build_windows.ps1` build verification |

## 4. Known limitations (documented, not defects)

- SHAP unavailable under Windows Application Control when `sklearn.cluster` native extensions are blocked; clear error reported, LIME fallback available.
- Some scikit-learn compiled submodules may be blocked depending on policy; MaintiQ avoids eager startup imports but cannot load blocked third-party `.pyd` files.
- Unsigned executable builds blocked by Smart App Control; distribution requires an EV code-signed executable/installer or end-user bypass.
- The AI4I 2020 dataset is not bundled; the user imports it via CSV. No benchmark metrics are claimed without the real dataset.
- No default trained model is shipped.

## 5. Sign-off

- [ ] All automated checks pass (unit + GUI, lint, format).
- [ ] Documentation matches implementation (`docs/`, `README.md`, `IMPLEMENTATION_STATUS.md`).
- [ ] Release artefacts exist (`release\MaintiQ-Portable\MaintiQ.exe`; Inno Setup installer configuration in `packaging\maintiq-installer.iss`).
- [ ] Windows build/test status stated truthfully (unsigned EXE launch blocked by Smart App Control in this environment).
- [ ] Academic prototype limitation displayed in the UI and in generated reports.
