#!/bin/bash
# JARVIS Python 3.12 Activation Script
# This script activates the Python 3.12 virtual environment and runs JARVIS

cd "$(dirname "$0")"

# Activate Python 3.12 virtual environment
source .venv/bin/activate

# Check if activation was successful
if [ $? -eq 0 ]; then
    echo "✓ Python 3.12 environment activated"
    python3 --version
    
    # Run JARVIS UI
    jarvis ui
else
    echo "✗ Failed to activate virtual environment"
    echo "Run: source .venv/bin/activate"
    exit 1
fi
