#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Harness reader for the M-E1 evidence inventory (phase 1): which authentic run evidence exists.

  read-me1.py DIR --trusted-jwks FILE --expect-repo OWNER/REPO --expect-run-id ID --expect-attempt N \
                  --expect-head-sha SHA
  read-me1.py --pk                          positive control: the comparator on synthetic records
  read-me1.py --check-run RUN_JSON OWNER/REPO HEAD ATTEMPT PREV_JSON        (used by fetch-me1.sh)
  read-me1.py --pick-artifact RUN_JSON ARTIFACTS_JSON HEAD                  (used by fetch-me1.sh)
  read-me1.py --write-manifest DIR OWNER/REPO HEAD ATTEMPT PREV_JSON ARTIFACTS_JSON ZIP_SHA256
  read-me1.py --selftest                    stand-alone only

DIR is produced by fetch-me1.sh (a NEW directory per run): manifest.json, api/run.json,
api/jobs.json, artifact/context.json, artifact/oidc-token.jwt.

TRUST ROOT (kept apart from the evidence): the issuer's public keys are NOT part of DIR. They are given
with --trusted-jwks, a file the owner fetched DIRECTLY from the token issuer (fetch-jwks.sh) into a
location OUTSIDE the evidence directory. A key file inside DIR is refused: a manifest digest cannot
authenticate the origin of a key that sits in the same replaceable package. Trusted-fetch conditions:
the owner's machine, TLS to the issuer, fetched after the run (key rotation), kept outside DIR.

What is measured: whether the platform-signed OIDC token (verified here, offline, against the issuer's
public keys, in pure Python) binds the (workflow path+ref, commit, identity, run, attempt) tuple the
API reports for the run, and how it differs from the workflow's own self-report (context.json). The
self-report is author-controlled, so it is never evidence on its own, and a difference in it does not
invalidate the signed evidence (it is reported as NOTE).

Measured on the first real run (45063800073): the token's `sub` carries the numeric owner and repository
IDs (`repo:OWNER@OWNERID/REPO@REPOID:ref:...`), not the documented plain form. Both forms are accepted;
in the ID form the numbers must equal the API's repository and owner IDs, and the `repository_id` and
`repository_owner_id` claims must equal them as well.

The check "P (PR-author influence)" needs the evidence of a pull_request run: it is NOT READ in this
package, so the strongest overall result is "EVIDENCE BOUND, P NOT READ"; the M-E1 verdict
(PASS / FAIL / INCONCLUSIVE) is taken in the report, not by this tool.
"""
import base64
import contextlib
import hashlib
import hmac
import io
import json
import os
import re
import subprocess
import sys
import tempfile

WORKFLOW_PATH = ".github/workflows/me1-evidence.yml"
ARTIFACT_NAME = "me1-evidence"
ISS = "https://token.actions.githubusercontent.com"
AUD = "me1-evidence"
FETCHED = ["artifact/context.json", "artifact/oidc-token.jwt", "api/run.json", "api/jobs.json"]
# the artifact must have been created (server time) this long after the token's exp (workflow waits 120 s)
PUBLISH_MARGIN = 60
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
HELD_ATTEMPT_1 = {"run_attempt": 1, "status": "completed", "conclusion": "action_required", "jobs": 0}
# DigestInfo prefix of SHA-256 (RFC 8017, EMSA-PKCS1-v1_5)
SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
TOLERANCE = 120  # seconds around the attempt window for the token's iat


# ---------------------------------------------------------------- helpers
def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def sha256_file(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def to_epoch(iso):
    import calendar
    import time
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


def window_of(run):
    w = {"start": run.get("run_started_at"), "end": run.get("updated_at")}
    ok = all(isinstance(v, str) and ISO.match(v) for v in w.values()) and w["start"] <= w["end"]
    return w, ok


def previous_ok(attempt, prev):
    if attempt == 1:
        return None if prev == [] else "attempt 1 must have no earlier attempt, got %r" % (prev,)
    if attempt == 2:
        return None if prev == [HELD_ATTEMPT_1] else (
            "attempt 2 needs attempt 1 completed/action_required with 0 jobs, got %r" % (prev,))
    return "attempt %r is not accepted (only 1, or 2 after a held attempt 1)" % (attempt,)


def pick_artifact(run, artifacts, head):
    w, ok = window_of(run)
    if not ok:
        return None, "attempt window unreadable"
    lst = artifacts.get("artifacts") if isinstance(artifacts, dict) else None
    if not isinstance(lst, list):
        return None, "artifact list unreadable"
    hit = []
    for a in lst:
        wr = a.get("workflow_run") or {}
        ca = a.get("created_at")
        if (a.get("name") == ARTIFACT_NAME and wr.get("id") == run.get("id")
                and wr.get("head_sha") == head and a.get("expired") is False
                and isinstance(ca, str) and ISO.match(ca) and w["start"] <= ca <= w["end"]
                and isinstance(a.get("id"), int) and not isinstance(a.get("id"), bool)):
            hit.append(a)
    if len(hit) != 1:
        return None, "%d artifact(s) qualify for this attempt (need exactly 1)" % len(hit)
    a = hit[0]
    return {"id": a["id"], "name": a["name"], "workflow_run_id": run["id"], "head_sha": head,
            "created_at": a["created_at"], "size_in_bytes": a.get("size_in_bytes")}, None


def artifact_ok(m):
    w, a = m.get("attempt_window"), m.get("artifact")
    if not (isinstance(w, dict) and isinstance(w.get("start"), str) and isinstance(w.get("end"), str)
            and ISO.match(w["start"]) and ISO.match(w["end"]) and w["start"] <= w["end"]):
        return "attempt window missing or unreadable"
    if not isinstance(a, dict):
        return "artifact record missing"
    if not isinstance(a.get("id"), int) or isinstance(a.get("id"), bool) or a["id"] <= 0:
        return "artifact id"
    if a.get("name") != ARTIFACT_NAME:
        return "artifact name"
    if a.get("workflow_run_id") != m.get("run_id") or a.get("head_sha") != m.get("head_sha"):
        return "artifact run or head differs from the manifest"
    ca = a.get("created_at")
    if not (isinstance(ca, str) and ISO.match(ca) and w["start"] <= ca <= w["end"]):
        return "artifact created outside the attempt window"
    if not (isinstance(a.get("zip_sha256"), str) and re.match(r"^[0-9a-f]{64}$", a["zip_sha256"])):
        return "artifact zip digest"
    return None


# ---------------------------------------------------------------- RS256 (pure Python)
def verify_rs256(signing_input, sig, jwk):
    """True iff sig is a valid RSASSA-PKCS1-v1_5 / SHA-256 signature of signing_input under jwk."""
    try:
        n, e = int.from_bytes(b64d(jwk["n"]), "big"), int.from_bytes(b64d(jwk["e"]), "big")
    except (KeyError, ValueError, TypeError):
        return False
    k = (n.bit_length() + 7) // 8
    if len(sig) != k or n < (1 << 1000) or e < 3:
        return False
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
    t = SHA256_PREFIX + hashlib.sha256(signing_input).digest()
    expected = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return hmac.compare_digest(em, expected)


def verify_token(token, jwks):
    """Returns (claims, error-or-None)."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None, "not a three-part JWT"
    try:
        header = json.loads(b64d(parts[0]))
        claims = json.loads(b64d(parts[1]))
        sig = b64d(parts[2])
    except (ValueError, TypeError):
        return None, "JWT parts are not decodable"
    if not isinstance(header, dict) or not isinstance(claims, dict):
        return None, "JWT header or payload is not an object"
    if header.get("alg") != "RS256":
        return claims, "alg is %r, only RS256 is accepted" % (header.get("alg"),)
    keys = jwks.get("keys") if isinstance(jwks, dict) else None
    if not isinstance(keys, list):
        return claims, "JWKS unreadable"
    cand = [k for k in keys if isinstance(k, dict) and k.get("kid") == header.get("kid")
            and k.get("kty") == "RSA"]
    if len(cand) != 1:
        return claims, "%d JWKS key(s) match kid %r" % (len(cand), header.get("kid"))
    if not verify_rs256((parts[0] + "." + parts[1]).encode(), sig, cand[0]):
        return claims, "signature invalid"
    return claims, None


# ---------------------------------------------------------------- records and comparator
FIELDS = ["repository", "run_id", "run_attempt", "sha", "workflow_ref", "event_name"]


def record_from_api(run):
    return {"repository": (run.get("repository") or {}).get("full_name"),
            "run_id": str(run.get("id")), "run_attempt": str(run.get("run_attempt")),
            "sha": run.get("head_sha"),
            "workflow_ref": "%s/%s@refs/heads/%s" % ((run.get("repository") or {}).get("full_name"),
                                                      run.get("path"), run.get("head_branch")),
            "event_name": run.get("event")}


def api_ids(run):
    """(repository id, owner id) as the API reports them, as strings (None when absent)."""
    repo = run.get("repository") or {}
    rid, oid = repo.get("id"), (repo.get("owner") or {}).get("id")
    f = lambda v: str(v) if isinstance(v, int) and not isinstance(v, bool) else None
    return f(rid), f(oid)


def sub_ok(sub, repo, ref, rid, oid):
    """The subject must be the documented plain form, or the ID form carrying EXACTLY the API's IDs."""
    if not isinstance(sub, str) or "/" not in (repo or ""):
        return False
    owner, name = repo.split("/", 1)
    if sub == "repo:%s:ref:%s" % (repo, ref):
        return True
    return (rid is not None and oid is not None
            and sub == "repo:%s@%s/%s@%s:ref:%s" % (owner, oid, name, rid, ref))


def record_from_claims(c):
    return {f: (str(c.get(f)) if c.get(f) is not None else None) for f in FIELDS}


def record_from_context(c):
    return {f: c.get(f) for f in FIELDS} if isinstance(c, dict) else {f: None for f in FIELDS}


def compare_records(a, b):
    """Fields in which the two records differ (empty = identical on all fields)."""
    return [f for f in FIELDS if a.get(f) != b.get(f)]


def pk_rows():
    """Positive control (#81 M-E1): the comparator is exercised on SYNTHETIC records only; it does not
    depend on whether the platform's evidence differs between runs (that is the measured subject)."""
    base = {"repository": "o/r", "run_id": "1", "run_attempt": "1", "sha": "a" * 40,
            "workflow_ref": "o/r/.github/workflows/me1-evidence.yml@refs/heads/main",
            "event_name": "workflow_dispatch"}
    rows = []
    for f in FIELDS:
        other = dict(base, **{f: base[f] + "x"})
        d = compare_records(base, other)
        rows.append(("PK (U) planted difference in %s" % f, "MET" if d == [f] else "NOT-MET", "differs in %s" % d))
    d = compare_records(base, dict(base))
    rows.append(("PK (J) identical records", "MET" if d == [] else "NOT-MET", "differences %s" % d))
    return rows


# ---------------------------------------------------------------- manifest
def check_manifest(d, expect_head, expect_repo, expect_run_id, expect_attempt):
    rows = []
    mtxt = read(os.path.join(d, "manifest.json"))
    if mtxt is None:
        return [("run binding", "NOT-MET", "manifest.json missing: the evidence is not bound to a run")], None
    try:
        m = json.loads(mtxt)
        assert isinstance(m, dict)
    except (ValueError, AssertionError):
        return [("run binding", "NOT-MET", "manifest.json is not a JSON object")], None
    problems = []
    want = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch", "status": "completed",
            "conclusion": "success", "head_branch": "main"}
    for k, v in want.items():
        if m.get(k) != v:
            problems.append("%s=%r" % (k, m.get(k)))
    if not isinstance(m.get("run_id"), int) or isinstance(m.get("run_id"), bool):
        problems.append("run_id")
    if not isinstance(m.get("head_sha"), str) or not SHA_RE.match(m["head_sha"]):
        problems.append("head_sha")
    files = m.get("files")
    if not isinstance(files, dict) or sorted(files) != sorted(FETCHED):
        problems.append("files set")
        files = {}
    for rel, dig in files.items():
        if sha256_file(os.path.join(d, rel)) != dig:
            problems.append("file %s differs from the manifest digest" % rel)
    known = set(FETCHED) | {"manifest.json"}
    present = set()
    for root, _, fs in os.walk(d):
        for f in fs:
            present.add(os.path.relpath(os.path.join(root, f), d))
    if present - known:
        problems.append("unlisted file(s) %s" % sorted(present - known))
    rows.append(("run binding", "NOT-MET" if problems else "MET",
                 "; ".join(problems) if problems else
                 "run %s attempt %s, workflow_dispatch, completed/success, branch main" % (m.get("run_id"), m.get("run_attempt"))))
    rows.append(("repository", "NOT-READ" if expect_repo is None else
                 ("MET" if m.get("repository") == expect_repo else "NOT-MET"), "manifest %r" % (m.get("repository"),)))
    if expect_run_id is None:
        rows.append(("run id", "NOT-READ", "--expect-run-id not given"))
    elif not re.match(r"^[0-9]+$", str(expect_run_id)):
        rows.append(("run id", "NOT-MET", "expected run id is not numeric"))
    else:
        rid = m.get("run_id")
        rows.append(("run id", "MET" if isinstance(rid, int) and not isinstance(rid, bool) and rid == int(expect_run_id) else "NOT-MET", "manifest %r" % (rid,)))
    att = m.get("run_attempt")
    if expect_attempt is None:
        rows.append(("attempt", "NOT-READ", "--expect-attempt not given"))
    elif not re.match(r"^[0-9]+$", str(expect_attempt)):
        rows.append(("attempt", "NOT-MET", "expected attempt is not numeric"))
    else:
        rows.append(("attempt", "MET" if isinstance(att, int) and not isinstance(att, bool) and att == int(expect_attempt) else "NOT-MET", "manifest %r" % (att,)))
    perr = previous_ok(att, m.get("previous_attempts")) if isinstance(att, int) and not isinstance(att, bool) else "attempt missing"
    rows.append(("earlier attempts", "MET" if perr is None else "NOT-MET", perr or "history acceptable for attempt %r" % (att,)))
    aerr = artifact_ok(m)
    rows.append(("artifact origin", "MET" if aerr is None else "NOT-MET", aerr or "artifact %s created inside the attempt window" % m["artifact"]["id"]))
    if expect_head is None:
        rows.append(("approved head SHA", "NOT-READ", "--expect-head-sha not given"))
    elif not SHA_RE.match(expect_head):
        rows.append(("approved head SHA", "NOT-MET", "expected value is not a 40-hex SHA"))
    else:
        rows.append(("approved head SHA", "MET" if m.get("head_sha") == expect_head else "NOT-MET", "run head %s" % m.get("head_sha")))
    return rows, m


# ---------------------------------------------------------------- evaluation
def trusted_keys(d, path):
    """The trust root, kept apart from the evidence. Returns (jwks, row)."""
    name = "trusted JWKS (separate from the evidence)"
    if path is None:
        return None, (name, "NOT-READ", "--trusted-jwks not given")
    real, base = os.path.realpath(path), os.path.realpath(d)
    if real == base or real.startswith(base + os.sep):
        return None, (name, "NOT-MET", "the key file is inside the evidence package: it cannot be a trust root")
    try:
        jwks = json.loads(read(path))
    except (TypeError, ValueError):
        return None, (name, "NOT-MET", "key file unreadable or not JSON")
    if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list) or not jwks["keys"]:
        return None, (name, "NOT-MET", "key file has no keys")
    return jwks, (name, "MET", "%d key(s), outside the evidence package; sha256 %s" % (len(jwks["keys"]), sha256_file(path)))


def evaluate(d, expect_head=None, expect_repo=None, expect_run_id=None, expect_attempt=None, trusted_jwks=None):
    res, man = check_manifest(d, expect_head, expect_repo, expect_run_id, expect_attempt)

    def add(name, ok, note=""):
        res.append((name, "MET" if ok else "NOT-MET", note))

    def note(name, text):
        res.append((name, "NOTE", text))

    jwks, jrow = trusted_keys(d, trusted_jwks)
    res.append(jrow)
    run = ctx = token = None
    try:
        run = json.loads(read(os.path.join(d, "api", "run.json")))
    except (TypeError, ValueError):
        pass
    try:
        ctx = json.loads(read(os.path.join(d, "artifact", "context.json")))
    except (TypeError, ValueError):
        ctx = None
    token = read(os.path.join(d, "artifact", "oidc-token.jwt"))
    if run is None or token is None or jwks is None:
        res.append(("OIDC evidence", "NOT-READ" if jrow[1] != "NOT-MET" else "NOT-MET",
                    "api/run.json or the token missing, or no usable trusted JWKS"))
        res.append(("P (PR-author influence)", "NOT-READ", "needs the evidence of a pull_request run (separate GO)"))
        return res

    api = record_from_api(run)
    if man:
        add("API metadata file agrees with the manifest",
            api["run_id"] == str(man.get("run_id")) and api["run_attempt"] == str(man.get("run_attempt"))
            and api["sha"] == man.get("head_sha") and (run.get("path") == man.get("workflow_path")),
            "api/run.json vs manifest")
    claims, err = verify_token(token, jwks)
    add("OIDC signature (issuer's public keys, offline)", err is None, err or "RS256 signature valid")
    if claims is None:
        res.append(("P (PR-author influence)", "NOT-READ", "needs the evidence of a pull_request run (separate GO)"))
        return res
    add("OIDC issuer", claims.get("iss") == ISS, "iss %r" % (claims.get("iss"),))
    add("OIDC audience (the measurement's own)", claims.get("aud") == AUD, "aud %r" % (claims.get("aud"),))
    w, wok = window_of(run)
    iat, exp = claims.get("iat"), claims.get("exp")
    tok_ok = (wok and isinstance(iat, int) and isinstance(exp, int) and not isinstance(iat, bool)
              and w["start"] and to_epoch(w["start"]) - TOLERANCE <= iat <= to_epoch(w["end"]) + TOLERANCE and exp > iat)
    add("OIDC issued inside the attempt window", bool(tok_ok), "iat %r, window %s..%s" % (iat, w["start"], w["end"]))
    art = (man or {}).get("artifact") or {}
    try:
        pub = to_epoch(art.get("created_at"))
    except (TypeError, ValueError):
        pub = None
    add("OIDC provably expired before the artifact was created (server time)",
        isinstance(exp, int) and not isinstance(exp, bool) and pub is not None and pub >= exp + PUBLISH_MARGIN,
        "exp %r, artifact created_at %s (needs >= exp+%ds)" % (exp, art.get("created_at"), PUBLISH_MARGIN))
    cl = record_from_claims(claims)
    for f in FIELDS:
        exp_v = api[f]
        if expect_repo is not None and f == "repository":
            exp_v = expect_repo
        add("OIDC binds %s" % f, cl[f] == exp_v and cl[f] is not None, "claim %r, API %r" % (cl[f], exp_v))
    repo = api["repository"]
    if claims.get("job_workflow_ref") is None:
        note("OIDC job_workflow_ref", "claim absent: not mandatory (documented mainly for reusable workflows); not mistaken for a failed binding")
    else:
        add("OIDC binds job_workflow_ref (path+ref)", claims.get("job_workflow_ref") == api["workflow_ref"], "claim %r" % (claims.get("job_workflow_ref"),))
    rid, oid = api_ids(run)
    add("OIDC binds repository_id (API repository.id)", rid is not None and claims.get("repository_id") == rid,
        "claim %r, API %r" % (claims.get("repository_id"), rid))
    add("OIDC binds repository_owner_id (API owner.id)", oid is not None and claims.get("repository_owner_id") == oid,
        "claim %r, API %r" % (claims.get("repository_owner_id"), oid))
    add("OIDC binds ref and subject (identity, IDs from the API)",
        claims.get("ref") == "refs/heads/main" and sub_ok(claims.get("sub"), repo, "refs/heads/main", rid, oid),
        "ref %r sub %r" % (claims.get("ref"), claims.get("sub")))
    for cname in ("workflow_sha", "job_workflow_sha"):
        if claims.get(cname) is None:
            note("OIDC %s" % cname, "claim absent: not mandatory")
        else:
            add("OIDC binds %s (the workflow file's commit)" % cname, claims.get(cname) == api["sha"], "claim %r" % (claims.get(cname),))
    note("OIDC informational claims", "ref_type %r, ref_protected %r, repository_visibility %r, runner_environment %r (reported, not judged)" % (
        claims.get("ref_type"), claims.get("ref_protected"), claims.get("repository_visibility"), claims.get("runner_environment")))
    # the self-report is author-controlled: it is only compared, never trusted
    diff = compare_records(record_from_context(ctx), cl)
    if ctx is None:
        note("self-report (context.json)", "unreadable; the signed evidence is judged on its own")
    elif diff:
        note("self-report (context.json) differs from the signed claims", "differs in %s (author-controlled; the signed claims decide)" % diff)
    else:
        note("self-report (context.json)", "identical to the signed claims (informational)")
    res.append(("P (PR-author influence)", "NOT-READ", "needs the evidence of a pull_request run (separate GO)"))
    return res


def overall(res):
    r = [x for x in res]
    if any(x[1] == "NOT-MET" for x in r):
        return "EVIDENCE NOT BOUND (NOT MET)"
    unread = [x[0] for x in r if x[1] == "NOT-READ"]
    if not unread:
        return "EVIDENCE BOUND, ALL READ"
    if all(u.startswith("P (") for u in unread):
        return "EVIDENCE BOUND, P NOT READ"
    return "INCOMPLETE (not read)"


def report(res):
    for c, r, n in res:
        print("%-52s %-9s %s" % (c, r, n))
    print("OVERALL: %s" % overall(res))
    print("INVENTORY (what each evidence type is; the verdict is taken in the report):")
    print("  API run metadata   - created by the platform, read from outside; unsigned; binds path/ref, head, run, attempt")
    print("  OIDC token claims  - created by the platform, signed; independently verifiable against the issuer's keys; see rows above")
    print("  context.json       - created by the workflow itself: self-report, author-controlled, never evidence on its own")


# ---------------------------------------------------------------- manifest writer and CLI helpers
def check_run(run_json, repo, head, attempt, prev_json):
    try:
        run = json.loads(read(run_json))
    except (TypeError, ValueError):
        return None, None, "run JSON unreadable"
    if not SHA_RE.match(head or ""):
        return None, None, "approved head is not a 40-hex SHA"
    if not re.match(r"^[0-9]+$", str(attempt)):
        return None, None, "attempt is not numeric"
    attempt = int(attempt)
    try:
        prev = json.loads(read(prev_json))
    except (TypeError, ValueError):
        return None, None, "earlier-attempts JSON unreadable"
    perr = previous_ok(attempt, prev)
    if perr:
        return None, None, perr
    got = {"workflow_path": run.get("path"), "event": run.get("event"), "status": run.get("status"),
           "conclusion": run.get("conclusion"), "head_branch": run.get("head_branch"),
           "run_attempt": run.get("run_attempt"), "head_sha": run.get("head_sha")}
    want = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch", "status": "completed",
            "conclusion": "success", "head_branch": "main", "run_attempt": attempt, "head_sha": head}
    bad = ["%s=%r (want %r)" % (k, got[k], v) for k, v in want.items() if got[k] != v]
    for key in ("repository", "head_repository"):
        if (run.get(key) or {}).get("full_name") != repo:
            bad.append("%s differs" % key)
    if not isinstance(run.get("id"), int) or isinstance(run.get("id"), bool):
        bad.append("run id")
    if bad:
        return None, None, "the run is not the approved one: " + "; ".join(bad)
    got["previous_attempts"] = prev
    return run, got, None


def check_run_main(run_json, repo, head, attempt, prev_json):
    _, _, err = check_run(run_json, repo, head, attempt, prev_json)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    print("run is the approved one")
    return 0


def pick_artifact_main(run_json, artifacts_json, head):
    try:
        run, arts = json.loads(read(run_json)), json.loads(read(artifacts_json))
    except (TypeError, ValueError):
        print("refusing: run or artifact JSON unreadable", file=sys.stderr)
        return 1
    rec, err = pick_artifact(run, arts, head)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    print(rec["id"])
    return 0


def write_manifest(d, repo, head, attempt, prev_json, artifacts_json, zip_sha):
    run_json = os.path.join(d, "api", "run.json")
    run, got, err = check_run(run_json, repo, head, attempt, prev_json)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    try:
        arts = json.loads(read(artifacts_json))
    except (TypeError, ValueError):
        print("refusing: artifact JSON unreadable", file=sys.stderr)
        return 1
    rec, aerr = pick_artifact(run, arts, head)
    if aerr:
        print("refusing: " + aerr, file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{64}$", zip_sha or ""):
        print("refusing: zip digest malformed", file=sys.stderr)
        return 1
    rec["zip_sha256"] = zip_sha
    got["attempt_window"] = window_of(run)[0]
    got["artifact"] = rec
    m = dict(got, run_id=run["id"], repository=repo,
             files={rel: sha256_file(os.path.join(d, rel)) for rel in FETCHED})
    if any(v is None for v in m["files"].values()):
        print("refusing: a fetched file is missing", file=sys.stderr)
        return 1
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
    print("manifest written for run %s (attempt %s, head %s)" % (m["run_id"], m["run_attempt"], head))
    return 0


# ---------------------------------------------------------------- self-test
HEAD = "a1" * 20
REPO = "o/r"
REPO_ID, OWNER_ID = 1467589211, 359862858  # the values read on the real run; the fixtures keep them
RUN = 123456
START, END = "2026-01-01T00:00:00Z", "2026-01-01T00:12:00Z"
IAT = 1767225610  # 2026-01-01T00:00:10Z; the token's exp is IAT + 300 (00:05:10Z)
ART_CREATED = "2026-01-01T00:07:20Z"  # exp + 130 s: the workflow publishes after exp + 120
KID = "test-kid"
DEL = object()


def openssl(*args, data=None):
    p = subprocess.run(["openssl"] + list(args), input=data, capture_output=True, check=True)
    return p.stdout


class Key:
    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.pem = os.path.join(self.dir, "k.pem")
        openssl("genrsa", "-out", self.pem, "2048")
        mod = openssl("rsa", "-in", self.pem, "-noout", "-modulus").decode().strip().split("=")[1]
        self.n = int(mod, 16)

    def jwk(self, kid=KID):
        nb = self.n.to_bytes((self.n.bit_length() + 7) // 8, "big")
        return {"kty": "RSA", "kid": kid, "alg": "RS256", "use": "sig",
                "n": base64.urlsafe_b64encode(nb).rstrip(b"=").decode(), "e": "AQAB"}

    def sign(self, signing_input):
        return openssl("dgst", "-sha256", "-sign", self.pem, "-binary", data=signing_input)


def b64e(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def make_token(key, claims, kid=KID, alg="RS256"):
    h = b64e(json.dumps({"alg": alg, "kid": kid, "typ": "JWT"}).encode())
    p = b64e(json.dumps(claims).encode())
    sig = key.sign((h + "." + p).encode()) if alg == "RS256" else b""
    return h + "." + p + "." + b64e(sig)


def good_claims(**over):
    c = {"iss": ISS, "aud": AUD, "sub": "repo:o@%d/r@%d:ref:refs/heads/main" % (OWNER_ID, REPO_ID),
         "repository": REPO, "repository_id": str(REPO_ID), "repository_owner_id": str(OWNER_ID),
         "workflow_sha": HEAD, "job_workflow_sha": HEAD,
         "ref_type": "branch", "ref_protected": "true", "repository_visibility": "public",
         "runner_environment": "github-hosted",
         "ref": "refs/heads/main", "sha": HEAD, "run_id": str(RUN), "run_attempt": "1",
         "event_name": "workflow_dispatch",
         "workflow_ref": "%s/%s@refs/heads/main" % (REPO, WORKFLOW_PATH),
         "job_workflow_ref": "%s/%s@refs/heads/main" % (REPO, WORKFLOW_PATH),
         "iat": IAT, "exp": IAT + 300}
    c.update(over)
    return c


def api_run(**over):
    r = {"id": RUN, "path": WORKFLOW_PATH, "event": "workflow_dispatch", "status": "completed",
         "conclusion": "success", "head_branch": "main", "run_attempt": 1, "head_sha": HEAD,
         "run_started_at": START, "updated_at": END,
         "repository": {"full_name": REPO, "id": REPO_ID, "owner": {"id": OWNER_ID}},
         "head_repository": {"full_name": REPO}}
    r.update(over)
    return r


ARTIFACT = {"id": 777, "name": ARTIFACT_NAME, "workflow_run_id": RUN, "head_sha": HEAD,
            "created_at": ART_CREATED, "size_in_bytes": 200, "zip_sha256": "c" * 64}


def build_fixture(key, claims=None, ctx=None, run=None, token=None, manifest=None, extra=None):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "artifact"))
    os.makedirs(os.path.join(d, "api"))
    run = run or api_run()
    ctx = ctx if ctx is not None else {f: v for f, v in record_from_api(run).items()}
    open(os.path.join(d, "artifact", "context.json"), "w").write(json.dumps(ctx))
    open(os.path.join(d, "artifact", "oidc-token.jwt"), "w").write(
        token if token is not None else make_token(key, claims or good_claims()) + "\n")
    open(os.path.join(d, "api", "run.json"), "w").write(json.dumps(run))
    open(os.path.join(d, "api", "jobs.json"), "w").write(json.dumps({"jobs": [{"id": 55, "name": "me1-evidence"}]}))
    m = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch", "status": "completed",
         "conclusion": "success", "head_branch": "main", "run_attempt": 1, "previous_attempts": [],
         "run_id": RUN, "head_sha": HEAD, "repository": REPO,
         "attempt_window": {"start": START, "end": END}, "artifact": dict(ARTIFACT),
         "files": {rel: sha256_file(os.path.join(d, rel)) for rel in FETCHED}}
    m.update(manifest or {})
    json.dump(m, open(os.path.join(d, "manifest.json"), "w"))
    if extra:
        extra(d)
    return d


def selftest():
    if os.environ.get("ME1_SELFTEST_CHILD"):
        print("selftest started from inside a selftest (recursion guard)", file=sys.stderr)
        return 99
    bad = 0
    key, other = Key(), Key()

    def case(label, got, want):
        nonlocal bad
        ok = got == want
        print("%-4s %-60s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1

    BOUND, NOT = "EVIDENCE BOUND, P NOT READ", "EVIDENCE NOT BOUND (NOT MET)"
    tdir = tempfile.mkdtemp()  # the trust root lives OUTSIDE every evidence directory

    def jwks_file(obj, raw=None):
        pth = os.path.join(tdir, "jwks-%d.json" % len(os.listdir(tdir)))
        open(pth, "w").write(raw if raw is not None else json.dumps(obj))
        return pth

    TJ = jwks_file({"keys": [key.jwk()]})

    def ev(d, **kw):
        a = dict(expect_head=HEAD, expect_repo=REPO, expect_run_id=RUN, expect_attempt=1, trusted_jwks=TJ)
        a.update(kw)
        return overall(evaluate(d, **a))

    # --- RS256 verifier: the primitive itself can fail ---
    sig_in = b"abc.def"
    good_sig = key.sign(sig_in)
    case("RS256: valid signature", verify_rs256(sig_in, good_sig, key.jwk()), True)
    case("RS256: other message", verify_rs256(b"abc.deg", good_sig, key.jwk()), False)
    case("RS256: other key", verify_rs256(sig_in, good_sig, other.jwk()), False)
    case("RS256: flipped bit", verify_rs256(sig_in, bytes([good_sig[0] ^ 1]) + good_sig[1:], key.jwk()), False)
    case("RS256: truncated signature", verify_rs256(sig_in, good_sig[:-1], key.jwk()), False)
    case("RS256: tiny modulus refused", verify_rs256(sig_in, good_sig, {"n": "AQAB", "e": "AQAB"}), False)

    # --- positive control (U)/(J) ---
    pk = pk_rows()
    case("PK: every planted difference detected, identical not flagged", all(r[1] == "MET" for r in pk), True)
    case("PK: row count", len(pk), len(FIELDS) + 1)

    # --- evaluation ---
    case("good evidence: bound, only P not read", ev(build_fixture(key)), BOUND)
    # evidence of another run presented as this run's (S) and old/other attempt (R)
    case("S: evidence of another run (expect another run id)", ev(build_fixture(key), expect_run_id=RUN + 1), NOT)
    case("S: evidence of another repository", ev(build_fixture(key), expect_repo="o/other"), NOT)
    case("R: evidence of another head (expect another head)", ev(build_fixture(key), expect_head="b2" * 20), NOT)
    case("R: evidence of another attempt (expect attempt 2)", ev(build_fixture(key), expect_attempt=2), NOT)
    for field, val in (("run_id", "999"), ("run_attempt", "2"), ("sha", "b2" * 20), ("repository", "o/other"),
                       ("event_name", "pull_request"),
                       ("workflow_ref", "o/r/.github/workflows/other.yml@refs/heads/main")):
        case("claims: other %s" % field, ev(build_fixture(key, claims=good_claims(**{field: val}))), NOT)
    case("claims: other job_workflow_ref", ev(build_fixture(key, claims=good_claims(job_workflow_ref="o/r/.github/workflows/x.yml@refs/heads/main"))), NOT)
    case("claims: other ref", ev(build_fixture(key, claims=good_claims(ref="refs/pull/1/merge"))), NOT)
    case("claims: other subject", ev(build_fixture(key, claims=good_claims(sub="repo:o/r:environment:x"))), NOT)
    case("claims: other issuer", ev(build_fixture(key, claims=good_claims(iss="https://evil.example"))), NOT)
    case("claims: other audience", ev(build_fixture(key, claims=good_claims(aud="sts.amazonaws.com"))), NOT)
    case("claims: issued before the window", ev(build_fixture(key, claims=good_claims(iat=IAT - 3600, exp=IAT - 3000))), NOT)
    case("claims: issued after the window", ev(build_fixture(key, claims=good_claims(iat=IAT + 3600, exp=IAT + 4200))), NOT)
    case("claims: expiry before issue", ev(build_fixture(key, claims=good_claims(exp=IAT - 1))), NOT)
    case("claims: iat is not a number", ev(build_fixture(key, claims=good_claims(iat="x"))), NOT)
    case("claims: field missing", ev(build_fixture(key, claims={k: v for k, v in good_claims().items() if k != "sha"})), NOT)
    case("token signed by another key", ev(build_fixture(key, token=make_token(other, good_claims()))), NOT)
    case("token with an unknown kid", ev(build_fixture(key, token=make_token(key, good_claims(), kid="nope"))), NOT)
    case("token alg none", ev(build_fixture(key, token=make_token(key, good_claims(), alg="none"))), NOT)
    case("token alg HS256", ev(build_fixture(key, token=make_token(key, good_claims(), alg="HS256"))), NOT)
    case("token payload tampered after signing", ev(build_fixture(key, token=(lambda t: t.split(".")[0] + "." + b64e(json.dumps(good_claims(run_id="999")).encode()) + "." + t.split(".")[2])(make_token(key, good_claims())))), NOT)
    case("token not a JWT", ev(build_fixture(key, token="not a jwt\\n")), NOT)
    case("trusted JWKS without keys", ev(build_fixture(key), trusted_jwks=jwks_file({"keys": []})), NOT)
    case("trusted JWKS key of another type", ev(build_fixture(key), trusted_jwks=jwks_file({"keys": [dict(key.jwk(), kty="EC")]})), NOT)
    case("trusted JWKS has the kid twice", ev(build_fixture(key), trusted_jwks=jwks_file({"keys": [key.jwk(), key.jwk()]})), NOT)
    case("trusted JWKS holds only another issuer's key", ev(build_fixture(key), trusted_jwks=jwks_file({"keys": [other.jwk()]})), NOT)
    # F2: the trust root is separate from the evidence
    case("F2: trusted JWKS not given -> INCOMPLETE", ev(build_fixture(key), trusted_jwks=None), "INCOMPLETE (not read)")
    case("F2: trusted JWKS file does not exist", ev(build_fixture(key), trusted_jwks="/nonexistent/jwks.json"), NOT)
    case("F2: trusted JWKS is not JSON", ev(build_fixture(key), trusted_jwks=jwks_file(None, raw="<html>")), NOT)
    dj = build_fixture(key, extra=lambda d: open(os.path.join(d, "jwks.json"), "w").write(json.dumps({"keys": [key.jwk()]})))
    case("F2: the key file inside the evidence package is refused as trust root", ev(dj, trusted_jwks=os.path.join(dj, "jwks.json")), NOT)
    rows = evaluate(dj, HEAD, REPO, RUN, 1, os.path.join(dj, "jwks.json"))
    case("F2: ... and that very row is the one that fails",
         [r[1] for r in rows if r[0].startswith("trusted JWKS")], ["NOT-MET"])
    # a complete, internally consistent substitution of token + key + manifest inside the package
    da = build_fixture(other, token=make_token(other, good_claims()),
                       extra=lambda d: open(os.path.join(d, "jwks.json"), "w").write(json.dumps({"keys": [other.jwk()]})))
    case("F2: attacker replaces token, key and manifest inside the package (owner's trusted keys decide)", ev(da), NOT)
    case("F2: ... even when the attacker's key file is offered as the trust root", ev(da, trusted_jwks=os.path.join(da, "jwks.json")), NOT)
    # F3: the self-report never invalidates the signed evidence; it is a NOTE
    case("F3: self-report differs, signed evidence stands", ev(build_fixture(key, ctx=dict(record_from_api(api_run()), sha="b2" * 20))), BOUND)
    rows = evaluate(build_fixture(key, ctx=dict(record_from_api(api_run()), sha="b2" * 20)), HEAD, REPO, RUN, 1, TJ)
    case("F3: ... and the difference is reported as a NOTE", [r[1] for r in rows if r[0].startswith("self-report")], ["NOTE"])
    case("F3: self-report is not an object, signed evidence stands", ev(build_fixture(key, ctx=["x"])), BOUND)
    # F4: job_workflow_ref is not mandatory, a wrong one is still a failure
    case("F4: job_workflow_ref absent -> not a failed binding", ev(build_fixture(key, claims={k: v for k, v in good_claims().items() if k != "job_workflow_ref"})), BOUND)
    rows = evaluate(build_fixture(key, claims={k: v for k, v in good_claims().items() if k != "job_workflow_ref"}), HEAD, REPO, RUN, 1, TJ)
    case("F4: ... reported as a NOTE", [r[1] for r in rows if r[0] == "OIDC job_workflow_ref"], ["NOTE"])
    # F1: the token must have expired, by SERVER time, before the artifact existed
    case("F1: artifact created before the token expired", ev(build_fixture(key, manifest={"artifact": dict(ARTIFACT, created_at="2026-01-01T00:05:00Z")})), NOT)
    case("F1: artifact created 30 s after exp (margin 60 s)", ev(build_fixture(key, manifest={"artifact": dict(ARTIFACT, created_at="2026-01-01T00:05:40Z")})), NOT)
    case("F1: artifact created exactly at exp + 60 s", ev(build_fixture(key, manifest={"artifact": dict(ARTIFACT, created_at="2026-01-01T00:06:10Z")})), BOUND)
    case("F1: token exp missing", ev(build_fixture(key, claims={k: v for k, v in good_claims().items() if k != "exp"})), NOT)
    # --- the subject and the ID claims, measured on the real run (45063800073) ---
    def sub_case(label, claims_over=None, run=None, want=BOUND, drop=()):
        c = good_claims(**(claims_over or {}))
        for k in drop:
            c.pop(k, None)
        case(label, ev(build_fixture(key, claims=c, run=run or api_run())), want)

    sub_case("sub: the ID form with the API's IDs is accepted (the shape measured on the real run)")
    sub_case("sub: the documented plain form is still accepted", {"sub": "repo:%s:ref:refs/heads/main" % REPO})
    sub_case("sub: ID form, wrong repository id in the subject", {"sub": "repo:o@%d/r@%d:ref:refs/heads/main" % (OWNER_ID, REPO_ID + 1)}, want=NOT)
    sub_case("sub: ID form, wrong owner id in the subject", {"sub": "repo:o@%d/r@%d:ref:refs/heads/main" % (OWNER_ID + 1, REPO_ID)}, want=NOT)
    sub_case("sub: ID form, the two ids swapped", {"sub": "repo:o@%d/r@%d:ref:refs/heads/main" % (REPO_ID, OWNER_ID)}, want=NOT)
    sub_case("sub: ID form, ids not numeric", {"sub": "repo:o@x/r@y:ref:refs/heads/main"}, want=NOT)
    sub_case("sub: only the owner carries an id", {"sub": "repo:o@%d/r:ref:refs/heads/main" % OWNER_ID}, want=NOT)
    sub_case("sub: only the repository carries an id", {"sub": "repo:o/r@%d:ref:refs/heads/main" % REPO_ID}, want=NOT)
    sub_case("sub: trailing junk", {"sub": "repo:o@%d/r@%d:ref:refs/heads/main:x" % (OWNER_ID, REPO_ID)}, want=NOT)
    sub_case("sub: other repository name in the ID form", {"sub": "repo:o@%d/other@%d:ref:refs/heads/main" % (OWNER_ID, REPO_ID)}, want=NOT)
    sub_case("sub: environment subject", {"sub": "repo:o@%d/r@%d:environment:x" % (OWNER_ID, REPO_ID)}, want=NOT)
    sub_case("sub: missing", drop=("sub",), want=NOT)
    sub_case("sub: the API reports no ids, the ID form cannot be confirmed", run=api_run(repository={"full_name": REPO}), want=NOT)
    sub_case("id claims: repository_id differs from the API", {"repository_id": str(REPO_ID + 1)}, want=NOT)
    sub_case("id claims: repository_owner_id differs from the API", {"repository_owner_id": str(OWNER_ID + 1)}, want=NOT)
    sub_case("id claims: repository_id missing", drop=("repository_id",), want=NOT)
    sub_case("id claims: repository_owner_id missing", drop=("repository_owner_id",), want=NOT)
    sub_case("id claims: repository_id is a number, not the documented string", {"repository_id": REPO_ID}, want=NOT)
    sub_case("api: ids differ from the token's", run=api_run(repository={"full_name": REPO, "id": REPO_ID + 5, "owner": {"id": OWNER_ID}}), want=NOT)
    sub_case("workflow_sha differs from the head", {"workflow_sha": "b2" * 20}, want=NOT)
    sub_case("job_workflow_sha differs from the head", {"job_workflow_sha": "b2" * 20}, want=NOT)
    sub_case("workflow_sha absent: not mandatory", drop=("workflow_sha", "job_workflow_sha"))
    rows = evaluate(build_fixture(key, claims=good_claims(ref_protected="false", runner_environment="self-hosted")), HEAD, REPO, RUN, 1, TJ)
    case("informational claims are reported and never judged",
         ([r[1] for r in rows if r[0] == "OIDC informational claims"], overall(rows)), (["NOTE"], BOUND))
    # the claim SET of the real token (names and non-secret values read on run 45063800073; the signature here is synthetic)
    REAL = {"iss": ISS, "aud": AUD, "sub": "repo:o@%d/r@%d:ref:refs/heads/main" % (OWNER_ID, REPO_ID),
            "actor": "x", "actor_id": "1", "base_ref": "", "head_ref": "", "check_run_id": "137335381530",
            "event_name": "workflow_dispatch", "ref": "refs/heads/main", "ref_protected": "true", "ref_type": "branch",
            "repository": REPO, "repository_id": str(REPO_ID), "repository_owner": "o", "repository_owner_id": str(OWNER_ID),
            "repository_visibility": "public", "run_attempt": "1", "run_id": str(RUN), "run_number": "1",
            "runner_environment": "github-hosted", "sha": HEAD, "job_workflow_sha": HEAD, "workflow": "me1-evidence",
            "workflow_ref": "%s/%s@refs/heads/main" % (REPO, WORKFLOW_PATH), "workflow_sha": HEAD,
            "job_workflow_ref": "%s/%s@refs/heads/main" % (REPO, WORKFLOW_PATH),
            "iat": IAT, "exp": IAT + 300, "nbf": IAT - 300, "jti": "j"}
    case("the 31-claim shape of the real token is accepted (regression: the first real reading)",
         (len(REAL), ev(build_fixture(key, claims=REAL))), (31, BOUND))
    # API side
    dd = build_fixture(key, run=api_run(head_sha="c3" * 20))
    rows = evaluate(dd, HEAD, REPO, RUN, 1, TJ)
    case("API run JSON disagrees with the manifest (that very row fails)",
         [r[1] for r in rows if r[0].startswith("API metadata file agrees")], ["NOT-MET"])
    case("manifest missing", ev(build_fixture(key, extra=lambda d: os.remove(os.path.join(d, "manifest.json")))), NOT)
    case("a file changed after the manifest (stale mix)", ev(build_fixture(key, extra=lambda d: open(os.path.join(d, "artifact", "context.json"), "a").write(" "))), NOT)
    case("unlisted file in the directory", ev(build_fixture(key, extra=lambda d: open(os.path.join(d, "old.txt"), "w").write("x"))), NOT)
    case("token file missing", ev(build_fixture(key, extra=lambda d: os.remove(os.path.join(d, "artifact", "oidc-token.jwt")))), NOT)
    case("manifest: artifact created outside the window", ev(build_fixture(key, manifest={"artifact": dict(ARTIFACT, created_at="2025-01-01T00:00:00Z")})), NOT)
    case("manifest: other event", ev(build_fixture(key, manifest={"event": "push"})), NOT)
    case("manifest: other workflow path", ev(build_fixture(key, manifest={"workflow_path": ".github/workflows/lab-gate-pr.yml"})), NOT)
    case("manifest: attempt 2 without a held attempt 1", ev(build_fixture(key, manifest={"run_attempt": 2}), expect_attempt=2), NOT)
    # missing expectations are INCOMPLETE, never bound
    case("--expect-head-sha not given", ev(build_fixture(key), expect_head=None), "INCOMPLETE (not read)")
    case("--expect-repo not given", ev(build_fixture(key), expect_repo=None), "INCOMPLETE (not read)")
    case("--expect-run-id not given", ev(build_fixture(key), expect_run_id=None), "INCOMPLETE (not read)")
    case("--expect-attempt not given", ev(build_fixture(key), expect_attempt=None), "INCOMPLETE (not read)")

    # --- manifest writer ---
    A_OK = {"artifacts": [{"id": 777, "name": ARTIFACT_NAME, "expired": False, "created_at": ART_CREATED,
                           "size_in_bytes": 200, "workflow_run": {"id": RUN, "head_sha": HEAD}}]}

    def writer(run, att, prev, arts, zsha="c" * 64, head=HEAD):
        d = build_fixture(key, run=run)
        os.remove(os.path.join(d, "manifest.json"))
        pp, ap = os.path.join(d, "..", "p%d.json" % id(prev)), os.path.join(d, "..", "a%d.json" % id(arts))
        json.dump(prev, open(pp, "w"))
        json.dump(arts, open(ap, "w"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = write_manifest(d, REPO, head, att, pp, ap, zsha)
        return rc, d

    rc, d = writer(api_run(), 1, [], A_OK)
    case("writer: approved run", rc, 0)
    case("writer: the written manifest is accepted by the reader", ev(d), BOUND)
    case("writer: other head", writer(api_run(), 1, [], A_OK, head="b2" * 20)[0], 1)
    case("writer: push event", writer(api_run(event="push"), 1, [], A_OK)[0], 1)
    case("writer: failed run", writer(api_run(conclusion="failure"), 1, [], A_OK)[0], 1)
    case("writer: attempt 2 without history", writer(api_run(run_attempt=2), 2, [], A_OK)[0], 1)
    case("writer: attempt 2 after a held attempt 1", writer(api_run(run_attempt=2), 2, [HELD_ATTEMPT_1], A_OK)[0], 0)
    case("writer: artifact outside the window", writer(api_run(), 1, [], {"artifacts": [dict(A_OK["artifacts"][0], created_at="2025-01-01T00:00:00Z")]})[0], 1)
    case("writer: two artifacts inside the window", writer(api_run(), 1, [], {"artifacts": A_OK["artifacts"] * 2})[0], 1)
    case("writer: zip digest malformed", writer(api_run(), 1, [], A_OK, zsha="zz")[0], 1)

    # --- command-line entry points (real subprocess calls) ---
    def cli(*argv):
        p = subprocess.run([sys.executable, "-I", os.path.abspath(__file__)] + [str(a) for a in argv],
                           capture_output=True, text=True, env=dict(os.environ, ME1_SELFTEST_CHILD="1"))
        return p.returncode, p.stdout + p.stderr

    d = build_fixture(key)
    base = [d, "--trusted-jwks", TJ, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1, "--expect-head-sha", HEAD]
    rc, out = cli(*base)
    case("CLI evaluate: bound evidence, exit 0", (rc, "OVERALL: EVIDENCE BOUND, P NOT READ" in out), (0, True))
    case("CLI evaluate: wrong run id, exit 1", cli(d, "--trusted-jwks", TJ, "--expect-repo", REPO, "--expect-run-id", RUN + 1, "--expect-attempt", 1, "--expect-head-sha", HEAD)[0], 1)
    case("CLI evaluate: no --trusted-jwks, INCOMPLETE exit 1", cli(d, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1, "--expect-head-sha", HEAD)[0], 1)
    dj2 = build_fixture(key, extra=lambda dd_: open(os.path.join(dd_, "jwks.json"), "w").write(json.dumps({"keys": [key.jwk()]})))
    case("CLI evaluate: key file inside the evidence package, exit 1", cli(dj2, "--trusted-jwks", os.path.join(dj2, "jwks.json"), "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1, "--expect-head-sha", HEAD)[0], 1)
    case("CLI evaluate: flag without value, exit 2", cli(d, "--expect-repo")[0], 2)
    case("CLI evaluate: extra positional, exit 2", cli(*(base + ["extra"]))[0], 2)
    case("CLI evaluate: missing flag, INCOMPLETE exit 1", cli(d, "--trusted-jwks", TJ, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1)[0], 1)
    rc, out = cli("--pk")
    case("CLI --pk: exit 0", (rc, "NOT-MET" in out), (0, False))
    t = tempfile.mkdtemp()
    json.dump(api_run(), open(t + "/run.json", "w")); json.dump([], open(t + "/prev.json", "w")); json.dump(A_OK, open(t + "/arts.json", "w"))
    case("CLI check-run: approved", cli("--check-run", t + "/run.json", REPO, HEAD, 1, t + "/prev.json")[0], 0)
    case("CLI check-run: wrong head", cli("--check-run", t + "/run.json", REPO, "b2" * 20, 1, t + "/prev.json")[0], 1)
    case("CLI check-run: wrong repository", cli("--check-run", t + "/run.json", "o/other", HEAD, 1, t + "/prev.json")[0], 1)
    case("CLI check-run: missing argument", cli("--check-run", t + "/run.json", REPO, HEAD, 1)[0], 2)
    rc, out = cli("--pick-artifact", t + "/run.json", t + "/arts.json", HEAD)
    case("CLI pick-artifact: prints the id", (rc, out.strip()), (0, "777"))
    case("CLI pick-artifact: wrong head", cli("--pick-artifact", t + "/run.json", t + "/arts.json", "b2" * 20)[0], 1)
    d2 = build_fixture(key); os.remove(os.path.join(d2, "manifest.json"))
    case("CLI write-manifest: approved", cli("--write-manifest", d2, REPO, HEAD, 1, t + "/prev.json", t + "/arts.json", "c" * 64)[0], 0)
    case("CLI write-manifest: missing argument", cli("--write-manifest", d2, REPO, HEAD, 1, t + "/prev.json", t + "/arts.json")[0], 2)
    case("CLI --selftest mixed with another argument is refused", cli("--selftest", "extra")[0], 2)
    case("CLI --selftest mixed with a directory is refused", cli(d, "--selftest")[0], 2)

    print("SELFTEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        if argv[1:] != ["--selftest"]:
            print("refusing: --selftest must be the only argument", file=sys.stderr)
            return 2
        return selftest()
    args = argv[1:]
    if args == ["--pk"]:
        rows = pk_rows()
        report(rows)
        return 0 if all(r[1] == "MET" for r in rows) else 1
    for flag, n, fn in (("--write-manifest", 8, write_manifest), ("--check-run", 6, check_run_main),
                        ("--pick-artifact", 4, pick_artifact_main)):
        if args and args[0] == flag:
            if len(args) != n:
                print(__doc__, file=sys.stderr)
                return 2
            return fn(*args[1:])
    opts = {}
    for flag, key in (("--expect-head-sha", "expect_head"), ("--expect-repo", "expect_repo"),
                      ("--expect-run-id", "expect_run_id"), ("--expect-attempt", "expect_attempt"),
                      ("--trusted-jwks", "trusted_jwks")):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(__doc__, file=sys.stderr)
                return 2
            opts[key] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    res = evaluate(args[0], **opts)
    report(res)
    return 0 if overall(res).startswith("EVIDENCE BOUND") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
