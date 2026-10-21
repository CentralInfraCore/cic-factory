#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""pr-status.py - read-only status of the open pull requests of several repositories.

One line per PR for the coordinator who integrates serially: the PR, its exact HEAD, the base it was tested against and the
base now, whether the base moved, the CI result for that very HEAD, the review state, and whether GitHub can merge it.

    pr-status.py                       the default repositories (PR_STATUS_REPOS, comma separated, overrides them)
    pr-status.py OWNER/REPO ...        these repositories
    pr-status.py --json                the same as JSON
    pr-status.py --pr OWNER/REPO#N     one PR only

It only reads. Every GitHub call is `gh api -X GET <path>`; nothing else is ever run, and the tests check that. The merge stays a
decision bound to the exact HEAD this prints: `gh pr merge N --squash --match-head-commit <head>`.

Exit status: 0 always when it could read; 2 if a repository or PR could not be read (the row says why).
"""
import argparse
import json
import os
import subprocess
import sys

DEFAULT_REPOS = [
    "CentralInfraCore/cic-primitive-forms",
    "CentralInfraCore/cic-schema-registry",
    "CentralInfraCore/cic-module-oracle-cloud",
    "CentralInfraCore/cic-primitive-engine",
    "CentralInfraCore/CIC_Relay",
]
FAIL = {"failure", "timed_out", "cancelled", "action_required", "startup_failure", "stale"}
OK = {"success", "neutral", "skipped"}


class ReadError(Exception):
    pass


def gh_get(path):
    """The only way this tool talks to GitHub: a GET through `gh api`."""
    done = subprocess.run(["gh", "api", "-X", "GET", path], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise ReadError((done.stderr or done.stdout).strip().splitlines()[-1][:200] if (done.stderr or done.stdout).strip() else "gh failed")
    try:
        return json.loads(done.stdout)
    except ValueError:
        raise ReadError("not JSON: " + path)


def pages(get, path):
    out, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        got = get("%s%sper_page=100&page=%d" % (path, sep, page))
        items = got if isinstance(got, list) else got.get("check_runs", [])
        out += items
        if len(items) < 100:
            return out
        page += 1


def ci_of(get, repo, sha):
    """Counts of the check runs and commit statuses of exactly this commit."""
    runs = pages(get, "repos/%s/commits/%s/check-runs" % (repo, sha))
    c = {"pass": 0, "fail": 0, "pending": 0}
    for r in runs:
        if r.get("status") != "completed":
            c["pending"] += 1
        elif r.get("conclusion") in FAIL:
            c["fail"] += 1
        elif r.get("conclusion") in OK:
            c["pass"] += 1
        else:
            c["fail"] += 1    # an unknown conclusion is not a pass
    st = get("repos/%s/commits/%s/status" % (repo, sha))
    for s in st.get("statuses", []):
        c[{"success": "pass", "pending": "pending"}.get(s.get("state"), "fail")] += 1
    total = c["pass"] + c["fail"] + c["pending"]
    state = "none" if total == 0 else "failing" if c["fail"] else "pending" if c["pending"] else "passing"
    return dict(c, total=total, state=state)


def review_of(get, repo, number, head):
    """The last verdict of each reviewer; a verdict given on an older commit is marked stale."""
    last = {}
    for r in pages(get, "repos/%s/pulls/%d/reviews" % (repo, number)):
        if r.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            last[(r.get("user") or {}).get("login", "?")] = r
    if not last:
        return {"state": "none", "reviews": []}
    items = [{"by": u, "state": r["state"], "on_head": r.get("commit_id") == head} for u, r in sorted(last.items())]
    if any(i["state"] == "CHANGES_REQUESTED" for i in items):
        state = "changes_requested"
    elif any(i["state"] == "APPROVED" and i["on_head"] for i in items):
        state = "approved"
    elif any(i["state"] == "APPROVED" for i in items):
        state = "approved_stale"
    else:
        state = "none"
    return {"state": state, "reviews": items}


def row(get, repo, pr):
    n, head, base = pr["number"], pr["head"]["sha"], pr["base"]["ref"]
    tested_base = pr["base"]["sha"]
    out = {"repo": repo, "pr": n, "title": pr.get("title", ""), "draft": bool(pr.get("draft")), "head": head, "base_ref": base,
           "base_at_pr": tested_base}
    try:
        now = get("repos/%s/git/ref/heads/%s" % (repo, base))["object"]["sha"]
        out["base_now"] = now
        out["base_moved"] = now != tested_base
        cmp_ = get("repos/%s/compare/%s...%s" % (repo, now, head))
        out["behind_by"], out["ahead_by"] = cmp_.get("behind_by"), cmp_.get("ahead_by")
        out["ci"] = ci_of(get, repo, head)
        out["review"] = review_of(get, repo, n, head)
        full = get("repos/%s/pulls/%d" % (repo, n))
        out["mergeable"] = {True: "yes", False: "no", None: "unknown"}[full.get("mergeable")]
        out["mergeable_state"] = full.get("mergeable_state") or "unknown"
        # the head may have moved between the list and now: what was read above belongs to `head` only if it did not
        out["head_stable"] = full["head"]["sha"] == head
    except (ReadError, KeyError) as e:
        out["error"] = str(e)
    return out


def collect(get, repos, only=None):
    rows, errors = [], 0
    for repo in repos:
        try:
            prs = get("repos/%s/pulls?state=open&per_page=100" % repo)
        except ReadError as e:
            rows.append({"repo": repo, "error": str(e)})
            errors += 1
            continue
        for pr in sorted(prs, key=lambda p: p["number"]):
            if only and (repo, pr["number"]) != only:
                continue
            r = row(get, repo, pr)
            errors += 1 if "error" in r else 0
            rows.append(r)
    return rows, errors


def verdict(r):
    """One word for the coordinator; it is advice to look, never a permission to merge."""
    if "error" in r:
        return "UNREAD"
    if r.get("draft"):
        return "draft"
    if not r.get("head_stable", True):
        return "HEAD-MOVED"
    if r["ci"]["state"] in ("failing", "none"):
        return "ci-" + r["ci"]["state"]
    if r["ci"]["state"] == "pending":
        return "ci-pending"
    if r["mergeable"] != "yes":
        return "mergeable-" + r["mergeable"]
    if r["review"]["state"] == "changes_requested":
        return "changes-requested"
    if r["base_moved"]:
        return "ready-base-moved"
    return "ready"


def table(rows):
    lines = []
    for r in rows:
        if "pr" not in r:
            lines.append("%s: UNREAD (%s)" % (r["repo"], r["error"]))
            continue
        head = "%s #%d  %s  %s" % (r["repo"].split("/")[-1], r["pr"], r["head"][:12], r["title"][:48])
        if "error" in r:
            lines.append("%s\n    UNREAD: %s" % (head, r["error"]))
            continue
        ci = r["ci"]
        lines.append("%s\n    %-18s ci %d/%d (%s)  review %s  merge %s/%s  base %s%s  ahead %s behind %s" % (
            head, verdict(r), ci["pass"], ci["total"], ci["state"], r["review"]["state"], r["mergeable"], r["mergeable_state"],
            r["base_ref"], " MOVED " + r["base_at_pr"][:8] + "->" + r["base_now"][:8] if r["base_moved"] else "", r["ahead_by"], r["behind_by"]))
        lines.append("    full head: " + r["head"])
    return "\n".join(lines) if lines else "no open pull requests"


def main(argv=None, get=gh_get):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--pr", help="OWNER/REPO#N")
    a = ap.parse_args(argv)
    only = None
    repos = a.repos or [r for r in os.environ.get("PR_STATUS_REPOS", "").split(",") if r] or DEFAULT_REPOS
    if a.pr:
        repo, _, n = a.pr.partition("#")
        if not n.isdigit() or "/" not in repo:
            ap.error("--pr wants OWNER/REPO#N")
        only, repos = (repo, int(n)), [repo]
    rows, errors = collect(get, repos, only)
    print(json.dumps(rows, indent=1) if a.json else table(rows))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
