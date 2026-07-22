#!/usr/bin/env zsh

# Automatically navigate to the directory where this script is located
cd "$(dirname "$0")"

echo "🚀 Starting IPEDS Dashboard..."

# Run using python -m streamlit to bypass shell interpreter shebang resolution issues
./.venv/bin/python3 -m streamlit run app.py
