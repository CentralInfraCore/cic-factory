#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-embedded-python.sh — a shell heredocokba ágyazott Python is kód.
#
#   E1  minden PY* határolójú heredoc lefordul
#       A core/@v0.1.1 a run-job.sh finalizer blokkjában IndentationError-t
#       szállított: a `running → awaiting_review/error` státuszírás minden
#       valódi futáson elszállt volna. A kapu zöld volt, mert a
#       `python3 -m py_compile` a `git ls-files '*.py'` listáját fordítja, az
#       pedig egyetlen fájl. A run-job.sh öt beágyazott programja — együtt
#       nagyjából 250 sor, benne minden állapotírás — soha nem került parserhez.
#       A `bash -n` a heredoc körüli shellt nézi, a tartalmába nem lát bele.
#
#   E2  python3-nak adott heredoc határolója PY*-gal kezdődik
#       E1 önmagában megkerülhető: aki `<<'EOF'`-fel ír Pythont, annak a
#       blokkja láthatatlan marad. E2 nélkül a kapu és az ellenőrzött ugyanazt
#       a vakfoltot osztaná.
#
# Hatókör: heredocok. A `python3 -c "..."` alakot nem fordítjuk — a shell
# a benne levő $változókat még a Python előtt behelyettesíti, tehát önmagában
# nem is érvényes program. Ha valahol érdemi logika kerül -c mögé, az E2
# szellemében heredoc a helyes forma.
#
# Exit 0 = rendben, exit 1 = van hiba.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR" || exit 1

FAILED=0

REPORT=$(python3 - <<'PY'
import json
import os
import re
import subprocess
import sys
import tempfile
import py_compile

# --cached --others --exclude-standard: a még nem addolt script is ellenőrzés
# alá esik. check-docs.sh ugyanezt csinálja, ugyanabból az okból -- különben a
# kapu az új fájlon hallgat, és csak `git add` után szólal meg.
files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.sh"],
    text=True).split()

# <<'PY' / <<"PY" / <<PY / <<-'PY' -- a <<- a tabokat vágja a sor elejéről.
HEREDOC = re.compile(r"""<<(-?)\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\2""")

e1, e2 = [], []

for path in sorted(set(files)):
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except (OSError, UnicodeDecodeError):
        continue

    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEREDOC.search(line)
        if not m:
            i += 1
            continue

        dash, _, delim = m.groups()
        start = i + 1

        # A heredoc a logikai parancs végén nyílik, de a parancs több sorra is
        # törhet backslash-sel -- a run-job.sh :570 blokkja pont ilyen. A
        # python3 tehát fentebb is lehet, mint a << maga.
        cmd, j = line, i
        while j > 0 and lines[j - 1].rstrip().endswith("\\"):
            j -= 1
            cmd = lines[j] + " " + cmd
        # A python3-at PARANCSNÉVKÉNT keressük, nem akárhol a sorban. A
        # `cat > "$dir/python3" <<FAKE` szintén tartalmazza a szót, és a
        # checker első változata emiatt egy shell-heredocot Python-blokknak
        # nézett. Parancsnév a sor elején, vagy |, &&, ||, ;, ( vagy $( után áll.
        is_python = re.search(
            r"(?:^|[|&;(]|\$\()\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*python3?(?:\s|$)",
            cmd) is not None

        body, i = [], i + 1
        closed = False
        while i < len(lines):
            probe = lines[i].lstrip("\t") if dash else lines[i]
            if probe.strip() == delim and probe.rstrip() == probe.strip():
                closed = True
                i += 1
                break
            body.append(lines[i].lstrip("\t") if dash else lines[i])
            i += 1
        if not closed:
            continue

        looks_python = delim.startswith("PY")

        if is_python and not looks_python:
            e2.append(f"  {path}:{start} → <<{delim} — python3-nak adott heredoc, "
                      f"de a határoló nem PY*-gal kezdődik, ezért E1 nem látja")
            continue

        if not looks_python:
            continue

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("\n".join(body) + "\n")
            tmp = fh.name
        try:
            py_compile.compile(tmp, doraise=True)
        except py_compile.PyCompileError as exc:
            # A kivétel a temp fájlra és a heredocon belüli sorszámra
            # hivatkozik. Mindkettő haszontalan annak, aki a hibát keresi:
            # a fájl már nincs meg, a sorszám pedig nem az, amit a szerkesztő
            # mutat. Átírjuk a valódi fájlra és a valódi sorra.
            reason = str(exc).strip()
            m2 = re.search(r'\(([^,]+), line (\d+)\)', reason)
            if m2:
                abs_line = start + int(m2.group(2))
                reason = reason[:m2.start()].strip() + f" — {path}:{abs_line}"
            else:
                reason = reason.replace(os.path.basename(tmp), path)
            e1.append(f"  {path}:{start} → <<{delim}\n      {reason}")

print(json.dumps({"e1": e1, "e2": e2,
                  "scanned": len(set(files))}))
PY
)
rc=$?
if [[ $rc -ne 0 || -z "$REPORT" ]]; then
    echo "check-embedded-python: a kinyerő lépés elszállt (rc=$rc)"
    exit 1
fi

E1=$(printf '%s' "$REPORT" | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin)["e1"]))')
E2=$(printf '%s' "$REPORT" | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin)["e2"]))')
N=$(printf '%s' "$REPORT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["scanned"])')

echo "E1 — a beágyazott Python lefordul"
if [[ -n "$E1" ]]; then
    echo "$E1"
    echo "  FAIL — beágyazott Python nem fordul"
    FAILED=1
else
    echo "  OK — $N shell script minden PY* heredocja lefordul"
fi

echo
echo "E2 — python3-nak adott heredoc PY* határolóval nyílik"
if [[ -n "$E2" ]]; then
    echo "$E2"
    echo "  FAIL — így E1 elől rejtve marad"
    FAILED=1
else
    echo "  OK — nincs elrejtett Python-heredoc"
fi

echo
[[ "$FAILED" -eq 0 ]] && echo "check-embedded-python: GO" || echo "check-embedded-python: NO-GO"
exit "$FAILED"
