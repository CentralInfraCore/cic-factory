# State Commit Plugin implementáció

## Kontextus

**Végrehajtási modell alapelv:** A state/ git ág automatikus commitmálása plugin feladat — a relay NEM ír git-be közvetlenül. A `state-commit.so` plugin minden ProofTrace esemény után rögzíti a rendszer állapotát auditálható, aláírt commitként.

**KB forrás:**
- `iac_ontology_and_design.md` (c1120): "Actual State → külön Git ág, ahová a rendszer visszaírja a mért adatokat"
- `commit-signing.md` (c724, c1002): GPG/Ed25519 aláírás kötelező, PEM trust-anchor
- `proof_trace.go` (c347): ProofArtifact → CommitRef

**Demo értéke (add.md 8.1–8.3 fázis):** A képernyőn élőben látható commitok — minden állapotváltozás auditált tény.

**Szülő job:** `poc-implementation-plan`
**Előfeltétel:** Nincs (alapkomponens, mások ezt hívják)

---

## Feladat

### 1. state-commit plugin implementáció

**Fájl:** `plugins/state-commit/main.go`

**Plugin inputState:**
```json
{
  "git_repo_path": "/path/to/iac-repo",
  "branch": "state/main",
  "signing_key_id": "relay-operator-key",
  "payload": {
    "infra.tf.json": "...",          // desired state (JSON)
    "actual_state.json": "...",       // tényleges állapot (JSON)
    "prooftrace.json": "..."          // ProofArtifact (canonical JSON)
  },
  "commit_message_template": "state: {event_type} #{seq} ({drift_type})",
  "event_meta": {
    "event_type": "provision|drift|hard_drift|rollback",
    "seq": 1,
    "drift_type": "NONE|SOFT_DRIFT|RECONCILIABLE_DRIFT|HARD_DRIFT"
  }
}
```

**Plugin outputState:**
```json
{
  "status": "success|error",
  "commit_hash": "sha256...",
  "commit_ref": "state/main@{commit_hash}",
  "signed_by": "relay-operator-key",
  "error_message": ""
}
```

### 2. Aláírási integráció

A commitnak GPG/Ed25519 aláírással kell megjelennie:
- A relay-01 VM-en tárolt kulcs (Vault vagy GPG keyring)
- `git commit -S` megfelelője programozottan (go-git vagy exec.Command)
- A commit hash a ProofArtifact `CommitRef` mezőjébe kerül vissza

**Fontos:** A privát kulcs fájlba mentése tilos — csak Vault vagy in-memory keyring.

### 3. Commit üzenet formátum

```
state: provision #1 (NONE)
state: drift #2 (SOFT_DRIFT → reconciled)
state: drift #3 (SOFT_DRIFT → reconciled)
state: drift #4 (RECONCILIABLE_DRIFT)
state: hard_drift #5 (HARD_DRIFT)
state: rollback #6 (→ ref #3)
```

### 4. state/ ág struktúra

Minden commit tartalma:
```
state/
  infra.tf.json        ← desired state (Terraform-ból)
  actual_state.json    ← tényleges állapot
  prooftrace.json      ← ProofArtifact (canonical JSON, aláírt)
```

### 5. Tesztelés

- Mock git repo-ban commit + aláírás ellenőrzés
- Commit hash determinisztikus (canonical JSON bemenettel)
- Sikertelen git push (network hiba) → plugin error visszajelzés, NEM pánik

---

## Output

`output/` könyvtárban:
- `commit-chain-model.md` — state/ ág commit lánc és CommitRef modell leírás
- `signing-model.md` — kulcskezelési megközelítés (Vault vs. GPG keyring) elemzés

A Go kód a **CIC-Relay repo** `plugins/state-commit/` könyvtárban.

---

## Fontos megszorítások

- A relay core kódot NEM módosítod
- Canonical JSON marshalling kötelező — azonos tartalom → azonos commit hash
- A plugin idempotens: ugyanaz az input → ugyanaz a commit (ha már létezik, ne duplikáljon)
- A privát kulcs kezelés: Vault token alapú, fájlba mentés TILOS

## Nyelvi szabály
- Dokumentumok: magyarul
- Go kód, YAML, JSON: angolul
