# Drift Detector Plugin implementáció

## Kontextus

**Végrehajtási modell alapelv:** A relay a drift detektálást NEM végzi maga — a `drift-detector.so` plugin összehasonlítja a ProofTrace utolsó ismert állapotát a tényleges állapottal, és visszaad egy strukturált drift eredményt.

**KB forrás:**
- `iac_ontology_and_design.md` (c1120): "Actual State → külön Git ág, ahová a rendszer visszaírja a mért adatokat"
- `plugin_interface.md` (c900): "bemeneti állapotleírás alapján műveletet hajt végre, visszajelzést ad"
- `proof_trace.go` (c347): `ProofTrace` — az immutable audit record

**Demo célja (add.md 8.2–8.3 fázis):**
- 4-5 kézi módosítás → SOFT_DRIFT / RECONCILIABLE_DRIFT detektálás → state/ commit
- Teljes törlés → HARD_DRIFT detektálás

**Szülő job:** `poc-implementation-plan`
**Előfeltétel:** `poc-terraform-plugin-01` (ProofArtifact pipeline kész)

---

## Feladat

### 1. drift-detector plugin implementáció

**Drift típusok (add.md alapján):**
```
SOFT_DRIFT        — kis eltérés, automatikusan reconcilálható
RECONCILIABLE_DRIFT — jelentős eltérés, manuális beavatkozás szükséges
HARD_DRIFT        — fizikai állapot null → ProofTrace nem vezethető le
```

**Plugin inputState:**
```json
{
  "last_proof_trace": { ... },     // utolsó érvényes ProofArtifact
  "actual_state": { ... },          // tényleges állapot (Terraform state)
  "drift_threshold": {
    "soft": 0.1,
    "reconciliable": 0.5
  }
}
```

**Plugin outputState:**
```json
{
  "drift_type": "SOFT_DRIFT|RECONCILIABLE_DRIFT|HARD_DRIFT|NONE",
  "drift_details": [
    { "field": "vyos.firewall.rule.100", "expected": "accept", "actual": "drop" }
  ],
  "reconcilable": true,
  "commit_payload": { ... }   // state/ ágra kerülő adat
}
```

### 2. state-commit plugin implementáció

A drift detektálás eredményét a `state-commit.so` plugin commitálja a state/ ágra.

**Plugin inputState:**
```json
{
  "git_repo": "/path/to/iac-repo",
  "branch": "state/main",
  "commit_message": "drift: SOFT_DRIFT #2",
  "payload": {
    "infra.tf.json": { ... },
    "actual_state.json": { ... },
    "prooftrace.json": { ... }
  }
}
```

**Fontos:** A commit GPG/Ed25519 aláírással kell megjelenjen (vault-sign-agent integrációval, vagy a relay-01 VM kulcsával).

### 3. Workflow YAML — drift loop

```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: poc.drift.check
  version: 1.0.0
spec:
  steps:
    - poc.drift-detector@1.0.0
    - poc.state-commit@1.0.0
```

### 4. VyOS állapot-olvasó segédlet

Leírás (nem plugin — külső eszköz): hogyan kérdezzük le a VyOS aktuális tűzfalszabályait és alakítjuk át `actual_state.json`-ná.

### 5. Tesztelés

- Mock ProofArtifact + mock tényleges állapot → SOFT_DRIFT ellenőrzés
- Null actual_state → HARD_DRIFT ellenőrzés
- Azonos állapot → NONE visszajelzés

---

## Output

`output/` könyvtárban:
- `drift-types.md` — drift típusok definíciója és összehasonlítási logika
- `state-branch-model.md` — state/ ág commit struktúra leírás

A Go kód a **CIC-Relay repo** `plugins/drift-detector/` és `plugins/state-commit/` könyvtárban.

---

## Fontos megszorítások

- A relay core kódot NEM módosítod
- Minden drift összehasonlítás determinisztikus és újrafuttatható
- canonical JSON marshalling a ProofTrace inputHash / outputHash számításhoz
- HARD_DRIFT esetén a plugin NEM próbál automatikus helyreállítást — csak rögzít

## Nyelvi szabály
- Dokumentumok: magyarul
- Go kód, YAML, JSON: angolul
