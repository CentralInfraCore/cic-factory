#!/usr/bin/env bash
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t2
git config --global --add safe.directory /w; cd /w; git checkout -q -- .; git status --short | head
rustup component add llvm-tools-preview 2>&1 | tail -1
cargo install cargo-llvm-cov --locked 2>&1 | tail -2
cargo llvm-cov --version
cargo test --all --locked 2>&1 | grep -E '^test result|FAILED|error' | head -40; echo "cargo test exit: ${PIPESTATUS[0]}"
cargo llvm-cov --all --locked --json --summary-only --output-path /out/rust-cov.json > /out/rust-cov.log 2>&1; echo "llvm-cov exit: $?"
cargo llvm-cov report --all 2>/dev/null | tail -40 > /out/rust-cov-table.txt
cat /out/rust-cov-table.txt
