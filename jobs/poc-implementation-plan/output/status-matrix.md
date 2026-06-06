# Komponens Státusz Mátrix — PoC v1 Komponensek

KB bizonyítékok alapján összeállítva. Minden státuszállítás node- vagy file-szintű forrással alátámasztott.

---

## Összefoglaló táblázat

| Komponens | Státusz | KB forrás | Megjegyzés |
|---|---|---|---|
| ProofTrace core | **implemented** | `c349`, `c880`, `c13`, ROADMAP_archive M3/M17 Done | Per-step hash, chain_hash, SourceDigest, canonical JSON — kódban él, tesztek fedik |
| Vault Transit signing (dev) | **implemented** | `c479`, `c130`, ROADMAP_archive M13 Done | `make dev-vault` bootstrap; `VaultCryptoService`; VAULT_TOKEN hiánya WARN+nil |
| Schema validator (Setx) | **implemented** | `c358`, `c13`, PROMPTMAP task `schema-validation-setx` Done | `ValidateSchema`, `validateInputSchema`, per-step schema check a `Setx`-ben |
| Recorder (Git audit) | **implemented** | `c13` (`recorder.go`), PROMPTMAP `setx-recorder-wire` + `prod-recorder-wiring` Done | Git-alapú expected+actual JSON + Vault aláírás; Vault nélkül WARN |
| ExecutionGraph (lineáris) | **implemented** | `c13` (`graph.go`), PROMPTMAP `execution-graph-linear` Done | Névvel ellátott lépések, DAG-szerű bekötés |
| WASM modul futtatás | **implemented** | `c13` (`cicwasm.go`), PROMPTMAP `wasm-exec-timeout` Done | LRU cache, singleflight, timeout, Call/allocate/deallocate ABI |
| Canonical JSON | **implemented** | `c13` (`canonicaljson.go`) | Determinisztikus hash-elés alapja |
| Observability Layer (Relay wiring) | **implemented** | ROADMAP_archive M22.6 Done | TraceFrame, CounterPoint, LogRecord, CaptureSink |
| PKI enforce (`pki_verify.go`) | **scaffold** | `c10`, `c38` | X.509 chain verify kész; CA lánc (CICRootCA→Intermediate→leaf) nem bootstrapped — szándékos előfeltétel |
| UpstreamSource (HTTP IaC) | **scaffold** | `c65`, `c984` M11 | relay federáció v2 előfeltétel; `FileSource` és `UpstreamSource` váz megvan |
| LocalWorker in-process | **scaffold** | `c65` | 3-process isolation + Vault előfeltétel |
| IaC Loader / Nexus IaC | **scaffold** | `c984` M11 (checklist: [ ] markerek) | `IaCLoader`, `FileSource` / `UpstreamSource`; gráfépítő logika elkezdve, nem bekötve |
| Nexus iac/operator/sync/isolation | **implementált de nem bekötve** | `c38` ("implementált de nem bekötve") | Kód megvan, `cmd/relay/main.go`-ban nem aktív |
| OIS (OpenIntentSign) | **concept** | `c2836`, `c2498` | Formális modell dokumentált; nincs runtime implementáció (`OIS()` függvény nem él a relay kódbázisban) |
| Drift detection engine | **concept** | `c1815`, `c1747` | Kategorizálás (SOFT/RECONCILIABLE/HARD drift) dokumentált; automatikus észlelő engine nincs implementálva |
| IaC state branch (git commit) | **concept** | `add.md` spec, `c1112` | `state/` ág automatikus commit leírva a specben; runtime nincs |
| PoSE (Proof of State Existence) | **concept** | `c2587` | Híd-koncepció ProofTrace↔PBS között; nincs runtime megfelelő |
| PBS (Physical Backup Snapshot) | **concept** | `c2587` | Fizikai állapot rögzítési réteg; nincs implementáció |
| Terraform integráció | **concept** | `add.md` spec | Terraform → CIC trigger leírva; nincs IaC szkeletonok vagy provider integráció |
| Quorum döntési réteg | **concept** | `c65`, `c10` | Nincs runtime megfelelő |
| CICmeta protocol | **concept** | `c65` | Nincs élő bridge a Relay runtime-hoz |

---

## Részletes státusz — kulcs komponensek

### ProofTrace core — **implemented**

- Forrás: `CIC-Relay/core/cabinet/proof_trace.yaml` (node n349, n348)
- `ProofTrace` struct: determinisztikus, clock-mentes, SourceDigest anchored
- `ProofTraceStep`: per-step kriptográfiai fingerprint
- M3 (proof-trace-type), M17 (Source-Pinned ProofTrace): ROADMAP_archive-ban Done
- Canonical JSON: `pkg/canonicaljson/canonicaljson.go` implemented
- **Bridge állapota**: teljes — ProofTrace concept → code → runtime → audit lánc zárt

### Vault Transit signing — **implemented**

- Forrás: `CIC-Relay/core/nexus/crypto/service.go` (node n479)
- `VaultCryptoService`: HashiCorp Vault Transit engine wrapper
- M13 Done: `make dev-vault`; `buildRecorderOption` a main-ben; VAULT_TOKEN hiánya WARN+nil recorder
- In-memory dev Vault: `vault` bináris kell (host-oldalon), token: `dev-root-token`, cím: `http://127.0.0.1:18200`
- **PoC v1 számára**: dev-vault elegendő; produkciós Vault külön telepítés

### Schema validator — **implemented**

- Forrás: `CIC-Relay/core/cabinet/schema_validate.yaml` (node n358)
- `ValidateSchema` + `validateInputSchema`: per-step schema check
- Schema store: `SchemaStore`/`WorkflowStore` CAS-alapú, thread-safe
- **Bridge állapota**: teljes

### Recorder (Git audit) — **implemented**

- Forrás: `CIC-Relay/core/nexus/recorder/recorder.go` (node c13)
- Git-alapú: expected+actual JSON + Vault aláírás → commit
- Prod wiring kész: `cmd/relay/main.go` env-ből olvassa a Vault konfigot
- **Bridge állapota**: teljes — de IaC `state/` ágba való automatikus commit nincs (concept)

### PKI enforce — **scaffold**

- Forrás: `CIC-Relay/core/cabinet/pki_verify.go` (node c13, c10)
- X.509 chain verify + CRL + SPKI pinning kód létezik
- **Előfeltétel**: CICRootCA → Intermediate CA → leaf cert bootstrap
- PoC v1-hez: nem blokkoló — dev-vault HMAC alapú aláírással dolgozhat

### OIS — **concept**

- Formális modell: `OIS(actor, action, context)` → intent + obligation check → ProofTrace
- OpenIntentSign repo: README és elvek dokumentáltak (node c2836)
- **Implementációs híd megszakad**: nincs `ois.Check()` függvény a relay kódbázisban
- Demo szempontjából: az "OIS-ellenőrzés" jelenleg manuális policy döntés

### Drift detection — **concept**

- Taxonómia dokumentált: Chain Drift (logikai réteg) / State Drift (fizikai réteg)
- 3 típus: SOFT_DRIFT, RECONCILIABLE_DRIFT, HARD_DRIFT — dokumentált
- **Implementációs híd megszakad**: automatikus észlelő engine nincs, nincs polling loop
- Demo szempontjából: drift manuálisan "kiváltható" + manuálisan rögzíthető

### IaC state branch — **concept**

- Elv: `state/` ág automatikus commit (desired + actual + prooftrace.json)
- IaC ontológia dokumentált: graph-alapú, Desired/Actual State szétválasztás
- **Implementációs híd megszakad**: nincs a relay-ben automatikus git commit az IaC repóba
- IaC Loader (M11) scaffold állapotban — `FileSource`/`UpstreamSource` vázak

### Terraform integráció — **concept**

- Spec (`add.md`): Terraform up → ProofTrace #1, drift → commit, rollback → `git merge state/ref → intent/main`
- **Implementációs híd megszakad**: nincs Terraform provider/hook, nincs IaC szkeletonok
- Teljes implementáció szükséges a demo futtatáshoz

---

## Összesített értékelés

**Erős alap (implemented):** ProofTrace lánc, Vault aláírás, Schema validáció, Recorder, WASM futtatás, Observability

**Szándékos scaffold (előfeltételhez kötött):** PKI enforce (CA lánc), UpstreamSource (federáció), LocalWorker (process isolation)

**PoC-hoz implementálandó (concept → code):** OIS policy check, Drift detection engine, IaC state branch automata, Terraform integráció
