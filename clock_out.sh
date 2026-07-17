#!/bin/bash

# 1. Safety Check: See if there are actually any changes to save
if [ -z "$(git status --porcelain)" ]; then
    echo "🟢 No changes detected. Your codebase is already synced with GitHub!"
    exit 0
fi

# 2. Handle the Commit Message
# If you type a message after the command (e.g., ./clock_out.sh "fixed button"), it uses that.
# Otherwise, it pauses and asks you to type one in the terminal.
if [ -n "$1" ]; then
    COMMIT_MSG="$1"
else
    echo -n "📝 What did you work on just now? (Press Enter to use default time-stamp): "
    read COMMIT_MSG
fi

# Fallback: If you just hit Enter without typing, it creates a timestamped message
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Routine clock-out save: $(date +'%Y-%m-%d %H:%M')"
fi

# 3. Execute the Git Sequence
echo "⏳ Staging files..."
git add .

echo "💾 Committing changes..."
git commit -m "$COMMIT_MSG"

echo "🚀 Pushing code to GitHub..."
git push origin main

echo "✅ Clock-out complete! Safe to close your laptop."
