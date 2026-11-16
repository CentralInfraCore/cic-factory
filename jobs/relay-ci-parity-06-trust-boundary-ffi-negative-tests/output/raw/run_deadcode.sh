#!/usr/bin/env bash
# PR-06 B: production reachability from the relay entry point (deadcode, golang.org/x/tools v0.52.0).
set -euo pipefail
SRC=${1:?usage: run_deadcode.sh CHECKOUT CACHE_DIR OUT_FILE}; C=${2:?}; OUT=${3:?}
U="$(id -u):$(id -g)"
docker run --rm --cpus 4 --user "$U" -v "$SRC":/src:ro -v "$C/gp":/gp -v "$C/gc":/gc -v "$C/home":/home -v "$(dirname "$OUT")":/out \
  -e HOME=/home -e GOPATH=/gp -e GOCACHE=/gc -e PATH=/gp/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin golang:1.26.10 \
  bash -c 'go install golang.org/x/tools/cmd/deadcode@v0.52.0 && mkdir -p /tmp/w && cp -r /src/. /tmp/w/ && cd /tmp/w && GOFLAGS=-mod=readonly deadcode ./cmd/relay > /out/'"$(basename "$OUT")"
