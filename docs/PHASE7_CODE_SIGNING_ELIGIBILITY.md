# MaintiQ — Phase 7: Code-Signing Eligibility

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Complete. No code-signing certificate or signing tooling available on this system.  
**Evidence standard:** PASS / FAIL / BLOCKED / DOCUMENTED. No invented results.

---

## 1. Code-signing certificate availability — NONE

### Windows certificate store search

| Store | CodeSigningCert count | Total certs | Suitable for code signing? |
|---|---|---|---|
| `Cert:\CurrentUser\My` | 0 | 6 | NO |
| `Cert:\LocalMachine\My` | 0 | 0 | NO |
| `Cert:\CurrentUser\CA` | N/A | 16 | NO (CA intermediate) |
| `Cert:\LocalMachine\CA` | N/A | 4 | NO (CA intermediate) |
| `Cert:\CurrentUser\Root` | N/A | 55 | NO (trusted root) |
| `Cert:\LocalMachine\Root` | N/A | 55 | NO (trusted root) |

### CurrentUser\My certificate details (6 certs, none suitable)

| Subject | Issuer | EKU | Private Key | Expires | Suitable? |
|---|---|---|---|---|---|
| CN=2f15328b-... | self-signed | (none) | Yes | 2027-06-13 | NO |
| CN=trust_33bdd4fb-... | self-signed | (none) | Yes | 2027-06-13 | NO |
| CN=9e5c822c-... | self-signed | (none) | Yes | 2027-06-11 | NO |
| CN=bba934ae-... | self-signed | (none) | Yes | 2026-12-21 | NO |
| CN=trust_2f15328b-... | self-signed | (none) | Yes | 2027-06-13 | NO |
| CN=33bdd4fb-... | self-signed | (none) | Yes | 2027-06-13 | NO |

**All 6 certs have empty Enhanced Key Usage (EKU)** — none carry the Code Signing EKU (`1.3.6.1.5.5.7.3.3`). They are self-signed (Subject == Issuer), likely auto-generated for TLS/internal use. **None can be used for Authenticode code signing.**

### Certificate files in project — NONE

| Pattern | Found? |
|---|---|
| `*.pfx` | NO |
| `*.p12` | NO |
| `*.cer` | NO |

---

## 2. Signing tooling availability — NONE

| Tool | Found? | Location | Notes |
|---|---|---|---|
| `signtool.exe` (Windows SDK) | NO | — | Not in Windows Kits 10 or 11 |
| `signtool.exe` (Visual Studio) | NO | — | Not in VS install directories |
| `osslsigncode` | NO | — | Not installed |
| `codesign` | NO | — | macOS tool, not applicable |
| `openssl` | NO | — | Not installed |
| `certutil.exe` | YES | `C:\Windows\system32\certutil.exe` | Can inspect certs, cannot sign |
| `New-SelfSignedCertificate` | YES | PowerShell PKI module | Can generate self-signed cert (not CA-trusted) |

**No Authenticode signing tool (signtool) is available.** `certutil` cannot sign binaries. `openssl` is not installed.

---

## 3. EV vs standard certificate requirements for Smart App Control

Smart App Control / Code Integrity (the confirmed blocker from Phase 2) requires binaries to be signed by a certificate that chains to a **Microsoft-trusted root CA**.

| Certificate type | Smart App Control trust? | Notes |
|---|---|---|
| EV code-signing cert (public CA) | YES — most reliable | EV-signed binaries historically bypass Smart App Control blocks |
| Standard (OV) code-signing cert (public CA) | MAYBE | Smart App Control has been more lenient with EV; standard OV may still be blocked on stricter policies |
| Self-signed cert | NO | Not trusted by Smart App Control |
| Internal/private CA cert | NO (unless CA root is deployed to target machines) | Would require deploying the CA root to every target machine |

**Bottom line:** A self-signed certificate (even one generated with `New-SelfSignedCertificate` with the Code Signing EKU) will **not** satisfy Smart App Control. The certificate must chain to a Microsoft-trusted root. An EV code-signing certificate from a public CA (DigiCert, Sectigo, GlobalSign, etc.) is the most reliable path.

---

## 4. Self-signed certificate viability — NOT viable for Smart App Control

`New-SelfSignedCertificate` is available and could generate a self-signed cert with Code Signing EKU, but:
- It will **not** chain to a Microsoft-trusted root
- Smart App Control will **still block** the signed binary
- Only suitable for internal testing where Smart App Control is disabled or the cert is manually trusted

---

## 5. Acceptance gate — Phase 7

| Criterion | Status |
|---|---|
| Code-signing certificate found on system | FAIL (none) |
| Signing tool (signtool) found | FAIL (none) |
| Certificate file (.pfx/.p12) found in project | FAIL (none) |
| EV/standard public CA cert available | FAIL (none) |
| Self-signed cert viable for Smart App Control | NO (documented) |
| Signing blocker identified and documented | DOCUMENTED |

**DOCUMENTED — Phase 7 acceptance gate met (blocker identified, no resolution possible without external cert).**

---

## 6. Blocker summary

**The unsigned EXE cannot pass Smart App Control / Code Integrity without code signing.** This is the final blocker preventing the MaintiQ Windows release from launching on target machines with Smart App Control enabled.

### Required to resolve

1. **Obtain a code-signing certificate** from a public CA trusted by Microsoft (EV recommended for Smart App Control compatibility):
   - DigiCert, Sectigo, GlobalSign, Entrust, etc.
   - EV code-signing cert preferred (hardware token, most reliable with Smart App Control)
   - Standard OV cert may work but is less certain with Smart App Control

2. **Install signing tooling:**
   - Windows SDK `signtool.exe` (from Windows Kits)
   - Or use the CA's signing service/API

3. **Sign the release artifacts:**
   - `release/staging/onedir/MaintiQ/MaintiQ.exe` (the bootloader EXE)
   - All `.dll` and `.pyd` files in the bundle (Qt DLLs, python313.dll, sklearn/numpy/xgboost extensions)
   - Ideally sign with timestamping (`/tr http://timestamp.digicert.com`)

4. **Rebuild after signing** (if signing changes file hashes, re-verify the bundle)

5. **Re-validate launch** on a machine with Smart App Control enabled

---

## Recommended next step (Phase 8)

Code-signing implementation — sign the one-dir bundle artifacts with the obtained certificate using signtool, then re-validate the full bundle end-to-end on a Smart App Control-enabled machine. This requires the user to procure a code-signing certificate first (Phase 7 found none available on this system).
