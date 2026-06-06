# Sub-job lista és függőségek

**Szülő job:** `poc-implementation-plan`
**Alap:** végrehajtási modell — minden PoC funkció plugin formájában implementálandó

---

## Sub-job áttekintés

| Job ID | Terület | Target repo | Branch | Státusz |
|---|---|---|---|---|
| `poc-infra-setup-01` | Proxmox IaC, VyOS, Vault setup | cic-factory | feature/poc-infra-setup-01 | pending |
| `poc-state-commit-01` | state-commit.so plugin | CIC-Relay | feature/poc-state-commit-01 | pending |
| `poc-terraform-plugin-01` | terraform-apply.so plugin | CIC-Relay | feature/poc-terraform-plugin-01 | pending |
| `poc-drift-detector-01` | drift-detector.so plugin | CIC-Relay | feature/poc-drift-detector-01 | pending |
| `poc-ois-rollback-01` | ois-validator.so + rollback-trigger.so | CIC-Relay | feature/poc-ois-rollback-01 | pending |

---

## Függőségi gráf

```
poc-infra-setup-01
    │
    ├──────────────────────────────┐
    │                              │
poc-state-commit-01          poc-terraform-plugin-01
    │                              │
    └──────────────┬───────────────┘
                   │
          poc-drift-detector-01
                   │
          poc-ois-rollback-01
```

**Magyarázat:**
- `poc-infra-setup-01`: nincs előfeltétel — alapinfrastruktúra
- `poc-state-commit-01`: nincs kód-előfeltétel (alap plugin), de infra kell a teszteléshez
- `poc-terraform-plugin-01`: infra setup után futtatható
- `poc-drift-detector-01`: terraform plugin és state-commit plugin szükséges (ProofArtifact pipeline)
- `poc-ois-rollback-01`: drift-detector és terraform plugin szükséges (OIS policy a ProofTrace láncra épül)

---

## Párhuzamosan futtatható

**Első kör (párhuzamos):**
- `poc-infra-setup-01`
- `poc-state-commit-01`
- `poc-terraform-plugin-01`

**Második kör (első kör után):**
- `poc-drift-detector-01`

**Harmadik kör (második kör után):**
- `poc-ois-rollback-01`

---

## Sub-job részletek

### poc-infra-setup-01

**Mit old meg:** Proxmox VM-ek, VyOS router, Vault(mem), IaC git repo struktúra

**Outputok:**
- Terraform IaC kód (infra/)
- VyOS baseline konfig
- Vault startup script
- IaC repo state/ + intent/ ág struktúra

**Demo kapcsolat:** Sprint 1 — nélküle semmi sem fut

---

### poc-state-commit-01

**Mit old meg:** `state-commit.so` plugin — ProofArtifact → aláírt git commit a state/ ágon

**Outputok:**
- `plugins/state-commit/main.go` (CIC-Relay)
- Commit chain modell dokumentáció
- Aláírási modell elemzés

**Demo kapcsolat:** Minden fázishoz szükséges — a "pörgő commitok" ez a plugin

---

### poc-terraform-plugin-01

**Mit old meg:** `terraform-apply.so` plugin — relay workflow → Terraform CLI → ProofTrace

**Outputok:**
- `plugins/terraform-apply/main.go` (CIC-Relay)
- Workflow YAML + schema definíció
- Plugin design dokumentáció

**Demo kapcsolat:** 8.1 fázis (infra felhúzás) és 8.4 fázis (rollback)

---

### poc-drift-detector-01

**Mit old meg:** `drift-detector.so` plugin — SOFT/RECONCILIABLE/HARD drift detektálás + state/ commit trigger

**Outputok:**
- `plugins/drift-detector/main.go` (CIC-Relay)
- Drift típusok dokumentáció
- VyOS állapot-olvasó segédlet

**Demo kapcsolat:** 8.2 fázis (kézi módosítások) és 8.3 fázis (Hard Drift)

---

### poc-ois-rollback-01

**Mit old meg:** `ois-validator.so` + `rollback-trigger.so` plugin — intent ág push → OIS ellenőrzés → Terraform apply

**Outputok:**
- `plugins/ois-validator/main.go` + `plugins/rollback-trigger/main.go` (CIC-Relay)
- OIS modell dokumentáció
- Intent ág workflow leírás

**Demo kapcsolat:** 8.4 fázis (visszaállítás) — a teljes demo csúcspontja

---

## Végrehajtási modell emlékeztető

> A relay NEM hajt végre kódot közvetlenül. Minden plugin `.so` formában, `plugin.Open()` + `Lookup()` betöltéssel fut. A relay core (`core/cabinet/`, `cmd/relay/`) egyetlen sub-jobban sem módosítható.

Minden sub-job agent kizárólag a megjelölt plugin könyvtárakban dolgozik, és a meglévő `cabinet/plugin.go` interfészt implementálja.
