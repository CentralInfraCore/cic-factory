# cic-object-model

The normative specification of the CIC object model, its conformance vectors,
and (once the implementation sub-jobs land) the Go and Rust reference
implementations.

**[`SPEC.md`](SPEC.md) is the authority.** The implementations are subordinate
to it: where an implementation disagrees with the specification, the
implementation is wrong.

---

## Status

| Component | Status |
|---|---|
| `SPEC.md` — 34 numbered invariants | written, normative |
| `conformance/` — 27 vectors | **written, never executed** |
| `docs/spec-vector-map.md` | 32/34 invariants vector-covered, 2 declared unvectorizable |
| `tools/check_spec_vectors.py` | runs and passes; negative-tested |
| `go/` | empty — `cic-object-model-go` sub-job |
| `rust/` | empty — `cic-object-model-rust` sub-job |
| `mk/rust.mk` | absent — see [`docs/rust-gate-extraction.md`](docs/rust-gate-extraction.md) |
| Docker build / CI | **not executed** — no Docker in the authoring environment |

No vector in this repository has ever run, because nothing here can run one
yet. `make conformance` fails rather than reporting success when no
implementation is present; a vector corpus that passes vacuously is worse than
none.

---

## Why a specification repository at all

Two properties are being frozen, and both need to be frozen *before* code
exists rather than distilled from it afterwards:

1. **The recursive node model** — primitives are not metadata attached to a
   node; they are CIC nodes themselves, which is what makes
   `network.values.mtu.access.read` an addressable, hashable, governable object
   rather than a path into a YAML blob.
2. **Closed semantics** — notably `origin`'s four permitted forms, and the
   three-rule object closure that leaves no way to smuggle an uninterpreted
   object graph past the model.

Spec, vectors and both implementations live in one repository on purpose. A
semantic change then arrives as a single change — SPEC + vectors + Go + Rust —
and it becomes physically awkward to alter one implementation's behaviour
without the corpus and the other implementation noticing. That mutual check is
the reason there are two implementations rather than one.

---

## Layout

```
SPEC.md                     the normative specification
spec/                       machine-readable schemas for the model itself
conformance/                the falsifiable part — YAML in, YAML out
  materialization/            authoring input -> canonical object
  invalid/                    input that MUST be rejected
  validation/                 canonical object -> accept / reject
docs/
  spec-vector-map.md          every invariant -> its vectors, or why it has none
  decision-delta.md           what this model changes in D-003 / D-011
  migration-surface.md        the measured file list this model would change
  branch-decision.md          why base-repo wasm/main
  rust-gate-extraction.md     line-referenced recipe for mk/rust.mk
go/                         reference implementation (sub-job)
rust/                       reference implementation (sub-job)
```

## Make targets

| Target | What it does |
|---|---|
| `make check` | Python/YAML quality gate |
| `make manifest-verify` | `MANIFEST.sha256` integrity |
| `make docs.link-check` | internal documentation links resolve |
| `make golang.quality` | Go gate over `go/` |
| `make conformance` | run the corpus against every present implementation |

`tools/check_spec_vectors.py` runs in CI and fails if `SPEC.md` and the vector
corpus drift apart — if an invariant claims a vector that does not exist, or a
vector claims an invariant that does not. It checks the *mapping*; it does not
run vectors.

## Reading order

1. [`SPEC.md`](SPEC.md) §2 (node model) and §4 (the discriminator) — the two
   sections everything else depends on
2. [`SPEC.md`](SPEC.md) §5 (origin) and its truth table
3. [`conformance/README.md`](conformance/README.md) — the vector format
4. [`docs/decision-delta.md`](docs/decision-delta.md) — what this changes and
   what it would otherwise have lost silently

## License

CC-BY-NC-SA-4.0 — see [`LICENSE.md`](LICENSE.md).
