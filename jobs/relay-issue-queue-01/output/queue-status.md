# relay-issue-queue-01 — sor végállapota (2026-11-15, a #58 véglegesítése)

Alap: `CentralInfraCore/CIC_Relay`, default ág `main`, jelenlegi `main@e43f2a8` (tree `6b9cc314e759e3485a7d278c52de2cc6a5a8e928`). Nyolc PR mergelve (a #173, #176, #182, #180, #177, #179, #181 és az integrációs regressziós teszt #190), nyolc issue lezárva (#157, #159, #160, #161, #163, #164, #165, #166). A PR-ok a tulajdonos kifejezett kérésére, a jóváhagyott (CI-vel igazolt) HEAD-en mergelődtek (`--merge --match-head-commit`), mindegyik előtt az aktuális main-hez igazítva; az issue-kat a tulajdonos kérésére zártam (a PR-ok `Refs`-t használtak), lezáró kommenttel.

| Issue | PR | Merge-commit | Issue |
|---|---|---|---|
| #160 nightly security | (nincs PR; a javítás #168) | n/a | **lezárva** a zöld nightly `security` jobbal (a teljes nightly még futott) |
| #161 recorder szerializálás | #173 | `9629baf` | **lezárva** |
| #159 kötelező trust mode | #176 | `e6d7616` | **lezárva** |
| #166 egységes trust context (A) | #182 | `156cc81` | **lezárva** |
| #163 actuate egress | #180 | `07bbce8` | **lezárva** |
| #165 proof persistence | #177 | `676f79c` | **lezárva** |
| #164 CRL | #179 | `8faf00c` | **lezárva** |
| (integrációs regressziós teszt, issue nélkül) | #190 | `e43f2a8` | mergelve |
| #157 compile autorizáció a végrehajtási határon | #181 | `c5ae320` | **lezárva** |
| #162 capability binding | — | — | **nyitva, HOLD**: a signing oldalon nincs rögzített boríték (`issue-162.md`) |
| #155 | — | — | **nyitva, HOLD**: külön, nem nyilvános kezelés alatt (nem része a nyilvános outputnak) |

## Követő issue-k (a lezáráskor dokumentált, de nem lefedett követelmények, összevonva)

| Issue | Tárgy |
|---|---|
| #185 | recorder: több író és context-tudatos zárvárakozás (#161) |
| #186 | evidence: workflow-szintű deklaráció és indulási ellenőrzés recorder nélkül (#165) |
| #187 | egress parity: közös policy, kérés-plafon, tartományok, belső célok (#163) |
| #188 | trust bootstrap: dev néma kihagyások, indulási hibák tesztje, első ágyazott modul (#159, #166) |
| #189 | PKI: SPKI-pin forrás, CRL-frissítési modell, folyamat-újraindítási teszt (#164) |

## Integrációs mérés

`integration-measurement.md`: az integrációs regressziós teszt (#190, mergelve) a mergelt `main@e43f2a8` fáján, 13 mutációs ellenpróbával; a nyers kimenetek az `evidence/integration-regression/` alatt, a `PROVENANCE.txt` köti őket a commit- és tree-azonosítókhoz. **A lezárások fejlesztési mérföldkő, nem produkciós jóváhagyás**: a #155 (nem nyilvános kezelés) és a #162 (signing szerződés) rendezéséig a produkciós biztonsági jóváhagyás HOLD; ezek, valamint a #185–#189 külön munkacsomag, a job lezárását nem blokkolják.

## Jelzések

- A GitHub által generált merge-commitok nem a fejlesztői kulccsal aláírtak; a commit-aláírás átalakulása a tulajdonos oldalán van.
- Más szál PR-jai (#183, #184, CI-mérés) is mozogtak; ezekhez nem nyúltam.
- A `work event done` kezdetben a ticket-formátum hiba miatt nem futott le (a `WORK_TICKET` a slugot kapja, a runtime neve eltér); az esemény azóta a megkerüléssel (`WORK_TICKET` a runtime nevére állítva) sikeresen lezárva. A hiba javítása külön, a másik repóban előkészített patch (nincs alkalmazva).
