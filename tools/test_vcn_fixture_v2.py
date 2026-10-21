#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""The v2 VCN fixture on disk is what its generator writes, the manifest is right, and the scope decisions of 2026-10-21 hold."""
import hashlib
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "..", "fixtures", "vcn-v2")
spec = importlib.util.spec_from_file_location("vcn2_gen", os.path.join(FX, "generate.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def load(*p):
    with open(os.path.join(FX, *p), encoding="utf-8") as fh:
        return json.load(fh)


def case(c, name):
    return load("cases", c, "expected", name)


class FixtureV2Tests(unittest.TestCase):
    def test_the_files_are_what_the_generator_writes(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_the_manifest_matches_every_file(self):
        with open(os.path.join(FX, "MANIFEST.sha256"), encoding="utf-8") as fh:
            rows = [l.split("  ", 1) for l in fh.read().splitlines()]
        self.assertGreater(len(rows), 100)
        for digest, name in rows:
            with open(os.path.join(FX, name), "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), digest, name)

    def test_every_case_has_every_stage(self):
        cases = load("cases.json")
        self.assertEqual(len(cases), 13)
        for c in cases:
            for f in ("observed.oci.json", "observed.registry.json", "plan.json", "scope.json", "engine-input.json",
                      "verdict.fields.json", "evidence.claims.json"):
                self.assertTrue(os.path.exists(os.path.join(FX, "cases", c, "expected", f)), (c, f))
            self.assertTrue(os.path.exists(os.path.join(FX, "cases", c, "oci", "response.json"))
                            != os.path.exists(os.path.join(FX, "cases", c, "oci", "error.json")), c)

    def test_there_is_no_global_plan_and_the_plan_follows_the_intent(self):
        self.assertFalse(os.path.exists(os.path.join(FX, "plan.json")))
        for c in load("cases.json"):
            cfg = load("cases", c, "intent.registry.json")["config"]
            planned = {s["path"] for s in case(c, "plan.json")["scalars"]}
            self.assertEqual(planned, {"/" + k for k in gen.SCALARS if k in cfg}, c)

    def test_an_undeclared_field_has_no_verdict_entry_and_is_listed_as_unmanaged(self):
        for c in ("desired-absent", "desired-absent-observed-present"):
            self.assertNotIn("/dns_label", case(c, "verdict.fields.json")["fields"], c)
            self.assertNotIn("/dns_label", case(c, "engine-input.json")["intent"], c)
        v = case("desired-absent-observed-present", "verdict.fields.json")
        self.assertEqual(v["object"], "CONFORMANT")
        self.assertEqual(case("desired-absent-observed-present", "scope.json")["unmanaged_observed_paths"], ["/dns_label"])
        self.assertEqual(case("desired-absent-observed-present", "observed.registry.json")["config"]["dns_label"], "prod")   # still seen
        self.assertEqual(case("desired-absent", "scope.json")["unmanaged_observed_paths"], [])    # nothing was seen, nothing to list

    def test_the_verdict_covers_exactly_the_managed_paths(self):
        for c in load("cases.json"):
            self.assertEqual(sorted(case(c, "verdict.fields.json")["fields"]), case(c, "scope.json")["managed_paths"], c)
            self.assertEqual(sorted(o["path"] for o in case(c, "engine-input.json")["observation"]),
                             case(c, "scope.json")["managed_paths"], c)
            self.assertEqual(case(c, "engine-input.json")["plan"], case(c, "plan.json"), c)

    def test_unmanaged_paths_are_never_in_the_engine_input_or_the_verdict(self):
        for c in load("cases.json"):
            sc = case(c, "scope.json")
            self.assertFalse(set(sc["unmanaged_observed_paths"]) & set(sc["managed_paths"]), c)
            self.assertFalse(set(sc["unmanaged_observed_paths"]) & set(case(c, "verdict.fields.json")["fields"]), c)

    def test_declared_keys_projects_the_observed_tags_but_the_observation_keeps_them(self):
        full = {t["key"] for t in case("extra-tag-undeclared", "observed.registry.json")["config"]["tags"]}
        proj = {t["key"] for t in case("extra-tag-undeclared", "engine-input.json")["observed"]["tags"]}
        self.assertEqual(full, {"env", "owner", "cost-center"})
        self.assertEqual(proj, {"env", "owner"})
        self.assertEqual(case("extra-tag-undeclared", "verdict.fields.json")["object"], "CONFORMANT")
        self.assertEqual(case("extra-tag-undeclared", "scope.json")["unmanaged_observed_paths"], ["/tags/{key=cost-center}/value"])

    def test_full_set_brings_the_extra_tag_into_the_scope(self):
        v = case("extra-tag-full-set", "verdict.fields.json")
        self.assertEqual(v["fields"]["/tags/{key=cost-center}/value"], "NOT_COMPARABLE")
        self.assertEqual(v["object"], "DRIFT")
        self.assertEqual(case("extra-tag-full-set", "scope.json")["unmanaged_observed_paths"], [])
        self.assertEqual(load("cases", "extra-tag-full-set", "intent.registry.json")["management"]["tags_scope"], "full-set")

    def test_a_declared_tag_that_oci_lacks_is_authoritative_absence(self):
        o = case("declared-tag-missing", "observed.registry.json")
        self.assertEqual(o["coverage"]["/tags/{key=owner}/value"], "absent")
        self.assertEqual(case("declared-tag-missing", "verdict.fields.json")["fields"]["/tags/{key=owner}/value"], "DRIFT")

    def test_an_empty_cidr_list_is_unknown_and_the_raw_value_is_kept(self):
        o3 = case("empty-cidr-blocks", "observed.oci.json")
        self.assertEqual(o3["coverage"]["/cidrBlocks"], "unknown")
        self.assertEqual(o3["observed_raw"], {"/cidrBlocks": []})
        self.assertNotIn("cidrBlocks", o3["effective_config"])
        v = case("empty-cidr-blocks", "verdict.fields.json")
        self.assertEqual((v["fields"]["/cidr_block"], v["object"]), ("UNOBSERVED", "INCOMPLETE"))

    def test_nothing_unobserved_or_unknown_is_ever_conformant(self):
        for c in load("cases.json"):
            obs = {o["path"]: o["coverage"] for o in case(c, "engine-input.json")["observation"]}
            ver = case(c, "verdict.fields.json")
            for path, cov in obs.items():
                if cov in ("unobserved", "unknown"):
                    self.assertEqual(ver["fields"][path], "UNOBSERVED", (c, path))
            if "UNOBSERVED" in ver["fields"].values() and not {"DRIFT", "NOT_COMPARABLE"} & set(ver["fields"].values()):
                self.assertEqual(ver["object"], "INCOMPLETE", c)

    def test_the_evidence_claims_apply_to_the_declared_scope_only(self):
        for c in load("cases.json"):
            claims, ver, sc = case(c, "evidence.claims.json"), case(c, "verdict.fields.json"), case(c, "scope.json")
            self.assertEqual(claims["conformance_scope"], "declared", c)
            self.assertEqual(claims["conformance_claimed"], ver["object"] == "CONFORMANT", c)
            self.assertEqual(claims["scope"]["managed_paths"], sc["managed_paths"], c)
            self.assertEqual(claims["scope"]["unmanaged_observed_paths"], sc["unmanaged_observed_paths"], c)
            if claims["conformance_claimed"]:
                self.assertEqual((claims["drift_paths"], claims["unobserved_paths"]), ([], []), c)

    def test_a_partial_read_is_not_false_and_a_404_is_not_absence(self):
        self.assertNotIn("ipv6_enabled", case("partial-read", "observed.registry.json")["config"])
        self.assertEqual(case("partial-read", "observed.registry.json")["coverage"]["/ipv6_enabled"], "unobserved")
        self.assertEqual(set(case("not-found", "observed.oci.json")["coverage"].values()), {"unknown"})
        self.assertEqual(set(case("transport-error", "observed.oci.json")["coverage"].values()), {"unobserved"})

    def test_the_lifecycle_map_has_no_silent_default(self):
        m = load("lifecycle-map.json")
        self.assertEqual((m["other"], m["map"]["UPDATING"]), ("unknown", "unknown"))


if __name__ == "__main__":
    unittest.main()
