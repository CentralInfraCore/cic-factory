#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# validate-meta.sh <job-id> | --file <path> | --template | --all
#
# The meta.yaml schema used to be a commented example and nothing more: the
# enums lived in comments, so a mistyped field name was silently accepted and a
# status of "finished" would have been taken as valid. jobs/.schema/meta.schema.json
# is now the definition; this validates against it.
#
#   <job-id> | --file   a real meta.yaml, fully validated
#   --template          the commented example. Its values are placeholders and
#                       cannot validate as a job, so what is checked is that its
#                       KEY SET matches the schema exactly -- which is the drift
#                       that actually happened: lease_expires, spec_gate, usage
#                       and runs were each added to one and not the other.
#   --all               every jobs/*/meta.yaml, for auditing
#
# Exit 0 = valid, exit 1 = not.

set -uo pipefail

WORKDIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA="$WORKDIR/jobs/.schema/meta.schema.json"
TEMPLATE="$WORKDIR/jobs/.schema/meta.yaml"

MODE="job"; TARGET=""
case "${1:-}" in
    "")          echo "Usage: $0 <job-id> | --file <path> | --template | --all" >&2; exit 1 ;;
    --template)  MODE="template" ;;
    --all)       MODE="all" ;;
    --file)      TARGET="${2:?--file needs a path}" ;;
    -*)          echo "Unknown flag: $1" >&2; exit 1 ;;
    *)           TARGET="$WORKDIR/jobs/$1/meta.yaml" ;;
esac

[[ -f "$SCHEMA" ]] || { echo "[ERROR] nincs séma: $SCHEMA" >&2; exit 1; }

python3 - "$SCHEMA" "$TEMPLATE" "$MODE" "$TARGET" "$WORKDIR" <<'PYEOF'
import glob, json, os, sys

schema_path, template_path, mode, target, workdir = sys.argv[1:6]

try:
    import yaml
    import jsonschema
except ImportError as e:
    print(f"[ERROR] hiányzó függőség: {e.name} (pip install pyyaml jsonschema)", file=sys.stderr)
    sys.exit(1)

schema = json.load(open(schema_path, encoding="utf-8"))

# A schema that is itself malformed would accept everything, which is the
# quietest possible failure.
try:
    jsonschema.Draft202012Validator.check_schema(schema)
except jsonschema.SchemaError as e:
    print(f"[ERROR] maga a séma érvénytelen: {e.message}", file=sys.stderr)
    sys.exit(1)

validator = jsonschema.Draft202012Validator(schema)


def report(path, errors):
    if not errors:
        print(f"  OK    {path}")
        return 0
    print(f"  FAIL  {path}")
    for e in errors:
        where = ".".join(str(x) for x in e.absolute_path) or "(gyökér)"
        print(f"          {where}: {e.message}")
    return 1


def keys_of(obj, prefix=""):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            out.add(full)
            out |= keys_of(v, full)
    return out


def schema_keys(node, prefix=""):
    out = set()
    for k, v in (node.get("properties") or {}).items():
        full = f"{prefix}.{k}" if prefix else k
        if v.get("deprecated"):
            continue
        out.add(full)
        out |= schema_keys(v, full)
    return out


rc = 0

if mode == "template":
    doc = yaml.safe_load(open(template_path, encoding="utf-8"))
    have, want = keys_of(doc), schema_keys(schema)
    missing, extra = sorted(want - have), sorted(have - want)
    if missing or extra:
        print(f"  FAIL  {os.path.relpath(template_path, workdir)}")
        for k in missing:
            print(f"          a sémában van, a sablonból hiányzik: {k}")
        for k in extra:
            print(f"          a sablonban van, a séma nem ismeri:  {k}")
        rc = 1
    else:
        print(f"  OK    {os.path.relpath(template_path, workdir)} — {len(want)} kulcs egyezik")

elif mode == "all":
    files = sorted(glob.glob(os.path.join(workdir, "jobs", "*", "meta.yaml")))
    ok = 0
    for f in files:
        errs = sorted(validator.iter_errors(yaml.safe_load(open(f, encoding="utf-8"))),
                      key=lambda e: list(e.absolute_path))
        if report(os.path.relpath(f, workdir), errs):
            rc = 1
        else:
            ok += 1
    print(f"\n  {ok}/{len(files)} érvényes")

else:
    if not os.path.isfile(target):
        print(f"[ERROR] nincs ilyen meta.yaml: {target}", file=sys.stderr)
        sys.exit(1)
    errs = sorted(validator.iter_errors(yaml.safe_load(open(target, encoding="utf-8"))),
                  key=lambda e: list(e.absolute_path))
    rc = report(os.path.relpath(target, workdir), errs)

sys.exit(rc)
PYEOF
