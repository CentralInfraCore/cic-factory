# oci-invoke-async-result — orchestrator verification recipe

Not run in this job by design (hard constraint 1 — no real OCI resource, no
real OCI call from the implementation turn). This is the exact recipe to close
the loop against a live tenancy, plus the runtime gotcha this job hit and
worked around.

## What "verified" means for this fix

1. Re-run `Invoke(ChangeInstanceCompartment)` against a live instance, exactly
   as measured on 2026-08-05 (see `docs/design/manual-verification.md`,
   `invoke` coverage row) — same action, same setup: move a real instance into
   a second compartment.
2. **Expected result, this time:** `operationResult.Status == "accepted"`
   (not `"succeeded"`), and `operationResult.WorkRequestID` populated with the
   real `ocid1.coreservicesworkrequest...` value OCI returns in the
   `opc-work-request-id` header (this is the same id `oci raw-request` showed
   directly against the same endpoint last time — cross-check it matches).
3. Feed that `work_request_id` into `Poll()` and confirm it reaches a
   terminal state (`work_status: SUCCEEDED`, `terminal: true`) — this closes
   the loop `Invoke → accepted + work_request_id → Poll → terminal`, the same
   shape already proven end-to-end for `Destroy → work_request_id → Poll` on
   2026-08-05 (`TerminateInstance`).
4. Separately, re-run a `Destroy()` 404 (e.g. destroy the same already-gone
   subnet from the original 409/404/400 measurement, or provoke a fresh 404)
   and confirm the envelope-level error now carries `provider_code` (expect
   `NotAuthorizedOrNotFound` or whatever OCI's actual 404 code is for that
   endpoint — not measured verbatim before, only that it was empty) and that
   the message contains OCI's own text, not just the synthesised "resource
   already gone" string.

## Environment gotcha this job hit (worth reading before running)

`docs/design/manual-verification.md`'s existing recipes assume a host Go
toolchain. In this environment Go only exists inside the `builder` container
(`docker compose`), and `docker-compose.yml` does **not** mount
`$HOME/.oci` into it. `mk/golang.mk:141-143`'s own printed advice — put the
key under a repo-relative gitignored path — was a trap as shipped: `.gitignore`
had no `*.pem` rule, so a key placed under the repo tree was one `git add -A`
away from being tracked. **This job added a `*.pem` rule to `.gitignore`** and
updated `docs/design/manual-verification.md`'s "Usage" section with the recipe
below, so this should no longer surprise the next runner — but flagging the
`*.pem` rule explicitly here in case it needs a second look before relying on
it for a real key.

What actually worked, measured 2026-08-05 by the orchestrator (mount the key
file directly, bypass the repo tree and the advice above entirely):

```bash
docker compose run --rm --no-deps \
  -v "$HOME/.oci/oci_api_key.pem:/run/oci-key.pem:ro" \
  -e OCI_KEY_PATH=/run/oci-key.pem \
  -e OCI_TENANCY_OCID -e OCI_USER_OCID -e OCI_FINGERPRINT -e OCI_REGION \
  -e REAL_OCI_TEST=1 \
  builder sh -eu -c 'cd /app/module && go test -tags manual_real_oci -count=1 -run TestManualRealOCIInvoke -v ./'
```

(`OCI_TENANCY_OCID` etc. with no `=value` after `-e` forwards the host shell's
already-exported value into the container — export them in the host shell
first.)

## Concretely, the two commands

**Invoke (async, the fix under test):**

```bash
export OCI_TENANCY_OCID=... OCI_USER_OCID=... OCI_FINGERPRINT=... OCI_REGION=eu-frankfurt-1
export OCI_TEST_KIND=cic:compute:instance
export OCI_TEST_RESOURCE_ID=ocid1.instance...        # the live instance
export OCI_INVOKE_OPERATION=ChangeInstanceCompartment
export OCI_INVOKE_CONFIG_JSON='{"compartmentId":"ocid1.compartment...."}'  # the second compartment

docker compose run --rm --no-deps \
  -v "$HOME/.oci/oci_api_key.pem:/run/oci-key.pem:ro" \
  -e OCI_KEY_PATH=/run/oci-key.pem \
  -e OCI_TENANCY_OCID -e OCI_USER_OCID -e OCI_FINGERPRINT -e OCI_REGION \
  -e OCI_TEST_KIND -e OCI_TEST_RESOURCE_ID \
  -e OCI_INVOKE_OPERATION -e OCI_INVOKE_CONFIG_JSON \
  -e REAL_OCI_TEST=1 \
  builder sh -eu -c 'cd /app/module && go test -tags manual_real_oci -count=1 -run TestManualRealOCIInvoke -v ./'
```

Read the test's own output for the `operationResult` JSON it printed — look
for `"status":"accepted"` and a non-empty `"work_request_id"`. If it still says
`"succeeded"` with no `work_request_id`, the fix did not take effect in the
built artifact (check `headSha` against what CI ran, and that `module.wasm`
in the branch actually contains this change — `make wasm.build` was run as
part of this job and `module/module.wasm` + `project.yaml`'s `buildHash` are
part of the commit).

**Then Poll the returned work_request_id to terminal:**

```bash
export OCI_POLL_PATH=/20160918/workRequests/<the ocid1.coreservicesworkrequest... from above>

docker compose run --rm --no-deps \
  -v "$HOME/.oci/oci_api_key.pem:/run/oci-key.pem:ro" \
  -e OCI_KEY_PATH=/run/oci-key.pem \
  -e OCI_TENANCY_OCID -e OCI_USER_OCID -e OCI_FINGERPRINT -e OCI_REGION \
  -e OCI_POLL_PATH \
  -e REAL_OCI_TEST=1 \
  builder sh -eu -c 'cd /app/module && go test -tags manual_real_oci -count=1 -run TestManualRealOCIPoll -v ./'
```

Expect `work_status: SUCCEEDED`, `terminal: true` (re-run with a fresh
`-count=1` a few seconds later if it's still `IN_PROGRESS`).

## After it passes

Update `docs/design/manual-verification.md`'s `invoke` coverage row and the
`not-found` row in the "Error paths" table from "fix landed, not yet
re-verified" to "verified" with the concrete measured `status`,
`work_request_id`, and `provider_code` values — that edit is the
orchestrator's, per hard constraint 6 of this job's spec.
