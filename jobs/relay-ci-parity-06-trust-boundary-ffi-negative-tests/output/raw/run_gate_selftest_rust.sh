#!/usr/bin/env bash
# PR-06 A.1/A.2 (Rust): run scripts/gate_selftest.py in the pinned rust image (digest-pinned), user-owned caches.
set -euo pipefail
SRC=${1:?usage: run_gate_selftest_rust.sh CHECKOUT CACHE_DIR}; C=${2:?}
U="$(id -u):$(id -g)"
docker run --rm --cpus 4 --user "$U" -v "$SRC":/src:ro -v "$C/work":/work -v "$C/cg":/cg -v "$C/ru":/ru -v "$C/tgt":/tgt -v "$C/home":/home -v "$C/pylib":/pylib \
  -e HOME=/home -e CARGO_HOME=/cg -e RUSTUP_HOME=/ru -e CARGO_TARGET_DIR=/tgt -e PYTHONPATH=/pylib -e PATH=/usr/local/cargo/bin:/cg/bin:/usr/local/bin:/usr/bin:/bin \
  rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8 \
  bash -c 'git config --global --add safe.directory /src; python3 /src/scripts/gate_selftest.py --src /src --work /work --only rust-cov,rust-mut'
