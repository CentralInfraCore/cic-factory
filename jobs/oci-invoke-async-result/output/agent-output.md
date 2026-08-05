Both pushed successfully. Summary of the work:

**cic-module-oracle-cloud** (`feature/oci-invoke-async-result`, commit `17c8549`, CI green matching this headSha):
- **A (primary):** `operationResult` gained `work_request_id`; `Invoke()` now reads `opc-work-request-id` and reports `status: "accepted"` instead of a false `"succeeded"` when the op is async, mirroring `Destroy()`'s already-verified rule. The `>=400` branch is untouched, as required.
- **B (secondary):** `Destroy()`'s 404 short-circuit now routes through `ociError()` like every other error path, so OCI's native `provider_code`/message survive instead of being silently dropped, while keeping `Class: not-found` and the envelope-level shape.
- Three new fixtures (`TestInvokeAsync`, `TestInvokeFailedStatusUnchanged`, `TestDestroyNotFoundKeepsProviderCode`), each proven to fail against the pre-fix code (negative direction shown for both A and B).
- `make check`, `golang.quality`, `wasm.build`, `wasm.test`, `manifest-verify`, `docs.link-check` all green; `MANIFEST.sha256`, `module.wasm`, `project.yaml` regenerated and committed alongside.
- `docs/design/manual-verification.md` updated to say the fix landed and is fixture-proven — explicitly **not** marked `verified` for real OCI, per the hard constraint.
- Added a `.gitignore` `*.pem` rule and a docker-compose recipe for running the manual-real-OCI harness without a host Go toolchain (documented in both `manual-verification.md` and this job's `orchestrator-verification.md`).

**cic-factory** (`feature/oci-invoke-async-result`): `output/agent-output.md`, `claim-evidence.md`, `reachability.md`, `orchestrator-verification.md` — including one flagged gap: DoD item 3's literal wording ("error_class/provider_code on invoke's failed result") isn't met, because `operationResult` never had those fields and the hard constraint said to leave the `>=400` branch unchanged — I followed the constraint and said so rather than silently narrowing the claim.

No PR opened, nothing pushed to `main`/`devel` — that's the orchestrator's call, along with the real-OCI re-verification recipe waiting in `orchestrator-verification.md`.