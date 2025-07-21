#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Create a virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
