# MaintiQ Release Notes

## [0.2.0] — 2026-11-14

**Release date:** 2026-11-14  
**Application:** MaintiQ — Industrial Failure Prediction with Explainable Artificial Intelligence  
**Academic basis:** Uttaranchal University BCA project synopsis (AI4I 2020 Predictive Maintenance Dataset)  
**Status:** Release — version bump 0.1.0 → 0.2.0; no machine-learning changes.

> **MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark
> dataset. Predictions and explanations are model outputs, not certified industrial
> diagnoses or maintenance instructions. Qualified human review is required.**

### What is new in v0.2.0

- **Version bump 0.1.0 → 0.2.0**, applied consistently across:
  - `pyproject.toml` (`[project] version = "0.2.0"`)
  - `src/maintiq/__init__.py` (`__version__`), `src/maintiq/config.py` (`APP_VERSION`)
  - `packaging\maintiq-installer.iss` (`MyAppVersion`)
  - About page, window title, and generated reports consume the single `__version__` source of truth.
- Release documentation updated: `README.md`, `docs/MODEL_CARD.md`, `docs/DEVELOPER_GUIDE.md`, `docs/USER_GUIDE.md`, `docs/QA_CHECKLIST.md`, `docs/SCREENSHOT_CHECKLIST.md`.
- Tests updated to assert version 0.2.0: `tests/unit/test_config.py`, `tests/unit/test_reporting.py`.
- **No machine-learning functionality was modified.** Training, prediction, evaluation, thresholds, explainability (SHAP/LIME), and registry behaviour are unchanged from v0.1.0.

### Release artefacts

| Artefact | Path | Notes |
|----------|------|-------|
| Source package | `src/maintiq/` | Version 0.2.0 |
| Installer script | `packaging\maintiq-installer.iss` | Inno Setup 6; `MaintiQ-Setup.exe` compiled with Inno Setup 6.7.3 and installation-tested in a dedicated test directory (install, Start Menu shortcut, optional desktop shortcut, uninstall verified). |
| PyInstaller spec | `packaging\maintiq.spec` | Tracked source asset; builds a one-folder distribution |

### Version manifest

| Field | Value |
|-------|-------|
| Application | MaintiQ |
| Version | 0.2.0 |
| Release date | 2026-11-14 |
| Previous version | 0.1.0 (2026-11-14) |

### Known limitations

- The AI4I 2020 dataset is not bundled; import it via Dataset Explorer before training. No benchmark metrics are claimed without the real dataset; no default trained model is shipped.
- SHAP is unavailable when `sklearn.cluster` native extensions are blocked by Windows Application Control/Smart App Control; LIME works where importable. Unavailability is reported explicitly — no explanations are fabricated.
- Unsigned `MaintiQ.exe` builds are blocked by Windows Smart App Control in this environment. Public distribution requires a suitable trusted code-signing certificate (EV certification is not specifically mandatory; signing does not guarantee that every security warning disappears). The final signed distribution should be tested on a clean Windows machine with Smart App Control enabled. End users should not be advised to disable Windows security or bypass application-control policies; signing does not unblock blocked third-party `.pyd` files.
- **Trusted code-signing certificate pending.** No code-signing certificate is available in this environment.
- **Inno Setup installer compilation.** `ISCC.exe` was installed; `MaintiQ-Setup.exe` compiled with Inno Setup 6.7.3 and installation-tested in a dedicated test directory.
- **Clean-machine Smart App Control testing pending.** No clean Windows 10/11 machine or VM is available; all EXE/Smart App Control results were observed on the development machine.
- The compiled Inno Setup installer (`release\MaintiQ-Setup.exe`) has been produced with Inno Setup 6.7.3 and installation-tested in a dedicated test directory.
- Gradient Boosting uses a pure-NumPy fallback when the scikit-learn native gradient-boosting extension is unavailable.

---

# MaintiQ Release Notes — v0.1.0 (historical, preserved)

> **MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark
> dataset. Predictions and explanations are model outputs, not certified industrial
> diagnoses or maintenance instructions. Qualified human review is required.**

## What is new in v0.1.0

Initial public/academic release. Implemented phases:

| Phase | Title | Contents |
|-------|-------|----------|
| 0 | Project foundation and architecture | `src/` layout, typed configuration, logging, exceptions, entry point, package metadata |
| 1 | Dataset ingestion, schema, and data quality | AI4I schema, CSV loader, validator, profiler, import workflow |
| 2 | Preprocessing pipeline | Leakage-safe imputation, encoding, scaling; stratified splits; pipeline serialization |
| 3 | Feature engineering | `temperature_diff`, `power_kw`, `wear_rate_proxy`, `torque_normalized`, `temp_wear_interaction` |
| 4 | Model training and model registry | LR, RF, GB, XGBoost training; JSON model registry with versioning, SHA-256 hashes, atomic writes |
| 5 | Model evaluation and threshold analysis | Metrics, confusion matrix, ROC/PR, leakage-safe threshold analysis, model comparison, charts |
| 6 | Explainable AI with SHAP and LIME | Local and global explanations, feature labels, clear errors when a backend is unavailable |
| 7 | Prediction engine and application services | Single-record inference, OOD warnings, predict-and-explain, ApplicationService orchestration |
| 8 | Native desktop GUI with PySide6 | 12-page window, background workers, Matplotlib canvases, stylesheet |
| 9 | Reporting, exports, and registry UX | JSON/CSV/PNG exports, registry delete UX, report bundles |
| 10 | Integration testing, security, hardening | End-to-end, cross-service, CLI, security tests; QA checklist |
| 11 | Windows executable and installer | PyInstaller one-folder `MaintiQ.exe`, Inno Setup installer script, build script |

## Release artefacts

| Artefact | Path | Notes |
|----------|------|-------|
| Portable executable | `release\MaintiQ-Portable\MaintiQ.exe` | PyInstaller one-file, windowed, SHA-256 below |
| Installer script | `packaging\maintiq-installer.iss` | Inno Setup 6; `MaintiQ-Setup.exe` produced when `iscc` is available |
| PyInstaller spec | `packaging\maintiq.spec` | Bundles PySide6, Matplotlib, scikit-learn, XGBoost, LIME, icons (SHAP and `sklearn.cluster` excluded from the package by design) |

**Executable SHA-256:** `927616252543DE31AB4D6DBE721EDAF8206B4F799D63201BC491990CD9846459`
(`release\MaintiQ-Portable\MaintiQ.exe`)

## Release manifest

| Field | Value |
|-------|-------|
| Application | MaintiQ |
| Version | 0.1.0 |
| Build date | 2026-11-14 |
| Build platform | Windows (PowerShell 5.1) |
| Python runtime | 3.13.14 |
| pandas | 2.3.3 |
| NumPy | 2.5.4 |
| scikit-learn | 1.9.1 |
| XGBoost | 2.1.4 |
| SHAP | 0.54.1 |
| LIME | 0.2.0.1 |
| Matplotlib | 3.11.2 |
| PySide6 | 6.12.0 |
| joblib | 1.6.0 |
| Test results | `pytest tests/unit -q`: 203 passed; `pytest tests/gui -q`: 15 passed |
| Lint | `ruff check src/ tests/`: all checks passed |
| Format | `ruff format --check src/ tests/`: 97 files formatted |

## How to run

Development:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install -r requirements-dev.txt
python -m maintiq
```

Installed end-user machine: run `MaintiQ-Setup.exe`, then launch MaintiQ from the Start Menu.
No separate Python installation is required.

## Known limitations

- The AI4I 2020 dataset is not bundled; import it via Dataset Explorer before training. No benchmark metrics are claimed without the real dataset; no default trained model is shipped.
- SHAP is unavailable when `sklearn.cluster` native extensions are blocked by Windows Application Control/Smart App Control; LIME works where importable. Unavailability is reported explicitly — no explanations are fabricated.
- Unsigned `MaintiQ.exe` builds are blocked by Windows Smart App Control in this environment. Public distribution requires a suitable trusted code-signing certificate (EV certification is not specifically mandatory; signing does not guarantee that every security warning disappears). The final signed distribution should be tested on a clean Windows machine with Smart App Control enabled. End users should not be advised to disable Windows security or bypass application-control policies; signing does not unblock blocked third-party `.pyd` files.
- All outputs require qualified human review; this is not a certified industrial diagnostic product.

## University submission mapping

Documentation maps features to the synopsis requirements: introduction/objectives, technology and requirements, problem definition, functional/non-functional requirements, modules and process logic, data structures, reports, security mechanisms, limitations, and future scope. See `docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, `docs/FEATURE_ENGINEERING.md`, `docs/MODEL_CARD.md`, `docs/USER_GUIDE.md`, `docs/DEVELOPER_GUIDE.md`, `docs/QA_CHECKLIST.md`.
