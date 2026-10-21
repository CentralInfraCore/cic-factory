# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Tests of the VCN pipeline runner with fake adapters (no toolchain needed), the optional integration test against the real component
checkouts, and the seeded defects of the runner (each must turn a test red)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapters  # noqa: E402
import run as runmod  # noqa: E402
import vcnpipe  # noqa: E402
from vcnpipe import Adapter, StageError, StageResult, Unavailable, digest  # noqa: E402

FX = os.path.join(HERE, "fixtures", "vcn-v1")


class Honest(Adapter):
    """A fake `executed` adapter that returns the expected file but reports what it consumed truthfully."""

    label = "executed"

    def __init__(self, stage, mutate=None, consumed_override=None, label=None, exc=None, unavailable=None):
        self.stage, self.mutate, self.override, self._label, self.exc, self.unavailable = stage, mutate, consumed_override, label, exc, unavailable

    def check_available(self, env):
        if self.unavailable:
            raise Unavailable(self.unavailable)

    def run(self, fx, case, inputs, env):
        if self.exc:
            raise self.exc
        out = fx.expected(case, vcnpipe.OUTPUT_NAME[self.stage])
        if self.mutate:
            out = self.mutate(json.loads(json.dumps(out)))
        consumed = {n: digest(inputs[n]) for n in vcnpipe.CONSUMES[self.stage]}
        consumed.update(self.override or {})
        return StageResult(self.stage, self._label or "executed", "fake", out, consumed)


def fake_set(**per_stage):
    return {s: {"executed": per_stage.get(s) or Honest(s), "fixture": adapters.FixtureAdapter(s)} for s in vcnpipe.STAGES}


def run_cli(argv, adapter_set=None, env=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = runmod.main(argv, env=env if env is not None else {}, adapter_set=adapter_set)
    return rc, out.getvalue(), err.getvalue()


def runner(adapter_set, **kw):
    return vcnpipe.Runner(vcnpipe.Fixture(FX), adapter_set, env={}, **kw)


class FixtureTests(unittest.TestCase):
    def test_the_vendored_fixture_matches_its_manifest(self):
        self.assertEqual(vcnpipe.Fixture(FX).check_manifest(), [])

    def test_a_changed_fixture_file_is_refused_before_anything_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "fx")
            shutil.copytree(FX, d)
            with open(os.path.join(d, "plan.json"), "a") as fh:
                fh.write(" ")
            rc, _, err = run_cli(["--fixture", d, "--fixture-only"])
            self.assertEqual(rc, 2)
            self.assertIn("changed: plan.json", err)

    def test_a_file_that_is_not_in_the_manifest_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "fx")
            shutil.copytree(FX, d)
            with open(os.path.join(d, "extra.json"), "w") as fh:
                fh.write("{}")
            self.assertEqual(run_cli(["--fixture", d, "--fixture-only"])[0], 2)

    def test_the_v2_layout_is_not_silently_run_as_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "fx")
            shutil.copytree(FX, d)
            with open(os.path.join(d, "cases", "conformant", "expected", "scope.json"), "w") as fh:
                fh.write("{}")
            rc, _, err = run_cli(["--fixture", d, "--fixture-only"])
            self.assertEqual(rc, 2)
            self.assertIn("v2", err)

    def test_usage_errors_are_exit_2(self):
        self.assertEqual(run_cli(["--fixture", "/nonexistent"])[0], 2)
        self.assertEqual(run_cli(["--case", "no-such-case", "--fixture-only"])[0], 2)
        self.assertEqual(run_cli(["--require-executed", "nonsense"])[0], 2)
        self.assertEqual(run_cli(["--fixture-only", "--require-executed", "all"])[0], 2)


class LabelTests(unittest.TestCase):
    def test_all_fixture_mode_passes_and_says_it_executed_nothing(self):
        rc, out, _ = run_cli(["--fixture-only", "--json"])
        doc = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual((doc["summary"]["cases"], doc["summary"]["cases_ok"], doc["summary"]["executed"]), (9, 9, 0))
        self.assertFalse(doc["summary"]["all_executed"])
        for c in doc["cases"]:
            self.assertEqual({s["label"] for s in c["stages"]}, {"fixture"})

    def test_text_report_never_presents_a_fixture_stage_as_executed(self):
        rc, out, _ = run_cli(["--fixture-only"])
        self.assertNotIn("EXECUTED", out)
        self.assertIn("FIXTURE", out)
        self.assertIn("NOT everything was executed", out)

    def test_honest_executed_adapters_are_labelled_executed(self):
        rc, out, _ = run_cli(["--json"], adapter_set=fake_set())
        doc = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertTrue(doc["summary"]["all_executed"])
        self.assertEqual(doc["summary"]["executed"], 36)

    def test_an_unavailable_adapter_falls_back_to_the_fixture_and_says_so(self):
        aset = fake_set(bind=Honest("bind", unavailable="CIC_REGISTRY_PATH is not set"))
        rc, out, _ = run_cli(["--json"], adapter_set=aset)
        doc = json.loads(out)
        self.assertEqual(rc, 0)
        labels = {s["stage"]: s["label"] for s in doc["cases"][0]["stages"]}
        self.assertEqual(labels, {"normalize": "executed", "bind": "fixture", "verdict": "executed", "evidence": "executed"})
        self.assertFalse(doc["summary"]["all_executed"])
        self.assertTrue(any("FIXTURE FALLBACK" in n for s in doc["cases"][0]["stages"] for n in s["notes"]))

    def test_a_required_stage_that_cannot_be_executed_is_an_error(self):
        aset = fake_set(verdict=Honest("verdict", unavailable="`cargo` is not on PATH"))
        rc, out, _ = run_cli(["--require-executed", "verdict"], adapter_set=aset)
        self.assertEqual(rc, 1)
        self.assertIn("must be executed but cannot be", out)
        rc, _, _ = run_cli(["--require-executed", "all"], adapter_set=aset)
        self.assertEqual(rc, 1)
        rc, _, _ = run_cli(["--require-executed", "normalize"], adapter_set=aset)   # the stage that IS available: fine
        self.assertEqual(rc, 0)

    def test_an_executed_adapter_that_fails_is_never_answered_with_a_fixture(self):
        aset = fake_set(normalize=Honest("normalize", exc=RuntimeError("go test exploded")))
        rc, out, _ = run_cli([], adapter_set=aset)             # no --require-executed: still an error
        self.assertEqual(rc, 1)
        self.assertIn("go test exploded", out)
        self.assertNotIn("FIXTURE FALLBACK", out)

    def test_an_adapter_that_reports_the_wrong_label_is_caught(self):
        aset = fake_set(bind=Honest("bind", label="fixture"))          # an executed adapter claiming to be a fixture stage
        rc, out, _ = run_cli(["--case", "conformant"], adapter_set=aset)
        self.assertEqual(rc, 1)
        self.assertIn("reported label", out)


class HandoffTests(unittest.TestCase):
    def test_a_stage_that_consumed_something_else_is_caught(self):
        wrong = {"obs_oci": "0" * 64}
        aset = fake_set(bind=Honest("bind", consumed_override=wrong))
        rc, out, _ = run_cli(["--case", "drift"], adapter_set=aset)
        self.assertEqual(rc, 1)
        self.assertIn("handoff to stage 4", out)

    def test_a_stage_that_lies_about_its_output_is_caught(self):
        def lie(v):
            v["object"] = "CONFORMANT"
            return v
        aset = fake_set(verdict=Honest("verdict", mutate=lie))
        rc, out, _ = run_cli(["--case", "drift"], adapter_set=aset)
        self.assertEqual(rc, 1)
        self.assertIn("stage 5 (verdict) output differs", out)

    def test_a_wrong_coverage_in_stage_3_is_caught_before_it_can_travel_on(self):
        def lie(v):
            v["coverage"]["/dnsLabel"] = "observed"
            return v
        aset = fake_set(normalize=Honest("normalize", mutate=lie))
        rc, out, _ = run_cli(["--case", "field-absent"], adapter_set=aset)
        self.assertEqual(rc, 1)
        self.assertIn("stage 3 (normalize) output differs", out)

    def test_a_wrong_stage_3_output_stops_the_run_before_stage_4_sees_it(self):
        seen = {}

        class Spy(Honest):
            def run(self, fx, case, inputs, env):
                seen["obs_oci"] = inputs["obs_oci"]
                return super().run(fx, case, inputs, env)

        class Tweak(Honest):
            def run(self, fx, case, inputs, env):
                r = super().run(fx, case, inputs, env)
                r.output["state"] = dict(r.output["state"], extra="x")     # differs from the expected file
                r.consumed = {n: digest(inputs[n]) for n in vcnpipe.CONSUMES[self.stage]}
                return r

        rep = runner(fake_set(normalize=Tweak("normalize"), bind=Spy("bind"))).run_case("conformant")
        self.assertFalse(rep.ok)                                         # stage 3 is wrong, so the run stops there
        self.assertNotIn("obs_oci", seen)

    def test_every_case_of_the_fixture_is_run_with_the_expected_verdicts(self):
        reps = [runner(fake_set()).run_case(c) for c in vcnpipe.Fixture(FX).cases()]
        self.assertTrue(all(r.ok for r in reps), [e for r in reps for e in r.errors])
        fx = vcnpipe.Fixture(FX)
        want = {c: fx.expected(c, "verdict")["object"] for c in fx.cases()}
        self.assertEqual({r.case: r.verdict for r in reps}, want)

    def test_the_open_question_case_is_reported_as_such_and_points_to_the_decision(self):
        rep = runner(fake_set()).run_case("desired-absent-observed-present")
        self.assertEqual(rep.verdict, "DRIFT")
        self.assertTrue(any("2026-10-21" in n and "v2" in n for n in rep.notes))


class AdapterUnitTests(unittest.TestCase):
    def test_a_missing_checkout_or_tool_is_unavailable_not_an_error(self):
        for ad in (adapters.ModuleAdapter(), adapters.RegistryAdapter(), adapters.EngineAdapter(), adapters.RelayAdapter()):
            with self.assertRaises(Unavailable):
                ad.check_available({"PATH": ""})
            with self.assertRaises(Unavailable):
                ad.check_available({"PATH": os.environ["PATH"], "CIC_MODULE_PATH": "/nonexistent", "CIC_REGISTRY_PATH": "/nonexistent",
                                    "CIC_ENGINE_PATH": "/nonexistent", "CIC_RELAY_PATH": "/nonexistent"})

    def test_the_compared_oci_paths_are_the_ones_the_fixture_compares(self):
        fx = vcnpipe.Fixture(FX)
        for c in fx.cases():
            self.assertEqual(sorted(fx.expected(c, "obs_oci")["coverage"]), sorted(adapters.OCI_COMPARED), c)
            self.assertTrue(set(fx.expected(c, "obs_oci")["state"]) <= set(adapters.OCI_STATE), c)

    def test_canonical_digest_is_independent_of_key_order_and_whitespace(self):
        self.assertEqual(digest({"b": [1, {"y": 1, "x": 2}], "a": "é"}), digest(json.loads('{"a": "é",\n "b": [1, {"x": 2, "y": 1}]}')))


@unittest.skipUnless(all(os.environ.get(v) for v in ("CIC_MODULE_PATH", "CIC_REGISTRY_PATH", "CIC_ENGINE_PATH", "CIC_RELAY_PATH")),
                     "the four component checkouts are not configured (CIC_MODULE_PATH, CIC_REGISTRY_PATH, CIC_ENGINE_PATH, CIC_RELAY_PATH)")
class IntegrationTests(unittest.TestCase):
    def test_all_four_components_are_executed_and_agree_with_the_fixture(self):
        rc, out, err = run_cli(["--require-executed", "all", "--json"], adapter_set=adapters.default_adapters(), env=dict(os.environ))
        self.assertEqual(rc, 0, out[-3000:] + err)
        doc = json.loads(out)
        self.assertTrue(doc["summary"]["all_executed"])
        self.assertEqual(doc["summary"]["executed"], 36)


@unittest.skipUnless(os.environ.get("CIC_REGISTRY_PATH"), "CIC_REGISTRY_PATH is not set")
class BrokenComponentTests(unittest.TestCase):
    def test_a_registry_whose_mapping_was_changed_fails_stage_4_for_real(self):
        """The executed registry adapter really runs the checkout's mapping: changing the mapping in a copy breaks the run."""
        src = os.environ["CIC_REGISTRY_PATH"]
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(os.path.join(src, "tools"), os.path.join(tmp, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
            rel = adapters.REGISTRY_CORRESPONDENCE
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)))
            with open(os.path.join(src, rel), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("dnsLabel", text)
            with open(os.path.join(tmp, rel), "w", encoding="utf-8") as fh:
                fh.write(text.replace("dnsLabel", "displayName"))
            only4 = {s: {"executed": adapters.RegistryAdapter() if s == "bind" else Honest(s, unavailable="not under test"),
                         "fixture": adapters.FixtureAdapter(s)} for s in vcnpipe.STAGES}
            rc, out, _ = run_cli(["--case", "conformant"], adapter_set=only4, env={"CIC_REGISTRY_PATH": tmp, "PATH": os.environ["PATH"]})
            self.assertEqual(rc, 1, out)
            # the real mapping code of the copy decides: either its output differs from the fixture (it maps something else) or the
            # component itself refuses the changed mapping (it checks its own coverage); both come from the executed code, not the fixture
            self.assertTrue("stage 4 (bind) output differs" in out or "the registry applier failed" in out and "CorrespondenceError" in out, out)
            self.assertNotIn("FIXTURE FALLBACK: CIC_REGISTRY", out)         # the registry stage was executed, not replaced


# ---- seeded defects of the runner: each textual change must turn a test above red ------------------------------------------------
DEFECTS = [
    ("the handoff is not checked", "vcnpipe.py", 'if res.label == "executed":\n                    for name in CONSUMES[stage]:', 'if False:\n                    for name in CONSUMES[stage]:'),
    ("a stage output is not compared with the fixture", "vcnpipe.py", "if res.output != expected:", "if False:"),
    ("a required stage may fall back", "vcnpipe.py", "if stage in self.require_executed:", "if False:"),
    ("the label of a result is not checked", "vcnpipe.py", "if res.label != adapter.label or res.stage != stage:", "if False:"),
    ("an adapter that fails falls back to the fixture", "vcnpipe.py", "raise StageError(\"stage %d (%s) %s adapter failed: %s: %s\" % (STAGE_NO[stage], stage, adapter.label, type(e).__name__, e))",
     "res = self.adapters[stage][\"fixture\"].run(self.fx, case, dict(arts), self.env)"),
    ("all_executed is always true", "vcnpipe.py", '"all_executed": bool(stages) and n_exec == len(stages) and all(r.ok for r in reports)', '"all_executed": True'),
    ("a failing case still exits 0", "run.py", "return 0 if all(r.ok for r in reports) else 1", "return 0"),
    ("the fixture manifest is not checked", "run.py", "problems = fx.check_manifest()", "problems = []"),
    ("the fixture adapter calls itself executed", "adapters.py", 'label = "fixture"\n\n    def __init__(self, stage):', 'label = "executed"\n\n    def __init__(self, stage):'),
    ("the report does not say that something was not executed", "vcnpipe.py", 'if s["fixture"]:', "if False:"),
    ("an unavailable adapter is an error even without --require-executed", "vcnpipe.py", 'notes.append("FIXTURE FALLBACK: %s" % u)\n            return fxa', 'raise StageError("unavailable: %s" % u)'),
]


@unittest.skipIf(os.environ.get("VCN_PIPELINE_SEEDED_RUN"), "inside a seeded run")
class SeededDefects(unittest.TestCase):
    def test_every_defect_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, rel, old, new in DEFECTS:
                work = os.path.join(tmp, "w")
                shutil.rmtree(work, ignore_errors=True)
                shutil.copytree(HERE, work, ignore=shutil.ignore_patterns("__pycache__"))
                path = os.path.join(work, rel)
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
                self.assertEqual(src.count(old), 1, "stale defect %r: %r occurs %d times" % (name, old[:60], src.count(old)))
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(src.replace(old, new))
                env = dict(os.environ, VCN_PIPELINE_SEEDED_RUN="1")
                for v in ("CIC_MODULE_PATH", "CIC_REGISTRY_PATH", "CIC_ENGINE_PATH", "CIC_RELAY_PATH"):
                    env.pop(v, None)
                done = subprocess.run([sys.executable, "-m", "unittest", "test_vcn_pipeline"], cwd=work, env=env, capture_output=True, text=True)
                self.assertNotEqual(done.returncode, 0, "NOT CAUGHT: %s" % name)


if __name__ == "__main__":
    unittest.main()
