# A policy normatív határa (N3)

Státusz: **specifikációs tervezet felülvizsgálatra.** Nem mérés, nem implementáció, nem döntés a Relay beállításairól.

Ez a dokumentum a `decision-requirements-spec.md` (R-I, R-V, R-C, R-X) **N3** nyitott kérdését zárja javaslatként, és pontosítja az R-V.1, R-V.2 és R-I.4 követelményeket. A digest képzésének konkrét szabályai (kanonizálás, tesztvektorok) az **N5** munkacsomag tárgya; itt csak a *logikai határ* van meghatározva: mi tartozik az állapotkötésbe, és mi nem.

A dokumentum részei élesen elkülönülnek:

| Rész | Szakasz | Jelleg |
|---|---|---|
| Normatív határ | 1–5 | Technológiafüggetlen követelmény. Megvalósítási eszközt nem nevez meg. |
| Scratch osztályozási példa | 6 | Elemzés: a mért scratch megvalósítás tényezőinek besorolása. **Nem mérés.** |
| Nyitott kérdések | 7 | Nem eldöntött. |
| Javasolt, nem igazolt megoldás | 8 | Sem követelmény, sem mért. |

---

## 1. Alapelv és az osztályozási teszt

> **Döntést befolyásoló tényező nem maradhat az állapotkötésen kívül.**

| Azonosító | Követelmény |
|---|---|
| R-P.1 | Minden **döntést befolyásoló tényezőnek** (DBT) az állapotkötésen belül MUST lennie: vagy az állapot-négyes egyik elemében, vagy a használat pillanatában kötelezően értékelt (nem gyorsítótárazott) tényezőként (R-P.12). Olyan DBT, amely sem a kötésben, sem a használati értékelésben nincs, nem megengedett. |
| R-P.2 | **Osztályozási teszt.** Egy tényező DBT, ha a többi tényező változatlansága mellett az ő megváltozása a döntés kimenetét, az indokolását vagy a döntés felhasználhatóságát megváltoztathatja. A tesztet az ellenőrző *viselkedésére* kell alkalmazni, nem a szándékolt szerepére: ami az ellenőrző számára olvasott bemenet, az DBT, akkor is, ha dokumentációnak szánták. |
| R-P.3 | **Kihagyás csak indoklással.** Egy tényező kizárása a kötésből MUST megnevezett és indokolt legyen (5. szakasz). A fel nem sorolt tényező alapértelmezésben **belül** van, nem kívül. |

---

## 2. Az állapotkötés elemei és határuk

Az állapot-négyes `T = (S, B, P, C)` elemeinek határa az alábbi.

| Elem | Mi tartozik bele |
|---|---|
| **S** (tárgy) | Az ítélet tárgya, azonosítva. A tárgyból az ellenőrző által levezetett reprezentációk (például a tárgy változáskészlete) a tárgy *képei*; a tárgy azonosítója köti őket, a levezetés módja C része, a levezetés forrásadata külső bemenet (R-P.5). |
| **B** (alap) | Az összehasonlítás alapja, azonosítva. |
| **P** (hatályos policy) | Az **effektív, feloldott** policy: az ellenőrző által a döntés pillanatában ténylegesen alkalmazott deklaratív szabályok és paraméterek összessége, az öröklés, a külső forrás és az alapértelmezés feloldása *után* (2.1). |
| **C** (ellenőrző) | Az ellenőrző implementációja és minden, ami a viselkedését meghatározza (2.2). |

### 2.1 R-P.4: a P tartalma (hatályos policy)

A P a deklaratív, a döntést meghatározó adat. Ide MUST tartozzon:

| P-elem | Megjegyzés |
|---|---|
| a védett halmaz (mit véd a policy) és annak teljessége-definíciója | a védett halmaz *meghatározása*, nem a tagjainak aktuális tartalma (az S) |
| a szabály-paraméterek és küszöbök | minden szám, minta, felsorolás, amelyet az ellenőrző a döntéshez használ |
| a **feljogosított kibocsátók halmaza** (deklarált) | lásd 4. szakasz; az élő jogosultsági állapot nem P |
| a **jóváhagyók halmaza** (deklarált) | lásd 4. szakasz |
| a bemeneti teljesség elvárása | az elvárt bemeneti halmaz definíciója (R-C.1) |
| a policy sémájának és szemantikai verziójának azonosítója | a policy értelmezése verziófüggő |
| a policy **feloldásának eredménye** | az öröklött, külső és alapértelmezett értékek feloldott értéke (2.3) |

### 2.2 R-P.5: a C tartalma

A C az ellenőrző implementációja és minden, amely a viselkedését meghatározza. Ide MUST tartozzon:

| C-elem | Megjegyzés |
|---|---|
| az ellenőrző kódja és a beágyazott állandók | a beágyazott alapértelmezések is |
| a **teljességvizsgálat** logikája | R-C.6: a gyengítése C-változás |
| a policy-feloldás és -összefésülés algoritmusa | a precedencia, az öröklési szabályok *feldolgozása* (a szabályok maguk P) |
| azok a függőségek és futtatókörnyezet-elemek, amelyek a viselkedést befolyásolják | a mélység (a függőségi zárlat határa) az N5/N1 tárgya |
| a tárgy képeit előállító levezetés (például a változáskészlet felsorolása) | a levezetés *módja*; a forrásadata külső bemenet |

### 2.3 R-P.6: külső, örökölt és dinamikus szabályok

A feloldott policy (P) három további forrást foglal magába. Mindháromra érvényes: **a döntéskor ténylegesen alkalmazott érték értékkel (snapshot) része a P-nek**, nem hivatkozásként.

| Forrás | Követelmény |
|---|---|
| **Örökölt szabály** (szülő, alapértelmezett, szervezeti szint) | A feloldott érték a P része; az öröklési forrás azonosítója és verziója rögzített. A forrás megváltozása, amely a feloldott értéket változtatja, P-változás. Ha a forrás megváltozása a feloldott értéket nem változtatja, az nem érvényteleníti a döntést (a feloldott érték az egyetlen mérce). |
| **Külső szabály** (a döntés pillanatában külső forrásból lekért adat) | A lekért érték snapshotként a P része. A forrás MUST feljogosított és a tárgy szerzőjétől független legyen (az R-I szerinti hitelesség adatforrásra is). A lekérés hibája vagy a forrás elérhetetlensége fail-closed (R-V.10). |
| **Dinamikus szabály** (idő- vagy állapotfüggő) | A dinamikus függvény a C része; a bemenete (idő, állapot) külső bemenetként snapshot. Az időfüggő szabály az értékelés idejét és az érvényességi korlátot a döntésben rögzíti; a korláton túl a döntés érvénytelen. |

### 2.4 R-P.7: hiányzó vagy értelmezhetetlen policy

- A hiányzó, értelmezhetetlen vagy a sémának nem megfelelő policy MUST negatív kimenetet adjon (fail-closed). Egy hiányzó érték MUST NOT csendben megengedő alapértelmezésre esni; az alapértelmezés vagy deklarált a P-ben, vagy a C része, és mindkét esetben kötött.
- Egy policy, amelyet az ellenőrző *részben* értelmez (ismeretlen kulcsokat figyelmen kívül hagy), nem teljes értelmezés: az ismeretlen elem a döntésből kimaradó DBT-t jelenthet, ezért az ismeretlen elem negatív kimenetet ad, vagy az ismeretlen elem bizonyítottan nem DBT (R-P.2).

---

## 3. Az érvénytelenítés határa

### 3.1 R-P.8: mely változások érvénytelenítik a korábbi döntést

Egy korábbi döntést érvénytelenít a kötött tényezők bármelyikének megváltozása. A kötés *mechanizmusa* (digest, kanonizálás) az N5 tárgya; itt a **mit** van rögzítve.

| Változás | Érvényteleníti? | Mechanizmus |
|---|---|---|
| S megváltozása | igen | állapotkötés (R-V.7) |
| B megváltozása | igen | állapotkötés |
| P bármely eleme (2.1), beleértve a feloldott értéket | igen | állapotkötés |
| a jóváhagyók vagy a feljogosított kibocsátók **deklarált halmazának** módosítása | igen | P-változás |
| C bármely eleme (2.2) | igen | állapotkötés (R-V.6) |
| a külső forrás snapshotjának megváltozása | igen | P-változás |
| az időfüggő döntés érvényességi korlátjának lejárata | igen | a döntésben rögzített korlát |
| a kibocsátó **élő jogosultsági állapotának** megváltozása (visszavonás, felfüggesztés) | a felhasználhatóságot érinti | használati értékelés (R-I.7), nem kötés |
| a fogyasztó **konfigurációjának** megváltozása | a felhasználást érinti | használati értékelés (R-P.12), nem kötés |
| olyan tényező változása, amely az 5. szakasz kizárási listáján van | nem | indokolt kizárás |

### 3.2 R-P.9: konzervatív érvénytelenítés

Az érvénytelenítés **konzervatív**: egy változás, amelyről nem bizonyítható, hogy nem DBT-t érint, érvénytelenít. Szemantikai ekvivalencián alapuló „ez a változás nem számít" elfogadás csak az N5 szerinti kanonikus alakon belül megengedett; azon kívül nem.

---

## 4. A jogosultságok helye

A kibocsátói és jóváhagyói jogosultságnak két, eltérő természetű rétege van. A kettő nem keverhető.

| Réteg | Mi ez | Hol helyezkedik el | Miért ott |
|---|---|---|---|
| **Deklarált** (ki *jogosult*) | A feljogosított kibocsátók és a jóváhagyók felsorolása | **P** (hatályos policy) | Statikus adat, rögzíthető és kötött; változása érvényteleníti a döntést (3.1) |
| **Élő állapot** (a jogosultság *most is fennáll-e*) | A kibocsátó visszavonásának, felfüggesztésének, a jóváhagyó tagságának aktuális állapota | **Használati értékelés** (R-I.7), nem P | Időben változó; nem rögzíthető egy döntéshez, mert épp az a kérdés, hogy a felhasználás pillanatában fennáll-e |
| **Jóváhagyási aktus** | Egy konkrét jóváhagyás egy konkrét tárgyra | A **tárgy és a védett változás digestjéhez kötött bizonyíték** (R-V.12), nem P és nem policy | A jóváhagyás egy esemény, nem szabály; az állapotváltozásra érvénytelen |

| Azonosító | Követelmény |
|---|---|
| R-P.10 | A deklarált halmazok MUST ugyanolyan védelem alatt álljanak, mint a P többi eleme (R-I.4, R-V.2): a tárgy szerzője a döntés idején nem módosíthatja. |
| R-P.11 | **A policy módosítását a módosítás előtti policy szerint kell megítélni.** Az, hogy ki jogosult a P módosítására, a B-oldali (módosítatlan) policyból jön, nem a módosított változatból: a tárgy szerzője a módosítással nem jogosíthatja fel magát. A P maga a védett halmaz tagja (önkövető védelem). |

---

## 5. Mi nem része a policynak, és miért

Az alábbi tényezők **kívül** vannak a P-n (és a kötésen), indoklással (R-P.3). Minden más tényező belül van.

| Kizárt tényező | Miért nem része | Hol kezelendő |
|---|---|---|
| A **tárgy tartalma** (S) | Az ítélet tárgya, nem a mérce; az S külön elem | S az állapotkötésben |
| A **döntés maga** és a naplói | Az ellenőrző kimenete, nem bemenete; levezetett adat | a bizonyíték-rekord |
| A kibocsátó **hitelesítő adata** (kulcs, token) | Titok: kötése vagy közlése sértené a titkosságát. Az élő jogosultsága használati értékelés | R-I.7; a csatorna-védelem a G3 tárgya |
| A **jóváhagyási aktus** | Esemény, nem szabály | R-V.12 szerinti, tárgyhoz kötött bizonyíték |
| A **fogyasztó kikényszerítési konfigurációja** | A felhasználást szabályozza, nem a döntést hozza; a fogyasztó a használat pillanatában a *mostani* konfigurációt alkalmazza, nem a döntés idejét | R-P.12; védelme a tárgy szerzőjétől külön követelmény (7. szakasz, N3.1) |
| A policyt **magyarázó dokumentáció**, megjegyzés | Csak akkor kizárt, ha az ellenőrző nem olvassa (R-P.2): amit az ellenőrző olvas, az DBT | tájékoztató; az ellenőrző olvasása esetén P |
| A futtatógép **működési állapota** (terhelés, gyorsítótár, időzítés), ha nem befolyásolja a viselkedést | Nem DBT (R-P.2). Ha befolyásolja a viselkedést, C-be tartozik | C |

| Azonosító | Követelmény |
|---|---|
| R-P.12 | A fogyasztó konfigurációját a **használat pillanatában, az aktuális értéken** MUST értékelni; a döntés idejének konfigurációja nem gyorsítótárazható. A konfiguráció védelme a tárgy szerzőjétől MUST fennálljon, mert ha a szerző megváltoztathatja, a kikényszerítés megkerülhető. |
| R-P.13 | **Kötetlen tényező.** Ha egy DBT sem a kötésbe, sem a használati értékelésbe nem helyezhető, a megfelelőség az adott tényezőre **PARTIAL / OPEN**, és az ilyen döntés önmagában nem jogosíthat fel végrehajtásra (R-V.11 és R-X.1 szerint). A kötetlen tényezőt nevesíteni MUST. |

---

## 6. Scratch osztályozási példa (elemzés, nem mérés)

A mért scratch megvalósítás (`raw/app/`, jelentés 3.6) tényezőinek besorolása az 1–5. szakasz szerint. **A besorolás elemzés; a "jelenleg kötött-e" oszlop a jelentésből ismert, nem új mérés.** Ahol a státusz nem ismert, „nem ellenőrzött" áll.

| Tényező | Besorolás | Jelenleg kötött? | Forrás |
|---|---|---|---|
| a policy fájl tartalma (védett halmaz, jóváhagyók, kibocsátó-kötés) | P | A digest a futási logban van, a check-run kimenetében **nem** | jelentés 3.6 |
| az ellenőrző kódja | C | **Nem**: nincs checker-digest a kimenetben | jelentés 3.6, N1 |
| a PR HEAD és a BASE | S, B | Igen (a check-run kimenete közli) | jelentés 3.6 |
| az alapág, amelyből a policy és a checker jön | B-oldali forrás | A checkout az aktuális alapágat veszi, a közölt BASE SHA az eseményből jön (eltérhet) | jelentés 3.6, **PARTIAL / OPEN** |
| a PR változáskészlete (a fájllista) | S képe; a forrásadata külső bemenet | Teljességvizsgálat mért (R-C); a lista snapshotja nem kötött: nem ellenőrzött | jelentés 4.2 |
| a jóváhagyó megjegyzések (jóváhagyási aktus) | R-V.12 szerinti bizonyíték | A megjegyzés formátuma HEAD és digest-kötött (mért: A4/A5) | jelentés 3.2 |
| a jóváhagyók halmaza | P (deklarált) | A policy része, kötése mint a P-é | jelentés 3.2 |
| a kötelező ellenőrzés konfigurációja (melyik ellenőrzés, milyen identitáshoz kötve, `strict`) | fogyasztói konfiguráció, használati értékelés | A fogyasztó aktuális értékét alkalmazza (mért: C2, A1) | jelentés 3.1, 3.3 |
| a kibocsátó élő jogosultsága | élő állapot, használati értékelés | Nem mért (felfüggesztés) | jelentés 7/1, N7 |

**Amit ebből a példa mutat (következtetés):** a scratch megvalósításban a **P digestje és a C digestje a kimenetből hiányzik, és a policy forrása nem garantáltan a közölt BASE-hez tartozik**, ezért R-P.1 szerint a policy és az ellenőrző jelenleg *kötetlen tényező* (R-P.13), a megfelelőség PARTIAL / OPEN. Ez azonos a 3.6 jelentés-szakasz és az N1/N2 megállapításával; itt a határ határozza meg, *mit* kell kötni.

---

## 7. Nyitott kérdések

Az N3 e javaslat elfogadásakor tekinthető lezártnak. A következők az N3 határkijelölésből következő **új** kérdések; nem szerepelnek az N1–N7-ben.

| # | Kérdés | Érintett |
|---|---|---|
| N3.1 | **A fogyasztói konfiguráció védelme.** Ki módosíthatja, és hogyan védett a tárgy szerzőjétől? A kikényszerítés konfigurációja megkerülhető, ha a szerző változtathat rajta. A védelem mechanizmusa nem mért. | R-P.12, R-I.4 |
| N3.2 | **A jóváhagyók deklarált halmaza és az élő tagság időzítése.** Ha a jóváhagyó tagsága a jóváhagyási aktus után szűnik meg, a már rögzített jóváhagyás érvényes marad-e? Az aktus idején fennálló jogosultság rögzítése és a későbbi változás kezelése. | R-P.10, R-V.12, R-I.7 |
| N3.3 | **A külső forrás hitelessége.** Mi teszi egy külső szabályforrást feljogosítottá és a tárgy szerzőjétől függetlenné; hogyan ellenőrizhető az R-I szerint adatforrásra. | R-P.6 |
| N3.4 | **A C mélysége.** A függőségi zárlat és a futtatókörnyezet mely elemei viselkedést befolyásolók (R-P.2), és mi a határ. | R-P.5, N5, N1 |
| N3.5 | **A nem érvénytelenítő változások köre.** Mely P- vagy C-változások bizonyíthatóan nem DBT-t érintenek, és ezért az N5 kanonikus alakján belül nem érvénytelenítenek. | R-P.9, N5 |

Függőségek: az N3 előfeltétele az **N5** tervezési részének és az **N1/N2** döntésnek (a policy határa nélkül nem dönthető el, mit köt a digest és mit olvas a verifier). Az N3.4 és az N3.5 az N5-tel közös; az N3.1 és az N3.3 a G3/G1 tárgya.

---

## 8. Javasolt, de még nem igazolt megoldás

**Nem mért védelem, nem része a követelményeknek.**

| # | Javaslat | Melyik követelményt szolgálja | Mi hiányzik az igazoláshoz |
|---|---|---|---|
| J-P1 | **Hatályos-policy jegyzék** (effective policy manifest): a döntés pillanatában feloldott P minden forrását (fájl, öröklési forrás, külső snapshot, alapértelmezés) felsoroló, forrásonként azonosított jegyzék; a bizonyíték-rekord a jegyzék azonosítóját hordozza | R-P.4, R-P.6, R-V.1 | N5 (az azonosító képzése); scratch mérés, hogy a jegyzékből hiányzó forrás a döntést negatívvá teszi |
| J-P2 | **Kizárási lista** mint a policy része: a kötésből kizárt tényezők felsorolása indoklással, védett, a P-vel együtt kötött | R-P.3 | Szerkezet (N5); review |
| J-P3 | **Az ellenőrző saját policy-teljességi önellenőrzése**: az ismeretlen kulcs vagy forrás negatív kimenet (R-P.7) | R-P.7 | Lokális teszt, majd scratch |
| J-P4 | A P módosításának megítélése a B-oldali policy szerint kikényszerítve (R-P.11) | R-P.11 | Scratch mérés: a PR a saját policyjával jóváhagyót hozzáad, a döntés elutasított |

---

## 9. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A policy határa a feloldott (effektív) policy, nem a policy fájl | Normatív állítás | 2.1, 2.3 | Tartalmi review | A „feloldott érték az egyetlen mérce" az N5-ben kanonizálandó |
| A deklarált jogosultság P-ben, az élő állapot használati értékelésben van | Normatív állítás | 4. szakasz | Tartalmi review | A két réteg határa (N3.2) nincs lezárva |
| A fogyasztói konfiguráció kizárható a kötésből, ha a használatkor értékelt | Normatív állítás | R-P.12, 5. szakasz | Tartalmi review | A konfiguráció védelme nem mért (N3.1) |
| A scratch checker P-je és C-je jelenleg nem kötött a check-run kimenetben | Mért (jelentés) | Jelentés 3.6, `raw/app/integrity-app.yml.txt` | A jelentés és a workflow olvasása | A besorolás (6. szakasz) elemzés |
| A scratch policy forrása a közölt BASE-hez nem garantáltan tartozik | Mért/olvasott, PARTIAL / OPEN | Jelentés 3.6 | A workflow checkout-lépése | Az eltérés bekövetkezése nem mért |
| A jóváhagyás HEAD- és digest-kötött | Mért (scratch) | A4/A5, PR29, PR30 | Jelentés 3.2 | Csak a mért eseteken |
| A külső, örökölt és dinamikus szabályok scratch-beli előfordulása | **Nem ellenőrzött** | — | A scratch policy és checker átvizsgálása (külön lépés) | A 2.3 szakasz követelmény-szintű, a scratch lefedettsége ismeretlen |
| Az N3 az e javaslat elfogadásakor zárható | Javaslat | Ez a dokumentum | Tartalmi review | A 7. szakasz új kérdései (N3.1–N3.5) |
| A javasolt megoldások (J-P1–J-P4) működnek | **Nem igazolt** | — | Scratch mérés (külön lépés) | Nincs mérés |

---

## 10. Mit nem állít ez a dokumentum

- Nem határozza meg a digest képzését, a kanonizálást, a tesztvektorokat (N5).
- Nem dönt az ellenőrzési helyről és a bizalmi horgonyról (N1/N2).
- Nem állítja, hogy a Relay védett; a 6. szakasz scratch osztályozás, nem mérés.
- Nem tekinti a javasolt megoldásokat (8. szakasz) igazoltnak.
- Nem dönt a Relay-implementációról, az éles beállításról, a #212 lezárásáról (HOLD).
