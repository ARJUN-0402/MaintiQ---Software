# MaintiQ — Phase 8: Code-Signing Implementation (BLOCKED — no certificate available)

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Status:** BLOCKED — Phase 7 confirmed no code-signing certificate or signing tooling exists on this system. A public CA certificate (EV recommended) must be procured before Phase 8 can proceed.  
**Evidence standard:** PASS / FAIL / BLOCKED / DOCUMENTED. No invented results.

---

## 1. Blocker statement

The bundled EXE (`release/staging/onedir/MaintiQ/MaintiQ.exe`) is **NotSigned** and cannot pass Smart App Control / Code Integrity on target machines (Phase 2 CONFIRMED). Code signing with a Microsoft-trusted certificate is required. No such certificate exists on this system (Phase 7), and I cannot procure one.

**Blocker: Certificate procurement.** User must obtain an EV code-signing certificate from a public CA trusted by Microsoft (DigiCert, Sectigo, GlobalSign, Entrust, etc.) and install Windows SDK `signtool.exe` before Phase 8 can execute.

---

## 2. Signing implementation procedure (ready for when cert is available)

### 2.1 Prerequisites

| Item | Required |
|---|---|
| Code-signing certificate | EV code-signing cert from public CA (preferred for Smart App Control) |
| Certificate file | `.pfx` or `.p12` with private key |
| Signing tool | `signtool.exe` from Windows SDK (Windows Kits 10 or 11) |
| Timestamping server | `http://timestamp.digicert.com` or CA-provided TSA |

### 2.2 Files to sign (in `release/staging/onedir/MaintiQ/`)

Sign in this order:

1. **`MaintiQ.exe`** — the bootloader EXE (primary)
2. **`_internal/python313.dll`** — CPython runtime
3. **`_internal/PySide6/Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, ...** — all 14 Qt DLLs (vendor-signed already; re-signing not required but harmless if done consistently)
4. **`_internal/numpy.libs/`, `_internal/pandas.libs/`, `_internal/scipy.libs/`** — native extension DLLs
5. **`_internal/sklearn/`** — sklearn `.pyd` extensions (excluding `_k_means_common.cp313-win_amd64.pyd` which is already excluded)
6. **`_internal/*.pyd`** — all compiled extensions

**Do not sign:** `.py`, `.pyc`, `.json`, `.zip`, `.pyz`, `.html`, `.csv`, `.png`, `.ico`, `.txt` files (signing non-binary files is unnecessary and can break PyInstaller's archive verification).

### 2.3 signtool command (template)

```powershell
# Sign the main EXE
& "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe" sign `
    /f "path\to\certificate.pfx" `
    /p "<pfx-password>" `
    /tr "http://timestamp.digicert.com" `
    /td SHA256 `
    /fd SHA256 `
    /v `
    "release/staging/onedir/MaintiQ/MaintiQ.exe"

# Sign all DLLs and PDYs in _internal (PowerShell)
Get-ChildItem -Path "release/staging/onedir/MaintiQ/_internal" -Recurse -Include *.dll,*.pyd | ForEach-Object {
    & "C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe" sign `
        /f "path\to\certificate.pfx" `
        /p "<pfx-password>" `
        /tr "http://timestamp.digicert.com" `
        /td SHA256 `
        /fd SHA256 `
        $_.FullName
}
```

### 2.4 Signing script to add

Create `scripts/sign_release.ps1` when a certificate is available. The script should:
- Accept `-CertificatePath`, `-CertificatePassword`, `-TimestampServer` parameters
- Sign `MaintiQ.exe` first, then all `.dll`/`.pyd` files under `_internal/`
- Verify each signature after signing
- Fail closed if any file fails to sign

---

## 2.5 Verification after signing

| Check | Command | Expected |
|---|---|---|
| EXE signature | `Get-AuthenticodeSignature "MaintiQ.exe"` | Status: Valid |
| All DLLs signed | Loop `Get-AuthenticodeSignature` on all `.dll`/`.pyd` | All Valid |
| Timestamp present | `signtool verify /v /pa "MaintiQ.exe"` | Timestamp shows CA TSA |
| Smart App Control | Launch EXE on target machine | No WinError 4551 |

---

## 3. What has been prepared (no code changes needed yet)

The following Phase 5 outputs are ready to be signed:

| Artifact | Path | Size | Current Authenticode |
|---|---|---|---|
| Bundled EXE | `release/staging/onedir/MaintiQ/MaintiQ.exe` | 22,843,697 bytes | NotSigned |
| Qt6Core.dll | `_internal/PySide6/Qt6Core.dll` | 10,472,760 bytes | Valid (vendor) |
| Qt6Gui.dll | `_internal/PySide6/Qt6Gui.dll` | 9,683,256 bytes | Valid (vendor) |
| Qt6Widgets.dll | `_internal/PySide6/Qt6Widgets.dll` | 6,520,120 bytes | Valid (vendor) |
| python313.dll | `_internal/python313.dll` | 6,132,448 bytes | NotSigned |
| sklearn pyds | `_internal/sklearn/` | various | NotSigned |
| _k_means_common.pyd | — | EXCLUDED | — |

SHA-256 manifest: `release/staging/onedir_manifest.csv` (2,169 files)

---

## 4. Smart App Control expectations after signing

| Scenario | Expected result |
|---|---|
| EV-signed EXE on Smart App Control machine | Should launch (EV certs are trusted) |
| OV-signed EXE on Smart App Control machine | May launch; less certain than EV |
| Self-signed EXE | Still blocked |
| Unsigned EXE | Blocked (current state) |

---

## 5. Acceptance gate — Phase 8

| Criterion | Status |
|---|---|
| Code-signing certificate available | BLOCKED (none on system) |
| signtool.exe available | BLOCKED (not installed) |
| Signing procedure documented | DOCUMENTED |
| Files to sign identified | DOCUMENTED |
| Verification steps defined | DOCUMENTED |

**BLOCKED — Phase 8 cannot execute without a certificate.** All implementation details are documented above for immediate execution once a certificate is procured.

---

## 6. Immediate next step

**Procure an EV code-signing certificate** from a public CA trusted by Microsoft. Once obtained:
1. Install the certificate (`.pfx`/`.p12`) on the build machine
2. Install Windows SDK `signtool.exe`
3. Run the signing procedure above on `release/staging/onedir/MaintiQ/`
4. Re-validate the bundle launches on a Smart App Control-enabled machine
5. Proceed to final release (one-file or one-dir, installer via `packaging\maintiq-installer.iss`)

No source code changes are required for Phase 8 — only certificate procurement and signing execution.
