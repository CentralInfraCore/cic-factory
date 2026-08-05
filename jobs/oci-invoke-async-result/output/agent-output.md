# oci-invoke-async-result — agent output

## kb_focus read (mandatory first step)

All three chunks resolved and were read before any code change:

- `c761` → `CIC-Relay/core/cabinet/proof_trace.yaml`, struct `ProofTraceStep` —
  "records the cryptographic fingerprint of a single workflow step."
- `c762` → `CIC-Relay/core/cabinet/proof_trace.yaml`, struct `ProofTrace` — the
  immutable, deterministic audit record; `SourceDigest`/`ChainHash` anchor it to
  source and chain the steps together.
- `c163` → `CIC-Relay/ai/SYSTEM_CONTEXT.md`, section "A ProofTrace" — the
  worked example of `steps: [{name, input_hash, output_hash, module}]` chained
  into `chain_hash`, optionally Vault-signed.

None were empty or missing. They ground the *why*: a ProofTrace step records
what a module claimed happened. A step that claims `"succeeded"` for a `202
Accepted` async operation is a false claim baked into an otherwise
cryptographically sound record — exactly what task A fixes.

## What I did

### A) `Invoke()` async result (primary, done)

- `operationResult` (`module/provider.go`) gained `WorkRequestID string
  \`json:"work_request_id,omitempty"\`` — same tag/semantics as
  `executionStep.WorkRequestID`.
- `Invoke()` now reads `headers["opc-work-request-id"]` into it unconditionally
  (mirrors `executeOne`'s unconditional read at the old `:985`).
- Status logic changed from `Status: "succeeded"` hardcoded, downgraded only on
  `>= 400`, to a three-way switch: `>= 400` → `failed` (unchanged, see below);
  else `WorkRequestID != ""` → `accepted`; else → `succeeded`.
- I followed `Destroy()`'s rule (`:610-611` before this change), not
  `Execute`/`executeOne`'s, because the spec named `Destroy`'s as the one
  "verified against real OCI" — `Execute`'s async-flag-then-downgrade shape is
  equivalent for a single step but `Destroy`'s inline `else if` is the more
  direct match for `Invoke`'s single-operation shape (no loop, no separate
  `async` bool needed). Net effect (accepted/succeeded/failed per case) is
  identical between the two existing patterns for a single step; I did not find
  a case where they'd disagree, so there is no eltérés to report beyond this
  structural note.
- The `>= 400` branch is untouched byte-for-byte in its logic (still only sets
  `Status`/`Error` from `pe.Message`) — per hard constraint A.4.

### B) `Destroy()` 404 loses the OCI code/message (secondary, done)

- The 404 short-circuit in `Destroy()` now runs the body through `ociError()`
  (same function every other branch already uses) instead of building a bare
  `&providerError{Class: classNotFound, Message: "..."}`. `ociError` already
  sets `Class: classNotFound` for a 404, so this is reuse, not new logic. The
  OCI message is folded into the existing synthesised text as `"resource
  already gone: <ocid> (<oci message>)"` rather than replacing it — both the
  human-readable "already gone" framing and the OCI message survive.
  `ProviderCode` is carried on the `providerError` returned by `ociError`
  directly.
- `Class: not-found` and the envelope-level shape (`errResult`, not a
  step-embedded error) are both unchanged, as the spec required.

Neither A nor B turned out larger than scoped — both landed as described.

## What I did NOT do

- Did not touch `Execute`/`executeOne`'s existing async logic (`:948-1010`
  region) — it was already correct per the spec, and constraint 3 forbids
  touching primitives/YANG schema, which is unrelated but I also avoided any
  scope creep into working code.
- Did not re-run the manual real-OCI harness — constraint 1 forbids it in this
  job; see `orchestrator-verification.md` for the recipe.
- Did not mark the `invoke` row in `docs/design/manual-verification.md` as
  `verified` for the fix — updated it to say the fix landed and is
  fixture-proven, explicitly flagged "not yet re-run against real OCI" (hard
  constraint 6).
- Did not open a PR and did not push to `main`/`devel` — pushed only to
  `feature/oci-invoke-async-result` on `cic-module-oracle-cloud`, per the job's
  git instructions.

## Environment friction hit and worked around

- The module repo's `docker compose run --rm setup` (populates `p_venv` for
  the Python tooling `make check` needs) failed on this host with
  `PermissionError: Permission denied: '/app/p_venv/...'` — the bind-mounted
  `p_venv/` directory had been created `root:root` by an earlier container run
  and I have no `sudo`/`chown` access to fix it. Worked around by copying an
  already-populated `p_venv/` from a sibling clone of the same repo
  (`/home/sinkog/sync/git.partners/CentralInfraCore/cic-module-oracle-cloud/p_venv`)
  instead of reinstalling. `p_venv/` is gitignored, so this has no effect on
  the commit. Flagging this for whoever runs this job's recipe next — `docker
  compose run --rm setup` may need a host-side `chown` first, or a fix to the
  compose file's user mapping.
- Confirmed the input.md's warning about untracked `.yaml` sidecars firsthand:
  `go test`/`go build` (and `make wasm.build`'s TinyGo step) leave dozens of
  untracked `module/*.yaml`, `tools/**/*.yaml`, `tests/**/*.yaml` files (they
  look like per-source-file doc/graph companions, generated by something in
  the build/test toolchain — not investigated further, out of scope). Every
  commit in this job used an explicit path list and `git status --short` was
  checked before each one; these files were deleted, never staged.
- `docker-compose.yml`'s `version:` key is obsolete per Docker Compose's own
  warning on every invocation — cosmetic, not touched (out of scope for this
  job).

## Verification run in this job (fixture-level, not real OCI)

All of these were run inside the `builder` container via `docker compose run`
(the Go toolchain lives there, not on the host):

- `go test ./module/...` (full suite) — green, including the three new/changed
  fixtures.
- Negative-direction check for A: reverted `Invoke()`'s status logic to the old
  hardcoded-`succeeded` form (keeping the new struct field so it still
  compiles) and re-ran — `TestInvokeAsync` failed exactly as expected
  (`status = "succeeded", want accepted`); `TestInvoke` and
  `TestInvokeFailedStatusUnchanged` stayed green. Restored the fix and
  confirmed the working tree was byte-identical to before the revert
  (`diff` — no output).
- Negative-direction check for B: reverted the 404 branch to the old bare
  `providerError`, re-ran — `TestDestroyNotFoundKeepsProviderCode` failed
  (`provider_code = ""`, message missing the OCI text); restored, confirmed
  identical.
- `make check`, `make golang.quality`, `make wasm.build`, `make wasm.test`,
  `make manifest-update` + `make manifest-verify`, `make docs.link-check` — all
  green, run after the fix was in place. Full logs and exit codes are in
  `claim-evidence.md`.

See `claim-evidence.md` for the point-by-point DoD table and
`reachability.md` for the production call path proof.
