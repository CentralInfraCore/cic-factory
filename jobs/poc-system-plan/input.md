# poc-system-plan — PoC rendszerterv szintézis (OCI)

## Célod

Szintetizáld az összes előző tervező és audit job kimenetét egyetlen, végrehajtható rendszertervvé, amely az OCI-ra adaptált PoC domain job-ok (`poc-infra-01`, `poc-observer-plugin-01`, `poc-drift-detection-01`, `poc-rollback-01`, `poc-schema-signing-01`) számára az egyetlen referenciadokumentum lesz.

Ez **szintézis, nem újrafelfedezés** — ne kérdőjelezd meg a lezárt döntéseket, ne keress alternatívákat. A meglévő outputokat olvasd el, majd írd meg a tervdokumentumot.

---

## Lezárt döntések (ne kérdőjelezd meg)

| Döntés | Érték |
|---|---|
| Demo infrastruktúra | **Oracle Cloud Infrastructure (OCI)** — Free Tier Ampere A1 |
| PBS helyettesítő | **git state commit** — az actual state közvetlenül a state/ ágra kerül git commitként, `pbs_root_hash` mező kimarad |
| Plugin betöltés | **Go .so natív modul** (nem WASM v1-ben) |
| OIS policy v1 | **allow all** — ha actor == "relay-operator" és action == "rollback" |
| Vault v1 | **mem mode** elegendő |
| Git state repo | **bare git repo** (v1-ben), state/ és intent/ ágak |
| Domain adapter repo | **cic-oci** (cic-proxmox helyett) |

---

## Bemenetek — kötelező olvasás

Olvasd el ezeket a job outputokat a szintézis előtt:

```
jobs/poc-implementation-plan/output/execution-model.md    — 4 fázis, CIC szerepek, ProofTrace struktúra
jobs/poc-implementation-plan/output/roadmap.md            — milestone-ok, demo forgatókönyv
jobs/poc-implementation-plan/output/status-matrix.md      — implemented/scaffold/concept mátrix
jobs/poc-implementation-plan/output/sub-jobs-overview.md  — domain job-ok függőségi gráfja
jobs/poc-bridge-check/output/                             — bridge térkép visszaellenőrzés (27 CONFIRMED, 6 PARTIAL, 2 INCORRECT)
jobs/poc-repo-design/output/repo-plan.md                  — repo struktúra terv (cic-proxmox → cic-oci adaptálandó)
jobs/relay-func-audit/output/gap-summary.md               — implemented/scaffold/concept Go-szintű leltár
jobs/relay-func-audit/output/relay-audit.md               — részletes relay forráskód audit
```

---

## OCI adaptáció — mit kell átírni a Proxmox-tervhez képest

A `roadmap.md` és `repo-plan.md` Proxmox-ra épül. Az alábbi eltéréseket vezesse át a rendszertervbe:

### Infrastruktúra réteg

| Proxmox elem | OCI megfelelője |
|---|---|
| Proxmox VM lifecycle (create/destroy) | OCI Compute instance (terraform-provider-oci) |
| Proxmox API kliens | OCI SDK / REST API |
| VyOS router (kézi szabálymódosítás 8.2-ben) | OCI Security List szabály kézi módosítása |
| OpenSwitch | OCI VCN subnet |
| PBS snapshot → `pbs_root_hash` | **nincs** — git state commit az anchor |
| `terraform-provider-proxmox` (bpg/proxmox) | `terraform-provider-oci` (hashicorp/oci) |
| Bastion VM | OCI Bastion service vagy egyszerű jump host VM |

### actual_state.json tartalma OCI-ban

PBS hiányában az `actual_state.json` az OCI instance metaadatokból épül fel:

```json
{
  "instance_id": "ocid1.instance...",
  "lifecycle_state": "RUNNING|TERMINATED",
  "shape": "VM.Standard.A1.Flex",
  "ocpus": 2,
  "memory_gb": 12,
  "public_ip": "...",
  "private_ip": "...",
  "vcn_id": "ocid1.vcn...",
  "security_rules_hash": "sha256:...",
  "collected_at": "RFC3339"
}
```

Ez kerül commitolva a `state/` ágra `actual_state.json`-ként, `pbs_root_hash` mező nélkül.

### Drift detekció OCI-ban

A drift összehasonlítás alapja:

- **NO_DRIFT**: `actual_state.json` (state/ ág HEAD) megegyezik az OCI API aktuális válaszával
- **RECONCILIABLE_DRIFT**: eltérés van, de az OCI API-n visszaállítható (pl. security rule módosítás)
- **HARD_DRIFT**: az instance nem létezik (lifecycle_state: TERMINATED vagy nem található)

---

## Elvárt kimenetek

Hozz létre az `output/` könyvtárban:

### 1. `system-plan.md` — a fő dokumentum

Tartalmazza:

**a) OCI minimális konfiguráció (Milestone 0)**
- OCI erőforrások listája: compartment, VCN, subnet, security list, compute instance-ok (Vault, Relay, Demo target, Bastion)
- Terraform OCI provider konfig váz
- Vault mem mode indítási lépések OCI VM-en
- Git state repo inicializálás (state/ és intent/ ágak)
- CIC-Relay binary deploy OCI VM-re

**b) Felülvizsgált relay workflow-ok (poc.iac.observe)**

Az `execution-model.md` Proxmox-ra írta a workflow lépéseit. Írja át OCI-ra:

```yaml
# poc.iac.observe v1.0 — OCI adaptáció
steps:
  - cic.iac.assert@1.0       # OIS intent rögzítés
  - cic.iac.snapshot@1.0     # OCI instance state lekérés (PBS helyett)
  - cic.iac.prooftrace@1.0   # ProofTrace létrehozás (pbs_root_hash nélkül)
  - cic.iac.commit@1.0       # GitStateRecorder commit → state/ ág
```

Minden lépésnél: mit vár bemenetként, mit ad ki, melyik Go interfészhez kötődik.

**c) domain job-ok implementációs scope-ja**

A `sub-jobs-overview.md` alapján, OCI-ra és git state commit-ra adaptálva:

| Domain job | Scope (OCI-adaptált) | Deliverable |
|---|---|---|
| `poc-infra-01` | OCI compartment + VCN + VM-ek Terraformmal, Vault mem, Relay binary, git state repo | `terraform apply` sikeres, relay elindul |
| `poc-observer-plugin-01` | OCI API kliens Go .so pluginként, `actual_state.json` buildelés, git state commit | `terraform apply` → state/ ág commit, `prooftrace.json` érvényes |
| `poc-drift-detection-01` | OCI state poll (periodic), drift osztályozás, state/ ág commit `drift_type`-pal | 5 kézi módosítás → 5 drift commit |
| `poc-rollback-01` | intent/ ág figyelő, OIS allow-all check, Terraform apply trigger, új ProofTrace | infra újjáépül, CommitRef visszautal |
| `poc-schema-signing-01` | Vault Transit key setup OCI VM-en, CICSourceCA stub aktiválás | `cic_sign` nem "unavailable" |

**d) Gap-ek a relay-func-audit alapján — mit kell megírni**

A `gap-summary.md` concept és scaffold elemei közül melyek blokkolják a PoC-t:

| Gap | PoC blokkoló? | Kezelés |
|---|---|---|
| `VerifyProofArtifact` soha nem hívódik | **igen** — a lánc nem auditálható vissza | `poc-observer-plugin-01` scope: meghívni a workflow végén |
| `PoSEResult` soha nem töltődik ki | részben — `pose_result: SKIPPED` elfogadható v1-ben | marad SKIPPED, v2-ben aktiválni |
| sign/verify dev bypass | elfogadható — Vault mem módban fut | `poc-schema-signing-01` oldja fel |
| `GitSyncer` soha nem hívódik | nem blokkoló | nem kell v1-ben |
| `isolation.Coordinator` nem hívódik | nem blokkoló | nem kell v1-ben |

**e) Felülvizsgált demo forgatókönyv (OCI)**

Az `roadmap.md` demo script OCI-ra átírva:
- Proxmox web UI → OCI Console / `oci-cli` / `terraform show`
- PBS snapshot → `oci compute instance get` kimenete
- VyOS szabály módosítás → OCI Security List szabály kézi módosítása
- Időzítések (az OCI API propagálási késleltetése figyelembevételével)

### 2. `oci-infra-sketch.md` — OCI infrastruktúra vázlat

Terraform resource-ok listája (nem teljes kód, csak azonosítók és típusok):
- `oci_identity_compartment`
- `oci_core_vcn`, `oci_core_subnet`, `oci_core_security_list`
- `oci_core_instance` × 4 (Bastion, Vault, Relay, Demo target)
- SSH key management
- OCI Free Tier korlátok és figyelmeztetések (region-specifikus Ampere elérhetőség)

### 3. `domain-job-inputs.md` — domain job-ok bemeneti összefoglalója

Minden domain job-hoz egy bekezdés: mit várhat el az előző job outputjától, milyen döntéseket nem kell újra meghoznia, és mi a pontos technikai belépési pontja.

---

## Amit NE csinálj

- Ne vitasd a Proxmox vs OCI döntést
- Ne tervezz WASM iSDK-t v1-be
- Ne tervezz PoSE VERIFIED módot v1-be (SKIPPED elfogadható)
- Ne tervezz CICSourceCA teljes PKI láncot v1-be (Vault mem mode elegendő)
- Ne adj új architektúrális döntéseket — csak adaptáld a meglévőket OCI-ra
- Ne hozz létre fájlokat az `output/`-on kívül

---

## Kontextus a KB-ból

A szintézishez releváns KB node-ok (ha MCP elérhető):

```
kb_status
get_chunk("c912")   — relay pozíció: nem tartalmaz állapotgépet
get_chunk("c2436")  — ProofTrace struktúra
get_chunk("c2498")  — OIS formális modell
get_chunk("c2543")  — drift osztályozás
get_chunk("c263")   — proof_artifact séma (commit_record, pose_result)
get_chunk("c590")   — GitStateRecorder.RecordState
get_chunk("c2616")  — CommitRef + state/ ág modell
```

Ha a KB nem elérhető, a fenti chunk-ok tartalmát az `execution-model.md` és `relay-audit.md` lefedi — azokból dolgozz.
