#!/usr/bin/env bash
# Job lifecycle wrapper
# Használat: ./tools/run-job.sh <job-id> [agent-id] [--resume]
#
#   --resume   Session-limit/error miatt megszakadt futás folytatása
#              UGYANABBAN a Claude Code session-ben (claude --resume <session_id>).
#              A meglévő workspace-t és feature branch-et újrahasználja,
#              nem klónoz újra. Feltétel: meta.yaml agent.session_id ki van töltve
#              (az előző futás állította be).
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
shift

AGENT_ID="agent-01"
RESUME=0
for arg in "$@"; do
    case "$arg" in
        --resume) RESUME=1 ;;
        *) AGENT_ID="$arg" ;;
    esac
done

JOB_DIR="$WORKDIR/jobs/$JOB_ID"
META="$JOB_DIR/meta.yaml"
INPUT="$JOB_DIR/input.md"
WORKSPACE="$JOB_DIR/workspace"
FACTORY_CLONE="$WORKSPACE/cic-factory"
FACTORY_REMOTE="git@github.com:CentralInfraCore/cic-factory.git"
FEATURE_BRANCH="feature/$JOB_ID"
AGENT_CONFIG="$HOME/.claude-personal/agents/$AGENT_ID"
PROJECT_SLUG=$(echo "$WORKDIR" | sed 's#/#-#g')
SESSION_DIR="$AGENT_CONFIG/projects/$PROJECT_SLUG"

# --- Ellenőrzések ---
[[ -f "$META" ]]  || { echo "[ERROR] Nem létezik: $META"; exit 1; }
[[ -f "$INPUT" ]] || { echo "[ERROR] Nem létezik: $INPUT"; exit 1; }
[[ -d "$AGENT_CONFIG" ]] || { echo "[ERROR] Agent nem létezik: $AGENT_CONFIG"; exit 1; }

STATUS=$(grep '^status:' "$META" | awk -F'"' '{print $2}')
MODEL=$(grep '^  model:' "$META" | awk -F'"' '{print $2}' || true)
SESSION_ID=$(grep '^\s*session_id:' "$META" | awk -F'"' '{print $2}' || true)

if [[ "$RESUME" -eq 1 ]]; then
    [[ -n "$SESSION_ID" ]] || { echo "[ERROR] meta.yaml agent.session_id üres — nincs mit resume-olni"; exit 1; }
    [[ -d "$FACTORY_CLONE" ]] || { echo "[ERROR] Nincs workspace: $FACTORY_CLONE — előbb futtasd a job-ot --resume nélkül"; exit 1; }
    [[ -f "$SESSION_DIR/$SESSION_ID.jsonl" ]] || { echo "[ERROR] Session jsonl nem található: $SESSION_DIR/$SESSION_ID.jsonl"; exit 1; }
else
    if [[ "$STATUS" == "running" ]]; then
        echo "[WARN] Job már fut. Folytatod? (y/N)"; read -r ans; [[ "$ans" == "y" ]] || exit 1
    fi
    if [[ "$STATUS" == "done" ]]; then
        echo "[WARN] Job már kész. Újrafuttatod? (y/N)"; read -r ans; [[ "$ans" == "y" ]] || exit 1
    fi
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
if [[ "$RESUME" -eq 1 ]]; then
    echo "[*] Resume — meglévő workspace újrahasználva: $FACTORY_CLONE"
    CURRENT_BRANCH=$(git -C "$FACTORY_CLONE" branch --show-current)
    [[ "$CURRENT_BRANCH" == "$FEATURE_BRANCH" ]] || echo "[WARN] Workspace branch ($CURRENT_BRANCH) != $FEATURE_BRANCH"
else
    echo "[*] Workspace: $FACTORY_CLONE"
    rm -rf "$WORKSPACE"
    mkdir -p "$WORKSPACE"
    git clone "$FACTORY_REMOTE" "$FACTORY_CLONE"
    git -C "$FACTORY_CLONE" checkout -b "$FEATURE_BRANCH"
    echo "[*] Feature branch: $FEATURE_BRANCH"
fi

# --- Prompt összeállítása ---
if [[ "$RESUME" -eq 1 ]]; then
    PROMPT="A munkamenet korábban megszakadt (session limit vagy hiba), mielőtt a feladat
befejeződött volna. Ugyanebben a session-ben folytatod, a teljes korábbi kontextus
(input.md, eddigi kutatás, döntések) megvan.

Nézd át a workspace jelenlegi állapotát (\`git -C $FACTORY_CLONE status\`,
\`git -C $FACTORY_CLONE log --oneline -10\`) és az eredeti input.md
(\`$FACTORY_CLONE/jobs/$JOB_ID/input.md\`) Definition of Done listáját — azonosítsd
mi van már kész és mi maradt hátra, majd fejezd be a hátralévő munkát.

Push csak \`$FEATURE_BRANCH\` branch-re. Main-re NEM."
else
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
fi

# --- Agent futtatás ---
echo "[*] Agent indítása: $AGENT_ID"
echo "[*] Model: ${MODEL:-default}"
MODEL_FLAG=()
[[ -n "$MODEL" ]] && MODEL_FLAG=(--model "$MODEL")
RESUME_FLAG=()
[[ "$RESUME" -eq 1 ]] && RESUME_FLAG=(--resume "$SESSION_ID")
mkdir -p "$FACTORY_CLONE/jobs/$JOB_ID/output"
export CIC_JOB_ID="$JOB_ID"
export CIC_WORKDIR="$WORKDIR"

OUTPUT_FILE="$FACTORY_CLONE/jobs/$JOB_ID/output/agent-output.md"
[[ "$RESUME" -eq 1 ]] && OUTPUT_FILE="$FACTORY_CLONE/jobs/$JOB_ID/output/agent-output-resume-$(date -u +%Y%m%dT%H%M%SZ).md"

# Marker az új session jsonl megtalálásához a futás után
SESSION_MARKER=$(mktemp)
sleep 1  # mtime-felbontás miatt biztosan a marker UTÁN íródjon az új jsonl

set +e
CLAUDE_CONFIG_DIR="$AGENT_CONFIG" claude --print "$PROMPT" \
    --mcp-config "$CIC_MCP_CONFIG" \
    "${MODEL_FLAG[@]}" \
    "${RESUME_FLAG[@]}" \
    > "$OUTPUT_FILE" 2>&1
EXIT_CODE=$?
set -e

# --- Session UUID elmentése (resume-hoz) ---
NEW_SESSION_ID=$(find "$SESSION_DIR" -maxdepth 1 -name '*.jsonl' -newer "$SESSION_MARKER" 2>/dev/null \
    | xargs -r ls -t 2>/dev/null | head -1 | xargs -r basename -s .jsonl || true)
rm -f "$SESSION_MARKER"
if [[ -n "$NEW_SESSION_ID" ]]; then
    SESSION_ID="$NEW_SESSION_ID"
    echo "[*] Session UUID: $SESSION_ID"
else
    echo "[WARN] Nem található új session jsonl a $SESSION_DIR alatt — session_id nem frissül"
fi

END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NEW_STATUS=$([[ $EXIT_CODE -eq 0 ]] && echo "done" || echo "error")
echo "[$([ "$NEW_STATUS" = "done" ] && echo "✓" || echo "!")] $JOB_ID — $NEW_STATUS ($END)"

# --- running → done/error (live meta) ---
python3 - "$META" "$NEW_STATUS" "$END" "$SESSION_ID" <<'PYEOF'
import sys, re
meta_path, status, end, session_id = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(meta_path) as f:
    content = f.read()
content = re.sub(r'^status:.*$', f'status: "{status}"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+completed:.*$', f'  completed: "{end}"', content, flags=re.MULTILINE)
if session_id:
    if re.search(r'^\s+session_id:', content, flags=re.MULTILINE):
        content = re.sub(r'^(\s+)session_id:.*$', rf'\1session_id: "{session_id}"', content, flags=re.MULTILINE)
    else:
        content = re.sub(r'^(\s+model:.*)$', rf'\1\n  session_id: "{session_id}"', content, flags=re.MULTILINE, count=1)
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
if [[ "$NEW_STATUS" == "error" ]]; then
    echo "[*] Folytatás ugyanebben a session-ben: ./tools/run-job.sh $JOB_ID $AGENT_ID --resume"
fi
