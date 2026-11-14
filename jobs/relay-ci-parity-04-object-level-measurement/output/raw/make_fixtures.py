#!/usr/bin/env python3
"""PR-04: cut small test fixtures out of the REAL tool outputs (nothing is invented).
Go:   the real objinventory output and the real cover profile of the goastdump module (15 functions).
Rust: the functions of cic-canonical/src/lib.rs from the real `cargo llvm-cov --json` export, their
      real c++filt names, and the real cargo-mutants listing/outcomes restricted to that file."""
import json, subprocess, sys
out, big, p03, src = sys.argv[1:5]
def load(p): return json.load(open(p))
# --- Go (unmodified copies)
for name in ("goastdump-inventory.json", "goastdump-cover.out"):
    open(f"{out}/{name}", "w").write(open(f"{big}/{name}").read())
open(f"{out}/goastdump-main.go.txt", "w").write(open(f"{src}/tools/goastdump/main.go").read())
# --- Rust
FILE = "cic-canonical/src/lib.rs"
llvm = load(f"{big}/llvm-cov.json"); d = llvm["data"][0]
fns = [f for f in d["functions"] if f["filenames"][0].endswith("/" + FILE)]
sub = {"data": [{"files": [f for f in d["files"] if f["filename"].endswith("/" + FILE)], "functions": fns, "totals": d["totals"]}],
       "type": llvm["type"], "version": llvm["version"], "cargo_llvm_cov": llvm["cargo_llvm_cov"]}
json.dump(sub, open(f"{out}/llvm-cov-cic-canonical.json", "w"), indent=1, sort_keys=True)
syms = sorted({f["name"] for f in fns})
names = subprocess.run(["c++filt"], input="\n".join(syms) + "\n", capture_output=True, text=True, check=True).stdout.splitlines()
json.dump(dict(zip(syms, names)), open(f"{out}/demangled-cic-canonical.json", "w"), indent=1, sort_keys=True)
mut = [m for m in load(f"{p03}/list.json") if m["file"] == FILE]
for m in mut: m.pop("diff", None)
json.dump(mut, open(f"{out}/mutants-cic-canonical.json", "w"), indent=1, sort_keys=True)
names_set = {m["name"] for m in mut}; rows = []; base = None
for k in range(8):
    o = load(f"{p03}/shards/{k}/mutants.out/outcomes.json")
    for r in o["outcomes"]:
        if r["scenario"] == "Baseline": base = base or r; continue
        if r["scenario"]["Mutant"]["name"] in names_set:
            r["log_path"] = "<elided>"; r["phase_results"] = []; rows.append(r)
oc = {"outcomes": [dict(base, log_path="<elided>", phase_results=[])] + rows, "total_mutants": len(rows),
      "cargo_mutants_version": "27.1.0"}
for f, s in (("caught", "CaughtMutant"), ("missed", "MissedMutant"), ("timeout", "Timeout"), ("unviable", "Unviable")):
    oc[f] = sum(1 for r in rows if r["summary"] == s)
json.dump(oc, open(f"{out}/outcomes-cic-canonical.json", "w"), indent=1, sort_keys=True)
open(f"{out}/cic-canonical-lib.rs.txt", "w").write(open(f"{src}/{FILE}").read())
print("rust fixture:", len(fns), "llvm-cov entries,", len(syms), "symbols,", len(mut), "mutants, outcomes", {k: oc[k] for k in ("caught","missed","timeout","unviable")})
