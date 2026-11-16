#!/usr/bin/env bash
# PR-06 B: the module-identity negative tests must be able to fail. Each tooth removes one production check on a
# scratch copy of the tree; the named test must then fail, and the same test must pass on the untouched copy.
set -uo pipefail
SRC=${1:?usage: teeth_module_identity.sh CHECKOUT}
export GOFLAGS="-mod=readonly -buildvcs=false"
run_tests() { (cd "$1" && go test -count=1 -run "TestLoadModule_SignerCertificate|TestLoadModule_RejectedSigner" ./cmd/relay/ 2>&1); }
tooth() { # name, anchor, replacement, expected-failing-subtest-regex
  local name=$1 anchor=$2 repl=$3 expect=$4 d
  d=$(mktemp -d); cp -r "$SRC/." "$d/"
  python3 - "$d/cmd/relay/bootstrap.go" "$anchor" "$repl" <<'PY'
import sys
p, a, b = sys.argv[1:]
s = open(p).read()
assert s.count(a) == 1, f"anchor occurs {s.count(a)} times"
open(p, "w").write(s.replace(a, b))
PY
  local out; out=$(run_tests "$d")
  if echo "$out" | grep -qE -- "--- FAIL: .*${expect}"; then echo "OK   tooth '$name': the test fails as it must (${expect})"; else echo "FAIL tooth '$name': no failing test matching ${expect}"; echo "$out" | tail -5; fi
  rm -rf "$d"
}
if run_tests "$SRC" | grep -q '^ok'; then echo "OK   untouched copy: the tests pass"; else echo "FAIL untouched copy: the tests do not pass"; exit 1; fi
tooth "chain verification skipped" '} else if !pkiAssets.TrustStoreLoaded {' '} else if true {' 'expired_signer'
tooth "CRLs not passed to the verification" '					CRLs:          pkiAssets.CRLs,
					CRLFreshness:  pkiAssets.CRLFreshness,
				}
				chains, verifyErr' '					CRLFreshness:  pkiAssets.CRLFreshness,
				}
				chains, verifyErr' 'revoked_signer'
