# A bizalmi horgony és az ellenőrzési mechanizmus (N1/N2)

Státusz: **specifikációs tervezet felülvizsgálatra.** Nem implementáció, nem mérés, nem döntés a Relay beállításairól.

Az **N3** (`policy-boundary-spec.md`) rögzítette, *mi* tartozik az állapotkötésbe; az **N5** (`digest-canonicalization-spec.md`), *hogyan* képződnek a digestek. Ez a dokumentum azt rögzíti, **honnan jön az elvárt érték** (N1: a bizalmi horgony) és **ki, hol és mivel veti össze** a közölt és az aktuális állapotot (N2: az ellenőrzési mechanizmus). A kettő együtt dönthető: a független verifier maga is kibocsátó, ezért az R-I szerint rá is vonatkozik a hitelesség, és a regressziónak véges horgonyon kell végződnie.

| Rész | Szakasz | Jelleg |
|---|---|---|
| Normatív: horgony | 2 (R-A.*) | Technológiafüggetlen követelmény. |
| Normatív: mechanizmus | 3 (R-M.*) | Technológiafüggetlen követelmény. |
| A mechanizmusok osztályozása | 4 | A megfelelőségi szintek; nem választ megvalósítást. |
| A scratch megfigyelései | 5 | Olvasás és a mért jelentés; **nem új mérés**. |
| Nyitott kérdések | 6 | Nem eldöntött. |
| Javasolt, nem igazolt megoldás | 7 | Sem követelmény, sem mért. |

---

## 1. Fogalmak

| Fogalom | Jelentés |
|---|---|
| **Fogyasztó / kikényszerítési pont** | Az a komponens, amely a következményes műveletet engedi vagy tiltja. |
| **Kibocsátó** | Az ellenőrző (checker), amely a döntést közli (R-I). |
| **Verifier** | Az a komponens, amely az R-V.4 összevetést végzi: a közölt `T_d` állapot-négyest a hiteles forrásból számolt `T_now`-val veti össze. A verifier lehet maga a fogyasztó, vagy a fogyasztó által megkövetelt, különálló komponens. |
| **Bizalmi horgony** | Olyan elem, amelynek hitelességét nem egy újabb döntés-lánc igazolja, hanem egy, a fogyasztó által a tárgy szerzőjétől és a kibocsátótól függetlenül kikényszerített tulajdonság. |
| **Elvárt-állapot forrás (ES)** | Az a hiteles forrás, amelyből a `T_now` elemei (S, B, P) és az elvárt ellenőrző-digest (`C_exp`) származnak. |
| **Nyilvántartás** (registry) | A `C_exp` (és az elvárt verifier-digest) értékeit hordozó, horgonyvédett adat, a B-oldalon (az alap oldalán), nem a tárgyban. |
| **Bizalmi alap** | Azon elemek nevesített halmaza, amelyeket a megfelelőség nem tud tovább igazolni, ezért elfogadottként nevesít (R-P.13). |

---

## 2. A bizalmi horgony (N1)

### 2.1 A lánc véges és nem önigazoló

| Azonosító | Követelmény |
|---|---|
| R-A.1 | **A bizalmi lánc véges, és horgonyon végződik.** Minden hitelességi állítás (a kibocsátóé, a verifieré, az elvárt digesté) visszavezethető egy **gyökér-horgonyra**. Önigazoló gyökér nem létezik: az az ellenőrző, amely a saját digestjét közli és ez igazolná önmagát, nem horgony (R-V.6). |
| R-A.2 | **A gyökér-horgony tulajdonságai.** A gyökér-horgonynak MUST: **(a)** a tárgy szerzője a döntés idején nem módosíthatja; **(b)** a kibocsátó hitelesítő adatától függetlennek lennie (a kibocsátó kompromittálása nem érinti a horgonyt); **(c)** a kikényszerítést a fogyasztó végezze, nem egy olyan komponens, amelyet a horgony védeni hivatott; **(d)** módosítása megítélt, rögzített és tulajdonítható legyen (R-A.4). |
| R-A.3 | **A gyökér-horgonyok halmaza kicsi, nevesített és nyilvános.** A gyökér-horgonyok a bizalmi alap részei (R-P.13), felsoroltak és indokoltak. Minden, ami nem szerepel a halmazban, nem horgony, hanem a horgonyhoz kötendő elem. |

### 2.2 Az elvárt ellenőrző-digest forrása (`C_exp`)

| Azonosító | Követelmény |
|---|---|
| R-A.4 | **A `C_exp` nyilvántartásból jön.** Az elvárt ellenőrző-digest MUST egy **nyilvántartásból** származzon, amely: **(a)** a B-oldalon van (az alap oldalán), nem a tárgyban és nem a kibocsátó kimenetében; **(b)** a tárgy szerzője számára nem módosítható; **(c)** a módosítása a módosítás **előtti** állapot szerint megítélt (R-P.11 elve), a módosítás szerzőjén **kívüli**, jogosult jóváhagyóval; **(d)** minden bejegyzése az ellenőrző azonosítóját, verzióját és N5 szerinti, címkézett digestjét hordozza; **(e)** minden módosítása rögzített és tulajdonítható. |
| R-A.5 | **Az ellenőrző megváltozása a `C` megváltozása.** Az ellenőrző új implementációjának digestjét MUST a nyilvántartásba **előbb** be kell jegyezni (R-A.4), mielőtt az új ellenőrző döntései elfogadottak lennének. Olyan döntés, amelynek `C`-je nincs a nyilvántartásban, érvénytelen (R-V.6, R-V.7). |
| R-A.6 | **Az új `C_exp` bejegyzése megfelelőségi bizonyítékhoz kötött.** A bejegyzés előfeltétele az új ellenőrző megfelelőségi bizonyítéka (R-X.2): a hibabeültetéses és konformanciateszt-készlet lefutása. A digest kötése az *azonosságot* igazolja, nem a *helyességet*; a helyességet külön bizonyíték igazolja, és a jóváhagyás önmagában nem helyettesíti. |

### 2.3 Telepítés (bootstrap) és forgatás

| Azonosító | Követelmény |
|---|---|
| R-A.7 | **A telepítés kimondott, egyszeri eseménye.** A kezdeti horgony beállítása az az **egyetlen** alkalom, amikor az elvárt érték a megelőző állapot szerinti megítélés nélkül kerül be. Ennek MUST: **(a)** névvel megjelölt, tulajdonítható, rögzített, a feljogosított tulajdonosi hatóság által végzett esemény lennie; **(b)** a kezdeti `C_exp`-et **független újraképzéssel** ellenőrizni: a digestet az ellenőrző forrásából egy, a szerzőtől független második fél újraképzi (R-D.19, R-D.20); **(c)** a bizalmi alap részeként nevesíteni (R-A.3). A telepítés elhallgatása nem megfelelő. |
| R-A.8 | **Forgatás és helyreállítás.** A horgony elemeinek (a `C_exp`, a feljogosított kibocsátók és verifierek halmaza, a gyökér-horgony hitelesítő adatai) cseréjére, visszavonására és kompromittálás utáni helyreállítására MUST legyen előírt eljárás: **(a)** a visszavont elem alatt kibocsátott döntés a visszavonás után nem használható fel (R-I.7); **(b)** a helyreállítás nem érvényesíti visszamenőleg a jogosulatlan időszakban kibocsátott döntést; **(c)** a kompromittálás és az észlelése közti időszak kezelése nyitott (N8-jelölt, 6. szakasz). |

---

## 3. Az ellenőrzési mechanizmus (N2)

### 3.1 Szerepek és függetlenség

| Azonosító | Követelmény |
|---|---|
| R-M.1 | **A verifier nem lehet a vizsgált tárgy saját verifiere.** A verifier MUST NOT lehessen definiálva, futtatva, konfigurálva vagy módosítva a tárgy által (a tárgy szerzője a döntés idején nem alakíthatja). A tárgy **adat** a verifier számára: a verifier a tárgy tartalmát soha nem hajtja végre. (A #213 elve; a #213 külön lépés, itt csak az elv.) |
| R-M.2 | **A verifier maga is R-I alá esik.** A verifier identitása feljogosított és ellenőrizhető (R-I.1–R-I.3), a verdikt a verifier döntése: a verifier állapot-négyese (`T_v`) kötött, az elvárt verifier-digestje a nyilvántartásban van (R-A.4). A regresszió a gyökér-horgonyon véget ér (R-A.1). |
| R-M.3 | **Szerepek függetlensége.** A kibocsátó és a verifier **közös hibaforrás nélküli**: nem közös hitelesítő adat, nem közös kódellátási út (forrás, összeállítás, kiadás), nem közös konfiguráció. Az egyik kompromittálása MUST NOT érintse a másikat. Ha a függetlenség nem garantálható, a megfelelőség PARTIAL / OPEN, és az ilyen döntés önmagában nem jogosít fel végrehajtásra (R-P.13). |

### 3.2 Az összevetés

| Azonosító | Követelmény |
|---|---|
| R-M.4 | **A `T_now` a verifier saját számítása.** A verifier a `T_now` minden elemét a hiteles forrásból, a kibocsátótól függetlenül számolja vagy olvassa (R-V.5): az S és B az alap és a tárgy hiteles tárolójából; a P a B-oldali policy-forrásból, a verifier saját feloldásával (R-P.4, R-P.6); az elvárt `C` a nyilvántartásból (R-A.4). A kibocsátó közölte érték nem lehet a `T_now` forrása. |
| R-M.5 | **Az összevetés.** A verifier a `T_d`-t a `T_now`-val az R-V.7 szerint veti össze, az N5 szerinti kanonizálás és címkézés szerint (R-D.19). A külső bemeneteket az R-P.14 szerinti ellenőrzéssel kezeli. |
| R-M.6 | **Az érvényességi verdikt kötött.** A verifier a verdiktet saját rekordban közli, amely hordozza a **saját maga számította** `T_now`-t és a kibocsátó döntésének azonosítóját. A verdikt csak arra az állapotra érvényes, amelyre számolták (R-V.4, R-V.11). A fogyasztó MUST megkövetelje **mind** a kibocsátó döntését, **mind** a verifier érvényességi verdiktjét, ugyanarra az állapotra. |

### 3.3 Elem szerinti ellenőrző

| Azonosító | Követelmény |
|---|---|
| R-M.7 | **Az ellenőrzés helye elemenként.** (a) Az **S és B** összevetésére a fogyasztó natív kötése elegendő lehet, ha igazolt, hogy a fogyasztó a tárgy és az alap elmozdulását a művelet pillanatában ellenőrzi (R-V.11). (b) A **P és C** összevetését a fogyasztó natívan nem végzi, hacsak igazolt, hogy képes rá; ilyenkor MUST **független verifier** végezze (4. szakasz, M1 vagy M2). (c) A kibocsátó **önellenőrzése** a P-re és a C-re **nem megengedett**, mert körkörös (R-A.1). |

### 3.4 Hibakezelés és használatkor-értékelés

| Azonosító | Követelmény |
|---|---|
| R-M.8 | **Fail-closed.** Ha a verifier nem elérhető, hibázik, vagy a `T_now` valamely eleme nem állapítható meg, **nincs érvényes érvényességi verdikt**, a művelet blokkolt (R-V.10). Ez az R-V.8 szerinti hiányzó érvényes döntés, nem elutasítás (az N5 `NO-DECISION` fogalma). |
| R-M.9 | **Használatkor-értékelés.** A verifier verdiktjét a következményes művelet pillanatában MUST érvényesnek értékelni: az állapot (`T_now`) nem változhatott a verdikt számítása óta (R-V.11), a kibocsátó és a verifier jogosultsága fennáll (R-I.7), és a fogyasztó konfigurációja az aktuális, megkerülhetetlen (R-P.12, R-P.16). Ha ez nem garantálható, a megfelelőség PARTIAL / OPEN, és a döntés önmagában nem jogosít fel végrehajtásra. |
| R-M.10 | **A verifier hozzáférhetősége nem lehet megkerülés.** A verifier elérhetetlensége miatti kivétel (vészhelyzeti megkerülés) csak feljogosított, rögzített, tulajdonítható, a módosítás előtti konfiguráció szerint megítélt eljárással megengedett (R-P.16 c); egy ilyen megkerülés maradék kockázata nevesített. |

---

## 4. A mechanizmusok osztályozása

A követelmények nem választanak megvalósítást; az alábbi osztályok azt mutatják, melyik mechanizmus mit tud igazolni. A besorolás **elemzés, nem mérés**.

| Osztály | Leírás | S, B | P, C | Megfelel? |
|---|---|---|---|---|
| **M1** | **Fogyasztó-natív** ellenőrzés: maga a fogyasztó számolja és veti össze a `T_now`-t | igen | igen, ha a fogyasztó képes rá | Igen (R-M.4, R-M.7) |
| **M2** | **Független verifier**: különálló komponens, amelynek verdiktjét a fogyasztó kötelezően megköveteli (R-M.6), a kibocsátótól független (R-M.3) | igen | igen | Igen, ha R-M.1–R-M.3 teljesül |
| **M3** | **Kibocsátói önellenőrzés**: a kibocsátó közli és maga ellenőrzi a saját `T_d`-jét | csak az S, B, amelyet a fogyasztó natívan köt | **nem** | **Nem** a P, C elemekre (R-M.7 c) |
| **M4** | **A tárgy által definiált ellenőrzés** (a tárgy tartalmazza vagy módosíthatja az ellenőrzést) | nem | nem | **Nem** (R-M.1) |

Következmény (**következtetés, nem mért**): ha a fogyasztó a P és C összevetésére natívan nem képes, az **M2** az egyetlen megfelelő mechanizmus; ehhez a fogyasztónak két, egymástól független, azonosítható bizonyítékot kell megkövetelnie (kibocsátó + verifier), ugyanarra az állapotra.

---

## 5. A scratch megfigyelései (olvasás és a mért jelentés; nem új mérés)

Forrás: `app-measurement-report.md` (3.1, 3.3, 3.6) és `raw/app/integrity-app.yml.txt`. **Nem új mérés.**

| Megfigyelés | Összevetés | Státusz |
|---|---|---|
| A kötelező ellenőrzés a kibocsátó identitásához kötött; azonos nevű hamis check nem elég | R-I teljesül a kibocsátóra; a fogyasztó natív kötése ez | **Mért** (A1, E3s) |
| A `strict` mellett az elavult zöld nem elfogadott a HEAD- és BASE-elmozdulásra | R-M.7 (a): az S, B natív kötése | **Mért** (C2, PR31, PR34) |
| Az ellenőrző és a policy az alapág aktuális csúcsáról, a job idején töltődik le (a közölt BASE SHA az eseményből jön) | Az ellenőrző és a policy forrása a B-oldal (R-A.4 a), de a kötés a közölt BASE-hez nem garantált | **Olvasott, PARTIAL / OPEN** (jelentés 3.6) |
| Az ellenőrző forrása a védett halmaz tagja; a módosítása jóváhagyáshoz és megfelelőséghez kötött | Az R-A.4 (c) részleges megfelelője a forrásra: jóváhagyó a B-oldali policy szerint; **digest-nyilvántartás nincs** | **Mért** (A3–A5) / következtetés |
| A kimenet nem hordozza a policy digestet és az ellenőrző digestjét | R-M.4, R-M.5 nem teljesíthetők a kimenetből | **Olvasott** (jelentés 3.6) |
| Nincs független verifier; nincs `C_exp` nyilvántartás; nincs bootstrap-rekord | R-A.4, R-A.7, R-M.2, R-M.6 nincs meg | **Nem létezik** a scratch-ben (olvasás) |
| Két, egymástól független kibocsátói identitás (két App) a kötelező ellenőrzésekhez | Az M2 előfeltétele; nem mértük, hogy a platform két külön identitáshoz kötött kötelező ellenőrzést kezel-e | **Nem mért** |

**Következtetés (nem mért):** a scratch jelenlegi *implicit* horgonya az alapág csúcsa és a védett halmaz jóváhagyási szabálya; ez az R-A.4 elemei közül a (a), (b), (c)-t közelíti, de nincs explicit nyilvántartás, nincs digest, nincs független verifier, és a közölt BASE-hez kötés nem garantált. A mechanizmus a besorolásban **M3 jellegű** a P és C elemekre (a kibocsátó közli, a platform csak az S, B-t köti), tehát az R-M.7 (c) szerint nem megfelelő.

---

## 6. Nyitott kérdések

Az N1 és N2 e javaslat elfogadásakor tekinthető lezártnak (a normatív rész szintjén). A következők az ebből következő **új** kérdések; nem szerepelnek az N1–N7-ben vagy az N3.x, N5.x-ben.

| # | Kérdés | Érintett |
|---|---|---|
| N1.1 | **A nyilvántartás helye és védelme.** Hol él a nyilvántartás technológiafüggetlenül (az alap oldalán, külön tárban), és mi a módosításának jogosultsági modellje; szükséges-e független aláíró hatóság. | R-A.4, R-A.2 |
| N1.2 | **A telepítés részletei.** Ki a „feljogosított tulajdonosi hatóság", mi a független újraképzés pontos eljárása, mi az igazolt rekord. | R-A.7 |
| N1.3 | **Forgatás és kompromittálás utáni helyreállítás, N8.** A kompromittálás és észlelése közti időszakban kibocsátott döntések kezelése; a horgony elemeinek visszavonása. | R-A.8, N8-jelölt |
| N2.1 | **A fogyasztó képessége.** A fogyasztó natívan összevetheti-e a P és C elemeket (a besorolás szerint valószínűleg nem). | R-M.7 |
| N2.2 | **Két független kötelező bizonyíték.** Kezelheti-e a fogyasztó két, különböző identitáshoz kötött kötelező ellenőrzést ugyanarra az állapotra; mi a közös hibaforrás nélküli függetlenség pontos mércéje. | R-M.3, R-M.6 |
| N2.3 | **A verifier saját bizalmi alapja.** Mi a verifier futtatókörnyezete és a rá vonatkozó nevesített bizalmi alap. | R-M.2, R-A.3 |
| N2.4 | **Atomi kötés a művelet pillanatában.** A fogyasztó natívan garantálja-e, hogy a verdikt csak az ellenőrzött állapotra szolgál a művelet pillanatában (TOCTOU). | R-M.9, R-V.11 |
| N2.5 | **A verifier elérhetetlenségének és a vészhelyzeti megkerülésnek a kezelése.** A blokkolás kockázata és a megkerülés rögzítése. | R-M.8, R-M.10 |

Függőségek: az **N1.1** és az **N2.1–N2.2** az N3 (P, C, a feljogosított halmazok) és az N5 (digest, jegyzék) lezárására épül; az **N2.4** a TOCTOU feltáró méréssel (open-case-triage 4. lépés) válik eldönthetővé; az **N1.3** a G3 (E1/E2, N7) csoporttal és az N8-jelölttel függ össze.

---

## 7. Javasolt, de még nem igazolt megoldás

**Nem mért védelem, nem része a követelményeknek.** Mindegyik külön scratch méréssel és review-val igazolandó, mielőtt bármilyen éles konfiguráció szóba kerülne.

| # | Javaslat | Szolgálja | Mi hiányzik az igazoláshoz |
|---|---|---|---|
| J-A1 | **Két identitásos architektúra (M2):** a kibocsátó és a verifier külön, egymástól független identitás, a kötelező ellenőrzések mindkettőhöz külön kötve, a fogyasztó mindkettőt megköveteli | R-M.3, R-M.6 | N2.2: scratch mérés, hogy a platform két külön identitáshoz kötött kötelező ellenőrzést együtt kezel, és az egyik hiánya blokkol |
| J-A2 | **A verifier az alap-oldalra rögzített hivatkozásból fut:** a checkout a közölt BASE SHA-ra rögzített (nem a mozgó alapágra), a verifier a kibocsátó forrását *adatként* olvassa, digestjét képezi, és a nyilvántartással veti össze | R-M.1, R-M.4, R-A.4 | Scratch mérés: az alapág a job közben elmozdul; a verifier digestje a nyilvántartásbelivel egyezik / eltér |
| J-A3 | **A `C_exp` nyilvántartás az alap-oldalon, védett halmazban**, a módosítása a módosítás előtti policy szerint, a szerzőn kívüli jóváhagyóval; a bejegyzés megfelelőségi bizonyítékhoz kötött | R-A.4–R-A.6 | N1.1; scratch mérés: a PR a saját `C_exp`-ét nem tudja bejegyezni |
| J-A4 | **A telepítés tulajdonosi eseményként**, független újraképzéssel és rekorddal | R-A.7 | N1.2 |
| J-A5 | A CIC meglévő aláírási láncának (fejlesztői aláírás + független ellenjegyzés) mint a nyilvántartás független aláíró hatóságának vizsgálata | R-A.4 (c), N1.1 | **Csak jelölt:** nem mértük, hogy illeszkedik-e; nem állítjuk, hogy alkalmas |

---

## 8. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A bizalmi lánc véges és nem önigazoló horgonyon végződik | Normatív állítás | R-A.1, R-A.2, 2.1 | Tartalmi review | A „gyökér-horgony" konkrét megvalósítása nyitott (N1.1) |
| Az elvárt ellenőrző-digest független nyilvántartásból jön, nem a kibocsátótól | Normatív állítás | R-A.4, R-V.6 | Tartalmi review | A nyilvántartás védelme nem mért (N1.1) |
| A verifier nem lehet a tárgy saját verifiere | Normatív állítás | R-M.1 | Tartalmi review | A #213 külön lépés |
| A kibocsátói önellenőrzés a P, C elemekre nem megfelelő (körkörös) | Normatív állítás | R-M.7 c, R-A.1 | Tartalmi review | – |
| A kötelező ellenőrzés kibocsátói identitáshoz kötése mért (scratch) | Mért | A1, A2, E3s | Jelentés 3.1 | Csak scratch; installáció-felfüggesztés nem mért |
| A `strict` az S, B elmozdulását natívan kezeli (scratch) | Mért | PR31, PR34 | Jelentés 3.3 | A check–merge ablak nem mért |
| A scratch-ben nincs független verifier, `C_exp` nyilvántartás, bootstrap-rekord | Olvasott | `integrity-app.yml.txt`, jelentés 3.6 | A workflow olvasása | A teljes scratch átvizsgálása nem történt |
| A scratch P, C elemekre M3 jellegű | **Következtetés, nem mért** | 5. szakasz | Tartalmi review; scratch mérés (külön lépés) | Az osztályozás elemzés |
| A fogyasztó a P, C-t natívan nem képes összevetni | **Következtetés, nem mért** | Jelentés 3.6 | Scratch mérés, N2.1 | Ha mégis képes, az M1 egyszerűsít |
| A platform két független identitáshoz kötött kötelező ellenőrzést kezel | **Nem mért** | — | J-A1 mérés, N2.2 | Az M2 előfeltétele |
| A telepítés független újraképzéssel megoldható | **Nem igazolt** | — | J-A4, N1.2 | Az N5 R-D.20 és a független implementáció |
| Az N1/N2 normatív része e javaslat elfogadásakor zárható | Javaslat | Ez a dokumentum | Tartalmi review | A 6. szakasz új kérdései |

---

## 9. Mit nem állít ez a dokumentum

- Nem választ megvalósítást és nem mér; az M1–M4 osztályozás és az 5. szakasz elemzés, a J-A1–J-A5 javaslat.
- Nem állítja, hogy a Relay védett; a scratch megfigyelések nem Relay-mérések.
- Nem dönt az algoritmusról és a kódolásról (N5.1, N5.2).
- Nem állítja, hogy a CIC aláírási lánca alkalmas nyilvántartás-aláíróként (J-A5 csak jelölt).
- Nem dönt a Relay-implementációról, az éles beállításról, a #212 lezárásáról (HOLD).
