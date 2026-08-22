#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-dependencies.sh — mit igényel a factory, és megvan-e.
#
# Eddig sehol nem volt leírva. Egy hiányzó `jq` vagy GNU `tar` nem az indításnál
# derült ki, hanem futás közben, egy félbehagyott jobnál -- és a hibaüzenet nem
# arról szólt, hogy egy csomag hiányzik.
#
# A GNU-kapcsolók külön vannak felsorolva, mert nem a parancs megléte a kérdés:
# a BSD/macOS `tar`, `date`, `find` és `stat` létezik, csak mást csinál. A
# repository ezért Linux/GNU-t vár; ez itt kimondva, nem feltételezve.
#
#   --list    csak felsorol, nem ellenőriz
#
# Exit 0 = minden megvan, exit 1 = hiányzik valami.

set -uo pipefail

# parancs|honnan|mire kell
REQUIRED=(
    "bash|bash|a teljes tooling"
    "git|git|a job-életciklus minden állapotátmenete"
    "python3|python3|meta-olvasás, index, séma-validáció"
    "jq|jq|a runner JSON-válaszának feldolgozása"
    "curl|curl|Vault signing és tanúsítvány-lekérés"
    "openssl|openssl|a commit-digest és az aláírás-ellenőrzés"
    "tar|tar (GNU)|a determinisztikus tree-snapshot"
    "envsubst|gettext-base|az input.md engedélyezett behelyettesítései"
    "timeout|coreutils|a finalizer hálózati műveletei"
    "date|coreutils|lease-határidők és időbélyegek"
    "find|findutils|a debug-log kiválasztása"
    "xargs|findutils|a shellcheck-futtatás"
    "sed|sed|szövegműveletek"
    "awk|awk|szövegműveletek"
    "stat|coreutils|az állapotkönyvtár jogosultságának ellenőrzése"
)

# GNU-kapcsoló|próba|mire kell
GNU_FEATURES=(
    "date -d|date -u -d '2026-01-01T00:00:00Z' +%s|lease-lejárat összehasonlítása"
    "tar --sort|tar --sort=name --mtime='UTC 1970-01-01' -cf /dev/null -T /dev/null|reprodukálható tree-digest"
    "find -printf|find . -maxdepth 0 -printf '%T@\\n'|a legfrissebb debug-log kiválasztása"
    "stat -c|stat -c '%a' .|jogosultság-ellenőrzés"
)

PY_MODULES=("yaml|PyYAML|meta.yaml olvasása" "jsonschema|jsonschema|a meta-séma érvényesítése")

if [[ "${1:-}" == "--list" ]]; then
    printf '%s\n' "Parancsok:"
    for r in "${REQUIRED[@]}"; do IFS='|' read -r c pkg why <<< "$r"
        printf '  %-10s %-16s %s\n' "$c" "$pkg" "$why"; done
    printf '%s\n' "" "GNU-kapcsolók:"
    for g in "${GNU_FEATURES[@]}"; do IFS='|' read -r n _ why <<< "$g"
        printf '  %-14s %s\n' "$n" "$why"; done
    printf '%s\n' "" "Python-modulok:"
    for m in "${PY_MODULES[@]}"; do IFS='|' read -r mod pkg why <<< "$m"
        printf '  %-12s %-14s %s\n' "$mod" "$pkg" "$why"; done
    exit 0
fi

FAILED=0

echo "Parancsok"
for r in "${REQUIRED[@]}"; do
    IFS='|' read -r cmd pkg why <<< "$r"
    if command -v "$cmd" >/dev/null 2>&1; then
        printf '  OK    %s\n' "$cmd"
    else
        printf '  HIÁNYZIK  %-10s (%s) — %s\n' "$cmd" "$pkg" "$why"
        FAILED=1
    fi
done

echo
echo "GNU-kapcsolók"
for g in "${GNU_FEATURES[@]}"; do
    IFS='|' read -r name probe why <<< "$g"
    if eval "$probe" >/dev/null 2>&1; then
        printf '  OK    %s\n' "$name"
    else
        printf '  HIÁNYZIK  %-14s — %s\n' "$name" "$why"
        printf '            A repository Linux/GNU-t vár. BSD/macOS toolchainen ez a kapcsoló mást jelent.\n'
        FAILED=1
    fi
done

echo
echo "Python-modulok"
for m in "${PY_MODULES[@]}"; do
    IFS='|' read -r mod pkg why <<< "$m"
    if python3 -c "import $mod" >/dev/null 2>&1; then
        printf '  OK    %s\n' "$mod"
    else
        printf '  HIÁNYZIK  %-12s (pip install %s) — %s\n' "$mod" "$pkg" "$why"
        FAILED=1
    fi
done

echo
[[ "$FAILED" -eq 0 ]] && echo "check-dependencies: GO" || echo "check-dependencies: NO-GO"
exit "$FAILED"
