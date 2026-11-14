#!/usr/bin/env bash
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t2
git config --global --add safe.directory /w; cd /w
sed -i '1s#^#// only a comment\n#' cic-canonical/src/lib.rs; git diff -- '*.rs' > /tmp/empty.diff
cargo mutants --workspace --list --json --in-diff /tmp/empty.diff >/tmp/o 2>/tmp/e; echo "A empty --json: exit=$? stdout=[$(cat /tmp/o)] bytes=$(wc -c </tmp/o) stderr=[$(tr '\n' ' ' </tmp/e)]"
cargo mutants --workspace --list --json --in-diff /nonexistent.diff >/tmp/o 2>/tmp/e; echo "B unreadable: exit=$? bytes=$(wc -c </tmp/o)"
cargo mutants --workspace --list --json --in-diff /tmp/empty.diff | sha256sum
git checkout -q -- .
