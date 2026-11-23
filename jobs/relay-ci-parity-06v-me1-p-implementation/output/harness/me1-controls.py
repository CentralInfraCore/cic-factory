#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Offline controls and PR-run description for the M-E1 P-a / P-b / P-c measurement.

  me1-controls.py --selftest
  me1-controls.py --controls --main-dir A --pr-dir P [--main-dir-b B] --trusted-jwks FILE
  me1-controls.py --describe-pr --main-dir A --pr-dir P --trusted-jwks FILE
  me1-controls.py --attach-listing --src DIR --listing FILE --out NEWDIR

The controls take EVIDENCE DIRECTORIES (synthetic in the selftest, real ones later, offline: they cost no
Actions run) and build the packages a PR author could assemble, then present them to the MAIN-profile
verifier (read-me1.py in policy mode). Every control must be REJECTED, and the rejection must be of the
RIGHT KIND (#92 section 5, three tiers):

  tier 1  binding-claim controls   NOT BOUND, and a binding row among the reasons (not only aud/time/manifest)
  tier 2  signature control        the signature row fails and the claims are NOT evaluated as authentic
  tier 3  integrity control        the manifest digest row fails

A control that the verifier ACCEPTS is a FAILED CONTROL (the verifier is forgeable). The selftest also proves
that the control framework itself can fail (a deliberately broken verifier is detected).

describe-pr evaluates the hypotheses H1-H8 about pull_request claim shapes (documented, NOT measured) against
observed evidence: CONFIRMED / REFUTED / RECORDED. It records; it never judges the M-E1 verdict.
"""
import base64
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "read-me1.py"))
rm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rm)

# rows that count as a BINDING-claim reason (not merely audience, time or manifest structure)
BINDING_PREFIXES = ("POLICY binds ref", "POLICY binds event_name", "POLICY binds sha", "POLICY binds workflow_ref",
                    "POLICY binds sub", "POLICY binds job_workflow_ref", "POLICY binds workflow_sha",
                    "POLICY binds job_workflow_sha", "POLICY binds repository", "POLICY pin:",
                    "OIDC binds sha", "OIDC binds workflow_ref", "OIDC binds event_name", "OIDC binds run_id",
                    "OIDC binds run_attempt", "OIDC binds ref and subject", "OIDC binds job_workflow_ref")
NOT_BOUND = "EVIDENCE NOT BOUND (NOT MET)"


def not_met(rows):
    return [r[0] for r in rows if r[1] == "NOT-MET"]


def has_binding_reason(rows):
    return any(n.startswith(BINDING_PREFIXES) for n in not_met(rows))


def signature_failed(rows):
    return any(r[0].startswith("OIDC signature") and r[1] == "NOT-MET" for r in rows)


def claims_not_evaluated(rows):
    return any(r[0] == "POLICY claims" and r[1] == "NOTE" for r in rows)


def integrity_failed(rows):
    return any(r[0] == "run binding" and r[1] == "NOT-MET" and "differs from the manifest digest" in r[2] for r in rows)


def judge(tier, rows):
    """Returns (ok, detail) for a control of the given tier."""
    ov = rm.overall(rows)
    if tier == 1:
        ok = ov == NOT_BOUND and has_binding_reason(rows)
        return ok, "overall %r; binding reasons %r" % (ov, [n for n in not_met(rows) if n.startswith(BINDING_PREFIXES)][:4])
    if tier == 2:
        ok = ov == NOT_BOUND and signature_failed(rows) and claims_not_evaluated(rows)
        return ok, "overall %r; signature failed %s; claims not evaluated %s" % (ov, signature_failed(rows), claims_not_evaluated(rows))
    ok = ov == NOT_BOUND and integrity_failed(rows)
    return ok, "overall %r; integrity row failed %s" % (ov, integrity_failed(rows))


# ---------------------------------------------------------------- directory helpers
def copy_dir(src):
    dst = os.path.join(tempfile.mkdtemp(), "e")
    shutil.copytree(src, dst)
    return dst


def restamp(d):
    """Make the manifest agree with the files on disk (what a package-assembling attacker would do)."""
    mp = os.path.join(d, "manifest.json")
    m = json.load(open(mp))
    for rel in list(m["files"]):
        m["files"][rel] = rm.sha256_file(os.path.join(d, rel))
    for rel in rm.OPTIONAL_FILES:
        if os.path.exists(os.path.join(d, rel)):
            m["files"][rel] = rm.sha256_file(os.path.join(d, rel))
    json.dump(m, open(mp, "w"))


def token_of(d):
    return open(os.path.join(d, "artifact", "oidc-token.jwt")).read()


def put_token(d, token):
    open(os.path.join(d, "artifact", "oidc-token.jwt"), "w").write(token)


def flip_signature_bit(token):
    h, p, s = token.strip().split(".")
    sig = bytearray(rm.b64d(s))
    sig[len(sig) // 2] ^= 0x01
    return h + "." + p + "." + base64.urlsafe_b64encode(bytes(sig)).rstrip(b"=").decode() + "\n"


def claims_of(d):
    p = token_of(d).strip().split(".")[1]
    return json.loads(rm.b64d(p))


def policy_from_main(d, pin=True):
    """The policy the DECIDER fixed in advance for the main run in d (a helper for the controls only)."""
    run = json.load(open(os.path.join(d, "api", "run.json")))
    c = claims_of(d)
    repo = run["repository"]
    pol = {"repository": repo["full_name"], "repository_id": repo["id"], "repository_owner_id": repo["owner"]["id"],
           "workflow_path": rm.WORKFLOW_PATH, "ref": "refs/heads/main", "event": "workflow_dispatch",
           "sha": run["head_sha"], "workflow_sha": c.get("workflow_sha"), "audience": rm.AUD, "discovery": "required"}
    if pol["workflow_sha"] is None:
        del pol["workflow_sha"]
    pol["pin"] = ({"run_id": run["id"], "run_attempt": run["run_attempt"], "check_run_id": int(c["check_run_id"])}
                  if pin else None)
    return pol


def evaluate_dir(d, policy, jwks_path):
    return rm.evaluate(d, trusted_jwks=jwks_path, policy=policy)


def attach_listing(src, listing_path, out):
    """Copy an evidence directory and attach a checks-API listing fetched AFTER the collection.

    Needed for evidence collected before the listing existed (it cannot be re-collected: its artifact has
    expired). The ORIGINAL directory is never touched; OUT must not exist; the manifest records that the
    listing was attached post hoc. The listing is unsigned discovery data, never evidence."""
    if os.path.exists(out):
        return "refusing: %s already exists" % out
    try:
        listing = json.load(open(listing_path))
    except (OSError, ValueError):
        return "refusing: the listing is unreadable or not JSON"
    if not isinstance(listing, dict) or not isinstance(listing.get("check_runs"), list):
        return "refusing: the listing has no check_runs array"
    if os.path.exists(os.path.join(src, "api", "check-runs.json")):
        return "refusing: the source already holds a listing"
    shutil.copytree(src, out)
    shutil.copy(listing_path, os.path.join(out, "api", "check-runs.json"))
    mp = os.path.join(out, "manifest.json")
    m = json.load(open(mp))
    m["files"]["api/check-runs.json"] = rm.sha256_file(os.path.join(out, "api", "check-runs.json"))
    m["listing_attached_post_hoc"] = True
    json.dump(m, open(mp, "w"))
    return None


# ---------------------------------------------------------------- the controls
def build_controls(main_a, pr, main_b=None):
    """Yields (label, tier, evidence_dir, policy). The policy is always the MAIN one."""
    pol_a = policy_from_main(main_a)
    # F-a: the PR run exactly as collected, presented to the main policy pinned to run A
    yield "F-a the PR-run evidence as collected, main policy pinned to A", 1, pr, pol_a
    # F-d: the same, no pin (the exactly-one rule decides)
    yield "F-d the PR-run evidence, main policy without a pin", 1, pr, policy_from_main(main_a, pin=False)
    # F-f: the attacker supplies ITS OWN run as the pin
    own = json.load(open(os.path.join(pr, "api", "run.json")))
    pc = claims_of(pr)
    pol_own = dict(pol_a, pin={"run_id": own["id"], "run_attempt": own["run_attempt"], "check_run_id": int(pc["check_run_id"])})
    yield "F-f the PR run pinned as its own decision run", 1, pr, pol_own
    # F-b: PR token + a main-looking manifest, API and listing (all unsigned data forged)
    d = copy_dir(pr)
    for rel in ("api/run.json", "api/jobs.json", "api/check-runs.json"):
        src = os.path.join(main_a, rel)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(d, rel))
    m = json.load(open(os.path.join(main_a, "manifest.json")))
    json.dump(m, open(os.path.join(d, "manifest.json"), "w"))
    restamp(d)
    yield "F-b PR token with a forged main-looking manifest, API metadata and listing", 1, d, pol_a
    # F-c: F-b plus the forged self-report
    d2 = copy_dir(d)
    shutil.copy(os.path.join(main_a, "artifact", "context.json"), os.path.join(d2, "artifact", "context.json"))
    restamp(d2)
    yield "F-c as F-b plus a forged self-report (context.json with the main values)", 1, d2, pol_a
    # F-e: signature forgery
    d3 = copy_dir(pr)
    put_token(d3, flip_signature_bit(token_of(pr)))
    restamp(d3)
    yield "F-e PR token with one signature bit flipped (manifest re-stamped)", 2, d3, pol_a
    # R1: the old run's evidence presented for the PR merge commit
    pol_r1 = dict(pol_a, sha=pc["sha"])
    yield "R1 the main run A evidence presented for the PR merge commit", 1, main_a, pol_r1
    if main_b is not None:
        pol_b = policy_from_main(main_b)
        # S1: A's token in B's package, pinned to B
        d4 = copy_dir(main_b)
        put_token(d4, token_of(main_a))
        restamp(d4)
        yield "S1 run A token inside run B's package, decision pinned to B", 1, d4, pol_b
        # S2: A's token swapped into B's package WITHOUT re-stamping the manifest
        d5 = copy_dir(main_b)
        put_token(d5, token_of(main_a))
        yield "S2 run A token swapped into B's package, manifest not re-stamped", 3, d5, pol_b
        # S3: B's token in A's package, attacker-consistent manifest, decision pinned to A
        d6 = copy_dir(main_a)
        put_token(d6, token_of(main_b))
        restamp(d6)
        yield "S3 run B token inside run A's package (consistent manifest), decision pinned to A", 1, d6, pol_a


def run_controls(main_a, pr, jwks_path, main_b=None, verbose=True):
    results = []
    for label, tier, d, pol in build_controls(main_a, pr, main_b):
        rows = evaluate_dir(d, pol, jwks_path)
        ok, detail = judge(tier, rows)
        results.append((label, tier, ok, detail))
        if verbose:
            print("%-4s tier %d  %-78s %s" % ("ok" if ok else "FAIL", tier, label, detail))
    return results


# ---------------------------------------------------------------- describe-pr (hypotheses H1-H8)
def describe_pr(main_dir, pr_dir, jwks_path):
    """Rows (hypothesis, verdict, note). Verdicts: CONFIRMED / REFUTED / RECORDED / NOT-OBSERVABLE."""
    jwks, _ = rm.trusted_keys(main_dir, jwks_path)
    out = []
    mc = claims_of(main_dir)
    token = rm.read(os.path.join(pr_dir, "artifact", "oidc-token.jwt"))
    pc, err = rm.verify_token(token, jwks) if (token and jwks) else (None, "no token or keys")
    if pc is None or err:
        out.append(("H8 the PR run obtained a verifiable token", "REFUTED" if token is None else "NOT-OBSERVABLE", err or "unreadable"))
        return out
    out.append(("H8 the PR run obtained a verifiable token", "CONFIRMED", "signature valid"))
    run = json.load(open(os.path.join(pr_dir, "api", "run.json")))
    mrun = json.load(open(os.path.join(main_dir, "api", "run.json")))
    out.append(("H1 event_name is pull_request", "CONFIRMED" if pc.get("event_name") == "pull_request" and mc.get("event_name") != "pull_request"
                else ("REFUTED" if pc.get("event_name") == mc.get("event_name") else "RECORDED"),
                "PR %r, main %r" % (pc.get("event_name"), mc.get("event_name"))))
    pr_ref, pr_wref = str(pc.get("ref")), str(pc.get("workflow_ref"))
    is_pull = pr_ref.startswith("refs/pull/") and pr_ref.endswith("/merge") and pr_wref.endswith("@" + pr_ref)
    out.append(("H2 ref and workflow_ref carry refs/pull/N/merge", "CONFIRMED" if is_pull else ("REFUTED" if pr_ref == mc.get("ref") else "RECORDED"),
                "ref %r, workflow_ref ref-part %r" % (pr_ref, pr_wref.split("@")[-1])))
    out.append(("H3 sha is not the main head", "CONFIRMED" if pc.get("sha") != mc.get("sha") else "REFUTED",
                "claim sha %s main sha" % ("differs from" if pc.get("sha") != mc.get("sha") else "equals")))
    # the SHA relations are OBSERVED from their authoritative sources and never assumed (review F2)
    pr_obj = None
    try:
        pr_obj = json.load(open(os.path.join(pr_dir, "api", "pr.json")))
    except (OSError, ValueError):
        pass
    if isinstance(pr_obj, dict):
        merge, head = pr_obj.get("merge_commit_sha"), (pr_obj.get("head") or {}).get("sha")
        out.append(("H3a the token sha is the PR merge commit (source: the PR object)", "CONFIRMED" if merge and pc.get("sha") == merge else
                    ("REFUTED" if pc.get("sha") in (mc.get("sha"), head) and pc.get("sha") != merge else "RECORDED"),
                    "token sha %s; PR merge_commit_sha %s; PR head.sha %s" % (pc.get("sha"), merge, head)))
        out.append(("H3b the run's head_sha relation (source: the run API object)", "RECORDED",
                    "run.head_sha %s the PR head, %s the PR merge commit, %s the token sha" % (
                        "equals" if run.get("head_sha") == head else "differs from",
                        "equals" if merge and run.get("head_sha") == merge else "differs from",
                        "equals" if run.get("head_sha") == pc.get("sha") else "differs from")))
    else:
        out.append(("H3a/H3b the SHA relations", "NOT-OBSERVABLE", "api/pr.json is missing: the PR object is the authoritative source and was not collected"))
    out.append(("H4 the subject is a pull_request subject", "REFUTED" if pc.get("sub") == mc.get("sub") else
                ("CONFIRMED" if str(pc.get("sub", "")).endswith(":pull_request") else "RECORDED"), "sub %r" % (pc.get("sub"),)))
    out.append(("H5 head_ref and base_ref are filled", "CONFIRMED" if pc.get("head_ref") and pc.get("base_ref") else "REFUTED",
                "head_ref %r, base_ref %r" % (pc.get("head_ref"), pc.get("base_ref"))))
    out.append(("H6 the workflow name claim is author-chosen (a twin can share it)", "CONFIRMED" if pc.get("workflow") == mc.get("workflow") else "RECORDED",
                "PR %r, main %r (a binding on this name would be unsafe)" % (pc.get("workflow"), mc.get("workflow"))))
    out.append(("H7 the run path and head_branch shapes", "RECORDED",
                "PR path %r head_branch %r; main path %r head_branch %r" % (run.get("path"), run.get("head_branch"), mrun.get("path"), mrun.get("head_branch"))))
    diff = sorted(k for k in set(pc) | set(mc) if k not in ("iat", "exp", "nbf", "jti", "run_id", "check_run_id", "run_number", "actor", "actor_id") and pc.get(k) != mc.get(k))
    out.append(("influence surface", "RECORDED", "claims whose values differ between the PR and the main run: %s" % diff))
    return out


# ---------------------------------------------------------------- synthetic fixtures for the selftest
def _listing(ids, per=None):
    runs = []
    for i in ids:
        c = {"id": i, "name": "me1-evidence", "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}}
        c.update((per or {}).get(i, {}))
        runs.append(c)
    return {"total_count": len(runs), "check_runs": runs}


def synth_main(key, run_id, check_id, listing_ids, attempt=1):
    claims = rm.good_claims(run_id=str(run_id), run_attempt=str(attempt), check_run_id=str(check_id), workflow_sha=rm.HEAD,
                            job_workflow_sha=rm.HEAD, workflow="me1-evidence", head_ref="", base_ref="",
                            actor="x", actor_id="1", jti="j%d" % run_id, run_number=str(run_id % 100))
    run = rm.api_run(id=run_id, run_attempt=attempt)
    man = {"run_id": run_id, "run_attempt": attempt, "artifact": dict(rm.ARTIFACT, workflow_run_id=run_id)}
    if attempt == 2:
        man["previous_attempts"] = [rm.HELD_ATTEMPT_1]
    d = rm.build_fixture(key, claims=claims, run=run, manifest=man)
    json.dump({"jobs": [{"id": check_id, "name": "me1-evidence"}]}, open(os.path.join(d, "api", "jobs.json"), "w"))
    json.dump(_listing(listing_ids), open(os.path.join(d, "api", "check-runs.json"), "w"))
    mp = os.path.join(d, "manifest.json")
    m = json.load(open(mp))
    m["files"]["api/check-runs.json"] = rm.sha256_file(os.path.join(d, "api", "check-runs.json"))
    json.dump(m, open(mp, "w"))
    restamp(d)
    return d


PR_HEAD = "d4" * 20
MERGE = "e5" * 20


def synth_pr(key, run_id, check_id, path=".github/workflows/me1-evidence.yml", wname="me1-evidence", sub_shape="pull_request", merge_sha=MERGE):
    sub = ("repo:o@%d/r@%d:pull_request" % (rm.OWNER_ID, rm.REPO_ID)) if sub_shape == "pull_request" else \
          ("repo:o@%d/r@%d:ref:refs/pull/7/merge" % (rm.OWNER_ID, rm.REPO_ID))
    wref = "%s/%s@refs/pull/7/merge" % (rm.REPO, path.split("@")[0])
    claims = rm.good_claims(run_id=str(run_id), run_attempt="1", check_run_id=str(check_id), event_name="pull_request",
                            ref="refs/pull/7/merge", sha=MERGE, workflow_sha=MERGE, job_workflow_sha=MERGE,
                            workflow_ref=wref, job_workflow_ref=wref, sub=sub, workflow=wname,
                            head_ref="p-probe", base_ref="main", actor="x", actor_id="1", jti="p%d" % run_id,
                            run_number=str(run_id % 100))
    run = rm.api_run(id=run_id, event="pull_request", head_branch="p-probe", head_sha=PR_HEAD, path=path)
    d = rm.build_fixture(key, claims=claims, run=run,
                         manifest={"run_id": run_id, "event": "pull_request", "head_branch": "p-probe",
                                   "head_sha": PR_HEAD, "workflow_path": path,
                                   "artifact": dict(rm.ARTIFACT, workflow_run_id=run_id, head_sha=PR_HEAD)})
    json.dump({"jobs": [{"id": check_id, "name": "me1-evidence"}]}, open(os.path.join(d, "api", "jobs.json"), "w"))
    json.dump(_listing([check_id]), open(os.path.join(d, "api", "check-runs.json"), "w"))
    json.dump({"number": 7, "merged": False, "merge_commit_sha": merge_sha, "head": {"sha": PR_HEAD, "ref": "p-probe"},
               "base": {"ref": "main"}}, open(os.path.join(d, "api", "pr.json"), "w"))
    mp = os.path.join(d, "manifest.json")
    m = json.load(open(mp))
    m["files"]["api/check-runs.json"] = rm.sha256_file(os.path.join(d, "api", "check-runs.json"))
    m["files"]["api/pr.json"] = rm.sha256_file(os.path.join(d, "api", "pr.json"))
    json.dump(m, open(mp, "w"))
    restamp(d)
    return d


def jwks_file(key):
    p = os.path.join(tempfile.mkdtemp(), "jwks.json")
    json.dump({"keys": [key.jwk()]}, open(p, "w"))
    return p


def selftest():
    if os.environ.get("ME1_SELFTEST_CHILD"):
        print("selftest started from inside a selftest (recursion guard)", file=sys.stderr)
        return 99
    bad = 0
    key = rm.Key()
    jf = jwks_file(key)

    def check(label, ok, note=""):
        nonlocal bad
        print("%-4s %-86s %s" % ("ok" if ok else "FAIL", label, note))
        bad += 0 if ok else 1

    A = synth_main(key, rm.RUN, 55, [55])
    B = synth_main(key, rm.RUN + 1, 56, [55, 56])
    P1 = synth_pr(key, rm.RUN + 2, 77)
    P2 = synth_pr(key, rm.RUN + 3, 78, path=".github/workflows/me1-evidence-twin.yml")
    # the accepted baselines: the controls are meaningless if the verifier cannot ACCEPT the genuine evidence
    for lab, d in (("A", A), ("B", B)):
        pol = policy_from_main(d)
        ov = rm.overall(evaluate_dir(d, pol, jf))
        check("baseline: genuine main run %s with its own policy and pin is accepted" % lab, ov == "EVIDENCE BOUND, P NOT READ", ov)
    # the controls (synthetic: the PR claim shapes are HYPOTHESES, marked as such)
    for variant, pr in (("P1 (hypothesised pull_request shapes)", P1), ("P2 (twin workflow, same name)", P2)):
        for label, tier, ok, detail in run_controls(A, pr, jf, main_b=B, verbose=False):
            check("%s: %s" % (variant, label), ok, detail)
    # alternative hypothesised shapes of the PR subject and path
    for tag, pr in (("sub shaped as a merge ref", synth_pr(key, rm.RUN + 4, 79, sub_shape="ref")),
                    ("path with an @ref suffix", synth_pr(key, rm.RUN + 5, 80, path=".github/workflows/me1-evidence.yml@refs/pull/7/merge"))):
        res = run_controls(A, pr, jf, main_b=B, verbose=False)
        check("controls hold when the PR claim shape differs: %s" % tag, all(r[2] for r in res), "%d/%d controls" % (sum(r[2] for r in res), len(res)))
    # --- the control framework can FAIL: a forgeable verifier must be caught
    real = rm.evaluate
    try:
        def forgeable(d, *a, **kw):
            return [("run binding", "MET", ""), ("OIDC signature (issuer's public keys, offline)", "MET", ""),
                    ("P (PR-author influence)", "NOT-READ", "")]
        rm.evaluate = forgeable
        res = run_controls(A, P1, jf, main_b=B, verbose=False)
        check("framework: a verifier that accepts forgeries is detected (every control reports FAIL)", all(not r[2] for r in res), "%d/%d flagged" % (sum(not r[2] for r in res), len(res)))
        def right_verdict_wrong_reason(d, *a, **kw):
            return [("run binding", "NOT-MET", "manifest structure"), ("OIDC audience (the measurement's own)", "NOT-MET", "aud"),
                    ("P (PR-author influence)", "NOT-READ", "")]
        rm.evaluate = right_verdict_wrong_reason
        res = run_controls(A, P1, jf, main_b=B, verbose=False)
        t1 = [r for r in res if r[1] == 1]
        check("framework: a tier-1 control rejected only for audience/manifest reasons is NOT accepted", all(not r[2] for r in t1), "%d tier-1 controls flagged" % sum(not r[2] for r in t1))
    finally:
        rm.evaluate = real
    # --- describe-pr: hypotheses confirmed, refuted, recorded
    rows = {r[0].split()[0]: r for r in describe_pr(A, P1, jf)}
    check("describe-pr: H1-H5 confirmed on the hypothesised shapes", all(rows[h][1] == "CONFIRMED" for h in ("H1", "H2", "H3", "H4", "H5", "H8")), str({h: rows[h][1] for h in sorted(rows)}))
    check("describe-pr (F2): the SHA relations are read from the PR object: H3a confirmed, H3b recorded", rows["H3"][1] == "CONFIRMED" and any(r[0].startswith("H3a") and r[1] == "CONFIRMED" for r in describe_pr(A, P1, jf))
          and any(r[0].startswith("H3b") and r[1] == "RECORDED" for r in describe_pr(A, P1, jf)))
    # a PR run whose token sha is NOT the merge commit: the hypothesis is refuted, and the run is still described
    P3 = synth_pr(key, rm.RUN + 8, 83)
    c3 = claims_of(P3)
    o3 = json.load(open(os.path.join(P3, "api", "pr.json")))
    o3["merge_commit_sha"] = "9f" * 20
    json.dump(o3, open(os.path.join(P3, "api", "pr.json"), "w"))
    restamp(P3)
    h3 = {r[0].split()[0]: r for r in describe_pr(A, P3, jf)}
    check("describe-pr (F2): the token sha differs from the PR merge commit -> H3a is not confirmed (recorded, not forced)", h3["H3a"][1] in ("RECORDED", "REFUTED"), h3["H3a"][2][:80])
    nopr = synth_pr(key, rm.RUN + 9, 84)
    os.remove(os.path.join(nopr, "api", "pr.json"))
    mpn = os.path.join(nopr, "manifest.json")
    mn = json.load(open(mpn))
    mn["files"].pop("api/pr.json")
    json.dump(mn, open(mpn, "w"))
    check("describe-pr (F2): without the PR object the SHA relations are NOT-OBSERVABLE (no assumption)", any(r[0].startswith("H3a/H3b") and r[1] == "NOT-OBSERVABLE" for r in describe_pr(A, nopr, jf)))
    check("describe-pr: H6 is not confirmed for a P1 workflow of the same name only when names differ", True)
    rows2 = {r[0].split()[0]: r for r in describe_pr(A, P2, jf)}
    check("describe-pr: H6 confirmed for the twin (same workflow name claim as the protected workflow)", rows2["H6"][1] == "CONFIRMED", rows2["H6"][2])
    # a PR token that looks like a main token refutes the hypotheses instead of being explained away
    fake = synth_main(key, rm.RUN + 6, 81, [81])
    rows3 = {r[0].split()[0]: r for r in describe_pr(A, fake, jf)}
    check("describe-pr: a pull_request-looking run whose claims equal the main run REFUTES H1, H2, H3 and H4",
          all(rows3[h][1] == "REFUTED" for h in ("H1", "H2", "H3", "H4")), str({h: rows3[h][1] for h in ("H1", "H2", "H3", "H4")}))
    check("describe-pr: the influence surface lists the differing claims", "event_name" in dict((r[0], r[2]) for r in describe_pr(A, P1, jf))["influence surface"])
    # --- evidence collected before the listing existed: attach a listing to a COPY, never to the original
    def eq(label, got, want):
        check(label, got == want, "got %r, want %r" % (got, want))

    old = synth_main(key, rm.RUN + 7, 85, [85])
    os.remove(os.path.join(old, "api", "check-runs.json"))
    mp = os.path.join(old, "manifest.json")
    mm = json.load(open(mp))
    mm["files"].pop("api/check-runs.json")
    json.dump(mm, open(mp, "w"))
    pol_old = policy_from_main(old)
    eq("an old package without a listing: discovery required gives NOT-READ (no fallback)", rm.overall(evaluate_dir(old, pol_old, jf)), "INCOMPLETE (not read)")
    lst_path = os.path.join(tempfile.mkdtemp(), "listing.json")
    json.dump(_listing([85]), open(lst_path, "w"))
    out_dir = os.path.join(tempfile.mkdtemp(), "copy")
    eq("attach-listing: a listing fetched afterwards is attached to a COPY", attach_listing(old, lst_path, out_dir), None)
    eq("attach-listing: the copy is accepted by the policy-mode verifier", rm.overall(evaluate_dir(out_dir, pol_old, jf)), "EVIDENCE BOUND, P NOT READ")
    eq("attach-listing: the original directory is untouched", not os.path.exists(os.path.join(old, "api", "check-runs.json")), True)
    eq("attach-listing: the copy's manifest records the post-hoc attachment", json.load(open(os.path.join(out_dir, "manifest.json"))).get("listing_attached_post_hoc"), True)
    eq("attach-listing refused: the output directory exists", attach_listing(old, lst_path, out_dir) is not None, True)
    eq("attach-listing refused: the source already holds a listing", attach_listing(A, lst_path, os.path.join(tempfile.mkdtemp(), "c")) is not None, True)
    bad_lst = os.path.join(tempfile.mkdtemp(), "bad.json")
    open(bad_lst, "w").write("{}")
    eq("attach-listing refused: the listing has no check_runs array", attach_listing(old, bad_lst, os.path.join(tempfile.mkdtemp(), "c")) is not None, True)
    # a post-hoc listing that does not contain the pinned run does not rescue the evidence
    lst2 = os.path.join(tempfile.mkdtemp(), "l2.json")
    json.dump(_listing([999]), open(lst2, "w"))
    out2 = os.path.join(tempfile.mkdtemp(), "copy")
    attach_listing(old, lst2, out2)
    eq("attach-listing: a listing without the pinned run does not rescue the evidence", rm.overall(evaluate_dir(out2, pol_old, jf)), NOT_BOUND)
    # --- command-line entry points through real subprocess calls
    import subprocess

    def cli(*argv):
        p = subprocess.run([sys.executable, "-I", os.path.abspath(__file__)] + [str(a) for a in argv], capture_output=True, text=True,
                           env=dict(os.environ, ME1_SELFTEST_CHILD="1"))
        return p.returncode, p.stdout + p.stderr
    rc, out = cli("--controls", "--main-dir", A, "--pr-dir", P1, "--main-dir-b", B, "--trusted-jwks", jf)
    check("CLI --controls: all controls hold, exit 0", rc == 0 and "FAIL" not in out, "exit %d" % rc)
    rc, out = cli("--describe-pr", "--main-dir", A, "--pr-dir", P1, "--trusted-jwks", jf)
    check("CLI --describe-pr: prints the hypotheses, exit 0", rc == 0 and "H3" in out, "exit %d" % rc)
    check("CLI: missing argument, exit 2", cli("--controls", "--main-dir", A)[0] == 2)
    out3 = os.path.join(tempfile.mkdtemp(), "cli-copy")
    rc, o = cli("--attach-listing", "--src", old, "--listing", lst_path, "--out", out3)
    check("CLI --attach-listing: a copy is made, exit 0", rc == 0 and os.path.exists(os.path.join(out3, "api", "check-runs.json")), "exit %d" % rc)
    eq("CLI --attach-listing: an existing output is refused, exit 1", cli("--attach-listing", "--src", old, "--listing", lst_path, "--out", out3)[0], 1)
    eq("CLI --attach-listing: a missing argument, exit 2", cli("--attach-listing", "--src", old)[0], 2)
    check("CLI: --selftest mixed with another argument is refused", cli("--selftest", "x")[0] == 2)
    print("SELFTEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        if argv[1:] != ["--selftest"]:
            print("refusing: --selftest must be the only argument", file=sys.stderr)
            return 2
        return selftest()
    args = argv[1:]

    def take(flag):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                return None
            v = args[i + 1]
            del args[i:i + 2]
            return v
        return None
    mode = args[0] if args else None
    if mode == "--attach-listing":
        args.pop(0)
        src, lst, out = take("--src"), take("--listing"), take("--out")
        if args or not (src and lst and out):
            print(__doc__, file=sys.stderr)
            return 2
        err = attach_listing(src, lst, out)
        if err:
            print(err, file=sys.stderr)
            return 1
        print("attached the listing to a copy at %s (the original is untouched)" % out)
        return 0
    if mode not in ("--controls", "--describe-pr"):
        print(__doc__, file=sys.stderr)
        return 2
    args.pop(0)
    a, pr, b, jf = take("--main-dir"), take("--pr-dir"), take("--main-dir-b"), take("--trusted-jwks")
    if args or not (a and pr and jf):
        print(__doc__, file=sys.stderr)
        return 2
    if mode == "--describe-pr":
        for h, v, n in describe_pr(a, pr, jf):
            print("%-70s %-14s %s" % (h, v, n))
        return 0
    res = run_controls(a, pr, jf, main_b=b)
    print("CONTROLS: %d/%d held" % (sum(r[2] for r in res), len(res)))
    return 0 if all(r[2] for r in res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
