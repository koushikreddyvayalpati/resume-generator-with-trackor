@echo off
REM Resume Generator - Windows Setup & Run
REM This script installs all dependencies and starts the app

echo.
echo 04 Resume Generator - Setup ^& Run
echo ==================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python 3 is not installed. Please install Python 3.8 or higher from https://www.python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo + Python %PYTHON_VERSION% found

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 04 Creating virtual environment...
    python -m venv venv
    echo + Virtual environment created
)

REM Activate virtual environment
echo 04 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo 04 Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install requirements
echo 04 Installing dependencies...
pip install -r requirements.txt --quiet
echo + All dependencies installed

REM Check for .env file
if not exist ".env" (
    echo 04 Creating .env file...
    (
        echo OUTPUT_ROOT=resumes
    ) > .env
    echo + .env file created
)

echo.
echo 0A Starting Resume Generator...
echo 0B Visit: http://127.0.0.1:5001
echo 0B Press Ctrl+C to stop the server
echo.

REM Run the app
python app.py

pause
