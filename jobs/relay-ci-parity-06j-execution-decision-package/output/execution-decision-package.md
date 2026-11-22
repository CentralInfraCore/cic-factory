# #212 — Végrehajtási döntési csomag a feltáró mérésekhez (CIC_Relay #212, 7. lépés)

Ez a dokumentum **döntési csomag**, nem végrehajtás. Nem hoz létre repót, App-ot, fiókot vagy titkot, nem módosít beállítást, nem mér. Az ajánlások **ajánlások**: a döntés a tulajdonosé. Az erőforrás-adatok **becslések, nem mértek**, és ennek megfelelően jelöltek. A csomag arra épül, hogy **kulcs, token vagy titok nem kerül hozzám**.

Forrás: a #81 mérési terv (`exploratory-measurement-plan.md`: 2.5, 3. szakasz, 5. fázistábla, 6. O-lista, 7. K-lista), a korábbi scratch mérések környezete (`app-measurement-report.md` 2. szakasz), a triázs 5. szakasza.

---

## 1. Hogyan használd ezt a csomagot

1. A 2. szakasz **egyetlen táblában** adja az ajánlott választ minden döntésre (K-1…K-8, O-1…O-6). Egy üzenetben jóváhagyható („elfogadom mind", vagy kivételekkel: „K-1 mást, a többi elfogadva").
2. A 3–4. szakasz tételenként indokol: alternatívák, előfeltételek, erőforrásigény, visszafordíthatóság.
3. Az 5. szakasz megmutatja, melyik döntés melyik mérési fázist **nyitja meg**; így nem kell mindent előre eldönteni, de a sorrend látható.
4. Ez a csomag **nem** a végrehajtási GO: a mérés indításához a döntések után külön GO kell.

---

## 2. Döntési összefoglaló

| ID | Kérdés | Ajánlott válasz | Nyitja / blokkolja |
|---|---|---|---|
| **K-1** | Hol fusson a feltáró mérés | **Új, dedikált, eldobható szervezet** (nem a `CentralInfraCore`), benne **két repó**: **X** (ellenséges PR-ok, **csak kanári**, valódi kulcs soha) és **Y** (a két App azonosság, a 3a–3b fázisban); a meglévő `cic-scratch-212-*` repók érintetlenek | 0. fázis |
| **K-2** | Nyilvános legyen-e a mérési repó | **Igen, nyilvános**; csak értéktelen kanári és scratch azonosító kerül bele | 0. fázis, fork-esetek |
| **K-3** | Az egy- és a kétidentitásos környezet előkészítése | **Külön előkészítés, nincs körkörös függés:** az X repó és a kanári (O-5a) a G0-hoz kell; a két App, az Y repó és a külső szerepek (O-2a, O-3, O-5b) a 2–3a kapukhoz, **a 0–1. fázissal párhuzamosan** készülhetnek | 2., 3a. fázis |
| **K-4** | A Relay fogad-e fork-PR-t | A tulajdonos **csak olvassa és közli** három beállítás értékét (nincs módosítás, 4. szakasz); a Relay-re a scratch eredmény nem általánosítható | Jel-2a prioritása |
| **K-5** | Erőforrás- és futásszám-korlát | **300 futás** felső korlát összesen, tételenként a terv szerinti szám; 1 órás tokenlejárati várakozások ütemezve; leállási küszöbök a 4. szakaszban | minden fázis |
| **K-6** | Mit változtathat a harness | A **4. szakasz O-4 táblájában** felsorolt, visszafordítható beállítások, **a tulajdonos által futtatott szkriptekkel** (nem én, hitelesítő adat nélkül) | 2., 3. fázis |
| **K-7** | Bizonyíték-típusok köre (M-E1) | **Nincs előzetes döntés**; az M-E1 az 1. fázis **első** tétele, az eredménye nyílt (a szervezet csomagjától függ) | M-E2, M-E3, M-E5 |
| **K-8** *(új)* | Ki hajtja végre a push-t és a PR-létrehozást a mérési repón; hogyan kezeljük a nyers kimenetet | **Tulajdonos futtatta push-szkriptek** (a jelenlegi minta); nyers kimenet a factory `raw/` alatt, titokellenőrzéssel | 0. fázis |
| **O-1** | Installáció-felfüggesztés és -visszaállítás | **Dedikált mérési App-okon**, ütemezett ablakokban (W1–W3); a `cic-integrity-scratch` nem érintett | 3. fázis |
| **O-2** | Két App; a kulcsok őrzése | **(a)** két új, minimális jogú App (kibocsátó, verifier), **kulcs nélkül** létrehozva és az Y repóra telepítve (3a); **(b)** a kulcsot a tulajdonos **csak a 3b fázisban** hozza létre, és **saját gépén őrzi**: a check-run-okat a tulajdonos futtatta szkript állítja elő; **GitHub-titokként alapértelmezésben nem kerül sehova**, és nem hozzám | 3a. (a), 3b. (b) |
| **O-3** | Mérési szerepek | **Öt külön szerep** (4.0 szakasz): tulajdonos/admin (nem mérési szereplő), írási jogú **nem admin** PR-szerző (gépi fiók A), külső fork-PR szerző (gépi fiók B), kibocsátó App, verifier App; **a tulajdonos saját, admin jogú identitása sosem PR-szerző** | 2. fázis |
| **O-4** | Beállítás-módosítások | Visszafordítható, **előre egyeztetett szkriptek, a tulajdonos futtatja**; előtte/utána állapot rögzítve | 2., 3. fázis |
| **O-5** | Kanári-értékek | **(a)** az X repón értéktelen `CANARY-212-…` érték a 0. fázisra; **(b)** az Y repón egy kanári-pár (M-D5) a 3a fázisra; **valódi kulcs a kanárival soha nincs egy repóban, és nem is fedik át egymást időben** | 0. (a), 3a. (b) |
| **O-6** | A mérés végállapota | A 3b után a **kulcsok visszavonása a tulajdonos által**, az App-ok felfüggesztése, **mindkét repó archiválása**, a gépi fiókok eltávolítása; **törlés HOLD** | a mérés után |

---

## 3. Olvasott tények (csak olvasó lekérdezés, ebben a sessionben)

| Tény | Érték | Státusz |
|---|---|---|
| `cic-scratch-212-public` | nyilvános, `allow_forking: true`, nem archivált | **olvasott** |
| `cic-scratch-212-workflows` | nyilvános, nem archivált | **olvasott** |
| `cic-scratch-212-private` | privát, nem archivált | **olvasott** |
| `CIC_Relay` | nyilvános, `allow_forking: true` | **olvasott** |
| A `CentralInfraCore` szervezet csomagja | `free` | **olvasott** |
| A szervezet kétlépcsős hitelesítést kötelezővé teszi-e | `false` (nem kötelező) | **olvasott** (lásd 6. szakasz, mellékmegfigyelés) |
| Hogy a fork-PR-ból induló workflow a Relay-en jóváhagyás nélkül lefut-e, mekkora a token jogosultsága | **nem olvasott** (admin beállítás) | K-4 |

A „nyilvános + `allow_forking`" a **szerkezeti** lehetőséget mutatja; hogy egy fork-PR-ra a workflow ténylegesen lefut-e, beállításfüggő (K-4, M-B1).

---

## 4. Tételenkénti ajánlások

### 4.0 Elkülönítési elvek és szerepek (az F1 és F3 javítása)

A csomag valamennyi ajánlása a következő elvekre épül. **Az elvek sérülése esetén a mérést le kell állítani.**

| # | Elv |
|---|---|
| **E-1** | **Kanári és valódi hitelesítő adat nem fedi át egymást.** A kiszivárgási és ellenséges-PR próbák idején a vizsgált környezetből **kizárólag értéktelen kanárik** érhetők el. |
| **E-2** | **Valódi hitelesítő adat csak a 3b fázisban létezik**, és **ellenséges PR akkor sem fut** abban a szervezetben: a 3b PR-jai jóindulatúak; az ellenséges viselkedést (azonos nevű check, jogosultság-túllépés, a másik azonosság módosítása) a tulajdonos által futtatott, az App saját tokenjével végzett API-hívások jelentik. |
| **E-3** | **A valódi App-kulcsok őrzése elkülönített és tulajdonosi:** a kulcsot a tulajdonos hozza létre, **a saját gépén őrzi**, a hívásokat a tulajdonos futtatta szkript végzi. **Alapértelmezésben nincs kulcs GitHub-titokként sem az X, sem az Y repón.** Kivétel csak külön tulajdonosi döntéssel, ha a B1–B4 és az M-D5 az azonos konfigurációra PASS (kanárival mérve), és csak az alapágra korlátozott, jóváhagyóhoz kötött környezetben. |
| **E-4** | **Időbeli sorrend:** a kanáris fázisok (0–3a) lezárulnak, mielőtt a valódi kulcs létrejön (3b). A kulcsot a 3b végén a tulajdonos visszavonja (O-6). |
| **E-5** | **Az A, B és E terület és az M-D6 valódi App-kulcs nélkül mérhető** (a platform alapértelmezett azonosságával és kanárival) — **következtetés a #81 elrendezéséből, nem mért**; ezért a valódi kulcs szükségessége a 3b fázisra szűkül. |
| **E-6** | **A kanáris mérés a tárolási konfigurációt méri, nem a kulcsot:** azt igazolja (a scratch-ben), hogy az adott tárolási hely és védelem a PR-ból elérhetetlen; a valódi kulcsra vonatkozó következtetés külön lépés. |

**Szerepek (az F3 javítása).** A mérésben öt, egymástól különálló szerep van; **egyetlen identitás sem tölthet be kettőt**, és a mérési eredményt a tulajdonos/admin identitás nem állíthatja elő.

| Szerep | Azonosság | Jogosultság | Mit tehet | Mit nem tehet |
|---|---|---|---|---|
| **S1 Tulajdonos / admin** | a tulajdonos admin jogú identitása | szervezeti tulajdonos | a beállítás-szkriptek (O-4) futtatása, felfüggesztés, kulcsőrzés, a PR-ok pusholása (K-8) | **nem PR-szerző, nem mérési check kibocsátója**: egy admin- vagy tulajdonosi jogú PR torzítaná a védelmi szabályok (pl. az adminokra is érvényesség) és a jogosultságok mérését |
| **S2 Írási jogú, nem admin PR-szerző** | **gépi fiók A** | külső együttműködő `write` szerepkörrel, **nem** tulajdonos, **nem** admin, **nem** maintain | belső (azonos repón lévő ágról induló) PR-ok | beállítás módosítása; védett ág megkerülése |
| **S3 Külső fork-PR szerző** | **gépi fiók B** | **nincs** jogosultság a repón | fork-PR-ok | bármilyen együttműködői jog |
| **S4 Kibocsátó App** | az Y repóra telepített App | minimális, check-írás | check-run kibocsátás (a tulajdonos futtatta szkripttel) | — |
| **S5 Verifier App** | külön App, külön hitelesítő adat | minimális, check-írás | verdikt-check kibocsátás | a másik App check-jének módosítása (M-D4 tárgya) |
| *(S6 Harness)* | én | **csak olvasó lekérdezés** és a szkriptek/PR-tartalmak előállítása | futásállapot-olvasás | **nincs írási hitelesítő adat**, nincs push (K-8) |

A védelmi szabályoknál az **„adminokra is érvényes" beállítás állapota** a 0. fázisban rögzítendő; az S1 szerep csak beállít, nem mér.

### K-1 — A mérési környezet

- **Ajánlás:** **új, dedikált, eldobható szervezet** (ingyenes csomag), benne **két repó**: **X** — az ellenséges PR-ok és a kiszivárgási próbák repója, **kizárólag értéktelen kanárival, valódi App-kulcs vagy token soha nincs benne**; **Y** — a két App azonosság mérései (3a–3b), amelyben **ellenséges PR csak akkor fut, ha az Y-ban nincs valódi kulcs** (4.0 szakasz). A nevek a tulajdonos döntései.
- **Alternatívák:** **(A)** új repók a meglévő `CentralInfraCore` szervezetben; **(B)** a meglévő `cic-scratch-212-public` újrahasznosítása.
- **Indoklás:** a mérés **ellenséges PR-okat**, installáció-felfüggesztést, szabály- és környezetvédelmi módosításokat és külső identitást tartalmaz. Az (A) esetben a szervezeti szintű beállítások (alapértelmezett workflow-jogosultság, szervezeti titkok és szabályok, a szervezet visszaélés-észlelése) közösek az éles repókkal; ennek hatása **következtetés, nem mért**, de a kockázat elkerülhető. A (B) esetben a mért alapállapot (nyitva hagyott mérési PR-ok, módosított `main`, a jelentés bizonyítékai) sérülne; a törlés HOLD, a módosítás ugyanúgy nem kívánatos. A **két repó** az, ami a kanáris és a valódi hitelesítő adatos fázisok átfedését szerkezetileg is kizárja (F1).
- **Előfeltétel:** a tulajdonos létrehozza a szervezetet és az X repót (az Y a 3a kapura); **a csomag ezt nem teszi**; az Actions engedélyezése.
- **Erőforrás:** tulajdonosi idő kb. 15–30 perc repónként (becslés); költség: nincs várható (ingyenes csomag).
- **Visszafordíthatóság:** a szervezet és a repók **archiválhatók**; a törlés HOLD.
- **Ha az (A)-t választod:** a 4.0 szakasz elkülönítési elvei változatlanul érvényesek, de a 6. szakasz R2 kockázata nyitott marad.

### K-2 — Láthatóság

- **Ajánlás:** **nyilvános** repó.
- **Indoklás:** a fork-PR esetek (M-B1) nyilvános repót és engedélyezett forkolást feltételeznek (az olvasott `allow_forking` a meglévő scratch-ben igaz); az Actions percek nyilvános repón díjtalanok (**dokumentált, ebben a sessionben nem ellenőrzött**). A tartalom nyilvánosságát az **értéktelen kanári** teszi elfogadhatóvá.
- **Korlát:** a repóba **nem kerülhet** személyes adat, éles azonosító, éles repó neve vagy bármilyen valós titok; a commit-szerzői adatok a mérési identitások.
- **Előfeltétel:** K-1.
- **Visszafordíthatóság:** a láthatóság privátra állítható, de a már közzétett tartalom indexelve lehet (**következtetés**); ezért a repóba csak ami nyilvánosságra szánt.

### K-3 — Az egy- és a kétidentitásos környezet előkészítése

- **Ajánlás:** **külön előkészítés, körkörös függés nélkül (az F2 javítása):** az **egyidentitásos** környezet (X repó, a platform alapértelmezett azonossága, kanári; **O-5a**) a G0-hoz szükséges; a **kétidentitásos** környezet (két App kulcs nélkül, Y repó, a gépi fiókok, a kanári-pár; **O-2a, O-3, O-5b**) a 2–3a kapukhoz kell, és **párhuzamosan** készülhet a 0–1. fázissal.
- **Indoklás:** a 0–1. fázis tételei (M-A1, M-A4, M-A5, M-B3, M-B5, M-E1–M-E5 és a beállítás nélküli részek) a platform alapértelmezett azonosságával mérhetők (E-5), tehát **nem várnak** a második App-ra vagy a gépi fiókokra; az O-5a nem függ az O-2-től.
- **Előfeltétel:** a tulajdonos megad egy tervezett időpontot az O-2a, O-3 és O-5b készre; ha nincs, a 2. és 3a–3b fázis **nem indul**, a 0–1. fázis eredménye önállóan jelentendő.
- **Erőforrás:** lásd O-2, O-3, O-5.

### K-4 — A Relay fork-PR viselkedése

- **Ajánlás:** a tulajdonos **csak olvassa**, és közli a következő három beállítás értékét a `CIC_Relay` Actions beállításai között: **(1)** a fork-PR-ból induló workflow-k jóváhagyási szabálya, **(2)** az alapértelmezett workflow-jogosultság (csak olvasás / olvasás és írás), **(3)** hogy a fork-PR-ból induló workflow kap-e írási jogú tokent. **Nincs módosítás.**
- **Indoklás:** a Relay nyilvános és forkolható (olvasott); az, hogy a fork-PR mennyire éri el a Relay CI-ját, a Jel-2a prioritását dönti el, és a scratch eredmény erre **nem általánosítható**; a három érték a kérdést mérés nélkül lezárja.
- **Előfeltétel:** a Relay repó admin hozzáférése (a tulajdonos).
- **Erőforrás:** kb. 5 perc.
- **Visszafordíthatóság:** csak olvasás, nincs változtatás.

### K-5 — Erőforrások és korlátok

- **Ajánlás:** **összesen legfeljebb 300 workflow-futás** a mérési szakaszban; tételenként a terv szerinti szám (lásd lent); **egyszerre egy mérési PR/futás** (sorosítva), hogy az ablakok ne keveredjenek; a kanári-kísérletek külön futásban.
- **Becslés (nem mért):** az alábbi futásszámok a #81 tételenkénti elrendezéséből és a 2.3 ismétlésszabályból adódnak.

| Terület | Tételek | Becsült futás | Várakozás |
|---|---|---|---|
| A TOCTOU | A1–A5 | 54 | injektálási pontok, +1/+5/+15 perces leolvasás |
| B csatornák | B1–B5 | 66 | — |
| C visszavonás | C1–C5 | 24 | a tokenlejárat (dokumentált ~1 óra, **nem mért**) |
| D két azonosság | D1–D6 | 38 | O-1 ablakok |
| E futási azonosság | E1–E5 | 36 | — |
| **Összesen** | 26 tétel | **kb. 218** (a kontrollfutásokkal és ismétlésekkel a 300-as korlátig) | |

- **Idő (becslés):** 0. fázis kb. fél nap; 1. fázis 1–2 nap; 2. fázis 1–2 nap; 3. fázis 1–2 nap, a tulajdonosi ablakoktól függően; a falióra-idő nagyobb része tulajdonosi várakozás.
- **Költség:** nem várható (nyilvános repó, ingyenes csomag: **dokumentált, nem ellenőrzött**).
- **API-korlát:** a harness körülbelül húszmásodpercenként egy lekérdezést tesz; ez a dokumentált óránkénti korlát (felhasználónként/telepítésenként több ezer kérés) töredéke; **dokumentált, nem mért**.
- **Leállási küszöb:** ha egy tétel 3 egymás utáni futása magyarázatlanul eltérő eredményt ad, vagy a futások összes száma eléri a 250-et megoldatlan INCONCLUSIVE-okkal, a mérést **szüneteltetni** és a tulajdonost értesíteni kell.
- **Visszafordíthatóság:** a korlát a végrehajtási GO-ban módosítható.

### K-6 — Mit változtathat a harness

- **Ajánlás:** csak az O-4 táblában felsorolt beállítások, **visszafordítható** módon, a változtatás előtti és utáni állapot rögzítésével, és **a tulajdonos által futtatott szkriptekkel**. Más beállítás **nem** módosítható.
- **Indoklás:** a K-6 és az O-4 ugyanaz a döntés két nézetből; a tilos lista nélkül a „harness" szerepe határtalan lenne.
- **Előfeltétel:** O-4 szkriptek előzetes egyeztetése.
- **Visszafordíthatóság:** a felsorolt beállítások mindegyike visszaállítható.

### K-7 — A bizonyíték-típusok köre

- **Ajánlás:** **nincs előzetes tulajdonosi döntés**, mert a kör a végrehajtás közben derül ki; az M-E1 az 1. fázis **első** tétele, hogy az eredménye a függő tételeket (M-E2 (2), M-E3, M-E5) korán eldöntse.
- **A leltár jelöltjei** (dokumentált, ebben a sessionben **nem ellenőrzött**): a futás metaadatai (futásazonosító, commit, workflow-útvonal, futási kísérlet) az API-ból; a futás által kérhető, a platform által aláírt azonosító-token és annak állításai; a platform által kínált, a futáshoz kötött igazolások (elérhetőségük a csomagtól függhet); a check-run kibocsátójának azonossága.
- **Indoklás:** a K-7 kérdése ténykérdés a platformról, nem tulajdonosi preferencia; a válasz mérés.
- **Előfeltétel:** K-1, K-2.
- **Következmény:** ha csak önbevallás érhető el, az M-E1 FAIL, és az R-M.11 PARTIAL/OPEN; ez érvényes eredmény.

### K-8 *(új)* — A mérési műveletek végrehajtója és a nyers kimenet

- **Ajánlás:** **a push-t és minden, a mérési repót módosító műveletet a tulajdonos futtatja** az eddigi push-szkript mintán; én a szkripteket és a mérési PR-ok tartalmát készítem el, olvasó lekérdezéseket futtatok (futásállapot, API-válasz), és **nem kapok írási hitelesítő adatot** a mérési repóra. A nyers kimenet a factory job `raw/` könyvtárába kerül, **titokellenőrzéssel** (csak értéktelen kanári lehet benne).
- **Indoklás:** a feltáró mérések tulajdonosi lépés-igénye így egységes marad; az ellenséges tartalmú PR-ok és a beállítás-módosítások nem kerülnek automatikus, hitelesítő adatot használó végrehajtásba.
- **Alternatíva:** a tulajdonos egy, **csak a mérési repóra** és rövid időre szóló, minimális jogú hozzáférést ad nekem. Ez **hitelesítő adat átadása**, ezért **nem ajánlott**; ha mégis ez kell, külön döntés.
- **Előfeltétel:** K-1.
- **Erőforrás:** minden push egy tulajdonosi parancs; a becsült futásszám alapján a push-ok száma a futásszámnál kisebb, mert egy PR több futást is ad (**becslés**).

### O-1 — Installáció-felfüggesztés és visszaállítás

- **Ajánlás:** a felfüggesztést a **dedikált mérési App-okon** (nem a `cic-integrity-scratch`-en) végzi a tulajdonos, három ablakban: **W1** (M-C1, M-C2, M-D3: felfüggesztés, majd a megfigyelés időpontjai), **W2** (M-C3: a visszavonás módjai egyenként: felfüggesztés, jogosultság-csökkentés, a repó eltávolítása az installációból), **W3** (M-C4: visszaállítás, V1 és V2).
- **Indoklás:** a felfüggesztés az App minden telepített repójára hat; dedikált App-pal a hatás a mérési repóra korlátozódik, és a mért alapállapot érintetlen.
- **Mit kapok vissza:** az időpontok (UTC) és a nem titkos kimenet (státusz, HTTP-kód, azonosítók); **kulcs nem**.
- **Előfeltétel:** O-2 (a) (dedikált App-ok) és (b) (a 3b-ben létrehozott kulcsok), K-1.
- **Erőforrás:** ablakonként kb. 15–30 perc tulajdonosi jelenlét (becslés).
- **Visszafordíthatóság:** igen (visszaállítás); a jogosultság-csökkentés visszaállításához az App-nak új engedélyezés kellhet (**dokumentált, nem mért**), ezt a W2-ben a tulajdonos kezeli.

### O-2 — A két App és a kulcsok őrzése

- **Ajánlás (a) — az App-ok létrehozása (3a kapu):** **két új, minimális jogú App** az új szervezetben: egy **kibocsátó** és egy **verifier** azonosság. Jogosultság: csak a check-ek írása, a tartalom és a metaadat olvasása; esemény/webhook nincs. Telepítés **csak az Y repóra**. A létrehozáskor **nem készül kulcs**.
- **Ajánlás (b) — a kulcsok őrzése (3b kapu, E-3):** a kulcsot a tulajdonos **a 3b elején** hozza létre, **a saját gépén őrzi**, és a check-run-okat **a tulajdonos futtatta szkript** állítja elő (telepítési token a kulcsból, check-run létrehozás vagy kísérlet). **GitHub-titokként alapértelmezésben nem kerül sehova**; nem küldi el nekem. Az M-C3 (d) kulcsforgatást is a tulajdonos végzi (a régi kulcs törlése, új létrehozása), és a nem titkos kimenetet közli.
- **Alternatíva (b):** a kulcs az Y repó környezeti titka **az alapágra korlátozott, jóváhagyóhoz kötött környezetben** — **csak** ha a B1–B4 és az M-D5 az azonos konfigurációra PASS (kanárival mérve), és a tulajdonos külön így dönt; ellenséges PR ekkor sem futhat az Y-ban (E-2).
- **Indoklás:** a kulcs és az ellenséges PR együttes jelenléte a hostile-PR repóban a kiszivárgás kockázata; a lokális őrzés a legerősebb elkülönítés, és a platform viselkedése az azonosságra (felfüggesztés, jogosultság) nem függ attól, hogy a check-run-t ki hozza létre (**következtetés, nem mért**; az M-C és M-D1–D4 tételei az azonosság kezelését mérik).
- **Mit kapok vissza:** az App azonosítók (nem titok); a szkriptek nem titkos kimenete.
- **Előfeltétel:** (a) K-1 (Y repó); (b) a 3a lezárása (E-4), O-1.
- **Erőforrás:** (a) kb. 30–45 perc App-onként; (b) kulcsgenerálás kb. 10 perc, a mérésenkénti szkriptfuttatások (becslés: a C és D1–D4 tételek becsült kb. 48 futása közül a check-run-ot igénylők) a tulajdonos ideje — ez a lokális őrzés ára.
- **Visszafordíthatóság:** az App-ok felfüggeszthetők, a kulcsok visszavonhatók (a 3b végén kötelezően, O-6); a törlés HOLD.

### O-3 — A mérési szerepek és a külső identitások (F3)

- **Ajánlás:** a 4.0 szakasz szerepei. **Két dedikált, a tulajdonos által birtokolt gépi fiók:** **A** — írási jogú, **nem admin** PR-szerző (külső együttműködő `write` szerepkörrel az X és az Y repón, **nem** tulajdonos, **nem** maintain, **nem** admin); **B** — külső fork-PR szerző (**semmilyen** jogosultság). **A tulajdonos saját, admin jogú identitása nem PR-szerző és nem mérési check kibocsátója** (S1).
- **Indoklás:** az M-B1 a belső és a fork-PR eseteket külön igényli; ha a PR-szerző szervezeti tulajdonos vagy admin, a védelmi szabályok adminokra vonatkozó viselkedése és a jogosultság-ellenőrzések torzulnának, és a mérés nem a támadó nézőpontját adná.
- **Megjegyzés:** a platform szabályzata a gépi fiókokra külön feltételeket szabhat; **ezt a tulajdonos ellenőrzi, én nem állítom.** Ha nem megoldható, a fork-esetek INCONCLUSIVE-ok (#81 M-B1), és az írási jogú szerepet egy másik, nem admin személy tölti be.
- **Előfeltétel:** K-1, K-2.
- **Erőforrás:** kb. 15–30 perc fiókonként (becslés).
- **Visszafordíthatóság:** a fiókok eltávolíthatók a szervezetből; a fork megszüntethető.

### O-4 — A beállítás-módosítások

- **Ajánlás:** a lenti módosítások **szkriptként**, előzetes egyeztetéssel, **a tulajdonos (S1) futtatja** a mérési repókon; minden módosítás előtt és után az állapot rögzítve. **A 0. fázisban az X repón a védett ág alapállapota (az 1. és 2. sor kezdőértéke: megkövetelt check, a `strict` kezdőállapota) is beállításmódosítás**: ezt a tulajdonos a repólétrehozáskor állítja be (K-1), a mérés közbeni váltások (a `strict` ki/be az M-A3 (2)-ben) szkriptesek. Ez pontosítja a #81 5. szakaszát, amely az M-A3 (1)–(3) sorokat tulajdonosi lépés nélkülinek sorolta, miközben a `strict` kapcsolása beállítás-módosítás.

| # | Módosítás | Mihez | Visszafordítható |
|---|---|---|---|
| 1 | A védett ág megkövetelt check-jeinek beállítása azonosság szerint (egy, majd két App) | M-A3, M-D1–D4 | igen |
| 2 | A frissesség-megkövetelés (`strict`) be/ki | M-A3 | igen |
| 3 | A jóváhagyók körének és a jóváhagyás-visszavonásnak módosítása | M-A3 (4)–(5) | igen |
| 4 | A megkövetelt check-készlet módosítása | M-A3 (6) | igen |
| 5 | Környezet-védelem és ág-szabály módosítása | M-B4 | igen |
| 6 | Repó-változók és környezeti beállítások módosítása a külső bemenet próbájához | M-A2 | igen |
| 7 | Olvasási jogosultságok megadása az állapotlekérdezés próbájához | M-C5 | igen |
| 8 | A workflow-jogosultság alapértelmezésének módosítása a mérési repón | M-B1, M-B3 | igen |
| 9 | A fork-PR workflow-jóváhagyási szabályának módosítása a mérési repón | M-B1 | igen |

- **Indoklás:** a lista zárt (K-6); a felsoroláson kívüli módosítás nem megengedett. A szkriptek a tulajdonos hitelesítő adatával futnak, én azokat nem látom.
- **Előfeltétel:** K-1, K-6; a szkriptek előzetes review-ja.
- **Erőforrás:** módosításonként néhány perc a tulajdonosnak (becslés); a szkriptek elkészítése az én feladatom.
- **Visszafordíthatóság:** minden tétel igen; az állapot-rögzítés az ellenőrzés alapja.

### O-5 — A kanári értékek (két lépésben, F1 + F2)

- **Ajánlás (a) — az X repón, a 0. fázisra:** a tulajdonos **véletlen, értéktelen** `CANARY-212-…` értékeket hoz létre, **azzal a tárolási hellyel és védelemmel**, amelyet a kibocsátó hitelesítő adata egy valódi telepítésben kapna (E-6): környezeti titok, alapágra korlátozott ág-szabállyal. **Ehhez nem kell App és nem kell az O-2** (nincs körkörös függés).
- **Ajánlás (b) — az Y repón, a 3a-ra:** egy **kanári-pár** (kibocsátó, verifier) az Y két, a későbbi valódi kulcsok helyét reprezentáló tárolási helyén (M-D5). **Valódi kulcs ekkor még nem létezik** (E-4).
- **Indoklás:** a kiszivárgási mérések (B terület, M-D5) csak úgy reprezentálják a tárolási konfigurációt, ha a kanári ugyanúgy védett; a kanári értéktelen, így nem titok az én számomra, az éles titkok ettől függetlenül nem kerülnek hozzám.
- **Előfeltétel:** (a) K-1 (X repó); (b) a 3a kapu, O-2 (a).
- **Erőforrás:** kb. 10–15 perc lépésenként (becslés).
- **Visszafordíthatóság:** a kanárik törölhetők.

### O-6 — A végállapot

- **Ajánlás:** a 3b végén azonnal a **kulcsok visszavonása a tulajdonos által** (E-4); a mérési App-ok **felfüggesztése**; a mérés végén **mindkét repó archiválása** (csak olvasható), a bizonyítékok megőrzése a `raw/` alatt; a gépi fiókok eltávolítása. **A szervezet és a repók törlése HOLD** marad.
- **Indoklás:** a bizonyítékok forrása megmarad az utólagos ellenőrzéshez; a kulcs-visszavonás a mérési App-ok kockázatát megszünteti, mielőtt bármilyen további ellenséges tevékenység indulna.
- **Előfeltétel:** a 3b lezárása.
- **Visszafordíthatóság:** az archiválás visszavonható; a kulcs-visszavonás nem (új kulcs kell).

---

## 5. Függőségi sorrend és teljes lefedés

### 5.1 Kapuk (a körkörös függés nélkül, F2)

| Kapu | Szükséges döntések és lépések | Megnyitja |
|---|---|---|
| **G0** | K-1 (szervezet, **X repó**), K-2, K-5, K-8, **O-5 (a)**, a védett ág alapállapota (O-4 1.–2. sor kezdőértéke) | 0. fázis (előkészítés, harness önellenőrzés), majd az 1. fázis |
| **G2** | **O-3** (A és B gépi fiók), O-4 szkriptek (3.–9. sor), K-6 | 2. fázis |
| **G3a** | K-1 (**Y repó**), **O-2 (a)** (két App, kulcs nélkül), **O-5 (b)**, O-4 (1., 5. sor az Y-ra), a **B1–B4 eredménye ismert** | 3a. fázis |
| **G3b** | O-1, **O-2 (b)** (a kulcs létrehozása és őrzése), a 3a. fázis lezárása (M-D5, M-B4 PASS vagy elfogadott kockázat) | 3b. fázis |
| **Lezárás** | O-6 | a mérés lezárása |

A **K-3** a kapuk előkészítésének ütemezése; a **K-4** és a **K-7** egyik kapunak sem előfeltétele (K-4 a Relay-következtetést, K-7 az M-E1 eredményét érinti). Az O-5 (a) **nem** függ az O-2-től; az O-2 (a) **nem** függ az O-5 (a)-tól: a körkörös függés megszűnt.

### 5.2 Teljes lefedés (a #81 5. szakaszával egyezően; az eltérések jelölve)

Minden mérési tétel pontosan egyszer vagy a #81 szerinti felosztásban szerepel; az M-A6 dokumentált korlát. Azt, ahol ez a csomag a #81-hez képest pontosít, a „Megjegyzés" oszlop jelöli.

| Tétel | Fázis | Kapu | Valódi App-kulcs kell? | Megjegyzés |
|---|---|---|---|---|
| M-A1 | 1 | G0 | nem | — |
| M-A2 (a platform-beállítás nélküli részek) | 1 | G0 | nem | a #81 szerint; a 4. szakasz O-4 1–2. sor kezdőértékét igényli |
| M-A2 (a többi) | 2 | G2 | nem | beállítás-módosítás (O-4 6. sor) |
| M-A3 (1)–(3) | 1 | G0 | nem | a #81 szerint **tulajdonosi lépés nélkülinek** sorolta; a (2) a `strict` kapcsolása miatt O-4 2. sort igényli — **pontosítás** (lásd O-4) |
| M-A3 (4)–(6) | 2 | G2 | nem | O-4 3.–4. sor |
| M-A4 | 1 | G0 | nem | — |
| M-A5 | 1 | G0 | nem | — |
| M-A6 | — | — | — | nem mérési tétel (dokumentált korlát) |
| M-B1 | 2 | G2 | nem (kanári) | O-3 A és B fiók, O-4 8–9. sor |
| M-B2 | 2 | G2 | nem (kanári) | — |
| M-B3 | 1 | G0 | nem (kanári) | — |
| M-B4 | 2 | G2 | nem (kanári) | O-4 5. sor |
| M-B5 | 1 | G0 | nem | — |
| M-C1 | 3 → **3b** | G3b | **igen** (lokális őrzés, E-3) | **pontosítás:** a #81 3. fázisa a 3b-re szűkül |
| M-C2 | 3 → **3b** | G3b | **igen** (lokális őrzés, E-3) | **pontosítás:** a #81 3. fázisa a 3b-re szűkül |
| M-C3 | 3 → **3b** | G3b | **igen** (lokális őrzés, E-3) | **pontosítás:** a #81 3. fázisa a 3b-re szűkül |
| M-C4 | 3 → **3b** | G3b | **igen** (lokális őrzés, E-3) | **pontosítás:** a #81 3. fázisa a 3b-re szűkül |
| M-C5 (állapotelemek, installációs állapot nélkül) | 2 | G2 | nem | O-4 7. sor |
| M-C5 (a kibocsátó jogosultsági/installációs állapotának eleme) | 3 → **3b** | G3b | **igen** (App-azonosítás kell az olvasáshoz) | **pontosítás** (E-5): ez az elem App-azonosítást igényel |
| M-D1 | 3 → **3b** | G3b | **igen** (lokális őrzés) | **pontosítás** |
| M-D2 | 3 → **3b** | G3b | **igen** (lokális őrzés) | **pontosítás** |
| M-D3 | 3 → **3b** | G3b | **igen** (lokális őrzés) | **pontosítás** |
| M-D4 | 3 → **3b** | G3b | **igen** (lokális őrzés) | **pontosítás** |
| M-D5 | 3 → **3a** | G3a | nem (kanári-pár) | **pontosítás**; függ: M-B1–M-B4 PASS |
| M-D6 | 3 → **3a** | G3a | nem (a verifier-definíció forrása hitelesítő adat nélkül mérhető: **következtetés, nem mért**) | **pontosítás** |
| M-E1 | 1 | G0 | nem | az első mérendő tétel (K-7) |
| M-E2 | 1 | G0 | nem | a (2) kérdés függ: M-E1 PASS (#81 5. szakasz) |
| M-E3 | 1 | G0 | nem | függ: M-E1 PASS (#81 5. szakasz) |
| M-E4 | 1 | G0 | nem | — |
| M-E5 | 1 | G0 | nem | függ: M-E1 PASS (#81 5. szakasz) |

A #81 3. fázisa itt **3a**-ra (kanáris, kulcs nélküli) és **3b**-re (valódi, lokálisan őrzött kulcs) oszlik: ez az F1 és az F2 következménye; a #81 többi fázisa változatlan.

---

## 6. Kockázatok és mellékmegfigyelés

| # | Kockázat | Enyhítés |
|---|---|---|
| R1 | Az ellenséges PR-ok tartalma nyilvános | csak értéktelen kanári és scratch azonosító kerül a repóba (K-2) |
| R2 | A szervezeti szintű beállítások és a visszaélés-észlelés közösek az éles repókkal (az (A) alternatívánál) | dedikált szervezet (K-1) |
| R3 | A mérési App kulcsa kerülne hozzám, vagy az ellenséges PR repójába | E-3: a kulcs a tulajdonos gépén marad, GitHub-titokként alapértelmezésben nincs; E-2: ellenséges PR és valódi kulcs nem él egy szervezetben egyszerre |
| R4 | A kanári a mérési kereten kívülre kerül | leállási feltétel (#81 2.5), a nyers kimenet titokellenőrzése (K-8) |
| R5 | A felfüggesztés más repót is érint | dedikált mérési App-ok (O-1) |
| R6 | A gépi fiók a platform szabályzatába ütközik | a tulajdonos ellenőrzi (O-3); a fork-esetek INCONCLUSIVE-ok lennének (#81 M-B1) |
| R7 | A becslés alulmarad | a 300-as korlát és a szüneteltetési küszöb (K-5) |
| R8 | A PR-szerző admin/tulajdonos jogú, ezért a védelmi szabályok és a jogosultságok mérése torzul | 4.0 szakasz: a szerepek elkülönítése (S1 nem PR-szerző; S2 nem admin) |
| R9 | A kanáris és a valódi hitelesítő adatos fázisok átfedik egymást | E-1, E-4: két repó, időbeli sorrend, a 3a lezárása a 3b előfeltétele |

**Mellékmegfigyelés (nem a csomag tárgya, a tulajdonos tájékoztatására):** a `CentralInfraCore` szervezetnél a kétlépcsős hitelesítés kötelezővé tétele **olvasott** módon ki van kapcsolva (`two_factor_requirement_enabled: false`). Ez az E1/E2 és az R-I.2 szempontjából a fiók-kompromittálás csatornáját érinti; **a csomag erről nem dönt, és nem módosítja**, a tulajdonos külön mérlegelheti.

---

## 7. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A csomag nem hoz létre, nem módosít és nem mér semmit | Ellenőrizhető | A diff csak `jobs/relay-ci-parity-06j-.../` alatti fájlokat érint | `git diff --stat origin/main..HEAD` | — |
| A scratch repó és a Relay nyilvános és forkolható; a szervezet csomagja `free`; a kétlépcsős követelmény ki van kapcsolva | **Olvasott** (csak olvasó lekérdezés) | 3. szakasz | `gh api repos/...` és `gh api orgs/...` újrafuttatása | Az állapot idővel változhat |
| A szervezeti szintű beállítások közösek az éles repókkal, ezért a K-1 (A) kockázatos | **Következtetés, nem mért** | A szervezeti beállítások természete | A végrehajtás előtt a szervezet beállításainak áttekintése (tulajdonos) | A hatás kisebb is lehet |
| A nyilvános repón az Actions percek díjtalanok | **Dokumentált, nem ellenőrzött** | A platform dokumentációja | A mérés elején egy kontrollfutás és a számlázási oldal olvasása (tulajdonos) | A szabályok változhatnak |
| A futások becsült száma kb. 218, a korlát 300 | **Becslés, nem mért** | A #81 tételenkénti elrendezése és a 2.3 szabály | A 0. fázis végén a tételenkénti terv szerinti újraszámolás | Az ismétlések és kontrollfutások növelhetik |
| A tokenlejárat dokumentált ideje kb. 1 óra | **Dokumentált, nem mért** | A platform dokumentációja | M-C3 mérése | A mért érték eltérhet |
| A második App, a gépi fiók, a kanári és a kulcsműveletek a tulajdonosi lépések | Rögzített elv | #81 6. szakasz | — | — |
| A K-7 (bizonyíték-típusok) a végrehajtás közben dől el, nem tulajdonosi preferencia | Rögzített, indokolt | 4. szakasz K-7 | M-E1 | A leltár jelöltjei dokumentáltak, nem mértek |
| A K-8 (a mérési műveletek végrehajtója) új nyitott kérdés, amely a #81-ben nem szerepelt | Rögzített | A #81 7. szakasza K-1–K-7-et sorol, K-8-at nem | A #81 olvasata | — |
| Az ajánlások nem helyettesítik a tulajdonosi döntést | Rögzített elv | 1. szakasz | — | — |
| A valódi App-kulcs csak a 3b fázisban létezik, a tulajdonos gépén marad, és ellenséges PR nem fut egy szervezetben vele | Rögzített elv (ajánlás) | 4.0 E-1–E-4; O-2 | A végrehajtási GO-ban a tulajdonos megerősíti; a 0. fázisban a tárolási hely dokumentálása | A lokális őrzés a tulajdonos munkáját növeli |
| Az A, B, E terület és az M-D6 valódi App-kulcs nélkül mérhető | **Következtetés a #81 elrendezéséből, nem mért** | #81 3. szakasz | A 0. fázisban a tételek elrendezésének átolvasása a kulcs-szükségletre | Ha egy tétel mégis App-azonosítást igényel, a 3b-be kerül |
| A #81 3. fázisa a 3a (kanáris) és a 3b (valódi) fázisra oszlik; az M-C5 egy eleme és az M-A3 (2) `strict` kapcsolása pontosítás | Rögzített, jelölt eltérés a #81-től | 5.2 tábla, O-4 | A #81 5. szakaszával és ezzel a táblával összevetés | A review a pontosítást elvetheti |
| Az O-5 (a) nem függ az O-2-től, az O-2 (a) nem függ az O-5 (a)-tól | Ellenőrizhető | 5.1 tábla | A kapuk függőségeinek átolvasása | — |
| A 26 mérési tétel az 5.2 táblában mind szerepel | Ellenőrizhető | 5.2 tábla | `grep` az M-A1…M-E5 azonosítókra | — |

---

## 8. Mit nem állít ez a dokumentum

- Nem hoz létre szervezetet, repót, App-ot, fiókot, titkot, és nem módosít beállítást; nem mér.
- Az ajánlások nem döntések; a döntés a tulajdonosé, és a végrehajtáshoz külön GO kell.
- Az erőforrás-adatok becslések, a platformviselkedésre vonatkozó állítások dokumentáltak vagy következtetések, **nem mértek**.
- Nem dönt az algoritmusról, a kódolásról, a Relay-implementációról, az éles beállításról, a #212 lezárásáról, a scratch törléséről (HOLD).
- A mellékmegfigyelés nem javaslat az éles szervezet módosítására.
