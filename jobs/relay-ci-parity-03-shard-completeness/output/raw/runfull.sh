#!/usr/bin/env bash
# PR-03: the real FULL Rust mutation run (300 mutants) in the pinned image, to measure the verdict split.
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
rm -rf /out/full; mkdir -p /out/full
cargo mutants --version
date -u +"start %FT%TZ"
cargo mutants --workspace --output /out/full > /out/full-run.log 2>&1; echo "full run exit=$?"
date -u +"end %FT%TZ"
