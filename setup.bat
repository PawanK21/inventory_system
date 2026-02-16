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

echo Installing dependencies...
python -m pip install -q fastapi uvicorn[standard] pydantic python-multipart starlette typing-extensions

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

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
echo   python main.py
echo.
echo Then open your browser to:
echo   http://localhost:8000
echo.
pause
