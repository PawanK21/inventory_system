# Windows PowerShell run script for Inventory Management System

Write-Host "🚀 Starting Inventory Management System Server..." -ForegroundColor Cyan
Write-Host ""

# Check if dependencies are installed
Write-Host "🔍 Checking dependencies..." -ForegroundColor Yellow
try {
    python -m pip show fastapi -q | Out-Null
} catch {
    Write-Host "⚠️  Installing dependencies..." -ForegroundColor Yellow
    python -m pip install -q fastapi uvicorn[standard] pydantic python-multipart starlette typing-extensions
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
Write-Host ""

python main.py
