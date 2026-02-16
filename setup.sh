#!/bin/bash

echo "🚀 Setting up Inventory Management System..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create static directory
echo "📁 Creating static directory..."
mkdir -p static

# Move frontend file
echo "🎨 Setting up frontend..."
mv index.html static/

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run the server: python main.py"
echo "  3. Open browser: http://localhost:8000"
echo ""
