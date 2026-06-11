#!/usr/bin/env bash
# Job lifecycle wrapper
# Használat: ./tools/run-job.sh <job-id> [agent-id]
#
# Job struktúra:
#   jobs/<job-id>/
#     input.md              ← orchestrátor definiálja
#     meta.yaml             ← lifecycle tracking
#     ref/                  ← referencia anyagok (opcionális, git-tracked)
#     workspace/            ← gitignored; agent klónjai élnek itt
#       cic-factory/        ← git clone, feature/<job-id> branch
#       <egyéb repo>/       ← ha a job más repót is igényel
set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"

# Lokális path konfig betöltése (gitignored)
[[ -f "$WORKDIR/tools/env.sh" ]] && source "$WORKDIR/tools/env.sh"

# MCP config: explicit env var, vagy a cic-factory szülőkönyvtárából derive-olva
CIC_MCP_CONFIG="${CIC_MCP_CONFIG:-$(dirname "$WORKDIR")/.mcp.json}"

JOB_ID="${1:?Adj meg egy job-id-t, pl: poc-implementation-plan}"
AGENT_ID="${2:-agent-01}"

JOB_DIR="$WORKDIR/jobs/$JOB_ID"
META="$JOB_DIR/meta.yaml"
INPUT="$JOB_DIR/input.md"
WORKSPACE="$JOB_DIR/workspace"
FACTORY_CLONE="$WORKSPACE/cic-factory"
FACTORY_REMOTE="git@github.com:CentralInfraCore/cic-factory.git"
FEATURE_BRANCH="feature/$JOB_ID"
AGENT_CONFIG="$HOME/.claude-personal/agents/$AGENT_ID"

# --- Ellenőrzések ---
[[ -f "$META" ]]  || { echo "[ERROR] Nem létezik: $META"; exit 1; }
[[ -f "$INPUT" ]] || { echo "[ERROR] Nem létezik: $INPUT"; exit 1; }
[[ -d "$AGENT_CONFIG" ]] || { echo "[ERROR] Agent nem létezik: $AGENT_CONFIG"; exit 1; }

STATUS=$(grep '^status:' "$META" | awk -F'"' '{print $2}')
MODEL=$(grep '^  model:' "$META" | awk -F'"' '{print $2}' || true)
if [[ "$STATUS" == "running" ]]; then
    echo "[WARN] Job már fut. Folytatod? (y/N)"; read -r ans; [[ "$ans" == "y" ]] || exit 1
fi
if [[ "$STATUS" == "done" ]]; then
    echo "[WARN] Job már kész. Újrafuttatod? (y/N)"; read -r ans; [[ "$ans" == "y" ]] || exit 1
fi

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- pending → running ---
echo "[*] $JOB_ID — running ($NOW)"
python3 - "$META" "$NOW" <<'PYEOF'
import sys, re
meta_path, now = sys.argv[1], sys.argv[2]
with open(meta_path) as f:
    content = f.read()
content = re.sub(r'^status:.*$', 'status: "running"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+started:.*$', f'  started: "{now}"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+completed:.*$', '  completed: ""', content, flags=re.MULTILINE)
with open(meta_path, "w") as f:
    f.write(content)
PYEOF

bash "$WORKDIR/tools/update-index.sh"
git -C "$WORKDIR" add "$META" jobs/index.yaml
git -C "$WORKDIR" commit -m "job: $JOB_ID — running"
git -C "$WORKDIR" push

# --- Workspace előkészítése ---
echo "[*] Workspace: $FACTORY_CLONE"
rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"
git clone "$FACTORY_REMOTE" "$FACTORY_CLONE"
git -C "$FACTORY_CLONE" checkout -b "$FEATURE_BRANCH"
echo "[*] Feature branch: $FEATURE_BRANCH"

# --- Prompt összeállítása (env var-ok kifejtve) ---
PROMPT="$(envsubst < "$INPUT")

---
## Munkakörnyezet

cic-factory klón: \`$FACTORY_CLONE\`
Feature branch: \`$FEATURE_BRANCH\`

- Output dokumentumok: \`$FACTORY_CLONE/jobs/$JOB_ID/output/\`
- Sub-job specek (ha létrehozol): \`$FACTORY_CLONE/jobs/<sub-job-id>/input.md\` + \`meta.yaml\`
- Referencia anyagok: \`$FACTORY_CLONE/jobs/$JOB_ID/ref/\`
- Egyéb repó klónok: \`$WORKSPACE/<repo-neve>/\` (ne commitold)

A munka végén commitolj és pushol a feature branch-re:
\`\`\`bash
git -C $FACTORY_CLONE add jobs/$JOB_ID/output/ jobs/
git -C $FACTORY_CLONE commit -m \"job: $JOB_ID — output\"
git -C $FACTORY_CLONE push -u origin $FEATURE_BRANCH
\`\`\`

Push csak \`$FEATURE_BRANCH\` branch-re. Main-re NEM."

# --- Agent futtatás ---
echo "[*] Agent indítása: $AGENT_ID"
echo "[*] Model: ${MODEL:-default}"
MODEL_FLAG=()
[[ -n "$MODEL" ]] && MODEL_FLAG=(--model "$MODEL")
mkdir -p "$FACTORY_CLONE/jobs/$JOB_ID/output"
export CIC_JOB_ID="$JOB_ID"
export CIC_WORKDIR="$WORKDIR"
set +e
CLAUDE_CONFIG_DIR="$AGENT_CONFIG" claude --print "$PROMPT" \
    --mcp-config "$CIC_MCP_CONFIG" \
    "${MODEL_FLAG[@]}" \
    > "$FACTORY_CLONE/jobs/$JOB_ID/output/agent-output.md" 2>&1
EXIT_CODE=$?
set -e

END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NEW_STATUS=$([[ $EXIT_CODE -eq 0 ]] && echo "done" || echo "error")
echo "[$([ "$NEW_STATUS" = "done" ] && echo "✓" || echo "!")] $JOB_ID — $NEW_STATUS ($END)"

# --- running → done/error (live meta) ---
python3 - "$META" "$NEW_STATUS" "$END" <<'PYEOF'
import sys, re
meta_path, status, end = sys.argv[1], sys.argv[2], sys.argv[3]
with open(meta_path) as f:
    content = f.read()
content = re.sub(r'^status:.*$', f'status: "{status}"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+completed:.*$', f'  completed: "{end}"', content, flags=re.MULTILINE)
with open(meta_path, "w") as f:
    f.write(content)
PYEOF

bash "$WORKDIR/tools/update-index.sh"
git -C "$WORKDIR" add "$META" jobs/index.yaml
git -C "$WORKDIR" commit -m "job: $JOB_ID — $NEW_STATUS"
git -C "$WORKDIR" push

echo "[✓] Kész: $JOB_ID — $NEW_STATUS"
echo "[*] Feature branch pusholt: $FEATURE_BRANCH"
echo "[*] Review: gh pr create --head $FEATURE_BRANCH"
