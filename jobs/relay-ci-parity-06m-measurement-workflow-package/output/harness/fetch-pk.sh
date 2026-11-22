#!/bin/bash
# Fetch the evidence read-pk.py evaluates for ONE approved run of pk-canary-channels.
# usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA
#   OUTDIR must NOT exist (a fresh directory per run: no leftovers from an earlier run).
#   The run must be: this workflow, workflow_dispatch, completed/success, branch main,
#   head SHA = APPROVED_HEAD_SHA, attempt 1, in $ORG/$X. Otherwise nothing is fetched.
# read-only API calls; writes only to OUTDIR.
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
RUN_ID=${1:?usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA}
OUT=${2:?usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA}
HEAD=${3:?usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA}
HERE=$(cd "$(dirname "$0")" && pwd)
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || { echo "refusing: run id is not numeric" >&2; exit 1; }
[ ! -e "$OUT" ] || { echo "refusing: $OUT already exists (use a new directory per run)" >&2; exit 1; }
mkdir -p "$OUT/artifact"
gh api "repos/$ORG/$X/actions/runs/$RUN_ID" > "$OUT/.run.json"
# validate the run BEFORE fetching anything else (a wrong run: refused, exit 1)
python3 -I "$HERE/read-pk.py" --check-run "$OUT/.run.json" "$ORG/$X" "$HEAD"
gh run view "$RUN_ID" --repo "$ORG/$X" --attempt 1 --log > "$OUT/log.txt"
JOB_ID=$(gh api "repos/$ORG/$X/actions/runs/$RUN_ID/attempts/1/jobs" --jq '[.jobs[] | select(.name=="pk-channels")] | if length==1 then .[0].id else empty end')
: "${JOB_ID:?no single pk-channels job in attempt 1}"
gh api "repos/$ORG/$X/check-runs/$JOB_ID/annotations" > "$OUT/annotations.json"
N_ART=$(gh api "repos/$ORG/$X/actions/runs/$RUN_ID/artifacts" --jq '[.artifacts[] | select(.name=="pk-channels" and .workflow_run.id=='"$RUN_ID"' and .workflow_run.head_sha=="'"$HEAD"'")] | length')
[ "$N_ART" = 1 ] || { echo "refusing: expected exactly one pk-channels artifact of this run and head, found $N_ART" >&2; exit 1; }
gh run download "$RUN_ID" --repo "$ORG/$X" -n pk-channels -D "$OUT/artifact"
python3 -I "$HERE/read-pk.py" --write-manifest "$OUT" "$OUT/.run.json" "$ORG/$X" "$HEAD"
rm -f "$OUT/.run.json"
echo "fetched run $RUN_ID into $OUT; the job summary is NOT fetched (see read-pk.py --attach-summary)"
