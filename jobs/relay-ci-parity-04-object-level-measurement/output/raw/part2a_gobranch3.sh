#!/usr/bin/env bash
# PR-04 II.A (3/3): gobco v1.3.4 vs native statement coverage on three packages (one is the nested goastdump module).
export GOFLAGS="-buildvcs=false" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local PATH=/gp/bin:$PATH
cd /w
printf "%-34s %-18s %-26s %s\n" package "statement cov." "gobco conditions" "gobco time"
row() { dir=$1; pkg=$2
  cd /w/$dir
  st=$(go test -count=1 -cover $pkg 2>&1 | grep -o 'coverage: [0-9.]*%' | head -1)
  s=$(date +%s%N); out=$(gobco $pkg 2>&1); ms=$(( ($(date +%s%N) - s) / 1000000 ))
  c=$(echo "$out" | grep -o 'Condition coverage: [0-9]*/[0-9]*' | head -1)
  printf "%-34s %-18s %-26s %s ms\n" "$dir $pkg" "$st" "${c:-<none: $(echo "$out" | tail -1 | cut -c1-30)>}" "$ms"
}
row . ./pkg/merkle
row . ./pkg/canonicaljson
row tools/goastdump .
