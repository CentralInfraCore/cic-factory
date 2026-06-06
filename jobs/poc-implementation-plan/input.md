# PoC és Demonstráció megvalósítási terv

## Kontextus

A CentralInfraCore (CIC) ökoszisztéma PoC és élő demonstráció megvalósítását kell megtervezned.
A specifikáció a `jobs/poc-implementation-plan/ref/add.md` fájlban található a workspace klónodon belül — olvasd el először.

A CIC jelenlegi implementációs állapotát a `cic-graph` MCP szerveren keresztül térképezd fel:
- `kb_status` — KB frissesség ellenőrzés
- `search_nodes` + `neighbors` — komponens állapot (implemented / scaffold / concept)
- `search_query` — szabad kérdések a rendszerről

**Minden állítást a KB-val alátámasztva tégy — ne feltételezz, hanem kérdezz le.**

---

## Feladat

### 1. Jelenlegi állapot felmérése

Térképezd fel a KB alapján minden PoC v1 komponensre:

| Komponens | Státusz | Megjegyzés |
|---|---|---|
| ProofTrace core | ? | |
| Vault Transit signing | ? | |
| Schema validator | ? | |
| OIS (OpenIntentSign) | ? | |
| IaC state branch | ? | |
| Drift detection | ? | |
| Terraform integráció | ? | |
| Relay runner | ? | |

### 2. Infrastruktúra döntési pont

A specifikáció szerint az alap infrastruktúra **Proxmox VAGY Oracle Cloud (OCI Free Tier)** lehet.
Mindkét opciót elemezd:

- **Proxmox**: lokális, teljes kontroll, hardware függőség, nincs cloud cost
- **OCI Free Tier**: cloud, ingyenes kvóta korlátok, hálózati latencia, könnyebb demo

Tegyél javaslatot melyikkel érdemes a PoC v1-et kezdeni, és miért. Ha mindkettőt támogatni kell, jelöld az IaC abstraction követelményét.

### 3. Megvalósítási roadmap

Az `add.md` alapján készíts egy részletes roadmap-et:

**PoC v1** (Proxmox/OCI + VyOS + Vault(mem) + Relay):
- Milyen komponensek hiányoznak teljesen?
- Milyen scaffold elemek igényelnek implementációt?
- Mi a kritikus út (dependency sorrendben)?
- Becsült komplexitás (kis/közepes/nagy)?

**PoC v2** (+ Talos, Gitea, Nexus, CloudNativePG, Prom/Grafana):
- Mi épül a v1-re vs mi párhuzamos?
- Új bridge-ek amik kellenek?

**PoC v3** (+ két telephely, k8s, titkosított link):
- Csak az architektúrális elvek — részletes terv nem szükséges

**Demo forgatókönyv** (8 fejezet az add.md-ben):
- Milyen demo-specifikus komponensek kellenek (drift trigger, rollback script, live display)?
- Melyik PoC verzió után futtatható?

### 4. Al-feladatok generálása

Minden jelentős implementációs területre hozz létre egy sub-job specifikációt.

**Format:** `jobs/<sub-job-id>/input.md` + `jobs/<sub-job-id>/meta.yaml`

Sub-job id konvenció: `poc-<terület>-<szám>`, pl:
- `poc-iac-terraform-01` — Terraform IaC szkeletonok
- `poc-drift-engine-01` — Drift detection implementáció
- `poc-relay-wiring-01` — Relay → ProofTrace bekötés
- `poc-demo-scripts-01` — Demo forgatókönyv szkriptek

Minden sub-job meta.yaml-ban:
```yaml
parent_job_id: "poc-implementation-plan"
level: "domain"  # vagy "repo"
status: "pending"
```

**Az sub-jobokat NE futtasd — csak hozd létre a spec fájlokat.** Az orchestrátor dönt a futtatási sorrendről.

---

## Output

Minden fájlt a workspace klónjába írj (`jobs/poc-implementation-plan/output/`):

- `output/roadmap.md` — teljes megvalósítási terv (fő dokumentum)
- `output/status-matrix.md` — komponens státusz táblázat KB bizonyítékokkal
- `output/infra-decision.md` — Proxmox vs OCI elemzés és javaslat
- `output/sub-jobs-overview.md` — létrehozott sub-jobok listája és célja

A sub-job spec fájlok: `jobs/poc-<terület>-<szám>/input.md` és `meta.yaml`

---

## Git

A munka végén commitolj és pushol a feature branch-re:

```bash
git -C $FACTORY_CLONE add jobs/poc-implementation-plan/output/ jobs/poc-*/
git -C $FACTORY_CLONE commit -m "job: poc-implementation-plan — output + sub-job specs"
git -C $FACTORY_CLONE push -u origin feature/poc-implementation-plan
```

**Push csak `feature/poc-implementation-plan` branch-re. Main/devel-re NEM.**

---

## Nyelvi szabály

- Output dokumentumok: **magyarul**
- YAML, JSON, shell, kód: **angolul**
- KB lekérdezések: bármelyik (MCP angolul válaszol)
