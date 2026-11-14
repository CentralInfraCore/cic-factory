#!/usr/bin/env bash
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t2
git config --global --add safe.directory /w; cd /w
f=http-executor/src/lib.rs
echo "### 1. a change INSIDE the #[cfg(test)] module of $f (line 815)"
sed -i '815s#$# // test-only edit#' $f; git diff -U0 -- $f | grep '^@@'
git diff -- '*.rs' > /tmp/t.diff
cargo mutants --workspace --list --in-diff /tmp/t.diff 2>/tmp/e | wc -l | sed 's/^/mutants listed: /'; echo "cargo-mutants says: $(tr '\n' ' ' </tmp/e | cut -c1-120)"
git checkout -q -- .
echo "### 2. a change in PRODUCTION code of the same file (line 100)"
sed -i '100s#$# // prod edit#' $f; git diff -U0 -- $f | grep '^@@'
git diff -- '*.rs' > /tmp/p.diff
cargo mutants --workspace --list --in-diff /tmp/p.diff 2>/dev/null | wc -l | sed 's/^/mutants listed: /'
git checkout -q -- .
echo "### 3. a change that REMOVES an assertion in the test module (a weaker test)"
n=$(awk 'NR>809 && /assert/ {print NR; exit}' $f); echo "first assert in test module at line $n: $(sed -n ${n}p $f)"
sed -i "${n}d" $f; git diff -U0 -- $f | grep '^@@'
git diff -- '*.rs' > /tmp/w.diff
cargo mutants --workspace --list --in-diff /tmp/w.diff 2>/tmp/e | wc -l | sed 's/^/mutants listed: /'
git checkout -q -- .
