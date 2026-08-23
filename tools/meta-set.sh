#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# meta-set.sh <meta-path> <kulcs>=<érték> [<kulcs>=<érték> ...]
#
# Mezőírás a meta.yaml-be, valódi YAML-parserrel megkeresett helyre.
#
# A meta-get.sh (#29, #30) az olvasás felét zárta le. Ez az írásé. A run-job.sh
# eddig három helyen, összesen tizenhét `re.sub`-bal írt a metába, és a minták
# nem voltak szekcióhoz kötve:
#
#   ^\s+completed:.*$     MINDEN behúzott completed: sort átírta, nem csak a
#                         timestamps alattit
#   ^\s+started:.*$       ugyanez
#   ^(\s+model:.*)$       az első model: alá szúrta a session_id-t, akárhol volt
#   ^status:.*$           count nélkül: duplikált kulcs esetén mindet
#   ^usage:\s*\n(...)*    az első üres sorig tartott, tehát a maradék régi mező
#                         az új blokk mögött maradt -- duplikált YAML-kulcsként
#
# Itt a fájlt a PyYAML `compose()` bontja csomópontfává, ami sor- és
# oszlopjelöléseket ad. Ebből tudjuk, PONTOSAN melyik sor tartozik a kulcshoz --
# a többi bájt érintetlen marad, tehát a kézzel írt kommentek és a formázás is.
#
# Ez szándékosan nem teljes YAML round-trip: az load+dump elveszítené a
# kommenteket, és a jobs/<id>/meta.yaml kézzel karbantartott dokumentum.
#
# Minden érték idézőjeles stringként íródik. A séma minden numerikus mezőt
# string VAGY szám alakban elfogad, tehát ez érvényes marad.
#
# Exit 0 = kiírva, 1 = a dokumentum nem értelmezhető vagy a kulcs nem kezelhető.

set -uo pipefail

META="${1:?meta-set.sh <meta-path> <kulcs>=<érték> ...}"
shift
[[ $# -gt 0 ]] || { echo "meta-set: adj meg legalább egy kulcs=érték párt" >&2; exit 1; }

[[ -f "$META" ]] || { echo "meta-set: nincs ilyen fájl: $META" >&2; exit 1; }

python3 - "$META" "$@" <<'PYEOF'
import sys

try:
    import yaml
except ImportError:
    print("meta-set: PyYAML kell a mezőíráshoz", file=sys.stderr)
    sys.exit(1)

meta_path, assignments = sys.argv[1], sys.argv[2:]


class StrictLoader(yaml.SafeLoader):
    """Duplikált kulcsra hibát ad. A PyYAML alapból az utolsót veszi, csendben;
    egy kétszer megadott status: nem elgépelés, hanem eldöntetlen dokumentum."""


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

raw = open(meta_path, encoding="utf-8").read()
lines = raw.split("\n")

try:
    yaml.load(raw, Loader=StrictLoader)          # validál (duplikátum, szintaxis)
    root = yaml.compose(raw, Loader=StrictLoader)  # jelölések a helyekhez
except Exception as exc:
    print(f"meta-set: {meta_path} nem értelmezhető YAML: {exc}", file=sys.stderr)
    sys.exit(1)

if root is None or not isinstance(root, yaml.MappingNode):
    print(f"meta-set: {meta_path} nem mapping", file=sys.stderr)
    sys.exit(1)


def quote(value):
    """Dupla idézőjeles YAML-skalár. A backslash és az idézőjel escape-elve."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def child(mapping, name):
    for key_node, value_node in mapping.value:
        if key_node.value == name:
            return key_node, value_node
    return None, None


def value_end_line(key_node, value_node):
    """Az utolsó sor, ami még az értékhez tartozik (0-alapú).

    Üres értéknél (`status:`) a jelölés a KÖVETKEZŐ sor elejére mutat, tehát
    ott vissza kell lépni -- különben a csere elnyelné a következő kulcsot."""
    end = value_node.end_mark.line
    if end > value_node.start_mark.line and value_node.end_mark.column == 0:
        end -= 1
    return max(end, key_node.start_mark.line)


# (sor_tól, sor_ig_bezárólag, új_sorok) hármasok; a végén alulról fölfelé
# alkalmazzuk, hogy a sorszámok ne csússzanak el.
edits = []
# Hiányzó gyökér-szekció: a mezőket sorrendben gyűjtjük, és a végén EGY
# beszúrásként írjuk ki. Külön beszúrásokként ugyanarra a pontra fordított
# sorrendben kerülnének be, és a szekció fejléce a mezői mögé csúszna.
new_sections = {}
# Ebben a futásban beszúrt kulcsok: a compose() fája nem tud róluk, tehát a
# következő beszúrás helyét innen kell tudni.
pending_inserts = {}


def indent_of(node):
    return " " * node.start_mark.column


def plan(path, value):
    parts = path.split(".")
    node = root
    for depth, name in enumerate(parts[:-1]):
        key_node, value_node = child(node, name)
        if key_node is None:
            # Hiányzó GYÖKÉR-szintű szekciót létrehozunk: a usage: blokk a
            # mező bevezetése előtti metákból hiányzik, és a runner ilyenkor
            # is ír bele. Mélyebb szintet nem találunk ki -- ott a hiány
            # inkább elgépelés, mint hiányzó mező.
            if depth == 0 and node is root and len(parts) == 2:
                new_sections.setdefault(name, [])
                node = None
                continue
            print(f"meta-set: a(z) '{name}' szekció nincs a dokumentumban, "
                  f"és nem hozom létre ({path})", file=sys.stderr)
            sys.exit(1)
        if not isinstance(value_node, yaml.MappingNode):
            print(f"meta-set: '{name}' nem mapping, {path} nem írható",
                  file=sys.stderr)
            sys.exit(1)
        node = value_node

    leaf = parts[-1]
    if node is None:
        new_sections[parts[0]].append(f"  {leaf}: {quote(value)}")
        return

    key_node, value_node = child(node, leaf)
    if key_node is not None:
        start = key_node.start_mark.line
        edits.append((start, value_end_line(key_node, value_node),
                      [f"{indent_of(key_node)}{leaf}: {quote(value)}"]))
        return

    # Nincs meg: a szülő utolsó gyereke UTÁN szúrjuk be, annak behúzásával.
    if node.value:
        last_key, last_value = node.value[-1]
        after = value_end_line(last_key, last_value)
        indent = indent_of(last_key)
    elif node is root:
        after = len(lines) - 1
        indent = ""
    else:
        print(f"meta-set: üres szekció, {path} nem szúrható be",
              file=sys.stderr)
        sys.exit(1)

    # Ha ugyanabba a szekcióba már szúrtunk be ebben a futásban, a mögé kell.
    section = ".".join(parts[:-1])
    after = max(after, pending_inserts.get(section, -1))
    pending_inserts[section] = after
    edits.append((after + 1, after, [f"{indent}{leaf}: {quote(value)}"]))


for assignment in assignments:
    if "=" not in assignment:
        print(f"meta-set: '{assignment}' nem kulcs=érték alakú", file=sys.stderr)
        sys.exit(1)
    key, _, val = assignment.partition("=")
    plan(key.strip(), val)

if new_sections:
    tail = []
    for name, rows in new_sections.items():
        tail.append(f"{name}:")
        tail.extend(rows)
    # A fájl utolsó eleme a záró újsor utáni üres string; elé fűzünk.
    at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
    edits.append((at, at - 1, tail))

for start, end, replacement in sorted(edits, key=lambda e: e[0], reverse=True):
    lines[start:end + 1] = replacement

open(meta_path, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
