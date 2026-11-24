#!/bin/bash
# Fetch the token issuer's public keys (JWKS) into ONE new file: the TRUST ROOT of read-me1.py.
# usage: fetch-jwks.sh OUTFILE
#   Run it on the owner's machine, over TLS, DIRECTLY from the issuer, AFTER the run (key rotation), and
#   keep OUTFILE OUTSIDE the evidence directory: read-me1.py refuses a key file inside it. OUTFILE must
#   not exist. The answer must be a JSON object with a non-empty `keys` array, else nothing is kept.
set -euo pipefail
OUT=${1:?usage: fetch-jwks.sh OUTFILE}
URL=https://token.actions.githubusercontent.com/.well-known/jwks
[ ! -e "$OUT" ] || { echo "refusing: $OUT already exists" >&2; exit 1; }
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
curl -sSf "$URL" > "$TMP"
jq -e '(type == "object") and (.keys | type == "array") and (.keys | length > 0)' "$TMP" > /dev/null || { echo "refusing: the answer is not a JWKS" >&2; exit 1; }
mv "$TMP" "$OUT"
trap - EXIT
echo "fetched $(jq '.keys | length' "$OUT") key(s) from $URL into $OUT (sha256 $(sha256sum "$OUT" | cut -d' ' -f1))"
