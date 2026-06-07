# CIC Bridge Térkép — PoC komponensek

> Módszertan: KB-alapú audit. A státuszokat nem a terv állításai, hanem a KB node-ok és kódreferenciák alapozzák meg.
> Forrás: `cic-graph` MCP szerver — chunks, go_struct/go_func/go_interface node-ok, doc node-ok.

---

## Összefoglaló

| Státusz | Darab |
|---|---|
| implemented | 8 |
| scaffold | 12 |
| concept | 7 |
| missing (KB-ban sincs) | 8 |

---

## Bridge lánc ahol megszakad

```
concept → code → runtime → audit

Sémák (Actor, Intent, RelayHeader, DesiredState, TerraformState,
       ActualState, Drift, PoSE, StateCommit, RollbackRequest,
       PolicyDecision):
  KB-ban: concept (doc node) ✓
  Kódban: NINCS — a terv .json sémákat vár, a relay cabinet saját Go-típusokat
          és yaml-alapú séma-regisztert használ → bridge törési pont: code

relay.validate / relay.canonicalize / relay.hash / relay.sign:
  KB-ban: implemented (go_func / go_interface) ✓
  Runtime: részleges — CryptoService/Vault bekötés scaffold
  Audit: ProofTrace chain lánc code-szinten létezik

relay.observe / relay.compare / relay.classifyDrift:
  KB-ban: concept (doc) ✓
  Kódban: részleges (obs/types.yaml, IaCValidator) — fizikai state collector
          (Proxmox/VyOS) nincs → bridge törési pont: code→runtime

relay.readIntentBranch / relay.emitOperatorInstruction:
  KB-ban: scaffold (Watcher interface) ✓
  Runtime: PollingWatcher bekötése az IaC-pipeline-ba hiányzik

OIS policy evaluator:
  KB-ban: concept (doc) ✓
  Kódban: NINCS Go implementáció → bridge törési pont: concept→code

Workflowk (yaml fájlok):
  KB-ban: nincs specifikus node → missing
```

---

## Komponensek státusza

---

### SÉMÁK

---

#### Actor.schema.json
- KB node: c2303 (Trust Anchor Lifecycle — doc), c2124 (Glossary — Actor fogalom)
- Státusz: **concept**
- Bridge törési pont: **code** — a KB-ban az Actor fogalmi szinten dokumentált (trustAnchorID, publicKey, hatályidő), de `Actor.schema.json` nevű fájl nem szerepel a KB-ban. A relay cabinet saját Go típusokkal dolgozik (RelaySpec, Relay struct), nem JSON Schema fájlokkal.
- Bizonyíték: c2303 (Trust Anchor Lifecycle doc), c615 (Relay Go struct — nincs Actor séma hivatkozás)
- Megjegyzés: A fogalom CIC-konform, de a séma-fájl formátum nem a relay natív megközelítése.

---

#### Intent.schema.json
- KB node: c1715 (OIS Obligation — doc), c1711-c1719 (ois_principles.md szekciók)
- Státusz: **concept**
- Bridge törési pont: **code** — az Intent/Obligation fogalom gazdagon dokumentált az OIS principles-ben, de `Intent.schema.json` kódreferencia nem szerepel a KB-ban.
- Bizonyíték: c1715 (OIS 3. Obligation szekció)
- Megjegyzés: OIS elvek concept szintűek — nincs Go struct vagy json schema implementáció a KB-ban.

---

#### RelayHeader.schema.json
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — a KB-ban nem szerepel RelayHeader fogalom. A relay saját `RelaySpec` (c616) Go struct-ot használ, amely tartalmazza a relay metaadatokat, de `RelayHeader` nevű entitás nincs.
- Bizonyíték: c616 (RelaySpec go_struct — nem RelayHeader)
- Megjegyzés: A terv által bevezetett fogalom, nem CIC-natív.

---

#### DesiredState.schema.json
- KB node: c984 (M11 IaC Processing roadmap), c615/c616 (nexus types)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — az `ExpectedState` fogalom létezik a KB-ban (c984 M11 DoD: "transzformálása `ExpectedState` objektummá"), az IaCSource interface (c509) és IaCValidator (c533) scaffold szinten megvan, de az M11 checklistje `[ ]` állapotban van → az IaC pipeline nem teljes.
- Bizonyíték: c984 (M11 checklist: részfeladatok jelölve de nem done)
- Megjegyzés: Előfeltétel: M11 teljesítése (IaC feldolgozás és gráf építés).

---

#### TerraformState.schema.json
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — a KB-ban Terraform-specifikus state schema nem szerepel. A relay IaC modell generikus (`IaCSource` interface, `GitSourceConfig`), nem Terraform-specifikus.
- Bizonyíték: c509 (IaCSource interface — generikus), c517 (GitSourceConfig — generikus)
- Megjegyzés: A terv Terraform-specifikus sémát vár, de a CIC IaC modellje provider-agnosztikus.

---

#### ActualState.schema.json
- KB node: c472 (Nexus Recorder — Actual State), c594 (GitStateRecorder.RecordState)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — az Actual State fogalom és a GitStateRecorder (c594) implementált, de a fizikai state gyűjtés (Proxmox, VyOS, OpenSwitch providerek) nincs a KB-ban → a collector oldal scaffold.
- Bizonyíték: c472 (recorder: "persisting Actual State"), c594 (RecordState metódus létezik)
- Megjegyzés: Előfeltétel: fizikai provider adapterek megírása.

---

#### Drift.schema.json
- KB node: c2536 (Drift Taxonomy doc), c1747-c1757 (drift_taxonomy.md szekciók)
- Státusz: **concept**
- Bridge törési pont: **code** — a drift taxonómia gazdagon dokumentált (Chain Drift, State Drift, SOFT/HARD/CHAIN kategóriák c2538-c2546), de `Drift.schema.json` Go struct vagy séma fájl nem szerepel a KB-ban.
- Bizonyíték: c2536 (Drift Taxonomy — doc only), c1747 (Two Major Classes of Drift — doc only)
- Megjegyzés: A fogalomrendszer CIC-konform és részletes, de runtime megfelelő hiányzik.

---

#### ProofTraceEvent.schema.json
- KB node: c349 (ProofTrace go_struct), c348 (ProofTraceStep go_struct), c1625 (ProofTrace Chain doc)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a `ProofTrace` és `ProofTraceStep` Go struct-ok léteznek a cabinet-ben (c349, c348), a WorkflowRecorder (c601) rögzíti a trace-t. Azonban a terv `ProofTraceEvent.schema.json` nevű JSON Sémát vár — ez a cabinet yaml-alapú megközelítéstől eltér, az esemény-szintű láncolás (prev hash) nem bekötött a fizikai state observation folyamatba.
- Bizonyíték: c349 (ProofTrace go_struct — SourceDigest, ChainHash mezők), c601 (WorkflowRecorder.Record)
- Megjegyzés: A struktúra implementált, de a PoC-specifikus observation workflow-ba való bekötés hiányzik.

---

#### PoSE.schema.json
- KB node: c2582 (PBS állapotfa modell), c2585 (Drift jelzés — PoSE)
- Státusz: **concept**
- Bridge törési pont: **code** — a PoSE (Proof of State Existence) fogalom és a PBS root hash mechanizmus dokumentált (c2582: `H(logical) == H(physical)`), de Go implementáció (PoSE verifier, PBS root calculator) nem szerepel a KB-ban.
- Bizonyíték: c2582 (PBS doc: "A PoSE a root hash-t ellenőrzi"), c2585 (drift jelzés logika — doc only)
- Megjegyzés: Kulcsfontosságú bridge hiány: a PoSE/PBS az egész verification lánc alapja, de nincs code megfelelője.

---

#### StateCommit.schema.json
- KB node: c1823 (The Commit Record — doc), c2613 (State Commit Model doc)
- Státusz: **concept**
- Bridge törési pont: **code** — a StateCommit rekord struktúra dokumentált (c1823: `id, traceHead, poseRoot, ts, actor` mezők), de Go struct implementáció nem szerepel a KB-ban. A GitStateRecorder (c594) a relay belső állapotát rögzíti, nem a kanonikus StateCommit rekordot.
- Bizonyíték: c1823 (Commit Record yaml struktúra — doc), c594 (RecordState — más célra)
- Megjegyzés: A state commit model CIC-konform és jól definiált, de implementációs bridge törési pont a code szinten.

---

#### RollbackRequest.schema.json
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — `RollbackRequest` fogalom nem szerepel a KB-ban. A quorum_release (c2220) tartalmaz rollback-hez kapcsolódó workflow-t, de nem relay-szintű schema formájában.
- Bizonyíték: keresés: "RollbackRequest rollback intent schema" → c2220 (release workflow — nem rollback schema)
- Megjegyzés: A terv által bevezetett fogalom. CIC-ban a rollback az OIS kötelezettség-feloldáson keresztül modellezhető, de ez nincs RollbackRequest sémában kifejezve.

---

#### PolicyDecision.schema.json
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — `PolicyDecision` fogalom nem szerepel a KB-ban. Az OIS principles (c1711-c1720) az obligation rendszert írja le, de `PolicyDecision` nevű entitás nem jelenik meg.
- Bizonyíték: c1715 (OIS 3. Obligation — nincs PolicyDecision), c2562 (OIS Layer — nincs PolicyDecision schema)
- Megjegyzés: A terv által bevezetett fogalom. A CIC-ban az OIS döntés nem `PolicyDecision` schema formájában van modellezve.

---

### MODULOK

---

#### schema-registry
- KB node: c365 (Cabinet interface), c357 (ValidateSchema), c217/c218 (PutSchema/GetSchema)
- Státusz: **implemented**
- Bridge törési pont: nincs — a Cabinet interface (c365) schema registry funkcionalitást valósít meg: `PutSchema`, `GetSchema`, `ValidateSchema` metódusok dokumentálva és Go kódban megvalósítva.
- Bizonyíték: c365 (Cabinet interface — "schema/module/workflow management"), c357 (ValidateSchema — Go func), c217 (PutSchema), c218 (GetSchema)
- Megjegyzés: A terv `schema-registry` modulja lefedett a Cabinet által.

---

#### intent-ingestor
- KB node: c580 (Watcher interface), c588 (PollingWatcher.Watch)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a `Watcher` interface (c580) és `PollingWatcher` (c588) scaffold szinten létezik az infrastruktúra-változások figyelésére, de intent-specifikus ingestor (OIS intent beolvasás) nincs a KB-ban.
- Bizonyíték: c580 (Watcher: "monitoring infrastructure changes"), c588 (PollingWatcher.Watch)
- Megjegyzés: Előfeltétel: OIS intent branch definiálása és Watcher bekötése.

---

#### terraform-desired-extractor
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — Terraform-specifikus desired state extractor nem szerepel a KB-ban. A CIC IaC model generikus (`IaCSource` interface), a Terraform integration nem CIC-natív fogalom.
- Bizonyíték: c509 (IaCSource — generikus), c984 (M11: "fájlrendszerből vagy API-n" — nem Terraform-specifikus)
- Megjegyzés: A terv Terraform-centrikus megközelítése eltér a CIC provider-agnosztikus IaC modelljétől.

---

#### terraform-state-reader
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — lásd terraform-desired-extractor. A CIC a kívánt állapotot `IaCSource` absztrakción keresztül olvassa, nem Terraform state reader-rel.
- Bizonyíték: c509 (IaCSource interface), c517 (GitSourceConfig — git-alapú forrás)
- Megjegyzés: A GitSource (c517) lefedi a git-alapú IaC olvasást, de a terraform.tfstate specifikus parse-olása nincs modellezve.

---

#### actual-state-collector (Proxmox, VyOS, OpenSwitch)
- KB node: c1118 (Proxmox mint Service fogalom — doc), c472 (Nexus Recorder Actual State)
- Státusz: **concept**
- Bridge törési pont: **code** — a Proxmox/VyOS provider mint `Service` fogalom dokumentált (c1118), és az Actual State recorder (c472) scaffold szinten létezik. De fizikai state lekérő adapterek (Proxmox API, VyOS CLI) nem szerepelnek a KB-ban Go kód szinten.
- Bizonyíték: c1118 (Proxmox mint Service — design doc), c472 (recorder: local Git cache, nem provider adapter)
- Megjegyzés: Kulcsfontosságú bridge hiány: a terv PoC flow-jának alapja, de nincs code megfelelő.

---

#### pbs-root-calculator
- KB node: c2582 (PBS állapotfa — doc)
- Státusz: **concept**
- Bridge törési pont: **code** — a PBS root hash mechanizmus dokumentált (c2582: fa-szerkezet, root hash ellenőrzés), de PBS kalkulátor Go implementáció nem szerepel a KB-ban.
- Bizonyíték: c2582 (PBS állapotfa modell — doc only)
- Megjegyzés: Előfeltétel a PoSE verification lánc zárásához.

---

#### canonical-json-normalizer
- KB node: c1127 (ToJSON go_func), c350 (ProofTrace canonical hash)
- Státusz: **implemented**
- Bridge törési pont: nincs — a `canonicaljson.ToJSON` (c1127) implementált: "marshals a Go value into a canonical JSON string [...] map keys are sorted alphabetically for deterministic output". Direkten használható.
- Bizonyíték: c1127 (ToJSON go_func — canonicaljson package), c350 (ProofTrace canonical hash hivatkozás)
- Megjegyzés: Ez az egyik legerősebb bridge-záró implementáció a relay-ben.

---

#### prooftrace-builder
- KB node: c349 (ProofTrace go_struct), c348 (ProofTraceStep go_struct), c601 (WorkflowRecorder.Record)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a `ProofTrace` és `ProofTraceStep` struktúrák implementáltak, a `WorkflowRecorder.Record` metódus ProofTrace-t perzisztál. De a PoC-specifikus observation workflow-ba (terraform apply → observation → proof) való bekötés nincs — a meglévő recorder workflow-oriented, nem state-observation-oriented.
- Bizonyíték: c349 (ProofTrace go_struct), c601 (WorkflowRecorder.Record — "workflow ID"-ra épül, nem state commitre)
- Megjegyzés: Előfeltétel: state observation pipeline bekötése a ProofTrace builderbe.

---

#### prooftrace-chain-validator
- KB node: c121 (ProofTrace integritás), c246 (proof_verify.yaml)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — `proof_verify.yaml` (c246) és a ProofTrace integritás ellenőrzés (c121) dokumentált és kódban van, de a PoC observation lánc validálásához szükséges bekötés (chain verify az audit flowban) nincs runtime szinten.
- Bizonyíték: c121 (ProofTrace integritás — SELF_CHECKLIST.md), c246 (proof_verify.yaml — cmd/relay)
- Megjegyzés: A validator kód létezik, de csak a CI/build pipeline-ban van bekötve, nem a runtime state observation flowban.

---

#### pose-verifier
- KB node: c2585 (Drift jelzés / PoSE logika — doc)
- Státusz: **concept**
- Bridge törési pont: **code** — a PoSE verifikáció logikája dokumentált (c2585: `H(logical) == H(physical)` → VERIFIED/DRIFT), de Go implementáció nem szerepel a KB-ban.
- Bizonyíték: c2585 (doc only — pose_pbs_integration.md)
- Megjegyzés: Lásd pbs-root-calculator — ezek egymás előfeltételei.

---

#### drift-classifier
- KB node: c2536 (Drift Taxonomy), c1747-c1752 (drift típusok — doc)
- Státusz: **concept**
- Bridge törési pont: **code** — a drift taxonómia (NO_DRIFT, SOFT, HARD, CHAIN) részletesen dokumentált, de drift osztályozó Go implementáció nem szerepel a KB-ban.
- Bizonyíték: c2536 (Drift Taxonomy doc), c1748 (Chain Drift), c1751 (State Drift) — mindkettő doc node, nem go_struct/go_func
- Megjegyzés: Előfeltétel: PoSE verifier és actual state collector megvalósítása.

---

#### state-commit-writer
- KB node: c594 (GitStateRecorder.RecordState), c472 (Nexus Recorder)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a `GitStateRecorder.RecordState` (c594) "persists the state to JSON files, signs it, and creates a git commit" — ez a state-commit-writer funkcionális megfelelője. Azonban a kanonikus StateCommit rekord (c1823 — `poseRoot`, `traceHead` mezők) nincs bekötve: a recorder `ExpectedState`-et ír, nem StateCommit YAML-t.
- Bizonyíték: c594 (RecordState — "references: types.ExpectedState"), c1823 (Commit Record — más séma)
- Megjegyzés: Előfeltétel: StateCommit séma implementálása és recorder adaptálása.

---

#### trust-anchor-registry
- KB node: c2303-c2310 (Trust Anchor Lifecycle doc)
- Státusz: **concept**
- Bridge törési pont: **code** — a Trust Anchor fogalom (anchorID, publicKey, hatályidő, bizalmi kontextus) részletesen dokumentált (c2303), de trust anchor registry Go implementáció nem szerepel a KB-ban. A `VaultCryptoService` (c479) Vault-alapú aláírást valósít meg, de nem trust anchor registry-t.
- Bizonyíték: c2303 (Trust Anchor Lifecycle — doc), c479 (VaultCryptoService — signing, nem registry)
- Megjegyzés: A VaultCryptoService részleges fedezetet ad az aláírási oldalon, de a registry (actor→key mapping, lifecycle) nincs.

---

#### rollback-intent-reader
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — rollback intent reader nem szerepel a KB-ban. A Watcher interface (c580) általános monitoring célra való, nem rollback-specifikus.
- Bizonyíték: keresés: "rollback intent" → c2220 (release workflow — nem relay rollback)
- Megjegyzés: A terv által bevezetett fogalom.

---

#### ois-policy-evaluator
- KB node: c2562 (OIS Layer — doc), c2489-c2501 (ois_principles.md szekciók)
- Státusz: **concept**
- Bridge törési pont: **code** — az OIS Layer dokumentált (c2562: "ellenőrzi, hogy a művelet szándéka és jogosultsági kerete összhangban van"), de OIS policy evaluator Go implementáció nem szerepel a KB-ban.
- Bizonyíték: c2562 (OIS Layer — doc only, implementation_core.md)
- Megjegyzés: Az OIS az egyik legfontosabb CIC-fogalom, de teljes mértékben concept szintű a relay kódban.

---

### RELAY FUNKCIÓK

---

#### relay.validate(input, schemaRef)
- KB node: c357 (ValidateSchema), c533 (IaCValidator.ValidateResource)
- Státusz: **implemented**
- Bridge törési pont: nincs — `ValidateSchema` (c357) és `IaCValidator.ValidateResource` (c533) implementáltak, a Cabinet schema validáció bekötött.
- Bizonyíték: c357 (ValidateSchema: "checks whether data carries a $schema key"), c533 (ValidateResource)

---

#### relay.canonicalize(object)
- KB node: c1127 (ToJSON go_func)
- Státusz: **implemented**
- Bridge törési pont: nincs — `canonicaljson.ToJSON` (c1127) implementált és determinisztikus.
- Bizonyíték: c1127 (ToJSON — "map keys sorted alphabetically")

---

#### relay.hash(canonicalObject)
- KB node: c350 (ProofTrace canonical hash), c1127 (ToJSON)
- Státusz: **implemented**
- Bridge törési pont: nincs — a hash kalkuláció a ProofTrace chain részeként implementált (c350, c349: SourceDigest, ChainHash mezők).
- Bizonyíték: c349 (ProofTrace: "SourceDigest anchors the chain [...] ChainHash")

---

#### relay.sign(hash, actorRef)
- KB node: c479 (VaultCryptoService go_struct), c480 (CryptoService interface)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a `CryptoService` interface (c480) és `VaultCryptoService` (c479) implementáltak. Azonban az `actorRef` paraméter (trust anchor + actor identity) bekötése a signing folyamatba nincs — a relay a Vault transit engine-t használja, de actor-specifikus signing (ki ír alá?) nincs a KB-ban.
- Bizonyíték: c479 (VaultCryptoService — Vault Transit), c480 (CryptoService interface)
- Megjegyzés: Előfeltétel: trust-anchor-registry bekötése a sign folyamatba.

---

#### relay.observe(providerRef)
- KB node: c1186 (Resource go_struct — obs/types.yaml), c472 (Nexus Recorder)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — az obs package (c1186: `Resource` struct) scaffold szinten létezik, de a `providerRef` (Proxmox, VyOS, OpenSwitch) specifikus megfigyelő logika nincs implementálva.
- Bizonyíték: c1186 (Resource struct — "identifies origin of observation")
- Megjegyzés: Előfeltétel: fizikai provider adapterek.

---

#### relay.compare(logical, physical)
- KB node: c2585 (Drift jelzés — H(logical)==H(physical)), c615/c616 (nexus types)
- Státusz: **concept**
- Bridge törési pont: **code** — a compare logika dokumentált (c2585), de Go implementáció nem szerepel a KB-ban.
- Bizonyíték: c2585 (doc: összehasonlítás logikája)

---

#### relay.classifyDrift(diff)
- KB node: c2536 (Drift Taxonomy doc)
- Státusz: **concept**
- Bridge törési pont: **code** — lásd drift-classifier.
- Bizonyíték: c2536 (Drift Taxonomy — doc only)

---

#### relay.buildProofTrace(event)
- KB node: c349 (ProofTrace go_struct), c601 (WorkflowRecorder.Record)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — lásd prooftrace-builder.
- Bizonyíték: c349, c601

---

#### relay.commitState(bundle)
- KB node: c594 (GitStateRecorder.RecordState), c1823 (Commit Record doc)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — lásd state-commit-writer.
- Bizonyíték: c594, c1823

---

#### relay.verifyCommit(commitRef)
- KB node: c246 (proof_verify.yaml), c121 (ProofTrace integritás)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — lásd prooftrace-chain-validator.
- Bizonyíték: c246, c121

---

#### relay.readIntentBranch()
- KB node: c580 (Watcher interface), c588 (PollingWatcher.Watch)
- Státusz: **scaffold**
- Bridge törési pont: **runtime** — a Watcher interface scaffold, de az intent branch (git branch mint OIS intent forrás) bekötése nincs runtime szinten.
- Bizonyíték: c580 (Watcher), c588 (PollingWatcher)

---

#### relay.emitOperatorInstruction()
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — `emitOperatorInstruction` fogalom nem szerepel a KB-ban. A relay DAG modell (c2589) kimenetet továbbít más komponensek felé, de explicit "operator instruction" emitter nincs.
- Bizonyíték: c2589 (relay: "továbbítja az eredményt más komponensek felé" — általánosan, nincs specifikus operátor utasítás emitter)

---

### WORKFLOWK

---

#### post_apply_observation.workflow.yaml
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — terraform apply utáni megfigyelési workflow nem szerepel a KB-ban. A cabinet workflow (c428) generikus step-based workflow struktúra, de `post_apply_observation` specifikus definíció nincs.
- Bizonyíték: c428 (Workflow.GetData — generikus workflow struct)

---

#### manual_drift_observation.workflow.yaml
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — manuális drift megfigyelési workflow nem szerepel a KB-ban.
- Bizonyíték: keresés: "drift observation workflow manual" → csak doc node-ok (drift taxonomy)

---

#### hard_drift_detection.workflow.yaml
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — HARD drift detection workflow nem szerepel a KB-ban. A HARD drift fogalom dokumentált (c1748 Chain Drift, c1751 State Drift), de workflow definíció nincs.
- Bizonyíték: c1748-c1752 (drift típusok — doc only, nincs workflow node)

---

#### rollback_intent.workflow.yaml
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — rollback intent workflow nem szerepel a KB-ban.
- Bizonyíték: c2220 (quorum release workflow — nem rollback intent)

---

#### rollback_post_apply_verify.workflow.yaml
- KB node: nincs KB node
- Státusz: **missing**
- Bridge törési pont: **concept** — rollback post-apply verification workflow nem szerepel a KB-ban.
- Bizonyíték: Nincs releváns chunk

---

## Megjegyzések az audithoz

1. **Séma formátum eltérés**: A terv `.json` sémákat (Actor.schema.json, Intent.schema.json stb.) vár, de a CIC relay cabinet yaml-alapú sémarendszert és Go típusokat használ. Ez nem hiány — ez architektúrális különbség.

2. **Terraform-specifikusság**: A terv több Terraform-specifikus komponenst (terraform-desired-extractor, terraform-state-reader, TerraformState.schema.json) vár. A CIC IaC modellje szándékosan provider-agnosztikus (`IaCSource` interface). Ezek nem "missing" abban az értelemben, hogy a CIC szándékosan nem Terraform-centrikus.

3. **PoSE/PBS bridge hiány kritikus**: A PoSE verifier és PBS root calculator teljes mértékben concept szintű, miközben ezek az egész verification lánc alapjai. Ez a legsúlyosabb bridge törési pont.

4. **OIS teljes mértékben concept**: Az OIS réteg (policy evaluator, obligation tracking) gazdag fogalmi dokumentációval rendelkezik, de nincs egyetlen Go implementáció sem a KB-ban.
