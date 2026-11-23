#!/bin/bash
# open-p-probe-pr.sh — OWNER-RUN. OPENING THE PROBE PR IS THE START OF THE MEASUREMENT: the pull_request event
# starts three runs (lab-gate-pr, P1, P2). It needs its own explicit GO, and it opens exactly ONE PR, once.
#   ME1_I_HAVE_THE_GO=yes bash open-p-probe-pr.sh PROBE_COMMIT_SHA
# The PR is NEVER merged: the owner closes it after the measurement. A held run is approved by the owner in
# the web UI (same run, a new attempt); there is no automatic re-run.
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
[ "$ORG" = "CIC-Security-Lab" ] || { echo "refusing: ORG is $ORG, not the lab" >&2; exit 1; }
[ "${ME1_I_HAVE_THE_GO:-}" = yes ] || { echo "refusing: this opens the measurement; set ME1_I_HAVE_THE_GO=yes only with the owner's explicit GO" >&2; exit 1; }
PROBE=${1:?usage: open-p-probe-pr.sh PROBE_COMMIT_SHA}
[[ "$PROBE" =~ ^[0-9a-f]{40}$ ]] || { echo "refusing: the probe commit is not a 40-hex SHA" >&2; exit 1; }
EXPECTED_MAIN_HEAD=${EXPECTED_MAIN_HEAD:-4d432f5e8250948af83ff909a7314eeddadb1c29}
STATE=${P_PROBE_STATE:-$HOME/.cache/ci-lab/p-probe.state}
REPO="$ORG/$X"
[ ! -e "$STATE" ] || { echo "refusing: the probe PR was already opened ($(tr '\n' ' ' < "$STATE")); no second opening" >&2; exit 1; }
[ "$(gh api "repos/$REPO/branches/main" --jq .commit.sha)" = "$EXPECTED_MAIN_HEAD" ] || { echo "refusing: the lab main is not the approved $EXPECTED_MAIN_HEAD" >&2; exit 1; }
[ "$(gh api "repos/$REPO/branches/p-probe" --jq .commit.sha)" = "$PROBE" ] || { echo "refusing: the remote p-probe is not at $PROBE" >&2; exit 1; }
[ "$(gh pr list --repo "$REPO" --head p-probe --state all --json number --jq length)" = 0 ] || { echo "refusing: a PR from p-probe already exists" >&2; exit 1; }
CHANGED=$(gh api "repos/$REPO/compare/main...p-probe" --jq '[.files[] | "\(.status) \(.filename)"] | sort | join(",")')
WANT="added .github/workflows/me1-evidence-twin.yml,modified .github/workflows/me1-evidence.yml"
[ "$CHANGED" = "$WANT" ] || { echo "refusing: the probe branch differs from main in other than the two approved files: $CHANGED" >&2; exit 1; }
echo "dispatched_at=$(date -u +%Y-%m-%dT%H:%M:%SZ) probe=$PROBE main=$EXPECTED_MAIN_HEAD" > "$STATE"
gh pr create --repo "$REPO" --base main --head p-probe --title "probe: P1 and P2 (measurement, NEVER merge)" \
  --body "M-E1 P-a/P-b measurement probe. Never merge; the owner closes it after the measurement."
echo "opened. Expect three runs (lab-gate-pr, P1, P2); approve a held run in the web UI if you decide so; do not open again."
