#!/usr/bin/env bash
# Installs CIC agent-specific Claude Code safety hooks.
# Usage: ./tools/install-claude-hooks.sh [agent-id]
# Default: agent-01
#
# Merges cic-hooks.json into the agent's settings.json.
# Replaces existing [CIC] hooks; preserves all other settings.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_FILE="$SCRIPT_DIR/cic-hooks.json"
AGENT_ID="${1:-agent-01}"
AGENT_DIR="$HOME/.claude-personal/agents/$AGENT_ID"
SETTINGS="$AGENT_DIR/settings.json"

[[ -f "$HOOKS_FILE" ]] || { echo "[ERROR] not found: $HOOKS_FILE"; exit 1; }
[[ -d "$AGENT_DIR" ]] || { echo "[ERROR] agent directory does not exist: $AGENT_DIR"; exit 1; }

echo "[*] installing CIC hooks for: $AGENT_ID"
echo "[*] target: $SETTINGS"

python3 - "$SETTINGS" "$HOOKS_FILE" << 'END_PYTHON'
import json, sys, os

settings_path = sys.argv[1]
hooks_path = sys.argv[2]

if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
    print("[*] loaded existing settings.json")
else:
    settings = {}
    print("[*] creating new settings.json")

with open(hooks_path) as f:
    cic_hooks = json.load(f)["hooks"]

if "hooks" not in settings:
    settings["hooks"] = {}

added = 0
for event, hook_list in cic_hooks.items():
    if event not in settings["hooks"]:
        settings["hooks"][event] = []
    # Remove existing CIC hooks (idempotent re-run)
    settings["hooks"][event] = [
        entry for entry in settings["hooks"][event]
        if not any(
            "[CIC]" in hook.get("command", "")
            for hook in entry.get("hooks", [])
        )
    ]
    settings["hooks"][event].extend(hook_list)
    added += len(hook_list)

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

total = sum(len(v) for v in settings["hooks"].values())
print(f"[OK] {added} CIC hooks installed ({total} total hooks in settings.json)")
END_PYTHON

echo ""
echo "[OK] done: $AGENT_DIR"
echo ""
echo "verify:"
echo "  jq '.hooks.PreToolUse | length' \"$SETTINGS\""
echo "  jq '[.hooks.PreToolUse[].hooks[].command | select(contains(\"[CIC]\"))] | length' \"$SETTINGS\""
