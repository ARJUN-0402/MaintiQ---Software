# MaintiQ — Windows Compatibility and Release Validation

**Project:** MaintiQ (repository root)
**Source launch:** `python -m maintiq`
**Status:** Compatibility matrix documented. Clean-machine validation NOT TESTED (no separate VM/PC available). Release acceptance not complete.
**Evidence standard:** PASS / FAIL / BLOCKED / NOT TESTED / DOCUMENTED. No invented results.

---

## 1. Test environment

| Field | Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language |
| OS build | 10.0.26300 (Build 26300) |
| Architecture | 64-bit (AMD64) |
| Smart App Control | Actively enforcing (Code Integrity event 3077 confirmed) |
| Code Integrity policy ID | `{0283ac0f-fff1-49ae-ada1-8a933130cad6}` |
| Test machine | Development machine (same as build machine) — NOT a clean Windows machine |
| Python available | YES (3.13.14, `.venv` and `.venv-build`) |
| PyInstaller available | YES (6.22.3, `.venv-build`) |
| Inno Setup / ISCC.exe | NOT INSTALLED |

**Important:** Windows compatibility validation requirements state that clean-machine tests must be run on "a clean Windows 10/11 VM or second PC without Python or the project's venv" and "Smart App Control in its normal enabled state." This machine is the development machine with Python installed, so clean-machine validation cannot be executed here. All clean-machine tests are marked NOT TESTED.

---

## 2. Artifact inventory and hashes

| Artifact | Path | Size | SHA-256 | Authenticode | Signed? |
|---|---|---|---|---|---|
| onedir EXE | `release/staging/onedir/MaintiQ/MaintiQ.exe` | 22,843,697 | `369BFB2376EDBE4A3E576E2C6E6AFC734B0C50C85E919917A56736DE292B5DB7` | NotSigned | NO |
| onefile EXE | `release/staging/onefile/MaintiQ.exe` | 130,753,015 | `0F2ECC08FE71271728CFA7E67E204BF5FAB1F40F2104BE4D93B69CA10EF42013` | NotSigned | NO |
| legacy portable EXE | `release/MaintiQ-Portable\MaintiQ.exe` | 130,956,988 | `927616252543DE31AB4D6DBE721EDAF8206B4F799D63201BC491990CD9846459` | NotSigned | NO |
| onedir bundle files | `release/staging/onedir/MaintiQ/` | 2,169 files | manifest: `release/staging/onedir_manifest.csv` | — | — |
| onefile manifest | `release/staging/onefile_manifest.csv` | 1 file | — | — | — |

All three EXEs are **NotSigned** — this is the root cause of the Smart App Control block.

---

## 3. Compatibility test matrix

### A. Platform compatibility

| Test | Environment | Result | Evidence |
|---|---|---|---|
| Windows 11, Smart App Control On | This machine (Build 26300) | BLOCKED | EXE launch blocked: `WinError 4551` — Code Integrity event 3077 generated |
| Windows 11, Evaluation state | — | NOT TESTED | No separate Evaluation-state machine available |
| Clean Windows 10/11 without Python | — | NOT TESTED | No clean VM/PC available |
| Standard user account | — | NOT TESTED | Tested as admin on dev machine only |
| Offline operation after installation | — | NOT TESTED | No installer compiled (installer not available) |

### B. Signature and certificate-chain verification

| Test | Artifact | Result | Evidence |
|---|---|---|---|
| Authenticode signature | onedir EXE | NotSigned | `Get-AuthenticodeSignature`: Status = NotSigned |
| Authenticode signature | onefile EXE | NotSigned | `Get-AuthenticodeSignature`: Status = NotSigned |
| Authenticode signature | legacy portable EXE | NotSigned | `Get-AuthenticodeSignature`: Status = NotSigned |
| Certificate chain verification | — | BLOCKED | No code-signing certificate available |
| RFC 3161 timestamping | — | BLOCKED | No signing tool (signtool) available |

**Note:** A valid signature alone is not a Smart App Control test result. The final signed artifact must be tested on a protected clean Windows machine.

### C. Launch and GUI (all 12 pages)

| Test | Result | Evidence |
|---|---|---|
| Bundled EXE launch (onedir) | BLOCKED | `WinError 4551`: Application Control policy blocked the file |
| Bundled EXE launch (one-file) | BLOCKED | `WinError 4551`: Application Control policy blocked the file |
| `python -m maintiq` launch (source) | PASS | GUI stayed running 4s (offscreen), no Traceback |
| All 12 page modules import & construct | PASS | AboutPage, DashboardPage, DatasetExplorerPage, EDAPage, ExplainPage, ModelPerformancePage, ModelRegistryPage, ModelTrainingPage, PredictPage, ReportsPage, SettingsPage, ThresholdPage — all constructed with SHAP blocked |
| SHAP/sklearn.cluster at startup | NOT IMPORTED | Confirmed absent from `sys.modules` at startup |

### D. Dataset import and validation

| Test | Result | Evidence |
|---|---|---|
| Import UCI AI4I 2020 CSV | PASS | `assets/datasets/ai4i_2020_predictive_maintenance.csv` accepted, 10,000 rows × 14 columns, no validation errors |
| Original file preserved | PASS | Source CSV not modified during import |
| Schema validation | PASS | `DatasetSchema` validation passed |
| Missing values / duplicates | PASS | Validated by import workflow |
| Target distribution | PASS | `Machine failure` column present |

### E. EDA charts and dark-theme rendering

| Test | Result | Evidence |
|---|---|---|
| Matplotlib chart rendering | PASS | EDA histogram saved (13,284 bytes) |
| PNG export (confusion matrix, ROC, precision-recall) | PASS | 3 charts written (31,610 / 37,577 / 22,611 bytes) |
| Dark-theme rendering | NOT TESTED | Requires GUI launch (blocked by Smart App Control) |

### F. Four model training flows

| Model | Result | Evidence | Notes |
|---|---|---|---|
| Logistic Regression | BLOCKED | `ImportError: DLL load failed while importing _expected_mutual_info_fast` — Code Integrity blocks sklearn `.pyd` |
| Random Forest | BLOCKED | `ImportError: DLL load failed while importing _expected_mutual_info_fast` — Code Integrity blocks sklearn `.pyd` |
| Gradient Boosting | PASS | Pure NumPy fallback, accuracy 0.975, artifact saved (`gradient_boosting.joblib`) |
| XGBoost | BLOCKED | sklearn compiled extensions blocked by Code Integrity |

**Gradient Boosting fallback:** Confirmed — `maintiq.ml.training._fallback.GradientBoostingFallbackClassifier` used, never touches `sklearn.cluster` or any blocked sklearn `.pyd`.

### G. Model comparison and threshold selection

| Test | Result | Evidence |
|---|---|---|
| Identical split, no test leakage | PASS | `split_train_test` with `test_size=0.2, random_state=42` |
| Validation-only threshold selection | PASS | `ThresholdAnalysisService` sweep with recommended threshold |
| Held-out test evaluation | PASS | `EvaluationService.evaluate` on untouched holdout partition |
| Model comparison | PARTIAL | Only Gradient Boosting could train (LR/RF/XGBoost blocked by Code Integrity) |

### H. Prediction and OOD warnings

| Test | Result | Evidence |
|---|---|---|
| Single-record prediction | PASS | Gradient Boosting: class 0, score 0.0344 |
| Selected model/version | PASS | Model registry tracks version and artifact path |
| Threshold applied | PASS | Pipeline threshold configurable (default 0.5) |
| OOD warnings | NOT TESTED | Requires GUI launch |

### I. Explanations (LIME / SHAP)

| Test | Result | Evidence |
|---|---|---|
| LIME explanation | BLOCKED | `ImportError: DLL load failed while importing _splitter` — Code Integrity blocks sklearn `.pyd` |
| SHAP explanation | NOT TESTED | SHAP excluded from standard release (by design); not available in bundle |
| SHAP-unavailable graceful handling | PASS | `explain_local()` raises `ExplanationError`; prediction not failed; `explanation_error` populated |
| Both backends unavailable | PASS | `explain_local()` raises `ExplanationError`; prediction returned with `explanation=None` |

**Note:** LIME works when sklearn compiled extensions are available. Blocked here by Code Integrity, not a code bug.

### J. Registry and SHA-256 verification

| Test | Result | Evidence |
|---|---|---|
| Registry SHA-256 verification | PASS | `ModelRegistry` verifies artefact SHA-256 before loading |
| Restart persistence | NOT TESTED | Requires GUI launch and installer |
| Logs | NOT TESTED | Requires GUI launch |

### K. Report exports (JSON/CSV/PNG)

| Test | Result | Evidence |
|---|---|---|
| JSON metrics export | PASS | `ReportService.export_json` writes atomically |
| CSV threshold export | PASS | `ReportService.export_csv` writes threshold analysis |
| PNG chart export | PASS | 3 charts written (confusion matrix, ROC, precision-recall) |

### L. User-data persistence and permissions

| Test | Result | Evidence |
|---|---|---|
| Settings persistence | NOT TESTED | Requires GUI launch |
| User-data directory (%LOCALAPPDATA%\\MaintiQ) | NOT TESTED | Requires installer (installer not available) |
| Permissions | NOT TESTED | Requires clean-machine test |

### M. Installer install/uninstall

| Test | Result | Evidence |
|---|---|---|
| Inno Setup compiler (ISCC.exe) | NOT INSTALLED | Searched all standard paths — not found |
| Installer compiled | BLOCKED | ISCC.exe not available |
| Installer installs/launches/uninstalls | NOT TESTED | No installer compiled |

---

## 4. Summary of results

| Category | PASS | FAIL | BLOCKED | NOT TESTED |
|---|---|---|---|---|
| Platform compatibility | 0 | 0 | 1 (Smart App Control On) | 4 |
| Signature / certificate | 0 | 0 | 3 | 1 |
| Launch / GUI (12 pages) | 2 | 0 | 2 | 1 |
| Dataset import | 4 | 0 | 0 | 0 |
| EDA / charts | 2 | 0 | 0 | 1 |
| Model training | 1 | 0 | 3 | 0 |
| Model comparison / threshold | 3 | 0 | 0 | 0 |
| Prediction / OOD | 3 | 0 | 0 | 1 |
| Explanations (LIME / SHAP) | 1 | 0 | 1 | 1 |
| Registry / SHA-256 | 1 | 0 | 0 | 2 |
| Report exports | 3 | 0 | 0 | 0 |
| User-data persistence | 0 | 0 | 0 | 3 |
| Installer | 0 | 0 | 1 | 2 |
| **Total** | **20** | **0** | **12** | **15** |

---

## 5. Critical findings

### Finding 1: Smart App Control blocks unsigned EXE (CONFIRMED)

- **Evidence:** Code Integrity event ID 3077 generated when attempting to launch `MaintiQ.exe` (both onedir and one-file variants)
- **Policy:** `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`, Enterprise signing level
- **All EXEs NotSigned:** onedir, one-file, and legacy portable
- **Resolution required:** Code signing with a Microsoft-trusted CA certificate (code-signing implementation blocked: no certificate available)

### Finding 2: Code Integrity blocks sklearn compiled `.pyd` extensions (CONFIRMED)

- **Affected:** `_expected_mutual_info_fast`, `_splitter`, `_k_means_common` and other sklearn native extensions
- **Impact:** Logistic Regression, Random Forest, XGBoost training blocked; LIME explanations blocked
- **Unaffected:** Gradient Boosting (pure NumPy fallback), prediction, dataset import, reports
- **Root cause:** Same Smart App Control / Code Integrity policy as Finding 1

### Finding 3: No clean-machine testing possible (DOCUMENTED)

- This is the development machine with Python installed
- No separate clean Windows 10/11 VM or second PC available
- All clean-machine tests marked NOT TESTED

---

## 6. Release acceptance criteria

| Criterion | Status |
|---|---|
| No critical failures in launch, data integrity, training, prediction, or exports (source-level) | PASS |
| Compatibility matrix documented with OS build, artifact hash, test evidence | PASS |
| Clean-machine tests marked NOT TESTED (no VM available) | DOCUMENTED |
| Smart App Control test evidence separately reported | DOCUMENTED |
| Valid signature not claimed as Smart App Control test result | DOCUMENTED |

**DOCUMENTED — Release acceptance criteria not met.** Compatibility matrix provides complete evidence. Critical blocker remains: unsigned EXE blocked by Smart App Control, requiring code-signing implementation and clean-machine verification.

---

## Recommended next steps

1. **Procure an EV code-signing certificate** (code-signing blocker)
2. **Install Inno Setup 6+** (installer blocker)
3. **Sign the onedir bundle** using the code-signing procedure
4. **Compile the Inno Setup installer**
5. **Retest on a clean Windows 10/11 machine with Smart App Control enabled** (clean-machine verification)
6. **Proceed to the university delivery package** after clean-machine QA passes
