# Komponens státusz mátrix — CIC PoC

KB chunk ID-k minden állítás mögött.

---

## Háromszintű státusz definíció

| Státusz | Jelentés |
|---|---|
| **implemented** | kódban él, tesztek fedik, CI zöld |
| **scaffold** | kódban van, de szándékosan bekötetlen — előfeltétel hiányzik |
| **concept** | dokumentált, de még nincs runtime megfelelője |

---

## Komponens státusz táblázat

| Komponens | Státusz | KB bizonyíték | Megjegyzés |
|---|---|---|---|
| **CIC-Relay mag (Go)** | implemented | c899, c900, c906 | plugin.Open() + Lookup(), .so betöltés működik |
| **Relay workflow engine** | implemented | c189, c927 | cic.schema.compile workflow beágyazva, NextHops/StateRequirement kiértékelés |
| **ProofTrace lánc** | implemented | c244, c263, c2436, c2564 | ProofArtifactCommit struct, proof_artifact.schema.yaml, SHA-256 láncolás |
| **GitStateRecorder** | implemented | c590, c600 | GitStateRecorder struct, WorkflowRecorder — git alapú állapottárolás |
| **Drift detekció (SOFT/RECONCILIABLE/HARD)** | implemented | c1815, c2543, c2618 | drift taxonomy dokumentált és kódilag hivatkozott |
| **OIS formális modell** | implemented | c2498, c2836, c2842 | OIS(actor, action, context) formális leírás, intent/obligation szétválasztás |
| **Schema validáció (relay)** | implemented | c927, c1803 | StateRequirement kiértékelés, schema-alapú validáció relay szinten |
| **ManagedEntity primitív** | implemented | c2801, c2672 | managed-entity.yaml — config_surface, state_surface, lifecycle_surface |
| **cic-primitives meta-séma réteg** | implemented | c2672, c2765 | 7 atomi primitív, sealed/defaulted/required slot contract |
| **IaC git state branch** | implemented | c1120, c517 | desired/actual state szétválasztás, GitSourceConfig struct |
| **schemapipeline (4-lépéses build)** | implemented | c453 | start/test/validate/release native relay modulok |
| **schemacompile (assert/build/sign)** | scaffold | c442 | cic.source.assert stub mode (chain verify nincs), cic_sign="unavailable" Vault nélkül |
| **CICSourceCA Vault signing** | scaffold | c442, c1312 | Layer 2 — cic_signed_ca="stub:pending", Vault nem bekötve |
| **PoSE (Proof of State Existence)** | scaffold | c263 | pose_result mező létezik a sémában, de SKIPPED a default |
| **WASM iSDK (host+guest)** | concept | c940, c943, c947 | API-szerződés dokumentált, v1 szinkron spec kész — runtime nincs |
| **OIS policy motor (obligation check)** | concept | c2498 | formális modell kész, runtime obligation engine nincs implementálva |
| **Rollback trigger (intent/ ág figyelő)** | concept | add.md 8.4 | git push intent/main → Terraform apply — nincs kész runtime hook |
| **PBS (Physical Base State) integráció** | concept | c2585, c2616 | pbs_root_hash a commit modellben szerepel, PBS snapshot tool nincs |
| **Terraform plugin (.so)** | concept | add.md 8.1 | terraform_observer plugin nincs megírva |
| **Drift → reconcile workflow** | concept | c1815, c1824 | „repair workflow" definiált, relay workflow nincs megírva |
| **ProofNode / licenc érvényesítés** | concept | add.md 5. | CICmeta valuta, licenc relay — nincs runtime implementáció |

---

## Bridge térkép

```
concept → code → runtime → audit
```

### Hol szakad meg a lánc?

| Komponens | concept | code | runtime | audit | Megszakad itt |
|---|---|---|---|---|---|
| Relay workflow engine | ✓ | ✓ | ✓ | ✓ | — (kész) |
| ProofTrace | ✓ | ✓ | ✓ | ✓ | — (kész) |
| GitStateRecorder | ✓ | ✓ | ✓ | ✓ | — (kész) |
| Drift detekció | ✓ | ✓ | partial | ✓ | runtime (reconcile flow nincs) |
| schemacompile | ✓ | ✓ | stub | — | runtime → audit (Vault nincs) |
| WASM iSDK | ✓ | — | — | — | code (nincs Go implementáció) |
| OIS obligation engine | ✓ | — | — | — | code |
| Rollback trigger | ✓ | — | — | — | code |
| PBS integráció | ✓ | partial | — | — | runtime |
| Terraform plugin | ✓ | — | — | — | code |

**Scaffold határvonal:** az schemacompile és schemapipeline kódban él, de Vault / CICSourceCA nélkül stub módban fut. Ez szándékos — a trust layer landing előfeltétele.

---

## Prioritás a PoC-hoz

A demonstrációhoz minimálisan szükséges implementált elemek:

1. **Terraform observer plugin (.so)** — concept → code (legmagasabb prioritás)
2. **Rollback trigger** — intent/ ág figyelő + Terraform apply hívás
3. **PBS snapshot tool** — aktuális infra állapot hash-elése
4. **OIS obligation check** — minimális policy motor (demo policy: allow all)
5. **PoSE aktiválás** — SKIPPED → VERIFIED mód

A WASM iSDK és ProofNode licenc a PoC v1-hez nem szükséges.
