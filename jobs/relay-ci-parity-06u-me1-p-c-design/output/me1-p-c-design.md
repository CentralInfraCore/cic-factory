# #212 — Az M-E1 P-c mérési terve, 1. fázis (06u)

**Státusz: terv (concept), nem végrehajtás.** Nem készült workflow-fájl, szkript vagy kód; nem indult futás; az X repón nem történt írás; bizonyíték letöltése nem történt. A terv két forrásból merít mért tényt: a tulajdonos gépén már meglévő bizonyítékból (futás 45063800073) és nyilvános, csak olvasó metaadat-lekérdezésekből (2. szakasz). A szerző képességei (megszakítás, törlés, újraindítás, szöveg-választás) **dokumentált, nem mért** feltételezések (3. szakasz). A terv megléte ≠ működik, a terv elfogadása ≠ sikeres mérés. **Az M-E1 ítélete nyitott, előzetesen `INCONCLUSIVE`**; ez a dokumentum nem mondja ki. **A D1–D8 és a D-c1–D-c5 döntések a tulajdonosnál nyitottak**; a terv a #81 teljes P-követelményével (D8) mint munkafeltevéssel dolgozik. A megvalósítás és a mérés külön GO. **Érvényes token semmilyen csatornán nem publikálható** (5. szakasz). K-5: 8/300.

## 1. Mi a P-c, és mit lehet belőle mérni

A #92 1.1 szakasza szerint a **P-c** a bizonyíték előállításának, kiválasztásának, elnyomásának és publikálásának szerzői befolyása.

**A „nulla befolyás" nem érhető el, és nem is mérhető.** Egy írási jogú PR-szerző a platformon dokumentáltan megszakíthat vagy újraindíthat futást, törölhet artifactot és naplót, elindíthatja a főági workflow-t, és választhat a futásai közül. Az **elérhetőség** tehát mindig befolyásolható. A követelmény ezért a **biztonságos hibaállapot**, amelyet a terv így fogalmaz meg (**D-c1: tulajdonosi jóváhagyás kell, mert ez a #81 „a PR szerzője nem módosíthatja" feltételének értelmezése**):

> **P-c teljesül**, ha a feltételezett (legrosszabb) szerzői képességek mellett **semmilyen szerzői cselekmény nem vezet ahhoz, hogy a verifier (i) olyan bizonyítékot fogad el, amely nem a döntés szempontjából releváns futáshoz tartozik, vagy (ii) a bizonyíték hiányát elfogadja**; és a szerző által választott szövegek (`workflow`, `actor`, `head_ref`) **nem kötőek**; és a publikálás időzítése nem tesz közzé érvényes tokent.

**Amit ez nem állít:** hogy a szerző nem tudja a bizonyítékot elnyomni (tudja); csak azt, hogy az elnyomás **fail-closed** (`NOT-READ`/`NOT-MET`), sosem elfogadás. Ha a tulajdonos a #81 szövegét úgy értelmezi, hogy az **elérhetőségre** is nulla befolyást követel, akkor **egyetlen mérés sem adhat PASS-t**, és az M-E1 `INCONCLUSIVE`/`FAIL`-hez vezet (D-c1 elutasítása).

## 2. Mért tények (olvasott, 2026-11-23; csak olvasó lekérdezések, a labor X repó, nem általánosíthatók)

| # | Tény | Forrás | Státusz |
|---|---|---|---|
| F1 | A futás 45063800073 tokenjének `check_run_id` állítása **137335381530**, ami **egyezik** a letöltött `api/jobs.json` job-azonosítójával és a `check_run_url`-ben szereplő check-run azonosítóval | a tulajdonos gépén lévő bizonyíték | **mért, egy futás** |
| F2 | A checks API a `4d432f5e…` commithoz két check-runt listáz: `me1-evidence` (137335381530) és `lab-gate` (137332377663); az `me1-evidence` check-run `status` `completed`, `conclusion` `success`, check-suite 121951553876 | `GET commits/{sha}/check-runs` | **mért, egy commit** |
| F3 | A checks API ismeri a `filter=latest` kapcsolót; egy futás mellett az eredménye azonos a teljes listával | `GET …/check-runs?filter=latest` | **mért (a kapcsoló létezése és egy futás); több futásnál a viselkedés nem mért** |
| F4 | Az artifact 14770618752 `expired` `false`, **`expires_at` 2026-11-23T20:06:16Z** (a megőrzés 1 nap) | `GET runs/ID/artifacts` | **mért**; **természetes kísérletet ad** (4. szakasz R2) |
| F5 | A token 31 állítást hordoz (a #91 3. szakasza), köztük a szerző által választható szöveget (`workflow`), a kiváltó azonosítót (`actor`, `actor_id`), az ágneveket (`head_ref`, `base_ref`), és a futásonként változót (`jti`, `run_number`, `iat`, `exp`, `nbf`, `check_run_id`) | a token olvasása | **mért, egy futás**; az `actor`, `actor_id`, `jti` értékét nem rögzítjük |

## 3. A fenyegetési modell: a szerző feltételezett képességei (dokumentált, **nem mért**)

A mérésükhöz második, alacsonyabb jogú (írás, de nem admin) azonosító kell; a labor tulajdonosa admin, a B sor (gépi fiókok) nem indult. **Ezért a terv a képességeket legrosszabb esetként feltételezi, és nem méri** (D-c5).

| # | Feltételezett képesség (írási jogú same-repo szerző) | Támadási vektor | Védő verifier-tulajdonság (4. szakasz) |
|---|---|---|---|
| A1 | futás megszakítása, sikertelenné tétele | elnyomás | V1 |
| A2 | artifact és napló törlése; a megőrzés lejártának kivárása | elnyomás | V1 |
| A3 | a főági workflow többszöri elindítása | kiválasztás | V2 |
| A4 | futás újraindítása (újabb kísérlet) a kedvező kiválasztásához | kiválasztás | V2 |
| A5 | a PR-futásban tetszőleges lépés: a token nem kérése, késői/korai publikálás, más tartalom | elnyomás, időzítés, csere | V1, V4, V5 |
| A6 | a szerző által választott szövegek: `workflow` név, ágnév, a kiváltó azonosító | névhamisítás | V3 |
| A7 | egy másik (nyilvános, lejárt) futás tokenjének másolása a saját artifactjába | csere | V5 (és P-a/S) |
| A8 | a bizonyíték-megőrzés (1 nap) kivárása vagy a futás késleltetése | időzítés | V1, V4 |

**Nem feltételezzük:** hogy a szerző a kibocsátó kulcsait, a tulajdonos gépét vagy a GitHub API-t kontrollálja (bizalmi gyökér: a GitHub és a tulajdonosi gép, a #91 5. szakasza).

## 4. A verifier tulajdonságai és a kontrolljaik

A **verifier** a `read-me1.py` (és a megvalósítási csomagban bővített változata); a kontrollok a verifier viselkedését mérik. Minden kontroll **tud bukni** (a megvalósításban mutációs ellenőrzéssel igazolva).

### V1 — Elnyomás: fail-closed

| Kontroll | Valódi vagy szintetikus | Elvárt |
|---|---|---|
| **R2: a lejárt artifact** — a 14770618752 az `expires_at` (2026-11-23T20:06:16Z) után, **új kimeneti könyvtárba** letöltve | **valódi, természetes, ingyenes** (csak olvasó API, K-5-be nem számít) | a gyűjtő megtagadja (`0 artifact(s) qualify`, az `expired` `true`), a verifier **nem** `EVIDENCE BOUND`; a már letöltött helyi másolat ettől független; **a meglévő (06r) `fetch-me1.sh`-val is elvégezhető**, megvalósítás nélkül |
| hiányzó artifact; törölt artifact; üres artifact; hiányzó token; hiányzó jegyzék-fájl | szintetikus | a gyűjtő/olvasó megtagadja vagy `INCOMPLETE (not read)`; sosem `BOUND` |
| megszakított, sikertelen, kihagyott, visszatartott futás | szintetikus (a visszatartott 1. kísérlet valódi adata a PK-futásból ismert) | a gyűjtő `check-run` ellenőrzése megtagadja (`conclusion` ≠ `success`, `status` ≠ `completed`) |
| a futás nem fejeződik be a várakozási időn belül | szintetikus | a szkript nem tölt le; nem fogad el |
| a bizalmi gyökér nem elérhető | a meglévő `fetch-jwks.sh` tesztek | az olvasó `INCOMPLETE` |

### V2 — Kiválasztás: a döntés szempontjából releváns futás platform-oldali forrásból

**A releváns futást nem a szerző vagy az olvasó bemenete határozza meg, hanem a platform checks API-ja** (D-c2): adott repó, commit és check-név (`me1-evidence`) alapján a checks API a releváns check-runt adja; a bizonyítéknak **hordoznia kell a `check_run_id` állítást, amely egyezik ezzel** (F1), és a `run_id`/`run_attempt` állításokat, amelyek a check-run futásához tartoznak.

| Kontroll | Valódi vagy szintetikus | Elvárt |
|---|---|---|
| **R1: az A futás levezetése** — a checks API-ból a `4d432f5e…` commithoz és az `me1-evidence` névhez levezetett `check_run_id` egyezik a token állításával (F1, F2) | **valódi, ingyenes, csak olvasó** | `MET`: a levezetett és az aláírt `check_run_id` egyezik |
| **R3: két futás ugyanazon a commiton** — a D6 szerinti második főági futás (B) után a commithoz **két** `me1-evidence` check-run tartozik: a checks API `filter=latest` viselkedése **mérendő**; az A bizonyítéka a legfrissebbre elvárva → elutasítva (`check_run_id`, `run_id`); a B bizonyítéka → `BOUND`; fordítva, ha a döntés az A-ra hivatkozik | **valódi** (a D6 futása, **a #92 keretében már számolt**, ezért P-c-ként 0 további kísérlet) | az elutasítás indokai között a `check_run_id`/`run_id`/`run_attempt` szerepel |
| több jelölt check-run, nincs egyértelmű „legfrissebb" szabály | szintetikus (hamis checks API) | **fail-closed**: a verifier **nem választ**, `NOT-READ`/`NOT-MET` |
| a levezetés forrása nem elérhető (a checks API hibája) | szintetikus | `INCOMPLETE`; nem esik vissza a szerző/olvasó által megadott azonosítóra |
| **R4 (opcionális, D-c3): újraindítás** — az A (vagy B) futás újraindítása után az új kísérlet új check-runt és `run_attempt` 2-t ad: az 1. kísérlet bizonyítéka a 2.-ra elvárva → elutasítva | **valódi**, +1 kísérlet (≤ 2 visszatartással), külön GO | az elutasítás indokai között a `run_attempt`/`check_run_id` szerepel |

**Korlát (kimondott):** a `check_run_id` állítás jelenléte **egy workflow_dispatch futáson mért**; pull_request-futásnál **hipotézis**. A levezetés forrása (a checks API) **ugyanaz a platform**, mint a kibocsátó: a bizalmi gyökér nem bővül, de a kötés nem független a GitHubtól.

### V3 — A szerző által választott szövegek nem kötőek

A tokenállítások három osztálya (a #91 3. szakaszának mért állításnevei alapján):

| Osztály | Állítások | Szabály |
|---|---|---|
| **kötő** | `repository`, `repository_id`, `repository_owner_id`, `sub`, `ref`, `sha`, `workflow_sha`, `job_workflow_sha`, `workflow_ref`, `event_name`, `run_id`, `run_attempt`, `check_run_id` | eltérésük `NOT-MET` |
| **szerző-választott, nem kötő** | `workflow` (a workflow neve), `actor`, `actor_id`, `head_ref`, `base_ref` | a verifier **nem használja**; változtatásuk **nem** változtatja a verdiktet |
| **futásonként változó, informatív** | `jti`, `run_number`, `iat`, `exp`, `nbf` | az `iat`/`exp`/`nbf` csak az időablak- és lejárat-ellenőrzésben szerepel |

| Kontroll | Valódi vagy szintetikus | Elvárt |
|---|---|---|
| minden **szerző-választott** állítás megváltoztatása (újra aláírt szintetikus tokenekkel) | szintetikus | a verdikt **változatlan** (`EVIDENCE BOUND, …`): a verifier érzéketlen rájuk |
| minden **kötő** állítás megváltoztatása | szintetikus | `NOT-MET` az adott soron: a verifier érzékeny rájuk |
| a névhamisítás valódi esete: a P2 (azonos nevű másik workflow) | valódi, a #92 mérésében | a `workflow` név azonossága nem ad hamis megerősítést |

### V4 — Az időzítés: érvényes token nem kerül közzé

| Kontroll | Valódi vagy szintetikus | Elvárt |
|---|---|---|
| a token a lejárata előtt került az artifactba (a szerző korán publikál) | szintetikus (az olvasó `provably expired` sora) | `NOT-MET` |
| az artifact az időablakon kívül jött létre; két azonos nevű artifact | szintetikus (a meglévő tesztek) | megtagadva |
| a lejárat-kapus workflow fail-closed leállása (hiányzó/távoli `exp`) | a #89 `test-me1-body.py` (23 ellenőrzés, szimulált órával) | nincs token, nincs feltöltés |
| **a támadó korai publikálása valódi futásban** | **NEM futtatjuk**: az maga lenne a token-kitettség (5. szakasz) | — |

### V5 — A tartalom cseréje

A másolt, lejárt (publikus) token egy másik futás artifactjában (A7): a verifier a **saját futásához** (artifact azonosítója és ablaka szerint) kötött `run_id`/`run_attempt`/`check_run_id` állításokat veti össze az API-val → elutasítás (a #92 S1–S3 és a P-a kontrollok fedik). **P-c-ben külön szintetikus eset:** a támadó a saját futása artifactjába másolja az A futás valódi tokenjét → `NOT-MET` (`run_id`, `check_run_id`).

### V6 — A szerzői képességek mérése

**Nincs a tervben** (D-c5): a második azonosító nélkül a képességek (A1–A8) nem mérhetők. A P-c ítélete ezért a **verifier viselkedésére** szól a feltételezett képességek mellett, nem a szerzői képességek igazolására.

## 5. Token-kezelés (érvényes token semmilyen csatornán nem publikálható)

1. **A P-c-ben nincs új token-kiadás.** A V2 valódi kontrolljai a **meglévő, review-zott `me1-evidence.yml`** futásait használják (R1 a meglévőt olvassa, R3 a D6 futása, R4 az újraindítás): a lejárat-kapus publikálás változatlan (`exp + 121 s`, szigorú óra-ellenőrzés, fail-closed, szerveridős olvasó-sor).
2. **A támadói viselkedés (korai/más csatornás publikálás) nem fut**; szintetikus tokenekkel modellezett (V4).
3. **A levezetés csak nyilvános metaadatot olvas** (checks API); a verifier nem ír ki tokent; a bizonyíték a tulajdonos gépén marad.
4. **A természetes kísérlet (R2) nem tölt le érvényes tokent**: az artifact lejárt, a lejárt token pedig a publikálás idején is lejárt volt.

## 6. Mérési protokoll (a megvalósítás után, külön GO-kkal)

| Lépés | Mi | K-5 | GO |
|---|---|---|---|
| 1 | a megvalósítási csomag (7. szakasz) szintetikus tesztjei és mutációs ellenőrzései | 0 | külön |
| 2 | **R1:** levezetés az A futásra (csak olvasó, ingyenes) | 0 | külön |
| 3 | **R2:** a lejárt artifact letöltési kísérlete az `expires_at` (2026-11-23T20:06:16Z) után; ha a megvalósítás addig nem kész, az artifact **már lejárt**, és a természetes kísérlet a lejárat utáni lekérdezéssel is elvégezhető (a lejárat tény marad) | 0 | külön |
| 4 | **R3:** a D6 szerinti második főági futás (a #92 szerint), a checks API `filter=latest` mérése, az A/B bizonyítékok keresztezése | **0 további** (a #92-ben számolt) | a #92 D6-hoz kötött |
| 5 | **R4 (opcionális, D-c3):** egy futás újraindítása | +1 (≤ +2 visszatartással) | külön |

## 7. A megvalósítási csomag tartalma (külön GO, külön review; ebben a PR-ban NINCS megvalósítás)

1. **A levezető modul** (a checks API olvasása commit + check-név szerint; fail-closed a több jelöltnél és az elérhetetlenségnél; mockolt tesztekkel és hamis API-val).
2. **Az olvasó bővítése:** a `check_run_id` mint kötelező kötés a levezetett azonosítóra (a szerző/olvasó bemenete **nem** írhatja felül); az állítások három osztálya kódban (kötő / szerző-választott nem kötő / informatív).
3. **A V1–V5 szintetikus kontrollok** és a **mutációs ellenőrzések**: a levezetés kikapcsolása, a `check_run_id` kötés kikapcsolása, egy szerző-választott állítás bekötése, a „legfrissebb" szabály kikapcsolása mind bukást ad.
4. **A tulajdonosi szkriptek:** az R2 természetes kísérlet új könyvtárba, az R3 keresztezése, az R4 (ha D-c3 igen); egyik sem indít automatikusan futást.
5. **A tesztek:** mockolt checks API, szimulált óra, parancssori belépési pontok alfolyamat-hívással.

## 8. Elfogadási kritériumok és az ítélet-leképezés

| Feltétel | Teljesül, ha | Nem teljesül / következmény |
|---|---|---|
| **C-c1 — elnyomás (V1)** | a szintetikus mátrix mind fail-closed, **és** az R2 valódi lejárt-artifact kísérlet megtagadva | bármely elfogadás → a P-c **bukott** |
| **C-c2 — kiválasztás (V2)** | az R1 `MET`, **és** az R3 (két futás ugyanazon a commiton) a levezetett legfrissebb futásra kötött, az elavult bizonyíték elutasítva a `check_run_id`/`run_id` indokkal; a több jelöltes eset fail-closed | az R3 hiánya (D6 nélkül) → részleges; a legfrissebb szabály nem egyértelmű és a verifier mégis választ → bukott |
| **C-c3 — szövegek (V3)** | a szerző-választott állítások megváltoztatása nem változtat a verdiktet, a kötőké igen | bármely szerző-választott állításra érzékeny verifier → a P-c bukott |
| **C-c4 — időzítés és csere (V4, V5)** | a korai publikálás, az időablakon kívüli, a kettős és a másolt-token esetek mind elutasítva | bármely elfogadás → bukott |
| **C-c5 — hatókör** | a jelentés kimondja, hogy a szerzői képességek feltételezettek (D-c5), a levezetés forrása a GitHub, és a mérés egy szervezetre, egy futástípusra szól | enélkül a PASS nem mondható ki |

**Az M-E1 ítélete (a mérés utáni jelentésben):**
- **PASS:** a #92 C1–C5 teljesül (a P-a/P-b, S, R, az attesztáció döntése), **és** C-c1–C-c5 teljesül, **és** a tulajdonos jóváhagyta a D-c1 értelmezést (a P-c a biztonságos hibaállapot), **és** a D8 a teljes követelmény. A PASS kimondása a hatókört viseli: same-repo PR, a vizsgált modell, egy szervezet; **az elnyomás lehetősége megmarad, csak fail-closed**.
- **FAIL:** a verifier bármely P-c kontrollban elfogad olyan bizonyítékot, amely nem a releváns futáshoz tartozik, vagy a hiányt elfogadja.
- **INCONCLUSIVE:** minden más eset (R3 hiánya, a levezetés forrása ambiguus vagy nem elérhető, a D-c1 elutasítva, a C-c5 hiányzik, a #92 feltételei nem teljesülnek).

**Nem következtethető:** hogy a szerző nem tud bizonyítékot elnyomni; fork-PR-ra; más szervezetre, a Relay-re vagy a production-re; a platform szerzői képességeinek mért ismerete.

## 9. K-5 keretigény (becslés, nem mért; kísérletenként)

| Lépés | Kísérlet (alap) | Feltételes felső |
|---|---|---|
| A #92 alapforgatókönyve (P1, P2, `lab-gate-pr`, D6 második főági futás) | 4 → **12/300** | 7 → 15/300 (a `lab-gate-pr` visszatartásával 16/300) |
| **P-c: R1, R2, a szintetikus kontrollok, a megvalósítási tesztek** | **0** | 0 |
| **P-c: R3** (a D6 futása) | **0 további** (a #92-ben számolt) | 0 |
| **P-c: R4 (opcionális, D-c3), egy futás újraindítása** | +1 | +2 |
| **Összesen (R4-gyel)** | **13/300** | **17/300** (a `lab-gate-pr` visszatartásával 18/300) |

**A P-c önmagában nem fogyaszt keretet** (R4 nélkül), mert a valódi kontrolljai a D6 futására és ingyenes olvasásokra épülnek. A D6 elmaradása a C-c2-t részlegessé teszi. Leállási küszöbök (#82 4. szakasz): 3 egymás utáni magyarázatlanul eltérő eredmény vagy 250 futás megoldatlan INCONCLUSIVE-okkal → szüneteltetés. **Automatikus újrafuttatás nincs.**

## 10. Tulajdonosi döntési pontok

| # | Döntés | Ajánlás |
|---|---|---|
| **D-c1** | A P-c értelmezése: a **biztonságos hibaállapot** (a szerző elnyomhat, de a verifier fail-closed, és nem fogad el nem releváns bizonyítékot), vagy az elérhetőségre is nulla befolyás | **biztonságos hibaállapot**; a második értelmezésben egyetlen mérés sem adhat PASS-t |
| **D-c2** | A döntés szempontjából releváns futás forrása | a **platform checks API-ja** (commit + check-név), nem a szerző/olvasó bemenete; a „legfrissebb" szabályt az R3 méri |
| **D-c3** | Az opcionális újraindítás (R4) a valódi kísérletválasztáshoz | **igen**, ha a #92 D6 megvan (+1 kísérlet); elhagyható a szintetikus fedezettel, a jelentés kimondja a korlátot |
| **D-c4** | Az R2 természetes kísérlet (lejárt artifact) | **igen**: ingyenes, csak olvasó, és az artifact ma 20:06:16Z-kor lejár |
| **D-c5** | A szerzői képességek mérése | **nem most**: második (írási, nem admin) azonosító kell (B sor); a képességek feltételezettek; a PASS hatóköre ezt kimondja |
| D6 (a #92-ből) | a második főági futás | **igen**: a C-c2 valódi alapja |
| D1–D8 (a #92-ből) | a tulajdonosi döntések | D1–D7 a mergelt terv ajánlása szerint, **D8: a teljes #81 követelmény** (a tulajdonos irányának megfelelően); formális rögzítése nyitott |

## 11. Kockázatok

| Kockázat | Védelem |
|---|---|
| Érvényes token kitettsége | 5. szakasz: nincs új token-kiadás; a támadói viselkedés nem fut; a levezetés csak nyilvános metaadatot olvas |
| A `check_run_id` állítás csak egy futástípuson mért | a korlát kimondva; pull_request-futásnál hipotézis, a #92 P1/P2 mérése adja az első adatot |
| A „legfrissebb check-run" szabály nem egyértelmű vagy platform-oldalon változó | az R3 méri; ambiguus esetben a verifier fail-closed; a viselkedés időbeli stabilitása nem mért |
| A levezetés forrása ugyanaz a platform | a bizalmi gyökér nem bővül; kimondva (C-c5) |
| A természetes kísérlet (R2) elmaradása | az artifact lejárta tény; a lekérdezés a lejárat után is elvégezhető |
| A szerzői képességek mérésének hiánya | feltételezett legrosszabb eset; a hatókör kimondott (D-c5) |
| A PASS félreértése az elnyomás lehetőségének hiányaként | a D-c1 szövege és a „nem következtethető" lista kimondja |

## 12. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A token `check_run_id` állítása egyezik a job-azonosítóval és a checks API check-run azonosítójával | **mért (labor, egy futás)** | F1, F2 | a tulajdonos gépén lévő bizonyíték és a checks API olvasása | pull_request-futásnál nem mért |
| Az artifact lejárata 2026-11-23T20:06:16Z | **mért** | F4 | `GET runs/ID/artifacts` | — |
| A `filter=latest` több futásnál a legfrissebbet adja | **dokumentált, nem mért** | F3 (egy futás) | az R3 | a viselkedés változhat |
| A szerző képességei (A1–A8) | **dokumentált, nem mért** | 3. szakasz | második azonosító (B sor) | a legrosszabb eset feltételezett |
| A verifier fail-closed az elnyomásra | tervezett követelmény; a szintetikus tesztek a #91–#92 láncban részben léteznek | V1 | a megvalósítás mátrixa, az R2 | az R2 a lejárat után mérhető |
| A szerző-választott szövegek nem kötőek | tervezett követelmény | V3 | szintetikus mutáció | — |
| A P-c teljesül | **nem állítom** | — | a mérés (külön GO) | — |
| Az elnyomás lehetősége megszűnik | **nem állítom; az ellenkezője feltételezett** | 1. szakasz | — | — |
| Az M-E1 ítélete | **nem állítom; előzetesen INCONCLUSIVE** | — | a mérés utáni jelentés | — |
| A K-5: a P-c önmagában 0, R4-gyel +1 (≤ +2) | **becslés, nem mért** | 9. szakasz | a futások listája | a D6 elmaradása és a visszatartások |
| Az X repó vagy az éles szervezet módosult | nem (**végrehajtási naplóra alapozott állítás**) | a terv készítésekor csak olvasó API-hívások és helyi fájlműveletek futottak | a session végrehajtási naplója; a `git log` ezt nem bizonyítja | a napló az én oldalam |

## 13. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét; nem állítja, hogy a P-c teljesül, és nem állítja, hogy a szerző nem tud bizonyítékot elnyomni.
- **Nem tekinti mértnek** a szerző képességeit és a `filter=latest` többfutásos viselkedését.
- **Nem tartalmaz** megvalósítást, workflow-fájlt, szkriptet, futást, PR-nyitást vagy bizonyíték-letöltést; ezek külön GO-t igényelnek.
- **Nem terjeszti ki** az eredményt fork-PR-ra, más szervezetre, a Relay-re vagy a production-re.
- **Nem módosítja** a #81–#92 tartalmát és a K-1–K-8 ajánlásokat.
