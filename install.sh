#!/usr/bin/env bash
set -euo pipefail

# Themis Plugin Installer
# Installs the Themis AI Judge Council plugin for Claude Code

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCOPE="${1:-project}"

usage() {
    echo "Usage: ./install.sh [scope]"
    echo ""
    echo "Scopes:"
    echo "  project  (default) Install into current project's .claude/ directory"
    echo "  user               Install globally into ~/.claude/"
    echo ""
    echo "Examples:"
    echo "  cd /path/to/your/project && /path/to/themis/install.sh"
    echo "  ./install.sh user"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

# Determine target directory
if [[ "$SCOPE" == "user" ]]; then
    TARGET_DIR="$HOME/.claude"
    echo "Installing Themis plugin globally (~/.claude/)"
elif [[ "$SCOPE" == "project" ]]; then
    TARGET_DIR="$(pwd)/.claude"
    echo "Installing Themis plugin into project ($(pwd)/.claude/)"
else
    echo "Error: Unknown scope '$SCOPE'. Use 'project' or 'user'."
    usage
    exit 1
fi

# Create directories
mkdir -p "$TARGET_DIR/skills"
mkdir -p "$TARGET_DIR/agents"

# Symlink skills
echo "  Linking skills..."
for skill_dir in "$SCRIPT_DIR"/skills/themis-*/; do
    skill_name=$(basename "$skill_dir")
    target="$TARGET_DIR/skills/$skill_name"
    if [[ -L "$target" ]]; then
        rm "$target"
    elif [[ -d "$target" ]]; then
        echo "    Warning: $target exists and is not a symlink, skipping"
        continue
    fi
    ln -s "$skill_dir" "$target"
    echo "    $skill_name -> linked"
done

# Symlink agents
echo "  Linking agents..."
for agent_file in "$SCRIPT_DIR"/agents/themis-*.md; do
    agent_name=$(basename "$agent_file")
    target="$TARGET_DIR/agents/$agent_name"
    if [[ -L "$target" ]]; then
        rm "$target"
    elif [[ -f "$target" ]]; then
        echo "    Warning: $target exists and is not a symlink, skipping"
        continue
    fi
    ln -s "$agent_file" "$target"
    echo "    $agent_name -> linked"
done

# Check Python dependencies
echo ""
echo "Checking dependencies..."
if python3 "$SCRIPT_DIR/scripts/check_dependencies.py"; then
    echo ""
    echo "Themis installed successfully!"
else
    echo ""
    echo "Themis installed, but some dependencies are missing (see above)."
    echo "Install them before running evaluations."
fi

echo ""
echo "Usage:"
echo "  In Claude Code, type: /themis-evaluate path/to/video.mp4"
echo ""
echo "To uninstall, run: $SCRIPT_DIR/uninstall.sh $SCOPE"
