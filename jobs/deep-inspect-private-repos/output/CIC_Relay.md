# CIC_Relay — Részletes Feltárás

**Dátum:** 2026-06-06
**Lokális elérési út:** `${CIC_RELAY_PATH}`
**Remote URL:** `git@github.com:CentralInfraCore/CIC_Relay.git`
**Aktív branch:** `devel` (párhuzamosan: `d/feature-007`, `main`)
**Go modul neve:** `centralrelay`

---

## Státusz

**Aktív fejlesztés.** Sprint 13 lezárva (M35 Done). A `devel` branch az aktuális fejlesztési ág; a `main` branch a stabil release pont. Az utolsó commit: `chore: add go.meta companion YAML for all Go source files`.

---

## Könyvtárstruktúra (3 szint)

```
CIC-Relay/
  ai/                  — AI context: SYSTEM_CONTEXT.md, ROADMAP.md, PROMPTMAP.yaml, ONBOARDING.md, LLM_LOCK.md, LLM_RULES.md
  api_tests/           — smoke.sh: E2E smoke tesztek futó relay ellen
  cmd/
    relay/             — HTTP API entry point, bootstrap, PKI
      main.go          — fő belépési pont (HTTP :8080 + --mode=module-worker)
      bootstrap.go     — PKI asset betöltés, embedded komponens regisztráció
      activator.go     — CabinetActivator (Operator → Cabinet bridge)
      middleware.go    — Rate limiter, concurrent cap
      compile_handler.go — /v1/schema/compile HTTP handler
      pki_bootstrap.go — PKI trust bootstrap (CIC_TRUST_MODE)
      proof_verify.go  — ProofTrace artifact ellenőrzés
      git_host_funcs.go — WASM git host function wiring
      embedded/        — beágyazott séma/workflow/WASM modulok
  config/
    relay.config.schema.yaml       — relay konfig séma (dogfooding)
    schemas/                       — további belső sémák (cert.selfsigned, ci.build, proof_artifact)
  context/
    CONTRACT.md        — kanonikus kontraktus (canonical JSON)
    GOALS.md
    LIMITS.md
    SYMBOLS.md + SYMBOLS.ALLOWPKGS
    TESTING.md
  core/
    cabinet/           — Végrehajtó réteg: schema/module/workflow registry + WASM runtime
      api.go           — Cabinet API interfész
      api_set.go       — Set/Setx implementáció
      cabinet.go       — CabinetService fő implementáció
      cicwasm.go       — wazero WASM integration
      proof_trace.go   — ProofTrace típus + chain_hash számítás
      workflow.go      — ExecutionGraph, lépések, kimenet-kulcsok
      schema.go        — schema store és betöltés
      module_descriptor.go — modul metaadat
      pki_verify.go    — X.509 lánc ellenőrzés (scaffold: CA lánc még nem bootstrapped)
      graph.go         — lineáris ExecutionGraph
      validate.go      — séma validáció
      stores.go        — in-memory store-ok (MemSchemaStore, MemWorkflowStore, MemModuleStore)
    modules/
      certselfsigned/  — önaláírt cert generátor natív modul
      cibuild/         — CI build natív modul (ci.build@1.0)
      schemacompile/   — schema compiler natív modul
      schemapipeline/  — schema pipeline natív modul
    nexus/
      crypto/          — HashiCorp Vault Transit aláírás
      git/             — GitOps: ExecGitOps, RepoRegistry, git host functions WASM-nak
      iac/             — IaC betöltő: FileSource, GitSource, IaCLoader, IaCValidator
      isolation/       — SubprocessWorker IPC, RunWorkerLoop (--mode=module-worker)
      operator/        — PollingWatcher, Bootstrapper, LifecycleManager, Operator
      recorder/        — GitStateRecorder, WorkflowRecorder → Vault-signed audit commits
      sync/            — audit squash + push
      types/           — közös Nexus típusok
  pkg/
    canonicaljson/     — determinisztikus JSON kanonizálás (rendezett kulcsok)
    merkle/            — BuildContext, Merkle-root build provenance hash, VerificationManifest
    obs/               — observability: TraceSink, LogSink, MetricSink, LogrusSink, CaptureSink
    sourcedigest/      — source tree hash számítás (pkg/sourcehash)
  embedded/
    pki/               — beágyazott PKI: root_ca.pem, intermediate_ca.pem, cic-source-ca.pem
  GOLDEN/              — golden teszt referenciák (cabinet_case01-06)
  examples/
    poc-cert-flow/     — PoC tanúsítvány folyamat példa
  scripts/             — dev segédeszközök: dev-vault.sh, gen_manifest.sh, quality.sh
  tools/
    canonicalize/      — canonicalize CLI tool
    certutils/         — X.509 cert parser
    sourcehash/        — source tree hash CLI
    symbolsgen/        — context/SYMBOLS.md generátor
  docs/
    en/               — angol dokumentáció (architecture, changelog, spec, pipeline, security, concept)
    hu/               — magyar dokumentáció (architecture, build-signing, ca-validation, roadmap, spec)
    engineering/      — symbols_spec.md
  features/
    feature-001 – feature-006  — feature spec-ek
  .github/workflows/
    verify.yml         — CI: go vet, staticcheck, symbol drift check, golden verify, coverage
    manifest-check.yml — CI: MANIFEST.sha256 drift ellenőrzés
```

---

## Entry Point — `cmd/relay/main.go`

A `main()` függvény két módban fut:
1. **Worker mode** (`--mode=module-worker`): SubprocessWorker IPC loop (izolált WASM végrehajtás)
2. **HTTP server mode** (alapértelmezett): `:8080` portón HTTP API

**Indulási sorrend:**
1. Config betöltés env változókból (`CIC_*` prefix)
2. Config séma-validáció (dogfooding: `cabinet.ValidateSchema("relay.config@1.0")`)
3. Cabinet stores inicializálás (in-memory: schema, module, workflow)
4. Vault secrets betöltés (`VAULT_TOKEN`, `CIC_VAULT_*`) → ProofTrace recorder
5. Git registry inicializálás + obs wiring
6. Cabinet service létrehozás
7. PKI trust bootstrap (`CIC_TRUST_MODE`)
8. Merkle BuildContext összerakása (ldflags injektált értékekből)
9. Natív komponensek regisztrálása
10. Beágyazott komponensek betöltése
11. Telepített komponensek betöltése (`/etc/cic-relay/components.d`)
12. Operator indítása (opcionális, ha `CIC_INFRA_REPO_PATH` be van állítva)
13. HTTP szerver indítása

**HTTP végpontok:**
- `GET /` — állapot (ok)
- `POST /set` — SetPayload végrehajtás (fő API)
- `GET /v1/schema/compile` — séma fordítás
- `GET /healthz` — liveness probe
- `GET /readyz` — readiness probe

---

## Függőségek (`go.mod`)

```
module centralrelay
go 1.24.0
toolchain go1.24.6

Fő függőségek:
  github.com/tetratelabs/wazero v1.9.0        — WASM végrehajtó
  github.com/hashicorp/vault/api v1.22.0      — Vault Transit API (ProofTrace signing)
  github.com/sirupsen/logrus v1.9.3           — strukturált JSON logging
  github.com/google/uuid v1.6.0              — request ID-k
  github.com/CycloneDX/cyclonedx-gomod v1.8.0 — SBOM generálás
  github.com/tetratelabs/wabin v0.0.0-...    — WASM kanonizálás
  github.com/hashicorp/golang-lru/v2 v2.0.7  — LRU cache (WASM compile cache)
  golang.org/x/sync v0.17.0                  — concurrency
  gopkg.in/yaml.v3 v3.0.1                    — YAML parsing
```

---

## CI/CD (`.github/workflows/`)

### `verify.yml` — minden push/PR minden branch-re
- `go vet ./...`
- `staticcheck@v0.6.1 ./...`
- Symbol drift check (`tools/symbolsgen context/SYMBOLS.ALLOWPKGS context/SYMBOLS.md`)
- Golden verify (canonicalize binary-val)
- Coverage (race mode, atomikus):
  - `core/cabinet`: min 95%
  - `cmd/relay`: min 80%
  - `tools/canonicalize`: min 85%
  - egyéb: min 75%
- Coverage HTML report artifact feltöltés

### `manifest-check.yml` — minden push/PR
- `MANIFEST.sha256` drift ellenőrzés (scripts/gen_manifest.sh)

---

## Milestone-térkép (ROADMAP.md alapján)

M1–M35 mind **Done**. Aktív sprint: 13 (lezárva). Scaffold állapotban lévő komponensek:

| Komponens | Státusz | Előfeltétel |
|---|---|---|
| `UpstreamSource` | scaffold | relay federáció v2 |
| `LocalWorker` in-process | scaffold | 3-process isolation + Vault |
| `cicSign`/`cicSignedCA` mezők | scaffold | Layer 2 CICSourceCA signing |
| quorum döntési réteg | concept | nincs runtime megfelelő |
| CICmeta protocol | concept | nincs élő bridge |

---

## ProofTrace — Architektúra

```
POST /set
  → cabinet.API.Set()
  → cabinet.Setx()
  → ExecutionGraph futtatás (lépésenkénti input/output hash)
  → ProofTrace.ChainHash = SHA256(step1.output_hash + step2.output_hash + ...)
  → ha recorder konfigurált: Vault.Transit.Sign(chain_hash)
  → ProofTrace struct visszaadva (signature mezővel)
```

A `ProofTrace` recorder nélkül is épül — Vault hiánya nem fatális, csak az aláírás marad el.

---

## CIC Kapcsolódások

- **CIC_Schemas**: a schema compiler által előállított signed YAML artifact-okat a Relay tölti be és validálja (`cabinet.ValidateSchema`)
- **cic-primitives**: a Relay nem importálja közvetlen — a schema-k YAML-ban definiáltak, a primitívek a schema rétegen keresztül kapcsolódnak
- **cic-mcp-private**: a KB tartalmaz CIC-Relay node-okat és edge-eket; az MCP szerver expozálja a Relay architektúra fogalmait AI asszisztenseknek

---

## Python tool réteg

A Relay tartalmaz egy Python tool réteget is (`tools/compiler.py`, `tools/finalize_release.py`, `tools/releaselib/`, `tools/schemalib/`) — ez a CIC_Schemas tooling másolata, `remote-merge`-gel átvett sablon. Pytest konfig: `pytest.ini`. Python deps: `requirements.txt` (pip-compile, Python 3.11).
