# Megvalósítási roadmap — PoC v1 + Demo forgatókönyv

**Alap:** add.md spec + KB végrehajtási modell
**Kritikus felismerés:** Minden új PoC funkcionalitás plugin (.so) formájában írandó, NEM relay core módosításként.

---

## PoC v1 — Hiányzó komponensek (KB státusz alapján)

### A. Plugin implementációk (mind concept → implemented)

| Plugin | Funkció | add.md kapcsolat | Komplexitás |
|---|---|---|---|
| `terraform-apply.so` | Terraform CLI hívás, kimenet visszaolvasás | 8.1 fázis: infra felhúzás | Közepes |
| `drift-detector.so` | ProofTrace vs. tényleges állapot összehasonlítás | 8.2 fázis: drift detektálás | Magas |
| `ois-validator.so` | OIS intent/obligation ellenőrzés | 8.4 fázis: rollback policy | Közepes |
| `state-commit.so` | state/ git ág auto commit | 8.1 fázis: CommitRef generálás | Alacsony |
| `rollback-trigger.so` | intent/ ág frissítés → Terraform apply | 8.4 fázis: rollback végrehajtás | Magas |

### B. Infrastruktúra setup (concept → runtime)

| Elem | Státusz | Lépés |
|---|---|---|
| Proxmox VM-ek | concept | Terraform IaC definiálás + provizionálás |
| VyOS router konfig | concept | Baseline konfig + drift demo szabályok |
| Vault(mem) | concept | Dev mode indítás, relay plugin token |
| IaC git repo (state/ ág) | concept | Repo létrehozás, branch struktura |
| intent/ ág | concept | Rollback workflow ág |

### C. Scaffold bekötések (előfeltétel-függők)

| Komponens | Előfeltétel | PoC v1-ben? |
|---|---|---|
| pki_verify.go | CICRootCA → Intermediate CA → leaf cert | Nem — v2 |
| LocalWorker in-process | 3-process isolation + Vault | Nem — v2 |
| WASM iSDK / host frame | iSDK könyvtár implementáció | Nem — v2 |

---

## Kritikus út — dependency sorrend

```
1. Infrastruktúra alap
   └── Proxmox VM-ek (bastion, vyos, vault, relay, tf-runner)
       └── VyOS baseline konfig

2. Vault(mem) + relay startup
   └── cic-relay binary deploy
       └── Plugin betöltési konfig (plugin dir)

3. IaC git repo setup
   └── state/ ág + intent/ ág
       └── state-commit.so plugin

4. Terraform plugin
   └── terraform-apply.so
       └── Tesztelés: relay workflow → Terraform apply

5. ProofTrace pipeline ellenőrzés
   └── Workflow YAML → lépés → ProofArtifact → CommitRef

6. Drift detektálás
   └── drift-detector.so
       └── VyOS szabály módosítás → SOFT_DRIFT detektálás

7. OIS validator
   └── ois-validator.so
       └── Rollback policy ellenőrzés

8. Rollback plugin
   └── rollback-trigger.so
       └── intent/ ág push → Terraform apply
```

---

## PoC v1 szprintek

### Sprint 1 — Alap infrastruktúra (est: 3-5 nap)
- Proxmox VM-ek Terraformmal
- VyOS router baseline
- Vault(mem) dev mode
- cic-relay deploy + smoke test

### Sprint 2 — Plugin réteg alapok (est: 5-7 nap)
- `state-commit.so` plugin
- `terraform-apply.so` plugin
- IaC git repo + state/ ág
- Relay workflow: Terraform up → ProofTrace → CommitRef

### Sprint 3 — Drift detektálás (est: 5-7 nap)
- `drift-detector.so` plugin
- SOFT_DRIFT / RECONCILIABLE_DRIFT / HARD_DRIFT típus implementáció
- VyOS kézi módosítás → drift commit → state/ ág frissítés

### Sprint 4 — Rollback (est: 5-7 nap)
- `ois-validator.so` plugin
- `rollback-trigger.so` plugin
- intent/ ág workflow
- Rollback demo: git merge → push → OIS ellenőrzés → Terraform apply

---

## Demo forgatókönyv — 4 fázis

### 8.1 Fázis: Infrastruktúra felhúzása
**Szükséges:** Sprint 1 + Sprint 2 kész

```
Terraform run → cic-relay workflow
    → terraform-apply.so plugin
    → ProofTraceStep rögzítés
    → state-commit.so plugin
    → state/ commit #1 (infra.tf.json + actual_state.json + prooftrace.json)
```

**Képernyőn látható:** VM-ek megjelennek Proxmox-on, state/ ágon az első commit élőben.

**PoC verzió:** v1 (Sprint 1+2 után)

---

### 8.2 Fázis: Kézi módosítások — drift keletkezése
**Szükséges:** Sprint 3 kész

```
4-5× VyOS szabály módosítás (manuálisan)
    → drift-detector.so plugin (relay-ből triggerelve)
    → SOFT_DRIFT / RECONCILIABLE_DRIFT meghatározás
    → state/ commit #2-#6 (drift: true, új állapot, ProofTrace lánc folytatása)
```

**Képernyőn látható:** state/ ágon pörögnek a commitok, minden kézi módosítás auditált esemény.

**PoC verzió:** v1 (Sprint 3 után)

---

### 8.3 Fázis: Infrastruktúra törlése — Hard Drift
**Szükséges:** Sprint 3 kész

```
Terraform destroy
    → PBS gyökér-hash null állapotba kerül
    → drift-detector.so: HARD_DRIFT detektálás
    → state/ commit: "eltűnés bizonyított"
    → ProofTrace lánc utolsó CommitRef megmarad
```

**Képernyőn látható:** VM-ek eltűnnek, state/ ágon HARD_DRIFT commit.

**PoC verzió:** v1 (Sprint 3 után)

---

### 8.4 Fázis: Visszaállítás — Intent ág + rollback
**Szükséges:** Sprint 4 kész

```bash
git checkout intent/main
git merge state/commit-3-ref
git push origin intent/main
```

```
intent/ push → relay figyeli az ágot
    → ois-validator.so: jogosult a rollback? → OIS policy ellenőrzés
    → rollback-trigger.so: Terraform apply (commit #3 állapot)
    → VM-ek megjelennek
    → ProofTrace: "rollback CommitRef visszautal #3-ra"
```

**Képernyőn látható:** élőben újraépülő infrastruktúra, OIS ellenőrzés eredménye, új ProofTrace.

**PoC verzió:** v1 teljes (Sprint 4 után)

---

## Összefoglaló táblázat

| Demo fázis | Szükséges sprint | Becsült idő | Kritikus plugin |
|---|---|---|---|
| 8.1 Infra felhúzás | S1 + S2 | 2 hét | terraform-apply, state-commit |
| 8.2 Drift keletkezés | S3 | 3 hét | drift-detector |
| 8.3 Hard Drift | S3 | 3 hét | drift-detector |
| 8.4 Rollback | S4 | 4-5 hét | ois-validator, rollback-trigger |

**Teljes PoC v1 → Demo futtatható:** ~5 hét (párhuzamos sprint munkával rövidíthető)

---

## PoC v2 elemek (nem v1 scope)

- Talos cluster, Gitea, Nexus, CloudNativePG, Prom/Grafana
- pki_verify.go bekötése (CICRootCA lánc)
- LocalWorker in-process (3-process isolation)
- WASM iSDK / host frame runtime
- UpstreamSource (relay federáció)
- PBS deduplikált backup
- Két telephely, titkosított kapcsolat (v3)
