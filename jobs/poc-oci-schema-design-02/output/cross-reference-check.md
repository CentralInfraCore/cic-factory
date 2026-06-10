# Cross-reference check — `cic-oci` 5 `DomainComposition`

> Az 5 fájl: `oci-compartment.yaml`, `oci-vcn.yaml`, `oci-subnet.yaml`,
> `oci-security-list.yaml` (ez a job) + `oci-compute-instance.yaml`
> (poc-oci-schema-design-01, nem módosítva).

---

## 1. `binding_surface` cím-referenciák konzisztenciája

| Forrás mező | Hivatkozott `binding_surface` | Konzisztens? |
|---|---|---|
| `OciVcn.config_surface.compartment_id` (pattern `^ocid1\.compartment\.`) | `OciCompartment.binding_surface` → `/cic-oci:compartments/compartment={ocid}` (logical_id `cic:oci:compartments:{ocid}`, OCID-prefix `ocid1.compartment.`) | ✅ |
| `OciSubnet.config_surface.vcn_id` (pattern `^ocid1\.vcn\.`) | `OciVcn.binding_surface` → `/cic-oci:vcns/vcn={ocid}` (OCID-prefix `ocid1.vcn.`) | ✅ |
| `OciSecurityList.config_surface.vcn_id` (pattern `^ocid1\.vcn\.`) | `OciVcn.binding_surface` → ua. | ✅ |
| `OciSubnet.config_surface.security_list_ids[]` (pattern `^ocid1\.securitylist\.`) | `OciSecurityList.binding_surface` → `/cic-oci:security-lists/security-list={ocid}` (OCID-prefix `ocid1.securitylist.`) | ✅ |
| `OciComputeInstance.config_surface.subnet_id` (pattern `^ocid1\.subnet\.`) | `OciSubnet.binding_surface` → `/cic-oci:subnets/subnet={ocid}` (OCID-prefix `ocid1.subnet.`) | ✅ |
| `OciComputeInstance.state_surface.vcn_id` | `OciVcn.binding_surface` (state-szintű referencia, nincs config_surface contract — ua. mintát követi, mint a többi `*_id` mező) | ✅ |

A `binding_surface.addresses[].schema_path` minden fájlban a
`/cic-oci:<plural>/<singular>={ocid}` mintát követi, a `logical_id` pedig
`cic:oci:<plural>:{ocid}` — mind az 5 fájlban azonos konvenció
(`oci-compute-instance.yaml`: `/cic-oci:instances/instance={ocid}`,
`cic:oci:instances:{ocid}` — ugyanez a séma).

**Eredmény: nincs eltérés.**

---

## 2. `security_rules_hash` számítási mód egyezősége

- `OciComputeInstance.state_surface.security_rules_hash` (poc-oci-schema-design-01,
  192–200. sor): leírás szerint
  `sha256(canonical_json(OciSecurityList.config_surface ingress+egress rules))`,
  formátum `^sha256:[a-f0-9]{64}$`.
- `OciSecurityList.state_surface.security_rules_hash` (ez a job): leírás szerint
  `sha256(canonical_json(ingress_security_rules + egress_security_rules))`
  — a **ténylegesen az OCI API-n érvényes** szabályokból számítva,
  ugyanazzal a `^sha256:[a-f0-9]{64}$` formátummal.

A két mező **ugyanazt a hash-számítási módot** (sha256 + canonical_json az
ingress+egress szabályok felett) és **ugyanazt a formátum-contractot**
használja. A különbség csak a forrás:

- `OciComputeInstance.state_surface.security_rules_hash` — a *kívánt*
  (config_surface-ből vett) szabálykészlet hash-e, amit az
  `OciComputeInstance` reconcile loop-ja drift-összevetéshez számol.
- `OciSecurityList.state_surface.security_rules_hash` — a *ténylegesen
  megfigyelt* (OCI API válaszból vett) szabálykészlet hash-e.

Ez szándékos és konzisztens: a drift detekció pontosan ennek a két hash-nek
az összevetése (`OciSecurityList.runtime.reconcile_loop` 3. lépés).

**Eredmény: nincs eltérés — a két mező kompatibilis hash-számítást használ.**

---

## 3. `cic-primitives/schemas/index.yaml` meta-séma — `DomainComposition` ág

A meta-séma `DomainComposition` esetén `spec.base.aggregate` mezőt követeli
meg (`required: [base]`, `base.aggregate` kötelező string).

| Fájl | `spec.kind` | `spec.base.aggregate` | `spec.base.ref` |
|---|---|---|---|
| `oci-compartment.yaml` | `DomainComposition` | `ManagedEntity` | `schemas/aggregate/managed-entity.yaml` |
| `oci-vcn.yaml` | `DomainComposition` | `ManagedEntity` | `schemas/aggregate/managed-entity.yaml` |
| `oci-subnet.yaml` | `DomainComposition` | `ManagedEntity` | `schemas/aggregate/managed-entity.yaml` |
| `oci-security-list.yaml` | `DomainComposition` | `ManagedEntity` | `schemas/aggregate/managed-entity.yaml` |
| `oci-compute-instance.yaml` (poc-oci-schema-design-01, ellenőrizve, nem módosítva) | `DomainComposition` | `ManagedEntity` | `schemas/aggregate/managed-entity.yaml` |

Mind az 5 fájl `metadata` blokkja tartalmazza a kötelező mezőket
(`name`, `version`, `description`, `owner`, `tags`, `validatedBy`) — a
`cic-oci-compute-instance.yaml` mintáját követve.

**Eredmény: mind az 5 fájl megfelel a `DomainComposition` ágnak.**

---

## 4. Eltérések / megjegyzések a `cic-oci-schema-plan.md` 4. fejezetéhez képest

- `OciCompartment`, `OciVcn`, `OciSubnet`: `operation_surface: { operations: [] }`
  — a `managed-entity.yaml` `operation_surface` slot `mode: defaulted,
  default: empty` definíciójának explicit, üres megfelelője. Ez a forma
  szerepelt az `input.md`-ben is javasolt opcióként.
- `OciSubnet.config_surface.security_list_ids[]`: a séma-tervben `[]` jelölés
  szerepelt típus megadása nélkül — `shape_type: collection,
  collection_variant: set, scalar_type: string` formában lett kidolgozva
  (YANG `leaf-list`), mivel kulcs nélküli OCID-lista, a `cic-primitives/schemas/atomic/shape.yaml`
  `collection.set` definíciója szerint.
- `OciSecurityList.config_surface.ingress_security_rules[]` /
  `egress_security_rules[]`: a `port_range` mező `shape_type: composite`
  (`min`/`max` integer fields) — a `kubernetes-pod.yaml` `resources.requests`/`limits`
  composite mintáját követve, mivel a séma-terv csak "port_range"-t említ
  típus nélkül.
- `notification_surface`: egyik új fájlban sincs (`OciCompartment`, `OciVcn`,
  `OciSubnet`, `OciSecurityList`) — a séma-terv 4. fejezete egyik fennmaradó
  erőforráshoz sem ír elő notification eseményt (csak az
  `OciComputeInstance`-hez, `lifecycle-state-changed`). A `managed-entity.yaml`
  `notification_surface` slot `mode: defaulted, default: empty` — a mező
  elhagyása ezzel konzisztens.

Az `oci-compute-instance.yaml` fájl **nem lett módosítva**.
