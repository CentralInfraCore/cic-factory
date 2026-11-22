#!/bin/bash
# Fetch the files read-pk.py evaluates for one run of pk-canary-channels.
# usage: fetch-pk.sh RUN_ID OUTDIR      (read-only API calls; writes only to OUTDIR)
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
RUN_ID=${1:?usage: fetch-pk.sh RUN_ID OUTDIR}
OUT=${2:?usage: fetch-pk.sh RUN_ID OUTDIR}
WF=$(gh api "repos/$ORG/$X/actions/runs/$RUN_ID" --jq .path)
if [ "$WF" != ".github/workflows/pk-canary-channels.yml" ]; then echo "refusing: run $RUN_ID is workflow $WF" >&2; exit 1; fi
mkdir -p "$OUT/artifact"
gh run view "$RUN_ID" --repo "$ORG/$X" --log > "$OUT/log.txt"
JOB_ID=$(gh api "repos/$ORG/$X/actions/runs/$RUN_ID/jobs" --jq '.jobs[] | select(.name=="pk-channels") | .id')
: "${JOB_ID:?no pk-channels job in run}"
gh api "repos/$ORG/$X/check-runs/$JOB_ID/annotations" > "$OUT/annotations.json"
gh run download "$RUN_ID" --repo "$ORG/$X" -n pk-channels -D "$OUT/artifact"
echo "fetched run $RUN_ID into $OUT (summary.txt is not fetched: the job summary is not read through the API here)"
