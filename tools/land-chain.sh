#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
# land-chain.sh - land a chain of PRs, in order, each one only when its own exact head is green, then check the merge commit.
#
#   land-chain.sh [--dry-run] OWNER/REPO REQUIRE_FILE POSTMERGE_FILE N:SHA [N:SHA ...]
#
# Meant to be run by the OWNER (`! tools/land-chain.sh ...` in a Claude Code prompt, or in a terminal): the owner's own instruction
# to merge these exact heads, in this order, is the authorization, typed as the list of N:FULL_SHA. It does not write an approval
# to GitHub and never merges anything that is not on the list. For each item, in order:
#   1. the PR head must still be SHA (a moved head is a new thing: stop);
#   2. wait (tools/ci-gate.py watch) until every check of REQUIRE_FILE passed on that head; red or timeout stops the chain;
#   3. the PR must be open and not conflicting;
#   4. `gh pr merge --squash --match-head-commit SHA`;
#   5. wait for the post-merge profile (POSTMERGE_FILE) on the merge commit; anything but green stops the chain, so a later PR is
#      never merged on top of a main that the earlier one broke. That check on main is also where the combination of the chain
#      is proved: each next PR is merged only after the previous merge commit is green.
# Stops at the first problem and says which item and why; items already merged stay merged (nothing is reverted).
# --dry-run: reads and reports each item (head, mergeable, the checks right now), merges nothing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
[ $# -ge 4 ] || { echo "usage: land-chain.sh [--dry-run] OWNER/REPO REQUIRE_FILE POSTMERGE_FILE N:SHA [N:SHA ...]" >&2; exit 2; }
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
  head=$(gh pr view "$N" -R "$REPO" --json headRefOid -q .headRefOid) || { echo "STOP: cannot read $REPO#$N" >&2; exit 3; }
  [ "$head" = "$SHA" ] || { echo "STOP: the head of #$N is $head, not $SHA (a moved head needs a new instruction)" >&2; exit 3; }
  if [ $DRY -eq 1 ]; then
    gh pr view "$N" -R "$REPO" --json state,isDraft,mergeable,mergeStateStatus -q '"state=\(.state) draft=\(.isDraft) mergeable=\(.mergeable) mergeState=\(.mergeStateStatus)"'
    python3 "$HERE/ci-gate.py" check "$REPO#$N" --head "$SHA" --require-from "$REQ" | tail -n 3
    continue
  fi
  python3 "$HERE/ci-gate.py" watch "$REPO#$N" --head "$SHA" --require-from "$REQ" --max-wait 14400 || { echo "STOP: #$N is not green on $SHA" >&2; exit 4; }
  read -r state draft mergeable < <(gh pr view "$N" -R "$REPO" --json state,isDraft,mergeable -q '"\(.state) \(.isDraft) \(.mergeable)"')
  [ "$state" = OPEN ] && [ "$draft" = false ] && [ "$mergeable" = MERGEABLE ] || { echo "STOP: #$N is $state draft=$draft mergeable=$mergeable" >&2; exit 5; }
  now=$(gh pr view "$N" -R "$REPO" --json headRefOid -q .headRefOid)
  [ "$now" = "$SHA" ] || { echo "STOP: the head of #$N moved to $now while waiting" >&2; exit 3; }
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
