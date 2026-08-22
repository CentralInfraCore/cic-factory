#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Exercises the state transition run-job.sh actually performs -- the real
# decision line, extracted from the script, not a copy of it.
#
# This exists because tools/test-run-job-finalizer.sh cannot cover it: that test
# extracts only the finalizer prelude (lines 1..trap), and the status decision
# lives far below it. Sabotaging the decision left the finalizer suite at
# 15 PASS / 0 FAIL, which is the definition of a blind gate.
#
# The invariant under test: run-job.sh may never write "done". It runs no output
# gate and produces no review artifact, so it has no basis for that claim.
# Only /job-close may close a job.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/run-job.sh"
SCHEMA="$(cd "$(dirname "$0")/.." && pwd)/jobs/.schema/meta.yaml"
CLOSE="$(cd "$(dirname "$0")/.." && pwd)/.claude/commands/job-close.md"

pass=0; fail=0
check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}

echo "1. A valódi döntési sor kiértékelése"
DECISION=$(grep -n 'NEW_STATUS=\$(\[\[ \$EXIT_CODE' "$SRC" | head -1)
if [[ -z "$DECISION" ]]; then
    echo "  FAIL  nem találom a NEW_STATUS döntési sort a run-job.sh-ban"; ((fail++))
else
    echo "  (run-job.sh:${DECISION%%:*})"
    LINE="${DECISION#*:}"
    check "exit 0 → awaiting_review" "awaiting_review" "$(EXIT_CODE=0 bash -c "$LINE; echo \$NEW_STATUS")"
    check "exit 1 → error"           "error"           "$(EXIT_CODE=1 bash -c "$LINE; echo \$NEW_STATUS")"
fi

echo
echo "2. Strukturális invariáns: a run-job.sh nem állíthat done-t"
# Any assignment or literal that would put "done" into meta.yaml's status field.
HITS=$(grep -nE 'status:[[:space:]]*"done"|echo "done"|NEW_STATUS="done"' "$SRC" || true)
check "nincs done-ra állítás" "" "$HITS"

echo
echo "3. A séma ismeri az új állapotot"
# The enum line specifically, not the file: the explanatory comment above it also
# contains the word, so a file-wide grep passes even with the enum gutted.
ENUM=$(grep -E '^status:' "$SCHEMA" || true)
case "$ENUM" in
    *awaiting_review*) echo "  PASS  a status-enum tartalmazza: $ENUM"; ((pass++)) ;;
    *) echo "  FAIL  a status-enum nem ismeri az awaiting_review-t: '$ENUM'"; ((fail++)) ;;
esac

echo
echo "4. A done-átmenet végrehajtható, és a /job-close azt hívja"
# Korábban ez a lépés a job-close.md szövegét grepelte. Az a konvenció meglétét
# bizonyította, nem az átmenet biztonságát: bárki beírhatta kézzel a done-t.
# A feltételek kikényszerítését a tools/test-close-job.sh méri (26 check);
# itt csak az köt, hogy a végrehajtható út létezik és a parancs azt használja.
CLOSER="$(cd "$(dirname "$0")" && pwd)/close-job.sh"
[[ -x "$CLOSER" ]] \
    && { echo "  PASS  tools/close-job.sh létezik és futtatható"; ((pass++)); } \
    || { echo "  FAIL  nincs végrehajtható tools/close-job.sh"; ((fail++)); }
grep -q 'close-job.sh' "$CLOSE" \
    && { echo "  PASS  a /job-close a scriptet hívja, nem leírja"; ((pass++)); } \
    || { echo "  FAIL  a /job-close nem hívja a close-job.sh-t"; ((fail++)); }

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
