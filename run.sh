#!/bin/bash

# Set Python to use a centralized location for bytecode files
export PYTHONPYCACHEPREFIX=.pycache_central

# Run the application
echo "Starting server on http://0.0.0.0:8000"
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload