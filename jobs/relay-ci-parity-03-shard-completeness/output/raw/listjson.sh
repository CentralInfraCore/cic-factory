#!/usr/bin/env bash
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
cargo mutants --version
cargo mutants --workspace --list --json > /out/list.json 2>/out/list.err; echo "list --json exit=$?"
cargo mutants --workspace --list > /out/list.txt 2>/dev/null; echo "list exit=$? lines=$(wc -l </out/list.txt)"
python3 - <<'PY'
import json
d=json.load(open("/out/list.json")); print("entries",len(d)); print(json.dumps(d[0],indent=1)); print(sorted({k for e in d for k in e}))
PY
head -3 /out/list.txt
