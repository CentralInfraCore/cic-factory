#!/usr/bin/env bash
# Helpers for the disposable scratch repo (GitHub API only; no git push).
R=${R:-CentralInfraCore/cic-scratch-212-public}
sc_ref() { gh api "repos/$R/git/ref/heads/$1" --jq .object.sha; }
sc_branch() { gh api -X POST "repos/$R/git/refs" -f ref="refs/heads/$1" -f sha="${2:-$(sc_ref main)}" --jq .ref; }
# sc_put <branch> <path> <local-file> <message>
sc_put() {
  local sha; sha=$(gh api "repos/$R/contents/$2?ref=$1" --jq .sha 2>/dev/null || true)
  gh api -X PUT "repos/$R/contents/$2" -f branch="$1" -f message="$4" -f content="$(base64 -w0 "$3")" ${sha:+-f sha="$sha"} --jq .commit.sha
}
# sc_del <branch> <path> <message>
sc_del() {
  local sha; sha=$(gh api "repos/$R/contents/$2?ref=$1" --jq .sha)
  gh api -X DELETE "repos/$R/contents/$2" -f branch="$1" -f message="$3" -f sha="$sha" --jq .commit.sha
}
# sc_pr <branch> <title>
sc_pr() { gh api -X POST "repos/$R/pulls" -f head="$1" -f base=main -f title="$2" -f body="scratch proof PR (disposable)" --jq .number; }
