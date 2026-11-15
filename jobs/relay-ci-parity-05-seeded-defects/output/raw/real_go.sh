#!/usr/bin/env bash
# PR-05: the Go side of the real pipeline (what object-evidence.yml does), as the current user.
set -euo pipefail
export HOME=/home GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w; T=/real
(cd tools/objinventory && go build -o "$T/objinventory" .)
python3 scripts/object_model.py scope-list --root . --scope .measurement-scope.json --lang go --class production > "$T/go-files.txt"
"$T/objinventory" $(cat "$T/go-files.txt") > "$T/go-inventory.json"
go test -count=1 -covermode=set -coverprofile="$T/go-cover.out" ./... > "$T/go-test.log" 2>&1
(cd tools/goastdump && "$T/objinventory" main.go > "$T/goastdump-inventory.json" && go test -count=1 -covermode=set -coverprofile="$T/goastdump-cover.out" ./... >/dev/null)
echo "go part done: $(wc -l < "$T/go-files.txt") production go files"
