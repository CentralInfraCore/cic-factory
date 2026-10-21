#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""ci-gate.py - follow the CI of one exact PR head and, when the policy allows, merge exactly that head.

    ci-gate.py check OWNER/REPO#N --head SHA                 one reading of the head: GREEN, RED, PENDING or HEAD-MOVED
    ci-gate.py watch OWNER/REPO#N --head SHA [--interval S]  poll until the head is no longer pending, then say the verdict
    ci-gate.py merge OWNER/REPO#N --head SHA --review-closed-at SHA [--dry-run]
    ci-gate.py post-merge OWNER/REPO --sha SHA               the CI of the merge commit on the target branch

The merge is the execution of a decision that was already taken, never the decision: it needs `--review-closed-at` with the very
head that is merged (a review of an older head does not carry over to a new one), every check of that head completed and passing
(a cancelled or unknown conclusion is not a pass), at least one check, the PR mergeable and the head unchanged since it was read.
Anything else refuses and says why. Pending is neither success nor failure: `watch` keeps watching, nothing is merged.

Exit status: 0 green / merged, 1 red or refused, 3 head moved, 4 pending (check only), 2 could not read.
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pr_status", os.path.join(HERE, "pr-status.py"))
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)


def run_gh(args):
    """The one place that writes: `gh pr merge`. Everything else goes through pr-status's read-only GET."""
    done = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=300)
    return done.returncode, (done.stdout + done.stderr).strip()


def failing_names(get, repo, sha):
    names = []
    for r in ps.pages(get, "repos/%s/commits/%s/check-runs" % (repo, sha)):
        if r.get("status") == "completed" and r.get("conclusion") not in ps.OK:
            names.append("%s (%s)" % (r.get("name"), r.get("conclusion")))
    for s in get("repos/%s/commits/%s/status" % (repo, sha)).get("statuses", []):
        if s.get("state") not in ("success", "pending"):
            names.append("%s (%s)" % (s.get("context"), s.get("state")))
    return names


def read(get, repo, n, head):
    """What the PR is right now, as far as this head is concerned."""
    pr = get("repos/%s/pulls/%d" % (repo, n))
    now = pr["head"]["sha"]
    out = {"head_now": now, "state": pr.get("state"), "base": pr["base"]["ref"], "draft": bool(pr.get("draft")),
           "mergeable": {True: "yes", False: "no", None: "unknown"}[pr.get("mergeable")]}
    if now != head:
        out["verdict"] = "HEAD-MOVED"
        return out
    ci = ps.ci_of(get, repo, head)
    out["ci"] = ci
    out["verdict"] = {"passing": "GREEN", "pending": "PENDING", "failing": "RED", "none": "RED"}[ci["state"]]
    if ci["state"] == "failing":
        out["failing"] = failing_names(get, repo, head)
    elif ci["state"] == "none":
        out["failing"] = ["no check ran on this head"]
    return out


def describe(r):
    ci = r.get("ci")
    line = "%s head=%s" % (r["verdict"], r["head_now"][:12])
    if ci:
        line += "  ci %d/%d (%d pending)" % (ci["pass"], ci["total"], ci["pending"])
    line += "  mergeable=%s" % r["mergeable"]
    for f in r.get("failing", []):
        line += "\n    - " + f
    return line


EXIT = {"GREEN": 0, "RED": 1, "HEAD-MOVED": 3, "PENDING": 4}


def watch(get, repo, n, head, interval, max_wait, sleep=time.sleep, now=time.monotonic, say=print):
    start = now()
    while True:
        r = read(get, repo, n, head)
        if r["verdict"] != "PENDING":
            return r
        if now() - start >= max_wait:
            return dict(r, verdict="PENDING", timed_out=True)
        say("pending: " + describe(r).splitlines()[0])
        sleep(interval)


def merge(get, repo, n, head, review_closed_at, dry_run=False, gh=run_gh, say=print):
    """Merge exactly `head`, or refuse and say why. Returns the exit status."""
    if review_closed_at != head:
        say("REFUSED: the review was closed at %s, not at the head %s: a new head needs a new review" % (review_closed_at[:12], head[:12]))
        return 1
    r = read(get, repo, n, head)
    say(describe(r))
    if r["verdict"] != "GREEN":
        say("REFUSED: the head is %s" % r["verdict"])
        return EXIT[r["verdict"]] if r["verdict"] == "HEAD-MOVED" else 1
    if r["state"] != "open" or r["draft"]:
        say("REFUSED: the PR is %s%s" % (r["state"], " (draft)" if r["draft"] else ""))
        return 1
    if r["mergeable"] != "yes":
        say("REFUSED: GitHub says mergeable=%s" % r["mergeable"])
        return 1
    # the last look, as close to the merge as it goes: the head must still be the one that was checked
    if read(get, repo, n, head)["verdict"] != "GREEN":
        say("REFUSED: the head changed or a check went red between the readings")
        return 1
    cmd = ["pr", "merge", str(n), "--repo", repo, "--squash", "--match-head-commit", head]
    if dry_run:
        say("DRY RUN: gh " + " ".join(cmd))
        return 0
    code, out = gh(cmd)
    say(out)
    if code != 0:
        # after a network blip the PR may have been merged: read before anything is retried
        after = get("repos/%s/pulls/%d" % (repo, n))
        if not after.get("merged"):
            say("NOT MERGED (gh exit %d)" % code)
            return 1
    after = get("repos/%s/pulls/%d" % (repo, n))
    say("MERGED %s" % (after.get("merge_commit_sha") or "?"))
    return 0 if after.get("merged") else 1


def post_merge(get, repo, sha, say=print):
    ci = ps.ci_of(get, repo, sha)
    say("post-merge %s: ci %d/%d (%s)" % (sha[:12], ci["pass"], ci["total"], ci["state"]))
    if ci["state"] == "failing":
        for f in failing_names(get, repo, sha):
            say("    - " + f)
    return {"passing": 0, "pending": 4}.get(ci["state"], 1)


def target(text):
    repo, _, n = text.partition("#")
    if "/" not in repo or not n.isdigit():
        raise SystemExit("expected OWNER/REPO#N, got %r" % text)
    return repo, int(n)


def main(argv=None, get=ps.gh_get, gh=run_gh, sleep=time.sleep):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "watch", "merge"):
        p = sub.add_parser(name)
        p.add_argument("pr")
        p.add_argument("--head", required=True)
        if name == "watch":
            p.add_argument("--interval", type=int, default=60)
            p.add_argument("--max-wait", type=int, default=3600)
        if name == "merge":
            p.add_argument("--review-closed-at", required=True)
            p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post-merge")
    p.add_argument("repo")
    p.add_argument("--sha", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "post-merge":
            return post_merge(get, a.repo, a.sha)
        repo, n = target(a.pr)
        if a.cmd == "merge":
            return merge(get, repo, n, a.head, a.review_closed_at, a.dry_run, gh)
        r = watch(get, repo, n, a.head, a.interval, a.max_wait, sleep) if a.cmd == "watch" else read(get, repo, n, a.head)
    except ps.ReadError as e:
        print("UNREAD: %s" % e)
        return 2
    print(describe(r))
    return EXIT[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
