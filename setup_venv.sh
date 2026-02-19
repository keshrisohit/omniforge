#!/bin/bash

# Setup script for OmniForge development environment
# This script creates a virtual environment and installs dependencies

set -e  # Exit on error

echo "=========================================="
echo "OmniForge Development Environment Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if Python 3.9+ is installed
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    echo "❌ Error: Python 3.9+ is required"
    echo "   Current version: $python_version"
    exit 1
fi

echo "✅ Python version is compatible"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "⚠️  Virtual environment already exists at .venv"
    read -p "   Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Removing existing virtual environment..."
        rm -rf .venv
    else
        echo "   Keeping existing virtual environment"
        echo ""
        echo "To activate the existing environment, run:"
        echo "   source .venv/bin/activate"
        exit 0
    fi
fi

python3 -m venv .venv
echo "✅ Virtual environment created at .venv"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null
echo "✅ pip upgraded"
echo ""

# Install package in editable mode with dev dependencies
echo "Installing OmniForge with development dependencies..."
echo "(This may take a few minutes...)"
pip install -e ".[dev]" > /dev/null 2>&1
echo "✅ OmniForge installed in editable mode"
echo ""

# Verify installation
echo "Verifying installation..."
python -c "import omniforge; print(f'✅ omniforge package imported successfully')"
python -c "import pytest; print(f'✅ pytest available')"
python -c "import black; print(f'✅ black available')"
python -c "import ruff; print(f'✅ ruff available (via ruff-linter)')" 2>/dev/null || echo "⚠️  ruff not available (optional)"
echo ""

echo "=========================================="
echo "Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "To activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "   pytest"
echo ""
echo "To format code:"
echo "   black ."
echo ""
echo "To lint code:"
echo "   ruff check ."
echo ""
echo "To start the server:"
echo "   python examples/start_server.py"
echo ""
echo "VS Code Debug Configurations Available:"
echo "   - Python: Current File"
echo "   - Python: FastAPI Server"
echo "   - Python: Run Tests"
echo "   - Python: Chat Endpoint Example"
echo "   - And more..."
echo ""
echo "Press F5 in VS Code to see all debug configurations!"
echo ""
