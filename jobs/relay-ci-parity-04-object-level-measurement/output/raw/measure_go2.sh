#!/usr/bin/env bash
# PR-04: the separate goastdump module (own profile, own inventory) and 5 repeated whole-module profiles.
export GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w
echo "### goastdump (nested module): profile and inventory"
(cd tools/goastdump && go test -count=1 -covermode=set -coverprofile=/out/goastdump-cover.out ./... 2>&1 | tail -2)
(cd tools/goastdump && /out/objinventory main.go > /out/goastdump-inventory.json; echo "objinventory exit=$?")
echo "### 5 repeated whole-module coverage profiles"
for i in 1 2 3 4 5; do
  go test -count=1 -covermode=set -coverprofile=/out/go-cover-r$i.out ./... > /out/go-test-r$i.log 2>&1; echo "run $i exit=$? blocks=$(wc -l < /out/go-cover-r$i.out)"
done
