#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# meta-set.sh — a mezőírás egyetlen helye. Az esetek nagy része arra méri,
# amit a régi `re.sub`-os írók NEM tudtak: melyik szekcióba tartozik a kulcs,
# mi történik a kommentekkel, és mi számít érvényes dokumentumnak.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
SET="$SRC/meta-set.sh"
GET="$SRC/meta-get.sh"
pass=0; fail=0
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
w()   { printf '%b' "$2" > "$T/$1.yaml"; echo "$T/$1.yaml"; }
get() { bash "$GET" "$1" "$2" 2>/dev/null; }
setf() { bash "$SET" "$@" >"$T/err.log" 2>&1; echo $?; }

echo "Szekció-vakság — ez volt a regexek fő hibája"
# A `^\s+completed:.*$` minta MINDEN behúzott completed: sort átírta. Itt kettő
# van, két külön szekcióban.
M=$(w scope 'timestamps:\n  completed: "A"\nusage:\n  completed: "B"\n')
check "az írás sikerül" "0" "$(setf "$M" 'timestamps.completed=UJ')"
check "  a megcélzott mező változott" "UJ" "$(get "$M" timestamps.completed)"
check "  a másik szekció érintetlen" "B" "$(get "$M" usage.completed)"

echo
echo "  ugyanez a másik irányban"
M=$(w scope2 'agent:\n  max_turns: 60\nusage:\n  max_turns: 999\n')
check "az írás sikerül" "0" "$(setf "$M" 'usage.max_turns=123')"
check "  a usage változott" "123" "$(get "$M" usage.max_turns)"
check "  az agent érintetlen" "60" "$(get "$M" agent.max_turns)"

echo
echo "Kommentek és formázás megmaradnak"
M=$(w keep 'job_id: "t"\n# kézzel írt komment\nstatus: "pending"\nagent:\n  model: "opus"   # sorvégi\n')
check "az írás sikerül" "0" "$(setf "$M" 'status=running')"
check "  a különálló komment megvan" "1" "$(grep -c '^# kézzel írt komment$' "$M")"
check "  a sorvégi komment megvan" "1" "$(grep -c 'model: \"opus\"   # sorvégi' "$M")"
check "  a status átíródott" "running" "$(get "$M" status)"

echo
echo "Írás minden bemeneti alakra — YAML szerint mind ugyanaz"
for form in 'status: "pending"' 'status: pending' "status: 'pending'" 'status: pending # komment'; do
    M=$(w form "$form\n")
    check "[$form]" "0" "$(setf "$M" 'status=running')"
    check "  értéke running" "running" "$(get "$M" status)"
done

echo
echo "Üres érték helyére írás (a jelölés a következő sorra mutat)"
M=$(w empty 'status:\njob_id: "t"\n')
check "az írás sikerül" "0" "$(setf "$M" 'status=running')"
check "  a status running" "running" "$(get "$M" status)"
check "  a következő kulcs megvan" "t" "$(get "$M" job_id)"

echo
echo "Hiányzó kulcs beszúrása"
M=$(w ins 'status: "pending"\nagent:\n  model: "opus"\n')
check "beszúrás szekcióba" "0" "$(setf "$M" 'agent.session_id=abc')"
check "  vissza is olvasható" "abc" "$(get "$M" agent.session_id)"
check "  a szekcióban van, nem a gyökérben" "1" "$(grep -c '^  session_id:' "$M")"
check "beszúrás gyökérbe" "0" "$(setf "$M" 'lease_expires=2026-01-01')"
check "  vissza is olvasható" "2026-01-01" "$(get "$M" lease_expires)"
check "  behúzás nélkül" "1" "$(grep -c '^lease_expires:' "$M")"

echo
echo "Egy hívás, több mező — köztük két új ugyanabba a szekcióba"
M=$(w multi 'status: "pending"\ntimestamps:\n  created: "C"\n')
check "az írás sikerül" "0" "$(setf "$M" 'status=done' 'timestamps.started=S' 'timestamps.completed=E')"
check "  status" "done" "$(get "$M" status)"
check "  created érintetlen" "C" "$(get "$M" timestamps.created)"
check "  started" "S" "$(get "$M" timestamps.started)"
check "  completed" "E" "$(get "$M" timestamps.completed)"

echo
echo "Idézőjelet és backslasht tartalmazó érték"
M=$(w esc 'error_message: ""\n')
check "az írás sikerül" "0" "$(setf "$M" 'error_message=ő "idézet" és \ jel')"
check "  pontosan olvasható vissza" 'ő "idézet" és \ jel' "$(get "$M" error_message)"

echo
echo "Fail closed — amit nem szabad megírni"
M=$(w dup 'status: "a"\nstatus: "b"\n')
check "duplikált kulcs → 1" "1" "$(setf "$M" 'status=c')"
check "  a fájl érintetlen" "2" "$(grep -c '^status:' "$M")"

M=$(w bad 'status: "lezaratlan\nagent:\n  model: "x\n')
check "hibás YAML → 1" "1" "$(setf "$M" 'status=c')"

M=$(w deep 'status: "pending"\n')
check "hiányzó MÉLY szekció → 1" "1" "$(setf "$M" 'a.b.c=1')"
check "  meg is mondja miért" "1" "$(grep -c "nincs a dokumentumban" "$T/err.log")"

M=$(w notmap 'agent: "string, nem mapping"\n')
check "nem-mapping szülő → 1" "1" "$(setf "$M" 'agent.model=x')"

check "kulcs=érték alak nélkül → 1" "1" "$(setf "$(w x 'status: "a"\n')" 'csak_kulcs')"
check "nincs ilyen fájl → 1" "1" "$(setf "$T/nincs.yaml" 'status=a')"

echo
echo "Hiányzó gyökér-szekció létrehozása"
# A usage: blokk a mező bevezetése előtti metákból hiányzik, és a runner
# ilyenkor is ír bele. A régi regex a timestamps: elé szúrta be; itt a fájl
# végére kerül, egyetlen rendezett blokként.
M=$(w newsec 'status: "running"\ntimestamps:\n  created: "C"\n')
check "az írás sikerül" "0" "$(setf "$M" 'usage.cost_usd=0.42' 'usage.turns=7' 'status=done')"
check "  a szekció fejléce a mezői ELŐTT van" "1" \
    "$(awk '/^usage:$/{h=NR} /^  cost_usd:/{c=NR} END{print (h && c && h < c) ? 1 : 0}' "$M")"
check "  cost_usd" "0.42" "$(get "$M" usage.cost_usd)"
check "  turns" "7" "$(get "$M" usage.turns)"
check "  a meglévő mezők érintetlenek" "C" "$(get "$M" timestamps.created)"
check "  a másik írás is megtörtént" "done" "$(get "$M" status)"
check "  egyetlen usage: sor" "1" "$(grep -c '^usage:$' "$M")"

echo
echo "A séma szerint érvényes marad, amit írtunk"
M=$(w valid 'status: "pending"\ntimestamps:\n  created: "C"\n')
bash "$SET" "$M" 'status=running' 'timestamps.started=S' >/dev/null 2>&1
check "PyYAML újra beolvassa" "0" "$(python3 -c "
import yaml,sys
yaml.safe_load(open('$M'))" >/dev/null 2>&1; echo $?)"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
