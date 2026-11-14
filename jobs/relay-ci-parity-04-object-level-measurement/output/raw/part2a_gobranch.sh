#!/usr/bin/env bash
# PR-04 II.A: evaluation of a Go branch-coverage tool (gobco, source-instrumenting). Measurement only.
export GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w
go version
echo "### provenance and pinnability"
GOFLAGS=-mod=mod go list -m -versions github.com/rillig/gobco 2>&1 | tr ' ' '\n' | tail -6 | tr '\n' ' '; echo
echo "### install a PINNED version (a tag, resolved through the module proxy; go.sum-verified by the toolchain)"
unset GOFLAGS; export GOFLAGS=-buildvcs=false
v=$(go list -m -versions github.com/rillig/gobco 2>/dev/null | tr ' ' '\n' | tail -1); echo "latest tag: $v"
go install github.com/rillig/gobco@$v 2>&1 | tail -3; echo "install exit=$?"
export PATH=/gp/bin:$PATH; command -v gobco && gobco -version 2>&1 | head -2
echo "### license and module info"
go mod download -json github.com/rillig/gobco@$v 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('Path',d['Path'],'Version',d['Version'],'Sum',d.get('Sum'))" 2>&1
ls $(go env GOMODCACHE)/github.com/rillig/gobco@$v 2>/dev/null | tr '\n' ' '; echo
head -3 $(go env GOMODCACHE)/github.com/rillig/gobco@$v/LICENSE 2>/dev/null
echo "### usage"; gobco -help 2>&1 | head -12
echo "### run on the goastdump module (own go.mod), twice, and compare"
cd tools/goastdump
for i in 1 2; do s=$(date +%s%N); gobco ./... > /tmp/gobco$i.txt 2>&1; echo "run $i exit=$? $(( ($(date +%s%N) - s) / 1000000 )) ms"; done
tail -6 /tmp/gobco1.txt | cut -c1-160
ls gobco-counts.json 2>/dev/null && python3 - <<'PY'
import json
c=json.load(open("gobco-counts.json")); print("conditions measured:",len(c) if isinstance(c,list) else type(c))
PY
diff <(grep -v "ms\|took" /tmp/gobco1.txt) <(grep -v "ms\|took" /tmp/gobco2.txt) >/dev/null && echo "two runs: identical report" || echo "two runs: reports DIFFER"
rm -f gobco-counts.json
echo "### the same tool on one root package ./pkg/merkle"
cd /w; s=$(date +%s%N); gobco ./pkg/merkle > /tmp/gobco-m.txt 2>&1; echo "exit=$? $(( ($(date +%s%N) - s) / 1000000 )) ms"; tail -5 /tmp/gobco-m.txt | cut -c1-160
echo "### statement coverage of the same package for comparison"
go test -count=1 -cover ./pkg/merkle 2>&1 | tail -1
