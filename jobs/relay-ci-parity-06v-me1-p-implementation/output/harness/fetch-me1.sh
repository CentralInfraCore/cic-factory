#!/bin/bash
# Fetch the M-E1 evidence for ONE approved ATTEMPT of ONE run of me1-evidence.yml.
# usage: fetch-me1.sh RUN_ID OUTDIR APPROVED_HEAD_SHA ATTEMPT [PROFILE]
#   PROFILE main (default): the protected workflow_dispatch run on main. PROFILE pr: a pull_request run of
#   the throwaway probe PR (the path and head_branch shapes are recorded, not asserted; APPROVED_HEAD_SHA is
#   then the PR head the run belongs to). Both profiles also fetch the checks-API listing of that commit
#   into api/check-runs.json: DISCOVERY and cross-check only, never the decision policy.
#   OUTDIR must NOT exist. The attempt must be: this workflow, workflow_dispatch, completed/success,
#   branch main, head SHA = APPROVED_HEAD_SHA, in $ORG/$X, and either attempt 1 with no earlier attempt
#   or attempt 2 whose attempt 1 was held (completed / action_required, zero jobs). The run's CURRENT
#   attempt must equal ATTEMPT before and after the fetch. The artifact is chosen by its unique id: the
#   one created inside THIS attempt's time window. The issuer's public keys are NOT fetched here: they
#   are the trust root and must stay apart from the evidence (fetch-jwks.sh, a separate file OUTSIDE
#   OUTDIR, given to read-me1.py with --trusted-jwks).
# read-only calls; writes only to OUTDIR.
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
U="usage: fetch-me1.sh RUN_ID OUTDIR APPROVED_HEAD_SHA ATTEMPT [main|pr]"
RUN_ID=${1:?$U}
OUT=${2:?$U}
HEAD=${3:?$U}
ATT=${4:?$U}
PROFILE=${5:-main}
[ "$PROFILE" = main ] || [ "$PROFILE" = pr ] || { echo "refusing: profile must be main or pr" >&2; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
RM="python3 -I $HERE/read-me1.py"
[[ "$RUN_ID" =~ ^[0-9]+$ ]] || { echo "refusing: run id is not numeric" >&2; exit 1; }
[[ "$ATT" =~ ^[0-9]+$ ]] || { echo "refusing: attempt is not numeric" >&2; exit 1; }
[ ! -e "$OUT" ] || { echo "refusing: $OUT already exists (use a new directory per run)" >&2; exit 1; }
mkdir -p "$OUT/artifact" "$OUT/api"
API="repos/$ORG/$X/actions/runs/$RUN_ID"

CUR=$(gh api "$API" --jq .run_attempt)
[ "$CUR" = "$ATT" ] || { echo "refusing: the run's current attempt is $CUR, not $ATT" >&2; exit 1; }
gh api "$API/attempts/$ATT" > "$OUT/api/run.json"
UPD=$(jq -r .updated_at "$OUT/api/run.json")
echo "[]" > "$OUT/.prev.json"
for a in $(seq 1 $((ATT - 1))); do
  A=$(gh api "$API/attempts/$a" --jq '{run_attempt, status, conclusion}')
  J=$(gh api "$API/attempts/$a/jobs" --jq '.jobs | length')
  jq --argjson a "$A" --argjson j "$J" '. + [$a + {jobs: $j}]' "$OUT/.prev.json" > "$OUT/.prev.tmp" && mv "$OUT/.prev.tmp" "$OUT/.prev.json"
done
$RM --check-run "$OUT/api/run.json" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json" "$PROFILE"

gh api "$API/attempts/$ATT/jobs" > "$OUT/api/jobs.json"
# discovery and cross-check source: the check-runs of the commit this run belongs to (never the decision policy)
gh api "repos/$ORG/$X/commits/$HEAD/check-runs?per_page=100" > "$OUT/api/check-runs.json"
gh api "$API/artifacts" > "$OUT/.arts.json"
ART_ID=$($RM --pick-artifact "$OUT/api/run.json" "$OUT/.arts.json" "$HEAD")
gh api "repos/$ORG/$X/actions/artifacts/$ART_ID/zip" > "$OUT/.artifact.zip"
ZIP_SHA=$(sha256sum "$OUT/.artifact.zip" | cut -d' ' -f1)
python3 -I -m zipfile -e "$OUT/.artifact.zip" "$OUT/artifact"

CUR2=$(gh api "$API" --jq .run_attempt)
UPD2=$(gh api "$API/attempts/$ATT" --jq .updated_at)
[ "$CUR2" = "$ATT" ] && [ "$UPD2" = "$UPD" ] || { echo "refusing: the run changed while fetching (attempt $CUR2, updated_at $UPD2 vs $UPD)" >&2; exit 1; }

$RM --write-manifest "$OUT" "$ORG/$X" "$HEAD" "$ATT" "$OUT/.prev.json" "$OUT/.arts.json" "$ZIP_SHA" "$PROFILE"
rm -f "$OUT/.prev.json" "$OUT/.prev.tmp" "$OUT/.arts.json" "$OUT/.artifact.zip"
echo "fetched run $RUN_ID attempt $ATT artifact $ART_ID into $OUT"
