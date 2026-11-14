# Phase 4 Audit — MaintiQ

Audit performed on 2026-11-14 before Phase 5 work began. Every item below was
re-verified by running the project's own tools; claims from the previous
execution log are marked as verified or not reproducible.

## Verified facts

- Repository root: C:\ARRU CODES\projects\MaintiQ. Not a git repository.
- Active interpreter: .venv\Scripts\python.exe, Python 3.13.14. Existing venv reused.
- Baseline test run: pytest tests/ -q -> 97 passed in 6.37s (reproducible).
- Ruff check src/ tests/ -> All checks passed (after removing stale UP038 rule).
- Ruff format --check -> clean.
- Installed packages: sklearn 1.9.1, numpy 2.5.4, pandas 2.3.3, xgboost 2.1.4, joblib 1.6.0, matplotlib 3.11.2, lime importable. shap import fails.
- No type checker configured in pyproject.toml. Not applicable.
- maintiq imports cleanly; importlib.metadata.version("maintiq") == 0.1.0.

## Environment constraints re-verified

| Claim from previous log | Result |
|---|---|
| Smart App Control blocks SimpleImputer and GradientBoostingClassifier | Not reproducible. Both import and run. |
| Pure-NumPy Gradient Boosting fallback exists | Verified in _fallback.py. |
| SHAP blocked | Verified. import shap raises ImportError on _k_means_common DLL. |
| LIME importable | Verified. |
| XGBoost trains/predicts | Verified. |

## Phase 4 Model Registry — Implementation complete

### Implemented

- `src/maintiq/ml/training/registry.py` — `ModelRegistry`:
  - Documented schema version ("1.0").
  - Creates empty registry safely when JSON file does not exist.
  - Rejects malformed JSON with `RegistryError`.
  - Rejects unsupported schema versions and invalid record shapes.
  - Registers a trained artifact only after the artifact exists on disk.
  - Assigns monotonically increasing per-model versions (v1, v2, ...), including after reload.
  - Records model name/display name, stable record ID, relative artifact path, creation timestamp in timezone-aware ISO 8601, SHA-256 checksum, metrics, parameters, split settings, dataset fingerprint, feature columns, target column, library versions, threshold, random seed.
  - Missing optional metadata represented as `null`/absent; never invented.
  - Writes JSON atomically using a temporary sibling file and `os.replace`.
  - All artifact paths constrained to configured model directory; rejects `..` traversal, absolute paths outside directory, and symlink escapes.
  - Resolves artifact paths safely via `_resolve_under_root`.
  - Verifies artifact SHA-256 before loading (`load_artifact` raises `ModelHashMismatchError` on mismatch).
  - Methods: `list_models`, `list_versions`, `get_version`, `get_latest`, `model_exists`, `version_exists`, `count_models`, `count_records`, `reload`, `clear`.
  - Returns defensive copies of mutable record data (via JSON round-trip).
  - Handles JSON serialization of NumPy scalar values; rejects unsupported values clearly.
  - Uses `threading.Lock` for same-process concurrent writes.
  - Documents that local model artifacts are trusted application data only.
- `RegistryError` and `ModelHashMismatchError` exist in `src/maintiq/core/exceptions.py`.
- `ModelTrainer.train_model()` integrates registry via `self.registry.register(...)` with all required kwargs.
- Registry exposed from `maintiq.ml.training` and `maintiq.registry`.

### Tests

`tests/unit/test_registry.py` — 21 tests covering:
- missing registry file creates empty state;
- registration and version increment;
- persistence across new registry instance/reload;
- list/get/latest/existence/count;
- malformed JSON;
- unsupported schema;
- invalid records;
- missing artifact;
- path traversal and outside-directory absolute paths;
- artifact hash verification;
- hash mismatch after artifact modification;
- JSON-safe metric serialization;
- atomic-write failure does not corrupt previous registry;
- trainer-to-registry integration.

All tests use specific domain exceptions (`RegistryError`, `ModelHashMismatchError`), not broad `Exception`.

### Remaining issues

- Cross-process locking is not implemented (only same-process threading lock). Documented as a limitation.
- AI4I 2020 dataset not obtained; registry stores dataset fingerprint only when known.
