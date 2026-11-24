# 06w — független forrásreview (rögzítés)

**Eredet:** a review szövege a tulajdonos 2026-11-24-i üzenetében érkezett (a `REVIEW-PACKAGE-06w.md` feltöltése után); ez a fájl összefoglalja, nem helyettesíti. Az értékelt csomag: `~/.cache/ci-lab/pcf-ps2/REVIEW-PACKAGE-06w.md`, 174 426 bájt, sha256 `3bf482a99e2053c493daea7959a9686bee4e815f62429c88dec0036cbf4b7d2f` (a review szerint egyezik). A jelentett commit: `6d6fb37955dd56c7bb56557156c470df22b43fd4`.

## Amit a review függetlenül ellenőrzött
| Vizsgálat | Eredmény |
|---|---|
| a csomag SHA-256 és mérete | PASS |
| a beágyazott `read-me1.py` és `test-pcv.py` SHA-256 | PASS (egyezik a csomagban rögzítettel) |
| Python szintaktikai ellenőrzés | PASS |
| `read-me1.py --selftest`, saját újrafuttatás | PASS |
| saját szintetikus ellenpróbák a kinyert verifierrel | baseline BOUND; `nbf = iat + 60` BOUND; `nbf = iat + 61` NOT BOUND (az új `OIDC not-before` sor `NOT-MET`); negatív `nbf` NOT BOUND; `repository_owner` megváltoztatása BOUND; negatív `iat` NOT BOUND; logikai `exp` NOT BOUND |

## Döntések
| Tétel | Döntés |
|---|---|
| N1–N8 szerződés | ACCEPT |
| I1 egész NumericDate | ACCEPT (dokumentált szigorítás) |
| **I2 tolerancia 120 → 60 másodperc** | **ACCEPT, megerősítve:** az elfogadott óraeltérés általános követelmény, legfeljebb 60 s; a 120 s nem állítandó vissza (F-T-1 lezárva) |
| I3 K-idő szemantikai kontroll | ACCEPT |
| I4 nincs `nbf` alsó korlát | ACCEPT a jelenlegi szerződésben |
| `repository_owner` P-besorolás | ACCEPT |
| a verifier célzott működése | ACCEPT |
| teljes M-E1 | INCONCLUSIVE |

## Amit a review nem állít (kimondott korlátok)
- A 145 selftest és a 33 mutáció **jelentés szerinti** PASS, független teljes újrafuttatás nincs: a csomag nem tartalmazza a `me1-controls.py` teljes forrását (amelyre a `test-pcv.py` épül; a 06v-tal bájtra azonos, `cmp`).
- Az A/B származtatott kontrollok **jelentés szerint** MET, független újramérés nincs (az evidence-könyvtárak tokenekkel nincsenek a csomagban).
- A push, a PR létrehozása és a merge **külön tulajdonosi jóváhagyást** igényel. A review javaslata: a 06w helyi review-lezárása és a PR előkészítése, az új szerződés-állapot és a korábbi 36/38 eredmény külön megőrzésével.

M-E1: INCONCLUSIVE · K-5: 12/300.
