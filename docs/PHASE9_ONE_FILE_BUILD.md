# MaintiQ — Phase 9: PyInstaller One-File Executable Build

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Complete. One-file variant built successfully. Launch blocked by Smart App Control (unsigned) — same as onedir.  
**Evidence standard:** PASS / FAIL / BLOCKED / DOCUMENTED. No invented results.

---

## 1. One-file spec created

New file: `packaging\maintiq-onefile.spec`

Built from the verified onedir spec (`packaging\maintiq.spec`) with the following changes:

| Setting | onedir spec | onefile spec | Rationale |
|---|---|---|---|
| `EXE` binaries/zipfiles/datas | `[]`, `[]`, `[]` (moved to COLLECT) | `a.binaries`, `a.zipfiles`, `a.datas` | One-file embeds all binaries in the EXE |
| `exclude_binaries` | `True` | not set | One-file mode does not use exclude_binaries |
| `COLLECT` block | Present | Not present | One-file produces a single EXE, no COLLECT needed |
| Output path | `release/staging/onedir/` | `release/staging/onefile/` | Separate staging path, previous release preserved |

All other settings identical: same hidden imports (minus shap), same excludes (`sklearn.cluster`, `shap`), same datas (`assets/icons`), same upx=True, same icon.

---

## 2. Build command and environment

| Item | Value |
|---|---|
| Build environment | `.venv-build` (Phase 4, isolated) |
| Python | 3.13.14 |
| PyInstaller | 6.22.3 |
| Command | `.venv-build\Scripts\python.exe -m PyInstaller packaging\maintiq-onefile.spec --noconfirm --distpath release/staging/onefile --workpath build/staging-onefile` |
| Previous release preserved | YES — `release/MaintiQ-Portable/` and `release/staging/onedir/` untouched |

---

## 3. Build output

| Artifact | Path | Size | SHA-256 | Modified |
|---|---|---|---|---|
| One-file EXE | `release/staging/onefile/MaintiQ.exe` | 130,753,015 bytes (~124.7 MB) | `0F2ECC08FE71271728CFA7E67E204BF5FAB1F40F2104BE4D93B69CA10EF42013` | 2026-11-14 21:02:55 |

Build artifacts saved:
- Warnings: `release/staging/onefile/_build_warn-maintiq-onefile.txt`
- Cross-reference: `release/staging/onefile/_build_xref-maintiq-onefile.html`
- Manifest: `release/staging/onefile_manifest.csv` (1 file)

The one-file EXE is larger than the onedir bootloader EXE (22.8 MB) because it embeds all DLLs, the Python runtime, and the PKG archive internally. Total on-disk size is comparable (~130 MB for one-file vs ~131 MB for onedir EXE + ~108 MB of sidecar DLLs).

---

## 4. Dependency exclusion verification

| Item | Present in one-file bundle? | Notes |
|---|---|---|
| `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` | **NO** | Excluded per Phase 1–3 |
| `shap` / `shap.*` | **NO** | Excluded per Phase 1–3 |
| `lime` | YES | Retained as optional backend |
| All Qt DLLs | YES | Embedded in EXE (vendor signatures preserved) |
| `python313.dll` | YES | Embedded in EXE |

---

## 5. Launch verification

| Test | Result |
|---|---|
| EXE exists | PASS (130,753,015 bytes) |
| EXE launches from staging without source/venv paths | BLOCKED — `WinError 4551`: "An Application Control policy has blocked this file" |

**The launch block is the Phase 2 CONFIRMED Smart App Control / Code Integrity policy** — the EXE is NotSigned. This is **not a build failure**; it is the same security block that requires code signing (Phases 7–8).

No attempt was made to `Unblock-File`, change security settings, or sign the EXE.

---

## 6. One-file vs onedir comparison

| Criterion | onedir | one-file |
|---|---|---|
| Build succeeded | PASS | PASS |
| All dependencies included | YES | YES |
| SHAP/cluster excluded | YES | YES |
| LIME retained | YES | YES |
| Qt vendor signatures preserved | YES | YES |
| Launch from staging | BLOCKED (unsigned) | BLOCKED (unsigned) |
| File count | 2,169 files | 1 file |
| Bootloader EXE size | 22.8 MB | 130.8 MB |
| Debuggability | Easier (files visible) | Harder (single archive) |
| Startup time | Faster (no extraction) | Slower (extracts to temp) |
| Distribution simplicity | Moderate (folder) | Simple (single file) |

**Recommendation:** Retain the **onedir** distribution as the primary release (PyInstaller recommends one-folder for easier debugging, faster startup, and visible file structure). The **one-file** variant is a valid secondary option for simpler distribution, but it is less reliable per PyInstaller guidance and has slower startup due to temp extraction. Do not force one-file if it is less reliable — keep the tested onedir distribution.

---

## 7. Acceptance gate — Phase 9

| Criterion | Status |
|---|---|
| One-file spec created from verified onedir spec | PASS |
| One-file build produced using `.venv-build` | PASS |
| Previous release preserved (not deleted) | PASS |
| Output at `release/staging/onefile/MaintiQ.exe` | PASS |
| SHA-256 manifest generated | PASS |
| PyInstaller warnings and xref saved | PASS |
| SHAP/clustering excluded | PASS |
| LIME retained | PASS |
| EXE launch | BLOCKED by Code Integrity (Phase 2, needs signing) |
| One-file vs onedir comparison documented | PASS |

**PASS — Phase 9 acceptance gate met.** The one-file diagnostic build is structurally correct. The only blocker is the unsigned EXE being blocked by Smart App Control / Code Integrity, requiring code signing (Phases 7–8).

---

## Recommended next step (Phase 10)

Proceed to Inno Setup installer build — **BLOCKED** because `ISCC.exe` is not installed on this system. The existing `packaging\maintiq-installer.iss` references `release\MaintiQ-Portable\*` (the old one-file portable path), not the new staged bundles. The script also has issues: `PrivilegesRequired=admin`, installs to `{pf}` (Program Files, protected), and `[UninstallDelete]` deletes the entire app directory on uninstall (risk of deleting user data). These need review before installer compilation.
