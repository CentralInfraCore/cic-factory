#!/usr/bin/env python3
"""PR-05 baseline: what the PR-04 verifier (object_model.py at CIC_Relay d38a1d5 / main) really does with seeded defects.
Measurement only: nothing is changed. Inputs are the real PR-04 fixtures (goastdump unit + cic-canonical Rust file).
usage: baseline_weaknesses.py <repo-root>"""
import copy, json, os, shutil, subprocess, sys, tempfile
repo = sys.argv[1]
sys.path.insert(0, f"{repo}/scripts")
import object_model as om, quality_gate as qg
FIX = f"{repo}/tests/test_tools/fixtures/object_model"
J = lambda n: json.load(open(f"{FIX}/{n}"))
T = lambda n: open(f"{FIX}/{n}").read()

def objects():
    blocks = om.parse_coverprofile(T("goastdump-cover.out"))
    go, _ = om.go_objects("goastdump", "goastdump", J("goastdump-inventory.json"), blocks, detail=True)
    root = tempfile.mkdtemp(); os.makedirs(f"{root}/cic-canonical/src"); shutil.copy(f"{FIX}/cic-canonical-lib.rs.txt", f"{root}/cic-canonical/src/lib.rs")
    ver = qg.rust_verdicts(J("outcomes-cic-canonical.json"), "fixture")
    rs, _ = om.rust_objects(J("llvm-cov-cic-canonical.json"), J("demangled-cic-canonical.json"), root, J("mutants-cic-canonical.json"), ver)
    return go, rs

def checkout():
    d = tempfile.mkdtemp(); env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    shutil.copy(f"{FIX}/goastdump-main.go.txt", f"{d}/main.go")
    for a in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "x"]):
        subprocess.run(["git", "-C", d, *a], check=True, env=env)
    g = lambda *a: subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=True).stdout.strip()
    return d, g("rev-parse", "HEAD"), g("rev-parse", "HEAD^{tree}")

go, rs = objects(); d, commit, tree = checkout()
inputs = {"x": {"sha256": "0" * 64, "bytes": 1}}
TOOLS = {"go": "go1.26.10", "rustc": "1.96.1", "cargo-mutants": "27.1.0", "cargo-llvm-cov": "0.9.1", "c++filt": "2.40"}
SCOPE = json.load(open(f"{repo}/.measurement-scope.json"))
honest = om.build_record(go + rs, commit, tree, TOOLS, inputs, SCOPE, {})
mutants = J("mutants-cic-canonical.json")
def reseal(r):
    r = copy.deepcopy(r); r["summary"] = om.summarize(r["objects"]); r["digest"] = om.canonical_digest({k: v for k, v in r.items() if k != "digest"}); return r
def run(r): 
    res = om.verify_record(r, d, {}, {"goastdump": ["main.go"]}, mutants)
    return " ".join(f"{k}={res[k]['verdict']}" for k in ("L1", "L2", "L3")), res
print(f"honest record: {len(honest['objects'])} objects ({sum(o['unit']=='goastdump' for o in honest['objects'])} go goastdump, {sum(o['lang']=='rust' for o in honest['objects'])} rust)")
v, res = run(honest); print(f"[control] honest record                          -> {v}")
print("   L3 unproven:", *res["L3"].get("unproven", []), sep="\n     ")

print("\n[W1] set identity: swap one goastdump object for a fake id, same count, resealed")
r = copy.deepcopy(honest); i = next(k for k, o in enumerate(r["objects"]) if o["unit"] == "goastdump"); fake = dict(r["objects"][i], id="go:goastdump.DoesNotExist", name="DoesNotExist")
r["objects"][i] = fake; r["objects"].sort(key=lambda o: o["id"]); v, res = run(reseal(r)); print(f"   swapped {len(r['objects'])} objects                 -> {v}   (L3 should be FAIL; a count cannot see a swap)")

print("\n[W2] can the L3 ever be PASS (COMPLETE_FOR_SCOPE) with the honest record and every input given?")
print(f"   honest record -> L3={run(honest)[1]['L3']['verdict']}   (always PARTIAL: the Rust part has no independent inventory)")

print("\n[W3] re-sealed VALUE forgery: one objects coverage changed to 100%, digest and summary recomputed, inputs untouched")
r = copy.deepcopy(honest); o = next(o for o in r["objects"] if o["unit"] == "goastdump" and o["coverage"]["state"] == "MEASURED" and o["coverage"]["covered"] < o["coverage"]["total"])
before = (o["coverage"]["covered"], o["coverage"]["total"]); o["coverage"]["covered"] = o["coverage"]["total"]; o["coverage"].pop("uncovered", None)
v, _ = run(reseal(r)); print(f"   {o['id']}: {before[0]}/{before[1]} -> {o['coverage']['covered']}/{o['coverage']['total']}   -> {v}   (no level re-derives the value from the inputs)")
r2 = copy.deepcopy(honest); next(x for x in r2["objects"] if x["id"] == o["id"])["coverage"]["covered"] = o["coverage"]["total"]
print(f"   the same change WITHOUT re-sealing -> {run(r2)[0]}   (the naive tamper is the only one the digest catches)")

print("\n[W4] duplicates")
r = copy.deepcopy(honest); r["objects"].append(copy.deepcopy(r["objects"][0])); r["objects"].sort(key=lambda o: o["id"]); v, res = run(reseal(r))
print(f"   same id twice, resealed -> {v}   L1 findings: {res['L1']['findings'][:1]}")
r = copy.deepcopy(honest); dup = copy.deepcopy(next(o for o in r["objects"] if o["unit"] == "goastdump")); dup["id"] += "#dup"; r["objects"].append(dup)
gi = [k for k, o in enumerate(r["objects"]) if o["unit"] == "goastdump"][1]; del r["objects"][gi]; r["objects"].sort(key=lambda o: o["id"]); v, _ = run(reseal(r))
print(f"   another id for the SAME source object, count kept equal (one other object removed), resealed -> {v}")

print("\n[W5] determinism: does a record say how many runs a measured coverage value comes from?")
c = next(o for o in honest["objects"] if o["coverage"]["state"] == "MEASURED")["coverage"]; print(f"   a MEASURED coverage field: {sorted(c)}   -> 'runs' present: {'runs' in c}")
