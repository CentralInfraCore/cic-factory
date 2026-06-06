# Sub-job lista és függőségek — CIC PoC

---

## Függőségi gráf

```
poc-infra-01 (Proxmox + Vault + Relay alap)
  ↓
poc-observer-plugin-01 (terraform_observer .so plugin)
  ↓
poc-drift-detection-01 (drift detekció + state commit)
  ↓
poc-rollback-01 (OIS + intent/ trigger + Terraform apply)
  ↓
poc-demo-script-01 (demo forgatókönyv, automatizálás, vizualizáció)

poc-schema-signing-01 (CICSourceCA / Vault signing — párhuzamos, nem blokkoló)
```

---

## Sub-job lista

### poc-infra-01 — Proxmox alap infrastruktúra

- **Függőség:** nincs
- **Scope:** Proxmox host konfigurálás, Vault mem mode, CIC-Relay binary build, git state repo init, Terraform Proxmox provider setup
- **CIC szerepek:** Human → minden fizikai lépés. CIC-Relay csak konfigurálva lesz.
- **Target repo:** cic-factory (IaC scripts), CIC-Relay (config)
- **Deliverable:** `relay start` sikeres, `terraform plan` fut, git state repo elérhető

---

### poc-observer-plugin-01 — Terraform observer .so plugin

- **Függőség:** poc-infra-01
- **Scope:** Go plugin írása (terraform_observer.so), relay workflow (poc.iac.observe), OIS intent rögzítés, ProofTrace generálás, GitStateRecorder commit, CommitRef #1
- **CIC szerepek:** CIC-ACT (ProofTrace, commit) | Plugin futtatja a Proxmox API hívást
- **Target repo:** CIC-Relay (plugin + workflow YAML)
- **Deliverable:** terraform apply → state/ ágon commit, prooftrace.json érvényes

---

### poc-drift-detection-01 — Drift detekció és state commit

- **Függőség:** poc-observer-plugin-01
- **Scope:** PBS hash polling (periodic), drift diagnózis (SOFT/RECONCILIABLE/HARD), state/ ág commit drift_type-pal, multi-commit vizualizáció
- **CIC szerepek:** CIC-OBS (detektál) + CIC-ACT (commitol)
- **Target repo:** CIC-Relay (drift detector modul + relay workflow)
- **Deliverable:** 5 kézi módosítás → 5 drift commit a state/ ágon, típusok jelölve

---

### poc-rollback-01 — OIS rollback trigger

- **Függőség:** poc-drift-detection-01
- **Scope:** GitSource intent/ ág figyelő, OIS obligation check (demo policy: allow all), Terraform apply triggering, új ProofTrace (CommitRef visszautal korábbira)
- **CIC szerepek:** CIC-ACT (ez az egyetlen fázis ahol CIC aktívan beavatkozik)
- **Target repo:** CIC-Relay (intent_watcher modul + OIS policy stub)
- **Deliverable:** git push intent/main → terraform apply fut → infra újjáépül → ProofTrace lánc zárul

---

### poc-demo-script-01 — Demo forgatókönyv és vizualizáció

- **Függőség:** poc-rollback-01
- **Scope:** Shell script a teljes 8.1–8.4 demo automatizálásra, terminál layout (git log, relay log, Proxmox UI), timing, prezentációs anyag
- **CIC szerepek:** csak dokumentáció és script — nem érint CIC kódot
- **Target repo:** cic-factory (demo scripts)
- **Deliverable:** egyetlen script indítja a demót, minden lépés vizuálisan követhető

---

### poc-schema-signing-01 — CICSourceCA Vault signing aktiválás (párhuzamos)

- **Függőség:** poc-infra-01 (Vault kell)
- **Párhuzamos:** poc-observer-plugin-01-gyel párhuzamosan futhat
- **Scope:** Vault PKI backend setup, CICSourceCA cert chain, schemacompile Layer 2 bekötése, cic_sign valós értékre állítása
- **CIC szerepek:** CIC-ACT (Vault signing relay modulon keresztül)
- **Target repo:** CIC-Relay (schemacompile modul Vault integráció), CIC-Schemas
- **Deliverable:** `cic_sign` valós Vault aláírással, `cic_signed_ca` nem stub

---

## Összefoglaló táblázat

| Sub-job ID | Leírás | Függőség | Prioritás | Becsült idő |
|---|---|---|---|---|
| poc-infra-01 | Proxmox + Vault + Relay alap | — | P0 | 2–3 hét |
| poc-observer-plugin-01 | Terraform observer .so plugin | poc-infra-01 | P1 | 2–3 hét |
| poc-drift-detection-01 | Drift detekció + state commit | poc-observer-plugin-01 | P2 | 2 hét |
| poc-rollback-01 | OIS rollback trigger | poc-drift-detection-01 | P3 | 2–3 hét |
| poc-demo-script-01 | Demo script + vizualizáció | poc-rollback-01 | P4 | 1 hét |
| poc-schema-signing-01 | CICSourceCA Vault signing | poc-infra-01 | P2 (párhuzamos) | 2 hét |

**Teljes becsült idő (kritikus út):** ~10–12 hét
**Párhuzamos végrehajtással (poc-schema-signing-01):** nem rövidíti a kritikus utat
