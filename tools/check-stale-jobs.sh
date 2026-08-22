#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-stale-jobs.sh [--quiet]
#
# Reports jobs that still claim "running" past their lease deadline.
#
# The running state is committed and pushed before the agent starts. If the
# wrapper then dies without correcting it -- SIGKILL, a lost machine, a failed
# push -- the remote keeps advertising a job that is not running, and
# jobs/index.yaml is generated from those same values, so the state map is wrong
# too.
#
# run-job.sh writes lease_expires alongside the running status, so the deadline
# travels out with it. That is what makes this checkable from the repository
# alone: nothing here depends on the dead process reporting anything.
#
# Exit 0 = nothing stale, exit 1 = at least one stale job.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
QUIET=0
[[ "${1:-}" == "--quiet" ]] && QUIET=1

NOW=$(date -u +%s)
STALE=0
NO_LEASE=0

for meta in "$WORKDIR"/jobs/*/meta.yaml; do
    [[ -f "$meta" ]] || continue
    status=$(grep '^status:' "$meta" | head -1 | sed 's/^status:[[:space:]]*//; s/^"//; s/"$//')
    [[ "$status" == "running" ]] || continue

    job=$(basename "$(dirname "$meta")")
    lease=$(grep '^lease_expires:' "$meta" | head -1 | sed 's/^lease_expires:[[:space:]]*//; s/^"//; s/"$//')

    if [[ -z "$lease" ]]; then
        NO_LEASE=$((NO_LEASE + 1))
        [[ "$QUIET" -eq 1 ]] || echo "?  $job — running, de nincs lease. A mező bevezetése előtti futás: nem eldönthető, elakadt-e."
        continue
    fi

    # An unparseable deadline is reported rather than ignored: a lease nobody can
    # read is the same as no lease, and silently skipping it would hide the job.
    if ! exp=$(date -u -d "$lease" +%s 2>/dev/null); then
        STALE=$((STALE + 1))
        [[ "$QUIET" -eq 1 ]] || echo "!  $job — running, és a lease értelmezhetetlen: '$lease'"
        continue
    fi

    if [[ "$NOW" -gt "$exp" ]]; then
        STALE=$((STALE + 1))
        [[ "$QUIET" -eq 1 ]] || {
            echo "!  $job — ELAKADT: 'running', de a lease lejárt $lease-kor"
            echo "     ($(( (NOW - exp) / 60 )) perce). A wrapper meghalt anélkül, hogy javította volna."
        }
    fi
done

if [[ "$QUIET" -eq 1 ]]; then
    echo "$STALE"
else
    echo ""
    if [[ "$STALE" -eq 0 ]]; then
        echo "Nincs elakadt job.$( [[ "$NO_LEASE" -gt 0 ]] && echo " ($NO_LEASE lease nélküli futás nem eldönthető.)" )"
    else
        echo "$STALE elakadt job. Nézd meg, fut-e még valóban az agent, mielőtt bármelyiket újraindítod."
    fi
fi

[[ "$STALE" -eq 0 ]]
