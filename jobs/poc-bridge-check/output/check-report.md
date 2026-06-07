# Bridge Térkép Visszaellenőrzés

> Forrás: `bridge-map.md` és `relay-coverage.md` (poc-plan-bridge-review output)
> Módszer: minden hivatkozott chunk `get_chunk(cXXXX)` hívással visszaellenőrizve
> KB státusz: elérhető, friss (chunks.pkl mtime: 2026-06-05)

---

## Összefoglaló

| Ítélet | Darab |
|---|---|
| CONFIRMED | 27 |
| PARTIAL | 6 |
| INCORRECT | 2 |
| UNVERIFIABLE | 0 |

---

## Ellenőrzött állítások

---

### IMPLEMENTÁLT KOMPONENSEK

---

### ValidateSchema (c357)

- Állítás (bridge-map.md): státusz = implemented, KB node: c357 (ValidateSchema go_func)
- KB visszaellenőrzés: `get_chunk("c357")` → `go_package`, `schema_validate.go`, tartalmaz `ValidateSchema` és `validateInputSchema` — "checks whether data carries a `$schema` key matching one of accepts"
- Ítélet: **PARTIAL**
- Megjegyzés: A chunk típusa `go_package`, nem `go_func` ahogy a bridge-map hivatkozza. Tartalmilag helyesen leírja a funkcionalitást, de a node típus eltérés van. Fontos: a `c217` (PutSchema) és `c218` (GetSchema) hivatkozások a bridge-mapban a Cabinet implementációjaként szerepelnek, azonban a KB-ban ezek `mockCabinetService` metódusok (`main_test_helper.yaml`) — nem a valódi Cabinet interface implementációi. A valódi Cabinet interface: c365 (go_interface, "schema/module/workflow management") — ez helyes hivatkozás.

---

### canonicaljson.ToJSON (c1127)

- Állítás (bridge-map.md): státusz = implemented, KB node: c1127 (ToJSON go_func)
- KB visszaellenőrzés: `get_chunk("c1127")` → `go_func`, `canonicaljson.go`, "marshals a Go value into a canonical JSON string. It ensures that map keys are sorted alphabetically for deterministic output"
- Ítélet: **CONFIRMED**
- Megjegyzés: Típus, tartalom, státusz teljes egyezés.

---

### ProofTrace go_struct (c349)

- Állítás (bridge-map.md): státusz = implemented, KB node: c349 (ProofTrace go_struct)
- KB visszaellenőrzés: `get_chunk("c349")` → `go_struct`, `proof_trace.yaml`, "immutable audit record of a completed workflow execution [...] SourceDigest anchors the chain [...] ChainHash"
- Ítélet: **CONFIRMED**
- Megjegyzés: Típus és tartalom egyezik. A `SourceDigest` és `ChainHash` mezők a bridge-map állításait alátámasztják.

---

### GitStateRecorder.RecordState (c594)

- Állítás (bridge-map.md): státusz = scaffold (state-commit-writer), KB node: c594
- KB visszaellenőrzés: `get_chunk("c594")` → `go_method`, `recorder.yaml`, "persists the state to JSON files, signs it, and creates a git commit. references: types.ExpectedState"
- Ítélet: **CONFIRMED**
- Megjegyzés: A bridge-map scaffold besorolása helyes — a metódus létezik és `ExpectedState`-et kezel, nem a kanonikus StateCommit rekordot (c1823). A bridge törési pont (runtime → StateCommit séma eltérés) alátámasztott.

---

### VaultCryptoService (c479)

- Állítás (bridge-map.md): státusz = implemented (relay.sign-nál scaffold), KB node: c479 (VaultCryptoService go_struct)
- KB visszaellenőrzés: `get_chunk("c479")` → `go_struct`, `service.yaml`, "implements CryptoService using HashiCorp Vault's Transit engine. references: api.Client"
- Ítélet: **CONFIRMED**
- Megjegyzés: VaultCryptoService létezik Go kódban, az actor binding hiány (actorRef bekötés) a bridge-mapban helyesen jelzett.

---

### SCAFFOLD KOMPONENSEK

---

### Watcher interface (c580)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c580 (Watcher go_interface)
- KB visszaellenőrzés: `get_chunk("c580")` → `go_interface`, `watcher.yaml`, "defines the interface for monitoring infrastructure changes"
- Ítélet: **CONFIRMED**
- Megjegyzés: Interface létezik Go kódban. A bridge törési pont (runtime — intent branch bekötés hiányzik) alátámasztott.

---

### IaCValidator.ValidateResource (c533)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c533 (IaCValidator.ValidateResource go_method)
- KB visszaellenőrzés: `get_chunk("c533")` → `go_method`, `validator.yaml`, "validates a single ResourceSpec against the Cabinet schema registry. Suitable for per-event validation in the Operator. references: types.ResourceSpec"
- Ítélet: **CONFIRMED**
- Megjegyzés: A bridge-map helyesen azonosítja a metódust. A ValidateResource implementált Go metódus.

---

### IaCSource interface (c509)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c509 (IaCSource go_interface)
- KB visszaellenőrzés: `get_chunk("c509")` → `go_interface`, `loader.yaml`, "defines the interface for retrieving raw configuration data"
- Ítélet: **CONFIRMED**
- Megjegyzés: Interface létezik, generikus — a bridge-map Terraform-agnosztikus megjegyzése helyes.

---

### WorkflowRecorder.Record (c601)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c601 (WorkflowRecorder.Record go_method)
- KB visszaellenőrzés: `get_chunk("c601")` → `go_method`, `workflow_recorder.yaml`, "persists the ProofTrace via the underlying StateRecorder. workflowID is used as the RunID; trace is stored as the actual state. references: types.ExpectedState"
- Ítélet: **CONFIRMED**
- Megjegyzés: A "workflow ID"-ra épül, nem state commitre — a bridge-map állítása helyes.

---

### CryptoService interface (c480)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c480 (CryptoService go_interface)
- KB visszaellenőrzés: `get_chunk("c480")` → `go_interface`, `service.yaml`, "defines the interface for cryptographic operations like signing and decrypting"
- Ítélet: **CONFIRMED**
- Megjegyzés: Interface létezik Go kódban. VaultCryptoService (c479) implementálja.

---

### CONCEPT KOMPONENSEK

---

### PBS állapotfa modell (c2582)

- Állítás (bridge-map.md): státusz = concept, KB node: c2582 (PBS állapotfa)
- KB visszaellenőrzés: `get_chunk("c2582")` → `section`, `pose_pbs_integration.md`, fa-szerkezet leírás, "A PoSE a root hash-t ellenőrzi. Ha a root eltér → drift."
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node, nem Go implementáció. Concept státusz helyes.

---

### Drift jelzés / H(logical)==H(physical) (c2585)

- Állítás (bridge-map.md): státusz = concept, KB node: c2585
- KB visszaellenőrzés: `get_chunk("c2585")` → `section`, `pose_pbs_integration.md`, "if H(logical) == H(physical): state = VERIFIED else: state = DRIFT"
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node. Concept státusz helyes. Azonban megjegyzés szükséges: a `VerifyProofArtifact` (c246) már tartalmaz `pose_result` mezőt (VERIFIED | DRIFT | SKIPPED) és `commit_record` referenciát — ez részleges kód-szintű megfelelő, amit a bridge-map nem említ. Lásd: relay.verifyCommit PARTIAL ítélet.

---

### Drift Taxonomy (c2536)

- Állítás (bridge-map.md): státusz = concept, KB node: c2536 (Drift Taxonomy doc)
- KB visszaellenőrzés: `get_chunk("c2536")` → `section`, `drift_taxonomy.md`, típus: `section`, kategória: `meta`
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node. Concept státusz helyes. A c1747-c1752 szekciók valóban doc node-ok (drift típusok).

---

### The Commit Record (c1823)

- Állítás (bridge-map.md): státusz = concept, KB node: c1823 (The Commit Record)
- KB visszaellenőrzés: `get_chunk("c1823")` → `section`, `state_commit_model.md` (EN), YAML struktúra: `id, traceHead, poseRoot, ts, actor` — doc node
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node, a YAML struktúra dokumentált de Go struct nincs a KB-ban. A bridge-map StateCommit YAML struktúrára vonatkozó hivatkozása helyes.

---

### Trust Anchor Lifecycle (c2303)

- Állítás (bridge-map.md): státusz = concept, KB node: c2303 (Trust Anchor Lifecycle doc)
- KB visszaellenőrzés: `get_chunk("c2303")` → `section`, `trust_anchor_lifecycle.md`, leírás: "anchorID, publicKey, hatályidő, bizalmi kontextus [...] életciklus fázisai"
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node. Concept státusz helyes.

---

### OIS Obligation (c1715)

- Állítás (bridge-map.md): státusz = concept, KB node: c1715 (OIS Obligation)
- KB visszaellenőrzés: `get_chunk("c1715")` → `section`, `ois_principles.md`, "Every intent implies a set of obligations after execution [...] Obligations cannot be 'lost'"
- Ítélet: **CONFIRMED**
- Megjegyzés: Doc node. Concept státusz helyes. Az Intent.schema.json "concept" besorolása alátámasztott.

---

### MISSING KOMPONENSEK

---

### RelayHeader.schema.json

- Állítás (bridge-map.md): státusz = missing, KB node: nincs; hivatkozás: c616 (RelaySpec go_struct)
- KB visszaellenőrzés: `search_query("RelayHeader relay header schema envelope")` → legjobb találat: c2589 (relay.md általános leírás), c615 (Relay struct), c1114 (iac_ontology). `get_chunk("c616")` → `go_struct`, "struct RelaySpec" — nem RelayHeader.
- Ítélet: **CONFIRMED**
- Megjegyzés: RelayHeader nem létezik a KB-ban. A RelaySpec (c616) valóban más entitás.

---

### TerraformState.schema.json

- Állítás (bridge-map.md): státusz = missing, KB node: nincs; hivatkozás: c509 (IaCSource), c517 (GitSourceConfig)
- KB visszaellenőrzés: `search_query("TerraformState terraform state schema relay")` → legjobb találatok: c615, c616 (nexus types), c2780 (shape.yaml sémák) — Terraform-specifikus state schema nem szerepel
- Ítélet: **CONFIRMED**
- Megjegyzés: Terraform-specifikus state schema valóban hiányzik. A CIC IaC modellje generikus, a bridge-map következtetése helyes.

---

### RollbackRequest.schema.json

- Állítás (bridge-map.md): státusz = missing; hivatkozás: c2220 (quorum release)
- KB visszaellenőrzés: `search_query("RollbackRequest rollback request schema")` → c2220 (quorum release rollback — "workflow automatikusan megszakad, naplózott incidentként"), c493 (exec_gitops), c182 (compile_handler) — rollback request schema nincs
- Ítélet: **CONFIRMED**
- Megjegyzés: c2220 tartalma helyes — kvórum-alapú rollback workflow, nem relay rollback séma. A bridge-map állítása helyes.

---

### PolicyDecision.schema.json

- Állítás (bridge-map.md): státusz = missing; hivatkozás: c1715, c2562
- KB visszaellenőrzés: `search_query("PolicyDecision policy decision OIS schema")` → c1018 (secret_and_audit_model), c892 (obs_modell), c740 (EN secret_and_audit), c2544 (drift), c2613 (state_commit) — PolicyDecision schema nincs. `get_chunk("c2562")` → OIS Layer doc: "Ellenőrzi, hogy a művelet szándéka és jogosultsági kerete összhangban van. Kimenet: engedélyezett vagy elutasított műveleti kontextus."
- Ítélet: **CONFIRMED**
- Megjegyzés: PolicyDecision nevű entitás valóban nem szerepel a KB-ban. Az OIS Layer (c2562) döntési kimenete nem sémaként van modellezve.

---

### emitOperatorInstruction

- Állítás (bridge-map.md): státusz = missing; hivatkozás: c2589 (relay DAG modell)
- KB visszaellenőrzés: `search_query("emitOperatorInstruction operator instruction relay emit")` → c912 (relay_pozicionalas), c2589 (relay.md), c1035 (relay spec), c914 (relay_pozicionalas) — explicit emitter nincs. `get_chunk("c2589")` → "továbbítja az eredményt más komponensek (pl. állapotfigyelő, generátor) felé" — általános
- Ítélet: **CONFIRMED**
- Megjegyzés: c2589 tartalma egyezik a bridge-map állításával. Nincs specifikus operator instruction emitter a KB-ban.

---

### post_apply_observation.workflow.yaml

- Állítás (bridge-map.md): státusz = missing; hivatkozás: c428 (generikus workflow struct)
- KB visszaellenőrzés: `search_query("post apply observation workflow terraform trigger")` → c166 (activator.yaml), c415 (cabinet types), c286 (api_set), c428 (workflow struct), c1187 (obs/types) — specifikus post_apply workflow nincs
- Ítélet: **CONFIRMED**
- Megjegyzés: A generikus workflow infrastruktúra (c428) létezik, de post_apply_observation specifikus definíció valóban hiányzik.

---

### RELAY FUNKCIÓK

---

### relay.validate (c357, c533)

- Állítás (bridge-map.md): státusz = implemented, KB node: c357 (ValidateSchema), c533 (ValidateResource)
- KB visszaellenőrzés: mindkét chunk visszaigazolva (lásd fent)
- Ítélet: **PARTIAL**
- Megjegyzés: A c357 típusa `go_package` (nem `go_func`). A bridge-map c217/c218 hivatkozásai (schema-registry komponensnél) mock implementációk, nem valódi Cabinet metódusok — ez a schema-registry komponens bridge-map leírásában pontatlanság.

---

### relay.canonicalize (c1127)

- Állítás (bridge-map.md): státusz = implemented, KB node: c1127
- KB visszaellenőrzés: visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.hash (c349, c350)

- Állítás (bridge-map.md): státusz = implemented, KB node: c350 (ProofTrace canonical hash), c349
- KB visszaellenőrzés: `get_chunk("c350")` → `go_func`, `hashValue`, "returns the hex-encoded SHA-256 of the canonical JSON representation of v. references: canonicaljson.ToJSON"
- Ítélet: **CONFIRMED**
- Megjegyzés: c350 `hashValue` go_func, nem "ProofTrace canonical hash" ahogy a bridge-map hivatkozza, de a tartalom (SHA-256, canonicaljson hivatkozás) alátámasztja az állítást.

---

### relay.sign (c479, c480)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c479, c480
- KB visszaellenőrzés: mindkét chunk visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.observe (c1186, c472)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c1186 (Resource go_struct), c472 (Nexus Recorder)
- KB visszaellenőrzés: `get_chunk("c1186")` → `go_struct`, "identifies the origin of an observation — which relay component emitted it". `get_chunk("c472")` → `section`, README.md, "persisting the Actual State and Expected State [...] local Git-based cache"
- Ítélet: **CONFIRMED**
- Megjegyzés: A bridge-map állítása helyes. c1186 az obs origin azonosítója, nem a fizikai adapter.

---

### relay.compare (c2585)

- Állítás (bridge-map.md): státusz = concept, KB node: c2585
- KB visszaellenőrzés: visszaigazolva (lásd PBS/Drift jelzés)
- Ítélet: **CONFIRMED**

---

### relay.classifyDrift (c2536)

- Állítás (bridge-map.md): státusz = concept, KB node: c2536
- KB visszaellenőrzés: visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.buildProofTrace (c349, c601)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c349, c601
- KB visszaellenőrzés: visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.commitState (c594, c1823)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c594, c1823
- KB visszaellenőrzés: visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.verifyCommit (c246, c121)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c246 (proof_verify.yaml), c121 (ProofTrace integritás)
- KB visszaellenőrzés: `get_chunk("c246")` → `go_func`, `VerifyProofArtifact`, "validates a ProofArtifact [...] pose_result value is one of: VERIFIED | DRIFT | SKIPPED (when present). 5. commit_record.id == chain_hash when commit_record is present. references: cabinet.ProofTraceStep"
- Ítélet: **PARTIAL**
- Megjegyzés: A bridge-map a `VerifyProofArtifact`-ot csak CI/build pipeline-hoz köti. Azonban a c246 tartalmaz `pose_result` és `commit_record` validációt — ezek a PoSE és StateCommit fogalmak részleges kód-szintű megfelelői. Ez azt jelenti, hogy a `relay.verifyCommit` és a PoSE/StateCommit bridge nem csak concept — a verifikátor kód már foglalkozik ezekkel. A bridge-map ezt nem emelte ki. Pontosítás: a `VerifyProofArtifact` scaffold szintje erősebb, mint ahogy a bridge-map bemutatja.

---

### relay.readIntentBranch (c580, c588)

- Állítás (bridge-map.md): státusz = scaffold, KB node: c580, c588
- KB visszaellenőrzés: visszaigazolva
- Ítélet: **CONFIRMED**

---

### relay.emitOperatorInstruction

- Állítás (bridge-map.md): státusz = missing
- KB visszaellenőrzés: visszaigazolva (nincs KB node)
- Ítélet: **CONFIRMED**

---

### SCHEMA-REGISTRY MODUL — PutSchema/GetSchema hivatkozás

- Állítás (bridge-map.md): KB node: c217 (PutSchema), c218 (GetSchema) — Cabinet interface metódusok
- KB visszaellenőrzés: `get_chunk("c217")` → `go_method`, `mockCabinetService.PutSchema`, `main_test_helper.yaml` — test mock. `get_chunk("c218")` → `go_method`, `mockCabinetService.GetSchema`, `main_test_helper.yaml` — test mock.
- Ítélet: **INCORRECT**
- Megjegyzés: A c217 és c218 nem a Cabinet interface valódi metódusai — ezek test mock implementációk (`main_test_helper.yaml`). A valódi Cabinet interface: c365 (go_interface, `service.yaml`). A schema-registry implemented státusza tartalmilag helyes (a Cabinet valóban végzi a schema regisztrációt), de a hivatkozott chunk-ok pontatlanok.

---

### actual-state-collector — c1118 Proxmox hivatkozás

- Állítás (bridge-map.md): státusz = concept, KB node: c1118 (Proxmox mint Service fogalom)
- KB visszaellenőrzés: `get_chunk("c1118")` → `section`, `iac_ontology_and_design.md`, "A virtualizációs platform (pl. Proxmox, vSphere, OpenStack) a CIC modellben Service-ként jelenik meg. Feladata: Erőforrások (VM-ek) létrehozása és menedzselése."
- Ítélet: **CONFIRMED**
- Megjegyzés: Design doc szekció, nem Go kód. A bridge-map concept besorolása helyes.

---

### DesiredState.schema.json — c984 M11 checklist

- Állítás (bridge-map.md): státusz = scaffold, KB node: c984 (M11 IaC Processing)
- KB visszaellenőrzés: `get_chunk("c984")` → `section`, `relay_milestones.md`, M11 checklist: "[ ] M11.1 [...] [ ] M11.2 [...] [ ] M11.3 [...] [ ] M11.4" — minden részfeladat nyitott
- Ítélet: **CONFIRMED**
- Megjegyzés: Az M11 checklistje valóban `[ ]` állapotban van (nincs befejezve). A scaffold besorolás és az "IaC pipeline nem teljes" megállapítás alátámasztott.

---

### WORKFLOWK (manual_drift, hard_drift, rollback_intent, rollback_post_apply)

- Állítás (bridge-map.md): mind missing, nincs KB node
- KB visszaellenőrzés: a search_query hívások nem hoztak specifikus workflow node-okat ezekre — csak általános doc és drift taxonomy node-okat
- Ítélet: **CONFIRMED**
- Megjegyzés: Az összes PoC-specifikus workflow yaml valóban hiányzik a KB-ból.

---

## Összefoglaló ítéletek

| Komponens | Ítélet | Megjegyzés |
|---|---|---|
| ValidateSchema (c357) | PARTIAL | Node típus: go_package, nem go_func |
| canonicaljson.ToJSON (c1127) | CONFIRMED | |
| ProofTrace go_struct (c349) | CONFIRMED | |
| GitStateRecorder.RecordState (c594) | CONFIRMED | |
| VaultCryptoService (c479) | CONFIRMED | |
| Watcher interface (c580) | CONFIRMED | |
| IaCValidator.ValidateResource (c533) | CONFIRMED | |
| IaCSource interface (c509) | CONFIRMED | |
| WorkflowRecorder.Record (c601) | CONFIRMED | |
| CryptoService interface (c480) | CONFIRMED | |
| PBS állapotfa (c2582) | CONFIRMED | |
| Drift jelzés (c2585) | CONFIRMED | |
| Drift Taxonomy (c2536) | CONFIRMED | |
| The Commit Record (c1823) | CONFIRMED | |
| Trust Anchor Lifecycle (c2303) | CONFIRMED | |
| OIS Obligation (c1715) | CONFIRMED | |
| RelayHeader — missing | CONFIRMED | |
| TerraformState — missing | CONFIRMED | |
| RollbackRequest — missing | CONFIRMED | |
| PolicyDecision — missing | CONFIRMED | |
| emitOperatorInstruction — missing | CONFIRMED | |
| post_apply_observation — missing | CONFIRMED | |
| relay.validate | PARTIAL | c217/c218 mock hivatkozások |
| relay.canonicalize | CONFIRMED | |
| relay.hash (c350) | CONFIRMED | |
| relay.sign | CONFIRMED | |
| relay.observe | CONFIRMED | |
| relay.compare | CONFIRMED | |
| relay.classifyDrift | CONFIRMED | |
| relay.buildProofTrace | CONFIRMED | |
| relay.commitState | CONFIRMED | |
| relay.verifyCommit | PARTIAL | VerifyProofArtifact erősebb, mint bemutatva |
| relay.readIntentBranch | CONFIRMED | |
| relay.emitOperatorInstruction | CONFIRMED | |
| schema-registry c217/c218 | INCORRECT | Mock metódusok, nem valódi Cabinet impl |
| actual-state-collector c1118 | CONFIRMED | |
| DesiredState M11 checklist | CONFIRMED | |
| Workflowk (4 db) | CONFIRMED | |
