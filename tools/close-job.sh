#!/usr/bin/env bash
# close-job.sh <job-id> [--dry-run]
#
# The only legal awaiting_review → done transition.
#
# Until this existed, `done` was a convention: job-close.md described the
# conditions and nothing enforced them. The runner had already lost the ability
# to write `done` (it leaves awaiting_review), but any other process, or anyone
# with an editor, could still close a job with no gate run and no review.
#
# Exit 0 = closed, exit 1 = refused. A refusal names the condition that failed.
#
#   C1  jobs/<job-id>/meta.yaml exists
#   C2  its status is exactly awaiting_review
#   C3  validate-output.sh <job-id> exits GO
#   C4  jobs/<job-id>/review.md exists, is non-empty, and carries no placeholder
#
# C4 exists because validate-output.sh deliberately excludes review.md from its
# own scan (see its O1 find filter) -- so nothing checked the review artifact at
# all. An empty or TODO-riddled review.md is worth exactly as much as no review,
# which is the thing job-close.md was written to prevent.
#
# What this script does NOT do: commit and push. The commit is Vault-signed and
# is the trust artifact; job-close.md step 6 owns it, because it also knows which
# sub-job specs travel with the job. This script decides legality and performs
# the state change; publishing it stays with the orchestrator.

set -euo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"

JOB_ID=""
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -*) echo "Unknown flag: $arg" >&2; exit 1 ;;
        *) JOB_ID="$arg" ;;
    esac
done

if [[ -z "$JOB_ID" ]]; then
    echo "Usage: $0 <job-id> [--dry-run]" >&2
    exit 1
fi

META="$WORKDIR/jobs/$JOB_ID/meta.yaml"
REVIEW="$WORKDIR/jobs/$JOB_ID/review.md"

refuse() { echo "REFUSED: $1" >&2; exit 1; }

# --- C1 ---
[[ -f "$META" ]] || refuse "C1 — nincs meta.yaml: $META"

# --- C2 ---
STATUS=$(grep '^status:' "$META" | head -1 | awk -F'"' '{print $2}')
if [[ "$STATUS" != "awaiting_review" ]]; then
    refuse "C2 — a job státusza '$STATUS', nem 'awaiting_review'. A done csak innen érhető el."
fi

# --- C3 ---
# `set -e` would abort here on NO-GO before the message could be written, so the
# call is guarded. The gate's own output is passed through: it names the failing
# rule, and repeating it here would be a second place to keep in sync.
if ! bash "$WORKDIR/tools/validate-output.sh" "$JOB_ID"; then
    refuse "C3 — a gépi output-kapu NO-GO-t adott (lásd fent). Javíttasd az agenttel."
fi

# --- C4 ---
[[ -f "$REVIEW" ]] || refuse "C4 — nincs review artifact: $REVIEW (sablon: /job-close 4. pont)"
[[ -s "$REVIEW" ]] || refuse "C4 — a review.md üres: $REVIEW"

# Same marker set and line-start anchoring as validate-output.sh's O3: a marker
# quoted mid-sentence is a statement about someone else's code, not an unfinished
# review.
PLACEHOLDERS=$(grep -nE '^[[:space:]]*([-*+>]|#{1,6}|[0-9]+\.)?[[:space:]]*(TODO|TBD|FIXME|XXX|kitöltendő|pótolandó)\b' \
    "$REVIEW" | head -3 || true)
if [[ -n "$PLACEHOLDERS" ]]; then
    echo "$PLACEHOLDERS" >&2
    refuse "C4 — a review.md befejezetlen (placeholder a fenti sorokban)"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "DRY-RUN: mind a négy feltétel teljesül, a job lezárható."
    exit 0
fi

# --- transition ---
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 - "$META" "$NOW" <<'PYEOF'
import re, sys
meta_path, now = sys.argv[1], sys.argv[2]
with open(meta_path, encoding="utf-8") as f:
    content = f.read()
content = re.sub(r'^status:.*$', 'status: "done"', content, flags=re.MULTILINE)
content = re.sub(r'^\s+completed:.*$', f'  completed: "{now}"', content, flags=re.MULTILINE)
with open(meta_path, "w", encoding="utf-8") as f:
    f.write(content)
PYEOF

bash "$WORKDIR/tools/update-index.sh"

echo "[✓] $JOB_ID — done ($NOW)"
echo ""
echo "A commit a tiéd — az a Vault-aláírt bizonyíték:"
echo "  git add jobs/$JOB_ID/ jobs/index.yaml   # + a sub-job specek, ha vannak"
echo "  git commit -m \"job: $JOB_ID — done + output + review\""
echo "  git push"
