# poc-demo-scripts-01 — Demo Forgatókönyv Szkriptek

## Feladat összefoglalása

A 4 fázisú CIC/Relay PoC demo forgatókönyv (add.md 8.1–8.4 fázis) futtatásához szükséges shell szkriptek, terminal live display és koordinátor logika megvalósítása.

**Előfeltétel:** Ez a job a következők befejezése után futtatható:
- `poc-relay-wiring-01` (state/ ág bridge)
- `poc-drift-engine-01` (drift detection + `/drift/status` endpoint)
- `poc-iac-terraform-01` (Terraform szkeletonok)
- `poc-ois-policy-01` (OIS `/ois/check` endpoint)

Az output a `jobs/poc-demo-scripts-01/output/demo/` mappába kerüljön.

## Megvalósítandó szkriptek

```
output/demo/
  ├── 01-terraform-up.sh          ← Fázis 8.1: Terraform apply + CIC ProofTrace trigger
  ├── 02-drift-trigger.sh         ← Fázis 8.2: 4–5 kézi módosítás szimulálása
  ├── 03-infra-destroy.sh         ← Fázis 8.3: Terraform destroy + HARD_DRIFT trigger
  ├── 04-rollback.sh              ← Fázis 8.4: OIS-ellenőrzés + git merge + Terraform apply
  ├── live-display.sh             ← Terminál: state/ ág commit log + drift status
  ├── demo-run-all.sh             ← Koordinátor: mind a 4 fázist sorban futtatja
  └── README.md                   ← Demo futtatási útmutató
```

## Szkript specifikációk

### `01-terraform-up.sh`

```bash
# 1. Terraform apply
# 2. Terraform output → actual_state.json generálása
# 3. CIC Relay API hívás (POST /setx) a ProofTrace indításához
# 4. Várakozás a state/ ág commit megjelenésére
# 5. git log state/ megjelenítése

RELAY_URL="${RELAY_URL:-http://localhost:8080}"
TF_DIR="${TF_DIR:-../poc-iac-terraform-01/output/terraform}"
STATE_REPO="${STATE_REPO:-/var/lib/cic-demo/state}"
```

### `02-drift-trigger.sh`

4–5 módosítás szimulálása (script paraméterelhető: `--count 5`):
- Módosítás típusok:
  - VyOS config változtatás (SSH a VyOS VM-re, konfig felülírás)
  - Bastion SSH rule módosítás
  - Relay port változtatás (Terraform resource update, de NE apply-oljunk)
  - Erőforrás átnevezés
- Minden módosítás után:
  - `GET http://localhost:8080/drift/status` → drift típus logolása
  - Várakozás state/ commit megjelenésére
  - `git log state/ --oneline -1` kiírása

### `03-infra-destroy.sh`

```bash
# 1. Terraform destroy
# 2. Várakozás HARD_DRIFT észlelésére (GET /drift/status poll)
# 3. state/ ág utolsó commit tartalmának megjelenítése
```

### `04-rollback.sh`

```bash
# 1. OIS ellenőrzés: POST /ois/check (action: rollback, drift_type: HARD_DRIFT)
# 2. Ha ALLOWED:
#    a. state/commit-3-ref azonosítása (3. commit)
#    b. git checkout intent/main
#    c. git merge state/<commit-ref>
#    d. git push origin intent/main
# 3. Terraform apply (az intent/main alapján)
# 4. Új ProofTrace megjelenítése

COMMIT_REF="${COMMIT_REF:-}" # ha üres, a 3. state/ commit-ot keresi automatikusan
```

### `live-display.sh`

Terminál folyamatos megjelenítés (tmux vagy watch alapú):

```bash
# Panel 1: git log state/ --oneline (utolsó 10 commit)
# Panel 2: GET /drift/status (5 másodperces poll)
# Panel 3: ProofTrace chain hash (az utolsó ismert)

# Ha tmux nem elérhető: watch -n 2 parancsok egymás után
```

### `demo-run-all.sh`

```bash
# Koordinátor: sorban futtatja az összes fázist
# Minden fázis után: 5 másodperces szünet + ENTER várakozás (interaktív)
# Nem-interaktív módban: --auto flag
```

## Konfiguráció

Minden szkript a következő env változókat olvassa:

```bash
RELAY_URL="http://localhost:8080"        # CIC Relay API
TF_DIR="<poc-iac-terraform-01 path>"    # Terraform könyvtár
STATE_REPO="/var/lib/cic-demo/state"    # state/ ág helyi klón
DEMO_PAUSE=5                             # fázisok közti szünet (s)
```

## Követelmények

- Minden szkript: `#!/usr/bin/env bash`, `set -euo pipefail`
- Minden lépés elején: echo kimenet (mit csinál, melyik fázis)
- Hibakezelés: ha Relay nem elérhető → hibaüzenet + exit 1
- Idempotens ahol lehetséges: `01-terraform-up.sh` futtatható újra (`terraform apply -refresh-only`)
- Bash 5.x kompatibilis, nincs zsh/fish specifikus szintaxis
- Nincs hardcoded IP — env változókból jön minden

## Elfogadási kritérium

- [ ] `bash -n *.sh` szintaxis hiba nélkül
- [ ] `01-terraform-up.sh` és `04-rollback.sh`: dokumentált mock mód (`--dry-run` flag) Terraform nélküli teszteléshez
- [ ] `live-display.sh` fut tmux nélkül is (watch fallback)
- [ ] `README.md` tartalmazza: előfeltételek, konfig, futtatási sorrend
- [ ] Minden szkript: `set -euo pipefail`
