#!/usr/bin/env bash
# PR-04 II.C (Rust): per-test coverage attribution on the pinned STABLE toolchain, crate cic-canonical (measurement only).
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
tests=$(cargo test -p cic-canonical --lib -- --list 2>/dev/null | sed -n 's/^\(.*\): test$/\1/p'); n=$(echo "$tests" | grep -c .)
echo "unit tests in cic-canonical (lib): $n"
s=$(date +%s%N); cargo llvm-cov -p cic-canonical --lib --json --output-path /out/pt-all.json >/dev/null 2>&1; echo "whole run, one profile: $(( ($(date +%s%N) - s) / 1000000 )) ms"
s=$(date +%s%N); k=0
for t in $tests; do cargo llvm-cov -p cic-canonical --lib --json --output-path /out/pt-$k.json -- --exact "$t" >/dev/null 2>&1 || echo "per-test run failed: $t"; k=$((k+1)); done
echo "one profile per test ($n runs): $(( ($(date +%s%N) - s) / 1000000 )) ms => $(( ($(date +%s%N) - s) / 1000000 / n )) ms per test"
python3 - <<'PY'
import glob,json
def covered(p):
    out=set()
    for f in json.load(open(p))["data"][0]["functions"]:
        fn=f["filenames"][0]
        for r in f["regions"]:
            if len(r)>=8 and r[7]==0 and r[4]>0: out.add((fn,f["name"],r[0],r[1],r[2],r[3]))
    return out
allc=covered("/out/pt-all.json"); union=set(); per=[]
for p in sorted(glob.glob("/out/pt-[0-9]*.json")):
    c=covered(p); per.append(len(c)); union|=c
print(f"covered code regions: whole run {len(allc)}; union of the per-test runs {len(union)}; equal: {union==allc}; per-test min/max {min(per)}/{max(per)}")
PY
