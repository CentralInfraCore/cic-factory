#!/usr/bin/env bash
# PR-04 II.B: can a PINNED nightly give Rust branch coverage? (measurement only, separate target dir)
export PATH=/usr/local/cargo/bin:$PATH:/ch/bin CARGO_TARGET_DIR=/t RUSTUP_HOME=/usr/local/rustup  # default CARGO_HOME: rustup must find itself; cargo-llvm-cov comes from /ch/bin
git config --global --add safe.directory /w; cd /w
echo "stable: $(rustc --version)"
for d in 2026-07-01 2026-06-30 2026-06-28 2026-07-03; do
  echo "### try rustup toolchain install nightly-$d (minimal + llvm-tools-preview)"
  if rustup toolchain install nightly-$d --profile minimal -c llvm-tools-preview >/tmp/rustup-$d.log 2>&1; then echo "installed nightly-$d"; N=nightly-$d; break; else tail -2 /tmp/rustup-$d.log | cut -c1-160; fi
done
[ -z "$N" ] && { echo "NO PINNED NIGHTLY COULD BE INSTALLED"; exit 0; }
rustc +$N --version; cargo +$N --version
date -u +"start %FT%TZ"
echo "### cargo +$N llvm-cov --branch (workspace, locked)"
cargo +$N llvm-cov --all --locked --branch --json --output-path /out/llvm-cov-branch-nightly.json > /out/nightly-branch.log 2>&1; echo "exit=$?"
date -u +"end %FT%TZ"
tail -4 /out/nightly-branch.log | cut -c1-200
python3 - <<'PY'
import json,os
p="/out/llvm-cov-branch-nightly.json"
if os.path.exists(p):
    d=json.load(open(p))["data"][0]; t=d["totals"]
    print("totals.branches:",{k:t["branches"][k] for k in ("count","covered","percent")})
    fs=d["functions"]; print("functions:",len(fs),"with branch records:",sum(1 for f in fs if f.get("branches")))
    print("sample branch record:",next((f["branches"][0] for f in fs if f.get("branches")),None))
PY
