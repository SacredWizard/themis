#!/usr/bin/env bash
set -euo pipefail

# Themis Plugin Uninstaller
# Removes Themis skills and agents from Claude Code

SCOPE="${1:-project}"

if [[ "$SCOPE" == "user" ]]; then
    TARGET_DIR="$HOME/.claude"
elif [[ "$SCOPE" == "project" ]]; then
    TARGET_DIR="$(pwd)/.claude"
else
    echo "Usage: ./uninstall.sh [project|user]"
    exit 1
fi

echo "Uninstalling Themis from $TARGET_DIR..."

removed=0
for item in "$TARGET_DIR"/skills/themis-* "$TARGET_DIR"/agents/themis-*.md; do
    if [[ -L "$item" ]]; then
        rm "$item"
        echo "  Removed $(basename "$item")"
        ((removed++))
    fi
done

if [[ $removed -eq 0 ]]; then
    echo "  No Themis symlinks found."
else
    echo "Removed $removed items. Themis uninstalled."
fi
