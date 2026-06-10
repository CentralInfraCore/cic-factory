# poc-oci-schema-design-01 — `cic-oci` séma- és repo-terv

## Célod

Készíts **tervet** (nem implementációt) arról, hogyan épüljön fel a `cic-oci` domain repo —
a `poc-system-plan` által kijelölt OCI domain adapter repo (`cic-proxmox` helyett).

Ez **tervezés, nem séma-implementáció**. A kimenet egy repo-bootstrap terv, egy séma-struktúra
terv, és **egyetlen** kidolgozott `DomainComposition` minta-fájl (reality check), ami igazolja,
hogy a minta működik OCI-ra. A teljes 5 erőforrás sémáját egy következő job (`poc-oci-schema-design-02`
vagy hasonló) implementálja, ha ez a terv jóváhagyásra kerül.

---

## Kontextus — amit a primitívek rétegéről tudni kell

A CIC séma-ökoszisztéma rétegei:

```
base-repo (közös template: tooling, signing, CLAUDE.md)
  └─ base remote of cic-primitives
       └─ cic-primitives (7+1 atomic primitive + aggregate kompozíciók)
            └─ base remote of {cic-compute, cic-network, cic-storage, cic-kubernetes, cic-yang, ... cic-oci}
```

Minden domain repo (`cic-compute`, `cic-network`, ...) ugyanazt a struktúrát követi:

```
schemas/
  atomic/      ← cic-primitives atomic primitívek átvétele (Shape, Role, Behavior,
                 Contract, Address, Identity, Event, Access)
  aggregate/   ← cic-primitives aggregate kompozíciók átvétele (ManagedEntity,
                 ConfigSurface, StateSurface, OperationSurface, NotificationSurface,
                 BindingSurface, PolicySurface)
  examples/    ← DomainComposition objektumok — a domain konkrét erőforrásai
```

Egy `DomainComposition` (lásd `cic-compute/schemas/examples/kubernetes-pod.yaml`):
- `base.aggregate: ManagedEntity` + `base.ref`
- `identity` — kind, namespace, version
- `config_surface` — mit ír be a felhasználó/Terraform (Shape mezők, Role: config)
- `state_surface` — mit ad vissza a rendszer ténylegesen (Role: state|operational|derived|volatile)
- `operation_surface` — végrehajtható műveletek (Behavior: action|operation)
- `notification_surface` — események (Event)
- `binding_surface` — cím/endpoint (Address)
- `derivation_chain` — **ez a "semantic mapping kontraktus"**: `yang` (modul váz) +
  `restconf`/`api` (végpontok) + `runtime` (reconcile loop, adapter contract)

### Branch/tag konvenció (megfigyelt minta a primitives-group-ban)

| Elem | Minta | `cic-oci`-ra alkalmazva |
|---|---|---|
| `origin` remote | `cic-<domain>` | `git@github.com:CentralInfraCore/cic-oci.git` |
| `base` remote | `cic-primitives` | `git@github.com:CentralInfraCore/cic-primitives.git` |
| `devel` ág | `base/devel`-t követi | ugyanúgy |
| `<domain>/main`, `<domain>/devel` | opcionális (network, yang használja) | ajánlott bevezetni |
| `<domain>/releases/vX.Y.Z` | kötelező, hosszú életű branch | `oci/releases/v0.1.0` |
| Tag-ek | dupla séma: `cic-<domain>@X.Y.Z` + `<domain>/@vX.Y.Z` | `cic-oci@0.1.0` + `oci/@v0.1.0` |
| Örökölt tag-ek | `primitives/@v0.1.x`, `base@0.5.0`, `schemas@v0.9.0` (a `base` merge-ekből) | ugyanígy várható |

---

## Bemenetek — kötelező olvasás (read-only referencia)

A `cic-factory` workspace mellett **klónozd read-only referenciaként** (NE módosítsd, NE pushold):

```bash
git clone git@github.com:CentralInfraCore/cic-primitives.git <workspace>/cic-primitives
git clone git@github.com:CentralInfraCore/cic-compute.git <workspace>/cic-compute
```

Olvasandó fájlok:

```
cic-primitives/schemas/index.yaml                          — meta-séma (AtomicPrimitive /
                                                               AggregatePrimitive / DomainComposition)
cic-primitives/schemas/atomic/*.yaml                        — 8 atomic primitive
cic-primitives/schemas/aggregate/*.yaml                     — aggregate kompozíciók

cic-compute/schemas/atomic/*.yaml                           — átvett atomic primitívek (minta)
cic-compute/schemas/aggregate/*.yaml                        — átvett aggregate-ek (minta)
cic-compute/schemas/examples/kubernetes-pod.yaml            — DomainComposition referencia minta
                                                               (derivation_chain blokkal)
```

Olvasd el a `cic-factory`-ban:

```
jobs/poc-system-plan/input.md                               — OCI lezárt döntések, actual_state.json
                                                               mezők (instance_id, lifecycle_state,
                                                               shape, ocpus, memory_gb, public_ip,
                                                               private_ip, vcn_id, security_rules_hash,
                                                               collected_at)
jobs/poc-implementation-plan/output/sub-jobs-overview.md    — domain job-ok (poc-infra-01,
                                                               poc-observer-plugin-01, ...)
```

Ha a `cic-primitives` / `cic-compute` repo nem klónozható (hálózati ok), a `kb_focus`-ban
megadott chunk-okat (`get_chunk`) használd helyettük — ezek ugyanazt a tartalmat fedik le.

---

## Elvárt kimenetek (`output/`)

### 1. `cic-oci-repo-bootstrap.md`

Repo-init terv a `cic-oci` repóhoz:
- `origin` / `base` remote-ok
- branch-séma: `devel`, `main`, `oci/devel`, `oci/main`, `oci/releases/v0.1.0`
- tag-séma: `cic-oci@0.1.0` + `oci/@v0.1.0`
- mit kell átemelni a `base-repo`/`cic-primitives` template-ből (tooling, CLAUDE.md, compiler.py,
  signing — ld. `cic-compute` mit örökölt)
- mi az **első release tartalma** (v0.1.0) — minimális kör: hány `DomainComposition` kell hozzá

### 2. `cic-oci-schema-plan.md`

Séma-struktúra terv:
- `schemas/atomic/` és `schemas/aggregate/` — melyik primitívet/aggregate-et veszi át
  változatlanul a `cic-primitives`-ből
- `schemas/examples/` — az 5 OCI `DomainComposition` egy-egy bekezdéses terve:

  | DomainComposition | config_surface (Terraform input) | state_surface (`actual_state.json` mezők) | operation_surface | binding_surface |
  |---|---|---|---|---|
  | `OciCompartment` | ... | ... | ... | OCID |
  | `OciVcn` | ... | ... | ... | OCID |
  | `OciSubnet` | ... | ... | ... | OCID |
  | `OciSecurityList` | ... | ... | start/stop nincs, csak update | OCID |
  | `OciComputeInstance` | shape, ocpus, memory_gb, image | lifecycle_state, public_ip,
    private_ip, security_rules_hash, collected_at | start/stop/terminate | OCID |

  Az `OciComputeInstance` `state_surface` mezői **pontosan egyezzenek** a
  `poc-system-plan/input.md`-ben definiált `actual_state.json` sémával — ne találj ki új mezőket.

- Függőségi sorrend a `DomainComposition`-ök implementálásához (mit kell előbb megírni)

### 3. `oci-compositions/oci-compute-instance.yaml` — reality check

**Egyetlen** kidolgozott `DomainComposition`, a `kubernetes-pod.yaml` mintájára, az
`OciComputeInstance`-ra:

- `config_surface`: `shape` (pl. `VM.Standard.A1.Flex`), `ocpus`, `memory_gb`, `image_id`,
  `subnet_id`, `display_name`
- `state_surface`: a `poc-system-plan` `actual_state.json` mezői 1:1
- `operation_surface`: `start`, `stop`, `terminate` (OCI lifecycle műveletek)
- `notification_surface`: `lifecycle-state-changed` event
- `binding_surface`: OCID-alapú cím (`/cic-oci:instances/instance={ocid}`)
- `derivation_chain`:
  - `yang`: modul váz `cic-oci-compute-instance`
  - `api`: OCI SDK/REST végpontok (`GET/POST /20160918/instances/{instanceId}`,
    `POST .../instances/{instanceId}/actions/start` stb.)
  - `runtime`: reconcile loop — `terraform plan/apply` ↔ `oci compute instance get` ↔
    git state commit (state/ ág, `pbs_root_hash` nélkül — ld. poc-system-plan döntés)

---

## Amit NE csinálj

- Ne hozd létre ténylegesen a `cic-oci` repót (nincs jogosultságod, és ez egy következő job feladata)
- Ne írd meg mind az 5 `DomainComposition`-t — csak az `OciComputeInstance`-t (reality check)
- Ne vitasd felül a `poc-system-plan`-ban lezárt OCI döntéseket (Free Tier Ampere A1, git state
  commit, Vault mem mode, OIS allow-all stb.)
- Ne módosítsd a `cic-primitives` / `cic-compute` klónokat
- Ne hozz létre fájlokat az `output/`-on kívül (kivéve ha sub-job specet hozol létre indokolt esetben)

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
