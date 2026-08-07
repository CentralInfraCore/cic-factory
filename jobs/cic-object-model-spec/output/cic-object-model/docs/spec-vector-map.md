# SPEC ↔ conformance vector map

Every normative statement in [`../SPEC.md`](../SPEC.md) is either backed by at
least one conformance vector or listed in [Unvectorizable](#unvectorizable)
with a justification. There is no third category: an invariant that is neither
covered nor explicitly excused is a gap, and
[`../tools/check_spec_vectors.py`](../tools/check_spec_vectors.py) fails the
build when one appears.

**This map records coverage, not results.** Every vector below is written and
none has been executed — no implementation exists in this repository yet. A
vector that has never run is a hypothesis.

## Coverage

| Invariant | Statement | § | Vectors |
|---|---|---|---|
| INV-001 | Exactly one `values` per node | 2.1 | `materialization/001_origin_yaml` <br> `materialization/005_closure_structured` <br> `materialization/007_normalize_scalar` <br> `materialization/008_normalize_list` <br> `materialization/009_normalize_map` |
| INV-002 | Exactly one `origin` per canonical node | 2.1 | `materialization/001_origin_yaml` <br> `materialization/002_origin_schema` <br> `materialization/005_closure_structured` <br> `materialization/007_normalize_scalar` <br> `materialization/008_normalize_list` <br> `materialization/009_normalize_map` <br> `validation/002_origin_empty` |
| INV-003 | Every primitive is itself a CIC node | 2.2 | `validation/003_origin_not_terminal` |
| INV-004 | `origin` is terminal | 2.3 | `validation/003_origin_not_terminal` |
| INV-005 | Primitive materialization terminates; declaration graph acyclic | 2.3 | `invalid/008_cyclic_primitive_declaration` |
| INV-006 | No documentation member on a canonical node | 2.4 | `validation/004_documentation_member` |
| INV-007 | Authoring input MUST NOT contain `origin` | 3 | `invalid/005_origin_in_authoring_input` |
| INV-008 | Envelope/payload decided by schema position, not keys | 4.3 | `materialization/007_normalize_scalar` <br> `materialization/011_discriminator_envelope` <br> `materialization/012_discriminator_payload_keywords` |
| INV-009 | At structured positions: envelope iff `values` present | 4.3 | `invalid/004_schema_declares_values_child` <br> `materialization/011_discriminator_envelope` |
| INV-010 | Schema MUST NOT declare a child named `values` | 4.3 | `invalid/004_schema_declares_values_child` <br> `materialization/011_discriminator_envelope` |
| INV-011 | No primitive interpretation below `values` | 4.3 | `materialization/006_closure_opaque` <br> `materialization/012_discriminator_payload_keywords` |
| INV-012 | No `default` member on a canonical node | 4.5 | `validation/005_default_member` |
| INV-013 | Origin grammar — exactly four forms | 5.2 | `materialization/001_origin_yaml` <br> `materialization/002_origin_schema` <br> `materialization/003_origin_sealed` <br> `materialization/004_origin_sealed_schema` <br> `materialization/009_normalize_map` <br> `materialization/010_normalize_empty_object` <br> `validation/001_origin_yaml_schema_conflict` |
| INV-014 | Origin is classification, not history | 5.2 | `invalid/005_origin_in_authoring_input` |
| INV-015 | `sealed` MUST carry `template` and `path` | 5.2 | `invalid/007_sealed_missing_path` <br> `materialization/003_origin_sealed` <br> `materialization/004_origin_sealed_schema` |
| INV-016 | `sealed` + `yaml` → invalid | 5.3 | `invalid/001_sealed_yaml_conflict` <br> `invalid/002_sealed_yaml_schema_conflict` |
| INV-017 | `yaml` + `schema` → invalid | 5.3 | `validation/001_origin_yaml_schema_conflict` |
| INV-018 | Empty origin → invalid | 5.3 | `validation/002_origin_empty` |
| INV-019 | No authoring at or below a sealed boundary | 5.4 | `invalid/001_sealed_yaml_conflict` <br> `invalid/002_sealed_yaml_schema_conflict` <br> `materialization/003_origin_sealed` <br> `materialization/004_origin_sealed_schema` |
| INV-020 | Origin `sealed` always a constructor; distinct from slot mode | 5.5 | `invalid/007_sealed_missing_path` <br> `materialization/003_origin_sealed` |
| INV-021 | Unknown primitives rejected | 6.1 | `invalid/006_unknown_primitive` |
| INV-022 | Every schema-declared primitive materialized | 6.1 | `invalid/006_unknown_primitive` |
| INV-023 | Named addressable entries, not anonymous lists | 6.3 | `materialization/013_access_inherit_injection` |
| INV-024 | `access` operations are `read` and `modify` | 6.4 | `materialization/013_access_inherit_injection` |
| INV-025 | `inherit` retained, per-operation, tri-state | 6.4 | `materialization/013_access_inherit_injection` |
| INV-026 | `default_injection` retained, `access.read` only | 6.4 | `materialization/013_access_inherit_injection` |
| INV-027 | Structured object → recursively materialized | 7 | `materialization/005_closure_structured` <br> `materialization/008_normalize_list` <br> `materialization/009_normalize_map` <br> `materialization/010_normalize_empty_object` |
| INV-028 | Explicit opaque → terminal value | 7 | `materialization/006_closure_opaque` <br> `materialization/012_discriminator_payload_keywords` |
| INV-029 | Undeclared arbitrary object → invalid | 7 | `invalid/003_closure_undeclared` |
| INV-030 | Materialization is deterministic | 8 | `materialization/001_origin_yaml` <br> `materialization/002_origin_schema` |
| INV-031 | Seven things a module MUST NOT receive | 9 | **see Unvectorizable** |
| INV-032 | Module input type constructible only by the materializer | 9 | **see Unvectorizable** |
| INV-033 | Canonical objects carry the model version | 11 | `validation/006_missing_model_version` |
| INV-034 | Modules declare the model version they consume | 11 | `validation/006_missing_model_version` |

**32 of 34 invariants are vector-covered.** The remaining
2 are below.

## Unvectorizable

A YAML-in / YAML-out vector can express any property of an *object*. It cannot
express a property of an *API*. These two invariants are of the second kind,
so they are assigned to the implementation sub-jobs as source-level checks
instead of being silently left uncovered.

| Invariant | Why no vector | How it is checked instead |
|---|---|---|
| INV-031 | The seven prohibitions (a–g) are properties of what crosses a module boundary, and this repository contains no module and no boundary. Each clause is nonetheless enforced *upstream* by an existing vector — the pipeline eliminates the condition before a module could observe it — so the risk is not that a clause is unenforced but that no single test names the boundary itself. | Clause-by-clause upstream coverage: (a) unresolved references — `invalid/003_closure_undeclared`; (b) short forms — `materialization/007_normalize_scalar`, `008`, `009`; (c) templates — `materialization/003_origin_sealed`, `004`; (d) sealed fragments — `invalid/001_sealed_yaml_conflict`; (e) unapplied defaults — `materialization/002_origin_schema`, `010`; (f) unknown primitives — `invalid/006_unknown_primitive`; (g) unvalidated objects — all `validation/*`. A true boundary test is deferred to the sub-jobs, which must add one integration test per clause. |
| INV-032 | States that `Validated<Canonical<CICObject>>` must be *unconstructible* outside the materializer. Unconstructibility is a compile-time property of a type; no data file can demonstrate it, because the failure mode is code that compiles when it should not. | Source-level, per implementation. Go: the type's constructor and fields unexported, verified by a test in a separate package that must fail to compile — plus `grep -rn` for any exported constructor. Rust: private-field newtype, verified by a `compile_fail` doctest. Both sub-job specs require this artifact by name. |

## Reading this map when reviewing a spec change

A change to a normative sentence in `SPEC.md` is not complete until this table
is regenerated and `check_spec_vectors.py` passes. That gate is what keeps the
spec from acquiring MUSTs that nothing tests — the failure mode this whole
document exists to prevent.
