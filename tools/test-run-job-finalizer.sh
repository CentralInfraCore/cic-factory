#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
# Exercises run-job.sh's finalizer prelude — the real text, extracted from the
# shipped script, not a hand-copied clone. Each case runs in its own process
# with a fixture meta.yaml.
set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/run-job.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# The prelude: everything up to and including the `trap finalize EXIT INT TERM`.
PRELUDE_END=$(grep -n '^trap finalize EXIT INT TERM$' "$SRC" | head -1 | cut -d: -f1)
sed -n "1,${PRELUDE_END}p" "$SRC" > "$TMP/prelude.sh"
echo "prelude: 1..$PRELUDE_END sor"

mkmeta() {
    cat > "$1" <<EOF
status: "$2"
error_message: ""
timestamps:
  created: "2026-01-01T00:00:00Z"
  started: "2026-01-01T00:00:00Z"
  completed: ""
EOF
}

pass=0; fail=0
check() { # name expected actual
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++));
    else echo "  FAIL  $1 — várt: [$2] kapott: [$3]"; ((fail++)); fi
}

run_case() { # script-body meta-status  -> prints "rc|status|stderr"
    local body="$1" st="$2"
    mkmeta "$TMP/meta.yaml" "$st"
    cat > "$TMP/case.sh" <<EOF
$(cat "$TMP/prelude.sh")
META="$TMP/meta.yaml"
$body
EOF
    local err rc
    err=$(bash "$TMP/case.sh" 2>&1 >/dev/null); rc=$?
    echo "$rc|$(grep '^status:' "$TMP/meta.yaml" | awk -F'"' '{print $2}')|$err"
}

echo
echo "1. Korai kilépés MIUTÁN mi állítottuk running-ra → meta error lesz"
out=$(run_case 'WE_SET_RUNNING=1; RUN_LOG="'"$TMP"'/run.log"; exit 7' "running")
check "exit kód megőrizve" "7" "${out%%|*}"
check "status → error" "error" "$(echo "$out" | head -1 | cut -d'|' -f2)"
grep -q 'idő előtt kilépett' <<<"$out" && { echo "  PASS  figyelmeztetés stderr-en"; ((pass++)); } \
    || { echo "  FAIL  nincs figyelmeztetés stderr-en"; ((fail++)); }
grep -q 'wrapper exited early' "$TMP/run.log" 2>/dev/null && { echo "  PASS  napló írva"; ((pass++)); } \
    || { echo "  FAIL  a napló nem íródott ($TMP/run.log)"; ((fail++)); }
grep -q 'error_message: "wrapper exited' "$TMP/meta.yaml" && { echo "  PASS  error_message kitöltve"; ((pass++)); } \
    || { echo "  FAIL  error_message üres"; ((fail++)); }
grep -q 'completed: "20' "$TMP/meta.yaml" && { echo "  PASS  completed timestamp kitöltve"; ((pass++)); } \
    || { echo "  FAIL  completed üres"; ((fail++)); }

echo
echo "2. Idegen 'running' meta (mi NEM állítottuk) → érintetlen marad"
out=$(run_case 'exit 1' "running")
check "status változatlan" "running" "$(echo "$out" | head -1 | cut -d'|' -f2)"

echo
echo "3. Normál út: FINALIZED=1 → a trap nem ír felül"
# awaiting_review, not done: this is the state run-job.sh actually leaves behind.
# Exit 0 says the agent finished; only /job-close may say the job is acceptable.
out=$(run_case 'WE_SET_RUNNING=1; FINALIZED=1; exit 0' "awaiting_review")
check "exit 0 megőrizve" "0" "${out%%|*}"
check "status változatlan" "awaiting_review" "$(echo "$out" | head -1 | cut -d'|' -f2)"

echo
echo '4. Lezárt stdout ("... | head"): a script véget ér, DE a finalizer lefut'
echo "   (ez az eredeti incidens: régen a SIGPIPE megkerülte az EXIT trapet)"
mkmeta "$TMP/meta.yaml" "running"
cat > "$TMP/pipe.sh" <<EOF
$(cat "$TMP/prelude.sh")
META="$TMP/meta.yaml"
RUN_LOG="$TMP/pipe.log"
WE_SET_RUNNING=1
for i in \$(seq 1 5000); do echo "sor \$i"; done
FINALIZED=1   # ide már nem jut el
EOF
bash "$TMP/pipe.sh" 2>"$TMP/pipe.err" | head -3 >/dev/null
sleep 0.2
check "status → error (nem ragad running-ban)" "error" \
    "$(grep '^status:' "$TMP/meta.yaml" | awk -F'"' '{print $2}')"
grep -q 'idő előtt kilépett' "$TMP/pipe.err" && { echo "  PASS  a finalizer lefutott zárt stdout mellett is"; ((pass++)); } \
    || { echo "  FAIL  a finalizer néma maradt"; ((fail++)); }
grep -q 'error_message: "wrapper exited' "$TMP/meta.yaml" && { echo "  PASS  error_message kitöltve"; ((pass++)); } \
    || { echo "  FAIL  error_message üres"; ((fail++)); }

echo
echo "5. SIGTERM futás közben → meta error, agent PID jelentve"
mkmeta "$TMP/meta.yaml" "running"
cat > "$TMP/term.sh" <<EOF
$(cat "$TMP/prelude.sh")
META="$TMP/meta.yaml"
RUN_LOG="$TMP/term.log"
WE_SET_RUNNING=1
sleep 300 &
AGENT_PID=\$!
echo \$AGENT_PID > "$TMP/agent.pid"
wait \$AGENT_PID
EOF
bash "$TMP/term.sh" 2>"$TMP/term.err" &
WRAPPER=$!
sleep 1
kill -TERM "$WRAPPER" 2>/dev/null
wait "$WRAPPER" 2>/dev/null
sleep 0.3
check "status → error" "error" "$(grep '^status:' "$TMP/meta.yaml" | awk -F'"' '{print $2}')"
grep -q 'MÉG FUT árván: PID' "$TMP/term.err" && { echo "  PASS  árva agent PID jelentve"; ((pass++)); } \
    || { echo "  FAIL  nincs árva-figyelmeztetés (dead code lenne)"; ((fail++)); }
AP=$(cat "$TMP/agent.pid" 2>/dev/null || echo "")
[[ -n "$AP" ]] && kill -0 "$AP" 2>/dev/null && { echo "  PASS  a háttérgyerek túlélte a wrapper TERM-jét"; ((pass++)); } \
    || { echo "  FAIL  a gyerek nem élte túl — nem lenne mit jelenteni"; ((fail++)); }
[[ -n "$AP" ]] && kill -TERM "$AP" 2>/dev/null

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
