#!/bin/bash
# Fetch the evidence read-pk.py evaluates for ONE approved ATTEMPT of ONE run of pk-canary-channels.
# usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA ATTEMPT
#   OUTDIR must NOT exist (a fresh directory per run: no leftovers from an earlier run).
#   The attempt must be: this workflow, workflow_dispatch, completed/success, branch main,
#   head SHA = APPROVED_HEAD_SHA, in $ORG/$X, and either attempt 1 with no earlier attempt, or
#   attempt 2 whose attempt 1 was held (completed / action_required, zero jobs).
#   Otherwise nothing is fetched.
# read-only API calls; writes only to OUTDIR.
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
U="usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA ATTEMPT"
RUN_ID=${1:?$U}
OUT=${2:?$U}
HEAD=${3:?$U}
ATT=${4:?$U}
HERE=$(cd "$(dirname "$0")" && pwd)
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || { echo "refusing: run id is not numeric" >&2; exit 1; }
[[ "$ATT" =~ ^[0-9]+$ ]] || { echo "refusing: attempt is not numeric" >&2; exit 1; }
[ ! -e "$OUT" ] || { echo "refusing: $OUT already exists (use a new directory per run)" >&2; exit 1; }
mkdir -p "$OUT/artifact"
API="repos/$ORG/$X/actions/runs/$RUN_ID"
gh api "$API/attempts/$ATT" > "$OUT/.run.json"
# the state of every earlier attempt (status, conclusion, number of jobs)
echo "[]" > "$OUT/.prev.json"
for a in $(seq 1 $((ATT - 1))); do
  A=$(gh api "$API/attempts/$a" --jq '{run_attempt, status, conclusion}')
  J=$(gh api "$API/attempts/$a/jobs" --jq '.jobs | length')
  jq --argjson a "$A" --argjson j "$J" '. + [$a + {jobs: $j}]' "$OUT/.prev.json" > "$OUT/.prev.tmp" && mv "$OUT/.prev.tmp" "$OUT/.prev.json"
done
# validate BEFORE fetching anything else (a wrong run or attempt: refused, exit 1)
python3 -I "$HERE/read-pk.py" --check-run "$OUT/.run.json" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json"
gh run view "$RUN_ID" --repo "$ORG/$X" --attempt "$ATT" --log > "$OUT/log.txt"
JOB_ID=$(gh api "$API/attempts/$ATT/jobs" --jq '[.jobs[] | select(.name=="pk-channels")] | if length==1 then .[0].id else empty end')
: "${JOB_ID:?no single pk-channels job in this attempt}"
gh api "repos/$ORG/$X/check-runs/$JOB_ID/annotations" > "$OUT/annotations.json"
N_ART=$(gh api "$API/artifacts" --jq '[.artifacts[] | select(.name=="pk-channels" and .workflow_run.id=='"$RUN_ID"' and .workflow_run.head_sha=="'"$HEAD"'")] | length')
[ "$N_ART" = 1 ] || { echo "refusing: expected exactly one pk-channels artifact of this run and head, found $N_ART" >&2; exit 1; }
gh run download "$RUN_ID" --repo "$ORG/$X" -n pk-channels -D "$OUT/artifact"
python3 -I "$HERE/read-pk.py" --write-manifest "$OUT" "$OUT/.run.json" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json"
rm -f "$OUT/.run.json" "$OUT/.prev.json"
echo "fetched run $RUN_ID attempt $ATT into $OUT; the job summary is NOT fetched (see read-pk.py --attach-summary)"
