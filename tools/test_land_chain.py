#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Regression tests of tools/land-chain.sh with a stub `gh` and a stub `ci-gate.py`: the script is run for real, and what it asks of them,
and what it never does, is read from the calls it made. The rule under test: nothing is merged for a PR that is not fresh (a base that moved
under its head, a moved head, a PR that is not mergeable), and --allow-behind is only the owner's explicit choice for a head that is behind."""
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SHA1, SHA2 = "1" * 40, "2" * 40

GH = """#!/bin/bash
echo "$@" >> "$STUB_LOG"
case "$1 $2" in
  "pr merge") exit "${STUB_MERGE_RC:-0}" ;;
  "pr view") for a in "$@"; do [ "$a" = "mergeCommit" ] && { echo "m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1m1"; exit 0; }; done; exit 0 ;;
esac
exit 0
"""

# the stub for ci-gate.py: `fresh N` answers from STUB_FRESH_<N> (default 0), watch from STUB_WATCH_RC, post-merge from STUB_POST_RC
CI_GATE = """#!/usr/bin/env python3
import os, sys
a = sys.argv[1:]
open(os.environ["STUB_LOG"], "a").write("ci-gate " + " ".join(a) + "\\n")
cmd = a[0]
if cmd == "fresh":
    n = a[1].split("#")[1]
    print("stub fresh #%s" % n)
    sys.exit(int(os.environ.get("STUB_FRESH_" + n, "0")))
if cmd == "watch":
    sys.exit(int(os.environ.get("STUB_WATCH_RC", "0")))
if cmd == "post-merge":
    sys.exit(int(os.environ.get("STUB_POST_RC", "0")))
sys.exit(0)
"""


class Chain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        os.makedirs(os.path.join(d, "bin"))
        os.makedirs(os.path.join(d, "tools"))
        shutil.copy(os.path.join(HERE, "land-chain.sh"), os.path.join(d, "tools", "land-chain.sh"))
        for path, text in ((os.path.join(d, "bin", "gh"), GH), (os.path.join(d, "tools", "ci-gate.py"), CI_GATE)):
            with open(path, "w") as fh:
                fh.write(text)
            os.chmod(path, 0o755)
        for name in ("req.txt", "post.txt"):
            with open(os.path.join(d, name), "w") as fh:
                fh.write("build\n")
        self.log = os.path.join(d, "log")
        open(self.log, "w").close()

    def tearDown(self):
        self.tmp.cleanup()

    def run_chain(self, *args, **env):
        d = self.tmp.name
        e = dict(os.environ, PATH=os.path.join(d, "bin") + os.pathsep + os.environ["PATH"], STUB_LOG=self.log, **{k: str(v) for k, v in env.items()})
        p = subprocess.run([os.path.join(d, "tools", "land-chain.sh")] + list(args), env=e, capture_output=True, text=True)
        with open(self.log) as fh:
            calls = fh.read().splitlines()
        return p.returncode, p.stdout + p.stderr, calls

    def base(self, *items, flags=()):
        d = self.tmp.name
        return list(flags) + ["o/r", os.path.join(d, "req.txt"), os.path.join(d, "post.txt")] + list(items)

    def merges(self, calls):
        return [c for c in calls if c.startswith("pr merge")]

    def test_fresh_pull_requests_are_merged_in_order_after_a_fresh_check_each(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1, "8:" + SHA2))
        self.assertEqual(rc, 0, out)
        merges = self.merges(calls)
        self.assertEqual(len(merges), 2)
        self.assertIn("--match-head-commit " + SHA1, merges[0])
        self.assertIn("--match-head-commit " + SHA2, merges[1])
        # fresh is asked before the wait and again right before the merge, for each PR
        seq = [" ".join(c.split()[:2]) for c in calls if c.split()[0] == "ci-gate" or c.startswith("pr merge")]
        self.assertEqual(seq[:5], ["ci-gate fresh", "ci-gate watch", "ci-gate fresh", "pr merge", "ci-gate post-merge"])

    def test_a_stale_pull_request_is_not_merged_and_the_chain_stops_with_8(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1), STUB_FRESH_7=1)
        self.assertEqual(rc, 8, out)
        self.assertEqual(self.merges(calls), [], "nothing is merged for a head that is not fresh")
        self.assertFalse([c for c in calls if c.startswith("ci-gate watch")], "no waiting for the CI of a head that is already stale")

    def test_the_second_pull_request_that_became_stale_stops_the_chain_after_the_first_was_merged(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1, "8:" + SHA2), STUB_FRESH_8=1)
        self.assertEqual(rc, 8, out)
        merges = self.merges(calls)
        self.assertEqual(len(merges), 1)
        self.assertIn(SHA1, merges[0])
        self.assertIn("m1m1m1", out)   # the first one is reported merged; the second is the one that stops it

    def test_a_pull_request_that_goes_stale_during_the_wait_is_not_merged(self):
        # fresh answers 0 before the wait and 1 after it: the stub reads a counter file
        d = self.tmp.name
        gate = os.path.join(d, "tools", "ci-gate.py")
        with open(gate, "w") as fh:
            fh.write(CI_GATE.replace('print("stub fresh #%s" % n)', 'c = os.path.join(os.path.dirname(os.environ["STUB_LOG"]), "n")\n    k = int(open(c).read()) if os.path.exists(c) else 0\n    open(c, "w").write(str(k + 1))\n    sys.exit(0 if k == 0 else 1)'))
        os.chmod(gate, 0o755)
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1))
        self.assertEqual(rc, 8, out)
        self.assertEqual(self.merges(calls), [])
        self.assertTrue([c for c in calls if c.startswith("ci-gate watch")])

    def test_a_moved_head_is_exit_3(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1), STUB_FRESH_7=3)
        self.assertEqual(rc, 3, out)
        self.assertEqual(self.merges(calls), [])

    def test_allow_behind_is_passed_to_every_fresh_check_and_only_then(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1, flags=["--allow-behind"]))
        self.assertEqual(rc, 0, out)
        fresh = [c for c in calls if c.startswith("ci-gate fresh")]
        self.assertEqual(len(fresh), 2)
        self.assertTrue(all("--allow-behind" in c for c in fresh))
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1))
        self.assertFalse([c for c in calls if c.startswith("ci-gate fresh") and "--allow-behind" in c][len(fresh):], "not allowed unless asked")
        self.assertEqual(rc, 0, out)

    def test_a_red_pull_request_is_not_merged(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1), STUB_WATCH_RC=1)
        self.assertEqual(rc, 4, out)
        self.assertEqual(self.merges(calls), [])

    def test_a_post_merge_that_is_not_green_stops_before_the_next_pull_request(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1, "8:" + SHA2), STUB_POST_RC=1)
        self.assertEqual(rc, 7, out)
        self.assertEqual(len(self.merges(calls)), 1, "the second PR is not merged on top of a main that is not green")

    def test_a_short_sha_and_a_bad_call_are_refused_before_anything_runs(self):
        rc, out, calls = self.run_chain(*self.base("7:abc123"))
        self.assertEqual(rc, 2, out)
        self.assertEqual(calls, [])

    def test_dry_run_merges_nothing(self):
        rc, out, calls = self.run_chain(*self.base("7:" + SHA1, flags=["--dry-run"]))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.merges(calls), [])


if __name__ == "__main__":
    unittest.main()
