# Infrastruktúra döntési pont — Proxmox vs OCI Free Tier

**Feladat:** PoC v1 platform kiválasztása
**PoC v1 spec (add.md):** Proxmox + VyOS + OpenSwitch + Bastion + Vault(mem) + Relay

---

## Összehasonlítás

| Szempont | Proxmox | OCI Free Tier |
|---|---|---|
| **Hardver** | Saját/dedikált szerver | Oracle Cloud (shared, free tier) |
| **VM-ek száma** | Korlátlan (saját HW) | 2 AMD VM (1 OCPU, 1GB RAM) vagy 4 ARM Ampere VM (24GB RAM total) |
| **Hálózat** | Teljes L2/L3 kontroll (VyOS, VLAN, tűzfal) | SDN, korlátozott L2 hozzáférés |
| **VyOS integráció** | Natív — VyOS VM közvetlenül telepíthető | Nem natív — VyOS image import szükséges, networking korlátok |
| **ProofTrace auditálhatóság** | Teljes — commit hash ellenőrizhető, fizikai backup (PBS) | Részleges — nincs közvetlen PBS, vendor lock-in audit |
| **Vault(mem) futtatás** | Helyi VM-ben futtatható, izolált | Cloud VM-ben futtatható, de hálózati latency |
| **Reprodukálhatóság** | Magas — IaC + PBS snapshot | Közepes — cloud API változhat |
| **Offline képesség** | Teljes | Nem — internet-függő |
| **Demonstrálhatóság** | Magas — képernyőn látható VM-ek, commit-ok | Közepes — cloud console UI-ban |
| **Telepítési komplexitás** | Közepes — Proxmox setup szükséges | Alacsony — OCI console alapból elérhető |
| **Költség** | Hardver amortizáció | 0 Ft (free tier) |
| **add.md kompatibilitás** | ✅ Teljes (v1 spec pontosan Proxmox-alapú) | ⚠️ Részleges (VyOS, OpenSwitch korlátok) |

---

## Részletes elemzés

### Proxmox

**Erősségek:**
- Az add.md v1 spec **explicit Proxmox-ra épít**: "Proxmox + VyOS + OpenSwitch + Bastion + Vault(mem) + Relay"
- Teljes L2/L3 hálózati kontroll — VyOS router, VLAN szegmentáció, tűzfalszabályok változtatása a 8.2 fázishoz (kézi módosítások + drift detektálás) natívan megvalósítható
- PBS (Proxmox Backup Server) deduplikált snapshotokkal a fizikai állapot auditáláshoz
- Demonstráció: élőben látható VM lista, hálózati topológia — vizuálisan is meggyőző
- Reprodukálható és offline — nem függ cloud API-tól

**Gyengeségek:**
- Hardver szükséges (ha nincs már Proxmox szerver)
- Kezdeti setup idő (~1-2 nap)

### OCI Free Tier

**Erősségek:**
- Azonnali hozzáférés, 0 Ft
- ARM Ampere VM-ek (4× OCPU, 24GB RAM) elégségesek relay futtatáshoz

**Gyengeségek:**
- VyOS + OpenSwitch integrációja **nem trivális** OCI networking modellben — L2 hozzáférés korlátozott
- A 8.1 fázis ("tűzfalszabályok, hálózati szegmensek") nehezen demonstrálható OCI SDN-en keresztül
- PBS nem elérhető — fizikai proof réteg hiányzik
- Vendor dependency — OCI API változtatás az auditot érintheti
- Ingyenes kvóta korlátai: 10TB kimenő adatforgalom/hó, 2 block storage

---

## Javaslat

**PoC v1 → Proxmox**

**Indoklás:**
1. Az add.md spec **explicit Proxmox-alapú** — a tervezési elvek (VyOS, PBS, hálózati topológia) erre épülnek. OCI-n a PoC csak részlegesen valósítható meg.
2. A demonstráció értékét a **fizikailag megfigyelhető állapotváltozás** adja (VM-ek megjelennek/eltűnnek, ProofTrace commit-ok pörögnek) — ez Proxmox-on nativ, OCI console-on közvetett.
3. A drift detektálás (8.2 fázis) tűzfalszabály-módosítással demonstrálható — VyOS natív Proxmox-on, OCI-n emulálni kell.
4. Ha Proxmox szerver nem elérhető: OCI ARM Free Tier **ideiglenes alternatíva** — relay + Vault(mem) futtatható, de VyOS/OpenSwitch helyett egyszerűsített hálózattal. A demo értéke csökken.

**Ha Proxmox szerver már elérhető → Proxmox. Ha nincs hardver → OCI Free Tier ideiglenes relay sandbox, Proxmox setup párhuzamosan.**

---

## PoC v1 minimális infrastruktúra igény (Proxmox)

| VM | CPU | RAM | Szerep |
|---|---|---|---|
| bastion | 1 vCPU | 1 GB | SSH belépési pont, GPG kulcs |
| vyos-gw | 2 vCPU | 1 GB | L3 router, tűzfalszabályok (drift demo) |
| vault-dev | 1 vCPU | 2 GB | Vault dev mode (mem backend) |
| relay-01 | 2 vCPU | 4 GB | cic-relay binary, plugin .so betöltés |
| terraform-runner | 1 vCPU | 2 GB | Terraform CLI, state git push |

**Összesen:** 7 vCPU, 10 GB RAM — egy közepes Proxmox szerveren elfér.
