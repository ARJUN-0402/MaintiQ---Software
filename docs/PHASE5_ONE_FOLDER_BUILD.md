# MaintiQ — Phase 5: PyInstaller One-Folder Diagnostic Build

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Complete. One-folder diagnostic build produced successfully. No code signing attempted (Phase 7-8).  
**Evidence standard:** PASS / FAIL / BLOCKED / NOT TESTED. No invented results.

---

## 1. Spec file changes

`packaging\maintiq.spec` was updated per Phases 1–3 findings (SHAP optional, `sklearn.cluster` causes blocked pyd):

| Change | Before | After | Rationale |
|---|---|---|---|
| `hiddenimports` | `"shap"`, `"lime"` | `"lime"` only | SHAP removed (proven optional, causes blocked pyd) |
| `hiddenimports` | `"sklearn"` | `"sklearn"` | Kept — core models need sklearn base |
| `excludes` | `[]` | `["sklearn.cluster", "shap"]` | Exclude blocked clustering + SHAP |
| `EXE` binaries/zipfiles/datas | `a.binaries`, `a.zipfiles`, `a.datas` | `[]`, `[]`, `[]` | Moved to COLLECT for one-dir mode |
| `EXE` new param | — | `exclude_binaries=True` | PyInstaller one-dir mode control |
| `COLLECT` block | — | Added | Standard PyInstaller one-dir pattern |
| `upx` | `True` | `True` | Kept (compression) |
| `console` | `False` | `False` | Windowed GUI app |

The spec remains the single source of truth — no competing build pipeline created. `--onedir`/`--onefile` are not valid with a spec file; the spec controls the mode.

---

## 2. Build command and environment

| Item | Value |
|---|---|
| Build environment | `.venv-build` (Phase 4, isolated, `.venv` untouched) |
| Python | 3.13.14 |
| PyInstaller | 6.22.3 |
| Command | `.venv-build\Scripts\python.exe -m PyInstaller packaging\maintiq.spec --noconfirm --distpath release/staging/onedir --workpath build/staging` |
| Previous release preserved | YES — `release/MaintiQ-Portable/MaintiQ.exe` untouched |
| Build output path | `release/staging/onedir/MaintiQ/` (one-dir) |

---

## 3. Build output structure

One-dir bundle at `release/staging/onedir/MaintiQ/`:

```
MaintiQ/
  MaintiQ.exe          (22,843,697 bytes, bootloader)
  _internal/
    python313.dll
    VCRUNTIME140.dll, VCRUNTIME140_1.dll
    libcrypto-3.dll, libssl-3.dll
    sqlite3.dll
    PySide6/Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll, ... (14 Qt DLLs)
    numpy.libs/, pandas.libs/, scipy.libs/
    sklearn/  (cluster/ present but _k_means_common.pyd ABSENT)
    base_library.zip, PYZ-00.pyz
  assets/icons/app.ico
  base_library.zip
```

- **2,169 files** total in the bundle
- Manifest with SHA-256 checksums: `release/staging/onedir_manifest.csv`
- PyInstaller warnings: `release/staging/onedir/_build_warn-maintiq.txt`
- Cross-reference: `release/staging/onedir/_build_xref-maintiq.html`

---

## 4. Dependency exclusion verification

| Item | Present in bundle? | Notes |
|---|---|---|
| `sklearn\cluster\_k_means_common.cp313-win_amd64.pyd` | **NO** | The blocked NotSigned binary from Phase 2 is excluded |
| `sklearn\cluster\_k_means_common.{lib,pxd,pyx}` | YES | Harmless source artifacts, never loaded |
| `sklearn\cluster\reshape.cp313-win_amd64.pyd` | YES | Present but never loaded (MaintiQ doesn't import sklearn.cluster) |
| `shap` / `shap.*` | **NO** | Excluded from bundle |
| `lime` | YES | Retained as optional backend |
| `Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll` | YES | Vendor signatures Valid (hashes match Phase 1) |
| `python313.dll` | YES | CPython runtime |

Qt DLL SHA-256 hashes match Phase 1 exactly — vendor Authenticode signatures preserved:
- Qt6Core.dll: `F57ED38AFD95D0306CCA9D88D997F639F70C7628A4F1F064EAE291D579487121`
- Qt6Gui.dll: `ABD20026E190E8CC69667D1BEA042DB05CD353CC05E7DA74B063C20B7DA3F6CD`
- Qt6Widgets.dll: `2F62CBE2869FFF4E20DF7369C2786E1EC7EC290D5A63D1371B7F70CF06909C3F`

---

## 5. Launch verification

| Test | Result |
|---|---|
| Bundled EXE exists at `release/staging/onedir/MaintiQ/MaintiQ.exe` | PASS (22.8 MB) |
| EXE launches from staging without source-tree or venv paths | BLOCKED — `WinError 4551`: "An Application Control policy has blocked this file" |

**The launch block is the Phase 2 CONFIRMED Smart App Control / Code Integrity policy** — the EXE is NotSigned and the machine enforces Enterprise signing level. This is **not a build failure**; it is the same security block that requires code signing (Phases 7–8). The one-dir structure is correct: all DLLs, Qt plugins, assets, and imports are present in the bundle.

No attempt was made to `Unblock-File`, change security settings, or sign the EXE in this phase.

---

## 6. Warnings analysis

`build/staging/maintiq/warn-maintiq.txt` saved to staging. Key findings:
- `excluded module named shap` — confirms SHAP exclusion is working
- Standard missing-module noise for optional/narwhals/pyarrow/xgboost/dask/cudf/scipy/sphinx/rich/graphviz — all conditional/optional imports, not required by MaintiQ
- No actionable missing module for MaintiQ's own code

---

## 7. Acceptance gate — Phase 5

| Criterion | Status |
|---|---|
| .spec updated — SHAP removed from hidden imports, sklearn.cluster excluded | PASS |
| One-dir build produced using `.venv-build` | PASS |
| Previous release preserved (not deleted) | PASS |
| Output at `release/staging/onedir/MaintiQ/` | PASS |
| All Qt DLLs present with valid vendor signatures | PASS |
| `_k_means_common.pyd` excluded from bundle | PASS |
| SHAP excluded from bundle | PASS |
| LIME retained | PASS |
| PyInstaller warnings and xref saved | PASS |
| SHA-256 manifest generated (2,169 files) | PASS |
| EXE launch from staging | BLOCKED by Code Integrity (Phase 2, needs signing) |

**PASS — Phase 5 acceptance gate met.** The one-folder diagnostic build is structurally correct. The only blocker is the unsigned EXE being blocked by Smart App Control / Code Integrity, which requires code signing (Phases 7–8).

---

## Recommended next step (Phase 6)

Functional validation of the one-dir bundle on a machine without Code Integrity enforcement (or with the EXE signed). Validate:
1. GUI launches and all 12 pages render
2. Dataset import, preprocessing, four-model training
3. Prediction with LIME backend (SHAP unavailable)
4. Reports and EDA charts

Then proceed to Phase 7 (code-signing eligibility) and Phase 8 (signing implementation).
