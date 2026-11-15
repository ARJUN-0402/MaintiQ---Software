# Windows Compatibility — MaintiQ

This document records **confirmed** runtime blockers observed in this environment
separately from **theoretical** compatibility concerns. It does not recommend or
imply disabling Windows security features.

## Confirmed environment (observed)

- OS shell: Windows PowerShell 5.1
- Python: 3.13.14 (`.venv\Scripts\python.exe`)
- scikit-learn: 1.9.1
- XGBoost: 2.1.4
- SHAP: 0.54.1 (installed)
- LIME: 0.2.0.1 (installed)
- Project: MaintiQ (repository root)

## Confirmed blocked native dependencies (Windows Application Control / Smart App Control)

The following were observed to fail with `ImportError: DLL load failed while
importing ...: An Application Control policy has blocked this file` when
imported in this environment:

| Component | Trigger | Observed status | Impact on MaintiQ |
|---|---|---|---|
| `sklearn.cluster._k_means_minibatch` / cluster package init | `import sklearn.cluster` or `from sklearn.cluster import KMeans/MiniBatchKMeans` | **Blocked** (confirmed) | No impact: MaintiQ source does not use `sklearn.cluster`, `KMeans`, or `MiniBatchKMeans`. |
| `sklearn.cluster._isotonic` / `_linkage` (seen in chain) | `sklearn.cluster` and SHAP import chain | **Blocked** (confirmed) | No direct MaintiQ dependency; contributes to SHAP import failure. |
| SHAP (`import shap`) | SHAP initialisation imports `sklearn.cluster.KMeans` via `shap.utils._legacy` | **Blocked/unavailable** (confirmed) | Optional explainability unavailable; app must remain usable and report unavailability clearly. |
| `sklearn.ensemble._gradient_boosting` | Direct import of sklearn `GradientBoostingClassifier` from extension module | **Blocked** in earlier logs (`gb.log`) | Mitigated: factory uses pure-NumPy `GradientBoostingFallbackClassifier` (no sklearn GB extension). |

Notes:
- `sklearn.cluster._k_means_common.cp313-win_amd64.pyd` was reported as blocked in
  earlier environment notes/logs; in the current probe `import
  sklearn.cluster._k_means_common` succeeded, but `sklearn.cluster` package
  initialisation still failed due to other blocked extensions. Treat the
  **cluster package / KMeans import path** as the confirmed blocked chain for
  SHAP in this environment.
- Installed `.pyd` files in the virtual environment are not modified by MaintiQ.

## Confirmed working dependencies (this environment)

| Component | Status | Notes |
|---|---|---|
| `import maintiq` / `python -m maintiq` | **OK** | Startup does not eagerly import optional/blocked explainability modules. |
| `import sklearn` | **OK** | Base package imports; specific extension-backed submodules may be blocked. |
| `sklearn.impute.SimpleImputer` | **OK** (probe) | Preprocessing still uses defensive/pure-NumPy paths where required. |
| `sklearn.svm.SVC`, `sklearn.neighbors.KNeighborsClassifier` | **OK** (probe) | Not required by MaintiQ predictive models. |
| `sklearn.linear_model.LogisticRegression` | **OK** | Required model supported. |
| `sklearn.ensemble.RandomForestClassifier` | **OK** | Required model supported. |
| `maintiq.ml.training._fallback.GradientBoostingFallbackClassifier` | **OK** | Pure-Python/NumPy fallback; preserves Gradient Boosting candidate without blocked sklearn GB extension. |
| `xgboost.XGBClassifier` | **OK** | Required model supported. |
| `import lime` | **OK** | Optional dependency importable; explainer wiring may be environment/data dependent. |

## Exact import chain for the blocked SHAP component (confirmed)

Observed chain when attempting `import shap`:

1. `shap/__init__.py` imports explainers
2. `shap/explainers/__init__.py` imports kernel explainer
3. `shap/explainers/_kernel.py` imports `shap.utils._legacy`
4. `shap/utils/_legacy.py` does `from sklearn.cluster import KMeans`
5. `sklearn.cluster` package initialisation loads extension modules (e.g.
   `_k_means_minibatch`, `_isotonic`, `_linkage` in observed failures)
6. Windows Application Control blocks one or more of those `.pyd` files →
   `ImportError: DLL load failed ... An Application Control policy has blocked this file`

MaintiQ avoids this at startup by **not importing SHAP at module import time**
and by exposing lazy `shap_status()` / `require_shap()` helpers that surface a
clear `ExplanationError` instead of crashing.

## Clustering dependency necessity

`sklearn.cluster`, `KMeans`, and `MiniBatchKMeans` are **not used** by MaintiQ
source code (`src/`). They are not required for dataset ingestion,
preprocessing, feature engineering, model training/inference for the four
required candidates, evaluation, or the CLI/desktop startup path. No startup
import in MaintiQ loads them.

## Theoretical / environment-dependent concerns (not observed as MaintiQ failures)

- Other sklearn compiled extensions not exercised by MaintiQ may be blocked on
  locked-down systems; behaviour depends on which submodules are imported.
- SHAP may work in environments where `sklearn.cluster` and its extensions are
  allowed; MaintiQ treats it as optional and detects availability at use time.
- LIME depends on additional packages (e.g. scikit-image/scipy) whose native
  components could be blocked on some systems; in this environment `import lime`
  succeeded but end-to-end explainer execution depends on runtime data and wiring.
- Signing an installer does **not** by itself resolve unsigned/blocked
  third-party dependency `.pyd` files under Windows Application Control policies.

## Required models and fallbacks (preserved)

- Logistic Regression — sklearn estimator (lazy import in factory).
- Random Forest — sklearn estimator (lazy import in factory).
- Gradient Boosting — **pure-NumPy fallback** `GradientBoostingFallbackClassifier`
  in `src/maintiq/ml/training/_fallback.py` (preserved).
- XGBoost — `xgboost.XGBClassifier`.

No fake model predictions or explanations are produced when optional
dependencies are unavailable.
