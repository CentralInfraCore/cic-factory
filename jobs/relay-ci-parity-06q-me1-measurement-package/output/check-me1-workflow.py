#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Fail-closed check of the M-E1 measurement workflow (phase 1, evidence inventory).

  check-me1-workflow.py DIR            DIR holds the workflow files (exactly one: me1-evidence.yml)
  check-me1-workflow.py --selftest DIR conforming AND every planted deviation rejected

The package may contain exactly the one expected file. The whole parsed document, the whole `run`
body included, must equal the approved text; the key 'on' is read as text; duplicate keys are errors.
The ONE permission beyond contents:read is `id-token: write` (needed to request the OIDC token); it is
approved here deliberately, at JOB level only (the workflow level stays contents:read), and nothing else
may be added. The token is written to the artifact directory only after it is provably expired.
"""
import os
import re
import sys
import yaml

FILE = "me1-evidence.yml"
ACTION = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"

# Tokens that must not occur anywhere (comments included). `id-token: write` is NOT in the list:
# it is the one approved exception, enforced by whole-document equality instead.
FORBIDDEN = [
    "pull_request", "workflow_run", "issue_comment", "schedule", "environment", "self-hosted",
    "secrets.", "toJSON", "contents: write", "write-all", "secrets: inherit", "github.event.",
    "github.head_ref", "wget", "set-output", "GITHUB_ENV", "GITHUB_STEP_SUMMARY", "::notice",
    'echo "$ACTIONS', "cat me1/oidc", "tee ", "> me1/oidc-token.jwt\n          printf", "/dev/stderr",
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

RUN_EXPECTED = (
    'set -euo pipefail\n'
    'mkdir me1\n'
    'jq -n --arg repository "$GH_REPOSITORY" --arg run_id "$GH_RUN_ID" --arg run_attempt "$GH_RUN_ATTEMPT" --arg sha "$GH_SHA" --arg ref "$GH_REF" --arg workflow_ref "$GH_WORKFLOW_REF" --arg event_name "$GH_EVENT_NAME" \'{repository: $repository, run_id: $run_id, run_attempt: $run_attempt, sha: $sha, ref: $ref, workflow_ref: $workflow_ref, event_name: $event_name}\' > me1/context.json\n'
    'TOKEN=$(curl -sSf -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=me1-evidence" | jq -er .value)\n'
    'case "$TOKEN" in *.*.*) ;; *) echo "not a JWT" >&2; exit 1 ;; esac\n'
    'P=$(printf \'%s\' "$TOKEN" | cut -d. -f2 | tr \'_-\' \'/+\')\n'
    'EXP=$(printf \'%s%s\' "$P" "$(printf \'%*s\' $(( (4 - ${#P} % 4) % 4 )) \'\' | tr \' \' =)" | base64 -d | jq -er \'.exp | select(type == "number") | floor\')\n'
    'NOW=$(date +%s)\n'
    'WAIT=$((EXP + 121 - NOW))\n'
    'if [ "$WAIT" -gt 721 ]; then echo "token expiry too far" >&2; exit 1; fi\n'
    'if [ "$WAIT" -gt 0 ]; then sleep "$WAIT"; fi\n'
    'if [ "$(date +%s)" -le $((EXP + 120)) ]; then echo "token not provably expired" >&2; exit 1; fi\n'
    'printf \'%s\\n\' "$TOKEN" > me1/oidc-token.jwt\n'
)

EXPECTED = {
    "name": "me1-evidence",
    "on": {"workflow_dispatch": None},
    "permissions": {"contents": "read"},
    "jobs": {"me1-evidence": {
        "name": "me1-evidence", "runs-on": "ubuntu-24.04", "timeout-minutes": 20,
        "permissions": {"contents": "read", "id-token": "write"},
        "steps": [
            {"name": "me1 collect",
             "env": {
                 "GH_REPOSITORY": "${{ github.repository }}",
                 "GH_RUN_ID": "${{ github.run_id }}",
                 "GH_RUN_ATTEMPT": "${{ github.run_attempt }}",
                 "GH_SHA": "${{ github.sha }}",
                 "GH_REF": "${{ github.ref }}",
                 "GH_WORKFLOW_REF": "${{ github.workflow_ref }}",
                 "GH_EVENT_NAME": "${{ github.event_name }}"},
             "run": RUN_EXPECTED},
            {"name": "me1 artifact", "uses": ACTION,
             "with": {"name": "me1-evidence", "path": "me1",
                      "retention-days": 1, "if-no-files-found": "error"}},
        ],
    }},
}


def check_file(text, forbidden=None):
    errors = []
    for tok in (FORBIDDEN if forbidden is None else forbidden):
        if tok.lower() in text.lower():
            errors.append("forbidden token %r" % tok)
    try:
        doc = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        return errors + ["yaml error: %s" % exc]
    if doc != EXPECTED or repr(doc) != repr(EXPECTED):
        errors.append("parsed document differs from the expected document")
    return errors


def check_dir(files, forbidden=None):
    errors = []
    if sorted(files) != [FILE]:
        errors.append("file set differs: %s" % sorted(files))
    if FILE in files:
        errors += check_file(files[FILE], forbidden)
    return errors


def load(d):
    out = {}
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            out[os.path.relpath(p, d)] = open(p, encoding="utf-8").read()
    return out


def mutants(files):
    w = files[FILE]

    def with_(text):
        return {FILE: text}

    LAST = "          printf '%s\\n' \"$TOKEN\" > me1/oidc-token.jwt\n"
    yield "extra file", dict(files, **{"extra.yml": "name: x\n"})
    yield "missing file", {}
    yield "pull_request trigger", with_(w.replace("workflow_dispatch:", "pull_request:"))
    yield "extra trigger", with_(w.replace("on:\n  workflow_dispatch:", "on:\n  push:\n  workflow_dispatch:"))
    yield "id-token at workflow level", with_(w.replace("permissions:\n  contents: read\njobs:", "permissions:\n  contents: read\n  id-token: write\njobs:"))
    yield "id-token missing at job level", with_(w.replace("      id-token: write\n", ""))
    yield "id-token read", with_(w.replace("id-token: write", "id-token: read"))
    yield "contents write", with_(w.replace("contents: read", "contents: write"))
    yield "extra write permission", with_(w.replace("      id-token: write\n", "      id-token: write\n      actions: write\n"))
    yield "environment", with_(w.replace("    runs-on:", "    environment: canary-branch\n    runs-on:"))
    yield "secret reference", with_(w.replace("          GH_EVENT_NAME:", "          X: ${{ secrets.CANARY_UNRESTRICTED }}\n          GH_EVENT_NAME:"))
    yield "event data", with_(w.replace("GH_EVENT_NAME: ${{ github.event_name }}", "GH_EVENT_NAME: ${{ github.event.sender.login }}"))
    yield "unpinned action", with_(w.replace("@ea165f8d65b6e75b540449e92b4886f43607fa02", "@v4"))
    yield "other action", with_(w.replace("actions/upload-artifact@", "evil/upload-artifact@"))
    yield "other SHA", with_(w.replace("ea165f8d", "ea165f8e"))
    yield "other audience", with_(w.replace("audience=me1-evidence", "audience=sts.amazonaws.com"))
    # F1: the token must not reach the artifact before it is provably expired
    yield "no wait before publishing", with_(w.replace('          if [ "$WAIT" -gt 0 ]; then sleep "$WAIT"; fi\n', ""))
    yield "no check that the wait elapsed", with_(w.replace('          if [ "$(date +%s)" -le $((EXP + 120)) ]; then echo "token not provably expired" >&2; exit 1; fi\n', ""))
    yield "smaller safety margin", with_(w.replace("WAIT=$((EXP + 121 - NOW))", "WAIT=$((EXP + 1 - NOW))"))
    yield "F5: wait computed to the boundary only (exp + 120)", with_(w.replace("WAIT=$((EXP + 121 - NOW))", "WAIT=$((EXP + 120 - NOW))"))
    yield "F5: cap one second too low (720)", with_(w.replace('"$WAIT" -gt 721', '"$WAIT" -gt 720'))
    yield "no cap on the wait", with_(w.replace('          if [ "$WAIT" -gt 721 ]; then echo "token expiry too far" >&2; exit 1; fi\n', ""))
    yield "token written before the wait", with_(w.replace('          NOW=$(date +%s)\n', '          printf \'%s\\n\' "$TOKEN" > me1/oidc-token.jwt\n          NOW=$(date +%s)\n'))
    yield "jq without -e", with_(w.replace("jq -er .value", "jq -r .value"))
    yield "no JWT shape check", with_(w.replace('          case "$TOKEN" in *.*.*) ;; *) echo "not a JWT" >&2; exit 1 ;; esac\n', ""))
    yield "exp not required to be a number", with_(w.replace("select(type == \"number\") | floor", "floor"))
    yield "token printed to the log", with_(w.replace(LAST, LAST + "          cat me1/oidc-token.jwt\n"))
    yield "request token printed", with_(w.replace(LAST, LAST + "          echo \"$ACTIONS_ID_TOKEN_REQUEST_TOKEN\"\n"))
    yield "token teed to stderr", with_(w.replace("| jq -er .value)", "| tee /dev/stderr | jq -er .value)"))
    yield "harmless extra instruction", with_(w.replace(LAST, LAST + "          date\n"))
    yield "other request url", with_(w.replace('"$ACTIONS_ID_TOKEN_REQUEST_URL&audience=me1-evidence"', '"https://example.invalid/&audience=me1-evidence"'))
    yield "changed context field", with_(w.replace("run_attempt: $run_attempt", 'run_attempt: "1"'))
    yield "missing context field", with_(w.replace(", workflow_ref: $workflow_ref", ""))
    yield "no set -e", with_(w.replace("          set -euo pipefail\n", ""))
    yield "longer retention", with_(w.replace("retention-days: 1", "retention-days: 90"))
    yield "other timeout", with_(w.replace("timeout-minutes: 20", "timeout-minutes: 360"))
    yield "self-hosted", with_(w.replace("ubuntu-24.04", "self-hosted"))
    yield "other check name", with_(w.replace("name: me1-evidence\n    runs-on", "name: other\n    runs-on"))
    yield "second job", with_(w + "  second:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo x\n")
    yield "duplicate key", with_(w.replace("  contents: read\n", "  contents: read\n  contents: read\n", 1))
    yield "on written yes", with_(w.replace("\non:\n", "\nyes:\n"))
    yield "empty file", with_("")
    yield "not yaml", with_("a: [\n")


def main(argv):
    if argv[1:2] == ["--selftest"] and len(argv) == 3:
        selftest, target = True, argv[2]
    elif len(argv) == 2 and argv[1] != "--selftest":
        selftest, target = False, argv[1]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    files = load(target)
    errs = check_dir(files)
    for e in errs:
        print("FAIL:", e)
    if errs:
        return 1
    print("OK: %d file conforms" % len(files))
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
