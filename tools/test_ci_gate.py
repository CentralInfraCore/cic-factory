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
                 reviews=None, comments=None, base=("main", "base0"), behind=0):
        self.runs = ALL_OK if runs is None else runs
        self.head, self.mergeable, self.state, self.draft = head, mergeable, state, draft
        self.statuses, self.merged = statuses or [], merged
        self.reviews = [] if reviews is None else reviews
        self.comments = [] if comments is None else comments
        self.base = list(base)
        self.behind = behind
        self.asked = []

    def __call__(self, path):
        self.asked.append(path)
        if path.startswith("repos/o/r/compare/"):
            return {"behind_by": self.behind}
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


def approved(head=H, login="owner", at="2026-10-21T10:00:00Z"):
    return {"user": {"login": login}, "state": "APPROVED", "commit_id": head, "submitted_at": at}


def comment(body, login="owner", at="2026-10-21T10:00:00Z"):
    return {"user": {"login": login}, "body": body, "created_at": at}


class Gh:
    def __init__(self, fake, code=0, merges=True):
        self.calls, self.fake, self.code, self.merges = [], fake, code, merges

    def __call__(self, args):
        self.calls.append(args)
        if self.merges and args[:2] == ["pr", "merge"]:
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

    def test_a_required_check_that_is_pending_is_neither_success_nor_failure(self):
        self.assertEqual(verdict(runs=[run("build"), run("test", status="queued"), run("lint")]), "PENDING")
        self.assertEqual(verdict(runs=[run("build"), run("test", status="in_progress"), run("lint")]), "PENDING")

    def test_a_pending_check_nobody_required_is_not_waited_for(self):
        # the aggregate gate that waits for the advisory shards must not keep an otherwise complete head pending
        r = cg.read(Fake(runs=ALL_OK + [run("quality", status="queued")]), R, N, H, REQ)
        self.assertEqual((r["verdict"], r["not_waited_for"]), ("GREEN", ["quality"]))

    def test_a_pending_unrequired_check_does_not_hide_a_failure_of_another(self):
        self.assertEqual(verdict(runs=ALL_OK + [run("quality", status="queued"), run("extra", "failure")]), "RED")

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


class Strictness(unittest.TestCase):
    """The three cases of the second review: none of them may give a false green."""

    def test_a_required_check_that_was_skipped_is_not_green(self):
        r = cg.read(Fake(runs=[run("build"), run("test", "skipped"), run("lint")]), R, N, H, REQ)
        self.assertEqual((r["verdict"], r["failing"]), ("RED", ["test (skipped)"]))
        self.assertEqual(verdict(runs=[run("build"), run("test", "neutral"), run("lint")]), "RED")

    def test_a_skipped_check_nobody_required_is_fine(self):
        self.assertEqual(verdict(runs=ALL_OK + [run("record", "skipped")]), "GREEN")

    def test_two_results_under_one_name_do_not_overwrite_each_other(self):
        # an old failure from one app is not hidden by a later success under the same name, in either order
        self.assertEqual(verdict(runs=[run("build", "failure"), run("build"), run("test"), run("lint")]), "RED")
        self.assertEqual(verdict(runs=[run("build"), run("build", "failure"), run("test"), run("lint")]), "RED")
        self.assertEqual(verdict(runs=[run("build", status="in_progress"), run("build"), run("test"), run("lint")]), "PENDING")
        self.assertEqual(verdict(runs=[run("build"), run("build"), run("test"), run("lint")]), "GREEN")

    def test_a_commit_status_and_a_check_of_one_name_are_both_kept(self):
        self.assertEqual(verdict(statuses=[{"state": "failure", "context": "build"}]), "RED")


class PostMerge(unittest.TestCase):
    def pm(self, fake):
        said = []
        return cg.post_merge(fake, R, "m" * 40, REQ, say=said.append), "\n".join(said)

    def test_the_whole_named_set_must_have_succeeded_on_the_merge_commit(self):
        self.assertEqual(self.pm(Fake())[0], 0)

    def test_one_finished_check_is_not_a_finished_merge_commit(self):
        code, said = self.pm(Fake(runs=[run("build")]))
        self.assertEqual(code, 4)
        self.assertIn("not reported yet: test", said)

    def test_pending_and_failed_and_skipped_required_checks(self):
        self.assertEqual(self.pm(Fake(runs=[run("build"), run("test", status="queued"), run("lint")]))[0], 4)
        self.assertEqual(self.pm(Fake(runs=[run("build"), run("test", "failure"), run("lint")]))[0], 1)
        self.assertEqual(self.pm(Fake(runs=[run("build"), run("test", "skipped"), run("lint")]))[0], 1)

    def test_a_merge_commit_with_no_check_at_all_is_not_a_success(self):
        self.assertEqual(self.pm(Fake(runs=[]))[0], 4)


class LateAdvisory(unittest.TestCase):
    def late(self, runs):
        said = []
        return cg.late_advisory(Fake(runs=runs), R, H, ("mut",), say=said.append), "\n".join(said)

    def test_passing_pending_and_failed_advisory_checks_after_the_merge(self):
        self.assertEqual(self.late(ALL_OK + [run("mut (0)"), run("mut (1)")])[0], 0)
        self.assertEqual(self.late(ALL_OK + [run("mut (0)"), run("mut (1)", status="queued")])[0], 4)
        code, said = self.late(ALL_OK + [run("mut (0)", "failure")])
        self.assertEqual(code, 1)
        self.assertIn("needs a ticket", said)

    def test_no_advisory_check_found_is_not_a_success(self):
        code, said = self.late(ALL_OK)
        self.assertEqual(code, 4)
        self.assertIn("not verified", said)
        self.assertEqual(self.late([])[0], 4)

    def test_only_the_advisory_checks_are_reported(self):
        self.assertEqual(self.late([run("build", "failure"), run("mut (0)")])[0], 0)


class LandFake(Fake):
    """The fake of one PR that is also followed over time: `script` is a list of functions, one called per sleep, that change
    the state the way the world does between two looks (CI finishes, an approval is written, the base moves, a dependency merges)."""

    def __init__(self, deps=None, script=(), **kw):
        super().__init__(**kw)
        self.deps, self.script = deps or {}, list(script)

    def __call__(self, path):
        for k, v in self.deps.items():
            if path.startswith(k):
                return v
        return super().__call__(path)

    def tick(self, _seconds):
        if self.script:
            self.script.pop(0)(self)


class Clock:
    def __init__(self):
        self.t = 0

    def sleep(self, s):
        self.t += s

    def now(self):
        return self.t


def land(fake, gh=None, required=REQ, approvers=("owner",), **kw):
    gh = gh or Gh(fake)
    clock = Clock()
    lines = []

    def sleep(s):
        clock.sleep(s)
        fake.tick(s)

    code = cg.land(fake, R, N, required, set(approvers), gh=gh, sleep=sleep, now=clock.now, say=lines.append, interval=10,
                   max_wait=kw.pop("max_wait", 100), **kw)
    return code, gh, lines


def approve(f):
    f.reviews = [approved()]


class Landing(unittest.TestCase):
    def test_it_waits_for_ci_then_for_the_approval_and_merges_exactly_that_head(self):
        f = LandFake(runs=[run("build"), run("test", status="queued"), run("lint")],
                     script=[lambda f: setattr(f, "runs", ALL_OK), approve])
        code, gh, lines = land(f)
        self.assertEqual(code, 0, lines)
        self.assertEqual(gh.calls, [["pr", "merge", "7", "--repo", R, "--squash", "--match-head-commit", H]])
        self.assertTrue(any("waiting" in l and "running: test" in l for l in lines), lines)
        self.assertTrue(any("waiting" in l and "approval" in l for l in lines), lines)

    def test_a_red_head_stops_and_merges_nothing(self):
        code, gh, lines = land(LandFake(runs=[run("build", "failure"), run("test"), run("lint")], reviews=[approved()]))
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("STOPPED: the head %s is RED" % H[:12], lines)

    def test_green_without_an_approval_waits_until_it_runs_out_and_merges_nothing(self):
        code, gh, lines = land(LandFake(), max_wait=30)
        self.assertEqual((code, gh.calls), (4, []))
        self.assertTrue(lines[-1].startswith("TIMED OUT"), lines)

    def test_the_approval_of_another_head_is_not_enough(self):
        code, gh, _ = land(LandFake(reviews=[approved(H2)]), max_wait=30)
        self.assertEqual((code, gh.calls), (4, []))

    def test_a_dependency_must_be_merged_first(self):
        dep = {"repos/o/other/pulls/3": {"state": "open", "merged": False}}
        f = LandFake(reviews=[approved()], deps=dep, script=[lambda f: f.deps.update({"repos/o/other/pulls/3": {"state": "closed", "merged": True}})])
        code, gh, lines = land(f, after=[("o/other", 3)])
        self.assertEqual(code, 0, lines)
        self.assertTrue(any("dependency o/other#3 is not merged yet" in l for l in lines), lines)
        self.assertEqual(len(gh.calls), 1)

    def test_a_dependency_closed_without_merge_stops_it(self):
        dep = {"repos/o/other/pulls/3": {"state": "closed", "merged": False}}
        code, gh, lines = land(LandFake(reviews=[approved()], deps=dep), after=[("o/other", 3)])
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("without being merged", lines[-1])

    def test_a_conflict_stops_it(self):
        code, gh, lines = land(LandFake(mergeable=False, reviews=[approved()]))
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("conflict", lines[-1])

    def test_a_closed_pr_stops_it_and_a_merged_one_is_done(self):
        self.assertEqual(land(LandFake(state="closed"))[0], 1)
        self.assertEqual(land(LandFake(merged=True, state="closed"))[0], 0)

    def test_a_head_behind_its_base_is_refused_without_keep_current(self):
        code, gh, lines = land(LandFake(behind=2, reviews=[approved()]))
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("2 commit(s) behind main", lines[-1])

    def test_keep_current_merges_the_base_in_and_the_old_approval_does_not_carry_over(self):
        def moved(f):  # what update-branch does: a new head, the base now contained, CI starts over, the review is of the old head
            f.head, f.behind, f.runs = H2, 0, [run("build", status="queued")]
        f = LandFake(behind=1, reviews=[approved(H)], script=[moved])
        code, gh, lines = land(f, keep_current=True, max_wait=40)
        self.assertEqual(code, 4, lines)
        self.assertEqual(gh.calls, [["api", "-X", "PUT", "repos/o/r/pulls/7/update-branch", "-f", "expected_head_sha=" + H]])
        self.assertTrue(any("updated" in l for l in lines), lines)

    def test_after_the_update_a_new_approval_of_the_new_head_lets_it_merge(self):
        def moved(f):
            f.head, f.behind, f.runs = H2, 0, ALL_OK
        f = LandFake(behind=1, reviews=[approved(H)], script=[moved, lambda f: setattr(f, "reviews", [approved(H), approved(H2, at="2026-10-21T11:00:00Z")])])
        code, gh, lines = land(f, keep_current=True)
        self.assertEqual(code, 0, lines)
        self.assertEqual(gh.calls[-1][-1], H2)

    def test_it_does_not_update_the_branch_while_a_dependency_is_still_open(self):
        dep = {"repos/o/other/pulls/3": {"state": "open", "merged": False}}
        code, gh, _ = land(LandFake(behind=1, deps=dep), after=[("o/other", 3)], keep_current=True, max_wait=20)
        self.assertEqual((code, gh.calls), (4, []))

    def test_a_refused_update_is_a_stop(self):
        code, gh, lines = land(LandFake(behind=1), Gh(LandFake(), code=1, merges=False), keep_current=True)
        self.assertEqual(code, 1)
        self.assertIn("update-branch refused", lines[-1])

    def test_dry_run_writes_nothing(self):
        code, gh, lines = land(LandFake(behind=1), keep_current=True, dry_run=True)
        self.assertEqual((code, gh.calls), (0, []))
        code, gh, lines = land(LandFake(reviews=[approved()]), dry_run=True)
        self.assertEqual((code, gh.calls), (0, []))
        self.assertTrue(any("DRY RUN" in l for l in lines))

    def test_the_post_merge_set_decides_the_end(self):
        f = LandFake(reviews=[approved()])
        orig = f.__call__

        def get(path):
            if path.endswith("/status") and "/commits/" + "m" * 40 in path:
                return {"statuses": []}
            if "/commits/" + "m" * 40 + "/check-runs" in path:
                return {"check_runs": [run("main-build"), run("main-test", "failure")]}
            return orig(path)
        f.__call__ = get  # noqa
        clock, lines, gh = Clock(), [], Gh(f)
        code = cg.land(get, R, N, REQ, {"owner"}, post_merge_required=["main-build", "main-test"], gh=gh, sleep=clock.sleep,
                       now=clock.now, say=lines.append, interval=10, max_wait=100)
        self.assertEqual(code, 1, lines)

    def test_it_writes_only_through_merge_and_update_branch(self):
        f = LandFake(behind=1, reviews=[approved(H2)], script=[lambda f: (setattr(f, "head", H2), setattr(f, "behind", 0))])
        _, gh, _ = land(f, keep_current=True)
        for c in gh.calls:
            self.assertTrue(c[:2] == ["pr", "merge"] or c[:4] == ["api", "-X", "PUT", "repos/o/r/pulls/7/update-branch"], c)


class Freshness(unittest.TestCase):
    """The last look before a merge also asks how far the head is behind its base (the CI of a stale base is not the merge result)."""

    def merge(self, fake):
        gh = Gh(fake)
        lines = []
        return cg.merge(fake, R, N, H, REQ, {"owner"}, gh=gh, say=lines.append), gh, lines

    def test_a_head_behind_its_base_is_never_merged_even_when_green_and_approved(self):
        code, gh, lines = self.merge(Fake(behind=3, reviews=[approved()]))
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("3 commit(s) behind main", lines[-1])

    def test_a_head_that_falls_behind_between_the_two_readings_is_not_merged(self):
        f = Fake(reviews=[approved()])
        reads = []
        orig = f.__call__

        def get(path):
            if path.startswith("repos/o/r/compare/"):
                reads.append(path)
                return {"behind_by": 0 if len(reads) == 1 else 1}  # the base moved after the first look
            return orig(path)
        gh, lines = Gh(f), []
        code = cg.merge(get, R, N, H, REQ, {"owner"}, gh=gh, say=lines.append)
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("behind", lines[-1])

    def test_land_does_not_merge_a_head_that_fell_behind_after_it_was_judged_green(self):
        f = LandFake(reviews=[approved()])
        seen = []
        orig = f.__call__

        def get(path):
            if path.startswith("repos/o/r/compare/"):
                seen.append(1)
                return {"behind_by": 0 if len(seen) == 1 else 2}  # fresh when land looked, behind at the last look
            return orig(path)
        gh, lines, clock = Gh(f), [], Clock()
        code = cg.land(get, R, N, REQ, {"owner"}, gh=gh, sleep=clock.sleep, now=clock.now, say=lines.append, interval=10, max_wait=50)
        self.assertEqual((code, gh.calls), (1, []))
        self.assertIn("behind", lines[-1])

    def test_a_fresh_head_still_merges(self):
        code, gh, _ = self.merge(Fake(reviews=[approved()]))
        self.assertEqual((code, len(gh.calls)), (0, 1))


if __name__ == "__main__":
    unittest.main()
