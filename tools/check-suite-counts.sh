#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-suite-counts.sh — a README-ben deklarált check-számok egyeznek-e azzal,
# amit a suite-ok ténylegesen jelentenek.
#
# A táblázat kézzel karbantartott szám-oszlopot tartalmaz, és el is csúszott:
# a test-check-docs.sh 12-t mondott 14 helyett, a test-verify-signatures.sh
# 18-at 20 helyett. Egy szám, amit senki nem ellenőriz, drifteli magát.
#
# Külön script, nem a check-docs.sh része: ez lefuttatja az összes suite-ot, a
# check-docs.sh pedig maga is fut egy suite-ban (test-check-docs.sh). Ha
# egymást hívnák, a futás rekurzióba menne.
#
# Exit 0 = egyezik, exit 1 = nem.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR" || exit 1

FAILED=0
CHECKED=0

while IFS='|' read -r name declared; do
    [[ -z "$name" ]] && continue
    if [[ ! -f "tools/$name" ]]; then
        echo "  FAIL  $name — a README sorol egy fájlt, ami nincs meg"
        FAILED=1
        continue
    fi
    actual=$(bash "tools/$name" 2>&1 | grep -cE '^[[:space:]]+PASS')
    CHECKED=$((CHECKED + 1))
    if [[ "$declared" == "$actual" ]]; then
        printf '  OK    %-36s %s\n' "$name" "$actual"
    else
        printf '  FAIL  %-36s deklarált %s, valójában %s\n' "$name" "$declared" "$actual"
        FAILED=1
    fi
done < <(python3 - <<'PYEOF'
import re
text = open("README.md", encoding="utf-8").read()
for m in re.finditer(r'^\| `tools/(test-[A-Za-z0-9._-]+\.sh)` \|(.*?)\((\d+) checks\)',
                     text, re.M):
    print(f"{m.group(1)}|{m.group(3)}")
PYEOF
)

echo
if [[ "$CHECKED" -eq 0 ]]; then
    echo "check-suite-counts: NO-GO — egyetlen deklarált számot sem találtam a README-ben"
    exit 1
fi
[[ "$FAILED" -eq 0 ]] && echo "check-suite-counts: GO ($CHECKED suite)" \
                      || echo "check-suite-counts: NO-GO"
exit "$FAILED"
