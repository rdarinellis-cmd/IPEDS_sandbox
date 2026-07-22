#!/usr/bin/env zsh
# This script rebuilds the Python virtual environment using the local system python3
# to resolve "no base python" errors.

echo "🧹 Removing old virtual environment..."
rm -rf .venv

echo "⚙️ Creating new virtual environment..."
python3 -m venv .venv

echo "📦 Upgrading pip and installing dashboard dependencies..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo "✅ Environment rebuild complete!"
echo "You can now run the dashboard using: ./run_dashboard.sh"
