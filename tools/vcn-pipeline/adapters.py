# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""The adapters of the VCN pipeline: one `fixture` and one `executed` adapter per stage.

The `executed` adapters run the REAL code of a component from its checkout without modifying that checkout: the component's sources
are copied to a scratch directory, a small test shim from `shims/` is added to the COPY, and the component's own build tool runs
the shim on the artifact the previous stage produced. The method is written into every result. Where a component has no official
entry point for its stage this is the only way to execute it; docs/vcn-pipeline.md proposes the thin entry point each repository
would need so that the shims can go away.

Environment: CIC_MODULE_PATH, CIC_REGISTRY_PATH, CIC_ENGINE_PATH, CIC_RELAY_PATH (the checkouts), CIC_PIPELINE_WORK (an optional
scratch/cache directory that survives the run; otherwise a temporary one). Tools: go (module, relay), cargo (engine), python3 with
PyYAML (registry).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import vcnpipe
from vcnpipe import Adapter, StageError, StageResult, Unavailable, digest

HERE = os.path.dirname(os.path.abspath(__file__))
SHIMS = os.path.join(HERE, "shims")
OUT = re.compile(r"^PIPELINE_SHIM_OUT (.*)$", re.M)

# the OCI paths the common fixture compares in stage 3 (the module returns the whole contract; the fixture's expected files are the
# projection to these, as the module's own test compares them)
OCI_COMPARED = ("/cidrBlocks", "/dnsLabel", "/freeformTags", "/isIpv6Enabled")
OCI_STATE = ("id", "lifecycleState", "ipv6CidrBlocks")
REGISTRY_CORRESPONDENCE = "providers/oracle-cloud/network/network-space/network-space.correspondence.yaml"


# ---- fixture adapters --------------------------------------------------------------------------------------------------------
class FixtureAdapter(Adapter):
    label = "fixture"

    def __init__(self, stage):
        self.stage = stage

    def run(self, fx, case, inputs, env):
        out = fx.expected(case, vcnpipe.OUTPUT_NAME[self.stage])
        return StageResult(self.stage, "fixture", "expected file of the fixture", out, {})


# ---- helpers -----------------------------------------------------------------------------------------------------------------
def _work(env):
    base = env.get("CIC_PIPELINE_WORK")
    if base:
        os.makedirs(base, exist_ok=True)
        return base
    return None


class _Scratch:
    """A scratch copy of a component, made once per Adapter instance."""

    def __init__(self, tag):
        self.tag, self.dir, self._tmp = tag, None, None

    def get(self, env, build):
        if self.dir is None:
            base = _work(env)
            if base is None:
                self._tmp = tempfile.mkdtemp(prefix="vcn-pipeline-%s-" % self.tag)
                base = self._tmp
            self.dir = os.path.join(base, self.tag)
            if os.path.exists(self.dir):
                shutil.rmtree(self.dir)
            build(self.dir)
        return self.dir


def _copy_tree(src, dst, skip=(".git", "target", "node_modules", "__pycache__")):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*skip), symlinks=True)


def _run(argv, cwd, env, timeout=1800):
    done = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return done


def _shim_out(done, what):
    if done.returncode != 0:
        tail = (done.stdout + done.stderr).strip().splitlines()[-12:]
        raise StageError("%s failed (exit %d): %s" % (what, done.returncode, " | ".join(tail)[:900]))
    m = OUT.search(done.stdout)
    if not m:
        raise StageError("%s printed no PIPELINE_SHIM_OUT line" % what)
    try:
        return json.loads(m.group(1))
    except ValueError as e:
        raise StageError("%s printed unreadable output: %s" % (what, e))


def _need_path(env, var, probe):
    p = env.get(var)
    if not p:
        raise Unavailable("%s is not set" % var)
    if not os.path.exists(os.path.join(p, probe)):
        raise Unavailable("%s=%s has no %s" % (var, p, probe))
    return p


def _need_tool(tool, env):
    if not shutil.which(tool, path=env.get("PATH")):
        raise Unavailable("`%s` is not on PATH" % tool)


# ---- stage 3: the oracle module ---------------------------------------------------------------------------------------------
class ModuleAdapter(Adapter):
    stage, label = "normalize", "executed"

    def __init__(self):
        self.scratch = _Scratch("module")

    def check_available(self, env):
        _need_path(env, "CIC_MODULE_PATH", "module/observed.go")
        _need_tool("go", env)

    def _prepare(self, env):
        def build(dst):
            _copy_tree(os.path.join(env["CIC_MODULE_PATH"], "module"), dst)
            shutil.copy(os.path.join(SHIMS, "module_shim_test.go"), os.path.join(dst, "pipeline_shim_test.go"))
        return self.scratch.get(env, build)

    def run(self, fx, case, inputs, env):
        kind, doc, text = fx.raw(case)
        if kind == "response":
            outcome = {"status": 200, "body": text, "transport": ""}
        elif doc.get("kind") == "transport":
            outcome = {"status": 0, "body": "", "transport": str(doc.get("message", "transport error"))}
        elif doc.get("kind") == "http":
            outcome = {"status": int(doc["status"]), "body": json.dumps({"code": doc.get("code", "")}), "transport": ""}
        else:
            raise StageError("unknown OCI error kind %r" % doc.get("kind"))
        d = self._prepare(env)
        inp = os.path.join(d, "pipeline_in.json")
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(outcome, fh)
        e = dict(os.environ, **{k: v for k, v in env.items() if k in ("PATH", "HOME", "GOPATH", "GOCACHE", "GOMODCACHE")})
        e.update(PIPELINE_SHIM_IN=inp, GOTOOLCHAIN=env.get("GOTOOLCHAIN", "local"), GOFLAGS="-mod=mod")
        got = _shim_out(_run(["go", "test", "-count=1", "-run", "^TestPipelineShim$", "-v", "."], d, e), "the module shim")
        cov = got.get("coverage", {})
        eff, state = got.get("effective_config", {}), got.get("state", {})
        out = {"effective_config": {p[1:]: eff[p[1:]] for p in OCI_COMPARED if p[1:] in eff},
               "state": {k: state[k] for k in OCI_STATE if k in state},
               "coverage": {p: cov[p] for p in OCI_COMPARED if p in cov}}
        if set(out["coverage"]) != set(OCI_COMPARED):
            raise StageError("the module reported no coverage for %s" % sorted(set(OCI_COMPARED) - set(out["coverage"])))
        return StageResult(self.stage, "executed", "go test shim on a scratch copy of module/ (normalizeObserved)", out,
                           {"raw": digest(doc)},
                           ["projected to the OCI paths the fixture compares: %s" % ", ".join(OCI_COMPARED)])


# ---- stage 4: the schema registry -------------------------------------------------------------------------------------------
REGISTRY_SCRIPT = r"""
import json, sys
req = json.load(sys.stdin)
sys.path.insert(0, req["registry"])
from tools.registrylib import correspondence as c
doc = c.load(req["registry"] + "/" + req["correspondence"])
out = c.apply(doc, req["observed"], req["intent"], set(req["emit"]))
print("PIPELINE_SHIM_OUT " + json.dumps(out, sort_keys=True))
"""


class RegistryAdapter(Adapter):
    stage, label = "bind", "executed"

    def check_available(self, env):
        p = _need_path(env, "CIC_REGISTRY_PATH", REGISTRY_CORRESPONDENCE)
        if not os.path.exists(os.path.join(p, "tools", "registrylib", "correspondence.py")):
            raise Unavailable("CIC_REGISTRY_PATH has no tools/registrylib/correspondence.py")
        try:
            import yaml  # noqa: F401
        except ImportError:
            raise Unavailable("PyYAML is not installed")

    def run(self, fx, case, inputs, env):
        plan = inputs["plan"]
        emit = sorted({s["path"][1:] for s in plan.get("scalars", [])} | {c["path"][1:] for c in plan.get("collections", [])})
        req = {"registry": env["CIC_REGISTRY_PATH"], "correspondence": REGISTRY_CORRESPONDENCE, "observed": inputs["obs_oci"],
               "intent": inputs["intent"], "emit": emit}
        done = subprocess.run([sys.executable, "-I", "-c", REGISTRY_SCRIPT], input=json.dumps(req), capture_output=True, text=True, timeout=300)
        out = _shim_out(done, "the registry applier")
        return StageResult(self.stage, "executed", "python -I import of tools.registrylib.correspondence from the checkout (apply)", out,
                           {"obs_oci": digest(req["observed"]), "intent": digest(req["intent"])})


# ---- stage 5: the primitive engine ------------------------------------------------------------------------------------------
class EngineAdapter(Adapter):
    stage, label = "verdict", "executed"

    def __init__(self):
        self.scratch = _Scratch("engine")

    def check_available(self, env):
        _need_path(env, "CIC_ENGINE_PATH", "engine/tests/differential.rs")
        _need_tool("cargo", env)

    def _prepare(self, env):
        def build(dst):
            _copy_tree(env["CIC_ENGINE_PATH"], dst)
            with open(os.path.join(dst, "engine", "tests", "differential.rs"), encoding="utf-8") as fh:
                text = fh.read()
            with open(os.path.join(SHIMS, "engine_shim_tail.rs"), encoding="utf-8") as fh:
                tail = fh.read()
            with open(os.path.join(dst, "engine", "tests", "pipeline_shim.rs"), "w", encoding="utf-8") as fh:
                fh.write(text + tail)
        return self.scratch.get(env, build)

    def run(self, fx, case, inputs, env):
        obs = inputs["obs_reg"]
        vec = {"intent": inputs["intent"], "observed": obs["config"],
               "observation": [{"path": p, "coverage": c} for p, c in sorted(obs["coverage"].items())], "plan": inputs["plan"]}
        d = self._prepare(env)
        inp = os.path.join(d, "pipeline_in.json")
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(vec, fh)
        e = dict(os.environ, **{k: v for k, v in env.items() if k in ("PATH", "HOME", "CARGO_HOME", "RUSTUP_HOME")})
        e.update(PIPELINE_SHIM_IN=inp, CARGO_TARGET_DIR=os.path.join(env.get("CIC_PIPELINE_WORK") or d, "engine-target"))
        done = _run(["cargo", "test", "-p", "cic-primitive-engine", "--test", "pipeline_shim", "pipeline_shim", "--", "--nocapture"], d, e)
        verdict = _shim_out(done, "the engine shim")
        out = {"object": verdict.get("object"), "fields": verdict.get("fields")}
        notes = ["engine digests: conformance_plan %s, observation %s" % (verdict.get("conformance_plan_digest"), verdict.get("observation_digest"))]
        return StageResult(self.stage, "executed", "cargo test shim on a scratch copy of the engine (evaluate_verdict)", out,
                           {"obs_reg": digest(obs), "intent": digest(vec["intent"]), "plan": digest(vec["plan"])}, notes)


# ---- stage 6: the Relay -----------------------------------------------------------------------------------------------------
class RelayAdapter(Adapter):
    stage, label = "evidence", "executed"

    def __init__(self):
        self.scratch = _Scratch("relay")

    def check_available(self, env):
        _need_path(env, "CIC_RELAY_PATH", "cmd/relay/vcn_slice_test.go")
        _need_tool("go", env)

    def _prepare(self, env, fx):
        def build(dst):
            _copy_tree(env["CIC_RELAY_PATH"], dst)
            shutil.copy(os.path.join(SHIMS, "relay_shim_test.go"), os.path.join(dst, "cmd", "relay", "pipeline_shim_test.go"))
            fixdst = os.path.join(dst, "cmd", "relay", "testdata", "vcn-v1")
            shutil.rmtree(fixdst, ignore_errors=True)
            shutil.copytree(fx.root, fixdst, ignore=shutil.ignore_patterns("__pycache__"))   # the evidence reads plan.json and the manifest from here
        return self.scratch.get(env, build)

    def run(self, fx, case, inputs, env):
        d = self._prepare(env, fx)
        inp = os.path.join(d, "pipeline_in.json")
        req = {"case": case, "raw": inputs["raw"], "intent": inputs["intent"], "observed_oci": inputs["obs_oci"],
               "observed_registry": inputs["obs_reg"], "verdict": inputs["verdict"]}
        with open(inp, "w", encoding="utf-8") as fh:
            json.dump(req, fh)
        e = dict(os.environ, **{k: v for k, v in env.items() if k in ("PATH", "HOME", "GOPATH", "GOCACHE", "GOMODCACHE")})
        e.update(PIPELINE_SHIM_IN=inp, GOTOOLCHAIN=env.get("GOTOOLCHAIN", "local"), GOFLAGS="-mod=mod")
        got = _shim_out(_run(["go", "test", "-count=1", "-run", "^TestPipelineShim$", "-v", "./cmd/relay"], d, e), "the Relay shim")
        if "error" in got:
            raise StageError("the Relay refused to build the evidence: %s" % got["error"])
        if not got["verify"].get("valid"):
            raise StageError("the Relay's own VerifyProofArtifact rejected the evidence: %s" % got["verify"].get("errors"))
        if not got.get("sidecar_bound"):
            raise StageError("the claims are not bound to the last step of the chain")
        steps = got["artifact"]["steps"]
        names = [s["name"] for s in steps]
        if names != ["normalize-oci", "bind-registry", "conformance", "claims"]:
            raise StageError("unexpected evidence steps %s" % names)
        # what the Relay says it hashed, to be compared by the runner with this side's own digests of the stage outputs
        conf_in = {"intent": inputs["intent"], "observed": inputs["obs_reg"]["config"], "coverage": inputs["obs_reg"]["coverage"], "plan": inputs["plan"]}
        consumed = {"raw": steps[0]["input_hash"], "obs_oci": steps[0]["output_hash"], "obs_reg": steps[1]["output_hash"],
                    "verdict": steps[2]["output_hash"], "intent": digest(inputs["intent"]), "plan": digest(inputs["plan"])}
        if steps[1]["input_hash"] != steps[0]["output_hash"] or steps[3]["input_hash"] != steps[2]["output_hash"]:
            raise StageError("the chain of the Relay is not linked step to step")
        if steps[2]["input_hash"] != digest(conf_in):
            raise StageError("the Relay hashed a different conformance input than the one this pipeline produced")
        if steps[3]["output_hash"] != digest(got["claims"]):
            raise StageError("the last step does not hash the claims it returned")
        c = got["claims"]
        out = {"conformance_claimed": c["conformance_claimed"], "drift_paths": c["drift_paths"], "unobserved_paths": c["unobserved_paths"], "object": c["object"]}
        return StageResult(self.stage, "executed", "go test shim on a scratch copy of the Relay (vcnEvidenceFrom, VerifyProofArtifact)", out, consumed,
                           ["chain_hash %s (a test-side chain over the stage hashes: not a signature, not a production ProofTrace)" % got["artifact"]["chain_hash"]])


def default_adapters():
    return {
        "normalize": {"executed": ModuleAdapter(), "fixture": FixtureAdapter("normalize")},
        "bind": {"executed": RegistryAdapter(), "fixture": FixtureAdapter("bind")},
        "verdict": {"executed": EngineAdapter(), "fixture": FixtureAdapter("verdict")},
        "evidence": {"executed": RelayAdapter(), "fixture": FixtureAdapter("evidence")},
    }
