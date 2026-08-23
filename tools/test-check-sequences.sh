#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-sequences.sh fixture-ökön. A valódi SPEC.md-n zölden fut — az önmagában
# nem mondja meg, hogy egy hiányos vagy túlígérő use case-t észrevenne.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

mkroot() { local r; r=$(mktemp -d); mkdir -p "$r/tools"
           cp "$SRC/check-sequences.sh" "$r/tools/"; echo "$r"; }
spec()   { printf '%b' "$2" > "$1/SPEC.md"; }
run()    { ( cd "$1" && bash tools/check-sequences.sh ) >"$1/out.log" 2>&1; echo $?; }

FULL='### UC-01 — Valami\n\n**Státusz:** `garantált`\n\n**Precondition:** x\n\n**Transition:** y\n\n**Postcondition:** z\n\n**Evidence:** w\n'

echo "0. Teljes use case → GO"
R=$(mkroot); spec "$R" "$FULL"
check "exit 0" "0" "$(run "$R")"
check_log "  GO-t mond" "check-sequences: GO" "$R/out.log"
rm -rf "$R"

echo
echo "S1 — hiányzó rész"
for part in Precondition Transition Postcondition Evidence; do
    R=$(mkroot)
    spec "$R" "$(printf '%b' "$FULL" | grep -v "^\*\*$part:\*\*")"
    check "$part nélkül exit 1" "1" "$(run "$R")"
    check_log "  megnevezi" "hiányzik: **$part:**" "$R/out.log"
    rm -rf "$R"
done

echo
echo "S1 — hiányzó vagy ismeretlen státusz"
R=$(mkroot); spec "$R" "$(printf '%b' "$FULL" | grep -v '^\*\*Státusz:\*\*')"
check "státusz nélkül exit 1" "1" "$(run "$R")"
check_log "  megnevezi" "hiányzik: **Státusz:**" "$R/out.log"
rm -rf "$R"
R=$(mkroot); spec "$R" "$(printf '%b' "$FULL" | sed 's/`garantált`/`majdnem`/')"
check "ismeretlen státusz exit 1" "1" "$(run "$R")"
check_log "  megnevezi" "ismeretlen státusz" "$R/out.log"
rm -rf "$R"

echo
echo "S1 — egyetlen use case sincs"
R=$(mkroot); spec "$R" '# SPEC\n\nsemmi.\n'
check "exit 1" "1" "$(run "$R")"
check_log "  ezt ki is mondja" "egyetlen '### UC-nn — cím' blokk sincs" "$R/out.log"
rm -rf "$R"

echo
echo "S2 — 'még nem' issue-hivatkozás nélkül"
# A leírt hiány, amihez nincs hova visszatérni, ugyanolyan rossz, mint a
# le nem írt.
R=$(mkroot)
spec "$R" "$(printf '%b' "$FULL" | sed 's/`garantált`/`még nem`/')"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi" "nem nevez meg nyitott issue-t" "$R/out.log"
rm -rf "$R"

echo
echo "  ugyanez issue-hivatkozással → GO"
R=$(mkroot)
spec "$R" "$(printf '%b' "$FULL" | sed 's/`garantált`/`még nem` — #41/')"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "S3 — done-út output-kapu vagy review nélkül"
R=$(mkroot)
spec "$R" '### UC-04 — Close\n\n**Státusz:** `garantált`\n\n**Precondition:** x\n\n**Transition:** awaiting_review → done\n\n**Postcondition:** z\n\n**Evidence:** w\n'
check "exit 1" "1" "$(run "$R")"
check_log "  hiányolja az output-kaput" "nem nevez meg output-kaput" "$R/out.log"
check_log "  hiányolja a review-t" "nem nevez meg review-artifactot" "$R/out.log"
rm -rf "$R"

echo
echo "  csak a review-val, kapu nélkül → még mindig bukik"
R=$(mkroot)
spec "$R" '### UC-04 — Close\n\n**Státusz:** `garantált`\n\n**Precondition:** x\n\n**Transition:** awaiting_review → done, review.md alapján\n\n**Postcondition:** z\n\n**Evidence:** w\n'
check "exit 1" "1" "$(run "$R")"
check_log "  a kaput hiányolja" "nem nevez meg output-kaput" "$R/out.log"
rm -rf "$R"

echo
echo "  mindkettővel → GO"
R=$(mkroot)
spec "$R" '### UC-04 — Close\n\n**Státusz:** `garantált`\n\n**Precondition:** x\n\n**Transition:** awaiting_review → done, validate-output.sh GO és review.md\n\n**Postcondition:** z\n\n**Evidence:** w\n'
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "S4 — az agent_done egyenlővé téve a done-nal"
R=$(mkroot); spec "$R" "$FULL"
printf 'Megjegyzés: agent_done = done a gyakorlatban.\n' >> "$R/SPEC.md"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a sort" "egyenlőként szerepel" "$R/out.log"
rm -rf "$R"

echo
echo "  a tagadó alak NEM hiba (épp az a lényeg)"
R=$(mkroot); spec "$R" "$FULL"
printf '### `agent_done` ≠ `done`\n\nAz agent_done nem azonos a done-nal.\n' >> "$R/SPEC.md"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
