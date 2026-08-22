#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
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

def commands(entry):
    return [h.get("command", "") for h in entry.get("hooks", [])]


# Everything this installer owns, by every spelling it has ever used. The
# original predicate looked only for the "[CIC]" marker, which the four
# script-invoking entries never carried -- they run tools/hooks/*.sh and
# log-event.py and have no message to mark. Those four were re-appended on every
# run, which is the whole of the 13 -> 17 growth.
#
# Matching the exact commands we are about to install is not enough on its own:
# it would leave behind entries from an older version of cic-hooks.json whose
# command text has since changed.
OURS = {c for hook_list in cic_hooks.values() for e in hook_list for c in commands(e)}


def is_ours(entry):
    for c in commands(entry):
        if "[CIC]" in c or "/tools/hooks/" in c or c in OURS:
            return True
    return False


added = removed = 0
for event, hook_list in cic_hooks.items():
    existing = settings["hooks"].get(event, [])
    kept = [e for e in existing if not is_ours(e)]
    removed += len(existing) - len(kept)
    settings["hooks"][event] = kept + hook_list
    added += len(hook_list)

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")

total = sum(len(v) for v in settings["hooks"].values())
print(f"[OK] {added} CIC hooks installed, {removed} previous ones replaced "
      f"({total} total hooks in settings.json)")
END_PYTHON

echo ""
echo "[OK] done: $AGENT_DIR"
echo ""
echo "verify:"
echo "  jq '.hooks.PreToolUse | length' \"$SETTINGS\""
echo "  jq '[.hooks.PreToolUse[].hooks[].command | select(contains(\"[CIC]\"))] | length' \"$SETTINGS\""
