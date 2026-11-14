# MaintiQ — Phase 1: Packaging and Native Dependency Audit

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Diagnostic audit only. No source edits, no rebuild, no signing.  
**Evidence standard:** Each item marked PASS / FAIL / BLOCKED / NOT TESTED. No invented hashes or results.

---

## 1. Build environment — exact dependency versions

| Package | Version | Source |
|---|---|---|
| Python | 3.13.14 (tags/v3.13.14, MSC v.1944, AMD64) | `sys.version` |
| CPython ABI tag | cp313-win_amd64 | interpreter |
| pandas | 2.3.3 | `importlib.metadata` |
| numpy | 2.5.4 | `importlib.metadata` |
| scikit-learn | 1.9.1 | `importlib.metadata` |
| xgboost | 2.1.4 | `importlib.metadata` |
| shap | 0.54.1 | `importlib.metadata` |
| lime | 0.2.0.1 | `importlib.metadata` |
| matplotlib | 3.11.2 | `importlib.metadata` |
| PySide6 | 6.12.0 | `importlib.metadata` |
| joblib | 1.6.0 | `importlib.metadata` |
| PyInstaller | 6.22.3 | `importlib.metadata` |
| pytest | 9.2.0 | `importlib.metadata` |

`pyproject.toml` `[project.dependencies]` declares all of the above as **hard runtime dependencies** — including `shap` and `lime`, although the code imports both lazily. `requirements-packaging.txt` pins `pyinstaller>=6.0,<7.0`. No lockfile exists; versions are ranges only.

Baseline checks: **221 tests passed** (unit + integration), `ruff check` clean, `ruff format --check` clean (97 files formatted).

---

## 2. Import chain — eager startup vs lazy feature-only

### Startup path (`python -m maintiq`)

```
__main__.py
  └─ maintiq/__init__.py          (version metadata only)
       └─ main() -> maintiq.ui.app:run
            ├─ PySide6 (QtCore, QtGui, QtWidgets)              EAGER
            ├─ maintiq.config                                  EAGER
            ├─ maintiq.services.ApplicationService             EAGER
            │    ├─ maintiq.data.import_workflow               EAGER
            │    ├─ maintiq.ml.prediction.service              EAGER
            │    ├─ maintiq.ml.training (ModelRegistry, Trainer) EAGER
            │    │    ├─ factory (sklearn/xgboost imports INSIDE build_model — lazy per model)
            │    │    ├─ pipeline (joblib, numpy, pandas, sklearn.base)
            │    │    └─ registry (joblib, numpy, pandas)
            │    └─ maintiq.reporting.service                  EAGER (matplotlib charts)
            └─ maintiq.ui.main_window                          EAGER
                 └─ ui/pages/__init__  -> ALL 12 pages imported EAGER at MainWindow construction
                      ├─ explain.py       -> maintiq.ml.explainability (lazy shap/lime — NOT imported at import time)
                      ├─ eda.py           -> matplotlib (EAGER via MatplotlibCanvas widget)
                      ├─ model_training.py-> config/services only
                      └─ ... other pages (PySide6 + services only)
```

Empirically verified at startup:
- `sklearn.cluster` loaded: **False**
- `shap` loaded: **False**
- `lime` loaded: **False**
- `xgboost` loaded: **False**
- `sklearn` loaded: **True** (via `sklearn.base`, `sklearn.preprocessing`, `sklearn.model_selection` in feature transformer/preprocessor — none of these pull `sklearn.cluster`)

### Lazy (feature-only) imports

| Symbol | Where | Trigger |
|---|---|---|
| `shap` | `maintiq/ml/explainability.py: require_shap()` / `explain_with_shap()` | Explain page, backend = shap/auto |
| `lime` | `maintiq/ml/explainability.py: require_lime()` / `explain_with_lime()` | Explain page, backend = lime/auto |
| `sklearn.linear_model.LogisticRegression` | `ml/training/factory.py: build_model()` | Train Logistic Regression |
| `sklearn.ensemble._forest.RandomForestClassifier` | `ml/training/factory.py: build_model()` | Train Random Forest |
| `xgboost.XGBClassifier` | `ml/training/factory.py: build_model()` | Train XGBoost |
| `maintiq.ml.training._fallback.GradientBoostingFallbackClassifier` | `ml/training/factory.py: build_model()` | Train Gradient Boosting (pure NumPy — NO sklearn.cluster) |

`maintiq.ml.explainability` already satisfies Phase 3 structure: `shap_status()`/`lime_status()` probe via `importlib.import_module`; `explain_local()` tries backends and degrades gracefully.

---

## 3. Root cause of `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd`

**Confirmed: SHAP is the cause.** Importing the top-level `shap` package (v0.54.1) transitively loads `sklearn.cluster`, including `_k_means_common`, `_k_means_elkan`, `_k_means_lloyd`, `_k_means_minibatch`, `_kmeans` — which resolve to `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` (196,096 bytes, **NotSigned**).

- `import xgboost` does **not** load `sklearn.cluster`.
- MaintiQ does **not** import `shap` at application startup; it is lazy and only reached when a user opens the **Explain Prediction** page and selects the SHAP backend.
- Gradient Boosting uses the documented pure-NumPy fallback (`ml/training/_fallback.py`), so it never touches `sklearn.ensemble._gb` or `sklearn.cluster`.
- All four models remain preserved: Logistic Regression, Random Forest, Gradient Boosting (NumPy fallback), XGBoost. LIME preserved (lazy). SHAP remains available but optional.

`sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` — **NotSigned** (SHA-256 `81302CA06D8A9FDDF3018E9B1E97E5D2F1FA340FFD84F576EF479F23EA9DCDE8`). Vendor signature must be preserved; must not be patched or re-signed without approval.

---

## 4. PyInstaller packaging audit

| Item | Finding |
|---|---|
| Spec file | **ABSENT** — `packaging\maintiq.spec` does not exist (glob: none). `.gitignore` ignores `*.spec`. `scripts/build_windows.ps1` line 17 references `packaging\maintiq.spec` but it is not in the repo. |
| Build script | `scripts/build_windows.ps1` — builds one-file, installs `requirements-packaging.txt`, cleans `build/` and `release\MaintiQ-Portable/`, runs `PyInstaller $spec`, optionally compiles `packaging\maintiq-installer.iss` via `iscc`. |
| Prior build artifacts | `build\maintiq\` contains Analysis-00.toc, EXE-00.toc, PKG-00.toc, PYZ-00.pyz, MaintiQ.pkg, warn-maintiq.txt (leftover from a previous local build; `/build/` is gitignored). |
| warn-maintiq.txt | Standard PyInstaller missing-module noise (posix/pwd/grp/*nix modules; optional shap/matplotlib/pandas/scipy imports). `sklearn.cluster._spectral`, `sklearn.cluster._bicluster` appear because shap was in the prior analysis scope. No actionable missing module for MaintiQ's own code. |
| Packaging mode | **ONE-FILE** (current portable). |
| Current output path | `release\MaintiQ-Portable\MaintiQ.exe` — single executable, no sidecar folder. |
| Hooks / runtime hooks / exclusions | None present (no spec, no custom hook directory identified). `collect_*` not used. |

---

## 5. Native binary inventory

Path | Owning package | Version | SHA-256 | Authenticode | Required for core startup?
|---|---|---|---|---|---|
| `release\MaintiQ-Portable\MaintiQ.exe` | MaintiQ (PyInstaller one-file) | 0.1.0 | `927616252543DE31AB4D6DBE721EDAF8206B4F799D63201BC491990CD9846459` | **NotSigned** | YES (the app itself) |
| `python313.dll` | CPython | 3.13.14 | — | — | YES (bundled into one-file EXE at runtime) |
| `.venv\Lib\site-packages\PySide6\Qt6Core.dll` | PySide6 / Qt | 6.12.0 | `F57ED38AFD95D0306CCA9D88D997F639F70C7628A4F1F064EAE291D579487121` | **Valid** | YES |
| `.venv\Lib\site-packages\PySide6\Qt6Gui.dll` | PySide6 / Qt | 6.12.0 | `ABD20026E190E8CC69667D1BEA042DB05CD353CC05E7DA74B063C20B7DA3F6CD` | **Valid** | YES |
| `.venv\Lib\site-packages\PySide6\Qt6Widgets.dll` | PySide6 / Qt | 6.12.0 | `2F62CBE2869FFF4E20DF7369C2786E1EC7EC290D5A63D1371B7F70CF06909C3F` | **Valid** | YES |
| `.venv\Lib\site-packages\numpy\_core\_multiarray_umath.cp313-win_amd64.pyd` | numpy | 2.5.4 | `F37332834048E3AEF93A33FF53F558A319CAD12009DEFB2231EE1BA4AA6105D8` | NotSigned | YES |
| `.venv\Lib\site-packages\xgboost\lib\xgboost.dll` | xgboost | 2.1.4 | `7CBDC132C1E20E0055939F4214E8DE81EACAFF5415460639321700664C2C04FA` | NotSigned | YES (XGBoost model) |
| `.venv\Lib\site-packages\sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` | scikit-learn | 1.9.1 | `81302CA06D8A9FDDF3018E9B1E97E5D2F1FA340FFD84F576EF479F23EA9DCDE8` | **NotSigned** | NO — only when SHAP explainer is used (feature-only) |

Vendor signatures on Qt DLLs are **Valid** and must be preserved. sklearn / numpy / xgboost native extensions are NotSigned (normal for PyPI wheels) and must not be patched/re-signed without legal/technical approval. `_k_means_common.pyd` is **not required for core startup** — it is only loaded if SHAP is invoked.

---

## 6. One-file vs one-folder

Current packaging: **one-file** (`release\MaintiQ-Portable\MaintiQ.exe`, single EXE).  
PyInstaller recommends validating one-folder (`--onedir`) before one-file because dependency failures are easier to diagnose. No `.spec` exists, so the exact prior build configuration (hidden imports, binaries, datas, exclusions, runtime hooks) cannot be reconstructed from the repo — it must be defined fresh in Phase 4/5.

---

## 7. Optional dependencies excludable from standard release

| Dependency | Role | Safe to exclude from standard release? | Notes |
|---|---|---|---|
| `shap` | Explainability backend (SHAP) | **YES** | Already lazy-imported; causes `sklearn.cluster/_k_means_common.pyd` (NotSigned) load. Excluding removes the blocked-pyd path entirely while preserving LIME. |
| `lime` | Explainability backend (LIME) | No (keep available) | Lazy-imported; pure-Python over numpy/scipy, no blocked native extension. Preserve per requirements. |
| `matplotlib` | EDA charts + PNG report exports | No | Required by EDA page and reporting service (core workflows). |
| `scikit-learn` | Preprocessing, LR, RF | No | Required core; Gradient Boosting uses NumPy fallback but LR/RF need sklearn. |
| `xgboost` | XGBoost model | No | Required core model. |
| `PySide6`, `pandas`, `numpy`, `joblib` | GUI, data, numerics, serialization | No | Required core. |

**Proposed standard-release dependency profile:** runtime = pandas, numpy, scikit-learn, xgboost, lime (optional), matplotlib, PySide6, joblib. `shap` moved to optional/extras (already lazy in code); excluded from the standard PyInstaller bundle unless the owner explicitly opts in. This satisfies Phase 3: GUI startup and all four training/prediction paths work without SHAP.

---

## 8. Acceptance gate — Phase 1

**PASS — evidence-based.**

- Exact dependency versions recorded (Section 1).
- Import chain traced empirically at startup: shap/lime/xgboost/sklearn.cluster NOT loaded at startup; only PySide6/numpy/pandas/joblib/matplotlib/sklearn-base load eagerly (Section 2).
- `_k_means_common.cp313-win_amd64.pyd` root cause confirmed: imported transitively by `shap`, not by MaintiQ at startup, not by xgboost or the NumPy Gradient Boosting fallback (Section 3). NotSigned, not required for core startup.
- PyInstaller audited: no `packaging/maintiq.spec` present; current build is one-file at `release\MaintiQ-Portable\MaintiQ.exe`; prior `warn-maintiq.txt` contains no actionable MaintiQ missing-module (Section 4).
- Native-binary inventory with SHA-256 + Authenticode status completed (Section 5); Qt vendor signatures Valid and preserved; sklearn/numpy/xgboost NotSigned and must not be patched.
- Optional-dependency analysis identifies `shap` as safely excludable; `lime` preserved (Section 7).

No source edited, no rebuild performed, no signing attempted, no Windows security settings changed. Nothing committed or pushed.

---

## Recommended next step (Phase 2)

Proceed to Windows security diagnostics: record Smart App Control state, inspect CodeIntegrity event log (3076/3077) around the blocked launch, run `Get-AuthenticodeSignature` on the EXE and `_k_means_common.pyd`, and classify the blocking mechanism as CONFIRMED / LIKELY / UNCONFIRMED. Do not use `Unblock-File` or security-policy changes as a fix.
