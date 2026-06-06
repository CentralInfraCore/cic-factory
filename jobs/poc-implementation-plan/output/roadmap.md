# CIC/Relay PoC Megvalósítási Roadmap

## Áttekintés

Ez a dokumentum a CIC/Relay PoC és Demonstráció megvalósítási tervét tartalmazza, a KB-alapú komponens státusz felmérés és az `add.md` specifikáció alapján.

A roadmap három PoC fázisra és egy demo forgatókönyvre tagolódik. Minden állítás KB-bizonyítékkal alátámasztott (részletek: `status-matrix.md`).

---

## Kiindulópont — Jelenlegi állapot

**Erős magalap (implemented, CI zöld):**
- ProofTrace core (hash-lánc, SourceDigest, canonical JSON)
- Vault Transit signing wrapper (`VaultCryptoService`, `make dev-vault`)
- Schema validator (`ValidateSchema`, per-step Setx check)
- Git-alapú Recorder (expected+actual state + Vault aláírás)
- ExecutionGraph (lineáris, névvel ellátott lépések)
- WASM modul futtatás (LRU cache, timeout, ABI)
- Observability layer (TraceFrame, CounterPoint, LogRecord)

**Szándékos scaffold (előfeltételhez kötött, PoC v1-ben nem kell aktiválni):**
- PKI enforce (`pki_verify.go`) — CA lánc bootstrap előfeltétel
- UpstreamSource — relay federáció v2 előfeltétel
- LocalWorker in-process — 3-process isolation előfeltétel

**Hiányzó, implementálandó (concept → implementált bridge):**
- OIS policy check engine
- Drift detection automatizmus (SOFT/RECONCILIABLE/HARD)
- IaC state branch automatikus git commit
- Terraform IaC szkeletonok (Proxmox provider)
- Demo szkriptek (drift trigger, rollback, live display)

---

## PoC v1 — Lokális bizonyítási kör

**Stack:** Proxmox + VyOS + Bastion + Vault(mem) + CIC-Relay

**Cél:** Az `add.md` demo forgatókönyv futtatásához szükséges minimális, de valódi CIC bizonyítási lánc.

### Hiányzó komponensek

| Komponens | Jelenlegi státusz | Szükséges munka |
|---|---|---|
| Terraform Proxmox IaC | concept | Szkeletonok: `relay.tf`, `vyos.tf`, `bastion.tf`, `vault.tf` |
| IaC state branch automata | concept | Git commit hook/script: desired+actual+prooftrace.json → `state/` ág |
| Drift detection script | concept | Polling loop: PBS snapshot vs ProofTrace utolsó hash összehasonlítás |
| OIS policy check (egyszerűsített) | concept | Minimális: intent+obligation ellenőrzés (YAML policy fájl alapján) |
| Demo drift trigger | nincs | Shell script: kézi módosítások szimulálása (szabály felülírás, stb.) |
| Demo rollback script | nincs | `git merge state/<ref> → intent/main` + Terraform apply |
| Live display (terminal) | nincs | `watch` + `git log --oneline state/` megjelenítés |
| Vault in-memory bootstrap | implemented | `make dev-vault` — kész, csak futtatni kell |
| Relay build + run | implemented | `make build && ./output/<commit>/cic-relay` — kész |

### Scaffold elemek amelyek implementációt igényelnek

**IaC Loader (M11 scaffold → implementálandó):**
- `IaCLoader` + `FileSource` vázak megvannak
- Szükséges: `FileSource` teljes implementáció (rekurzív YAML olvasás, `Relay/Host/Service` gráf építés)
- Ez adja a Relay "desired state" inputját a Terraform outputból

**Recorder → state/ ág bridge:**
- A `recorder.go` git commitot ír az audit repóba
- Szükséges: Recorder kiterjesztés vagy külön script, amely a `state/` ágba írja a ProofTrace-t

### Kritikus út (dependency sorrendben)

```
1. Terraform Proxmox szkeletonok
   ↓
2. IaC FileSource implementáció (Relay beolvassa a Terraform outputot)
   ↓
3. Vault dev-vault bootstrap (make dev-vault)
   ↓
4. Relay build + futtatás (make build)
   ↓
5. Recorder → state/ ág bridge (automatikus git commit)
   ↓
6. Drift detection script (polling loop)
   ↓
7. OIS policy check (egyszerűsített YAML alapú)
   ↓
8. Demo drift trigger + rollback szkriptek
   ↓
9. Live display (terminal watch)
```

### Komplexitás becslés

| Terület | Becsült munka | Megjegyzés |
|---|---|---|
| Terraform Proxmox IaC | 3–5 nap | VyOS, Bastion, Vault VM + hálózat |
| IaC FileSource (M11 befejezés) | 2–3 nap | Részben scaffold megvan |
| Recorder → state/ ág bridge | 1–2 nap | Recorder kész, csak routing kell |
| Drift detection script | 2–3 nap | Concept → egyszerű polling loop |
| OIS policy check (egyszerűsített) | 2–3 nap | YAML policy + intent/obligation check |
| Demo szkriptek | 2–3 nap | Trigger, rollback, live display |
| Integráció + teszt | 3–5 nap | End-to-end próba |
| **Összesen** | **~15–24 nap** | 1 developer, parallel részfeladatokkal |

---

## PoC v2 — Menedzselt, megfigyelhető környezet

**Stack:** v1 + Talos cluster + Gitea + Nexus + CloudNativePG + Prometheus/Grafana

**Cél:** CIC ökoszisztéma menedzselt, dokumentált, megfigyelhető változata.

### Mi épül v1-re

| Komponens | Függ v1-től | Párhuzamos v1-gyel |
|---|---|---|
| Talos k8s cluster | Igen — Proxmox IaC szkeletonok kiterjesztése | Terraform modulok bővítése |
| Gitea (git hosting) | Igen — state/ ág hosting | Gitea deploy párhuzamos lehet |
| Nexus (artifact registry) | Nem közvetlen | Párhuzamos Gitea-val |
| CloudNativePG | Igen — Talos cluster megléte | |
| Prometheus + Grafana | Igen — Relay observability layer wiring | ObsLayer v1-ben implemented |

### Architektúrális elvek

- A Relay observability layer (TraceFrame, CounterPoint) → Prometheus metrikák exportálása
- ProofTrace chain → Gitea-ba kerül (state/ ág), nem lokális git
- Nexus: WASM modulok és schema artifact-ok tárolása
- CloudNativePG: audit log perzisztencia (a recorder Git-alapú, de DB-re átírható)

---

## PoC v3 — Elosztott, redundáns bizonyítási architektúra

**Stack:** v2 + két telephely + k8s federáció + titkosított link

**Architektúrális elvek (csak elvszintű, implementáció v2 után):**

- Két Proxmox cluster (vagy Proxmox + OCI) — két telephely
- VyOS titkosított tunnel (IPsec/WireGuard) a helyszínek között
- Relay federáció: `UpstreamSource` (jelenleg scaffold) → v3-ban aktiválható (relay federáció v2 előfeltétel teljesül)
- PKI enforce (`pki_verify.go` scaffold) → v3-ban aktiválható (CICRootCA → Intermediate CA → leaf cert bootstrap)
- Quorum döntési réteg (concept v1/v2) → v3 potenciális implementáció terület
- ProofTrace chain cross-site szinkronizáció: `core/nexus/sync/syncer` (implementált, nem bekötve)

---

## Demo Forgatókönyv — 4 fázis

Az `add.md` szerinti demonstráció. **Futtatható: PoC v1 teljes befejezése után.**

### Szükséges demo-specifikus komponensek

| Komponens | Szükséges fázishoz | Státusz |
|---|---|---|
| `demo/terraform/` szkeletonok | 8.1 Fázis | concept → poc-iac-terraform-01 |
| `demo/scripts/drift-trigger.sh` | 8.2 Fázis | nincs → poc-demo-scripts-01 |
| Automatikus state/ ág commit | 8.1–8.3 Fázis | concept → poc-relay-wiring-01 |
| Drift detection (SOFT/RECONCILIABLE/HARD) | 8.2–8.3 Fázis | concept → poc-drift-engine-01 |
| `demo/scripts/rollback.sh` | 8.4 Fázis | nincs → poc-demo-scripts-01 |
| Live display (terminal) | Összes fázis | nincs → poc-demo-scripts-01 |
| OIS-ellenőrzés (rollback policy) | 8.4 Fázis | concept → poc-ois-policy-01 |

### Fázis-időrend

**8.1 — Terraform up:**
```
Terraform apply → CIC ProofTrace #1 → state/ commit #1
  ├── infra.tf.json (desired state)
  ├── actual_state.json (PBS snapshot)
  └── prooftrace.json (hash, aláírás)
```
Szükséges: poc-iac-terraform-01 + poc-relay-wiring-01

**8.2 — Drift (4–5 kézi módosítás):**
```
drift-trigger.sh → CIC drift észlel → SOFT_DRIFT / RECONCILIABLE_DRIFT
→ state/ commit #2–#6 (drift: true, actual_state frissül)
```
Szükséges: poc-drift-engine-01 + poc-demo-scripts-01

**8.3 — Hard Drift (infra törlés):**
```
Terraform destroy → PBS null state → HARD_DRIFT rögzítve
→ state/ commit #7 (hard_drift: true)
```
Szükséges: poc-drift-engine-01

**8.4 — Rollback:**
```
rollback.sh state/commit-3-ref → intent/ ág merge
→ OIS-ellenőrzés (policy: ALLOWED) → Terraform apply
→ Infra újjáépül → Új ProofTrace (visszautal #3-ra)
```
Szükséges: poc-ois-policy-01 + poc-demo-scripts-01

### Demo futtathatóság feltétele

A teljes 4 fázisú demo **PoC v1 összes sub-job lezárása után** futtatható:
- poc-relay-wiring-01 ✓ done
- poc-drift-engine-01 ✓ done
- poc-iac-terraform-01 ✓ done
- poc-ois-policy-01 ✓ done
- poc-demo-scripts-01 ✓ done

---

## Összefoglaló ütemterv

```
Sprint 1 (1–2 hét): Alap bekötések
  poc-relay-wiring-01: IaC FileSource + state/ ág bridge

Sprint 2 (1–2 hét): Infra szkeletonok
  poc-iac-terraform-01: Proxmox IaC + provider modulok

Sprint 3 (1–2 hét): Drift + OIS
  poc-drift-engine-01: Drift detection engine
  poc-ois-policy-01: OIS policy check (egyszerűsített)

Sprint 4 (1 hét): Demo összerakás
  poc-demo-scripts-01: trigger, rollback, live display

Sprint 5 (1 hét): Integráció + end-to-end demo futtatás

→ PoC v1 + Demo kész: ~5–7 hét (1 developer)
```
