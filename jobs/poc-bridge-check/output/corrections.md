# Bridge Térkép Korrekciók

> Ez a fájl kizárólag az INCORRECT és PARTIAL ítéletű állításokat tartalmazza.
> Forrás: `check-report.md`

---

## INCORRECT állítások

---

### schema-registry — c217 (PutSchema) és c218 (GetSchema) hivatkozások

**Állítás a bridge-map.md-ben:**
```
#### schema-registry
- KB node: c365 (Cabinet interface), c357 (ValidateSchema), c217/c218 (PutSchema/GetSchema)
- Státusz: implemented
- Bizonyíték: c365 (Cabinet interface), c357 (ValidateSchema), c217 (PutSchema), c218 (GetSchema)
```

**Hiba:**
A `c217` és `c218` chunk-ok **nem** a Cabinet interface valódi metódusait tartalmazzák.

- `c217` → `mockCabinetService.PutSchema` — forrás: `cmd/relay/main_test_helper.yaml` (test helper)
- `c218` → `mockCabinetService.GetSchema` — forrás: `cmd/relay/main_test_helper.yaml` (test helper)

Ezek test mock implementációk, nem a production Cabinet interface metódusai.

**Helyes hivatkozás:**
A valódi Cabinet interface: `c365` (go_interface, `core/cabinet/service.yaml`) — "defines the central API for schema/module/workflow management". A Cabinet interface tartalmazza a PutSchema/GetSchema/ValidateSchema metódusokat, de ezek a KB-ban külön chunk-ként a mock implementáción keresztül vannak indexelve, nem a tényleges interface definícióból.

**Státusz-hatás:**
A `schema-registry` implemented státusza tartalmilag helyes (a Cabinet valóban végzi a schema regisztrációt — c365 alátámasztja), de a `c217`/`c218` bizonyíték-hivatkozások félrevezetők. A korrekt bizonyíték: c365 (Cabinet interface) és c357 (ValidateSchema go_package).

---

## PARTIAL állítások

---

### ValidateSchema (c357) — node típus eltérés

**Állítás a bridge-map.md-ben:** c357 típusa = `go_func`

**Valóság:** `get_chunk("c357")` → típus: `go_package` (nem `go_func`)

**Forrás:** `core/cabinet/schema_validate.yaml` — a chunk az egész package-t lefedi (`ValidateSchema` és `validateInputSchema` is benne van).

**Státusz-hatás:** Az implemented státusz tartalmilag helyes. A hibás típus-hivatkozás nem változtat a státuszon, de a node típus pontatlan.

---

### relay.validate — c217/c218 hivatkozás

**Állítás a relay-coverage.md-ben és bridge-map.md-ben:**
A schema-registry és relay.validate bizonyítékainál c217/c218 szerepel mint Cabinet PutSchema/GetSchema implementáció.

**Valóság:** Lásd fent — mock metódusok.

**Státusz-hatás:** A `relay.validate` implemented státusza helyes. A bizonyíték-hivatkozások pontosítandók: c365 (Cabinet interface) a helyes forrás.

---

### relay.verifyCommit (c246) — PoSE és StateCommit tartalom alulreprezentálva

**Állítás a bridge-map.md-ben:**
```
relay.verifyCommit — scaffold
Bridge törési pont: runtime — [...] A validator kód létezik, de csak a CI/build pipeline-ban van bekötve
```

**Valóság:** `get_chunk("c246")` → `VerifyProofArtifact` (go_func, `cmd/relay/proof_verify.yaml`) tartalma:
```
4. pose_result value is one of: VERIFIED | DRIFT | SKIPPED (when present).
5. commit_record.id == chain_hash when commit_record is present.
references: cabinet.ProofTraceStep
```

A `VerifyProofArtifact` tehát már validálja a `pose_result` (PoSE kimenet) és `commit_record` (StateCommit) mezőket. Ez azt jelenti:

- A PoSE eredmény (VERIFIED/DRIFT) **séma-szinten már definiált** a verifikátor kódban — nem teljes mértékben "concept"
- A StateCommit rekord (`commit_record.id == chain_hash`) **referenciaszinten bekötött** a verifikátorban

**Pontosítás:**
A bridge-map a `pose-verifier` és `state-commit-writer` komponenseket teljes mértékben concept/scaffold-ként kezeli, de a `VerifyProofArtifact` (c246) már tartalmaz PoSE és StateCommit logikát. Ez nem implementált, de erősebb scaffold mint ahogy a térkép bemutatja:

- `pose_result` mező: a verifikátor elfogadja és ellenőrzi — az értékkészlet definiált (VERIFIED | DRIFT | SKIPPED)
- `commit_record`: a verifikátor ellenőrzi, hogy `commit_record.id == chain_hash`

**Státusz-hatás:**
A `relay.verifyCommit` scaffold státusza helyes, de a bridge-map nem mutat rá, hogy ez a scaffold erősebb mint a tiszta concept — részleges kód-szintű PoSE és StateCommit integráció már létezik a verifikátorban. Ez nem változtatja meg a teljes PoSE/StateCommit concept státuszát (Go implementáció még mindig hiányzik), de a bridge törési pont pontosabb leírást igényel.
