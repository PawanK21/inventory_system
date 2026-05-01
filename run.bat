@echo off
REM Inventory Management System - Run Script for Windows Command Prompt

echo.
echo ========================================
echo Inventory Management System
echo ========================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check dependencies
echo Checking dependencies...
python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
)

REM Create static directory if needed
if not exist "static" (
    mkdir static
)

REM Move index.html if needed
if exist "index.html" (
    if not exist "static\index.html" (
        move index.html static\index.html
    )
)

echo.
echo Starting FastAPI Server...
echo.
echo Server will be available at: http://localhost:8000
echo API Documentation at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server.
echo.

python main.py
pause
