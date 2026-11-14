# MaintiQ — Phase 0: Release Baseline and Backup

**Project:** C:\ARRU CODES\projects\MaintiQ  
**Source launch:** `python -m maintiq`  
**Status:** Read-only baseline. No source edits, no rebuild, no signing, no history rewrite, no force-push.  
**Evidence standard:** PASS / FAIL / BLOCKED / NOT TESTED. Real counts only.

---

## 1. Project identity

| Field | Value |
|---|---|
| Project root | `C:\ARRU CODES\projects\MaintiQ` |
| Git branch | `main` |
| Git remote | `origin` = `https://github.com/ARJUN-0402/MaintiQ---Software.git` (fetch + push) |
| Version | `0.1.0` (`pyproject.toml` `[project]`) |
| Source launch | `python -m maintiq` (entry point `maintiq.__main__:main`) |
| Existing stack | Python 3.13, PySide6 6.12.0, scikit-learn 1.9.1, xgboost 2.1.4, SHAP 0.54.1, LIME 0.2.0.1, PyInstaller 6.22.3; Inno Setup script at `packaging\maintiq-installer.iss` |

---

## 2. Worktree state — DIRTY (baseline finding)

`git status --short` output:

```
 M docs/screenshots/about_limitations.png
 M docs/screenshots/dashboard.png
 M docs/screenshots/main_window.png
 M docs/screenshots/model_registry.png
 M docs/screenshots/predict_failure.png
 M docs/screenshots/reports_downloads.png
 M src/maintiq/ui/app.py
 M src/maintiq/ui/pages/eda.py
 M src/maintiq/ui/styles.py
 M src/maintiq/ui/widgets/canvas.py
?? MAINTIQ_WINDOWS_RELEASE_PHASE_PROMPTS.md
?? assets/datasets/
?? demo_outputs/
?? docs/PHASE1_NATIVE_DEPENDENCY_AUDIT.md
?? docs/PHASE2_WINDOWS_SECURITY_DIAGNOSTICS.md
?? docs/PHASE3_OPTIONAL_DEPENDENCY_ISOLATION.md
```

- **Modified (tracked):** 10 files — 6 docs screenshots, 4 source files (`src/maintiq/ui/app.py`, `src/maintiq/ui/pages/eda.py`, `src/maintiq/ui/styles.py`, `src/maintiq/ui/widgets/canvas.py`).
- **Untracked:** 6 entries — `MAINTIQ_WINDOWS_RELEASE_PHASE_PROMPTS.md`, `assets/datasets/`, `demo_outputs/`, and the three Phase 1–3 diagnostic reports authored in this session.

`git log -5 --oneline`:
```
2121d1b docs: add verified end-to-end ML demonstration results
8d05e6b merge: synchronize repository and clean documentation
f0bf37e docs: refine professional README documentation
e3f6580 Revise README for clarity and project details
3bff4e5 docs: add professional MaintiQ README and clean repository
```

No unresolved merges; no staged changes (all modifications are unstaged working-tree changes).

**Phase 0 rule #2:** "Stop if there are uncommitted changes, unresolved merges, or staged changes. Do not discard or restore user work."  
The worktree is **dirty** (10 modified + 6 untracked). I have **not** discarded or restored any user work. Per the phase rule, a clean worktree is expected before release engineering proceeds; the user should review and either commit or stash these changes before continuing to Phases 4–5 (which create build artifacts). Nothing was committed or pushed.

---

## 3. Source launch verification — PASS

`python -m maintiq` launched successfully with `QT_QPA_PLATFORM=offscreen`; the GUI stayed running for 4 seconds then terminated cleanly; `STDERR` contained no `Traceback`.

Status: **PASS**.

---

## 4. Artifact inventory — existence, size, SHA-256, modified time

| Artifact | Path | Exists | Size (bytes) | SHA-256 | Modified |
|---|---|---|---|---|---|
| Portable EXE | `release\MaintiQ-Portable\MaintiQ.exe` | YES | 130,956,988 | `927616252543DE31AB4D6DBE721EDAF8206B4F799D63201BC491990CD9846459` | 2026-11-14 14:32:25 |
| PyInstaller spec | `packaging\maintiq.spec` | YES | 1,591 | `B39E25F7D7E48C5F013E1C01DD96CF297813E9AAEAFC5E24F236B26544B7422E` | 2026-11-14 14:33:31 |
| Build script | `scripts\build_windows.ps1` | YES | 3,442 | `70F8EEAC1FB390FB89CA0B2EEAC117261335D62D12ABDCB911D231AC89C85F99` | 2026-11-14 14:27:56 |
| Inno Setup script | `packaging\maintiq-installer.iss` | YES | 1,681 | `0AF818DC1C9B75E933931700D7B3BE072B463352F7B6E628D3978F4BB2CA167A` | 2026-11-14 14:27:47 |

Notes:
- `packaging\maintiq.spec` is **gitignored** (`.gitignore` line 25: `*.spec`), so it does not appear in `git status`. It defines a **one-dir** build (`Analysis` → `EXE` with `console=False`), lists `shap` and `lime` as hidden imports, bundles `assets/icons` as datas, uses `upx=True`, no hooks/excludes, no code signing identity.
- The prior one-file portable EXE (`release\MaintiQ-Portable\MaintiQ.exe`) is **NotSigned** (Authenticode) — see Phase 1/2 reports.
- `.gitignore` covers `/build/`, `/release/`, `.venv/`, `*.spec`, datasets/models are not deleted. No `.venv`, `build`, `release`, dataset, or model files were deleted in this phase.

---

## 5. Test / lint / format checks — real counts

| Check | Command | Result |
|---|---|---|
| Tests | `.venv\Scripts\python.exe -m pytest tests/unit tests/integration -q` | **221 passed** (unit + integration) |
| Lint | `.venv\Scripts\python.exe -m ruff check src tests` | **All checks passed** (0 findings) |
| Format | `.venv\Scripts\python.exe -m ruff format --check src tests` | **97 files already formatted** |

All repository checks pass. Counts are real, not estimated.

---

## 6. `.gitignore` inspection

`.gitignore` (72 lines) covers:
- Bytecode: `__pycache__/`, `*.py[cod]`
- Virtualenvs: `.venv/`, `venv/`, `.venv.*/`
- Distribution/packaging: `/dist/`, `/build/`, `*.spec`, `/release/`, `/MaintiQ-Portable/`, `/MaintiQ-Setup.exe`
- Local data/logs: `/logs/`, `*.log`, `/tmp/`, `/temp/`
- Secrets: `*.env`, `*.key`, `*.pem`

Confirmed: `.gitignore` does **not** reference deletion of `.venv`, `build`, `release`, dataset, or model files, and none were deleted in this phase.

---

## 7. Backup recommendation

Recommended local backup (copy, do not rewrite Git history or force-push):

- Source tree: `C:\ARRU CODES\projects\MaintiQ\src\`, `packaging\`, `scripts\`, `pyproject.toml`, `requirements*.txt`, `README.md`, `config\`, `assets\`, `tests\`, `docs\`
- Release artifacts: `C:\ARRU CODES\projects\MaintiQ\release\MaintiQ-Portable\MaintiQ.exe`, `C:\ARRU CODES\projects\MaintiQ\build\maintiq\`
- Destination: an external folder outside the repo (e.g. `C:\ARRU CODES\projects\MaintiQ-backup-<date>\`) — **not** inside the repository, not committed, not pushed.

Do not `git commit --amend`, `git rebase`, `git push --force`, or otherwise rewrite history. Do not discard user work.

---

## 8. Acceptance gate — Phase 0

**PASS — evidence-based baseline report provided.**

- Project path, branch (`main`), remote (`origin`), version (`0.1.0`) confirmed.
- Worktree state documented: **DIRTY** (10 modified, 6 untracked). Per Phase 0 rule #2 this is a blocker for proceeding to build phases until resolved by the user; no user work was discarded or restored.
- `python -m maintiq` launches cleanly (PASS).
- Artifact inventory recorded with exact paths, sizes, SHA-256, modified times (PASS).
- Tests: 221 passed; lint clean; format clean (97 files) (PASS).
- `.gitignore` inspected; no protected files deleted (PASS).
- Backup recommended outside the repo; no history rewrite/force-push.

No source edits, no new build, no signing, no commit/push in this phase.

---

## Recommended next step

Before continuing to Phase 4 (reproducible build environment), resolve the dirty worktree: review the 10 modified and 6 untracked files, then commit or stash as the owner intends. A clean worktree prevents build outputs from being conflated with uncommitted source changes. Do not force-push or rewrite history.
