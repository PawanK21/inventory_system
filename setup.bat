@echo off
REM Inventory Management System - Setup Script for Windows Command Prompt

echo.
echo ========================================
echo Inventory Management System Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel -q

REM Install dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo Dependencies installed successfully

REM Create static directory
if not exist "static" (
    echo Creating static directory...
    mkdir static
)

REM Move index.html if it exists
if exist "index.html" (
    if not exist "static\index.html" (
        echo Moving index.html to static folder...
        move index.html static\index.html
    )
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the server, run:
echo   run.bat (recommended)
echo   or
echo   .venv\Scripts\python.exe main.py
echo.
echo Then open your browser to:
echo   http://localhost:8000
echo.
pause
