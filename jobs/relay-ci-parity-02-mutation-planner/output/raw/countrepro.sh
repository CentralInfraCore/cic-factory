#!/usr/bin/env bash
# PR-02: the new fail-closed counter against the real cargo-mutants (cases A/B/C of PR-01).
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
cargo mutants --version
C="python3 scripts/count_mutants.py --out /tmp/list.txt --"
sed -i '1s#^#// only a comment\n#' cic-canonical/src/lib.rs; git diff -- '*.rs' > /tmp/empty.diff
echo "### A valid, empty listing"
n=$($C cargo mutants --workspace --list --in-diff /tmp/empty.diff 2>/tmp/e); rc=$?; echo "count_mutants exit=$rc n=[$n] stderr=[$(tr '\n' ' ' </tmp/e)]"
echo "### B unreadable --in-diff"
n=$($C cargo mutants --workspace --list --in-diff /nonexistent.diff 2>/tmp/e); rc=$?; echo "count_mutants exit=$rc n=[$n] stderr=[$(tr '\n' ' ' </tmp/e | cut -c1-300)]"
echo "### C broken .cargo/mutants.toml"
printf '\nexclude_re = ["("]\n' >> .cargo/mutants.toml
n=$($C cargo mutants --workspace --list 2>/tmp/e); rc=$?; echo "count_mutants exit=$rc n=[$n] stderr=[$(tr '\n' ' ' </tmp/e | cut -c1-300)]"
git checkout -q -- .cargo/mutants.toml
echo "### D the workflow form under bash -e: B must now fail the step"
bash -e -c 'n=$(python3 scripts/count_mutants.py -- cargo mutants --workspace --list --in-diff /nonexistent.diff 2>/dev/null) || { echo "step fails: listing failed"; exit 1; }; echo "n=$n"'; echo "step exit code: $?"
echo "### E FULL listing (rust_full): a real number"
n=$($C cargo mutants --workspace --list 2>/dev/null); echo "count_mutants exit=$? n=[$n] listing_lines=$(wc -l </tmp/list.txt)"
git checkout -q -- .
