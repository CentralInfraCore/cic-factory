# #212 — A P-a/P-b és P-c/V közös megvalósítási csomagja (06v)

**Státusz: megvalósítás, kizárólag szintetikus tesztekkel.** Nem indult GitHub Actions-futás, nem történt írás az X repón, nem nyílt PR, nem töltöttem le bizonyítékot, és a tulajdonosi szkriptek csak helyi bare repón és hamis `gh`-n futottak. A `pull_request`-futások állításainak szemantikája **hipotézis** (3. szakasz). **A P-c/F nem része a csomagnak, és teljes M-E1 PASS nem mondható ki**: a tulajdonosi döntések (D8, D-c6) szerint a teljes #81 követelményhez a valós szerzői viselkedés vizsgálata is kell. **Az M-E1 ítélete nyitott, `INCONCLUSIVE`.** A megvalósítás megléte ≠ működik a GitHubon; a zöld teszt ≠ sikeres mérés. K-5: 8/300, a csomag nem fogyasztott keretet.

## 1. A rögzített döntések, amelyeket a csomag követ

| Döntés | Tartalom | Hol érvényesül |
|---|---|---|
| D1 | same-repo PR, a fork-PR a B sor után | a P1/P2 egy ágon, a repó írási joga mellett; a fork-eset nincs lefedve |
| D2 | lejárat-kapus teljes token, érvényes token nem publikálható | a P1/P2 törzse a #89 lejárat-kapus törzs változatlanul; az ellenőrző teljes szövegegyezést kényszerít |
| D3 | P1 és P2 együtt | egy PR, két workflow |
| D4 | a mérési PR lezárása tulajdonosi művelet, az ág törlése külön | a PR nem mergelendő; a szkriptek egyike sem töröl |
| D5 | az artifact-attestáció külön csomag, nem teljesült | nincs a csomagban |
| D6, D-c3, D-c4 | a második főági futás, az újraindítás, a lejárt artifact lekérdezése külön GO | nincs elindítva; a szkriptek/kontrollok előkészítettek, de nem futtattak valódi adatra |
| D8, D-c6 | a teljes #81 követelmény; a P-c/V önmagában nem elég | a csomag a P-c/V-t és a P-a/P-b-t adja részeredményként, a P-c/F-et nem |
| D-c1, D-c2 | biztonságos hibaállapot; előre rögzített döntési politika, a checks API csak felderít | 4. szakasz |

## 2. Mit tartalmaz a csomag

| Elem | Fájl | Szerep |
|---|---|---|
| **P1** | `payload/p1/.github/workflows/me1-evidence.yml` (blob `b5d21c2d6d99d87ef6e508bf85984fc35c400b80`) | a védett workflow **a helyén módosítva**: `pull_request` trigger hozzáadva (a `workflow_dispatch` marad); a lejárat-kapus törzs, a közönség és az artifact-név **változatlan** |
| **P2** | `payload/p2/.github/workflows/me1-evidence-twin.yml` (blob `35e27ba42a45cb1fec18c66ec7a519c5c16a2790`) | **új** workflow, **azonos `name:` és job-névvel**, csak `pull_request` triggerrel, azonos törzzsel |
| P-ellenőrző | `check-me1-p-workflows.py` | pontosan a két fájl, teljes dokumentum- és `run`-test-egyezés, 81 beültetett eltérés |
| Olvasó | `harness/read-me1.py` | az #90-es olvasó + **döntési politika mód** (`--policy`), a felderítés és keresztellenőrzés, az állításosztályok |
| Gyűjtő | `harness/fetch-me1.sh` | + `pr` profil (a **PR-fej jogosultsága** a PR API-objektumához kötve, `api/pr.json`; a futás SHA-mezői csak **megfigyelve**), + a checks-API lista (`api/check-runs.json`) a manifestben |
| Kontrollok | `harness/me1-controls.py` | hamisítási, keresztezési és visszajátszási kontrollok (valódi bizonyítékra is ráengedhetők, offline), a `describe-pr` hipotézis-értékelő, a `--attach-listing` |
| Tesztek | `harness/test-pcv.py`, `test-fetch-me1.py`, `test-me1-body.py` | a P-c/V mátrix és a mutációs ellenőrzés, a gyűjtő lánc, a törzs szárazfutása |
| Tulajdonosi szkriptek | `owner/deliver-p-probe.sh`, `owner/open-p-probe-pr.sh`, `owner/test-owner-scripts.py` | a mérési ág helyi előkészítése (nem pushol), a PR megnyitása (**ez maga a mérés indítása**) |

## 3. A hipotézisek kezelése (a `pull_request` állításalakjai nem mértek)

- **A tervek H1–H8 hipotézisei** (`event_name`, `ref`/`workflow_ref`, `sha`, `sub`, `head_ref`/`base_ref`, a `workflow` név, a `path`/`head_branch` alakja, a token kérhetősége) **nem lettek mértként kódolva**. A `describe-pr` ezeket **CONFIRMED / REFUTED / RECORDED / NOT-OBSERVABLE** állapotba értékeli a megfigyelt bizonyíték alapján; egy főági állításokat hordozó „pull_request-nek látszó" futás a H1–H4-et **megcáfolja**, nem magyarázza el (tesztelt).
- **A `pr` profil gyűjtése a jogosultságot és a megfigyelést szétválasztja (review F2).** *Jogosultság:* a jóváhagyott PR-fej commitja a **PR API-objektumához** (`api/pr.json`, hiteles forrás) kötött: `number` = a kért PR-szám, `head.sha` = a jóváhagyott fej, `head.ref` = `p-probe`, `base.ref` = `main`, nem mergelt; ez fail-closed. *Futás ↔ PR kötés (review F3):* a futást a **futás saját API-metaadata** (`pull_requests`) köti a jóváhagyott PR-hoz: **pontosan egy** társított PR lehet, és az a jóváhagyott szám (`head.ref` = `p-probe`, `base.ref` = `main`); hiányzó, üres, nem lista, más számú vagy **többértelmű** (két PR-hoz tartozó) társítás **fail-closed**. A bejegyzésen belüli SHA-k csak rögzítettek (`observed.run_pull_requests`), nem előfeltevések. *Megfigyelés:* a futás **saját** `head_sha`, `path`, `head_branch` mezője **csak rögzített**, az egyenlőségét a PR fejével **nem feltételezzük** (H3, H7): a manifest `observed` blokkja rögzíti, hogy a futás `head_sha`-ja egyenlő-e a PR fejével, illetve a PR merge-commitjával. Az artifact és a lista a **futás saját `head_sha`-jához** kötött. Így a mérés **egyszerre fail-closed és képes megfigyelni az eltérést**, amelynek megfigyelése a célja (tesztelt: a futás `head_sha`-ja eltér a PR fejétől, a gyűjtés mégis megtörténik, az eltérés rögzítve).
- **Az olvasó politika módja kizárólag a főági profilt támogatja** (esemény `workflow_dispatch`, ref `refs/heads/main`, a védett workflow útvonala; más érték a politika betöltésekor hiba). **PR-profilú elfogadási politika nincs megvalósítva**: a PR-futás bizonyítékát ebben a csomagban kizárólag **negatív kontrollként** vetjük a főági politika elé; a saját elfogadási profilja csak mért értékekre épülhet, külön csomagban.
- **A `workflow_sha` és a `job_workflow_sha` elvárt értéke külön politika-mező**, nem a `sha`-ból levezetett (a #93 review megjegyzése): a főági profilban a mért alak az, hogy mindhárom a futás head-je, de **a politika nem feltételezi**; ha a mező hiányzik, a sor `NOTE` („nem kötött"), nem hallgatólagos egyenlőség.
- **A szintetikus PR-fixtúrák a hipotézis-alakot jelölik** (a tesztkimenet „hypothesised pull_request shapes" címkével), és **két alternatív alakra** is lefutnak (a `sub` más alakja, a `path` `@ref` utótaggal): a kontrollok az alakváltozatra is tartanak.

## 4. A döntési politika és a felderítés (V2)

**A döntési politika előre rögzített**, a bizonyítéktól és a publikálójától függetlenül (`--policy FILE`): tárgy (repó, azonosítók), a jóváhagyott workflow-azonosság (útvonal és ref), esemény, a jóváhagyott commit (`sha`), opcionálisan a `workflow_sha`, a közönség, és vagy a **pin** (`run_id`, `run_attempt`, `check_run_id`), vagy a „pontosan egy jogosult futás" szabály. A betöltés **fail-closed**: ismeretlen kulcs, hiányzó kulcs, rossz típus (köztük `bool` mint azonosító), nem 40 hexás SHA, nem főági profil mind hiba.

| Szabály | Megvalósítás |
|---|---|
| A K állítások várt értéke a **politikából** jön | `POLICY binds …` sorok; a tokenen belüli konzisztencia önmagában nem elég (tesztelt: belsőleg konzisztens token más commitra → `NOT-MET`) |
| A pin | `POLICY pin: run_id`, `run_attempt`, `check_run_id`; a `check_run_id` egyezik az API job-azonosítójával is |
| **Nincs „legfrissebb" szabály** | rögzítés nélkül több jelölt → `NOT-READ` („a verifier nem választ"), a listasorrendtől és az indítási időtől függetlenül |
| A checks API **felderít és keresztellenőriz** | a rögzített check-run jelölt, `completed`/`success`, github-actions app; a rögzítés **utáni** új futás **tájékoztató riasztás**, nem váltás |
| A felderítés elérhetetlensége | `NOT-READ`, **nincs visszaesés** a pinre vagy az olvasó bemenetére; **a P-c/V profilban nincs opcionális felderítés** (review F1): a politika `discovery: optional` értéke a **betöltéskor hiba**, így hiányzó lista mellett a politika módban `EVIDENCE BOUND` sosem adódhat |
| Csonkolt lista (`total_count` > az oldal) | `NOT-READ`: egy csonkolt első oldal nem adhat hamis „egyetlen jelöltet" (a saját átnézésem találta) |
| Régi csomag lista nélkül | a `me1-controls.py --attach-listing` a listát **másolathoz** csatolja (az eredeti érintetlen, a manifest jelöli); a valódi A-futás (45063800073) csomagja így használható, mert az **artifactja lejárt, újragyűjtés nem lehetséges** |

**Állításosztályok (a kódban):** **K** (kötelezően kötött: repó, azonosítók, workflow-azonosság, esemény, ref, `sub`, `sha`, `workflow_sha`, `job_workflow_sha`, futás, kísérlet, `check_run_id`, kibocsátó, közönség), **P** (platform által igazolt, a döntéshez nem használt: `actor`, `actor_id`, `ref_type`, `ref_protected`, `repository_visibility`, `runner_environment`, `run_number`, `jti`), **S** (szerző-választott: `workflow`, `head_ref`, `base_ref`). A P és S állítások **jelentve, nem ítélve** (az `actor`, `actor_id`, `jti` értéke nem kerül kiírásra); változtatásuk a verdiktet **nem** változtatja (tesztelt mind a 11-re), a K állítások változtatása `NOT-MET` (tesztelt mind a 16-ra).

## 5. A kontrollok (offline, a #92 5. szakasza szerinti három szinttel)

A kontrollok **bizonyíték-könyvtárakból** építik a PR-szerző lehetséges csomagjait, és a **főági** politikájú verifier elé teszik; valódi könyvtárakra is ráengedhetők, **és nem fogyasztanak futást**. Minden kontrollnak `NOT BOUND`-nak kell lennie **a megfelelő fajta indokkal**.

| Kontroll | Csomag | Szint |
|---|---|---|
| F-a | a PR-futás bizonyítéka, ahogy gyűjtöttük, a főági politika az A-ra rögzítve | 1 |
| F-d | ugyanez rögzítés nélkül (a „pontosan egy jelölt" szabály) | 1 |
| F-f | a támadó a **saját futását** rögzíti döntési futásnak | 1 |
| F-b | PR-token + **hamisított főági-nak kinéző** manifest, API-metaadat és lista | 1 |
| F-c | F-b + hamisított önbevallás (`context.json` a főági értékekkel) | 1 |
| F-e | PR-token egy bit módosított aláírással | 2 |
| R1 | a főági A bizonyítéka a PR merge-commitjára elvárva | 1 |
| S1 | az A tokenje a B csomagjában, a döntés a B-re rögzítve | 1 |
| S2 | az A tokenje a B csomagjában, a manifest **nem** frissítve | 3 |
| S3 | a B tokenje az A csomagjában, konzisztens manifest, a döntés az A-ra rögzítve | 1 |

**Szintek:** (1) `NOT BOUND` **és** a kötő sorok (`ref`, `event_name`, `sha`, `workflow_ref`, `sub`, a pin sorai) között legalább egy elutasítás; nem elég az audience, az idő vagy a manifest-szerkezet. (2) az aláírás-sor elutasított, **és** az állítások **nincsenek hitelesként kiértékelve**: az olvasó ezt az átnézés során kijavított módon végzi (érvénytelen aláírás után a régi sorok sem értékelik az állításokat, csak `NOTE`). (3) a manifest-digest sor elutasított.

**A kontroll-keretrendszer maga is tud bukni:** egy szándékosan hamisítható verifier (mindent elfogad) esetén **minden** kontroll `FAIL`; egy olyan verifier, amely a tier-1 kontrollokat csak audience/manifest okkal utasítja el, a tier-1 kontrollokat **nem** teljesítettnek jelzi (tesztelt). A **kiinduló elfogadás** is tesztelt: a valódi főági futások a saját politikájukkal és pinükkel `EVIDENCE BOUND` (a kontroll csak akkor értelmes, ha a verifier a valódit el tudja fogadni).

## 6. A P-c/V lefedettség (a #93 V1–V5 szerint)

| Tulajdonság | Tesztelt esetek (szintetikus, hacsak nem jelölt) |
|---|---|
| **V1 elnyomás** | hiányzó, üres token; hiányzó `context.json`, `api/run.json`, manifest; hiányzó/nem létező bizalmi kulcs; 14 érvénytelen politika; a gyűjtő megtagadja a nem sikeres futást (sikertelen, megszakított, kihagyott, időtúllépett, semleges, **visszatartott `action_required`**, folyamatban, sorban); a lejárt és a törölt artifact nem választható (**az R2 alakja, szintetikusan; a valódi lejárt artifact lekérdezése külön GO**) |
| **V2 kiválasztás** | pin A + lista [A,B] (B frissebb): az A elfogadva, a B elutasítva; pin B fordítva; **rögzítés után új futás**: a pin marad, riasztás; a lista sorrendjének megfordítása nem változtat; rögzítés nélkül két jelölt: nem választ; pontosan egy jelölt; nulla jelölt; **csonkolt lista**; a lista hiánya: nincs visszaesés; a rögzített check-run sikertelen, folyamatban, más app, más név; a pin `check_run_id`-ja ≠ az API job-azonosítója; **három izolált eset** (azonos `check_run_id`, csak a `run_id` tér el; csak a `run_attempt` tér el; azonos pin és token, csak az API job-azonosító tér el) |
| **V3 állításosztályok** | 16 K-állítás változtatása → elutasítva; 11 P/S-állítás változtatása → változatlan; más jóváhagyott commit a politikában; más `workflow_sha`; hiányzó `workflow_sha` a politikában → `NOTE`; hiányzó `job_workflow_ref` |
| **V4 időzítés** | a publikálás a lejárat előtt; 30 s-mal utána (60 s alatt); az időablakon kívül; két artifact az ablakban |
| **V5 csere** | S1–S3 és a másolt-token kontrollok |
| **V6** | **nincs** a csomagban (D-c5: a szerzői képességek mérése a B sorhoz kötött) |

## 7. Tesztek és mutációs ellenőrzés (helyi, 2026-11-23)

| Teszt | Eredmény |
|---|---|
| `check-me1-p-workflows.py --selftest` | **81 beültetett eltérés**, mind elutasítva, a tiltott-token lista nélkül is (köztük: `pull_request_target`, a szűrő kiszélesítése, a P2 `workflow_dispatch`-e, a P1 triggerének elvesztése, a P2 nevének és job-nevének eltérése, az `id-token` workflow-szinten, titok-hivatkozás, a token naplóba írása három módon, `gh` visszaküldés, a lejárat-kapu bármely elemének hiánya) |
| `test-me1-body.py` a P1-re és a P2-re | **23 + 23** ellenőrzés (hamis `curl`/`date`/`sleep`, szimulált óra) |
| `read-me1.py --selftest` | **120** ellenőrzés (a meglévő olvasó változatlanul zöld, az új logika csak `--policy` mellett fut) |
| `me1-controls.py --selftest` | **50** ellenőrzés (kiinduló elfogadás, a kontrollok P1-re és P2-re, két alternatív PR-alak, a keretrendszer bukása, `describe-pr`, `--attach-listing`, parancssor) |
| `test-pcv.py --selftest` | **106** ellenőrzés (a V1–V5 mátrix, a politika-betöltés, az F1 negatív tesztek, a parancssor) |
| `test-fetch-me1.py` | **64** ellenőrzés (a lánc, a lista a manifestben, a `pr` profil: a PR-fej jogosultsága, az **eltérő futás-SHA megfigyelése**, a **futás ↔ PR kötés** 9 negatív esete, az elutasítások, végpontok közti elfogadás) |
| `owner/test-owner-scripts.py` | **21** ellenőrzés (helyi bare repó és hamis `gh`: 7 elutasítási eset a szállításnál, 9 a megnyitásnál, és az egyszeri megnyitás) |
| **Összesen** | **488 ellenőrzés** (81 + 46 + 120 + 50 + 106 + 64 + 21) |
| `test-pcv.py --mutations` | **23 beültetett olvasó-hiba, mind elbukik** (a PR-gyűjtő mutációit a `test-fetch-me1.py` fogja) |

**A mutációs ellenőrzés tanulságai (a „kapu vakfolt" elve szerint, nem sikertörténetként):**
- Az **első futásban 4 mutáns túlélt.** A kivizsgálás: (a) **valódi hiány**: a `check_run_id` ↔ API job-azonosító keresztellenőrzésére nem volt izolált teszt (egy másik sor elfedte): **izolált teszt pótolva**; (b) **redundáns rétegek** (`workflow_ref`, `repository_id`, a pin `run_id`): az egyrétegű mutációt a régi olvasó független sora elfogta, ezért ezekre **mindkét réteget együtt** mutálom; (c) a kombinált pin-mutáció is túlélt, mert a `check_run_id`-pin elfedte: **két újabb izolált teszt** (csak a `run_id` tér el; csak a `run_attempt` tér el). Végül 11/11, majd a csonkolt lista felvételével **12/12**.
- **Review-kör 1 (d5406f3):** **F1** a `discovery: optional` mód megszűnt a P-c/V profilban (betöltéskor hiba; negatív tesztek, mutáció: 4 bukás); **F2** a PR-gyűjtő a PR-fej jogosultságát és a futás SHA-mezőinek megfigyelését szétválasztotta (a PR API-objektum a jogosultság forrása, az eltérés megfigyelhető; 4 új mutáció, mind elbukik). Az új mutációk 17-re emelték a listát.
- **Review-kör 2 (91a2ae7):** **F3 (HIGH)** a gyűjtő a jóváhagyott PR-t és a futást külön-külön ellenőrizte, a kettő kapcsolatát nem: most (a) a visszaolvasott PR-objektum `number` mezője egyezik a kért PR-számmal, (b) a futás `pull_requests` metaadata pontosan ezt az egy PR-t nevezi meg; minden más fail-closed, külön tesztekkel. 6 új mutáció (23 összesen), mind elbukik. **A mutációs ellenőrzés itt is mutatott egy túlélőt:** az üres `pull_requests` lista két rétegen akad el (üresség-ellenőrzés és `len != 1`), az egyrétegű mutáció egyenértékű volt, ezért a két réteget együtt vettem ki; az első kísérletem hibás volt (a tartalék-bejegyzés szöveges PR-számot kapott), ezt a második menet javította. A SHA-mezők értelmezése továbbra sem előfeltételezett.
- Az olvasó-javítás, amelyet a kontrollok átnézése hozott: érvénytelen aláírás után a régi sorok **még kiértékelték** az (nem hiteles) állításokat; most `NOTE`.
- A saját átnézésem hozta a csonkolt lista védelmét.
- A mutációk **nem fedik** a PR-profil elfogadási logikáját (az nincs megvalósítva), a `describe-pr` ítéleteit és a tulajdonosi szkripteket (azokat a mockolt tesztek).

## 8. A tulajdonosi folyamat (mind külön tulajdonosi GO, a megvalósítás merge-e után; most semmi nem fut)

| # | Lépés | K-5 | Külső hatás |
|---|---|---|---|
| 1 | a megvalósítás merge-e | 0 | nincs (a factory-ban) |
| 2 | `deliver-p-probe.sh` (helyi): a mérési ág a jóváhagyott commitból, blob- és fájlkészlet-ellenőrzéssel, **nem pushol** | 0 | nincs |
| 3 | az ág pusholása | 0 | ír az X repóba; **nem indít futást** |
| 4 | **`open-p-probe-pr.sh` (a mérés indítása)**: `ME1_I_HAVE_THE_GO=yes`, egyszeri, `.state` védett, a `main` és az ág ellenőrzött | 3 (lab-gate-pr, P1, P2), a visszatartással ≤ 5 | PR az X repón; **nem mergelendő** |
| 5 | visszatartott futás jóváhagyása a weben | a 2. kísérlet | a tulajdonos döntése |
| 6 | `fetch-me1.sh … pr PR_SZÁM` futásonként (a PR API-objektummal); `me1-controls.py --controls/--describe-pr` | 0 | csak olvasó |
| 7 | a második főági futás (D6) és az `--attach-listing` az A-ra | +1 (≤ 2) | futás |
| 8 | az R2 lejárt-artifact lekérdezés (D-c4) | 0 | csak olvasó |
| 9 | az opcionális újraindítás (R4, D-c3) | +1 (≤ 2) | futás |
| 10 | a PR lezárása (D4) | 0 | a tulajdonos |

**A K-5 előszámítás a #92/#93 szerint változatlan** (becslés, nem mért): alap 12/300, feltételes felső 15/300; R4-gyel 13/17; a `lab-gate-pr` visszatartásával +1.

## 9. Korlátok, amelyeket a csomag kimond

- **Szintetikus fixtúrák**: a valódi GitHub-viselkedés (a PR-futás állításai, a `filter=latest`, a visszatartás) a mérésig ismeretlen. A tesztek igazolják a **verifier** viselkedését a feltételezett alakokra, nem a platform viselkedését.
- **A P-c/F nincs benne** (D-c5, D-c6): a szerzői képességek a B sor nélkül nem mérhetők; a teljes M-E1 PASS ezért **nem** érhető el ezzel a csomaggal.
- **A döntéshozó szerepét a mérésben a tulajdonos tölti be** (a pin a független bemenet); éles CI-kapuban az orchestrator volna, ennek megvalósítása nem része a csomagnak.
- **A felderítés forrása ugyanaz a platform**, mint a kibocsátó: a bizalmi gyökér nem bővül.
- **Csak főági profilú politika**; PR-profilú elfogadási politika nincs. Fork-PR és az artifact-attestáció nincs lefedve.
- A `check_run_id` állítás jelenléte **egy workflow_dispatch futáson mért**, a `pull_request` esetre hipotézis.

## 10. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A P1/P2 fájlok pontosan a jóváhagyott szövegek, érvényes token nem publikálható bennük | mért (helyi, szintetikus) | 81 beültetett eltérés elutasítva; a törzs-szárazfutás 2×23 | `check-me1-p-workflows.py`, `test-me1-body.py` | a GitHub elfogadása és futtatása nem mért (a visszatartás lehetséges) |
| A verifier a döntési politikához köt, nincs „legfrissebb" szabály, a rögzítés utáni új futás csak riasztás | mért (helyi, szintetikus) | `test-pcv.py` 106; a mutációk 23/23 | `--selftest`, `--mutations` | a döntéshozói szerep a mérésben a tulajdonosé |
| A verifier fail-closed az elnyomás szintetikus eseteire | mért (helyi, szintetikus) | V1 esetek | `test-pcv.py` | a valódi lejárt artifact lekérdezése nem történt meg (D-c4, külön GO) |
| A kontrollok a megfelelő fajta indokkal utasítanak el, és a keretrendszer bukni tud | mért (helyi, szintetikus) | `me1-controls.py` 50; a hamisítható verifier detektálva | `--selftest` | a PR-alakok hipotézisek |
| A `describe-pr` a hipotéziseket megerősíti vagy megcáfolja; az SHA-viszonyokat a PR-objektumból és a futás-objektumból olvassa, nem feltételezi | mért (helyi, szintetikus) | CONFIRMED/REFUTED/RECORDED/NOT-OBSERVABLE esetek, a H3a/H3b | `--selftest` | a valódi PR-futás alakja ismeretlen |
| A PR-gyűjtő a PR-fej jogosultságát a PR API-objektumához köti, és a futás SHA-mezőinek eltérését megfigyeli, nem utasítja el | mért (mockolt) | 24 PR-profil eset a `test-fetch-me1.py`-ban (köztük a futás ↔ PR kötés 9 negatívja); 10 mutáció | `test-fetch-me1.py`, `--mutations` | a valódi API-objektumok mezőalakja nem mért |
| A tulajdonosi szkriptek fail-closed és a megnyitás egyszeri | mért (mockolt) | `owner/test-owner-scripts.py` 21 | helyi bare repó és hamis `gh` | a valódi `gh` és GitHub viselkedés nem mért |
| A P-a/P-b és a P-c/V részeredményt adhat | tervezett | a #92/#93 kritériumai | a mérés utáni jelentés | a teljes M-E1 PASS a P-c/F nélkül nem mondható ki |
| A P-c teljesül, a teljes M-E1 PASS | **nem állítom** | — | a P-c/F mérése (B sor) | — |
| A `pull_request`-futás állításai a H1–H8 szerintiek | **nem állítom, hipotézis** | — | a P1/P2 futás (külön GO) | a hipotézis megbukhat |
| Új Actions-futás, X-repó írás, PR-nyitás történt | nem (**végrehajtási naplóra alapozott állítás**) | a csomag készítésekor csak helyi fájlműveletek, helyi bare repó és hamis `gh` | a session végrehajtási naplója; a `git log` ezt nem bizonyítja | a napló az én oldalam |

## 11. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét, és nem állítja, hogy a P-c vagy a P teljesül; a P-c/F nem része a csomagnak.
- **Nem tekinti mértnek** a `pull_request`-futás állításait; azok hipotézisek.
- **Nem tartalmaz** futást, PR-nyitást, bizonyíték-letöltést, X-repóbeli írást, H1/H2-t, M-A…M-D tételt, valódi App-kulcsot vagy Relay-implementációt; ezek külön GO-t igényelnek.
- **Nem terjeszti ki** az eredményt fork-PR-ra, más szervezetre, a Relay-re vagy a production-re.
- **Nem módosítja** a #81–#93 tartalmát és a K-1–K-8 ajánlásokat.
