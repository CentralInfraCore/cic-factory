# Döntési követelmények: kibocsátói hitelesség, döntési érvényesség, bemeneti teljesség

Státusz: **specifikációs tervezet felülvizsgálatra.** Nem implementáció, nem mérés, nem döntés a Relay beállításairól.

A dokumentum négy, egymástól élesen elválasztott részből áll. A besorolás a szakasz fejléce, nem a mondat hangneme dönti el:

| Rész | Szakasz | Mit jelent |
|---|---|---|
| **Normatív** | 2–4 | Technológiafüggetlen követelmény. Megvalósítási eszközt nem nevez meg. |
| **Mért** | 6 | Scratch környezetben, valós GitHub-futással igazolt tulajdonság. Csak a mért esetre érvényes. |
| **Nyitott** | 7 | Nem bizonyított, vagy nem eldöntött. Nem tekinthető teljesültnek. |
| **Javasolt, nem igazolt** | 8 | Megoldási irány. Sem a követelmény része, sem mért. |

A 5. szakasz (megfelelési leképezés) tájékoztató: megmutatja, hogyan viszonyul egy konkrét megvalósítás (GitHub) a követelményekhez, de nem normatív.

---

## 1. Hatókör és fogalmak

A követelmények CIC általános döntési és bizonyíték-modelljének részei, nem csak CI/CD-szabályok. Bármely rendszerre vonatkoznak, amelyben egy **kibocsátó** egy **tárgyra** vonatkozó **döntést** hoz, és egy **fogyasztó** ezt a döntést egy későbbi, következményekkel járó műveletnél (például egyesítés, kiadás, végrehajtás) felhasználja.

| Fogalom | Jelentés |
|---|---|
| **Tárgy** (subject) | Amit a döntés minősít (például egy változáskészlet egy adott állapotban). |
| **Bemenet** (input) | Minden adat, amelyből a döntés születik: a tárgy tartalma, a policy, az összehasonlítási alap. |
| **Policy** | A döntés szabályait és paramétereit rögzítő, azonosítható adat. |
| **Ellenőrző** (checker) | A bemenetből a döntést előállító, azonosítható implementáció. |
| **Kibocsátó** (issuer) | Az az identitás, amely a döntést közli. |
| **Döntés** (decision) | A kibocsátó által közölt ítélet (például elfogad / elutasít) a hozzá tartozó **bizonyíték-rekorddal**. |
| **Fogyasztó** (consumer) | Az a komponens, amely a döntést felhasználva következményes műveletet enged vagy tilt. |
| **Állapot-négyes** (state tuple) | `T = (S, B, P, C)`: **S** a tárgy azonosítója (például HEAD), **B** az összehasonlítási alap azonosítója (például BASE), **P** a policy tartalom-digestje, **C** az ellenőrző implementációjának digestje. |
| **Hiteles** | A bizonyíték tényleg attól az identitástól származik, amelynek tulajdonítják. |
| **Érvényes** | A bizonyíték a fogyasztás pillanatában is arra az állapotra vonatkozik, amelyre a fogyasztó a műveletet végzi. |

Alapelv: **a hiteles bizonyíték nem feltétlenül érvényes bizonyíték.** A három követelmény külön-külön szükséges, és egyik sem pótolja a másikat (5.4 szakasz).

Kulcsszavak: a MUST / MUST NOT a követelmény kötelező voltát jelzi, a SHOULD az indokolt eltérést megengedő ajánlást. A követelmény-azonosítók (R-I, R-V, R-C) stabil hivatkozási pontok.

---

## 2. R-I: Kibocsátói hitelesség

> A döntést csak arra feljogosított, ellenőrizhető identitás bocsáthatja ki.

| Azonosító | Követelmény |
|---|---|
| R-I.1 | A fogyasztónak MUST ellenőriznie, hogy a döntést kibocsátó identitás a feljogosított kibocsátók halmazába tartozik, **a döntés fogadásakor és a következményes művelet felhasználási pillanatában is** (R-I.7). |
| R-I.2 | A feljogosítottság és a kibocsátó azonosítása MUST olyan tulajdonságon alapulni, amelyet a tárgy szerzője nem tud előállítani vagy módosítani. Az azonosító, amelyet a döntés vagy a tárgy maga állít (például egy név vagy felirat), önmagában nem elegendő. |
| R-I.3 | Az identitás ellenőrzése MUST a fogyasztó oldalán, a kibocsátótól független ponton történjen. A kibocsátó önbevallása nem bizonyíték. |
| R-I.4 | A feljogosított kibocsátók halmaza (és annak módosítása) MUST ugyanolyan védelem alatt álljon, mint a policy (R-V.2): a tárgy szerzője nem módosíthatja. |
| R-I.5 | A feljogosított kibocsátó hiánya (nem elérhető, érvénytelen, nem azonosítható) MUST negatív kimenetet adjon: pozitív döntés nem létezhet. A hiány nem azonos a „nincs ellenkező döntés"-sel. |
| R-I.6 | Azonos tartalmú vagy azonos nevű döntés, amelyet nem feljogosított identitás bocsátott ki, MUST NOT helyettesítheti a feljogosított kibocsátó döntését. |
| R-I.7 | **Visszavonás és felfüggesztés.** A feljogosítottság **időben változó** tulajdonság. Ha a kibocsátó jogosultságát a döntés kibocsátása után, de a felhasználás előtt visszavonták vagy felfüggesztették, a döntés **történeti bizonyítékként megmarad** (nem törlendő, nem hamis), de a következményes művelet engedélyezésére MUST NOT használható; a művelethez új döntés kell feljogosított kibocsátótól. Ha a kibocsátó jogosultsági állapota a felhasználás pillanatában nem állapítható meg, a kimenet negatív (fail-closed). A jogosultság helyreállítása a visszavonás vagy felfüggesztés ideje alatt kibocsátott (vagy akkor jogosulatlan kibocsátótól származó) döntést MUST NOT visszamenőleg érvényesíti; a helyreállított kibocsátó döntését az aktuális felhasználáskor R-I.1 és R-V újra értékeli. |

**Ami nem része ennek a követelménynek:** hogy a feljogosított kibocsátó döntése helyes-e (ezt R-V és R-C, valamint az ellenőrző helyessége fedi), és hogy a kibocsátó kulcsa vagy tokenje milyen csatornán sérülhet (nyitott kérdés, 7. szakasz).

---

## 3. R-V: Döntési érvényesség

> A döntés kötődjön az ellenőrzött állapothoz, az alkalmazott policyhoz és az ellenőrző implementációjához. Bármelyik változása esetén az érvényességet újra kell értékelni.

### 3.1 Kötés

| Azonosító | Követelmény |
|---|---|
| R-V.1 | Minden döntés bizonyíték-rekordja MUST tartalmazza az állapot-négyest `T_d = (S, B, P, C)` mind a négy elemével. Hiányzó elem esetén a döntés érvénytelen. |
| R-V.2 | A policy (P) és az összehasonlítási alap (B) forrása MUST olyan, amelyet a tárgy szerzője a döntés idején nem módosíthat. |
| R-V.3 | A rekordnak azt az állapotot MUST rögzítenie, amelyből a döntés ténylegesen született (**használt = közölt**). Az olyan megvalósítás, amelyben a közölt `T_d` és a ténylegesen felhasznált bemenetek eltérhetnek, nem felel meg R-V.3-nak (lásd 7.2). |

### 3.2 Ellenőrzés: a rögzítés nem érvényesség

A digest rögzítése önmagában **nem** bizonyítja az érvényességet. Az érvényességhez az alábbi ellenőrzés MUST megtörténjen.

| Azonosító | Követelmény |
|---|---|
| R-V.4 | **Ellenőrzési pont.** A fogyasztó a következményes művelet előtt, azzal egy ellenőrzésben MUST összevesse a döntés `T_d` négyesét az aktuális `T_now` négyessel. |
| R-V.5 | **`T_now` forrása.** A `T_now` elemeit a fogyasztó MUST a hiteles forrásból, a kibocsátótól függetlenül számolja vagy olvassa (S és B a tárgy és az alap aktuális állapota; P a policy forrásának aktuális tartalma). A kibocsátó közölte érték nem szolgálhat `T_now`-ként. |
| R-V.6 | **Az ellenőrző azonosságának kötése (C).** A `T_d.C` elemet a fogyasztó MUST egy **elvárt ellenőrző-digesttel** vesse össze, amelynek forrása független a kibocsátott döntéstől és a tárgy szerzőjétől. Az ellenőrző saját maga által közölt digestje önmagában körkörös, ezért nem elégséges (lásd 7.1). |
| R-V.7 | **Egyezés:** az állapotkötés akkor áll fenn, ha `T_d.S = T_now.S`, `T_d.B = T_now.B`, `T_d.P = T_now.P` és `T_d.C = elvárt C`. Az egyezés **szükséges, de nem elégséges**: az állapotkötés érvényességét igazolja, a döntés elfogadhatóságát nem (lásd 4.1). |

### 3.3 Eltérés következménye

| Azonosító | Követelmény |
|---|---|
| R-V.8 | Bármelyik elem eltérése esetén a döntés MUST érvénytelennek minősüljön, és a következményes művelet MUST NOT engedélyezett legyen a régi döntésre hivatkozva. Az érvénytelen döntés **nem negatív döntés** (nem „elutasítva"), hanem **hiányzó érvényes döntés**: a művelet blokkolt, amíg érvényes döntés nem készül. |
| R-V.9 | Az érvénytelenítés után a művelet engedélyezéséhez MUST új döntés szülessen az aktuális `T_now`-ra. Korábbi döntés újrahasználata, vagy a változás kézi felülbírálata nem helyettesíti ezt. |
| R-V.10 | Ha a `T_now` valamely eleme nem állapítható meg (hiteles forrás nem elérhető), a következmény ugyanaz, mint az eltérésnél (fail-closed): a művelet blokkolt. |
| R-V.11 | **Az állapotkötésnek a művelet végrehajtásakor is fenn MUST állnia.** Az R-V.4 ellenőrzés és a következményes művelet közti időablakot a megvalósításnak MUST lezárnia (a művelet atomikusan az ellenőrzött állapothoz kötött, vagy a művelet pillanatában ismételt, azzal egy lépésben végzett ellenőrzés). Ha ez nem garantálható, a megvalósítás megfelelősége az R-V.11-re **PARTIAL / OPEN**, és az ilyen döntés **önmagában nem jogosíthat fel végrehajtásra**: a maradék ablak dokumentálása nem teljesíti a követelményt, csak a hiányt rögzíti (lásd 7.2). |

### 3.4 Jóváhagyás és érvényesség

| Azonosító | Követelmény |
|---|---|
| R-V.12 | Az emberi jóváhagyás **felhatalmazás**, nem a döntés felülbírálata: a jóváhagyott tárgynak a megfelelőségi ellenőrzésen is át kell mennie. A jóváhagyás szintén egy konkrét állapothoz kötött (a tárgy azonosítója és a védett változás digestje), és állapotváltozásra érvénytelen. |

---

## 4. R-C: Bemeneti teljesség

> Hiányos vagy nem igazolhatóan teljes bemenetből pozitív döntés nem születhet.

| Azonosító | Követelmény |
|---|---|
| R-C.1 | Az ellenőrzőnek MUST **bizonyíthatóan** megállapítania, hogy a feldolgozott bemenet az **elvárt bemeneti halmaz** teljes egésze, a bemenet forrásának önbevallásától függetlenül. A bizonyíték az elvárt halmaz tartalmára (nem csak a méretére) vonatkozik. A darabszám-egyezés **önmagában nem elegendő** (egy elem hiányozhat, miközben egy másik duplikálva szerepel, és a darabszám változatlan), csak egy lehetséges részmechanizmus; olyan mechanizmus is megfelel, amely az elemkészlet azonosságát igazolja (például az elemek és az elvárt halmaz egyezése, vagy a halmaz hiteles összegző digestje). |
| R-C.2 | Ha a teljesség nem állapítható meg, vagy a bemenet hiányos, az ellenőrzőnek MUST negatív kimenetet adnia, külön azonosítható okkal (a mért megvalósításban `INCOMPLETE_CHANGESET`). Pozitív döntés nem születhet. |
| R-C.3 | Az ellenőrző nem támaszkodhat arra, hogy a bemeneti forrás hibát jelez. Az olyan forrás, amely a korlátjánál csendben csonkít, megengedett, ha az ellenőrző a csonkolást a teljességvizsgálatból felismeri. |
| R-C.4 | **Forráskorlát:** ha a forrás ismert korlátja (például maximálisan visszaadható elemszám) elérésekor a forrás csonkíthat, a teljességet a korlát elérése nem igazolja; a kimenet negatív, **hacsak a teljesség más, hiteles mechanizmussal nem igazolható**. A korlát elérése önmagában nem általános elutasítási ok: a konkrét küszöb (például a scratch ellenőrző 3000-es határa) a megvalósítás tulajdonsága, nem a követelményé. |
| R-C.5 | A bemenet beolvasása közben bekövetkező hiba (lapozási hiba, átmeneti hiba, a tárgy mozgása) MUST negatív kimenetet adjon; részeredményből pozitív döntés nem születhet. |
| R-C.6 | A teljességvizsgálat maga is az ellenőrző része: a változása a `C` digestet változtatja (R-V), ezért a teljességvizsgálat gyengítése érvényességi eltérésként jelenik meg. |

### 4.1 Együttes teljesülés (R-X)

| Azonosító | Követelmény |
|---|---|
| R-X.1 | Egy döntés a következményes művelet engedélyezésére akkor fogadható el, ha **R-I, R-V és R-C együttesen** teljesül a felhasználás pillanatában. Egyik követelmény teljesülése sem pótolja a másikét (5.4). |
| R-X.2 | A három követelmény teljesülése **nem bizonyítja az ellenőrző szemantikai helyességét**: az állapot-négyes egyezése azt mutatja, hogy *ugyanaz* az ellenőrző döntött, nem azt, hogy az *helyesen* döntött. Az ellenőrző helyességét külön bizonyíték (például megfelelőségi és hibabeültetéses tesztek) igazolja, ez e specifikáció hatókörén kívül esik. |

---

## 5. Megfelelési leképezés (tájékoztató, nem normatív)

### 5.1 Alapelv

A követelmények nem neveznek meg technológiát. Ez a szakasz csak azt rögzíti, hogy a mért GitHub-megvalósítás melyik követelményhez melyik eszközzel viszonyul, és mi hiányzik. A mért részletek a 6. szakaszban vannak.

### 5.2 Leképezés

| Követelmény | GitHub-megvalósítási eszköz (jelölt) | Státusz |
|---|---|---|
| R-I | A kötelező státusz-ellenőrzés a dedikált GitHub App identitásához kötve (`integration_id`) | Mért (scratch), 6.1 |
| R-V (S, B) | `strict_required_status_checks_policy: true` (elavult zöld nem fogadható) | Mért (scratch), 6.2 |
| R-V (P, C kötés, R-V.1–R-V.7) | Check-run kimenetbe írt digest, rögzített checkout | **Nyitott / javasolt**, 7.2, 8 |
| R-C | `changed_files` és a listázott fájlok összevetése, fail-closed | Mért (scratch), 6.3 |

### 5.3 Ami nincs a követelmények között

A ruleset, az Actions, az App és a `pull_request_target` nem követelmény. Ha egy másik platform ugyanezt más eszközzel teljesíti, a követelmények változatlanok.

### 5.4 A három követelmény viszonya (nem helyettesítik egymást)

| Ha csak ez teljesül | Mi marad védetlen | Mért ellenpélda |
|---|---|---|
| R-I (hiteles kibocsátó) | Elavult vagy hiányos bemenetből hiteles pozitív döntés | C2b, C2c (érvényesség), PR37 (teljesség) |
| R-V (érvényes) | Hamis kibocsátó érvényesnek látszó állapotra hivatkozik | A1, E3s |
| R-C (teljes bemenet) | Hamis kibocsátó vagy elavult döntés | A1, E3s, C2b, C2c |

---

## 6. Már méréssel igazolt tulajdonságok

**Minden tétel scratch repóra vonatkozik** (`CentralInfraCore/cic-scratch-212-public`, dedikált App `cic-integrity-scratch`). **Nem éles védelem.** Forrás: `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md`; a nyers bizonyíték `output/raw/app/` alatt.

### 6.1 Kibocsátói hitelesség (R-I)

| Mért tulajdonság | Eset | Korlát |
|---|---|---|
| Az `integrity` ellenőrzés `integration_id` 5852604-hez kötve: az Actions-job által küldött azonos nevű zöld check a merge-hez nem elegendő (`blocked`) | A1 (PR25) | A „blocked" ok-okozata kontrasztra épül, más szabály izolált hatása nincs mérve |
| A kibocsátó tokenhibája (hiányzó `app-id`) mellett a hamis Actions-check nem pótolja az App-checket | A2 (PR26) | Tokenhiba; **az installáció felfüggesztése nem mért** |
| Hamis commit status sem helyettesíti az App check-runt | E3s (PR36) | – |
| Az eredeti Actions-only kötésnél a hamis zöld elfogadott volt (`clean`) | R3, PR21 | ellenpélda, a korábbi állapot |

### 6.2 Döntési érvényesség (R-V)

| Mért tulajdonság | Eset | Korlát |
|---|---|---|
| `strict: false` mellett a régi zöld elfogadott BASE-változás után (`clean`) | C2b | ellenpélda |
| `strict: false` mellett a régi zöld elfogadott policy-változás után | C2c | ellenpélda |
| `strict: true` mellett ugyanez `behind`, vagyis a régi döntés nem elég | C2 (PR31, PR34) | Csak a GitHub által látott BASE/HEAD mozgást fedi; **a külső policy-változás változatlan HEAD és BASE mellett nem mért** |
| A jóváhagyás felhatalmazás, nem felülbírálat: jóváhagyás mellett a nem megfelelő változás is elutasított | A4/A5 (PR29, PR30) | – |

### 6.3 Bemeneti teljesség (R-C)

| Mért tulajdonság | Eset | Korlát |
|---|---|---|
| **Eredeti hiba:** 3002 fájlos PR-nél a files API 3000 fájlt adott, a védett fájl kimaradt, hamis SUCCESS | PR37 | ellenpélda (az eredeti bizonyíték megőrizve) |
| Javított ellenőrző: 2999 fájl SUCCESS; 3000, 3001 DENY; 5 fájl SUCCESS; PR37 újranyitva DENY | PR40–PR43, PR37 | Valós Actions-futás; a hibaágak (eltérés, lapozás, API-hiba) csak **lokális mock**. A 3000-es küszöb a scratch megvalósítás tulajdonsága; a listázott fájlok és a `changed_files` számláló egyezése darabszám-alapú részmechanizmus, **a hiányzó+duplikált elem esetet nem mértük** (N6) |
| A védett útvonalról átnevezés a régi és az új nevet is vizsgálja | PR28 (A6), PR22 | A6-nál a `verify` is bukott, az App-check önálló hatása nem izolált |

---

## 7. Nyitott kérdések

Egyik sem tekinthető igazoltnak. A teljes, 11 tételes lista a mérési jelentés 7. szakasza; itt azok, amelyek a normatív követelményeket közvetlenül érintik, kiegészítve az e specifikáció által felvetett kérdésekkel.

### 7.1 A spec által felvetett új kérdések

| # | Kérdés | Érintett |
|---|---|---|
| N1 | **Az elvárt ellenőrző-digest (R-V.6) bizalmi horgonya.** Honnan származik az elvárt `C`, hogy független legyen a kibocsátótól és a tárgy szerzőjétől? Ha az ellenőrző saját magát igazolja, az körkörös. | R-V.6 |
| N2 | **Ki végzi az R-V.4 ellenőrzést, és hol.** A fogyasztó (a platform merge-kapuja) mit tud összevetni; ha a platform csak a kibocsátó közölte adatot látja, az R-V.5 teljesíthető-e egyáltalán platformon belül. | R-V.4, R-V.5 |
| N3 | **A policy (P) pontos határa.** Mi tartozik a policyhoz (a policy fájl, a védett halmaz, az `approvers` lista, a feljogosított kibocsátók halmaza); a digest mit fed le. | R-V.1, R-I.4 |
| N4 | **Az érvénytelenítés megvalósítása.** R-V.8 szerint az érvénytelen döntés hiányzó döntés. Hogyan válik ez a platformon blokkoló állapottá anélkül, hogy az új döntés automatikusan újra kibocsátódna (és ezzel a felülbírálás útja nyílna meg). | R-V.8, R-V.9 |
| N5 | **Digest-kanonizálás.** Mit jelent a tartalom-digest a policy és az ellenőrző esetében (kanonikus bájtsorrend, többfájlos implementáció, függőségek). Az ellenőrző digestje fedi-e a függőségeit és a futtatókörnyezetet. | R-V.1, R-V.6 |
| N6 | **Darabszámon túli teljességigazolás (R-C.1).** A scratch ellenőrző a listázott fájlok és a `changed_files` számláló egyezését vizsgálja; hiányzó és duplikált elem azonos darabszám mellett nem mért. Milyen hiteles mechanizmus igazolja az elemkészlet azonosságát (R-C.1), és mikor teszi lehetővé a forráskorlát feletti elfogadást (R-C.4). | R-C.1, R-C.4 |
| N7 | **Jogosultság-visszavonás időzítése (R-I.7).** Hogyan állapítható meg a kibocsátó aktuális jogosultsága a felhasználás pillanatában, és mi a következmény, ha ez a platformon nem lekérdezhető (az installáció felfüggesztése nem mért, 7/1). | R-I.1, R-I.7 |

### 7.2 A mérési jelentés 7. szakaszából, a követelményekkel összekötve

| Jelentés § | Nyitott eset | Érintett követelmény |
|---|---|---|
| 7/1 | App-kiesés teljes köre: az **installáció felfüggesztése** (csak a tokenhiba mért) | R-I.5 |
| 7/2 | Fork-PR és második identitás | R-I.1–R-I.3 |
| 7/3 | E0: a tényleges token-hatókör túlnyújtási kísérlete | R-I.2, R-I.4 |
| 7/2 (E1/E2) | A kulcs és a token további csatornái (E1 csak részben, E2 nem bizonyított) | R-I.2 |
| 7/4 | E3 további bemenetek: újsor-tartalmú fájlnév és digest-ütköztetés; szimbolikus link jóváhagyással; policy-parser hiba Actions-ben | R-C.2, R-C.5, R-V.12 |
| 7/5 | Teljességi hibák Actions-beli esete (eltérés, lapozás, API-hiba): csak lokális mock | R-C.2, R-C.5 |
| 7/6 | **TOCTOU és állapotkötés (4/d PARTIAL / OPEN):** a checkout az aktuális alapágat veszi a job idején, miközben a közölt BASE SHA az eseményből jön; a policy digest nincs a check-run kimenetében | **R-V.1, R-V.3, R-V.11** |
| 7/7 | A `strict: true` korlátja: külső policy-változás változatlan HEAD és BASE mellett | R-V.5, R-V.7 |
| 7/8 | Az újrafuttatás jogosultsága mint döntési jogosultság | R-I.1, R-V.9 |
| 7/9 | A `blocked` állapot szabályonkénti izolálása | R-I (mérési bizonyosság) |
| 7/10 | Relay-specifikus esetek (GATE/BOOTSTRAP, védett halmaz teljessége, job-törlés, Renovate, bootstrap, Relay-beli `strict`) | R-I, R-V, R-C |
| 7/11 | A code-owner szabály korábbi diagnosztizálatlan viselkedése, `default_workflow_permissions` eltérés | R-I |

---

## 8. Javasolt, de még nem igazolt megoldások

**Egyik sem mért védelem. Nem része a követelményeknek, nem tekinthető igazoltnak.** Mindegyik külön scratch méréssel és review-val igazolandó, mielőtt bármilyen éles konfiguráció szóba kerülne.

| # | Javaslat | Melyik követelményt szolgálja | Mi hiányzik az igazoláshoz |
|---|---|---|---|
| J1 | A checkoutot a közölt BASE SHA-ra rögzíteni (nem a mozgó alapágra) | R-V.3 (használt = közölt) | Scratch mérés: az alapág a job közben elmozdul, a döntés a közölt SHA-ból születik-e |
| J2 | A policy digestet és az ellenőrző digestet a check-run kimenetében közölni (HEAD és BASE mellett) | R-V.1 | Scratch mérés; a közlés önmagában nem érvényesség (lásd J3) |
| J3 | Független ellenőrzési lépés, amely a közölt `T_d`-t a hiteles forrásból számolt `T_now`-val összeveti, eltérésnél blokkol | R-V.4–R-V.8 | Hol fut (N2), mi a horgony (N1); mérés: a policy- és ellenőrző-változás elutasítva |
| J4 | Az elvárt ellenőrző-digest a védett alapágból olvasva, nem a tárgyból és nem a kibocsátóból | R-V.6 | N1 megoldása; bootstrap-kérdés (az ellenőrző első telepítése) |
| J5 | A feljogosított kibocsátók halmazának és az ellenőrző digestnek ugyanolyan védelem alá helyezése, mint a policy | R-I.4, R-V.2 | N3 szerinti határ |
| J6 | Az Actions-beli teljességi hibaágak mérése valós futásban (a mock helyett) | R-C.5 | Scratch mérés |
| J7 | Az installáció felfüggesztésének mérése | R-I.5 | A privát kulcs használata (tulajdonosi lépés) |

---

## 9. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A három követelmény külön-külön szükséges, egyik sem pótolja a másikat | Mért (ellenpéldák), scratch | A1/E3s, C2b/C2c, PR37 (6. szakasz) | A mérési jelentés 1. és 3. szakasza, `raw/app/` | Csak a mért esetekre; Relay-ben nem igazolt |
| Az App-identitáshoz kötött kötelező ellenőrzés elutasítja a hamis Actions-checket | Mért, scratch | PR25, PR26, PR36 | `raw/app/`, jelentés 3.1 | Installáció-felfüggesztés nem mért |
| A `strict: true` a régi zöldet a BASE/HEAD-mozgásra elutasítja | Mért, scratch | PR31, PR34 | Jelentés 3.3 | Külső policy-változás nem fedett |
| A fail-closed teljességvizsgálat a 3000-es korlátnál DENY, 2999-nél SUCCESS | Mért, scratch (valós Actions) | PR40, PR41, PR42, PR43 | Run ID-k a jelentésben | A hibaágak csak lokális mock |
| A digest rögzítése nem bizonyítja az érvényességet | Normatív állítás (3.2) | Ez a specifikáció; a 3.6 jelentés-szakasz mutatja a hiányt | Tartalmi review | – |
| A közölt BASE SHA és a ténylegesen használt checker/policy azonossága | **Nem igazolt (PARTIAL / OPEN)** | Jelentés 3.6, `raw/app/integrity-app.yml.txt` | Scratch mérés (J1–J3, külön lépés) | A rés a mért megvalósításban fennáll |
| Az ellenőrző-digest bizalmi horgonya megoldható | **Nem igazolt** | – | N1 | Körkörösség, bootstrap |
| A GitHub App, a ruleset és az Actions megfelelő megvalósítási eszköz | Részben mért (R-I, R-V S/B, R-C), tájékoztató | 5.2 szakasz | – | R-V P/C kötése még nincs |

---

## 10. Mit nem állít ez a dokumentum

- Nem állítja, hogy a Relay védett; a mérések scratch repóban készültek.
- Nem tekinti a javasolt megoldásokat (8. szakasz) igazoltnak.
- Nem dönt a Relay-implementációról, az éles beállításról vagy a #212 lezárásáról (HOLD).
- Nem osztályozza és nem priorizálja a nyitott eseteket; ez a következő lépés.
- A digest-eket (R-V) nem tekinti elégségesnek a rögzítésük miatt; az érvényesség ellenőrzéssel és az eltérés következményével áll (3.2, 3.3).
