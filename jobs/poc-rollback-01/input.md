# poc-rollback-01 — OIS rollback trigger

## Kontextus

Szülő job: `poc-implementation-plan` — olvasd el az `output/execution-model.md`-t (különösen a 8.4 fázis leírását).

**Előfeltétel:** `poc-drift-detection-01` kész.

Ez az egyetlen fázis ahol a CIC **aktívan beavatkozik** (CIC-ACT szerepkör).

## Feladat

A 8.4 fázis (Rollback) implementálása:
1. Human: `git merge state/commit-3-ref` + `git push intent/main`
2. CIC: intent/ ág push észlelése
3. CIC: OIS obligation check
4. CIC: Terraform apply trigger
5. CIC: Új ProofTrace (CommitRef visszautal #3-ra)

### 1. GitSource intent/ ág figyelő

`CIC-Relay/core/nexus/iac/intent_watcher.go`:
- Polling az intent/ ágon (v1: git fetch + diff, 5 sec interval)
- Új commit észlelésekor: intent payload kiolvasása
- Átadás az OIS obligation check-nek

### 2. OIS obligation check (demo policy)

Az OIS formális modell (c2498) alapján:

```go
// OIS(actor, action, context)
func CheckObligation(actor, action string, policy DemoPolicy) (bool, error) {
    // v1 demo policy: ALLOWED ha actor == "relay-operator"
    // és action == "rollback"
    if actor == "relay-operator" && action == "rollback" {
        return true, nil
    }
    return false, errors.New("PERMISSION_DENIED")
}
```

Az intent és obligation szétválasztása kötelező:
- `intent`: "Mit szeretnék tenni?" → restore to commit-3 state
- `obligation`: "Megtehetem-e?" → policy alapján ellenőrzés

### 3. Terraform apply trigger

Ha obligation == ALLOWED:
```go
// Terraform apply a meghatározott korábbi állapot alapján
cmd := exec.Command("terraform", "apply", "-auto-approve",
    "-var-file=state-commit-3.tfvars")
```

A CommitRef #3-ból kinyert desired state alapján.

### 4. Új ProofTrace

A rollback sikeres végrehajtása után:
```json
{
  "id": "sha256(<payload>)",
  "actor": "relay-operator",
  "intent": "rollback to commit-3",
  "prev": "<hard_drift_commit_id>",
  "commit_record": {
    "id": "<chain_hash>",
    "trace_head": "<prooftrace_id>",
    "pose_root": "<new_pbs_hash>"
  }
}
```

A `commit_record.trace_head` visszautal a #3 CommitRef-re.

### 5. Demo script

`jobs/poc-rollback-01/output/demo-rollback.sh`:
```bash
# Human gesztusonként futtatandó:
git -C $STATE_REPO checkout state/
git log --oneline state/ | head -10   # CommitRef #3 azonosítás
git -C $INTENT_REPO checkout intent/main
git -C $INTENT_REPO merge state/commit-3-ref
git -C $INTENT_REPO push origin intent/main
# CIC intent watcher észleli, OIS check, terraform apply fut
```

### 6. Ellenőrzési feltételek (Definition of Done)

- [ ] git push intent/main → relay érzékeli (max 10 sec)
- [ ] OIS obligation check fut és ALLOWED-t ad vissza
- [ ] terraform apply fut és infra újjáépül
- [ ] Proxmox UI-ban látható a VM megjelenése
- [ ] Új ProofTrace keletkezik a state/ ágon
- [ ] Új CommitRef trace_head visszautal commit #3-ra

## Megjegyzések

- A rollback nem „automatikus" — a human gesztusonként (git push) triggereli
- Az OIS policy v1-ben stub (allow all) — valós policy motor v2+
- A Terraform apply szinkron a demo kedvéért (async v2+)

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Go kód, shell script, YAML: **angolul**
