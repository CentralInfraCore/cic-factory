#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-suite-counts.sh fixture-ökön: a valódi repón zölden fut, ami önmagában
# nem bizonyítja, hogy egy elcsúszott számot észrevenne.

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

# Fixture: egy suite, ami adott számú PASS sort ír, és egy README, ami állít
# valamennyit róla.
mkroot() { # <valós-PASS-szám> <README-ben deklarált szám>
    local r; r=$(mktemp -d); mkdir -p "$r/tools"
    cp "$SRC/check-suite-counts.sh" "$r/tools/"
    {
        echo '#!/usr/bin/env bash'
        echo "for i in \$(seq 1 $1); do echo \"  PASS  eset \$i\"; done"
    } > "$r/tools/test-fixture.sh"
    printf '# Fixture\n\n| `tools/test-fixture.sh` | valami (%s checks) |\n' "$2" > "$r/README.md"
    echo "$r"
}
run() { bash "$1/tools/check-suite-counts.sh" >"$1/out.log" 2>&1; echo $?; }

echo "Egyező szám → GO"
R=$(mkroot 5 5)
check "exit 0" "0" "$(run "$R")"
check_log "  GO-t mond" "check-suite-counts: GO" "$R/out.log"
rm -rf "$R"

echo
echo "Elcsúszott szám → NO-GO, és mindkét értéket megmondja"
R=$(mkroot 7 5)
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi az eltérést" "deklarált 5, valójában 7" "$R/out.log"
rm -rf "$R"

echo
echo "README-sor fájl nélkül → NO-GO"
R=$(mkroot 5 5); rm "$R/tools/test-fixture.sh"
check "exit 1" "1" "$(run "$R")"
check_log "  megmondja hogy nincs meg" "nincs meg" "$R/out.log"
rm -rf "$R"

echo
echo "Deklarált szám nélküli README → NO-GO (nem néma siker)"
# Enélkül egy elrontott táblázat-formátum úgy nézne ki, mint egy zöld futás.
R=$(mkroot 5 5); printf '# Fixture\n\nnincs itt tábla\n' > "$R/README.md"
check "exit 1" "1" "$(run "$R")"
check_log "  ki is mondja" "egyetlen deklarált számot sem" "$R/out.log"
rm -rf "$R"

echo
echo "Átvevő repó: nincs suite-táblázat, de van dependency.yaml → GO"
# A magban a hiányzó táblázat hiba; egy átvevő örökli az eszközöket, de nem az
# állításokat. Enélkül minden átvevő gate-je pirosra váltana.
R=$(mkroot 5 5); printf '# Átvevő\n\nnincs tábla.\n' > "$R/README.md"
printf 'schema_version: "1.0"\n' > "$R/dependency.yaml"
check "exit 0" "0" "$(run "$R")"
check_log "  ki is mondja" "átvevő repó" "$R/out.log"
rm -rf "$R"

echo
echo "  ugyanez dependency.yaml NÉLKÜL (a mag) → NO-GO"
R=$(mkroot 5 5); printf '# Mag\n\nnincs tábla.\n' > "$R/README.md"
check "exit 1" "1" "$(run "$R")"
rm -rf "$R"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
