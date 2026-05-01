# Windows PowerShell setup script for Inventory Management System

Write-Host "🚀 Setting up Inventory Management System..." -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    python --version | Out-Null
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "🐍 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel -q

# Install dependencies from requirements.txt
Write-Host "📥 Installing dependencies from requirements.txt..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies installed" -ForegroundColor Green

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

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the server:" -ForegroundColor Cyan
Write-Host "  PowerShell: .\run.ps1" -ForegroundColor White
Write-Host "  Command Prompt: run.bat" -ForegroundColor White
Write-Host "  Direct: .venv\Scripts\python.exe main.py" -ForegroundColor White
Write-Host ""
Write-Host "Then open your browser to: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
