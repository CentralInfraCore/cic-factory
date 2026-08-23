#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-stale-jobs.sh against fixtures that are stuck on purpose. Running it
# against the real jobs proves almost nothing: none of them are "running", so a
# detector that never fires would look identical to one that works.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

mkroot() { local r; r=$(mktemp -d); mkdir -p "$r/tools"
           cp "$SRC/check-stale-jobs.sh" "$SRC/meta-get.sh" "$r/tools/"; echo "$r"; }
addjob() {
    local root="$1" job="$2" status="$3" lease="$4"
    mkdir -p "$root/jobs/$job"
    cat > "$root/jobs/$job/meta.yaml" <<EOF
job_id: "$job"
status: "$status"
lease_expires: "$lease"
EOF
}
run() { bash "$1/tools/check-stale-jobs.sh" >"$1/out.log" 2>&1; echo $?; }

PAST=$(date -u -d '-2 hours' +"%Y-%m-%dT%H:%M:%SZ")
FUTURE=$(date -u -d '+2 hours' +"%Y-%m-%dT%H:%M:%SZ")

echo "1. Lejárt lease + running → elakadt"
R=$(mkroot); addjob "$R" stuck running "$PAST"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a jobot" "stuck — ELAKADT" "$R/out.log"
check_log "  megmondja mennyi ideje" "perce" "$R/out.log"
rm -rf "$R"

echo
echo "2. Élő lease + running → nem elakadt"
R=$(mkroot); addjob "$R" alive running "$FUTURE"
check "exit 0" "0" "$(run "$R")"
check_log "  ezt ki is mondja" "Nincs elakadt job" "$R/out.log"
rm -rf "$R"

echo
echo "3. Csak a running állapotot nézi"
# Egy lezárt job lejárt lease-szel nem elakadt — a lease a futásról szól.
R=$(mkroot)
addjob "$R" closed done "$PAST"
addjob "$R" waiting awaiting_review "$PAST"
addjob "$R" failed error "$PAST"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "4. Lease nélküli running → jelenti, de nem nevezi elakadtnak"
# Az 51 régi job pontosan ilyen. Elakadtnak jelölni őket hamis riasztás lenne,
# elhallgatni viszont azt sugallná, hogy ellenőrizve vannak.
R=$(mkroot); addjob "$R" legacy running ""
check "exit 0" "0" "$(run "$R")"
check_log "  kimondja, hogy nem eldönthető" "nem eldönthető" "$R/out.log"
rm -rf "$R"

echo
echo "5. Értelmezhetetlen lease → elakadtnak számít"
# Egy lease, amit senki nem tud elolvasni, annyit ér mint a semmi — de csendben
# átugrani annyi lenne, mint elrejteni a jobot.
R=$(mkroot); addjob "$R" garbled running "nem-egy-datum"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi az okot" "értelmezhetetlen" "$R/out.log"
rm -rf "$R"

echo
echo "6. Több job, vegyesen"
R=$(mkroot)
addjob "$R" s1 running "$PAST"
addjob "$R" s2 running "$PAST"
addjob "$R" ok running "$FUTURE"
addjob "$R" fin done "$PAST"
check "exit 1" "1" "$(run "$R")"
check "  --quiet a darabszámot adja" "2" "$(bash "$R/tools/check-stale-jobs.sh" --quiet 2>/dev/null)"
rm -rf "$R"

echo
echo "Sorvégi komment nem rejtheti el a futó jobot (#29)"
# `s/"$//` nem illeszkedik kommentelt sorra, tehát a régi olvasó
# `running" # agent-01`-et látott, a `[[ == running ]]` elbukott, és a
# `continue` kihagyta a jobot -- pont azt, amiért a checker létezik.
R=$(mkroot); mkdir -p "$R/jobs/hidden"
cat > "$R/jobs/hidden/meta.yaml" <<EOF
job_id: "hidden"
status: "running" # agent-01
lease_expires: "$PAST"
EOF
check "exit 1" "1" "$(run "$R")"
check_log "  megtalálja" "hidden — ELAKADT" "$R/out.log"
rm -rf "$R"

echo
echo "Idézőjel nélküli status ugyanígy látszik"
R=$(mkroot); mkdir -p "$R/jobs/bare"
cat > "$R/jobs/bare/meta.yaml" <<EOF
job_id: "bare"
status: running
lease_expires: "$PAST"
EOF
check "exit 1" "1" "$(run "$R")"
check_log "  megtalálja" "bare — ELAKADT" "$R/out.log"
rm -rf "$R"

echo
echo "Olvashatatlan status: jelenteni kell, nem kihagyni"
# Ugyanaz az elv, amit a lease már követett: amit senki nem tud elolvasni, az
# nem ok a kihagyásra.
R=$(mkroot); mkdir -p "$R/jobs/broken"
printf 'job_id: "broken"\nstatus: "running\nagent:\n  model: "opus\n' > "$R/jobs/broken/meta.yaml"
check "exit 1" "1" "$(run "$R")"
check_log "  jelenti" "nem olvasható" "$R/out.log"
rm -rf "$R"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
