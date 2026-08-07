#!/bin/sh
#
# Initializes the repository by setting up the necessary Git hooks.
# This script is intended to be run once after cloning the template.

set -e

# Find the git repository root
GIT_DIR=$(git rev-parse --git-dir)
if [ -z "$GIT_DIR" ]; then
    echo "[ERROR] Not a git repository. Cannot set up hooks."
    exit 1
fi

HOOKS_DIR="$GIT_DIR/hooks"
TOOLS_DIR=$(git rev-parse --show-toplevel)/tools

echo "--- Initializing Git hooks ---"

# Capture the current PATH from the environment where init-hooks.sh is executed
CURRENT_PATH="$PATH"

# Set up pre-commit hook for validation
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"
if [ -f "$PRE_COMMIT_HOOK" ]; then
    echo "[INFO] A pre-commit hook already exists. Backing it up to pre-commit.bak."
    mv "$PRE_COMMIT_HOOK" "$PRE_COMMIT_HOOK.bak"
fi
echo "  ✓ Done."

# Set up commit-msg hook for signing
COMMIT_MSG_HOOK="$HOOKS_DIR/commit-msg"
if [ -f "$COMMIT_MSG_HOOK" ]; then
    echo "[INFO] A commit-msg hook already exists. Backing it up to commit-msg.bak."
    mv "$COMMIT_MSG_HOOK" "$COMMIT_MSG_HOOK.bak"
fi
echo "[*] Symlinking commit-msg hook from tools directory..."
ln -s -f "../../tools/git_hook_commit-msg.sh" "$COMMIT_MSG_HOOK"
echo "  ✓ Done."

echo "\nRepository initialization complete. Hooks are set up."
