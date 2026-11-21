# Az S/B/P/C digestek képzése és kanonizálása (N5, tervezési szakasz)

Státusz: **tervezési specifikáció felülvizsgálatra.** Nem implementáció, nem mérés, nem döntés a Relay beállításairól. A konformanciatesztek **tervezettek**, nem megírtak és nem futtatottak.

Az **N3** (`policy-boundary-spec.md`) azt rögzítette, *mi* tartozik az állapotkötésbe. Ez a dokumentum azt, **hogyan képződnek** a kötött elemek digestjei, hogy a digest egyértelműen azonosítsa azt, amit kötnie kell. Az **N1/N2** (az elvárt digest bizalmi horgonya, az ellenőrzés helye) nem része ennek a dokumentumnak.

| Rész | Szakasz | Jelleg |
|---|---|---|
| Normatív szabályok | 2–6 | Technológiafüggetlen követelmény (R-D.*). |
| Konformanciateszt-terv | 7 | Tervezett pozitív és negatív tesztek; nem futtatott. |
| Kapcsolódás az N3-hoz | 8 | Leképezés az N3 elemeire és követelményeire. |
| A scratch digest-képzés megfigyelései | 9 | Kódolvasás; **nem mérés**. |
| Nyitott kérdések | 10 | Nem eldöntött. |
| Javasolt, nem igazolt megoldás | 11 | Sem követelmény, sem mért. |

---

## 1. Fogalmak

| Fogalom | Jelentés |
|---|---|
| **Logikai bemenet** | Az az adat, amelyet a digest azonosít, a reprezentációjától függetlenül (például egy rendezetlen halmaz elemei, nem a felsorolásuk sorrendje). |
| **Kanonikus alak** | A logikai bemenet egyetlen, szabállyal meghatározott bájtsorozata. |
| **Digest** | A kanonikus alakból, kijelölt algoritmussal képzett, algoritmus-azonosítóval ellátott érték. |
| **Címke** (domain tag) | A digest bemenetének részét képező, a digest típusát és verzióját azonosító elem. |
| **Jegyzék** (manifest) | Egy összetett elem (P, C, S képe) alkotóelemeinek kanonikus felsorolása, elemenként azonosítóval és tartalom-digesttel. |
| **Lezárás** (closure) | Mindazon elemek összessége, amelyek a viselkedést vagy az értéket befolyásolják (R-D.12). |

---

## 2. Általános szabályok

| Azonosító | Követelmény |
|---|---|
| R-D.1 | **Az algoritmus azonosított és rögzített halmazból való.** A digest ábrázolása az algoritmus azonosítóját MUST tartalmazza (`<algoritmus>:<érték>`). Az elfogadott algoritmusok halmaza rögzített és verziózott; az ismeretlen algoritmust a fogyasztó MUST elutasítani. A halmaz kiválasztása nyitott (N5.1). |
| R-D.2 | **Ütközésállóság.** Az algoritmus MUST ütközés- és második előkép-álló legyen a tervezett használat időtartamára. Csonkolt digest MUST NOT elfogadott. |
| R-D.3 | **Teljes érték szerinti összehasonlítás.** A digest összevetése a teljes, azonosított értékre történik; rövidített vagy előtag-összevetés MUST NOT elegendő. |
| R-D.4 | **A digest csak teljes, kanonikus bemenetből képződhet.** Ha a bemenet nem kanonizálható vagy nem igazolhatóan teljes (R-D.14), digest MUST NOT képződjön: részleges vagy „legjobb tudomású" digest nem létezik, mert az érvényes digestnek tűnne. |

---

## 3. Kanonizálás

### 3.1 Determinizmus és egyértelműség

| Azonosító | Követelmény |
|---|---|
| R-D.5 | **Determinizmus.** Azonos logikai bemenetből a kanonikus alak MUST azonos bájtsorozat legyen, függetlenül a platformtól, nyelvi beállítástól, időtől, a futás sorrendjétől, a rendezetlen gyűjtemények felsorolási sorrendjétől, és a tárolórendszer bejárási sorrendjétől. |
| R-D.6 | **Egyértelműség (injektivitás).** Különböző logikai bemenetből a kanonikus alak MUST különböző bájtsorozat legyen. A kódolás MUST önhatároló vagy hosszprefixes: két elem összefűzése nem eredményezhet olyan bájtsorozatot, amely egy másik elempárból is előállhat (például `("a\nb","c")` és `("a","b\nc")` kanonikus alakja eltér). Határoló karakterre épülő összefűzés, amely az elem tartalmában is előfordulhat, nem megengedett. |
| R-D.7 | **Explicit típus.** A kanonikus alak minden értéke típusazonosított; az `üres`, a `hiányzó` és a `null` különböző kanonikus alakú; a logikai és a szám és a szöveg nem téveszthető össze. |

### 3.2 Típusok kezelése

| Típus | Szabály |
|---|---|
| **Szöveg** | Meghatározott kódolású bájtsorozat. A kódolás hibája (érvénytelen bájtsor) MUST elutasítást adjon. **Implicit normalizálás nincs** (nincs Unicode-normalizálás, nincs kis-/nagybetű-egységesítés, nincs szóköz- vagy sorvég-átalakítás): a két különböző bájtsorozat különböző érték. Ha egy normalizálás szükséges, azt a kanonikus alak *explicit, verziózott* szabályként tartalmazza (R-D.15). |
| **Név** (például útvonal, azonosító) | Bájtsorozat, **bármely bájtot** tartalmazhat, beleértve a sortörést és a határolóként használatos karaktereket; a hosszprefixes kódolás miatt ez nem okoz kétértelműséget. |
| **Fájl- és adat-tartalom** | Nyers bájtok; sorvég-, szóköz- vagy kódolás-átalakítás nincs. |
| **Szám** | Egyetlen kanonikus ábrázolás értékenként. Kétértelmű ábrázolású típus (például lebegőpontos) csak definiált kanonikus formával megengedett; ellenkező esetben elutasítás. |
| **Leképezés** (map) | Kulcs szerint, a kulcs kanonikus bájtsorrendje szerint rendezett. Ismétlődő kulcs MUST elutasítást adjon. |
| **Rendezett lista** | A sorrend jelentős; a sorrend a kanonikus alak része. |
| **Rendezetlen halmaz** | Elemei a kanonikus bájtok szerint rendezettek. Ismétlődő elem MUST elutasítást adjon (az elemszám a halmaz kanonikus alakjának része). |
| **Ismeretlen vagy nem támogatott típus** | MUST elutasítást adjon. |

---

## 4. Domain separation, típus- és verzióazonosítás

| Azonosító | Követelmény |
|---|---|
| R-D.8 | **Címke minden digestben.** Minden digest bemenete MUST tartalmazza a címkét: a specifikáció azonosítóját, az **elemtípust** (S, B, P, C, jegyzékelem, jóváhagyási hatókör, összetett kötés) és a **séma-verziót**. Azonos bájtsorozat más típuscímkével MUST más digestet adjon. |
| R-D.9 | **Típusok közti összetévesztés tilos.** Egy adott típusú digest MUST NOT elfogadott más típus helyén. A fogyasztó az elvárt típuscímkét a saját oldalán határozza meg, nem a digestet hozó rekordból. |
| R-D.10 | **Verzió.** A séma-verzió változása MUST különböző digestet adjon. Az ismeretlen vagy nem támogatott verzió a fogyasztónál MUST elutasítást adjon (fail-closed); nincs automatikus „legközelebbi verzióra" visszaesés. |
| R-D.11 | **Összetett kötés.** Az állapot-négyes `T = (S, B, P, C)` a négy elemdigestből képződő összetett digest is lehet. Az összetett digest bemenete a négy elemdigest, rögzített sorrendben, hosszprefixes kódolással, saját típuscímkével; a rekord MUST tartalmazza az elemdigesteket is, hogy az eltérés helye azonosítható legyen. |

---

## 5. Az elemek digestje, a lezárás és a teljesség

### 5.1 Elemenkénti szabály

| Elem | A digest bemenete (logikai) | Megjegyzés |
|---|---|---|
| **S** (tárgy) | A tárgy **tartalom-azonosítója** (nem módosítható, tartalomból képzett), és a levezetett kép(ek) digestje | A változtatható név (például egy ágnév) nem S: csak tartalom-azonosító köthető. |
| **S képe** (például változáskészlet) | **Rendezetlen halmaz**, elemei rekordok: `(típus, új név, régi név, tartalom-azonosító)`; átnevezésnél mindkét név az elemben; az elemszám a kanonikus alak része | Név bármely bájtot tartalmazhat (3.2). A kép teljességét R-C.1 igazolja, a digest ezt nem helyettesíti. |
| **B** (alap) | Az alap tartalom-azonosítója | Ugyanúgy nem módosítható azonosító. |
| **P** (hatályos policy) | A **hatályos-policy jegyzék** (N3 2.1–2.3.2): minden forrás (fájl, öröklési forrás, külső snapshot, alapértelmezés) bejegyzése `(forrás-azonosító, bizalmi és szemantikai attribútumok, a feloldott érték kanonikus digestje)`; a kizárási lista; a séma és szemantikai verzió; a deklarált halmazok | Rendezetlen halmaz a forrásokra; a feloldott érték a logikai értékre kanonizált, nem a forrásszövegre (R-D.15). |
| **C** (ellenőrző) | Az **implementációs jegyzék**: minden lezárásbeli elem `(azonosító, verzió, tartalom-digest)`; a beágyazott állandók; a teljességvizsgálat logikája (R-C.6) | Lásd 5.2. |
| **Jóváhagyási hatókör** | A védett változások kanonikus halmaza (az S képének védett részhalmaza), `(típus, új név, régi név, tartalom-azonosító)` elemekkel | Az R-V.12 szerinti jóváhagyás ezt köti; saját típuscímke. |

### 5.2 Függőségi lezárás és a digestképzés teljessége

| Azonosító | Követelmény |
|---|---|
| R-D.12 | **A lezárás meghatározása.** A C jegyzéke MUST tartalmazza a viselkedést befolyásoló **valamennyi** elemet: az ellenőrző kódját, a közvetlen és közvetett függőségeit, a futtatókörnyezetet és a beágyazott állandókat. A lezárás határa (a függőségi zárlat mélysége, N3.4) a jegyzékben nevesített; a határon kívüli elemek **bizalmi alapként** nevesítettek, nem hallgatottak el (R-P.13). |
| R-D.13 | **Tartalom-azonosított függőségek.** A jegyzék minden eleme tartalom-digesttel azonosított. Olyan elem, amely nem tartalom-azonosított (mozgó verzió, változtatható hivatkozás), nem köthető: **kötetlen tényező**, PARTIAL / OPEN (R-P.13), és az ilyen ellenőrző döntése önmagában nem jogosít fel végrehajtásra. |
| R-D.14 | **A jegyzék teljessége igazolt.** A jegyzék teljességét **két független módon** MUST igazolni: (a) *statikus felsorolással* (a lezárás elemeinek feloldása), és (b) *futásidejű ellenőrzéssel*, hogy az ellenőrző csak jegyzékben szereplő elemet tölt be vagy hajt végre; a jegyzéken kívüli elem betöltése MUST hibát adjon (fail-closed). A statikus felsorolás önmagában nem igazolja, hogy a futás nem használt mást. |

---

## 6. Szemantikai egyenértékűség, fail-closed

### 6.1 Konzervatív egyenértékűség

| Azonosító | Követelmény |
|---|---|
| R-D.15 | **Alapértelmezés: nincs egyenértékűség.** Két bemenet digestje akkor és csak akkor azonos, ha kanonikus alakjuk azonos. A kanonikus alak *maga* határozza meg az egyenértékűség egyetlen megengedett formáját (például a leképezés kulcssorrendje közömbös). Minden további egyenértékűség (például megjegyzések vagy szóköz figyelmen kívül hagyása) csak **explicit, verziózott, indokolt és tesztelt** kanonizálási szabályként vezethető be, **és** csak akkor, ha igazolt, hogy az ellenőrző az eltérést nem olvassa (N3.5, R-P.2). Bizonytalanság esetén a kimenet: különböző digest (érvénytelenítés, R-P.9). |
| R-D.16 | **Az implicit átalakítás hiba.** Az a megvalósítás, amelyben a digest bemenete egy átalakításon megy át, amelyet a kanonikus szabály nem nevez meg (például a sorvég egységesítése egy beolvasó réteg által), nem felel meg R-D.5–R-D.7-nek; a megfelelőség ezekre PARTIAL / OPEN. |

### 6.2 Fail-closed

| Azonosító | Követelmény |
|---|---|
| R-D.17 | Az alábbi esetek MUST negatív kimenetet adjanak, megkülönböztethető okkal, **digest képzése nélkül** (R-D.4): érvénytelen kódolás; ismétlődő kulcs vagy halmazelem; ismeretlen típus, címke, verzió vagy algoritmus; nem kanonizálható bemenet; hiányos jegyzék vagy lezárás (R-D.14); nem tartalom-azonosított függőség (R-D.13); elérhetetlen forrás (R-P.6); a forrás szándékolt tartalmán kívüli értelmezhetetlen elem (R-P.7). |
| R-D.18 | A negatív kimenet okát a döntés rögzíti (például `NONCANONICAL`, `INCOMPLETE_CLOSURE`, `UNKNOWN_VERSION`); a hibát nem szabad „nincs digest"-ként, azaz üres vagy hiányzó értékként kezelni, mert a fogyasztó azt pozitív döntésként értelmezhetné. |

### 6.3 Ellenőrzés a fogyasztónál

| Azonosító | Követelmény |
|---|---|
| R-D.19 | A fogyasztó (vagy a verifier) a digestet **ugyanezen normatív szabályok szerint újraképzi** a hiteles forrásból (R-V.5), és a kibocsátó közölte értéket nem tekinti bizonyítéknak. |
| R-D.20 | **Független implementációk egyezése.** A normatív szabályoknak legalább két, egymástól független implementációja MUST azonos digestet adjon a teljes konformanciateszt-készleten (7. szakasz). Az egy implementáció által definiált kanonikus alak, amelyet más nem tud megismételni, nem normatív szabály. |

---

## 7. Konformanciateszt-terv

**Tervezett, nem megírt és nem futtatott tesztek.** A tesztkészlet része a konformanciának (R-D.20). Minden tesztnek **képesnek kell lennie bukni** (lásd 7.3).

### 7.1 Pozitív tesztek (azonos logikai bemenet → azonos digest, és a várt értékek)

| Azonosító | Teszt | Várt | Követelmény |
|---|---|---|---|
| T-P1 | Azonos bemenet ismételt futtatása, különböző platformon és nyelvi beállítással | azonos digest | R-D.5 |
| T-P2 | Leképezés kulcssorrendjének permutálása | azonos digest | R-D.5, 3.2 |
| T-P3 | Rendezetlen halmaz elemeinek permutálása | azonos digest | R-D.5, 3.2 |
| T-P4 | A bejárási sorrend változtatása (a tárolórendszer felsorolási sorrendje) | azonos digest | R-D.5 |
| T-P5 | Kézzel számított aranyvektorok minden elemtípusra (S, B, P, C, jegyzékelem, jóváhagyási hatókör, összetett kötés) | a vektor szerinti digest | R-D.8, R-D.11 |
| T-P6 | Két független implementáció azonos eredménye az aranyvektorokon és a negatív készleten | azonos eredmény | R-D.20 |
| T-P7 | Újsor- és határoló-tartalmú név, hosszprefixes kódolással | érvényes, a vektor szerinti digest | R-D.6 |
| T-P8 | Átnevezés: mindkét név az elemben | a két név a digestben | 5.1 |

### 7.2 Negatív és érzékenységi tesztek (eltérő bemenet → eltérő digest, vagy elutasítás)

| Azonosító | Teszt | Várt | Követelmény |
|---|---|---|---|
| T-N1 | Bármely lefedett mező egyetlen bitjének megváltoztatása | eltérő digest | R-D.6 |
| T-N2 | Mező elhagyása; mező hozzáadása | eltérő digest | R-D.6 |
| T-N3 | Rendezett lista sorrendjének megváltoztatása | eltérő digest | 3.2 |
| T-N4 | Összefűzési kétértelműség: `("a\nb","c")` kontra `("a","b\nc")`; `("ab","c")` kontra `("a","bc")` | eltérő digest | R-D.6 |
| T-N5 | Üres, hiányzó és `null` érték | három különböző digest | R-D.7 |
| T-N6 | Azonos bájtok más típuscímkével (S kontra P kontra C) | eltérő digest | R-D.8 |
| T-N7 | Típusok közti összetévesztés: egy P-digest S helyén a fogyasztónál | elutasítás | R-D.9 |
| T-N8 | Ismeretlen séma-verzió; ismeretlen algoritmus | elutasítás | R-D.10, R-D.1 |
| T-N9 | Csonkolt digest; előtag-összevetés | elutasítás | R-D.2, R-D.3 |
| T-N10 | Ismétlődő kulcs a leképezésben; ismétlődő elem a halmazban | elutasítás, digest nélkül | R-D.17, 3.2 |
| T-N11 | Érvénytelen kódolású szöveg | elutasítás, digest nélkül | 3.2, R-D.17 |
| T-N12 | Ismeretlen vagy nem támogatott típus | elutasítás | 3.2 |
| T-N13 | Sorvég: azonos tartalom CRLF és LF sorvéggel | **eltérő** digest (nincs implicit átalakítás) | 3.2, R-D.16 |
| T-N14 | Unicode: ugyanannak a karakternek két kódolási alakja a névben | **eltérő** digest (nincs implicit normalizálás) | 3.2, R-D.15 |
| T-N15 | Szóköz vagy megjegyzés hozzáadása a policyhoz (a kanonikus szabály nem nevezi egyenértékűnek) | eltérő digest | R-D.15 |
| T-N16 | A jegyzékből hiányzó, de betöltött függőség | az ellenőrző hibát ad | R-D.14 |
| T-N17 | Nem tartalom-azonosított (mozgó) függőség a lezárásban | kötetlen tényező, PARTIAL / OPEN | R-D.13 |
| T-N18 | A teljességvizsgálat logikájának gyengítése | eltérő C digest | R-C.6, R-D.12 |
| T-N19 | A policy ismeretlen kulccsal | elutasítás | R-P.7, R-D.17 |
| T-N20 | Elérhetetlen külső forrás | elutasítás, digest nélkül | R-P.6, R-D.17 |
| T-N21 | A negatív kimenet okának és a „nincs digest" érték megkülönböztetése | az ok rögzített, az üres érték nem pozitív | R-D.18 |
| T-N22 | Az összetett kötésben egy elemdigest cseréje | eltérő összetett digest; az eltérés helye azonosítható | R-D.11 |

### 7.3 A tesztek képessége a bukásra (meta-tesztek)

A tesztkészlet csak akkor bizonyít, ha tudjuk, hogy bukni képes. Minden negatív teszthez tartozik egy **szándékosan hibás referencia-implementáció** (planted defect), amelyen a teszt MUST bukjon:

| Beültetett hiba | A bukó teszt |
|---|---|
| a címke elhagyása | T-N6, T-N7 |
| határolóra épülő összefűzés hosszprefix helyett | T-N4, T-P7 |
| implicit sorvég- vagy Unicode-normalizálás | T-N13, T-N14 |
| kulcsrendezés elhagyása | T-P2 |
| csonkolt összehasonlítás | T-N9 |
| ismétlődő elem csendes összevonása | T-N10 |
| a futásidejű betöltés-ellenőrzés elhagyása | T-N16 |

Az a teszt, amely a beültetett hibán nem bukik, nem érvényes konformanciateszt.

---

## 8. Kapcsolódás az N3 normatív policy-határához

| N3 elem vagy követelmény | A digest-képzés megfelelője |
|---|---|
| P: a hatályos (feloldott) policy (R-P.4) | A hatályos-policy jegyzék (5.1): a feloldott érték kanonikus digestje, nem a forrásszöveg |
| Az öröklött forrás bizalmi és szemantikai attribútumai (R-P.15) | A jegyzékbejegyzés attribútum-mezői; bármelyik változása más digest (R-D.15 szerint nincs egyenértékűség) |
| C: az ellenőrző és lezárása (R-P.5) | Az implementációs jegyzék és a teljességigazolás (R-D.12–R-D.14) |
| Külső bemenet kötése: hely, ellenőrzés, érvénytelenítés (R-P.14) | A „hely" a digest elemtípusát adja (S, B vagy P); az „ellenőrzés" a fogyasztói újraképzés (R-D.19); az „érvénytelenítés" a digest eltérése |
| Kizárási lista (R-P.3) | A P jegyzékének része; kötött, így a kizárás módosítása is érvénytelenít |
| Hiányzó vagy értelmezhetetlen policy: fail-closed (R-P.7) | R-D.17 |
| Konzervatív érvénytelenítés (R-P.9) | R-D.15 |
| Kötetlen tényező: PARTIAL / OPEN (R-P.13) | R-D.13, R-D.14 |
| Fogyasztói konfiguráció: használatkor értékelt, nem kötött (R-P.12, R-P.16) | **Nem része a digestnek**; a kötés tárgya az N3 szerint nem ez |
| Jóváhagyási aktus: a tárgyhoz és a védett változáshoz kötött (R-V.12) | A jóváhagyási hatókör digestje (5.1), saját típuscímkével |

---

## 9. A scratch digest-képzés megfigyelései (kódolvasás, nem mérés)

Forrás: `raw/app/integrity-final.py.txt`, 100. és 116. sor. **Ez a kód elolvasása a fenti szabályok fényében; nem futtatott mérés, és nem a teljes digest-képzés átvizsgálása.** A következtetések jelölve.

| Megfigyelés | Összevetés | Státusz |
|---|---|---|
| A policy digest a fájl szövegének SHA-256-ja, a `sha256:` előtaggal a naplóban | Algoritmus-azonosító megvan (R-D.1); **címke és séma-verzió nincs** (R-D.8, R-D.10) | Kódolvasás |
| A policy szövege szöveges módban, UTF-8 dekódolással van beolvasva, majd újrakódolva | **Következtetés (nem mért):** szöveges módú beolvasásnál a sorvég-átalakítás implicit lehet, így CRLF és LF sorvégű azonos policy azonos digestet adhat. Ez **implicit egyenértékűség** (R-D.16), amelyet a szabály nem nevez meg | Következtetés |
| A jóváhagyási digest a védett változásrekordok `\n`-nel összefűzött SHA-256-ja; a rekord `"<státusz> <régi név vagy -> -> <új név> <sha>"` szövegsor | **Következtetés (nem reprodukált):** a nevek bármely karaktert tartalmazhatnak, a rekord- és mezőhatároló pedig szöveges, ezért a nevekben előforduló határoló (újsor, ` -> `) esetén elvileg két különböző változáskészlet azonos összefűzött szöveget adhat (R-D.6). A jelentés 7/4 pontja (újsor-tartalmú fájlnév, digest-ütköztetés) ezt nem mérte | Következtetés, nyitott |
| A rekordok rendezése a nyelv alapértelmezett szöveg-összehasonlítása szerint | Determinisztikus; a rendezés alapja nem a kanonikus szabályban megnevezett bájt-sorrend, hanem a nyelv saját összehasonlítása (az egyezés a bájt-sorrenddel nem szabály, ezért a platformfüggetlenség nem igazolt, R-D.5) | Kódolvasás |
| A rekord a régi és az új nevet is tartalmazza átnevezéskor | Megfelel az 5.1 szabályának (mért: a `rename` regresszió, jelentés 3.2/4) | Mért (scratch) |
| A jóváhagyási digest nem tartalmaz típuscímkét; a policy digest és az ellenőrző digestje nincs a kimenetben | R-D.8 nem teljesül; R-D.12 szerint a C jegyzék hiányzik | Kódolvasás; jelentés 3.6 |
| A jóváhagyás az `APPROVE-PROTECTED head=<sha> digest=sha256:<hex>` formátumú | Algoritmus-azonosító és HEAD-kötés megvan; verzió- és típusazonosítás nincs | Kódolvasás; mért: A4/A5 |

**Ami ebből következik (következtetés):** a scratch megvalósítás digest-képzése az R-D.5–R-D.10 szabályoknak jelenleg **nem felel meg** vagy nem igazolt, a legfontosabb eltérések: nincs címke és verzió, az összefűzés nem hosszprefixes, és a sorvég egyértelműsége nem igazolt. Ezek a 7. szakasz tesztjeinek (T-N4, T-N8, T-N13) konkrét célpontjai. **Nem állítjuk, hogy az ütközés vagy az egyenértékűség ténylegesen előidézhető**; ezt mérés dönti el.

---

## 10. Nyitott kérdések

| # | Kérdés | Érintett |
|---|---|---|
| N5.1 | **Az algoritmus-halmaz.** Mely algoritmusok engedélyezettek, mi a váltási eljárás, és meddig érvényes egy algoritmus-azonosító. | R-D.1, R-D.2 |
| N5.2 | **A kanonikus kódolás.** Önhatároló bináris kódolás kontra szabványos kanonikus szöveges forma. A követelményekből (R-D.5–R-D.7) levezethető-e egyetlen jelölt, vagy a döntés a megvalósításon múlik. | R-D.5–R-D.7 |
| N5.3 | **A C lezárásának mélysége.** A függőségi zárlat, a futtatókörnyezet és a platform mely elemei kerülnek a jegyzékbe, és melyek nevesített bizalmi alap (N3.4). | R-D.12, N3.4 |
| N5.4 | **A nem érvénytelenítő változások köre.** Van-e bármely egyenértékűségi szabály, amely indokolt és tesztelt (N3.5), vagy az alapértelmezés (nincs egyenértékűség) marad. | R-D.15, N3.5 |
| N5.5 | **A futásidejű betöltés-ellenőrzés kikényszerítése.** Hogyan igazolható egy adott futtatókörnyezetben, hogy a jegyzéken kívüli elem nem töltődik be. | R-D.14 |
| N5.6 | **A nagy és lapozott bemenet digestje.** A hiányos lista (R-C) és a digest viszonya; mikor jön létre digest részleges forrás mellett (R-D.4 szerint soha). | R-D.4, R-C.1 |

Függőségek: az N5 az N3 határára épül; az **N1/N2** (az elvárt C bizalmi horgonya, az ellenőrzés helye) után válik teljessé: a jegyzék akkor köt, ha az elvárt digest független forrásból jön.

---

## 11. Javasolt, de még nem igazolt megoldás

**Nem mért védelem, nem része a követelményeknek.**

| # | Javaslat | Szolgálja | Mi hiányzik az igazoláshoz |
|---|---|---|---|
| J-D1 | A kanonikus alak hosszprefixes, típusozott kódolással (T-L-V jellegű), a címke a bemenet első eleme | R-D.6–R-D.8 | N5.2 döntés; két független implementáció és az aranyvektorok (T-P5, T-P6) |
| J-D2 | A C jegyzéke jegyzékek jegyzéke (fa-szerkezet): részjegyzékek digestjei a gyökérben, így egy elem eltérése azonosítható | R-D.11, R-D.12 | N5.3; mérés, hogy az eltérés helye azonosítható |
| J-D3 | Futásidejű betöltés-ellenőrzés: az ellenőrző induláskor a betöltött elemeket a jegyzékkel veti össze, és eltérésnél hibával megáll | R-D.14 | N5.5; planted-defect teszt (T-N16) |
| J-D4 | A tesztkészlet két független nyelvű referencia-implementációval (R-D.20) | R-D.20 | Megírás és futtatás (külön lépés, GO-val) |

---

## 12. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A digestképzés szabálya (kanonizálás, címke, verzió, lezárás, fail-closed) az N3 határát követi | Normatív állítás | 2–6. szakasz, 8. szakasz leképezés | Tartalmi review | A kódolás-választás (N5.2) még nyitott |
| A scratch policy digest nem tartalmaz címkét és verziót | Olvasott (kód) | `integrity-final.py.txt` 100. sor | A kód olvasása | A teljes digest-képzés nincs átvizsgálva |
| A sorvég-egyértelműség a scratch policy digestnél nem igazolt | **Következtetés, nem mért** | Szöveges módú beolvasás, 100. sor | Tervezett T-N13, mérés külön GO-val | A tényleges viselkedés nem futtatott |
| A jóváhagyási digest összefűzése nem hosszprefixes, névütközés elvileg lehetséges | **Következtetés, nem reprodukált** | 116. sor, a rekordformátum (93. sor) | Tervezett T-N4, T-P7, mérés külön GO-val | Az ütközés tényleges előidézhetősége nem mért |
| Az átnevezésnél mindkét név a digestben van | Mért (scratch) | A `rename` regresszió, jelentés 3.2/4 | Jelentés | Csak a mért esetekre |
| A tesztkészlet képes bukni (planted defect) | **Terv** | 7.3 szakasz | A beültetett hibák futtatása (külön lépés) | A tesztek nincsenek megírva |
| A két független implementáció egyezése elérhető | **Nem igazolt** | — | J-D4, külön lépés | Az egyik implementáció definiálhatja a formát |
| A C lezárása és a betöltés-ellenőrzés kivitelezhető | **Nem igazolt** | — | N5.3, N5.5, mérés | A futtatókörnyezet korlátai |
| Az N5 tervezési része e javaslat elfogadásakor zárható | Javaslat | Ez a dokumentum | Tartalmi review | A 10. szakasz kérdései (N5.1–N5.6) |

---

## 13. Mit nem állít ez a dokumentum

- Nem írt és nem futtatott tesztet; a konformanciateszt-terv terv.
- Nem választ algoritmust és kódolást (N5.1, N5.2).
- Nem dönt az ellenőrzés helyéről és a bizalmi horgonyról (N1/N2).
- Nem állítja, hogy a Relay védett; a 9. szakasz kódolvasás, nem mérés, és a következtetések nem tények.
- Nem dönt a Relay-implementációról, az éles beállításról, a #212 lezárásáról (HOLD).
