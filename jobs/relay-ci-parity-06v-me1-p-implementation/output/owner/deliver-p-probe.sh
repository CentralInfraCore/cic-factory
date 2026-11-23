#!/bin/bash
# deliver-p-probe.sh — OWNER-RUN. Prepares the throwaway probe branch LOCALLY. It does NOT push and does NOT
# open a PR: pushing a branch starts nothing, but opening the PR does (open-p-probe-pr.sh, separate GO).
#   APPROVED_FACTORY_SHA=<merge commit of the approved implementation PR> bash deliver-p-probe.sh
# The probe branch changes EXACTLY two files of the lab repository's main:
#   M .github/workflows/me1-evidence.yml        (P1: the protected workflow modified in place)
#   A .github/workflows/me1-evidence-twin.yml   (P2: a new workflow with the same name)
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
[ "$ORG" = "CIC-Security-Lab" ] || { echo "refusing: ORG is $ORG, not the lab" >&2; exit 1; }
: "${APPROVED_FACTORY_SHA:?set it to the merge commit of the approved implementation PR}"
FACTORY=${FACTORY:-/home/sinkog/sync/claude_factory/CIC/workdir/jobs/relay-ci-parity-01-inventory/workspace/cic-factory}
EXPECTED_MAIN_HEAD=${EXPECTED_MAIN_HEAD:-4d432f5e8250948af83ff909a7314eeddadb1c29}
BASE_BLOB=9030b6f1759297f344052ada7757ba22e80cd5af   # the protected workflow on main, the base P1 modifies
P1_BLOB=b5d21c2d6d99d87ef6e508bf85984fc35c400b80
P2_BLOB=35e27ba42a45cb1fec18c66ec7a519c5c16a2790
P1_SRC=${P1_SRC:-jobs/relay-ci-parity-06v-me1-p-implementation/output/payload/p1/.github/workflows/me1-evidence.yml}
P2_SRC=${P2_SRC:-jobs/relay-ci-parity-06v-me1-p-implementation/output/payload/p2/.github/workflows/me1-evidence-twin.yml}
REMOTE=${ME1_REMOTE:-git@github.com:$ORG/$X.git}
[ "$(git -C "$FACTORY" rev-parse "$APPROVED_FACTORY_SHA:$P1_SRC")" = "$P1_BLOB" ] || { echo "refusing: P1 blob on the approved factory commit differs" >&2; exit 1; }
[ "$(git -C "$FACTORY" rev-parse "$APPROVED_FACTORY_SHA:$P2_SRC")" = "$P2_BLOB" ] || { echo "refusing: P2 blob on the approved factory commit differs" >&2; exit 1; }
WORK=$(mktemp -d)
git clone -q "$REMOTE" "$WORK/repo"
[ "$(git -C "$WORK/repo" rev-parse HEAD)" = "$EXPECTED_MAIN_HEAD" ] || { echo "refusing: the lab main is $(git -C "$WORK/repo" rev-parse HEAD), not the approved $EXPECTED_MAIN_HEAD" >&2; exit 1; }
[ "$(git -C "$WORK/repo" rev-parse HEAD:.github/workflows/me1-evidence.yml)" = "$BASE_BLOB" ] || { echo "refusing: the protected workflow on main is not the approved base blob" >&2; exit 1; }
git -C "$WORK/repo" checkout -q -b p-probe
git -C "$FACTORY" show "$APPROVED_FACTORY_SHA:$P1_SRC" > "$WORK/repo/.github/workflows/me1-evidence.yml"
git -C "$FACTORY" show "$APPROVED_FACTORY_SHA:$P2_SRC" > "$WORK/repo/.github/workflows/me1-evidence-twin.yml"
[ "$(git hash-object "$WORK/repo/.github/workflows/me1-evidence.yml")" = "$P1_BLOB" ] || { echo "refusing: P1 blob mismatch after extraction" >&2; exit 1; }
[ "$(git hash-object "$WORK/repo/.github/workflows/me1-evidence-twin.yml")" = "$P2_BLOB" ] || { echo "refusing: P2 blob mismatch after extraction" >&2; exit 1; }
git -C "$WORK/repo" add .github/workflows/me1-evidence.yml .github/workflows/me1-evidence-twin.yml
CHANGED=$(git -C "$WORK/repo" diff --cached --name-status | sort)
WANT=$(printf 'A\t.github/workflows/me1-evidence-twin.yml\nM\t.github/workflows/me1-evidence.yml\n')
[ "$CHANGED" = "$WANT" ] || { echo "refusing: the probe changes more or other than the two approved files:" >&2; echo "$CHANGED" >&2; exit 1; }
git -C "$WORK/repo" commit -q -m "probe: P1 (protected workflow modified in place) and P2 (same-name workflow); NEVER merge"
echo "probe commit: $(git -C "$WORK/repo" rev-parse HEAD)"
echo "changed files vs main: $(git -C "$WORK/repo" diff --name-status HEAD~1 HEAD | tr '\n' ' ')"
echo "next (separate GO): git -C $WORK/repo push origin p-probe   (starts nothing), then open-p-probe-pr.sh PROBE_COMMIT (OPENS the measurement)"
