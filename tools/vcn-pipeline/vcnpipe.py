# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""The core of the local, read-only OCI VCN pipeline: Intent -> Observed State -> Conformance/Drift -> Evidence.

Four stages, one adapter each, behind one interface (a stage turns the outputs of the stages before it into its own output):

    3 normalize  the oracle module     raw GetVcn answer          -> observed state in OCI names, with coverage
    4 bind       the schema registry   observed (OCI names)       -> observed state in registry names, with coverage
    5 verdict    the primitive engine  intent + observed + plan   -> per-path verdicts and the object verdict
    6 evidence   the Relay             all of the above           -> the evidence claims, in a hash chain

Every stage result carries an honest label: `executed` (the real component ran, from its checkout) or `fixture` (the expected file of
the fixture was used, because the executed adapter was unavailable). A fixture stage is never reported as executed; a stage that was
required to be executed and was not is an error; an executed adapter that ran and failed or disagreed is an error and never falls
back. The runner hands each stage the ACTUAL output of the stage before it (never the fixture's expected file), then checks the
handoff by digest and the result against the fixture's expected files.

Nothing here talks to OCI, signs anything or claims a cryptographic proof.
"""
import hashlib
import json
import os

STAGES = ("normalize", "bind", "verdict", "evidence")
STAGE_NO = {"normalize": 3, "bind": 4, "verdict": 5, "evidence": 6}
# what each stage consumes (names of artifacts) and what its output is compared with (a file under the case's expected/)
CONSUMES = {
    "normalize": ("raw",),
    "bind": ("obs_oci", "intent"),
    "verdict": ("obs_reg", "intent", "plan"),
    "evidence": ("raw", "intent", "obs_oci", "obs_reg", "verdict", "plan"),
}
OUTPUT_NAME = {"normalize": "obs_oci", "bind": "obs_reg", "verdict": "verdict", "evidence": "claims"}
EXPECTED_FILE = {"obs_oci": "observed.oci.json", "obs_reg": "observed.registry.json", "verdict": "verdict.fields.json",
                 "claims": "evidence.claims.json"}


class StageError(Exception):
    """A stage ran (or tried to) and failed, or its result is wrong. Never answered with a fallback."""


class Unavailable(Exception):
    """An executed adapter cannot be used here (a path or a tool is missing). Only this may be answered with the fixture adapter."""


def canon(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(doc):
    return hashlib.sha256(canon(doc).encode("utf-8")).hexdigest()


class Fixture:
    """A fixture directory in the v1 layout (a global plan.json, expected/ files per case)."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        if not os.path.isdir(self.root):
            raise StageError("fixture directory not found: %s" % root)
        if any(os.path.exists(os.path.join(self.root, "cases", c, "expected", "scope.json")) for c in self._case_dirs()):
            raise StageError("this is a v2 (scope-aware) fixture: this runner version understands the v1 layout only; "
                             "see docs/vcn-pipeline.md, 'Fixture v2'")

    def _case_dirs(self):
        d = os.path.join(self.root, "cases")
        return sorted(os.listdir(d)) if os.path.isdir(d) else []

    def load(self, *parts):
        path = os.path.join(self.root, *parts)
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError) as e:
            raise StageError("fixture file %s: %s" % ("/".join(parts), e))

    def text(self, *parts):
        with open(os.path.join(self.root, *parts), encoding="utf-8") as fh:
            return fh.read()

    def cases(self):
        return sorted(self.load("cases.json"))

    def plan(self, case):
        return self.load("plan.json")

    def intent(self, case):
        return self.load("cases", case, "intent.registry.json")

    def raw(self, case):
        """(kind, document, text) of the OCI answer: 'response' (200 and a body) or 'error' (an HTTP error or no answer)."""
        for kind, name in (("response", "response.json"), ("error", "error.json")):
            if os.path.exists(os.path.join(self.root, "cases", case, "oci", name)):
                return kind, self.load("cases", case, "oci", name), self.text("cases", case, "oci", name)
        raise StageError("case %s has no OCI answer" % case)

    def expected(self, case, name):
        return self.load("cases", case, "expected", EXPECTED_FILE[name])

    def check_manifest(self):
        """Every listed file has the listed digest, and every file in the directory is listed (README.md, MANIFEST and SOURCE aside)."""
        listed = {}
        for line in self.text("MANIFEST.sha256").splitlines():
            h, _, name = line.partition("  ")
            listed[name] = h
        problems = []
        for name, h in listed.items():
            try:
                with open(os.path.join(self.root, name), "rb") as fh:
                    if hashlib.sha256(fh.read()).hexdigest() != h:
                        problems.append("changed: " + name)
            except OSError:
                problems.append("missing: " + name)
        for base, _, names in os.walk(self.root):
            for n in names:
                rel = os.path.relpath(os.path.join(base, n), self.root).replace(os.sep, "/")
                if rel not in listed and rel not in ("MANIFEST.sha256", "README.md", "SOURCE.md") and "__pycache__" not in rel:
                    problems.append("not in the manifest: " + rel)
        return problems


class StageResult:
    def __init__(self, stage, label, method, output, consumed, notes=()):
        self.stage, self.label, self.method = stage, label, method
        self.output, self.consumed, self.notes = output, consumed, list(notes)


class Adapter:
    """One stage, one way of doing it. `label` is 'executed' or 'fixture'."""

    stage = None
    label = None

    def check_available(self, env):
        """Raise Unavailable(reason) if this adapter cannot run here. Called before run()."""

    def run(self, fx, case, inputs, env):
        raise NotImplementedError


class CaseReport:
    def __init__(self, case):
        self.case, self.stages, self.errors, self.verdict, self.notes = case, [], [], None, []

    @property
    def ok(self):
        return not self.errors

    def as_dict(self):
        return {"case": self.case, "ok": self.ok, "errors": self.errors, "object_verdict": self.verdict, "notes": self.notes,
                "stages": [{"stage": r.stage, "no": STAGE_NO[r.stage], "label": r.label, "method": r.method,
                            "output_digest": digest(r.output), "consumed": r.consumed, "notes": r.notes} for r in self.stages]}


class Runner:
    def __init__(self, fx, adapters, env=None, require_executed=(), fixture_only=False):
        """adapters: {stage: {"executed": Adapter, "fixture": Adapter}}."""
        self.fx, self.adapters, self.env = fx, adapters, dict(os.environ if env is None else env)
        self.require_executed, self.fixture_only = set(require_executed), fixture_only
        bad = self.require_executed - set(STAGES)
        if bad:
            raise StageError("unknown stage(s) to require: %s" % ", ".join(sorted(bad)))
        if self.fixture_only and self.require_executed:
            raise StageError("--fixture-only and --require-executed contradict each other")

    def _pick(self, stage, notes):
        ex, fxa = self.adapters[stage]["executed"], self.adapters[stage]["fixture"]
        if self.fixture_only:
            return fxa
        try:
            ex.check_available(self.env)
            return ex
        except Unavailable as u:
            if stage in self.require_executed:
                raise StageError("stage %d (%s) must be executed but cannot be: %s" % (STAGE_NO[stage], stage, u))
            notes.append("FIXTURE FALLBACK: %s" % u)
            return fxa

    def run_case(self, case):
        rep = CaseReport(case)
        try:
            kind, raw_doc, _ = self.fx.raw(case)
            arts = {"raw": raw_doc, "intent": self.fx.intent(case), "plan": self.fx.plan(case)}
            for stage in STAGES:
                notes = []
                adapter = self._pick(stage, notes)
                try:
                    res = adapter.run(self.fx, case, dict(arts), self.env)
                except StageError:
                    raise
                except Exception as e:                      # an adapter that blows up is an error, never a fallback
                    raise StageError("stage %d (%s) %s adapter failed: %s: %s" % (STAGE_NO[stage], stage, adapter.label, type(e).__name__, e))
                res.notes = notes + res.notes
                if res.label != adapter.label or res.stage != stage:
                    raise StageError("stage %d (%s): the adapter reported label/stage %r/%r, it is %r/%r" %
                                     (STAGE_NO[stage], stage, res.label, res.stage, adapter.label, stage))
                rep.stages.append(res)
                # the handoff: what an executed stage says it consumed is what the stages before it produced. A fixture stage consumed
                # nothing (it returns the expected file), so there is no handoff to check there, and the report says so.
                if res.label == "executed":
                    for name in CONSUMES[stage]:
                        want = digest(arts[name])
                        got = res.consumed.get(name)
                        if got != want:
                            raise StageError("handoff to stage %d (%s): it consumed %s with digest %s, the previous stage produced %s" %
                                             (STAGE_NO[stage], stage, name, got, want))
                else:
                    res.notes.append("handoff not checked: a fixture stage consumes nothing")
                out_name = OUTPUT_NAME[stage]
                expected = self.fx.expected(case, out_name)
                if res.output != expected:
                    raise StageError("stage %d (%s) output differs from the fixture's expected/%s: %s" %
                                     (STAGE_NO[stage], stage, EXPECTED_FILE[out_name], _diff(expected, res.output)))
                arts[out_name] = res.output
            exp_v = self.fx.expected(case, "verdict")
            if arts["verdict"].get("object") != exp_v.get("object") or arts["verdict"].get("fields") != exp_v.get("fields"):
                raise StageError("final verdict differs from expected/verdict.fields.json")
            rep.verdict = arts["verdict"]["object"]
            described = self.fx.load("cases.json").get(case, "")
            if "OPEN QUESTION" in described:
                rep.notes.append("OPEN QUESTION case, reproduced as the v1 fixture records it (%s). The owner decided on 2026-10-21 that an "
                                 "undeclared field is unmanaged by default; the scope-aware fixture v2 changes this outcome. This is NOT the "
                                 "current intended behaviour." % rep.verdict)
        except StageError as e:
            rep.errors.append(str(e))
        return rep


def _diff(want, got):
    if isinstance(want, dict) and isinstance(got, dict):
        parts = []
        for k in sorted(set(want) | set(got)):
            if want.get(k, "<absent>") != got.get(k, "<absent>"):
                parts.append("%s: want %s, got %s" % (k, canon(want.get(k, "<absent>"))[:120], canon(got.get(k, "<absent>"))[:120]))
        return "; ".join(parts[:4]) or "differs"
    return "want %s, got %s" % (canon(want)[:120], canon(got)[:120])


def summary(reports):
    stages = [r for rep in reports for r in rep.stages]
    n_exec = sum(1 for r in stages if r.label == "executed")
    per = {}
    for s in STAGES:
        labels = {r.label for rep in reports for r in rep.stages if r.stage == s}
        per[s] = sorted(labels)
    return {"cases": len(reports), "cases_ok": sum(1 for r in reports if r.ok), "stage_runs": len(stages), "executed": n_exec,
            "fixture": len(stages) - n_exec, "per_stage_labels": per, "all_executed": bool(stages) and n_exec == len(stages) and all(r.ok for r in reports)}


def render(reports):
    lines = []
    for rep in reports:
        lines.append("%-34s %s  %s" % (rep.case, "OK  " if rep.ok else "FAIL", rep.verdict or "-"))
        lines.append("    " + "  ".join("%d:%s=%s" % (STAGE_NO[r.stage], r.stage, r.label.upper()) for r in rep.stages))
        for r in rep.stages:
            for n in r.notes:
                lines.append("    stage %d: %s" % (STAGE_NO[r.stage], n))
        for n in rep.notes:
            lines.append("    NOTE: " + n)
        for e in rep.errors:
            lines.append("    ERROR: " + e)
    s = summary(reports)
    lines.append("")
    lines.append("%d/%d cases ok; stage runs: %d executed, %d fixture" % (s["cases_ok"], s["cases"], s["executed"], s["fixture"]))
    lines.append("per stage: " + "; ".join("%d %s: %s" % (STAGE_NO[k], k, "/".join(v) or "-") for k, v in s["per_stage_labels"].items()))
    methods = sorted({(STAGE_NO[r.stage], r.stage, r.label, r.method) for rep in reports for r in rep.stages})
    lines.append("how each stage ran:")
    for no, stage, label, method in methods:
        lines.append("  %d %-9s %-8s %s" % (no, stage, label.upper(), method))
    if s["fixture"]:
        lines.append("NOT everything was executed: stages labelled FIXTURE used the fixture's expected file, not the component.")
    return "\n".join(lines)
