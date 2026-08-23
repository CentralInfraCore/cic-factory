#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-licence.sh fixture-ökön. A valódi repón zölden fut; az önmagában nem
# mondja meg, hogy egy átírt AGPL-szöveget vagy egy eltűnt kikötést észrevenne.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SRC/.." && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

mkroot() {
    local r; r=$(mktemp -d); mkdir -p "$r/tools"
    cp "$SRC/check-licence.sh" "$r/tools/"
    cp "$ROOT/LICENSE" "$ROOT/LICENSE.md" "$r/"
    echo "$r"
}
run() { ( cd "$1" && bash tools/check-licence.sh ) >"$1/out.log" 2>&1; echo $?; }

echo "0. Az igazi fájlok → GO (különben a többi eset semmit nem mond)"
R=$(mkroot)
check "exit 0" "0" "$(run "$R")"
check_log "  GO-t mond" "check-licence: GO" "$R/out.log"
rm -rf "$R"

echo
echo "L1 — az AGPL-szöveg egyetlen módosított sora"
R=$(mkroot)
sed -i '20s/.*/EZ A SOR ÁT VAN ÍRVA/' "$R/LICENSE"
check "exit 1" "1" "$(run "$R")"
check_log "  megmondja hogy megváltozott" "az AGPL-szöveg megváltozott" "$R/out.log"
rm -rf "$R"

echo
echo "L1 — a függelék UTÁNI szerkesztés nem bukik (ez a lényeg)"
# A régi kapu a teljes fájlt hashelte, tehát a §7 függeléket sem engedte.
R=$(mkroot)
printf '\n  Egy további, a §7 által megengedett megjegyzés.\n' >> "$R/LICENSE"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "L2 — a függelék jelölője eltávolítva"
R=$(mkroot)
grep -v -- '--- ADDITIONAL TERMS (AGPL-3.0 section 7) ---' "$R/LICENSE" > "$R/L.tmp"
mv "$R/L.tmp" "$R/LICENSE"
check "exit 1" "1" "$(run "$R")"
check_log "  a jelölőt hiányolja" "nincs '--- ADDITIONAL TERMS" "$R/out.log"
rm -rf "$R"

echo
echo "L2 — jelölő megvan, a kikötés szövege nincs"
R=$(mkroot)
awk '/^--- ADDITIONAL TERMS/{print; exit} {print}' "$R/LICENSE" > "$R/L.tmp"
mv "$R/L.tmp" "$R/LICENSE"
check "exit 1" "1" "$(run "$R")"
check_log "  ezt meg is mondja" "az attribution kikötés nincs a LICENSE-ben" "$R/out.log"
rm -rf "$R"

echo
echo "L3 — a kikötés eltűnik a LICENSE.md-ből"
# Ez volt a kiindulási állapot, csak fordítva: két fájl, két igazság.
R=$(mkroot)
grep -v 'must preserve the' "$R/LICENSE.md" > "$R/M.tmp"
mv "$R/M.tmp" "$R/LICENSE.md"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi az eltérést" "a LICENSE.md nem tartalmazza a kikötést" "$R/out.log"
rm -rf "$R"

echo
echo "L1 — hiányzó LICENSE"
R=$(mkroot); rm "$R/LICENSE"
check "exit 1" "1" "$(run "$R")"
rm -rf "$R"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
