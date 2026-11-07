# 01b spec — orchestrator validation and review (2026-11-07, DRAFT; the job is NOT started)

Reviewer: the orchestrator that wrote the spec. **Limited independence**: the writer and the reviewer are the same party; an independent check by the owner's external reviewer is recommended before the start decision.

## Mechanical gates
- `tools/validate-meta.sh forms-oracle-vcn-slice-01b`: OK.
- `tools/validate-spec.sh`: first run NO-GO (K7: Go source audit without a `grep -rn` call-chain prescription); fixed by putting the prescription into the `implemented` definition; second run GO; third run (after the hint additions below) GO.
- `agent.config_dir` is an absolute path (cic-factory-core #92 avoided); `session_id` empty; `status: pending`; no push of the spec yet.

## Facts the spec relies on — re-checked against the code, not taken from the 01a text
| Spec statement | Check | Result |
|---|---|---|
| `Plan` rejects an empty `observed`, with a test `TestPlanRejectsEmptyObserved` | read provider.go:~445 and provider_test.go:~202 (round 2) | confirmed |
| production `Observe` = `effectiveConfig`(:860) + `applyDerivations`(:861) | read provider.go:827-875 | confirmed |
| the execution result has no `resource_id`; the design requires it at provider-abi.md:99 | struct read (round 2/3) | confirmed |
| removing the source-presence guard in `applyDerivations` survives the module's existing tests | planted defect M2 in a full-tree copy (round 4) | confirmed (all tests green) |
| `execBinding` carries host/base_path/key_id/resource_id/revision, no compartment | provider.go:~901 | confirmed |
| Forms' Go side is a library without a CLI; `Parse/CompileSchema/Validate/Expand/Normalize/NormalizeWithPolicy` exist | grep in the pinned copy (2f02a75): expand.go:213, normalizewithpolicy.go:17, validate.go:303, schema.go:126, parse.go:25, normalize.go:44 | confirmed; spec now says the vectors need a small Go driver |
| the NetworkSpace test path exists in Forms | `go/real_schema_test.go` (TestRealRegistrySchemas passed, round 4) | confirmed |
| `module_loadtest_test.go` loads the TinyGo artefact of `make wasm.build` | read the file header | confirmed; spec now says so |
| `make manifest-update` needs `docker compose exec builder` | Makefile:97-101 | confirmed; spec now gives the equivalent command |
| the module's builder image has TinyGo | 01a measurement (tinygo 0.39.0) and my own docker runs for Go | TinyGo itself not re-run by me: relies on the 01a report |

## Corrections made during the review
1. Removed "all 55 tests" from the S4 finding (the test count is NIV in 01a); it now says "the module's whole existing test suite".
2. Added the Forms vector-generation hint and a stop condition if `Expand`/`Normalize` cannot produce the `config_surface` output at the pinned commit.
3. Added the MANIFEST regeneration fallback and the `make wasm.build` note.

## Residual risks (not removed by editing)
- **Turn budget.** 200 turns for S1-S6 is tight (the read-only 01a took 127 turns over three attempts). The spec prioritises S4 -> S3 -> S2 -> S1 -> S5 -> S6 and allows `NOT MEASURED`, but a PARTIAL result is likely; a usage limit can cut the run again (it did in 01a).
- **S4 design fork.** Whether `Observe` should use `normalizeObserved`'s protection can change the ABI output shape; the spec turns that into a stop-and-report condition, which may stop the run early.
- **S2 is a proposal.** The spec forbids merging it before the owner decides and requires a decision record; the code may therefore sit unmerged for a long time.
- **Q2 diff-scoped target (>= 90%) and Q4 tooling.** The mutation tool is the agent's choice (gremlins worked in 01a, with timeout sensitivity); the result will be NIV unless the orchestrator re-runs it.
- **Licence.** Golden vectors are generated data; the one-way Apache-2.0 -> CC BY-NC-SA question for any Forms code stays an owner decision; PR #35 (the licence correction) is not yet merged.
- **Same-party review** (see above).

## State
Files only in the live workdir (untracked): `jobs/forms-oracle-vcn-slice-01b/{meta.yaml,input.md,output/.gitkeep,ref/spec-review.md}`. Not committed, not pushed, not started. Start requires the owner's separate GO. M2 and R1 stay open.

---
# Addendum 2026-11-07 (after two independent reviews): the draft was SPLIT

This file was written for the original single-job draft `forms-oracle-vcn-slice-01b` (commit 66627ed, kept in history; the original text is in `ref/original-01b-draft-input.md`). The directory was renamed with `git mv` to `forms-oracle-vcn-hardening-01b-a` and the spec rewritten.

Two independent reviews reached the same recommendation: do not start S1-S6 as one 200-turn job.
1. The owner's external review: CONDITIONAL GO for rework, NO-GO for starting as one job; split into 01b-A (S3+S4+targeted S6), 01b-B (S1+S5), 01b-C (S2 after the owner decides M2). That review could not read the then-untracked files, so it is architectural, not line-level.
2. A fresh read-only subagent review (`ref/independent-review-subagent.md`): SPLIT FIRST, with ten findings. I re-verified the load-bearing ones myself before using them: F3 (`module/module.wasm` is tracked, `project.yaml` `buildHash` equals its sha256, the load test reads `module.wasm`, so a real-Call test would run the old binary), F1 (production `Observe` already omits `isIpv6Enabled` when the source is absent; the gap is a missing production-path test), F4/F6 (`executeOne` is shared by every provider operation; `compartmentId` is a `required` config field that `conformIntent` already enforces and `renderBody` already sends from `config`).

## What changed in 01b-A (S4 + S3 only, `max_turns` 130)
- S4 is test-only; the production `Observe` is not modified; wiring `normalizeObserved` into `Observe` is an owner decision (it would change the `effective_config` content). Positive controls added (absent / `[]` / non-empty / `null` / `state` unchanged). The Plan replace hazard (input-only -> replace) must be named, not changed. Stop condition keeps the RED test, the reproduction and the ABI-impact analysis (owner's request).
- S3: `resource_id` on `steps[i]` only, create role only, `omitempty`; errors through `result.status=failed` + `error_class`; OCID shape `ocid1.vcn.` + non-empty remainder; message says the VCN was created; non-create results byte-identical; `provider-abi.md` is informative, divergence reported, not treated as a requirement; compatibility checks (`go vet -tags manual_real_oci`, no `DisallowUnknownFields`, `abi.schema.yaml` scope).
- New "measurement infrastructure" block: `docker run` on a scratch copy instead of `docker compose exec` (project-name collision), print mount and HEAD first; build the guest to a scratch path and point the new test at it by an env variable; `module/module.wasm` and `project.yaml` are not modified or committed and the committed artefact is stated stale; generalise the load-test mock (body, status, request counter); Q2 via an out-of-repo script; Q4 has an explicit `NOT MEASURED` escape; Q7 declared absent.
- The bit-identical list was extended (project.yaml, module.wasm, abi/capability/project schemas, oci-sdk.lock.yaml, schemas/core, testdata/vcn-v1, manual_real_oci_test.go).
- Removed from this job: S1, S5 (mapping, Forms vectors), S2 (`compartment_id`, the M2 decision record), all Forms/primitives/registry clones. They move to two future specs (mapping job; binding job after the owner's M2 decision), not yet written.

## Gates after the rewrite
`validate-meta.sh` OK; `validate-spec.sh` GO. Not started; not pushed.

## Still true
The orchestrator who wrote this spec also checked it (limited independence); the two reviews above are the independence. Not yet checked by anyone: whether the builder image can build TinyGo output to a scratch path with the module's flags (the host has no Go; only the image does), and whether a mutation tool can be installed there at run time (Q4 therefore may end as `NOT MEASURED`).
