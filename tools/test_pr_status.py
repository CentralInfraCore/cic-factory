#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Tests of tools/pr-status.py with a fake GitHub: what it says for each state a PR can be in, and that it only ever reads."""
import importlib.util
import io
import json
import os
import re
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pr_status", os.path.join(HERE, "pr-status.py"))
ps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ps)

R = "o/r"
H, B0, B1 = "h" * 40, "b" * 40, "c" * 40


class Fake:
    """A GitHub with one PR; every path asked for is recorded."""

    def __init__(self, **kw):
        self.asked = []
        self.base_now = kw.get("base_now", B0)
        self.head_now = kw.get("head_now", H)
        self.runs = kw.get("runs", [{"status": "completed", "conclusion": "success"}] * 3)
        self.statuses = kw.get("statuses", [])
        self.reviews = kw.get("reviews", [])
        self.mergeable = kw.get("mergeable", True)
        self.draft = kw.get("draft", False)
        self.fail = kw.get("fail")
        self.prs = kw.get("prs", [self.pr()])

    def pr(self, n=7):
        return {"number": n, "title": "a title", "draft": self.draft if hasattr(self, "draft") else False,
                "head": {"sha": H}, "base": {"ref": "main", "sha": B0}}

    def __call__(self, path):
        self.asked.append(path)
        if self.fail and self.fail in path:
            raise ps.ReadError("HTTP 404")
        if path.startswith("repos/o/r/pulls?state=open"):
            return self.prs
        if "/git/ref/heads/main" in path:
            return {"object": {"sha": self.base_now}}
        if "/compare/" in path:
            return {"behind_by": 0 if self.base_now == B0 else 2, "ahead_by": 1}
        if path.startswith("repos/o/r/commits/%s/check-runs" % H):
            return {"check_runs": self.runs}
        if path.startswith("repos/o/r/commits/%s/status" % H):
            return {"statuses": self.statuses}
        if "/reviews" in path:
            return self.reviews
        if re.match(r"repos/o/r/pulls/\d+$", path):
            return {"mergeable": self.mergeable, "mergeable_state": "clean" if self.mergeable else "dirty", "head": {"sha": self.head_now}}
        raise AssertionError("unexpected path " + path)


def run(fake, repos=(R,), only=None):
    rows, errors = ps.collect(fake, list(repos), only)
    return rows, errors


class StatusTests(unittest.TestCase):
    def one(self, **kw):
        rows, errors = run(Fake(**kw))
        self.assertEqual(len(rows), 1)
        return rows[0], errors

    def test_a_green_pr_is_ready(self):
        r, errors = self.one()
        self.assertEqual((ps.verdict(r), errors), ("ready", 0))
        self.assertEqual((r["head"], r["ci"]["state"], r["ci"]["total"], r["mergeable"], r["base_moved"]), (H, "passing", 3, "yes", False))

    def test_a_moved_base_is_reported_with_both_ends(self):
        r, _ = self.one(base_now=B1)
        self.assertTrue(r["base_moved"])
        self.assertEqual((r["base_at_pr"], r["base_now"], r["behind_by"]), (B0, B1, 2))
        self.assertEqual(ps.verdict(r), "ready-base-moved")
        self.assertIn("MOVED bbbbbbbb->cccccccc", ps.table([r]))

    def test_ci_states(self):
        done = lambda c: {"status": "completed", "conclusion": c}
        for runs, state in [([done("success"), done("failure")], "failing"), ([done("success"), {"status": "in_progress"}], "pending"),
                            ([], "none"), ([done("skipped"), done("success")], "passing"), ([done("something_new")], "failing")]:
            r, _ = self.one(runs=runs)
            self.assertEqual(r["ci"]["state"], state, runs)
        r, _ = self.one(runs=[done("success")], statuses=[{"state": "failure"}])
        self.assertEqual(r["ci"]["state"], "failing")           # a commit status counts as much as a check run
        r, _ = self.one(runs=[done("success")], statuses=[{"state": "pending"}])
        self.assertEqual(r["ci"]["state"], "pending")

    def test_failing_pending_and_missing_ci_are_never_ready(self):
        for runs in ([{"status": "completed", "conclusion": "failure"}], [{"status": "queued"}], []):
            r, _ = self.one(runs=runs)
            self.assertNotEqual(ps.verdict(r), "ready")
            self.assertNotEqual(ps.verdict(r), "ready-base-moved")

    def test_mergeability(self):
        r, _ = self.one(mergeable=False)
        self.assertEqual((r["mergeable"], ps.verdict(r)), ("no", "mergeable-no"))
        r, _ = self.one(mergeable=None)
        self.assertEqual((r["mergeable"], ps.verdict(r)), ("unknown", "mergeable-unknown"))

    def test_reviews(self):
        approved = {"user": {"login": "x"}, "state": "APPROVED", "commit_id": H}
        r, _ = self.one(reviews=[approved])
        self.assertEqual(r["review"]["state"], "approved")
        r, _ = self.one(reviews=[dict(approved, commit_id="old" * 13)])
        self.assertEqual(r["review"]["state"], "approved_stale")             # approved a commit that is not the head
        r, _ = self.one(reviews=[approved, {"user": {"login": "y"}, "state": "CHANGES_REQUESTED", "commit_id": H}])
        self.assertEqual((r["review"]["state"], ps.verdict(r)), ("changes_requested", "changes-requested"))
        r, _ = self.one(reviews=[{"user": {"login": "x"}, "state": "CHANGES_REQUESTED", "commit_id": H}, approved])
        self.assertEqual(r["review"]["state"], "approved")                    # the last verdict of a reviewer counts
        r, _ = self.one(reviews=[{"user": {"login": "x"}, "state": "COMMENTED", "commit_id": H}])
        self.assertEqual(r["review"]["state"], "none")

    def test_a_head_that_moved_while_reading_is_flagged(self):
        r, _ = self.one(head_now="9" * 40)
        self.assertFalse(r["head_stable"])
        self.assertEqual(ps.verdict(r), "HEAD-MOVED")

    def test_a_draft_is_a_draft(self):
        r, _ = self.one(draft=True)
        self.assertEqual(ps.verdict(r), "draft")

    def test_what_cannot_be_read_is_said_not_guessed(self):
        rows, errors = run(Fake(fail="/compare/"))
        self.assertEqual(errors, 1)
        self.assertEqual(ps.verdict(rows[0]), "UNREAD")
        self.assertIn("UNREAD", ps.table(rows))
        rows, errors = run(Fake(fail="pulls?state=open"))
        self.assertEqual((errors, ps.table(rows).startswith("o/r: UNREAD")), (1, True))

    def test_one_pr_only(self):
        f = Fake(prs=[Fake().pr(7), Fake().pr(9)])
        rows, _ = run(f, only=(R, 9))
        self.assertEqual([r["pr"] for r in rows], [9])

    def test_main_prints_json_and_the_exit_status(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ps.main(["--json", R], get=Fake())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue())[0]["head"], H)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ps.main([R], get=Fake(fail="/reviews")), 2)

    def test_only_reads_through_gh_get(self):
        # the single way out of the tool is `gh api -X GET`; nothing else is run
        calls = []

        def fake_run(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="[]", stderr="")

        with mock.patch.object(ps.subprocess, "run", fake_run):
            ps.gh_get("repos/o/r/pulls")
        self.assertEqual(calls, [["gh", "api", "-X", "GET", "repos/o/r/pulls"]])
        with open(os.path.join(HERE, "pr-status.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(len(re.findall(r"subprocess\.\w+\(", src)), 1)
        for word in ("POST", "PATCH", "PUT", "DELETE", "gh pr merge", "gh pr edit", "git push"):
            self.assertNotRegex(re.sub(r'""".*?"""', "", src, flags=re.S), r'["\']' + re.escape(word) + r'["\']')

    def test_every_path_asked_for_belongs_to_the_listed_repository(self):
        f = Fake()
        run(f)
        self.assertTrue(all(p.startswith("repos/o/r/") for p in f.asked), f.asked)
        self.assertTrue(any(p.startswith("repos/o/r/commits/%s/check-runs" % H) for p in f.asked))

    def test_the_default_repositories_are_named(self):
        self.assertIn("CentralInfraCore/cic-primitive-forms", ps.DEFAULT_REPOS)
        self.assertEqual(len(set(ps.DEFAULT_REPOS)), len(ps.DEFAULT_REPOS))


if __name__ == "__main__":
    unittest.main()
