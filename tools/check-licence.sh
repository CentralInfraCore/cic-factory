#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-licence.sh — a licencfájlok nem mondhatnak egymásnak ellent.
#
#   L1  az AGPL-szöveg bájtra változatlan
#       A kapu eddig a teljes LICENSE SHA-ját pinelte. Ez jó cél volt --
#       verbatim GPL-szöveget nem szabad átírni --, de kizárta a §7 szerinti
#       függeléket is, amit maga a licenc enged. Most a függelék előtti rész
#       hasheljük: az AGPL-szöveg ugyanúgy sérthetetlen, a kiegészítés viszont
#       lehetséges.
#
#   L2  a §7 függelék jelen van, és tartalmazza az attribution kikötést
#       A kikötés eddig csak a LICENSE.md-ben állt, a LICENSE-ben nem -- és a
#       LICENSE.md maga mondta, hogy eltérés esetén a LICENSE az irányadó. A
#       kikötést hordozó dokumentum jelentette ki, hogy a kikötés nélküli
#       fájl győz.
#
#   L3  a két fájl ugyanazt a kikötést hordozza
#       Ha a LICENSE.md-ből kikerül vagy átíródik, az megint két igazság.
#
# Exit 0 = rendben, exit 1 = nem.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR" || exit 1

MARKER='--- ADDITIONAL TERMS (AGPL-3.0 section 7) ---'
AGPL_SHA256='0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0'
# Egy mondat, ami mindkét fájlban azonos alakban szerepel. Nem a teljes szöveget
# hasonlítjuk: a két fájl formázása eltér (idézetblokk vs behúzás).
TERM_ANCHOR='must preserve the'

FAILED=0

echo "L1 — az AGPL-szöveg változatlan"
if [[ ! -f LICENSE ]]; then
    echo "  FAIL — nincs LICENSE fájl"
    FAILED=1
else
    AGPL_PART=$(awk -v m="$MARKER" 'index($0, m) == 1 && length($0) == length(m) {exit} {print}' LICENSE)
    ACTUAL=$(printf '%s\n' "$AGPL_PART" | sha256sum | cut -d' ' -f1)
    if [[ "$ACTUAL" == "$AGPL_SHA256" ]]; then
        echo "  OK — a függelék előtti rész bájtra a verbatim AGPL-3.0"
    else
        echo "  FAIL — az AGPL-szöveg megváltozott"
        echo "         várt:   $AGPL_SHA256"
        echo "         kapott: $ACTUAL"
        FAILED=1
    fi
fi

echo
echo "L2 — a §7 függelék jelen van"
if ! grep -qF -- "$MARKER" LICENSE 2>/dev/null; then
    echo "  FAIL — nincs '$MARKER' jelölő a LICENSE-ben"
    FAILED=1
elif ! grep -qF -- "$TERM_ANCHOR" LICENSE 2>/dev/null; then
    echo "  FAIL — a jelölő megvan, de az attribution kikötés nincs a LICENSE-ben"
    FAILED=1
else
    echo "  OK — a kikötés abban a fájlban áll, ami irányadó"
fi

echo
echo "L3 — a LICENSE.md ugyanazt a kikötést hordozza"
if [[ ! -f LICENSE.md ]]; then
    echo "  FAIL — nincs LICENSE.md"
    FAILED=1
elif ! grep -qF -- "$TERM_ANCHOR" LICENSE.md; then
    echo "  FAIL — a LICENSE.md nem tartalmazza a kikötést, a LICENSE igen"
    FAILED=1
else
    echo "  OK — mindkét fájl ugyanazt mondja"
fi

echo
[[ "$FAILED" -eq 0 ]] && echo "check-licence: GO" || echo "check-licence: NO-GO"
exit "$FAILED"
