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

# K7 — Forráskód audit esetén: grep + _test.go kizárás kötelező
# Csak akkor kötelező, ha a spec forrás-elemzést / call-chain audit-ot kér (nem build/format job)
if grep -qE '(audit|call.chain|implemented|scaffold|hívódik|olvasd a forrás|statusz.meghatároz)' "$SPEC"; then
    if ! grep -qE 'grep -rn|grep -r ' "$SPEC"; then
        FAILURES+=("K7: Go forráskód audit, de nincs 'grep -rn' előírás a call-chain ellenőrzéshez")
    fi
    if ! grep -qE '_test\.go|deadcode' "$SPEC"; then
        FAILURES+=("K7b: grep van, de nincs '_test.go' kizárás vagy 'deadcode' — exportált szimbólumoknál grep -v _test.go VAGY deadcode ./... kötelező")
    fi
fi

# K9 — Reachability artifact kötelező: production call site (file:line) VAGY deadcode output
# Ha a spec implemented/scaffold státuszt határoz meg forráskódon alapulva
if grep -qE '(implemented|scaffold|hívódik|production.*call|call.*chain)' "$SPEC"; then
    if ! grep -qE '(deadcode|call.?site|call.?path|file:line|hívó.*fájl|hívó.*sor|production.*hívás)' "$SPEC"; then
        FAILURES+=("K9: nincs reachability artifact előírva — kell: production call site (file:line) VAGY 'deadcode ./...' output az agent outputban; 'symbol létezik' ≠ 'production hívja'")
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
