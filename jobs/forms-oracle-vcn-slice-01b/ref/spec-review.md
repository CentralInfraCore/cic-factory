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
