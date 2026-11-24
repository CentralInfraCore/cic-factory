#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""P-c/V test matrix (#93 V1-V5) for the policy-mode verifier, on SYNTHETIC evidence only.

  python3 -I test-pcv.py --selftest      the matrix
  python3 -I test-pcv.py --mutations     the matrix must FAIL on every planted verifier defect

The decision policy is fixed in advance; the checks API only discovers and cross-checks; there is no
"latest run" rule. Nothing here touches GitHub or the lab.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location("mc", os.path.join(HERE, "me1-controls.py"))
mc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(mc)
rm = mc.rm

BOUND = "EVIDENCE BOUND, P NOT READ"
NOT = "EVIDENCE NOT BOUND (NOT MET)"
INC = "INCOMPLETE (not read)"


def selftest():
    if os.environ.get("ME1_SELFTEST_CHILD"):
        print("selftest started from inside a selftest (recursion guard)", file=sys.stderr)
        return 99
    bad = 0
    key = rm.Key()
    jf = mc.jwks_file(key)

    def check(label, got, want):
        nonlocal bad
        ok = got == want
        print("%-4s %-92s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1

    def A(listing=(55,), **kw):
        return mc.synth_main(key, rm.RUN, 55, list(listing))

    def B(listing=(55, 56)):
        return mc.synth_main(key, rm.RUN + 1, 56, list(listing))

    def ev(d, pol):
        return rm.overall(mc.evaluate_dir(d, pol, jf))

    def rows(d, pol):
        return mc.evaluate_dir(d, pol, jf)

    def policy_file(obj, raw=None):
        p = os.path.join(tempfile.mkdtemp(), "policy.json")
        open(p, "w").write(raw if raw is not None else json.dumps(obj))
        return p
    def cli(*argv):
        p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "read-me1.py")] + [str(a) for a in argv], capture_output=True, text=True,
                           env=dict(os.environ, ME1_SELFTEST_CHILD="1"))
        return p.returncode, p.stdout + p.stderr
    pinA = mc.policy_from_main
    # ---------------------------------------------------------------- V2: selection
    a2, b2 = A((55, 56)), B((55, 56))
    check("V2 pin A, listing [A,B] (B is the newer run): the A evidence is accepted", ev(a2, pinA(a2)), BOUND)
    check("V2 ... the 'additional candidate runs' alert is raised, the verifier does not switch",
          [r[1] for r in rows(a2, pinA(a2)) if r[0] == "POLICY discovery: additional candidate runs"], ["NOTE"])
    check("V2 pin B: the B evidence is accepted although A is older", ev(b2, pinA(b2)), BOUND)
    check("V2 pin A, the B evidence presented: rejected (pin and check_run_id)", ev(b2, pinA(a2)), NOT)
    check("V2 pin B, the A evidence presented: rejected", ev(a2, pinA(b2)), NOT)
    a3 = A((55, 56, 57))
    check("V2 a run C appears AFTER the pin: the pinned evidence stays accepted", ev(a3, pinA(a3)), BOUND)
    check("V2 ... and C is only an alert (extra candidates listed)", [r[2] for r in rows(a3, pinA(a3)) if r[0] == "POLICY discovery: additional candidate runs"][0].startswith("[56, 57]"), True)
    # the order of the listing and of the start times must not matter (no 'latest' rule)
    a4 = A((56, 55))
    check("V2 listing order swapped: pinned verdict unchanged", ev(a4, pinA(a4)), BOUND)
    p_nopin = pinA(a2, pin=False)
    check("V2 no pin, two candidates: the verifier does not choose (never the latest)", ev(a2, p_nopin), INC)
    check("V2 no pin, two candidates, the OTHER run's evidence: still does not choose", ev(b2, pinA(b2, pin=False)), INC)
    check("V2 no pin, two candidates, listing order swapped: still does not choose", ev(a4, pinA(a4, pin=False)), INC)
    a5 = A((55,))
    check("V2 no pin, exactly one candidate and it is this evidence's run: accepted", ev(a5, pinA(a5, pin=False)), BOUND)
    a6 = mc.synth_main(key, rm.RUN, 55, [56])
    check("V2 no pin, exactly one candidate but it is ANOTHER run: rejected", ev(a6, pinA(a6, pin=False)), NOT)
    a7 = mc.synth_main(key, rm.RUN, 55, [])
    check("V2 no pin, no candidate: rejected", ev(a7, pinA(a7, pin=False)), NOT)

    def drop_listing(d):
        os.remove(os.path.join(d, "api", "check-runs.json"))
        mp = os.path.join(d, "manifest.json")
        m = json.load(open(mp))
        m["files"].pop("api/check-runs.json")
        json.dump(m, open(mp, "w"))
    a8 = A((55,))
    drop_listing(a8)
    check("V2 discovery required, the listing is unavailable: incomplete, NO fallback to the pin", ev(a8, pinA(a8)), INC)
    # F1: there is NO optional discovery in the P-c/V profile: the policy that asks for it is refused at load,
    # so a missing listing can never yield EVIDENCE BOUND through the policy mode
    popt = policy_file_obj = None
    check("F1 a policy with discovery=optional is refused at load (no P-c/V profile without discovery)", rm.load_policy(policy_file(dict(pinA(a8), discovery="optional")))[0], None)
    check("F1 ... the error says discovery must be required", "must be required" in (rm.load_policy(policy_file(dict(pinA(a8), discovery="optional")))[1] or ""), True)
    check("F1 CLI: the optional policy is refused (exit 2), so the missing listing is never tolerated",
          cli(a8, "--trusted-jwks", jf, "--policy", policy_file(dict(pinA(a8), discovery="optional")))[0], 2)
    check("F1 discovery=required stated explicitly is accepted", rm.load_policy(policy_file(dict(pinA(a8), discovery="required")))[1], None)
    for label, per, want in (("the pinned check-run concluded failure", {"conclusion": "failure"}, NOT),
                             ("the pinned check-run is still in progress", {"status": "in_progress", "conclusion": None}, NOT),
                             ("the pinned check-run belongs to another app", {"app": {"slug": "evil-app"}}, NOT),
                             ("the pinned check-run has another name", {"name": "other"}, NOT)):
        d = A((55,))
        lst = mc._listing([55], {55: per})
        json.dump(lst, open(os.path.join(d, "api", "check-runs.json"), "w"))
        mc.restamp(d)
        check("V2 " + label, ev(d, pinA(d)), want)
    dt = A((55,))
    trunc = mc._listing([55])
    trunc["total_count"] = 150     # more check-runs exist than the single page holds
    json.dump(trunc, open(os.path.join(dt, "api", "check-runs.json"), "w"))
    mc.restamp(dt)
    check("V2 the listing is TRUNCATED (total_count above the page): discovery incomplete, never a silent single candidate", ev(dt, pinA(dt)), INC)
    check("V2 ... also without a pin", ev(dt, pinA(dt, pin=False)), INC)
    d = A((55,))
    pol = pinA(d)
    pol["pin"]["check_run_id"] = 99
    check("V2 the pinned check_run_id is not the Actions job id of the run (API cross-check): rejected", ev(d, pol), NOT)
    # isolated: the token's check_run_id and the pin AGREE (99), only the API job id (55) differs
    d99 = mc.synth_main(key, rm.RUN, 99, [99])
    jobs_p = os.path.join(d99, "api", "jobs.json")
    json.dump({"jobs": [{"id": 55, "name": "me1-evidence"}]}, open(jobs_p, "w"))
    mc.restamp(d99)
    check("V2 ISOLATED: token and pin agree on check_run_id, the Actions job id (API) differs: rejected", ev(d99, pinA(d99)), NOT)
    # isolated: the same check_run_id (55) everywhere, ONLY the run_id differs from the pin
    other_run = mc.synth_main(key, rm.RUN + 1, 55, [55])
    check("V2 ISOLATED: check_run_id agrees with the pin, only the run_id differs: rejected", ev(other_run, pinA(A((55,)))), NOT)
    # isolated: only the run_attempt differs (attempt 2 after a held attempt 1), same ids otherwise
    att2 = mc.synth_main(key, rm.RUN, 55, [55], attempt=2)
    check("V2 ISOLATED: only the run_attempt differs from the pin (attempt 2 against a pin on attempt 1): rejected", ev(att2, pinA(A((55,)))), NOT)
    check("V2 ... and the same attempt-2 evidence with a pin on attempt 2 is accepted", ev(att2, dict(pinA(A((55,))), pin={"run_id": rm.RUN, "run_attempt": 2, "check_run_id": 55})), BOUND)

    # ---------------------------------------------------------------- V3: claim classes
    def mutated(over=None, drop=()):
        c = rm.good_claims(run_id=str(rm.RUN), run_attempt="1", check_run_id="55", workflow_sha=rm.HEAD, job_workflow_sha=rm.HEAD,
                           workflow="me1-evidence", head_ref="", base_ref="", actor="x", actor_id="1", jti="j", run_number="1")
        c.update(over or {})
        for k in drop:
            c.pop(k, None)
        d = rm.build_fixture(key, claims=c)
        json.dump({"jobs": [{"id": 55, "name": "me1-evidence"}]}, open(os.path.join(d, "api", "jobs.json"), "w"))
        json.dump(mc._listing([55]), open(os.path.join(d, "api", "check-runs.json"), "w"))
        mp = os.path.join(d, "manifest.json")
        m = json.load(open(mp))
        m["files"]["api/check-runs.json"] = rm.sha256_file(os.path.join(d, "api", "check-runs.json"))
        json.dump(m, open(mp, "w"))
        mc.restamp(d)
        return d
    base = mutated()
    pol0 = pinA(base)
    check("V3 baseline: all claims as the policy expects", ev(base, pol0), BOUND)
    K_CHANGES = {"repository": "o/other", "repository_id": "1", "repository_owner_id": "2",
                 "workflow_ref": "o/r/.github/workflows/other.yml@refs/heads/main",
                 "job_workflow_ref": "o/r/.github/workflows/other.yml@refs/heads/main", "event_name": "push",
                 "ref": "refs/heads/dev", "sub": "repo:o/r:environment:x", "sha": "b2" * 20,
                 "workflow_sha": "b2" * 20, "job_workflow_sha": "b2" * 20, "run_id": "999", "run_attempt": "2",
                 "check_run_id": "56", "iss": "https://evil.example", "aud": "sts.amazonaws.com"}
    for name, val in K_CHANGES.items():
        check("V3 K claim changed: %s -> rejected" % name, ev(mutated({name: val}), pol0), NOT)
    PS_CHANGES = {"actor": "someone-else", "actor_id": "999", "ref_type": "tag", "ref_protected": "false",
                  "repository_visibility": "private", "runner_environment": "self-hosted", "run_number": "999",
                  "jti": "other", "workflow": "totally-different-name", "head_ref": "x", "base_ref": "y"}
    for name, val in PS_CHANGES.items():
        check("V3 P/S claim changed: %s -> verdict unchanged" % name, ev(mutated({name: val}), pol0), BOUND)
    check("V3 internally consistent token for another commit, the policy approves HEAD: rejected (the token alone is not enough)",
          ev(mutated({"sha": "b2" * 20, "workflow_sha": "b2" * 20, "job_workflow_sha": "b2" * 20}), pol0), NOT)
    check("V3 the policy requires another approved commit than the token carries: rejected", ev(base, dict(pol0, sha="c3" * 20)), NOT)
    check("V3 the policy gives another workflow_sha: rejected", ev(base, dict(pol0, workflow_sha="c3" * 20)), NOT)
    nowf = {k: v for k, v in pol0.items() if k != "workflow_sha"}
    check("V3 the policy gives no workflow_sha: not bound (its meaning per event type is not assumed), verdict stays", ev(base, nowf), BOUND)
    check("V3 ... and says so", [r[1] for r in rows(base, nowf) if r[0] == "POLICY workflow_sha"], ["NOTE"])
    check("V3 job_workflow_ref absent: not mandatory", ev(mutated(drop=("job_workflow_ref",)), pol0), BOUND)

    # ---------------------------------------------------------------- V3-time and the P class of repository_owner (06w contract amendment)
    # N1-N7: nbf/iat/exp as NumericDate, nbf <= iat + 60, iat < exp, skew <= 60 s, iat in the window, exp before the artifact, no current clock.
    IAT, S0, E0 = rm.IAT, rm.to_epoch(rm.START), rm.to_epoch(rm.END)
    ART = rm.to_epoch(rm.ART_CREATED)

    def stat(d, prefix, pol=None):
        return [r[1] for r in rows(d, pol or pol0) if r[0].startswith(prefix)]
    NB = "OIDC not-before (nbf)"
    WIN = "OIDC issued inside the attempt window"
    EXPR = "OIDC provably expired"
    check("V3t baseline: the nbf row is MET (real shape nbf = iat - 300)", stat(base, NB), ["MET"])
    for label, val, want in (("nbf = iat (accepted)", IAT, BOUND), ("nbf = iat + 60 (the boundary, accepted)", IAT + 60, BOUND),
                             ("nbf = iat + 61 (one second over, rejected)", IAT + 61, NOT), ("nbf = iat + 1000000 (rejected)", IAT + 1000000, NOT),
                             ("nbf = iat - 10000 (no lower bound, accepted)", IAT - 10000, BOUND), ("nbf = 0 (no lower bound, accepted)", 0, BOUND),
                             ("nbf = -1 (not a valid NumericDate here)", -1, NOT), ("nbf is a string", str(IAT), NOT), ("nbf is true", True, NOT),
                             ("nbf is null", None, NOT), ("nbf is a fraction (stricter than RFC 7519, I1)", IAT - 300.5, NOT)):
        check("V3t nbf: %s" % label, ev(mutated({"nbf": val}), pol0), want)
    check("V3t nbf: missing -> rejected, on the nbf row", (ev(mutated(drop=("nbf",)), pol0), stat(mutated(drop=("nbf",)), NB)), (NOT, ["NOT-MET"]))
    check("V3t nbf = iat + 61: the nbf row is the one that fails", stat(mutated({"nbf": IAT + 61}), NB), ["NOT-MET"])
    check("V3t nbf = iat + 61: ONLY the nbf row fails (isolated)", [r[0] for r in rows(mutated({"nbf": IAT + 61}), pol0) if r[1] == "NOT-MET"], [NB + " present, valid, consistent with iat"])
    check("V3t nbf within the permitted range changes no row status", [r[1] for r in rows(mutated({"nbf": IAT - 10000}), pol0)], [r[1] for r in rows(base, pol0)])
    check("V3t iat missing -> rejected", ev(mutated(drop=("iat",)), pol0), NOT)
    check("V3t exp missing -> rejected", ev(mutated(drop=("exp",)), pol0), NOT)
    check("V3t exp = iat -> rejected (iat < exp)", ev(mutated({"exp": IAT}), pol0), NOT)
    check("V3t exp < iat -> rejected", ev(mutated({"exp": IAT - 1}), pol0), NOT)
    check("V3t iat is true / a string / negative / a fraction -> rejected",
          [ev(mutated({"iat": v}), pol0) for v in (True, str(IAT), -5, IAT + 0.5)], [NOT, NOT, NOT, NOT])
    check("V3t exp is a string / a fraction -> rejected", [ev(mutated({"exp": v}), pol0) for v in (str(IAT + 300), IAT + 300.5)], [NOT, NOT])
    # N4/N5: the clock skew is at most 60 s around the attempt window
    check("V3t iat = window start - 60 (boundary): the window row is MET", stat(mutated({"iat": S0 - 60, "nbf": S0 - 360, "exp": S0 + 240}), WIN), ["MET"])
    check("V3t iat = window start - 61: the window row is NOT-MET", stat(mutated({"iat": S0 - 61, "nbf": S0 - 361, "exp": S0 + 239}), WIN), ["NOT-MET"])
    check("V3t iat = window end + 60 (boundary): the window row is MET", stat(mutated({"iat": E0 + 60, "nbf": E0 - 240, "exp": E0 + 360}), WIN), ["MET"])
    check("V3t iat = window end + 61: the window row is NOT-MET", stat(mutated({"iat": E0 + 61, "nbf": E0 - 239, "exp": E0 + 361}), WIN), ["NOT-MET"])
    # N6: the artifact is created at least 60 s after exp
    check("V3t artifact created at exp + 60 (boundary): the expiry row is MET", stat(mutated({"exp": ART - 60}), EXPR), ["MET"])
    check("V3t artifact created at exp + 59: the expiry row is NOT-MET", stat(mutated({"exp": ART - 59}), EXPR), ["NOT-MET"])
    # N7: the current clock is not part of the acceptance of historical evidence
    import time as _time
    real_time = _time.time
    try:
        verdicts = []
        for fake in (1.0, 1.9e9, 4.0e9):
            _time.time = (lambda v=fake: v)
            verdicts.append((ev(base, pol0), [r[1] for r in rows(base, pol0)]))
    finally:
        _time.time = real_time
    check("V3t the verdict and every row status are the same with the clock set to 1970, 2030 and 2096 (N7)",
          all(v == (BOUND, [r[1] for r in rows(base, pol0)]) for v in verdicts), True)
    vsrc = open(os.path.join(HERE, "read-me1.py")).read()
    check("V3t read-me1.py never reads the current time (no time.time / datetime.now / utcnow / monotonic)",
          [w for w in ("time.time(", "datetime.now", "utcnow", "time.monotonic", "date.today") if w in vsrc], [])
    # N8: the owner NAME is P, the owner ID is K
    check("V3o classes: 16 K + 9 P + 3 S, repository_owner is P and not K, repository_owner_id is K",
          (len(rm.K_CLAIMS), len(rm.P_CLAIMS), len(rm.S_CLAIMS), "repository_owner" in rm.P_CLAIMS, "repository_owner" in rm.K_CLAIMS,
           "repository_owner_id" in rm.K_CLAIMS), (16, 9, 3, True, False, True))
    time_claims = {"iat", "exp", "nbf"}
    cl_base = rm.good_claims(run_id=str(rm.RUN), run_attempt="1", check_run_id="55", workflow_sha=rm.HEAD, job_workflow_sha=rm.HEAD,
                             workflow="me1-evidence", head_ref="", base_ref="", actor="x", actor_id="1", jti="j", run_number="1")
    check("V3o every claim of the real-shaped token is classified (K, K-time, P or S): none unclassified",
          sorted(set(cl_base) - set(rm.K_CLAIMS) - time_claims - set(rm.P_CLAIMS) - set(rm.S_CLAIMS)), [])
    for val in ("someone-else", "", "o/x", 17):
        check("V3o repository_owner changed to %r: verdict and every row status unchanged" % (val,),
              (ev(mutated({"repository_owner": val}), pol0), [r[1] for r in rows(mutated({"repository_owner": val}), pol0)]),
              (BOUND, [r[1] for r in rows(base, pol0)]))
    check("V3o repository_owner removed: verdict unchanged (it is not mandatory)", ev(mutated(drop=("repository_owner",)), pol0), BOUND)
    allps = {"actor": "a2", "actor_id": "9", "ref_type": "tag", "ref_protected": "false", "repository_visibility": "private",
             "runner_environment": "self-hosted", "run_number": "999", "jti": "other", "repository_owner": "someone-else",
             "workflow": "totally-different-name", "head_ref": "x", "base_ref": "y"}
    check("V3o all 12 P/S claims (with repository_owner) changed together: verdict and every row status unchanged",
          (ev(mutated(allps), pol0), [r[1] for r in rows(mutated(allps), pol0)]), (BOUND, [r[1] for r in rows(base, pol0)]))
    check("V3o the P/S report row names repository_owner", [("repository_owner='o'" in r[2]) for r in rows(base, pol0) if r[0].endswith("claim classes P and S")], [True])

    # ---------------------------------------------------------------- V1: suppression, fail-closed
    for label, mut in (("unknown key", lambda p: dict(p, extra=1)),
                       ("missing repository", lambda p: {k: v for k, v in p.items() if k != "repository"}),
                       ("repository_id as a string", lambda p: dict(p, repository_id="1")),
                       ("repository without an owner", lambda p: dict(p, repository="r")),
                       ("other event (the reader supports the main profile only)", lambda p: dict(p, event="pull_request")),
                       ("other ref", lambda p: dict(p, ref="refs/pull/7/merge")),
                       ("other workflow path", lambda p: dict(p, workflow_path=".github/workflows/x.yml")),
                       ("sha not 40-hex", lambda p: dict(p, sha="abc")),
                       ("workflow_sha not 40-hex", lambda p: dict(p, workflow_sha="abc")),
                       ("discovery value unknown", lambda p: dict(p, discovery="maybe")),
                       ("pin with a missing field", lambda p: dict(p, pin={"run_id": 1, "run_attempt": 1})),
                       ("pin with a non-positive id", lambda p: dict(p, pin={"run_id": 0, "run_attempt": 1, "check_run_id": 5})),
                       ("pin with a boolean id", lambda p: dict(p, pin={"run_id": True, "run_attempt": 1, "check_run_id": 5})),
                       ("job_name other than the measured job", lambda p: dict(p, job_name="x"))):
        pol_f, err = rm.load_policy(policy_file(mut(pol0)))
        check("V1 invalid policy refused (fail-closed): " + label, pol_f is None and err is not None, True)
    pol_f, err = rm.load_policy(policy_file(None, raw="not json"))
    check("V1 invalid policy refused: not JSON", pol_f is None, True)
    pol_f, err = rm.load_policy(policy_file(pol0))
    check("V1 the valid policy loads", err, None)

    def with_file(mutator, pol):
        d = mutated()
        mutator(d)
        return ev(d, pol)
    check("V1 token file missing: rejected", with_file(lambda d: os.remove(os.path.join(d, "artifact", "oidc-token.jwt")), pol0), NOT)

    def empty_token(d):
        open(os.path.join(d, "artifact", "oidc-token.jwt"), "w").write("")
        mc.restamp(d)
    check("V1 token empty (manifest re-stamped): not accepted", with_file(empty_token, pol0) in (NOT, INC), True)
    check("V1 context.json missing: rejected", with_file(lambda d: os.remove(os.path.join(d, "artifact", "context.json")), pol0), NOT)
    check("V1 api/run.json missing: not accepted", with_file(lambda d: os.remove(os.path.join(d, "api", "run.json")), pol0) in (NOT, INC), True)
    check("V1 manifest missing: rejected", with_file(lambda d: os.remove(os.path.join(d, "manifest.json")), pol0), NOT)
    d = mutated()
    check("V1 the trusted keys are unavailable: incomplete", rm.overall(rm.evaluate(d, trusted_jwks=None, policy=pol0)), INC)
    check("V1 the trusted keys file does not exist: rejected", rm.overall(rm.evaluate(d, trusted_jwks="/nonexistent/jwks.json", policy=pol0)), NOT)
    # a run that did not succeed is refused by the collector (check_run), never fetched into evidence
    runs_dir = tempfile.mkdtemp()
    prev1 = os.path.join(runs_dir, "p.json")
    json.dump([], open(prev1, "w"))
    for label, over in (("failure", {"conclusion": "failure"}), ("cancelled", {"conclusion": "cancelled"}),
                        ("skipped", {"conclusion": "skipped"}), ("timed_out", {"conclusion": "timed_out"}),
                        ("neutral", {"conclusion": "neutral"}), ("action_required (held)", {"conclusion": "action_required"}),
                        ("in progress", {"status": "in_progress", "conclusion": None}), ("queued", {"status": "queued", "conclusion": None})):
        rj = os.path.join(runs_dir, "r.json")
        json.dump(rm.api_run(**over), open(rj, "w"))
        run_, got, err = rm.check_run(rj, rm.REPO, rm.HEAD, 1, prev1)
        check("V1 the collector refuses a run that is %s (suppression is never evidence)" % label, err is not None, True)
    arts = {"artifacts": [{"id": 1, "name": rm.ARTIFACT_NAME, "expired": True, "created_at": rm.ART_CREATED, "workflow_run": {"id": rm.RUN, "head_sha": rm.HEAD}}]}
    rec, aerr = rm.pick_artifact(rm.api_run(), arts, rm.HEAD)
    check("V1 an EXPIRED artifact is not picked (the R2 natural-experiment shape, synthetic)", rec is None and aerr is not None, True)
    rec, aerr = rm.pick_artifact(rm.api_run(), {"artifacts": []}, rm.HEAD)
    check("V1 a deleted (absent) artifact is not picked", rec is None and aerr is not None, True)

    # ---------------------------------------------------------------- V4: timing and publication
    for label, created in (("created BEFORE the token expired (early publication)", "2026-01-01T00:05:00Z"),
                           ("created 30 s after exp (below the 60 s margin)", "2026-01-01T00:05:40Z"),
                           ("created outside the attempt window", "2025-01-01T00:00:00Z")):
        d = mutated()
        mp = os.path.join(d, "manifest.json")
        m = json.load(open(mp))
        m["artifact"]["created_at"] = created
        json.dump(m, open(mp, "w"))
        check("V4 artifact " + label + ": rejected", ev(d, pol0), NOT)
    two = {"artifacts": [dict(arts["artifacts"][0], expired=False, id=1), dict(arts["artifacts"][0], expired=False, id=2)]}
    rec, aerr = rm.pick_artifact(rm.api_run(), two, rm.HEAD)
    check("V4 two artifacts in the window: not picked (ambiguous)", rec is None and aerr is not None, True)

    # ---------------------------------------------------------------- command line
    pf = policy_file(pol0)
    rc, out = cli(base, "--trusted-jwks", jf, "--policy", pf)
    check("CLI --policy: bound evidence, exit 0", (rc, "OVERALL: EVIDENCE BOUND, P NOT READ" in out), (0, True))
    rc, out = cli(mutated({"sha": "b2" * 20}), "--trusted-jwks", jf, "--policy", pf)
    check("CLI --policy: a rejected package, exit 1", rc, 1)
    check("CLI --policy together with --expect-run-id: refused, exit 2", cli(base, "--trusted-jwks", jf, "--policy", pf, "--expect-run-id", "1")[0], 2)
    check("CLI --policy with an invalid policy: refused, exit 2", cli(base, "--trusted-jwks", jf, "--policy", policy_file(None, raw="x"))[0], 2)
    check("CLI --policy without a value: refused, exit 2", cli(base, "--policy")[0], 2)
    print("SELFTEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


# ---------------------------------------------------------------- mutation check: the matrix can FAIL
MUTATIONS = [
    ("the nbf check is ignored (06w N1-N3)",
     [('bool(numeric_date(nbf) and numeric_date(iat) and nbf <= iat + NBF_SKEW)', 'True')]),
    ("a missing nbf is accepted (06w N1)",
     [('bool(numeric_date(nbf) and numeric_date(iat) and nbf <= iat + NBF_SKEW)', 'bool(nbf is None or (numeric_date(nbf) and numeric_date(iat) and nbf <= iat + NBF_SKEW))')]),
    ("the nbf boundary is off by one (nbf < iat + 60)",
     [('nbf <= iat + NBF_SKEW)', 'nbf < iat + NBF_SKEW)')]),
    ("the nbf skew is 61 instead of 60",
     [('NBF_SKEW = 60    #', 'NBF_SKEW = 61    #')]),
    ("nbf is compared with the CURRENT clock instead of iat (06w N7)",
     [('nbf <= iat + NBF_SKEW)', 'nbf <= __import__("time").time() + NBF_SKEW)')]),
    ("the iat window tolerance is 120 s again (06w N4)",
     [('TOLERANCE = 60   #', 'TOLERANCE = 120  #')]),
    ("the current clock enters the acceptance of the iat (06w N7)",
     [('and w["start"] and to_epoch(w["start"]) - TOLERANCE <= iat <= to_epoch(w["end"]) + TOLERANCE and exp > iat)',
       'and w["start"] and to_epoch(w["start"]) - TOLERANCE <= iat <= to_epoch(w["end"]) + TOLERANCE and exp > iat and iat <= __import__("time").time())')]),
    ("a non-integer NumericDate is accepted (06w I1)",
     [('return isinstance(v, int) and not isinstance(v, bool) and v >= 0', 'return isinstance(v, (int, float)) and not isinstance(v, bool)')]),
    ("the owner NAME is bound like a K claim (06w N8)",
     [('    add("binds repository_owner_id", claims.get("repository_owner_id") == str(pol["repository_owner_id"]), "claim %r" % (claims.get("repository_owner_id"),))',
       '    add("binds repository_owner_id", claims.get("repository_owner_id") == str(pol["repository_owner_id"]), "claim %r" % (claims.get("repository_owner_id"),))\n    add("binds repository_owner", claims.get("repository_owner") == "o", "claim %r" % (claims.get("repository_owner"),))')]),
    ("repository_owner is removed from the P class (06w N8)",
     [('"run_number", "jti", "repository_owner"]', '"run_number", "jti"]')]),
    ("the pin's run_id and run_attempt are ignored (policy row AND the independent legacy expectation)",
     [('add("pin: run_id", claims.get("run_id") == str(pin["run_id"]) and (man or {}).get("run_id") == pin["run_id"],',
       'add("pin: run_id", True,'),
      ('add("pin: run_attempt", claims.get("run_attempt") == str(pin["run_attempt"]) and (man or {}).get("run_attempt") == pin["run_attempt"],',
       'add("pin: run_attempt", True,'),
      ('        rid, att = str(pin["run_id"]), str(pin["run_attempt"])',
       '        rid, att = str((man or {}).get("run_id")), str((man or {}).get("run_attempt"))')]),
    ("the pinned check_run_id claim is ignored",
     [('add("pin: check_run_id", claims.get("check_run_id") == str(pin["check_run_id"]),',
       'add("pin: check_run_id", True,')]),
    ("the pinned check-run is not cross-checked with the Actions job id (isolated by its own test)",
     [('add("pin: check_run_id equals the Actions job id (API)", job_ids == [pin["check_run_id"]],',
       'add("pin: check_run_id equals the Actions job id (API)", True,')]),
    ("the listing's conclusion and status are not checked",
     [('len(hit) == 1 and hit[0].get("status") == "completed" and hit[0].get("conclusion") == "success",', 'True,')]),
    ("an ambiguous selection picks the candidate that matches (no exactly-one rule)",
     [('if len(cands) == 1:', 'if len(cands) >= 1:')]),
    ("a missing listing is tolerated (the missing-listing row is only a NOTE)",
     [('rows.append(("POLICY discovery: candidate runs", "NOT-READ",', 'rows.append(("POLICY discovery: candidate runs", "NOTE",')]),
    ("F1: the policy may ask for an optional discovery (the P-c/V profile has no such mode)",
     [('    if pol.get("discovery", "required") != "required":', '    if False:')]),
    ("a truncated listing is tolerated (the first page is taken as complete)",
     [('    if isinstance(total, int) and not isinstance(total, bool) and total > len(lst):\n        return None',
       '    if False:\n        return None')]),
    ("the approved commit is not bound to the policy",
     [('add("binds sha (the approved commit)", claims.get("sha") == pol["sha"],',
       'add("binds sha (the approved commit)", True,')]),
    ("the approved workflow identity is not bound (policy row AND the legacy workflow_ref field)",
     [('add("binds workflow_ref (the approved workflow identity)", claims.get("workflow_ref") == wref,',
       'add("binds workflow_ref (the approved workflow identity)", True,'),
      ('    for f in FIELDS:\n        exp_v = api[f]',
       '    for f in FIELDS:\n        if f == "workflow_ref":\n            continue\n        exp_v = api[f]')]),
    ("repository_id is not bound to the policy (policy row AND the legacy API row)",
     [('add("binds repository_id", claims.get("repository_id") == str(pol["repository_id"]),',
       'add("binds repository_id", True,'),
      ('add("OIDC binds repository_id (API repository.id)", rid is not None and claims.get("repository_id") == rid,',
       'add("OIDC binds repository_id (API repository.id)", True,')]),
    ("an author-choosable claim (the workflow name) is bound",
     [('    add("binds iss", claims.get("iss") == ISS, "claim %r" % (claims.get("iss"),))',
       '    add("binds iss", claims.get("iss") == ISS and claims.get("workflow") == "me1-evidence", "claim %r" % (claims.get("iss"),))')]),
    ("the policy's workflow_sha is not bound",
     [('add("binds %s (the approved workflow file commit)" % cname, claims.get(cname) == pol["workflow_sha"],',
       'add("binds %s (the approved workflow file commit)" % cname, True,')]),
    # F2: the PR-collection path (covered by test-fetch-me1.py)
    ("F2: the PR object's head.sha is not compared with the approved PR head",
     [('    if h.get("sha") != approved_head:', '    if False:')], ("test-fetch-me1.py",)),
    ("F2: the PR object's head.ref is not checked",
     [('(h.get("sha"), approved_head))\n    if h.get("ref") != probe_ref:', '(h.get("sha"), approved_head))\n    if False:')], ("test-fetch-me1.py",)),
    ("F3: the run's PR entry head branch is not checked",
     [('    bad = []\n    if h.get("ref") != probe_ref:', '    bad = []\n    if False:')], ("test-fetch-me1.py",)),
    ("F2: a merged probe PR is accepted",
     [('    if pr.get("merged") is not False:', '    if False:')], ("test-fetch-me1.py",)),
    # F3: the run <-> approved PR link
    ("F3: the PR object's number is not compared with the PR number asked for",
     [('    elif not re.match(r"^[0-9]+$", str(expected_number)) or pr["number"] != int(expected_number):', '    elif False:')], ("test-fetch-me1.py",)),
    ("F3: the run's PR entry number is not compared with the approved PR number",
     [('    if not re.match(r"^[0-9]+$", str(expected_number)) or e["number"] != int(expected_number):', '    if False:')], ("test-fetch-me1.py",)),
    ("F3: a run without any pull_requests is accepted (the emptiness check AND the exactly-one layer removed together)",
     [('    if not isinstance(prs, list) or not prs:', '    if False:'),
      ('    if len(prs) != 1:', '    if len(prs) > 1:'),
      ('    e = prs[0]\n', '    e = prs[0] if prs else {"number": int(expected_number), "head": {"ref": probe_ref}, "base": {"ref": base_ref}}\n')], ("test-fetch-me1.py",)),
    ("F3: a run associated with several pull requests is accepted (ambiguity tolerated)",
     [('    if len(prs) != 1:', '    if False:')], ("test-fetch-me1.py",)),
    ("F3: the run <-> PR link is not checked in the collection at all",
     [('        link, lerr = check_run_pr_link(run, pr_number)\n        if lerr:', '        link, lerr = [{"number": pr_number}], None\n        if lerr:')], ("test-fetch-me1.py",)),
    ("F2: the run's head_sha is assumed equal to the PR head again (the observation is turned back into a premise)",
     [('want = {"event": "pull_request", "status": "completed", "conclusion": "success", "run_attempt": attempt}',
       'want = {"event": "pull_request", "status": "completed", "conclusion": "success", "run_attempt": attempt, "head_sha": head}')], ("test-fetch-me1.py",)),
]


def mutations():
    src = open(os.path.join(HERE, "read-me1.py")).read()
    failed = 0
    for entry in MUTATIONS:
        name, repls = entry[0], entry[1]
        scripts = entry[2] if len(entry) > 2 else ("test-pcv.py", "me1-controls.py")
        mutated_src = src
        for old, new in repls:
            if mutated_src.count(old) != 1:
                print("MUTATION ERROR: %r does not match exactly once in read-me1.py (%d)" % (name, mutated_src.count(old)))
                return 2
            mutated_src = mutated_src.replace(old, new)
        tmp = tempfile.mkdtemp()
        for f in ("read-me1.py", "me1-controls.py", "test-pcv.py", "test-fetch-me1.py", "fetch-me1.sh", "fetch-jwks.sh"):
            shutil.copy(os.path.join(HERE, f), tmp)
        open(os.path.join(tmp, "read-me1.py"), "w").write(mutated_src)
        n = 0
        for script in scripts:
            args = [] if script == "test-fetch-me1.py" else ["--selftest"]
            p = subprocess.run([sys.executable, "-I", os.path.join(tmp, script)] + args, capture_output=True, text=True)
            n += sum(1 for l in p.stdout.splitlines() if l.startswith("FAIL"))
        print("%-4s mutation %-86s %d failing check(s)" % ("ok" if n else "FAIL", name, n))
        failed += 0 if n else 1
    print("MUTATIONS %s (%d planted defects)" % ("ALL CAUGHT" if not failed else "SOME NOT CAUGHT", len(MUTATIONS)))
    return 1 if failed else 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    if argv[1:] == ["--mutations"]:
        return mutations()
    print("usage: test-pcv.py --selftest | --mutations (stand-alone only)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
