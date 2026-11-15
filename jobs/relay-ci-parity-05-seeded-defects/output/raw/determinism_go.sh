#!/usr/bin/env bash
# PR-05 C: N repeated whole-module Go coverage profiles of the SAME tree, to find which blocks vary (measurement only).
export HOME=/home GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w
N=${1:-20}; go version; echo "tree: $(git rev-parse HEAD)"
for i in $(seq 1 $N); do
  go test -count=1 -covermode=set -coverprofile=/out/cov-$i.out ./... > /out/cov-$i.log 2>&1; echo "run $i exit=$? blocks=$(wc -l < /out/cov-$i.out)"
done
