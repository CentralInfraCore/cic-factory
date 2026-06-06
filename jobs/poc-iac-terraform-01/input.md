# poc-iac-terraform-01 — Terraform IaC szkeletonok (Proxmox PoC v1)

## Feladat összefoglalása

A PoC v1 infrastruktúrájához szükséges Terraform IaC szkeletonok megvalósítása Proxmox provider alapján. A szkeletonok biztosítják a demo forgatókönyv (add.md 8.1 fázis) Terraform up/destroy/apply ciklusát.

Az output a `jobs/poc-iac-terraform-01/output/terraform/` mappába kerüljön (cic-factory klónban), és a CIC IaC ontológia elveit kövesse: graph-alapú, Desired/Actual State szétválasztás, platform-független CIC objektumok → provider-specifikus modulok.

## Célinfrastruktúra (PoC v1 stack)

```
Proxmox cluster
  ├── VM: vyos-router-01       (VyOS hálózati forgalomirányító)
  ├── VM: bastion-01           (Bastion/Jump host, SSH belépési pont)
  ├── VM: vault-01             (HashiCorp Vault in-memory, dev mode)
  └── VM: relay-01             (CIC-Relay Go bináris)
  
Hálózat:
  ├── Management network: 10.10.0.0/24
  └── Relay network: 10.20.0.0/24
```

## Megvalósítandó Terraform struktúra

```
output/terraform/
  ├── main.tf                  ← Provider konfiguráció (bpg/proxmox)
  ├── variables.tf             ← Paraméterek (Proxmox URL, node neve, stb.)
  ├── outputs.tf               ← Output értékek (VM IP-k, stb.)
  ├── modules/
  │   ├── vyos/
  │   │   ├── main.tf          ← VyOS VM definíció
  │   │   ├── variables.tf
  │   │   └── outputs.tf
  │   ├── bastion/
  │   │   ├── main.tf
  │   │   ├── variables.tf
  │   │   └── outputs.tf
  │   ├── vault/
  │   │   ├── main.tf
  │   │   ├── variables.tf
  │   │   └── outputs.tf
  │   └── relay/
  │       ├── main.tf
  │       └── variables.tf
  └── README.md                ← Rövid indítási útmutató
```

## CIC IaC séma fájlok (CIC-Relay relay.yaml formátum)

A Terraform mellett hozz létre CIC IaC YAML leírásokat is:

```
output/cic-iac/
  ├── relay.yaml               ← CIC Relay objektum
  └── hosts/
      ├── vyos-router-01.yaml
      ├── bastion-01.yaml
      ├── vault-01.yaml
      └── relay-01.yaml
```

A YAML formátum (meglévő testdata alapján):
```yaml
apiVersion: cic/v1
kind: Host
metadata:
  name: relay-01
spec:
  ip: "10.10.0.4"
  role: relay
  services:
    - name: cic-relay
      port: 8080
```

## Fontos követelmények

- **Provider:** `bpg/proxmox` (https://github.com/bpg/terraform-provider-proxmox) — szélesebb körben dokumentált, mint a Telmate
- **VM OS:** Ubuntu 22.04 cloud image (Proxmox template alapú)
- **VyOS:** VyOS 1.4 (rolling vagy LTS) — cloud-init kompatibilis image
- **Vault:** Ubuntu VM-re `vault` bináris telepítés (cloud-init user_data), `dev` mód indítás
- **Relay:** Ubuntu VM-re a CIC-Relay Go bináris másolás (Terraform provisioner vagy cloud-init)
- **Hálózat:** Proxmox Linux Bridge alapú (nem OVS) — PoC egyszerűség miatt
- **Változók:** Minden érzékeny adat (`proxmox_password`, stb.) `variables.tf`-ben deklarált, értékük `terraform.tfvars.example`-ban mintaként, de NEM a tényleges értékkel

## IaC abstraction réteg

A struktúra legyen előkészítve a platform-függetlenségre:

```
modules/
  ├── proxmox/    ← jelenlegi implementáció
  └── oci/        ← üres könyvtár + README placeholder ("OCI modulok: PoC v2+ célkitűzés")
```

## Elfogadási kritérium

- [ ] `terraform validate` hibamentes minden modulon
- [ ] `terraform plan` futtatható (Proxmox endpoint nélkül: `-target` nélkül, változók mock értékekkel)
- [ ] CIC IaC YAML fájlok az `apiVersion: cic/v1` + `kind: Relay/Host` formátumot követik
- [ ] `modules/oci/` placeholder létezik az abstraction rétegnek
- [ ] `README.md` tartalmazza: `terraform init`, `terraform apply`, `terraform destroy` lépéseket
- [ ] Nincs hardcoded IP/credential a verziókövető fájlokban
