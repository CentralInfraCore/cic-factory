# SPEC.md defects found by implementing it

Model version 0.1, measured against `SPEC.md` at `9ae04c1` and the 27-vector
corpus in `conformance/`.

This is the report the Go reference implementation produced by being the first
thing to execute the corpus. Sixteen defects are recorded. None of them was
worked around in code without being written down here first, and every one is
anchored by an `SD-nnn` comment at the place in `go/` where the choice was
forced.

**All 27 vectors pass.** That is not the same as "the specification is
correct": in six places the corpus and the normative text disagree, and the
corpus won, because `SPEC.md` §10 defines conformance as matching the vectors.
Those six are the ones to read first: **SD-003, SD-004, SD-005, SD-009,
SD-013, SD-014.**

## Severity

| | Meaning |
|---|---|
| **blocking** | Two normative statements cannot both hold. An implementer must violate one. |
| **divergent** | The corpus requires behaviour the normative text does not state, or contradicts. |
| **underspecified** | Two readings both satisfy the text and produce different output. |
| **editorial** | Wrong or incomplete, but not behaviour-changing. |

---

## SD-004 — INV-022 and INV-021 are both false of the root node

| | |
|---|---|
| **Where** | `SPEC.md` §6.1 (INV-021, INV-022), §11 (INV-033) |
| **Severity** | **blocking** |
| **Anchor** | `go/objectmodel/primitives.go`, `canonical.go`, `validate.go` |

INV-022: *"A canonical node MUST carry every primitive its schema declares for
that position."* Every vector schema declares `root: shape: object`. So every
canonical object's root node MUST carry a `shape` primitive.

**No expected.yaml in the corpus has one.** All 13 materialization vectors show
a root of exactly `cic`, `values`, `origin`.

Simultaneously INV-021: *"A node MUST NOT carry a member that is neither
`values`, `origin`, nor a member of the primitive set."* The root carries
`cic` (required by INV-033). `cic` is not `values`, not `origin`, and not one
of the eight atoms.

So the root node violates INV-021 as specified, and satisfying INV-022 on it
would break the entire corpus.

**Why it could not be worked around.** These are not compatible readings —
they are opposite outputs. Measured: with the root emitting its declared
`shape`, **13 of 13 materialization vectors fail**; with it omitted, 13 pass.

**Suggestion.** State that the document root is a node *plus* the `cic`
envelope member, and that INV-021/INV-022 are scoped to nodes below the root —
or make `cic` a sibling of the root node rather than a member of it. The second
is cleaner: it keeps INV-021 total.

---

## SD-005 — INV-005 is unfalsifiable as worded, and `invalid/008` tests something else

| | |
|---|---|
| **Where** | `SPEC.md` §2.3 (INV-005); `conformance/invalid/008_cyclic_primitive_declaration` |
| **Severity** | **divergent** |
| **Anchor** | `go/objectmodel/schema.go` — `checkPrimitiveCycle` |

INV-005 says the primitive-declaration graph must be acyclic: *"a primitive's
own primitives MUST NOT, directly or transitively, re-declare the node they
hang from."*

The vector schema language (`conformance/README.md`) is a **finite literal
tree**. It has no `$ref`, no named type reuse, no recursion mechanism. A schema
written in it cannot re-declare a node, and materialization against it cannot
fail to terminate. **INV-005 as stated cannot be violated by any schema the
corpus can express**, so it is not falsifiable.

What `invalid/008` actually contains is a finite, explicitly written nesting:

```
mtu.access.read.contract.rules.guard.access.read.contract.rules.guard: {}
```

That terminates. It is not a cycle in the node graph. The inner `access` hangs
from `guard`, not from `mtu`. The vector is testing a different and stronger
property: **acyclicity of the primitive-*name* graph** (`access` → `contract` →
`access`), which the expected error path confirms —
`$.mtu.access.read.contract.rules.guard.access` is the point where a primitive
name repeats on its own declaration path.

**Why it could not be worked around.** Implementing INV-005 literally makes the
check dead code and `invalid/008` fail. This implementation enforces the
name-graph property to pass the vector.

**Suggestion.** Either reword INV-005 to the property the vector tests ("a
primitive name MUST NOT reappear on its own declaration path"), or keep INV-005
and mark it unvectorizable-until-the-schema-language-has-references, and give
`invalid/008` its own invariant. Note the name-graph rule is strictly stronger
and forbids legitimate finite schemas — that trade-off should be a decision,
not a side effect.

---

## SD-013 — §8.7 must discriminate without a schema, which INV-008 forbids

| | |
|---|---|
| **Where** | `SPEC.md` §4.3 (INV-008), §8.7; `conformance/validation/*` |
| **Severity** | **blocking** |
| **Anchor** | `go/objectmodel/validate.go` — `validatePayload` |

INV-008: *"Whether a mapping is a node envelope or payload MUST be determined
by the schema-declared shape at that position. An implementation MUST NOT
decide this by inspecting keys alone."*

All six `validation/` vectors supply **`object.yaml` and nothing else** — no
`schema.yaml`. `conformance/README.md` explains why this is necessary: truth
table rows 7 and 8 are unreachable from authoring input, so they can only be
exercised against an already-canonical object.

But final validation has to walk that object, and to walk it it has to know
which mappings are nodes. With no schema, the only available signal is key
inspection — precisely what INV-008 prohibits.

**Why it could not be worked around.** There is no third option. This
implementation inspects keys (a mapping is a node iff it contains `values`) and
therefore violates INV-008 on the `validation/*` path. The failure mode is
real, not theoretical: an opaque payload that happens to contain a `values` key
mapping to a mapping will be mis-identified as a node and validated as one.

**Suggestion.** Scope INV-008 to materialization (§8.1–§8.6), and state
explicitly that §8.7 on a schema-less object is structural, key-directed, and
weaker — or require `validation/` vectors to carry the schema.

---

## SD-003 — primitive payloads are not materialized, contradicting §2.2 and INV-027

| | |
|---|---|
| **Where** | `SPEC.md` §2.2, §7 (INV-027); `conformance/materialization/011`, `013` |
| **Severity** | **divergent** |
| **Anchor** | `go/objectmodel/primitives.go` — `normalizePrimitive` |

§2.2 is the passage that motivates the whole recursive model:

> This is what makes `network.values.mtu.access.read` a first-class,
> addressable object rather than a path into a YAML blob. It can be hashed,
> diffed, referenced from evidence, and governed by its own `access` — because
> it is a node like any other.

In the corpus it is not. `materialization/013` expects:

```yaml
access:
  values:
    read:
      rules: {operator: {subjects: [...], effect: allow}}
      inherit: true
      default_injection: 0
  origin: [schema]
```

`access.read` is a plain mapping. It has no `values`, no `origin`, no address
of its own. It cannot be governed by its own `access`, and it cannot be
referenced from evidence as a node — exactly the properties §2.2 claims for it.
The same is true of `shape.values`, which is a raw `{type, scalar_type}` map.

INV-027 compounds this: *"A structured object known to the schema MUST be
recursively materialized: every schema-known child MUST become a CIC node."*
The `access` declaration in `schema.yaml` **is** schema-known and structured.

**Why it could not be worked around.** Materializing primitive payloads into
nodes fails `materialization/011` and `013`. This implementation keeps them
verbatim.

**Suggestion.** Decide whether primitive-internal structure is nodes or data.
If data (as the corpus says), §2.2's motivating example is wrong and should be
replaced — it is currently the strongest argument in the document for a
property the model does not have. If nodes, both vectors need rewriting and the
recursion needs a stated depth bound.

---

## SD-014 — INV-007 and INV-011 disagree about `origin` in a non-opaque payload

| | |
|---|---|
| **Where** | `SPEC.md` §3 (INV-007), §4.3 (INV-010, INV-011) |
| **Severity** | **blocking** |
| **Anchor** | `go/objectmodel/entry.go` — `entryWalk` |

INV-007: *"Authoring input MUST NOT contain an `origin` member at any depth
**outside an opaque payload**."*

INV-011: *"Below a `values` member, no CIC primitive interpretation applies.
Keys named `values`, `origin`, `access`, `shape` or any other primitive name
occurring in payload are domain data and MUST be preserved verbatim."*

A structured (non-opaque) payload containing a key named `origin` satisfies
INV-011's "preserve verbatim" and violates INV-007's "at any depth outside an
opaque payload". INV-010 reserves only `values` at schema-declaration time, so
a schema may legally declare a child named `origin` and make this reachable.

**Measured.** With a schema declaring `iface.origin: {shape: scalar}` and input
`iface: {origin: customer-supplied}`, this implementation (following INV-011)
produces a canonical object containing:

```yaml
values:
  iface:
    values:
      origin:                       # a node named origin...
        values: customer-supplied
        origin: [yaml]              # ...carrying its own origin
```

Following INV-007 instead, the same input is rejected at entry validation. Two
readings, both textually supported, opposite outputs. No vector covers it.

**Why it could not be worked around.** A choice was forced. This implementation
applies INV-007 to envelope-level `origin` members only, which is what passes
both `invalid/005` (envelope `origin` → rejected) and `materialization/012`
(opaque payload `origin` → preserved).

**Suggestion.** Either extend INV-010 to reserve `origin` as well as `values`
at schema-declaration time — which makes the conflict unreachable and is the
smaller change — or restate INV-007 as "MUST NOT contain an `origin` **envelope
member**".

---

## SD-009 — §8.2 has no syntax, no vector, and INV-031(a) is mis-mapped

| | |
|---|---|
| **Where** | `SPEC.md` §8.2, §9 (INV-031a); `docs/spec-vector-map.md` |
| **Severity** | **divergent** |
| **Anchor** | `go/objectmodel/refs.go` |

§8.2 is a normative pipeline stage with two MUSTs and a FAILURE clause. The
vector schema language defines **no external-reference syntax at all**, so no
input can carry a reference, no vector exercises the stage, and the stage is
necessarily a no-op in any 0.1-conformant implementation.

`docs/spec-vector-map.md` claims otherwise. Its INV-031 row maps clause (a)
*"unresolved references"* to **`invalid/003_closure_undeclared`** — a vector
whose `meta.yaml` declares `invariants: [INV-029]` and whose subject is an
undeclared arbitrary object. It has nothing to do with reference resolution.
The clause is listed as covered and is not.

This also punctures the claim in §10 that "every normative statement in this
document is mapped to a vector or is explicitly marked unvectorizable":
`check_spec_vectors.py` checks `INV-nnn` ↔ vector mappings, and the FAILURE
clauses of §8.1–§8.8 carry no INV numbers, so they escape the gate entirely.
§8.5's *"a required value neither authored nor defaultable → reject"* has no
code, no vector and no invariant.

**Suggestion.** Mark §8.2 out of scope for 0.1 alongside the template
resolution protocol (§1 already excludes that), correct the INV-031(a) mapping,
and give the §8 FAILURE clauses invariant numbers so the gate can see them.

---

## SD-002 — `schema-load` is a pipeline stage §8 does not have

| | |
|---|---|
| **Where** | `SPEC.md` §8; `conformance/README.md` error table |
| **Severity** | **divergent** |
| **Anchor** | `go/objectmodel/errors.go` — `StageSchemaLoad` |

§8 enumerates eight stages, beginning at entry validation. Three vectors
(`invalid/004`, `007`, `008`) assert `stage: schema-load`, and
`conformance/README.md` lists two error codes as "Raised at: schema load".

`conformance/README.md` also makes stage placement normative and binding:
*"Rejecting with the right code at the wrong stage is a failure."* So an
implementation is required to raise errors at a stage the normative pipeline
does not define. §8 also names none of its stages — the strings
`entry-validation`, `primitive-evaluation` and `final-validation` exist only in
the vectors.

**Suggestion.** Add §8.0 "Schema load" with its own INPUT/OUTPUT/MUST/FAILURE
block (INV-010, INV-015, INV-005 belong to it), and give every stage its
normative string name in §8.

---

## SD-001 — `access` sub-defaults are injected by the vectors, by no invariant

| | |
|---|---|
| **Where** | `SPEC.md` §6.4 (INV-025, INV-026); `materialization/011`, `013` |
| **Severity** | **underspecified** |
| **Anchor** | `go/objectmodel/primitives.go` — `normalizePrimitive` |

`materialization/013`'s schema declares `access.read` with no `inherit`. The
expected output has `inherit: true`. So a sub-default was injected.

The same vector's `access.modify` has no `default_injection`, and INV-026 says
its default is `null` — the expected output does **not** contain
`default_injection: null`. So that sub-default was not injected.

Both fields are described as having a default in identical language
("`true` (default)", "`null` (the default)"). One is materialized, the other is
not, and no invariant states that primitive-internal defaults are materialized
at all. INV-022 governs *primitives*, not fields inside a primitive's payload.

**Why it could not be worked around.** Injecting both fails `013`; injecting
neither fails `011` and `013`. This implementation injects `inherit` only,
matching the corpus.

**Suggestion.** State the rule: which primitive-internal fields are
materialized when absent, and which are absent-means-default. As written, an
independent implementer has no way to derive the corpus's behaviour.

---

## SD-006 — a sealed node's shape and children come from the template, unstated

| | |
|---|---|
| **Where** | `SPEC.md` §8.3; `materialization/003`, `004` |
| **Severity** | **underspecified** |
| **Anchor** | `go/objectmodel/template.go` — `buildEffective` |

In both vectors, `access_policy` is declared with `sealed_from` **and nothing
else** — no `shape`, no `children`, no `default`. The expected output gives it
`shape: {values: {type: object}, origin: [schema]}` and a fully materialized
child.

So the node's entire schema is adopted from the template entry at the
referenced path. §8.3's MUST covers only origin recording ("record template
identity and source path"); nothing says the template's *schema* becomes the
node's schema, which is the larger behaviour.

A second unstated rule sits inside the same vectors: the child `enabled` gets
`path: $.access.read` in its origin — the template **mount** path, not the
child's own path within the template (`$.access.read.enabled`). INV-015 says
the path exists to distinguish instantiations, which is consistent with the
mount path, but the choice is nowhere stated.

**Suggestion.** Add to §8.3: a `sealed_from` node adopts the referenced
template node's schema in full, and every node produced from that expansion
carries the mount path — not its own sub-path — in its origin's `sealed` term.

---

## SD-010 — INV-030 requires byte-identity; §8.8 defines no serialization

| | |
|---|---|
| **Where** | `SPEC.md` §8 (INV-030), §8.8, §10 |
| **Severity** | **underspecified** |
| **Anchor** | `go/objectmodel/yamlutil.go`, `canonical.go` |

INV-030: *"the same schema and input MUST produce a byte-identical canonical
object."* §8.8: *"MUST produce a deterministic serialization."* §10: output must
match `expected.yaml` **"exactly"**.

Nothing defines the mapping key order, the indent, the sequence style, or the
scalar quoting. Two conformant implementations will produce different bytes for
the same object — Go and Rust certainly will, and the corpus itself is
inconsistent (`origin: [yaml]` flow style in the expected files, which no
stated rule requires).

Read strictly, INV-030 is only per-implementation determinism, and then §10's
"exactly" cannot mean bytes. Read as cross-implementation, INV-030 is
unsatisfiable without a canonical form.

**Why it could not be worked around.** This implementation defines its own
order (node members: `values`, `origin`, then primitives in §6.1 order; payload
mappings sorted) and the vector runner compares **parsed structure, not
bytes**. A byte comparison would fail all 13 materialization vectors purely on
formatting.

**Suggestion.** Specify a canonical serialization in §8.8, or state that
conformance is semantic equality of the parsed object and demote INV-030 to
per-implementation determinism. This matters more than it looks: `origin` is
supposed to be hashable evidence, and a hash over undefined bytes is not
evidence.

---

## SD-012 — §8.6 mandates `inherit` chain resolution that 0.1 cannot perform

| | |
|---|---|
| **Where** | `SPEC.md` §1, §6.4 (INV-025), §8.6 |
| **Severity** | **blocking** |
| **Anchor** | `go/objectmodel/primitives.go` — `evaluatePrimitives` |

§8.6 MUST: *"materialize every declared primitive (INV-022); **resolve
`inherit` chains for `access`** (INV-025)."*

INV-025's tri-state cannot be resolved in 0.1:

- `true` → "sub-objects inherit this rule" — needs a parent rule to inherit.
- `0` → "full reset; the sub-object **recomputes from its PolicySurface**".

§1 puts the runtime policy-decision point out of scope, and
`docs/decision-delta.md` defers PolicySurface entirely, stating that
per-operation inheritance semantics *"will have to define what per-operation
inheritance means when the two operations disagree. This specification does not
define that."*

So §8.6 contains a MUST whose semantics the same document declines to define.
`materialization/013` records `read.inherit: true` and `modify.inherit: 0`
verbatim — divergent, unresolved — so no vector requires resolution either.

**Why it could not be worked around.** Resolution is not implementable without
inventing PolicySurface semantics, which would be spec invention. This
implementation records `inherit` and does not resolve it. **DoD-relevant: this
is one §8.6 MUST this implementation does not satisfy, and cannot.**

**Suggestion.** Strike "resolve `inherit` chains" from §8.6 for 0.1 and add it
to §1's out-of-scope list next to the policy-decision point, so the pipeline
does not carry an obligation the model defers.

---

## SD-007 — no rule for an absent value that is neither defaultable nor required

| | |
|---|---|
| **Where** | `SPEC.md` §8.5 |
| **Severity** | **underspecified** |
| **Anchor** | `go/objectmodel/defaults.go` — `materializeDefaults` |

§8.5's only FAILURE is *"a required value neither authored nor defaultable →
reject"*. A child that is declared, **not** required, has no default, and is not
authored, falls through every clause. INV-001 forbids a node without `values`,
so it cannot be emitted empty. No vector reaches the case.

Three possible behaviours — omit the node, emit `values: null`, reject — and
nothing selects one. This implementation omits it, the only option that neither
invents a value nor violates INV-001.

**Suggestion.** Add the rule to §8.5. "Omitted" is the natural choice but it
has a consequence worth stating: the canonical object's member set then depends
on what was authored, which weakens INV-022's "every primitive its schema
declares" into "every primitive of every node that exists".

---

## SD-008 — INV-029 covers objects; undeclared scalars are unruled

| | |
|---|---|
| **Where** | `SPEC.md` §7 (INV-029), §8.1 |
| **Severity** | **underspecified** |
| **Anchor** | `go/objectmodel/entry.go` — `entryPayload` |

INV-029: *"An **object** that is neither schema-known nor explicitly declared
opaque is invalid and MUST be rejected."* `invalid/003` exercises exactly that —
`surprise: {arbitrary: structure}`.

An undeclared **scalar** (`surprise: 5`) is not an object. No invariant rejects
it, and nothing says to keep it either — and it cannot be kept, since it has no
schema position and so no shape, no origin rule and no place in the canonical
form. Silently dropping authored data is the worst of the three outcomes.

This implementation rejects undeclared children of any type with
`E_UNDECLARED_OBJECT`/INV-029, which is stricter than the invariant says.

**Suggestion.** Reword INV-029 to "a value" rather than "an object", or add a
companion invariant for undeclared scalars.

---

## SD-011 — the schema language is normative in behaviour, informal in status

| | |
|---|---|
| **Where** | `SPEC.md` (absent); `conformance/README.md` "Schema language used by the vectors" |
| **Severity** | **editorial** |
| **Anchor** | `go/objectmodel/schema.go` — `parseSchemaNode` |

`SPEC.md` says the schema decides everything — the discriminator (INV-008), the
primitive set at a position (INV-022), opacity (INV-028), defaults (§8.5) — and
never defines what a schema is. The only definition is a fenced block in
`conformance/README.md` introduced as *"Deliberately minimal — just enough to
exercise the model"*.

Consequences an implementer hits immediately: whether an unrecognised schema key
is an error or inert (this implementation rejects, fail-closed); whether
`shape:`+`scalar_type:` siblings collapsing into one `shape` primitive node is
normative (the vectors require it, no text states it); whether a schema may
declare a primitive at a position the instance may then override (`011` relies
on it).

**Suggestion.** Either promote the schema language to a normative section of
`SPEC.md`, or state explicitly that the vector schema language is a test
fixture and that real schemas come from `CIC-Schemas` — in which case the
corpus is testing the model through a language that is not the real one, and
that should be said out loud.

---

## SD-015 — `conformance/README.md`'s error table lists 8 of 13 codes

| | |
|---|---|
| **Where** | `conformance/README.md` "Error codes" |
| **Severity** | **editorial** |

The table is presented as the code set and the stage mapping. Five codes used
by vectors are missing from it:

| Missing code | Vector | Stage |
|---|---|---|
| `E_CYCLIC_PRIMITIVE_DECLARATION` | `invalid/008` | schema-load |
| `E_ORIGIN_NOT_TERMINAL` | `validation/003` | final-validation |
| `E_DOCUMENTATION_ON_NODE` | `validation/004` | final-validation |
| `E_DEFAULT_MEMBER_ON_NODE` | `validation/005` | final-validation |
| `E_MISSING_MODEL_VERSION` | `validation/006` | final-validation |

Since the table is the only place stage placement is stated normatively
("An implementation MUST raise the stated code at the stated stage"), a code
absent from it has no specified stage at all.

**Suggestion.** Complete the table, and add the codes §8's FAILURE clauses
require but no vector exercises (see SD-009).

---

## SD-016 — INV-032 is not fully achievable in Go; the residue is `nil`

| | |
|---|---|
| **Where** | `SPEC.md` §9 (INV-032) |
| **Severity** | **editorial** |
| **Anchor** | `go/objectmodel/materialize.go`, `go/module/module.go` |

INV-032 requires that a value of `Validated<Canonical<CICObject>>` be
*"constructible only by the core materializer"*, and names the mechanism: *"an
unexported constructor in Go"*.

An unexported constructor is not sufficient on its own — an unexported
constructor still leaves the exported struct's zero value constructible
(`var o objectmodel.Object` compiles anywhere). This implementation uses the
stronger available construct: an interface with an unexported marker method,
which no external package can implement. Verified by a compile-fail artifact
(`go/inv032/testdata/forge/`).

One hole remains and no Go construct closes it: the **nil interface value**.
`var o objectmodel.CanonicalObject` is legal in any package. It cannot carry
forged *data* — there is no object behind it — so it is a liveness rather than
an integrity problem, and `module.Execute` rejects it at runtime.

**Suggestion.** Reword INV-032's Go clause from "an unexported constructor" to
"an interface with an unexported method, or an unexported concrete type", and
state that the nil case is a runtime check. Rust's `compile_fail` newtype has
no equivalent hole, so the two implementations are not equally strong here —
worth saying in the spec rather than discovering at review.

---

## What the defects do not include

Three things the job brief flagged as suspicious were examined and found sound:

- **§4.3's `list` row** ("a mapping at a list position is an envelope"). The
  table is per-position, and a list *element*'s position is typed by `item:`,
  so element mappings are discriminated by the `object` row. A list payload can
  never be a mapping, so the row is correct as written. No defect.
- **INV-022 and `role`** ("every node carries `shape`, but `role` only where
  declared"). Consistent: `shape` is declared at every position and `role` only
  in `materialization/013`. The real inconsistency is the root node — SD-004.
- **INV-025 with divergent per-operation `inherit`.** Materialization records
  both operations independently, so divergence is representable and
  `materialization/013` passes. The problem is not representation but
  resolution, recorded as SD-012.
