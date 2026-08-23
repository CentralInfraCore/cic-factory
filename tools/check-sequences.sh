#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-sequences.sh — a SPEC.md use-case szerződése nem állíthat többet a
# megvalósításnál.
#
#   S1  minden UC hordozza mind az öt kötelező részt
#       Precondition, Transition, Postcondition, Evidence és Státusz. Az ötödik
#       nélkül a másik négy félrevezető: egy sequence, ami a szándékot írja le,
#       ugyanúgy néz ki, mint egy, ami a viselkedést.
#
#   S2  a `még nem` és a `részleges` státusz megnevezi a nyitott issue-t
#       Enélkül a hiány nem követhető: leírva van, de nincs hova visszatérni.
#
#   S3  minden dokumentált `done` út tartalmaz output-kaput ÉS review-artifactot
#       Ez a repó legfontosabb invariánsa. Ha egy sequence `done`-t ír le
#       anélkül, hogy mindkettőt megnevezné, a dokumentáció egy olyan utat
#       hirdet, amit a close-job.sh nem enged.
#
#   S4  az `agent_done` és a `done` sehol nem szinonima
#       A dokumentáció nem állíthatja egyenlőnek azt, amit a kód szándékosan
#       két külön állapotban és két külön jogosultságban tart.
#
# Exit 0 = rendben, exit 1 = van hiba.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKDIR" || exit 1

FAILED=0

REPORT=$(python3 - <<'PYEOF'
import json
import re

text = open("SPEC.md", encoding="utf-8").read()
lines = text.split("\n")

# A use-case blokkok: "### UC-nn — cím" a következő "### UC" vagy "## " jelig.
starts = [(i, m.group(1), m.group(2))
          for i, line in enumerate(lines)
          if (m := re.match(r"^### (UC-\d+) — (.+)$", line))]

blocks = []
for idx, (line_no, uc, title) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
    for j in range(line_no + 1, end):
        if re.match(r"^## ", lines[j]):
            end = j
            break
    blocks.append((uc, title, line_no + 1, "\n".join(lines[line_no:end])))

REQUIRED = ["Precondition", "Transition", "Postcondition", "Evidence"]
STATUSES = ["garantált", "részleges", "még nem"]

s1, s2, s3, s4 = [], [], [], []

if not blocks:
    s1.append("  SPEC.md — egyetlen '### UC-nn — cím' blokk sincs")

for uc, title, line_no, body in blocks:
    for part in REQUIRED:
        if f"**{part}:**" not in body:
            s1.append(f"  SPEC.md:{line_no} {uc} — hiányzik: **{part}:**")

    m = re.search(r"\*\*Státusz:\*\*\s*`([^`]+)`", body)
    if not m:
        s1.append(f"  SPEC.md:{line_no} {uc} — hiányzik: **Státusz:** `…`")
        continue
    status = m.group(1).strip()
    if status not in STATUSES:
        s1.append(f"  SPEC.md:{line_no} {uc} — ismeretlen státusz: "
                  f"'{status}' (várt: {', '.join(STATUSES)})")
        continue

    # S2 — a nem teljes státusz nevezze meg a nyitott issue-t.
    if status in ("még nem", "részleges") and not re.search(r"#\d+", body):
        s2.append(f"  SPEC.md:{line_no} {uc} — '{status}', de nem nevez meg "
                  f"nyitott issue-t (#nn)")

    # S3 — done-út output-kapu és review nélkül.
    if re.search(r"\bdone\b", body) and status != "még nem":
        writes_done = bool(re.search(r"(→|status=)\s*done\b", body)) or \
            "awaiting_review → done" in body
        if writes_done:
            has_gate = bool(re.search(r"validate-output|output-kapu", body))
            # Az `awaiting_review` szó tartalmazza a "review"-t, tehát az
            # ellenőrzés mindig teljesült volna. A review-ARTIFACTOT keressük,
            # nem a szótagot: review.md, /job-review, vagy a szó önállóan.
            has_review = bool(re.search(
                r"review\.md|/job-review|(?<!awaiting_)\breview(?!_)\b",
                body, re.IGNORECASE))
            if not has_gate:
                s3.append(f"  SPEC.md:{line_no} {uc} — done-utat ír le, de nem "
                          f"nevez meg output-kaput")
            if not has_review:
                s3.append(f"  SPEC.md:{line_no} {uc} — done-utat ír le, de nem "
                          f"nevez meg review-artifactot")

# S4 — agent_done és done sehol nem egyenlő. A tagadó alak (≠, nem, NEM)
# épp a lényeg, azt nem szabad hibának venni.
for path in ("SPEC.md", "README.md", "CLAUDE.md"):
    try:
        body = open(path, encoding="utf-8").read()
    except OSError:
        continue
    for i, line in enumerate(body.split("\n"), 1):
        if "agent_done" not in line:
            continue
        if re.search(r"agent_done\s*(=|==|≡|↔)\s*[`\"']?done", line) or \
           re.search(r"agent_done\s+(és|and)\s+.{0,12}done.{0,20}(ugyanaz|azonos|same|equivalent)", line):
            s4.append(f"  {path}:{i} — az agent_done és a done egyenlőként "
                      f"szerepel: {line.strip()[:70]}")

print(json.dumps({"s1": s1, "s2": s2, "s3": s3, "s4": s4,
                  "count": len(blocks)}))
PYEOF
)
rc=$?
if [[ $rc -ne 0 || -z "$REPORT" ]]; then
    echo "check-sequences: az elemző lépés elszállt (rc=$rc)"
    exit 1
fi

pick() { printf '%s' "$REPORT" | python3 -c "import json,sys; print('\n'.join(json.load(sys.stdin)['$1']))"; }
N=$(printf '%s' "$REPORT" | python3 -c "import json,sys; print(json.load(sys.stdin)['count'])")

rule() { # cím, kulcs, ok-üzenet, fail-üzenet
    local out; out=$(pick "$2")
    echo "$1"
    if [[ -n "$out" ]]; then
        echo "$out"
        echo "  FAIL — $4"
        FAILED=1
    else
        echo "  OK — $3"
    fi
    echo
}

rule "S1 — minden use case hordozza mind az öt részt" s1 \
     "$N use case, mindegyik teljes" \
     "hiányos use-case blokk"
rule "S2 — a nem teljes státusz megnevezi a nyitott issue-t" s2 \
     "minden 'részleges' és 'még nem' hivatkozik issue-ra" \
     "leírt hiány, ami nem követhető vissza"
rule "S3 — minden done-út output-kaput és review-t nevez meg" s3 \
     "nincs done-út a két feltétel nélkül" \
     "a dokumentáció olyan utat hirdet, amit a close-job.sh nem enged"
rule "S4 — az agent_done és a done nem szinonima" s4 \
     "sehol nincsenek egyenlőként kezelve" \
     "a dokumentáció egyenlővé teszi a két állapotot"

[[ "$FAILED" -eq 0 ]] && echo "check-sequences: GO" || echo "check-sequences: NO-GO"
exit "$FAILED"
