# `cic-oci` — séma-struktúra terv

> Státusz: **concept** (terv). Egyetlen kidolgozott `DomainComposition`:
> `oci-compositions/oci-compute-instance.yaml` (reality check). A többi 4
> erőforrás itt csak egy-egy bekezdésben/táblázat-sorban van megtervezve —
> implementáció a `poc-oci-schema-design-02` (vagy hasonló) job feladata.

---

## 1. `schemas/atomic/` — átvétel a `cic-primitives`-ből

A `cic-primitives/schemas/atomic/` 8 atomot tartalmaz (a 7 "irreducible atom" +
`Access`, amely a `c1861` chunk leírása szerint Phase 8.2-ben került be).
A `cic-compute` referencia ebből **7-et** vett át (nincs `access.yaml` a
`cic-compute/schemas/atomic/`-ban).

| Atom | Átvétel `cic-oci`-ba | Indoklás |
|---|---|---|
| `Shape` | igen, v0.1.0-tól | minden `config_surface`/`state_surface` node erre épül |
| `Role` | igen, v0.1.0-tól | `config`/`state`/`operational` szerepkör-jelölés minden mezőn |
| `Behavior` | igen, v0.1.0-tól | `operation_surface` (start/stop/terminate) |
| `Contract` | igen, v0.1.0-tól | enum/range/pattern validáció (pl. `lifecycle_state` enum) |
| `Address` | igen, v0.1.0-tól | `binding_surface` — OCID-alapú cím |
| `Identity` | igen, v0.1.0-tól | minden `DomainComposition` `identity` blokkja |
| `Event` | igen, v0.1.0-tól | `notification_surface` (pl. `lifecycle-state-changed`) |
| `Access` | **nem v0.1.0-ban** | csak akkor kell, ha `policy_surface`-t implementálunk; OIS v1 "allow all" → nincs domain-szintű policy tartalom. Felvétel a `poc-oci-schema-design-02`-ben, ha a PolicySurface aggregate is bekerül. |

## 2. `schemas/aggregate/` — átvétel a `cic-primitives`-ből

| Aggregate | Átvétel | Indoklás |
|---|---|---|
| `ManagedEntity` | igen, v0.1.0 | minden `DomainComposition` `base.aggregate` |
| `ConfigSurface` | igen, v0.1.0 | |
| `StateSurface` | igen, v0.1.0 | |
| `OperationSurface` | igen, v0.1.0 | |
| `PolicySurface` | **nem v0.1.0-ban** | l. `Access` indoklás fent — `ManagedEntity.policy_surface` slot `mode: defaulted, default: open`, explicit tartalom nélkül is érvényes |

`NotificationSurface` és `BindingSurface` **nincs** dedikált aggregate fájlként a
`cic-primitives`-ben (`schemas/aggregate/` directory listing: csak
`config-surface`, `managed-entity`, `operation-surface`, `policy-surface`,
`state-surface` — 5 fájl). A `managed-entity.yaml` ezeket slot-szinten kezeli:

```yaml
notification_surface:
  mode: defaulted
  type: "Event[]"
  atomic_ref: schemas/atomic/event.yaml
  default: empty
  description: >
    ... Jövőbeli NotificationSurface aggregate fogja köré burkolni ...

binding_surface:
  mode: required
  type: "Address[]"
  atomic_ref: schemas/atomic/address.yaml
  description: >
    ... Jövőbeli BindingSurface aggregate köré burkolja az adapter referenciát is.
```

→ **Státusz: concept** a dedikált aggregate-ekre. A `cic-oci`
`DomainComposition`-ök a `kubernetes-pod.yaml` / `cloud-instance.yaml` mintát
követve közvetlenül `notification_surface.events[]` és
`binding_surface.addresses[]` listákat írnak `Event`/`Address` atomic_ref-fel —
ez **implemented** minta (mindkét referencia repóban így működik).

## 3. `schemas/domain/` vs `schemas/examples/` — döntés

A `cic-compute` repóban **mindkét** könyvtár létezik:
- `schemas/domain/` — 3 db véglegesített `DomainComposition` (`virtual-machine.yaml`,
  `cloud-instance.yaml`, `physical-machine.yaml`) — ezek a domain "termékei".
- `schemas/examples/` — a `cic-primitives`-ből örökölt `kubernetes-pod.yaml`
  (idegen domain mintapélda, megőrizve referenciaként) + `examples/invalid/`
  (negatív tesztesetek).

A jelen job input-ja (`schemas/examples/` — DomainComposition objektumok, a domain
konkrét erőforrásai) a **`cic-compute/schemas/domain/` szemantikáját** írja le, csak
más néven. **Javaslat:** `cic-oci` kövesse a `cic-compute` tényleges, megvalósult
mintáját:

```
schemas/domain/      ← OciCompartment, OciVcn, OciSubnet, OciSecurityList,
                        OciComputeInstance — az 5 OCI DomainComposition
schemas/examples/    ← cic-primitives kubernetes-pod.yaml átvétele referenciaként
                        + examples/invalid/ (negatív tesztek, cic-compute mintából)
```

A jelen job reality-check fájlja (`oci-compositions/oci-compute-instance.yaml`)
ennek megfelelően a végleges helyén `schemas/domain/oci-compute-instance.yaml`
lenne — itt külön `oci-compositions/` alatt van, mert ez a job nem hozza létre a
repót.

---

## 4. Az 5 OCI `DomainComposition` terve

Minden sor: `config_surface` (Terraform input — `oci_core_*` resource attribútumok),
`state_surface` (mit ad vissza a megfigyelő — OCI API / `actual_state.json`),
`operation_surface` (CIC műveletek), `binding_surface` (OCID-alapú cím).

### `OciCompartment`

| Surface | Tartalom |
|---|---|
| `config_surface` | `name`, `description`, `parent_compartment_id` (tenancy OCID vagy szülő compartment) |
| `state_surface` | `compartment_id` (OCID), `lifecycle_state` (`ACTIVE`/`DELETING`/`DELETED`), `time_created` |
| `operation_surface` | nincs explicit — a compartment lifecycle Terraform-vezérelt (create/delete csak `terraform apply`/`destroy`-on keresztül, nincs külön CIC operation) |
| `binding_surface` | `/cic-oci:compartments/compartment={ocid}` |

Megjegyzés: a `poc-system-plan` Milestone 0-ban a compartment egyszeri,
`terraform apply`-val létrejövő erőforrás — drift detekció szempontjából
alacsony prioritású (ritkán változik).

### `OciVcn`

| Surface | Tartalom |
|---|---|
| `config_surface` | `cidr_block`, `display_name`, `compartment_id` (ref `OciCompartment` binding) |
| `state_surface` | `vcn_id` (OCID), `lifecycle_state`, `default_route_table_id`, `default_security_list_id` |
| `operation_surface` | nincs explicit (Terraform-vezérelt lifecycle, mint `OciCompartment`) |
| `binding_surface` | `/cic-oci:vcns/vcn={ocid}` |

### `OciSubnet`

| Surface | Tartalom |
|---|---|
| `config_surface` | `cidr_block`, `display_name`, `vcn_id` (ref), `availability_domain` (Free Tier AD), `route_table_id`, `security_list_ids[]` |
| `state_surface` | `subnet_id` (OCID), `lifecycle_state`, `virtual_router_ip` |
| `operation_surface` | nincs explicit |
| `binding_surface` | `/cic-oci:subnets/subnet={ocid}` |

### `OciSecurityList`

| Surface | Tartalom |
|---|---|
| `config_surface` | `vcn_id` (ref), `display_name`, `ingress_security_rules[]` (protocol, source, port_range), `egress_security_rules[]` |
| `state_surface` | `security_list_id` (OCID), `lifecycle_state`, `security_rules_hash` (a `poc-system-plan` `actual_state.json`-ban szereplő hash mező itt az `OciComputeInstance.state_surface`-ben jelenik meg, de a forrás-hash itt számolható: `sha256(canonical_json(ingress+egress rules))`) |
| `operation_surface` | **start/stop nincs** — kizárólag `update` (a `poc-system-plan` szerint a drift demo lépése pontosan ez: "OCI Security List szabály kézi módosítása") |
| `binding_surface` | `/cic-oci:security-lists/security-list={ocid}` |

### `OciComputeInstance` (reality check — kidolgozva)

| Surface | Tartalom |
|---|---|
| `config_surface` | `shape` (pl. `VM.Standard.A1.Flex`), `ocpus`, `memory_gb`, `image_id`, `subnet_id`, `display_name` |
| `state_surface` | **1:1 a `poc-system-plan/input.md` `actual_state.json` sémájával**: `instance_id`, `lifecycle_state`, `shape`, `ocpus`, `memory_gb`, `public_ip`, `private_ip`, `vcn_id`, `security_rules_hash`, `collected_at` |
| `operation_surface` | `start`, `stop`, `terminate` (OCI lifecycle műveletek, l. `cic-compute/schemas/domain/cloud-instance.yaml` start/stop/terminate mintája) |
| `notification_surface` | `lifecycle-state-changed` event |
| `binding_surface` | `/cic-oci:instances/instance={ocid}` |

→ teljes kidolgozás: `oci-compositions/oci-compute-instance.yaml`

---

## 5. Függőségi sorrend az implementációhoz

A `derivation_chain.runtime.adapter_contract` (OCI SDK hívások) és a
`poc-observer-plugin-01` scope-ja alapján:

```
1. OciCompartment      ← gyökér; minden más erőforrás compartment_id-t referál
2. OciVcn              ← compartment-en belül; subnet-ek és security list-ek tartója
3. OciSubnet           ← VCN-en belül; ComputeInstance ehhez kötődik
   OciSecurityList     ← VCN-en belül; SubnetTel párhuzamosan implementálható
4. OciComputeInstance  ← subnet + security list + image_id (compartment-en belül)
```

Indoklás:
- `OciCompartment` és `OciVcn` egymás után, mert minden további erőforrás
  `compartment_id`-t és/vagy `vcn_id`-t referál — ezek nélkül a `binding_surface`
  OCID-jei nem értelmezhetők.
- `OciSubnet` és `OciSecurityList` egymástól függetlenek (mindkettő csak a VCN-re
  támaszkodik), implementálhatók párhuzamosan.
- `OciComputeInstance` az utolsó, mert `config_surface.subnet_id` a `OciSubnet`-re,
  a `state_surface.security_rules_hash` pedig (számítási szempontból) a
  `OciSecurityList`-re mutat.
- A `poc-observer-plugin-01` (amely az `actual_state.json`-t építi és git state
  commit-ot végez) **kizárólag az `OciComputeInstance`-hez kötődik** — ez az oka,
  hogy ez a job ezt dolgozta ki elsőként reality check gyanánt.

---

## 6. Validáció

A `cic-primitives/schemas/index.yaml` (meta-séma) változatlanul érvényes
`cic-oci`-ra is — minden `DomainComposition` fájlnak meg kell felelnie a
`spec.kind: DomainComposition` ágnak (`required: [base]`, `base.aggregate`
megadva). A `tools/compiler.py` (változatlan átvétel a `cic-compute`-ból)
validálja ezt — l. `cic-oci-repo-bootstrap.md` 4. pont.
