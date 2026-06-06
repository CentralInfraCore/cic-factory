# poc-observer-plugin-01 — Terraform observer .so plugin

## Kontextus

Szülő job: `poc-implementation-plan` — olvasd el az `output/execution-model.md`-t.

**Előfeltétel:** `poc-infra-01` kész.

## Feladat

A 8.1 fázis (Terraform up) implementálása. A CIC szerepe: **OBSERVER + RECORDER**.
A human futtatja a Terraform-ot. A CIC az eredményt rögzíti.

### 1. Go plugin (.so)

`CIC-Relay/core/plugins/terraform_observer/` könyvtárban:

```go
// Exportált függvény (pontos szignatúra szükséges — c906 alapján)
// go build -buildmode=plugin
func ObserveState(input json.RawMessage) (json.RawMessage, error)
```

Feladatai:
- Proxmox API lekérdezés (aktuális VM állapot, hálózat, tűzfalszabályok)
- `actual_state.json` generálás (IP-k, VM states, rule list)
- PBS root hash számítás (sha256 az actual_state felett — PBS stub v1-ben)

### 2. Relay workflow YAML

`CIC-Relay/core/workflows/poc.iac.observe.yaml`:

```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: poc.iac.observe
  version: "1.0"
spec:
  steps:
    - name: assert_intent
      module: cic.iac.assert@1.0   # OIS intent rögzítés
      # ...
    - name: snapshot
      module: cic.iac.snapshot@1.0 # Proxmox API → actual_state.json
      # ...
    - name: prooftrace
      module: cic.iac.prooftrace@1.0 # ProofTrace létrehozás
      # ...
    - name: commit_state
      module: cic.iac.commit@1.0   # GitStateRecorder commit
      # ...
```

### 3. ProofTrace generálás

A proof_artifact.schema.yaml (c263) alapján:
- `chain_hash`: SHA-256(sourceDigest + workflowID + per-step hashes)
- `steps[]`: minden lépés input_hash + output_hash
- `commit_record`: actor, trace_head, pose_root (PBS hash)
- `pose_result`: "SKIPPED" (v1-ben elegendő)

### 4. GitStateRecorder commit

`state/` ágra commit:
```
state/
  infra.tf.json        ← desired state (Terraform plan output)
  actual_state.json    ← Proxmox API alapján
  prooftrace.json      ← proof_artifact schema szerint
```

### 5. Ellenőrzési feltételek (Definition of Done)

- [ ] `go build -buildmode=plugin` sikeres
- [ ] Plugin betöltése relay-ből működik
- [ ] terraform apply után state/ ágon commit keletkezik
- [ ] prooftrace.json érvényes (chain_hash sha256 egyezik)
- [ ] `git log state/` mutatja CommitRef #1-et

## Megjegyzések

- A plugin stateless: nem tárol adatot, nem lép kapcsolatba más komponensekkel (c900)
- OIS obligation check v1-ben: stub (ALLOWED always), de a struktúra legyen kész
- PBS root hash v1-ben: sha256(actual_state.json) — valós PBS integráció v2+

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Go kód, YAML: **angolul**
