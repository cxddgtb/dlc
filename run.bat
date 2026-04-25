@echo off
REM Quick start script for Windows
echo ========================================
echo CXDDZY-Pro v2.0 - Quick Start
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/3] Starting node fetcher...
echo.
python main.py

echo.
echo [3/3] Done! Check output/ directory for results.
pause
