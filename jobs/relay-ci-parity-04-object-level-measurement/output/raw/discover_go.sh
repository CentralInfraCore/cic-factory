#!/usr/bin/env bash
# PR-04: real Go measurements of CIC_Relay (coverage profile, object inventory, the inventory tool's own tests).
export GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w
go version
echo "### objinventory tests"; (cd tools/objinventory && go vet ./... && go test -count=1 -cover ./... 2>&1 | tail -5)
echo "### real Go inventory of the root module (production files)"
files=$(git ls-files '*.go' | grep -v '_test\.go$' | grep -v '/testdata/' | grep -v '^tools/goastdump/' | grep -v '^tools/objinventory/')
echo "production go files: $(echo "$files" | wc -l)"
(cd tools/objinventory && go build -o /out/objinventory .)
/out/objinventory $files > /out/go-inventory.json; echo "objinventory exit=$?"
echo "### real coverage profile (set mode), whole root module"
date -u +"start %FT%TZ"
go test -count=1 -covermode=set -coverprofile=/out/go-cover.out ./... > /out/go-test.log 2>&1; echo "go test exit=$?"
date -u +"end %FT%TZ"
grep -vc "^ok\|no test files" /out/go-test.log | sed 's/^/non-ok lines: /'
head -1 /out/go-cover.out; wc -l < /out/go-cover.out | sed 's/^/blocks+1: /'
go tool cover -func=/out/go-cover.out | tail -1
