param(
    [switch]$InstallPyInstaller,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"

$PythonCommand = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
} else {
    throw "Python was not found. Install Python 3 first, then run this script again."
}

if ($InstallPyInstaller) {
    & $PythonCommand -m pip install --upgrade pyinstaller
}

function Build-GhostLockExe {
    param(
        [string]$Name
    )

    $IconArgs = @()
    if (Test-Path "assets\ghostlock.ico") {
        $IconArgs = @("--icon", "assets\ghostlock.ico")
    }

    $VersionArgs = @()
    if (Test-Path "assets\version_info.txt") {
        $VersionArgs = @("--version-file", "assets\version_info.txt")
    }

    $DataArgs = @()
    if (Test-Path "assets\ghostlock.png") {
        $DataArgs += @("--add-data", "assets\ghostlock.png;assets")
    }
    if (Test-Path "assets\ghostlock.ico") {
        $DataArgs += @("--add-data", "assets\ghostlock.ico;assets")
    }

    & $PythonCommand -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name $Name `
        @IconArgs `
        @VersionArgs `
        @DataArgs `
        ghostlock.py

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed while building $Name with exit code $LASTEXITCODE. If an exe with that name is running, close it before rebuilding."
    }
}

if (-not $SetupOnly) {
    Build-GhostLockExe -Name "GhostLock"
}

Build-GhostLockExe -Name "Setup"

Write-Host ""
Write-Host "Build complete."
if (-not $SetupOnly) {
    Write-Host "App:   dist\GhostLock.exe"
}
Write-Host "Setup: dist\Setup.exe"
