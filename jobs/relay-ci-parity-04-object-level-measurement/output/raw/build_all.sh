#!/usr/bin/env bash
# PR-04: the object-evidence/1 record of the whole measured tree from the real tool outputs (pinned image):
# the root Go module, the separate goastdump module (own profile, uncovered spans kept), the Rust workspace,
# and 5 repeated Go profiles (an object whose covered count differs between runs is NONDETERMINISTIC).
set -e
git config --global --add safe.directory /w
cd /s/scripts
outs=""; for k in 0 1 2 3 4 5 6 7; do outs="$outs --rust-outcomes /p03/shards/$k/mutants.out/outcomes.json"; done
reps=""; for i in 1 2 3 4 5; do reps="$reps --go-repeat root=/out/go-cover-r$i.out"; done
python3 object_model.py build --root /w --scope /s/.measurement-scope.json --out /out/evidence.json \
  --go-unit root,.,/out/go-inventory-prod.json,/out/go-cover.out \
  --go-unit goastdump,tools/goastdump,/out/goastdump-inventory.json,/out/goastdump-cover.out,detail $reps \
  --llvm-cov /out/llvm-cov.json --rust-list /p03/list.json $outs \
  --tool go=go1.26.10 --tool rustc=1.96.1 --tool cargo-mutants=27.1.0 --tool cargo-llvm-cov=0.9.1 --tool objinventory=objinventory/1
