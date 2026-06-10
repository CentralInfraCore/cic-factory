# poc-oci-schema-design-02 — `cic-oci` maradék 4 `DomainComposition`

## Célod

A `poc-oci-schema-design-01` job megtervezte a `cic-oci` séma-struktúráját, és
kidolgozott **egy** `DomainComposition`-t (`OciComputeInstance`) reality
check-ként. Ez a job a **maradék 4 erőforrást** dolgozza ki ugyanabban a
mintában:

```
1. OciCompartment
2. OciVcn
3. OciSubnet
   OciSecurityList   (Subnet-tel párhuzamos, egymástól független)
```

(`OciComputeInstance`-t **ne** dolgozd újra — az kész, lásd alább.)

Ez **séma-implementáció**, nem repo-bootstrap — a `cic-oci` repo létrehozása
továbbra sem ennek a jobnak a feladata.

---

## Kontextus — a `poc-oci-schema-design-01` lezárt döntései

Olvasd el a `cic-factory`-ban (a saját repód, nincs külön klónozás):

```
jobs/poc-oci-schema-design-01/output/cic-oci-repo-bootstrap.md
jobs/poc-oci-schema-design-01/output/cic-oci-schema-plan.md
jobs/poc-oci-schema-design-01/output/oci-compositions/oci-compute-instance.yaml
```

Ezekből lezárt döntések, amiket **nem vitatsz felül**:

- **Branch modell**: `cic-oci` v0.1.0 = main-only, `origin`/`base` remote pár,
  dupla tag séma (`cic-oci@0.1.0` + `oci/@v0.1.0`). Ez a job nem érinti a
  repo-struktúrát, csak séma-fájlokat ír.
- **`schemas/domain/` vs `schemas/examples/`**: az 5 OCI `DomainComposition`
  végső helye `schemas/domain/` (a `cic-compute/schemas/domain/` mintáját
  követve), `schemas/examples/` a `cic-primitives` `kubernetes-pod.yaml`
  referenciájának van fenntartva. Ez a job is `schemas/domain/`-szemantikával
  ír — a kimeneti útvonal lentebb pontosítva.
- **v0.1.0 minimális kör**: `Access` atom és `PolicySurface` aggregate **nem**
  kerül be (OIS v1 = allow-all, nincs domain-szintű policy tartalom).
- A `poc-system-plan` lezárt OCI döntései (Free Tier Ampere A1, git state
  commit `pbs_root_hash` nélkül, Vault mem mode, OIS allow-all,
  drift osztályozás NO_DRIFT/RECONCILIABLE_DRIFT/HARD_DRIFT) érvényesek és nem
  vitathatók felül.

A `cic-oci-schema-plan.md` 4. fejezete (`Az 5 OCI DomainComposition terve`)
tartalmazza mind az 5 erőforrás surface-tábláját (`config_surface`,
`state_surface`, `operation_surface`, `binding_surface`) — ez a kötelező
specifikáció a most elkészítendő 4 fájlhoz. **Ne találj ki új mezőket**, ami
ott nincs megadva — ha hiányzik egy részlet, a `cic-compute/schemas/domain/`
analóg fájljaiból (pl. `cloud-instance.yaml`) vedd a mintát.

---

## Bemenetek — kötelező olvasás (read-only referencia)

Klónozd read-only referenciaként (NE módosítsd, NE pushold):

```bash
git clone git@github.com:CentralInfraCore/cic-primitives.git <workspace>/cic-primitives
git clone git@github.com:CentralInfraCore/cic-compute.git <workspace>/cic-compute
```

Olvasandó fájlok:

```
cic-primitives/schemas/atomic/*.yaml                  — atomic primitívek (Shape, Role,
                                                          Behavior, Contract, Address,
                                                          Identity, Event)
cic-primitives/schemas/aggregate/*.yaml               — ManagedEntity, ConfigSurface,
                                                          StateSurface, OperationSurface

cic-compute/schemas/domain/*.yaml                     — véglegesített DomainComposition
                                                          minták (pl. cloud-instance.yaml,
                                                          virtual-machine.yaml) — operation_
                                                          surface és binding_surface minták
cic-compute/schemas/examples/kubernetes-pod.yaml      — DomainComposition referencia
```

Ha a klónozás nem lehetséges, a `kb_focus`-ban megadott chunk-okat
(`get_chunk`) használd.

---

## Elvárt kimenetek (`output/oci-compositions/`)

4 db kidolgozott `DomainComposition` YAML, az `oci-compute-instance.yaml`
struktúráját követve (`base`, `identity`, `config_surface`, `state_surface`,
`operation_surface` ha releváns, `notification_surface` ha releváns,
`binding_surface`, `derivation_chain` — `yang` + `api` + `runtime`):

### 1. `output/oci-compositions/oci-compartment.yaml`

A séma-terv `OciCompartment` sora alapján:
- `config_surface`: `name`, `description`, `parent_compartment_id`
- `state_surface`: `compartment_id` (OCID), `lifecycle_state`
  (`ACTIVE`/`DELETING`/`DELETED`), `time_created`
- `operation_surface`: **nincs** — Terraform-vezérelt lifecycle (jelezd a
  `derivation_chain.runtime`-ban, hogy ez a séma miért operation_surface
  nélküli — pl. `operation_surface: { operations: [] }` vagy a mezőt el is
  hagyhatod, ha a `cic-primitives` aggregate ezt megengedi — ellenőrizd a
  `managed-entity.yaml` `operation_surface` slot `mode`-ját)
- `binding_surface`: `/cic-oci:compartments/compartment={ocid}`

### 2. `output/oci-compositions/oci-vcn.yaml`

A séma-terv `OciVcn` sora alapján:
- `config_surface`: `cidr_block`, `display_name`, `compartment_id` (ref
  `OciCompartment` binding-re)
- `state_surface`: `vcn_id` (OCID), `lifecycle_state`,
  `default_route_table_id`, `default_security_list_id`
- `operation_surface`: nincs (mint `OciCompartment`)
- `binding_surface`: `/cic-oci:vcns/vcn={ocid}`

### 3. `output/oci-compositions/oci-subnet.yaml`

A séma-terv `OciSubnet` sora alapján:
- `config_surface`: `cidr_block`, `display_name`, `vcn_id` (ref), `availability_domain`,
  `route_table_id`, `security_list_ids[]`
- `state_surface`: `subnet_id` (OCID), `lifecycle_state`, `virtual_router_ip`
- `operation_surface`: nincs
- `binding_surface`: `/cic-oci:subnets/subnet={ocid}`

### 4. `output/oci-compositions/oci-security-list.yaml`

A séma-terv `OciSecurityList` sora alapján:
- `config_surface`: `vcn_id` (ref), `display_name`, `ingress_security_rules[]`
  (protocol, source, port_range), `egress_security_rules[]`
- `state_surface`: `security_list_id` (OCID), `lifecycle_state`,
  `security_rules_hash` (`sha256(canonical_json(ingress+egress rules))`)
- `operation_surface`: **csak `update`** — start/stop/terminate nincs (ez a
  drift demo célpontja: "OCI Security List szabály kézi módosítása")
- `binding_surface`: `/cic-oci:security-lists/security-list={ocid}`

### 5. `output/cross-reference-check.md`

Rövid (max ~1 oldal) ellenőrző jegyzet:
- minden `binding_surface` cím-referencia (pl. `OciSubnet.config_surface.vcn_id`
  → `OciVcn.binding_surface`) konzisztens-e a 4+1 fájl között
- a `OciComputeInstance.state_surface.security_rules_hash` mező és az
  `OciSecurityList.state_surface.security_rules_hash` számítási módja
  ugyanaz-e (mindkettő `sha256(canonical_json(...))`)
- a `cic-primitives/schemas/index.yaml` meta-séma szerint mind az 5 fájl
  (a meglévő `oci-compute-instance.yaml`-t is beleértve) megfelel-e a
  `DomainComposition` ágnak (`base.aggregate` + `base.ref` megadva)
- ha bármelyik pont nem stimmel, jelezd itt — ne javítsd át a meglévő
  `oci-compute-instance.yaml`-t (az másik job kimenete, csak a saját
  4 fájlodra figyelj)

---

## Amit NE csinálj

- Ne dolgozd újra az `OciComputeInstance`-t (`oci-compute-instance.yaml`)
- Ne hozd létre ténylegesen a `cic-oci` repót
- Ne vitasd felül a `poc-oci-schema-design-01` vagy a `poc-system-plan`
  lezárt döntéseit (branch modell, `schemas/domain/` döntés, OCI-specifikus
  döntések)
- Ne találj ki olyan mezőt, ami a `cic-oci-schema-plan.md` 4. fejezetében
  nincs megadva — ha hiányzik valami, kövesd a `cic-compute/schemas/domain/`
  analóg mintáját, és jelezd a `cross-reference-check.md`-ben, ha eltérsz
- Ne hozz létre fájlokat az `output/`-on kívül (kivéve ha sub-job specet
  hozol létre indokolt esetben)

---

## Kontextus a KB-ból

```
kb_status
search_nodes("primitives")
get_chunk("c1861")   — cic-primitives pozíció a rendszerben (réteg-ábra)
get_chunk("c1862")   — schemas/atomic — 7 irreducible atom
get_chunk("c1863")   — schemas/aggregate — kompozíciók
get_chunk("c2934")   — The Primitive Model — Why This Layer Exists
get_chunk("c2936")   — What a Primitive Is
get_chunk("c2941")   — primitive-model.meta.yaml
```
