# relay-func-audit — Relay Funkcionalitás Audit (javított)

**Audit dátuma:** 2026-06-07 (javítva: 2026-06-07)
**Forrás:** Go forráskód közvetlen olvasása — `grep`, `Read` eszközökkel, nem KB metaadatból
**Relay forráskód:** `${CIC_RELAY_PATH}/`

> **Megjegyzés:** Az első audit verzió hibás volt — a Go fájlok létezéséből következtetett implementálásra
> anélkül hogy a hívási láncot ellenőrizte. Ez a verzió közvetlen forráskód-olvasáson alapul.

---

## Cabinet

**KB referencia:** c365, c781 — Cabinet: schema/module/workflow registry; séma→workflow→modul összerendelés

**Go fájl:** `core/cabinet/service.go` — `Cabinet` interface + `cabinetService`

**Státusz:** implemented

**Lefedettség:**
- `Cabinet` interface: `PutSchema`, `GetSchema`, `PutModule`, `GetModule`, `PutWorkflow`, `GetWorkflow`, `Setx`, `Close`
- In-memory store-ok: `memSchemaStore`, `memModuleStore` (content-addressable, checksum → module), `memWorkflowStore`
- `PutSchema/Module/Workflow`: "Validation is now handled by the constructor" komment — de ez csak strukturális checksum, **nincs aláírás-ellenőrzés**
- `WithRecorder`, `WithObsSinks` functional options

**Kritikus hiány:**
- `PutModule` és `PutSchema` **semmilyen aláírás-ellenőrzést nem végez** — bárki regisztrálhat modult vagy sémát az API-on. Az aláírás-ellenőrzés kizárólag a bootstrap-kori `loadModule`-ban él, és csak akkor, ha `TrustStoreLoaded=true`.

---

## Schema kezelés

**KB referencia:** c927 — `StateRequirement`, `Dependencies`, `NextHops`, `PluginRef`

**Go fájl:** `core/cabinet/types.go`, `schema.go`, `schema_validate.go`, `validate.go`

**Státusz:** scaffold (struktúra implemented, kiértékelés hiányzik)

**Lefedettség:**
- `SchemaDef`: `StateRequirement`, `Dependencies`, `NextHops` mezők definiálva
- `NewSchema()`: `validateAndChecksum` — name/version kötelező, WASM limit, SHA-256 checksum
- `validateInputSchema` / `ValidateSchema`: `$schema` kulcs alapú input validáció

**Hiány (scaffold):**
- `StateRequirement`, `Dependencies`, `NextHops` mezők definiáltak, de a `Setx()` **nem értékeli egyiket sem** — a végrehajtás szigorúan lineáris `Steps` tömb szerint halad
- `PluginRef` mező a `SchemaDef`-ben nem létezik — a modul referencia a workflow step stringben él

---

## Workflow végrehajtás

**KB referencia:** c912 — deklarált gráfot hajt végre; `NextHops` alapján folytat

**Go fájl:** `core/cabinet/cabinet.go:Setx()`, `graph.go`, `workflow.go`

**Státusz:** implemented (lineáris); NextHops/StateRequirement scaffold

**Lefedettség:**
- `Setx()`: workflow resolve → `ParseExecutionGraph` → `executionContext` → step loop → ProofTrace build → recorder
- Native Go dispatch: `reflect`-alapú, szigorú signature ellenőrzéssel
- WASM dispatch: `wasmManager.NewHostInstance` → init/process/get/notify, timeout kezelés

**Hiány (scaffold):**
- `NextHops`-alapú feltételes elágazás nincs
- `StateRequirement` kiértékelés hiányzik
- `Dependencies` cross-workflow ellenőrzés hiányzik

---

## Module rendszer

**KB referencia:** c781 — plugin module metadata; c365 — PutModule/GetModule

**Go fájl:** `core/cabinet/module_descriptor.go`, `stores.go`, `native_components.go`

**Státusz:** implemented (de aláírás-gate nincs — ld. Cabinet)

**Lefedettség:**
- `ModuleDescriptor`: `Meta`, `Type`, `Accepts`, `OutputKeys`, `WasmCode`, `NativeImpl`
- `NewModuleDescriptor()`: WASM canonicalizáció (custom section strip), composite checksum
- Regisztrált natív modulok: `core.test`, `ci.build`, `cic.source.assert`, `cic.schema.build`, `cic.artifact.sign`, `cert.selfsigned`, 4 pipeline modul

---

## Plugin rendszer (WASM)

**KB referencia:** c781 — plugin modules; c912 — pluginokon hívja a műveleteket

**Go fájl:** `core/cabinet/cicwasm.go`

**Státusz:** implemented

**Lefedettség:**
- `WasmManager`: wazero runtime, LRU compiled module cache, WASI support
- `NewHostInstance`: timeout context, library mode
- `CicWasmHost`: Process/Get/Init/Notify — mind `callGuest`-en át
- Git host functions WASM-hoz: `cmd/relay/git_host_funcs.go` — 6 git operáció, JSON ABI

**Hiány:**
- `DefaultMemoryPages` konfigurálható, de `InstantiateModule`-ban nincs alkalmazva (scaffold)

---

## ProofTrace és Verification

**KB referencia:** ProofTrace struct, ChainHash, PoSE, StateCommit

**Go fájl:** `core/cabinet/proof_trace.go`, `cmd/relay/proof_verify.go`

**Státusz:** implemented (generálás); scaffold/concept (ellenőrzés, PoSE)

**Lefedettség — ami ténylegesen fut:**
- `ProofTrace`: `WorkflowID`, `SourceDigest`, `Steps`, `ChainHash`, `Timestamp` — generálódik minden `Setx` hívásban
- `ComputeChainHashV1`: domain-separated SHA-256, per-step input/output hash
- `setHandler`: `resp.Trace.ChainHash` → TraceFrame `chain_anchor` attr (OTel span, nem auditálható gate)

**Lefedettség — ami SOHA NEM HÍVÓDIK production kódban:**
- `VerifyProofArtifact` (`proof_verify.go:53`) — implementálva, de `grep -rn "VerifyProofArtifact" --include="*.go"` (non-test): **nulla találat**. Halott kód production szempontból.
- `ProofArtifactFromTrace` (`proof_verify.go:138`) — szintén soha nem hívódik production kódban.

**Mezők definiálva, de soha nem töltődnek ki:**
- `PoSEResult` — `ProofArtifact` struct-ban definiált, `VerifyProofArtifact` ellenőrzi az értékét, de **production kódban sehol nem kerül kitöltésre** (VERIFIED / DRIFT / SKIPPED értékek)
- `CommitRecord` — szintén definiált, soha nem példányosodik production flow-ban

**Hiány:**
- Vault-aláírt ProofTrace struktúra nincs — a Vault signing csak a recorder Git commiten él
- PoSE protokoll (physical state evidence): **concept** — struktúra és enum definiált, de nincs runtime producer
- A "verification" az originális szándék szerint azt jelenti hogy valaki ellenőrzi a chain_hash-t — erre nincs production flow

---

## Sign/Verify flow — teljes kép

**Go fájl:** `cmd/relay/bootstrap.go:loadModule`, `cmd/relay/pki_bootstrap.go`, `core/modules/schemacompile/schemacompile.go`

**Státusz:** scaffold (CA bundle nélkül teljesen bypass-olható)

### WASM modul betöltés aláírás-ellenőrzése (`bootstrap.go:390–479`)

```
.pem nem létezik         → Warn("module is unsigned")        → modul BETÖLTVE
TrustStoreLoaded=false   → Warn("trust ecosystem not bootstrapped") → modul BETÖLTVE  
TrustStoreLoaded=true + .pem → VerifyCertificateChain()      → elutasítás vagy elfogadás
```

Dev módban (nincs CA bundle, `TrustStoreLoaded=false`) **minden modul betöltődik aláírástól függetlenül**.

### `cic.source.assert` (`schemacompile.go:43–130`)

```go
// bootstrap.go:69–81
var certVerify schemacompile.CertVerifyFunc
if pkiAssets.TrustStoreLoaded {
    certVerify = func(cert *x509.Certificate) error { ... } // valódi ellenőrzés
}
// ha TrustStoreLoaded=false → certVerify = nil

// schemacompile.go:120
if verify != nil {  // nil esetén kihagyva — explicit: "stub mode"
    // cert chain ellenőrzés
}
```

Komment: *"stub mode (no chain verification)"*, *"Layer 1 not yet wired"*.

### `cic.artifact.sign` (`schemacompile.go:198–294`)

- `signer=nil` → `cic_sign = "unavailable"` (nem fatal, nem blokkol)
- `TrustStoreLoaded=false` → `cic_signed_ca = "stub:pending"` (explicit string literal a kódban)

### `PutModule` / `PutSchema` API (`service.go:325–362`)

```go
func (c *cabinetService) PutModule(m *ModuleDescriptor) error {
    c.modules.Put(m)   // aláírás-ellenőrzés nincs
    return nil
}
```

Bootstrap után futásidőben bármi regisztrálható ellenőrzés nélkül.

### `VerifyCertificateChain` tényleges hívási helyek

```
bootstrap.go:78   → cic.source.assert certVerify closure (csak TrustStoreLoaded=true)
bootstrap.go:457  → loadModule PKI verify (csak TrustStoreLoaded=true)
```

Összesen 2 hívási hely, mindkettő az `if TrustStoreLoaded` feltétel mögött.

---

## Nexus: IaC

**Go fájl:** `core/nexus/iac/loader.go`, `source_file.go`, `source_git.go`, `source_upstream.go`, `validator.go`

**Státusz:** implemented

**Lefedettség:**
- `IaCSource` interface + 3 implementáció: `FileSource`, `GitSource`, `UpstreamSource`
- `GitSource`: hardened env (`GIT_CONFIG_NOSYSTEM`, `GIT_TERMINAL_PROMPT`, `core.hooksPath=/dev/null`), per-command timeout
- `Loader`: YAML unmarshal, kind dispatch, graph build, path validáció
- `IaCValidator`: `Cabinet.GetSchema` alapú séma-validáció

---

## Nexus: Git

**Go fájl:** `core/nexus/git/gitops.go`, `registry.go`, `exec_gitops.go`

**Státusz:** implemented

**Lefedettség:**
- `GitOps` interface: Clone/Fetch/Checkout/Commit/Push/Status — mind implementálva
- `RepoRegistry`: repoID→path map, unknown repoID reject
- `ExecGitOps`: hardened env, 1MB output limit, 30s timeout
- WASM host functions: JSON ABI, 6 git operáció

---

## Nexus: Isolation

**Go fájl:** `core/nexus/isolation/coordinator.go`, `worker_local.go`, `worker_subprocess.go`, `ipc.go`

**Státusz:** scaffold — `Coordinator` production kódban NEM BEKÖTÖTT

**Lefedettség:**
- `Worker` interface + `Coordinator.Unwrap()`: 3-lépéses onion unwrap Relay→Module→Host
- `LocalWorker`: in-process decrypt, `CryptoService.Decrypt` hívás
  - Komment: *"In a real implementation, this would run in a separate process with its own identity"*
  - *"In a real scenario, the CryptoService would be configured with a specific key for this worker"*
- `SubprocessWorker`: subprocess spawn, stdin/stdout JSON IPC
- `RunWorkerLoop`: subprocess worker loop

**Kritikus hiány:**
- `NewCoordinator` production kódban **soha nem hívódik** — `grep -rn "NewCoordinator" (non-test, non-isolation/)`: **nulla találat**
- Production kód csak `RunWorkerLoop(context.Background(), os.Stdin, os.Stdout, nil)` hív — **nil crypto service-szel**
- Az onion `Wrap` (titkosítás) oldala nincs megírva — csak `Unwrap` (visszafejtés) létezik
- A `DecryptRequest.KeyID` átadódik IPC-n, de `LocalWorker` figyelmen kívül hagyja

---

## Nexus: Crypto

**Go fájl:** `core/nexus/crypto/service.go`

**Státusz:** implemented (Vault-dependent)

**Lefedettség:**
- `CryptoService` interface: `Sign`, `Decrypt`, `HealthCheck`
- `VaultCryptoService`: Vault Transit engine, env-alapú config
- mTLS és token renewal/lease kezelés: nincs (scaffold)

---

## Nexus: Recorder

**Go fájl:** `core/nexus/recorder/recorder.go`, `workflow_recorder.go`

**Státusz:** implemented (de recorder nil ha Vault nincs)

**Lefedettség:**
- `GitStateRecorder`: manifest hash → Vault sign → git commit → HEAD hash
- `WorkflowRecorder`: `cabinet.ExecutionRecorder` adapter
- `buildRecorderOption`: Vault config → recorder chain; **ha Vault nincs → `WithRecorder(nil)` → recording disabled, non-fatal**

**Hiány:**
- `GitStateRecorder` git parancsai nincsenek hardened-elve (ellentétben az `ExecGitOps`-szal)
- Vault nélkül a teljes ProofTrace audit recording ki van kapcsolva (non-fatal warn)

---

## Nexus: Operator

**Go fájl:** `core/nexus/operator/bootstrap.go`, `watcher.go`, `lifecycle.go`

**Státusz:** implemented (HMAC bootstrap scaffold — explicit komment)

**Lefedettség:**
- `Bootstrapper`: HMAC-SHA256 token, 24h TTL — **explicit scaffold komment** a fájl elején
- `LifecycleManager`: host onboard/offboard, in-memory `HostRegistry`
- `Operator`: event loop, `PollingWatcher` (30s interval), dependency gating
- `CabinetActivator`: `schemaRef → WorkflowID → Cabinet.Setx`

**Wiring (`main.go:518`):**
```go
b := operator.NewBootstrapper([]byte(secret), nil, logger)   // nil recorder!
lm := operator.NewLifecycleManager(b, reg, nil, logger)      // nil recorder!
```
A bootstrap token issuance **nem kerül auditálásra** — a recorder nil.

**Hiány (scaffold):**
- HMAC → PKI leaf cert onboarding: M3 előfeltétel, explicit komment
- `HostRegistry` in-memory: restart esetén elvesznek az állapotok
- Bootstrap audit disabled (nil recorder)

---

## Nexus: Sync

**Go fájl:** `core/nexus/sync/syncer.go`

**Státusz:** scaffold — production kódban NEM BEKÖTÖTT

**Lefedettség:**
- `GitSyncer.SyncDaily`: cache branch → squash merge → commit → push → prune

**Kritikus hiány:**
- `NewGitSyncer` production kódban **soha nem hívódik** — nincs scheduler, nincs wiring
- `runGit` nincs hardened-elve (nincs `GIT_CONFIG_NOSYSTEM` stb.)

---

## Relay entrypoint és handler-ek

**Go fájl:** `cmd/relay/main.go`, `middleware.go`, `pki_bootstrap.go`

**Státusz:** implemented (részlegesen scaffold)

**Lefedettség:**
- HTTP server, routes, rate limiter, concurrent cap
- `setHandler`, `compileHandler`, `pipelineHandler`
- PKI bootstrap: `loadPKIAssets`, `TrustStoreLoaded` flag
- `buildRecorderOption`, `buildOperatorIfConfigured`

**Hiány (scaffold/concept):**
- `TrustModeProd = "prod" // scaffold: CICPlatformCA not embedded` — explicit komment
- `readyzHandler`: identikus a `healthzHandler`-rel — "For now, readiness is the same as liveness" komment, dependency check nincs
- Metrics scrape endpoint (Prometheus/OTel) nincs

---

## Pkg: Merkle, Obs

**Státusz:** implemented — ezek valóban teljesek, production kódban bekötöttek.

- `pkg/merkle`: `LeafHash`, `HexMerkleRoot`, `BuildVerificationRoot`, `BuildContext`
- `pkg/obs`: `LogSink`/`MetricSink`/`TraceSink`, `LogrusSink`, `ChainSink`, `CaptureSink`
