# poc-drift-detection-01 — Drift detekció és state commit

## Kontextus

Szülő job: `poc-implementation-plan` — olvasd el az `output/execution-model.md`-t és `output/status-matrix.md`-t.

**Előfeltétel:** `poc-observer-plugin-01` kész.

## Feladat

A 8.2 fázis (kézi módosítások) és 8.3 fázis (Hard Drift) implementálása.
A CIC szerepe: **OBSERVER + RECORDER** — a kézi módosításokat a human végzi.

### 1. PBS hash polling

Periodic (vagy event-driven) figyelő:
- Proxmox API lekérdezés meghatározott intervallumonként (v1: 10 sec)
- `actual_state.json` frissítés
- PBS root hash újraszámítás: `sha256(actual_state.json)` (v1 PBS stub)

### 2. Drift diagnózis logika (c2543 alapján)

```go
func DetectDrift(prooftraceHash, pbsRootHash string) DriftType {
    if prooftraceHash == pbsRootHash {
        return NO_DRIFT
    } else if isDerivable(prooftraceHash, pbsRootHash) {
        return RECONCILIABLE_DRIFT
    } else {
        return HARD_DRIFT
    }
}
```

Drift típusok (c1815):
- `SOFT_DRIFT`: kis ideiglenes eltérés (latency, in-progress change)
- `RECONCILIABLE_DRIFT`: ismert, javítható eltérés
- `HARD_DRIFT`: strukturális divergencia (pl. VM törlés)

### 3. State commit drift esetén

Minden drift esemény → state/ ág új commit:
```json
{
  "drift": true,
  "drift_type": "SOFT_DRIFT|RECONCILIABLE_DRIFT|HARD_DRIFT",
  "actual_state": { ... },
  "prooftrace": { "prev": "<előző_id>", ... }
}
```

### 4. HARD_DRIFT kezelés (8.3 fázis)

Ha `actual_state = {}` (terraform destroy után):
- PBS root hash = sha256("{}") → nem egyezik az utolsó ProofTrace canonical_state-jével
- `HARD_DRIFT` commit a state/ ágon
- ProofTrace lánc: utolsó érvényes CommitRef megmarad (nem nullázódik)

### 5. Demo script

`jobs/poc-drift-detection-01/output/demo-drift.sh`:
- 5× automatizált kézi módosítás (VyOS SSH + rule módosítás)
- Minden módosítás után: `git log --oneline state/` kimenet
- Vizualizáció: drift_type megjelenítése minden commitban

### 6. Ellenőrzési feltételek (Definition of Done)

- [ ] 5 kézi módosítás → 5 commit a state/ ágon
- [ ] Minden commit tartalmaz drift_type-t
- [ ] HARD_DRIFT commit keletkezik terraform destroy után
- [ ] ProofTrace lánc intact marad a törlés után
- [ ] `git log state/` mutatja az összes commitot

## Megjegyzések

A CIC ebben a fázisban **nem avatkozik be** — csak megfigyel és rögzít.
A kézi módosítások nem triggerelnek automatikus javítást (reconcile workflow v2+).

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Go kód, shell script, YAML: **angolul**
