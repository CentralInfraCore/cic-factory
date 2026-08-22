#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# meta-get.sh <meta-path> <dotted.key>
#
# Egyetlen mező kiolvasása a meta.yaml-ből, valódi YAML-parserrel.
#
# Eddig minden olvasó saját regexet hozott: a close-job.sh kettőt is, egymástól
# eltérőt, a check-stale-jobs.sh egy harmadikat, a run-job.sh öt beágyazott
# Python-blokkot. Ugyanaz a dokumentum különbözőnek látszott attól függően, ki
# nézte -- és két kontroll ezen bukott meg:
#
#   status: "running" # agent-01     a stale-checker nem látta futónak (#29)
#   spec_gate: skipped # ok          a close C5 ellenőrzése kimaradt (#30)
#
# Mindkettő ugyanaz a dokumentum, mint a komment nélküli alak. Ez a script az
# egyetlen hely, ahol a mezőolvasás történik.
#
# Kimenet és exit code -- a hívónak a kettőt meg kell tudnia különböztetni,
# mert nem ugyanaz a döntés tartozik hozzájuk:
#
#   0   a mező megvan, az értéke a stdout-on (skalár, üres is lehet)
#   2   a mező NINCS a dokumentumban — régi meta, a hívó dönt
#   1   a dokumentum nem értelmezhető, vagy a mező nem skalár — fail closed
#
# A 2-es a megengedő ág. Ami eddig hibásan is oda esett, az most 1-es.

set -uo pipefail

META="${1:?meta-get.sh <meta-path> <dotted.key>}"
KEY="${2:?meta-get.sh <meta-path> <dotted.key>}"

[[ -f "$META" ]] || { echo "meta-get: nincs ilyen fájl: $META" >&2; exit 1; }

python3 - "$META" "$KEY" <<'PYEOF'
import sys

try:
    import yaml
except ImportError:
    print("meta-get: PyYAML kell a mezőolvasáshoz", file=sys.stderr)
    sys.exit(1)

meta_path, key = sys.argv[1], sys.argv[2]


class StrictLoader(yaml.SafeLoader):
    """A PyYAML alapból az utolsó duplikált kulcsot veszi, csendben. Egy
    kétszer megadott status: nem elgépelés, hanem eldöntetlen dokumentum --
    és az olvasók (regex: első, YAML: utolsó) ellentétesen döntenék el."""


def no_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        k = loader.construct_object(key_node, deep=deep)
        if k in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplikált kulcs: {k!r}", key_node.start_mark)
        seen.add(k)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates)

try:
    with open(meta_path, encoding="utf-8") as fh:
        doc = yaml.load(fh, Loader=StrictLoader)
except Exception as exc:
    print(f"meta-get: {meta_path} nem értelmezhető YAML: {exc}", file=sys.stderr)
    sys.exit(1)

if doc is None:
    print(f"meta-get: {meta_path} üres", file=sys.stderr)
    sys.exit(1)
if not isinstance(doc, dict):
    print(f"meta-get: {meta_path} nem mapping", file=sys.stderr)
    sys.exit(1)

node = doc
for part in key.split("."):
    if not isinstance(node, dict):
        print(f"meta-get: {key} — a(z) '{part}' előtti elem nem mapping",
              file=sys.stderr)
        sys.exit(1)
    if part not in node:
        sys.exit(2)          # hiányzik: a hívó dönt
    node = node[part]

if isinstance(node, (dict, list)):
    print(f"meta-get: {key} nem skalár", file=sys.stderr)
    sys.exit(1)
if node is None:
    print("")                # `status:` érték nélkül -> üres, de létező mező
    sys.exit(0)
if isinstance(node, bool):
    print("true" if node else "false")
    sys.exit(0)

print(node)
PYEOF
