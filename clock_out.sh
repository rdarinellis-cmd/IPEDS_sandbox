#!/bin/bash

# 1. Check for uncommitted files AND unpushed commits
UNCOMMITTED=$(git status --porcelain)
UNPUSHED=$(git log origin/main..HEAD 2>/dev/null)

if [ -z "$UNCOMMITTED" ] && [ -z "$UNPUSHED" ]; then
    echo "🟢 No changes detected. Your codebase is already synced with GitHub!"
    exit 0
fi

# 2. Only commit if there are actually new file modifications
if [ -n "$UNCOMMITTED" ]; then
    if [ -n "$1" ]; then
        COMMIT_MSG="$1"
    else
        echo -n "📝 What did you work on just now? (Press Enter for timestamp): "
        read COMMIT_MSG
    fi

    if [ -z "$COMMIT_MSG" ]; then
        COMMIT_MSG="Routine clock-out save: $(date +'%Y-%m-%d %H:%M')"
    fi

    echo "⏳ Staging files..."
    git add .

    echo "💾 Committing changes..."
    git commit -m "$COMMIT_MSG"
fi

# 3. Always push if we made it this far
echo "🚀 Pushing code to GitHub..."
git push origin main

echo "✅ Clock-out complete! Safe to close your laptop."
