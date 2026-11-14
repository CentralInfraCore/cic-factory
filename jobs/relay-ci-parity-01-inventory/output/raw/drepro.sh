export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; git config --global user.email a@b; git config --global user.name x
cd /w
echo "### environment"; rustc --version; cargo --version; cargo mutants --version; git rev-parse HEAD
# GitHub's default shell for `run:` without `shell:` is `bash -e {0}` (no pipefail). We emulate it with `bash -e`.
cat > /tmp/count.sh <<'X'
# the exact lines of mutation-pr.yml:65 / nightly.yml:148 (the listing command is parameterised by $LIST_CMD)
n=$($LIST_CMD | grep -c . || true)
echo "n=$n"
X
run() { echo; echo "\$ [$1]"; LIST_CMD="$2" bash -e /tmp/count.sh; echo "step exit code: $?"; }
echo; echo "### 1. valid full listing (nightly.yml:148 form)"
run "valid full listing" "cargo mutants --workspace --list"
echo; echo "### 2. valid diff with a real code change (mutation-pr.yml:65 form)"
sed -i '0,/-> u32 {/s//-> u32 {\n    let _ = 0;/' ffi/src/lib.rs 2>/dev/null; git diff --stat -- '*.rs' | tail -1
git diff -- '*.rs' > /tmp/pr.diff; wc -l /tmp/pr.diff
run "in-diff, real change" "cargo mutants --workspace --list --in-diff /tmp/pr.diff"
git checkout -q -- .
echo; echo "### 3. valid, legitimately empty: a diff that touches no mutable code (doc comment only)"
sed -i '1s#^#// only a comment\n#' cic-canonical/src/lib.rs; git diff -- '*.rs' > /tmp/empty.diff
run "in-diff, comment only" "cargo mutants --workspace --list --in-diff /tmp/empty.diff"
git checkout -q -- .
echo; echo "### 4. the listing command FAILS (stderr shown, as in the CI log)"
echo "--- 4a. --in-diff points at a file that cannot be read"
run "in-diff, unreadable diff file" "cargo mutants --workspace --list --in-diff /nonexistent.diff"
echo "--- 4b. the same command with the pipe checked (what a fail-closed step would see)"
( set -o pipefail; cargo mutants --workspace --list --in-diff /nonexistent.diff 2>&1 | grep -c . ; echo "pipefail pipeline exit: ${PIPESTATUS[0]} / $?" ) || true
echo "--- 4c. only the cargo-mutants config is broken (build and tests are untouched)"
cp .cargo/mutants.toml /tmp/mutants.toml.bak
printf '\nexclude_re = ["("]\n' >> .cargo/mutants.toml
echo "listing alone:"; cargo mutants --workspace --list >/tmp/l.out 2>/tmp/l.err; echo "exit=$? stdout_lines=$(wc -l </tmp/l.out)"; head -c 600 /tmp/l.err
run "full listing, broken config" "cargo mutants --workspace --list"
echo "--- 4d. unpinned tool version drift is not reproduced here (ci installs 'tool: cargo-mutants' with no version)"
cp /tmp/mutants.toml.bak .cargo/mutants.toml
echo "--- 4e. a failed listing, then the plan decision as in the workflow"
n=$(cargo mutants --workspace --list --in-diff /nonexistent.diff 2>/dev/null | grep -c . || true); shards=0; if [ "$n" -gt 0 ]; then shards=$(( (n + 39) / 40 )); fi; echo "n=$n shards=$shards  -> rust job condition (rust_shards != '0') = $([ "$shards" != 0 ] && echo run || echo SKIPPED)"
echo; echo "### 5. without '|| true' under bash -e (what the workflow would do if only the || true were removed)"
LIST_CMD="cargo mutants --workspace --list --in-diff /tmp/empty.diff" bash -e -c 'n=$($LIST_CMD | grep -c .); echo "n=$n"'; echo "step exit code: $?   (a legitimately empty listing now fails the step)"
