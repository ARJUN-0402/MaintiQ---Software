# -*- mode: python -*-

# PyInstaller spec for MaintiQ (Windows desktop executable).
#
# Build:
#   .\.venv\Scripts\pyinstaller packaging\maintiq.spec --noconfirm
#
# Output: release\MaintiQ-Portable\MaintiQ.exe (onedir) or
#         dist\MaintiQ.exe when overriding --distpath. See scripts\build_windows.ps1.

from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if not (ROOT / "pyproject.toml").exists():
    raise SystemExit("Run the build from the MaintiQ repository root (pyproject.toml not found).")

a = Analysis(
    [str(ROOT / "src" / "maintiq" / "__main__.py")],
    pathex=[str(SRC), str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "icons"), "assets/icons"),
    ],
    hiddenimports=[
        "maintiq",
        "maintiq.ml.explainability",
        "lime",
        "sklearn",
        "xgboost",
        "joblib",
        "pandas",
        "numpy",
        "matplotlib.backends.backend_qtagg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["sklearn.cluster", "shap"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    [],
    [],
    name="MaintiQ",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    exclude_binaries=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icons" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="MaintiQ",
)
