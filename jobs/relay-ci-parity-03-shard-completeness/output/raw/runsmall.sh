#!/usr/bin/env bash
export PATH=/ch/bin:$PATH CARGO_HOME=/ch CARGO_TARGET_DIR=/t
git config --global --add safe.directory /w; cd /w
rm -rf /out/mo; mkdir -p /out/mo
# a small real run: only the mutants of canonical_number
cargo mutants --workspace --re 'canonical_number' --output /out/mo --list >/out/small-list.txt 2>/dev/null; echo "small listing: $(wc -l </out/small-list.txt) mutants"
cargo mutants --workspace --re 'canonical_number' --output /out/mo > /out/small-run.log 2>&1; echo "small run exit=$?"
ls -R /out/mo | head -20
