#!/usr/bin/env bash
# Job lifecycle wrapper — meta.yaml frissítés, agent futtatás, commit, push
# Használat: ./tools/run-job.sh <job-id> [agent-id]
set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
JOB_ID="${1:?Adj meg egy job-id-t, pl: map-private-source}"
AGENT_ID="${2:-agent-01}"

JOB_DIR="$WORKDIR/jobs/$JOB_ID"
META="$JOB_DIR/meta.yaml"
INPUT="$JOB_DIR/input.md"
OUTPUT_DIR="$JOB_DIR/output"
AGENT_CONFIG="$HOME/.claude-personal/agents/$AGENT_ID"

# --- Ellenőrzések ---
[[ -f "$META" ]]  || { echo "[ERROR] Nem létezik: $META"; exit 1; }
[[ -f "$INPUT" ]] || { echo "[ERROR] Nem létezik: $INPUT"; exit 1; }
[[ -d "$AGENT_CONFIG" ]] || { echo "[ERROR] Agent nem létezik: $AGENT_CONFIG"; exit 1; }

STATUS=$(grep '^status:' "$META" | awk -F'"' '{print $2}')
if [[ "$STATUS" == "running" ]]; then
    echo "[WARN] Job már fut. Folytatod? (y/N)"
    read -r ans; [[ "$ans" == "y" ]] || exit 1
fi
if [[ "$STATUS" == "done" ]]; then
    echo "[WARN] Job már kész. Újrafuttatod? (y/N)"
    read -r ans; [[ "$ans" == "y" ]] || exit 1
fi

mkdir -p "$OUTPUT_DIR"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- pending → running ---
echo "[*] $JOB_ID — running ($NOW)"
python3 - "$META" "$NOW" <<'EOF'
import sys, re

meta_path, now = sys.argv[1], sys.argv[2]
with open(meta_path) as f:
    content = f.read()
content = re.sub(r'^status:.*$', 'status: "running"', content, flags=re.MULTILINE)
content = re.sub(r'^  started:.*$', f'  started: "{now}"', content, flags=re.MULTILINE)
content = re.sub(r'^  completed:.*$', '  completed: ""', content, flags=re.MULTILINE)
with open(meta_path, "w") as f:
    f.write(content)
EOF

bash "$WORKDIR/tools/update-index.sh"
git -C "$WORKDIR" add "$META" jobs/index.yaml
git -C "$WORKDIR" commit -m "job: $JOB_ID — running"
git -C "$WORKDIR" push

# --- Agent futtatás ---
echo "[*] Agent indítása: $AGENT_ID"
PROMPT=$(cat "$INPUT")
set +e
CLAUDE_CONFIG_DIR="$AGENT_CONFIG" claude --print "$PROMPT" > "$OUTPUT_DIR/agent-output.md" 2>&1
EXIT_CODE=$?
set -e

END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- running → done/error ---
if [[ $EXIT_CODE -eq 0 ]]; then
    NEW_STATUS="done"
    echo "[✓] $JOB_ID — done ($END)"
else
    NEW_STATUS="error"
    echo "[!] $JOB_ID — error (exit $EXIT_CODE)"
fi

python3 - "$META" "$NEW_STATUS" "$END" <<'EOF'
import sys, re

meta_path, status, end = sys.argv[1], sys.argv[2], sys.argv[3]
with open(meta_path) as f:
    content = f.read()
content = re.sub(r'^status:.*$', f'status: "{status}"', content, flags=re.MULTILINE)
content = re.sub(r'^  completed:.*$', f'  completed: "{end}"', content, flags=re.MULTILINE)
with open(meta_path, "w") as f:
    f.write(content)
EOF

bash "$WORKDIR/tools/update-index.sh"
git -C "$WORKDIR" add "$JOB_DIR" jobs/index.yaml
git -C "$WORKDIR" commit -m "job: $JOB_ID — $NEW_STATUS"
git -C "$WORKDIR" push

echo "[*] Kész. Output: $OUTPUT_DIR/agent-output.md"
