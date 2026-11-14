## Goal

Bring the test and CI quality model of `CentralInfraCore/CIC_Relay` up to the level implemented in `CentralInfraCore/cic-primitive-forms`.

This is an implementation task, not only an audit. The target is not just ">90% coverage" but the quality model behind the Forms: verified mutation coverage, fail-closed gates, seeded-defect tests, FULL and DIFF runs, verifiable evidence, and a CI that tests itself.

**Principle:** the CI should not prove that the tests are green. It should prove that the decision drawn from the checks is justified and verifiable by the available evidence. A skip is not a pass. Missing evidence is not evidence.

Do not copy the Forms pipelines mechanically. Build the test system on the actual behavior of the Relay (Go, Rust, WASM, PKI, Vault, FFI, workflow, proof). Keep the existing correct tests and controls. Test infrastructure work is kept separate from production code fixes.

## Starting point

Relay: `.github/workflows/{verify,mutation-pr,mutation,nightly,manifest-check}.yml`, `scripts/{mutation_plan,gremlins_gate,baseline_guard}.py`, `.mutation-baseline.json`, `.mutation-cost.json`.

Forms reference: `p1.yml`, `p1-proof.yml`, `nightly.yml`, `proof-plan.yml`, `evidence.yml`, `evidence-probes.yml`, `quality_gate.py`, `coverage_gate.py`, `diff_gate.py`, `seeded_defects.py`, `tools/test-evidence/`, `tools/proof-plan/`, `docs/DELTA-DIFF-GATE.md`, `docs/FAST-FULL.md`, `docs/TEST-EVIDENCE.md`.

First step: record the commit ids of both repositories and produce an object-level gap analysis that separates working checks, missing tests, faulty CI gates, unmeasured areas, and requirements that cannot currently be met because of implementation defects.

## Quality gates (machine-readable, explicit versioned scope)

| Metric | Target |
|---|---|
| Go statement coverage | >90% |
| Rust line coverage | >90% |
| Go/Rust branch coverage | >90% |
| Go/Rust mutation score | >90% |
| FFI integration | positive and negative test for every declared ABI boundary |
| Critical trust-boundary regression | zero accepted wrong authorization |
| Missing or broken measurement | mandatory FAIL |
| Incomplete mutation shard | mandatory FAIL |

- The measurement scope is explicit, versioned and changeable only through review. Production code, test helpers, generated files and experimental (unwired) components are separated.
- No unjustified exclusion of tests, packages or files to reach the target.
- If an area misses the target, record a precise, measurable debt list and a fix task. Do not lower the bar to get green. An initial baseline is allowed only as a documented, temporary ratchet.

## Mutation testing: FULL and DIFF

Build on Go `gremlins` and Rust `cargo-mutants`.

**DIFF (pull request):** mutate the changed production objects; consider the effect of modified or deleted tests; escalate conservatively to FULL on changes to test helpers, fixtures, dependencies, build settings or gate logic when narrowing cannot be proven safe; no silent skip for new packages, new tests, deleted files or an uncertain git diff. `mutation_plan.py` must not treat test-only changes as unable to change the mutation result.

**FULL:** measures the whole declared production scope. Every planned mutant gets exactly one interpretable execution or exclusion status. Shard results are checked for list completeness, duplicate and missing verdicts, unknown or corrupt reports, separate handling of timeouts and unviable mutants, and planned vs. measured mutant equality.

**Known defect to fix first:** the Rust mutant enumeration in `mutation-pr.yml` and `nightly.yml` uses a `grep -c ... || true` pattern that can mask a failure of the listing command. A failed enumeration must never mean zero mutants. Check the enumeration success first, then handle an empty-but-valid result separately. Test every such failure path.

## Self-testing of the test infrastructure

Modeled on the Forms `quality-gate-selftest` and `seeded-defects`. Minimum negative probes:

1. Deliberately weakening the test suite lowers coverage and the quality gate turns red.
2. A deliberately surviving mutant turns the mutation gate red.
3. A missing mutation shard makes FULL unable to succeed.
4. A duplicated or tampered mutant verdict is rejected.
5. A missing or unreadable coverage report is not read as a zero measurement or as success.
6. A faulty test-selection planner cannot silently skip tests.
7. A faulty or missing evidence artifact cannot get VERIFIED.
8. A modified or unknown measuring-tool version makes the result unusable automatically.

Seeded-defect tests run in an isolated environment and must not permanently modify the production tree or repository evidence. The quality gate tests are themselves covered by a separate quality gate.

## Relay-specific trust boundaries

- **Module identity and authorization** (`cmd/relay/bootstrap.go`, `cic_flow_registry.go`, `cic_flow_manifest.go`, `core/cabinet/pki_verify.go`): negative tests for a bad certificate chain, modified WASM, manipulated capability manifest, missing or invalid signature, unauthorized capability request. A matching hash is not proof of origin or authorization.
- **Execution and resource limits** (`cmd/relay/cic_flow_host_funcs.go`, `core/modules/httpcap/`, `http-executor/`, `core/cabinet/cicwasm.go`): redirects, internal network addresses, DNS result changes, timeouts, response size limits, WASM memory use, resource release after guest errors. Identical contract-based vectors for the Rust and Go HTTP paths where the same security rule applies.
- **Workflow and proof chain** (`core/cabinet/service.go`, `cmd/relay/proof_verify.go`, `core/nexus/recorder/`): partial execution, interruption, concurrent proof recording, corrupt chain hash, missing signature, state-continuity errors. The following must stay distinct and never be merged into one `success`/`verified` value: execution succeeded; evidence exists; evidence is structurally consistent; evidence is cryptographically authenticated; evidence is acceptable under the given trust policy.
- **FFI, Vault, release:** Rust–Go FFI memory ownership, null pointer, bad length, double free, panic boundary. Vault integration uses an isolated reproducible environment with no real keys or production privileges. Source, build, manifest, signer identity and released artifact are tested as separate links.
- If a negative test exposes a missing production guarantee, record it and fix it in a separate, targeted PR. Do not hide it with a test exclusion.

## Differential and fuzz testing

Shared vectors for Go, Rust and Python where applicable: byte-level canonical format equality, identical digests, error-class and error-path correspondence, preservation of absent/null/empty, order-independent deterministic results, consistent rejection of bad input. Fuzz targets are identified per object; found defects become reproducible regression tests. Agreement between implementations does not prove correctness: for critical cases an independent reference oracle and a deliberately faulty implementation are required.

## CI evidence and proof-aware reuse

**Evidence contract** (reference: Forms `test-evidence`, `proof-plan`): per full check, record commit and tree identity, test and mutation scope, toolchain and tool versions, executed checks and results, justification of skipped checks, raw or verifiably reconstructable coverage and mutation data, and the overall verdict. The report is canonicalizable, integrity-checked and verifiable by an independent verifier. Publication comes in a separate step; GitHub App, attestation, protected branch and watchdog stay off until their negative probes pass.

**Proof-aware reuse** is a separate, later phase and report-only first. No test may be skipped from the proven baseline run. Decisions: `REUSE_ELIGIBLE`, `RERUN_REQUIRED`, `UNVERIFIABLE`; uncertain or incomplete evidence never yields reuse. Compare the planner output with an independent full run of the same commit and report every `FALSE_REUSE`. It becomes a mandatory gate or an actual skip mechanism only after a separately approved development and security decision. Do not port the Forms proof-aware planner first: make the Relay's own results reliable and complete before proving which can be reused.

## Implementation order (separate, reviewable PRs)

| PR | Content | Closing condition |
|---|---|---|
| PR-01 | CI inventory and object-level gap analysis | reproducible baseline and scope |
| PR-02 | Fix mutation planner and faulty measurement paths | every enumeration failure fail-closed |
| PR-03 | Unified quality gate and completeness validation | incomplete report or shard rejected |
| PR-04 | Branch coverage and object-level measurement | scope-bound, verified thresholds |
| PR-05 | Seeded defects and CI self-test | deliberate defects verifiably turn red |
| PR-06 | Trust-boundary and FFI negative tests | critical contracts tested, deviations recorded |
| PR-07 | FULL/DIFF integration, nightly failure reporting | separate measurement and failure-report path |
| PR-08 | Evidence record and offline verifier | authenticated, complete check record |
| PR-09 | Evidence publication and negative probes | activation only after successful trust checks |
| PR-10 | Proof-aware shadow planner | zero accepted FALSE_REUSE, no automatic skip |

Each PR is independently testable. CI work does not come with unjustified production refactoring.

## Development rules

1. Do not delete a valid test only because it is red.
2. Do not weaken a threshold or baseline without an explicit measurement reason and approval.
3. No `|| true`, `continue-on-error` or skippable job where the result is part of a mandatory gate. If a separate parser evaluates the tool failure, test its completeness and correctness.
4. Distinguish an empty result from a failed measurement.
5. Keep shadow/report-only clearly separate from mandatory gates.
6. Every gate change has at least one negative test that reproduces the earlier defect.
7. Measurements are reproducible; record the relevant identity of the measuring environment.
8. Check branch protection and required checks, but change external repository settings only with separate permission.
9. Do not claim a security property is proven when only a passing unit test or high coverage supports it.
10. Do not declare a CI phase done until an actual GitHub Actions run confirms it.

## Acceptance criteria

- The active production scope meets the defined coverage and mutation gates, or the remaining gaps are listed as explicit blockers.
- FULL and DIFF planning and execution are reproducible.
- Missing, corrupt, duplicated or contradictory measurement evidence cannot lead to a successful verdict.
- The quality gates' own negative tests can actually turn the pipeline red.
- Critical trust-boundary contracts have negative regression tests.
- Known production defects are not hidden by test exclusions.
- Claims made by the CI are traceable to a concrete run, commit, test and result.
- The state of the evidence and proof-aware experimental layers is documented precisely and not mixed with the state of the mandatory gates.

## Final report

After implementation, produce a comparison of the original Relay, the Forms reference, and the improved Relay: exact coverage and mutation numbers, seeded-defect results, all remaining weaknesses, mandatory gates, non-mandatory checks, and real GitHub Actions run ids.

Start with a check of the current state of both repositories and a reproduction of the first, highest-risk CI gate defect (the Rust enumeration `|| true` masking).

