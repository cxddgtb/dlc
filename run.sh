#!/bin/bash
# Quick start script for Linux/Mac

echo "========================================"
echo "CXDDZY-Pro v2.0 - Quick Start"
echo "========================================"
echo

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found! Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[INFO] Python version: $PYTHON_VERSION"

# Install dependencies
echo "[1/3] Installing dependencies..."
pip3 install -r requirements.txt -q

# Run fetcher
echo "[2/3] Starting node fetcher..."
echo
python3 main.py

echo
echo "[3/3] Done! Check output/ directory for results."
