# PoC és Demonstráció megvalósítási terv

## Kontextus

A CentralInfraCore (CIC) ökoszisztéma PoC és élő demonstráció megvalósítását kell megtervezned.
A demonstráció specifikációja: `jobs/poc-implementation-plan/ref/add.md` — olvasd el először.

---

## Boot sequence — KÖTELEZŐ, ebben a sorrendben, kihagyás nélkül

### 1. KB elérhetőség
`kb_status`

### 2. A teljes CIC repó térkép feltérképezése

Kérdezd le a KB-t az összes releváns repóra és területre. **Minden lekérdezéshez olvasd el a visszakapott chunk-okat (`get_chunk`):**

**Relay végrehajtási modell:**
- `search_query`: "relay szerepe mit csinál mit nem csinál plugin stateless"
- `search_query`: "relay workflow step plugin PluginRef StateRequirement NextHops Dependencies BaseBlock"
- `search_query`: "wasm iSDK host frame plugin interface"
- `search_nodes`: "graf_vegrehajtas allapotmodell schema_kezeles relay_pozicionalas plugin_interface wasm_isdk"

**Primitívek és schema rendszer:**
- `search_query`: "primitives BaseBlock CIC schema alap típusok minta példa"
- `search_nodes`: "cic-primitives primitives schema"
- `search_query`: "CIC-Schemas postgresql schema compiler signing release artifact"
- `search_query`: "schema signed artifact Vault CICSourceCA release workflow"

**IaC és állapot modell:**
- `search_query`: "IaC state desired actual state branch git commit ProofTrace"
- `search_query`: "drift SOFT RECONCILIABLE HARD detection observer"
- `search_nodes`: "iac_ontology state_commit drift"

**CIC-objs kollekcio:**
- `search_query`: "cic-objs cic-compute cic-network cic-storage cic-primitives objektum típusok"
- `search_query`: "OIS OpenIntentSign intent obligation policy rollback"

### 3. A demonstráció pontos értelmezése

Az `add.md` 8.1–8.4 fázisait olvasd el pontosan. Válaszolj ezekre a KB + add.md alapján:

**Mi a CIC szerepe fázisanként?**
- 8.1 (Terraform up): Ki indítja a Terraformot? Mit csinál a CIC közben?
- 8.2 (kézi módosítások): Ki módosít? Mit csinál a CIC?
- 8.3 (infra törlés): Ki törli? Mit csinál a CIC?
- 8.4 (rollback): Mi triggeri a CIC beavatkozását? Mit csinál pontosan?

**Ha a válasz: CIC egyes fázisokban CSAK megfigyelő és rögzítő — ezt explicit rögzítsd a tervben.**

### 4. Státusz ellenőrzés

Minden komponensre: implemented / scaffold / concept — node- vagy file-szintű KB bizonyítékkal.

### 5. Bridge térkép

`concept → code → runtime → audit` — hol szakad meg?

---

## Feladat

### 1. execution-model.md

A teljes végrehajtási lánc, primitívek mintájával:
```
add.md demo lépés → [ki indítja?] → relay workflow → plugin (.so) → ProofTrace
```

Tartalmazza:
- A relay pontos szerepe fázisanként (observer vs actor)
- BaseBlock / StateRequirement / PluginRef / NextHops / Dependencies használati minta konkrét példával
- Plugin betöltési mechanizmus (.so vs WASM iSDK)
- A primitívek és a CIC-Schemas postgresql schema hogyan illeszkedik a rendszerbe

### 2. status-matrix.md

Komponens státusz táblázat KB chunk ID-kkal.

### 3. infra-decision.md

Proxmox vs OCI Free Tier — elemzés és javaslat.

### 4. roadmap.md

PoC v1 + demo forgatókönyv a **helyes CIC szerepek** figyelembevételével:
- Mit csinál a CIC (rögzít, figyel, beavatkozik)?
- Mit csinál a human (Terraform, kézi módosítás)?
- Melyik fázisban van aktív CIC beavatkozás?

### 5. Sub-job specek

A végrehajtási modell és a helyes CIC szerepek alapján.

Sub-job meta.yaml minta:
```yaml
schema_version: "1.0"
job_id: "poc-<terület>-01"
parent_job_id: "poc-implementation-plan"
level: "domain"
target:
  repo: ""
  path: ""
kb_focus: []
promptmap_ref: ""
agent:
  config_dir: "~/.claude-personal/agents/agent-01"
  model: "claude-sonnet-4-6"
workplace:
  repos: []
  branch: "feature/poc-<terület>-01"
status: "pending"
error_message: ""
timestamps:
  created: "2026-06-06T00:00:00Z"
  started: ""
  completed: ""
```

Sub-jobokat NE futtasd.

---

## Output

`jobs/poc-implementation-plan/output/` a klónodban:
- `execution-model.md` — végrehajtási modell, primitívek, CIC szerepek fázisanként
- `status-matrix.md` — komponens státusz KB bizonyítékokkal
- `infra-decision.md` — Proxmox vs OCI
- `roadmap.md` — helyes CIC szerepekkel
- `sub-jobs-overview.md` — sub-job lista és függőségek

Sub-job spec fájlok: `jobs/<sub-job-id>/input.md` + `meta.yaml`

---

## Git — munka végén

```bash
git -C $FACTORY_CLONE add jobs/poc-implementation-plan/output/ jobs/poc-*/
git -C $FACTORY_CLONE commit -m "job: poc-implementation-plan — output + sub-job specs"
git -C $FACTORY_CLONE push -u origin feature/poc-implementation-plan
```

Push csak `feature/poc-implementation-plan` branch-re. Main-re NEM.

## Nyelvi szabály
- Output dokumentumok: **magyarul**
- YAML, JSON, shell, kód: **angolul**
