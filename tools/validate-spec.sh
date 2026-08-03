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

META="jobs/$JOB_ID/meta.yaml"
if [[ ! -f "$META" ]]; then
    echo "NO-GO: $META not found" >&2
    exit 1
fi

FAILURES=()
WARNINGS=()

# K10 — agent.model kitöltve (kritikus)
# Üres model esetén a run-job.sh nem ad --model flaget, és a job csendben a
# (drága) default modellen fut. Néma hiba: sehol nem látszik, hogy megtörtént.
# Szándékosan NEM ellenőrzünk konkrét modellnév-listát — az elavulna.
MODEL_VALUE=$(grep -E '^\s+model:' "$META" | head -1 | sed -E 's/^\s+model:\s*"?([^"]*)"?\s*$/\1/' || true)
if [[ -z "$MODEL_VALUE" ]]; then
    FAILURES+=("K10: meta.yaml agent.model üres — a job a default modellen futna, mérhetetlenül. Tölts ki egyet: claude-opus-5 | claude-sonnet-5 | claude-haiku-4-5 (alias is jó: opus | sonnet | haiku)")
fi

# K11 — kb_focus kitöltve (figyelmeztetés, nem blokkoló)
# A run-job.sh a kb_focus-t kötelező első olvasási listaként injektálja a promptba.
# Üresen hagyva a gyenge modell magától keres a KB-ban — ott a leggyengébb.
if grep -qE '^kb_focus:\s*\[\s*\]\s*$' "$META" || ! grep -qE '^kb_focus:' "$META"; then
    WARNINGS+=("K11: kb_focus üres — az agent magától keres a KB-ban. Ha tudsz kiindulási chunk/node id-t (pl. c1719), írd be: a felfedezés a gyenge modell gyenge pontja. FIGYELEM: a chunk-id nem stabil — újraindexelés eltolja. Ellenőrizd a get_chunk file_path-ját, mielőtt beírod.")
fi

# K1 — Konkrét forrás path vagy chunk-id megadva (abszolút path, env var path, vagy KB chunk)
if ! grep -qE '(/home/|get_chunk\(|c[0-9]{3,}|/sync/|\.go"|\.go`|\$\{CIC_|\$\{RELAY|\$\{WORKDIR)' "$SPEC"; then
    FAILURES+=("K1: nincs konkrét forrás path vagy KB chunk-id (pl. /home/..., \${CIC_RELAY_PATH}, get_chunk, c1719)")
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
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    for w in "${WARNINGS[@]}"; do
        echo "  WARN: $w"
    done
    echo ""
fi
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
    echo "Javítsd az input.md-t / meta.yaml-t, majd futtasd újra."
    exit 1
fi
