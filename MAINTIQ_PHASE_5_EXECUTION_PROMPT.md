# MaintiQ — Phase 4 Registry Verification + Phase 5 Execution Prompt

## Mission

Continue the existing MaintiQ repository. Do **not** recreate the project or rewrite completed phases. First verify and finish the Phase 4 model registry work that was just attempted, then implement Phase 5: evaluation, model comparison, threshold analysis, evaluation visualisations, and report export.

Work sequentially, make changes in the repository, run tests and linting, update `IMPLEMENTATION_STATUS.md`, and stop after Phase 5 acceptance criteria pass. Do not begin Phase 6 (SHAP/LIME implementation) in this task.

---

## 1. Known project context — use as a starting point, not as proof

Project root:

`C:\ARRU CODES\projects\MaintiQ`

Environment observed in the latest session:

- Windows PowerShell 5.1
- Python 3.13.14
- Virtual environment: `.venv`
- Scikit-learn 1.9.1
- Python executable: `.venv\Scripts\python.exe`

Latest user-provided execution log reports:

- Phase 0: scaffold, config, exceptions, rotating logging, entry point, package metadata, README, changelog, implementation status, architecture documentation — reported complete.
- Phase 1: dataset schema/loader/validator/profiler/import workflow and data dictionary — reported complete.
- Phase 2: preprocessing component and tests — reported complete.
- Phase 3: feature engineering transformer and tests — reported complete.
- Phase 4: model factory, pipeline, trainer, and pure-NumPy Gradient Boosting fallback exist; training pipeline work has been in progress.
- Latest full test run: **97 passed**.
- Latest `ruff check src/ tests/`: **All checks passed**. The config also emits a warning that the removed Ruff rule `UP038` is still listed; clean up that stale setting only if safe and consistent with the project's Ruff version.
- `docs/PHASE_4_AUDIT.md` was reported as present.
- Optional-dependency/startup tests and an explainability module were reported as present.

Important environment constraints:

- Windows Security previously displayed a block for `sklearn/cluster/_k_means_common.cp313-win_amd64.pyd`.
- The user verified that this `.pyd` file exists in the active venv and `Get-AuthenticodeSignature` reports `NotSigned`. Its SHA-256 was recorded in the chat, but this does not independently prove the file's provenance or establish which Windows policy blocked it.
- Prior logs also reported blocked Scikit-learn compiled imports, SHAP, and `sklearn.impute.SimpleImputer` on this machine.
- A pure-NumPy fallback classifier exists at `maintiq.ml.training._fallback.GradientBoostingFallbackClassifier`.
- XGBoost training and prediction were previously reported as working.
- LIME was reported as importable.
- The AI4I 2020 dataset and Inno Setup availability were previously reported as not yet verified.

Treat these as observations from previous runs. Recheck the actual repository and environment before relying on any of them. Do not claim a dependency is working just because an earlier log says it worked.

---

## 2. Mandatory first action: inspect the actual repository

Before editing anything:

1. Set the working directory to the project root using a correctly quoted PowerShell path.
2. Inspect the current files and contents of:
   - `src/maintiq/ml/training/`
   - `src/maintiq/ml/evaluation/`
   - `src/maintiq/core/exceptions.py`
   - `src/maintiq/config.py` (or the actual config module)
   - `tests/unit/`
   - `pyproject.toml`
   - `IMPLEMENTATION_STATUS.md`
   - `docs/PHASE_4_AUDIT.md`
3. Read the current `registry.py`, if present, as source code. Do not assume the previous attempted write succeeded correctly. Check syntax, indentation, imports, symbols, type annotations, and runtime behaviour.
4. Confirm whether `RegistryError` and `ModelHashMismatchError` actually exist. If not, add appropriate domain exceptions without breaking existing exception inheritance or imports.
5. Confirm the actual `ModelTrainer.train_model()` signature and the current `TrainingResult` structure before integrating a registry. Do not guess argument names or change APIs blindly.
6. Confirm whether an evaluation service already exists and read its implementation before replacing it.
7. Run the baseline full test suite before modifications and record the exact count and failures. Do not call a test suite “passing” unless it was actually run.

Use PowerShell commands that work with the project path containing spaces. For example:

```powershell
Set-Location -LiteralPath "C:\ARRU CODES\projects\MaintiQ"
$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $python)) { throw "Project virtual-environment Python was not found: $python" }
& $python --version
```

---

## 3. Complete the Phase 4 model registry gate

A registry file was just attempted after several editor/write failures. Verify and repair it rather than blindly overwriting it.

### Registry requirements

Implement or complete a local JSON-based `ModelRegistry` under the existing training package, preferably at:

`src/maintiq/ml/training/registry.py`

Respect the project's established naming and style if an equivalent implementation already exists.

The registry must:

- Use a documented schema version.
- Create an empty registry safely when the JSON file does not exist.
- Reject malformed JSON with a clear domain-specific error.
- Reject unsupported schema versions and invalid record shapes.
- Register a trained artifact only after the artifact exists.
- Assign monotonically increasing per-model versions (`v1`, `v2`, ...), including after reload.
- Record model name/display name, stable record ID, relative artifact path, creation timestamp in timezone-aware ISO 8601, SHA-256 checksum, metrics, parameters, random seed/split details where available, selected threshold, feature names/order, library versions, and dataset provenance only when actually known.
- Represent missing optional metadata honestly as `null` / absent; never invent it.
- Write JSON atomically using a temporary sibling file and `os.replace`.
- Keep all artifact paths constrained to the configured model directory. Reject `..` traversal, absolute paths outside the directory, and symlink escapes.
- Resolve artifact paths safely.
- Verify artifact SHA-256 before loading an artifact.
- Provide methods to list models, list versions, get one version, get latest, test existence, count records, reload, and clear records where appropriate.
- Return defensive copies of mutable record data so callers cannot silently mutate registry internals.
- Handle JSON serialization of NumPy scalar values and common metadata safely, converting only supported values to JSON primitives. Reject unsupported values clearly rather than silently stringifying arbitrary model objects.
- Use a thread lock for same-process concurrent writes if the current design can be called concurrently. Do not claim cross-process locking unless it is actually implemented.
- Never load joblib/pickle artifacts from an untrusted source. Document that local model artifacts are trusted application data only.

### Trainer integration

- Inspect the existing trainer API before editing.
- Integrate registry registration after a model artifact has been saved successfully and metrics/metadata are available.
- If registry persistence fails, return/report a clear failure and avoid falsely claiming that the model is registered. Do not leave contradictory status in the UI or implementation log.
- Preserve the current training return contract where practical; update callers/tests coherently if a change is necessary.
- Do not introduce a second competing registry or duplicate model storage.

### Registry tests

Add or update tests covering:

- missing registry file creates empty state;
- registration and version increment;
- persistence across a new registry instance/reload;
- list/get/latest/existence/count;
- malformed JSON;
- unsupported schema;
- invalid records;
- missing artifact;
- path traversal and outside-directory absolute paths;
- artifact hash verification;
- hash mismatch after artifact modification;
- JSON-safe metric serialization;
- atomic-write failure does not corrupt the previous registry;
- trainer-to-registry integration.

Do not use broad `pytest.raises(Exception)` assertions. Assert the project's specific domain exception.

**Phase 4 gate:** do not move to Phase 5 implementation until registry tests pass, trainer integration works, full existing tests still pass, and Ruff passes.

---

## 4. Phase 5 — Evaluation service

Implement or strengthen the current evaluation service using the real trainer/pipeline interfaces discovered during inspection.

### Required metrics

For binary classification, calculate and expose:

- accuracy;
- precision;
- recall;
- F1-score;
- ROC-AUC;
- confusion matrix (`tn`, `fp`, `fn`, `tp`).

Useful additional metrics may include specificity, balanced accuracy, false-positive rate, false-negative rate, and average precision, provided definitions and undefined cases are handled correctly.

### Correctness requirements

- Validate target labels and prediction/probability shapes.
- Verify positive-class probability column mapping; do not assume the second column is positive without inspecting estimator classes or pipeline contract.
- Make threshold explicit and validate that it is within `[0, 1]`.
- Calculate predicted labels from probabilities using the supplied threshold when the pipeline API supports it. Do not accidentally ignore the requested threshold by calling a default-threshold `predict()` method.
- Handle single-class targets: ROC-AUC must be reported as `null`/undefined with an explanation, not as a fabricated value or an unhandled exception.
- Handle zero denominators according to a documented zero-division policy.
- Return JSON-safe primitive values. Do not serialize NaN or Infinity as invalid JSON numbers; use `null` plus a reason where appropriate.
- Preserve the distinction between metrics and raw arrays/predictions.
- Do not import K-Means or clustering components to calculate classification metrics.
- Keep optional dependencies lazy and isolated.

Add tests for normal binary data, all-positive/all-negative targets, zero precision/recall denominators, invalid thresholds, mismatched shapes, non-finite probabilities, and positive-class ordering.

---

## 5. Phase 5 — Prevent threshold-analysis data leakage

This is a mandatory correctness requirement.

- Inspect the current train/test split implementation and data flow.
- Threshold selection must use a validation set or training-only cross-validation predictions. It must **not** use the final held-out test set to choose a threshold.
- Keep the test set untouched until the final evaluation of the chosen model/threshold.
- If the existing workflow has only train/test splitting, implement a reproducible train/validation/test strategy or an equivalent training-only out-of-fold method. Preserve class balance where feasible and document small-dataset edge cases.
- Record random seed, split sizes/ratios, and the source of threshold selection in metadata.
- Make it explicit in the UI/report which data partition produced each metric.

### Threshold analysis outputs

For each candidate threshold, calculate at least:

- threshold;
- precision;
- recall;
- F1-score;
- false positives;
- false negatives;
- true positives;
- true negatives;
- specificity (if implemented).

Provide a configurable threshold grid, with a sensible default spanning `[0, 1]`. Include the configured default threshold (normally 0.50) even if it is not on the grid.

Support a documented recommendation objective such as maximizing validation F1. Make tie-breaking deterministic and documented. Do not present an optimized threshold as universally optimal or as a clinical/industrial safety threshold. The user remains responsible for human review.

Add tests proving that threshold analysis consumes validation scores and does not inspect the final test target when selecting a threshold.

---

## 6. Phase 5 — Model comparison

Implement a `ComparisonService` (or extend an existing equivalent) that:

- compares Logistic Regression, Random Forest, Gradient Boosting, and XGBoost when each is available;
- uses identical data partitions and metric definitions across candidates;
- records model display name, configuration, training outcome, artifact/version reference, and evaluation metrics;
- handles an unavailable model with an explicit status/reason rather than fabricating results;
- sorts or highlights models only according to an explicit selected metric;
- does not automatically promote a model solely because of accuracy, especially when class imbalance makes recall/precision important;
- includes a warning that benchmark results do not establish production industrial reliability.

Add tests for all-success, partial-failure, and no-model-success cases.

---

## 7. Phase 5 — Evaluation visualisations

Use the plotting library already adopted by the project. Avoid introducing a new charting stack without a clear reason.

Generate clear, labelled charts for:

- model metric comparison;
- confusion matrix;
- ROC curve (when both target classes are present);
- precision-recall curve;
- threshold-versus-metric analysis;
- false-positive/false-negative trade-off.

Requirements:

- Charts must use the actual calculated arrays/metrics; no placeholder or synthetic performance values.
- Every chart must have a title, axis labels, legend where useful, and appropriate units.
- Handle undefined ROC/PR cases gracefully.
- Save figures under the configured reports/figures directory, not hard-coded absolute paths.
- Close figure handles after saving to avoid memory leaks.
- Keep plotting code separate from evaluation calculations and UI code.

Add tests that validate chart creation with temporary output paths and confirm graceful handling of one-class input.

---

## 8. Phase 5 — Reporting and exports

Implement reporting around real evaluation outputs.

Required formats:

- JSON metrics/model comparison export;
- CSV threshold-analysis export;
- PNG evaluation charts.

HTML summary is optional if it can be generated cleanly using installed dependencies. Do not add PDF generation in this phase unless the project already has a supported report subsystem.

Reports must include, when known:

- MaintiQ application version;
- model family and registered version;
- dataset name/version/fingerprint;
- target definition;
- input feature names/order;
- random seed and split details;
- threshold and threshold-selection method;
- metrics and confusion matrix;
- creation timestamp;
- warnings/limitations.

Do not include made-up dataset provenance, unverified accuracy scores, or claims that predictions are certified industrial diagnoses.

Write exports atomically where practical. Sanitize filenames and prevent path traversal. Add tests for JSON/CSV correctness, missing optional metadata, and invalid output paths.

---

## 9. Dataset verification and provenance

The prior log said the AI4I 2020 dataset had not yet been obtained/verified. Recheck the actual data folder.

- If the official dataset is already present, validate its file format, expected columns, target column, row count, and a reproducible fingerprint. Record actual findings.
- If it is absent, do not invent rows, training metrics, or a successful benchmark run. Ensure the application has a clear import workflow and document the required dataset source and expected schema.
- Do not silently use randomly generated test fixtures as the real AI4I dataset.
- Keep UDI/Product ID and failure-mode indicators out of predictive input features as specified in the university synopsis; ensure the target definition is explicit.
- Add or update a dataset-verification test using a small synthetic fixture only for unit-testing the validator, clearly labelled as a test fixture.

---

## 10. Windows and dependency constraints

- Do not disable Smart App Control or Windows Security.
- Do not rename, patch, or delete blocked `.pyd` files.
- Do not claim an unsigned native extension is safe solely because its filename matches a package.
- Do not claim signing the installer will sign or automatically trust all bundled native dependencies.
- Avoid loading clustering modules unless a documented MaintiQ feature genuinely needs them.
- Keep optional SHAP/LIME imports lazy; failures must be reported honestly and must not prevent unrelated desktop startup or core prediction workflows.
- Preserve the pure-NumPy Gradient Boosting fallback if it remains correct and tested.
- Keep XGBoost functionality only if it imports/trains/predicts in the actual current environment; otherwise report it as unavailable with a clear reason.
- Inspect and document the project's Python version requirement. The active environment is Python 3.13.14, while an earlier prompt reportedly targeted Python 3.11. Align `pyproject.toml`, dependency constraints, README and test matrix with the version actually supported by the chosen dependencies. Do not change Python versions automatically or remove the user's venv without approval.

---

## 11. Quality gates and required commands

Run commands from the project root. Use the venv interpreter explicitly.

At minimum:

```powershell
& $python -m pytest tests/ -q
& $python -m ruff check src/ tests/
```

Also run the project's configured type checker if one exists. If type checking is not configured, document that rather than inventing a successful result.

Quality requirements:

- No regressions in the baseline tests.
- Add focused tests for every new service and failure mode.
- No broad exception assertions.
- No placeholder pass statements for required functionality.
- No fabricated benchmark metrics.
- No silently swallowed exceptions.
- No secrets or user-specific absolute paths committed.
- Tests use temporary directories for artifacts/reports.
- Ensure file writes are deterministic and portable on Windows.

Fix failures before marking a gate complete. If a dependency or Windows policy prevents a real integration test, mark it blocked and provide the exact error and affected functionality. Do not disguise a skipped test as a pass.

---

## 12. Documentation and status updates

Update:

- `IMPLEMENTATION_STATUS.md` — phase-by-phase status, exact test count, lint status, unresolved blockers;
- `CHANGELOG.md` — concise Phase 4 registry/Phase 5 changes;
- `README.md` — current evaluation, threshold and report capabilities;
- `docs/PHASE_4_AUDIT.md` — registry audit result and remaining issues;
- create `docs/PHASE_5_EVALUATION.md` documenting metric definitions, split strategy, threshold selection, leakage prevention, model comparison, chart/report outputs, limitations;
- update architecture documentation if the actual design changed.

Never mark a deliverable complete unless the implementation and verification exist.

---

## 13. Final execution order

Execute in this exact order:

1. Inspect current repository and baseline tests.
2. Audit and repair `registry.py` syntax/behaviour.
3. Add registry unit tests and integrate registry with `ModelTrainer`.
4. Run Phase 4 gate: full tests + Ruff + type check if configured.
5. Implement/repair `EvaluationService` and metric tests.
6. Implement leakage-safe validation/threshold-selection flow and tests.
7. Implement `ComparisonService` and tests.
8. Implement evaluation charts and tests.
9. Implement JSON/CSV/PNG report exports and tests.
10. Verify AI4I dataset presence/provenance or document that it remains absent.
11. Run the complete quality gate again.
12. Update documentation/status with actual outcomes.
13. Stop. Do not start Phase 6.

## 14. Final response required from KiloCode

At completion, report:

- exact files created/modified;
- whether registry syntax and integration were verified;
- registry test results;
- Phase 5 feature checklist;
- exact full pytest result (passed/failed/skipped);
- Ruff result and any warnings;
- type-check result or explicit “not configured”;
- whether the actual AI4I dataset was verified;
- which models actually trained and evaluated in this environment;
- any Windows Security/native dependency blockers;
- remaining work before Phase 6.

Do not claim completion if any required acceptance criterion is unmet. If blocked, stop at the blocker, document it accurately, and preserve all existing working code.
