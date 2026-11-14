#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Egy factory job interaktív végrehajtása a `work` (tmux-os, tartós agent-szál)
# alatt a run-job.sh helyett.
#
# Használat: tools/work-open.sh <job-id> [agent-id] [--skip-spec-gate] [-- <work open argumentumok>]
#
# Vékony adapter, nem a work másolata: a workspace-t ugyanúgy készíti elő, mint
# a run-job.sh (klón + feature/<job-id> ág a jobs/<id>/workspace/ alatt), aztán
# a `work open --dir <workspace>`-ot hívja. A szál munkakönyvtára a workspace.
#
# Mit NEM ad: a run-job.sh életciklusát. Nincs running státusz, lease, run_id,
# usage-mérés -- a meta.yaml nem változik. A close-job.sh kapui (output,
# review.md) ugyanúgy érvényesek; a review-nak ki kell mondania, hogy a job
# interaktív work-szálban készült, nem mért run-job futásban.
#
# Az agent profilja a JOB-ból jön (meta.yaml agent.config_dir, különben
# ~/.claude-personal/agents/<agent-id>), és a workspace .envrc-jén át éri el a
# claude-ot (a work az agent-run-ban `direnv exec`-kel indít). Így nem függ
# attól, melyik shellből indítottad a work-öt.
#
# Meglévő workspace-nél:
#   - él hozzá work-szál  -> újraéleszti (a work open idempotens)
#   - nincs szál          -> megáll, és megmondja, mi van benne. Nem töröl.
#
# WORK_BIN: a work helye (alapból a PATH-ról); teszteléshez felülírható.

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$WORKDIR/tools/lib-workspace-guard.sh"

JOB_ID="${1:?Adj meg egy job-id-t}"
shift
AGENT_ID="agent-01"
SKIP_SPEC_GATE=0
EXTRA=()
while (( $# )); do
    case "$1" in
        --skip-spec-gate) SKIP_SPEC_GATE=1; shift ;;
        --) shift; EXTRA=("$@"); break ;;
        -*) echo "[ERROR] ismeretlen opció: $1" >&2; exit 1 ;;
        *)  AGENT_ID="$1"; shift ;;
    esac
done

# Az azonosítókból path és ticketnév épül.
valid_id() {
    [[ "$2" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || { echo "[ERROR] érvénytelen $1: '$2'" >&2; return 1; }
}
valid_id job-id "$JOB_ID" || exit 1
valid_id agent-id "$AGENT_ID" || exit 1

WORK_BIN="${WORK_BIN:-work}"
command -v "$WORK_BIN" >/dev/null || { echo "[ERROR] nincs work a PATH-on (WORK_BIN)" >&2; exit 1; }
command -v direnv >/dev/null || { echo "[ERROR] a direnv szükséges: az agent profilját az .envrc adja át" >&2; exit 1; }

JOB_DIR="$WORKDIR/jobs/$JOB_ID"
META="$JOB_DIR/meta.yaml"
INPUT="$JOB_DIR/input.md"
WORKSPACE="$JOB_DIR/workspace"
CLONE="$WORKSPACE/cic-factory"
BRANCH="feature/$JOB_ID"
# work ticketnév: ^task-[a-z0-9][a-z0-9-]*$ -- a job-id '.' és '_' jelét '-'-re cseréljük.
SLUG="${JOB_ID//[._]/-}"
TICKET="task-$SLUG"
[[ "$TICKET" =~ ^task-[a-z0-9][a-z0-9-]*$ ]] || { echo "[ERROR] a job-id-ből nem képezhető work ticket: $TICKET" >&2; exit 1; }

[[ -f "$META" && -f "$INPUT" ]] || { echo "[ERROR] hiányzik: $META vagy $INPUT" >&2; exit 1; }

CFG=$(bash "$WORKDIR/tools/meta-get.sh" "$META" agent.config_dir 2>/dev/null) || CFG=""
[[ -n "$CFG" ]] || CFG="$HOME/.claude-personal/agents/$AGENT_ID"
CFG="${CFG/#\~/$HOME}"
[[ -d "$CFG" ]] || { echo "[ERROR] az agent-konfiguráció nem létezik: $CFG" >&2; exit 1; }
CFG="$(cd "$CFG" && pwd)"

if [[ -e "$WORKSPACE" ]]; then
    if "$WORK_BIN" info "$TICKET" >/dev/null 2>&1; then
        echo "[*] Meglévő work-szál: $TICKET -- újraélesztés"
        exec "$WORK_BIN" open "$TICKET" "${EXTRA[@]}"
    fi
    echo "[!] A workspace már létezik, és nincs hozzá work-szál: $WORKSPACE" >&2
    REPORT=$(workspace_loss_report "$WORKSPACE")
    if [[ -n "$REPORT" ]]; then
        echo "    Ami benne van (elveszne egy újrakezdésnél):" >&2
        printf '%s\n' "$REPORT" >&2
    else
        echo "    Üres vagy tiszta, de nem én hoztam létre ehhez a szálhoz." >&2
    fi
    echo "    Nem törlök és nem írok felül. Döntsd el: töröld kézzel, vagy indítsd" >&2
    echo "    újra a szálat: $WORK_BIN open $TICKET --dir $WORKSPACE" >&2
    exit 1
fi

if [[ "$SKIP_SPEC_GATE" -eq 1 ]]; then
    echo "[WARN] --skip-spec-gate -- a gépi spec-kapu KIHAGYVA. Ez a futás nem igazolt." >&2
else
    ( cd "$WORKDIR" && bash tools/validate-spec.sh "$JOB_ID" ) \
        || { echo "[ERROR] a spec-kapu NO-GO; --skip-spec-gate-tel tudatosan kihagyható" >&2; exit 1; }
fi

REMOTE="${CIC_FACTORY_REMOTE:-$(git -C "$WORKDIR" remote get-url origin 2>/dev/null || true)}"
[[ -n "$REMOTE" ]] || { echo "[ERROR] nem állapítható meg, honnan klónozzon: nincs origin, nincs CIC_FACTORY_REMOTE" >&2; exit 1; }

mkdir -p "$WORKSPACE"
git clone -q "$REMOTE" "$CLONE"
git -C "$CLONE" checkout -q -b "$BRANCH"
printf 'export CLAUDE_CONFIG_DIR=%s\n' "$CFG" > "$WORKSPACE/.envrc"
direnv allow "$WORKSPACE/.envrc"

PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT
cat > "$PROMPT_FILE" <<EOF
Ez egy interaktív factory job (job-id: $JOB_ID), work-szálban fut, nem run-job.sh futásban.
A meta.yaml státusza nem változik; a lezárást a tulajdonos végzi.

Munkakönyvtár (workspace): $WORKSPACE
cic-factory klón: $CLONE (ág: $BRANCH)

1. Olvasd el: $CLONE/jobs/$JOB_ID/input.md -- az a feladat. A boot sequence-t
   (cic-graph KB) te futtatod, az input.md szerint.
2. Az output dokumentumok helye: $CLONE/jobs/$JOB_ID/output/
3. Más repók klónjai a $WORKSPACE/<repo-neve>/ alá kerülnek (nem commitolod őket
   a cic-factory ágra).
4. Commit és push csak a $BRANCH ágra. Main-re, devel-re nem pusholsz, merge-et
   nem csinálsz.
5. Nyelvi szabály: dokumentáció magyarul, kód/YAML/shell angolul.

A munka NEM tekinthető késznek, amíg az output nincs commitolva és pusholva a
$BRANCH ágra: a workspace törlése előtt a run-job.sh ezt ellenőrzi.
EOF

exec "$WORK_BIN" open "$TICKET" --dir "$WORKSPACE" --title "factory job: $JOB_ID" \
    --prompt-file "$PROMPT_FILE" "${EXTRA[@]}"
