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
| **K-1** | Hol fusson a feltáró mérés | **Új, dedikált, eldobható szervezet** (nem a `CentralInfraCore`) és benne egy új repó; a meglévő `cic-scratch-212-*` repók érintetlenek | 0. fázis |
| **K-2** | Nyilvános legyen-e a mérési repó | **Igen, nyilvános**; csak értéktelen kanári és scratch azonosító kerül bele | 0. fázis, fork-esetek |
| **K-3** | Második App és külső identitás: mikor | A tulajdonos a 0–1. fázis alatt **párhuzamosan** előkészíti (O-2, O-3); a 2–3. fázis csak a ténylegesen kész elemekkel indul | 2., 3. fázis |
| **K-4** | A Relay fogad-e fork-PR-t | A tulajdonos **csak olvassa és közli** három beállítás értékét (nincs módosítás, 4. szakasz); a Relay-re a scratch eredmény nem általánosítható | Jel-2a prioritása |
| **K-5** | Erőforrás- és futásszám-korlát | **300 futás** felső korlát összesen, tételenként a terv szerinti szám; 1 órás tokenlejárati várakozások ütemezve; leállási küszöbök a 4. szakaszban | minden fázis |
| **K-6** | Mit változtathat a harness | A **4. szakasz O-4 táblájában** felsorolt, visszafordítható beállítások, **a tulajdonos által futtatott szkriptekkel** (nem én, hitelesítő adat nélkül) | 2., 3. fázis |
| **K-7** | Bizonyíték-típusok köre (M-E1) | **Nincs előzetes döntés**; az M-E1 az 1. fázis **első** tétele, az eredménye nyílt (a szervezet csomagjától függ) | M-E2, M-E3, M-E5 |
| **K-8** *(új)* | Ki hajtja végre a push-t és a PR-létrehozást a mérési repón; hogyan kezeljük a nyers kimenetet | **Tulajdonos futtatta push-szkriptek** (a jelenlegi minta); nyers kimenet a factory `raw/` alatt, titokellenőrzéssel | 0. fázis |
| **O-1** | Installáció-felfüggesztés és -visszaállítás | **Dedikált mérési App-okon**, ütemezett ablakokban (W1–W3); a `cic-integrity-scratch` nem érintett | 3. fázis |
| **O-2** | Második App, kulcsforgatás | **Két új, minimális jogú App** (kibocsátó, verifier) az új szervezetben; a kulcsot a tulajdonos hozza létre és helyezi el, **nem hozzám kerül** | 3. fázis |
| **O-3** | Külső (fork) identitás | **Dedikált gépi fiók** a tulajdonos tulajdonában, a `CentralInfraCore`-ban **nincs** tagsága | 2. fázis |
| **O-4** | Beállítás-módosítások | Visszafordítható, **előre egyeztetett szkriptek, a tulajdonos futtatja**; előtte/utána állapot rögzítve | 2., 3. fázis |
| **O-5** | Kanári-értékek | **Értéktelen, véletlen** `CANARY-212-…` értékek a tulajdonos által létrehozva, az éles tárolási hellyel azonos védelemmel | 0., 1. fázis |
| **O-6** | A mérés végállapota | **Archiválás és megőrzés**, a mérési App-ok kulcsainak visszavonása a tulajdonos által; **törlés HOLD** | a mérés után |

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

### K-1 — A mérési környezet

- **Ajánlás:** **új, dedikált, eldobható szervezet** (ingyenes csomag) és benne egy új repó a feltáró mérésekhez. A név a tulajdonos döntése (javaslat: a szervezetnek és a repónak is jelezze az eldobhatóságot).
- **Alternatívák:** **(A)** új repó a meglévő `CentralInfraCore` szervezetben; **(B)** a meglévő `cic-scratch-212-public` újrahasznosítása.
- **Indoklás:** a mérés **ellenséges PR-okat**, installáció-felfüggesztést, szabály- és környezetvédelmi módosításokat és külső identitást tartalmaz. Az (A) esetben a szervezeti szintű beállítások (alapértelmezett workflow-jogosultság, szervezeti titkok és szabályok, a szervezet visszaélés-észlelése) közösek az éles repókkal; ennek hatása **következtetés, nem mért**, de a kockázat elkerülhető. A (B) esetben a mért alapállapot (nyitva hagyott mérési PR-ok, módosított `main`, a jelentés bizonyítékai) sérülne; a törlés HOLD, a módosítás ugyanúgy nem kívánatos.
- **Előfeltétel:** a tulajdonos létrehozza a szervezetet és a repót (**a csomag ezt nem teszi**); az Actions engedélyezése a repón.
- **Erőforrás:** tulajdonosi idő kb. 15–30 perc (becslés); költség: nincs várható (ingyenes csomag).
- **Visszafordíthatóság:** a szervezet és a repó **archiválható**; a törlés HOLD.
- **Ha az (A)-t választod:** a mérés a 4. szakasz minden más korlátjával és a szervezeti beállítások érintetlenül hagyásával futhat, de a 6. szakasz R2 kockázata nyitott marad.

### K-2 — Láthatóság

- **Ajánlás:** **nyilvános** repó.
- **Indoklás:** a fork-PR esetek (M-B1) nyilvános repót és engedélyezett forkolást feltételeznek (az olvasott `allow_forking` a meglévő scratch-ben igaz); az Actions percek nyilvános repón díjtalanok (**dokumentált, ebben a sessionben nem ellenőrzött**). A tartalom nyilvánosságát az **értéktelen kanári** teszi elfogadhatóvá.
- **Korlát:** a repóba **nem kerülhet** személyes adat, éles azonosító, éles repó neve vagy bármilyen valós titok; a commit-szerzői adatok a mérési identitások.
- **Előfeltétel:** K-1.
- **Visszafordíthatóság:** a láthatóság privátra állítható, de a már közzétett tartalom indexelve lehet (**következtetés**); ezért a repóba csak ami nyilvánosságra szánt.

### K-3 — A második App és a külső identitás időzítése

- **Ajánlás:** az O-2 és az O-3 előkészítése **párhuzamos** a 0–1. fázissal; a 2. fázis akkor indul, ha az O-3 kész, a 3. fázis akkor, ha az O-2 és az O-1 ablakok rendelkezésre állnak.
- **Indoklás:** a 0–1. fázis tételei (M-A1, M-A4, M-A5, M-B3, M-B5, M-E1…E5 és a nem beállításigényes részek) tulajdonosi identitás nélkül mérhetők; így a tulajdonosi előkészítés nem blokkolja a kezdést.
- **Előfeltétel:** a tulajdonos megad egy tervezett időpontot az O-2 és az O-3 készre; ha nincs, a 2. és 3. fázis **nem indul**, a 0–1. fázis eredménye önállóan jelentendő.
- **Erőforrás:** lásd O-2, O-3.

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
- **Előfeltétel:** O-2 (dedikált App-ok), K-1.
- **Erőforrás:** ablakonként kb. 15–30 perc tulajdonosi jelenlét (becslés).
- **Visszafordíthatóság:** igen (visszaállítás); a jogosultság-csökkentés visszaállításához az App-nak új engedélyezés kellhet (**dokumentált, nem mért**), ezt a W2-ben a tulajdonos kezeli.

### O-2 — A második App és a kulcsforgatás

- **Ajánlás:** **két új, minimális jogú App** az új szervezetben: egy **kibocsátó** és egy **verifier** azonosság. Jogosultság: csak a check-ek írása, a tartalom és a metaadat olvasása; esemény/webhook nincs. Telepítés **csak a mérési repóra**. A kulcsot a tulajdonos hozza létre, és a mérési repó környezeti titkaként helyezi el; **nem küldi el nekem**. Az M-C3 (d) kulcsforgatást is a tulajdonos végzi (a régi kulcs törlése és új létrehozása), és közli a kimenetet.
- **Indoklás:** az M-D1–D6 két független azonosságot igényel; a kulcsforgatás csak a mérési App-on történik; a `cic-integrity-scratch` kulcsának visszavonása/törlése külön, a mérésektől független tulajdonosi tétel marad (nem sürgős).
- **Mit kapok vissza:** az App azonosítók (nem titok).
- **Előfeltétel:** K-1; az App-ok létrehozásához a szervezet tulajdonosi jogosultsága.
- **Erőforrás:** kb. 30–45 perc tulajdonosi idő App-onként (becslés).
- **Visszafordíthatóság:** az App-ok felfüggeszthetők, a kulcsok visszavonhatók; a törlés HOLD.

### O-3 — A külső identitás

- **Ajánlás:** egy **dedikált, a tulajdonos által birtokolt gépi fiók**, amely a `CentralInfraCore` szervezetnek **nem tagja**, és a mérési szervezetben **nincs írási joga** a mérési repóhoz (a fork-ból nyit PR-t). A második, írási jogú „PR-szerző" szerep (azonos repó ága) a tulajdonos saját, már meglévő azonossága lehet a mérési szervezeten belül.
- **Indoklás:** az M-B1 a fork-PR és a belső PR eseteit külön igényli; a gépi fiók elkülöníti a hitelesítő adatokat az éles azonosságoktól.
- **Megjegyzés:** a platform szabályzata a gépi fiókokra külön feltételeket szabhat; **ezt a tulajdonos ellenőrzi, én nem állítom.**
- **Előfeltétel:** K-1, K-2.
- **Erőforrás:** kb. 15 perc (becslés).
- **Visszafordíthatóság:** a fiók eltávolítható a mérési szervezetből; a fork megszüntethető.

### O-4 — A beállítás-módosítások

- **Ajánlás:** a lenti módosítások **szkriptként**, előzetes egyeztetéssel, **a tulajdonos futtatja** a mérési repón; minden módosítás előtt és után az állapot rögzítve.

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

### O-5 — A kanári értékek

- **Ajánlás:** a tulajdonos **véletlen, értéktelen** értékeket hoz létre `CANARY-212-` előtaggal, **az éles hitelesítő adatok tárolási helyével azonos védelemmel** (ugyanaz a hatókör és ugyanaz a környezetvédelem a mérési repón), külön a kibocsátóhoz és a verifierhez (M-D5). A kanári-értékek **nem titkok az én számomra** (értéktelenek); az éles titkok ettől függetlenül nem kerülnek hozzám.
- **Indoklás:** a kiszivárgási mérések (B terület) csak úgy reprezentálják a valódi csatornákat, ha a kanári ugyanúgy védett, mint a valódi hitelesítő adat; a körkörösséget a 0. fázis tárolási hely-dokumentációja ellenőrzi (#81 claim-evidence tábla).
- **Előfeltétel:** K-1, O-2 (a tárolási hely kialakítása).
- **Erőforrás:** kb. 10–15 perc (becslés).
- **Visszafordíthatóság:** a kanárik törölhetők.

### O-6 — A végállapot

- **Ajánlás:** a mérés végén a mérési repó **archiválása** (csak olvasható), a bizonyítékok megőrzése a `raw/` alatt, a mérési App-ok **felfüggesztése** és kulcsaik **visszavonása** a tulajdonos által, a gépi fiók eltávolítása. **A szervezet és a repó törlése HOLD** marad.
- **Indoklás:** a bizonyítékok forrása megmarad az utólagos ellenőrzéshez; a kulcsok visszavonása a mérési App-ok kockázatát megszünteti.
- **Előfeltétel:** a mérés lezárása.
- **Visszafordíthatóság:** az archiválás visszavonható; a kulcs-visszavonás nem (új kulcs kell).

---

## 5. Függőségi sorrend: melyik döntés mit nyit meg

| Kapu | Szükséges döntések | Megnyitja |
|---|---|---|
| **G0** | K-1, K-2, K-8, O-5 (a kanári-hely O-2-től is függ), K-5 | 0. fázis (előkészítés, harness önellenőrzés), majd az 1. fázis |
| **G1** | K-7 (nincs döntés), a 0. fázis lezárása | 1. fázis: M-E1 először, majd M-A1, M-A4, M-A5, M-B3, M-B5, M-E2–E5 |
| **G2** | O-3, O-4 szkriptek, K-3 (O-3), K-6, K-4 (nem blokkoló) | 2. fázis: M-B1, M-B2, M-B4, M-A3 (4)–(6), M-A2, M-C5 |
| **G3** | O-1, O-2, K-3 (O-2) | 3. fázis: M-C1–M-C4, M-D1–M-D6 |
| **Lezárás** | O-6 | a mérés lezárása |

A K-4 egyik kapunak sem előfeltétele; csak a Relay-re vonatkozó következtetést teszi lehetővé.

---

## 6. Kockázatok és mellékmegfigyelés

| # | Kockázat | Enyhítés |
|---|---|---|
| R1 | Az ellenséges PR-ok tartalma nyilvános | csak értéktelen kanári és scratch azonosító kerül a repóba (K-2) |
| R2 | A szervezeti szintű beállítások és a visszaélés-észlelés közösek az éles repókkal (az (A) alternatívánál) | dedikált szervezet (K-1) |
| R3 | A mérési App kulcsa kerülne hozzám | O-2: a kulcsot a tulajdonos kezeli, nem küldi el (K-8) |
| R4 | A kanári a mérési kereten kívülre kerül | leállási feltétel (#81 2.5), a nyers kimenet titokellenőrzése (K-8) |
| R5 | A felfüggesztés más repót is érint | dedikált mérési App-ok (O-1) |
| R6 | A gépi fiók a platform szabályzatába ütközik | a tulajdonos ellenőrzi (O-3); a fork-esetek INCONCLUSIVE-ok lennének (#81 M-B1) |
| R7 | A becslés alulmarad | a 300-as korlát és a szüneteltetési küszöb (K-5) |

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

---

## 8. Mit nem állít ez a dokumentum

- Nem hoz létre szervezetet, repót, App-ot, fiókot, titkot, és nem módosít beállítást; nem mér.
- Az ajánlások nem döntések; a döntés a tulajdonosé, és a végrehajtáshoz külön GO kell.
- Az erőforrás-adatok becslések, a platformviselkedésre vonatkozó állítások dokumentáltak vagy következtetések, **nem mértek**.
- Nem dönt az algoritmusról, a kódolásról, a Relay-implementációról, az éles beállításról, a #212 lezárásáról, a scratch törléséről (HOLD).
- A mellékmegfigyelés nem javaslat az éles szervezet módosítására.
