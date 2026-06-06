# poc-infra-01 — Proxmox alap infrastruktúra

## Kontextus

Ez a job a CIC PoC demonstráció alap infrastruktúráját hozza létre.
Szülő job: `poc-implementation-plan` — olvasd el az `output/roadmap.md`-t és az `output/infra-decision.md`-t.

A döntés: **Proxmox** (nem OCI). Az indoklást lásd `infra-decision.md`.

## Feladat

### 1. IaC scriptek a cic-factory-ban

Hozz létre `jobs/poc-infra-01/output/iac/` könyvtárban:

- `proxmox/main.tf` — Terraform konfiguráció (bpg/proxmox provider, demo VM template)
- `proxmox/variables.tf` — API endpoint, token, node neve
- `proxmox/outputs.tf` — VM IP-k, azonosítók
- `vault/init.sh` — Vault dev mode indítás, CIC key setup script
- `relay/config.yaml` — CIC-Relay alap konfiguráció (git state repo, port)
- `git-state-repo/init.sh` — bare git repo init, state/ és intent/ ágak létrehozása

### 2. Dokumentáció

`jobs/poc-infra-01/output/setup-guide.md`:
- Lépésről-lépésre Proxmox host előkészítés
- Terraform init és first apply
- CIC-Relay indítás ellenőrzése
- git log state/ — üres repo ellenőrzés

### 3. Ellenőrzési feltételek (Definition of Done)

- [ ] `terraform plan` fut hibátlanul
- [ ] CIC-Relay elindul és health check válaszol
- [ ] `git log state/` parancs végrehajtható (üres, de ág létezik)
- [ ] Vault dev mode elérhető, CIC key beállítva

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Terraform HCL, shell script, YAML: **angolul**

## Git

Push csak `feature/poc-infra-01` branch-re.
