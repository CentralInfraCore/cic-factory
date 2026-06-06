# Komponens státusz mátrix — PoC v1

**Módszer:** KB-alapú, minden állítás chunk ID-val alátámasztva.
**Forrás:** CIC-Relay CLAUDE.md, relay_pozicionalas.md, plugin_interface.md, wasm_isdk.md, cabinet/*.go

---

## Relay core

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| relay binary (Go) | **implemented** | c49 (README.md): `make build && ./output/<commit>/cic-relay`, `RELAY_URL=http://localhost:8080 make test-api` | Futtatható, API tesztelhető |
| cabinet/proof_trace.go | **implemented** | c347: `ProofTraceStep, ProofTrace, hashValue, computeChainHash` — Go csomag KB-ban dokumentálva | Kriptografikus lánc kész |
| cabinet/plugin.go | **implemented** | c346: `package cabinet / plugin.go` — Go csomag létezik | Plugin betöltési logika |
| ProofArtifact / VerifyProofArtifact | **implemented** | c241: `cmd/relay/proof_verify.go` — `ProofArtifact`, `VerifyProofArtifact`, `MarshalProofArtifact` | Verifikáló pipeline kész |
| Workflow YAML loader | **implemented** | c171: `WorkflowFile` struct, bootstrap.yaml | Workflow definíció betöltés |
| Schema pipeline (schemapipeline) | **implemented** | c459: `core/modules/schemapipeline/schemapipeline.yaml` | Séma-validáció modul |
| StateRequirement kiértékelés | **implemented** | c927: relay kiértékeli a `StateRequirement` mezőt a plugin válasza alapján | Állapotellenőrzés a gráfban |
| NextHops traversal | **implemented** | c912: relay `NextHops` mezők alapján továbbhalad | Gráf-bejárás |
| core.ping lépés | **implemented** | c190: `default.yaml` — `core.ping@1.0.0` beágyazott workflow | Alapértelmezett beépített lépés |

---

## Plugin réteg

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| Plugin .so betöltés (plugin.Open/Lookup) | **implemented** | c906: `go build -buildmode=plugin`, `plugin.Open()` + `Lookup()` | Go plugin API kész |
| Plugin descriptor regisztráció | **implemented** | c788: "Plugins are discovered and registered via descriptors, not loaded eagerly" | Lazy betöltési minta |
| terraform-apply plugin | **concept** | Nincs .so implementáció, csak add.md-ben leírt szándék | PoC-hoz létrehozandó |
| drift-detector plugin | **concept** | c1120: state ág logika leírva, de plugin nincs | PoC-hoz létrehozandó |
| ois-validator plugin | **concept** | c2836: OIS elv dokumentált, relay integráció nincs | PoC-hoz létrehozandó |
| state-commit plugin | **concept** | c1120: "Actual State → külön Git ág" — de auto commit plugin nincs | PoC-hoz létrehozandó |
| rollback intent plugin | **concept** | add.md 8.4 fázis leírja, nincs implementáció | PoC-hoz létrehozandó |

---

## WASM réteg

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| WASM iSDK koncepció | **concept** | c940: `wasm_isdk.md` — "Defines the concept and contract..." | Dokumentált, nincs runtime |
| Host frame (WASM executor) | **concept** | c943: "Host keret: diszpécser hívásait WASM-hívássá alakítja" — csak dokumentum szinten | Implementációs bridge hiányzik |
| iSDK guest SDK könyvtár | **concept** | c943: "iSDK (guest/wasm oldali SDK): a WASM modulba linkelt könyvtár" | Nincs Go/WASM csomag |

---

## PKI / Vault / Aláírás

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| commit-signing (GPG/Ed25519) | **implemented** | c724, c1002: `commit-signing.md` — `git verify-commit`, PEM export | cic-factory commit hook aktív |
| pki_verify.go bekötése | **scaffold** | c10 (CLAUDE.md): "scaffold — CICRootCA → Intermediate CA → leaf cert bootstrap" | Előfeltétel: CA lánc |
| Vault(mem) integráció | **concept** | add.md v1 spec: "Vault(mem)" — nincs relay runtime bekötés | PoC v1-hez szükséges |
| Vault-sign-agent | **implemented** | c1230: vault-sign-agent.md — több repo-ban dokumentált | Aláírási tool elérhető |
| CICRootCA lánc | **concept** | c10: "CICRootCA → Intermediate CA → leaf cert" — előfeltétel a pki_verify-hoz | Bootstrapelni kell |

---

## IaC / Állapot réteg

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| IaC ontológia és tervezési elvek | **implemented** | c1114, c1120: `iac_ontology_and_design.md` — desired/actual state szétválasztás | Dokumentált és specifikált |
| Git state ág (desired/actual) | **concept** | c1120: "Actual State → külön Git ág, ahová a rendszer visszaírja a mért adatokat" — nincs automatizmus | Manuálisan kell létrehozni |
| Drift típusok (SOFT/RECONCILIABLE/HARD) | **concept** | add.md 8.2, 8.3 fázis — drift típusok definiáltak, detektálás nincs implementálva | plugin szintű munka |
| PoSE (Proof of State Existence) | **concept** | add.md 4. rész: "PoSE integráció" — ProofTrace + PBS snapshot egységbe fogása | PBS nincs PoC v1-ben |
| PBS (Physical Backup System) | **concept** | add.md: "PBS deduplikált, időbélyeges mentések" — v2+ elem | PoC v1-ben kihagyható |

---

## OIS / Quorum réteg

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| OIS elvek (Intent, Obligation, Policy) | **concept** | c2836, c2498: OIS dokumentáció, nincs relay runtime bridge | Csak dokumentum szinten |
| quorum döntési réteg | **concept** | c10 (CLAUDE.md): "concept — nincs runtime megfelelő" | PoC v1-ben nem szükséges |
| CICmeta protocol | **concept** | c10 (CLAUDE.md): "concept — nincs élő bridge a Relay runtime-hoz" | v2+ elem |
| LocalWorker in-process | **scaffold** | c10 (CLAUDE.md): "scaffold — 3-process isolation + Vault" | Előfeltétel: Vault bekötés |
| UpstreamSource | **scaffold** | c10 (CLAUDE.md): "scaffold — relay federáció (v2)" | v2 elem |

---

## Összesítés

| Kategória | Implemented | Scaffold | Concept |
|---|---|---|---|
| Relay core | 9 | 0 | 0 |
| Plugin réteg | 2 | 0 | 5 |
| WASM réteg | 0 | 0 | 3 |
| PKI / Vault | 2 | 1 | 2 |
| IaC / Állapot | 1 | 0 | 4 |
| OIS / Quorum | 0 | 2 | 3 |
| **Összesen** | **14** | **3** | **17** |

**Kritikus megállapítás:** A relay core stabil és implemented. A PoC v1 fő munkája a **plugin réteg** (5 concept → implemented), a **IaC state ág** automatizálása, és a **Vault(mem) bekötése**. A WASM réteg PoC v1-ben kihagyható — `.so` plugin alapú végrehajtás elegendő.
