#!/usr/bin/env bash
# validate-spec.sh <job-id>
# Mechanikus spec validátor — gépi kényszer, nem Claude-döntés.
# Exit 0 = GO, Exit 1 = NO-GO

set -euo pipefail

JOB_ID="${1:-}"
if [[ -z "$JOB_ID" ]]; then
    echo "Usage: $0 <job-id>" >&2
    exit 1
fi

SPEC="jobs/$JOB_ID/input.md"
if [[ ! -f "$SPEC" ]]; then
    echo "NO-GO: $SPEC not found" >&2
    exit 1
fi

FAILURES=()

# K1 — Konkrét forrás path vagy chunk-id megadva (abszolút path, env var path, vagy KB chunk)
if ! grep -qE '(/home/|get_chunk\(|c[0-9]{3,}|/sync/|\.go"|\.go`|\$\{CIC_|\$\{RELAY|\$\{WORKDIR)' "$SPEC"; then
    FAILURES+=("K1: nincs konkrét forrás path vagy KB chunk-id (pl. /home/..., \${CIC_RELAY_PATH}, get_chunk, c781)")
fi

# K3 — Explicit tiltott rövidítés (audit: fájl létezése ≠ implemented; build: exit code ≠ siker stb.)
if ! grep -qE '(≠ implemented|nem implemented|file.*existence|fájl.*létez|existence.*does not|létezése nem|≠ működik|≠ sikeres|exit.*code.*≠|kimenet.*olvasd|output.*olvasd)' "$SPEC"; then
    FAILURES+=("K3: nincs explicit tiltott rövidítés (pl. 'fájl létezése ≠ implemented', 'exit code 0 ≠ sikeres')")
fi

# K4 — Output fájlnév meghatározva
if ! grep -qE 'output/[a-z].*\.md' "$SPEC"; then
    FAILURES+=("K4: nincs konkrét output fájlnév (pl. output/report.md)")
fi

# K8 — Claim-evidence tábla az outputban
if ! grep -qE '(Állítás|Claim).*(Bizonyíték|Evidence).*(Verifikáci|Verification)' "$SPEC"; then
    FAILURES+=("K8: nincs claim-evidence tábla előírva az outputban (kell: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat)")
fi

# K7 — Forráskód audit esetén: grep kötelező
# Csak akkor kötelező, ha a spec forrás-elemzést / call-chain audit-ot kér (nem build/format job)
if grep -qE '(audit|call.chain|implemented|scaffold|hívódik|olvasd a forrás|statusz.meghatároz)' "$SPEC"; then
    if ! grep -qE 'grep -rn|grep -r ' "$SPEC"; then
        FAILURES+=("K7: Go forráskód audit, de nincs 'grep -rn' előírás a call-chain ellenőrzéshez")
    fi
fi

# Eredmény
echo "=== validate-spec: $JOB_ID ==="
if [[ ${#FAILURES[@]} -eq 0 ]]; then
    echo "MECHANIKUS ELLENŐRZÉS: GO"
    echo "Folytasd: /job-validate $JOB_ID (evidence-alapú ellenőrzés)"
    exit 0
else
    echo "MECHANIKUS ELLENŐRZÉS: NO-GO"
    for f in "${FAILURES[@]}"; do
        echo "  FAIL: $f"
    done
    echo ""
    echo "Javítsd az input.md-t, majd futtasd újra."
    exit 1
fi
