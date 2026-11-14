export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w; git checkout -q -- .
echo "### exit codes of cargo-mutants itself (stdout and stderr kept apart)"
sed -i '1s#^#// only a comment\n#' cic-canonical/src/lib.rs; git diff -- '*.rs' > /tmp/empty.diff
cargo mutants --workspace --list --in-diff /tmp/empty.diff >/tmp/o 2>/tmp/e; echo "A valid, empty listing (diff applies, no mutable code): exit=$? stdout_bytes=$(wc -c </tmp/o) stderr=[$(tr '\n' ' ' </tmp/e)]"
cargo mutants --workspace --list --in-diff /nonexistent.diff >/tmp/o 2>/tmp/e; echo "B failed listing (unreadable diff):                    exit=$? stdout_bytes=$(wc -c </tmp/o)"
printf '\nexclude_re = ["("]\n' >> .cargo/mutants.toml
cargo mutants --workspace --list >/tmp/o 2>/tmp/e; echo "C failed listing (broken .cargo/mutants.toml):         exit=$? stdout_bytes=$(wc -c </tmp/o)"
git checkout -q -- .cargo/mutants.toml
echo; echo "### the workflow line, bash -e (GitHub default), for A / B / C"
cnt() { bash -e -c 'n=$('"$1"' 2>/dev/null | grep -c . || true); echo "n=$n"'; }
cnt "cargo mutants --workspace --list --in-diff /tmp/empty.diff"
cnt "cargo mutants --workspace --list --in-diff /nonexistent.diff"
echo "(C):"; printf '\nexclude_re = ["("]\n' >> .cargo/mutants.toml; cnt "cargo mutants --workspace --list"; git checkout -q -- .cargo/mutants.toml
echo; echo "### same line WITHOUT '|| true', bash -e (no pipefail): A / B"
nt() { bash -e -c 'n=$('"$1"' 2>/dev/null | grep -c .); echo "n=$n"'; echo "step exit code: $?"; }
nt "cargo mutants --workspace --list --in-diff /tmp/empty.diff"
nt "cargo mutants --workspace --list --in-diff /nonexistent.diff"
echo; echo "### with 'bash -eo pipefail', '|| true' kept: B (is the failure then visible?)"
bash -eo pipefail -c 'n=$(cargo mutants --workspace --list --in-diff /nonexistent.diff 2>/dev/null | grep -c . || true); echo "n=$n"'; echo "step exit code: $?"
echo; echo "### a failure-aware form: list to a file, check the listing command first, then count"
cat > /tmp/safe.sh <<'X'
set -eu
cargo mutants --workspace --list --in-diff "$1" > /tmp/list.txt 2>/tmp/list.err || { echo "LISTING FAILED (exit $?)"; cat /tmp/list.err; exit 1; }
n=$(grep -c . /tmp/list.txt || true); echo "n=$n (listing succeeded)"
X
bash /tmp/safe.sh /tmp/empty.diff; echo "exit=$?"; bash /tmp/safe.sh /nonexistent.diff; echo "exit=$?"
git checkout -q -- .
