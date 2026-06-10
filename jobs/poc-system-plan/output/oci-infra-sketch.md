# OCI Infrastruktúra Vázlat — PoC v1

> Nem teljes Terraform kód — resource azonosítók, típusok, és OCI Free Tier korlátok.
> Részletes lépések: `system-plan.md` 1. fejezet.

---

## 1. Identity / Compartment

| Resource | Típus | Megjegyzés |
|---|---|---|
| `oci_identity_compartment.cic_poc` | compartment | minden PoC erőforrás ide kerül; elkülöníti a quota-t a tenancy más erőforrásaitól |

---

## 2. Hálózat

| Resource | Típus | Megjegyzés |
|---|---|---|
| `oci_core_vcn.cic_poc_vcn` | VCN | pl. CIDR `10.0.0.0/16` |
| `oci_core_subnet.cic_poc_subnet` | subnet | egy publikus subnet, `10.0.1.0/24` — PoC egyszerűsítés, nincs külön privát subnet |
| `oci_core_internet_gateway.cic_poc_igw` | internet gateway | publikus subnet route-jához |
| `oci_core_route_table.cic_poc_rt` | route table | default route → IGW |
| `oci_core_security_list.cic_poc_sl` | security list | lásd alább |

### Security List szabályok (kiindulási minimum)

| Irány | Forrás/Cél | Port | Cél |
|---|---|---|---|
| Ingress | `0.0.0.0/0` | TCP 22 | SSH a Bastion-ra |
| Ingress | VCN CIDR (`10.0.0.0/16`) | TCP 22 | SSH bastionról a többi VM-re |
| Ingress | VCN CIDR | TCP 8200 | Vault API (Relay → Vault) |
| Ingress | VCN CIDR | TCP egyéb | Relay HTTP API (port a relay configból) |
| Egress | `0.0.0.0/0` | all | kimenő (OCI API hívások, csomagfrissítés) |

> A 8.2 demo fázisban **ezt a security list-et módosítja kézzel** a human (5x) — ez generálja
> a drift eseményeket. A `security_rules_hash` (lásd `system-plan.md` 2.2) ennek a listának
> a kanonikus hash-e.

---

## 3. Compute Instance-ok

| Resource | Shape | OCPU / RAM | Szerep | Always Free? |
|---|---|---|---|---|
| `oci_core_instance.bastion` | `VM.Standard.E2.1.Micro` | 1 / 1 GB | SSH jump host | igen (AMD micro, 2 darab jár ingyen) |
| `oci_core_instance.vault` | `VM.Standard.A1.Flex` | 1 / 6 GB | Vault dev mode | igen (Ampere A1 keretből) |
| `oci_core_instance.relay` | `VM.Standard.A1.Flex` | 1 / 6 GB | CIC-Relay binary + natív modulok | igen (Ampere A1 keretből) |
| `oci_core_instance.demo_target` | `VM.Standard.A1.Flex` | 2 / 12 GB | Terraform create/destroy célpont (8.1/8.3) | igen (Ampere A1 keretből) |

**Ampere A1 Always Free összesítés:** 1+1+2 = **4 OCPU**, 6+6+12 = **24 GB** — pontosan a Free Tier
keret (4 OCPU / 24 GB összesen, region-enként). Ha a `demo_target` mérete csökken (pl. 1/6),
marad szabad kapacitás más célra, de a 2/12-es méret is belefér.

### Image / OS

- Bastion, Vault, Relay: Ubuntu 22.04 ARM64 (Ampere) ill. AMD64 (E2.1.Micro a bastionhoz — ha AMD shape)
- Demo target: tetszőleges (a demo szempontjából csak a lifecycle state számít)

---

## 4. SSH kulcskezelés

| Elem | Megjegyzés |
|---|---|
| `oci_core_instance.*.metadata.ssh_authorized_keys` | minden VM-hez ugyanaz a publikus kulcs (PoC egyszerűsítés) |
| Privát kulcs | csak a Bastion-on (vagy az operátor gépén) — a belső VM-ek a Bastionon keresztül érhetők el (`ProxyJump`) |
| Terraform változó | `var.ssh_public_key` — fájlból (`file("~/.ssh/cic_poc.pub")`) |

---

## 5. OCI Free Tier korlátok és figyelmeztetések

| Korlát | Hatás |
|---|---|
| **Ampere A1 region-elérhetőség** | nem minden region-ben van szabad Always Free Ampere A1 kapacitás — `terraform apply` `Out of host capacity` hibával elszállhat. Javasolt: olyan region kiválasztása, ahol a kapacitás elérhető (pl. próba régiók, vagy retry-loop a Terraform apply körül). |
| **2 AMD E2.1.Micro VM ingyenes** | ha a Bastion AMD shape-et használ, ez a kvóta korlátozza — PoC-ban 1 darab elég |
| **Block storage** | Always Free: 200 GB total (boot volume + block volume összesen) — 4 VM boot volume-ja ebbe kell hogy beférjen (alapértelmezett 50 GB/instance × 4 = 200 GB — pontosan a határon, érdemes kisebb boot volume méretet beállítani, pl. 50GB→47GB) |
| **Instance lifecycle propagálás** | create/terminate átmenetek néhány tíz másodperctől percekig tarthatnak — a `poc-drift-detection-01` poll-nak ezt figyelembe kell vennie (lásd `system-plan.md` 5. fejezet) |
| **VCN/subnet limitek** | Always Free: 2 VCN/region — a PoC 1-et használ, bőven a kereten belül |
| **API rate limit** | OCI API hívások (instance get, security list update) rate-limitáltak — a periodikus poll (30s) ezen belül marad |

---

## 6. Terraform state

A Terraform state (a Terraform saját állapotfájlja, **nem** a CIC `state/` git ág!) lokálisan
vagy OCI Object Storage backend-ben tárolható. PoC v1: lokális `terraform.tfstate` a Bastion vagy
az operátor gépén — elegendő a demóhoz, nem keverendő össze a CIC `actual_state.json`/`state/` ággal,
amely a CIC ProofTrace lánc része.
