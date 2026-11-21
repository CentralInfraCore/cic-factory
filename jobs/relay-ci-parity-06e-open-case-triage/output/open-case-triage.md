# A nyitott esetek és kérdések besorolása és priorizálása

Státusz: **elemzés és tervezés, felülvizsgálatra.** Nem mérés, nem implementáció, nem döntés a Relay beállításairól.

Forrás: a mérési jelentés 7. szakasza (`Jel-1` … `Jel-11`, a jelentés számozása) és a specifikáció 7.1 szakasza (`N1` … `N7`). A követelmény-azonosítók (R-I, R-V, R-C, R-X) a `decision-requirements-spec.md`-ből valók.

**Jelölés.** *Mért* = a mérési jelentésben igazolt. *Következtetés* = ebből az elemzésből következik, nem mért; minden következtetés így van megjelölve, és mérésig nem tekinthető ténynek.

---

## 1. Besorolás és módszer

| Prioritás | Besorolás | Besorolási szabály ebben a dokumentumban |
|---|---|---|
| **P0** | Architekturális döntést blokkoló | A tétel kimenetele eldönti, hogy egy normatív követelmény egyáltalán teljesíthető-e adott architektúrán belül, vagy hol kell a megvalósításnak elhelyezkednie |
| **P1** | Megvalósítást blokkoló | Az architektúra adott, de a tétel nélkül a megvalósítás nem írható le vagy nem fogadható el |
| **P2** | Mérési bizonyosságot erősítő | A megvalósítás leírható; a tétel egy már leírt tulajdonság bizonyosságát emeli |
| **P3** | Relay-specifikus, későbbi munkacsomag | A tétel a Relay konkrét repójához kötött; az általános modell lezárása előtt nem értelmezhető |

A besorolás a tétel **következményéből** adódik, nem a nehézségéből. Ahol egy összevont csoport tagjai eltérő prioritásúak, a prioritás tagonként szerepel, a csoport prioritása a legmagasabb tagé.

A jelentés 7/2 tétele három önálló kérdést fog össze (fork-PR és második identitás; az E1 további csatornái; az E2), ezért itt `Jel-2a`, `Jel-2b`, `Jel-2c` néven külön szerepel. Az eredeti `Jel-2` hivatkozás így is visszakövethető.

---

## 2. Összevonási térkép (visszakövethetőség)

| Csoport | Név | Tagok (eredeti azonosítók) | Csoport-prioritás |
|---|---|---|---|
| **G1** | Bizalmi horgony és ellenőrzési hely | N1, N2, N3 | P0 |
| **G2** | Állapotkötés és időablak | Jel-6 (TOCTOU, 4/d), Jel-7 (`strict` korlát), N4, N5 | P0 |
| **G3** | Kibocsátói jogosultság és hitelesítő adat életciklusa | Jel-1, N7, Jel-2c (E2), Jel-8, Jel-2a, Jel-2b, Jel-3 (E0) | P0 |
| **G4** | Bemeneti teljesség | N6, Jel-4, Jel-5 | P1 |
| **G5** | Mérési bizonyosság | Jel-9, Jel-11 | P2 |
| **G6** | Relay-specifikus esetek | Jel-10 | P3 |

Összevonva (egy kérdésként kezelve): **N7 + Jel-1** (a jogosultság-visszavonás kérdése és az installáció felfüggesztésének mérése ugyanannak az állításnak az architekturális és a mérési oldala); **Jel-6 + Jel-7** (az időablak és a `strict` korlát ugyanazt a hiányt két oldalról írja le: mi köti a döntést az állapothoz a végrehajtáskor). Minden egyéb tétel külön marad.

Ellenőrzés: a 11 eredeti tétel (`Jel-1`…`Jel-11`, a Jel-2 három részre bontva) és az `N1`…`N7` mind pontosan egy csoportban szerepel.

---

## 3. Függőségek és összefüggések

### 3.1 N1–N2: az ellenőrző bizalmi horgonya és az ellenőrzés helye

- **N1** azt kérdezi, honnan jön az elvárt ellenőrző-digest úgy, hogy független legyen a kibocsátótól és a tárgy szerzőjétől (R-V.6). **N2** azt kérdezi, ki és hol végzi az R-V.4 összevetést (R-V.5: a fogyasztó a kibocsátótól függetlenül számol).
- **Kapcsolat (következtetés):** a két kérdés nem választható szét. Ha az összevetést (N2) a platform merge-kapuja végezné, az csak azt látja, amit a platform natívan ismer. A mért tény: a required check a kibocsátó identitásához köthető (A1, E3s) és a `strict` natívan kezeli a HEAD- és BASE-elmozdulást (C2, PR31/PR34). A policy és az ellenőrző digestjét a platform a mérések szerint **nem** ismeri; ezt a check-run kimenete sem hordozza (jelentés 3.6). Ebből következik: **az R-V.5 a P és C elemekre platformon belül, külön lépés nélkül nem teljesíthető**, tehát egy további, a kibocsátótól független ellenőrző lépés (verifier) szükséges. Ez következtetés, nem mért.
- **Regresszió (következtetés):** a független verifier maga is döntést bocsát ki, tehát R-I rá is vonatkozik (ki a verifier, ellenőrizhető-e az identitása). A regresszió véges kell legyen: a horgonynak olyan elemnek kell lennie, amelyet a platform natívan kikényszerít (a required check identitás-kötése és a `strict`), nem egy újabb önbevalló ellenőrző. Ez azonos elv a #213-ban rögzített „a verifier nem lehet a PR saját verifiere" szabállyal; az azonosság itt állítás a szempontra, a #213 külön lépés.
- **N3** (a policy határa) a közös előfeltétel: amíg nincs eldöntve, mi tartozik P-hez (policy fájl, védett halmaz, approvers, feljogosított kibocsátók halmaza), nem dönthető el, mit köt a digest, és mit kell a verifiernek a hiteles forrásból olvasnia.

### 3.2 TOCTOU és az állapotkötés

- **Mért:** a HEAD- és BASE-elmozdulást a `strict: true` natívan elutasítja (`behind`, PR31; PR34 blocked). A checkout az aktuális alapágat veszi a job idején, miközben a közölt BASE SHA az eseményből jön; a policy digest nincs a check-run kimenetében (jelentés 3.6, **PARTIAL / OPEN**).
- **Nem mért:** a check és a merge közti ablak; a változatlan HEAD/BASE melletti külső policy-változás (`strict` korlát).
- **Következtetés:** R-V.11 (a kötés a végrehajtáskor is fenn kell álljon) a S és B elemekre a `strict` + a platform merge-kapuja révén valószínűleg lefedett, a P és C elemekre **nem**; amíg nincs mérés, a P/C kötésre a megfelelőség PARTIAL / OPEN, és az ilyen döntés a spec R-V.11 szerint önmagában nem jogosít fel végrehajtásra.
- **N4** (hogyan válik az érvénytelen döntés blokkoló állapottá felülbírálati út nélkül) és **N5** (digest-kanonizálás) a megoldás részletei; N4 az időablak lezárásának módjától függ, ezért a TOCTOU után következik.

### 3.3 E2 és a jogosultság-visszavonás

- **E2 (Jel-2c):** a kibocsátó hitelesítő adatának (installation token, a mögötte lévő kulcs) a PR-ből elérhetetlensége nem bizonyított; a mért PR35 a kulcs hiányát mutatta a PR-ből, a token további csatornáit (naplók, artifactok, a job környezete, ugyanazon futásban befolyásolt lépés) nem.
- **Következtetés:** az R-I gyökere a hitelesítő adat titkossága: ha az E2 sérül, az eredmény **valódi kibocsátói identitással kibocsátott hamis döntés**, amelyet a fogyasztó (R-I.1–R-I.3 szerint) hitelesnek lát. A fogyasztó oldaláról ez nem észlelhető; az egyetlen helyreállítási út a jogosultság visszavonása (R-I.7).
- **Összefüggés E2 ↔ R-I.7 ↔ TOCTOU (következtetés):** R-I.7 a visszavonás utáni felhasználást tiltja. A kompromittálás *észlelése* azonban utólagos, ezért a visszavonás előtt, a kompromittált időszakban kibocsátott döntések **hitelesnek és (az állapotkötés szerint) érvényesnek** látszanak. A jelenlegi R-I.7 ezt nem fedi: csak a visszavonás utáni felhasználást tiltja, a visszavonást megelőző, utólag gyanússá váló döntések kezelését nem. Ez **új kérdés-jelölt (N8)**, a specifikációban nem szerepel; itt azért kerül elő, mert az E2 lezárhatatlansága esetén ez az egyetlen védelmi vonal. N8 felvétele a spec módosítása, külön döntés.
- **Jel-1 + N7:** nem mért, hogy a platform a már közzétett, hiteles check-run-t továbbra is elfogadja-e, ha a kibocsátó installációját utólag felfüggesztik; és hogy lekérdezhető-e a felhasználás pillanatában a jogosultság (R-I.1, R-I.7). Következtetés (nem mért): ha a platform a merge-nél nem értékeli újra a kibocsátó jogosultságát, az R-I.7 platformon belül csak a visszavonás utáni *új* checkekre teljesül, a már közzétett check-run maradéka a TOCTOU ablak része.

### 3.4 Függőségi gráf (egy sorban)

`N3 → {N1 + N2} → Jel-6/Jel-7 → N4, N5` · `Jel-2c → N7/Jel-1 → (N8-jelölt)` · `Jel-8` függ az N2-től (ki dönt az újrafuttatásról) és a G3-tól · `N6 → Jel-5` · `G1 + G2 → Jel-10` (Relay-specifikus csak az általános horgony után).

---

## 4. Tételek (az öt kötelező mezővel)

A „Lezáráshoz szükséges bizonyíték" a **lezárás feltétele**, nem elvégzett munka.

### G1 — Bizalmi horgony és ellenőrzési hely (P0)

**N3 — A policy határa** · P0
- *Követelmény:* R-V.1, R-V.2, R-I.4.
- *Függőség:* nincs (előfeltétele N1, N2, N5-nek).
- *Meglévő bizonyíték és korlát:* a scratch `policy.json` védett halmazt, approvers-t tartalmaz (mért, `raw/app/`); hogy a feljogosított kibocsátók halmaza és a védett halmaz definíciója hova tartozik, nincs eldöntve. Korlát: a scratch policy mérete és szerkezete nem általánosítható a Relay-re.
- *Lezáráshoz:* a P tartalmának normatív felsorolása (mit fed a digest), és annak kimondása, hogy mi nem része; review által elfogadva. Mérés nem szükséges.
- *Sorrend:* 1.

**N1 — Elvárt ellenőrző-digest bizalmi horgonya** · P0
- *Követelmény:* R-V.6, R-I.2.
- *Függőség:* N3, N2 (3.1).
- *Meglévő bizonyíték és korlát:* az App-identitás-kötés és a `strict` natív kikényszerítése mért (A1, E3s, C2); az ellenőrző digestje nem része a check-run kimenetnek (jelentés 3.6); nincs mért horgony. Korlát: a körkörösség elvi, nem mért.
- *Lezáráshoz:* döntött architektúra-leírás arról, honnan jön az elvárt C (és a bootstrap: az ellenőrző első telepítése), plusz egy scratch mérés, hogy a tárgy szerzője az elvárt C forrását nem tudja módosítani.
- *Sorrend:* 2 (N2-vel együtt).

**N2 — Az R-V.4 ellenőrzés helye és végzője** · P0
- *Követelmény:* R-V.4, R-V.5.
- *Függőség:* N3, N1.
- *Meglévő bizonyíték és korlát:* a platform natívan a S és B elemet kezeli (mért); a P és C összevetésére nincs mért mechanizmus. Korlát: a „platform nem látja a P/C-t" következtetés (3.1), nem mért.
- *Lezáráshoz:* döntött architektúra-leírás a verifier helyéről és identitásáról (R-I.1 a verifierre is), plusz scratch mérés, hogy a verifier a P- vagy C-eltérést valós Actions-futásban elutasítja.
- *Sorrend:* 2.

### G2 — Állapotkötés és időablak (P0)

**Jel-6 + Jel-7 — TOCTOU és a `strict` korlát (4/d)** · P0
- *Követelmény:* R-V.1, R-V.3, R-V.5, R-V.7, R-V.11.
- *Függőség:* N1, N2 (a P/C kötés helye).
- *Meglévő bizonyíték és korlát:* `strict: true` mellett HEAD/BASE elmozdulás elutasítva (PR31 `behind`, PR34 blocked); a checkout–BASE-eltérés és a policy digest hiánya a check-run kimenetből (jelentés 3.6, forrás `raw/app/integrity-app.yml.txt`). Korlát: a check–merge ablak és a külső policy-változás nem mért.
- *Lezáráshoz:* scratch mérések: (a) az alapág a job közben elmozdul — a döntés a közölt SHA-ból született-e; (b) külső policy-változás változatlan HEAD és BASE mellett; (c) a check–merge ablak viselkedése. Plusz a megoldás (J1–J3 a specben) mérése: a P és C a check-run kimenetében és a verifier összevetése.
- *Sorrend:* 3.

**N4 — Az érvénytelenítés megvalósítása** · P1
- *Követelmény:* R-V.8, R-V.9.
- *Függőség:* Jel-6/Jel-7, N2.
- *Meglévő bizonyíték és korlát:* a legutóbbi App-check határozza meg a merge-állapotot, az újrafuttatás felülírhat egy bukást (A4, PR29; jelentés 5). Korlát: ez a jóváhagyás utáni újraértékelés, nem az érvénytelenítés mérése.
- *Lezáráshoz:* leírt mechanizmus, amelyben az érvénytelen döntés blokkoló (nem „elutasított") állapot, és az új döntés csak az aktuális T_now-ra jön létre; scratch mérés, hogy a régi zöld nem fogadható el.
- *Sorrend:* 5.

**N5 — Digest-kanonizálás** · P1
- *Követelmény:* R-V.1, R-V.6.
- *Függőség:* N3.
- *Meglévő bizonyíték és korlát:* a scratch policy digestje a futási logban szerepel (`policy-digest=sha256:…`); a kanonizálás módja (bájtsorrend, többfájlos implementáció, függőségek, futtatókörnyezet) nincs definiálva. Korlát: a mért digest a scratch policy fájlra vonatkozik.
- *Lezáráshoz:* normatív kanonizálási szabály a P-re és C-re, tesztvektorokkal (azonos tartalom → azonos digest; egy bájtváltozás → eltérő digest); mérés lokálisan elegendő.
- *Sorrend:* 4.

### G3 — Kibocsátói jogosultság és hitelesítő adat életciklusa (P0)

**Jel-2c — E2: a token elérhetetlensége a PR-ből** · P0
- *Követelmény:* R-I.2, R-I.4.
- *Függőség:* nincs (gyökér); Jel-3 enyhíti a következményét.
- *Meglévő bizonyíték és korlát:* PR35 mutatja, hogy a PR környezetében a kulcs hiányzik, az environment-es job elutasított (`Branch "refs/pull/35/merge" is not allowed to deploy`); a token csatornái átvizsgálással, nem méréssel kezeltek (jelentés 3.4, 5).
- *Lezáráshoz:* scratch mérés a token csatornáira (naplók, artifactok, job környezet, ugyanazon futásban befolyásolt lépés) hostile PR-ral; lezáratlan marad, ha egy csatorna nem zárható.
- *Sorrend:* 3 (a P0 mérések között; az eredménye dönti el N8 súlyát).

**N7 + Jel-1 — Jogosultság-visszavonás és az installáció felfüggesztése** · P0
- *Követelmény:* R-I.1, R-I.5, R-I.7.
- *Függőség:* Jel-2c (következmény), TOCTOU.
- *Meglévő bizonyíték és korlát:* az A2 a tokenhibát mérte (hiányzó `app-id`, `blocked`, PR26); az installáció felfüggesztése nem mért, mert App-JWT, vagyis a privát kulcs kellene. A kulcsot a tulajdonos kezeli.
- *Lezáráshoz:* scratch mérés tulajdonosi lépéssel: (a) felfüggesztett installáció mellett új PR; (b) már közzétett check-run állapota felfüggesztés után; (c) lekérdezhető-e a jogosultság a felhasználás pillanatában. A kulcs nem kerül hozzám.
- *Sorrend:* 3.

**Jel-8 — Az újrafuttatás jogosultsága mint döntési jogosultság** · P1
- *Követelmény:* R-I.1, R-V.9.
- *Függőség:* N2 (ki dönt), G3.
- *Meglévő bizonyíték és korlát:* az újrafuttatás új check-runt hoz, a legutóbbi számít (A4, jelentés 5); hogy ki futtathat újra, nem értékelt.
- *Lezáráshoz:* a platform jogosultsági modelljének leírása (ki indíthat újrafuttatást), és annak kimondása, hogy az újrafuttatás nem lehet az érvénytelenítés megkerülése; mérés: a nem jogosult nem tud érvényes döntést előállítani.
- *Sorrend:* 6.

**Jel-2a — Fork-PR és második identitás** · P1
- *Követelmény:* R-I.1–R-I.3.
- *Függőség:* Jel-2c.
- *Meglévő bizonyíték és korlát:* nincs mérés. Hogy a Relay fogad-e fork-PR-t, nem ellenőrzött; a prioritás ettől függ (ha nem fogad, P2).
- *Lezáráshoz:* scratch mérés fork-PR-ral, és annak ellenőrzése, hogy a második identitás nem állíthat elő azonos nevű, elfogadott checket.
- *Sorrend:* 6.

**Jel-2b — E1 további csatornái** · P2
- *Követelmény:* R-I.2.
- *Függőség:* Jel-2c.
- *Meglévő bizonyíték és korlát:* PR35 részleges (más esemény- és workflow-típusok, fork-PR, naplók, artifactok nem mértek).
- *Lezáráshoz:* a csatornák mérése hostile PR-ral.
- *Sorrend:* 7 (Jel-2c-vel együtt végezhető, ha ott lesz mérés).

**Jel-3 — E0: túlnyújtási kísérlet** · P2
- *Követelmény:* R-I.2, R-I.4 (a következmény korlátozása).
- *Függőség:* Jel-2c.
- *Meglévő bizonyíték és korlát:* a telepítés jogosultságai pontosan a négy kért (API, mért); a nem engedélyezett műveletek próbája nem történt.
- *Lezáráshoz:* a token által megtehető, nem engedélyezett műveletek próbája (várt: elutasítva).
- *Sorrend:* 7.

### G4 — Bemeneti teljesség (P1)

**N6 — Darabszámon túli teljességigazolás** · P1
- *Követelmény:* R-C.1, R-C.4.
- *Függőség:* nincs.
- *Meglévő bizonyíték és korlát:* a scratch checker a listázott fájlokat és a `changed_files` számlálót veti össze (PR40–PR43, PR37); hiányzó+duplikált elem azonos darabszám mellett nem mért.
- *Lezáráshoz:* hiteles mechanizmus leírása az elemkészlet azonosságára, tesztek a hiányzó+duplikált esetre, és annak megállapítása, hogy a forráskorlát felett mikor elfogadható az eredmény.
- *Sorrend:* 4.

**Jel-4 — E3 további bemenetek** · P2
- *Követelmény:* R-C.2, R-C.5, R-V.12.
- *Függőség:* N6 (a bemenet-modell).
- *Meglévő bizonyíték és korlát:* hostile fájlnevek PR38 PASS; parser-hiba lokálisan `exit=1`; újsor-tartalmú fájlnév, digest-ütköztetés, szimbolikus link jóváhagyással, parser-hiba Actions-ben nem mért.
- *Lezáráshoz:* mérés az említett esetekre.
- *Sorrend:* 8.

**Jel-5 — Teljességi hibák Actions-beli esete** · P2
- *Követelmény:* R-C.2, R-C.5.
- *Függőség:* N6.
- *Meglévő bizonyíték és korlát:* az eltérés, lapozási hiba, API-hiba lokális mockkal tesztelt; Actions-ben nem.
- *Lezáráshoz:* a hibaágak kiváltása valós futásban.
- *Sorrend:* 8.

### G5 — Mérési bizonyosság (P2)

**Jel-9 — A `blocked` állapot szabályonkénti izolálása** · P2
- *Követelmény:* R-I (mérési bizonyosság).
- *Függőség:* nincs.
- *Meglévő bizonyíték és korlát:* A1–A3, A6 kontraszt-érvelés (jelenléttel `clean`, hiányában `blocked`); A6-nál a `verify` is bukott.
- *Lezáráshoz:* egyetlen szabály bukása a többi zöld mellett, mindegyikre külön.
- *Sorrend:* 9.

**Jel-11 — A code-owner szabály korábbi viselkedése, `default_workflow_permissions`** · P2
- *Követelmény:* R-I (a token hatóköre; a jóváhagyási szabályok).
- *Függőség:* Jel-3.
- *Meglévő bizonyíték és korlát:* a (d) kísérlet viselkedése diagnosztizálatlan; a repo-szintű `default_workflow_permissions` eltérése dokumentált, nem elemzett.
- *Lezáráshoz:* izolált mérés a code-owner szabályra; a permissions-eltérés hatásának leírása.
- *Sorrend:* 9.

### G6 — Relay-specifikus esetek (P3)

**Jel-10 — Relay-specifikus esetek** · P3
- *Követelmény:* R-I, R-V, R-C (a Relay-re alkalmazva).
- *Függőség:* G1, G2 lezárása (az általános modell és horgony előbb); N3 (a védett halmaz teljessége).
- *Tartalom:* GATE/BOOTSTRAP/`object_model.py`/action manipulációk, Renovate/permissions kompatibilitás, a bootstrap hét lépése, a védett halmaz teljessége, job-törlés és `if`/`needs` manipulációk, a Relay-beli `strict` viselkedés.
- *Meglévő bizonyíték és korlát:* nincs (a mérések scratch repóban készültek); semmi nem tekinthető a Relay-re igazoltnak.
- *Lezáráshoz:* külön munkacsomag a Relay-terv részeként, külön review-val.
- *Sorrend:* 10.

---

## 5. Javasolt végrehajtási sorrend

A sorrend a függőségeket követi; a **mérési** lépések mind külön GO-t igényelnek, a **tervezési** lépések nem mérnek.

| Lépés | Mi | Típus | Tételek |
|---|---|---|---|
| 1 | A policy határának rögzítése | tervezés | N3 |
| 2 | A bizalmi horgony és az ellenőrzési hely döntése | tervezés, majd mérés | N1 + N2 |
| 3 | A P0 mérések: állapotkötés/TOCTOU, E2, jogosultság-visszavonás | mérés (scratch) | Jel-6/Jel-7, Jel-2c, N7/Jel-1 |
| 4 | Kanonizálás és a teljességigazolás tervezése | tervezés (+lokális teszt) | N5, N6 |
| 5 | Az érvénytelenítés megvalósítása | tervezés, mérés | N4 |
| 6 | Újrafuttatás-jogosultság, fork-PR | mérés | Jel-8, Jel-2a |
| 7 | A hitelesítő adat csatornáinak kiegészítése | mérés | Jel-2b, Jel-3 |
| 8 | Bemeneti esetek Actions-ben | mérés | Jel-4, Jel-5 |
| 9 | Mérési bizonyosság | mérés | Jel-9, Jel-11 |
| 10 | Relay-terv | tervezés | Jel-10 |

A 3. lépés belső sorrendje: az E2 mérés előbb, mert az eredménye adja meg N8 súlyát; az installáció felfüggesztése tulajdonosi kulcs-lépést igényel.

**Amit ez a sorrend nem dönt el:** hogy az 1–2. lépés kimenete (az architektúra) milyen konkrét GitHub-megvalósítást jelent; hogy a Relay fogad-e fork-PR-t; hogy az N8 felvételre kerül-e a specifikációba.

---

## 6. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A 11 eredeti tétel és N1–N7 mind pontosan egy csoportban szerepel | Ellenőrizhető | 2. szakasz térkép | A jelentés 7. és a spec 7.1 szakaszával összevetés | A Jel-2 háromra bontása az én döntésem |
| Az R-V.5 a P és C elemekre platformon belül külön lépés nélkül nem teljesíthető | **Következtetés, nem mért** | Jelentés 3.6 (a check-run nem hordoz P/C-t, a checkout az aktuális alapágat veszi) | Scratch mérés (2–3. lépés) | Ha a platform natívan kötné a P/C-t, N2 egyszerűsödik |
| A független verifier regressziója véges, ha a horgony natívan kikényszerített | **Következtetés** | A1/E3s és C2 mért natív kikényszerítés | Architektúra-review (2. lépés) | A natív kikényszerítés Relay-ben nem igazolt |
| Az E2 sérülése hiteles identitású hamis döntést ad, a fogyasztó nem észleli | **Következtetés** | R-I szerkezet; PR35 csak a kulcsot mérte | Scratch mérés (3. lépés) | A token csatornái nem mértek |
| A kompromittált időszakban kibocsátott döntések kezelése nem fedett (N8-jelölt) | **Következtetés** | A spec R-I.7 szövege | Spec-review | Új követelmény, a spec módosítása |
| A már közzétett check-run sorsa a felfüggesztés után | **Nem mért** | Jelentés 7/1 | Scratch mérés tulajdonosi kulcs-lépéssel | A kulcs nem kerülhet hozzám |
| Az `strict: true` a S és B elemekre natívan kötést ad | Mért (scratch) | PR31, PR34 | Jelentés 3.3 | Csak a mért esetekre; a check–merge ablak nem mért |
| Az újrafuttatás felülírja a korábbi bukást | Mért (scratch) | A4, PR29; jelentés 5 | Jelentés 5 | Hogy ki futtathat újra, nem értékelt |
| A Relay fogad-e fork-PR-t | **Nem ellenőrzött** | — | A Relay repo beállításainak olvasása (olvasás, nem módosítás) | A Jel-2a prioritása ettől függ |

---

## 7. Mit nem állít ez a dokumentum

- Nem mér, nem módosít semmit; minden mérési lépés külön GO-t igényel.
- A *következtetés*-jelölésű állítások nem tények: mérésig nem használhatók a megvalósítás alapjául.
- Nem dönt a Relay-implementációról, az éles beállításról, a #212 lezárásáról (HOLD).
- Nem vezeti be az N8-at a specifikációba; csak jelzi.
- A prioritás a következményből adódik, nem a bizonyítottságból: egy P0 tétel lehet könnyen megoldható, egy P2 nehezen.
