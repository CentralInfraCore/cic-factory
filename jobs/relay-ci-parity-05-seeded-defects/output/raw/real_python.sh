#!/usr/bin/env bash
# PR-05: the Rust side, the record, the verification and the seeded defects on the REAL record.
set -euo pipefail
export HOME=/home PATH=/usr/local/cargo/bin:/cg/bin:$PATH CARGO_HOME=/cg RUSTUP_HOME=/ru CARGO_TARGET_DIR=/tgt
git config --global --add safe.directory /w; cd /w; T=/real
tools=(--tool "go=go1.26.10" --tool "rustc=$(rustc --version | awk '{print $2}')" --tool "cargo-llvm-cov=$(cargo llvm-cov --version | awk '{print $2}')" --tool "cargo-mutants=$(cargo mutants --version | awk '{print $2}')" --tool "objinventory=objinventory/1")
python3 scripts/object_model.py build --root . --scope .measurement-scope.json --out "$T/evidence.json" \
  --go-unit "root,.,$T/go-inventory.json,$T/go-cover.out" --go-unit "goastdump,tools/goastdump,$T/goastdump-inventory.json,$T/goastdump-cover.out,detail" \
  --llvm-cov "$T/llvm-cov.json" --rust-list "$T/rust-list.json" --rust-prefix "$PWD/" "${tools[@]}"
INP=(--input "go-inventory:root=$T/go-inventory.json" --input "go-coverprofile:root=$T/go-cover.out" --input "go-inventory:goastdump=$T/goastdump-inventory.json" --input "go-coverprofile:goastdump=$T/goastdump-cover.out" --input "llvm-cov-json=$T/llvm-cov.json" --input "rust-mutant-list=$T/rust-list.json" --input "scope=.measurement-scope.json")
echo; echo "### verify"; python3 scripts/object_model.py verify --record "$T/evidence.json" --root . --scope .measurement-scope.json --rust-list "$T/rust-list.json" "${INP[@]}" | tee "$T/verify.txt" || true
echo; echo "### seeded defects on the real record"; python3 scripts/seeded_defects.py --record "$T/evidence.json" --root . --scope .measurement-scope.json --rust-list "$T/rust-list.json" --expect-l3 PARTIAL "${INP[@]}" | tee "$T/seeded-defects.txt" || true
