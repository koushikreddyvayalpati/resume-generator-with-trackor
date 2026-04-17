param(
    [switch]$SkipLibreOfficeCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller

$portablePath = Join-Path $repoRoot "vendor\LibreOfficePortable\App\libreoffice\program\soffice.exe"
$programPath = Join-Path $repoRoot "vendor\libreoffice\program\soffice.exe"

if (-not $SkipLibreOfficeCheck -and -not (Test-Path $portablePath) -and -not (Test-Path $programPath)) {
    Write-Host ""
    Write-Host "LibreOffice is not bundled yet." -ForegroundColor Yellow
    Write-Host "Place LibreOffice Portable at:"
    Write-Host "  vendor\LibreOfficePortable\App\libreoffice\program\soffice.exe"
    Write-Host ""
    Write-Host "Or place a normal LibreOffice program folder at:"
    Write-Host "  vendor\libreoffice\program\soffice.exe"
    Write-Host ""
    Write-Host "Build anyway with -SkipLibreOfficeCheck if this machine has LibreOffice installed globally."
    exit 1
}

& .\.venv\Scripts\pyinstaller.exe --clean --noconfirm packaging\resume_tool_windows.spec

Write-Host ""
Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  dist\ResumeTool\ResumeTool.exe"
