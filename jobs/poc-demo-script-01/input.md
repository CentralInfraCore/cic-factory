# poc-demo-script-01 — Demo forgatókönyv és vizualizáció

## Kontextus

Szülő job: `poc-implementation-plan` — olvasd el az `output/roadmap.md` demo forgatókönyv szekcióját.

**Előfeltétel:** `poc-rollback-01` kész (minden fázis implementálva).

## Feladat

A teljes 8.1–8.4 demonstráció összefogása, automatizálása és vizualizálása.

### 1. Master demo script

`jobs/poc-demo-script-01/output/run-demo.sh`:

```bash
#!/usr/bin/env bash
# CIC PoC Demo — teljes forgatókönyv
# Előfeltétel: poc-infra-01, poc-observer-plugin-01,
#              poc-drift-detection-01, poc-rollback-01 kész

# Fázis 8.1 — Terraform up
phase_81_terraform_up() { ... }

# Fázis 8.2 — 5x kézi módosítás (automatizált)
phase_82_manual_changes() { ... }

# Fázis 8.3 — Infra törlés
phase_83_destroy() { ... }

# Fázis 8.4 — Rollback
phase_84_rollback() { ... }

# Vizualizáció: párhuzamos terminal ablakok
# - git log --oneline state/ (folyamatosan frissülő)
# - relay log (stdout)
# - Proxmox API poll (VM állapot)
```

### 2. Terminál layout (tmux)

```
┌─────────────────────────┬──────────────────────────┐
│ git log state/ (watch)  │ CIC-Relay log (tail -f)  │
├─────────────────────────┼──────────────────────────┤
│ Proxmox VM status       │ Demo step indicator      │
└─────────────────────────┴──────────────────────────┘
```

`jobs/poc-demo-script-01/output/tmux-layout.sh` — tmux session setup

### 3. Commit anatómia vizualizátor

`jobs/poc-demo-script-01/output/show-commit.sh`:
- Adott CommitRef tartalmának megjelenítése
- prooftrace.json formázott output (chain_hash, actor, timestamp)
- `git verify-commit HEAD` eredmény

### 4. Prezentációs checklist

`jobs/poc-demo-script-01/output/demo-checklist.md`:
- Minden fázis előtt/után ellenőrzési pontok
- „Mi bizonyítja ezt?" — kriptográfiai hivatkozással minden lépésnél
- Kulcsüzenetek (nem technikai közönségnek is érthető)

### 5. Ellenőrzési feltételek (Definition of Done)

- [ ] `run-demo.sh` hibátlanul fut végig (~30 perc)
- [ ] tmux layout automatikusan feláll
- [ ] Minden fázisban látható commit a state/ ágon
- [ ] Rollback végén az infra valóban visszaáll
- [ ] `git verify-commit` végig érvényes aláírást mutat

## Megjegyzések

- A script legyen megszakítható és újraindítható (idempotens fázisok)
- Hibaüzenet esetén informatív üzenet (mi hiányzik, melyik előfeltétel)
- Timing: fázisok között 30 sec várakozás a vizuális hatásért

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Shell script, YAML: **angolul**
