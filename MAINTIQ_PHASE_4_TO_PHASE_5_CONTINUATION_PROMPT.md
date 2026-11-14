# MaintiQ — Phase 4 Completion Audit + Phase 5 Continuation Prompt

## Instructions for KiloCode

You are continuing an existing MaintiQ codebase. Do not start over, regenerate the project scaffold, or replace working modules. Work in the existing repository:

`C:\ARRU CODES\projects\MaintiQ`

The active environment in the latest execution log is Python `3.13.14` in `.venv`. Do not silently recreate or downgrade the environment to Python 3.11. First inspect `pyproject.toml`, requirements, the active interpreter, and the actual package compatibility. Make only evidence-based environment changes and document them.

Your task is to audit the current Phase 4 implementation, finish the remaining model-registry integration, and then implement Phase 5: model evaluation, model comparison, threshold analysis, and evaluation reports.

The current project is an academic BCA predictive-maintenance prototype aligned with the approved MaintiQ synopsis. Its defined candidate models are Logistic Regression, Random Forest, Gradient Boosting, and XGBoost. Its expected classification measures include accuracy, precision, recall, F1-score, ROC-AUC, and confusion-matrix information. Do not expand the scope into live factory telemetry, PLC/SCADA control, or certified industrial diagnosis.

---

# 1. Known repository state — verify before editing

The latest execution log reports:

- Phase 0 complete: package scaffold, configuration, exceptions, rotating logging, entry point, project metadata, README, changelog, implementation status, and architecture documentation.
- Phase 1 complete: dataset schema, loader, validator, profiler, import workflow, and data dictionary.
- Phase 2 complete: preprocessing pipeline, artifact serialization, split settings, and tests.
- Phase 3 complete: feature engineering transformer and documentation.
- Phase 4 core implementation added: model factory, pure-NumPy Gradient Boosting fallback, model pipeline, model trainer, evaluation service, package exports, and associated unit tests.
- Latest full test run: **89 passed**.
- Ruff passed on the newly created/modified files.
- Package import smoke test succeeded and reported MaintiQ version `0.1.0`.
- A whole-`src/` Ruff check still reports five `PLC0415` findings in `src/maintiq/ml/training/factory.py`. They are intentional lazy imports used to preserve graceful degradation when optional/compiled ML dependencies cannot load. Do not move those imports to module scope just to satisfy lint; doing so could break startup in the affected Windows environment.
- The application environment reports that Windows Smart App Control blocks some scikit-learn compiled `.pyd` modules. The SimpleImputer import chain and SHAP are blocked; `GradientBoostingClassifier` is blocked. A pure-NumPy fallback classifier exists. XGBoost train/predict and LIME imports were reported working.
- The AI4I 2020 dataset has not yet been obtained and verified in the current project environment.
- Inno Setup availability has not yet been verified.

Treat all of the above as claims from the previous execution log, not as guaranteed current state. Re-run checks and inspect the working tree before deciding what is actually complete.

## Important known files

- `src/maintiq/ml/preprocessing/preprocessor.py`
- `src/maintiq/ml/features/transformer.py`
- `src/maintiq/ml/training/factory.py`
- `src/maintiq/ml/training/_fallback.py`
- `src/maintiq/ml/training/pipeline.py`
- `src/maintiq/ml/training/trainer.py`
- `src/maintiq/ml/evaluation/service.py`
- `tests/unit/`
- `IMPLEMENTATION_STATUS.md`

Do not assume these paths or APIs are unchanged. Read them before editing.

---

# 2. Mandatory first action: audit current state

Before writing code:

1. Confirm the repository root and inspect `git status --short`.
2. Read `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `IMPLEMENTATION_STATUS.md`, and the existing architecture documentation.
3. Inspect the current implementations and public APIs of:
   - `ModelTrainer`
   - `TrainingResult`
   - `ModelPipeline`
   - `build_model` and `model_display_name`
   - `EvaluationService`
   - `ClassificationMetrics`
   - `Preprocessor`
   - `FeatureEngineeringTransformer`
4. Inspect all related tests, especially `test_trainer.py`, `test_pipeline.py`, and `test_evaluation.py`.
5. Run the current full test suite and record the actual baseline result.
6. Run Ruff on `src/` and `tests/`, and run any configured type checker. Record existing failures before changing anything.
7. Check whether a concrete model registry already exists anywhere in the repository. Search before creating a duplicate implementation.
8. Confirm whether the 89-test result is still reproducible.

Create or update a concise audit note in `docs/PHASE_4_AUDIT.md`. It must distinguish verified facts, existing limitations, and pending tasks.

Do not reset or discard user changes. Do not overwrite files wholesale when a targeted patch is safer.

---

# 3. Finish Phase 4: implement a concrete model registry

The latest log says `ModelTrainer` has an optional integration point that calls `registry.register(...)`, but no concrete registry implementation exists. Confirm this. If still missing, implement a local, file-based JSON registry consistent with the existing architecture. Do not introduce a database.

Suggested module location:

`src/maintiq/ml/training/registry.py`

Adjust the location only if the existing package structure provides a better established location.

## Registry responsibilities

Implement a small, testable `ModelRegistry` that can:

- Register a trained model and its metadata.
- List registered model versions.
- Retrieve one model record by its stable identifier/version.
- Retrieve the latest version for a model family/name.
- Resolve the artifact path safely.
- Validate registry structure and required metadata when loading.
- Handle missing registry files as an empty registry where appropriate.
- Handle malformed JSON and unsupported schema versions with clear domain-specific errors.
- Avoid losing records when two writes occur in quick succession within the same process.
- Write changes atomically: write a temporary file, flush/close it, then replace the registry file.
- Use relative artifact paths where possible and prevent paths from escaping the configured model directory.

## Registry record fields

Persist only values that are useful and actually available. At minimum, support:

- registry schema version
- stable model record ID/version
- model key and display name
- artifact path relative to the model directory
- artifact SHA-256 checksum, when the artifact exists
- creation timestamp in timezone-aware ISO 8601 format
- model/library version metadata when available
- training configuration and random seed
- training/validation/test split information when available
- selected decision threshold
- evaluation metrics, serialized as JSON-compatible primitives
- feature names/order or feature-schema reference
- optional dataset provenance/version information
- active/default status only if the application has a clearly defined selection workflow

Do not invent metric values or dataset provenance. Missing optional metadata must be represented honestly.

## Integrate with ModelTrainer

- Make the existing trainer and registry API agree exactly.
- Register a model only after training, evaluation, and artifact persistence have succeeded.
- If registry writing fails, raise a clear error or return a clearly represented partial-failure result; do not silently claim registration succeeded.
- Ensure a cancelled training run does not create a model artifact or registry entry.
- Preserve the current `TrainingResult` behavior and its default values for early cancellation.
- Keep the trainer testable by allowing temporary model and registry directories to be injected or overridden without writing into the real user profile during tests.

## Registry tests

Add focused unit tests for:

- new/empty registry
- registering the first model
- registering multiple versions
- listing and retrieving records
- latest-version lookup
- missing model lookup
- malformed JSON
- unsupported registry schema version
- invalid or path-traversal artifact references
- artifact checksum verification
- atomic-write behavior as far as practical to test
- trainer-to-registry integration
- cancelled training does not register a model

Do not weaken tests just to obtain a passing result.

---

# 4. Phase 5: evaluation and model comparison

The evaluation service already exists. Extend it only after reviewing its current behavior and tests. Reuse it instead of creating a competing metrics implementation.

## 4.1 Classification metrics

Support and test:

- accuracy
- precision
- recall
- F1-score
- ROC-AUC
- confusion matrix values: TN, FP, FN, TP
- total sample count and positive/negative support where useful

Requirements:

- Handle zero-division cases explicitly and consistently.
- Handle single-class test targets without crashing; ROC-AUC should be `None`/null with an explanatory status, not a fabricated number.
- Ensure probabilities are finite and within `[0, 1]` before metric calculation.
- Ensure labels are valid binary values and array lengths match.
- Ensure metric serialization is JSON-safe and stable.
- Preserve the existing `ClassificationMetrics` public API unless a migration is necessary; update all callers and tests if it changes.

Do not report accuracy alone. Failure data can be imbalanced, so precision, recall, F1, and false-negative/false-positive counts must remain visible.

## 4.2 Model comparison

Implement a comparison service that consumes evaluation records from multiple trained candidate models and produces a consistent comparison table/data object.

The comparison must:

- use the same evaluation dataset/split for every candidate in a comparison run;
- record each model's name/version and threshold;
- present the defined metrics with consistent rounding only at presentation/export time;
- represent unavailable metrics honestly;
- avoid silently ranking models by accuracy alone;
- not declare one model universally best without a stated selection criterion.

If a recommended model is shown, make the selection criterion explicit. For example, a recall-focused criterion can be chosen only when the project configuration or evaluator explicitly requests it.

## 4.3 Threshold analysis

Implement threshold analysis as a separate, testable component.

It should:

- accept true labels and predicted probabilities/scores;
- evaluate a configurable series of thresholds in `[0, 1]`;
- calculate confusion-matrix counts and precision, recall, F1, and accuracy at each threshold;
- make false positives and false negatives easy to compare;
- support a configurable default threshold, initially `0.50` unless existing project configuration says otherwise;
- return structured data suitable for a table and chart;
- validate invalid thresholds and malformed inputs.

**Avoid test-set leakage:** threshold selection/optimization must use validation data (or an explicitly documented cross-validation strategy), not the final held-out test set. The final test set is used only for the final unbiased evaluation after the threshold has been selected.

Do not label a threshold as optimal unless the optimization objective is specified and the selected threshold was derived from validation data. Keep threshold analysis descriptive by default.

## 4.4 Evaluation plots

Generate data and plots for:

- confusion matrix
- ROC curve when both classes are present and scores are valid
- precision-recall curve when valid
- model metric comparison
- threshold versus precision/recall/F1
- threshold versus false-positive/false-negative counts

Use the plotting libraries already present in the project. Do not add a second visualization stack without a clear reason. Plot generation should be independent from core metric calculations so the evaluation layer remains testable when a GUI or plotting backend is unavailable.

## 4.5 Evaluation reports and exports

Create a reporting component or extend the existing reporting layer to generate, as supported by the current architecture:

- `metrics.json`
- `model_comparison.csv`
- `threshold_analysis.csv`
- confusion-matrix image
- ROC and precision-recall images when calculable
- threshold analysis image
- a concise HTML evaluation report, if feasible with existing dependencies

Reports must include:

- project/application version
- model name/version
- evaluation timestamp
- dataset identity/provenance only when known
- split details and random seed only when recorded
- threshold used
- metric definitions/values
- limitations or unavailable metrics

Never put fabricated dataset names, sample counts, metrics, or dates into a report. Use explicit `unknown`/`not recorded` values when necessary.

Write reports only under the configured reports directory. Make output paths configurable and ensure tests use `tmp_path`.

---

# 5. Dataset verification gate

The latest log states that the official AI4I 2020 dataset has not yet been obtained and verified. This is a project-level blocker for real training claims.

1. Inspect the existing dataset import workflow and expected schema.
2. Check whether a real AI4I dataset file already exists in the repository or documented local data directory.
3. If it does not exist, do not create a fake file and do not report synthetic results as AI4I benchmark performance.
4. Add or refine a guided import instruction that identifies the official dataset source and the expected file/schema, while preserving the project's existing data-import design.
5. Use synthetic data only for automated unit/integration tests, clearly labelled as test fixtures.
6. Add a dataset verification report/check that records whether the supplied file matches the required schema and includes basic row/column and target checks.
7. Document that benchmark evaluation remains pending until a verified AI4I dataset is supplied.

Do not make network access mandatory for normal offline application operation.

---

# 6. Windows and dependency constraints

The previous log reports Windows Smart App Control blocking certain compiled scikit-learn extensions. Treat this as an environment constraint, not as a reason to falsify results or silently change the ML algorithms.

- Preserve graceful optional-dependency handling.
- Do not move intentionally lazy optional imports to top-level just to satisfy Ruff.
- If appropriate, add narrow `# noqa: PLC0415` comments with clear rationale to the five intentional lazy imports in `factory.py`, or configure a narrowly scoped Ruff per-file ignore. Do not globally disable the rule.
- Keep the pure-NumPy Gradient Boosting fallback explicitly identified as a fallback implementation, not as scikit-learn's GradientBoostingClassifier.
- Do not claim SHAP is working while its import is blocked. SHAP work belongs to the explainability phase and should have a graceful unavailable state until the environment is resolved.
- Keep LIME optional and handle missing dependencies gracefully.
- Do not silently change Python versions or pin incompatible packages. Verify support using installed package metadata and the project's declared Python range.

---

# 7. Quality gates — mandatory before marking work complete

Run the actual project commands after implementation. At minimum:

1. Full tests: `python -m pytest tests/ -q`
2. Ruff source and tests: `python -m ruff check src/ tests/`
3. Ruff formatting check if configured: `python -m ruff format --check src/ tests/`
4. Configured type checker, if present in `pyproject.toml` or project scripts.
5. Package import smoke test for the public APIs.
6. A small end-to-end training/evaluation test using clearly labelled synthetic fixture data.
7. Registry persistence/reload test.
8. Report export test using a temporary output directory.

Use the project's actual venv interpreter. In PowerShell, quote paths that contain spaces and invoke the interpreter with the call operator (`&`). Do not paste Unix-only shell syntax into PowerShell.

Do not stop at the first test failure. Diagnose and fix implementation defects. Do not change expected behavior merely to make tests green.

If an optional dependency is unavailable, test both the available and unavailable code paths where practical and document the limitation.

---

# 8. Documentation and status updates

Update:

- `IMPLEMENTATION_STATUS.md`
- relevant module documentation
- `docs/PHASE_4_AUDIT.md`
- `README.md` only where user-facing capabilities/status need to change

Document clearly:

- what was implemented
- what was tested
- exact test count and command output summary
- Ruff/type-check results
- dataset verification status
- unavailable optional dependencies
- known Windows Smart App Control limitations
- remaining work for Phase 6 (explainability), Phase 7 (prediction), desktop UI, packaging, and installer

Do not mark a phase complete unless its acceptance criteria and tests pass.

---

# 9. Git discipline

Do not commit automatically unless the user has explicitly enabled automatic commits in the current environment. Prepare a suggested commit message after a successful checkpoint.

Suggested checkpoint messages:

- `feat: add persistent model registry`
- `feat: implement evaluation and threshold analysis`
- `feat: add model comparison and evaluation reports`

Do not include generated models, local datasets, user-specific files, virtual environments, or secrets in Git.

---

# 10. Definition of done

This continuation is complete only when:

- the concrete registry is implemented and integrated with the trainer;
- registry persistence and error cases are tested;
- evaluation metrics and model comparison are stable and tested;
- threshold analysis is implemented without test-set leakage;
- report artefacts can be generated in a temporary test directory;
- all existing and new tests pass;
- Ruff is clean across the intended source and test scope, or any remaining exception is explicitly documented and narrowly scoped;
- package imports succeed;
- implementation status and limitations are documented;
- AI4I dataset status is truthfully reported as verified or pending.

At the end, provide a concise completion report with:

1. files created/modified;
2. registry behavior implemented;
3. evaluation/reporting capabilities implemented;
4. exact tests passed/failed;
5. lint/format/type-check status;
6. dataset verification status;
7. outstanding blockers;
8. suggested next phase.

**Start now with the audit in Section 2. Finish the missing Phase 4 registry integration, then proceed to Phase 5. Do not rebuild Phases 0–3.**
