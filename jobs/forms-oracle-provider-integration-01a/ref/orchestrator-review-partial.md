# 01a orchestrator review of the PARTIAL result (2026-11-07)

Scope: local review of the workspace output only. No push, no resume, no new job, workspace kept. The run was cut by the account usage limit (see run-history.md), not by the turn limit.

## Mechanical gate
`tools/validate-output.sh forms-oracle-provider-integration-01a` -> NO-GO (O1 x6, O2, O4). It reads `jobs/<id>/output/` in the LIVE workdir; the outputs exist only in the agent workspace, so it inspected 0 files. The result is therefore "gate not applicable to the workspace location", plus the true findings: `relay-requirements.md` and `claim-evidence.md` absent; `agent-output.md` is the 60-byte limit message. Not re-run against a copy (that would write into the live job directory).

## Re-measured by the orchestrator (independent of the agent)
- Pin hash: `git cat-file -p 6db77d4:general/network/network-space/network-space.yaml | sha256sum` = `c9a4d14c...3b68` = `corpus/pins.yaml` line 53. Matches.
- Module VCN contract at 3e38886: `vcn.json` config 13 properties, state 19, `required: [compartmentId]`. Matches the claim.
- Module has no Forms reference in `*.go` / `go.mod` at 3e38886 (grep returns nothing). Matches "zero Forms imports".

## Not re-measured (agent's claims, taken as documented-with-command, not as verified)
Docker/Go test runs (TestRealRegistrySchemas PASS, coverage 82.9%/88.7%, mutation 159/217), field-level counts (4 expressible / 9 not; 2 reverse gaps), Relay inventory, licence section. Needs sampling with re-run before any of them is relied on.

## Measured / documented / open (VCN, as stated in contract-mapping.md)
- Measured (agent, one independently confirmed above): NetworkSpace compiles in Forms at the pinned commit; config_surface 7 nodes vs module 13 fields; `compartmentId` and `displayName` are not expressible in NetworkSpace (Forms rejects them as UNKNOWN_FIELD); `dns_support_enabled`/`dns_hostnames_enabled` have no OCI counterpart.
- Documented: the correspondence rules (first/rest/map_to_list/value_map, `kind: unsupported`, `composition`) live in cic-schema-registry `ac567ae`, AFTER the Forms pin `6db77d4`; implemented there, `concept` in the module.
- Open: the whole forward direction (intent -> OCI request) has no code place in any repo; `compartmentId` has no intent home (create cannot be planned from the schema alone); OCI `UPDATING` has no enum value; `subnet_count` needs a second OCI call the module does not have; pin drift between Forms pin and registry main must be a decision.

## Decision point (owner)
Targeted resume for the two missing outputs (after the usage limit resets, 14:00 Europe/Budapest) vs accepting the three files as a partial baseline. Recommendation: first sample-verify the agent's un-re-measured claims; the resume then only needs `relay-requirements.md` and `claim-evidence.md`. 01b stays HOLD.

## Sampling round 1 (2026-11-07, after the owner's GO) — independent re-measurement

Order per the owner: (1) field mapping, (2) registry 6db77d4..ac567ae, (3) Forms/Relay call path, then Docker/coverage/mutation/licence. Done: (1) partly, (2). NOT yet done: (3) and everything after it.

### (2) Registry 6db77d4..ac567ae — MEASURED
- 7 commits. `git diff 6db77d4 ac567ae -- general/network/network-space/network-space.yaml`: ONE line, `modify: [OU=adapters, O=cic]` -> `modify: ["OU=adapters,O=cic"]` (the CertPattern single-pattern change). The canonical NetworkSpace is semantically identical; its file bytes (and so the pinned sha256) are not.
- The provider dir `providers/oracle-cloud/network/network-space/` differs only by the ADDED `network-space.correspondence.yaml` (168 lines).
- Consequence: the agent's claim "the change since the pin does not overwrite statements about the pinned state" is confirmed for the canonical schema. The open item is a pin decision: moving the pin changes the digest (pins.yaml sha256 must change) and brings in the correspondence file.

### (1) Provenance of values — MEASURED facts, then an OPEN question
- NetworkSpace `binding_surface.addresses[0].key_fields` at the pin: `backend` (enum [cloud]), `provider`, `location` (region), `id` (e.g. VCN OCID). No compartment, no tenancy. `adapter_capabilities.known_adapters: []` (deliberately empty until a real adapter exists).
- Module `execBinding` (module/provider.go:~901, 3e38886): `host` (region endpoint), `base_path`, `key_id` (`<tenancyOCID>/<userOCID>/<fingerprint>`), `resource_id`, `revision`. No compartment. The comment says it is supplied with the intent.
- `compartmentId` in the module appears only as the action-managed VCN field (`x-cic-action: ChangeVcnCompartmentDetails`) and in `contracts.go`; no code derives it from the binding.
- So the owner's hypothesis (compartmentId as a Relay-resolved provider-binding value, not authored intent) is NOT contradicted, but is also NOT supported by any current contract: neither binding schema carries it. The tenancy OCID inside `key_id` is not a general compartment OCID (equal only for the root compartment). Origin of `compartmentId` = OPEN, to be decided; candidate homes: (a) module `execBinding` field (ABI change, no new primitive), (b) an authored intent field (schema change), (c) adapter-capability config. Each has different consequences for Forms (Forms validates config_surface only).
- Corollary: the "9 not expressible" count conflates fields with different origins. Until each of the 13 fields is classified (authored / binding / default / provider-computed / observed), "9 contract defects" is NOT established; only "not expressible in the NetworkSpace config_surface" is measured.
- Not yet checked: where the CREATE body is built and whether create needs `binding.resource_id` (Invoke requires it, provider.go:~679); this decides whether create is plannable at all.

## Sampling round 2 — create path and the 13 VCN config fields (module 3e38886, code read; no run)

### Create path — MEASURED by reading the code (file:line in module/provider.go)
- Create is `Execute` (:972) with a CALLER-supplied `plan.provider_operations` containing `CreateVcn` (role create, `POST /vcns`, no path_params). `Plan` (:410) never creates: an empty `observed` is rejected (:~445, issue #31, test `TestPlanRejectsEmptyObserved`, provider_test.go:~201: "a brand-new resource is created via a directly-constructed Execute(CreateVcn) call, never through Plan").
- `Execute` requires only `binding.host` and `binding.key_id` (:~976). `resource_id` is NOT required for create (its path `/vcns` has no `{param}`). `resource_id` IS required by `Invoke` (:~679, actions on existing resources) and by `Observe`/`Destroy`. So the owner's worry is answered: the resource_id requirement does not apply to create. Not a defect there.
- Create body = every contract field present in `config.data` (`renderBody` :1092, role create): the module sends the caller's OCI-named config as-is. There is NO intent->OCI translation in the create path; `config.data` must already be `cidrBlock`, `compartmentId`, ... (forward mapping absent, consistent with round 1).
- GAP (measured on the returned shapes): `executionStep` (:~955) has operation/http_status/etag/opc_request_id/work_request_id/error fields only, and `pollResult` (:725) has work_status/percent/terminal/http_status only. Neither returns the created resource's OCID, so after `Execute(CreateVcn)` the ABI gives the caller no `resource_id` for the next `Observe`. NOT checked: whether the caller/Relay obtains it another way (response body not surfaced, docs/design/manual-verification.md not yet read). Status: open lifecycle question, not yet a proven defect.
- Structural consequence: desired-vs-observed reconciliation cannot start from "does not exist"; create lives outside Plan. Documented in code comments, covered by one negative test, not a bug but a contract the 01b design must respect.

### The 13 fields (policy = vcn.json `x-cic-policy`, MEASURED; origin/role columns = analysis from contract text, to be confirmed)
| OCI field | Role / policy | Origin (analysis) | NetworkSpace | Forward | Back | Change needed |
|---|---|---|---|---|---|---|
| compartmentId | create-required body; action-managed (ChangeVcnCompartment) | **OPEN**: authored vs binding vs execution context; not in binding_surface keys nor execBinding | none | missing | module state has it; NS state none: missing | decision first, then binding OR schema |
| cidrBlock | create-only | authored | partial (cidr_block; OCI prefers plural) | missing | documented (registry, rule `first`, py tests) | mapping |
| cidrBlocks | create-only | authored | cidr_block + secondary_cidr_blocks | missing | documented (rules first/rest) | mapping + implementation |
| dnsLabel | create-only | authored | dns_label | missing (name differs) | implemented in module via effectiveConfig name match (agent's claim, not re-run) | mapping (rename) |
| displayName | mutable | authored-optional (OCI generates one if omitted: also provider-default) | none | missing | missing | owner decision: is it intent? |
| freeformTags | mutable | authored | tags (list of key/value) | missing | documented (map_to_list) | mapping |
| definedTags | mutable | authored or tenancy tag-defaults (provider-computed): OPEN | none | missing | missing | decision |
| securityAttributes | mutable (ZPR) | provider-specific authored: OPEN | none | missing | missing | decision (provider extension vs core) |
| isZprOnly | mutable (ZPR) | provider-specific authored: OPEN | none | missing | missing | decision |
| isIpv6Enabled | input-only (create-time) | authored | ipv6_enabled | missing | implemented in module (derivation from ipv6CidrBlocks, agent's claim) | forward mapping |
| isOracleGuaAllocationEnabled | input-only | provider-specific option | none | missing | missing (not returned) | decision |
| byoipv6CidrDetails | input-only | provider-specific advanced | none | missing | missing | decision |
| ipv6PrivateCidrBlocks | create-only | provider-specific advanced | none | missing | missing | decision |

Rule kept (owner): no schema change just to make OCI create work; each field must first be shown to be authored intent and not execution context / binding. Fields marked OPEN above are not proven authored.
Nothing here was run; the "implemented in module" back-direction entries rely on the agent's report and are in the list of claims still to re-run.

## Sampling round 3 — Forms -> Relay -> Oracle reachability and the created OCID (module 3e38886, Relay 55a899f; code/doc read, nothing run)

### Reachability (MEASURED by grep/read, independent re-check of the agent's Relay section)
- Forms -> module: module `*.go`/`go.mod` have no Forms reference (round 1). Forms -> Relay: no Forms reference in Relay `*.go`/`go.mod`. No production call path from Forms to the module exists in either repo.
- Relay -> module: Relay's only guest calls are `core/cabinet/cicwasm.go:277,283,289,295` with fixed op strings `process|get|init|notify`; `service.go:~229-243` switches on those four and its `default` is `WASM module %q does not support operation %q`. The module's `Call` dispatches `describe|validate|observe|plan|execute|poll|invoke|destroy` (`module/abi.go:~36-51`), `default` -> `unknown op`. The two vocabularies do not intersect. Agent's claim CONFIRMED independently. The ABI mechanics (exports, packed return, {data,error}) match per the agent (not re-read by me). The eight ops were verified against real OCI by direct test harness, not through the Relay (documented, manual-verification.md).

### Created OCID — two separate obligations (owner's split)
1. Does the provider response contain the OCID? Documented-by-OCI-contract, not measured by me: `CreateVcn` is synchronous per manual-verification.md ("CreateVcn/UpdateVcn are synchronous") and OCI returns the Vcn object with `id`. NOT verified here: I did not read a captured real response or fixture. Status: documented, not measured.
2. Does the CIC execution contract hand it on? Two layers:
   - Design (`docs/design/specs/provider-abi.md`, marked informative): `execution-result.provider_metadata: { opc_request_id, etag, resource_id }` (:99) and `observation.provider_metadata.resource_id` (:79).
   - Code (MEASURED): `executionStep` has operation/http_status/etag/opc_request_id/work_request_id/error/error_class/provider_code only — NO resource_id, and the response body is not surfaced; `pollResult` likewise. `executeOne` reads the response only for status/headers/error. So the documented `resource_id` in the execution result is NOT implemented.
   - Documented workaround (manual-verification.md:~204-208): "after a `Create`, find the new resource's OCID with the `oci` CLI ... to feed into the next Observe". That is a manual step, not a CIC mechanism.
   - Relay side: no code at 55a899f handles `resource_id`, `provider_metadata` or an execution result (grep in non-test Go: no hits). So no component downstream picks the OCID up either.
   - Chain `CreateVcn response -> execution result -> Relay -> state binding -> Observe`: response (documented has id) -> execution result (BREAKS: field documented, not in code) -> Relay (no provider-ABI path at all) -> binding (module `execBinding.resource_id` is caller-supplied) -> Observe (requires it). Verdict: the OCID is not lost by an existing component handling it elsewhere; it is dropped in `executeOne`, and no other component compensates. This is a measured implementation gap against the module's own design doc, a blocker for any create->observe flow, but fixable inside the module without a new primitive or schema (extend the execution result), subject to the ABI/contract decision.
   - Identity model: state-model.md:~60-68 says correlate by the stable CIC `uid`, never by `provider_id`; so the OCID is the current realization id (provider_id) and must be stored by the state binding. That binding component is not found in either repo (not exhaustively searched: only module docs/code, Relay Go).

### compartmentId — new evidence for the owner's hypothesis (documented design vs code)
- `provider-abi.md:73` (informative): `observe-request.binding: { provider: oracle-cloud, region: eu-frankfurt-1, compartment_id: ocid1.compartment... }` — the module's own design puts `compartment_id` in the BINDING.
- Code `execBinding` (provider.go:~901) has host/base_path/key_id/resource_id/revision, NO compartment_id. So: documented design supports "binding", implementation does not carry it. This is a design-vs-code divergence, plus the NetworkSpace key_fields have no compartment (round 1). The question "authored vs binding vs context" now has a documented lean toward binding in one of three documents; still not a decision.

### Contract gaps for a VCN vertical slice (no change to existing CIC architecture) — candidate list, to be confirmed
1. Forward mapping NetworkSpace(expanded Forms object) -> OCI `CreateVcn` config (absent everywhere; the actual 01b core).
2. `compartmentId` home (binding per module design doc vs intent): owner decision; if binding, add `compartment_id` to `execBinding` (module ABI change).
3. Execution result must carry the created `resource_id` (documented, not implemented).
4. Where the state binding stores `provider_id` (not found).
5. Relay op-vocabulary mismatch (4 vs 8 ops): only matters if the slice must run through the Relay; the 01b test harness path would bypass it (as the 8 verified ops did) — decision whether Relay integration is in or out of the slice.
6. Create outside Plan: the slice's lifecycle must call Execute(CreateVcn) directly.

## Sampling round 4 — back mappings, coverage, licence (all in throw-away copies via `git archive`, scratch dir under the job tmp; no repo touched)

Copies: module 3e38886, registry ac567ae and 6db77d4, Forms 2f02a75. Module tests ran in the module's builder image (go1.25.0); registry tests with host pytest (`PYTHONPATH=.`).

### Back mapping in the MODULE (production path vs test-only) — MEASURED
- Production path (file:line, 3e38886): `Observe` provider.go:827 -> `effectiveConfig` :860 -> `applyDerivations` :861 (correspondence.go:61). The only derivation in `correspondence/vcn.json` is `isIpv6Enabled <- ipv6CidrBlocks` (`bool-from-nonempty`). `dnsLabel`/`cidrBlock`/`cidrBlocks`/`freeformTags` come through `effectiveConfig` by OCI field name (no registry naming, no rule).
- `normalizeObserved` (observed.go:68; the four-valued coverage observed/absent/unobserved/unknown and the "unobserved value is deleted from effective_config" filter, observed.go:132-136) has NO production caller: grep of non-test code finds only its definition. All callers are in observed_test.go. Status: scaffold/test-only. `Observe`'s output carries no coverage (the agent's claim confirmed).
- Planted defects in a full-tree copy (baseline green, `go test .` 2.6 s): M1 invert `bool-from-nonempty` -> caught (TestNormalizeObservedMatchesTheFixture, TestObserve). M3 empty array counts as non-empty -> caught (TestNormalizeObservedMatchesTheFixture). **M2 remove the source-presence check in `applyDerivations` (fabricates `isIpv6Enabled=false` from an absent source) -> SURVIVES, all tests green.** Reason: the "partial read never fabricates" test goes through `normalizeObserved`, whose filter deletes the value afterwards; the production `Observe` path has no such filter and no test of the absent-source case. The guarantee that holds in production today rests on one unguarded `if !ok { continue }`.

### Back mapping in the REGISTRY (ac567ae)
- `tests/test_tools/test_registrylib/test_correspondence.py` + `tests/test_tools/test_vcn_fixture.py`: 40 passed (agent reported 37 for the correspondence file; different file set, not a contradiction).
- Production reachability: no code outside `tools/registrylib/correspondence.py` references the applier (grep over `tools/`): it is a tested library with no caller (not wired into `registry_validate.py`). "implemented in the registry" therefore means: implemented + tested, NOT used by any production flow.
- Planted defects in the applier (copy): first/rest swapped -> 7 failed; value_map default `unknown`->`available` -> 1 failed; map_to_list unsorted -> 1 failed; **value_map no longer defaults for non-string values -> SURVIVES** (40 passed; for None/numbers `dict.get(v, default)` returns the default anyway, so only unhashable values would differ: possibly near-equivalent, not proven equivalent).

### Coverage — MEASURED
- `module` package: **82.7%** in both default and `-covermode=atomic` modes. The agent's **82.9% is NOT reproduced**; 82.7% equals the owner-direction doc's figure. The agent flagged a +0.2 pp drift itself and could not name the cause. `tools/oci-extract` root 88.7% reproduced exactly; `cmd/oci-extract` and `cmd/oci-sweep` 0.0% reproduced. Command: `cd module && GOFLAGS=-mod=mod go test -count=1 -covermode=atomic -cover .`
- Not re-measured: mutation (agent: 159/217 runnable mutants, 100% efficacy, 58 uncovered; gremlins), branch coverage, staticcheck/govulncheck. Mutation needs a long run; not done in this round.

### Licence — MEASURED, and a correction to OUR OWN merged document
- Forms 2f02a75: `LICENSE` is Apache-2.0; 69 files carry `SPDX-License-Identifier: Apache-2.0`, no other identifier, no AGPL/Affero text anywhere. The agent's finding is CONFIRMED.
- The statement in `cic-module-oracle-cloud` `docs/design/forms-integration-direction.md:90` ("the Forms repository is mixed ... adopted tooling AGPL-3.0-or-later, two hooks MIT") describes the licence of THIS repo (cic-factory, see its LICENSE.md), not of Forms. That document was merged in cic-module-oracle-cloud #34 from this session. It needs a correction PR (no GO given to edit it; not edited). The agent reported "not verifiable" correctly; the cause is our conflation.
- The licence caveat itself stands in a different form: module/registry are CC BY-NC-SA 4.0, Forms Apache-2.0 (one-way direction question as the agent laid out), cic-primitives bytes bound by the pin's own manifest.

## Round 5 — owner decisions of 2026-11-07 and the Q0-Q9 inventory closure

### Decisions recorded
- Licence correction PR: GO, opened as cic-module-oracle-cloud #35 (docs-only, base `devel`, branch `docs/forms-licence-correction`, commit 90f4a83, signed by the hook; merge NOT authorized). `sha256sum -c MANIFEST.sha256` passes for all entries on the branch.
- Full mutation re-measure: HOLD until after the 01a closes. The agent's 159/217 (100% efficacy, 58 uncovered, timeout-sensitive) stays `NOT INDEPENDENTLY VERIFIED`; it is not required for the 01a baseline closure. Order: (1) close 01a evidence + Q0-Q9 inventory, (2) reproduce the full mutation run as a separate controlled run only if the 01a acceptance needs it, (3) diff-level mutation gate for new/changed code in 01b.
- 01a `--resume`, push, 01b, new schema: HOLD. T3 second copy: NOT BACKED UP.

### 01b BLOCKING test case (owner wording, recorded verbatim in substance)
"If `ipv6CidrBlocks` is absent from the OCI response, the CIC state must not contain an `isIpv6Enabled=false` value derived from it. A missing observation must not become an observed `false`." The test must drive the production `Observe` path (provider.go:827 -> effectiveConfig -> applyDerivations), not only `normalizeObserved`. Evidence it is needed: planted defect M2 (round 4) survives all 55 non-manual tests.

### Q0-Q9 inventory (module 3e38886 unless noted) — status per row
| Level | Agent's report | Independent re-measure | Status |
|---|---|---|---|
| Q0 format/static/vuln | gofmt 0 files, vet 0, staticcheck 0, govulncheck clean on module; oci-extract: 1 stdlib vuln (os@go1.25, fixed in go1.25.8) called from cmd/oci-sweep/main.go:118 | gofmt/vet/staticcheck re-run: 0 / exit 0 / exit 0 (module). govulncheck NOT re-run (needs vuln DB network) | module: measured (3 of 4 checks re-run); govulncheck + oci-extract vuln: NOT INDEPENDENTLY VERIFIED |
| Q1 unit | PASS; 26 top-level Test funcs (+8 manual) | PASS. Count differs: 55 top-level `func Test` in the non-manual test files of `module/`, 7 `TestManualRealOCI*` | PASS reproduced; the agent's counts (26, 8) NOT reproduced (probably a different counting rule, not stated) |
| Q1+ race | `-race` green in ~25 s, not in CI (`golang.test` would, `ci.yml` does not call it) | `go test -race -count=1 .` ok in 25.9 s; `ci.yml` has no `race` line (grep) | measured; scaffold (make target exists, no CI step) |
| Q2 line coverage | module 82.9%, oci-extract 88.7%, cmd/* 0.0%, three together 56.3% | module 82.7% (default and atomic), oci-extract 88.7%, cmd/* 0.0% | module figure NOT reproduced (82.7 vs 82.9); rest reproduced; the three-package 56.3% not re-computed |
| Q3 branch coverage | none in module, not measurable; reusable `tools/branchcov` in Forms (AST, Go+Rust+Python) | not re-checked | agent report only; reuse is a licence/dependency decision (Apache-2.0 vs CC BY-NC-SA, PR #35 text) |
| Q4 mutation | 159/217, 100% efficacy, 58 uncovered, timeout-sensitive; go-mutesting panics | not re-run (HOLD) | NOT INDEPENDENTLY VERIFIED |
| Q5 gate can fail | none in module; Forms has seeded_defects + selftest jobs | my planted defects (M1-M3, registry mutants) show a test-level ability to fail; one survivor (M2) shows a blind spot | module gate-fail proof: absent (agent) and one measured blind spot (orchestrator) |
| Q6 shared vectors | `module/testdata/vcn-v1/` (9 cases) vendored from cic-factory fixtures/vcn-v1 | registry copy at ac567ae `tests/fixtures/vcn-v1` exercised by the 40 passing registry tests | partly; agent claim plausible, vendored-copy provenance not re-checked |
| Q7 claim-evidence | manual-verification.md hand-kept; three defects found and recorded | read round 3, consistent | partly; no machine-checked claim-evidence table in the module |
| Q8 reachability | not a requirement; `deadcode` not applicable to the guest build (cgo) | my own finding: `normalizeObserved` has no production caller (round 4) | the module's own tests do not prove reachability; the 01b gate must |
| Q9 determinism | MANIFEST gate, WASM hash check match; reproducibility probe non-fatal and does NOT reproduce | not re-run | agent report only |

## Round 6 — final orchestrator review of the completed 01a output set (2026-11-07, after the controlled resume)

### Evidence chain and tree state
- Local commits in the workspace (feature branch, NOT pushed, push URL disabled): `b62f624` (relay-requirements.md, claim-evidence.md, agent report), `22849fa` (baseline.md, contract-mapping.md; hashes b66da3e5…, a876924c… identical to the pre-resume record). Staged by explicit path; the modified workspace `input.md` and all untracked scratch files stay out of the commits. Secret scan of the two files: 2 hits, both prose about the Relay's secret-manifest check, no credential. No remote ref of the feature branch exists (`ls-remote` 0).

### O5 — the 275 unresolved `file:line` references, classified (232 distinct refs; the validator's 321 counts repeats across files)
My classifier resolved each distinct ref against the pinned commits (module 3e38886, Forms 2f02a75, registry 6db77d4/ac567ae, Relay 55a899f, primitives 73ae469, factory HEAD) and checked the line number against the file length at that commit:
| Class | Count | Meaning |
|---|---|---|
| Full path resolves at a pinned commit, line in range | 107 | genuine; the validator misses them only because the roots in `env.sh` are other repos/branches |
| Bare file name, exactly one candidate in range | 109 | resolvable by context (a repo prefix is missing) |
| Bare file name, ambiguous | 9 (8 multi-repo, 1 multi-file) | e.g. `service.go:18` (Relay cabinet vs crypto), `policy.go:143`, `resolve.go:79`, `main.go:640/658`; needs the surrounding text to pick; not wrong, not self-resolving |
| Path not found as written | 7 | 4 × `app/module/cicflow_guest.go:30-36` = the container path of `module/cicflow_guest.go` (55 lines, in range); 2 × `cic-primitive-forms/go/schema.go:60,138` = Forms `go/schema.go` (557 lines, in range); 1 × `usr/local/go/src/go/types/sizes.go:229` = Go stdlib inside the builder image (outside every repo; quoted from a tool output; not checkable here) |
| File exists but line OUT OF RANGE | 0 | none found |
So: no reference points past the end of its file; none is demonstrably wrong; 109+9+7 need a repo prefix or context. "Line in range" proves reachability of the reference, not that the line supports the claim (next block).

### AM-run / AM-read sampling
- Content sample: 14 of the 41 AM rows that carry a full-path ref (seed 7). 14/14 point at a real line on the claim's subject; 0 contradicted. Three are weak (they cite the declaration, not the evidence line): `core/cabinet/stores.go:13` for "in-memory PoC" (an interface line, not the in-memory implementation), `module/contracts.go:17` for "exactly three resources" (one of three embed lines), `module/provider.go:812` for "Observe echoes the caller's resource_id" (a struct field; the echo is at the assignment near :866).
- Re-runs by the orchestrator (independent): `TestRealRegistrySchemas` 4/4 PASS against the registry at 6db77d4; `TestNormalizeObservedMatchesTheFixture` 9/9 subcases PASS; `TestVCNFixtureIsTheVendoredOne` PASS; module coverage 82.7%, oci-extract 88.7%, race green, gofmt/vet/staticcheck clean (rounds 4-5). Mutation, govulncheck, Q3/Q6/Q9: not re-run, `NIV` in the output.
- Class labelling in `claim-evidence.md`: all disputed items are `NIV`; the agent adopted the orchestrator's corrections rather than defending its own numbers.

### Rating: CONDITIONAL GO (as a partial baseline and design input, not as a closed 01a)
Reasons it is not a plain GO: mutation score, govulncheck, Q3/Q6/Q9 are `NIV`; the lifecycle gate has not run in its place (needs the branch on the remote); M2 and R1 are open owner decisions; the licence statement it relies on is only corrected in an open PR (#35). Reasons it is not HOLD: the four documents are internally consistent with the independent re-measurements, the immutable inputs are bit-identical, the scope was kept, and the central findings (NetworkSpace/VCN field gaps, create path outside Plan, OCID not propagated, normalizeObserved test-only, Relay 4-vs-8 ops, no Forms wiring) were each re-checked against code.
Conditions: (1) keep the `NIV` items out of any acceptance claim; (2) the nine ambiguous and the 109 bare-name refs get a repo prefix in any later revision (the outputs are immutable now, so this is a note, not an edit); (3) lifecycle `validate-output.sh` after the owner allows the feature-branch push; (4) M2 and R1 stay open, no mechanism chosen; (5) merge of #35 before the licence section is cited as corrected; (6) the three weak citations are re-pointed if the claims are reused.
Not done / not decided: push, `/job-close`, #35 merge, 01b, mutation re-run.
