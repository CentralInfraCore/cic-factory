# Infrastruktúra döntés — Proxmox vs OCI Free Tier

KB alap: add.md 6. fejezet (v1–v3 infrastruktúra roadmap), c453 (schemapipeline docker exec)

---

## Követelmények a demonstrációhoz

A PoC v1 demonstrációhoz a következő infrastruktúra szükséges (add.md 6. fejezet):

- Virtuális gépek (VM) provizionálása és törlése (Terraform által)
- Hálózati szegmens, tűzfalszabályok
- Vault (mem mód elfogadható v1-ben)
- CIC-Relay futtatása
- PBS snapshot képesség (actual state rögzítés)
- Git repo a state/ és intent/ ágakhoz
- Bastion (opcionális, de ajánlott)

---

## Összehasonlítás

### Proxmox

**Előnyök:**
- Teljes kontroll: VM lifecycle (create/destroy) teljesen programozható Terraformmal
- Terraform Proxmox provider elérhető és aktívan fejlesztett
- Nincs külső függőség, nincs hálózati latencia, offline is működik
- A `v1 → v2 → v3` roadmap (add.md 6.) lokális Proxmox-ra épül explicit módon
- PBS (Proxmox Backup Server) natívan integrált — ez a dokumentációban hivatkozott PBS réteg (c2585, c2616)
- VyOS + OpenSwitch hálózati réteg futtatható Proxmox VM-ként
- Docker exec alapú schemapipeline (c453) lokálisan működik

**Hátrányok:**
- Hardvert igényel (vagy meglévő Proxmox cluster)
- Beállítási overhead

---

### OCI Free Tier (Oracle Cloud Infrastructure)

**Előnyök:**
- Ingyenes Ampere A1 VM-ek (4 OCPU, 24 GB RAM free tier)
- Nincs hardver szükséges
- Terraform OCI provider elérhető

**Hátrányok:**
- VM lifecycle korlátozások: free tier VM-ek törlése/újraindítása lassan propagál, race condition a demonstráció során
- PBS integráció nem natív — OCI-ban nincs Proxmox Backup Server, helyettesítő megoldást kell keresni
- `HARD_DRIFT` demonstráció (8.3 fázis) nehezebbé válik, ha a VM destroy lassú vagy inkonzisztens az OCI API-n
- Hálózati szegmens + tűzfalszabályok kézi módosítása (8.2 fázis) OCI VCN-ben komplexebb
- VyOS / OpenSwitch futtatása OCI-ban nem triviális
- Internet-függő: ha az OCI API lassú, a demonstráció akadozhat
- `v1 → v2 → v3` tervben nincs OCI — az architektúrális döntések Proxmox-ra épülnek

---

## Döntés: Proxmox

**Javasolt: Proxmox**

**Indoklás:**

1. **PBS natív integráció** — a CIC architektúra explicit módon PBS-t hivatkozik az actual state rögzítésére (c2585, c2616). OCI-ban ezt szimulálni kell, ami a demonstráció hitelessége ellen hat.

2. **VM lifecycle teljes kontroll** — a 8.3 fázis (Hard Drift) csak akkor demonstrálható meggyőzően, ha a VM valóban azonnal eltűnik. Proxmox-on ez azonnali, OCI-ban nem garantált.

3. **add.md roadmap konzisztencia** — a specifikáció explicit v1 infrastruktúrája: `Proxmox + VyOS + OpenSwitch + Bastion + Vault(mem) + Relay`. Az OCI eltérítés az architektúrális döntésektől való eltérés.

4. **Offline demonstrálhatóság** — ügyfél előtt bemutatott PoC-nál a hálózatfüggőség kockázat. Proxmox-on helyi LAN elegendő.

5. **Teljes IaC kontroll** — Terraform Proxmox provider (bpg/proxmox) érett, a teljes lifecycle (VM create, network config, destroy) szkriptelhető.

---

## Proxmox v1 minimális konfiguráció

```
Proxmox host (meglévő vagy dedikált szerver)
├── VM: Bastion (Ubuntu, SSH jump host)
├── VM: Vault (mem mode, v1-ben elegendő)
├── VM: CIC-Relay (Go binary + plugin .so fájlok)
├── VM: Demo target (ez az infrastruktúra amit Terraform provizionál/töröl)
├── Network: VyOS router (tűzfalszabályok kézi módosítása 8.2 fázisban)
└── PBS: Proxmox Backup Server (actual state snapshot → pbs_root_hash)
```

**Terraform provider:** `github.com/bpg/terraform-provider-proxmox` — v0.60+

**Git state repo:** helyi Gitea (v2-ben) vagy egyszerű bare git repo (v1-ben elegendő)
