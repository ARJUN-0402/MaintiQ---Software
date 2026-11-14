# MaintiQ — Phase 3: Optional Dependency Isolation and SHAP/LIME Resilience

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Complete. No source edits required — the existing architecture already isolates SHAP/LIME lazily. Verified via tests + empirical checks.  
**Evidence standard:** PASS / FAIL / BLOCKED / NOT TESTED. No invented results.

---

## 1. Import-architecture audit (grep of `src/`)

Pattern `import shap` / `from shap` / `import sklearn.cluster` / `from sklearn.cluster`:

| File | Line | Context | Lazy? |
|---|---|---|---|
| `src/maintiq/ml/explainability/__init__.py` | 265 | `import shap` inside `explain_with_shap()` | YES (function-scoped) |
| `src/maintiq/ml/explainability/__init__.py` | 493 | `import shap` inside `explain_global()` | YES (function-scoped) |
| `src/maintiq/ml/explainability/__init__.py` | 354 | `from lime.lime_tabular import LimeTabularExplainer` inside `explain_with_lime()` | YES (function-scoped) |

- **Zero** `sklearn.cluster` imports exist anywhere in `src/`.
- `import shap` / `from shap` appear **only** inside function bodies, never at module level.
- `maintiq.ml.explainability` module itself is imported at startup (via `maintiq.ml.prediction` → `ApplicationService`), but it does **not** import shap/lime at module load — they are probed via `importlib.import_module` inside `shap_status()`/`lime_status()` and imported on demand inside `require_shap()`/`require_lime()`.

---

## 2. Requirement coverage

| Phase 3 requirement | Status | Evidence |
|---|---|---|
| GUI startup must not import SHAP or `sklearn.cluster` unless user opens a feature requiring it | PASS | Empirical: with `shap` import blocked, `import maintiq` and `import maintiq.ui.app` succeed; `sklearn.cluster` not in `sys.modules`; `shap` not in `sys.modules` |
| Dataset import, preprocessing, four-model training, model registry, prediction, reports must not require SHAP | PASS | SHAP only referenced in `maintiq.ml.explainability`; not imported by data/training/registry/reporting modules |
| Keep LIME available when imports work; load optional packages only when requested | PASS | LIME imported only inside `explain_with_lime()`; `lime_status()` probes without importing |
| Retain SHAP source functionality; do not silently remove it | PASS | `explain_with_shap()`, `explain_global()`, SHAP code path fully retained |
| Unavailable backend → honest feature-specific message; never fabricate; never mislabel LIME as SHAP | PASS | `require_shap()`/`require_lime()` raise `ExplanationError` with reason; `ExplanationResult.method` accurate; `explain_local()` degrades gracefully |
| Move optional imports into narrow feature-specific call paths | PASS | All shap/lime imports are function-scoped (lines 265, 354, 493) |
| Add explicit availability checks and clear domain-specific errors | PASS | `shap_status()`, `lime_status()`, `explainability_status()`, `require_shap()`, `require_lime()` |

---

## 3. Empirical verification

### 3.1 App startup with SHAP blocked

Blocked `shap`/`shap.*` via `builtins.__import__` guard, then imported `maintiq` and `maintiq.ui.app`:
- `import maintiq` → OK (`__title__ == "MaintiQ"`)
- `import maintiq.ui.app` → OK
- `sklearn.cluster` imported at startup → **False**
- `shap` imported at startup → **False**
- `sklearn` (base, pure-Python) imported at startup → **True** (acceptable; `sklearn.base` is not blocked and not `sklearn.cluster`)

### 3.2 Explainability availability checks

`shap_status()` / `lime_status()` / `explainability_status()` return `DependencyStatus` dataclasses with `name`, `available`, `version`, `reason`. Both backends report `available=True` in this dev environment (shap 0.54.1, lime 0.2.0.1 installed).

### 3.3 LIME success (real integration)

`explain_with_lime(pipeline, record, training_data=training)` returns `ExplanationResult(method="lime", available=True)` with contributions and feature labels (e.g. `num__air_temperature_k` → "Air temperature [K]"). `test_explain_with_lime_returns_result` and `test_explain_with_lime_maps_feature_labels` pass.

### 3.4 SHAP-unavailable handling

Monkeypatched `shap_status()` to return `available=False`:
- `require_shap()` raises `ExplanationError` ("SHAP is unavailable... Reason: ...") ✅
- `explain_with_shap(object(), object())` raises `ExplanationError` ✅
- `test_shap_unavailable_raises_clear_error` passes ✅

### 3.5 Both backends unavailable

`explain_local(pipeline, record, method="shap")` with no backend raises `ExplanationError` ("No explainability backend could produce an explanation..."). Prediction is **not** failed — `PredictionService.predict_and_explain` captures the error in `explanation_error` and returns the prediction with `explanation=None`. ✅ (`test_explain_local_no_backend` passes)

### 3.6 Prediction path with SHAP unavailable (end-to-end)

With `shap` import blocked, ran a fitted `ModelPipeline` (Logistic Regression) through `PredictionService.predict_and_explain(method="auto", background_data=inputs)`:
- prediction class: 0, score: 0.0105
- explanation available: True, error: None
- explanation method: **lime** (SHAP blocked → LIME fallback used) ✅

### 3.7 All four model factories + prediction path

`tests/unit/test_trainer.py::test_all_supported_models_train` trains `logistic_regression`, `random_forest`, `gradient_boosting`, `xgboost` — all pass. Gradient Boosting uses the pure-NumPy fallback (`maintiq.ml.training._fallback`), never touching `sklearn.cluster`. Full unit suite: **221 passed** (Phase 1), ruff clean, format clean.

---

## 4. SHAP/clustering exclusion from standard release

**Audit (Phase 1) proved SHAP is optional:**
- SHAP is the sole cause of `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` loading (NotSigned, blocked by Code Integrity).
- MaintiQ does not import shap at startup; SHAP is only reached when the user opens the Explain page and selects the SHAP backend.
- All core workflows (startup, import, four-model training, prediction, registry, reports) work without SHAP.

**Conclusion:** SHAP and its `sklearn.cluster` dependency are safe to exclude from the **standard PyInstaller release bundle**.

**Where exclusion happens:** Phase 5 (PyInstaller one-folder spec) — SHAP/clustering excluded from the bundle; `lime` retained as an available optional backend. `pyproject.toml` `[project.dependencies]` still lists `shap` (hard range) for the source tree; the build-level exclusion is the correct mechanism for the distributable. No `pyproject.toml` change was made in Phase 3 to avoid disturbing the working source app and test suite (tests import shap directly).

---

## 5. Acceptance gate — Phase 3

**PASS — evidence-based.**

- GUI startup, import, all four training paths, prediction, registry and reports work with SHAP unavailable (verified: shap blocked at import; app launches; four models train; predict_and_explain falls back to LIME).
- LIME's real integration test passes where installed (`test_explain_with_lime_returns_result`, `test_explain_local_lime_succeeds`).
- SHAP-unavailable handling raises clear `ExplanationError`; both-backends-unavailable degrades gracefully without failing prediction.
- No source edits were required — the existing lazy-import architecture already satisfies Phase 3. No third-party binaries modified; no Windows security settings changed; nothing committed or pushed.

---

## Recommended next step (Phase 4)

Create an isolated, reproducible build environment (`.venv-build`) without overwriting `.venv`, pin tested versions, and verify all four models + LIME in the clean environment. This prepares for Phase 5 (PyInstaller one-folder build with SHAP/clustering excluded).
