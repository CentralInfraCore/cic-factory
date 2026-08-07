# CIC Object Model — Normative Specification

**Model version: 0.1**
**Status: normative, unimplemented.** No implementation of this document exists
yet. The conformance corpus in `conformance/` has been written but never
executed. See [Conformance](#10-conformance) for what that means for the
reader.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
MAY and OPTIONAL in this document are to be interpreted as described in
RFC 2119.

This document is the authority. The `go/` and `rust/` implementations are
subordinate to it: where an implementation disagrees with this document, the
implementation is wrong. Where this document disagrees with itself, that is a
defect to be reported, not resolved by an implementer's judgement.

---

## 1. Scope and purpose

The CIC object model defines the single semantic form in which infrastructure
objects are represented between the point where a human (or an agent) authors
YAML and the point where a provisioner module receives an object to act on.

It exists to remove interpretation from every layer below the schema. A module
does not decide what an input means, whether a default applies, whether a
reference resolves, or who may write a field. All of that is decided before the
module is reachable, by the pipeline in §8, and the result is the only thing a
module can be handed (§9).

**Out of scope for 0.1:** the CertPattern matching algorithm, the template
repository/resolution protocol, the wire encoding of a canonical object, and
the runtime policy-decision point. This document specifies the object model and
its materialization, not the systems that consume it.

---

## 2. The node model

### 2.1 Definition

A **CIC node** is the single structural unit of the model. Every node has the
same grammar, at every depth, regardless of what it describes.

```
CICNode :=
{
    values : Value          # REQUIRED — the payload
    origin : Origin         # REQUIRED in canonical form — authoring authority
    <primitive> : CICNode   # zero or more, one per declared primitive
}

Value :=
      Scalar                # string | integer | number | boolean | bytes | null
    | List<CICNode>
    | Map<String, CICNode>
    | Opaque                # terminal; see §7
```

`values` is the payload. Everything else on the node describes the payload's
semantics. This is the whole model.

**INV-001** — Every CIC node MUST have exactly one `values` member.

**INV-002** — Every CIC node in canonical form MUST have exactly one `origin`
member.

### 2.2 Why it is recursive

The members that describe the payload — `shape`, `role`, `contract`, `access`,
and the rest of §6 — are **not metadata fields attached to the node**. Each is
itself a CIC node, with its own `values`, its own `origin`, and potentially its
own primitives.

This is what makes `network.values.mtu.access.read` a first-class, addressable
object rather than a path into a YAML blob. It can be hashed, diffed,
referenced from evidence, and governed by its own `access` — because it is a
node like any other.

**INV-003** — Each primitive member of a node MUST itself be a CIC node
satisfying INV-001 and INV-002.

### 2.3 Why the recursion terminates

INV-003 as stated is non-terminating: if `access` is a node, it has an `origin`;
if `origin` were a node, it would have an `origin`, and so on without end. The
model is only implementable because two things bound it.

**INV-004** — `origin` is terminal. An `origin` member MUST NOT itself carry
`values`, `origin`, or any primitive. It is a value in the grammar of §5, not a
node.

**INV-005** — Primitive materialization MUST terminate. A schema declares a
finite set of primitives per node, and the primitive-declaration graph MUST be
acyclic: a primitive's own primitives MUST NOT, directly or transitively,
re-declare the node they hang from. An implementation encountering such a cycle
MUST reject the schema.

INV-004 is the reason `origin` is not a ninth atom (§6.2): it is the fixed
point of the recursion, and a fixed point cannot be a member of the set it
terminates.

### 2.4 What is not on the node

`descr` / `description` is **not** part of the instance node. Documentation is a
property of the schema, not of a value instance; carrying it on every
materialized node would duplicate schema knowledge into every object.

**INV-006** — A canonical CIC node MUST NOT carry a documentation member.
Documentation MUST be obtained from the schema.

---

## 3. The two planes

The model has two planes, and most confusion about it comes from conflating
them.

| | Authoring plane | Canonical plane |
|---|---|---|
| Written by | human / agent, in YAML | the materializer, never by hand |
| Shape | partial subtree, short forms allowed | every node fully expanded |
| `origin` | MUST NOT appear | REQUIRED on every node |
| Below `values` | domain data, uninterpreted | CIC nodes (unless opaque) |
| Consumed by | the materializer | modules (§9) |

The author does not write a CIC object. The author writes a **value subtree**;
the schema plus the materializer produce the CIC object from it.

**INV-007** — Authoring input MUST NOT contain an `origin` member at any depth
outside an opaque payload. `origin` is computed, never declared. An input
containing one MUST be rejected at entry validation (§8.1).

INV-007 is what makes `origin` trustworthy: a node cannot claim its own
provenance.

---

## 4. The structural discriminator

### 4.1 The problem

In the authoring plane, `mtu: 9000` and

```yaml
mtu:
  values: 9000
  access:
    modify:
      rules:
        net-admin:
          subjects: ["OU=network-admins,O=acme"]
          effect: allow
```

must both be accepted, and something must decide whether a given mapping is a
**node envelope** or **payload**.

### 4.2 What does not work

A purely syntactic rule — "a mapping is an envelope iff it directly contains
`values` and `default`" — is **unsound in both directions**, and this
specification does not adopt it.

*False positive.* Domain payload legitimately carrying both keys is misread as
an envelope:

```yaml
checkbox:
  values: [on, off]     # a domain enumeration
  default: false        # the domain's own default
```

*False negative.* It rejects canonical nodes, which carry `values` and `origin`
but no `default` (§4.5).

### 4.3 The rule

The schema is always available during materialization. It — not key inspection
— decides the plane.

**INV-008** — Whether a mapping is a node envelope or payload MUST be
determined by the schema-declared shape at that position. An implementation
MUST NOT decide this by inspecting keys alone.

Given the schema-declared shape at a position, for an authoring value `V`:

| Declared shape | `V` is a mapping | `V` is not a mapping |
|---|---|---|
| `scalar` | envelope (a scalar position cannot hold a map payload) | payload (short form) |
| `list` | envelope | payload (short form) |
| `object` (structured) | envelope **iff** `V` contains key `values`; else payload | payload (short form) |
| `opaque` | payload, always (§7) | payload |

**INV-009** — At a structured-object position, a mapping MUST be treated as a
node envelope if and only if it directly contains the key `values`.

**INV-010** — A schema MUST NOT declare a child property named `values` at a
structured-object position. A schema that does MUST be rejected.

INV-010 is what makes INV-009 total: with the name unavailable to schema
authors, no structured payload can accidentally present as an envelope. This is
a constraint on *schema declaration*, not a global reserved word — `values` is
free as a key inside any payload, at any depth below a `values` member, and
inside any opaque subtree.

**INV-011** — Below a `values` member, no CIC primitive interpretation applies.
Keys named `values`, `origin`, `access`, `shape` or any other primitive name
occurring in payload are domain data and MUST be preserved verbatim.

So this input is unambiguous and entirely legal:

```yaml
interface:
  values:
    name: eth0
    access: customer      # domain data — INV-011
    values:
      foo: bar            # domain data — INV-011
  access:                 # CIC primitive — envelope level
    read:
      rules:
        ops:
          subjects: ["OU=operators,O=acme"]
          effect: allow
```

`interface.access` is a primitive; `interface.values.access` is a string.

### 4.4 `values` is plural because the payload is uniform

`values` holds the payload whether it is a scalar, a list, or a map. There is no
separate `value` / `values` distinction by arity — one member, one name, always.

### 4.5 `default` is not part of the model

The authoring-plane marker `default: true` — "this value came from a default"
— is **superseded by `origin`**. `origin: [schema]` states exactly that, and
states it more precisely (it distinguishes a schema default from a template's
schema default, which a boolean cannot).

**INV-012** — A canonical CIC node MUST NOT carry a `default` member. Value
provenance MUST be expressed through `origin`.

A schema still declares defaults; `default` is a schema-side declaration, not a
node member. The consequence is recorded in `docs/decision-delta.md`.

---

## 5. Origin

### 5.1 What origin is

`origin` classifies **authoring authority**: not merely where a value came
from, but who was entitled to put it there. It answers a question `access`
cannot:

- `origin` — may this node exist / be written at all, and by which authority?
- `access` — given that it may be written, which identity may write it?

These are separate concerns and MUST NOT be conflated.

### 5.2 Grammar

**INV-013** — `origin` MUST match exactly this grammar. No other form is valid.

```
Origin :=
      [ yaml ]
    | [ schema ]
    | [ sealed(template, path) ]
    | [ sealed(template, path), schema ]
```

Concrete YAML encoding:

```yaml
origin: [yaml]

origin: [schema]

origin:
  - sealed:
      template: $network-object
      path: $.access.read

origin:
  - sealed:
      template: $network-object
      path: $.access.read
  - schema
```

Meaning:

| Origin | Meaning |
|---|---|
| `[yaml]` | The instance YAML explicitly supplied this value. |
| `[schema]` | The value materialized from this node's schema default. |
| `[sealed(t,p)]` | The node and its value came from the closed template `t` at path `p`. |
| `[sealed(t,p), schema]` | The template defined and closed the node; the value came from the template node's schema default. |

**INV-014** — `origin` is a classification, not a history. It MUST NOT
accumulate lifecycle events (`transformed`, `migrated`, `normalized`, …).
Audit history belongs to ProofTrace, not to the object model.

**INV-015** — A `sealed` term MUST carry both `template` and `path`. A
`sealed` term missing either MUST be rejected. The template identity alone is
insufficient: one template may be instantiated at many paths, and provenance
that cannot distinguish them is not provenance.

The `template` reference SHOULD be content-addressed (`$name@sha256:…`) so that
origin is reproducible rather than merely descriptive. 0.1 does not require it.

### 5.3 The truth table

Read as: which source facts hold for this node's current value.

| # | sealed | yaml | schema | Result | Origin |
|---|---|---|---|---|---|
| 1 | no | yes | no | **valid** | `[yaml]` |
| 2 | no | no | yes | **valid** | `[schema]` |
| 3 | yes | no | no | **valid** | `[sealed(t,p)]` |
| 4 | yes | no | yes | **valid** | `[sealed(t,p), schema]` |
| 5 | yes | yes | no | **INVALID** | — |
| 6 | yes | yes | yes | **INVALID** | — |
| 7 | no | yes | yes | **INVALID** | — |
| 8 | no | no | no | **INVALID** | — |

**INV-016** — `sealed` and `yaml` MUST NOT both hold (rows 5, 6). `sealed`
means authoring is closed at and below this node; a YAML-sourced value there is
a structurally illegal authoring attempt, not merely a bad value.

**INV-017** — `yaml` and `schema` MUST NOT both hold (row 7). A single
effective value is either explicitly supplied or defaulted; it cannot be both.

**INV-018** — `origin` MUST NOT be empty (row 8). Every materialized node has
an authority; a node with no origin is unattributable and MUST be rejected.

Rows 3 and 4 are why `sealed` combines with `schema` but not with `yaml`:
`sealed` constrains *structural* authority while `schema` describes *value*
source. They are different dimensions. `yaml` is a value source too, which is
why it collides with both.

> Row 8 is not present in the source material this model was derived from; the
> table there enumerated six rows and left the all-negative case undefined.
> INV-018 closes it. Recorded in `docs/decision-delta.md`.

### 5.4 Sealed as an authoring boundary

**INV-019** — Authoring input MUST NOT supply any value at or below a node
whose origin contains `sealed`. Such an attempt MUST be rejected at entry
validation (§8.1) with a structural error, not silently ignored and not
deferred to a later validation stage.

This is a fail-closed property: the traversal stops at the boundary rather than
allowing invalid input to participate in reference resolution or template
expansion first.

### 5.5 `sealed` is an overloaded word — disambiguation

`sealed` already exists in the CIC schema layer with a **different** meaning:
it is one of the three aggregate slot modes (`sealed | defaulted | required`),
governing whether a *derived schema* may override a slot of its base aggregate.

| | Slot mode `sealed` | Origin `sealed(t,p)` |
|---|---|---|
| Plane | schema → schema (type derivation) | schema → instance (authoring) |
| Constrains | a derived type overriding a base slot | instance YAML writing a node |
| Encoding | bare token, as `mode: sealed` | constructor with arity 2 |

**INV-020** — The two MUST NOT be unified. Origin `sealed` MUST always appear
as a constructor carrying `template` and `path` (INV-015); the bare token
`sealed` in an `origin` is invalid. This makes the two syntactically
distinguishable at every occurrence.

---

## 6. Primitives

### 6.1 The set

The primitive set is the eight irreducible atoms:

`shape`, `role`, `behavior`, `contract`, `address`, `identity`, `event`,
`access`.

This specification does **not** change that set.

**INV-021** — A node MUST NOT carry a member that is neither `values`,
`origin`, nor a member of the primitive set. Unknown primitives MUST be
rejected.

**INV-022** — A canonical node MUST carry every primitive its schema declares
for that position, materialized per §8. Primitive semantics MUST NOT be left
undefined for a valid node.

### 6.2 `origin` is not a ninth atom

`origin` is a member of the node envelope, alongside `values` — not a
primitive. Three properties separate it from every atom:

1. **Authorability.** Every atom is declared by a schema author. `origin` is
   never authored (INV-007); it is computed.
2. **Subject.** The atoms describe the *managed object* — its structure, its
   role, its constraints, who may reach it. `origin` describes the *node as an
   artifact of materialization*.
3. **Recursion.** Every atom is itself a CIC node (INV-003). `origin` is
   terminal (INV-004); it is the fixed point that makes the recursion
   well-founded.

Consequently D-003 (the irreducible atom set) is **unchanged** by this model.
See `docs/decision-delta.md`.

### 6.3 Primitives are grouped, not prefixed

A primitive's internal structure MUST be expressed as nested groups, never as
name prefixes.

```yaml
# normative
shape:
  values:
    type: scalar
    scalar_type: integer

# NOT normative — prefix encoding
shape_type: scalar
scalar_type: integer
```

**INV-023** — Within a primitive, named addressable entries MUST be used in
place of ordered anonymous lists wherever the entry has identity. `contract[0]`
is not a stable address; `contract.rules.mtu-range` is.

The reason is not aesthetic. A deterministic addressable path is what allows an
entry to be hashed, diffed, referenced from evidence, and overridden by policy.
An index changes when a neighbour is inserted; a name does not.

### 6.4 `access`

`access` is the one primitive whose structure this document fixes, because it
carries semantics that already exist in the schema layer and must not be lost.

```yaml
access:
  read:
    rules:
      operator:
        subjects: ["OU=operators,O=acme"]
        effect: allow
      auditor:
        subjects: ["OU=auditors,O=acme"]
        effect: allow
    inherit: true
    default_injection: null
  modify:
    rules:
      network-admin:
        subjects: ["OU=network-admins,O=acme"]
        effect: allow
    inherit: true
```

The two operations are named **`read`** and **`modify`**.

**INV-024** — `access` MUST declare operations under the names `read` and
`modify`. `write` is not a valid operation name.

**INV-025** — `inherit` is retained with its established tri-state semantics
and MUST be placed per-operation, at `access.<operation>.inherit`:

| Value | Meaning |
|---|---|
| `true` (default) | Sub-objects inherit this rule for this field. |
| `false` | Not inherited; the sub-object takes its own default rules. |
| `0` | Full reset; the sub-object recomputes from its PolicySurface. |

**INV-026** — `default_injection` is retained and MUST be placed at
`access.read.default_injection`. It declares what a requester without read
permission receives: `null` (default) hides the field entirely; any other value
is injected in its place so that the field's existence does not leak. It is
invalid under `access.modify` — a denied write has no value to inject.

INV-025 and INV-026 relocate two fields that a purely additive reading of the
new structure would have dropped. Both mappings are lossless and are recorded
in `docs/decision-delta.md`.

---

## 7. Object closure — the three rules

The one remaining way out of the model would be to hide an unprocessed object
graph behind a bare `{}`. These three rules close it.

**INV-027** — A structured object known to the schema MUST be recursively
materialized: every schema-known child MUST become a CIC node. It MUST NOT
survive as a raw `map<string, any>`.

**INV-028** — An object the schema explicitly declares **opaque** is a terminal
value. No CIC semantics apply below it; its content MUST be preserved verbatim
and MUST NOT be materialized into nodes.

**INV-029** — An object that is neither schema-known nor explicitly declared
opaque is **invalid** and MUST be rejected.

Opacity MUST be declared, never inferred. An object does not become opaque by
being empty, by being unrecognized, or by being awkward to materialize.

### 7.1 The empty object

`foo: {}` at a structured position does not mean "an arbitrary empty map". It
means the node exists and its children materialize from schema defaults:

```yaml
# schema declares foo.bar default 42, foo.baz default true
# input:
foo: {}

# canonical:
foo:
  values:
    bar:
      values: 42
      origin: [schema]
    baz:
      values: true
      origin: [schema]
  origin: [yaml]
```

`foo`'s origin is `[yaml]` — the author asserted the node's presence. Its
children's origins are `[schema]` — the author supplied no values. If the
schema declares no required children and no defaults, the effective value is
legitimately an empty object, and it is still a valid CIC node with a known
shape — not an unprocessed subtree.

---

## 8. The materialization pipeline

Each stage below is normative. An implementation MAY fuse stages internally but
MUST produce results indistinguishable from performing them in this order — in
particular, a later stage MUST NOT observe input that an earlier stage would
have rejected.

**INV-030** — Materialization MUST be deterministic: the same schema and input
MUST produce a byte-identical canonical object.

### 8.1 Entry validation

- **INPUT:** raw authoring tree
- **OUTPUT:** structurally legal authoring tree
- **MUST:** reject input containing an `origin` member (INV-007); reject
  authoring at or below a sealed boundary (INV-019); reject undeclared
  arbitrary objects (INV-029)
- **MUST NOT:** perform reference resolution, template expansion, or default
  application
- **FAILURE:** reject, before the input can participate in any later stage

Validating only at the end of the pipeline would let invalid input take part in
expansion and resolution first, producing states that are hard to attribute.

### 8.2 External reference resolution

- **INPUT:** structurally legal authoring tree
- **OUTPUT:** tree with no unresolved external references
- **MUST:** fully resolve every reference
- **MUST NOT:** leave a reference for a module to resolve (§9)
- **FAILURE:** unresolvable reference → reject

### 8.3 Sealed / template expansion

- **INPUT:** resolved authoring tree
- **OUTPUT:** tree with no unexpanded template references
- **MUST:** record template identity and source path in the origin of every
  node produced (INV-015)
- **MUST NOT:** permit any authoring value below a sealed boundary (INV-019)
- **FAILURE:** authoring attempt below a sealed subtree → reject

### 8.4 Recursive node construction

- **INPUT:** expanded tree
- **OUTPUT:** every schema-known structured child represented as a CIC node
- **MUST:** apply the discriminator of §4 at every position; apply the closure
  rules of §7
- **MUST NOT:** leave a schema-known child as a raw value (INV-027)
- **FAILURE:** undeclared arbitrary object → reject (INV-029)

### 8.5 Schema value and default materialization

- **INPUT:** node tree with authored values
- **OUTPUT:** node tree with every absent defaultable value filled
- **MUST:** set `origin: [schema]` on every node filled from a default, and
  `[sealed(t,p), schema]` where the default came from a sealed template's schema
- **MUST NOT:** produce a node whose origin holds both `yaml` and `schema`
  (INV-017)
- **FAILURE:** a required value neither authored nor defaultable → reject

### 8.6 Primitive evaluation

- **INPUT:** node tree with values materialized
- **OUTPUT:** node tree with every schema-declared primitive materialized as a
  node
- **MUST:** materialize every declared primitive (INV-022); resolve `inherit`
  chains for `access` (INV-025)
- **MUST NOT:** admit an unknown primitive (INV-021)
- **FAILURE:** unknown primitive, or a primitive whose semantics cannot be
  resolved → reject

### 8.7 Final validation

- **INPUT:** fully materialized node tree
- **OUTPUT:** validated node tree
- **MUST:** enforce every contract; enforce the origin grammar and truth table
  (§5.2, §5.3); confirm INV-001, INV-002 hold at every node
- **FAILURE:** any violation → reject

### 8.8 Canonicalization

- **INPUT:** validated node tree
- **OUTPUT:** canonical CIC object
- **MUST:** produce a deterministic serialization (INV-030); stamp the model
  version (§11)
- **FAILURE:** non-deterministic output → implementation defect

---

## 9. The module boundary contract

**INV-031** — A module MUST NOT receive any of the following:

| # | MUST NOT receive | Because |
|---|---|---|
| a | unresolved references | the module would become a resolver |
| b | authoring short forms | the module would become a normalizer |
| c | templates | the module would become an expander |
| d | sealed source fragments | the module would see a pre-boundary artifact |
| e | unapplied schema defaults | the module would become a default engine |
| f | unknown primitives | the module would define semantics |
| g | unvalidated objects | the module would become the validator |

**INV-032** — The type of a module's input MUST be
`Validated<Canonical<CICObject>>`, and a value of that type MUST be
constructible only by the core materializer. A module API accepting an
unvalidated map (`Execute(map[string]any)`, or equivalent) violates this
specification.

This is a construction-level guarantee, not a convention. "Validate before you
call" is a rule that can be forgotten; "an invalid object has no representation
that crosses the boundary" cannot be. The Go and Rust implementations MUST both
enforce INV-032 through their type systems — an unexported constructor in Go, a
private-field newtype in Rust.

---

## 10. Conformance

An implementation is conformant if and only if it produces, for every vector in
`conformance/`, output matching `expected.yaml` (or the error class in
`expected-error.yaml`) exactly.

Vectors are implementation-independent: YAML in, YAML out. Go, Rust, and any
later implementation run the same corpus.

**Every normative statement in this document is mapped to a vector or is
explicitly marked unvectorizable, in [`docs/spec-vector-map.md`](docs/spec-vector-map.md).**
That mapping is machine-checked by `tools/check_spec_vectors.py`, which fails
if an invariant claims a vector that does not exist or a vector claims an
invariant that does not exist. The check verifies the *mapping*, not
conformance results.

**Status of the corpus as of model 0.1: written, never executed.** No
implementation exists in this repository. `make conformance` fails rather than
passing vacuously when no implementation is present. A vector that has never
run is a hypothesis, not evidence, and this specification does not claim
otherwise.

---

## 11. Versioning

**INV-033** — Every canonical CIC object MUST carry the model version it
conforms to.

```yaml
cic:
  model: "0.1"
```

**INV-034** — A module MUST declare the model version it consumes, and a host
MUST NOT hand a module an object of a version the module has not declared.

Modules do not claim to support a YAML dialect; they consume a numbered object
model. This is the semantic equivalent of an ABI, and it is versioned from the
first day rather than being called `latest` and pinned retroactively.

Within 0.x, any change to a normative statement in this document is a version
increment and MUST arrive in a single change together with its conformance
vectors and both implementations. Keeping the spec, the vectors, and the two
implementations in one repository is deliberate: it makes it physically awkward
to change one implementation's semantics without the other and the corpus
noticing.

---

## 12. Invariant index

| ID | Statement | §|
|---|---|---|
| INV-001 | Exactly one `values` per node | 2.1 |
| INV-002 | Exactly one `origin` per canonical node | 2.1 |
| INV-003 | Every primitive is itself a CIC node | 2.2 |
| INV-004 | `origin` is terminal | 2.3 |
| INV-005 | Primitive materialization terminates; declaration graph acyclic | 2.3 |
| INV-006 | No documentation member on a canonical node | 2.4 |
| INV-007 | Authoring input MUST NOT contain `origin` | 3 |
| INV-008 | Envelope/payload decided by schema position, not keys | 4.3 |
| INV-009 | At structured positions: envelope iff `values` present | 4.3 |
| INV-010 | Schema MUST NOT declare a child named `values` | 4.3 |
| INV-011 | No primitive interpretation below `values` | 4.3 |
| INV-012 | No `default` member on a canonical node | 4.5 |
| INV-013 | Origin grammar — exactly four forms | 5.2 |
| INV-014 | Origin is classification, not history | 5.2 |
| INV-015 | `sealed` MUST carry `template` and `path` | 5.2 |
| INV-016 | `sealed` + `yaml` → invalid | 5.3 |
| INV-017 | `yaml` + `schema` → invalid | 5.3 |
| INV-018 | Empty origin → invalid | 5.3 |
| INV-019 | No authoring at or below a sealed boundary | 5.4 |
| INV-020 | Origin `sealed` always a constructor; distinct from slot mode | 5.5 |
| INV-021 | Unknown primitives rejected | 6.1 |
| INV-022 | Every schema-declared primitive materialized | 6.1 |
| INV-023 | Named addressable entries, not anonymous lists | 6.3 |
| INV-024 | `access` operations are `read` and `modify` | 6.4 |
| INV-025 | `inherit` retained, per-operation, tri-state | 6.4 |
| INV-026 | `default_injection` retained, `access.read` only | 6.4 |
| INV-027 | Structured object → recursively materialized | 7 |
| INV-028 | Explicit opaque → terminal value | 7 |
| INV-029 | Undeclared arbitrary object → invalid | 7 |
| INV-030 | Materialization is deterministic | 8 |
| INV-031 | Seven things a module MUST NOT receive | 9 |
| INV-032 | Module input type constructible only by the materializer | 9 |
| INV-033 | Canonical objects carry the model version | 11 |
| INV-034 | Modules declare the model version they consume | 11 |

---

## 13. Related documents

- [`docs/spec-vector-map.md`](docs/spec-vector-map.md) — every invariant to its
  vectors, or its unvectorizable justification
- [`docs/decision-delta.md`](docs/decision-delta.md) — what this model changes
  in D-003 and D-011, and what would otherwise have been lost silently
- [`docs/migration-surface.md`](docs/migration-surface.md) — the measured file
  list this model would change
- [`docs/branch-decision.md`](docs/branch-decision.md) — why this repository
  was bootstrapped from `base-repo` `wasm/main`
- [`docs/rust-gate-extraction.md`](docs/rust-gate-extraction.md) — the
  line-referenced recipe for `mk/rust.mk`
- [`conformance/README.md`](conformance/README.md) — vector format
