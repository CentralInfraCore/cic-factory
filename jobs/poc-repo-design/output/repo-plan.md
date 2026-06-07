# PoC Repó Struktúra Terv

> KB alapú terv — minden állítás mögött chunk hivatkozás áll.
> Módszertan: bridge-map.md + relay-coverage.md + corrections.md + KB közvetlen lekérdezés.

---

## Összefoglaló táblázat

| Repó / Branch | Típus | Örököl | Implementál | Betöltés módja |
|---|---|---|---|---|
| `cic-proxmox` | új repó (domain adapter) | base-repo (remote merge), CIC-Relay `IaCSource` + `Watcher` interface | `ActualStateCollector` (új), `IaCSource` (opcionális) | natív modul (`core/modules/`) |
| `cic-vyos` | új repó (domain adapter) | base-repo (remote merge), CIC-Relay `Watcher` interface | `ActualStateCollector` (új) | natív modul (`core/modules/`) |
| `cic-openswitch` | új repó (domain adapter) | base-repo (remote merge), CIC-Relay `Watcher` interface | `ActualStateCollector` (új) | natív modul (`core/modules/`) |
| `CIC-Schemas` `poc/v1` branch | új branch meglévő repóban | CIC-Schemas `template` branch (worktree minta) | PoC sémák (DesiredState, ActualState, Drift, PoSE, StateCommit, Actor, Intent) | schema artifact (relay Cabinet regisztrál) |
| `CIC-Relay` `core/modules/pocobs/` | új csomag meglévő repóban | CIC-Relay `core/modules/` minta (schemacompile, schemapipeline) | `PBSRootCalculator`, `PoSEVerifier`, `DriftClassifier` | natív modul (relay bootstrap regisztrálja) |
| `CIC-Relay` `core/nexus/statecommit/` | új csomag meglévő repóban | CIC-Relay `core/nexus/recorder/` minta (GitStateRecorder) | `StateCommitWriter` (StateCommit séma adaptáció) | nexus belső csomag |
| `CIC-Relay` `core/nexus/trustanchor/` | új csomag meglévő repóban | CIC-Relay `core/nexus/crypto/` (CryptoService interface) | `TrustAnchorRegistry` | nexus belső csomag |

---

## Öröklési térkép

### 1. `cic-proxmox` — új repó

```
[cic-proxmox]
  örököl:
    - base-repo (git remote `base`): Makefile, CI pipeline, signing hook
      (commit-msg ECDSA Vault Transit), project.yaml, docs sablon
      Minta: cic-compute, cic-network (c2676, c2669, c2806)
    - CIC-Relay interface definíciók (Go import):
        core/nexus/operator/watcher.go → Watcher interface (c580)
        core/nexus/iac/loader.go       → IaCSource interface (c509)
        pkg/obs/types.go               → Resource struct (c1186)
  implementál:
    - ActualStateCollector interface (ld. Interface definíciók fejezet)
    - Proxmox API klienslogika (REST API / QEMU agent alapú state lekérés)
    - (opcionális) IaCSource — ha a Proxmox konfigurációját git IaC forrásból is
      olvassa a relay (provider-agnosztikus minta: c509)
  betöltődik:
    - natív modulként: core/modules/proxmoxobs/ a CIC-Relay-ben
    - a relay bootstrap regisztrálja (minta: schemacompile, schemapipeline — c442, c453)
    - NEM .so plugin: a .so buildmode külső, stateless logikára való (c899, c900, c906);
      az ActualStateCollector stateful provider kapcsolatot tart fenn → natív modul
  függőség:
    - ActualStateCollector interface definíciója a CIC-Relay-ben (előbb kell)
    - CIC-Relay bootstrap regisztráció (core/modules/ bővítése)
```

### 2. `cic-vyos` — új repó

```
[cic-vyos]
  örököl:
    - base-repo (git remote `base`): azonos minta mint cic-proxmox
    - CIC-Relay: Watcher (c580), Resource (c1186)
  implementál:
    - ActualStateCollector (VyOS CLI / NETCONF alapú state lekérés)
  betöltődik:
    - natív modul: core/modules/vyosobs/ a CIC-Relay-ben
  függőség:
    - ActualStateCollector interface definíciója (CIC-Relay, előbb kell)
    - cic-proxmox-tól független; párhuzamosan implementálható
```

### 3. `cic-openswitch` — új repó

```
[cic-openswitch]
  örököl:
    - base-repo (git remote `base`): azonos minta
    - CIC-Relay: Watcher (c580), Resource (c1186)
  implementál:
    - ActualStateCollector (OpenSwitch NETCONF/RESTCONF alapú state lekérés)
  betöltődik:
    - natív modul: core/modules/openswitchobs/ a CIC-Relay-ben
  függőség:
    - ActualStateCollector interface definíciója (előbb kell)
    - cic-proxmox-tól és cic-vyos-tól független
```

### 4. `CIC-Schemas` — `poc/v1` branch

```
[CIC-Schemas / poc/v1 branch]
  örököl:
    - CIC-Schemas `template` branch (worktree minta — c1298, c1256)
    - base-repo compiler tooling: tools/compiler.py, Makefile (c2806)
    - signing lánc: commit-msg hook (ECDSA Vault Transit)
  implementál:
    Sémák (YAML séma fájlok, CIC-Schemas compiler feldolgozza):
      - DesiredState (scaffold: ExpectedState fogalom már létezik — c984, de nincs .yaml séma)
      - ActualState  (scaffold: GitStateRecorder ismeri — c472, c594 — de séma nincs)
      - Drift        (concept: taxonómia dokumentált — c2536; SOFT/HARD/CHAIN kategóriák)
      - PoSE         (concept: H(logical)==H(physical) logika — c2582, c2585)
      - StateCommit  (concept: id, traceHead, poseRoot, ts, actor mezők — c1823)
      - Actor        (concept: trustAnchorID, publicKey, hatályidő — c2303)
      - Intent       (concept: OIS obligation — c1715)
    Vault signing: IGEN — a CIC-Schemas pipeline minden releaselt sémát aláír
    (minta: cic.artifact.sign@1.0 — c442; cic.schema.compile workflow — c189)
  betöltődik:
    - schema artifact → relay Cabinet PutSchema-n keresztül regisztrálódik
    - relay.validate ezeket validálja (Cabinet.ValidateSchema — c357, c365)
  függőség:
    - base-repo template branch: CIC-Schemas-ban már van (upstream)
    - nincs Go kód függőség — schema-first lépés
    - a relay natív modulok (pocobs, statecommit) az itt definiált sémákat fogják
      importálni → a sémák ELŐBB kell hogy legyenek
```

### 5. `CIC-Relay` — `core/modules/pocobs/` (új csomag)

```
[CIC-Relay / core/modules/pocobs/]
  örököl:
    - core/modules/ minta: schemacompile (c442), schemapipeline (c453)
    - natív modul regisztráció: relay bootstrap (c558, c564, c167)
    - canonicaljson.ToJSON (c1127) — determinisztikus hash-hoz
    - ProofTrace struct (c349), ProofTraceStep (c348) — a trace lánc részévé teszi
  implementál:
    - PBSRootCalculator: PBS állapotfa Merkle root hash kalkuláció
      (fogalom: c2582 — "fa-szerkezet, root hash ellenőrzés")
    - PoSEVerifier: H(logical) == H(physical) összehasonlítás, VERIFIED/DRIFT/SKIPPED
      kimenet (fogalom: c2585; az értékkészlet VerifyProofArtifact-ban definiált — c246)
    - DriftClassifier: NO_DRIFT / SOFT / HARD / CHAIN osztályozás
      (fogalom: c2536, c1747-c1752)
    Natív modul azonosítók (relay workflow-ban hivatkozható):
      cic.obs.pbs.calc@1.0
      cic.obs.pose.verify@1.0
      cic.obs.drift.classify@1.0
  betöltődik:
    - natív modulként: a relay bootstrap regisztrálja (mint schemacompile — c442)
    - relay workflow yaml-ban hivatkozható lépésként
  függőség:
    - CIC-Schemas poc/v1 sémák (PoSE, Drift értékkészletek)
    - ActualStateCollector interface (az adapter-repók ezt használják)
    - ProofTrace chain (implementált — c349, c348)
```

### 6. `CIC-Relay` — `core/nexus/statecommit/` (új csomag)

```
[CIC-Relay / core/nexus/statecommit/]
  örököl:
    - core/nexus/recorder/ minta: GitStateRecorder.RecordState (c594)
    - WorkflowRecorder.Record (c601) — ProofTrace perzisztálás
    - VaultCryptoService signing (c479) — az aláírási mechanizmus megvan
  implementál:
    - StateCommitWriter: kanonikus StateCommit rekord írása
      (séma: c1823 — id, traceHead, poseRoot, ts, actor mezők)
    - A GitStateRecorder.RecordState adaptálása: jelenleg ExpectedState-et ír (c594),
      a StateCommitWriter a PoSE root-ot és trace head-et is hozzáadja
    - Git commit létrehozása az audit repóba (meglévő mechanizmus adaptálása)
  betöltődik:
    - nexus belső csomag (nem natív modul): a relay core workflow hívja
    - hasonlóan a recorder package-hez
  függőség:
    - CIC-Schemas poc/v1 StateCommit séma
    - core/modules/pocobs/ PoSEVerifier kimenete (poseRoot)
    - core/cabinet/proof_trace.go ProofTrace (traceHead — c349)
    - VaultCryptoService (c479) actor binding-hoz TrustAnchorRegistry szükséges
```

### 7. `CIC-Relay` — `core/nexus/trustanchor/` (új csomag)

```
[CIC-Relay / core/nexus/trustanchor/]
  örököl:
    - core/nexus/crypto/ minta: CryptoService interface (c480),
      VaultCryptoService (c479)
    - Actor séma fogalom (c2303 — trustAnchorID, publicKey, hatályidő)
  implementál:
    - TrustAnchorRegistry: actor → Vault signing key mapping, lifecycle kezelés
    - Az aláírási folyamatba bekötés: relay.sign(hash, actorRef) — az actorRef
      alapján kiválasztja a megfelelő Vault Transit kulcsot
  betöltődik:
    - nexus belső csomag
  függőség:
    - CIC-Schemas poc/v1 Actor séma
    - VaultCryptoService (c479) — megvan, ezt wrappeli
    - PoC-ban elfogadható: egyetlen hardcoded actor (a teljes registry concept szintű)
```

---

## Dependency order

Topológiai sorrend — mi blokkolja mit:

```
Szint 0 — nincs függőség (azonnal indítható):
  [A] base-repo — már megvan (upstream)
  [B] CIC-Schemas poc/v1 branch — schema-first, nincs Go függőség

Szint 1 — Szint 0 után:
  [C] CIC-Relay: ActualStateCollector interface definíció
      (core/nexus/ vagy core/modules/ alá; az adapter repók ezt importálják)
  [D] CIC-Relay: core/nexus/trustanchor/ (TrustAnchorRegistry)
      Feltétel: Actor séma (B) + VaultCryptoService (megvan)

Szint 2 — Szint 1 után:
  [E] cic-proxmox repó — ActualStateCollector interface megvan (C)
  [F] cic-vyos repó — ActualStateCollector interface megvan (C)
  [G] cic-openswitch repó — ActualStateCollector interface megvan (C)
  [H] CIC-Relay: core/modules/pocobs/ (PBSRootCalculator, PoSEVerifier, DriftClassifier)
      Feltétel: poc/v1 sémák (B), canonicaljson (megvan), ProofTrace (megvan)

Szint 3 — Szint 2 után:
  [I] CIC-Relay: core/nexus/statecommit/ (StateCommitWriter)
      Feltétel: StateCommit séma (B), PoSEVerifier (H), TrustAnchorRegistry (D),
                ProofTrace chain (megvan)

Szint 4 — Szint 3 után:
  [J] CIC-Relay: PoC workflow yaml-ok (observation pipeline bekötés)
      Feltétel: minden modul regisztrált (E/F/G adapter-ok, H pocobs, I statecommit)
```

Függőségi gráf (nyilak: "szükséges előtte"):

```
base-repo [A] ──────────────────────────────────────────→ cic-proxmox [E]
                                                         → cic-vyos [F]
                                                         → cic-openswitch [G]

CIC-Schemas poc/v1 [B] ─────────────────────────────────→ pocobs [H]
                   └────────────────────────────────────→ statecommit [I]
                   └────────────────────────────────────→ trustanchor [D]

ActualStateCollector interface [C] ─────────────────────→ cic-proxmox [E]
                               └────────────────────────→ cic-vyos [F]
                               └────────────────────────→ cic-openswitch [G]

pocobs [H] ─────────────────────────────────────────────→ statecommit [I]
trustanchor [D] ────────────────────────────────────────→ statecommit [I]
statecommit [I] ────────────────────────────────────────→ workflow yaml-ok [J]
cic-proxmox [E] ────────────────────────────────────────→ workflow yaml-ok [J]
```

---

## Interface definíciók

### ActualStateCollector — új Go interface

A CIC-Relay-ben definiálandó (javasolt hely: `core/nexus/operator/collector.go`).
Az adapter repók (cic-proxmox, cic-vyos, cic-openswitch) ezt implementálják natív modulként.

```go
// ActualStateCollector defines the interface for provider-specific physical
// state collection. Implementations are registered as native relay modules.
// KB reference: c472 (Nexus Recorder — Actual State), c1186 (obs/types.Resource)
type ActualStateCollector interface {
    // Collect queries the physical provider and returns the current actual state.
    // The returned ActualState must be serializable to canonical JSON.
    Collect(ctx context.Context) (*ActualState, error)

    // Provider returns a stable string identifier for this adapter.
    // Used as the obs.Resource origin field (c1186).
    // Examples: "proxmox", "vyos", "openswitch"
    Provider() string
}
```

### ActualState — Go struct (StateCommitWriter-hez)

```go
// ActualState holds the collected physical state from a provider.
// Corresponds to ActualState.schema.yaml in CIC-Schemas poc/v1.
// KB reference: c472 (Nexus Recorder), c594 (GitStateRecorder.RecordState)
type ActualState struct {
    Provider    string                 `json:"provider"`
    CollectedAt time.Time              `json:"collected_at"`
    Resources   map[string]interface{} `json:"resources"`
    // Canonical hash computed by canonicaljson.ToJSON (c1127)
    Hash        string                 `json:"hash,omitempty"`
}
```

### PBSRootCalculator — natív modul interface

```go
// PBSRootCalc computes the PBS (Proof-of-State) Merkle root hash
// from the logical (desired) and physical (actual) state trees.
// KB reference: c2582 (PBS állapotfa modell — doc)
// Native module ID: cic.obs.pbs.calc@1.0
type PBSRootCalc interface {
    // Calc returns the PBS root hash for the given logical and physical states.
    // Uses canonicaljson.ToJSON (c1127) for deterministic serialization.
    Calc(ctx context.Context, logical, physical *ActualState) (string, error)
}
```

### PoSEVerifier — natív modul interface

```go
// PoSEVerifier verifies Proof of State Existence by comparing
// the logical (desired) and physical (actual) PBS root hashes.
// KB reference: c2585 (Drift jelzés — H(logical)==H(physical))
// KB reference: c246 (VerifyProofArtifact — VERIFIED|DRIFT|SKIPPED értékkészlet)
// Native module ID: cic.obs.pose.verify@1.0
type PoSEVerifier interface {
    // Verify returns one of: "VERIFIED", "DRIFT", "SKIPPED"
    Verify(ctx context.Context, logicalHash, physicalHash string) (string, error)
}
```

### DriftClassifier — natív modul interface

```go
// DriftClassifier classifies the type of drift between logical and physical state.
// KB reference: c2536 (Drift Taxonomy), c1747-c1752 (SOFT/HARD/CHAIN kategóriák)
// Native module ID: cic.obs.drift.classify@1.0
type DriftClassifier interface {
    // Classify returns one of: "NO_DRIFT", "SOFT", "HARD", "CHAIN"
    Classify(ctx context.Context, logical, physical *ActualState) (string, error)
}
```

### TrustAnchorRegistry — nexus belső interface

```go
// TrustAnchorRegistry maps actor identifiers to their Vault signing keys.
// KB reference: c2303 (Trust Anchor Lifecycle doc), c479 (VaultCryptoService)
// KB reference: c480 (CryptoService interface)
type TrustAnchorRegistry interface {
    // SigningKeyFor returns the Vault Transit key name for the given actor.
    SigningKeyFor(ctx context.Context, actorID string) (string, error)
    // Register adds or updates an actor's key mapping.
    Register(ctx context.Context, actorID, vaultKeyName string) error
}
```

---

## PoC workflow yaml minta

Az observation pipeline relay workflow-ban (minta: c189 — `cic.schema.compile`):

```yaml
# cic.poc.observe.yaml — PoC observation workflow
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: cic.poc.observe
  version: "1.0"
  description: "PoC state observation: collect → PBS → PoSE → drift → commit"
spec:
  steps:
    - cic.obs.collect@1.0.collect(provider_ref) -> actual_state
    - cic.obs.pbs.calc@1.0.calc(desired_state, actual_state) -> pbs_root
    - cic.obs.pose.verify@1.0.verify(pbs_root.logical, pbs_root.physical) -> pose_result
    - cic.obs.drift.classify@1.0.classify(desired_state, actual_state) -> drift_result
    - cic.obs.state.commit@1.0.commit(actual_state, pose_result, drift_result) -> state_commit
```

---

## Megjegyzések — döntési pontok

### D1: Plugin vs. natív modul az adapterekhez

A KB alapján a plugin `.so` modell stateless, izolált logikára való (c899, c900, c906).
Az ActualStateCollector provider kapcsolatot tart fenn (API session, auth token) — ez
stateful. **Ezért a natív modul minta az ajánlott** (mint schemacompile — c442).
Ha az orchestrátor el akarja különíteni az adapter életciklusát a relay-től, a .so
modell is szóba jöhet, de akkor a session kezelés a relay oldalán marad.
**Döntés szükséges**: stateful adapter kezelés helye (relay vs. adapter-oldal).

### D2: IaCSource implementáció az adapter repókban

Az IaCSource interface (c509) generikus konfigurációs adat lekérőre való. Ha a Proxmox /
VyOS konfigurációját git IaC forrásból olvassa a relay (pl. Terraform HCL), akkor az
adapter implementálhatja az IaCSource-t is. Ha az adapter csak actual state-et gyűjt
(nincs git IaC forrás a PoC-ban), az IaCSource implementáció kihagyható.
**Döntés szükséges**: van-e git IaC forrás a PoC desired state-hez, vagy a desired
state más forrásból jön (pl. manuális YAML)?

### D3: TrustAnchorRegistry PoC-ban

A teljes TrustAnchorRegistry concept szintű (c2303). PoC-ban elfogadható egyetlen
hardcoded actor + egyetlen Vault kulcs (a VaultCryptoService CIC_VAULT_KEY konfigja
alapján — c260). A registry csak akkor szükséges, ha több actor ír alá különböző
kulcsokkal. **Döntés szükséges**: elegendő-e PoC-ban egyetlen signing actor?

### D4: CIC-Schemas poc/v1 sémák Vault signing szükségessége

A CIC-Schemas pipeline minden releaselt sémát aláír (c442, c189). PoC-ban a Vault
signing opcionálisan kihagyható (stub mode: cic_sign = "unavailable" — c442 alapján
ez non-fatal, a provenance rekord teljes marad). **Döntés szükséges**: kell-e Vault
signing a PoC séma release-hez, vagy stub mode elegendő az első iterációban?

### D5: Terraform-specifikus komponensek

A bridge-map.md és corrections.md alapján a TerraformState.schema.json és a
terraform-desired-extractor / terraform-state-reader komponensek nem CIC-natív
fogalmak — a CIC IaC modellje provider-agnosztikus (c509, c517). A PoC desired state
forrása lehet bármilyen IaCSource implementáció (git-alapú YAML, Terraform HCL, stb.)
anélkül, hogy Terraform-specifikus adapter kellene.
**Döntés szükséges**: Ha a PoC mégis Terraform tfstate-et használ desired source-ként,
akkor egy generikus GitSource + Terraform state parser szükséges — ez NEM önálló repó,
hanem az IaCSource implementációja az adapter oldalán.

---

## KB hivatkozások összefoglalója

| Chunk | Tartalom | Felhasználás |
|---|---|---|
| c509 | IaCSource go_interface | adapter interface minta |
| c580 | Watcher go_interface | observer minta |
| c1186 | obs/types.Resource go_struct | origin azonosítás |
| c480 | CryptoService go_interface | signing interface |
| c479 | VaultCryptoService go_struct | signing implementáció |
| c442 | schemacompile go_package | natív modul minta |
| c453 | schemapipeline go_package | natív modul pipeline minta |
| c189 | cic.schema.compile workflow | workflow yaml minta |
| c899 | plugin_interface.md (szerep) | plugin vs. natív modul döntés |
| c906 | plugin_interface.md (tech) | .so buildmode leírás |
| c349 | ProofTrace go_struct | trace chain |
| c348 | ProofTraceStep go_struct | trace step |
| c594 | GitStateRecorder.RecordState | state commit minta |
| c1127 | canonicaljson.ToJSON | determinisztikus hash |
| c2582 | PBS állapotfa modell (doc) | PBSRootCalculator fogalom |
| c2585 | PoSE drift jelzés (doc) | PoSEVerifier fogalom |
| c2536 | Drift Taxonomy (doc) | DriftClassifier fogalom |
| c1823 | StateCommit Commit Record (doc) | StateCommit séma mezők |
| c2303 | Trust Anchor Lifecycle (doc) | TrustAnchorRegistry fogalom |
| c1298 | git-management.meta.yaml | CIC-Schemas branch minta |
| c2676 | domain repók README | base-repo remote merge minta |
| c2669 | domain repók CLAUDE.md | base-repo + CIC-Schemas öröklés |
| c260 | relay.config.schema.yaml | CIC_VAULT_KEY konfig |
| c246 | VerifyProofArtifact go_func | VERIFIED/DRIFT/SKIPPED értékkészlet |
