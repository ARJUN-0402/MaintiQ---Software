# MaintiQ Developer Guide

**MaintiQ v0.2.0** — Industrial Failure Prediction with Explainable Artificial Intelligence

> **MaintiQ is an academic decision-support prototype using the AI4I 2020 benchmark
> dataset. Predictions and explanations are model outputs, not certified industrial
> diagnoses or maintenance instructions. Qualified human review is required.**

## 1. Project layout

```
MaintiQ/
├── src/maintiq/           # Application source (src layout)
│   ├── core/              # Configuration, logging, exceptions, paths
│   ├── data/              # Dataset schema, loader, validator, profiler, import workflow
│   ├── domain/            # Typed business entities
│   ├── ml/                # preprocessing, features, training, evaluation, prediction, explainability
│   ├── registry/          # JSON model registry (re-exported via maintiq.registry)
│   ├── reporting/         # ReportService: JSON/CSV/PNG exports
│   ├── services/          # ApplicationService orchestration layer
│   ├── ui/                # PySide6 desktop GUI (app, main_window, pages, widgets, worker, signals, styles)
│   ├── __init__.py        # __version__, __title__, __description__, __academic_notice__
│   └── __main__.py        # `python -m maintiq` entry point
├── assets/
│   ├── icons/             # app.ico
│   └── datasets/          # AI4I sample CSV present in source (not bundled in the EXE; user imports it at runtime)
├── config/                # configuration files
├── docs/                  # architecture, data dictionary, feature engineering, model card, user guide, developer guide, QA checklist, release notes
├── packaging/             # maintiq.spec (tracked PyInstaller spec), maintiq-installer.iss (Inno Setup)
├── scripts/
│   └── build_windows.ps1  # Windows build script
├── tests/
│   ├── unit/              # unit tests
│   ├── integration/       # end-to-end, cross-service, CLI, security tests
│   └── gui/               # offscreen-mode PySide6 smoke tests
├── pyproject.toml         # package metadata, dependencies, ruff config
├── requirements.txt       # runtime dependencies
├── requirements-dev.txt   # dev dependencies (pytest, pytest-qt, ruff)
├── README.md
└── CHANGELOG.md
```

## 2. Environment setup (Windows)

Python 3.11+ is required (developed and tested with Python 3.13 in this
environment). Do not weaken the machine-wide PowerShell execution policy; if
script activation is blocked, invoke the virtual environment's Python directly.

```powershell
# Create and activate a virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install the package in editable mode
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
```

If `Activate.ps1` is blocked:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 3. Run the application (development)

```powershell
python -m maintiq
```

The native PySide6 desktop GUI launches. `maintiq` console script is also
registered via `pyproject.toml` (`[project.scripts] maintiq = "maintiq.__main__:main"`).

The AI4I sample CSV is present in `assets/datasets/` but is not bundled in
the executable and is not auto-loaded on first launch; import it via the
Dataset Explorer before training or predicting (see docs/USER_GUIDE.md).

## 4. Test commands

```powershell
# Full test suite (unit + integration + GUI, Qt offscreen mode)
pytest

# Unit tests only
pytest tests/unit

# GUI smoke tests only (QT_QPA_PLATFORM=offscreen is set by tests/gui/conftest.py)
pytest tests/gui

# Integration tests only
pytest tests/integration

# Verbose run of a single file
pytest tests/unit/test_registry.py -v
```

GUI tests run headlessly using Qt's offscreen platform; no display is required.

## 5. Quality checks

```powershell
# Lint
ruff check src/ tests/

# Format check
ruff format --check src/ tests/

# Apply formatting
ruff format src/ tests/
```

Ruff is configured in `pyproject.toml` (`line-length = 100`, target `py310`,
src layout `src`). No separate type checker is configured; ruff rules cover
import sorting, unused imports, and common bugs.

## 6. Packaging (Windows)

```powershell
.\scripts\build_windows.ps1
```

What it does:

1. Installs `requirements-packaging.txt` (`pyinstaller>=6.0,<7.0`).
2. Cleans `build/` and `release/MaintiQ-Portable/` output.
3. Builds `release/MaintiQ-Portable/MaintiQ/` via PyInstaller
   (`packaging\maintiq.spec`): a **one-folder**, windowed executable bundling
   PySide6 plugins, Matplotlib, scikit-learn, XGBoost, pandas, NumPy, joblib,
   LIME, icons, and package resources. SHAP and `sklearn.cluster` are excluded
   from the bundle (SHAP is optional; its `sklearn.cluster` native extension is
   blocked by Windows Application Control on locked-down systems).
4. Compiles `release\MaintiQ-Setup.exe` with Inno Setup (`iscc`) when Inno Setup
   is installed (`packaging\maintiq-installer.iss`).

Outputs:

- `release\MaintiQ-Portable\MaintiQ\MaintiQ.exe` — portable one-folder executable.
- `release\MaintiQ-Setup.exe` — Windows installer (when Inno Setup is available).

The executable stores user data under `%LOCALAPPDATA%\MaintiQ` (frozen-aware
project-root detection), so user data is never written into the protected
install directory. The workflow works offline after installation; no browser or
hosted service is required.

Build notes observed in this environment:

- Launch of the unsigned `MaintiQ.exe` is blocked by Windows Smart App Control /
  Application Control. Public distribution requires a suitable trusted
  code-signing certificate (EV certification is not specifically mandatory;
  signing does not guarantee that every security warning disappears). The final
  signed distribution should be tested on a clean Windows machine with Smart App
  Control enabled. End users should not be advised to disable Windows security
  or bypass application-control policies.
- Some scikit-learn native extensions (e.g. `sklearn.cluster`) may be blocked by
  Application Control, which makes SHAP unavailable in locked-down Windows
  environments. LIME works where importable. Signing does not unblock blocked
  third-party `.pyd` files under these policies.
- `packaging\maintiq-installer.iss` and build output under `build/` and
  `release/` are gitignored; `packaging\maintiq.spec` is tracked.

## 7. Dependency groups

Runtime (`requirements.txt`): pandas, NumPy, scikit-learn, XGBoost, SHAP, LIME,
Matplotlib, PySide6, joblib.

Dev (`requirements-dev.txt`): pytest, pytest-qt, ruff.

Packaging (`requirements-packaging.txt`): PyInstaller.

Optional dependencies (SHAP/LIME) are imported lazily; application startup does
not require them.

## 8. Version and release

- Package version: `0.2.0` (`pyproject.toml`, `src/maintiq/__init__.py`).
- Release notes: `docs/RELEASE_NOTES.md`.
- QA checklist: `docs/QA_CHECKLIST.md`.

## 9. Conventions

- Type hints and docstrings on public modules; dataclasses for configuration and
  results.
- `pathlib.Path` for all paths; no hard-coded absolute developer paths.
- Writable runtime data under `%LOCALAPPDATA%\MaintiQ`; never in the install
  directory.
- Imported CSVs treated as untrusted (200 MB cap, no macro/script execution).
- Registered model artefacts verified by SHA-256 before load; no arbitrary
  Joblib/pickle loading.
- UI modules are thin and delegate to `ApplicationService`; no model-training
  logic in UI modules (enforced by
  `tests/gui/test_app.py::test_ui_modules_contain_no_training_logic`).
