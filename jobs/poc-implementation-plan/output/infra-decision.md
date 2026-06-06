# Infrastruktúra Döntési Pont — Proxmox vs Oracle Cloud (OCI Free Tier)

## Kontextus

A PoC v1 célja a lokális, önálló bizonyítási kör felépítése:
`Proxmox/OCI + VyOS + Vault(mem) + Relay`

A demo forgatókönyv szempontjából a következő követelmények adottak:
- Terraform IaC provizionálás futtatható legyen valós infrastruktúrán
- 4–5 kézi módosítás alkalmazható (szabályok, konfig, erőforrások)
- Infrastruktúra törlés és újjáépítés végrehajtható
- ProofTrace + state branch commit valós időben látható

---

## Elemzés

### Proxmox (helyi, on-premise)

**Előnyök:**
- Teljes kontroll: nincs hálózati latencia, nincs cloud rate limit, offline is működik
- VyOS, OpenSwitch, Bastion: dedikált VM-ek könnyen kezelhetők Terraform Proxmox providerrel
- Vault (in-memory dev mode): lokálisan fut, nincs külső függőség
- Demo körülmények: képernyőn pörögnek a commitok — helyi rendszernél ez gyorsabb és megbízhatóbb
- IaC szkeletonok generálása és tesztelése: nincs cloud cost, nincs API limit
- A CIC-Relay `make dev-vault` és `make build` megvan — lokálisan is fut

**Hátrányok:**
- Hardver szükséges: legalább egy dedikált szerver vagy workstation (pl. mini-PC, NUC, stb.)
- Initiális setup (Proxmox telepítés, hálózat konfiguráció): egyszeri, de időigényes
- Terraform Proxmox provider: kevésbé "mainstream" mint AWS/OCI, de stabil és dokumentált

**Terraform integráció:** `terraform-provider-proxmox` (Telmate vagy bpg/proxmox) — stabil, PoC-ra alkalmas

---

### Oracle Cloud (OCI Free Tier)

**Előnyök:**
- Mindig ingyenes tier: 2 AMD Micro VM (1/8 OCPU, 1 GB RAM) + 4 ARM VM (24 GB RAM összesen)
- Nincs hardver kiadás
- OCI Terraform provider: hivatalosan támogatott, jól dokumentált

**Hátrányok:**
- Always Free korlátok: erőforrás-korlátok jelentősek, VyOS / OpenSwitch VM-ek + Bastion + Vault + Relay → valószínűleg kifut a free limitből
- Hálózati latencia: demo közben a commitok "pörögnek" — cloud esetén lassabb, kevésbé látványos
- VyOS OCI-n: lehetséges, de ritkán tesztelt, community support kell
- API rate limiting: gyors Terraform apply/destroy ciklusoknál (demo) problémás lehet
- Nincs teljes kontroll: hálózati szegmensek, tűzfalszabályok cloud-specifikus korlátokkal
- Account függőség: OCI account szükséges, always free nem garantált minden régióban

**Terraform integráció:** `hashicorp/oci` — hivatalos, de PoC-ra a free tier korlátok megkötik

---

## IaC Abstraction Réteg követelménye

Ha **mindkét platform** szóba jön (pl. v1 Proxmox, v2+ OCI), kötelező az IaC abstraction réteg:

```
CIC IaC Schema (platform-független)
    ↓
Provider-specifikus Terraform modul
    ├── modules/proxmox/  ← Proxmox VM, hálózat, tűzfal
    └── modules/oci/      ← OCI Compute, VCN, Security List
```

Az abstraction réteg:
- A CIC IaC ontológia gráf-alapú: `Relay` → `Host` → `Service` — ez platform-független
- A Terraform modulok a konkrét provider API-ra képezik le a CIC objektumokat
- A `state/` ág tartalma platformtól független (`desired_state.json`, `actual_state.json`, `prooftrace.json`)

---

## Javaslat

**PoC v1-hez: Proxmox az ajánlott platform.**

Indoklás:
1. **Demo minőség**: helyi infrastruktúrán a Terraform apply/destroy gyors, a commitok valós időben láthatók — ez a demo "pörögnek a commitok" élménye szempontjából kritikus
2. **Teljes kontroll**: VyOS, OpenSwitch, Bastion, Vault(mem) mind lokálisan fut — nincs cloud dependency
3. **Hálózati valósság**: Proxmox-on valódi hálózati szegmensek, tűzfalszabályok kezelhetők — ez teszi a drift demonstrációt hitelessé
4. **Nincs free tier limit**: a demo törlés+újjáépítés ciklusa nem ütközik resource quotába
5. **Fejlesztői közelség**: a `make dev-vault`, `make build` és a relay indítása ugyanazon a gépen futhat

**OCI Free Tier ajánlott fázis:** PoC v2+ esetén, ha cloud-natív demonstráció szükséges, vagy ha Proxmox hardver nem áll rendelkezésre. Ebben az esetben az IaC abstraction réteg (provider modulok) a v1 Proxmox szkeletonokból deriválható.

**Minimális Proxmox hardver PoC v1-hez:**
- 1 fizikai gép vagy erős workstation (pl. 16 GB RAM, 8 mag)
- Proxmox VE 8.x
- Minimum VM-ek: 1× VyOS router, 1× Bastion/Jump host, 1× Relay (Go binary), Vault in-memory

---

## Döntési mátrix

| Szempont | Proxmox | OCI Free Tier |
|---|---|---|
| Demo látványosság | Kiváló | Közepes |
| Terraform integráció | Jó (community provider) | Kiváló (official) |
| Erőforrás korlát | Nincs (saját hw) | Jelentős |
| VyOS támogatás | Kiváló | Korlátozott |
| Vault (in-memory) | Egyszerű | Egyszerű |
| IaC abstraction szükséges | Ha OCI is kell: igen | Igen |
| Hálózati valósság | Teljes | Részleges |
| **Összesített PoC v1** | **Ajánlott** | Alternatív |
