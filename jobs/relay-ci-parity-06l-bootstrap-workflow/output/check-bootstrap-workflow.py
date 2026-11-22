#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Check the 4.6a bootstrap workflow against the binding constraints of the
phase 0 runbook (06k, 4.6a). Fail-closed: any deviation is an error.

  check-bootstrap-workflow.py FILE        check one file (exit 0 = conforms)
  check-bootstrap-workflow.py --selftest FILE
                                          check that FILE conforms AND that each
                                          planted deviation is rejected
"""
import sys
import yaml

CHECK_NAME = "lab-gate"
# Raw-text tokens that must not appear anywhere (comments included).
FORBIDDEN_TEXT = [
    "secrets", "environment", "uses:", "${{", "pull_request",
    "workflow_dispatch", "workflow_run", "canary", "env:", "github_token",
    "permissions: write", "write",
]


def check(text):
    errors = []
    low = text.lower()
    for tok in FORBIDDEN_TEXT:
        if tok in low:
            errors.append("forbidden token: %r" % tok)
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return ["yaml parse error: %s" % exc]
    if not isinstance(doc, dict):
        return ["top level is not a mapping"]
    # PyYAML (YAML 1.1) reads the key 'on' as boolean True.
    keys = {("on" if k is True else k) for k in doc}
    if keys != {"name", "on", "permissions", "jobs"} or len(keys) != len(doc):
        errors.append("top-level keys differ: %s" % sorted(map(str, doc)))
    on = doc.get("on", doc.get(True))
    if on != {"push": {"branches": ["main"]}}:
        errors.append("trigger is not exactly push to main: %r" % (on,))
    if doc.get("permissions") != {"contents": "read"}:
        errors.append("permissions is not exactly contents: read")
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or list(jobs) != [CHECK_NAME]:
        errors.append("jobs is not exactly one job with id %s" % CHECK_NAME)
        return errors
    job = jobs[CHECK_NAME]
    if set(job) != {"name", "runs-on", "timeout-minutes", "steps"}:
        errors.append("job keys differ: %s" % sorted(job))
    if job.get("name") != CHECK_NAME:
        errors.append("job name is not %s" % CHECK_NAME)
    steps = job.get("steps")
    if not isinstance(steps, list) or len(steps) != 1:
        errors.append("job must have exactly one step")
    else:
        step = steps[0]
        if set(step) != {"name", "run"}:
            errors.append("step keys differ: %s" % sorted(step))
    return errors


def mutants(text):
    """Planted deviations; each must be rejected."""
    yield "secret reference", text.replace('echo "lab-gate bootstrap, the check exists"', 'echo "${{ secrets.X }}"')
    yield "environment", text.replace("    runs-on:", "    environment: e\n    runs-on:")
    yield "extra trigger pull_request", text.replace("on:\n  push:", "on:\n  pull_request:\n  push:")
    yield "workflow_dispatch", text.replace("on:\n  push:", "on:\n  workflow_dispatch:\n  push:")
    yield "other branch", text.replace("[main]", "[main, dev]")
    yield "write permission", text.replace("contents: read", "contents: write")
    yield "no permissions", text.replace("permissions:\n  contents: read\n", "")
    yield "third-party action", text.replace("run: echo", "uses: x/y@v1\n        # run: echo")
    yield "wrong check name", text.replace("name: lab-gate\n", "name: other\n")
    yield "second job", text + "  second:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo x\n"
    yield "second step", text + "      - name: more\n        run: echo y\n"
    yield "empty file", ""
    yield "not yaml", "a: [\n"


def main(argv):
    selftest = "--selftest" in argv
    args = [a for a in argv[1:] if a != "--selftest"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    with open(args[0], encoding="utf-8") as fh:
        text = fh.read()
    errors = check(text)
    for e in errors:
        print("FAIL:", e)
    if errors:
        return 1
    print("OK: %s conforms" % args[0])
    if selftest:
        for label, m in mutants(text):
            if m == text:
                print("SELFTEST ERROR: mutant %r did not change the file" % label)
                return 1
            if not check(m):
                print("SELFTEST FAIL: mutant %r was accepted" % label)
                return 1
            print("rejected mutant: %s" % label)
        print("SELFTEST OK: %d mutants rejected" % len(list(mutants(text))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
