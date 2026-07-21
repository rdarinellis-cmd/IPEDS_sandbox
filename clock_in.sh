#!/bin/bash

echo "📡 Pulling latest code and data from GitHub..."
git pull origin main

echo "🐍 Checking Python virtual environment..."
# If the .venv folder doesn't exist on this machine, create it
if [ ! -d ".venv" ]; then
    echo "Creating new virtual environment for this machine..."
    python3 -m venv .venv
fi

echo "📦 Syncing project dependencies..."
# Use the direct binary path to avoid activation errors
.venv/bin/pip install -r requirements.txt --quiet

echo "🟢 Clock-in complete! Your codebase and Python environment are ready."
