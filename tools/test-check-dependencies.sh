#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-dependencies.sh — a gépen, ahol fejlesztünk, minden megvan, tehát a
# zöld futás önmagában semmit nem bizonyít. Az eseteket úgy állítjuk elő, hogy
# egy-egy függőséget elrejtünk a PATH-ról.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
CHK="$SRC/check-dependencies.sh"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}

# Szűkített PATH, amiből egy megadott parancs hiányzik: minden mást
# symlinkelünk, a kihagyottat nem.
without() {
    local drop="$1" d; d=$(mktemp -d)
    local c p
    for c in bash git python3 jq curl openssl tar envsubst timeout date find xargs sed awk stat cat cut grep head sort tr printf mktemp dirname basename rm mkdir; do
        [[ "$c" == "$drop" ]] && continue
        p=$(command -v "$c" 2>/dev/null) || continue
        ln -sf "$p" "$d/$c"
    done
    echo "$d"
}
run_without() {
    local d; d=$(without "$1")
    PATH="$d" bash "$CHK" >"$d/out.log" 2>&1
    local rc=$?
    echo "$rc|$d"
}

echo "0. Teljes környezetben GO (különben a többi eset semmit nem mond)"
out=$(bash "$CHK" 2>&1); rc=$?
check "exit 0" "0" "$rc"
check "  GO-t mond" "1" "$(printf '%s' "$out" | grep -c 'check-dependencies: GO')"

echo
echo "Egy-egy parancs elrejtve → NO-GO, és megnevezi"
for cmd in jq curl openssl envsubst git; do
    r=$(run_without "$cmd"); rc="${r%%|*}"; d="${r#*|}"
    check "$cmd nélkül exit 1" "1" "$rc"
    check "  megnevezi" "1" "$(grep -c "HIÁNYZIK  $cmd" "$d/out.log")"
    check "  NO-GO-t mond" "1" "$(grep -c 'check-dependencies: NO-GO' "$d/out.log")"
    rm -rf "$d"
done

echo
echo "Hiányzó Python-modul → NO-GO"
D=$(mktemp -d)
# A valódi értelmezőt ABSZOLÚT úton hívjuk, és a heredoc nincs idézve, hogy a
# $REAL_PY3 beleíródjon. `env python3` a megnövelt PATH-on újra ezt a wrappert
# találná meg -- az első változat így végtelen rekurzióba futott, és a suite
# nem elbukott, hanem beállt. Egy beragadó teszt rosszabb a bukónál: nem mond
# semmit, csak elfogy tőle az idő.
REAL_PY3=$(command -v python3)
cat > "$D/python3" <<FAKE
#!/usr/bin/env bash
# yaml importja bukik, minden más megy
if [[ "\${1:-}" == "-c" && "\${2:-}" == *"import yaml"* ]]; then exit 1; fi
exec "$REAL_PY3" "\$@"
FAKE
chmod +x "$D/python3"
PATH="$D:$PATH" bash "$CHK" >"$D/out.log" 2>&1
check "exit 1" "1" "$?"
check "  a modult nevezi meg" "1" "$(grep -c 'HIÁNYZIK  yaml' "$D/out.log")"
check "  megmondja mivel telepíthető" "1" "$(grep -c 'pip install PyYAML' "$D/out.log")"
rm -rf "$D"

echo
echo "GNU-kapcsoló hiánya → NO-GO, és kimondja hogy Linux/GNU kell"
D=$(mktemp -d)
REAL_DATE=$(command -v date)
cat > "$D/date" <<FAKE
#!/usr/bin/env bash
# BSD date: nincs -d
for a in "\$@"; do [[ "\$a" == "-d" ]] && exit 1; done
exec "$REAL_DATE" "\$@"
FAKE
chmod +x "$D/date"
PATH="$D:$PATH" bash "$CHK" >"$D/out.log" 2>&1
check "exit 1" "1" "$?"
check "  a kapcsolót nevezi meg" "1" "$(grep -c 'HIÁNYZIK  date -d' "$D/out.log")"
check "  kimondja a platform-elvárást" "1" "$(grep -c 'Linux/GNU-t vár' "$D/out.log")"
rm -rf "$D"

echo
echo "--list nem ellenőriz, csak felsorol"
out=$(bash "$CHK" --list 2>&1); rc=$?
check "exit 0" "0" "$rc"
check "  felsorolja a parancsokat" "1" "$(printf '%s' "$out" | grep -c '^Parancsok:')"
check "  a GNU-kapcsolókat is" "1" "$(printf '%s' "$out" | grep -c '^GNU-kapcsolók:')"
check "  a Python-modulokat is" "1" "$(printf '%s' "$out" | grep -c '^Python-modulok:')"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
