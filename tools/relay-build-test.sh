#!/usr/bin/env bash
# relay-build-test.sh — end-to-end test harness for relay-driven build + build_hash
#
# Exercises the running relay over HTTP only. Does NOT modify CIC-Relay
# (that repo is read-only from here).
#
# What each test proves is documented in docs/relay-build-hash-test.md.
# The decisive one is T5: if build_hash does not change when the source
# changes, the hash does not attest the built source.
#
# Usage:
#   RELAY_URL=http://127.0.0.1:8080 \
#   PIPE_REPO_URL=file:///src/cic-schemas \
#   PIPE_SCHEMA=postgresql PIPE_VERSION=v0.18.0 PIPE_BRANCH=postgres/dev \
#   PIPE_BRANCH_B=postgres/other \
#     ./tools/relay-build-test.sh
#
# Exit 0 = every executed test passed. Exit 1 = at least one failed.
# Tests that cannot run (missing input) are SKIPped, never silently passed.
set -uo pipefail

RELAY_URL="${RELAY_URL:-http://127.0.0.1:8080}"
PIPE_REPO_URL="${PIPE_REPO_URL:-}"
PIPE_SCHEMA="${PIPE_SCHEMA:-}"
PIPE_VERSION="${PIPE_VERSION:-}"
PIPE_BRANCH="${PIPE_BRANCH:-}"
PIPE_BRANCH_B="${PIPE_BRANCH_B:-}"   # second, DIFFERENT source for T5
OUTDIR="${OUTDIR:-./relay-build-test-out}"

command -v jq >/dev/null || { echo "FATAL: jq is required"; exit 1; }
mkdir -p "$OUTDIR"

PASS=0; FAIL=0; SKIP=0
ok()   { echo "  [PASS] $*"; PASS=$((PASS+1)); }
bad()  { echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }
skip() { echo "  [SKIP] $*"; SKIP=$((SKIP+1)); }
hdr()  { echo ""; echo "=== $* ==="; }

# ---------------------------------------------------------------- T0 preflight
hdr "T0 — preflight: is the relay reachable?"
for ep in /healthz /readyz; do
    code=$(curl -s -o "$OUTDIR/t0${ep//\//_}.body" -w '%{http_code}' --max-time 10 "$RELAY_URL$ep" 2>/dev/null)
    if [[ "$code" == "200" ]]; then
        ok "$ep -> 200"
    else
        bad "$ep -> ${code:-no response}. Relay not reachable at $RELAY_URL"
    fi
done
if [[ "$FAIL" -gt 0 ]]; then
    echo ""
    echo "Aborting: the relay must be running before any further test is meaningful."
    echo "Note: docker-compose.yml in CIC-Relay defines builder containers only —"
    echo "there is no relay service in it, and the root Dockerfile is the Python"
    echo "schema-compiler image. Starting the relay is currently a manual step."
    exit 1
fi

# ------------------------------------------------------------ pipeline helper
# run_pipeline <branch> <out-prefix> -> writes <prefix>.json, echoes http code
run_pipeline() {
    local branch="$1" prefix="$2"
    local body
    body=$(jq -n --arg s "$PIPE_SCHEMA" --arg v "$PIPE_VERSION" \
                 --arg b "$branch" --arg r "$PIPE_REPO_URL" \
                 '{schema:$s, version:$v, branch:$b, repo_url:$r}')
    curl -s -o "$prefix.json" -w '%{http_code}' --max-time 900 \
         -X POST -H 'Content-Type: application/json' \
         -d "$body" "$RELAY_URL/v1/schemas/pipeline" 2>/dev/null
}

have_pipe_inputs=1
for v in PIPE_REPO_URL PIPE_SCHEMA PIPE_VERSION PIPE_BRANCH; do
    [[ -n "${!v}" ]] || { have_pipe_inputs=0; }
done

# ------------------------------------------------------------------ T1 happy
hdr "T1 — pipeline run produces build_hash + proof_trace"
BUILD_HASH_A=""; VROOT_A=""
if [[ "$have_pipe_inputs" -eq 0 ]]; then
    skip "T1: set PIPE_REPO_URL, PIPE_SCHEMA, PIPE_VERSION, PIPE_BRANCH"
else
    code=$(run_pipeline "$PIPE_BRANCH" "$OUTDIR/run_a")
    if [[ "$code" != "200" ]]; then
        bad "pipeline -> HTTP $code; body: $(head -c 300 "$OUTDIR/run_a.json" 2>/dev/null)"
    else
        BUILD_HASH_A=$(jq -r '.artifact.build_hash // empty' "$OUTDIR/run_a.json")
        VROOT_A=$(jq -r '.artifact.verification_root // empty' "$OUTDIR/run_a.json")
        CHAIN_A=$(jq -r '.proof_trace.chain_hash // .proof_trace.ChainHash // empty' "$OUTDIR/run_a.json")
        [[ -n "$BUILD_HASH_A" ]] && ok "build_hash present: $BUILD_HASH_A" \
                                 || bad "artifact.build_hash missing"
        [[ -n "$VROOT_A" ]] && ok "verification_root present: $VROOT_A" \
                            || bad "artifact.verification_root missing"
        [[ -n "$CHAIN_A" ]] && ok "proof_trace.chain_hash present: $CHAIN_A" \
                            || bad "proof_trace.chain_hash missing"
        jq -r '.proof_trace.steps // [] | length as $n | "  steps in trace: \($n)"' "$OUTDIR/run_a.json"
    fi
fi

# ------------------------------------------------------- T2 verify roundtrip
hdr "T2 — /v1/proof/verify accepts the unmodified artifact"
if [[ ! -s "$OUTDIR/run_a.json" ]]; then
    skip "T2: no pipeline result from T1"
else
    jq '.proof_trace' "$OUTDIR/run_a.json" > "$OUTDIR/trace_a.json"
    code=$(curl -s -o "$OUTDIR/verify_a.json" -w '%{http_code}' --max-time 60 \
        -X POST -H 'Content-Type: application/json' \
        -d @"$OUTDIR/trace_a.json" "$RELAY_URL/v1/proof/verify")
    valid=$(jq -r '.valid // empty' "$OUTDIR/verify_a.json" 2>/dev/null)
    if [[ "$code" == "200" && "$valid" == "true" ]]; then
        ok "verify(unmodified) -> valid=true"
    else
        bad "verify(unmodified) -> HTTP $code valid=$valid; errors: $(jq -c '.errors // []' "$OUTDIR/verify_a.json" 2>/dev/null)"
    fi
fi

# --------------------------------------------------- T3 tamper: chain_hash
hdr "T3 — verify REJECTS a tampered chain_hash"
if [[ ! -s "$OUTDIR/trace_a.json" ]]; then
    skip "T3: no trace from T2"
else
    jq '.chain_hash = (.chain_hash | sub("^.";"0"))' "$OUTDIR/trace_a.json" > "$OUTDIR/trace_t3.json" 2>/dev/null \
      || jq '.chain_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"' \
           "$OUTDIR/trace_a.json" > "$OUTDIR/trace_t3.json"
    curl -s -o "$OUTDIR/verify_t3.json" --max-time 60 \
        -X POST -H 'Content-Type: application/json' \
        -d @"$OUTDIR/trace_t3.json" "$RELAY_URL/v1/proof/verify" >/dev/null
    valid=$(jq -r '.valid // empty' "$OUTDIR/verify_t3.json" 2>/dev/null)
    if [[ "$valid" == "false" ]]; then
        ok "tampered chain_hash rejected"
    else
        bad "tampered chain_hash ACCEPTED (valid=$valid) — verification is not binding"
    fi
fi

# ------------------------------------------------ T4 tamper: step output_hash
hdr "T4 — verify REJECTS a tampered step output_hash"
if [[ ! -s "$OUTDIR/trace_a.json" ]]; then
    skip "T4: no trace from T2"
else
    nsteps=$(jq -r '.steps // [] | length' "$OUTDIR/trace_a.json")
    if [[ "${nsteps:-0}" -lt 1 ]]; then
        skip "T4: trace has no steps to tamper with"
    else
        jq '.steps[0].output_hash = "sha256:deadbeef"' "$OUTDIR/trace_a.json" > "$OUTDIR/trace_t4.json"
        curl -s -o "$OUTDIR/verify_t4.json" --max-time 60 \
            -X POST -H 'Content-Type: application/json' \
            -d @"$OUTDIR/trace_t4.json" "$RELAY_URL/v1/proof/verify" >/dev/null
        valid=$(jq -r '.valid // empty' "$OUTDIR/verify_t4.json" 2>/dev/null)
        if [[ "$valid" == "false" ]]; then
            ok "tampered step output_hash rejected (chain recomputation binds the steps)"
        else
            bad "tampered step ACCEPTED (valid=$valid) — steps are NOT bound to chain_hash"
        fi
    fi
fi

# ------------------------------------- T5 DECISIVE: does build_hash track source?
hdr "T5 — DECISIVE: does build_hash change when the SOURCE changes?"
if [[ -z "$BUILD_HASH_A" ]]; then
    skip "T5: no build_hash from T1"
elif [[ -z "$PIPE_BRANCH_B" ]]; then
    skip "T5: set PIPE_BRANCH_B to a branch with DIFFERENT content than PIPE_BRANCH"
else
    code=$(run_pipeline "$PIPE_BRANCH_B" "$OUTDIR/run_b")
    if [[ "$code" != "200" ]]; then
        bad "second pipeline run -> HTTP $code"
    else
        BUILD_HASH_B=$(jq -r '.artifact.build_hash // empty' "$OUTDIR/run_b.json")
        VROOT_B=$(jq -r '.artifact.verification_root // empty' "$OUTDIR/run_b.json")
        echo "  branch A ($PIPE_BRANCH):   build_hash=$BUILD_HASH_A"
        echo "  branch B ($PIPE_BRANCH_B): build_hash=$BUILD_HASH_B"
        if [[ "$BUILD_HASH_A" != "$BUILD_HASH_B" ]]; then
            ok "build_hash DIFFERS across sources — it tracks the built source"
        else
            bad "build_hash IDENTICAL across different sources — it does NOT attest the built source"
        fi
        echo "  verification_root A: $VROOT_A"
        echo "  verification_root B: $VROOT_B"
        if [[ "$VROOT_A" == "$VROOT_B" ]]; then
            echo "  [NOTE] verification_root also identical — consistent with the audit finding that"
            echo "         it is built from the relay's own build-time constants (main.go:713-715)."
        fi
    fi
fi

# ---------------------------------------------------------- T6 determinism
hdr "T6 — is build_hash stable for the SAME input?"
if [[ -z "$BUILD_HASH_A" ]]; then
    skip "T6: no build_hash from T1"
else
    code=$(run_pipeline "$PIPE_BRANCH" "$OUTDIR/run_a2")
    if [[ "$code" != "200" ]]; then
        bad "repeat run -> HTTP $code"
    else
        BUILD_HASH_A2=$(jq -r '.artifact.build_hash // empty' "$OUTDIR/run_a2.json")
        if [[ "$BUILD_HASH_A" == "$BUILD_HASH_A2" ]]; then
            ok "build_hash reproducible for identical input"
        else
            bad "build_hash differs for identical input: $BUILD_HASH_A vs $BUILD_HASH_A2 (nondeterminism)"
        fi
    fi
fi

# ------------------------------------------------------------------ summary
echo ""
echo "================================================"
echo "  PASS=$PASS  FAIL=$FAIL  SKIP=$SKIP"
echo "  Raw responses kept in: $OUTDIR/"
echo "================================================"
[[ "$SKIP" -gt 0 ]] && echo "  NOTE: SKIP is not PASS. A skipped test proved nothing."
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
