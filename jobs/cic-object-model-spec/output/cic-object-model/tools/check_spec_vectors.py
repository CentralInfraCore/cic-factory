"""check_spec_vectors — keep SPEC.md and the conformance corpus from drifting.

This is a *mapping* gate, not a conformance run. It answers one question: is
every normative statement in SPEC.md either backed by a vector or explicitly
declared unvectorizable? It cannot and does not tell you whether any vector
passes — no implementation is required to run it.

Checks:

  C1  Every INV-nnn defined in SPEC.md's invariant index (section 12) appears
      in docs/spec-vector-map.md.
  C2  Every INV-nnn referenced by a vector's meta.yaml exists in SPEC.md.
      (Catches a vector pinned to an invariant that was renumbered away.)
  C3  Every INV-nnn in SPEC.md is either covered by >=1 vector or listed in
      the map's "unvectorizable" table with a non-empty justification.
  C4  Every vector directory has the files its category requires.
  C5  Every truth-table row 1..8 in SPEC.md section 5.3 has a vector.

Exit 0 if all pass, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "SPEC.md"
MAP = ROOT / "docs" / "spec-vector-map.md"
CONFORMANCE = ROOT / "conformance"

INV_RE = re.compile(r"\bINV-(\d{3})\b")

REQUIRED_FILES = {
    "materialization": {"meta.yaml", "schema.yaml", "input.yaml", "expected.yaml"},
    "invalid": {"meta.yaml", "schema.yaml", "input.yaml", "expected-error.yaml"},
    "validation": {"meta.yaml", "object.yaml", "expected-error.yaml"},
}


def spec_invariants() -> set[str]:
    """Invariants defined in SPEC.md's index table (section 12)."""
    text = SPEC.read_text(encoding="utf-8")
    index = text.split("## 12. Invariant index", 1)
    if len(index) != 2:
        sys.exit("SPEC.md: section 12 (Invariant index) not found")
    return {f"INV-{m}" for m in INV_RE.findall(index[1])}


def spec_truth_table_rows() -> set[int]:
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("### 5.3 The truth table", 1)
    if len(section) != 2:
        sys.exit("SPEC.md: section 5.3 (truth table) not found")
    body = section[1].split("###", 1)[0]
    rows = set()
    for line in body.splitlines():
        m = re.match(r"\|\s*(\d)\s*\|", line)
        if m:
            rows.add(int(m.group(1)))
    return rows


def vectors() -> list[dict]:
    found = []
    for meta_path in sorted(CONFORMANCE.glob("*/*/meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        meta["_dir"] = meta_path.parent
        meta["_category"] = meta_path.parent.parent.name
        found.append(meta)
    return found


def map_unvectorizable() -> dict[str, str]:
    """INV -> justification, from the map's unvectorizable table."""
    if not MAP.exists():
        sys.exit(f"{MAP} not found")
    text = MAP.read_text(encoding="utf-8")
    section = text.split("## Unvectorizable", 1)
    if len(section) != 2:
        return {}
    out = {}
    for line in section[1].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and INV_RE.fullmatch(cells[0] or ""):
            justification = cells[-1]
            if justification and not set(justification) <= {"-"}:
                out[cells[0]] = justification
    return out


def main() -> int:
    failures: list[str] = []

    spec_invs = spec_invariants()
    if not spec_invs:
        sys.exit("SPEC.md: no invariants parsed from section 12")
    vecs = vectors()
    unvec = map_unvectorizable()
    map_text = MAP.read_text(encoding="utf-8")
    map_invs = {f"INV-{m}" for m in INV_RE.findall(map_text)}

    # C1
    for inv in sorted(spec_invs - map_invs):
        failures.append(f"C1 {inv}: defined in SPEC.md but absent from {MAP.name}")

    # C2 + coverage tally
    covered: dict[str, list[str]] = {}
    for v in vecs:
        vid = v.get("id", str(v["_dir"]))
        for inv in v.get("invariants", []):
            if inv not in spec_invs:
                failures.append(
                    f"C2 {vid}: references {inv}, which SPEC.md does not define"
                )
            covered.setdefault(inv, []).append(vid)

    # C3
    for inv in sorted(spec_invs):
        if inv not in covered and inv not in unvec:
            failures.append(
                f"C3 {inv}: no vector covers it and it is not listed as "
                f"unvectorizable with a justification"
            )

    # C4
    for v in vecs:
        cat = v["_category"]
        required = REQUIRED_FILES.get(cat)
        if required is None:
            failures.append(f"C4 {v['_dir']}: unknown vector category '{cat}'")
            continue
        present = {p.name for p in v["_dir"].iterdir() if p.is_file()}
        for missing in sorted(required - present):
            failures.append(f"C4 {v.get('id', v['_dir'])}: missing {missing}")

    # C5
    rows_in_spec = spec_truth_table_rows()
    rows_covered = {v["truth_table_row"] for v in vecs if "truth_table_row" in v}
    for row in sorted(rows_in_spec - rows_covered):
        failures.append(f"C5 truth-table row {row}: no vector")

    print(f"SPEC.md invariants:      {len(spec_invs)}")
    print(f"vectors:                 {len(vecs)}")
    print(f"invariants with vectors: {len(covered)}")
    print(f"declared unvectorizable: {len(unvec)}")
    print(f"truth-table rows:        {len(rows_covered)}/{len(rows_in_spec)}")
    print()

    if failures:
        print(f"FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("PASS — SPEC.md and the vector corpus agree.")
    print()
    print("NOTE: this gate checks the spec<->vector mapping only. It does not")
    print("run any vector. Vector status is 'written, never executed' until an")
    print("implementation lands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
