# #212 — A feltáró mérések terve (CIC_Relay #212, 6. lépés)

Ez a dokumentum **mérési terv**, nem mérés. Nem hajt végre mérést, kulcsműveletet, implementációt, és nem módosít Relay- vagy repository-beállítást. A benne szereplő „várt" eredmények **hipotézisek**, nem mért tények; ahol a platform viselkedéséről szól, ott **következtetés, nem mért**, amíg a végrehajtás (külön GO) le nem futott. A végrehajtás eredménye is csak **scratch** környezetben mért, **nem production-igazolt**.

Forrás: a #76 követelmények (R-I, R-V, R-C, R-X), a #78 policy-határ (R-P), a #79 digest-szabályok (R-D), a #80 horgony és mechanizmus (R-A, R-M), a triázs (open-case-triage 3.1–3.3, G1–G3, 5. szakasz 4. lépés), és a korábbi scratch mérések (app-measurement-report 2–3. szakasz).

---

## 1. Hatókör és hogyan illeszkedik a sorrendbe

- A triázs 4. lépése: **a jelenlegi viselkedés** feltáró mérése. A mérés a **platformot** vizsgálja (mit kényszerít ki natívan, mi látható kívülről, mi nem). A még nem létező ellenőrző mechanizmust (R-M.5, R-M.6, R-M.10, a `C_exp` nyilvántartás R-A.4–R-A.8) **nem** méri; azok igazolása a 6. lépés (igazoló mérések), a megoldási terv (5. lépés) után.
- A mérési eredmények bemenetei: az állapotkötés megoldási terve (5. lépés), az N4 érvénytelenítési mechanizmus, az N1.4 és N2.6 nyitott kérdések, és az N8-jelölt (amelynek fennállása **nem** függ ezek kimenetétől).
- Öt terület, jelölésük: **A** TOCTOU, **B** E1/E2 csatornák, **C** visszavonás és felfüggesztés, **D** két független kibocsátói azonosság, **E** tényleges futási azonosság.

---

## 2. Közös szabályok (minden mérési tételre)

### 2.1 Ítéletek

| Ítélet | Jelentése |
|---|---|
| **PASS** | A tétel *hipotézise* (a védő tulajdonság) a megadott esetekben teljesült, **és** a pozitív kontroll bukott/észlelt a megadott módon (a mérés tud bukni). |
| **FAIL** | A hipotézis legalább egy esetben **nem** teljesült: a mérés rést talált. A FAIL **érvényes, értékes eredmény**, nem a mérés hibája. Egyetlen, újrajátszható megfigyelés elég hozzá. |
| **INCONCLUSIVE** | A mérés nem döntött: a pozitív kontroll nem működött; a környezet menet közben megváltozott; az eredmény nem reprodukálható; a platform viselkedése kívülről nem figyelhető meg; vagy a tétel előfeltétele (tulajdonosi lépés) nem teljesült. |

**Szabályok:** az INCONCLUSIVE-ot nem szabad PASS-ként vagy FAIL-ként jelenteni. A PASS csak úgy állítható, ha a pozitív kontroll működött. A hiányzó kontroll önmagában INCONCLUSIVE. Az eredmény mindig a mért esetekre vonatkozik, nem általánosítható (R-P.13 szellemében: a kötetlen marad PARTIAL/OPEN).

### 2.2 Pozitív kontroll és negatív esetek

- **Pozitív kontroll (PK):** minden tételnél előre megadott, ismert tulajdonságú eset, amelyen a mérési elrendezésnek a *várt* eredményt kell adnia: egy **ültetett hiba** (a mérés észleli), és egy **ismert jó** eset (a mérés nem jelez hamis riasztást). Ha a PK nem teljesül, a tétel INCONCLUSIVE (a „kapu vakfolt" elve: egy ellenőrzés, amelyről nem mértük, hogy tud-e bukni, nem bizonyít).
- **Negatív esetek osztályai** (minden tételnél megnevezve, melyek vonatkoznak rá):
  - **R — visszajátszás:** egy korábban hiteles (zöld, érvényes) bizonyíték vagy művelet újbóli felhasználása megváltozott állapotban.
  - **S — bizonyítékhelyettesítés:** egy másik forrásból, azonosságtól, futásból, committól vagy típusból származó bizonyíték elfogadtatása a kért helyett.
  - **X — túlnyújtás:** a hitelesítő adat vagy a jogosultság a szándékolt hatókörön túli használata.
  - **D — leromlott állapot:** hiányzó, elérhetetlen, részleges vagy kétértelmű forrás (fail-closed ellenőrzése).
  - **P — ültetett hiba:** szándékosan beültetett eltérés, amelyet a tételnek észlelnie kell.

### 2.3 Ismételhetőség és időzítés

- **Determinisztikus tétel:** legalább két, egymástól független futás azonos ítélettel. Eltérés esetén INCONCLUSIVE.
- **Időzítésfüggő tétel:** az időzítést **ellenőrzött injektálási ponttal** kell rögzíteni (a futó job egy meghatározott ponton vár, a tulajdonos vagy a harness megváltoztatja az állapotot, majd a job folytat), nem véletlen időzítéssel. PASS csak úgy állítható, hogy a platform minden meghatározott injektálási ponton determinisztikusan viselkedett; a „N futásban nem észleltük" **önmagában INCONCLUSIVE**, mert véges mintával a hiány nem bizonyítható.
- **Belső, kívülről nem injektálható ablak** (pl. a platform belső értékelése és a ref frissítése közti rés): a terv ezt **nem mérhetőnek** jelöli (A6), a várt ítélet INCONCLUSIVE, a maradék kockázat dokumentált.

### 2.4 Bizonyíték és rögzítés

Minden mérési futásnál rögzítendő: UTC időpont, futásazonosító (run id), `headSha` és az érintett ref-ek SHA-ja a mérés előtt és után, a nyers kimenet (a `raw/` alatt), a tétel azonosítója és ítélete. A jelentés minden eredményét **„scratch, mért"** vagy **„scratch, nem mért"** jelöli. A következtetést „következtetés, nem mért" jelöli. Az eredmény **nem production-igazolt**.

### 2.5 Környezet és biztonsági korlátok

- **Csak scratch.** A korábbi mérések `cic-scratch-212-public` repóját és a `cic-integrity-scratch` App-ot (ID 5852604) az app-measurement-report 2. szakasza írja le. A repó állapota szándékosan megmaradt (mérési PR-ok, módosított `main`); a **törlése HOLD**. A javaslat: a feltáró mérések **új, dedikált scratch repón** fussanak, hogy a már mért alapállapot ne sérüljön (K-1 nyitott kérdés, tulajdonosi döntés).
- **Hitelesítő adat helyett kanári.** A kiszivárgási próbák (B terület) **kizárólag kanári értékkel** (a mérés számára létrehozott, értéktelen, azonosítható titokkal) futnak. **Éles kulcs, az App privát kulcsa és bármely éles token nem kerül a mérésbe és nem kerül hozzám.** Ahol a platform viselkedése a valódi kulcs használatán múlik (JWT-alapú műveletek), a műveletet a tulajdonos végzi, és csak a nem titkos kimenetet (státusz, HTTP-kód, azonosítók) adja át.
- **Leállási feltétel:** ha egy lépés élő repót, a Relay-t, éles beállítást vagy valódi kulcsot érintene; ha a harness váratlan jogosultságot kap; vagy ha egy kanári a mérési kereten kívül jelenne meg, a mérést le kell állítani, és a tulajdonost értesíteni.
- A mérés nem fogyaszt korlátlan erőforrást: a futások száma tételenként a tervben megadott; az Actions-percek és a rate limit a végrehajtási GO-ban fogadandó el (K-5).

---

## 3. A mérési tételek

Minden tétel mezői: **H** hipotézis (a védő tulajdonság, amelyet PASS esetén állítunk) · **Köv.** visszavezetés a normatív követelményekre · **Elrendezés** · **PK** pozitív kontroll · **Negatív** esetosztályok (2.2) és konkrétumok · **Ítélet** (PASS / FAIL / INCONCLUSIVE) · **Tul.** tulajdonosi lépés (6. szakasz) · **Bemenete** (mit ad tovább).

### 3.A TOCTOU: az ellenőrzés és a felhasználás közötti állapotváltozás

**M-A1 — Az alapág elmozdulása a job futása közben**
- **H:** a döntés abból az S/B állapotból születik, amelyet a kibocsátó közöl; ha az alapág a job indulása és lefutása között elmozdul, az eltérés észlelhető, vagy a döntés nem használható.
- **Köv.:** R-V.1, R-V.3 (használt = rögzített), R-V.7, R-V.11; R-P.12.
- **Elrendezés:** a scratch workflow a közölt `BASE_SHA`-t az eseményből, a checker és a policy-t a job idején az alapág csúcsáról tölti (a korábbi jelentés 3.6 megfigyelése, olvasott). Ellenőrzött injektálási pont: a job a checkout előtt vár; az alapágon új commit jön, amely a policy-t módosítja; a job folytat. Rögzítendő: melyik SHA-ból töltött a checker és a policy; mit közöl a kimenet; a döntés mely állapotra vonatkozik.
- **PK:** (ültetett) a módosított policy más döntést ad, mint az eredeti, így az eltérés a kimenetből kimutatható; (ismert jó) mozgatás nélküli futás: a checkout SHA = `BASE_SHA`.
- **Negatív:** P (ültetett policy-módosítás), R (az így kapott zöld újrafelhasználása a régi állapotra).
- **Ítélet:** PASS = a kimenet vagy a platform mindkét esetben azonosítja, hogy a checker/policy SHA ≠ közölt `BASE_SHA`, vagy a döntés ilyenkor nem jön létre. FAIL = a döntés zöld, és a kimenet nem árulja el az eltérést. INCONCLUSIVE = az injektálás nem a megadott ponton történt, vagy a PK nem teljesült.
- **Tul.:** nincs (a scratch alapág módosítását a harness végzi, a jogosultságot a tulajdonos előzetesen adja: O-4).
- **Bemenete:** állapotkötés megoldási terve (J1–J3), N4.

**M-A2 — Külső bemenet változása változatlan HEAD és BASE mellett**
- **H:** egy döntést befolyásoló külső bemenet (nem fájl a fán) megváltozása érvényteleníti a döntést, vagy a változás kimutatható a használatkor.
- **Köv.:** R-P.14, R-P.15, R-P.12, R-P.16, R-V.5, R-V.7; R-V.11.
- **Elrendezés:** a döntést befolyásoló, nem fán lévő bemenetek jegyzéke a scratch workflow-ból (pl. a repó változói, a környezet konfigurációja, az approver-készlet, a platform-oldali szabályok). Mindegyiket külön változtatjuk úgy, hogy a HEAD és a BASE változatlan marad; a zöld check állapotát és a merge-lehetőséget figyeljük.
- **PK:** egy bemenet, amelynek a megváltoztatása a döntést **bizonyítottan** megváltoztatja (ültetett); egy bemenet, amelynek változása nem hat a döntésre (ismert jó).
- **Negatív:** P, R (a régi zöld a megváltozott bemenet után), D (a bemenet nem olvasható).
- **Ítélet:** PASS = minden DBT-bemenet változása után a check újraértékelődik, vagy a régi zöld nem elég a merge-hez. FAIL = legalább egy DBT-bemenet változott, és a régi zöld továbbra is elég. INCONCLUSIVE = a bemenetek jegyzéke nem volt teljes (a jegyzék teljessége maga is bizonyítandó: a végrehajtáskor a workflow soronkénti átvizsgálása).
- **Tul.:** egyes platform-szintű beállítások módosítása (O-4).
- **Bemenete:** R-P.14 igazolása, a policy-határ (N3) „külső bemenet" kategóriája.

**M-A3 — Az újraértékelés mátrixa a check és a merge között**
- **H:** minden meghatározott állapotváltozás, amely a döntést érvényteleníti, a merge-kapunál megállítja a műveletet.
- **Köv.:** R-V.4, R-V.7, R-V.8, R-V.11.
- **Elrendezés:** zöld check után egyenként, külön PR-on: (1) HEAD-változás, (2) BASE-változás, `strict` be- és kikapcsolva, (3) a policy fájl változása az alapágon, (4) az approver-készlet változása, (5) a jóváhagyás visszavonása, (6) a required-check készlet változása. Mindegyiknél a merge-állapot (`mergeStateStatus`, merge-kísérlet eredménye) rögzítve, közvetlenül a változás után és ellenőrzött késleltetésekkel.
- **PK:** (1)–(2) `strict` mellett a korábbi mérés szerint elutasít (PR31, PR34; mért): ezek a mátrix ismert jó oszlopa. Ültetett: egy hamis „változatlan" állapot (nincs változás), ahol a merge-nek át kell mennie.
- **Negatív:** R (a régi zöld változás után), D (az állapot nem lekérdezhető).
- **Ítélet:** minden sorra külön PASS (megállítja) / FAIL (átengedi) / INCONCLUSIVE; a tétel eredménye a sorok vektora, nem egyetlen ítélet.
- **Tul.:** a (4)–(6) sorokhoz repó-beállítás módosítás (O-4).
- **Bemenete:** melyik elemet fedi a platform natívan (S, B) és melyiket nem (P, C): az R-M.7 osztályozás alapja.

**M-A4 — A régi zöld visszajátszása**
- **H:** egy korábbi, az akkori állapotra hiteles check újrafuttatása vagy újrafelhasználása a megváltozott állapotban nem ad érvényes döntést a régi `T_d`-vel.
- **Köv.:** R-V.7, R-V.8, R-V.9, R-V.11; R-M.6 (a verdikt újrafelhasználhatatlansága, a mechanizmus nélkül csak a platform viselkedését mérjük).
- **Elrendezés:** (a) a régi workflow-futás **újrafuttatása** a BASE/policy megváltozása után: melyik állapotot használja (a régi esemény-adatot vagy az aktuálisat), mit közöl; (b) egy ágon ugyanarra a commitra új PR; (c) a régi check-run és az újrafuttatás viszonya (a legutóbbi számít, A4 korábbi mérés).
- **PK:** ültetett: a policy úgy módosul, hogy a régi zöld már hibás; a helyes viselkedés az, hogy az újrafuttatás **az aktuális** állapotra ad döntést, vagy elutasít.
- **Negatív:** **R** (fő), P.
- **Ítélet:** PASS = az újrafuttatás vagy az aktuális állapotot használja és ezt közli, vagy a régi zöld nem fogadható el; FAIL = az újrafuttatás a régi állapotra ad zöldet, amely a merge-hez elég, és a kimenet nem jelzi; INCONCLUSIVE = a használt állapot nem állapítható meg.
- **Tul.:** nincs.
- **Bemenete:** N4 (az érvénytelenítés blokkoló állapota), R-V.9.

**M-A5 — Bizonyítékhelyettesítés a futások között**
- **H:** egy futás által előállított bizonyíték (artifact, gyorsítótár, kimenet) nem fogadható el egy másik futás, commit vagy típus bizonyítékaként.
- **Köv.:** R-V.3, R-D.9 (típusok összetévesztése), R-M.6, R-M.11; R-C.3.
- **Elrendezés:** a verifier-szerű fogyasztó artifactot vagy gyorsítótárat olvas egy korábbi futásból; kérdés: a platform név- és hatókör-szabályai megakadályozzák-e, hogy egy PR-ből induló futás ugyanazon néven felülírjon vagy előre elhelyezzen egy későbbi, hitelesnek szánt bizonyítékot (artifact-névütközés, cache-mérgezés, check-run kimenet másolása).
- **PK:** ültetett: két futás azonos nevű artifactot állít elő eltérő tartalommal; a fogyasztónak azonosítania kell, melyik honnan jön.
- **Negatív:** **S** (fő), R.
- **Ítélet:** PASS = a fogyasztó a forrást (run id, commit, identitás) megkülönbözteti, a nem hiteles forrás bizonyítéka nem kerül elfogadásra. FAIL = a nem hiteles forrás bizonyítéka észrevétlenül elfogadódik. INCONCLUSIVE = a forrás nem állapítható meg.
- **Tul.:** nincs.
- **Bemenete:** az R-M.6 verdikt-kötés és a futási bizonyíték (N2.6) követelményeinek kiindulópontja.

**M-A6 — A platform belső merge-ablaka (nem mérhető kívülről)**
- **H:** a merge-kapu értékelése és a ref frissítése közötti belső ablak nem használható ki.
- **Köv.:** R-V.11.
- **Elrendezés:** nincs; a rés kívülről nem injektálható és nem figyelhető meg (következtetés, nem mért).
- **Ítélet:** **INCONCLUSIVE by design.** A tétel célja: a maradék kockázat kimondott rögzítése (a jelentésben a „platform belső ablak" sor), hogy a megoldási terv ne állítsa, hogy az R-V.11 e rétegben bizonyított.
- **Bemenete:** a megoldási terv „nem lefedett" listája.

### 3.B E1/E2 csatornák: a hitelesítő adat elérhetetlensége a vizsgált tárgyból

A tételek **kanári értékkel** futnak (2.5). A „hitelesítő adat" itt mindig a kanári. A PR-szerző (támadó) szerepét egy **a repóhoz írási joggal bíró és egy külső (fork) identitás** játssza; a második identitás létrehozása tulajdonosi lépés (O-3).

**M-B1 — Esemény- és workflow-típusonként: kapja-e a PR-ból induló futás a kanárit**
- **H:** a PR szerzője által kiváltott futások egyike sem éri el a kibocsátó hitelesítő adatának kanári-megfelelőjét.
- **Köv.:** R-I.2, R-I.4; R-A.2; R-M.3 (a).
- **Elrendezés:** a kanári a kibocsátó hitelesítő adatával azonos **tárolási helyen és védelemmel** (ugyanaz a hatókör, ugyanaz az environment-védelem) létrehozva. Eseménytípusok és ágak: a PR-ból induló `pull_request` (azonos repó ága), `pull_request` fork-ból, `pull_request_target`, `workflow_run`, `issue_comment`, a PR-szerző saját ágára `push`, `workflow_dispatch`. Mindegyiknél a PR a workflow-t módosítja úgy, hogy a kanárit kiolvassa. Rögzítendő: a kanári hozzáférhető volt-e.
- **PK:** egy ismerten hozzáférő konfiguráció (a kanári a korlátozás nélküli helyen): a harness ezt kiolvassa (ültetett); egy ismerten védett: a kanári nem olvasható (ismert jó).
- **Negatív:** **X** (kanári használata a hatókörén túl), S (a kanáriként megjelenő hamis érték).
- **Ítélet:** PASS = eseménytípusonként a kanári nem olvasható, a PK teljesült. FAIL = legalább egy típusnál olvasható. INCONCLUSIVE = egy eseménytípus kiváltása nem volt lehetséges (pl. a repó nem fogad forkot), vagy a PK nem teljesült; ez külön rögzítendő (nem „PASS").
- **Tul.:** a külső identitás és a kanári-beállítás (O-3, O-5).
- **Bemenete:** az E1-csatornák P0-státuszának lezárása vagy fenntartása (Jel-2b), az R-M.13 közös-útvonal dokumentáció.

**M-B2 — Kiszivárgási csatornák: napló, artifact, gyorsítótár, összegzés, check-run kimenet**
- **H:** a kanári nem szivárog ki olyan csatornán, amelyet a PR szerzője olvashat.
- **Köv.:** R-I.2, R-I.4; R-M.3 (a).
- **Elrendezés:** olyan futás, amely a kanárit hozzáfér (a védett konfigurációban, a PR-szerző kódjával *nem*): kísérletek arra, hogy a platform maszkolása átalakított értékre (kódolás, darabolás, megfordítás) is érvényes-e; hogy a kanári az artifactba, a gyorsítótárba, a job-összegzésbe, a check-run kimenetébe, a naplóba kerülhet-e, és ezeket a PR szerzője olvashatja-e.
- **PK:** a harness egy ismert, maszkolatlan kanárit (nem titokként regisztrált) kiír: a mérési elrendezésnek ezt a csatornán látnia kell (ültetett); egy titokként regisztrált értéknél a maszkolás észlelhető (ismert jó).
- **Negatív:** **X**, P (átalakított érték).
- **Ítélet:** PASS = egyik csatornán sem olvasható átalakítás nélküli vagy triviálisan átalakított kanári; FAIL = legalább egy csatornán olvasható; INCONCLUSIVE = valamely csatornát a harness nem tudott olvasni.
- **Tul.:** O-5.
- **Bemenete:** Jel-2b/2c lezárása; a megmaradó kockázat dokumentálása.

**M-B3 — Ugyanazon futásban a PR által befolyásolt lépés**
- **H:** a hitelesítő adatot birtokló futásba a PR szerzőjének kódja nem kerülhet.
- **Köv.:** R-I.2; R-M.3 (b) (kódellátási út), (d) (futási példány); R-M.1.
- **Elrendezés:** a hitelesítő adatot birtokló job-ban a PR-ból érkező elemek: a checkout a PR ágáról, a PR által módosított lokális/összetett action, a környezetet és az útvonalat módosító mechanizmusok (a futó job környezeti változóinak és `PATH`-jának módosítása korábbi lépésből), a PR által módosított workflow-fájl. Kérdés: melyik elem jut a kanárit birtokló lépés közelébe.
- **PK:** ültetett: a kanári birtokló lépés előtti, a harness által befolyásolt lépés a kanárit kiolvassa; a mérésnek ezt észlelnie kell.
- **Negatív:** **X**, S (a lépés helyettesítése azonos nevűvel).
- **Ítélet:** PASS = nincs olyan, a PR által befolyásolható elem, amely a kanárit birtokló lépés előtt vagy közben fut; FAIL = van; INCONCLUSIVE = a PK nem teljesült.
- **Tul.:** nincs.
- **Bemenete:** R-M.3 (b), (d) igazolása; a független verifier elhelyezésének feltételei.

**M-B4 — Az environment-védelem megkerülése**
- **H:** az environment-hez kötött hitelesítő adatot csak a szándékolt, védett ágról induló futás éri el.
- **Köv.:** R-I.2; R-A.2 (a) (a tárgy szerzője nem módosíthatja); R-M.3 (c).
- **Elrendezés:** a korábban mért elutasítás (`refs/pull/35/merge` nem deployolhat, PR35, mért) a kiindulópont. Újak: az ág-szabály mintájának megfelelő ágat a PR-szerző létre tud-e hozni; a védett ágra írási jog nélkül; a szabály módosítása PR-ból; a jóváhagyó kör módosítása.
- **PK:** ültetett: az environment-védelmet a tulajdonos ideiglenesen lazítja (egy ismert rés): a mérésnek ezt észlelnie kell.
- **Negatív:** **X**, S.
- **Ítélet:** PASS = a védelem minden próbánál megállít; FAIL = valamely próba hozzáfér; INCONCLUSIVE = a védelem beállítását a harness nem tudta ellenőrizni.
- **Tul.:** O-4 (az ágszabály és a környezet beállításai).
- **Bemenete:** az R-A.2 teljesíthetősége; N1.1 (a nyilvántartás védelme).

**M-B5 — Mutábilis függőség (a kódellátási út)**
- **H:** a hitelesítő adatot birtokló futás kódja nem változtatható meg a tárgy szerzője által elérhető módon, a futtató és az ellenőrző közti útvonalon.
- **Köv.:** R-M.3 (b); R-D.13 (tartalom-azonosított függőségek); R-D.21.
- **Elrendezés:** a workflow harmadik fél action-jét **a mérés saját, scratch action-repójából** hivatkozza (nem külső szolgáltatásból): (a) címke szerint, (b) commit SHA szerint. A címkét áthelyezzük (ellenőrzött injektálási pont), és megfigyeljük, melyik kód futott. Ugyanez az interpreter és az eszközök verziójára (a runner képfájl frissülése: kívülről nem injektálható, csak megfigyelés).
- **PK:** a két hivatkozási mód viselkedése eltér (a címke elmozdulása hat, az SHA nem): ez az ismert eltérés.
- **Negatív:** **S** (a kód helyettesítése), P.
- **Ítélet:** PASS = SHA szerinti hivatkozás esetén az elmozdított címke nem hat, és a címke szerinti hivatkozás veszélye dokumentált; FAIL = az SHA szerinti hivatkozás is megváltoztatható; INCONCLUSIVE = a futás nem azonosította, melyik kód futott.
- **Tul.:** nincs.
- **Bemenete:** R-D.13/R-D.21 igazolása; az E terület.

### 3.C Visszavonás és az installáció felfüggesztése

**M-C1 — Felfüggesztett installáció: új PR**
- **H:** a felfüggesztett kibocsátó nem tud új, érvényes döntést kibocsátani, és a merge nem engedélyezett.
- **Köv.:** R-I.1, R-I.5, R-I.7; R-V.10 (hiányzó forrás: negatív kimenet).
- **Elrendezés:** a tulajdonos felfüggeszti az App installációját; új PR nyílik; megfigyeljük: létrejön-e check-run, mi a PR merge-állapota, mi a hibaüzenet (token kiadás, check-run létrehozás).
- **PK:** a felfüggesztés **előtt** ugyanazon elrendezés zöld (ismert jó); a **bizonyítottan hibás** workflow (hiányzó `app-id`, A2 korábbi mérés) `blocked` állapotot ad (ültetett).
- **Negatív:** **D** (a kibocsátó nem elérhető), X.
- **Ítélet:** PASS = nem jön létre új érvényes check, a PR nem mergelhető; FAIL = a PR mergelhető érvényes check nélkül, vagy hamis zöld; INCONCLUSIVE = a felfüggesztés nem hatott a megfigyelt időn belül (késleltetés), vagy a PK nem teljesült.
- **Tul.:** **O-1** (felfüggesztés és visszaállítás; a kulcs nem kerül hozzám).
- **Bemenete:** N7, R-I.7 platformon belüli teljesíthetősége.

**M-C2 — A már közzétett check-run sorsa a felfüggesztés után**
- **H:** a felfüggesztés után a korábban kibocsátott döntés nem engedélyezi a következményes műveletet.
- **Köv.:** R-I.1 (használatkori ellenőrzés), R-I.7, R-M.9.
- **Elrendezés:** egy PR, amelyen a kibocsátó zöld check-runt tett; a felfüggesztés után figyeljük: a merge-kapu továbbra is elfogadja-e; mi látható az API-ból ugyanarról a check-runról (azonos? megjelölt?). Időpontok: azonnal, +1, +5, +15 perc (a késleltetés mérése).
- **PK:** ültetett: a check-run kézzel (a harness által) törölve/érvénytelenítve (ha a platform engedi): a merge-kapu viselkedése a „nincs check" referencia; ismert jó: a felfüggesztés előtt a merge engedélyezett.
- **Negatív:** **R** (a visszavont azonosság korábbi döntése).
- **Ítélet:** PASS = a merge a felfüggesztés után nem engedélyezett, vagy a platform a használatkor újraértékeli a jogosultságot; FAIL = a merge engedélyezett (a már közzétett check elég); INCONCLUSIVE = a viselkedés időben változott és a harness nem rögzítette az átmenetet.
- **Tul.:** O-1.
- **Bemenete:** N7/Jel-1, N8 háttere: a kompromittált időszakban kibocsátott döntések sorsa.

**M-C3 — A hitelesítő adat érvényessége a visszavonás után**
- **H:** a visszavonás után a korábban kiadott token vagy bejelentkezési adat nem használható új döntés kibocsátására.
- **Köv.:** R-I.5, R-I.7; R-A.8 (forgatás, helyreállítás).
- **Elrendezés:** a visszavonás módjai külön-külön: (a) installáció felfüggesztése, (b) jogosultság csökkentése (a `checks: write` megvonása), (c) a repó eltávolítása az installációból, (d) a kulcs forgatása. Mindegyiknél: egy a visszavonás **előtt** kiadott token használható-e a visszavonás után (check-run létrehozási kísérlet), és mennyi idő múlva válik használhatatlanná.
- **PK:** a visszavonás előtt a token használható (ismert jó); a token lejáratának ismert ideje után használhatatlan (ültetett: referencia).
- **Negatív:** **R** (régi token), X.
- **Ítélet:** PASS = a visszavonás után a régi token nem hoz létre új érvényes check-runt (a lejárati időn belül sem); FAIL = igen, és a használhatóság ablaka mért; INCONCLUSIVE = a token kiadás ideje nem rögzíthető.
- **Tul.:** **O-1** (a)–(c); **O-2** (d): a kulcsforgatás tulajdonosi művelet.
- **Bemenete:** az R-A.8 forgatási eljárásának időkorlátai, N8.

**M-C4 — A helyreállítás nem érvényesít visszamenőleg**
- **H:** a visszaállított kibocsátó a felfüggesztés alatt (vagy előtte, jogosulatlanként) hozott állapotot nem érvényesíti visszamenőleg.
- **Köv.:** R-I.7 (utolsó mondat), R-A.9, R-A.10.
- **Elrendezés:** a felfüggesztés alatt a PR állapota; a visszaállítás után: a korábbi PR check-állapota változik-e magától; kell-e új döntés.
- **PK:** ültetett: egy a felfüggesztés alatt módosított PR; a visszaállítás után a régi (a módosítás előtti) zöld nem lehet érvényes az új HEAD-re.
- **Negatív:** **R**.
- **Ítélet:** PASS = a visszaállítás után új döntés kell az érintett PR-hoz; FAIL = az állapot visszamenőleg érvényessé válik; INCONCLUSIVE = a platform késleltetése miatt nem állapítható meg.
- **Tul.:** O-1.
- **Bemenete:** R-I.7 a megoldási tervben.

**M-C5 — Az aktuális hiteles állapot lekérdezhetősége a felhasználás pillanatában**
- **H:** egy független fogyasztó a felhasználás pillanatában, a kibocsátótól függetlenül le tudja kérdezni az aktuális hiteles állapotot: az ág csúcsát, a szabályokat, a kibocsátó jogosultsági állapotát, a nyilvántartás aktuális tartalmát.
- **Köv.:** R-V.5, R-M.4, R-M.9, R-A.10; R-I.1.
- **Elrendezés:** minden állapotelemre: milyen identitás és milyen jogosultság kell az olvasáshoz; a válasz tartalmaz-e időbélyeget vagy verziót; a gyorsítótárazás és a késleltetés; hozzáfér-e egy a tárgy szerzője által befolyásolt futás ugyanahhoz (és ha igen, ez megkérdőjelezi-e a függetlenséget).
- **PK:** egy ismerten megváltoztatott állapotelem (ültetett): a lekérdezésnek az új értéket kell adnia az ismert késleltetésen belül.
- **Negatív:** **D** (az olvasás nem lehetséges: az elvárt eredmény a negatív/fail-closed), S.
- **Ítélet:** PASS = minden állapotelem lekérdezhető a használat pillanatában és az aktuális értéket adja; FAIL = valamelyik elem csak a döntés idejű, régebbi állapotból olvasható (pl. a régi BASE-ről), vagy nem olvasható; INCONCLUSIVE = a lekérdezés eredményét nem lehetett az igazi állapothoz hasonlítani.
- **Tul.:** O-4 (egyes olvasási jogosultságok megadása).
- **Bemenete:** N1.4 (nyilvántartás-állapot kezelése), R-M.9 teljesíthetősége.

### 3.D Két független kibocsátói azonosság együttes kikényszerítése

A tételekhez egy **második, független kibocsátói azonosság** kell (második scratch App, külön hitelesítő adat, külön hatókör). Létrehozása tulajdonosi lépés (**O-2**); a kulcs nem kerül hozzám.

**M-D1 — Két required check, külön azonosságra kötve**
- **H:** a merge-kapu mindkét azonosság check-jét külön megköveteli; bármelyik hiánya megállítja a merge-t.
- **Köv.:** R-I.1–R-I.3; R-M.2; R-A.1; R-X (együttes elfogadás).
- **Elrendezés:** két check, két azonosság (a korábban mért azonosságkötés mintájára, A1/E3s), mindkettő megkövetelve; kombinációk: mindkettő zöld, az egyik hiányzik, az egyik piros, az egyik rossz azonosságtól.
- **PK:** ismert jó: mindkettő zöld → mergelhető; ültetett: az egyik hiányzik → nem.
- **Negatív:** **S** (azonos nevű check másik azonosságtól), D, R.
- **Ítélet:** a kombinációk mátrixa; PASS = a négy hibás kombináció mindegyike megállít; FAIL = bármelyik átenged; INCONCLUSIVE = a platform nem engedi két azonosság külön megkövetelését (ez maga is eredmény: a követelmény natívan nem teljesíthető).
- **Tul.:** O-2, O-4.
- **Bemenete:** R-M.2, az M2 osztály kivitelezhetősége.

**M-D2 — Azonos nevű check-ek és állapotok helyettesítése**
- **H:** a megkövetelt azonosság check-jét más azonosság azonos nevű check-je vagy állapotjelzése nem helyettesítheti.
- **Köv.:** R-I.2, R-I.3 (azonosság kötése); R-M.6 (S, helyettesítés).
- **Elrendezés:** azonos nevű check-run a repó saját munkafolyamat-azonosságától (korábban mért: az Actions-identitás külön check-et adott, A1: PASS), egy harmadik azonosságtól, és egy *commit-állapotként* (nem check-run) közölt azonos nevű jelzés.
- **PK:** ismert jó: a megkövetelt azonosság saját check-je elfogadott.
- **Negatív:** **S** (fő), P.
- **Ítélet:** PASS = egyik helyettesítés sem teljesíti a követelményt; FAIL = bármelyik teljesíti; INCONCLUSIVE = valamelyik azonosság nem volt előállítható.
- **Tul.:** O-2.
- **Bemenete:** az identitás-kötés határai (a verdikt hordozásának helye).

**M-D3 — Az egyik azonosság elérhetetlensége**
- **H:** az egyik kibocsátó/verifier elérhetetlensége vagy felfüggesztése a merge megállítása, nem a követelmény elengedése.
- **Köv.:** R-V.10, R-M.8 (fail-closed), R-I.7.
- **Elrendezés:** a két azonosság közül egyet felfüggesztünk, majd a másikat; a PR állapota.
- **PK:** a két azonosság mindegyike nélkül a PR nem mergelhető (ültetett); mindkettővel igen (ismert jó).
- **Negatív:** **D**.
- **Ítélet:** PASS = bármelyik hiányában a merge nem engedélyezett; FAIL = bármelyik hiányában engedélyezett; INCONCLUSIVE = a felfüggesztés hatása nem figyelhető meg.
- **Tul.:** O-1.
- **Bemenete:** az R-M.8 platformon belüli kikényszeríthetősége.

**M-D4 — Az egyik azonosság hatásköre a másikon**
- **H:** az egyik azonosság nem tudja a másik check-jét újrafuttatni, felülírni, törölni vagy a hatókörét módosítani.
- **Köv.:** R-M.3 (a), (c); R-M.1; R-I.4.
- **Elrendezés:** a kibocsátó azonosság jogosultságaival (a korábban mért négy jogosultság) próbálkozás a verifier azonosság check-jével: létrehozás ugyanazon néven, felülírás, a check-suite módosítása; a jogosultsági modell leírása (ki indíthat újrafuttatást: Jel-8 is).
- **PK:** ismert jó: a saját check módosítható; ültetett: a másik azonosságé nem.
- **Negatív:** **X**, **S**, R.
- **Ítélet:** PASS = a másik azonosság check-jéhez nem fér hozzá; FAIL = hozzáfér; INCONCLUSIVE = a jogosultsági modell nem állapítható meg.
- **Tul.:** O-2.
- **Bemenete:** Jel-8; R-M.3.

**M-D5 — Közös kompromittálási útvonal a két azonosság között**
- **H:** egyetlen hostile PR sem szerzi meg mindkét azonosság hitelesítő adatát (kanáriját) ugyanazon a csatornán.
- **Köv.:** R-M.3 (a)–(d), R-M.13 (három réteg); R-A.1.
- **Elrendezés:** a két kanári az azonosságok valós tárolási helyén; a B terület eseménytípusai; **a közös tárolási hely, közös workflow, közös runner** feltárása konfiguráció-olvasással.
- **PK:** a B terület PK-i; ültetett: közös tárolási hely esetén mindkét kanári elérhető (a mérés észleli).
- **Negatív:** **X**, S.
- **Ítélet:** PASS = nincs közös útvonal a mért csatornákon; FAIL = van; INCONCLUSIVE = a B terület releváns tételei INCONCLUSIVE-ek. A talált közös útvonalat a jelentés R-M.13 szerint a **közös bizalmi alap** vagy a **fennmaradó kockázat** rétegbe sorolja.
- **Tul.:** O-2, O-5.
- **Bemenete:** az R-M.13 dokumentáció; N1.1.

**M-D6 — A verifier definícióját a tárgy nem módosíthatja**
- **H:** a PR szerzője nem változtathatja meg, melyik azonosságot követeli meg a merge-kapu, és nem módosíthatja a verifier job definícióját úgy, hogy a verifier verdiktje megváltozzon.
- **Köv.:** R-M.1, R-A.2 (a), R-V.2.
- **Elrendezés:** a hostile PR (a) módosítja a workflow-t, amely a verifiert futtatja, (b) a megkövetelt check nevét vagy azonosságát megváltoztató szabályt próbál módosítani, (c) a verifier workflow-t ugyanazon néven más tartalommal futtatja.
- **PK:** ültetett: a módosítás a verifier verdiktjét megváltoztatja, ha a PR-verziót használnák (a mérés ezt észleli); ismert jó: az alapág-verziót futtatva a verdikt nem változik.
- **Negatív:** **P**, **S**.
- **Ítélet:** PASS = a verifier a PR-től független (alapág-) definícióból fut, és a szabály a PR-ből nem módosítható; FAIL = a PR módosíthatja; INCONCLUSIVE = nem állapítható meg, melyik definíció futott.
- **Tul.:** O-2, O-4.
- **Bemenete:** R-M.1 teljesíthetősége.

### 3.E A tényleges futási azonosság bizonyíthatósága

**M-E1 — Milyen hiteles futási bizonyíték áll rendelkezésre**
- **H:** a platform olyan bizonyítékot ad egy futásról, amely hitelesen köti a futást a workflow-definícióhoz (útvonal, commit) és az azonossághoz, a tárgy szerzője által nem befolyásolható módon, és a kibocsátótól függetlenül ellenőrizhető.
- **Köv.:** R-M.11, R-M.12; R-D.21; R-V.6.
- **Elrendezés:** leltár: a futás metaadatai, a futás által megszerezhető, platform által aláírt azonosító (tokenek és állítások), igazolások, ha a platform kínál; mindegyiknél: kicsoda hozza létre, a PR szerzője befolyásolhatja-e a tartalmát, a független fél a kibocsátó közreműködése nélkül ellenőrizheti-e, mit köt (workflow-útvonal, SHA, azonosság, futási kísérlet).
- **PK:** ültetett: két különböző workflow/commit futásának bizonyítéka **eltérő** tartalmat kell hordozzon (ezt a mérés észleli); ismert jó: ugyanazon futás kétszeri lekérdezése azonos bizonyítékot ad.
- **Negatív:** **S** (más futás bizonyítéka), **R** (régi futás bizonyítéka), P.
- **Ítélet:** PASS = van legalább egy bizonyíték-típus, amely (workflow, commit, azonosság, futás) négyesét hitelesen köti, a PR szerzője nem módosíthatja, és független fél ellenőrizheti; FAIL = csak a kibocsátó önbevallása elérhető (az R-M.11 nem teljesíthető, PARTIAL/OPEN marad); INCONCLUSIVE = a bizonyíték-típus ellenőrizhetősége nem döntött el.
- **Tul.:** nincs (a platform-eszközök vizsgálata); egyes igazolások beállítása O-4.
- **Bemenete:** **N2.6** (hiteles futási bizonyíték), az R-M.11 teljesíthetősége az M2 osztályra.

**M-E2 — A forrásból képzett digest nem bizonyítja a futást**
- **H:** (a *ellenőrzött* hipotézis) ha a forrás digestje egyezik, a végrehajtott implementáció is azonos. **A terv szerint ezt várhatóan megcáfoljuk**; a mérés célja, hogy a rés megfigyelt legyen, és hogy a M-E1 bizonyítéka észleli-e.
- **Köv.:** R-M.4, R-M.11; R-D.12, R-D.21, R-D.22.
- **Elrendezés:** ültetett eltérések, a forrás digestjének megváltoztatása nélkül: (a) a futás közbeni letöltés felülírja az ellenőrző logikáját, (b) mutábilis action-hivatkozás elmozdulása, (c) interpreter- vagy csomagverzió eltérés, (d) környezeti változó, amely a döntést megváltoztatja, (e) a `PATH` árnyékolása.
- **PK:** minden ültetett eltérésnél a **viselkedés** a forrásétól tényleg eltér (a harness ezt a kimenetből kimutatja); ismert jó: eltérés nélkül a viselkedés azonos.
- **Negatív:** **P** (fő), S.
- **Ítélet:** két kérdés külön: (1) „a forrás-digest elég?" — **FAIL várt**, ha legalább egy eltérés a forrás-digest változatlansága mellett hat; (2) „a M-E1 bizonyítéka észleli?" — PASS = az eltérés a bizonyítékból kimutatható; FAIL = nem; INCONCLUSIVE = a PK nem teljesült.
- **Tul.:** nincs.
- **Bemenete:** az R-M.4 alátámasztása, az R-D.21 megvalósíthatóságának korlátai.

**M-E3 — A futási azonosság rögzítése: önbevallás vagy független bizonyíték**
- **H:** a futási azonosság (az interpreter és a betöltött elemek azonossága) olyan módon rögzíthető, amely nem a futó kódtól (a vizsgált ellenőrzőtől) származó önbevallás.
- **Köv.:** R-D.21, R-D.12, R-D.13; R-M.11; R-M.12.
- **Elrendezés:** a futó ellenőrző maga rögzíti a saját futási azonosságát (önbevallás: referencia), és összevetjük azzal, amit a platform vagy egy független lépés rögzít; kérdés: eltérő (ültetett: megmérgezett) futásnál az önbevallás megbízhatatlan-e, és a független rögzítés észleli-e.
- **PK:** ültetett: az ellenőrző hamis azonosságot ír önmagáról; a mérésnek az eltérést észlelnie kell, ha van független forrás.
- **Negatív:** **P**, **S** (a futási azonosság hamisítása).
- **Ítélet:** PASS = van független rögzítés, amely a hamis önbevallást észleli; FAIL = csak önbevallás van (R-M.11/12 e réteggel nem teljesíthető); INCONCLUSIVE = a független rögzítés nem értékelhető.
- **Tul.:** nincs.
- **Bemenete:** N2.6, az R-D.21 megvalósítási feltételei.

**M-E4 — Nem deklarált, döntést befolyásoló bemenet**
- **H:** egy deklarálatlan bemenet döntésre gyakorolt hatása észlelhető vagy kizárható.
- **Köv.:** R-D.22, R-D.23, R-P.14; R-C.3.
- **Elrendezés:** ültetett nem deklarált bemenetek: környezeti változó, hálózati letöltés, a runner képfájl változása, a rendszeridő, a gyorsítótár tartalma; mindegyik megváltoztatja a döntést, miközben a deklarált jegyzék változatlan.
- **PK:** minden ültetett bemenet hatása a harnessből kimutatható (ismert); ismert jó: a deklarált bemenet változása a jegyzék változásával jár.
- **Negatív:** **P**, X.
- **Ítélet:** PASS = a nem deklarált bemenet hatása észlelhető/kizárható; FAIL = észrevétlenül befolyásolja a döntést; INCONCLUSIVE = a hatás a harnessből nem mutatható ki.
- **Tul.:** nincs.
- **Bemenete:** R-D.22, a P-határ (N3) „kötetlen tényező" kezelése.

**M-E5 — A futási bizonyíték visszajátszása és helyettesítése**
- **H:** egy futás bizonyítéka nem fogadható el egy másik futás, commit, workflow vagy kísérlet döntéséhez.
- **Köv.:** R-M.6, R-M.11 (a döntéshez kötés), R-D.9; R-V.3.
- **Elrendezés:** a M-E1-ben azonosított bizonyíték(ok) **keresztfelhasználása**: A futás bizonyítékát B futás döntéséhez csatolva; régi futás bizonyítéka új commitra; azonos futás más kísérlete (újrafuttatás); más workflow bizonyítéka. A bizonyíték tartalmaz-e olyan mezőt, amely az ilyen felcserélést megkülönbözteti.
- **PK:** ültetett: a két futás bizonyítéka különbözik; ismert jó: azonos futás azonos bizonyítéka.
- **Negatív:** **R**, **S** (mindkettő fő).
- **Ítélet:** PASS = minden keresztfelhasználás eltérő mezőkkel megkülönböztethető, és (a fogyasztó szerepében) elutasítható; FAIL = valamelyik felcserélés az adatokból nem különböztethető meg; INCONCLUSIVE = a bizonyíték nem hordoz megkülönböztető mezőt, vagy az M-E1 INCONCLUSIVE.
- **Tul.:** nincs.
- **Bemenete:** R-M.6 és R-M.11 mezőkészlete.

---

## 4. Visszavezetési mátrix

### 4.1 Tétel → követelmény

| Tétel | Követelmények |
|---|---|
| M-A1 | R-V.1, R-V.3, R-V.7, R-V.11, R-P.12 |
| M-A2 | R-P.14, R-P.15, R-P.12, R-P.16, R-V.5, R-V.7, R-V.11 |
| M-A3 | R-V.4, R-V.7, R-V.8, R-V.11 |
| M-A4 | R-V.7, R-V.8, R-V.9, R-V.11, R-M.6 |
| M-A5 | R-V.3, R-D.9, R-M.6, R-M.11, R-C.3 |
| M-A6 | R-V.11 |
| M-B1 | R-I.2, R-I.4, R-A.2, R-M.3 |
| M-B2 | R-I.2, R-I.4, R-M.3 |
| M-B3 | R-I.2, R-M.1, R-M.3 |
| M-B4 | R-I.2, R-A.2, R-M.3 |
| M-B5 | R-M.3, R-D.13, R-D.21 |
| M-C1 | R-I.1, R-I.5, R-I.7, R-V.10 |
| M-C2 | R-I.1, R-I.7, R-M.9 |
| M-C3 | R-I.5, R-I.7, R-A.8 |
| M-C4 | R-I.7, R-A.9, R-A.10 |
| M-C5 | R-V.5, R-M.4, R-M.9, R-A.10, R-I.1 |
| M-D1 | R-I.1, R-I.2, R-I.3, R-M.2, R-A.1, R-X |
| M-D2 | R-I.2, R-I.3, R-M.6 |
| M-D3 | R-V.10, R-M.8, R-I.7 |
| M-D4 | R-I.4, R-M.1, R-M.3 |
| M-D5 | R-M.3, R-M.13, R-A.1 |
| M-D6 | R-M.1, R-A.2, R-V.2 |
| M-E1 | R-M.11, R-M.12, R-D.21, R-V.6 |
| M-E2 | R-M.4, R-M.11, R-D.12, R-D.21, R-D.22 |
| M-E3 | R-D.21, R-D.12, R-D.13, R-M.11, R-M.12 |
| M-E4 | R-D.22, R-D.23, R-P.14, R-C.3 |
| M-E5 | R-M.6, R-M.11, R-D.9, R-V.3 |

### 4.2 Követelmény-család → lefedés

| Család | Lefedés ebben a tervben | Nem fedett ebben a szakaszban (és hol marad) |
|---|---|---|
| **R-I** | R-I.1–R-I.5, R-I.7 platformon belüli viselkedése (B, C, D terület) | A kibocsátó-függetlenség mechanizmus szintű igazolása (6. lépés) |
| **R-V** | R-V.1, R-V.3–R-V.5, R-V.7–R-V.11 a platform natív viselkedésére (A terület) | A P/C kötés igazolása (megoldás nélkül nem mérhető; 6. lépés); R-V.12 (emberi jóváhagyás: korábbi mérés) |
| **R-C** | Csak érintőlegesen (M-A5, M-E4: R-C.3) | R-C.1, R-C.2, R-C.4–R-C.6: N6 és a Jel-4/Jel-5 mérések (7–8. lépés) |
| **R-P** | R-P.12, R-P.14–R-P.16 (M-A1, M-A2) | R-P.1–R-P.11, R-P.13: a P-határ tervezési szintű, nem platformmérés |
| **R-D** | R-D.9, R-D.12, R-D.13, R-D.21–R-D.23 a futási azonosság felől (E, B terület) | R-D.1–R-D.8, R-D.10, R-D.11, R-D.14–R-D.20: **lokális** tesztvektorok (8. lépés, N5 (b)) |
| **R-A** | R-A.1, R-A.2, R-A.8–R-A.10 platform-képességként (B, C, D) | R-A.3–R-A.7: a nyilvántartás/telepítés mechanizmusa (megoldási terv után) |
| **R-M** | R-M.1–R-M.4, R-M.8, R-M.9, R-M.11, R-M.12 mint feltételezett platform-tulajdonságok (A, C, D, E) | R-M.5, R-M.6 (verdikt), R-M.10 (kivételes eljárás), R-M.13 (dokumentáció): mechanizmus nélkül nem mérhető |

---

## 5. Sorrend és függőségek a mérésen belül

| Fázis | Tételek | Előfeltétel |
|---|---|---|
| **0 — Előkészítés és önellenőrzés** | a harness önellenőrzése (minden PK külön, a tételek előtt); a kanárik elhelyezése; a mérési környezet rögzítése | O-5 (kanárik), K-1 (környezet döntés) |
| **1 — Tulajdonosi lépés nélkül** | M-A1, M-A2 (a platform-beállítás nélküliek), M-A3 (1)–(3), M-A4, M-A5, M-B3, M-B5, M-E1–M-E5 | 0. fázis |
| **2 — Külső identitással és beállításokkal** | M-B1, M-B2, M-B4, M-A3 (4)–(6), M-A2 többi, M-D4 (egy azonossággal), M-C5 | O-3, O-4 |
| **3 — Kulcsműveletet / felfüggesztést igénylő** | M-C1–M-C4, M-D1–M-D3, M-D5, M-D6 | O-1, O-2 (második azonosság), K-3 |
| **Mindig** | M-A6 (nem mérhető): a jelentésben rögzítendő | — |

**Függőségek:** a M-D5 a B terület eredményeire épít; a M-C2 és M-C3 a M-C1 felfüggesztési környezetére; a M-E5 az M-E1 bizonyíték-leltárára; a M-D1–D4 a második azonosságra. **Egy tétel INCONCLUSIVE-sége nem szünteti meg a függő tételek értékelését, de azokat jelölni kell** (a függő tétel ítélete csak akkor PASS, ha az előfeltétel eredménye nem INCONCLUSIVE).

**Az eredmények felhasználása (nem döntés):** a FAIL-ek a megoldási terv (5. lépés) követelményeit pontosítják; a PASS-ok a platform natívan megbízható elemeit rögzítik (S, B), **de csak a mért esetekre**; az INCONCLUSIVE-ok nyitott kérdésként maradnak. Az N8 fennállását egyik eredmény sem dönti el.

---

## 6. Tulajdonosi beavatkozások jegyzéke

A terv **nem** végzi el ezeket; a végrehajtási GO-ban külön elfogadandók. A kulcs és a titok **nem kerül hozzám**; a tulajdonos csak a nem titkos kimenetet (státusz, HTTP-kód, azonosítók, képernyő- vagy API-kimenet) adja át.

| Azonosító | Lépés | Mihez kell | Mit kapok vissza |
|---|---|---|---|
| **O-1** | Az App installációjának felfüggesztése és visszaállítása a scratch szervezetben (a megadott időpontokban) | M-C1–M-C4, M-D3 | Az időpontok és a kimenet (UI/API státusz) |
| **O-2** | Második scratch App létrehozása és telepítése; a kulcs forgatása (M-C3 (d)); a két azonosság hitelesítő adatainak beállítása a scratch repón | M-C3 (d), M-D1–D6 | A második App azonosítója (nem titok); a kulcsot nem |
| **O-3** | Külső (fork) identitás vagy második emberi fiók a hostile PR-okhoz | M-B1 és a fork-esetek | Az identitás neve |
| **O-4** | Scratch repó-beállítások módosítása a mérési tételek szerint (szabályok, környezet-védelem, ágszabályok, `strict`, olvasási jogosultságok) | M-A2, M-A3 (4)–(6), M-B4, M-C5, M-D6 | A beállítás előtti és utáni állapot (kimenet) |
| **O-5** | A kanári értékek létrehozása és a megfelelő tárolási helyre helyezése | M-B1, M-B2, M-D5 | A kanári nem titkos azonosítója (nem az értéke, vagy az értéke, mert értéktelen) |
| **O-6** | A mérés végén a scratch állapot visszaállítása/megőrzése (a törlés HOLD) | minden | A döntés |

A scratch repók és az App **törlése HOLD**.

---

## 7. Nyitott kérdések a mérési tervhez

| # | Kérdés | Következmény |
|---|---|---|
| **K-1** | Új, dedikált scratch repó legyen a feltáró méréshez, vagy a meglévő `cic-scratch-212-public`? (Javaslat: új, a korábbi mért alapállapot megőrzésére.) | A környezet rögzítése, O-4 hatóköre |
| **K-2** | A repó nyilvános-e a mérés alatt (a fork-esetek ezt feltételezik: következtetés, nem mért)? Ha a végrehajtási környezet nem fogad forkot, a M-B1 fork-sorai INCONCLUSIVE-ek. | M-B1 lefedettsége |
| **K-3** | Rendelkezésre áll-e második scratch App és külső identitás, és mikor? | A 3. fázis időzítése |
| **K-4** | A Relay fogad-e fork-PR-t (nem ellenőrzött, olvasás szükséges)? A M-B1 eredménye csak a scratch-re vonatkozik; a Relay-re a kérdés külön tisztázandó. | A Jel-2a prioritása |
| **K-5** | Az Actions-percek, a rate limit és a futások száma tételenként (a végrehajtási GO-ban elfogadandó). | A 2.3 szabály ismétlésszámai |
| **K-6** | A visszajátszási próbák körében a harness mely beállításokat változtathatja (O-4 pontos listája). | Az M-A2 jegyzékének teljessége |
| **K-7** | A bizonyíték-típusok köre (M-E1): milyen platform-oldali igazolások érhetők el a scratch szervezeten; ez csak a végrehajtás közben derül ki. | M-E1 hatóköre |

---

## 8. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A terv nem mér, nem végez kulcsműveletet, nem módosít beállítást | Ellenőrizhető | A diff csak `jobs/relay-ci-parity-06i-.../` alatti fájlokat érint | `git diff --stat origin/main..HEAD` | — |
| Minden mérési tételnek van pozitív kontrollja és PASS/FAIL/INCONCLUSIVE kritériuma | Ellenőrizhető | 3. szakasz: tételenként PK és Ítélet mező | A tételek szisztematikus átolvasása (27 tétel: A1–A6, B1–B5, C1–C5, D1–D6, E1–E5) | A kritérium helyessége a végrehajtásig nem igazolt |
| Minden tétel visszavezethető a normatív követelményekre | Ellenőrizhető | 4.1 mátrix, 4.2 családi lefedés | A hivatkozott R-azonosítók léte a #76–#80 specifikációkban | Az R-azonosítók szövege változhat egy későbbi specifikáció-módosítással |
| A negatív esetek között van visszajátszás (R) és bizonyítékhelyettesítés (S) | Ellenőrizhető | 2.2 osztályok; M-A4, M-A5, M-C2, M-D1, M-D2, M-E5 | A „Negatív" mezők | — |
| A platform a S és B elemet natívan kötő viselkedése mért | **Mért (scratch, korábban)** | PR31, PR34 (app-measurement-report 3.3) | A jelentés | Csak a mért esetekre; a terv újra nem méri, hanem a mátrixba (M-A3) építi |
| Az R-V.5 a P és C elemekre platformon belül külön lépés nélkül nem teljesíthető | **Következtetés, nem mért** | open-case-triage 3.1; app-measurement-report 3.6 | M-A1, M-A2, M-E1 | A platform natívan köthet többet, mint feltételeztük |
| A scratch repó publikus, ezért fork-PR ott kiváltható | **Következtetés, nem mért** | app-measurement-report 2. szakasz (publikus repó) | K-2: a végrehajtás első lépése | A szervezet-beállítások korlátozhatják a fork-PR-t |
| A M-A6 belső ablak kívülről nem injektálható | **Következtetés, nem mért** | A platform belső értékelése kívülről nem megfigyelhető | Nincs; az INCONCLUSIVE by design ezt rögzíti | Ha lenne megfigyelhető jel, a tétel mérhetővé válna |
| A forrás-digest egyezése nem bizonyítja a végrehajtott implementáció azonosságát | **Következtetés, nem mért** | R-M.4 (a #80-ban kimondott követelmény) | M-E2 | A tétel célja épp ennek igazolása vagy cáfolata |
| Az E1/E2 mérés kimenete nem dönti el az N8 fennállását | Rögzített elv | open-case-triage 3.3 | — | — |
| A kanári az éles kulccsal azonos védelmű tárolási helyen reprezentálja a kulcs csatornáit | **Következtetés, nem mért** | A tárolási hely és védelem megegyezése a mérés kialakításától függ | O-5 és a 0. fázis (a kanári elhelyezésének dokumentálása) | Ha a védelem eltér, a mérés a kulcs csatornáira nem általánosítható |
| A terv várt eredményei hipotézisek | Rögzített | 3. szakasz „H" mezők | — | A „várt" nem összetévesztendő a „mért"-tel |

---

## 9. Mit nem állít ez a dokumentum

- Nem mér és nem hajt végre kulcs- vagy beállítás-műveletet; a végrehajtás külön GO-t igényel.
- A tételek „H" és „várt" állításai **hipotézisek**; a végrehajtás után is csak **scratch, mért** minősítésűek, **nem production-igazoltak**, és a Relay-re nem vonatkoznak (Jel-10, külön munkacsomag).
- Nem dönt az algoritmusról, a kódolásról, a Relay-implementációról, az éles beállításról, a #212 lezárásáról, a scratch repók törléséről.
- Nem vezeti be az N8-at a specifikációba, és nem módosítja a #76–#80 követelményeit.
- Nem állítja, hogy a felsorolt öt terület a teljes támadási felület: más csatornák (pl. a Relay-specifikus esetek, a bemeneti teljesség) a triázs további lépéseiben szerepelnek.
