#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Mocked-GitHub test of fetch-me1.sh (no network, no lab access): a fake `gh` and a fake `curl` serve
canned answers, the fetch script runs for real, and read-me1.py reads what it produced.
Every refusal path must exit non-zero AND leave no manifest.   python3 -I test-fetch-me1.py"""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rm", os.path.join(HERE, "read-me1.py"))
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)

RUN, HEAD, REPO, JOB = rm.RUN, rm.HEAD, rm.REPO, 55
API = "repos/o/r/actions/runs/%d" % RUN
GH = r'''#!/bin/bash
f() { echo "$1" | sed 's#/#__#g'; }
[ "$1" = api ] || { echo "mock: unexpected gh $*" >&2; exit 1; }
p=$2; shift 2; q=""; [ "${1:-}" = --jq ] && q=$2
n=$(cat "$MOCK/.n_$(f "$p")" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$MOCK/.n_$(f "$p")"
case "$p" in */zip) cat "$MOCK/artifact.zip"; exit 0;; esac
file="$MOCK/$(f "$p").json"
[ -e "$MOCK/$(f "$p").v$n.json" ] && file="$MOCK/$(f "$p").v$n.json"
[ -e "$file" ] || { echo "mock: no fixture for $p" >&2; exit 1; }
if [ -n "$q" ]; then jq -r "$q" "$file"; else cat "$file"; fi
'''
CURL = r'''#!/bin/bash
[ -e "$MOCK/jwks.json" ] || exit 22
cat "$MOCK/jwks.json"
'''


def j(path, obj, mock, variant=None):
    name = path.replace("/", "__") + (".v%d" % variant if variant else "") + ".json"
    json.dump(obj, open(os.path.join(mock, name), "w"))


def run_obj(n, updated=rm.END, **over):
    return rm.api_run(run_attempt=n, updated_at=updated, **over)


def art(id_=777, created=rm.ART_CREATED, head=HEAD, run=RUN, expired=False):
    return {"id": id_, "name": rm.ARTIFACT_NAME, "expired": expired, "created_at": created,
            "size_in_bytes": 200, "workflow_run": {"id": run, "head_sha": head}}


PR_HEAD = "d4" * 20
MERGE_SHA = "e5" * 20


def pr_obj(**over):
    o = {"number": 7, "state": "open", "merged": False, "merge_commit_sha": MERGE_SHA,
         "head": {"sha": PR_HEAD, "ref": "p-probe"}, "base": {"ref": "main"}}
    for k, v in over.items():
        if k in ("head", "base") and isinstance(v, dict):
            o[k] = dict(o[k], **v)
        else:
            o[k] = v
    return o
def pr_entry(number=7, head_ref="p-probe", base_ref="main", head_sha=None):
    return {"number": number, "head": {"ref": head_ref, "sha": head_sha or PR_HEAD}, "base": {"ref": base_ref, "sha": HEAD}}


PR_OVER = {"event": "pull_request", "head_branch": "p-probe", "head_sha": PR_HEAD,
           "path": ".github/workflows/me1-evidence.yml", "pull_requests": [pr_entry()]}


def build(key, att, prev_jobs=0, artifacts=None, latest=None, claims=None, tweak=None, run_over=None, head=HEAD, listing=True, pr=None):
    mock = tempfile.mkdtemp()
    if pr is not None:
        j("repos/o/r/pulls/7", pr, mock)
    latest = att if latest is None else latest
    ro = run_over or {}
    j(API, run_obj(latest, **ro), mock)
    j(API + "/attempts/%d" % att, run_obj(att, **ro), mock)
    j(API + "/attempts/%d/jobs" % att, {"jobs": [{"id": JOB, "name": "me1-evidence"}]}, mock)
    if att == 2:
        j(API + "/attempts/1", {"run_attempt": 1, "status": "completed", "conclusion": "action_required"}, mock)
        j(API + "/attempts/1/jobs", {"jobs": [{"id": 1}] * prev_jobs}, mock)
    j(API + "/artifacts", {"artifacts": [art(head=head)] if artifacts is None else artifacts}, mock)
    if listing:
        j("repos/o/r/commits/%s/check-runs?per_page=100" % head,
          {"total_count": 1, "check_runs": [{"id": JOB, "name": "me1-evidence", "status": "completed", "conclusion": "success",
                                             "app": {"slug": "github-actions"}}]}, mock)
    c = claims or rm.good_claims(run_attempt=str(att), run_id=str(RUN), check_run_id=str(JOB), workflow_sha=HEAD, job_workflow_sha=HEAD)
    run = run_obj(att, **ro)
    with zipfile.ZipFile(os.path.join(mock, "artifact.zip"), "w") as z:
        z.writestr("context.json", json.dumps(rm.record_from_api(run)))
        z.writestr("oidc-token.jwt", rm.make_token(key, c) + "\n")
    json.dump({"keys": [key.jwk()]}, open(os.path.join(mock, "jwks.json"), "w"))  # served by the fake issuer
    if tweak:
        tweak(mock)
    return mock


def run_fetch(mock, att, pre_existing_out=False, profile=None, head=HEAD, pr=None):
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, ".cache", "ci-lab"))
    open(os.path.join(home, ".cache", "ci-lab", "env.sh"), "w").write("ORG=o\nX=r\nY=y\nexport ORG X Y\n")
    bindir = tempfile.mkdtemp()
    for name, body in (("gh", GH), ("curl", CURL)):
        p = os.path.join(bindir, name)
        open(p, "w").write(body)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    out = os.path.join(tempfile.mkdtemp(), "out")
    if pre_existing_out:
        os.makedirs(out)
    env = dict(os.environ, HOME=home, MOCK=mock, PATH=bindir + ":" + os.environ["PATH"])
    cmd = ["bash", os.path.join(HERE, "fetch-me1.sh"), str(RUN), out, head, str(att)] + ([profile] if profile else []) + ([str(pr)] if pr is not None else [])
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return p.returncode, out, p.stderr.strip().splitlines()[-1:]


def main():
    bad = 0
    key = rm.Key()

    def check(label, ok, note=""):
        nonlocal bad
        print("%-4s %-64s %s" % ("ok" if ok else "FAIL", label, note))
        bad += 0 if ok else 1

    tj = tempfile.mkdtemp()  # the trust root, OUTSIDE every evidence directory
    jf = os.path.join(tj, "jwks.json")
    json.dump({"keys": [key.jwk()]}, open(jf, "w"))
    for att in (1, 2):
        mock = build(key, att)
        rc, out, err = run_fetch(mock, att)
        check("attempt %d: fetch succeeds" % att, rc == 0, " ".join(err))
        check("attempt %d: the evidence directory holds no key file" % att, rc == 0 and not os.path.exists(os.path.join(out, "jwks.json")))
        if rc == 0:
            res = rm.overall(rm.evaluate(out, HEAD, REPO, RUN, att, jf))
            check("attempt %d: read-me1 gives EVIDENCE BOUND, P NOT READ" % att, res == "EVIDENCE BOUND, P NOT READ", res)
            check("attempt %d: other expected attempt is NOT MET" % att,
                  rm.overall(rm.evaluate(out, HEAD, REPO, RUN, 3 - att, jf)) == "EVIDENCE NOT BOUND (NOT MET)")

    # --- discovery: the checks-API listing is fetched into the evidence and listed in the manifest
    mock = build(key, 1)
    rc, out, err = run_fetch(mock, 1)
    man = json.load(open(os.path.join(out, "manifest.json"))) if rc == 0 else {"files": {}}
    check("the checks-API listing is fetched and digest-listed in the manifest", rc == 0 and "api/check-runs.json" in man["files"]
          and os.path.exists(os.path.join(out, "api", "check-runs.json")))
    pol = {"repository": REPO, "repository_id": rm.REPO_ID, "repository_owner_id": rm.OWNER_ID, "workflow_path": rm.WORKFLOW_PATH,
           "ref": "refs/heads/main", "event": "workflow_dispatch", "sha": HEAD, "workflow_sha": HEAD, "audience": rm.AUD,
           "discovery": "required", "pin": {"run_id": RUN, "run_attempt": 1, "check_run_id": JOB}}
    res = rm.overall(rm.evaluate(out, trusted_jwks=jf, policy=pol)) if rc == 0 else "fetch failed"
    check("end to end: the fetched package is accepted by the policy-mode verifier (pinned, discovery required)", res == "EVIDENCE BOUND, P NOT READ", res)
    # --- the pr profile: AUTHORIZATION of the PR head (PR object) kept apart from the OBSERVATION of the run's SHA fields
    mockp = build(key, 1, run_over=PR_OVER, head=PR_HEAD, pr=pr_obj())
    rc, out, err = run_fetch(mockp, 1, profile="pr", head=PR_HEAD, pr=7)
    manp = json.load(open(os.path.join(out, "manifest.json"))) if rc == 0 else {}
    check("pr profile: a pull_request run is fetched, the manifest records profile, observed path and head_branch",
          rc == 0 and manp.get("profile") == "pr" and manp.get("head_branch") == "p-probe" and manp.get("workflow_path") == PR_OVER["path"] and manp.get("event") == "pull_request", " ".join(err))
    check("pr profile: the PR object is fetched and digest-listed (the authorization source)", rc == 0 and "api/pr.json" in manp.get("files", {}))
    check("pr profile: the observed relations are RECORDED (run head equals the PR head here, recorded not assumed)",
          rc == 0 and manp.get("observed", {}).get("run_head_sha_equals_pr_head") is True and manp["observed"].get("pr_number") == 7, str(manp.get("observed")))
    check("F3 the run's PR link is recorded in the manifest (number, refs; the SHA inside is recorded, not asserted)",
          rc == 0 and manp.get("observed", {}).get("run_pull_requests", [{}])[0].get("number") == 7, str(manp.get("observed")))
    check("pr profile: the checks-API listing of the run's commit is fetched", rc == 0 and os.path.exists(os.path.join(out, "api", "check-runs.json")))
    # F2: the run's head_sha DIFFERS from the PR head (e.g. the merge commit). The measurement must be able to
    # OBSERVE exactly this deviation instead of failing on it: collected, the relation recorded as False.
    mockd = build(key, 1, run_over=dict(PR_OVER, head_sha=MERGE_SHA), head=MERGE_SHA, pr=pr_obj())
    rc, out, err = run_fetch(mockd, 1, profile="pr", head=PR_HEAD, pr=7)
    mand = json.load(open(os.path.join(out, "manifest.json"))) if rc == 0 else {}
    check("F2 the run's head_sha differs from the approved PR head: COLLECTED, the deviation is observed, not refused", rc == 0, " ".join(err))
    check("F2 ... the manifest records run_head_sha_equals_pr_head=False and equals_pr_merge_commit=True",
          rc == 0 and mand["observed"]["run_head_sha_equals_pr_head"] is False and mand["observed"]["run_head_sha_equals_pr_merge_commit"] is True, str(mand.get("observed")))
    check("F2 ... and the artifact and the listing are bound to the run's OWN head_sha (the manifest head_sha is the observed one)", rc == 0 and mand["head_sha"] == MERGE_SHA)
    mockp2 = build(key, 1, run_over=dict(PR_OVER, path=".github/workflows/me1-evidence.yml@refs/pull/7/merge"), head=PR_HEAD, pr=pr_obj())
    rc, out, err = run_fetch(mockp2, 1, profile="pr", head=PR_HEAD, pr=7)
    check("pr profile: a path with an @ref suffix is recorded verbatim (H7 is not asserted)", rc == 0 and json.load(open(os.path.join(out, "manifest.json")))["workflow_path"].endswith("@refs/pull/7/merge"))

    def refuse(label, mock, att, pre=False, **kw):
        rc, out, err = run_fetch(mock, att, pre, **kw)
        check("refused: " + label, rc != 0 and not os.path.exists(os.path.join(out, "manifest.json")),
              "rc=%d %s" % (rc, " ".join(err)[:70]))

    refuse("pr profile: the run is a workflow_dispatch run", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, event="workflow_dispatch"), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("pr profile: the run comes from main (not a probe branch)", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, head_branch="main"), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("pr profile: the run failed", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, conclusion="failure"), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the PR object's head.sha is not the approved PR head", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj(head={"sha": "a9" * 20})), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the PR's head.ref is not the probe branch", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj(head={"ref": "feature"})), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the PR's base is not main", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj(base={"ref": "dev"})), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the probe PR was merged", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj(merged=True)), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the PR object cannot be read", build(key, 1, head=PR_HEAD, run_over=PR_OVER), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F2 authorization: the PR object has no number", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr={k: v for k, v in pr_obj().items() if k != "number"}), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("pr profile: the PR number is missing", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj()), 1, profile="pr", head=PR_HEAD)
    refuse("pr profile: the PR number is not numeric", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr="x")
    refuse("main profile: a PR number is given (it belongs to the pr profile only)", build(key, 1), 1, profile="main", pr=7)
    # F3: the RUN must be tied to the approved PR by the API's own metadata of the run, and the PR object read
    # back must be THE PR that was asked for
    refuse("F3 the PR object read back has another number than the one asked for (PR 7 asked, object says 8)", build(key, 1, head=PR_HEAD, run_over=PR_OVER, pr=pr_obj(number=8)), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run belongs to ANOTHER pull request (approved PR 7, the run's pull_requests names 9)", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[pr_entry(number=9)]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run carries NO pull_requests (empty list): the link is not established, fail-closed", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run has no pull_requests key at all: fail-closed", build(key, 1, head=PR_HEAD, run_over={k: v for k, v in PR_OVER.items() if k != "pull_requests"}, pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the pull_requests value is not a list: fail-closed", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests={"number": 7}), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run is associated with two pull requests (the approved one and another): ambiguous, fail-closed", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[pr_entry(7), pr_entry(9)]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run's pull_requests entry has no numeric number", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[{"head": {"ref": "p-probe"}, "base": {"ref": "main"}}]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run's PR entry names another head branch", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[pr_entry(head_ref="feature")]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("F3 the run's PR entry names another base branch", build(key, 1, head=PR_HEAD, run_over=dict(PR_OVER, pull_requests=[pr_entry(base_ref="dev")]), pr=pr_obj()), 1, profile="pr", head=PR_HEAD, pr=7)
    refuse("main profile: a pull_request run is presented", build(key, 1, run_over=PR_OVER, head=HEAD), 1)
    refuse("unknown profile", build(key, 1), 1, profile="weird")
    refuse("the checks-API listing cannot be read (no silent skip)", build(key, 1, listing=False), 1)
    refuse("a later attempt exists (current 3, fetching 2)", build(key, 2, latest=3), 2)
    refuse("current attempt differs from the asked one", build(key, 1, latest=2), 1)
    refuse("attempt changes while fetching", build(key, 2, tweak=lambda m: j(API, run_obj(3), m, variant=2)), 2)
    refuse("attempt object updated while fetching", build(key, 2, tweak=lambda m: j(API + "/attempts/2", run_obj(2, updated="2026-01-01T00:00:59Z"), m, variant=2)), 2)
    refuse("attempt 1 of attempt 2 had a job", build(key, 2, prev_jobs=1), 2)
    refuse("artifact created before the window", build(key, 1, artifacts=[art(created="2025-12-31T23:00:00Z")]), 1)
    refuse("artifact created after the window", build(key, 1, artifacts=[art(created="2026-01-01T00:30:00Z")]), 1)
    refuse("artifact of another head", build(key, 1, artifacts=[art(head="b2" * 20)]), 1)
    refuse("two artifacts inside the window", build(key, 1, artifacts=[art(), art(id_=778)]), 1)
    refuse("no artifact", build(key, 1, artifacts=[]), 1)
    refuse("attempt 3 asked for", build(key, 2), 3)
    refuse("output directory exists", build(key, 1), 1, pre=True)
    # a token that does not verify is fetched but the READER refuses it
    other_keys = os.path.join(tj, "other.json")
    json.dump({"keys": [rm.Key().jwk()]}, open(other_keys, "w"))
    mock = build(key, 1)
    rc, out, err = run_fetch(mock, 1)
    res = rm.overall(rm.evaluate(out, HEAD, REPO, RUN, 1, other_keys)) if rc == 0 else "fetch failed"
    check("keys of another issuer as trust root: the reader says NOT MET", res == "EVIDENCE NOT BOUND (NOT MET)", res)
    mock = build(key, 1, claims=rm.good_claims(sha="b2" * 20))
    rc, out, err = run_fetch(mock, 1)
    res = rm.overall(rm.evaluate(out, HEAD, REPO, RUN, 1, jf)) if rc == 0 else "fetch failed"
    check("claims of another commit: fetched, the reader says NOT MET", res == "EVIDENCE NOT BOUND (NOT MET)", res)
    # --- fetch-jwks.sh: the trust root is fetched into ONE new file, only if it looks like a JWKS ---
    def jwks_run(body, pre_existing=False):
        bindir = tempfile.mkdtemp()
        p = os.path.join(bindir, "curl")
        open(p, "w").write("#!/bin/bash\n" + body)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        out = os.path.join(tempfile.mkdtemp(), "jwks.json")
        if pre_existing:
            open(out, "w").write("old")
        r = subprocess.run(["bash", os.path.join(HERE, "fetch-jwks.sh"), out],
                           env=dict(os.environ, PATH=bindir + ":" + os.environ["PATH"]), capture_output=True, text=True)
        return r.returncode, out

    rc, out = jwks_run('echo \'{"keys":[{"kid":"a"}]}\'')
    check("fetch-jwks: a JWKS is kept", rc == 0 and os.path.exists(out))
    for label, body in (("curl fails", "exit 22"), ("not JSON", "echo '<html>'"), ("no keys array", "echo '{}'"),
                        ("empty keys", "echo '{\"keys\":[]}'"), ("a list instead of an object", "echo '[1]'")):
        rc, out = jwks_run(body)
        check("fetch-jwks refused: " + label, rc != 0 and not os.path.exists(out))
    rc, out = jwks_run("echo '{\"keys\":[{}]}'", pre_existing=True)
    check("fetch-jwks refused: output file exists (and is left untouched)", rc != 0 and open(out).read() == "old")
    print("TEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
