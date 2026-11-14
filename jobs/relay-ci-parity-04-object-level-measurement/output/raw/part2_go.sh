#!/usr/bin/env bash
# PR-04 part II feasibility (measurement only): per-test attribution cost (II.C) and package-level change impact (II.D), Go.
export GOFLAGS="-buildvcs=false -mod=readonly" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
git config --global --add safe.directory /w; cd /w
echo "### II.C per-test coverage attribution, sample package ./pkg/merkle"
go test -count=1 -c -o /tmp/merkle.test ./pkg/merkle >/dev/null 2>&1
tests=$(go test -list '.*' ./pkg/merkle | grep -E '^(Test|Fuzz|Example)' ); n=$(echo "$tests" | wc -l); echo "tests in the package: $n"
s=$(date +%s%N); go test -count=1 -coverprofile=/tmp/all.out ./pkg/merkle >/dev/null 2>&1; e=$(date +%s%N)
echo "whole package, one profile: $(( (e - s) / 1000000 )) ms"
s=$(date +%s%N); k=0
for t in $tests; do go test -count=1 -run "^$t\$" -coverprofile=/tmp/t_$k.out ./pkg/merkle >/dev/null 2>&1; k=$((k+1)); done; e=$(date +%s%N)
echo "one profile per test ($n invocations): $(( (e - s) / 1000000 )) ms  => $(( (e - s) / 1000000 / n )) ms per test"
python3 - <<'PY'
import glob,re
def cov(p):
    out=set()
    for ln in open(p).read().splitlines()[1:]:
        m=re.match(r"(.+) (\d+) (\d+)$",ln)
        if m and int(m.group(3))>0: out.add(m.group(1))
    return out
allc=cov("/tmp/all.out"); union=set(); per=[]
for f in sorted(glob.glob("/tmp/t_*.out")):
    c=cov(f); per.append(len(c)); union|=c
print(f"covered blocks: whole run {len(allc)}; union of the per-test runs {len(union)}; equal: {union==allc}; per-test min/max {min(per)}/{max(per)}")
PY
echo "### II.D package-level change impact (go list), module-local packages"
mod=$(go list -m); tot=$(go list ./... | wc -l); echo "packages in the module: $tot"
echo "deps of ./core/cabinet inside the module: $(go list -deps ./core/cabinet | grep -c "^$mod")"
for p in pkg/canonicaljson core/cabinet; do
  imp=$(go list -f '{{.ImportPath}} {{join .Imports " "}} {{join .TestImports " "}}' ./... | awk -v p="$mod/$p" '{for(i=2;i<=NF;i++) if($i==p){print $1; break}}' | wc -l)
  echo "packages that import $p directly (incl. tests): $imp"
done
