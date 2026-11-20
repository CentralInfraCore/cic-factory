#!/usr/bin/env python3
"""Integrity check for the scratch repo. Runs from the BASE checkout (pull_request_target).

It treats the pull request strictly as data (GitHub API); it never checks out or executes PR code.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

import yaml

REPO = os.environ["REPO"]
PR = os.environ["PR_NUMBER"]
HEAD = os.environ["HEAD_SHA"]
BASE = os.environ.get("BASE_SHA", "")
APPROVAL = re.compile(r"^APPROVE-PROTECTED head=([0-9a-f]{40}) digest=sha256:([0-9a-f]{64})[ \t\r]*$", re.M)


def api(path, raw=False):
    cmd = ["gh", "api", "--paginate", path] if not raw else ["gh", "api", "-H", "Accept: application/vnd.github.raw+json", path]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    if raw:
        return out
    # --paginate concatenates JSON arrays
    return json.loads(out.replace("][", ","))


def deny(msg):
    print(f"DENY: {msg}")
    sys.exit(1)


def main():
    policy_text = open("policy.json", encoding="utf-8").read()
    policy = json.loads(policy_text)
    pdigest = hashlib.sha256(policy_text.encode()).hexdigest()
    print(f"base={BASE} head={HEAD} policy-digest=sha256:{pdigest}")
    files = api(f"repos/{REPO}/pulls/{PR}/files")
    changed = sorted(f"{f['status']} {f['filename']} {f.get('sha')}" for f in files
                     if any(f["filename"].startswith(p) for p in policy["protected"]))
    if not changed:
        print("UNCHANGED: no protected path touched")
        return
    digest = hashlib.sha256("\n".join(changed).encode()).hexdigest()
    print("protected paths changed:\n  " + "\n  ".join(changed))
    comments = api(f"repos/{REPO}/issues/{PR}/comments")
    ok = False
    for c in comments:
        if c["user"]["login"] not in policy["approvers"]:
            continue
        for m in APPROVAL.finditer(c["body"]):
            if m.group(1) == HEAD and m.group(2) == digest:
                ok = True
    if not ok:
        deny(f"protected paths changed without a head- and digest-bound approval (head={HEAD} digest=sha256:{digest})")
    # approval is authorization only: the changed workflow must still conform
    wf = yaml.safe_load(api(f"repos/{REPO}/contents/.github/workflows/ci.yml?ref={HEAD}", raw=True))
    job = (wf.get("jobs") or {}).get("verify")
    on = wf.get(True) or wf.get("on") or {}
    if job is None:
        deny("conformance: job 'verify' missing in head ci.yml")
    if "if" in job or "continue-on-error" in job or "needs" in job:
        deny("conformance: job 'verify' is conditional")
    if not any("scripts/check.sh" in (s.get("run") or "") for s in job.get("steps", [])):
        deny("conformance: job 'verify' does not run scripts/check.sh")
    pr = on.get("pull_request") if isinstance(on, dict) else None
    if isinstance(on, dict) and ("pull_request" not in on or (pr or {}).get("paths") or (pr or {}).get("branches")):
        deny("conformance: pull_request trigger missing or filtered")
    print("APPROVED_UPDATE: approval valid and head ci.yml conforms")


main()
