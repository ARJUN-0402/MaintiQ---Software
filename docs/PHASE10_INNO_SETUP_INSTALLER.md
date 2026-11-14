# MaintiQ — Phase 10: Inno Setup Installer Build (BLOCKED)

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** BLOCKED — `ISCC.exe` (Inno Setup compiler) is not installed on this system.  
**Evidence standard:** PASS / FAIL / BLOCKED / DOCUMENTED. No invented results.

---

## 1. Blocker statement

Inno Setup compiler (`ISCC.exe`) is not available on this system. Searched standard locations:

| Path | Found? |
|---|---|
| `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` | NO |
| `C:\Program Files\Inno Setup 6\ISCC.exe` | NO |
| `C:\Program Files (x86)\Inno Setup 5\ISCC.exe` | NO |
| `C:\Program Files\Inno Setup 5\ISCC.exe` | NO |
| `iscc` on PATH | NO |

Per Phase 10 rule #2: "Detect ISCC.exe and record Inno Setup version. Do not assume it is installed." — confirmed NOT installed.

**Blocker: Inno Setup not installed.** User must install Inno Setup 6+ from https://jrsoftware.org/isinfo.php before Phase 10 can compile the installer.

---

## 2. Installer script inspection

File: `packaging\maintiq-installer.iss` (56 lines)

### Current configuration

| Setting | Value | Notes |
|---|---|---|
| AppName | MaintiQ | |
| AppVersion | 0.2.0 | Updated in `packaging\maintiq-installer.iss` for v0.2.0; installer remains uncompiled (Inno Setup not installed — see blocker in Section 1). |
| AppPublisher | MaintiQ Project | |
| AppPublisherURL | https://github.com/MaintiQ/MaintiQ | |
| DefaultDirName | `{pf}\MaintiQ` | Program Files (protected location) |
| PrivilegesRequired | admin | Requires admin rights |
| Compression | lzma | |
| SolidCompression | yes | |
| OutputDir | release | |
| OutputBaseFilename | MaintiQ-Setup | |
| SetupIconFile | assets\icons\app.ico | |
| Source files | `release\MaintiQ-Portable\*` | **REFERENCES OLD PATH** |

### Issues identified

| Issue | Location | Severity | Recommendation |
|---|---|---|---|
| Source path points to old portable | Line 39: `Source: "release\MaintiQ-Portable\*"` | HIGH | Update to point to verified bundle (`release/staging/onedir/MaintiQ/` or `release/staging/onefile/MaintiQ.exe`) |
| Installs to Program Files | Line 19: `DefaultDirName={pf}\...` | MEDIUM | Protected location; requires admin; consider `{localappdata}\MaintiQ` |
| Requires admin privileges | Line 23: `PrivilegesRequired=admin` | MEDIUM | Consider user-level install to avoid admin requirement |
| Uninstall deletes all app data | Line 50: `Type: filesanddirs; Name="{app}"` | HIGH | Could delete user data (models, registry, logs, settings). User data removal must be explicit/opt-in per Phase 10 rule #7 |
| No user-data directories created | `[Code] InitializeSetup` returns True unconditionally | MEDIUM | Should create per-user data dirs (%LOCALAPPDATA%\MaintiQ) |
| Installer not signed | N/A | HIGH | Unsigned installer will be blocked by Smart App Control (Phase 7-8 blocker) |

---

## 3. Bundle selection for installer

Two verified bundles exist:

| Bundle | Path | Status |
|---|---|---|
| onedir | `release/staging/onedir/MaintiQ/` | 2,169 files, verified structure |
| one-file | `release/staging/onefile/MaintiQ.exe` | 130.8 MB, single file |

Per Phase 9 recommendation, the **onedir** bundle is the preferred primary distribution. The installer source should be updated to `release/staging/onedir/MaintiQ\*` (or the one-file variant if that's the chosen delivery format).

---

## 4. Acceptance gate — Phase 10

| Criterion | Status |
|---|---|
| ISCC.exe detected | BLOCKED (not installed) |
| Installer script inspected | DOCUMENTED |
| Installer script issues identified | DOCUMENTED |
| Bundle selection documented | DOCUMENTED |

**BLOCKED — Phase 10 cannot execute without Inno Setup.** The installer script requires review and updates before compilation:

1. Install Inno Setup 6+
2. Update `Source:` path to point to the verified onedir (or one-file) bundle
3. Review install location (`{pf}` vs user data dir)
4. Review `PrivilegesRequired=admin`
5. Fix `[UninstallDelete]` to not delete user data
6. Add user-data directory creation
7. Compile installer
8. Sign installer (Phase 8 workflow)
9. Test install/launch/uninstall in clean environment

No installer was compiled, no files were modified, nothing was committed or pushed.
