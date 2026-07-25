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
LEVEL=$(grep '^level:' "$META" | awk -F'"' '{print $2}' || true)

# --- meta.yaml extras: kb_focus + max_turns ---
# kb_focus is injected into the prompt as a mandatory first-read list (weak models
# are poor at discovery, good at execution — hand them the context).
# max_turns is a hard runaway guard; without it an agent can burn unbounded tokens.
eval "$(python3 - "$META" <<'PYEOF'
import sys, re, shlex

meta = open(sys.argv[1]).read()

# kb_focus: inline list (kb_focus: ["a", "b"]) or block list (kb_focus:\n  - "a")
focus = []
m = re.search(r'^kb_focus:\s*\[(.*?)\]\s*$', meta, re.MULTILINE)
if m:
    focus = re.findall(r'"([^"]+)"', m.group(1))
else:
    m = re.search(r'^kb_focus:\s*\n((?:[ \t]+-[ \t]+.*\n)+)', meta, re.MULTILINE)
    if m:
        focus = [x.strip().strip('"') for x in re.findall(r'-[ \t]+(.*?)[ \t]*$', m.group(1), re.MULTILINE)]

m = re.search(r'^\s+max_turns:\s*"?(\d+)"?', meta, re.MULTILINE)
turns = m.group(1) if m else ""

print(f"KB_FOCUS={shlex.quote(' '.join(focus))}")
print(f"META_MAX_TURNS={shlex.quote(turns)}")
PYEOF
)"

# Level-based max_turns default when meta.yaml does not pin one
if [[ -n "$META_MAX_TURNS" ]]; then
    MAX_TURNS="$META_MAX_TURNS"
else
    case "$LEVEL" in
        domain)       MAX_TURNS=40 ;;
        repo)         MAX_TURNS=60 ;;
        orchestrator) MAX_TURNS=80 ;;
        *)            MAX_TURNS=60 ;;
    esac
fi

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

# --- kb_focus prompt block ---
KB_FOCUS_BLOCK=""
if [[ -n "$KB_FOCUS" ]]; then
    KB_FOCUS_LIST=""
    for node in $KB_FOCUS; do
        KB_FOCUS_LIST+="- \`$node\`"$'\n'
    done
    KB_FOCUS_BLOCK="
---
## Kötelező első olvasás — kb_focus

Mielőtt bármit írnál vagy állítanál, olvasd el ezeket a KB elemeket a \`cic-graph\` MCP-n:

$KB_FOCUS_LIST
Használd: \`get_chunk(\"<id>\")\` chunk-ra (c-előtag), \`get_node(\"<id>\")\` node-ra (n-előtag),
vagy \`focus_pack\` a teljes csomagra.

Ezek nem javaslatok — a job specje jelölte ki őket kiindulási pontnak.
Ha valamelyik nem létezik vagy üres, azt írd le az outputban. Ne találd ki a tartalmát.
"
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
$KB_FOCUS_BLOCK
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
echo "[*] Model: ${MODEL:-default}  |  max-turns: $MAX_TURNS"
[[ -n "$KB_FOCUS" ]] && echo "[*] kb_focus injektálva: $KB_FOCUS"
MODEL_FLAG=()
[[ -n "$MODEL" ]] && MODEL_FLAG=(--model "$MODEL")
RESUME_FLAG=()
[[ "$RESUME" -eq 1 ]] && RESUME_FLAG=(--resume "$SESSION_ID")
mkdir -p "$FACTORY_CLONE/jobs/$JOB_ID/output"
export CIC_JOB_ID="$JOB_ID"
export CIC_WORKDIR="$WORKDIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="$FACTORY_CLONE/jobs/$JOB_ID/output/agent-output.md"
[[ "$RESUME" -eq 1 ]] && OUTPUT_FILE="$FACTORY_CLONE/jobs/$JOB_ID/output/agent-output-resume-$STAMP.md"
RAW_JSON="$(mktemp)"

# Fallback marker: ha a JSON parse elszáll, a jsonl mtime-keresés még megmenti a session_id-t
SESSION_MARKER=$(mktemp)
sleep 1  # mtime-felbontás miatt biztosan a marker UTÁN íródjon az új jsonl

set +e
CLAUDE_CONFIG_DIR="$AGENT_CONFIG" claude --print "$PROMPT" \
    --mcp-config "$CIC_MCP_CONFIG" \
    --output-format json \
    --max-turns "$MAX_TURNS" \
    "${MODEL_FLAG[@]}" \
    "${RESUME_FLAG[@]}" \
    > "$RAW_JSON" 2>"$RAW_JSON.stderr"
EXIT_CODE=$?
set -e

# --- JSON kibontás: result → agent-output.md, usage → shell változók ---
RUN_SESSION_ID=""; RUN_COST=""; RUN_TURNS=""
RUN_IN_TOKENS=""; RUN_OUT_TOKENS=""; RUN_DURATION_MS=""; RUN_JSON_OK="0"
eval "$(python3 - "$RAW_JSON" "$OUTPUT_FILE" <<'PYEOF'
import sys, json, shlex

raw_path, out_path = sys.argv[1], sys.argv[2]
raw = open(raw_path, encoding="utf-8", errors="replace").read()

def emit(**kw):
    for k, v in kw.items():
        print(f"{k}={shlex.quote('' if v is None else str(v))}")

try:
    data = json.loads(raw)
    if isinstance(data, list):          # stream-json safety net
        data = data[-1]
    if not isinstance(data, dict):
        raise ValueError("unexpected shape")
except Exception:
    # Not JSON: crash, auth prompt, or session-limit banner. Keep raw text for the human.
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(raw)
    emit(RUN_JSON_OK="0")
    sys.exit(0)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(str(data.get("result", "")))

usage = data.get("usage") or {}
emit(
    RUN_SESSION_ID=data.get("session_id"),
    RUN_COST=data.get("total_cost_usd"),
    RUN_TURNS=data.get("num_turns"),
    RUN_IN_TOKENS=usage.get("input_tokens"),
    RUN_OUT_TOKENS=usage.get("output_tokens"),
    RUN_DURATION_MS=data.get("duration_ms"),
    RUN_JSON_OK="1",
)
PYEOF
)"

# stderr csak akkor kerül fájlba, ha nem üres
if [[ -s "$RAW_JSON.stderr" ]]; then
    cp "$RAW_JSON.stderr" "$FACTORY_CLONE/jobs/$JOB_ID/output/agent-stderr-$STAMP.log"
fi
rm -f "$RAW_JSON" "$RAW_JSON.stderr"

# --- Session UUID elmentése (resume-hoz) ---
if [[ -n "$RUN_SESSION_ID" ]]; then
    SESSION_ID="$RUN_SESSION_ID"
    echo "[*] Session UUID: $SESSION_ID (JSON)"
else
    NEW_SESSION_ID=$(find "$SESSION_DIR" -maxdepth 1 -name '*.jsonl' -newer "$SESSION_MARKER" 2>/dev/null \
        | xargs -r ls -t 2>/dev/null | head -1 | xargs -r basename -s .jsonl || true)
    if [[ -n "$NEW_SESSION_ID" ]]; then
        SESSION_ID="$NEW_SESSION_ID"
        echo "[*] Session UUID: $SESSION_ID (jsonl fallback)"
    else
        echo "[WARN] Session UUID nem állapítható meg — --resume nem fog működni"
    fi
fi
rm -f "$SESSION_MARKER"

if [[ "$RUN_JSON_OK" == "1" ]]; then
    echo "[*] Költség: ${RUN_COST:-n/a} USD | turns: ${RUN_TURNS:-n/a}/$MAX_TURNS | tokens: ${RUN_IN_TOKENS:-?} in / ${RUN_OUT_TOKENS:-?} out"
else
    echo "[WARN] Az agent kimenete nem JSON — nyers szöveg az output fájlban, nincs költség-adat"
fi

END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NEW_STATUS=$([[ $EXIT_CODE -eq 0 ]] && echo "done" || echo "error")
echo "[$([ "$NEW_STATUS" = "done" ] && echo "✓" || echo "!")] $JOB_ID — $NEW_STATUS ($END)"

# --- running → done/error + usage (live meta) ---
python3 - "$META" "$NEW_STATUS" "$END" "$SESSION_ID" \
         "$RUN_COST" "$RUN_TURNS" "$RUN_IN_TOKENS" "$RUN_OUT_TOKENS" "$RUN_DURATION_MS" "$MAX_TURNS" <<'PYEOF'
import sys, re

(meta_path, status, end, session_id,
 cost, turns, in_tok, out_tok, duration_ms, max_turns) = sys.argv[1:11]

with open(meta_path) as f:
    content = f.read()

content = re.sub(r'^status:.*$', f'status: "{status}"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+completed:.*$', f'  completed: "{end}"', content, flags=re.MULTILINE)

if session_id:
    if re.search(r'^\s+session_id:', content, flags=re.MULTILINE):
        content = re.sub(r'^(\s+)session_id:.*$', rf'\1session_id: "{session_id}"', content, flags=re.MULTILINE)
    else:
        content = re.sub(r'^(\s+model:.*)$', rf'\1\n  session_id: "{session_id}"', content, flags=re.MULTILINE, count=1)

# usage block — cost visibility per job (P3). Rewritten in full on every run.
usage_block = (
    "usage:\n"
    f'  cost_usd: "{cost}"\n'
    f'  turns: "{turns}"\n'
    f'  max_turns: "{max_turns}"\n'
    f'  input_tokens: "{in_tok}"\n'
    f'  output_tokens: "{out_tok}"\n'
    f'  duration_ms: "{duration_ms}"\n'
)
if re.search(r'^usage:\s*$', content, flags=re.MULTILINE):
    content = re.sub(r'^usage:\s*\n(?:[ \t]+\S.*\n)*', usage_block, content, flags=re.MULTILINE, count=1)
else:
    # insert before timestamps: so the file keeps a stable field order
    if re.search(r'^timestamps:\s*$', content, flags=re.MULTILINE):
        content = re.sub(r'^timestamps:\s*$', usage_block + "timestamps:", content, flags=re.MULTILINE, count=1)
    else:
        content = content.rstrip("\n") + "\n" + usage_block

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
