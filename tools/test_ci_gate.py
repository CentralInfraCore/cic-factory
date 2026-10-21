#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Tests of tools/ci-gate.py with a fake GitHub: what it says for each state a head can be in, and when it merges and when not."""
import importlib.util
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ci_gate", os.path.join(HERE, "ci-gate.py"))
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)

R, N = "o/r", 7
H, H2 = "a" * 40, "b" * 40
REQ = ["build", "test", "lint"]


def run(name, conclusion="success", status="completed"):
    return {"name": name, "status": status, "conclusion": conclusion if status == "completed" else None}


ALL_OK = [run(n) for n in REQ]


class Fake:
    def __init__(self, runs=None, head=H, mergeable=True, state="open", draft=False, statuses=None, merged=False,
                 reviews=None, comments=None, base=("main", "base0")):
        self.runs = ALL_OK if runs is None else runs
        self.head, self.mergeable, self.state, self.draft = head, mergeable, state, draft
        self.statuses, self.merged = statuses or [], merged
        self.reviews = [] if reviews is None else reviews
        self.comments = [] if comments is None else comments
        self.base = list(base)
        self.asked = []

    def __call__(self, path):
        self.asked.append(path)
        if path.startswith("repos/o/r/pulls/7/reviews"):
            return self.reviews
        if path.startswith("repos/o/r/issues/7/comments"):
            return self.comments
        if path.startswith("repos/o/r/pulls/7"):
            return {"state": self.state, "draft": self.draft, "mergeable": self.mergeable, "merged": self.merged,
                    "merge_commit_sha": "m" * 40 if self.merged else None, "head": {"sha": self.head}, "base": {"ref": self.base[0]}}
        if path.startswith("repos/o/r/git/ref/heads/"):
            return {"object": {"sha": self.base[1]}}
        if "/check-runs" in path:
            return {"check_runs": self.runs}
        if path.endswith("/status"):
            return {"statuses": self.statuses}
        raise AssertionError(path)


def approved(head=H, login="owner"):
    return {"user": {"login": login}, "state": "APPROVED", "commit_id": head, "submitted_at": "2026-10-21T10:00:00Z"}


def comment(body, login="owner", at="2026-10-21T10:00:00Z"):
    return {"user": {"login": login}, "body": body, "created_at": at}


class Gh:
    def __init__(self, fake, code=0, merges=True):
        self.calls, self.fake, self.code, self.merges = [], fake, code, merges

    def __call__(self, args):
        self.calls.append(args)
        if self.merges:
            self.fake.merged = True
        return self.code, "gh said"


def verdict(advisory=(), required=REQ, **kw):
    return cg.read(Fake(**kw), R, N, H, required, advisory)["verdict"]


class Verdicts(unittest.TestCase):
    def test_green_needs_every_required_check_present_complete_and_passing(self):
        self.assertEqual(verdict(), "GREEN")
        self.assertEqual(verdict(runs=ALL_OK + [run("extra", "skipped")]), "GREEN")

    def test_one_finished_check_is_not_green_when_the_others_have_not_reported(self):
        # the case the review found: three fake checks are enough for pr-status, a named set is not
        r = cg.read(Fake(runs=[run("build")]), R, N, H, REQ)
        self.assertEqual(r["verdict"], "PENDING")
        self.assertEqual(r["waiting"], ["not reported yet: test", "not reported yet: lint"])

    def test_three_passing_checks_with_the_wrong_names_are_not_green(self):
        self.assertEqual(verdict(runs=[run("a"), run("b"), run("c")]), "PENDING")

    def test_pending_is_neither_success_nor_failure(self):
        self.assertEqual(verdict(runs=ALL_OK + [run("slow", status="in_progress")]), "PENDING")
        self.assertEqual(verdict(runs=[run("build"), run("test", status="queued"), run("lint")]), "PENDING")

    def test_a_failure_is_red_and_named_even_while_others_are_missing(self):
        r = cg.read(Fake(runs=[run("build", "failure")]), R, N, H, REQ)
        self.assertEqual((r["verdict"], r["failing"]), ("RED", ["build (failure)"]))

    def test_a_cancelled_check_is_not_a_pass(self):
        self.assertEqual(verdict(runs=[run("build"), run("test", "cancelled"), run("lint")]), "RED")

    def test_an_unknown_conclusion_is_not_a_pass(self):
        self.assertEqual(verdict(runs=[run("build"), run("test", "weird"), run("lint")]), "RED")

    def test_a_failed_check_that_is_not_required_is_still_red(self):
        self.assertEqual(verdict(runs=ALL_OK + [run("extra", "failure")]), "RED")

    def test_a_failed_commit_status_is_red(self):
        self.assertEqual(verdict(statuses=[{"state": "failure", "context": "ci/x"}]), "RED")

    def test_a_moved_head_is_not_read_as_the_old_one(self):
        self.assertEqual(verdict(head=H2), "HEAD-MOVED")

    def test_an_empty_required_set_is_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# nothing\nadvisory: x\n")
        try:
            with self.assertRaises(SystemExit):
                cg.load_required(f.name)
        finally:
            os.unlink(f.name)


class Advisory(unittest.TestCase):
    SLOW = [run("mut (0)", status="in_progress"), run("mut (1)", status="queued")]

    def test_a_running_advisory_check_is_not_waited_for(self):
        r = cg.read(Fake(runs=ALL_OK + self.SLOW), R, N, H, REQ, ("mut",))
        self.assertEqual(r["verdict"], "GREEN")
        self.assertEqual(r["not_waited_for"], ["mut (0)", "mut (1)"])

    def test_a_required_check_is_still_waited_for(self):
        self.assertEqual(verdict(advisory=("mut",), runs=[run("build")] + self.SLOW), "PENDING")

    def test_a_real_failure_of_an_advisory_check_still_blocks(self):
        self.assertEqual(verdict(advisory=("mut",), runs=ALL_OK + [run("mut (0)", "failure")]), "RED")

    def test_a_cancelled_advisory_check_is_a_warning_and_not_evidence(self):
        r = cg.read(Fake(runs=ALL_OK + [run("mut (0)", "cancelled")]), R, N, H, REQ, ("mut",))
        self.assertEqual(r["verdict"], "GREEN")
        self.assertIn("mut (0) was cancelled (advisory, not counted as evidence)", r["warnings"])

    def test_the_required_file_reads_advisory_prefixes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# c\nadvisory: mut-\nbuild\ntest # trailing\n")
        try:
            self.assertEqual(cg.load_required(f.name), (["build", "test"], ["mut-"]))
        finally:
            os.unlink(f.name)


class Approval(unittest.TestCase):
    def ok(self, **kw):
        return cg.approval(Fake(**kw), R, N, H, {"owner"})

    def test_no_evidence_is_no_approval(self):
        self.assertFalse(self.ok()[0])

    def test_a_review_approved_on_this_head_counts(self):
        self.assertTrue(self.ok(reviews=[approved()])[0])

    def test_an_approval_of_an_older_head_does_not_carry_over(self):
        ok, why = self.ok(reviews=[approved(H2)])
        self.assertFalse(ok)
        self.assertIn("another head", why)

    def test_a_comment_with_the_head_counts(self):
        self.assertTrue(self.ok(comments=[comment("fine\nmerge-approved: " + H)])[0])

    def test_a_comment_for_a_prefix_or_another_head_does_not(self):
        self.assertFalse(self.ok(comments=[comment("merge-approved: " + H[:12])])[0])
        self.assertFalse(self.ok(comments=[comment("merge-approved: " + H2)])[0])

    def test_someone_who_is_not_an_approver_cannot_approve(self):
        self.assertFalse(self.ok(reviews=[approved(login="stranger")], comments=[comment("merge-approved: " + H, "stranger")])[0])

    def test_a_later_withdrawal_wins(self):
        self.assertFalse(self.ok(comments=[comment("merge-approved: " + H, at="2026-10-21T10:00:00Z"),
                                           comment("merge-revoked: " + H, at="2026-10-21T11:00:00Z")])[0])
        self.assertFalse(self.ok(reviews=[approved(), {"user": {"login": "owner"}, "state": "CHANGES_REQUESTED",
                                                       "commit_id": H, "submitted_at": "2026-10-21T12:00:00Z"}])[0])

    def test_an_approval_after_a_withdrawal_wins(self):
        self.assertTrue(self.ok(comments=[comment("merge-revoked: " + H, at="2026-10-21T09:00:00Z"),
                                          comment("merge-approved: " + H, at="2026-10-21T10:00:00Z")])[0])


class Watching(unittest.TestCase):
    def test_it_polls_until_the_head_is_decided(self):
        fake = Fake(runs=[run("build"), run("test", status="in_progress"), run("lint")])
        slept = []

        def sleep(s):
            slept.append(s)
            fake.runs = ALL_OK if len(slept) == 2 else fake.runs

        out = cg.watch(fake, R, N, H, REQ, 1, 100, sleep=sleep, say=lambda *_: None)
        self.assertEqual((out["verdict"], slept), ("GREEN", [1, 1]))

    def test_it_gives_up_pending_after_the_limit(self):
        t = iter(range(0, 1000, 40))
        out = cg.watch(Fake(runs=[]), R, N, H, REQ, 1, 100, sleep=lambda s: None, now=lambda: next(t), say=lambda *_: None)
        self.assertEqual((out["verdict"], out.get("timed_out")), ("PENDING", True))


class Merging(unittest.TestCase):
    def go(self, fake=None, **kw):
        fake = fake or Fake(reviews=[approved()])
        gh = Gh(fake, **{k: kw.pop(k) for k in ("code", "merges") if k in kw})
        said = []
        code = cg.merge(fake, R, N, H, REQ, {"owner"}, gh=gh, say=said.append, **kw)
        return code, gh.calls, "\n".join(said)

    def test_a_green_approved_head_is_merged_by_exactly_that_head(self):
        code, calls, said = self.go()
        self.assertEqual((code, calls), (0, [["pr", "merge", "7", "--repo", R, "--squash", "--match-head-commit", H]]))
        self.assertIn("MERGED", said)

    def test_without_the_approval_read_from_github_nothing_is_merged(self):
        for fake in (Fake(), Fake(reviews=[approved(H2)]), Fake(reviews=[approved(login="stranger")])):
            code, calls, said = self.go(fake)
            self.assertEqual((code, calls), (1, []))
            self.assertIn("REFUSED", said)

    def test_a_head_with_one_finished_check_is_never_merged(self):
        code, calls, _ = self.go(Fake(runs=[run("build")], reviews=[approved()]))
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [])

    def test_red_pending_and_moved_heads_are_never_merged(self):
        for kw in (dict(runs=[run("build", "failure"), run("test"), run("lint")]),
                   dict(runs=[run("build"), run("test", status="queued"), run("lint")]), dict(head=H2)):
            code, calls, _ = self.go(Fake(reviews=[approved()], **kw))
            self.assertNotEqual(code, 0)
            self.assertEqual(calls, [], kw)

    def test_a_conflicting_closed_or_draft_pr_is_never_merged(self):
        for kw in (dict(mergeable=False), dict(mergeable=None), dict(state="closed"), dict(draft=True)):
            code, calls, _ = self.go(Fake(reviews=[approved()], **kw))
            self.assertEqual((code, calls), (1, []), kw)

    def test_the_whole_environment_must_be_unchanged_between_the_two_readings(self):
        for what, change in (("base_sha", lambda f: f.base.__setitem__(1, "base1")), ("draft", lambda f: setattr(f, "draft", True)),
                             ("mergeable", lambda f: setattr(f, "mergeable", False))):
            fake = Fake(reviews=[approved()])
            real, seen = fake.__call__, []

            def get(path, real=real, fake=fake, change=change, seen=seen):
                if path.startswith("repos/o/r/pulls/7") and "/reviews" not in path:
                    seen.append(path)
                    if len(seen) == 2:  # the second reading of the PR
                        change(fake)
                return real(path)

            gh = Gh(fake)
            said = []
            code = cg.merge(get, R, N, H, REQ, {"owner"}, gh=gh, say=said.append)
            self.assertEqual((code, gh.calls), (1, []), what)

    def test_dry_run_merges_nothing(self):
        code, calls, said = self.go(dry_run=True)
        self.assertEqual((code, calls), (0, []))
        self.assertIn("DRY RUN", said)

    def test_a_failed_gh_is_not_a_merge_unless_the_pr_is_merged(self):
        code, _, said = self.go(code=1, merges=False)
        self.assertEqual(code, 1)
        self.assertIn("NOT MERGED", said)
        code, _, said = self.go(code=1, merges=True)  # the network blip: merged after all
        self.assertEqual(code, 0)

    def test_it_only_writes_through_gh_pr_merge(self):
        fake = Fake(reviews=[approved()])
        self.go(fake)
        self.assertTrue(all(p.startswith("repos/o/r/") for p in fake.asked))


class PostMerge(unittest.TestCase):
    def test_the_merge_commit_ci_is_read(self):
        self.assertEqual(cg.post_merge(Fake(), R, "m" * 40, say=lambda *_: None), 0)
        self.assertEqual(cg.post_merge(Fake(runs=[run("a"), run("b", status="queued")]), R, "m" * 40, say=lambda *_: None), 4)
        self.assertEqual(cg.post_merge(Fake(runs=[run("x", "failure")]), R, "m" * 40, say=lambda *_: None), 1)


if __name__ == "__main__":
    unittest.main()
