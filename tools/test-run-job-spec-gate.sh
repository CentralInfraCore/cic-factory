#!/usr/bin/env bash
#
# The spec gate in run-job.sh: /job-run has always made validate-spec.sh
# mandatory and forbidden starting an agent on NO-GO, but the script itself
# skipped it -- so the rule only held on the path nobody takes.
#
# Each case runs the real run-job.sh against a throwaway workdir. The runs stop
# on their own shortly after the gate (no git repo, no agent), which is enough:
# what is under test is whether the gate refuses, and what it records when it is
# deliberately bypassed.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    local desc="$1" want="$2" log="$3"
    if grep -qF -- "$want" "$log"; then echo "  PASS  $desc"; ((pass++))
    else echo "  FAIL  $desc — nem található: '$want'"; ((fail++)); fi
}
check_not_log() {
    local desc="$1" unwanted="$2" log="$3"
    if grep -qF -- "$unwanted" "$log"; then echo "  FAIL  $desc — ott van: '$unwanted'"; ((fail++))
    else echo "  PASS  $desc"; ((pass++)); fi
}

# A spec that passes validate-spec.sh: concrete source path (K1), an explicit
# forbidden shortcut (K3), a named output file (K4), and a required
# claim-evidence table (K8). No Go audit, so K7/K9 stay out of it.
mkjob() {
    local root="$1" good="$2"
    mkdir -p "$root/tools" "$root/jobs/t"
    cp "$SRC/run-job.sh" "$SRC/validate-spec.sh" "$SRC/update-index.sh" "$root/tools/"
    if [[ "$good" == "good" ]]; then
        cat > "$root/jobs/t/input.md" <<'EOF'
# Teszt job

## Forrás
Olvasd el: /home/example/repo/docs/thing.md

## Tiltott rövidítések
- fájl létezése ≠ implemented
- exit code 0 ≠ sikeres

## Output
`output/report.md` — tartalmazza:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
EOF
    else
        printf '# Teszt job\n\nCsinálj valamit.\n' > "$root/jobs/t/input.md"
    fi
    cat > "$root/jobs/t/meta.yaml" <<'EOF'
schema_version: "1.0"
job_id: "t"
status: "pending"
spec_gate: ""
agent:
  config_dir: ""
  model: "claude-sonnet-5"
timestamps:
  created: "2026-01-01T00:00:00Z"
  started: ""
  completed: ""
EOF
}

run_job() {
    local root="$1"; shift
    ( cd "$root" && bash tools/run-job.sh t "$@" ) >"$root/out.log" 2>&1
    echo $?
}
field() { grep "^$2:" "$1/jobs/t/meta.yaml" | head -1 | awk -F'"' '{print $2}'; }

echo "0. A fixture-ök a kaput valóban átengedik / megbuktatják"
T=$(mktemp -d); mkjob "$T" good
( cd "$T" && bash tools/validate-spec.sh t ) >/dev/null 2>&1
check "a 'good' spec GO" "0" "$?"
rm -rf "$T"
T=$(mktemp -d); mkjob "$T" bad
( cd "$T" && bash tools/validate-spec.sh t ) >/dev/null 2>&1
check "a 'bad' spec NO-GO" "1" "$?"
rm -rf "$T"

echo
echo "1. NO-GO spec → a runner nem indul"
T=$(mktemp -d); mkjob "$T" bad
check "exit 1" "1" "$(run_job "$T")"
check_log "  a kapura hivatkozik" "A spec-kapu NO-GO-t adott" "$T/out.log"
check_log "  felajánlja a menekülőutat" "--skip-spec-gate" "$T/out.log"
check "  a job pending marad" "pending" "$(field "$T" status)"
check "  a spec_gate érintetlen" "" "$(field "$T" spec_gate)"
check_not_log "  nem indult workspace-klónozás" "Workspace" "$T/out.log"
rm -rf "$T"

echo
echo "2. GO spec → a kapu átenged, és ezt rögzíti"
T=$(mktemp -d); mkjob "$T" good
run_job "$T" >/dev/null
check_log "  a kapu GO-t adott" "MECHANIKUS ELLENŐRZÉS: GO" "$T/out.log"
# A futás a git-lépésnél megáll (nincs repo), és a finalizer error-t ír — ez a
# helyes viselkedés, azt a test-run-job-finalizer.sh fedi. Itt az számít, hogy a
# pending → running átmenet egyáltalán megtörtént, vagyis a kapu átengedte.
check "  a pending → running átmenet lefutott" "1" \
    "$(grep -cE '^\s+started: "20' "$T/jobs/t/meta.yaml")"
check "  spec_gate: passed" "passed" "$(field "$T" spec_gate)"
rm -rf "$T"

echo
echo "3. --skip-spec-gate → NO-GO specen is elindul, de nyomot hagy"
T=$(mktemp -d); mkjob "$T" bad
run_job "$T" --skip-spec-gate >/dev/null
check_log "  hangosan figyelmeztet" "a gépi spec-kapu KIHAGYVA" "$T/out.log"
check_not_log "  a kapu nem is futott" "MECHANIKUS ELLENŐRZÉS" "$T/out.log"
check "  a NO-GO spec ellenére elindult" "1" \
    "$(grep -cE '^\s+started: "20' "$T/jobs/t/meta.yaml")"
check "  spec_gate: skipped — a review látja" "skipped" "$(field "$T" spec_gate)"
rm -rf "$T"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
