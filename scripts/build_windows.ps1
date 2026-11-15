# MaintiQ Windows packaging script.
#
# Builds the standalone executable with PyInstaller and, when Inno Setup is
# available, the MaintiQ-Setup.exe installer.
#
# Usage (from the repository root, with the MaintiQ virtualenv activated):
#   .\scripts\build_windows.ps1
#
# Outputs:
#   release\MaintiQ-Portable\MaintiQ\MaintiQ.exe        (one-folder portable executable)
#   release\MaintiQ-Setup.exe                    (Inno Setup installer, if iscc is installed)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$spec = Join-Path $root "packaging\maintiq.spec"
$portableDir = Join-Path $root "release\MaintiQ-Portable"
$setupExe = Join-Path $root "release\MaintiQ-Setup.exe"
$issScript = Join-Path $root "packaging\maintiq-installer.iss"

# Resolve the Python interpreter: prefer the active virtualenv, fall back to `python`.
$pythonExe = "python"
if (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) {
    $pythonExe = Join-Path $root ".venv\Scripts\python.exe"
}

Write-Host "MaintiQ build script" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor Gray
Write-Host "Python: $pythonExe" -ForegroundColor Gray

# Ensure PyInstaller is available.
Write-Host "`nChecking PyInstaller..." -ForegroundColor Cyan
$req = Join-Path $root "requirements-packaging.txt"
& $pythonExe -m pip install --quiet -r $req
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install packaging dependencies from $req"
}
& $pythonExe -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller is not installed; run: pip install -r requirements-packaging.txt"
}

# Clean previous build outputs.
Write-Host "`nCleaning previous build outputs..." -ForegroundColor Cyan
foreach ($dir in @("build", $portableDir)) {
    $path = Join-Path $root $dir
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path | Out-Null
        Write-Host "Removed $path" -ForegroundColor Gray
    }
}

# Build the one-folder portable executable.
Write-Host "`nBuilding MaintiQ.exe with PyInstaller..." -ForegroundColor Cyan
& $pythonExe -m PyInstaller $spec --noconfirm --distpath $portableDir --workpath (Join-Path $root "build")
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed"
}

$exe = Join-Path $portableDir "MaintiQ\MaintiQ.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Expected executable not found: $exe"
}
Write-Host "Portable executable built: $exe" -ForegroundColor Green

# Build the Inno Setup installer when the compiler is available.
Write-Host "`nChecking for Inno Setup compiler (iscc)..." -ForegroundColor Cyan
$isccPaths = @(
    (Get-Command iscc -ErrorAction SilentlyContinue).Source,
    Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe",
    Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe",
    Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
)
$iscc = $null
foreach ($path in $isccPaths) {
    if ($path -and (Test-Path $path)) {
        $iscc = $path
        Write-Host "Found ISCC at: $path" -ForegroundColor Gray
        break
    }
}
if ($iscc) {
    Set-Location $root
    & $iscc $issScript
    if ($LASTEXITCODE -eq 0 -and (Test-Path $setupExe)) {
        Write-Host "Installer built: $setupExe" -ForegroundColor Green
    } else {
        Write-Error "Inno Setup compilation failed or did not produce $setupExe"
    }
} else {
    Write-Host "Inno Setup not found; skipping installer." -ForegroundColor Yellow
    Write-Host "Install Inno Setup (https://jrsoftware.org/isinfo.php) and re-run to build MaintiQ-Setup.exe" -ForegroundColor Yellow
}

Write-Host "`nBuild complete." -ForegroundColor Cyan
Write-Host "Portable: $portableDir\MaintiQ\MaintiQ.exe" -ForegroundColor Gray
if (Test-Path $setupExe) { Write-Host "Installer: $setupExe" -ForegroundColor Gray }
