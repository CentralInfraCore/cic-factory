#!/usr/bin/env bash
# PR-03: shard 7/8 re-run (the first run was cut off when the scratch volume filled up).
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
rm -rf /out/shards/7
cargo mutants --workspace --shard 7/8 --output /out/shards/7 > /out/shards/run-7.log 2>&1; echo "shard 7/8 exit=$?"
