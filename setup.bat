@echo off
title Abhijeet WS - Setup

cd /d "%~dp0"

echo ==========================================
echo       Abhijeet WS - First Time Setup
echo ==========================================
echo.

echo Checking Python...
python --version

if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3 and try again.
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo        SETUP COMPLETED SUCCESSFULLY
echo ==========================================
echo.
echo You can now run the application using:
echo.
echo     run_app.bat
echo.
pause