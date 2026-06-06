# PoC v1 Infrastruktúra Setup

## Kontextus

A CIC/Relay PoC v1 alapinfrastruktúrájának Terraform IaC megvalósítása Proxmox környezetben.

**Szülő job:** `poc-implementation-plan`
**Végrehajtási modell:** A relay NEM hajt végre kódot közvetlenül — az infra setup Terraform pluginen keresztül valósul meg.

---

## Feladat

### 1. Terraform IaC definiálás

Hozd létre a PoC v1 Proxmox infrastruktúra Terraform kódját:

```
infra/
  main.tf        ← Proxmox provider, VM-ek
  network.tf     ← VyOS router, VLAN definíciók
  variables.tf   ← paraméterek
  outputs.tf     ← IP-k, VM ID-k
```

**VM-ek:**
- `bastion` — 1 vCPU, 1GB RAM, SSH belépési pont
- `vyos-gw` — 2 vCPU, 1GB RAM, VyOS router (drift demo)
- `vault-dev` — 1 vCPU, 2GB RAM, Vault dev mode
- `relay-01` — 2 vCPU, 4GB RAM, cic-relay binary
- `terraform-runner` — 1 vCPU, 2GB RAM, Terraform + state git

### 2. VyOS baseline konfig

Alap router konfiguráció (YAML/set parancsok formájában):
- Interface definíciók
- Alap tűzfalszabályok (amelyek majd a drift demóban módosulnak)
- VLAN szegmensek

### 3. Vault(mem) startup script

Shell script a relay-01 VM-en:
- `vault server -dev` indítás
- Plugin token generálás a relay számára
- Health check endpoint

### 4. IaC git repo struktúra

```
iac-repo/
  state/         ← actual state ág (desired + actual + prooftrace)
  intent/        ← rollback intent ág
  README.md      ← branch modell leírás
```

### 5. state/ ág bootstrap

Első commit minta struktúra:
```
state/
  infra.tf.json        ← desired state (Terraform-ból generált JSON)
  actual_state.json    ← tényleges állapot sablon
  prooftrace.json      ← ProofArtifact sablon
```

---

## Output

`output/` könyvtárban:
- `terraform/` — teljes Terraform IaC
- `scripts/vault-startup.sh` — Vault dev mode script
- `scripts/relay-deploy.sh` — cic-relay telepítési script
- `iac-repo-structure.md` — git repo struktúra leírás
- `vyos-baseline.txt` — VyOS set parancsok

---

## Fontos megszorítások

- A relay core kódot NEM módosítod
- Minden infra elem Terraform-ban deklarált (IaC elv)
- Minden script idempotens és újrafuttatható
- A VyOS konfig olyan legyen, hogy kézi módosítással SOFT_DRIFT demonstrálható

## Nyelvi szabály
- Dokumentumok: magyarul
- Terraform, shell, YAML, JSON: angolul
