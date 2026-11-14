#!/usr/bin/env bash
# PR-03: the 8 real shards of the 300-mutant plan, each with its own outputs dir (as the CI runs them).
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
rm -rf /out/shards; mkdir -p /out/shards
for k in 0 1 2 3 4 5 6 7; do
  cargo mutants --workspace --shard $k/8 --output /out/shards/$k > /out/shards/run-$k.log 2>&1; echo "shard $k/8 exit=$?"
done
