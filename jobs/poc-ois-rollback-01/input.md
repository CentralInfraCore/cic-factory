# OIS Validator + Rollback Trigger Plugin implementáció

## Kontextus

**Végrehajtási modell alapelv:** A rollback folyamat két plugin láncolatokon keresztül valósul meg — az OIS validator ellenőrzi a jogosultságot, a rollback-trigger plugin végrehajtja a Terraform apply-t.

**KB forrás:**
- `ois_principles.md` (c2498): OIS intent/obligation/policy modell
- `plugin_interface.md` (c900): plugin stateless, csak relay hívásra működik
- `relay_pozicionalas.md` (c912): relay pluginokon keresztül hívja a konkrét műveleteket

**Demo célja (add.md 8.4 fázis):**
```bash
git checkout intent/main
git merge state/commit-3-ref
git push origin intent/main
```
→ relay észleli az intent/ push-t → OIS ellenőrzés → Terraform apply (commit #3 állapot)

**Szülő job:** `poc-implementation-plan`
**Előfeltétel:** `poc-terraform-plugin-01`, `poc-drift-detector-01`

---

## Feladat

### 1. OIS Validator plugin

**Fájl:** `plugins/ois-validator/main.go`

Az OIS egyszerűsített modellje a PoC-hoz:
- **Intent:** ki, mit, milyen okból akar visszaállítani
- **Obligation:** a rollback policy feltételei (pl. HARD_DRIFT vagy RECONCILIABLE_DRIFT megelőzte)
- **Policy:** az Obligation teljesül-e az aktuális ProofTrace lánc alapján

**Plugin inputState:**
```json
{
  "actor": "relay-operator",
  "intent": "rollback",
  "target_commit_ref": "commit-3-hash",
  "last_proof_chain": [...],
  "policy": {
    "require_prior_drift": true,
    "allowed_actors": ["relay-operator"]
  }
}
```

**Plugin outputState:**
```json
{
  "authorized": true,
  "reason": "RECONCILIABLE_DRIFT precedent found in chain",
  "obligation_met": true,
  "proof_event": { ... }   // OIS event a ProofTrace-be
}
```

**Ha `authorized: false`:** a relay LEÁLLÍTJA a workflow-t, nem folytatja a rollback-trigger lépést.

### 2. Rollback Trigger plugin

**Fájl:** `plugins/rollback-trigger/main.go`

**Plugin inputState:**
```json
{
  "terraform_dir": "/path/to/tf",
  "target_state": { ... },       // commit #3 desired state
  "ois_proof_event": { ... },    // OIS validator kimenete
  "vault_token": "..."
}
```

**Plugin outputState:**
```json
{
  "status": "success|error",
  "actual_state_after": { ... },
  "proof_back_ref": "commit-3-hash",
  "new_proof_trace_step": { ... }
}
```

### 3. Intent ág figyelő

A relay-nek figyelnie kell az `intent/` ágra — amikor oda push érkezik:
1. Beolvassa az intent YAML-t
2. Elindítja az `poc.ois.rollback` workflow-t

Ez **nem plugin**, hanem relay konfigurációs kérdés. Leírás szükséges:
- Hogyan konfigurálható a relay intent ág figyelésre (webhook vagy polling)?
- Milyen relay.yaml konfig szükséges?

### 4. Rollback workflow YAML

```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: poc.ois.rollback
  version: 1.0.0
spec:
  steps:
    - poc.ois-validator@1.0.0
    - poc.rollback-trigger@1.0.0
    - poc.state-commit@1.0.0
```

### 5. ProofTrace annotáció

A rollback ProofArtifact-nak tartalmaznia kell:
```json
{
  "workflow_id": "poc.ois.rollback",
  "back_ref": "commit-3-hash",
  "ois_event": { "actor": "...", "intent": "rollback", "authorized": true }
}
```

### 6. Tesztelés

- Mock intent push → OIS validator engedélyez → rollback-trigger mock Terraform-mal
- Jogosulatlan actor → OIS validator megtagad → workflow leáll
- Hiányzó ProofTrace precedens → obligation_met: false

---

## Output

`output/` könyvtárban:
- `ois-model.md` — OIS intent/obligation/policy modell a PoC-ban
- `intent-branch-workflow.md` — intent ág figyelés és rollback flow leírás

A Go kód a **CIC-Relay repo** `plugins/ois-validator/` és `plugins/rollback-trigger/` könyvtárban.

---

## Fontos megszorítások

- A relay core kódot NEM módosítod
- Az OIS validator döntése determinisztikus és auditálható (ProofTrace-be kerül)
- `authorized: false` esetén NINCS automatikus rollback — a plugin csak visszajelez
- A PoC-hoz egyszerűsített OIS modell elegendő — teljes quorum döntési réteg v2+

## Nyelvi szabály
- Dokumentumok: magyarul
- Go kód, YAML, JSON: angolul
