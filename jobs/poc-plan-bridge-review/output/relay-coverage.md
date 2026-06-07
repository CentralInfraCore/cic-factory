# Relay Meglévő Képességek Térképe — PoC lefedettség

> Kérdés: a meglévő relay képességek lefedik-e a terv relay funkcióit?
> Ha igen — nem kell újat írni, csak bekötni (scaffold → implemented).

---

## Összefoglaló

| Relay képesség | Meglévő relay komponens | Lefedettség |
|---|---|---|
| validate | Cabinet.ValidateSchema + IaCValidator | **teljes** |
| canonicalize | canonicaljson.ToJSON | **teljes** |
| hash | ProofTrace ChainHash | **teljes** |
| sign | VaultCryptoService | **részleges** (actor binding hiányzik) |
| observe | obs/types.Resource + Nexus Recorder | **részleges** (provider adapterek hiányoznak) |
| compare | — | **nincs** |
| classifyDrift | — | **nincs** |
| buildProofTrace | ProofTrace struct + WorkflowRecorder | **részleges** (observation bekötés hiányzik) |
| commitState | GitStateRecorder.RecordState | **részleges** (StateCommit séma eltér) |
| verifyCommit | proof_verify + ProofTrace integritás | **részleges** (runtime flow bekötés hiányzik) |
| readIntentBranch | Watcher interface (PollingWatcher) | **részleges** (intent branch nincs definiálva) |
| emitOperatorInstruction | — | **nincs** |

---

## Implementált relay képességek — nem kell újraírni

### 1. Schema validáció (`relay.validate`)

**Meglévő kód:** `core/cabinet/schema_validate.go`
- `ValidateSchema` (c357): ellenőrzi a `$schema` kulcsot az elfogadott sémaIDk ellen
- `IaCValidator.ValidateResource` (c533): ResourceSpec validálása a Cabinet sémaregiszter ellen
- `Cabinet` interface (c365): `PutSchema`, `GetSchema`, `ValidateSchema` metódusok

**PoC lefedettség:** A terv `relay.validate(input, schemaRef)` funkciója teljesen lefedett. Csak a PoC-specifikus sémák (Actor, Intent stb.) regisztrálása szükséges a Cabinet-be — ez konfiguráció, nem új kód.

---

### 2. Kanonikus JSON (`relay.canonicalize`)

**Meglévő kód:** `pkg/canonicaljson/canonicaljson.go`
- `ToJSON` (c1127): determinisztikus JSON marshal, ábécé-rendezett map kulcsok

**PoC lefedettség:** Teljes. A `canonical-json-normalizer` modul már létezik.

---

### 3. Hash kalkuláció (`relay.hash`)

**Meglévő kód:** `core/cabinet/proof_trace.go`
- `ProofTrace.SourceDigest` és `ChainHash` (c349): a lánc hash mechanizmusa implementált

**PoC lefedettség:** Teljes a ProofTrace-en belül. Önálló hash utility szükséges lehet a PBS root hash kalkulációhoz — ez a pbs-root-calculator komponens.

---

### 4. Git-alapú state rögzítés (`relay.commitState` részben)

**Meglévő kód:** `core/nexus/recorder/recorder.go`
- `GitStateRecorder.RecordState` (c594): JSON fájlokba írja, aláírja, és git commitot hoz létre
- `WorkflowRecorder.Record` (c601): ProofTrace-t perzisztál workflow ID alapján

**PoC lefedettség:** Részleges. A mechanizmus adott, de a PoC StateCommit rekord (c1823: `poseRoot`, `traceHead`, `actor` mezők) nem azonos a jelenlegi `ExpectedState` formátummal. Adaptáció szükséges, nem új komponens.

---

### 5. Kriptográfiai aláírás (`relay.sign` részben)

**Meglévő kód:** `core/nexus/crypto/service.go`
- `CryptoService` interface (c480): signing és decrypt metódusok
- `VaultCryptoService` struct (c479): HashiCorp Vault Transit engine implementáció

**PoC lefedettség:** Részleges. Az aláírási mechanizmus létezik. Hiányzik az actor-specifikus bekötés: melyik actor (actorRef) melyik Vault kulcsot használja. Ez a trust-anchor-registry bridge hiánya.

---

### 6. IaC forrás olvasás (`relay.readIntentBranch` részben)

**Meglévő kód:** `core/nexus/iac/`
- `IaCSource` interface (c509): generikus konfigurációs adat lekérő
- `GitSourceConfig` struct (c517): git-alapú forrás konfiguráció

**PoC lefedettség:** Részleges. A git-alapú IaC olvasás megvan. Az "intent branch" (OIS intent mint git branch) koncepció nincs explicit bekötve — a Watcher (c580/c588) infrastruktúra változásokat figyel, nem OIS intent brancht.

---

### 7. ProofTrace felépítés (`relay.buildProofTrace` részben)

**Meglévő kód:** `core/cabinet/proof_trace.go`
- `ProofTrace` struct (c349): immutable audit rekord, SourceDigest, ChainHash
- `ProofTraceStep` struct (c348): egyedi lépés kriptográfiai lábnyoma
- `WorkflowRecorder.Record` (c601): ProofTrace perzisztálás

**PoC lefedettség:** Részleges. A ProofTrace struktúra és a rögzítési mechanizmus implementált. A PoC-specifikus `ProofTraceEvent` (egy observation esemény trace-je, nem egy teljes workflow trace) bekötése szükséges.

---

### 8. ProofTrace lánc verifikáció (`relay.verifyCommit` részben)

**Meglévő kód:** `cmd/relay/proof_verify.yaml` (c246), `ai/SELF_CHECKLIST.md` (c121)
- A proof verify parancs létezik relay CLI szinten

**PoC lefedettség:** Részleges. A verifikáció a build/CI pipeline-ban bekötött. A runtime state observation flow audit lánca (verifyCommit a PoC deploymentben) nincs bekötve.

---

### 9. Infrastruktúra megfigyelés (`relay.observe` részben)

**Meglévő kód:** `core/nexus/operator/watcher.go`, `pkg/obs/types.go`
- `Watcher` interface (c580): infrastruktúra változások monitorozása
- `PollingWatcher.Watch` (c588): polling alapú megfigyelés
- `Resource` struct (c1186): observation forrás azonosítása

**PoC lefedettség:** Részleges. A megfigyelési infrastruktúra scaffold szinten megvan. Hiányoznak a provider-specifikus adapterek (Proxmox API, VyOS CLI, OpenSwitch NETCONF).

---

## Amit valóban meg kell írni (nincs relay fedezet)

### Kritikus (PoC flow nem indítható nélkülük)

| Komponens | Miért kritikus | Becsült munka |
|---|---|---|
| `actual-state-collector` (Proxmox/VyOS adapterek) | A fizikai állapot lekérése nélkül az observe→compare→drift lánc nem indul | új kód — provider adapterek |
| `pbs-root-calculator` | A PoSE verification (H(logical)==H(physical)) alapja | új kód — hash fa kalkulátor |
| `pose-verifier` | A drift detekció logikája | új kód — compare + classify |
| `drift-classifier` | SOFT/HARD/CHAIN drift kategorizálás | új kód — taxonomy implementáció |

### Fontos (PoC hiányos nélkülük)

| Komponens | Miért fontos | Megjegyzés |
|---|---|---|
| `StateCommit` séma adaptáció | A `poseRoot` és `traceHead` mezők hiányoznak a recorder-ből | meglévő recorder adaptálása |
| `trust-anchor-registry` | Actor→key mapping az aláíráshoz | új komponens, de Vault fedezi a signing részt |
| OIS layer (intent validation) | A terv OIS decision-t vár | concept szintű, PoC-ban opcionálisan kihagyható |

### Alacsony prioritás (PoC futhat nélkülük)

| Komponens | Megjegyzés |
|---|---|
| Workflowk (yaml fájlok) | A relay cabinet workflow struktúra adott, ezek konfigurációs fájlok |
| `rollback-intent-reader` | PoC scope-on kívül lehet |
| `ois-policy-evaluator` | PoC-ban mockolt döntéssel helyettesíthető |

---

## Relay lefedettség összegzés

A meglévő relay a következőket **nem kell újraírni** a PoC-hoz:
- Schema validáció (Cabinet)
- Kanonikus JSON (canonicaljson)
- Hash kalkuláció (ProofTrace chain hash)
- Git state rögzítés (GitStateRecorder) — adaptálandó
- Vault signing (VaultCryptoService) — actor binding hiányzik
- IaC git olvasás (GitSource) — intent branch bekötés hiányzik
- ProofTrace struktúra és recorder — observation bekötés hiányzik

A PoC legkritikusabb nyitott munkája:
**fizikai state collector adapterek + PBS/PoSE implementáció** — ezek nélkül az observation→verify lánc nem zárható.
