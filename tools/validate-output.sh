#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
# validate-output.sh <job-id>
# Mechanikus output validátor — merge előtti gépi kapu.
# Párja: validate-spec.sh (a spec oldalt fedi). Ez az output oldalt fedi.
#
# Cél: a drága (emberi / erős modell) review a TARTALOMRA menjen, ne a FORMÁRA.
# Amit gép el tud dönteni, azt ne az orchestrátor nézze át kézzel.
#
# FIGYELEM — visszamenőleges futtatás: ez a kapu ÚJ jobokra van kalibrálva.
# A 2026-07-25 előtt lezárt jobokon az O2 (claim-evidence) és O4 (reachability)
# tömegesen bukik, mert azok a specek a K8/K9 szabályok BEVEZETÉSE ELŐTT íródtak —
# ez nem azok hibája, hanem visszamenőleges szigor. A régi jobokon egyedül az
# O1 (megnevezett output hiányzik) jelent valódi hibát.
# Mérés 2026-07-25-én, 35 done jobon: O1=9, O2=22, O4=13.
#
# Exit 0 = GO, Exit 1 = NO-GO
set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f "$WORKDIR/tools/env.sh" ]] && source "$WORKDIR/tools/env.sh"

JOB_ID="${1:-}"
if [[ -z "$JOB_ID" ]]; then
    echo "Usage: $0 <job-id>" >&2
    exit 1
fi

SPEC="$WORKDIR/jobs/$JOB_ID/input.md"
OUTDIR="$WORKDIR/jobs/$JOB_ID/output"

[[ -f "$SPEC" ]]  || { echo "NO-GO: $SPEC not found" >&2; exit 1; }
[[ -d "$OUTDIR" ]] || { echo "NO-GO: $OUTDIR not found" >&2; exit 1; }

FAILURES=()
WARNINGS=()

# --- O1 — a specben megnevezett output fájlok léteznek és nem üresek ---
# CSAK a "## Output" szekcióból olvasunk. Az input.md máshol is hivatkozhat
# `output/*.md` fájlokra — de azok MÁS jobok outputjai, bemeneti referenciaként
# (pl. "olvasd el a jobs/X/output/report.md-t"). Azokat leszállítandónak venni
# hamis pozitív; a job-create.md szerint a leszállítandók a 4. (Output) szekcióban vannak.
OUTPUT_SECTION=$(awk '/^#{1,3}[[:space:]]+Output/{flag=1; next} /^#{1,3}[[:space:]]/{flag=0} flag' "$SPEC" || true)

if [[ -n "$OUTPUT_SECTION" ]]; then
    DECLARED=$(grep -oE '[a-z0-9._-]+\.md' <<< "$OUTPUT_SECTION" | sort -u || true)
else
    # Nincs Output szekció — a teljes specből olvasunk, de csak figyelmeztetünk,
    # mert nem tudjuk megkülönböztetni a leszállítandót a referenciától.
    DECLARED=""
    WARNINGS+=("O1: nincs '## Output' szekció az input.md-ben — a leszállítandó fájlok nem ellenőrizhetők gépileg. Add hozzá (lásd /job-create 4. pont).")
fi

if [[ -z "$DECLARED" && -n "$OUTPUT_SECTION" ]]; then
    WARNINGS+=("O1: az '## Output' szekció nem nevez meg .md fájlt — a validate-spec.sh K4-nek ezt el kellett volna kapnia")
elif [[ -n "$DECLARED" ]]; then
    for name in $DECLARED; do
        f="$OUTDIR/$name"
        if [[ ! -f "$f" ]]; then
            FAILURES+=("O1: a spec előírja de hiányzik: output/$name")
        elif [[ ! -s "$f" ]]; then
            FAILURES+=("O1: üres fájl: output/$name")
        fi
    done
fi

# Minden ténylegesen jelen lévő .md (az agent-output/stderr naplókat kihagyva)
mapfile -t PRESENT < <(find "$OUTDIR" -maxdepth 1 -name '*.md' \
    ! -name 'agent-output*.md' ! -name 'review.md' -printf '%f\n' | sort)

if [[ ${#PRESENT[@]} -eq 0 ]]; then
    FAILURES+=("O1: nincs egyetlen érdemi .md output sem a $OUTDIR alatt")
fi

# --- O2 — claim-evidence tábla legalább egy outputban ---
# A K8 a specben írja elő; itt azt ellenőrizzük, hogy tényleg meg is született.
CE_FOUND=0
for name in "${PRESENT[@]:-}"; do
    [[ -n "$name" ]] || continue
    if grep -qE '^\|.*(Állítás|Claim).*\|.*(Bizonyíték|Evidence).*\|' "$OUTDIR/$name"; then
        CE_FOUND=1
        break
    fi
done
if [[ "$CE_FOUND" -eq 0 ]]; then
    FAILURES+=("O2: nincs claim-evidence táblázat egyetlen outputban sem (fejléc: | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |)")
fi

# --- O3 — placeholder / befejezetlen szöveg ---
# A "majd kitöltöm" jellegű maradékok merge előtt fogandók el, nem utána.
# A markert SORELEJÉHEZ kötjük (listajel/fejléc után is jó). Prózában idézett
# marker — pl. "a fájl elején FIXME jelzi, hogy..." — nem placeholder, hanem
# egy másik repo forráskódjáról szóló tényállítás. Az sorközépen áll.
PLACEHOLDER_HITS=""
for name in "${PRESENT[@]:-}"; do
    [[ -n "$name" ]] || continue
    hits=$(grep -nE '^[[:space:]]*([-*+>]|#{1,6}|[0-9]+\.)?[[:space:]]*(TODO|TBD|FIXME|XXX|kitöltendő|pótolandó)\b' \
        "$OUTDIR/$name" | head -3 || true)
    if [[ -n "$hits" ]]; then
        PLACEHOLDER_HITS+="    $name:"$'\n'
        while IFS= read -r line; do PLACEHOLDER_HITS+="      $line"$'\n'; done <<< "$hits"
    fi
done
if [[ -n "$PLACEHOLDER_HITS" ]]; then
    FAILURES+=("O3: befejezetlen placeholder az outputban:"$'\n'"$PLACEHOLDER_HITS")
fi

# --- O4 — reachability artifact, ha a spec megkövetelte (K9 párja) ---
# Ha a spec implemented/scaffold státuszt kér, az outputnak file:line hívási
# pontot VAGY deadcode kimenetet kell tartalmaznia. "symbol létezik" ≠ "production hívja".
if grep -qE '(implemented|scaffold|hívódik|call.?chain)' "$SPEC"; then
    REACH_FOUND=0
    for name in "${PRESENT[@]:-}"; do
        [[ -n "$name" ]] || continue
        if grep -qE '([A-Za-z0-9_/.-]+\.(go|py|sh|yaml|json):[0-9]+|deadcode)' "$OUTDIR/$name"; then
            REACH_FOUND=1
            break
        fi
    done
    if [[ "$REACH_FOUND" -eq 0 ]]; then
        FAILURES+=("O4: a spec státusz-meghatározást kér, de az outputban nincs reachability artifact (file:line hívási pont VAGY 'deadcode ./...' kimenet)")
    fi
fi

# --- O5 — file:line hivatkozások feloldhatósága (figyelmeztetés) ---
# Az outputok gyakran más repókra hivatkoznak; ami itt nem oldható fel, az nem
# automatikusan hiba — de a review-nak látnia kell, mit nem tudott a gép igazolni.
declare -a ROOTS=("$WORKDIR")
[[ -n "${CIC_RELAY_PATH:-}" ]]   && ROOTS+=("$CIC_RELAY_PATH")
[[ -n "${CIC_SCHEMAS_PATH:-}" ]] && ROOTS+=("$CIC_SCHEMAS_PATH")
[[ -n "${CIC_KB_PATH:-}" ]]      && ROOTS+=("$CIC_KB_PATH")

UNRESOLVED=0; RESOLVED=0
for name in "${PRESENT[@]:-}"; do
    [[ -n "$name" ]] || continue
    while IFS= read -r ref; do
        [[ -n "$ref" ]] || continue
        path="${ref%%:*}"
        found=0
        for root in "${ROOTS[@]}"; do
            [[ -e "$root/$path" ]] && { found=1; break; }
        done
        if [[ "$found" -eq 1 ]]; then RESOLVED=$((RESOLVED+1)); else UNRESOLVED=$((UNRESOLVED+1)); fi
    done < <(grep -ohE '[A-Za-z0-9_][A-Za-z0-9_/.-]*\.(go|py|sh):[0-9]+' "$OUTDIR/$name" | sort -u || true)
done
if [[ "$UNRESOLVED" -gt 0 ]]; then
    WARNINGS+=("O5: $UNRESOLVED file:line hivatkozás nem oldható fel a ismert repo-gyökerekből ($RESOLVED feloldható). Nem automatikusan hiba — de a review nézze meg. Tipp: tools/env.sh-ban add meg a repo path-okat.")
fi

# --- Eredmény ---
echo "=== validate-output: $JOB_ID ==="
echo "Vizsgált fájlok: ${#PRESENT[@]}  |  feloldott file:line: $RESOLVED"
echo ""
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    for w in "${WARNINGS[@]}"; do echo "  WARN: $w"; done
    echo ""
fi
if [[ ${#FAILURES[@]} -eq 0 ]]; then
    echo "MECHANIKUS OUTPUT-ELLENŐRZÉS: GO"
    echo "A forma rendben. A tartalmi review most jön — lásd /job-review."
    exit 0
else
    echo "MECHANIKUS OUTPUT-ELLENŐRZÉS: NO-GO"
    for f in "${FAILURES[@]}"; do echo "  FAIL: $f"; done
    echo ""
    echo "Ne mergelj amíg ez NO-GO. Javíttasd az agenttel, vagy írj jobb input.md-t."
    exit 1
fi
