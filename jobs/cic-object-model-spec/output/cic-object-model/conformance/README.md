# Conformance vectors

These vectors are the falsifiable part of [`SPEC.md`](../SPEC.md). A normative
sentence with no vector behind it is an assertion; a vector is a test that can
fail.

**Status: written, never executed.** No implementation exists in this
repository yet. Nothing here has passed — it has been authored. See
[`../docs/spec-vector-map.md`](../docs/spec-vector-map.md) for the full
invariant coverage picture.

## Format

Vectors are implementation-independent: YAML in, YAML out. Go, Rust, and any
later implementation run the same corpus with no per-language fixtures.

```
conformance/
  materialization/<id>_<name>/    authoring input -> canonical object
    meta.yaml         id, invariants covered, description
    schema.yaml       the CIC schema
    input.yaml        authoring-plane input
    expected.yaml     the canonical object that MUST be produced

  invalid/<id>_<name>/            authoring input that MUST be rejected
    meta.yaml
    schema.yaml
    input.yaml
    expected-error.yaml   error code, invariant, path, pipeline stage

  validation/<id>_<name>/         canonical object -> accept / reject
    meta.yaml
    object.yaml           a canonical object presented for final validation
    expected-error.yaml   (reject cases)
```

### Why `validation/` exists

Truth-table rows 7 (`yaml` + `schema`) and 8 (empty origin) cannot be produced
by any authoring input: `origin` may not appear in authoring input at all
(INV-007). They are reachable only as defects in an already-materialized
object — a materializer bug, or a hand-forged object presented at the module
boundary. `validation/` exercises §8.7 final validation directly, taking a
canonical object as input rather than authoring YAML. Without it, two rows of
the origin truth table would be unfalsifiable.

## Schema language used by the vectors

Deliberately minimal — just enough to exercise the model:

```yaml
model: "0.1"
root:
  shape: object
  children:
    <name>:
      shape: scalar | list | object | opaque
      scalar_type: string | integer | number | boolean | bytes
      role: config | state | operational
      default: <value>            # makes the position defaultable
      required: true              # no default, must be authored
      children: {...}             # for shape: object
      item: {...}                 # for shape: list
      sealed_from:                # closes authoring at and below this node
        template: $<name>
        path: $.<path>
      access: {...}               # an access primitive declaration

templates:
  $<template-name>:
    $.<path>:
      shape: object
      children: {...}             # the template's own schema, incl. defaults
      content: {...}              # OPTIONAL explicit template values
```

`content` is what separates truth-table rows 3 and 4, and it is the only
difference between vectors `003_origin_sealed` and `004_origin_sealed_schema`:

- template supplies `content` → the value came from the template itself →
  `origin: [sealed(t,p)]`
- template supplies no `content`, the value comes from the template's own
  schema default → `origin: [sealed(t,p), schema]`

That distinction is the case simpler provenance models cannot express, and it
is the reason `origin` is a list rather than an enum.

## Canonical output shape

Every node carries `values` and `origin`, plus every primitive its schema
declares. `shape` is always declared (a position must be typed), so it appears
on every node. This is verbose by design — it is the model.

```yaml
cic:
  model: "0.1"
values:
  mtu:
    values: 9000
    origin: [yaml]
    shape:
      values: {type: scalar, scalar_type: integer}
      origin: [schema]
origin: [yaml]
```

## Error codes

| Code | Invariant | Raised at |
|---|---|---|
| `E_ORIGIN_DECLARED_IN_INPUT` | INV-007 | entry validation |
| `E_AUTHORING_BELOW_SEALED` | INV-019, INV-016 | entry validation |
| `E_UNDECLARED_OBJECT` | INV-029 | entry validation |
| `E_SCHEMA_RESERVED_CHILD_VALUES` | INV-010 | schema load |
| `E_SEALED_MISSING_TEMPLATE_OR_PATH` | INV-015 | schema load |
| `E_UNKNOWN_PRIMITIVE` | INV-021 | primitive evaluation |
| `E_ORIGIN_YAML_SCHEMA_CONFLICT` | INV-017 | final validation |
| `E_ORIGIN_EMPTY` | INV-018 | final validation |

An implementation MUST raise the stated code at the stated stage. Rejecting
with the right code at the wrong stage is a failure: stage order is normative
(§8), because a later stage must never observe input an earlier stage would
have rejected.
