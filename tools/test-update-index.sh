#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# update-index.sh — eddig nem volt saját tesztje. Közvetve lefutott minden
# lifecycle-suite-ban, de tartalmi assertion nélkül: senki nem mérte, hogy a
# generált index azt mondja-e, amit a meta.
#
# Az esetek nagy része arra megy, amit a régi regexes olvasó elrontott, plusz
# az elakadt jobok megjelölésére (#19).

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}

PAST=$(date -u -d '-2 hours' +"%Y-%m-%dT%H:%M:%SZ")
FUTURE=$(date -u -d '+2 hours' +"%Y-%m-%dT%H:%M:%SZ")

mkroot() { local r; r=$(mktemp -d); mkdir -p "$r/tools" "$r/jobs"
           cp "$SRC/update-index.sh" "$r/tools/"; echo "$r"; }
addjob() { mkdir -p "$1/jobs/$2"; printf '%b' "$3" > "$1/jobs/$2/meta.yaml"; }
run()    { bash "$1/tools/update-index.sh" >"$1/out.log" 2>&1; echo $?; }

# A generált indexet valódi parserrel olvassuk vissza -- ha nem érvényes YAML,
# az itt derül ki, nem a következő olvasónál.
q() { python3 - "$1" "$2" <<'PYEOF'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
path = sys.argv[2].split(".")
node = doc
for p in path:
    if isinstance(node, list):
        node = next((x for x in node if str(x.get("id")) == p), None)
    elif isinstance(node, dict):
        node = node.get(p)
    else:
        node = None
    if node is None:
        print(""); sys.exit(0)
print(node if not isinstance(node, (dict, list)) else "<block>")
PYEOF
}

echo "0. Alapeset — a generált index érvényes YAML"
R=$(mkroot)
addjob "$R" a 'job_id: "a"\nlevel: "repo"\nstatus: "done"\ntimestamps:\n  created: "C"\n'
check "exit 0" "0" "$(run "$R")"
check "  a job szerepel" "done" "$(q "$R/jobs/index.yaml" 'jobs.a.status')"
check "  a totals megvan" "1" "$(q "$R/jobs/index.yaml" 'totals.jobs')"
rm -rf "$R"

echo
echo "Sorvégi komment a status-on (#29 az index oldalán)"
# A régi `^status:\s*"?([^"\n]+)"?` az egész maradékot vitte: az indexben
# `running # agent-01` jelent meg státuszként.
R=$(mkroot)
addjob "$R" a "job_id: \"a\"\nstatus: running # agent-01\nlease_expires: \"$FUTURE\"\ntimestamps:\n  created: \"C\"\n"
run "$R" >/dev/null
check "a státusz tiszta" "running" "$(q "$R/jobs/index.yaml" 'jobs.a.status')"
rm -rf "$R"

echo
echo "Szekció-vakság — a mező NEVE nem elég, a helye számít"
# A régi read_nested az ELSŐ azonos nevű behúzott mezőt vitte, bárhol állt.
R=$(mkroot)
addjob "$R" a 'job_id: "a"\nstatus: "done"\ntimestamps:\n  created: "C"\nagent:\n  model: "opus"\n  cost_usd: "NEM-EZ"\n  turns: "999"\nusage:\n  cost_usd: "2.50"\n  turns: "7"\n'
run "$R" >/dev/null
check "cost_usd a usage-ból" "2.50" "$(q "$R/jobs/index.yaml" 'jobs.a.cost_usd')"
check "  turns a usage-ból" "7" "$(q "$R/jobs/index.yaml" 'jobs.a.turns')"
check "  model az agentből" "opus" "$(q "$R/jobs/index.yaml" 'jobs.a.model')"
rm -rf "$R"

echo
echo "Elakadt job megjelölése (#19)"
# Eddig csak akkor derült ki, ha valaki begépelte a check-stale-jobs.sh-t.
R=$(mkroot)
addjob "$R" stuck "job_id: \"stuck\"\nstatus: \"running\"\nlease_expires: \"$PAST\"\ntimestamps:\n  created: \"C\"\n"
addjob "$R" alive "job_id: \"alive\"\nstatus: \"running\"\nlease_expires: \"$FUTURE\"\ntimestamps:\n  created: \"C\"\n"
addjob "$R" finished 'job_id: "finished"\nstatus: "done"\nlease_expires: ""\ntimestamps:\n  created: "C"\n'
run "$R" >/dev/null
check "a lejárt lease stale" "stale" "$(q "$R/jobs/index.yaml" 'jobs.stuck.stale')"
check "  az élő lease nem" "" "$(q "$R/jobs/index.yaml" 'jobs.alive.stale')"
check "  a befejezett sem" "" "$(q "$R/jobs/index.yaml" 'jobs.finished.stale')"
check "  a totals számolja" "1" "$(q "$R/jobs/index.yaml" 'totals.stale_jobs')"
check "  a kimenet is mondja" "1" "$(grep -c 'STALE' "$R/out.log")"
rm -rf "$R"

echo
echo "Lease nélküli és értelmezhetetlen lease-ű futó job"
R=$(mkroot)
addjob "$R" nolease 'job_id: "nolease"\nstatus: "running"\ntimestamps:\n  created: "C"\n'
addjob "$R" bad 'job_id: "bad"\nstatus: "running"\nlease_expires: "tegnap"\ntimestamps:\n  created: "C"\n'
run "$R" >/dev/null
check "lease nélkül jelölve" "no-lease" "$(q "$R/jobs/index.yaml" 'jobs.nolease.stale')"
check "  olvashatatlan lease jelölve" "unreadable-lease" "$(q "$R/jobs/index.yaml" 'jobs.bad.stale')"
# A no-lease nem elakadás: a mező bevezetése előtti futásból is származhat.
check "  a stale_jobs csak az igazolhatót számolja" "1" "$(q "$R/jobs/index.yaml" 'totals.stale_jobs')"
rm -rf "$R"

echo
echo "Olvashatatlan meta — bekerül megjelölve, nem tűnik el"
# Kihagyva a job láthatatlan lenne, pont amikor baj van vele.
R=$(mkroot)
addjob "$R" ok 'job_id: "ok"\nstatus: "done"\ntimestamps:\n  created: "C"\n'
addjob "$R" broken 'job_id: "broken"\nstatus: "lezaratlan\n'
addjob "$R" dup 'job_id: "dup"\nstatus: "a"\nstatus: "b"\n'
check "exit 0 — a generálás nem áll meg" "0" "$(run "$R")"
check "  az ép job megvan" "done" "$(q "$R/jobs/index.yaml" 'jobs.ok.status')"
check "  a hibás is bekerült" "unreadable" "$(q "$R/jobs/index.yaml" 'jobs.broken.status')"
check "  a duplikált kulcsú is" "unreadable" "$(q "$R/jobs/index.yaml" 'jobs.dup.status')"
check "  a totals számolja" "2" "$(q "$R/jobs/index.yaml" 'totals.unreadable_metas')"
check "  mindkettő egysoros indoklást kapott" "2" "$(grep -c '^    error: "' "$R/jobs/index.yaml")"
rm -rf "$R"

echo
echo "A költség-összegzés a usage-ból jön"
R=$(mkroot)
addjob "$R" a 'job_id: "a"\nstatus: "done"\ntimestamps:\n  created: "C"\nusage:\n  cost_usd: "1.25"\n'
addjob "$R" b 'job_id: "b"\nstatus: "done"\ntimestamps:\n  created: "C"\nusage:\n  cost_usd: "2.75"\n'
addjob "$R" c 'job_id: "c"\nstatus: "pending"\ntimestamps:\n  created: "C"\n'
run "$R" >/dev/null
check "összeg" "4.0000" "$(q "$R/jobs/index.yaml" 'totals.cost_usd')"
check "  árazott jobok" "2" "$(q "$R/jobs/index.yaml" 'totals.priced_jobs')"
check "  összes job" "3" "$(q "$R/jobs/index.yaml" 'totals.jobs')"
rm -rf "$R"

echo
echo "job_id hiányában a könyvtárnév az azonosító"
R=$(mkroot)
addjob "$R" nevenincs 'status: "done"\ntimestamps:\n  created: "C"\n'
run "$R" >/dev/null
check "az id a könyvtárnév" "done" "$(q "$R/jobs/index.yaml" 'jobs.nevenincs.status')"
rm -rf "$R"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
