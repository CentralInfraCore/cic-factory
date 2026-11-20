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

REPO = os.environ.get("REPO", "")
PR = os.environ.get("PR_NUMBER", "")
HEAD = os.environ.get("HEAD_SHA", "")
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


API_FILE_LIMIT = 3000   # GitHub lists at most 3000 files of a pull request
PAGE_SIZE = 100


class IncompleteChangeset(Exception):
    """The list of changed files cannot be proven complete: the decision must fail closed."""


def load_changeset(get_pr, get_files_page, head_sha):
    """Return the complete list of changed files, or raise IncompleteChangeset.

    Fails closed when: the API call fails, the head moved, the pull request reaches the API
    listing limit, the pagination does not terminate, or the number of listed files differs from
    the pull request's own changed_files counter.
    """
    try:
        pr = get_pr()
    except Exception as e:  # any API failure
        raise IncompleteChangeset(f"pull request lookup failed: {type(e).__name__}") from e
    if pr.get("head", {}).get("sha") != head_sha:
        raise IncompleteChangeset("the pull request head moved during the check")
    expected = pr.get("changed_files")
    if not isinstance(expected, int) or expected < 0:
        raise IncompleteChangeset("changed_files is missing or invalid")
    if expected >= API_FILE_LIMIT:
        raise IncompleteChangeset(f"changed_files={expected} reaches the API listing limit {API_FILE_LIMIT}")
    files, page = [], 1
    while True:
        try:
            batch = get_files_page(page)
        except Exception as e:
            raise IncompleteChangeset(f"files page {page} failed: {type(e).__name__}") from e
        files.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        if page > API_FILE_LIMIT // PAGE_SIZE + 1:
            raise IncompleteChangeset("pagination did not terminate")
    if len(files) != expected:
        raise IncompleteChangeset(f"listed {len(files)} files but changed_files={expected}")
    return files


def protected_changes(files, protected):
    """Return the sorted change records that touch a protected path.

    A file counts as touching the protected set when EITHER its new name (filename) OR its old
    name (previous_filename, present for renames/copies) is protected. Both names go into the
    record, so the approval digest binds the full move, not only the destination.
    """
    out = []
    for f in files:
        names = [f["filename"]]
        if f.get("previous_filename"):
            names.append(f["previous_filename"])
        if any(n.startswith(p) for n in names for p in protected):
            out.append(f"{f['status']} {f.get('previous_filename') or '-'} -> {f['filename']} {f.get('sha')}")
    return sorted(out)


def main():
    policy_text = open("policy.json", encoding="utf-8").read()
    policy = json.loads(policy_text)
    pdigest = hashlib.sha256(policy_text.encode()).hexdigest()
    print(f"base={BASE} head={HEAD} policy-digest=sha256:{pdigest}")
    try:
        files = load_changeset(
            lambda: json.loads(subprocess.run(["gh", "api", f"repos/{REPO}/pulls/{PR}"], check=True,
                                              capture_output=True, text=True).stdout),
            lambda n: json.loads(subprocess.run(["gh", "api", f"repos/{REPO}/pulls/{PR}/files?per_page={PAGE_SIZE}&page={n}"],
                                                check=True, capture_output=True, text=True).stdout),
            HEAD,
        )
    except IncompleteChangeset as e:
        deny(f"INCOMPLETE_CHANGESET: {e}")
    changed = protected_changes(files, policy["protected"])
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


if __name__ == "__main__":
    main()
