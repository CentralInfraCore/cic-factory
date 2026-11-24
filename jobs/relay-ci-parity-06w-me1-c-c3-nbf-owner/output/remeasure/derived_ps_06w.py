#!/usr/bin/env python3
"""06w re-measurement of C-c3 on the 06w harness (K-time semantics of the contract amendment, repository_owner in P). Derived from derived_ps.py.

E2/E3/E4 of the P/S invariance measurement (offline, read-only on the evidence; isolated copies).

Uses the UNCHANGED harness (read-me1.py, me1-controls.py) through importlib. A copy of an evidence directory gets a token
carrying the REAL decoded claim set of that run, re-signed with a throwaway test key; the test JWKS is a separate file.
usage: derived_ps.py HARNESS_DIR OUT_DIR
"""
import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile

H, OUT = sys.argv[1], sys.argv[2]
B = os.path.expanduser("~/.cache/ci-lab")
spec = importlib.util.spec_from_file_location("mc", os.path.join(H, "me1-controls.py"))
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)
rm = mc.rm

# classes, exactly as in the contract table (#93 V3); time claims are the table's "iat/exp/nbf" row
K = ["repository", "repository_id", "repository_owner_id", "workflow_ref", "job_workflow_ref", "event_name", "ref", "sub",
     "sha", "workflow_sha", "job_workflow_sha", "run_id", "run_attempt", "check_run_id", "iss", "aud"]
KT = ["iat", "exp", "nbf"]
P = ["actor", "actor_id", "ref_type", "ref_protected", "repository_visibility", "runner_environment", "run_number", "jti", "repository_owner"]
S = ["workflow", "head_ref", "base_ref"]
HIDE = {"actor", "actor_id", "jti"}
ALIAS = {"sub": ["binds sub", "ref and subject"], "iss": ["issuer"], "aud": ["audience"], "check_run_id": ["pin: check_run_id"],
         "run_id": ["run_id", "run id"], "run_attempt": ["run_attempt", "attempt"], "iat": ["attempt window"],
         "exp": ["expired before"], "nbf": ["nbf", "not-before"], "sha": ["binds sha"], "event_name": ["event_name"],
         "ref": ["binds ref"], "workflow_ref": ["workflow_ref"], "job_workflow_ref": ["job_workflow_ref"],
         "workflow_sha": ["workflow_sha"], "job_workflow_sha": ["job_workflow_sha"], "repository": ["repository"],
         "repository_id": ["repository_id"], "repository_owner_id": ["repository_owner_id"]}
BASES = [("B / policy B", B + "/me1-raw-d6-B/45469841682", B + "/d6-eval/main-decision-policy-B.json"),
         ("A2 / policy A", B + "/d6-eval/A2", B + "/p-probe-trust/main-decision-policy.json")]
PR = [("P1", B + "/p-probe-raw/45224515605"), ("P2", B + "/p-probe-raw/45224516981")]
res = []          # (item, claim, expectation, observed, status)
out = []


def say(s=""):
    out.append(s)
    print(s)


def claims(d):
    return json.loads(rm.b64d(open(os.path.join(d, "artifact", "oidc-token.jwt")).read().strip().split(".")[1]))


def klass(n):
    return "K" if n in K else "K-time" if n in KT else "P" if n in P else "S" if n in S else "UNCLASSIFIED"


def mutate(name, v):
    s = str(v)
    if name == "repository":
        return "o/other"
    if name in ("workflow_ref", "job_workflow_ref"):
        return "o/r/.github/workflows/other.yml@refs/heads/main"
    if name == "event_name":
        return "push"
    if name == "ref":
        return "refs/heads/dev"
    if name == "sub":
        return "repo:o/r:environment:x"
    if name == "iss":
        return "https://evil.example"
    if name == "aud":
        return "sts.amazonaws.com"
    if name in ("iat", "exp", "nbf") and isinstance(v, int):
        return v + 1000000
    if isinstance(v, bool):
        return not v
    if len(s) == 40 and all(c in "0123456789abcdef" for c in s):
        return ("b2" * 20) if s != "b2" * 20 else ("c3" * 20)
    if isinstance(v, int):
        return v + 1
    if s.isdigit():
        return str(int(s) + 1)
    return s + "-x"


key = rm.Key()
jf = mc.jwks_file(key)
tmp = tempfile.mkdtemp()


def derived(base_dir, cl):
    d = os.path.join(tmp, "c%d" % len(os.listdir(tmp)))
    shutil.copytree(base_dir, d)
    open(os.path.join(d, "artifact", "oidc-token.jwt"), "w").write(rm.make_token(key, cl) + "\n")
    mc.restamp(d)
    return d


def evaluate(d, pol):
    rows = mc.evaluate_dir(d, pol, jf)
    return rm.overall(rows), [(r[0], r[1]) for r in rows], rows


# ---------------------------------------------------------------- E2 classification of the real tokens
say("## E2 claim classification of the REAL tokens (contract table #93 V3)")
allnames = {}
for lab, d in [("A", B + "/me1-raw/45063800073"), ("B", B + "/me1-raw-d6-B/45469841682")] + PR:
    c = claims(d)
    allnames[lab] = c
    say("%-3s %2d claims: K=%d K-time=%d P=%d S=%d UNCLASSIFIED=%s" % (lab, len(c), sum(klass(n) == "K" for n in c), sum(klass(n) == "K-time" for n in c),
                                                                          sum(klass(n) == "P" for n in c), sum(klass(n) == "S" for n in c),
                                                                          sorted(n for n in c if klass(n) == "UNCLASSIFIED")))
unclass = sorted({n for c in allnames.values() for n in c if klass(n) == "UNCLASSIFIED"})
res.append(("E2", "claim names of the real tokens", "all classified by the contract table", "unclassified: %s" % (unclass or "none"),
            "MET" if not unclass else "NOT-MET (specification gap)"))
say("E2 result: %s" % res[-1][4])
say()

# ---------------------------------------------------------------- E3 derived controls
for lab, bdir, polf in BASES:
    pol, err = rm.load_policy(polf)
    assert err is None, err
    cl = claims(bdir)
    say("## E3 base %s: real claim set of the run (%d claims), re-signed with a throwaway key, evidence COPY" % (lab, len(cl)))
    real_rows = rm.overall(mc.evaluate_dir(bdir, pol, B + "/d6-eval/jwks-B-20261124T195455Z.json"))
    say("real evidence, real JWKS: %s" % real_rows)
    ov0, st0, _ = evaluate(derived(bdir, dict(cl)), pol)
    ok = ov0 == rm.overall(mc.evaluate_dir(bdir, pol, B + "/d6-eval/jwks-B-20261124T195455Z.json")) and "BOUND" in ov0 and "NOT BOUND" not in ov0
    say("E3a baseline (real claims, test key): %s" % ov0)
    res.append(("E3a", lab, "derived baseline == the real verdict (BOUND)", ov0, "MET" if ok else "NOT-MET"))
    # E3b K and K-time claims
    for n in [x for x in K if x in cl]:
        c2 = dict(cl)
        c2[n] = mutate(n, cl[n])
        ov, st, rows = evaluate(derived(bdir, c2), pol)
        nm = [r[0] for r in rows if r[1] == "NOT-MET"]
        named = [r for r in nm if any(a in r.lower() for a in [n.lower()] + ALIAS.get(n, []))]
        good = "NOT BOUND" in ov and bool(named)
        res.append(("E3b", "%s: %s" % (lab, n), "NOT BOUND, a NOT-MET row names the claim", "%s; NOT-MET rows naming it: %s (all NOT-MET rows: %d)" % (ov, named[:3], len(nm)),
                    "MET" if good else "NOT-MET"))
    for n in [x for x in K + KT if x not in cl]:
        res.append(("E3b", "%s: %s" % (lab, n), "-", "claim absent from the real token of this run; not varied", "NOT-READ"))
    # E3t: the K-time claims by the 06w SEMANTICS (the violation counts, not the byte change)
    iat0, exp0, nbf0 = cl["iat"], cl["exp"], cl["nbf"]
    TIME_CASES = [("iat", iat0 + 1000000, False, "iat far outside the attempt window"), ("exp", exp0 + 1000000, False, "exp so late that the artifact is not 60 s after it"),
                  ("exp", iat0, False, "exp = iat"), ("nbf", iat0 + 1000000, False, "nbf far above iat+60"), ("nbf", iat0 + 61, False, "nbf = iat+61"),
                  ("nbf", iat0 + 60, True, "nbf = iat+60 (boundary, permitted)"), ("nbf", iat0, True, "nbf = iat (permitted)"),
                  ("nbf", iat0 - 10000, True, "nbf = iat-10000 (permitted range: changed, still accepted)"), ("nbf", "ABSENT", False, "nbf missing"),
                  ("nbf", str(nbf0), False, "nbf a string"), ("nbf", float(nbf0) + 0.5, False, "nbf a fraction")]
    for n, v, permitted, desc in TIME_CASES:
        c2 = dict(cl)
        if v == "ABSENT":
            c2.pop(n)
        else:
            c2[n] = v
        ov, st, rows = evaluate(derived(bdir, c2), pol)
        nm = [r[0] for r in rows if r[1] == "NOT-MET"]
        named = [r for r in nm if any(a in r.lower() for a in [n.lower()] + ALIAS.get(n, []) + ["attempt window", "expired before"] if n in ("iat", "exp"))
                 or any(a in r.lower() for a in [n.lower()] + ALIAS.get(n, []))]
        if permitted:
            good = "NOT BOUND" not in ov and st == st0
            res.append(("E3t", "%s: %s" % (lab, desc), "accepted, every row status identical to the baseline", "%s; rows identical: %s" % (ov, st == st0), "MET" if good else "NOT-MET"))
        else:
            good = "NOT BOUND" in ov and bool(named)
            res.append(("E3t", "%s: %s" % (lab, desc), "NOT BOUND with a NOT-MET row on that claim", "%s; NOT-MET rows naming it: %s (all: %d)" % (ov, named[:2], len(nm)), "MET" if good else "NOT-MET"))
    # E3c P and S one at a time and together
    ps_present = [n for n in P + S if n in cl]
    for n in ps_present:
        c2 = dict(cl)
        c2[n] = mutate(n, cl[n])
        ov, st, _ = evaluate(derived(bdir, c2), pol)
        same = ov == ov0 and st == st0
        res.append(("E3c", "%s: %s (%s)" % (lab, n, klass(n)), "verdict and every row status identical to the baseline", "%s; rows identical: %s" % (ov, st == st0), "MET" if same else "NOT-MET"))
    for n in [x for x in P + S if x not in cl]:
        res.append(("E3c", "%s: %s (%s)" % (lab, n, klass(n)), "-", "claim absent from the real token of this run; not varied", "NOT-READ"))
    c3 = dict(cl)
    for n in ps_present:
        c3[n] = mutate(n, cl[n])
    ov, st, _ = evaluate(derived(bdir, c3), pol)
    res.append(("E3c", "%s: ALL %d P/S claims together" % (lab, len(ps_present)), "verdict and every row status identical to the baseline", "%s; rows identical: %s" % (ov, st == st0),
                "MET" if (ov == ov0 and st == st0) else "NOT-MET"))
    # informational: the unclassified claims (behaviour only, never MET)
    for n in [x for x in cl if klass(x) == "UNCLASSIFIED"]:
        c2 = dict(cl)
        c2[n] = mutate(n, cl[n])
        ov, st, _ = evaluate(derived(bdir, c2), pol)
        res.append(("E3-unclassified", "%s: %s" % (lab, n), "(the contract does not classify it)", "verdict %s; rows identical to baseline: %s" % (ov, st == st0), "NOT-READ (specification gap)"))
    say()

# ---------------------------------------------------------------- E4 observation A vs B
say("## E4 which P/S claim VALUES differ between the real tokens of A and B (observation; K also differs, so NOT an isolated invariance proof)")
a, b = allnames["A"], allnames["B"]
for n in P + S:
    if n in a and n in b:
        same = a[n] == b[n]
        val = "" if same or n in HIDE else "  A=%r B=%r" % (a[n], b[n])
        say("%-24s %-3s %s%s" % (n, klass(n), "same" if same else "DIFFERS", val))
        res.append(("E4", n, "(observation)", "same" if same else "differs between A and B; each token still bound by its own policy (R3b)", "RECORDED"))
say()

# ---------------------------------------------------------------- summary
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
with open(os.path.join(OUT, "results-table.txt"), "w") as f:
    for r in res:
        f.write("%-16s %-44s %-12s | %s\n" % (r[0], r[1], r[4], r[3]))
cnt = {}
for r in res:
    k = (r[0], r[4].split(" ")[0])
    cnt[k] = cnt.get(k, 0) + 1
say("## counts")
for k in sorted(cnt):
    say("%-16s %-10s %d" % (k[0], k[1], cnt[k]))
open(os.path.join(OUT, "run-log.txt"), "w").write("\n".join(out) + "\n")
shutil.rmtree(tmp, ignore_errors=True)
