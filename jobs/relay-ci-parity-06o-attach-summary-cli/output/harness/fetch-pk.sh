#!/bin/bash
# Fetch the evidence read-pk.py evaluates for ONE approved ATTEMPT of ONE run of pk-canary-channels.
# usage: fetch-pk.sh RUN_ID OUTDIR APPROVED_HEAD_SHA ATTEMPT
#   OUTDIR must NOT exist (a fresh directory per run: no leftovers from an earlier run).
#   The attempt must be: this workflow, workflow_dispatch, completed/success, branch main,
#   head SHA = APPROVED_HEAD_SHA, in $ORG/$X, and either attempt 1 with no earlier attempt, or
#   attempt 2 whose attempt 1 was held (completed / action_required, zero jobs).
#   The run's CURRENT attempt must equal ATTEMPT before and after the fetch (a later attempt, or
#   a change of the attempt while fetching, is refused). The artifact is chosen by its unique id:
#   the one artifact created inside THIS attempt's time window. Otherwise nothing is accepted.
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
RP="python3 -I $HERE/read-pk.py"
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || { echo "refusing: run id is not numeric" >&2; exit 1; }
[[ "$ATT" =~ ^[0-9]+$ ]] || { echo "refusing: attempt is not numeric" >&2; exit 1; }
[ ! -e "$OUT" ] || { echo "refusing: $OUT already exists (use a new directory per run)" >&2; exit 1; }
mkdir -p "$OUT/artifact"
API="repos/$ORG/$X/actions/runs/$RUN_ID"

# the run's current attempt must be the one we fetch (BEFORE gathering anything)
CUR=$(gh api "$API" --jq .run_attempt)
[ "$CUR" = "$ATT" ] || { echo "refusing: the run's current attempt is $CUR, not $ATT" >&2; exit 1; }
gh api "$API/attempts/$ATT" > "$OUT/.run.json"
UPD=$(jq -r .updated_at "$OUT/.run.json")
# the state of every earlier attempt (status, conclusion, number of jobs)
echo "[]" > "$OUT/.prev.json"
for a in $(seq 1 $((ATT - 1))); do
  A=$(gh api "$API/attempts/$a" --jq '{run_attempt, status, conclusion}')
  J=$(gh api "$API/attempts/$a/jobs" --jq '.jobs | length')
  jq --argjson a "$A" --argjson j "$J" '. + [$a + {jobs: $j}]' "$OUT/.prev.json" > "$OUT/.prev.tmp" && mv "$OUT/.prev.tmp" "$OUT/.prev.json"
done
# validate the run BEFORE fetching anything else (a wrong run or attempt: refused, exit 1)
$RP --check-run "$OUT/.run.json" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json"

gh run view "$RUN_ID" --repo "$ORG/$X" --attempt "$ATT" --log > "$OUT/log.txt"
JOB_ID=$(gh api "$API/attempts/$ATT/jobs" --jq '[.jobs[] | select(.name=="pk-channels")] | if length==1 then .[0].id else empty end')
: "${JOB_ID:?no single pk-channels job in this attempt}"
gh api "repos/$ORG/$X/check-runs/$JOB_ID/annotations" > "$OUT/annotations.json"

# the artifact: by its unique id, the one created inside this attempt's window
gh api "$API/artifacts" > "$OUT/.arts.json"
ART_ID=$($RP --pick-artifact "$OUT/.run.json" "$OUT/.arts.json" "$HEAD")
gh api "repos/$ORG/$X/actions/artifacts/$ART_ID/zip" > "$OUT/.artifact.zip"
ZIP_SHA=$(sha256sum "$OUT/.artifact.zip" | cut -d' ' -f1)
python3 -I -m zipfile -e "$OUT/.artifact.zip" "$OUT/artifact"

# the attempt must not have changed while we fetched (AFTER gathering)
CUR2=$(gh api "$API" --jq .run_attempt)
UPD2=$(gh api "$API/attempts/$ATT" --jq .updated_at)
[ "$CUR2" = "$ATT" ] && [ "$UPD2" = "$UPD" ] || { echo "refusing: the run changed while fetching (attempt $CUR2, updated_at $UPD2 vs $UPD)" >&2; exit 1; }

$RP --write-manifest "$OUT" "$OUT/.run.json" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json" "$OUT/.arts.json" "$ZIP_SHA"
rm -f "$OUT/.run.json" "$OUT/.prev.json" "$OUT/.prev.tmp" "$OUT/.arts.json" "$OUT/.artifact.zip"
echo "fetched run $RUN_ID attempt $ATT artifact $ART_ID into $OUT; the job summary is NOT fetched (see read-pk.py --attach-summary)"
