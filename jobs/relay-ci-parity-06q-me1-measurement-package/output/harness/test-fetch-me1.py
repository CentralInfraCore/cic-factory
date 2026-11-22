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


def build(key, att, prev_jobs=0, artifacts=None, latest=None, claims=None, tweak=None):
    mock = tempfile.mkdtemp()
    latest = att if latest is None else latest
    j(API, run_obj(latest), mock)
    j(API + "/attempts/%d" % att, run_obj(att), mock)
    j(API + "/attempts/%d/jobs" % att, {"jobs": [{"id": JOB, "name": "me1-evidence"}]}, mock)
    if att == 2:
        j(API + "/attempts/1", {"run_attempt": 1, "status": "completed", "conclusion": "action_required"}, mock)
        j(API + "/attempts/1/jobs", {"jobs": [{"id": 1}] * prev_jobs}, mock)
    j(API + "/artifacts", {"artifacts": [art()] if artifacts is None else artifacts}, mock)
    c = claims or rm.good_claims(run_attempt=str(att))
    run = run_obj(att)
    with zipfile.ZipFile(os.path.join(mock, "artifact.zip"), "w") as z:
        z.writestr("context.json", json.dumps(rm.record_from_api(run)))
        z.writestr("oidc-token.jwt", rm.make_token(key, c) + "\n")
    json.dump({"keys": [key.jwk()]}, open(os.path.join(mock, "jwks.json"), "w"))  # served by the fake issuer
    if tweak:
        tweak(mock)
    return mock


def run_fetch(mock, att, pre_existing_out=False):
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
    p = subprocess.run(["bash", os.path.join(HERE, "fetch-me1.sh"), str(RUN), out, HEAD, str(att)],
                       env=env, capture_output=True, text=True)
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

    def refuse(label, mock, att, pre=False):
        rc, out, err = run_fetch(mock, att, pre)
        check("refused: " + label, rc != 0 and not os.path.exists(os.path.join(out, "manifest.json")),
              "rc=%d %s" % (rc, " ".join(err)[:70]))

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
