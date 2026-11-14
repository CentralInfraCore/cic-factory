#!/usr/bin/env bash
# PR-04: what do cargo-llvm-cov and the pinned stable toolchain really give? (discovery, measurement only)
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
rustc --version; cargo --version; cargo llvm-cov --version
date -u +"start %FT%TZ"
echo "### 1. function-level JSON export (stable)"
cargo llvm-cov --all --locked --json --output-path /out/llvm-cov.json > /out/llvm-cov.log 2>&1; echo "llvm-cov json exit=$?"
tail -3 /out/llvm-cov.log
ls -la /out/llvm-cov.json 2>&1 | awk '{print $5" bytes"}'
echo "### 2. branch coverage on the pinned STABLE toolchain"
cargo llvm-cov --all --locked --branch --json --output-path /out/llvm-cov-branch.json > /out/llvm-cov-branch.log 2>&1; echo "llvm-cov --branch exit=$?"
tail -6 /out/llvm-cov-branch.log
date -u +"end %FT%TZ"
