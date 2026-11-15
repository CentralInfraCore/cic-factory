#!/usr/bin/env bash
# PR-05 B: can rustdoc's JSON (pinned nightly) be an independent Rust object inventory? (measurement only)
set -uo pipefail
export HOME=/home PATH=/usr/local/cargo/bin:$PATH CARGO_HOME=/cg RUSTUP_HOME=/ru CARGO_TARGET_DIR=/tgtdoc
git config --global --add safe.directory /w; cd /w
N=nightly-2026-07-01
rustup toolchain install $N --profile minimal >/dev/null 2>&1 || true   # rustup exits non-zero at the end when CARGO_HOME is not its own home; the toolchain is what counts
rustc +$N --version >/dev/null 2>&1 && echo "installed $N" || { echo "NIGHTLY NOT USABLE"; exit 0; }
rustc +$N --version
date -u +"start %FT%TZ"
RUSTDOCFLAGS="-Z unstable-options --output-format json --document-private-items" cargo +$N doc --workspace --no-deps --document-private-items --locked > /real/rustdoc/doc.log 2>&1; echo "cargo doc exit=$?"
date -u +"end %FT%TZ"
ls /tgtdoc/doc/*.json 2>/dev/null | wc -l | sed 's/^/rustdoc json files: /'
cp /tgtdoc/doc/*.json /real/rustdoc/ 2>/dev/null; tail -3 /real/rustdoc/doc.log | cut -c1-160
