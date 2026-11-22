# #212 — Az M-E1 P és S/R mérőcsomag terve, 1. fázis (06t)

**Státusz: terv (concept), nem végrehajtás.** Nem készült workflow-fájl, szkript vagy kód; nem indult futás; az X repón nem történt írás. A pull_request-eseményre vonatkozó állításalakok (`sub`, `ref`, `sha`, `workflow_ref`, `event_name`, `head_ref`, a futás `path` és `head_branch` mezője) **dokumentált, nem mért hipotézisek** (2. szakasz); a terv a megcáfolásukat is előírja. A terv megléte ≠ működik, a terv elfogadása ≠ sikeres mérés. **Az M-E1 ítélete (PASS / FAIL / INCONCLUSIVE) nyitott, előzetesen `INCONCLUSIVE`**; ez a dokumentum nem mondja ki. **Egy lehetséges későbbi `PASS` hatóköre a vizsgált elfogadási és támadási modellre (P-a, P-b, same-repo PR) korlátozott; a P-c nem vizsgált** (1.1). **Érvényes token semmilyen csatornán nem publikálható** (4. szakasz). A végrehajtás külön tulajdonosi GO, külön megvalósítási csomaggal és review-val. K-5: 8/300.

## 1. Mit kell eldönteni, és mit nem

| Tétel | Kérdés (a #81 szerint) | Ez a terv |
|---|---|---|
| **P** | a PR szerzője módosíthatja-e a bizonyítékot, vagy elfogadtathat-e olyat, amely a védett futás bizonyítékának látszik | mérési protokoll valódi PR-futásokkal és offline hamisítási kontrollokkal |
| **S** | egy másik futás bizonyítéka elfogadható-e a kért helyett | valódi adaton (két futás) és az offline keresztezett bizonyítékokon |
| **R** | egy régi futás bizonyítéka elfogadható-e új commitra | a PR merge-commit mint másik commit; a tiszta eset külön döntés (D7) |
| artifact-attestáció | a platform kínál-e további igazolást | **nincs a csomagban**, külön döntés (D5) |
| fork-PR | külső (fork) szerző befolyása | **kívül marad** (D1): külső identitás (B sor) kell hozzá |

**A terv a #81 „PK a mérőeszközt ellenőrzi, nem a hipotézist" elvét követi:** a kontrollok nem függnek attól, hogy a platform bizonyítéka eltér-e.

### 1.1 A P három külön tulajdonsága, és hogy a PASS melyiket fedi (review F1)

A #81 PASS-feltétele: „a PR szerzője **nem módosíthatja**". Ez három külön tulajdonságra bontható; **a terv kontrolljai közülük az első kettőt fedik, a harmadikat nem**:

| Tulajdonság | Mit jelent | Lefedettség a tervben |
|---|---|---|
| **P-a** — elfogadtathatóság | a PR szerzője elfogadtathatja-e a verifierrel **egy másik futás, commit, esemény vagy workflow** hiteles bizonyítékát a védett futás helyett | **vizsgált**: P1, P2, S, R, a keresztezett bizonyítékok |
| **P-b** — módosíthatóság | a szerző módosíthatja-e az **aláírt állításokat és a kísérő adatokat** (manifest, API-metaadat, önbevallás) úgy, hogy a verifier elfogadja | **vizsgált, korlátozottan**: a hamisítási kontrollok F-a…F-e (offline, a valódi tokenekkel); a szerző *workflow-viselkedése* nem mért (4. szakasz) |
| **P-c** — előállítás, kiválasztás, elnyomás, publikálás | a szerző **nem állít elő, elnyom, lecserél vagy szelektíven publikál** bizonyítékot; több futást indíthat és a kedvezőt választhatja; írási joggal a főági workflow-t is elindíthatja; az időzítést és a szerző-választott szövegeket (`workflow` név, ágnév) befolyásolhatja | **nem teljesen vizsgált**: a verifier fail-closed (a hiányzó bizonyíték `NOT-READ`, nem elfogadás), de a szerző befolyása a kiválasztásra, az időzítésre és a publikálásra **nem mért** |

**A PASS hatóköre ezért** nemcsak a same-repo PR-ra, hanem a **ténylegesen vizsgált elfogadási és támadási modellre (P-a, P-b)** korlátozott. **Ha a #81 P-feltétele ennél erősebbet követel (a P-c-t is), az M-E1 `INCONCLUSIVE` marad**; ennek értelmezése a D8 tulajdonosi döntés.

## 2. Fenyegetési modell és bizalmi határok

**Szereplők.** *PR-szerző (támadó):* ír egy ágat az X repóban, és PR-t nyit; ő kontrollálja a PR-ben a workflow-fájlok tartalmát, nevét, útvonalát, a `name:` és `job` neveket, a lépések logikáját, azt, hogy kér-e tokent és milyen közönséggel, és hogy mit publikál. *Tulajdonos (jóindulatú):* futtatja a szkripteket, jóváhagy, olvas. *GitHub:* kibocsátó és API; **a bizalmi gyökér** (a #91 5. szakasza szerint: az aláírás ellenőrzése a futás kódjától függetlenül végezhető, de nem a GitHubtól). *Olvasó:* a `read-me1.py`; nem a Relay-implementáció.

**Megjegyzés a P-c-hez:** a same-repo PR-szerző **írási jogú**, ezért a főági `workflow_dispatch`-et is elindíthatja, több futást indíthat, és a kedvezőt választhatja. Egy ilyen főági futás bizonyítéka **valódi főági bizonyíték**, nem hamisítvány; a kérdés az, hogy a verifier **mit kér** (konkrét futás, kísérlet, commit), és mi történik, ha az nem érhető el (fail-closed). Ezt a terv **nem méri** (1.1).

**Mit kontrollál a támadó, és mit nem (hipotézisek, a mérés tárgya):**

| # | Hipotézis (dokumentált, **nem mért**) | Várt érték same-repo PR-nál | Hogyan bukhat meg |
|---|---|---|---|
| H1 | a PR-futásban `event_name` `pull_request` | a főági futás `workflow_dispatch` | ha egyező: a támadó a főági eseményt utánozná |
| H2 | a `ref` és a `workflow_ref` ref-része `refs/pull/N/merge` | a főági `refs/heads/main` | ha `refs/heads/main`: a támadó a védett ref alatt futna |
| H3 | a `sha` a PR merge-commitja, nem a főág feje; az API `head_sha`-ja a PR fejé lehet, **más**, mint a token `sha`-ja | a főági `4d432f5e…` | ha a főági fej: a támadó a védett commitot utánozná; az eltérés alakját a mérés rögzíti, az olvasó profilja ebből épül |
| H4 | a `sub` pull_request-alakú (várhatóan `…:pull_request`, azonosítókkal) | a főági `…:ref:refs/heads/main` | ha egyező: a subject nem különböztet |
| H5 | a `head_ref`/`base_ref` kitöltött | a főági üres | informatív |
| H6 | a `workflow` állítás (a workflow `name:`-je) **a szerző által választott szöveg** | — | ha a szerző azt választja, hogy egyezzen a védettével: a névre kötés **nem biztonságos** (a verifier nem köthet rá) |
| H7 | a futás `path` és `head_branch` mezője PR-futásnál más alakú (pl. `@refs/pull/..` utótaggal, a PR ágneve) | a főági `.github/workflows/me1-evidence.yml`, `main` | az eltérés alakját a mérés rögzíti |
| H8 | same-repo PR-ban a workflow kaphat `id-token: write`-ot | fork-PR-ban nem (dokumentált) | ha nem kap: a P `NOT-READ`, nem `PASS` |

**Amit a terv nem feltételez:** hogy a PR-futás tokenje „rosszabb" a főáginál. A kérdés, hogy a **verifier** a főági elvárásaival (ref, esemény, commit, workflow-útvonal) elutasítja-e, bármit is tesz a szerző.

**Bizalmi határok (a #91 5. szakaszának folytatása):**
1. A kibocsátó nyilvános kulcsai a tulajdonos gépén, TLS-en, közvetlenül a kibocsátótól, a bizonyítékcsomagon **kívül** (`fetch-jwks.sh`, `--trusted-jwks`).
2. A PR-futás workflow-ja **a szerző kontrollja alatt van**: a mérésben a szerzőt mi játsszuk, ezért a PR-ben szereplő fájlok **rögzített, review-zott szövegek** (blob-ellenőrzéssel szállítva); a támadó viselkedését a **hamisítási kontrollok** (5. szakasz) modellezik offline, **nem** olyan workflow-val, amely érvényes tokent publikálna.
3. **A mérési workflow nem használ titkot**: a fájlok tiltják a `secrets.*` és az `environment:` használatát, és az ellenőrző a teljes szöveg egyezését kényszeríti ki. **Ez nem a platform által kikényszerített hozzáférési tilalom**: a same-repo PR-futás **dokumentáltan, nem mért módon** hozzáférhet a repó-titkokhoz (az X repóban a `CANARY_UNRESTRICTED` repó-szintű, értéktelen kanári). A same-repo PR jogosultsági modellje **külön biztonsági kérdés marad**, amelyet ez a terv nem old meg és nem mér.
4. Az olvasó és a gyűjtő a már review-zott lánc kiterjesztése (8. szakasz), nem új, ellenőrizetlen eszköz.

## 3. A mérési protokoll (a megvalósítás után, külön GO-val)

### 3.1 A kísérleti elrendezés

**Egyetlen eldobható PR az X repón** (`p-probe` ág → `main`), amelyet **nem mergelünk**, és a mérés után a tulajdonos lezár. Az ág push-a önmagában nem indít futást; **a PR megnyitása a mérés indítása** (a `pull_request` esemény), ezért a PR létrehozásának külön GO-ja és állapotjelzője (`.state`) van.

| Futás | Mi váltja ki | Tartalom (a PR-ben) | Mit mér |
|---|---|---|---|
| `lab-gate-pr` | a PR megnyitása (a meglévő workflow) | változatlan | nem mérési futás, a K-5-be beszámít |
| **P1** — a védett workflow módosítása a helyén | a PR megnyitása | a `.github/workflows/me1-evidence.yml` **módosítva**: `pull_request` trigger hozzáadva (a lejárat-kapus törzs és a közönség `me1-evidence` **változatlan**) | milyen állításokat ad ugyanarra a fájlútvonalra a PR-verzió; elutasítja-e a főági elvárású verifier |
| **P2** — azonos nevű másik workflow | a PR megnyitása | **új** fájl (más útvonal), azonos `name:` és job-névvel, azonos lejárat-kapus törzzsel és közönséggel | a név- és job-névazonosság (H6) nem ad-e a verifiernek hamis megerősítést |
| **S-valódi** (ajánlott, D6) | `workflow_dispatch` a `main`-ről | a meglévő `me1-evidence.yml` változatlanul | a tiszta S: ugyanaz a workflow és ref, **csak a futás** más |

A PR-futások (a H3 szerint, **dokumentált, nem mért**) a **PR merge-commitján** futnak, amely **másik commit**, mint a főág feje: ez adná az R valódi adatát (3.3); ha a mérés mást mutat, az R valódi adata is más.

**Ugyanaz a közönség (`me1-evidence`) minden futásban.** Ez szándékos: ha a közönség eltérne, a főági elvárású verifier már emiatt elutasítaná a PR-tokent, és a kötő állítások (`workflow_ref`, `ref`, `sha`, `event_name`, `sub`) szerepe elfedődne. A kontroll csak akkor érvényes, ha az elutasítás okai között a kötő állítások szerepelnek (5. szakasz).

### 3.2 Sorrend (mindegyik lépés külön tulajdonosi GO, a megvalósítás merge-e után)

1. **Szállítás:** a tulajdonos szkriptje a jóváhagyott factory-commitból a két PR-fájlt egy új ágra írja (blob-ellenőrzéssel, push nélkül); a tulajdonos pushol.
2. **PR megnyitása** (a mérés indítása): egyetlen indítás, `.state` védelemmel; a szkript megtagadja a másodikat.
3. **Várakozás:** a futások párhuzamosan ≈ 7–8 percig tartanak (a token lejáratáig). Visszatartás (P3) esetén a jóváhagyás a tulajdonos döntése a weben; a 2. kísérlet ugyanazon futás újabb kísérlete. **Automatikus újrafuttatás nincs.**
4. **Letöltés és kiolvasás** futásonként (`fetch` a tulajdonos GO-jával): új kimeneti könyvtár, kötés a futáshoz, kísérlethez és commithoz, a bizalmi gyökér külön fájlban.
5. **A PR lezárása** a tulajdonos által (nem merge); az ág törlése külön döntés (D4).
6. **S-valódi** (ha D6 igen): külön `workflow_dispatch`, külön GO.

### 3.3 Mit jelent az S és az R valódi adaton

- **Definíciók (review F2):** **S:** azonos commit, workflow és ref, **különböző futás**. **R:** azonos workflow és ref, **különböző commit és futás**. A valódi adaton a futás-különbség **nem egyváltozós**: két futás tokenje a `run_id`-n túl az `iat`, `exp`, `nbf`, `jti`, `run_number`, `check_run_id` állításban és az artifact-eredetben is eltér; egy új commiton végrehajtott futás szükségszerűen új futás is. **Az izolált, egyváltozós kontroll a szintetikus selftest** (a meglévő `R: evidence of another head`, `S: evidence of another run id`, az állításonkénti eltérések); a valódi és a szintetikus kontroll **együtt** adja az elfogadási alapot.
- **S valódi adaton:** a második főági futás (B, D6) bizonyítéka az A helyett → az elutasítás indokai a `run_id`, `run_attempt`, az artifact-eredet és a manifest-kötés (a futásonként változó többi állítás mellett); minden kötő állítás (`sha`, `ref`, `workflow_ref`, `event_name`, `sub`) **azonos**, tehát a futás-azonosság kötése a mérés tárgya. A P1/P2 bizonyítéka az A helyett **nem S**, hanem P-a (más workflow/ref/esemény is).
- **R valódi adaton:** a főági A bizonyítéka a PR merge-commitjára elvárva és fordítva **nem tiszta R**: a PR-futás a commiton kívül a `ref`-ben, az eseményben és a `sub`-ban is eltér. **A különböző commitú, azonos ref-ű és workflow-jú valódi R** új főági commitot és dispatch-futást igényelne (D7: **HOLD, egyelőre nem szükséges**). A jelentés kimondja a korlátot: a `sha`-kötés valódi adaton csak a PR merge-commit különbségével (nem tiszta), izoláltan a szintetikus tesztben igazolt.

## 4. Token-kezelés: érvényes token semmilyen csatornán nem publikálható

A szabály minden futásra, **a támadói modell futásaira is**.

1. **Csak lejárat-kapus publikálás** (a #89/#91 mechanizmusa, változatlanul): a token csak shell-változóban él; a lépés kiolvassa az `exp`-et; ha az hiányzik, nem szám, vagy 600 s-nál messzebb van, **fail-closed** (nincs token, nincs feltöltés); `exp + 121 s`-ig vár; az órát szigorúan újraellenőrzi (`> exp + 120 s`); csak ekkor írja a fájlba. Az olvasó a szerveroldali artifact-létrehozási időt is ellenőrzi (≥ `exp + 60 s`).
2. **Tiltott csatornák (az ellenőrző beültetett hibákkal védi):** napló (`echo`, `cat`, `tee`, `/dev/stderr`), `$GITHUB_STEP_SUMMARY`, `::notice`/annotáció, PR- vagy issue-komment, cache, `GITHUB_ENV`/`GITHUB_OUTPUT`, bármely hálózati kérés (a `curl` kizárólag a futtató saját token-végpontjára), az `ACTIONS_ID_TOKEN_REQUEST_TOKEN` kiírása.
3. **A támadói viselkedés nem valósul meg érvényes tokennel.** A „rosszindulatú" PR-szerző lehetőségeit (más közönség kérése, más csatornára publikálás, korai feltöltés) **nem futtatjuk**: ezeket offline, a valódi tokenek keresztezésével és a manifest/API hamisításával modellezzük (5. szakasz), mert egy ilyen valódi futás **maga lenne a token-kitettség**. Ez a terv kifejezett korlátja: a támadó *workflow-viselkedését* nem mérjük, csak azt, hogy a **verifier** mit fogad el.
4. **A P1/P2 fájlok fix, review-zott szövegek**, az ellenőrző (a `check-me1-workflow.py` mintájára) a teljes dokumentum- és `run`-test-egyezést kéri; titok- és környezet-hivatkozás, hálózati parancs a `curl` token-kérésén kívül, `github.event.*` használat tiltott.
5. **Ha a PR-futásban a token nem kérhető** (H8: nincs `id-token` jog): a futás fail-closed leáll; a P **`NOT-READ`**, nem `PASS`.
6. **Alternatíva a döntéshez (D2):** a PR-futásokból csak a **dekódolt állítások** (nem a teljes token) és a token SHA-256-ja publikálandó. Előny: soha semmi, ami a tokenhez hasonlít, nem kerül a nyilvános artifactba. Hátrány: a PR-token aláírása nem ellenőrizhető offline; a P kérdése (a verifier elutasítja-e) a hamisítási kontrollokban a **teljes** tokent igényli. Ajánlás: a lejárat-kapus (1. pont) mechanizmus, mert bevált és a #91 review-ja elfogadta.

## 5. Negatív kontrollok és pozitív kontroll (PK)

**PK (#81 2.2): (U) és (J), szintetikus, a hipotézistől függetlenül.** (U) ültetett: két ismerten eltérő rekord (minden mezőre külön) → az összehasonlító észleli; (J) ismert jó: két azonos rekord → nincs riasztás. A meglévő `--pk` és selftest lefedi; a megvalósítás a PR-futás állításkészletére (`head_ref`, `base_ref`) bővíti. A PK nem teljesülése → INCONCLUSIVE.

**Hamisítási kontrollok (P, offline, a valódi PR-tokenekkel, K-5-be nem számítanak):** a P1 (és P2) valódi tokenje a következő csomagokban kerül a **főági profilú** verifier elé:

| # | A csomag | A támadó mit állít | Elvárt eredmény |
|---|---|---|---|
| F-a | a PR-futás valódi manifestje és API-metaadata | semmit nem hamisít | `NOT-MET` (esemény, ág, útvonal-alak a manifestben) |
| F-b | a PR-token + a **főági-nak kinéző** manifest és `api/run.json` (hamisított) | a futás főági | `NOT-MET`: az aláírt `event_name`, `ref`, `workflow_ref`, `sha`, `sub` eltér a (hamisított) API-tól és a főági elvárástól |
| F-c | mint F-b + a hamisított önbevallás (`context.json`) a főági értékekkel | az önbevallás is főági | `NOT-MET` (az önbevallás nem bizonyíték; az aláírt állítások döntenek) |
| F-d | a PR-token + a **PR-nak megfelelő, konzisztens** manifest, de főági elvárással | — | `NOT-MET` (a kötő állítások a főági elvárástól eltérnek) |
| F-e | a PR-token aláírásának módosítása (egy bit) | aláírás-hamisítás | `NOT-MET` (aláírás) — a primitív selftest már fedi |

**Elfogadási feltételek a kontrollokra (három szint, review F4):**
1. **Kötő-állításos kontrollok** (F-a, F-b, F-c, F-d, S1, S3, R1, R2): `NOT-MET`, és az elutasítás indokai között legalább **egy kötő állítás** (`workflow_ref`, `ref`, `sha`, `event_name`, `sub`, `run_id`, `run_attempt`) szerepel, **nemcsak** a `aud`, `iat`/`exp` vagy a manifest-szerkezet. Ez zárja ki, hogy a kontroll egy mellékes eltéréstől „teljesüljön".
2. **Aláírás-kontroll** (F-e): az **érvénytelen aláírás önmagában elegendő és elvárt** elutasítási ok: érvénytelen aláírásnál az állítások nem tekinthetők hitelesnek, ezért kötő állításos indok **nem követelhető**. Feltétel: az `OIDC signature` sor `NOT-MET`, és az olvasó **nem értékeli hitelesként** az állításokat (a kötési sorok ilyenkor tájékoztató jellegűek).
3. **Integritás-kontroll** (S2: a manifest digest-integritása): a manifest-digest sor (`run binding`: a fájl eltér a jegyzék digestjétől) `NOT-MET`; kötő állításos indok itt sem követelhető, mert a bizonyíték csomagszinten sérült.

**S offline kontrollok (valódi tokenekkel, ingyenes):** (S1) az A tokenje a B (vagy P1) API/manifest oldalával → `NOT-MET` (`run_id`, `run_attempt`, `sha`); (S2) a B tokenje az A manifestjével → `NOT-MET` (digest); (S3) a támadó-konzisztens manifest + a B tokenje + az A API-ja → `NOT-MET` (állítások ≠ API).
**R offline kontrollok:** (R1) az A bizonyítéka a PR merge-commitjára elvárva → `NOT-MET` (`sha`); (R2) a P1 bizonyítéka a főági fejre elvárva → `NOT-MET` (`sha`, `ref`).

## 6. Elfogadási kritériumok és az M-E1 ítélet-leképezés

| Feltétel | Teljesül, ha | Nem teljesül / következmény |
|---|---|---|
| **C1** (kész) | a platform által aláírt bizonyíték a négyest köti (`EVIDENCE BOUND`) | — (a #91 szerint `MET`) |
| **C2 — P-a és P-b** | a P1 és a P2 futás **elérhető** (token kapható), és minden kontroll az 5. szakasz három szintje szerint teljesül (F-a…F-d kötő állítással, F-e aláírással, S2 digesttel indokolva); a PR-futás kötő állításai (`ref`, `sha`, `event_name`, `workflow_ref`, `sub`) legalább egyikben eltérnek a főágitól mindkét futásban | ha bármelyik hamisítás **elfogadott** → a P **bukott**; ha a futás vagy a token nem elérhető → `NOT-READ`/`INCONCLUSIVE` |
| **C2c — P-c** | **nem része az elfogadásnak** (1.1): a szerzői befolyás a kiválasztásra, elnyomásra, időzítésre és publikálásra nem mért; a verifier fail-closed viselkedése tervezési követelmény | ha a D8 szerint a P-c is kötelező → az M-E1 `INCONCLUSIVE` |
| **C3 — S** | a második főági futás (D6) valódi S-kontrollja (azonos commit, workflow, ref; különböző futás) és az offline S1–S3 mind `NOT-MET` a megfelelő indokokkal (`run_id`, `run_attempt`, artifact-eredet; S2: digest); az izolált egyváltozós kontroll a szintetikus selftest | D6 nélkül az S **legfeljebb részleges** (a jelentésben jelölve) |
| **C4 — R** | az R1–R2 `NOT-MET` a `sha`-val (és a többi eltérő állítással) indokolva **és** a szintetikus izolált `sha`-teszt zöld; a különböző commitú, azonos ref-ű és workflow-jú valódi R (D7) **HOLD** | a jelentés kimondja, hogy a valódi R nem tiszta (nem egyváltozós) |
| **C5** | a tulajdonos döntése az artifact-attestációról (D5) | döntés nélkül az M-E1 `INCONCLUSIVE` marad |
| **PK** | (U) és (J) teljesül a PR-állításkészletre is | `INCONCLUSIVE` |

**Az M-E1 ítélete (a mérés utáni jelentésben, nem az eszközben):**
- **PASS:** C1–C4 teljesül és a PK zöld, a C5 a D5 szerint rendezett, **és a D8 szerint a #81 P-feltétele a P-a/P-b-re értendő**; **a PASS kimondása kifejezetten a same-repo PR-ra és a ténylegesen vizsgált elfogadási és támadási modellre (P-a, P-b) szűkített hatókört viseli** (fork-PR nem vizsgált, D1; a P-c nem vizsgált, 1.1).
- **FAIL:** egy támadó-variáns bizonyítéka a főági verifierrel **elfogadott** (a PR-szerző a védett bizonyítékot utánozni tudja), vagy csak önbevallás érhető el.
- **INCONCLUSIVE:** minden más eset (hiányzó vagy visszatartott futás, nem kapható token, a lejárat-kapu fail-closed leállt, a PK nem teljesül, a C3/C4 részleges, a C5 nyitott, **vagy a D8 szerint a P-c is kötelező**).

**Nem következtethető:** `PASS` a fork-PR-ra és a P-c-re (a szerzői kiválasztás, elnyomás, publikálás befolyására); `PASS` egy futásból az időbeli stabilitásra; általánosítás más szervezetre, a Relay-re vagy a production-re.

## 7. K-5 keretigény (becslés, nem mért; kísérletenként, a tulajdonos szabálya szerint)

| Lépés | GO | Kísérlet (alap) | Legfeljebb (a visszatartásokkal) |
|---|---|---|---|
| A megvalósítás helyi tesztjei, a terv és a szállítás előkészítése | megvan / külön | 0 | 0 |
| A PR megnyitása: `lab-gate-pr` + P1 + P2 | külön GO | 3 | 5 (a P1 és P2 visszatartható; a `lab-gate-pr` **eddig** két futásnál nem volt visszatartva: ez korábbi megfigyelés, nem garancia) |
| S-valódi: második főági dispatch (D6, ajánlott) | külön GO | 1 | 2 |
| **Összesen (D6-tal)** | | **4** | **7 (feltételes felső becslés)**; ha a `lab-gate-pr` is visszatartott: **8** |
| Opcionális tiszta R: új főági commit (PR + merge: 2) + dispatch (D7) | külön GO | 3 | 4 |

**Keretigény: 8 + 4 = 12 / 300 (D6-tal); feltételes felső becslés 15 / 300 (a `lab-gate-pr` visszatartásának kizárása korábbi megfigyelésen alapul, nem garancia; visszatartásával 16 / 300); D7-tel (HOLD) további legfeljebb +4.** A hamisítási kontrollok, az offline S/R és a helyi tesztek nem fogyasztanak keretet. **Leállási küszöbök (#82 4. szakasz):** ha egy tétel 3 egymás utáni futása magyarázatlanul eltérő eredményt ad, vagy a futások száma eléri a 250-et megoldatlan INCONCLUSIVE-okkal, a mérést szüneteltetni és a tulajdonost értesíteni kell. **Automatikus újrafuttatás nincs**: minden újabb futás új GO.

## 8. A megvalósítási csomag tartalma (külön GO, külön review; ebben a PR-ban NINCS megvalósítás)

1. **A P1 és P2 workflow-fájl** és az ellenőrzőjük (`check-me1-p-workflows.py`): teljes dokumentum- és `run`-test-egyezés, beültetett hibák (titok- és környezet-hivatkozás, hálózati parancs, korai feltöltés, a token kiírása minden csatornán, más közönség, `github.event.*`, a lejárat-kapu bármely elemének hiánya), a tiltott-token lista nélkül is elutasítva.
2. **Az olvasó és a gyűjtő bővítése** (`--profile main|pr`): a PR-futás várt alakjai (esemény, `head_branch`, a `path` alakja, a kötő állítások) **a mért értékekből**, nem a dokumentációból (a 06r tanulsága: a `sub` alakja); a profilok közötti negatív tesztek; az elutasítási indokok **listázása** (a „kötő állítás szerepel" elfogadási feltétel gépi ellenőrzése).
3. **A hamisítási és keresztezési kontrollok automatizálása** (F-a…F-e, S1–S3, R1–R2) a valódi bizonyítékból összeállított, offline csomagokkal.
4. **A tulajdonosi szkriptek:** szállítás (blob-ellenőrzés, push nélkül), a PR megnyitása egyetlen indítással és `.state` védelemmel, futásonkénti letöltés és kiolvasás a tulajdonos GO-jával.
5. **A tesztek:** mockolt lánc, szimulált óra a lejárat-kapura, parancssori belépési pontok alfolyamat-hívással, mutációs ellenőrzések (a kontrollok tudnak bukni).

## 9. Tulajdonosi döntési pontok

| # | Döntés | Ajánlás |
|---|---|---|
| **D1** | A P hatóköre: csak same-repo PR, vagy fork-PR is (külső identitás, B sor kell) | **same-repo**; a fork-PR külön, a B sor után; a PASS hatóköre kimondott (same-repo PR és a vizsgált P-a/P-b modell, 1.1) |
| **D2** | A PR-futások publikálási módja: lejárat-kapus teljes token (A), vagy csak dekódolt állítások és digest (B) | **A** (bevált, a #91-ben review-zott); B tartalék |
| **D3** | P1 és P2 együtt, vagy csak P1 | **együtt** (egy PR, két futás): a név-hamisítás (H6) a P1-ből nem látszik |
| **D4** | A PR és a `p-probe` ág sorsa a mérés után | a PR lezárása a tulajdonosé; az ág törlése külön döntés (a törlés írási művelet) |
| **D5** | Az artifact-attestáció (`attestations: write`, külön action) bekerül-e az M-E1 ítéletébe | **külön csomag vagy kifejezett kizárás**; döntés nélkül az M-E1 `INCONCLUSIVE` |
| **D6** | Második főági `workflow_dispatch` futás a tiszta S-hez | **igen** (≤ 2 kísérlet) |
| **D7** | Új főági commit és dispatch a különböző commitú, azonos ref-ű és workflow-jú valódi R-hez | **HOLD, egyelőre nem szükséges**; az R1–R2 + a szintetikus `sha`-teszt elfogadott; a jelentés kimondja, hogy a valódi R nem egyváltozós |
| **D8** | A #81 „a PR szerzője nem módosíthatja" feltételének értelmezése: P-a/P-b, vagy a P-c is | **P-a/P-b**; a P-c külön tulajdonság (fail-closed verifier, nem mért szerzői befolyás); ha a P-c is kötelező, az M-E1 `INCONCLUSIVE` marad |

## 10. Kockázatok

| Kockázat | Védelem |
|---|---|
| Érvényes token kitettsége | 4. szakasz: lejárat-kapus publikálás, a támadói viselkedés nem fut, fail-closed, az olvasó szerveridős ellenőrzése |
| Titok-hozzáférés a PR-futásban (a repó-szintű kanári) | a mérési workflow nem használ titkot (ellenőrző); a platform nem tiltja a hozzáférést (dokumentált, nem mért), a kanári értéktelen; a same-repo PR jogosultsági modellje külön kérdés |
| A PR véletlen mergelése | a PR nem mergelendő; a tulajdonos lezárja; a `main` védett (`lab-gate`) |
| A PR-futás visszatartása (P3) | előre betervezve a K-5-ben; a jóváhagyás a tulajdonos döntése; nincs automatikus újrafuttatás |
| A főági `me1-evidence.yml` véletlen módosulása | a PR csak egy ágon módosítja; a szállítás előtt/után a `main` blobja ellenőrzött |
| A PR-futás alakjára vonatkozó téves feltételezés (H1–H8) | a profilok mért értékekre épülnek; a hipotézis megcáfolása érvényes eredmény |
| Egy futás, egy szervezet, egy pillanatkép | az általánosítás tilos; a PASS hatóköre kimondott |

## 11. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A PR-futás állításalakjai (H1–H8) | **dokumentált, nem mért** | 2. szakasz táblázata | a P1/P2 futás kiolvasása | a hipotézis megbukhat; az olvasó profilja a mért értékekre épül |
| A kontrollok az elutasítás indokaiként a kötő állításokat is megkövetelik | tervezett követelmény | 5. szakasz | a megvalósítás gépi ellenőrzése | a megvalósítás review-ja |
| Érvényes token sehol nem publikálódik a PR-futásokban sem | tervezett követelmény + a #91-ben mért mechanizmus | 4. szakasz; a 06q/06r lejárat-kapus bizonyíték | az ellenőrző beültetett hibái, a szimulált órás teszt, a szerveridős olvasó-sor | az élettartam és az óra stabilitása nem mért |
| Az S valódi kontrollja a második főági futás (azonos commit, workflow, ref); a valódi adaton a futás-különbség nem egyváltozós | következtetés a tervből, nem mért | 3.3 | D6; az izolált kontroll a szintetikus selftest | — |
| A különböző commitú, azonos ref-ű és workflow-jú valódi R új főági commitot igényel, és nem egyváltozós | következtetés a tervből, nem mért | 3.3 | D7 (HOLD) | a jelentés kimondja a korlátot |
| A PASS a P-a/P-b modellre korlátozott, a P-c nem vizsgált | tervezett hatókör | 1.1, 6. szakasz | D8 | ha a #81 a P-c-t is követeli: INCONCLUSIVE |
| A mérési workflow nem használ titkot; a platform hozzáférési tilalmat nem kényszerít ki | tervezett követelmény; a platform viselkedése dokumentált, nem mért | 2. szakasz 3. pont | az ellenőrző teljes-szöveg-egyezése | a same-repo PR jogosultsági modellje külön kérdés |
| A P1/P2 eredménye a PR-szerző befolyásáról | **nem állítom** | — | a mérés (külön GO) | — |
| Az M-E1 ítélete | **nem állítom; előzetesen INCONCLUSIVE** | — | a mérés utáni jelentés | — |
| A K-5 keretigény: alap 4, **feltételes felső becslés** 7 kísérlet (D6-tal) | **becslés, nem mért** | 7. szakasz | a tényleges futások listája | a visszatartások és az újrafuttatások |
| Az X repó vagy az éles szervezet módosult | nem (**végrehajtási naplóra alapozott állítás**) | a terv készítésekor csak helyi fájlműveletek; írást az X repón kizárólag a tulajdonos végezne | a session végrehajtási naplója; a `git log` ezt nem bizonyítja | a napló az én oldalam |

## 12. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét, és nem állítja, hogy a PR-szerző nem befolyásolhatja a bizonyítékot.
- **Nem tekinti mértnek** a pull_request-esemény állításalakjait; azok hipotézisek.
- **Nem tartalmaz** megvalósítást, workflow-fájlt, szkriptet, futást, PR-nyitást vagy bizonyíték-letöltést; ezek külön GO-t igényelnek.
- **Nem terjeszti ki** az eredményt fork-PR-ra, más szervezetre, a Relay-re vagy a production-re.
- **Nem módosítja** a #81–#91 tartalmát és a K-1–K-8 ajánlásokat.
