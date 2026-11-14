# MaintiQ build environment setup script.
#
# Creates and provisions an isolated .venv-build directory without touching
# the existing .venv development environment. Pins all dependency versions
# to the tested lock file for reproducibility.
#
# Usage (from the repository root, in PowerShell):
#   .\scripts\setup_build_env.ps1
#
# Outputs:
#   .venv-build/             isolated build environment
#   requirements-build.lock  pinned package versions

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvBuild = Join-Path $root ".venv-build"
$pythonExe = "python"
$lockFile = Join-Path $root "requirements-build.lock"
$runtimePinned = Join-Path $root "requirements-runtime-standard-pinned.txt"
$devPinned = Join-Path $root "requirements-dev-pinned.txt"
$packagingPinned = Join-Path $root "requirements-packaging-pinned.txt"

Write-Host "MaintiQ build environment setup" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor Gray

# ---------------------------------------------------------------------------
# Prerequisites: confirm Python is available
# ---------------------------------------------------------------------------
Write-Host "`nChecking Python interpreter..." -ForegroundColor Cyan
try {
    $pyVersion = & $pythonExe --version 2>&1
    Write-Host "Python: $pyVersion" -ForegroundColor Gray
} catch {
    Write-Error "Python interpreter not found on PATH. Install Python 3.10+ and re-run."
}

# ---------------------------------------------------------------------------
# Step 1: Create isolated build environment (do not overwrite .venv)
# ---------------------------------------------------------------------------
if (Test-Path $venvBuild) {
    Write-Host "`nBuild environment .venv-build already exists. Skipping creation." -ForegroundColor Yellow
} else {
    Write-Host "`nCreating isolated build environment .venv-build..." -ForegroundColor Cyan
    & $pythonExe -m venv $venvBuild
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create .venv-build"
    }
    Write-Host "Created .venv-build" -ForegroundColor Green
}

$venvPython = Join-Path $venvBuild "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Expected Python executable not found in .venv-build: $venvPython"
}

# ---------------------------------------------------------------------------
# Step 2: Upgrade pip in the build environment
# ---------------------------------------------------------------------------
Write-Host "`nUpgrading pip in .venv-build..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to upgrade pip in .venv-build"
}

# ---------------------------------------------------------------------------
# Step 3: Install pinned dependencies
# Order: runtime -> dev -> packaging. Fail closed if any file is missing.
# ---------------------------------------------------------------------------
foreach ($reqFile in @($runtimePinned, $devPinned, $packagingPinned)) {
    if (-not (Test-Path $reqFile)) {
        Write-Error "Required pinned requirements file not found: $reqFile"
    }
}

# Helper: run pip install and fail only on non-zero exit code (ignore stderr warnings).
function Invoke-PipInstall {
    param([string]$RequiresFile, [switch]$Editable, [string]$Path)
    $ErrorActionPreferenceOld = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if ($Editable) {
        & $venvPython -m pip install -e "$Path"
    } else {
        & $venvPython -m pip install -r "$RequiresFile"
    }
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $ErrorActionPreferenceOld
    if ($exitCode -ne 0) {
        Write-Error "pip install failed with exit code $exitCode"
    }
}

Write-Host "`nInstalling standard-release runtime dependencies (no SHAP)..." -ForegroundColor Cyan
Invoke-PipInstall -RequiresFile $runtimePinned

Write-Host "Installing development dependencies..." -ForegroundColor Cyan
Invoke-PipInstall -RequiresFile $devPinned

Write-Host "Installing packaging dependencies..." -ForegroundColor Cyan
Invoke-PipInstall -RequiresFile $packagingPinned

# ---------------------------------------------------------------------------
# Step 4: Install MaintiQ itself in editable mode for testing
# ---------------------------------------------------------------------------
Write-Host "`nInstalling MaintiQ (editable) into .venv-build..." -ForegroundColor Cyan
Invoke-PipInstall -Editable -Path $root

# ---------------------------------------------------------------------------
# Step 5: Verify installation
# ---------------------------------------------------------------------------
Write-Host "`nVerifying installed packages..." -ForegroundColor Cyan
$expected = @("pandas", "numpy", "scikit-learn", "xgboost", "lime", "matplotlib", "PySide6", "joblib", "PyInstaller", "pytest", "ruff")
$missing = @()
foreach ($pkg in $expected) {
    $ErrorActionPreference = "Continue"
    $found = & $venvPython -c "import importlib.metadata as m; print(m.version('$pkg'))" 2>$null
    $ErrorActionPreference = "Stop"
    if (-not $found) {
        $missing += $pkg
        Write-Host "  MISSING: $pkg" -ForegroundColor Red
    } else {
        Write-Host "  OK: $pkg == $found" -ForegroundColor Gray
    }
}
if ($missing.Count -gt 0) {
    Write-Error "Missing packages in .venv-build: $($missing -join ', ')"
}

# ---------------------------------------------------------------------------
# Step 6: Verify source startup (SHAP must not be imported at startup)
# ---------------------------------------------------------------------------
Write-Host "`nVerifying source startup (SHAP/cluster not imported at startup)..." -ForegroundColor Cyan
$startupCheck = @"
import builtins, sys
real_import = builtins.__import__
def guarded(name, *a, **k):
    if name == 'shap' or name.startswith('shap.'):
        raise ImportError('shap blocked for startup check')
    return real_import(name, *a, **k)
builtins.__import__ = guarded
for mod in list(sys.modules):
    if mod == 'shap' or mod.startswith('shap.') or 'sklearn.cluster' in mod:
        del sys.modules[mod]
import maintiq, maintiq.ui.app
cluster = any('sklearn.cluster' in m for m in sys.modules)
shap_loaded = any(m == 'shap' or m.startswith('shap.') for m in sys.modules)
assert not cluster, 'sklearn.cluster must not be imported at startup'
assert not shap_loaded, 'shap must not be imported at startup'
print('STARTUP OK:', maintiq.__title__)
"@
$ErrorActionPreference = "Continue"
$startupResult = & $venvPython -c $startupCheck 2>&1
$startupExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($startupExitCode -ne 0) {
    Write-Error "Source startup verification failed`n$startupResult"
}
Write-Host $startupResult -ForegroundColor Green

# ---------------------------------------------------------------------------
# Complete
# ---------------------------------------------------------------------------
Write-Host "`nBuild environment setup complete." -ForegroundColor Green
Write-Host "Environment: $venvBuild" -ForegroundColor Gray
Write-Host "Python:      $venvPython" -ForegroundColor Gray
Write-Host "Lock file:   $lockFile" -ForegroundColor Gray
Write-Host "`nNext steps:" -ForegroundColor Gray
Write-Host "  Activate:   .venv-build\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  Run tests:  .venv-build\Scripts\python.exe -m pytest tests/unit tests/integration" -ForegroundColor Gray
Write-Host "  Build:      .\scripts\build_windows.ps1" -ForegroundColor Gray
