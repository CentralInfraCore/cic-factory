#!/usr/bin/env bash
# PR-06 B: the FFI airlock tests must be able to fail. Each tooth removes one guard of ffi/src/lib.rs on a scratch copy;
# the named test must then fail. The same tests must pass on the untouched copy.
set -uo pipefail
SRC=${1:?usage: teeth_ffi.sh CHECKOUT}
# the crate under test is rebuilt every time: a build cache shared with another (mutated) copy must never decide a verdict
run_tests() { (cd "$1" && cargo clean -p cic-ffi >/dev/null 2>&1; cargo test -p cic-ffi --locked 2>&1); }
tooth() { # name, anchor, replacement, test that must fail
  local name=$1 anchor=$2 repl=$3 expect=$4 d out
  d=$(mktemp -d); cp -r "$SRC/." "$d/"
  python3 - "$d/ffi/src/lib.rs" "$anchor" "$repl" <<'PY'
import sys
p, a, b = sys.argv[1:]
s = open(p).read()
assert s.count(a) == 1, f"anchor occurs {s.count(a)} times"
open(p, "w").write(s.replace(a, b))
PY
  out=$(run_tests "$d")
  if echo "$out" | grep -qE "test tests::${expect} \.\.\. FAILED|${expect}.*(SIGSEGV|signal)"; then echo "OK   tooth '$name': ${expect} fails as it must";
  elif echo "$out" | grep -qE "SIGSEGV|signal: 11|process didn't exit successfully"; then echo "OK   tooth '$name': the test process crashed (${expect} cannot pass)";
  else echo "FAIL tooth '$name': ${expect} did not fail"; echo "$out" | tail -6; fi
  rm -rf "$d"
}
out=$(run_tests "$SRC"); if echo "$out" | grep -q "test result: ok. 30 passed"; then echo "OK   untouched copy: 30 tests pass"; else echo "FAIL untouched copy"; echo "$out" | tail -5; exit 1; fi
tooth "panic backstop removed" 'let Ok(Some(result)) = catch_unwind(move || core(&owned)) else {' 'let Ok(Some(result)) = Ok::<_, ()>(core(&owned)) else {' 'a_panic_in_the_core_is_contained_and_reported_as_a_rejection'
tooth "empty-result check removed" '    if result.is_empty() {
        return ptr::null_mut();
    }' '' 'an_empty_core_result_is_a_rejection_not_an_empty_buffer'
tooth "null pointer guard removed" 'let owned: Vec<u8> = if ptr.is_null() || len == 0 {' 'let owned: Vec<u8> = if len == 0 {' 'a_null_pointer_with_a_nonzero_length_is_read_as_empty_and_never_dereferenced'
tooth "out_len not zeroed up front" '    *out_len = 0;

    // Reject oversized input' '    // Reject oversized input' 'every_rejection_path_leaves_out_len_at_zero'
