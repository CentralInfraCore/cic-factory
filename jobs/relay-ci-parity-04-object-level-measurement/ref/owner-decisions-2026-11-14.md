# Tulajdonosi döntések és utasítás a PR-04-hez (2026-11-14)

Forrás: a tulajdonos beillesztett üzenete a PR-01–03 lezárása után. Szó szerinti átvétel (a bevezető bekezdés kihagyásával).

## Javasolt döntések

| Kérdés | Döntés | Indok |
|---|---|---|
| 1. Unviable: 83/300 | Nem bukik a kapu, de kötelezően külön kimutatandó | Az unviable nem azonos a túlélő mutánssal. Nem szabad sem automatikusan sikernek, sem hibának számítani. |
| 2. Rust mutation score | `caught / (caught + missed)` | A ténylegesen értékelhető mutációkon mért arány. A timeout és egyéb státusz külön kezelendő, dokumentált szabály szerint. |
| 3. goastdump: 78% | Bevonjuk a PR-04 mérési scope-jába | Nem engedném eltüntetni a gyenge területet a teljes Go-átlag mögött. |

A Rust 90%-os küszöböt csak az egyértelmű score-definíció rögzítése után érvényesíteném. Az unviable arányára külön figyelmeztetési és később szigorítható kaput vezetnék be, **mutation-policy/2** alatt.

## PR-04 — elvárt tartalom

Itt már a Forms szemléletét vinném tovább: ne pusztán globális százalékokat gyűjtsünk, hanem bizonyítható legyen, hogy az egyes produkciós objektumok milyen ellenőrzést kaptak.

1. **Branch coverage:** Rust és Go esetén külön, csomag- és objektumszintű bontással, ahol a mérőeszköz ezt hitelesen támogatja.
2. **Object inventory:** produkciós függvények, metódusok és releváns implementációs egységek azonosítása stabil kulcsokkal.
3. **Coverage mapping:** objektum → teszt → coverage → mutation evidence, a nem feloldható kapcsolatok külön jelzésével.
4. **Change impact:** megváltozott produkciós objektum és releváns függőségei alapján érintettségi kimutatás.
5. **Evidence:** canonical formátum, bemeneti digestek, toolchain-verziók és reprodukálható mérési eredmények.
6. **Gate:** globális és objektumszintű eredmények elkülönítése; a hiányzó mérés nem válhat implicit sikeres ellenőrzéssé.

Fontos különbség: **a PR-04 még ne vezessen be automatikus tesztkihagyást**. Előbb bizonyítsa a mérési és objektum-hozzárendelési modell helyességét. A Forms reuse-kerneljének elveit később lehet biztonságosan ráépíteni.

A `tools/goastdump` esetében a 78%-os coverage önmagában még nem bizonyítja, hogy kritikusan gyenge. Azt kell először tisztázni, hogy a hiányzó lefedettség AST-feldolgozási, hibakezelési vagy kevésbé lényeges diagnosztikai ágakat érint-e.

## Utasítás a CI-t építő agentnek

A PR-01–03 lezárását elfogadom a megadott merge-commitok és main-CI eredmények alapján.

A következő lépés a PR-04 job-spec elkészítése az #169 szerint.

Döntések:

- Az unviable mutációk ne számítsanak sem caught, sem missed eredménynek. Külön kötelező metrikaként szerepeljenek. A jelenlegi érték ne buktasson, de a későbbi szigorítás kizárólag mutation-policy/2 verzióváltással történhet.
- A Rust mutation score alapja: caught / (caught + missed). Minden egyéb mutációs státusz kezelését és a nevezőből történő kizárását külön dokumentálni kell. A 90%-os küszöb ennek alapján értelmezendő.
- A tools/goastdump kerüljön be a PR-04 mérési scope-jába, külön riportolással.

A PR-04 célja nem egyszerűen a coverage növelése, hanem a mérés objektumszintű, ellenőrizhető modelljének kialakítása.

Elvárások:

- Branch coverage Rust és Go esetén, az eszközök tényleges képességeinek megfelelően.
- Produkciós objektumok stabil azonosítása.
- Objektum–teszt–coverage–mutation kapcsolatok felépítése.
- A nem mérhető és nem hozzárendelhető objektumok explicit UNVERIFIABLE jelölése.
- Canonical evidence és reprodukálható mérési eredmények.
- Globális és objektumszintű metrikák elkülönítése.
- A Forms CI minőségi és bizonyítási elveivel való konzisztencia.

A specifikációban különítsd el a közvetlenül megvalósítható funkciókat és azokat, amelyek további mérőeszközt vagy instrumentációt igényelnek.

Automatikus tesztkihagyás, reuse-optimalizáció és új, bizonyítatlan objektumszintű blocking gate egyelőre ne kerüljön bele.

Először a teljes job-spec készüljön el, konkrét elfogadási kritériumokkal, mérési korlátokkal, negatív tesztekkel és CI evidence-követelményekkel. Implementáció csak a specifikáció felülvizsgálata után indulhat.

A Relay CI fejlesztésének nem az a végső célja, hogy ugyanazokat a százalékokat produkálja, mint a Forms. Hanem hogy ugyanazzal a bizonyítási szigorral tudjon állításokat tenni a saját kódjáról.
