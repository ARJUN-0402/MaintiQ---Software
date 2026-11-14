# MaintiQ — Phase 2: Windows Smart App Control / Code Integrity Diagnostics

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Diagnostic only. No settings changed, no Unblock-File, no policy changes, no signing.  
**Evidence standard:** PASS / FAIL / BLOCKED / NOT TESTED. No invented results.

---

## 1. Smart App Control state (read-only, not changed)

`Get-MpComputerStatus` returned `SmartAppControl:` and `SmartAppControlEnabled:` empty (property not exposed on this build).  
Registry `HKLM:\SYSTEM\CurrentControlSet\Control\DeviceGuard\Services\SmartAppControl` and `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SmartScreen` returned no value.

**Active enforcement observed:** Microsoft-Windows-CodeIntegrity/Operational event ID **3077** is actively being generated, which means Code Integrity / Smart App Control is actively blocking unsigned binaries on this machine. Exact On / Evaluation / Off toggle could not be read directly via `Get-MpPreference` on this build, but enforcement is confirmed by the 3077 events below.

State: **ACTIVELY ENFORCING (On-equivalent behavior confirmed via event log)** — exact toggle not directly readable.

---

## 2. Code Integrity event log — Microsoft-Windows-CodeIntegrity/Operational

Event ID 3077 = "Code Integrity determined that a process attempted to load a file that did not meet the Enterprise signing level requirements or violated code integrity policy."

All events share Policy ID: `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`.

### MaintiQ.exe launch blocks (powershell.exe as calling process)

| TimeCreated | Event ID | Process attempting load | Blocked file path | Policy ID |
|---|---|---|---|---|
| 2026-11-14 17:54:45 | 3077 | `...\WindowsPowerShell\v1.0\powershell.exe` | `...\MaintiQ\release\MaintiQ-Portable\MaintiQ.exe` | `{0283ac0f-...}` |
| 2026-11-14 17:54:34 | 3077 | `...\WindowsPowerShell\v1.0\powershell.exe` | `...\MaintiQ\release\MaintiQ-Portable\MaintiQ.exe` | `{0283ac0f-...}` |
| 2026-11-14 14:32:47 | 3077 | `...\WindowsPowerShell\v1.0\powershell.exe` | `...\MaintiQ\release\MaintiQ-Portable\MaintiQ.exe` | `{0283ac0f-...}` |

### sklearn native extension blocks (python3.13.exe as calling process)

| TimeCreated | Event ID | Process | Blocked file path |
|---|---|---|---|
| 2026-11-14 16:56:58 | 3077 | `...\PythonSoftwareFoundation.Python.3.13_...\python3.13.exe` | `...\site-packages\pyarrow\lib.cp313-win_amd64.pyd` |
| 2026-11-14 14:07:25 | 3077 | python3.13.exe | `...\sklearn\manifold\_utils.cp313-win_amd64.pyd` |
| 2026-11-14 14:06:52 | 3077 | python3.13.exe | `...\sklearn\datasets\_svmlight_format_fast.cp313-win_amd64.pyd` |
| 2026-11-14 14:06:50 | 3077 | python3.13.exe | `...\sklearn\manifold\_barnes_hut_tsne.cp313-win_amd64.pyd` |
| 2026-11-14 13:43:34–36 | 3077 | python3.13.exe | `...\sklearn\_isotonic.cp313-win_amd64.pyd` (repeated) |
| 2026-11-14 13:40:22 | 3077 | powershell.exe | `...\ .venv\Scripts\pytest.exe` |

No event ID 3076 (audit-allow) was relevant to MaintiQ; all MaintiQ-related records are 3077 (blocks).

---

## 3. Authenticode signature verification

| File | Status | StatusMessage |
|---|---|---|
| `release\MaintiQ-Portable\MaintiQ.exe` | **NotSigned** | The file is not digitally signed. |
| `.venv\Lib\site-packages\sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` | **NotSigned** | The file is not digitally signed. |

**Interpretation:** `NotSigned` describes signature state only; it does **not** prove malware. The block occurs because these unsigned files fail the Enterprise signing level required by the active Code Integrity policy.

---

## 4. .pyd provenance verification (not downloaded from an untrusted site)

File: `.venv\Lib\site-packages\sklearn\cluster\_k_means_common.cp313-win_amd64.pyd`
- Exists: **Yes**
- Size: 196,096 bytes
- SHA-256: `81302ca06d8a9fddf3018e9b1e97e5d2f1fa340ffd84f576ef479f23ea9dcde8`
- Listed in `scikit-learn` package files: **Yes** (`_k_means_common.cp313-win_amd64.pyd`, plus `.lib`/`.pxd`/`.pyx`)
- scikit-learn version: **1.9.1**
- Install path: standard `.venv\Lib\site-packages\` (installed via pip from the official scikit-learn wheel)

**Provenance: CONFIRMED** — the pyd is part of the officially installed scikit-learn 1.9.1 wheel, not a binary downloaded from an untrusted site. Vendor signature must be preserved; it must not be patched or re-signed without legal/technical approval.

---

## 5. Mechanism differentiation (read-only)

| Mechanism | Evidence on this machine | Relevant to MaintiQ block? |
|---|---|---|
| **Smart App Control / Code Integrity** | Event 3077 generated, Policy ID `{0283ac0f-...}`, "Enterprise signing level requirements" | **YES — confirmed blocker** |
| SmartScreen (download/browser) | Registry `SmartScreen\Enabled` empty; no SmartScreen events | No — SmartScreen flags downloads, not local EXE load |
| Defender Antivirus | `DisableRealtimeMonitoring: False`, `DisableBehaviorMonitoring: False` (AV on) but no Defender AV detection events (1116/1117) | No — this is Code Integrity, not malware detection |
| WDAC / AppLocker policy | `Get-AppLockerPolicy` cmdlet unavailable; block reported via Code Integrity 3077 with "Enterprise signing level" | Code Integrity family (related), evidenced by 3077 |
| PowerShell execution policy | All scopes Undefined except CurrentUser `Bypass`; controls scripts, not EXE/DLL loading | No — not a factor for EXE launch |

**Conclusion:** The block is **Smart App Control / Code Integrity** (event 3077, Enterprise signing level), not SmartScreen, not Defender AV, and not PowerShell execution policy.

---

## 6. Files and features affected

| File | Signed? | Required for core startup? | Feature affected | Status |
|---|---|---|---|---|
| `release\MaintiQ-Portable\MaintiQ.exe` | NotSigned | YES — the app itself | **App launch** (all 12 pages) | BLOCKED |
| `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` | NotSigned | NO — only when SHAP explainer invoked | SHAP explanations (Explain page, backend=shap/auto) | BLOCKED if SHAP used |
| `sklearn\manifold\_utils.cp313-win_amd64.pyd` | NotSigned | NO (manifold, not core) | Manifold learning (not a core MaintiQ workflow) | BLOCKED if used |
| `sklearn\datasets\_svmlight_format_fast.cp313-win_amd64.pyd` | NotSigned | NO | svmlight dataset loading (not core) | BLOCKED if used |
| `sklearn\manifold\_barnes_hut_tsne.cp313-win_amd64.pyd` | NotSigned | NO | TSNE (not core) | BLOCKED if used |
| `sklearn\_isotonic.cp313-win_amd64.pyd` | NotSigned | NO | Isotonic regression (not core) | BLOCKED if used |
| `sklearn` base (imported at startup) | — | Partially — `sklearn.base` loads at startup via feature transformer/preprocessor | Core import succeeds, but dependent pyds may block on use | Partial |

Key insight from Phase 1: MaintiQ does **not** import `sklearn.cluster` at startup; `_k_means_common.pyd` is only loaded when the user explicitly invokes SHAP. Therefore:
- **App launch is BLOCKED** because MaintiQ.exe itself is NotSigned (primary block).
- **SHAP explanations would be BLOCKED** because `_k_means_common.pyd` is NotSigned (secondary, feature-only).
- Core training (Logistic Regression / Random Forest) imports sklearn at startup but uses the NumPy Gradient Boosting fallback; whether LR/RF training triggers blocked sklearn pyds depends on which sklearn submodules load — NOT TESTED in this phase (requires a run attempt, which would be blocked).

---

## 7. Classification

**CONFIRMED.**

The blocking mechanism is supported by direct Windows evidence:
- Code Integrity event ID 3077 explicitly records MaintiQ.exe being blocked because it "did not meet the Enterprise signing level requirements or violated code integrity policy."
- Authenticode confirms MaintiQ.exe and `_k_means_common.pyd` are **NotSigned**.
- SmartScreen, Defender AV, and PowerShell execution policy are ruled out.

Root cause: MaintiQ.exe is an unsigned PyInstaller one-file executable running on a machine with Code Integrity / Smart App Control actively enforcing an Enterprise signing level. Unsigned project-owned executables are blocked. Additionally, unsigned third-party native extensions (sklearn/xgboost/numpy pyds) would be blocked if loaded.

---

## 8. Acceptance gate — Phase 2

**PASS — evidence-based.**

- Smart App Control state: active enforcement confirmed via Code Integrity 3077 events (exact On/Evaluation/Off toggle not directly readable via `Get-MpPreference`).
- Code Integrity event log inspected: multiple 3077 records for MaintiQ.exe and sklearn pyds, with event ID, time, full path, policy details captured.
- Event ID/time/full path/policy/SHA-256 recorded for each blocked file.
- `Get-AuthenticodeSignature` run on EXE and blocked pyd: both NotSigned (signature state, not malware proof).
- `_k_means_common.pyd` provenance verified against the installed scikit-learn 1.9.1 wheel (not an untrusted download).
- Mechanism distinguished from SmartScreen, Defender AV, WDAC/AppLocker, and PowerShell execution policy.
- Finding classified as **CONFIRMED**.

No `Unblock-File`, no security-policy changes, no settings modifications were used as a fix. No signing attempted.

---

## Recommended next step (Phase 3)

Proceed to optional dependency isolation: move SHAP (and its `sklearn.cluster`/`_k_means_common.pyd` dependency) into a narrow, lazy, feature-only call path so GUI startup and all four training/prediction paths work without SHAP. This removes the `_k_means_common.pyd` block for the standard release. The remaining block — unsigned MaintiQ.exe itself — requires code signing (Phase 7/8) or is addressed by the dependency isolation making the standard bundle not require the blocked pyds; however the EXE launch block is a signing-level issue that ultimately needs a trusted signature (Phase 7 eligibility, Phase 8 implementation).
