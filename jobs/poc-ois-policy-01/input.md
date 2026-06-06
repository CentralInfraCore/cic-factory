# poc-ois-policy-01 — OIS Policy Check (egyszerűsített, PoC)

## Feladat összefoglalása

Az OpenIntentSign (OIS) formális modelljének egyszerűsített runtime implementációja a PoC-hoz. Jelenleg az OIS elvek és formális modell dokumentáltak (KB), de nincs `ois.Check()` függvény a relay kódbázisban.

A demo forgatókönyv 8.4 fázisában (Rollback) az OIS-ellenőrzés dönti el, hogy a rollback-szándék engedélyezett-e a policy alapján.

**Fontos:** Ez nem az OIS teljes implementációja — ez a PoC-hoz elegendő, policy-fájl alapú, egyszerűsített változat.

## OIS formális modell (KB alapján)

```
OIS(actor, action, context) :=
    let intent      = declare(actor, action)
    let obligation  = check(actor, context.policy, context.time)
    if obligation == ALLOWED then
        state' = reduce(state, intent)
        trace  = ProofTrace(intent, obligation, state')
        return (state', trace)
    else
        return ERROR(PERMISSION_DENIED)
```

## Elvégzendő lépések

### 1. OIS Policy fájl formátum (`config/ois-policy.yaml`)

```yaml
apiVersion: cic/v1
kind: OISPolicy
metadata:
  name: poc-policy
spec:
  rules:
    - actor: "*"
      action: "rollback"
      obligation: "ALLOWED"
      condition: "drift_type IN [RECONCILIABLE_DRIFT, HARD_DRIFT]"
    - actor: "*"
      action: "terraform-apply"
      obligation: "ALLOWED"
      condition: "intent_branch == intent/main"
    - actor: "*"
      action: "terraform-destroy"
      obligation: "ALLOWED"
      condition: "always"
```

### 2. OIS Checker interface (`core/nexus/ois/checker.go`)

```go
type Intent struct {
    Actor   string
    Action  string
    Context map[string]string
}

type ObligationResult struct {
    Allowed   bool
    Reason    string
    PolicyRef string
}

type OISChecker interface {
    Check(intent Intent) (ObligationResult, error)
}
```

### 3. PolicyFileChecker implementáció (`core/nexus/ois/policy_checker.go`)

- Betölti a `config/ois-policy.yaml` fájlt (vagy `CIC_OIS_POLICY_PATH` env-ből)
- `Check()`: végigmegy a szabályokon, az első egyező rule-t alkalmazza
- Egyszerű condition evaluátor: `==`, `IN`, `always` — nincs komplex kifejezés-kiértékelő
- Ha nincs egyező rule: `DENIED` (default deny)

### 4. HTTP endpoint — OIS check (`cmd/relay/main.go` kiterjesztés)

Új endpoint: `POST /ois/check`

Request body:
```json
{
  "actor": "relay-operator",
  "action": "rollback",
  "context": {
    "drift_type": "HARD_DRIFT",
    "intent_branch": "intent/main"
  }
}
```

Response:
```json
{
  "allowed": true,
  "reason": "policy rule matched: rollback ALLOWED on HARD_DRIFT",
  "policy_ref": "poc-policy"
}
```

### 5. OIS → ProofTrace integráció

Az OIS döntés kerüljön be a ProofTrace-be:
- Ha `ALLOWED`: a `ProofTraceStep` tartalmaz egy `ois_obligation: ALLOWED` metaadatot
- Ha `DENIED`: a request elutasítva, ProofTrace-be `ois_obligation: DENIED` kerül

### 6. Egységtesztek (`core/nexus/ois/checker_test.go`)

- Legalább 3 teszteset: ALLOWED action, DENIED action, ismeretlen actor
- Policy YAML-ből betöltve, nem hardcoded

## Fontos megszorítások

- Ez NEM az OIS teljes implementációja — scaffold-szintű, de bekötött
- A policy evaluátor szándékosan egyszerű (nem Rego/CEL)
- A `cicSign` / `cicSignedCA` mezők (CLAUDE.md scaffold térkép) még nem szükségesek
- Vault-alapú aláírás az OIS döntésen: opcionális PoC-ban (WARN ha nincs)

## KB hivatkozások

- OIS formális modell: `docs/hu/meta/ois_principles.md` (Formális modell szekció)
- OIS README: `source/OpenIntentSign/github/README.md`
- OIS Obligation: `docs/en/meta/ois_principles.md` (Obligation szekció)
- ProofTrace: `core/cabinet/proof_trace.yaml`

## Elfogadási kritérium

- [ ] `OISChecker.Check()` ALLOWED/DENIED választ ad policy YAML alapján
- [ ] `POST /ois/check` endpoint működik
- [ ] OIS döntés ProofTrace-be integrálva
- [ ] `make test` zöld
- [ ] `config/ois-policy.yaml` létezik PoC policy szabályokkal
- [ ] `CIC_OIS_POLICY_PATH` env dokumentálva
