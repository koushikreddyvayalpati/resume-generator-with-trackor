# Resume Generator - Windows Setup & Run (PowerShell)
# This script installs all dependencies and starts the app

Write-Host "`n04 Resume Generator - Setup & Run" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Yellow
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "+ Python $pythonVersion found" -ForegroundColor Green
} catch {
    Write-Host "X Python 3 is not installed. Please install Python 3.8 or higher from https://www.python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Get the script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommandPath
Set-Location $scriptDir

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "04 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "+ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "04 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "04 Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install requirements
Write-Host "04 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "+ All dependencies installed" -ForegroundColor Green

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "04 Creating .env file..." -ForegroundColor Yellow
    $defaultPath = "$env:USERPROFILE\Documents\tharun-resume"
    "OUTPUT_ROOT=$defaultPath" | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "+ .env file created" -ForegroundColor Green
}

Write-Host ""
Write-Host "0A Starting Resume Generator..." -ForegroundColor Yellow
Write-Host "0B Visit: http://127.0.0.1:5001" -ForegroundColor Cyan
Write-Host "0B Press Ctrl+C to stop the server" -ForegroundColor Cyan
Write-Host ""

# Run the app
python app.py

Read-Host "Press Enter to exit"
