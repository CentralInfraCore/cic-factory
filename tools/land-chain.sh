#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
# land-chain.sh - land a chain of PRs, in order, each one only when its own exact head is green, then check the merge commit.
#
#   land-chain.sh [--dry-run] [--allow-behind] OWNER/REPO REQUIRE_FILE POSTMERGE_FILE N:SHA [N:SHA ...]
#
# Meant to be run by the OWNER (`! tools/land-chain.sh ...` in a Claude Code prompt, or in a terminal): the owner's own instruction
# to merge these exact heads, in this order, is the authorization, typed as the list of N:FULL_SHA. It does not write an approval
# to GitHub and never merges anything that is not on the list. For each item, in order:
#   1. the PR must be FRESH (tools/ci-gate.py fresh): the head is still SHA, the PR is open, not a draft, mergeable, and not behind its base.
#      A head that is behind its base was judged on a base that has since moved: its CI does not describe the merge result, so the chain STOPS
#      (exit 8). In a chain of independent PRs from one base every PR after the first is behind; bring such a branch up to date (a new head, a new
#      instruction) or pass --allow-behind, the owner's explicit choice to merge a green head that is behind, which never overrides a moved head,
#      a closed or draft PR, or one that GitHub does not call mergeable;
#   2. wait (tools/ci-gate.py watch) until every check of REQUIRE_FILE passed on that head; red or timeout stops the chain;
#   3. fresh again, as close to the merge as it goes (the base may have moved while waiting);
#   4. `gh pr merge --squash --match-head-commit SHA`;
#   5. wait for the post-merge profile (POSTMERGE_FILE) on the merge commit; anything but green stops the chain, so a later PR is
#      never merged on top of a main that the earlier one broke. What that proves is what the profile names: for CentralInfraCore/cic-primitive-forms
#      it is the LIGHT set a push to main runs (the unit tests, the corpus, the coverage, the parity), not the mutation and the fuzz. Those are
#      measured by the nightly FULL, which is a separate piece of evidence (tools/ci-required/cic-primitive-forms.nightly.txt) and is not
#      claimed here.
# Stops at the first problem and says which item and why; items already merged stay merged (nothing is reverted).
# Exit codes: 2 bad call, 3 the head moved, 4 not green, 6 the merge failed, 7 the post-merge profile is not green, 8 not fresh (behind its base, not mergeable, closed, draft).
# --dry-run: reads and reports each item (head, mergeable, the checks right now), merges nothing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DRY=0
BEHIND=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --allow-behind) BEHIND="--allow-behind"; shift ;;
    *) break ;;
  esac
done
[ $# -ge 4 ] || { echo "usage: land-chain.sh [--dry-run] [--allow-behind] OWNER/REPO REQUIRE_FILE POSTMERGE_FILE N:SHA [N:SHA ...]" >&2; exit 2; }
REPO=$1; REQ=$2; POST=$3; shift 3
for f in "$REQ" "$POST"; do [ -s "$f" ] || { echo "no such profile: $f" >&2; exit 2; }; done
for item in "$@"; do
  case "$item" in [0-9]*:[0-9a-f]*) ;; *) echo "bad item '$item': want N:FULL_SHA" >&2; exit 2 ;; esac
  [ ${#item} -ge 42 ] || { echo "item '$item': the head must be the full 40-character sha" >&2; exit 2; }
done

total=$#; i=0
for item in "$@"; do
  i=$((i+1)); N=${item%%:*}; SHA=${item#*:}
  echo "== [$i/$total] $REPO#$N  head $SHA"
  python3 "$HERE/ci-gate.py" fresh "$REPO#$N" --head "$SHA" $BEHIND; rc=$?
  [ $rc -eq 0 ] || { echo "STOP: #$N is not fresh (a moved head or a base that moved under it needs a new instruction); nothing was merged for it" >&2; [ $rc -eq 3 ] && exit 3; exit 8; }
  if [ $DRY -eq 1 ]; then
    gh pr view "$N" -R "$REPO" --json state,isDraft,mergeable,mergeStateStatus -q '"state=\(.state) draft=\(.isDraft) mergeable=\(.mergeable) mergeState=\(.mergeStateStatus)"'
    python3 "$HERE/ci-gate.py" check "$REPO#$N" --head "$SHA" --require-from "$REQ" | tail -n 3
    continue
  fi
  python3 "$HERE/ci-gate.py" watch "$REPO#$N" --head "$SHA" --require-from "$REQ" --max-wait 14400 || { echo "STOP: #$N is not green on $SHA" >&2; exit 4; }
  python3 "$HERE/ci-gate.py" fresh "$REPO#$N" --head "$SHA" $BEHIND; rc=$?
  [ $rc -eq 0 ] || { echo "STOP: #$N is not fresh any more after the wait; nothing was merged for it" >&2; [ $rc -eq 3 ] && exit 3; exit 8; }
  gh pr merge "$N" -R "$REPO" --squash --match-head-commit "$SHA" || { echo "STOP: gh pr merge failed for #$N" >&2; exit 6; }
  mc=$(gh pr view "$N" -R "$REPO" --json mergeCommit -q .mergeCommit.oid)
  [ -n "$mc" ] || { echo "STOP: #$N has no merge commit after the merge" >&2; exit 6; }
  echo "merged #$N as $mc; waiting for the post-merge profile"
  for _ in $(seq 1 240); do
    python3 "$HERE/ci-gate.py" post-merge "$REPO" --sha "$mc" --require-from "$POST"; rc=$?
    [ $rc -ne 4 ] && break
    sleep 30
  done
  [ $rc -eq 0 ] || { echo "STOP: post-merge of #$N ($mc) is not green (rc=$rc); the chain does not go on" >&2; exit 7; }
  echo "post-merge of #$N green"
done
[ $DRY -eq 1 ] && echo "dry run: nothing was merged" || echo "chain landed: $total PR(s)"
