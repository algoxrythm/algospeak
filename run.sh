#!/bin/bash
# run.sh - Helper script to run the STT Overlay with correct environment

# Ensure we are in the project directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please create it first:"
    echo "python3 -m venv .venv"
    exit 1
fi

# Activate venv
source .venv/bin/activate

# EXPLICITLY ADD CUDA LIBRARY PATHS
# This fixes the "Invalid handle" / "Cannot load symbol" errors
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/.venv/lib/python3.10/site-packages/nvidia/cudnn/lib
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/.venv/lib/python3.10/site-packages/nvidia/cublas/lib

# Run the application
echo "Starting STT Overlay..."
python main.py
