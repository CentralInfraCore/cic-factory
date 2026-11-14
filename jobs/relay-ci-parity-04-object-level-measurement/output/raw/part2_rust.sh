#!/usr/bin/env bash
# PR-04 part II feasibility: crate-level change impact from cargo metadata (II.D, Rust).
export PATH=/ch/bin:$PATH CARGO_HOME=/ch
git config --global --add safe.directory /w; cd /w
cargo metadata --no-deps --format-version 1 --locked --offline 2>/dev/null | python3 -c '
import json,sys
m=json.load(sys.stdin); names={p["name"] for p in m["packages"]}
dep={p["name"]:sorted(d["name"] for d in p["dependencies"] if d["name"] in names) for p in m["packages"]}
print("workspace crates:",len(names)); [print("  ",k,"->",v) for k,v in sorted(dep.items())]
def rev(t):
    out={t}; ch=True
    while ch:
        ch=False
        for k,v in dep.items():
            if k not in out and out&set(v): out.add(k); ch=True
    return out
for t in ("cic-canonical","connections"): print(f"crates affected by a change of {t} (reverse closure): {sorted(rev(t))}")
'
