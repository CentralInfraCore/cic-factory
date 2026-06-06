# Sub-job-ok Áttekintése

A `poc-implementation-plan` szülő job által létrehozott sub-job specifikációk listája.

---

## Létrehozott sub-job-ok

| Job ID | Célrepo | Terület | Státusz | Szülő |
|---|---|---|---|---|
| `poc-relay-wiring-01` | CIC-Relay | IaC FileSource + state/ ág bridge | pending | poc-implementation-plan |
| `poc-drift-engine-01` | CIC-Relay | Drift detection engine | pending | poc-implementation-plan |
| `poc-iac-terraform-01` | cic-factory | Terraform IaC szkeletonok (Proxmox) | pending | poc-implementation-plan |
| `poc-ois-policy-01` | CIC-Relay | OIS policy check (egyszerűsített) | pending | poc-implementation-plan |
| `poc-demo-scripts-01` | cic-factory | Demo forgatókönyv szkriptek | pending | poc-implementation-plan |

---

## Részletes leírások

### `poc-relay-wiring-01` — Relay → ProofTrace bekötés és state/ ág bridge

**Cél:** A CIC-Relay scaffold elemek befejezése és a PoC state/ ág automatikus commit bridge megvalósítása.

**Miért szükséges:** A KB szerint a `core/nexus/iac` M11 mérföldkő scaffold állapotban van (`FileSource`/`UpstreamSource` vázak), és a `recorder.go` jelenleg az audit repóba commitol, nem az IaC `state/` ágba. A demo 8.1 fázisa ezt a kettős bekötést igényli.

**Fő deliverable-ek:**
- `IaCLoader` + `FileSource` teljes implementáció
- `GitStateWriter`: desired+actual+prooftrace.json → `state/` ág commit
- `CIC_STATE_REPO_PATH` env dokumentálva

**Dependency:** Blokkol minden más sub-jobot (state/ ág alapja mindennek)

**Branch:** `feature/poc-relay-wiring-01`

---

### `poc-drift-engine-01` — Drift Detection implementáció

**Cél:** A SOFT_DRIFT / RECONCILIABLE_DRIFT / HARD_DRIFT taxonómia automatikus detekciós motorjának megvalósítása.

**Miért szükséges:** A KB szerint a drift taxonómia concept szinten dokumentált, de automatikus észlelő engine nincs. A demo 8.2 (kézi módosítások) és 8.3 (infra törlés) fázisai valós időben igényelnek drift észlelést és state/ commit triggert.

**Fő deliverable-ek:**
- `DriftDetector` interface + `ComparatorDetector` implementáció
- `DriftWriter`: drift event → state/ ág commit
- `GET /drift/status` HTTP endpoint
- Egységtesztek (NONE, SOFT, HARD esetekre)

**Dependency:** `poc-relay-wiring-01` (state/ ág bridge)

**Branch:** `feature/poc-drift-engine-01`

---

### `poc-iac-terraform-01` — Terraform IaC szkeletonok

**Cél:** Proxmox-alapú Terraform IaC modulok és CIC IaC YAML leírások megvalósítása a PoC v1 stackhez (VyOS, Bastion, Vault, Relay VM-ek).

**Miért szükséges:** Nincs egyetlen Terraform fájl sem a CIC kódbázisban. A demo 8.1 és 8.4 fázisa (`terraform apply`, `terraform destroy`) teljes Terraform integrációt igényel.

**Fő deliverable-ek:**
- `output/terraform/` — Proxmox provider modulok (vyos, bastion, vault, relay)
- `output/cic-iac/` — CIC IaC YAML leírások (`apiVersion: cic/v1`)
- `modules/oci/` placeholder (v2+ IaC abstraction)
- `terraform validate` hibamentes

**Dependency:** Független (párhuzamos poc-relay-wiring-01-gyel)

**Branch:** `feature/poc-iac-terraform-01`

---

### `poc-ois-policy-01` — OIS Policy Check (egyszerűsített PoC)

**Cél:** Az OpenIntentSign formális modell egyszerűsített runtime implementációja: YAML policy fájl alapú intent+obligation ellenőrzés, a rollback engedélyezéséhez szükséges.

**Miért szükséges:** A KB szerint az OIS concept szinten dokumentált (formális modell, elvek), de nincs `ois.Check()` a relay kódbázisban. A demo 8.4 fázisa (Rollback) OIS-ellenőrzést igényel a `intent/main` ágra való push előtt.

**Fő deliverable-ek:**
- `OISChecker` interface + `PolicyFileChecker` implementáció
- `config/ois-policy.yaml` — PoC policy szabályok
- `POST /ois/check` HTTP endpoint
- OIS döntés integráció a ProofTrace-be

**Dependency:** `poc-relay-wiring-01` (ProofTrace bekötés)

**Branch:** `feature/poc-ois-policy-01`

---

### `poc-demo-scripts-01` — Demo Forgatókönyv Szkriptek

**Cél:** A 4 fázisú CIC/Relay PoC demo futtatásához szükséges shell szkriptek, live terminal display és koordinátor script megvalósítása.

**Miért szükséges:** A demo forgatókönyv (add.md 8.1–8.4) kézi lépéseit automatizálni kell a hiteles, reprodukálható bemutatóhoz. A szkriptek az összes többi sub-job API-jaira épülnek.

**Fő deliverable-ek:**
- `01-terraform-up.sh` — Terraform apply + ProofTrace trigger
- `02-drift-trigger.sh` — 4–5 kézi módosítás szimulálása
- `03-infra-destroy.sh` — Terraform destroy + HARD_DRIFT
- `04-rollback.sh` — OIS check + git merge + Terraform apply
- `live-display.sh` — Terminál live display (state/ log + drift status)
- `demo-run-all.sh` — Koordinátor (interaktív és automatikus mód)

**Dependency:** MINDEN más sub-job (`poc-relay-wiring-01`, `poc-drift-engine-01`, `poc-iac-terraform-01`, `poc-ois-policy-01`)

**Branch:** `feature/poc-demo-scripts-01`

---

## Futtatási sorrend

```
Párhuzamos sprint 1:
  poc-relay-wiring-01    (blokkol mindent)
  poc-iac-terraform-01   (független)

Sprint 2 (poc-relay-wiring-01 után):
  poc-drift-engine-01
  poc-ois-policy-01

Sprint 3 (mind kész):
  poc-demo-scripts-01

→ Demo futtatható
```

---

## Nem létrehozott sub-job-ok — indoklás

| Terület | Döntés | Indok |
|---|---|---|
| PKI / CA bootstrap | Nem hozva létre | scaffold, nem blokkolja a PoC-t — `dev-vault` HMAC elegendő |
| UpstreamSource | Nem hozva létre | relay federáció v2 előfeltétel, PoC v3 terület |
| PBS implementáció | Nem hozva létre | Terraform state output mint "actual state" elegendő PoC-hoz |
| Quorum réteg | Nem hozva létre | concept, PoC v3 terület |
| CICmeta protocol | Nem hozva létre | concept, nincs relay runtime bridge |
| Talos / Gitea / Nexus | Nem hozva létre | PoC v2 területek — v1 after |
