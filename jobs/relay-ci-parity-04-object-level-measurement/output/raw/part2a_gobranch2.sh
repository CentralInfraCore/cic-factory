#!/usr/bin/env bash
# PR-04 II.A (2/2): the nested-module case, the -branch mode, and reproducibility of gobco v1.3.4.
export GOFLAGS="-buildvcs=false" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local PATH=/gp/bin:$PATH
cd /w
echo "### reproducibility: ./pkg/merkle twice, condition lines compared"
for i in 1 2; do gobco ./pkg/merkle 2>&1 | grep -E "^Condition|never" > /tmp/m$i.txt; done
wc -l < /tmp/m1.txt | sed 's/^/lines: /'; cmp -s /tmp/m1.txt /tmp/m2.txt && echo "two runs: identical" || echo "two runs: DIFFER"
echo "### -branch mode on ./pkg/merkle"; gobco -branch ./pkg/merkle 2>&1 | grep -E "^Branch|^Condition|never" | head -4 | cut -c1-150
echo "### the nested module goastdump (own go.mod): from inside it"
cd tools/goastdump; echo "-- gobco ."; gobco . 2>&1 | tail -3; echo "exit=$?"
echo "-- gobco ./..."; gobco ./... 2>&1 | tail -2
echo "### from the root with the nested path"; cd /w; gobco ./tools/goastdump 2>&1 | tail -3 | cut -c1-200; echo "exit=${PIPESTATUS[0]}"
echo "### a package that does not exist: is the exit status non-zero (fail-closed)?"
gobco ./no/such/pkg >/tmp/x.txt 2>&1; echo "exit=$? : $(tail -1 /tmp/x.txt | cut -c1-120)"
echo "### a package without tests"
mkdir -p /tmp/notest/p && cd /tmp/notest && printf 'module notest\n\ngo 1.22\n' > go.mod && printf 'package p\n\nfunc F(a int) int {\n\tif a > 1 {\n\t\treturn 1\n\t}\n\treturn 0\n}\n' > p/p.go && gobco ./p 2>&1 | tail -3 | cut -c1-150; echo "exit=${PIPESTATUS[0]}"
