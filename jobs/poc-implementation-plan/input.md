# PoC és Demonstráció megvalósítási terv

## Kontextus

A CentralInfraCore (CIC) ökoszisztéma PoC és élő demonstráció megvalósítását kell megtervezned.
A specifikáció a munkakörnyezeted klónjában: `jobs/poc-implementation-plan/ref/add.md`

---

## Boot sequence — KÖTELEZŐ, ebben a sorrendben

### 1. KB elérhetőség
`kb_status` — ellenőrizd hogy a KB elérhető és friss.

### 2. Végrehajtási modell megértése (ELŐSZÖR EZT)

Mielőtt bármit tervezel, értsd meg hogyan hajt végre egy relay lépést a rendszer:

- `search_query`: "relay végrehajtó egység step hogyan fut plugin wasm"
- `search_query`: "wasm modul iSDK host frame plugin interface relay"
- `search_query`: "relay mit nem csinál közvetlenül plugin role stateless"
- `search_nodes`: "plugin_interface wasm_isdk relay_pozicionalas"

**Kérdések amiket meg kell válaszolnod a KB alapján mielőtt továbblépesz:**
1. Mi a relay tényleges szerepe — mit csinál és mit NEM csinál közvetlenül?
2. Mi hajt végre egy konkrét műveletet (fájlírás, hálózati hívás, állapotváltozás)?
3. Hogyan kapcsolódik egy workflow lépés a tényleges végrehajtóhoz?
4. Mi az iSDK és a host frame szerepe?

**Ha a válasz: WASM modul — akkor a PoC minden új lépése WASM modulként írandó, nem Go kódként a relay core-ba.**

### 3. Komponens státusz felmérés

Csak az előző lépés után: `search_nodes` → `search_query` → státusz (implemented/scaffold/concept) a PoC v1 komponensekre.

### 4. Bridge térkép

Hol szakad meg a lánc `concept → code → runtime → audit` között?

---

## Feladat

### 1. Végrehajtási modell dokumentálása

Az output első és legfontosabb része: **hogyan fut egy PoC lépés a relay rendszerben?**

```
input.md spec lépés → relay workflow step → [???] → ProofTrace
```

Töltsd ki a `[???]`-t a KB alapján. Ez határozza meg az összes többi döntést.

### 2. Komponens státusz mátrix

KB bizonyítékokkal alátámasztva — minden állítás node- vagy file-szintű forrással.

### 3. Infrastruktúra döntési pont

Proxmox vs Oracle Cloud (OCI Free Tier) — elemzés és javaslat a PoC v1-hez.

### 4. Megvalósítási roadmap

Az `add.md` spec (ref/ könyvtárban) és a KB alapján:

**PoC v1** (Proxmox/OCI + VyOS + Vault(mem) + Relay):
- Hiányzó komponensek (KB-val alátámasztva)
- Kritikus út dependency sorrendben
- Komplexitás becslés

**Demo forgatókönyv** (4 fázis az add.md-ből):
- Melyik fázishoz mi szükséges
- Melyik PoC verzió után futtatható

### 5. Sub-job specifikációk

A végrehajtási modell megértése alapján hozz létre sub-job speceket.

**A sub-job specek a cic-factory klónodban jönnek létre:**
`jobs/<sub-job-id>/input.md` + `meta.yaml`

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

**Sub-jobokat NE futtasd — csak hozd létre a spec fájlokat.**

---

## Output

Írj a klónodban: `jobs/poc-implementation-plan/output/`

- `output/execution-model.md` — **hogyan fut egy relay lépés** (ez a legfontosabb)
- `output/roadmap.md` — megvalósítási terv
- `output/status-matrix.md` — komponens státusz KB bizonyítékokkal
- `output/infra-decision.md` — Proxmox vs OCI elemzés
- `output/sub-jobs-overview.md` — sub-job lista és függőségek

Sub-job spec fájlok: `jobs/<sub-job-id>/input.md` és `meta.yaml`

---

## Git — a munka végén

```bash
git -C $FACTORY_CLONE add jobs/poc-implementation-plan/output/ jobs/poc-*/
git -C $FACTORY_CLONE commit -m "job: poc-implementation-plan — output + sub-job specs"
git -C $FACTORY_CLONE push -u origin feature/poc-implementation-plan
```

Push csak `feature/poc-implementation-plan` branch-re. Main-re NEM.

---

## Nyelvi szabály

- Output dokumentumok: **magyarul**
- YAML, JSON, shell, kód: **angolul**
