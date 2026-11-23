#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Dry-run test of the me1-evidence `run` body (no network): fake curl/date/sleep. The token must be
written to the artifact directory ONLY after it is provably expired; every unusable case must exit
non-zero and leave no token file.   python3 -I test-me1-body.py [WORKFLOW_FILE]"""
import base64
import json
import os
import stat
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "..", "payload", ".github", "workflows", "me1-evidence.yml")
T0 = 1_800_000_000


def b64e(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def jwt(claims):
    return b64e(b'{"alg":"RS256","kid":"k"}') + "." + b64e(json.dumps(claims).encode()) + "." + b64e(b"sig")


def run_case(body, curl_out, date_values, sim=False):
    """sim=True: a SIMULATED clock, date = T0 + the total slept so far (sleep advances it exactly)."""
    t = tempfile.mkdtemp()
    open(os.path.join(t, "body.sh"), "w").write(body)
    bindir = os.path.join(t, "bin")
    os.mkdir(bindir)
    shims = {
        "curl": '#!/bin/bash\ncat "$SHIM_DIR/curl.out"\n',
        "sleep": '#!/bin/bash\necho "$1" >> "$SHIM_DIR/sleep.log"\nslept=$(cat "$SHIM_DIR/slept" 2>/dev/null || echo 0)\necho $((slept + $1)) > "$SHIM_DIR/slept"\n',
        "date": ('#!/bin/bash\necho $(( $(sed -n 1p "$SHIM_DIR/date.values") + $(cat "$SHIM_DIR/slept" 2>/dev/null || echo 0) ))\n' if sim else
                 '#!/bin/bash\nn=$(cat "$SHIM_DIR/date.n" 2>/dev/null || echo 0)\necho $((n+1)) > "$SHIM_DIR/date.n"\nsed -n "$((n+1))p" "$SHIM_DIR/date.values"\n'),
    }
    for name, text in shims.items():
        p = os.path.join(bindir, name)
        open(p, "w").write(text)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    open(os.path.join(t, "curl.out"), "w").write(curl_out)
    open(os.path.join(t, "date.values"), "w").write("\n".join(str(v) for v in date_values) + "\n")
    env = dict(os.environ, PATH=bindir + ":" + os.environ["PATH"], SHIM_DIR=t,
               GH_REPOSITORY="o/r", GH_RUN_ID="5", GH_RUN_ATTEMPT="1", GH_SHA="a" * 40,
               GH_REF="refs/heads/main", GH_WORKFLOW_REF="o/r/.github/workflows/me1-evidence.yml@refs/heads/main",
               GH_EVENT_NAME="workflow_dispatch", ACTIONS_ID_TOKEN_REQUEST_TOKEN="x",
               ACTIONS_ID_TOKEN_REQUEST_URL="https://x/?a=1")
    w = os.path.join(t, "w")
    os.mkdir(w)
    p = subprocess.run(["bash", os.path.join(t, "body.sh")], cwd=w, env=env, capture_output=True, text=True)
    sl = open(os.path.join(t, "sleep.log")).read().split() if os.path.exists(os.path.join(t, "sleep.log")) else []
    tok = os.path.join(w, "me1", "oidc-token.jwt")
    return p.returncode, sl, (open(tok).read().strip() if os.path.exists(tok) else None), p.stdout + p.stderr


def main():
    wf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    doc = yaml.safe_load(open(wf))
    body = doc["jobs"]["me1-evidence"]["steps"][0]["run"]
    bad = 0

    def check(label, ok, note=""):
        nonlocal bad
        print("%-4s %-62s %s" % ("ok" if ok else "FAIL", label, note))
        bad += 0 if ok else 1

    exp = T0 + 300
    good = json.dumps({"value": jwt({"exp": exp, "iat": T0})}) + "\n"
    rc, sl, tok, out = run_case(body, good, [T0, exp + 121])
    check("normal: waits exp+121-now, then publishes", rc == 0 and sl == [str(300 + 121)] and tok == jwt({"exp": exp, "iat": T0}), "sleep %s" % sl)
    rc, sl, tok, out = run_case(body, good, [T0, exp + 120])
    check("clock after the wait not past exp+120 -> no token (strict check unchanged)", rc != 0 and tok is None)
    # F5: the clock advances by EXACTLY the slept time; a normal run must not be refused at the boundary
    for delta in (1, 2, 119, 120, 121, 300, 599, 600):
        c = json.dumps({"value": jwt({"exp": T0 + delta})}) + "\n"
        rc, sl, tok, out = run_case(body, c, [T0], sim=True)
        check("F5: simulated clock, exp - now = %d s -> published" % delta, rc == 0 and tok is not None and sl == [str(delta + 121)], "sleep %s" % sl)
    c = json.dumps({"value": jwt({"exp": T0 + 601})}) + "\n"
    rc, sl, tok, out = run_case(body, c, [T0], sim=True)
    check("F5: exp - now = 601 s -> refused (cap at the exact boundary), no sleep, no token", rc != 0 and tok is None and sl == [])
    rc, sl, tok, out = run_case(body, good, [T0, T0 + 5])
    check("clock did not advance (shim) -> no token", rc != 0 and tok is None)
    far = json.dumps({"value": jwt({"exp": T0 + 4000})}) + "\n"
    rc, sl, tok, out = run_case(body, far, [T0, T0 + 99999])
    check("expiry too far (> 600 s) -> fail closed, no sleep, no token", rc != 0 and tok is None and sl == [])
    past = json.dumps({"value": jwt({"exp": T0 - 1000})}) + "\n"
    rc, sl, tok, out = run_case(body, past, [T0, T0 + 1])
    check("already expired long ago: no wait, publishes", rc == 0 and sl == [] and tok is not None)
    for label, claims in (("exp missing", {"iat": T0}), ("exp not a number", {"exp": "soon"}), ("exp null", {"exp": None})):
        rc, sl, tok, out = run_case(body, json.dumps({"value": jwt(claims)}) + "\n", [T0, T0 + 99999])
        check("%s -> fail closed, no token" % label, rc != 0 and tok is None)
    for label, text in (("value null", '{"value": null}\n'), ("value missing", "{}\n"), ("not JSON", "<html>\n"),
                        ("not a JWT", '{"value": "abc"}\n'), ("empty", "")):
        rc, sl, tok, out = run_case(body, text, [T0, T0 + 99999])
        check("curl answer %s -> fail closed, no token" % label, rc != 0 and tok is None)
    rc, sl, tok, out = run_case(body, good, [T0, exp + 121])
    check("the token never appears in the step's own output", jwt({"exp": exp, "iat": T0}) not in out)
    print("TEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
