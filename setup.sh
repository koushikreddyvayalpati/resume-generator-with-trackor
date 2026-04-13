#!/bin/bash

# Resume Generator - One-Command Setup & Run
# This script installs all dependencies and starts the app

set -e  # Exit on error

echo "📄 Resume Generator - Setup & Run"
echo "=================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION found"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📥 Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
echo "📚 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ All dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "📋 Creating .env file from template..."
    cp .env.example .env 2>/dev/null || echo "OUTPUT_ROOT=resumes" > .env
    echo "✅ .env file created"
fi

echo ""
echo "🚀 Starting Resume Generator..."
echo "📱 Visit: http://127.0.0.1:5001"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

# Run the app
python3 app.py
