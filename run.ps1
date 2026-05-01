# Windows PowerShell run script for Inventory Management System

Write-Host "🚀 Starting Inventory Management System Server..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"

# Check if dependencies are installed
Write-Host "🔍 Verifying dependencies..." -ForegroundColor Yellow
$pythonPath = ".venv\Scripts\python.exe"
& $pythonPath -m pip show fastapi -q | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Installing dependencies..." -ForegroundColor Yellow
    & $pythonPath -m pip install -r requirements.txt
}

# Check if static directory exists and has index.html
if (-not (Test-Path "static/index.html")) {
    Write-Host "📁 Setting up static files..." -ForegroundColor Yellow
    if (-not (Test-Path "static")) {
        New-Item -ItemType Directory -Name "static" -Force | Out-Null
    }
    if (Test-Path "index.html") {
        Move-Item -Path "index.html" -Destination "static/index.html" -Force
    }
}

# Run the server
Write-Host "🎯 Starting FastAPI server..." -ForegroundColor Green
Write-Host "📡 Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📖 API docs at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

& $pythonPath main.py
