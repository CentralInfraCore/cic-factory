#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Fail-closed check of the P1/P2 probe workflows (M-E1 P-a/P-b measurement package).

  check-me1-p-workflows.py DIR            DIR holds the probe files (exactly two)
  check-me1-p-workflows.py --selftest DIR conforming AND every planted deviation rejected

The package may contain exactly the two expected files:
  me1-evidence.yml       P1: the protected workflow modified IN PLACE (a pull_request trigger added)
  me1-evidence-twin.yml  P2: a NEW workflow with the SAME `name:` and job name
Both carry the reviewed, expiry-gated token step unchanged, the SAME audience (me1-evidence), no secret,
no environment, no network beyond the runner's own token endpoint. The whole parsed document, the whole
`run` body included, must equal the approved text; `on` is read as text; duplicate keys are errors.
The ONE permission beyond contents:read is `id-token: write`, at JOB level only.
These files are NEVER merged: they travel in a throwaway pull request that the owner closes.
"""
import os
import re
import sys
import yaml

FILES = ["me1-evidence.yml", "me1-evidence-twin.yml"]
ACTION = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"

# Tokens that must not occur anywhere (comments included). `pull_request` itself is the point of these files.
FORBIDDEN = [
    "pull_request_target", "workflow_run", "issue_comment", "schedule", "environment", "self-hosted",
    "secrets.", "toJSON", "contents: write", "write-all", "secrets: inherit", "github.event.",
    "github.head_ref", "wget", "set-output", "GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY",
    "::notice", 'echo "$ACTIONS', "cat me1/oidc", "tee ", "/dev/stderr", "gh api", "gh pr",
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
    "me1-evidence.yml": {'name': 'me1-evidence',
 'on': {'pull_request': {'branches': ['main']}, 'workflow_dispatch': None},
 'permissions': {'contents': 'read'},
 'jobs': {'me1-evidence': {'name': 'me1-evidence',
                           'runs-on': 'ubuntu-24.04',
                           'timeout-minutes': 20,
                           'permissions': {'contents': 'read', 'id-token': 'write'},
                           'steps': [{'name': 'me1 collect',
                                      'env': {'GH_REPOSITORY': '${{ github.repository }}',
                                              'GH_RUN_ID': '${{ github.run_id }}',
                                              'GH_RUN_ATTEMPT': '${{ github.run_attempt }}',
                                              'GH_SHA': '${{ github.sha }}',
                                              'GH_REF': '${{ github.ref }}',
                                              'GH_WORKFLOW_REF': '${{ github.workflow_ref }}',
                                              'GH_EVENT_NAME': '${{ github.event_name }}'},
                                      'run': RUN_EXPECTED},
                                     {'name': 'me1 artifact',
                                      'uses': 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
                                      'with': {'name': 'me1-evidence',
                                               'path': 'me1',
                                               'retention-days': 1,
                                               'if-no-files-found': 'error'}}]}}},
    "me1-evidence-twin.yml": {'name': 'me1-evidence',
 'on': {'pull_request': {'branches': ['main']}},
 'permissions': {'contents': 'read'},
 'jobs': {'me1-evidence': {'name': 'me1-evidence',
                           'runs-on': 'ubuntu-24.04',
                           'timeout-minutes': 20,
                           'permissions': {'contents': 'read', 'id-token': 'write'},
                           'steps': [{'name': 'me1 collect',
                                      'env': {'GH_REPOSITORY': '${{ github.repository }}',
                                              'GH_RUN_ID': '${{ github.run_id }}',
                                              'GH_RUN_ATTEMPT': '${{ github.run_attempt }}',
                                              'GH_SHA': '${{ github.sha }}',
                                              'GH_REF': '${{ github.ref }}',
                                              'GH_WORKFLOW_REF': '${{ github.workflow_ref }}',
                                              'GH_EVENT_NAME': '${{ github.event_name }}'},
                                      'run': RUN_EXPECTED},
                                     {'name': 'me1 artifact',
                                      'uses': 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',
                                      'with': {'name': 'me1-evidence',
                                               'path': 'me1',
                                               'retention-days': 1,
                                               'if-no-files-found': 'error'}}]}}},
}


def check_file(name, text, forbidden=None):
    errors = []
    for tok in (FORBIDDEN if forbidden is None else forbidden):
        if tok.lower() in text.lower():
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
            out[os.path.relpath(p, d)] = open(p, encoding="utf-8").read()
    return out


def mutants(files):
    a, b = files["me1-evidence.yml"], files["me1-evidence-twin.yml"]
    LAST = "          printf '%s\\n' \"$TOKEN\" > me1/oidc-token.jwt\n"

    def both(fn, label):
        # the same deviation planted in each file separately
        yield label + " (P1)", dict(files, **{"me1-evidence.yml": fn(a)})
        yield label + " (P2)", dict(files, **{"me1-evidence-twin.yml": fn(b)})

    yield "extra file", dict(files, **{"extra.yml": "name: x\n"})
    yield "missing P1", {k: v for k, v in files.items() if k != "me1-evidence.yml"}
    yield "missing P2", {k: v for k, v in files.items() if k != "me1-evidence-twin.yml"}
    yield "P1 loses the pull_request trigger", dict(files, **{"me1-evidence.yml": a.replace("  pull_request:\n    branches: [main]\n", "")})
    yield "P2 gains workflow_dispatch", dict(files, **{"me1-evidence-twin.yml": b.replace("  pull_request:\n    branches: [main]\n", "  pull_request:\n    branches: [main]\n  workflow_dispatch:\n")})
    yield "P2 name differs from the protected workflow", dict(files, **{"me1-evidence-twin.yml": b.replace("name: me1-evidence\non:", "name: me1-evidence-twin\non:")})
    yield "P2 job name differs", dict(files, **{"me1-evidence-twin.yml": b.replace("    name: me1-evidence\n", "    name: other\n")})
    for lab, fn in (
        ("pull_request_target", lambda t: t.replace("pull_request:", "pull_request_target:")),
        ("branch filter widened", lambda t: t.replace("branches: [main]", "branches: ['**']")),
        ("extra push trigger", lambda t: t.replace("on:\n", "on:\n  push:\n", 1)),
        ("id-token at workflow level", lambda t: t.replace("permissions:\n  contents: read\njobs:", "permissions:\n  contents: read\n  id-token: write\njobs:")),
        ("id-token missing", lambda t: t.replace("      id-token: write\n", "")),
        ("contents write", lambda t: t.replace("contents: read", "contents: write")),
        ("extra write permission", lambda t: t.replace("      id-token: write\n", "      id-token: write\n      pull-requests: write\n")),
        ("environment", lambda t: t.replace("    runs-on:", "    environment: canary-branch\n    runs-on:")),
        ("secret reference", lambda t: t.replace("          GH_EVENT_NAME:", "          X: ${{ secrets.CANARY_UNRESTRICTED }}\n          GH_EVENT_NAME:")),
        ("event data", lambda t: t.replace("GH_EVENT_NAME: ${{ github.event_name }}", "GH_EVENT_NAME: ${{ github.event.pull_request.title }}")),
        ("unpinned action", lambda t: t.replace("@ea165f8d65b6e75b540449e92b4886f43607fa02", "@v4")),
        ("other action", lambda t: t.replace("actions/upload-artifact@", "evil/upload-artifact@")),
        ("other audience", lambda t: t.replace("audience=me1-evidence", "audience=sts.amazonaws.com")),
        ("no wait before publishing", lambda t: t.replace('          if [ "$WAIT" -gt 0 ]; then sleep "$WAIT"; fi\n', "")),
        ("no check that the wait elapsed", lambda t: t.replace('          if [ "$(date +%s)" -le $((EXP + 120)) ]; then echo "token not provably expired" >&2; exit 1; fi\n', "")),
        ("smaller safety margin", lambda t: t.replace("WAIT=$((EXP + 121 - NOW))", "WAIT=$((EXP + 1 - NOW))")),
        ("no cap on the wait", lambda t: t.replace('          if [ "$WAIT" -gt 721 ]; then echo "token expiry too far" >&2; exit 1; fi\n', "")),
        ("token written before the wait", lambda t: t.replace("          NOW=$(date +%s)\n", "          printf '%s\\n' \"$TOKEN\" > me1/oidc-token.jwt\n          NOW=$(date +%s)\n")),
        ("jq without -e", lambda t: t.replace("jq -er .value", "jq -r .value")),
        ("no JWT shape check", lambda t: t.replace('          case "$TOKEN" in *.*.*) ;; *) echo "not a JWT" >&2; exit 1 ;; esac\n', "")),
        ("token printed to the log", lambda t: t.replace(LAST, LAST + "          cat me1/oidc-token.jwt\n")),
        ("request token printed", lambda t: t.replace(LAST, LAST + "          echo \"$ACTIONS_ID_TOKEN_REQUEST_TOKEN\"\n")),
        ("token teed to stderr", lambda t: t.replace("| jq -er .value)", "| tee /dev/stderr | jq -er .value)")),
        ("harmless extra instruction", lambda t: t.replace(LAST, LAST + "          date\n")),
        ("token posted back via gh", lambda t: t.replace(LAST, LAST + "          gh pr comment 1 --body \"$TOKEN\"\n")),
        ("other request url", lambda t: t.replace('"$ACTIONS_ID_TOKEN_REQUEST_URL&audience=me1-evidence"', '"https://example.invalid/&audience=me1-evidence"')),
        ("changed context field", lambda t: t.replace("run_attempt: $run_attempt", 'run_attempt: "1"')),
        ("no set -e", lambda t: t.replace("          set -euo pipefail\n", "")),
        ("other artifact name", lambda t: t.replace("name: me1-evidence\n          path: me1", "name: other\n          path: me1")),
        ("longer retention", lambda t: t.replace("retention-days: 1", "retention-days: 90")),
        ("other timeout", lambda t: t.replace("timeout-minutes: 20", "timeout-minutes: 360")),
        ("self-hosted", lambda t: t.replace("ubuntu-24.04", "self-hosted")),
        ("second job", lambda t: t + "  second:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: echo x\n"),
        ("duplicate key", lambda t: t.replace("  contents: read\n", "  contents: read\n  contents: read\n", 1)),
        ("on written yes", lambda t: t.replace("\non:\n", "\nyes:\n")),
        ("empty file", lambda t: ""),
        ("not yaml", lambda t: "a: [\n"),
    ):
        for m in both(fn, lab):
            yield m


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
