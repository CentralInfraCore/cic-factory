#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""ci-gate.py - follow the CI of one exact PR head and, when the policy allows, merge exactly that head.

    ci-gate.py check OWNER/REPO#N --head SHA --require-from FILE            one reading: GREEN, RED, PENDING or HEAD-MOVED
    ci-gate.py watch OWNER/REPO#N --head SHA --require-from FILE [--interval S]
    ci-gate.py merge OWNER/REPO#N --head SHA --require-from FILE --approver LOGIN... [--dry-run]
    ci-gate.py post-merge OWNER/REPO --sha SHA                               the CI of the merge commit on the target branch

The merge is the execution of a decision that was already taken, never the decision, and the evidence of the decision is read from
GitHub, not typed in:

* the checks: FILE names every check that must have run on the head (one name per line, `#` comments). Each must be present and
  completed passing; one that has not reported yet is PENDING, not green, so a head with a single finished check cannot pass.
  A cancelled or unknown conclusion is not a pass, and a failure of any check, required or not, is RED;
* the approval: a review APPROVED on that very commit by one of the `--approver` logins, or a comment by one of them that holds
  the line `merge-approved: <full head sha>`, with nothing of theirs after it that withdraws it (a review CHANGES_REQUESTED or
  DISMISSED, a comment `merge-revoked: <sha>`). An approval of an older head does not carry over to a new one;
* the environment: the PR open, not draft, mergeable, its base branch at the same commit and the head unchanged between two
  readings taken one after the other.

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


def check_states(get, repo, sha):
    """name -> 'pass' | 'pending' | 'fail' for every check run and commit status of exactly this commit."""
    out = {}
    for r in ps.pages(get, "repos/%s/commits/%s/check-runs" % (repo, sha)):
        if r.get("status") != "completed":
            state = "pending"
        elif r.get("conclusion") in ps.OK:
            state = "pass"
        else:
            state = "fail:%s" % r.get("conclusion")
        out[r.get("name")] = state
    for st in get("repos/%s/commits/%s/status" % (repo, sha)).get("statuses", []):
        out[st.get("context")] = {"success": "pass", "pending": "pending"}.get(st.get("state"), "fail:%s" % st.get("state"))
    return out


def load_required(path):
    """(required names, advisory prefixes). A line `advisory: PREFIX` names checks that are not waited for (the long mutation
    shards): they never keep a head pending, a cancelled one is a warning, but a real failure of one still makes it RED."""
    required, advisory = [], []
    with open(path, encoding="utf-8") as f:
        for l in f:
            l = l.split("#")[0].strip()
            if l.startswith("advisory:"):
                advisory.append(l[len("advisory:"):].strip())
            elif l:
                required.append(l)
    if not required:
        raise SystemExit("%s names no check: an empty required set would make every head green" % path)
    return required, advisory


def read(get, repo, n, head, required, advisory=()):
    """What the PR is right now, as far as this head is concerned."""
    pr = get("repos/%s/pulls/%d" % (repo, n))
    now = pr["head"]["sha"]
    out = {"head_now": now, "state": pr.get("state"), "base": pr["base"]["ref"], "draft": bool(pr.get("draft")),
           "mergeable": {True: "yes", False: "no", None: "unknown"}[pr.get("mergeable")],
           "base_sha": get("repos/%s/git/ref/heads/%s" % (repo, pr["base"]["ref"]))["object"]["sha"]}
    if now != head:
        out["verdict"] = "HEAD-MOVED"
        return out
    states = check_states(get, repo, head)
    out["ci"] = {"total": len(states), "pass": sum(v == "pass" for v in states.values()),
                 "pending": sum(v == "pending" for v in states.values())}
    soft = lambda k: any(k.startswith(a) for a in advisory)
    failing = ["%s (%s)" % (k, v[5:]) for k, v in sorted(states.items()) if v.startswith("fail") and not (soft(k) and v == "fail:cancelled")]
    out["warnings"] = ["%s was cancelled (advisory, not counted as evidence)" % k for k, v in sorted(states.items()) if soft(k) and v == "fail:cancelled"]
    out["not_waited_for"] = [k for k, v in sorted(states.items()) if soft(k) and v == "pending"]
    missing = [r for r in required if r not in states]
    waiting = [k for k, v in sorted(states.items()) if v == "pending" and not soft(k)]
    if failing:
        out["verdict"], out["failing"] = "RED", failing
    elif missing or waiting:
        out["verdict"] = "PENDING"
        out["waiting"] = ["not reported yet: " + m for m in missing] + ["running: " + w for w in waiting]
    else:
        out["verdict"] = "GREEN"
    return out


def describe(r):
    ci = r.get("ci")
    line = "%s head=%s" % (r["verdict"], r["head_now"][:12])
    if ci:
        line += "  ci %d/%d (%d pending)" % (ci["pass"], ci["total"], ci["pending"])
    line += "  mergeable=%s" % r["mergeable"]
    for f in r.get("failing", []):
        line += "\n    - " + f
    for w in r.get("waiting", [])[:6]:
        line += "\n    . " + w
    for w in r.get("warnings", []):
        line += "\n    ! " + w
    if r.get("not_waited_for"):
        line += "\n    ~ not waited for (advisory): %d running" % len(r["not_waited_for"])
    return line


EXIT = {"GREEN": 0, "RED": 1, "HEAD-MOVED": 3, "PENDING": 4}


def approval(get, repo, n, head, approvers):
    """The decision of an approver about exactly this head, read from GitHub: (approved, reason)."""
    events = []  # (time, login, kind) in the order GitHub reports them, per login the last one wins
    for r in ps.pages(get, "repos/%s/pulls/%d/reviews" % (repo, n)):
        login = (r.get("user") or {}).get("login")
        if login in approvers:
            kind = {"APPROVED": "approve" if r.get("commit_id") == head else "approve-other-head",
                    "CHANGES_REQUESTED": "revoke", "DISMISSED": "revoke"}.get(r.get("state"))
            if kind:
                events.append((r.get("submitted_at") or "", login, kind))
    for c in ps.pages(get, "repos/%s/issues/%d/comments" % (repo, n)):
        login = (c.get("user") or {}).get("login")
        if login not in approvers:
            continue
        for line in (c.get("body") or "").splitlines():
            line = line.strip()
            if line == "merge-approved: " + head:
                events.append((c.get("created_at") or "", login, "approve"))
            elif line.startswith("merge-approved: "):
                events.append((c.get("created_at") or "", login, "approve-other-head"))
            elif line.startswith("merge-revoked: "):
                events.append((c.get("created_at") or "", login, "revoke"))
    last = {}
    for when, login, kind in sorted(events):
        last[login] = kind
    if "approve" in last.values():
        return True, "approved by %s" % ", ".join(sorted(l for l, k in last.items() if k == "approve"))
    if "approve-other-head" in last.values():
        return False, "an approver approved another head: a new head needs a new approval"
    return False, "no approval of this head by %s" % ", ".join(sorted(approvers))


def watch(get, repo, n, head, required, interval, max_wait, advisory=(), sleep=time.sleep, now=time.monotonic, say=print):
    start = now()
    while True:
        r = read(get, repo, n, head, required, advisory)
        if r["verdict"] != "PENDING":
            return r
        if now() - start >= max_wait:
            return dict(r, verdict="PENDING", timed_out=True)
        say("pending: " + describe(r).splitlines()[0])
        sleep(interval)


SNAPSHOT = ("head_now", "state", "base", "base_sha", "draft", "mergeable", "verdict", "failing", "waiting")


def merge(get, repo, n, head, required, approvers, dry_run=False, gh=run_gh, say=print, advisory=()):
    """Merge exactly `head`, or refuse and say why. Returns the exit status."""
    ok, why = approval(get, repo, n, head, approvers)
    say(why)
    if not ok:
        say("REFUSED: " + why)
        return 1
    r = read(get, repo, n, head, required, advisory)
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
    # the last look, as close to the merge as it goes: the whole environment must be the one that was judged
    again = read(get, repo, n, head, required, advisory)
    changed = [k for k in SNAPSHOT if again.get(k) != r.get(k)]
    if changed:
        say("REFUSED: between the two readings %s changed" % ", ".join(changed))
        return 1
    if not approval(get, repo, n, head, approvers)[0]:
        say("REFUSED: the approval was withdrawn between the readings")
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
    states = check_states(get, repo, sha)
    failing = ["%s (%s)" % (k, v[5:]) for k, v in sorted(states.items()) if v.startswith("fail")]
    pending = [k for k, v in sorted(states.items()) if v == "pending"]
    say("post-merge %s: %d checks, %d passing, %d pending, %d failing" % (
        sha[:12], len(states), sum(v == "pass" for v in states.values()), len(pending), len(failing)))
    for f in failing:
        say("    - " + f)
    if not states:
        say("    no check ran on this commit")
        return 1
    return 1 if failing else 4 if pending else 0


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
        p.add_argument("--require-from", required=True, help="file with the name of every check that must pass")
        if name == "watch":
            p.add_argument("--interval", type=int, default=60)
            p.add_argument("--max-wait", type=int, default=3600)
        if name == "merge":
            p.add_argument("--approver", action="append", required=True, help="GitHub login whose approval of this head counts")
            p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post-merge")
    p.add_argument("repo")
    p.add_argument("--sha", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "post-merge":
            return post_merge(get, a.repo, a.sha)
        repo, n = target(a.pr)
        required, advisory = load_required(a.require_from)
        if a.cmd == "merge":
            return merge(get, repo, n, a.head, required, set(a.approver), a.dry_run, gh, advisory=advisory)
        r = (watch(get, repo, n, a.head, required, a.interval, a.max_wait, advisory, sleep) if a.cmd == "watch"
             else read(get, repo, n, a.head, required, advisory))
    except ps.ReadError as e:
        print("UNREAD: %s" % e)
        return 2
    print(describe(r))
    return EXIT[r["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
