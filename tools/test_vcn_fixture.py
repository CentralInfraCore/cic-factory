#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""The VCN fixture on disk is exactly what its generator writes, its manifest is right, and its expected verdicts follow the
documented engine semantics (the properties the four repositories rely on)."""
import hashlib
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "..", "fixtures", "vcn-v1")
spec = importlib.util.spec_from_file_location("vcn_gen", os.path.join(FX, "generate.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def load(*p):
    with open(os.path.join(FX, *p), encoding="utf-8") as fh:
        return json.load(fh)


class FixtureTests(unittest.TestCase):
    def test_the_files_are_what_the_generator_writes(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_the_manifest_matches_every_file(self):
        with open(os.path.join(FX, "MANIFEST.sha256"), encoding="utf-8") as fh:
            rows = [l.split("  ", 1) for l in fh.read().splitlines()]
        self.assertGreater(len(rows), 50)
        for digest, name in rows:
            with open(os.path.join(FX, name), "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), digest, name)

    def test_every_case_has_every_stage(self):
        cases = load("cases.json")
        self.assertEqual(len(cases), 9)
        for c in cases:
            for f in ("intent.registry.json", "expected/observed.oci.json", "expected/observed.registry.json",
                      "expected/verdict.fields.json", "expected/evidence.claims.json"):
                self.assertTrue(os.path.exists(os.path.join(FX, "cases", c, f)), (c, f))
            self.assertTrue(os.path.exists(os.path.join(FX, "cases", c, "oci", "response.json"))
                            != os.path.exists(os.path.join(FX, "cases", c, "oci", "error.json")), c)

    def test_nothing_unobserved_or_unknown_is_ever_conformant(self):
        for c in load("cases.json"):
            obs, ver = load("cases", c, "expected", "observed.registry.json"), load("cases", c, "expected", "verdict.fields.json")
            for path, cov in obs["coverage"].items():
                if cov in ("unobserved", "unknown"):
                    self.assertEqual(ver["fields"][path], "UNOBSERVED", (c, path))
            if "UNOBSERVED" in ver["fields"].values() and "DRIFT" not in ver["fields"].values():
                self.assertEqual(ver["object"], "INCOMPLETE", c)
            claims = load("cases", c, "expected", "evidence.claims.json")
            self.assertEqual(claims["conformance_claimed"], ver["object"] == "CONFORMANT", c)
            if claims["conformance_claimed"]:
                self.assertEqual((claims["drift_paths"], claims["unobserved_paths"]), ([], []), c)

    def test_a_partial_read_is_not_false_and_a_404_is_not_absence(self):
        o = load("cases", "partial-read", "expected", "observed.registry.json")
        self.assertNotIn("ipv6_enabled", o["config"])
        self.assertEqual(o["coverage"]["/ipv6_enabled"], "unobserved")
        nf = load("cases", "not-found", "expected", "observed.registry.json")
        self.assertEqual(set(nf["coverage"].values()), {"unknown"})
        self.assertEqual(set(load("cases", "transport-error", "expected", "observed.registry.json")["coverage"].values()), {"unobserved"})

    def test_the_open_question_is_recorded_not_hidden(self):
        v = load("cases", "desired-absent-observed-present", "expected", "verdict.fields.json")
        self.assertEqual((v["fields"]["/dns_label"], v["object"]), ("NOT_COMPARABLE", "DRIFT"))
        self.assertIn("OPEN QUESTION", load("cases.json")["desired-absent-observed-present"])

    def test_the_lifecycle_map_has_no_silent_default(self):
        m = load("lifecycle-map.json")
        self.assertEqual(m["other"], "unknown")
        self.assertEqual(m["map"]["UPDATING"], "unknown")           # OCI has a state the registry enum cannot name
        self.assertEqual(set(m["map"].values()) - {"unknown"}, {"pending", "available", "deleting", "deleted"})


if __name__ == "__main__":
    unittest.main()
