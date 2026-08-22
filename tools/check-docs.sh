#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-docs.sh — két dolgot néz, mindkettő olyan hiba, ami már megtörtént.
#
#   D1  nincs törött relatív markdown-link
#       Az extraction után négy volt belőlük: a CLAUDE.md kötelező olvasásként
#       hivatkozott egy fájlra, ami nem jött át, egy másik pedig a repón kívülre
#       mutatott.
#
#   D2  egyetlen dokumentum sem definiálja újra a meta.yaml sémáját
#       A CLAUDE.md felsorolta a mezőket, aztán a séma három mezővel előrement
#       (lease_expires, spec_gate, usage) és a másolat hallgatott róluk. Egy
#       séma, amit két helyen írunk le, egy helyen elavul.
#
# Exit 0 = rendben, exit 1 = van hiba.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR" || exit 1

FAILED=0

echo "D1 — relatív markdown-linkek"
BROKEN=$(python3 - <<'PY'
import os, re, subprocess
out = []
for f in subprocess.check_output(["git", "ls-files", "*.md"], text=True).split():
    base = os.path.dirname(f)
    with open(f, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', line):
                t = m.group(2).split('#')[0].strip()
                if not t or t.startswith(("http://", "https://", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(base, t))):
                    out.append(f"  {f}:{i} → {m.group(2)}")
print("\n".join(out))
PY
)
if [[ -n "$BROKEN" ]]; then
    echo "$BROKEN"
    echo "  FAIL — törött link"
    FAILED=1
else
    echo "  OK — nincs törött link"
fi

echo
echo "D2 — a meta.yaml sémája egy helyen él"
DUPES=$(python3 - <<'PY'
import re, subprocess
# A séma jellemzője: egy yaml blokk, amiben együtt szerepel a job_id és a status
# top-level kulcs. Prózában idézett egyetlen mezőnév nem duplikáció.
pat = re.compile(r'```ya?ml\n(.*?)```', re.S)
out = []
for f in subprocess.check_output(["git", "ls-files", "*.md"], text=True).split():
    body = open(f, encoding="utf-8").read()
    for block in pat.findall(body):
        has_job = re.search(r'^job_id:', block, re.M)
        has_status = re.search(r'^status:', block, re.M)
        if has_job and has_status:
            out.append(f"  {f}: yaml blokk újradefiniálja a sémát")
print("\n".join(out))
PY
)
if [[ -n "$DUPES" ]]; then
    echo "$DUPES"
    echo "  FAIL — a sémát a jobs/.schema/meta.yaml definiálja; a dokumentum hivatkozzon rá"
    FAILED=1
else
    echo "  OK — egyetlen dokumentum sem definiálja újra"
fi

echo
[[ "$FAILED" -eq 0 ]] && echo "check-docs: GO" || echo "check-docs: NO-GO"
exit "$FAILED"
