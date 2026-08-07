# Decision delta — what this model changes, and what it would have lost

This document exists because the expensive failure is not a decision that is
overturned loudly. It is a decision that is *superseded silently* — a field
that stops being mentioned, and is therefore gone without anyone deciding it
should be.

Two decisions are recorded in all six `CIC-objs` repositories and are in scope:
**D-003** (the irreducible atom set) and **D-011** (Access as an atom). This
document states the fate of each, and separately accounts for every field of
D-011 that the object model's source material does not mention at all.

---

## Measurement correction: D-003 already says eight, not seven

The job brief for this work described D-003 as "7 irreducible atoms", sourced
from KB chunk `c4255`.

**That is stale.** The live working tree says eight:

```
primitives-group/{primitives,cic-compute,cic-network,cic-storage,
                  cic-yang,cic-kubernetes}/ai/DECISIONS.md:37

## D-003 — 8 atom mint irreducibilis szint (2026-04-30, bővítve 2026-05-04)

**Döntés:** Shape, Role, Behavior, Contract, Address, Identity, Event, Access
             — ez a 8 atom.
```

D-011 was folded back into D-003 on 2026-05-04, in all six repositories
(verified: line 37 of all six `ai/DECISIONS.md`). The KB snapshot still carries
the pre-amendment text. Anything downstream that reasons from "7 atoms" is
reasoning from the snapshot, not from the repositories.

This matters for the decision below: there is a **precedent** for how an atom
gets added — D-011 established Access, then D-003 was amended to absorb it.
That is the pattern any ninth atom would have to follow.

---

## D-003 — the irreducible atom set

**Verdict: UNCHANGED. No amendment required.**

The question posed was whether `origin` becomes a ninth atom or belongs to a
different category. It is a different category, on three independent grounds
(SPEC §6.2):

| | The eight atoms | `origin` |
|---|---|---|
| Authored by | a schema author, declaratively | nobody — it is computed (INV-007) |
| Describes | the managed object | the node as an artifact of materialization |
| Recursion | is itself a CIC node (INV-003) | is terminal (INV-004) |

The third ground is the decisive one and it is structural, not a matter of
taste. INV-003 says every primitive is a CIC node; a CIC node has an `origin`.
If `origin` were a primitive, it would need an `origin`, which would need an
`origin`. The model would not terminate. `origin` is the fixed point that makes
the recursion well-founded — and a fixed point cannot be a member of the set it
terminates.

So `origin` joins `values` in the **node envelope**. The atom set stays at
eight, and D-003 needs no edit.

The first ground has a practical consequence worth stating: because `origin` is
never authored, it is the only member of a node that cannot lie about itself. A
schema author can declare a misleading `role`; nobody can declare a misleading
`origin`. That property is lost the moment `origin` becomes authorable, which
is why INV-007 is stated as a MUST rather than a convention.

---

## D-011 — Access as an atom

**Verdict: the atom SURVIVES; its internal structure is REPLACED.**

Access remains the eighth irreducible atom, orthogonal to Role, present on
every Shape value. Nothing in this model weakens that. What changes is how it
is written.

### Structural changes

| D-011 | This model | Why |
|---|---|---|
| `value` | `values` | One payload member across the whole model, whatever its arity (SPEC §4.4) |
| `access: [CertPattern]` | `access.read.rules.<name>` | Grouping over prefixing; named entries over anonymous lists (INV-023) |
| `modify: [CertPattern]` | `access.modify.rules.<name>` | as above |
| flat `inherit` | `access.<op>.inherit` | see below |
| flat `default_injection` | `access.read.default_injection` | see below |

The rename `access:`/`modify:` → `access.read`/`access.modify` removes a real
wart in D-011: the atom was called `access` **and** contained a field called
`access` meaning "who may read". The read operation is now named `read`, and
`access` names only the primitive.

### Why named rules rather than a list

D-011's `access: [CertPattern]` is an ordered anonymous list, so a rule's
address is `access[0]`. That address is not stable: inserting a rule renumbers
its neighbours. In a system whose premise is that evidence references state,
an address that silently changes meaning is a defect. `access.read.rules.operator`
does not move.

### `read` / `modify`, not `read` / `write`

The source material used `modify` and `write` interchangeably. `modify` is
normative (INV-024), for continuity with D-011 and with the live
`schemas/atomic/access.yaml`, which uses `modify`.

---

## The two fields the source material never mentions

D-011 defines five fields. The research material behind this object model
discusses `value`, `access` and `modify`. It says **nothing whatsoever** about
`inherit` or `default_injection`.

Silence is not a decision. Both are accounted for here.

### `inherit` — RETAINED

**Disposition: retained, relocated, semantics unchanged, strictly more
expressive.**

```
D-011:       inherit: true | false | 0        (one field, governs the whole node)
This model:  access.<operation>.inherit       (per operation)
```

Tri-state semantics are carried over verbatim:

| Value | Meaning |
|---|---|
| `true` (default) | sub-objects inherit this rule for this field |
| `false` | not inherited; the sub-object takes its own default rules |
| `0` | full reset; the sub-object recomputes from its PolicySurface |

Migration is lossless and mechanical: a flat `inherit: X` becomes
`access.read.inherit: X` **and** `access.modify.inherit: X`.

The relocation is a genuine gain, not churn. D-011's single field forces read
and modify to inherit identically. Per-operation inheritance expresses the case
that motivated the Access atom in the first place — `role: state` fields where
an adapter writes and users read. There, modify rules are adapter-specific and
should not propagate to sub-objects, while read rules should. The flat form
cannot say that.

Covered by `conformance/materialization/013_access_inherit_injection`
(INV-025), which exercises the default `true` and an explicit `0`.

### `default_injection` — RETAINED

**Disposition: retained, relocated to `access.read` only.**

Semantics carried over verbatim: what a requester without permission receives.
`null` (the default) hides the field entirely; any other value is injected so
that the field's existence does not leak.

The relocation narrows it from the node to the read operation, because that is
where it was always meaningful. D-011 places it flat, alongside both `access`
and `modify`, but its definition — "what the requester gets if they have no
access rights to the value" — is about reading. A denied write has no value to
inject; the write simply does not happen. Under this model
`access.modify.default_injection` is invalid (INV-026) rather than merely
meaningless.

Migration is lossless: flat `default_injection: X` becomes
`access.read.default_injection: X`.

Covered by `conformance/materialization/013_access_inherit_injection`
(INV-026).

### PolicySurface

D-011 makes PolicySurface the source of inherited defaults when
`inherit: true`. That relationship is **unchanged** and out of scope here.
PolicySurface remains an aggregate; this model specifies where the `inherit`
flag lives, not what it inherits from. `cic-compute`'s live
`schemas/domain/compute-resource.yaml` (branch `main`) already carries a
`policy_surface:` block with `inherit_policy: true`, and this model does not
disturb it.

---

## Conflicts with the live `access.yaml`

Where this specification and the live `schemas/atomic/access.yaml` disagree,
the specification wins. The disagreements, named:

| # | Live `access.yaml` | This model | Note |
|---|---|---|---|
| 1 | `value:` | `values:` | Rename |
| 2 | `access:` = who may read | `access.read` | The atom no longer contains a field of its own name |
| 3 | `access`/`modify` are `list<CertPattern>` | `rules` map, named entries | INV-023 |
| 4 | `inherit` at node level | `access.<op>.inherit` | Lossless, more expressive |
| 5 | `default_injection` at node level | `access.read.default_injection` | Invalid under modify |
| 6 | short form `key: value` normalized "by the compiler" | discriminator is schema-positional, INV-008 | The live file states the short/long equivalence but not how they are told apart; SPEC §4 supplies the missing rule |

Item 6 is the substantive one. `access.yaml` has carried the short-form/
long-form equivalence since `v0.0.dev` — the central idea of this model is not
new. What has never been written down is the *discriminator*: which of the two
a given mapping is. That gap is what SPEC §4 closes, and it is why a purely
syntactic rule was rejected (SPEC §4.2).

---

## Derived decisions not traceable to D-003 or D-011

These are new normative positions this specification takes. They are listed
here so that a reviewer can challenge them individually rather than having them
arrive bundled inside a larger document.

| # | Decision | Rationale | Vector |
|---|---|---|---|
| A | `origin` is envelope, not the ninth atom | SPEC §6.2; termination argument | `validation/003_origin_not_terminal` |
| B | The discriminator is schema-positional, not syntactic | A `values`+`default` rule is unsound both ways (SPEC §4.2) | `materialization/011`, `012`, `invalid/004` |
| C | `default` is superseded by `origin` | `origin: [schema]` says the same thing and distinguishes a template's schema default, which a boolean cannot | `validation/005_default_member` |
| D | `values` reserved at schema-declaration time only | Makes the discriminator total without a global keyword reservation | `invalid/004_schema_declares_values_child` |
| E | Empty origin is invalid | The source truth table enumerated six rows and left the all-negative case undefined | `validation/002_origin_empty` |
| F | Origin `sealed` is always a 2-arity constructor | Disambiguates it from the existing slot mode — see below | `invalid/007_sealed_missing_path` |
| G | `descr` is not a node member | Documentation belongs to the schema; on the node it would make two objects with equal values differ | `validation/004_documentation_member` |
| H | Primitive declaration graph must be acyclic | Without it the model does not terminate and is not implementable | `invalid/008_cyclic_primitive_declaration` |

### Decision F in detail — `sealed` is an overloaded word

This is the most likely source of downstream confusion, and it was nearly
missed: a first pass over the repositories suggested `sealed` appeared only
once, in prose in `identity.yaml`. It is in fact a **live enum value**, in all
six repositories:

```
<repo>/schemas/index.yaml:98            enum: [sealed, defaulted, required]
<repo>/schemas/aggregate/config-surface.yaml:30      mode: sealed
<repo>/schemas/aggregate/state-surface.yaml:30       mode: sealed
<repo>/schemas/aggregate/operation-surface.yaml:52   mode: sealed
<repo>/schemas/aggregate/managed-entity.yaml:116     mode: sealed
```

enforced by the compiler (`sealed slot 'lifecycle_surface' must not be
overridden`) and covered by a negative example
(`schemas/examples/invalid/domain-sealed-override.yaml`).

That `sealed` is **D-005's aggregate slot mode**, and it means something else:

| | Slot mode `sealed` (D-005) | Origin `sealed(t,p)` (this model) |
|---|---|---|
| Plane | schema → schema | schema → instance |
| Constrains | a derived type overriding a base slot | instance YAML authoring a node |
| Answers | may this type change this slot? | may this YAML write here? |

They are cousins — both express "closed to modification" — but they close
different things against different actors, and unifying them would be a
category error. INV-020 keeps them apart syntactically: the slot mode is always
the bare token `mode: sealed`, and the origin term is always a constructor
carrying `template` and `path`. A bare `sealed` in an `origin` is invalid.

---

## What a reviewer should push back on

Stated plainly, because a delta document that only defends itself is not worth
reading:

1. **Decision C removes a field that six repositories do not currently have,
   but that D-011's short-form/long-form text implies.** If `default` is being
   used anywhere as a runtime marker rather than a schema declaration, C breaks
   it. Not measured — no `default:` usage audit was performed at instance level,
   only at schema level.
2. **INV-025's per-operation `inherit` is a semantic extension, not merely a
   relocation.** It is lossless in the migration direction, but it creates
   states the old model could not represent, and PolicySurface resolution will
   have to define what per-operation inheritance means when the two operations
   disagree. This specification does not define that; it is deferred with
   PolicySurface.
3. **Nothing here has been executed.** Every claim about behaviour in this
   document is a claim about what the specification *says*, not about what any
   implementation *does*, because there is no implementation.
