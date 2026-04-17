param(
    [string]$SofficePath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11+ from python.org and enable 'Add python.exe to PATH'."
}

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if ($SofficePath) {
    if (-not (Test-Path $SofficePath)) {
        throw "SOFFICE_PATH does not exist: $SofficePath"
    }
    $env:SOFFICE_PATH = $SofficePath
}

$env:RESUME_DESKTOP_MODE = "1"
& .\.venv\Scripts\python.exe desktop_app.py
