#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""ci-gate.py - follow the CI of one exact PR head and, when the policy allows, merge exactly that head.

    ci-gate.py check OWNER/REPO#N --head SHA --require-from FILE            one reading: GREEN, RED, PENDING or HEAD-MOVED
    ci-gate.py watch OWNER/REPO#N --head SHA --require-from FILE [--interval S]
    ci-gate.py merge OWNER/REPO#N --head SHA --require-from FILE --approver LOGIN... [--dry-run]
    ci-gate.py land OWNER/REPO#N --require-from FILE --approver LOGIN... [--after OWNER/REPO#M]... [--keep-current]
               [--post-merge-from FILE] [--interval S] [--max-wait S] [--dry-run]    follow one PR to its merge (see `land`)
    ci-gate.py post-merge OWNER/REPO --sha SHA --require-from FILE           the CI of the merge commit, against its own named set
    ci-gate.py late-advisory OWNER/REPO --head SHA --require-from FILE       what the checks not waited for said in the end

The merge is the execution of a decision that was already taken, never the decision, and the evidence of the decision is read from
GitHub, not typed in:

* the checks: FILE names every check that must have run on the head (one name per line, `#` comments). Each must be present and
  completed with `success` (skipped or neutral is not the gate having run); one that has not reported yet is PENDING, not green,
  so a head with a single finished check cannot pass. When a name has several results (re-runs, two apps) the worst stands.
  A cancelled or unknown conclusion is not a pass, and a failure of any check, required or not, is RED;
* the approval: a review APPROVED on that very commit by one of the `--approver` logins, or a comment by one of them that holds
  the line `merge-approved: <full head sha>`, with nothing of theirs after it that withdraws it (a review CHANGES_REQUESTED or
  DISMISSED, a comment `merge-revoked: <sha>`). An approval of an older head does not carry over to a new one;
* the environment: the PR open, not draft, mergeable, its base branch at the same commit and the head unchanged between two
  readings taken one after the other.

Anything else refuses and says why. Pending is neither success nor failure: `watch` keeps watching, nothing is merged. Only the
named set is waited for: a check nobody required that is still running is reported, a failure of any check still blocks.

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


def _merge_state(old, new):
    """Several results under one name (a re-run, two apps): the worst one stands. fail > pending > skip > pass."""
    rank = lambda v: 3 if v.startswith("fail") else 2 if v == "pending" else 1 if v == "skip" else 0
    return new if old is None or rank(new) > rank(old) else old


def check_states(get, repo, sha):
    """name -> 'pass' | 'skip' | 'pending' | 'fail:<why>' for every check run and commit status of exactly this commit.

    `skip` is a skipped or neutral run: fine for a check nobody required, not a pass for one that is required. When one name has
    several results (re-runs, two apps) none of them is dropped: the worst stands, so an old failure is not hidden behind a
    newer success that came from somewhere else."""
    out = {}
    for r in ps.pages(get, "repos/%s/commits/%s/check-runs" % (repo, sha)):
        if r.get("status") != "completed":
            state = "pending"
        elif r.get("conclusion") == "success":
            state = "pass"
        elif r.get("conclusion") in ps.OK:
            state = "skip"
        else:
            state = "fail:%s" % r.get("conclusion")
        out[r.get("name")] = _merge_state(out.get(r.get("name")), state)
    # the combined status API already keeps the latest state of each context
    for st in get("repos/%s/commits/%s/status" % (repo, sha)).get("statuses", []):
        state = {"success": "pass", "pending": "pending"}.get(st.get("state"), "fail:%s" % st.get("state"))
        out[st.get("context")] = _merge_state(out.get(st.get("context")), state)
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
    # how far the head is behind its base: a CI that ran on a stale base says nothing about the merge result
    out["behind"] = get("repos/%s/compare/%s...%s" % (repo, pr["base"]["ref"], now)).get("behind_by", 0)
    if now != head:
        out["verdict"] = "HEAD-MOVED"
        return out
    states = check_states(get, repo, head)
    out["ci"] = {"total": len(states), "pass": sum(v == "pass" for v in states.values()),
                 "pending": sum(v == "pending" for v in states.values())}
    soft = lambda k: any(k.startswith(a) for a in advisory)
    failing = ["%s (%s)" % (k, v[5:]) for k, v in sorted(states.items()) if v.startswith("fail") and not (soft(k) and v == "fail:cancelled")]
    out["warnings"] = ["%s was cancelled (advisory, not counted as evidence)" % k for k, v in sorted(states.items()) if soft(k) and v == "fail:cancelled"]
    # only the named set decides: a check nobody required (an advisory shard, the aggregate gate that waits for them) that is still
    # running is reported, never waited for. A real failure of any check, required or not, is still RED above.
    out["not_waited_for"] = [k for k, v in sorted(states.items()) if v == "pending" and k not in required]
    # a required check passes only by succeeding: skipped or neutral is not the gate having run
    not_run = ["%s (%s)" % (r, "skipped") for r in required if states.get(r) == "skip"]
    failing += not_run
    missing = [r for r in required if r not in states]
    waiting = [k for k in required if states.get(k) == "pending"]
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


SNAPSHOT = ("head_now", "state", "base", "base_sha", "behind", "draft", "mergeable", "verdict", "failing", "waiting")


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
    if r["behind"]:
        say("REFUSED: the head is %d commit(s) behind %s; its CI does not describe the merge result" % (r["behind"], r["base"]))
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


def land(get, repo, n, required, approvers, after=(), keep_current=False, post_merge_required=None, interval=60, max_wait=14400,
         advisory=(), dry_run=False, gh=run_gh, sleep=time.sleep, now=time.monotonic, say=print):
    """Follow one PR to its merge, as far as the policy allows, and stop where it does not. No head is given: it follows the head
    the PR has, and the approval (head-bound, read from GitHub) is what pins the commit that may be merged. Each round:

    1. the PR merged: done (then the post-merge set, when given). Closed unmerged: stop.
    2. every `after` PR (a dependency, possibly in another repository) must be merged first; one closed unmerged stops it.
    3. a head GitHub cannot merge (conflicts) stops it: a person or an agent resolves that, nothing is guessed.
    4. a head that is behind its base is not judged: a green on a stale base says nothing about the merge result (a clean text merge
       can still break the build). With `keep_current` the base is merged into the PR branch (`update-branch`, once the
       dependencies are in); the head moves, the CI starts over and the approval of the old head does not carry over. Without it
       the PR is refused as behind. GitHub's own `mergeable_state` says "behind" only when the base requires up-to-date branches,
       so the distance is measured here.
    5. CI of the head: PENDING waits, RED stops, GREEN goes on.
    6. the approval of this very head: none waits (and says so once), then the same `merge` as above runs, with its two readings.

    Exit status: 0 landed (and the post-merge set passed, when given), 1 refused or stopped, 4 still waiting when `max_wait` ran out."""
    start, last = now(), [None]

    def wait(why):
        if why != last[0]:
            say("waiting: " + why)
            last[0] = why
        if now() - start >= max_wait:
            say("TIMED OUT while waiting: " + why)
            return 4
        sleep(interval)
        return None

    while True:
        pr = get("repos/%s/pulls/%d" % (repo, n))
        if pr.get("merged"):
            return _after_merge(get, repo, pr.get("merge_commit_sha"), post_merge_required, interval, max_wait, sleep, now, say)
        if pr.get("state") != "open":
            say("STOPPED: the PR is %s without being merged" % pr.get("state"))
            return 1
        pending_dep = None
        for drepo, dn in after:
            dep = get("repos/%s/pulls/%d" % (drepo, dn))
            if dep.get("merged"):
                continue
            if dep.get("state") != "open":
                say("STOPPED: the dependency %s#%d was %s without being merged" % (drepo, dn, dep.get("state")))
                return 1
            pending_dep = "the dependency %s#%d is not merged yet" % (drepo, dn)
        head, base = pr["head"]["sha"], pr["base"]["ref"]
        if pr.get("mergeable") is False:
            say("STOPPED: GitHub cannot merge %s into %s (conflict): resolve it, then land again" % (head[:12], base))
            return 1
        behind = get("repos/%s/compare/%s...%s" % (repo, base, head)).get("behind_by", 0)  # also read() and merge() look at it
        if behind and not pending_dep:
            if not keep_current:
                say("REFUSED: the head %s is %d commit(s) behind %s; its CI does not describe the merge result (use --keep-current)" % (head[:12], behind, base))
                return 1
            if dry_run:
                say("DRY RUN: would merge %s into the PR branch (update-branch, expected head %s)" % (base, head[:12]))
                return 0
            code, out = gh(["api", "-X", "PUT", "repos/%s/pulls/%d/update-branch" % (repo, n), "-f", "expected_head_sha=" + head])
            if code != 0:
                say("STOPPED: update-branch refused (conflict or the head moved): %s" % out)
                return 1
            say("updated: %s merged into the PR branch; the head moves, its CI and its approval start over" % base)
            last[0] = None
            stop = wait("the new head of the updated branch")
            if stop is not None:
                return stop
            continue
        if pending_dep:
            stop = wait(pending_dep)
            if stop is not None:
                return stop
            continue
        r = read(get, repo, n, head, required, advisory)
        if r["verdict"] == "RED":
            say(describe(r))
            say("STOPPED: the head %s is RED" % head[:12])
            return 1
        if r["verdict"] != "GREEN":  # PENDING, or HEAD-MOVED between the two reads: look again
            stop = wait("CI of %s: %s" % (head[:12], "; ".join(r.get("waiting", [r["verdict"]]))[:120]))
            if stop is not None:
                return stop
            continue
        ok, why = approval(get, repo, n, head, approvers)
        if not ok:
            stop = wait("%s is green; %s" % (head[:12], why))
            if stop is not None:
                return stop
            continue
        code = merge(get, repo, n, head, required, approvers, dry_run, gh, say, advisory)
        if code != 0 or dry_run:
            return code
        merged = get("repos/%s/pulls/%d" % (repo, n))
        return _after_merge(get, repo, merged.get("merge_commit_sha"), post_merge_required, interval, max_wait, sleep, now, say)


def _after_merge(get, repo, sha, required, interval, max_wait, sleep, now, say):
    if not required:
        return 0
    start = now()
    while True:
        code = post_merge(get, repo, sha, required, say)
        if code != 4 or now() - start >= max_wait:
            return code
        sleep(interval)


def post_merge(get, repo, sha, required, say=print):
    """The CI of the merge commit on the target branch against its own named set (`post-merge` profile): 0 only when every
    required check is present and succeeded; a missing one is pending (4), a failure or a skipped required one is 1."""
    states = check_states(get, repo, sha)
    failing = ["%s (%s)" % (k, v[5:]) for k, v in sorted(states.items()) if v.startswith("fail")]
    failing += ["%s (skipped)" % r for r in required if states.get(r) == "skip"]
    missing = [r for r in required if r not in states]
    pending = [k for k, v in sorted(states.items()) if v == "pending"]
    say("post-merge %s: %d checks, %d passing, %d pending, %d failing, %d required not reported" % (
        sha[:12], len(states), sum(v == "pass" for v in states.values()), len(pending), len(failing), len(missing)))
    for f in failing:
        say("    - " + f)
    for m in missing:
        say("    . not reported yet: " + m)
    return 1 if failing else 4 if (missing or pending) else 0


def late_advisory(get, repo, head, advisory, say=print):
    """After the merge: what the advisory checks (not waited for) of the merged head said in the end. A failure is a defect of the
    merged state and needs a ticket; this prints the command, it does not open one."""
    states = {k: v for k, v in check_states(get, repo, head).items() if any(k.startswith(a) for a in advisory)}
    failing = ["%s (%s)" % (k, v[5:]) for k, v in sorted(states.items()) if v.startswith("fail")]
    pending = [k for k, v in sorted(states.items()) if v == "pending"]
    say("late advisory %s: %d checks, %d passing, %d pending, %d failing" % (
        head[:12], len(states), sum(v == "pass" for v in states.values()), len(pending), len(failing)))
    if not states:
        # nothing found is not nothing wrong: the checks may not have reported yet, or the prefix matches nothing
        say("    no advisory check found on this head: not verified")
        return 4
    for f in failing:
        say("    - " + f)
    if failing:
        say("A defect found after the merge needs a ticket: gh issue create --repo %s --title \"Late advisory check failed on %s\"" % (repo, head[:12]))
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
    p = sub.add_parser("land")
    p.add_argument("pr")
    p.add_argument("--require-from", required=True, help="file with the name of every check that must pass")
    p.add_argument("--approver", action="append", required=True, help="GitHub login whose approval of the head counts")
    p.add_argument("--after", action="append", default=[], metavar="OWNER/REPO#M", help="a PR that must be merged first")
    p.add_argument("--keep-current", action="store_true", help="merge the base into the PR branch when it is behind (the head moves)")
    p.add_argument("--post-merge-from", help="the post-merge profile: after the merge, wait for it on the merge commit")
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--max-wait", type=int, default=14400)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post-merge")
    p.add_argument("repo")
    p.add_argument("--sha", required=True)
    p.add_argument("--require-from", required=True, help="the post-merge profile: every check that must have succeeded on the merge commit")
    p = sub.add_parser("late-advisory")
    p.add_argument("repo")
    p.add_argument("--head", required=True, help="the head that was merged")
    p.add_argument("--require-from", required=True, help="the profile whose advisory prefixes are reported")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "post-merge":
            return post_merge(get, a.repo, a.sha, load_required(a.require_from)[0])
        if a.cmd == "late-advisory":
            return late_advisory(get, a.repo, a.head, load_required(a.require_from)[1])
        repo, n = target(a.pr)
        required, advisory = load_required(a.require_from)
        if a.cmd == "land":
            return land(get, repo, n, required, set(a.approver), [target(x) for x in a.after], a.keep_current,
                        load_required(a.post_merge_from)[0] if a.post_merge_from else None, a.interval, a.max_wait, advisory,
                        a.dry_run, gh, sleep)
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
