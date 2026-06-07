# relay-func-audit — Gap Summary (javított)

**Audit dátuma:** 2026-06-07 (javítva: 2026-06-07)
**Forrás:** Go forráskód közvetlen olvasása — grep + Read eszközökkel

> **Fontos:** Az első verzió hibás volt. Az agent Go fájlok *létezéséből* következtetett
> "implemented" státuszra, anélkül hogy a hívási láncot ellenőrizte volna.
> Ez a verzió a tényleges production hívási láncon alapul.

---

## Implemented — ténylegesen fut production kódban

| Komponens | Go csomag | Megjegyzés |
|---|---|---|
| `Cabinet` interface + stores | `core/cabinet/service.go`, `stores.go` | teljes CRUD, in-memory |
| `Setx` lineáris workflow | `core/cabinet/cabinet.go` | native + WASM dispatch |
| `ParseExecutionGraph` | `core/cabinet/graph.go` | két formátum |
| WASM Manager (wazero) | `core/cabinet/cicwasm.go` | LRU, singleflight, timeout |
| ProofTrace generálás | `core/cabinet/proof_trace.go` | ChainHash, per-step hash |
| Schema checksum + input validate | `core/cabinet/validate.go`, `schema_validate.go` | strukturális, nem kriptográfiai |
| PKI cert chain verify (feltételes) | `core/cabinet/pki_verify.go` | CSAK `TrustStoreLoaded=true` esetén |
| Natív modulok (5+4) | `core/modules/` | cert.selfsigned, ci.build, schemacompile, schemapipeline |
| Vault crypto service | `core/nexus/crypto/service.go` | Sign + Decrypt + HealthCheck |
| Git state recorder | `core/nexus/recorder/recorder.go` | Vault sign + git commit |
| GitOps + ExecGitOps | `core/nexus/git/` | 6 operáció, hardened env |
| IaC Loader + 3 forrás | `core/nexus/iac/` | File, Git, Upstream |
| IaCValidator | `core/nexus/iac/validator.go` | Cabinet.GetSchema alapú |
| Operator + PollingWatcher | `core/nexus/operator/watcher.go` | 30s polling, event loop |
| LifecycleManager | `core/nexus/operator/lifecycle.go` | onboard/offboard, in-memory |
| Bootstrapper (HMAC) | `core/nexus/operator/bootstrap.go` | scaffold comment-tel |
| CabinetActivator | `cmd/relay/activator.go` | schemaRef → Setx |
| HTTP server + middleware | `cmd/relay/main.go`, `middleware.go` | rate limit, concurrent cap |
| Merkle provenance | `pkg/merkle/` | LeafHash, VerificationManifest |
| Observability sinks | `pkg/obs/` | LogSink, MetricSink, TraceSink |

---

## Scaffold — kódban van, de nem bekötött vagy feltételhez kötött

| Komponens | Hol | Probléma / Előfeltétel |
|---|---|---|
| PKI signing enforcement | `bootstrap.go:loadModule` | `TrustStoreLoaded=false` → unsigned modul warning-gal BETÖLTVE (nem rejected) |
| `cic.source.assert` cert verify | `schemacompile.go:120` | `certVerify=nil` dev módban → `if verify != nil` kihagyva, explicit "stub mode" komment |
| `cic.artifact.sign` output | `schemacompile.go:285` | `cic_sign="unavailable"`, `cic_signed_ca="stub:pending"` Vault/CA nélkül |
| `PutModule`/`PutSchema` signing gate | `service.go:325–362` | nulla ellenőrzés — bárki regisztrálhat futásidőben |
| `StateRequirement`/`NextHops` eval | `cabinet.go:Setx` | mezők definiálva, `Setx` nem értékeli |
| `GitSyncer` | `core/nexus/sync/syncer.go` | `NewGitSyncer` **soha nem hívódik** production kódban |
| `isolation.Coordinator` | `core/nexus/isolation/coordinator.go` | `NewCoordinator` **soha nem hívódik** production kódban; production csak `RunWorkerLoop(…, nil)` |
| Onion encryption `Wrap` oldala | `coordinator.go` | csak `Unwrap` (decrypt) létezik; `Wrap` (multi-layer encrypt) nincs megírva |
| `LocalWorker` process identity | `worker_local.go` | "In a real implementation, this would run in a separate process" — valójában host process-ben fut |
| PKI M3 bootstrap | `operator/bootstrap.go` | explicit: "PKI integration awaits M3 bootstrap" |
| `prod` trust mode | `pki_bootstrap.go:15` | explicit scaffold comment: "CICPlatformCA not embedded" |
| ProofTrace Vault signature | `proof_trace.go` | Vault signing csak a Git commiten, nem magán a trace struktúrán |
| `readyzHandler` | `main.go:220` | "For now, readiness is the same as liveness" — nincs dependency check |
| Bootstrap audit recording | `main.go:518` | `NewBootstrapper(secret, nil, logger)` — nil recorder, token issuance nem auditált |
| Vault TLS / token renewal | `crypto/service.go` | nincs mTLS konfig, nincs lease renewal |
| WASM memory limit | `cicwasm.go` | `DefaultMemoryPages` konfigurálható, `InstantiateModule`-ban nem alkalmazott |

---

## Concept — KB-ban vagy struktúrában definiált, de nincs runtime producer

| Komponens | Hol definiált | Miért concept |
|---|---|---|
| `VerifyProofArtifact` | `cmd/relay/proof_verify.go:53` | Implementálva, de **production kódban soha nem hívódik** — `grep` nulla találat (non-test) |
| `ProofArtifactFromTrace` | `cmd/relay/proof_verify.go:138` | Szintén soha nem hívódik production kódban |
| `PoSEResult` mező | `ProofArtifact` struct | Definiált és validált, de **sehol nem töltődik ki** production flow-ban |
| `CommitRecord` mező | `ProofArtifact` struct | Definiált, de sehol nem példányosodik production kódban |
| PoSE protokoll (VERIFIED/DRIFT/SKIPPED) | `proof_verify.go:108` | Enum és validáció kész, nincs aki feltöltse |
| Multi-relay koordináció | — | Nincs Go megfelelő |
| Prometheus/OTel scrape endpoint | — | Metrikák emittálódnak logrusba, HTTP endpoint nincs |
| Párhuzamos workflow step | — | Csak lineáris `Steps` tömb |
| `.so` plugin modell | — | Tudatosan WASM váltotta ki |

---

## A sign/verify flow valódi állapota

```
Elvárt (KB alapján):          Tényleges (Go forráskód alapján):
─────────────────────         ─────────────────────────────────
modul betöltés → verify  →   warning + betölt (TrustStoreLoaded=false esetén)
assert → cert chain      →   nil verifier → kihagyva (dev módban)
artifact.sign → Vault    →   "unavailable" (Vault nélkül)
ProofArtifact → verify   →   VerifyProofArtifact soha nem hívódik
PoSE result              →   mező definiált, soha nem töltődik ki
commit → Vault sign      →   recorder nil ha Vault nincs → recording disabled
```

**Az egyetlen ténylegesen futó sign/verify:**
- `GitStateRecorder`: Vault Transit sign → manifest + git commit — **de csak ha Vault be van állítva**
- `VerifyCertificateChain` a bootstrap `loadModule`-ban — **de csak ha van CA bundle**

---

## PoC-hoz szükséges elemek státusza

| Elem | Státusz | PoC hatás |
|---|---|---|
| Lineáris workflow végrehajtás | implemented | PoC-ra elegendő |
| WASM modul futtatás | implemented | PoC-ra elegendő |
| ProofTrace generálás | implemented | ChainHash megvan |
| PKI enforce | scaffold | dev módban bypass — PoC-ban elfogadható |
| PoSE verifiction | concept | PoC-t blokkolhatja ha elvárt |
| ProofTrace auditálható verify | concept | `VerifyProofArtifact` soha nem hívódik — **PoC-ban gap** |
| StateRequirement/NextHops | scaffold | lineáris workflow PoC-ra elegendő |
| GitSyncer | scaffold | PoC-ban nem kritikus |
| Isolation Coordinator | scaffold | PoC-ban nem kritikus |
