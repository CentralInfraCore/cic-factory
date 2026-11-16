#!/usr/bin/env bash
# PR-06 A.1/A.2 (Go): run scripts/gate_selftest.py in the pinned golang image, user-owned caches, read-only checkout.
set -euo pipefail
SRC=${1:?usage: run_gate_selftest_go.sh CHECKOUT CACHE_DIR}; C=${2:?}
U="$(id -u):$(id -g)"
docker run --rm --cpus 4 --user "$U" -v "$SRC":/src:ro -v "$C/work":/work -v "$C/gp":/gp -v "$C/gc":/gc -v "$C/home":/home -v "$C/pylib":/pylib \
  -e HOME=/home -e GOPATH=/gp -e GOCACHE=/gc -e PYTHONPATH=/pylib -e PATH=/gp/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin golang:1.26.10 \
  bash -c 'git config --global --add safe.directory /src; python3 /src/scripts/gate_selftest.py --src /src --work /work --only go-cov,go-mut'
