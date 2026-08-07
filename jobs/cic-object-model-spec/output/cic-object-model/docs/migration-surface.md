# Migration surface — measured, not estimated

Every file below was counted on disk on 2026-08-07. Where a claim is a
category rather than a file, it says so.

**Measurement roots**

| What | Path |
|---|---|
| The six repositories (live working trees) | `/home/sinkog/sync/git.partners/CentralInfraCore/primitives-group/` |
| OCI compositions (not yet materialized) | `<cic-factory>/jobs/poc-oci-schema-design-0{1,2}/output/oci-compositions/` |

Note on naming: on disk the `cic-primitives` repository is checked out as
`primitives-group/primitives/` (remote `CentralInfraCore/cic-primitives.git`).
The other five use their repository names.

---

## 0. Three corrections to the assumed starting picture

These change the size and the character of the work, so they come first.

### 0.1 The divergence is language, not semantics — and it is total

The premise for this work was that `schemas/atomic/access.yaml` exists in two
different contents across the six repositories while `shape.yaml` is still
uniform, and that migration is therefore non-mechanical where they differ.

Measured, both halves of that are wrong:

- **All 17 schema files diverge**, not one. Every file under `schemas/`
  except `index.yaml` has exactly two variants.
- **The split is 1-vs-5, and it is prose language only.** `primitives/` has
  been translated to English; the five domain copies still carry the original
  Hungarian. `index.yaml` is byte-identical across all six.

Structural comparison — parsing each file and comparing the full set of YAML
key paths — reports **0 files with differing key structure across all 6
repositories** (18 files compared, multi-document safe).

So migration **is** mechanical. What is not yet decided is the language axis:
whether the single normative source is English (following `primitives/`) or
whether the Hungarian text is retained anywhere. That is a decision, not a
merge conflict.

### 0.2 `cloud-instance.yaml` no longer exists

The domain composition cited as the live example of the encoding this model
replaces was deleted. History:

```
ef68978 feat: unified ComputeResource schema, deprecate platform-specific types
146a9b3 chore: remove deprecated platform-specific compute schemas
```

`schemas/domain/{cloud-instance,physical-machine,virtual-machine}.yaml` survive
only on the stale `origin/main`. The live domain composition is
`schemas/domain/compute-resource.yaml` on local `main`.

### 0.3 Domain compositions exist in one repository only, and not on `devel`

| Repo | `main` | `origin/main` | `devel` (checked out) |
|---|---|---|---|
| cic-compute | `compute-resource.yaml` | 3 deprecated files | **none** |
| primitives, cic-network, cic-storage, cic-yang, cic-kubernetes | none | none | none |

All six working trees are on `devel`, where no `schemas/domain/` directory
exists at all. A migration script run against the checked-out trees would
silently touch zero domain compositions. **The domain work is on `main`.**

---

## 1. Atomic primitives — 48 files (8 × 6)

```
{primitives,cic-compute,cic-network,cic-storage,cic-yang,cic-kubernetes}/schemas/atomic/
    access.yaml       ← REPLACED (structure)
    shape.yaml        ← amended (see 1.2)
    role.yaml         ← unchanged
    contract.yaml     ← amended (see 1.3)
    identity.yaml     ← unchanged (see 1.4)
    address.yaml      ← unchanged
    behavior.yaml     ← unchanged
    event.yaml        ← unchanged
```

### 1.1 `access.yaml` — replaced, 6 copies

The only file whose content this model rewrites rather than adjusts. Changes
per `decision-delta.md`: `value` → `values`; `access`/`modify` flat CertPattern
lists → `access.read.rules.<name>` / `access.modify.rules.<name>`; `inherit`
relocated per-operation; `default_injection` relocated to `access.read`.

Affected lines in each copy: `value:` ×1, `inherit` ×11, `default_injection`
×6.

### 1.2 `shape.yaml` — amended, 6 copies

`spec.fields.properties.default` (lines 59–61) declares a per-field default. It
stays — a schema still declares defaults. What changes is that the *node* no
longer carries a `default` member (INV-012); `origin: [schema]` records that a
value came from one. The file needs a note distinguishing the schema-side
declaration from the (now removed) node-side marker, or the two will be
conflated during implementation.

### 1.3 `contract.yaml` — amended, 6 copies

Contracts are currently expressed as anonymous ordered lists in the
compositions that consume this file (`contract: [- type: pattern, ...]`). INV-023
requires named addressable entries. The atom's own definition must state the
`rules.<name>` shape.

### 1.4 `identity.yaml` — unchanged

Flagged only to close a false lead. `identity.yaml` mentions `inherit` 8 times
and `sealed` once, and neither is related to this model:

- its `inheritance_rules` (line 69) govern **type derivation** — how a derived
  type inherits its base's aggregate surfaces — not Access's `inherit` field;
- its line 74 mention of `sealed` is prose describing slot narrowing, i.e.
  D-005's slot mode, not origin's authoring boundary.

No change. See `decision-delta.md` Decision F.

---

## 2. Aggregate compositions — 30 files (5 × 6)

```
{...six repos...}/schemas/aggregate/
    config-surface.yaml       line 30  mode: sealed
    state-surface.yaml        line 30  mode: sealed
    operation-surface.yaml    line 52  mode: sealed
    managed-entity.yaml       line 116 mode: sealed
    policy-surface.yaml       — (no sealed slot)
```

**No structural change required.** `mode: sealed` is D-005's slot mode and this
model does not touch it (INV-020). These 30 files appear in the surface only
because they are the reason the disambiguation must be written down: after this
model lands, `sealed` denotes two different things in the same repository, and
whoever reads `mode: sealed` next must not reach for the origin semantics.

**Action: documentation only.** Each of the four files carrying a sealed slot
should gain a one-line comment pointing at SPEC §5.5.

---

## 3. Meta-schema — 6 files

```
{...six repos...}/schemas/index.yaml
    line 98   enum: [sealed, defaulted, required]
```

Byte-identical across all six (the only such file). The enum stays; the
meta-schema must additionally learn:

- the node envelope (`values` + `origin`) and the origin grammar (INV-013);
- the constraint that a schema must not declare a child named `values`
  (INV-010) — this is a meta-schema-level check, and is exactly what
  `conformance/invalid/004_schema_declares_values_child` exercises.

---

## 4. Example schemas — 24 files (4 × 6)

```
{...six repos...}/schemas/examples/
    kubernetes-pod.yaml
    invalid/aggregate-invalid-slot-mode.yaml
    invalid/domain-sealed-override.yaml
    invalid/missing-required-metadata.yaml
```

`kubernetes-pod.yaml` uses the composition encoding of §5 and must be
re-encoded. The three `invalid/` examples are negative fixtures for D-005 slot
modes and remain valid as they are — but they are the natural place to add
negative fixtures for the new invariants, so that the repositories' own example
corpus and `conformance/` do not drift apart.

---

## 5. Domain compositions — 1 live file

```
cic-compute (branch main):  schemas/domain/compute-resource.yaml
```

107 lines match the encoding this model replaces:

```yaml
- name: cpu_cores
  atomic_ref: schemas/atomic/shape.yaml
  shape_type: scalar          # prefix, not group          → shape.values.type
  scalar_type: integer        # second prefix, same concept → shape.values.scalar_type
  role: config                # flat                        → role.values
  contract:
    - type: range             # anonymous list: this is contract[0]
      expression: "1..256"    #                             → contract.rules.<name>
```

This is the single richest example of the target transformation and should be
migrated first, as the reference conversion.

On the stale `origin/main`, three further files carry the same encoding
(`cloud-instance.yaml`, `physical-machine.yaml`, `virtual-machine.yaml`). They
are deleted upstream; they are listed only so that a migration run against
`origin/main` is not mistaken for a run against current state.

---

## 6. OCI compositions — 5 files, not yet materialized

In the cic-factory repository, not in `CIC-objs`:

| File | `shape_type` | `scalar_type` | anonymous contract entries | `atomic_ref` |
|---|---|---|---|---|
| `jobs/poc-oci-schema-design-01/output/oci-compositions/oci-compute-instance.yaml` | 23 | 23 | 7 | 22 |
| `jobs/poc-oci-schema-design-02/output/oci-compositions/oci-compartment.yaml` | 6 | 6 | 4 | 8 |
| `jobs/poc-oci-schema-design-02/output/oci-compositions/oci-security-list.yaml` | 20 | 14 | 12 | 10 |
| `jobs/poc-oci-schema-design-02/output/oci-compositions/oci-subnet.yaml` | 9 | 9 | 5 | 11 |
| `jobs/poc-oci-schema-design-02/output/oci-compositions/oci-vcn.yaml` | 7 | 7 | 4 | 9 |
| **total** | **65** | **59** | **32** | **60** |

These are the cheapest files to migrate and the most valuable to migrate early:
they have never been materialized into any repository, so converting them costs
no coordination, and they will otherwise be written into `CIC-objs` in the old
encoding and have to be converted twice.

---

## 7. Totals

| Group | Files | Disposition |
|---|---|---|
| Atomic primitives | 48 | 6 replaced (`access`), 12 amended (`shape`, `contract`), 30 unchanged |
| Aggregate compositions | 30 | documentation only |
| Meta-schema `index.yaml` | 6 | extended |
| Example schemas | 24 | 6 re-encoded, 18 unchanged + additions |
| Domain compositions (live) | 1 | re-encoded — reference conversion |
| OCI compositions | 5 | re-encoded before materialization |
| **Total in scope** | **114** | of which **~30** need real content work |

The 114 is dominated by six-fold duplication. The actual intellectual work is
one `access.yaml`, one `contract.yaml`, one `index.yaml`, one
`compute-resource.yaml`, one `kubernetes-pod.yaml`, and five OCI compositions —
then a fan-out.

---

## 8. What is not measured here

Stated so it is not mistaken for zero:

- **Consumers of these schemas.** `compiler.py` in each repository validates
  against `index.yaml` and enforces the slot modes; it was not read. Any change
  to the meta-schema (§3) lands on it.
- **Instance-level `default:` usage.** `decision-delta.md` Decision C removes
  the node-side `default` member. Only schema-side declarations were counted;
  no instance corpus was audited, because none was located.
- **The release artifacts.** `primitives/release/cic-primitives-v0.1.{4,5}.yaml`
  contain `sealed`; they are signed, published artifacts and migrating them is
  a re-release question, not an edit.
- **Whether any of this compiles.** Nothing in this document was executed. The
  file counts are verified; the dispositions are proposals.
