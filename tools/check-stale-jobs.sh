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
    job=$(basename "$(dirname "$meta")")

    # `s/"$//` does not match a line with a trailing comment, so
    # `status: "running" # agent-01` parsed as `running" # agent-01` and the
    # job was skipped -- invisible to the very check meant to surface it (#29).
    # meta-get.sh reads it with a YAML parser instead.
    rc=0; status=$(bash "$WORKDIR/tools/meta-get.sh" "$meta" status 2>/dev/null) || rc=$?
    if [[ "$rc" -ne 0 ]]; then
        # The same reasoning the lease already used: a status nobody can read is
        # not a reason to skip the job, it is a reason to report it.
        STALE=$((STALE + 1))
        [[ "$QUIET" -eq 1 ]] || echo "!  $job — a meta.yaml status mezője nem olvasható. Nem eldönthető, fut-e."
        continue
    fi
    [[ "$status" == "running" ]] || continue

    lease=$(bash "$WORKDIR/tools/meta-get.sh" "$meta" lease_expires 2>/dev/null) || lease=""

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
