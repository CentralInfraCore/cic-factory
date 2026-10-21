#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Tests of tools/ci-gate.py with a fake GitHub: what it says for each state a head can be in, and when it merges and when not."""
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ci_gate", os.path.join(HERE, "ci-gate.py"))
cg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cg)

R, N = "o/r", 7
H, H2 = "a" * 40, "b" * 40
OK = {"status": "completed", "conclusion": "success", "name": "ok"}


class Fake:
    def __init__(self, runs=None, head=H, mergeable=True, state="open", draft=False, statuses=None, merged=False):
        self.runs = [OK] * 3 if runs is None else runs
        self.head, self.mergeable, self.state, self.draft = head, mergeable, state, draft
        self.statuses, self.merged = statuses or [], merged
        self.asked = []

    def __call__(self, path):
        self.asked.append(path)
        if path.startswith("repos/o/r/pulls/7"):
            return {"state": self.state, "draft": self.draft, "mergeable": self.mergeable, "merged": self.merged,
                    "merge_commit_sha": "m" * 40 if self.merged else None, "head": {"sha": self.head}, "base": {"ref": "main"}}
        if "/check-runs" in path:
            return {"check_runs": self.runs}
        if path.endswith("/status"):
            return {"statuses": self.statuses}
        raise AssertionError(path)


class Gh:
    def __init__(self, fake, code=0, merges=True):
        self.calls, self.fake, self.code, self.merges = [], fake, code, merges

    def __call__(self, args):
        self.calls.append(args)
        if self.merges:
            self.fake.merged = True
        return self.code, "gh said"


def verdict(**kw):
    return cg.read(Fake(**kw), R, N, H)["verdict"]


class Verdicts(unittest.TestCase):
    def test_green_needs_every_check_complete_and_passing(self):
        self.assertEqual(verdict(), "GREEN")
        self.assertEqual(verdict(runs=[OK, {"status": "completed", "conclusion": "skipped", "name": "s"}]), "GREEN")

    def test_pending_is_neither_success_nor_failure(self):
        self.assertEqual(verdict(runs=[OK, {"status": "in_progress", "name": "p"}]), "PENDING")

    def test_a_failure_is_red_and_named(self):
        r = cg.read(Fake(runs=[OK, {"status": "completed", "conclusion": "failure", "name": "unit"}]), R, N, H)
        self.assertEqual((r["verdict"], r["failing"]), ("RED", ["unit (failure)"]))

    def test_a_cancelled_check_is_not_a_pass(self):
        self.assertEqual(verdict(runs=[OK, {"status": "completed", "conclusion": "cancelled", "name": "c"}]), "RED")

    def test_an_unknown_conclusion_is_not_a_pass(self):
        self.assertEqual(verdict(runs=[{"status": "completed", "conclusion": "weird", "name": "w"}]), "RED")

    def test_a_head_without_any_check_is_red_not_green(self):
        self.assertEqual(verdict(runs=[]), "RED")

    def test_a_failed_commit_status_is_red(self):
        self.assertEqual(verdict(statuses=[{"state": "failure", "context": "ci/x"}]), "RED")

    def test_a_moved_head_is_not_read_as_the_old_one(self):
        self.assertEqual(verdict(head=H2), "HEAD-MOVED")


class Watching(unittest.TestCase):
    def test_it_polls_until_the_head_is_decided(self):
        states = iter([[{"status": "queued", "name": "p"}], [{"status": "in_progress", "name": "p"}], [OK]])
        real = Fake().__call__

        seen = []

        def get2(path):
            if "/check-runs" in path:
                get2.runs = next(states) if get2.fresh else get2.runs
                get2.fresh = False
                return {"check_runs": get2.runs}
            get2.fresh = True
            return real(path)

        get2.fresh, get2.runs = True, None
        out = cg.watch(get2, R, N, H, 1, 100, sleep=lambda s: seen.append(s), say=lambda *_: None)
        self.assertEqual(out["verdict"], "GREEN")
        self.assertEqual(seen, [1, 1])

    def test_it_gives_up_pending_after_the_limit(self):
        fake = Fake(runs=[{"status": "queued", "name": "p"}])
        t = iter(range(0, 1000, 40))
        out = cg.watch(fake, R, N, H, 1, 100, sleep=lambda s: None, now=lambda: next(t), say=lambda *_: None)
        self.assertEqual((out["verdict"], out.get("timed_out")), ("PENDING", True))


class Merging(unittest.TestCase):
    def go(self, fake=None, review=H, **kw):
        fake = fake or Fake()
        gh = Gh(fake, **{k: kw.pop(k) for k in ("code", "merges") if k in kw})
        said = []
        code = cg.merge(fake, R, N, H, review, gh=gh, say=said.append, **kw)
        return code, gh.calls, "\n".join(said)

    def test_a_green_reviewed_head_is_merged_by_exactly_that_head(self):
        code, calls, said = self.go()
        self.assertEqual((code, calls), (0, [["pr", "merge", "7", "--repo", R, "--squash", "--match-head-commit", H]]))
        self.assertIn("MERGED", said)

    def test_a_review_of_another_head_does_not_carry_over(self):
        code, calls, said = self.go(review=H2)
        self.assertEqual((code, calls), (1, []))
        self.assertIn("new head needs a new review", said)

    def test_red_pending_and_moved_heads_are_never_merged(self):
        for kw in (dict(runs=[OK, {"status": "completed", "conclusion": "failure", "name": "u"}]),
                   dict(runs=[OK, {"status": "queued", "name": "p"}]), dict(head=H2)):
            code, calls, _ = self.go(Fake(**kw))
            self.assertNotEqual(code, 0)
            self.assertEqual(calls, [], kw)

    def test_a_conflicting_closed_or_draft_pr_is_never_merged(self):
        for kw in (dict(mergeable=False), dict(mergeable=None), dict(state="closed"), dict(draft=True)):
            code, calls, _ = self.go(Fake(**kw))
            self.assertEqual((code, calls), (1, []), kw)

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
        fake = Fake()
        self.go(fake)
        self.assertTrue(all(p.startswith("repos/o/r/") for p in fake.asked))


class PostMerge(unittest.TestCase):
    def test_the_merge_commit_ci_is_read(self):
        said = []
        self.assertEqual(cg.post_merge(Fake(), R, "m" * 40, say=said.append), 0)
        self.assertEqual(cg.post_merge(Fake(runs=[OK, {"status": "queued", "name": "p"}]), R, "m" * 40, say=lambda *_: None), 4)
        self.assertEqual(cg.post_merge(Fake(runs=[{"status": "completed", "conclusion": "failure", "name": "x"}]), R, "m" * 40, say=lambda *_: None), 1)


if __name__ == "__main__":
    unittest.main()
