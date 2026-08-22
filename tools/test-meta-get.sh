#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# meta-get.sh — a mezőolvasás egyetlen helye. Az itteni esetek nagy része
# ugyanannak a dokumentumnak a különböző, de YAML szerint AZONOS alakja: a
# korábbi regexes olvasók ezeket különbözőnek látták, és két kontroll épp
# ezen bukott meg (#29, #30).
#
# A három exit code jelentése külön mérve, mert a hívók döntése rajta múlik:
#   0 = megvan, 2 = nincs a dokumentumban, 1 = nem értelmezhető.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
GET="$SRC/meta-get.sh"
pass=0; fail=0
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
# "<rc>:<érték>" alakban ad vissza, hogy egy assertion mindkettőt fedje
get() { local out rc; out=$(bash "$GET" "$1" "$2" 2>/dev/null); rc=$?; echo "$rc:$out"; }
w() { printf '%b' "$2" > "$T/$1.yaml"; echo "$T/$1.yaml"; }

echo "Ugyanaz a dokumentum, öt írásmód — ugyanaz az érték"
check 'idézőjelben'            "0:running" "$(get "$(w a 'status: "running"\n')" status)"
check 'idézőjel nélkül'        "0:running" "$(get "$(w b 'status: running\n')" status)"
check 'aposztróffal'           "0:running" "$(get "$(w c "status: 'running'\n")" status)"
check 'sorvégi kommenttel'     "0:running" "$(get "$(w d 'status: "running" # agent-01\n')" status)"
check 'idézőjel nélkül + komment' "0:running" "$(get "$(w e 'status: running # agent-01\n')" status)"

echo
echo "#29 — a stale-checker ezt nem látta futónak"
M=$(w f 'status: "running" # agent-01\nlease_expires: "2020-01-01T00:00:00Z"\n')
check 'a status running' "0:running" "$(get "$M" status)"

echo
echo "#30 — a close C5 ellenőrzése ezen esett át"
M=$(w g 'status: "awaiting_review"\nspec_gate: skipped # a review majd\n')
check 'a spec_gate skipped' "0:skipped" "$(get "$M" spec_gate)"

echo
echo "Beágyazott mező, pontozott úton"
M=$(w h 'agent:\n  model: "opus"\n  max_turns: 60\nusage:\n  max_turns: 999\n')
check 'agent.model'      "0:opus" "$(get "$M" agent.model)"
# A run-job.sh regexe nem szekcióhoz kötött: az azonos nevű mezőt akárhonnan
# felszedi. Itt a pontozott út dönti el, melyikről van szó.
check 'agent.max_turns'  "0:60"   "$(get "$M" agent.max_turns)"
check 'usage.max_turns'  "0:999"  "$(get "$M" usage.max_turns)"

echo
echo "Hiányzó mező = 2, nem hiba és nem üres érték"
M=$(w i 'status: "pending"\n')
check 'nincs spec_gate'          "2:" "$(get "$M" spec_gate)"
check 'nincs timestamps.started' "2:" "$(get "$M" timestamps.started)"
check 'létező, de üres mező = 0' "0:" "$(get "$(w j 'status:\n')" status)"

echo
echo "Nem értelmezhető dokumentum = 1 (fail closed)"
check 'duplikált kulcs'   "1:" "$(get "$(w k 'status: "a"\nstatus: "b"\n')" status)"
check 'lezáratlan idézet' "1:" "$(get "$(w l 'status: "running\nagent:\n  model: "opus\n')" status)"
check 'nem mapping'       "1:" "$(get "$(w m -- 'csak egy string\n')" status)"
check 'üres fájl'         "1:" "$(get "$(w n '')" status)"
check 'a mező nem skalár' "1:" "$(get "$(w o 'agent:\n  model: "opus"\n')" agent)"
check 'nincs ilyen fájl'  "1:" "$(bash "$GET" "$T/nincs.yaml" status >/dev/null 2>&1; echo "$?:")"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
