# poc-drift-engine-01 — Drift Detection implementáció

## Feladat összefoglalása

A CIC drift taxonomy (SOFT_DRIFT, RECONCILIABLE_DRIFT, HARD_DRIFT) kódba épített detekciós motorjának megvalósítása. Jelenleg a drift taxonómia és kategóriák dokumentáltak (KB), de automatikus észlelő engine nincs a relay kódbázisban.

A demo forgatókönyv (add.md 8.2–8.3 fázis) drift észlelést igényel valós időben.

## Elvégzendő lépések

### 1. Drift típusok definíciója (`core/nexus/drift/types.go`)

```go
type DriftType string

const (
    DriftNone           DriftType = "NONE"
    DriftSoft           DriftType = "SOFT_DRIFT"
    DriftReconciliable  DriftType = "RECONCILIABLE_DRIFT"
    DriftHard           DriftType = "HARD_DRIFT"
)

type DriftEvent struct {
    Type        DriftType
    Description string
    Timestamp   string  // injektált, nem clock
    CommitRef   string  // ProofTrace utolsó igazolt CommitRef
    ActualState map[string]interface{}
}
```

### 2. DriftDetector interface (`core/nexus/drift/detector.go`)

```go
type DriftDetector interface {
    Detect(desired ExpectedState, actual ActualState) (DriftEvent, error)
}
```

Implementáció:
- `ComparatorDetector`: összehasonlítja a desired (ProofTrace utolsó commit) és actual state (Terraform state output / PBS snapshot) állapotokat
- Kategorizálás logika:
  - Ha actual == desired → `NONE`
  - Ha eltérés kis mértékű / átmeneti → `SOFT_DRIFT`
  - Ha eltérés javítható ismert remediation flow-val → `RECONCILIABLE_DRIFT`
  - Ha actual teljesen eltér (pl. null / nem létező) → `HARD_DRIFT`

**Megjegyzés:** PoC-ban a kategorizálás szabályai egyszerűsíthetők:
- Null actual state → `HARD_DRIFT`
- Mezőszintű eltérés → `SOFT_DRIFT`
- Strukturális eltérés (hiányzó resource) → `RECONCILIABLE_DRIFT`

### 3. DriftWriter — state/ ág frissítés drift esetén (`core/nexus/drift/writer.go`)

Minden `DriftEvent` után:
- A state/ ágra új commit kerül (lásd poc-relay-wiring-01 `GitStateWriter`)
- A commit tartalmazza: `actual_state.json`, `drift_event.json`, `prooftrace.json` (lánc folytatódik)
- `drift_event.json` struktúra: `DriftEvent` canonical JSON formátuma

### 4. HTTP endpoint — drift poll (`cmd/relay/main.go` kiterjesztés)

Új endpoint: `GET /drift/status`
- Visszaadja az utolsó `DriftEvent`-et JSON formátumban
- A demo live display ezt pollozza

### 5. Egységtesztek

- `core/nexus/drift/detector_test.go`
- Legalább 3 teszteset: NONE, SOFT_DRIFT, HARD_DRIFT
- Determinisztikus: mock ActualState injektálható

## Fontos megszorítások

- A DriftDetector ne pollozzon belső timer-rel — a detekció triggerelt legyen (kívülről hívható)
- Timestamp injektálás kötelező (nem `time.Now()` közvetlen hívás)
- Canonical JSON kötelező a `drift_event.json`-hez
- `HARD_DRIFT` esetén a rendszer NEM auto-javít — csak rögzít és escalate-el (HTTP 200, de `drift_type: HARD_DRIFT`)

## KB hivatkozások

- Drift taxonómia: `docs/en/reality/state.md` (Drift Detection szekció)
- Drift osztályok: `docs/en/reality/drift_taxonomy.md` (Chain Drift / State Drift)
- Error & Drift Handling: `docs/en/reality/implementation_core.md`
- ProofTrace: `core/cabinet/proof_trace.yaml`

## Elfogadási kritérium

- [ ] `DriftDetector.Detect()` visszaad NONE/SOFT/RECONCILIABLE/HARD-ot a mock input alapján
- [ ] `DriftWriter` state/ ágra commitot ír drift event esetén
- [ ] `GET /drift/status` endpoint létezik és JSON választ ad
- [ ] `make test` zöld
- [ ] Determinisztikus (nincs `time.Now()` közvetlen hívás, timestamp injektálható)
