#!/usr/bin/env bash
# the CURRENT per-package coverage line of verify.yml, run on broken profiles (set -euo pipefail, as in the step)
try() {  # $1 label  $2 profile path
  bash -c 'set -euo pipefail
  p=example.com/m/pkg
  pc=$(go tool cover -func='"$2"' | awk "END{gsub(/%/,\"\"); print \$3+0}")
  echo "pc=[$pc]"
  min=80
  awk -v p="$pc" -v m="$min" "BEGIN{ if (p+0 < m+0) { print \"FAIL: coverage below threshold\"; exit 1 } }"
  echo "-> step would PASS this package"' ; echo "[$1] exit=$?"
}
cd /tmp; go version
: > empty.out;                         try "empty file"      /tmp/empty.out
printf 'mode: set\n' > modeonly.out;   try "mode line only"  /tmp/modeonly.out
printf 'garbage\n' > garbage.out;      try "garbage"         /tmp/garbage.out
try "missing file" /tmp/nope.out
