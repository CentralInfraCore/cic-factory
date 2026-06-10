# poc-infra-01 — OCI alap infrastruktúra (Milestone 0)

## Kontextus

Ez a job a CIC PoC demonstráció alap infrastruktúráját hozza létre **OCI-n**
(Oracle Cloud Infrastructure, Free Tier). Gyökér job — nincs előzménye.

Kötelező olvasás (ezek lezárt döntések, nem kérdőjelezhetők meg):

```
jobs/poc-system-plan/output/system-plan.md          — 1. fejezet (Milestone 0)
jobs/poc-system-plan/output/oci-infra-sketch.md     — Terraform resource lista, Free Tier korlátok
jobs/poc-system-plan/output/domain-job-inputs.md    — poc-infra-01 szakasz: belépési pont,
                                                        deliverable a poc-observer-plugin-01-nek
```

Korábban ez a job Proxmox-alapú volt (`infra-decision.md`) — ez a döntés **megfordult**,
a PoC infrastruktúra OCI Free Tier (Ampere A1). Ne hivatkozz a Proxmox-tervre.

---

## Lezárt döntések (ne kérdőjelezd meg)

- Infrastruktúra: OCI Free Tier — 1 compartment, 1 VCN, 1 publikus subnet, 1 security list,
  4 instance (Bastion `VM.Standard.E2.1.Micro`, Vault/Relay/Demo target `VM.Standard.A1.Flex`
  1+1+2 OCPU = 4 OCPU/24GB — pontosan az Ampere A1 Always Free keret)
- Vault = mem mode (`vault server -dev`), Transit engine, egyetlen kulcs `cic-relay-signing`
- Git state repo = bare git repo, `state`/`intent` orphan ágak
- CIC-Relay build: `GOOS=linux GOARCH=arm64` (Ampere A1 = ARM64), `TrustStoreLoaded=false`
  marad (dev mód)
- Terraform provider: `hashicorp/oci`

---

## Elvárt kimenetek (`output/`)

### 1. `output/iac/oci/`

- `main.tf` — `oci_identity_compartment`, `oci_core_vcn`, `oci_core_subnet`,
  `oci_core_internet_gateway`, `oci_core_route_table`, `oci_core_security_list`
  (`oci-infra-sketch.md` 2. fejezet szabályai), 4× `oci_core_instance`
  (`oci-infra-sketch.md` 3. fejezet)
- `variables.tf` — `tenancy_ocid`, `user_ocid`, `fingerprint`, `private_key_path`,
  `compartment_ocid`, `oci_region`, `ssh_public_key`
- `outputs.tf` — instance OCID-k és IP-k (különösen a `demo_target` OCID-ja —
  erre a `poc-observer-plugin-01` snapshot lépése hivatkozik)

### 2. `output/iac/vault/init.sh`

- `vault server -dev` indítás
- `transit` secrets engine bekapcsolása
- `cic-relay-signing` Transit kulcs létrehozása
  (`system-plan.md` 1.3 — pontos parancsok onnan átvehetők)

### 3. `output/iac/relay/config.yaml`

- `cic-relay` minimum konfig: `CIC_VAULT_KEY=cic-relay-signing`, Vault cím,
  git state repo elérési út, `TrustStoreLoaded: false`

### 4. `output/iac/git-state-repo/init.sh`

- bare repo init (`git init --bare`)
- `state` és `intent` orphan ágak létrehozása és push
  (`system-plan.md` 1.4 — pontos parancsok onnan átvehetők)

### 5. `output/setup-guide.md`

Lépésről lépésre:
- OCI Terraform `apply` (region-választás megjegyzés az Ampere A1 kapacitás-korlát miatt,
  `oci-infra-sketch.md` 5. fejezet)
- Vault dev mode indítás és Transit kulcs ellenőrzés
- `cic-relay` build (ARM64) és deploy a Relay VM-re, health check
- `git log state/` és `git log intent/` — üres (csak init commit) ágak ellenőrzése

---

## Ellenőrzési feltételek (Definition of Done)

- [ ] `terraform plan` fut hibátlanul az `oci-infra-sketch.md` resource-listájával
- [ ] `cic-relay` ARM64 build sikeres, health check válaszol
- [ ] `git log state/` és `git log intent/` végrehajtható (orphan ágak léteznek)
- [ ] Vault dev mode elérhető, `cic-relay-signing` Transit kulcs beállítva
- [ ] `outputs.tf` exportálja a `demo_target` instance OCID-ját

---

## Amit NE csinálj

- Ne implementálj semmit a `core/modules/pocobs/`-ban (ez a `poc-observer-plugin-01` scope-ja)
- Ne implementálj `ActualStateCollector`-t (`poc-observer-plugin-01`)
- Ne aktiváld a Vault signinget a `schemacompile`/`schemapipeline` artifact-okon
  (`poc-schema-signing-01` scope-ja) — itt csak a Transit kulcs létrehozása a feladat
- Ne vitasd a Proxmox vs OCI döntést, ne tervezz alternatívát

---

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Terraform HCL, shell script, YAML: **angolul**

## Git

Push csak `feature/poc-infra-01` branch-re.
