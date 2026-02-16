# Windows PowerShell setup script for Inventory Management System

Write-Host "🚀 Setting up Inventory Management System..." -ForegroundColor Cyan

# Check if Python is installed
try {
    python --version | Out-Null
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Install dependencies globally
Write-Host "📥 Installing dependencies..." -ForegroundColor Yellow
python -m pip install -q fastapi uvicorn[standard] pydantic python-multipart starlette typing-extensions

# Create static directory (if not exists)
Write-Host "📁 Creating static directory..." -ForegroundColor Yellow
if (-not (Test-Path "static")) {
    New-Item -ItemType Directory -Name "static" -Force | Out-Null
}

# Check if index.html exists and move it if needed
if (Test-Path "index.html" -and -not (Test-Path "static/index.html")) {
    Write-Host "🎨 Setting up frontend..." -ForegroundColor Yellow
    Move-Item -Path "index.html" -Destination "static/index.html" -Force
}

Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server:" -ForegroundColor Cyan
Write-Host "  Run: python main.py" -ForegroundColor White
Write-Host "  Open browser: http://localhost:8000" -ForegroundColor White
Write-Host ""
