# relay-ci-parity-05-seeded-defects — seeded defect esetek és a CI önteszt

## Kontextus

A `CentralInfraCore/CIC_Relay` **#169** issue (másolat: `ref/issue-169-body.md`) tízlépéses PR-sorozat.
**Ez a job a PR-05-öt fedi:** „Seeded defects and CI self-test”, záró feltétel: *szándékos hibák igazoltan pirosra váltanak*.

Előzmények (mind mergelve, a `main` CI zöld):

- PR-02: a Rust felsorolás fail-closed; PR-03: a teljességi verifier és a terv-állapotok — `ref/pr03-report.md`.
- PR-04: az objektumszintű mérési modell (`object-id/1`, `object-evidence/1`), az L1/L2/L3 verifier — `ref/pr04-report.md`.
  A Relay `main` fej: `d38a1d597e208ae0fe1f963d2b52ae71c639ff2e`; a cic-factory `main` fej: `ca13ddfa3e8550169c13d86e0c27e318c6e081d1`.

**A PR-05 célja nem több kapu, hanem az, hogy az ellenőrzőrendszer saját hibafelismerő képessége bizonyított legyen:** minden
kapu ellen szándékosan előidézett hibával megmérjük, hogy tényleg pirosra vált, és **minden negatív esethez tartozik egy pozitív
kontroll** (a hibátlan bemenet zöld). A tulajdonos döntése és a kötelező esetek: `ref/owner-decisions-pr05-2026-11-15.md`.

**Ez a spec külön felülvizsgálatra készül; a job indítása a spec review-ja és mergelése után történik.** A PR-05 implementációt ad
(a CIC_Relay scriptjeit, tesztjeit és report-only workflow-ját módosítja, és PR-t nyit a CIC_Relay felé), de **csak az alábbi hatókörben**.
Új küszöb, új blokkoló kapu és toolchain-csere **nincs**.

## Amit a PR-04 verifier ma NEM tud (a spec kiindulópontja, a forrásból és a mérésből)

A PR-04 jelentése és a `scripts/object_model.py` olvasata szerint a verifier gyengeségei (**ellenőrizd, ne higgy a spec szövegének**):

1. **Az L3 darabszámot hasonlít, nem halmazt.** A Go-oldalon az objektumok száma a független `func`-sor-számmal; egy objektum törlése és egy kitalált beszúrása
   ugyanazt a számot adja, és az L3 nem veszi észre. A Rust-oldalon csak az „a `cargo-mutants` által ismert függvényeknek van objektuma” részhalmaz-ellenőrzés van.
2. **Nincs független Rust-objektumleltár**, ezért az L3 Rust-része mindig `PARTIAL`, és az L3 **soha nem lehet `PASS`** (`COMPLETE_FOR_SCOPE`).
3. **A mérési értékeket a verifier nem vezeti le újra a bemenetekből.** Az L2 a bemeneti fájlok digestjét hasonlítja a rekordban lévővel; egy objektum `coverage`-értékét
   megváltoztató és a digestet következetesen újrapecsételő hamisítást (a bemeneti fájlok érintetlenek) sem az L1, sem az L2, sem az L3 nem fogja meg. (Mérd meg, mielőtt javítod.)
4. **Az azonos azonosítójú duplikátumot az L1 fogja** (`ids are not sorted and unique`), nem az L3: a tulajdonos táblázata L3 FAIL-t ír. **Ezt a különbséget a jelentésben tisztázd:** a spec
   mindkét változatot előírja (lásd A.4).
5. **Az egyszeri mérés nem determinizmus-bizonyíték.** A rekord nem jelöli, hány futásból származik egy érték; a CI egy profilt készít, a helyi hat ismétlés három nemdeterminisztikus
   Go-objektumot talált (`core/nexus/isolation.SubprocessWorker.Decrypt`, `core/nexus/operator.PollingWatcher.Watch`, `core/nexus/operator.scanDir`).

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits` fogalmakra. A státuszt (implemented / scaffold / concept) node- vagy fájlszinten
   támaszd alá, különben ne állítsd tényként.
2. Olvasd el: `ref/owner-decisions-pr05-2026-11-15.md`, `ref/issue-169-body.md` („Self-testing of the test infrastructure”, „Development rules”, „Acceptance criteria”),
   `ref/pr04-report.md` (különösen 3., 5., 8., 10., 12.), `ref/pr03-report.md`.
3. Olvasd el a **Forms referenciát** (csak olvasásra, **nem másolandó**): `tools/seeded_defects.py`, `tools/quality_gate.py` (`selftest`), `docs/FAST-FULL.md`. A tanulság a **szigor**
   (a kapu hibát tud), nem a kód.
4. Klónozz friss klónként: `$WORKSPACE/CIC_Relay/` (alapértelmezett ág `main`; a `devel` elavult) és `$WORKSPACE/cic-primitive-forms/`. **Rögzítsd a pontos commit-azonosítókat és az ágat.**
   A Relay `main` tartalmazza a `d38a1d5`-öt; ha nem, állj meg és jelezd. **Ha a `workspace/` alatt már van `CIC_Relay` mappa, ne azt használd** (korábbi jobokból piszkos lehet; ok ismeretlen):
   új, tiszta klónt készíts, és a `git status --short | wc -l` kimenetét rögzítsd a klónozás után **és** a mérések előtt.
5. Helyi tájékozódási klónok (csak olvasásra, lehetnek elavultak): `${CIC_RELAY_PATH}`, `~/sync/git.partners/CentralInfraCore/`. **A mérés a friss klónon megy**, nem a helyin.
6. **Reachability (Go forráskód):** egy Go szimbólumról vagy scriptről csak akkor mondd, hogy production-hívott, ha megvan a hívási út:
   `grep -rn <szimbólum> --include=*.go . | grep -v _test.go` VAGY `deadcode ./...` kimenet, production call site `file:line`-nal. A `symbol létezik` ≠ `production hívja`. Ugyanez a CI-scriptekre: a workflow-ból hívott script `file:line`-ja.
7. **Mérési környezet:** `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`, `golang:1.26.x` (a `verify.yml` Go-verziója), `cargo-mutants 27.1.0`, `cargo-llvm-cov 0.9.1`, binutils `c++filt`.

## Feladat — A. rész: a kötelező seeded defect esetek (tulajdonosi táblázat)

Minden esethez: a **seeded defect** egy *forrás-bemenetből* (a valódi, pinelt eszközök kimenetéből vagy a PR-04 valós fixture-jeiből) **származtatott**, a származtatás leírva; a verifier **a tényleges `object_model.py verify` / `quality_gate.py verify`**
(nem egy másolat). Minden negatív eset mellett a **pozitív kontroll**: ugyanaz a bemenet hiba nélkül, amelyen a várt verdikt zöld/`PARTIAL`/`COMPLETE_FOR_SCOPE`.

| # | Szándékos hiba | Elvárt eredmény | Megjegyzés |
|---|---|---|---|
| A.1 | Objektum törlése (a digest és az összesítő következetesen újrapecsételve) | **L3 FAIL** | halmaz-különbségként nevezze meg a hiányzó azonosítót |
| A.2 | Nem létező objektum beszúrása (újrapecsételve) | **L3 FAIL** | halmaz-különbségként nevezze meg a felesleges azonosítót |
| A.3 | Objektum cseréje **változatlan darabszám mellett** (újrapecsételve) | **L3 FAIL** | ma átmenne: ez a halmazazonosság bizonyítéka |
| A.4 | Objektum duplikálása | **L3 FAIL** (más azonosítóval, de ugyanazon forrásobjektumra) és **L1 FAIL** (azonos azonosítóval) | lásd a kiindulópont 4. pontját; mindkét változat és a különbség magyarázata kötelező |
| A.5 | Mérési eredmény manipulálása | **L1 FAIL** (a digest nem egyezik); **és** az újrapecsételt változat is FAIL (A.5b) | az A.5b a kiindulópont 3. pontja: újralevezetést igényel |
| A.6 | Más commitból származó evidence | **L2 FAIL** | commit és fa-azonosság |
| A.7 | Hamis vagy eltérő bemeneti digest | **L2 FAIL** | a rekordban hamisított digest és/vagy megváltoztatott bemeneti fájl |
| A.8 | Hiányzó kötelező mérési eredmény | **FAIL** | a hiányzó mező (L1), a hiányzó bemeneti fájl (nincs rekord), és a scope által **kötelezőnek** jelölt, de teljesen hiányzó egység (pl. nincs Rust-objektum) → L3 FAIL |
| A.9 | Nemdeterminisztikus mérés | **nem minősíthető stabil bizonyítéknak** | lásd C. rész: a rekord jelölje a futások számát; az egyszeri mérés nem „stabil” |

## Feladat — B. rész: az L3 `PASS` csak igazolt teljességnél

- **Halmazazonosság, nem darabszám.** Go és Rust esetén a rekord objektum-azonosítóinak halmaza egy **független** felsorolás halmazával hasonlítandó; a kimenet a **szimmetrikus különbséget** nevezi meg (hiányzó és felesleges azonosítók), nem csak két számot.
- **Független Go-leltár:** független = **nem** a `tools/objinventory` (`go/ast`) kimenete és **nem** a rekord saját bemenete. Értékelj jelölteket (pl. a `gofmt`-olt forrás oszlop-0 `func` soraiból levezetett azonosítók a receiver-normalizálással, vagy más pinelt eszköz), **mérd meg** a PR-04 azonosító-szerződésével (`object-id/1`) való egyezést a valós 464 + 15 objektumon, és dokumentáld az eltéréseket (build-tag, `init#`, generikus receiver).
- **Független Rust-leltár:** ma nincs. Értékelj legalább ezeket, **mérd meg** és hasonlítsd a valós 196 objektumhoz: (a) `rustdoc --output-format json --document-private-items` a pinelt nightly-n (a PR-04 mérése szerint a `nightly-2026-07-01` települ és a workspace-t fordítja); (b) egy `syn`-alapú felsoroló (új függőség: származás, pin, licenc előbb); (c) a `cargo-mutants` listája (csak a mutálható függvények: részhalmaz, **nem független teljesség**). Ha **egyik sem** pinelhető és reprodukálható, a Rust-oldal **marad `PARTIAL`**, indoklással: ne tegyél úgy, mintha igazolt volna.
- **`PASS` (azaz `COMPLETE_FOR_SCOPE`) csak akkor**, ha **minden** egység (Go root, `goastdump`, Rust) halmazazonossága igazolt. Ha bármelyik nem, az L3 `PARTIAL`, és a nem igazolt rész felsorolt. A `PARTIAL`-t **nem nevezheted át** `PASS`-nak.
- Pozitív kontroll: egy fixture, amelyen mindkét független leltár egyezik → `COMPLETE_FOR_SCOPE`; és egy, amelyen a Rust-oldal nem igazolt → `PARTIAL` (nem `PASS`).

## Feladat — C. rész: determinizmus és a három nemdeterminisztikus Go-objektum

1. **Vizsgáld ki** a három objektumot (`SubprocessWorker.Decrypt`, `PollingWatcher.Watch`, `scanDir`): legalább **20** ismételt, azonos fán futtatott lefedettségmérés, a változó blokkok azonosítása (melyik forrássor, miért), és az ok **besorolása** (időzítés/goroutine, alfolyamat, fájlrendszer-bejárás sorrendje, valódi tesztlyuk). A következtetés **mérésen** alapuljon, ne találgatáson; amit nem tudsz megállapítani, azt jelöld **nem megállapítva**.
2. **Rekordszinten:** minden `MEASURED` lefedettségi mező jelölje, **hány független futásból** származik (`runs`), és hogy a futások egyeztek-e. Az egyetlen futásból származó érték **nem** „stabil”: a verifier ezt külön állapotként adja (pl. `DETERMINISM_NOT_SHOWN`), és a **stabil bizonyítékhoz szükséges minimum futásszámot a mért szórásból indokold** (ne találd ki).
3. A seeded defect A.9: egy szándékosan ingadozó mérés (a valós ismétlések egyikéből származtatva) → `NONDETERMINISTIC`, **nem** stabil bizonyíték; az egyszeri mérés **nem** kap stabil minősítést.
4. **Tilos** a nemdeterminisztikus objektumot kizárással eltüntetni; ha a teszt javítható lenne, az **termékkód-/tesztjavítás, külön PR** (itt csak rögzítsd).

## Feladat — D. rész: az automatikus seeded defect harness

- **Egy belépési pont** (pl. `scripts/seeded_defects.py` + `pytest`-integráció), amely az összes A–C esetet **automatikusan** lefuttatja egy **izolált** másolaton: a termékfát és a repó-bizonyítékokat **nem** módosítja, a futás végén nincs maradék. A harness az esetek **adata** (név, származtatás, elvárt verdikt, a hozzá tartozó pozitív kontroll), nem szétszórt, kézi tesztek.
- **A harness saját ellenpróbája (ez a PR-05 lényege):** a verifier egy-egy ellenőrzését egy scratch-másolaton **kiiktatva** a harness **pirosra vált**, és megnevezi, melyik seeded defect nem bukott el. A PR-04 `teeth.py`-a (a cic-factory `main`-en: `jobs/relay-ci-parity-04-object-level-measurement/output/raw/teeth.py`, kimenete: `…/raw/teeth.txt`) a minta; a 12 ottani eset és az A–C esetek **együtt** legyenek lefedve, és minden kiiktatás **a megfelelő esetet** buktassa (nem akármelyiket).
- **CI:** a harness fusson a `python` jobban (pytest), és a valós eszközöket igénylő része **külön, report-only** workflow-ban (a `object-evidence` mintája). **Nem required check, semmi nem vár rá.**
- A harness **nem lehet vakfolt maga**: minden negatív eset a **konkrét hibaüzenetet** is ellenőrizi (nem „valamilyen” hibát), és a **szerkezeti** bukás („a függvény/lépés nem létezik”) nem számít bizonyítéknak.

## Feladat — E. rész: a #169 minimum-próbáinak leképezése

A #169 „Self-testing” 1–8. próbáját képezd le: mindegyikhez **melyik seeded defect fedi** (a PR-02/03/04 meglévő tesztjei és az A–D rész esetei), vagy **kimondottan nem fedett** és miért:
1. gyengített teszt-készlet → a lefedettségi kapu piros; 2. túlélő mutáns → a mutációs kapu piros; 3. hiányzó shard → a FULL nem lehet sikeres; 4. duplikált vagy meghamisított verdikt elutasítva;
5. hiányzó/olvashatatlan lefedettségi riport nem nulla és nem siker; 6. hibás tervező nem hagyhat ki tesztet; 7. hibás evidence nem lehet `VERIFIED`; 8. módosított/ismeretlen eszközverzió használhatatlan.
Az 1. és a 2. **valós eszközt és a termékfa izolált, szándékosan gyengített másolatát** igényli: **mérd meg a költséget**; ha a futásidő indokolja, a report-only workflow **kézi indítású**, de **lefut legalább egyszer** és a run id rögzített. A 3–8. nagyrészt a PR-02/03/04 tesztjeivel fedett: ezt **hivatkozással** igazold, és ahol a lefedés csak egységteszt (nem a valódi artifactokon futó seeded defect), azt mondd ki.

## Nem része a jobnak (ne csináld)

- **Küszöb, padló vagy baseline lazítása**; új numerikus küszöb; új **blokkoló** kapu; a meglévő kapuk (`verify.yml` padlók, `--fail-under-lines 90`, mutációs ratchet, `completeness`) **nem módosulnak** (a diffben ellenőrizve).
- **Automatikus tesztkihagyás, reuse, proof-aware tervező** (PR-10); **toolchain-csere** (a Rust nightly csak a független leltár **mérésére**, report-only).
- A `gobco` (HOLD: licenc), a `mutation-policy/3`, a per-teszt hozzárendelés bevezetése, a Go-mutációk objektumszintű hozzárendelése: **külön döntés/PR**.
- **Termékkód módosítása**, a nemdeterminisztikus objektumok tesztjeinek javítása (csak rögzítsd).
- A mérés **publikációja** (PR-08/09); a CIC_Relay külső beállításai (ruleset, branch protection, required check).

## Negatív tesztek és pozitív kontrollok

**Két külön fajta; ne keverd** (a PR-04 tanulsága): az „a javítás előtti állapoton bukjon” csak ott követelmény, ahol van javítás előtti állapot.
- **R (a meglévő viselkedést módosítják):** pl. az L3 darabszám-összehasonlításának halmazazonosságra cserélése. A régi (`d38a1d5`) állapoton lefut, és a **módosított** viselkedés tesztje ott az **ELVÁRT OKBÓL BUKIK** (a konkrét üzenettel; pl. A.3 átmegy a régin, a szimmetrikus különbséggel bukik az újon). A bizonyíték a **hibát reprodukáló** bukás; a szerkezeti bukás nem.
- **N (új képességek):** a harness, a független leltár, a `runs` mező, az újralevezetés. A régi állapotban nincs mit futtatni: a bizonyíték (1) a valós fixture-ön elfogadás (pozitív kontroll), (2) hibás bemenetre **konkrét üzenettel** elutasítás, (3) **ellenpróba** (kiiktatott ellenőrzés → bukó teszt), (4) a hibás bemenet a **valós kimenetből származtatott**.
- **Minden negatív esethez pozitív kontroll** tartozik, és a harness a kettőt **párban** futtatja (a pozitív kontroll hiánya a harness hibája).

## Mérési korlátok (a jelentésben kimondandó)

- **Lemezhely és tulajdon.** A 16 GB-os `/tmp` tmpfs a PR-03-ban megtelt; a PR-04-ben a buildek a `~/.cache/relay-ci-parity-*/` alatt voltak. **A konténerek root-ként írták a fájlokat**, ezért a törlés `sudo`-t igényelt (`target`, `target-nightly`, `gp`, `gc`, a PR-03 `target-full`): **futtass konténert `--user "$(id -u):$(id -g)"`-rel** és a `HOME`/`CARGO_HOME`/`GOCACHE`/`GOPATH` a felhasználó könyvtárába mutasson, hogy a mérés után a takarítás jogosultság nélkül menjen. Rögzítsd a felhasznált helyet.
- **Statement ≠ branch**; a név a mérés fajtáját követi (PR-04). A nightly csak mérés, nem a stabil mérés helyettesítője.
- **Determinizmus:** az ismétlések száma a mért szórásból indokolt; egyszeri mérés nem bizonyít.
- **Idő és költség** (a valós eszközös seeded defectek, a független leltár) mérendő és jelentendő; a futásidő nem érv a szigor ellen, de a megvalósíthatóság adata.
- **Reprodukálhatóság:** pinelt kép-digest, eszközverziók, a kimenetek digestje.

## Elfogadási kritériumok

1. A tulajdonosi táblázat **mind a 9 esete** (A.1–A.9) automatikusan fut, **a várt szinten bukik**, és mindegyik mellett ott a **pozitív kontroll**; a duplikátum mindkét változata (A.4) és az újrapecsételt manipuláció (A.5b) is.
2. Az L3 **halmazazonosságot** ellenőriz (Go és Rust), a kimenet a szimmetrikus különbséget nevezi meg; az **A.3 a régi állapoton átmegy, az újon bukik** (R-bizonyíték).
3. Az **L3 `PASS` csak igazolt teljességnél**; a Rust-oldal vagy független leltárral igazolt, vagy **indokoltan `PARTIAL`**; a `PARTIAL` nem nevezhető át.
4. A **független Rust-leltár** értékelése mért adatokkal (jelöltek, egyezés a valós 196 objektummal, költség, pinelhetőség); a döntés indokolt.
5. A **három nemdeterminisztikus objektum** kivizsgálva (≥ 20 futás, a változó blokkok és az ok besorolása), vagy a **nem megállapított** rész kimondva; a rekord jelöli a `runs`-t, az egyszeri mérés nem „stabil”.
6. A harness **izolált**, a termékfát nem módosítja, és az **ellenpróbája** igazolt: a verifier minden kiiktatott ellenőrzésére **a megfelelő seeded defect** bukik (nyers kimenet).
7. A #169 1–8. próbájának **leképezése** kész (fedett / hivatkozással fedett / kimondottan nem fedett).
8. A meglévő blokkoló kapuk, küszöbök és baseline-ok **változatlanok** (a diffben ellenőrizve); a harness **nem required check**.
9. **Valódi GitHub Actions futás** a PR fejére (zöld), és legalább egy **szándékosan hibás, nem mergelendő** futás, amelyen **a harness piros** (pl. egy szándékosan gyengített verifier), run id-kkal; különben **nem mérve**.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented. A workflow létezése ≠ hogy fut, és a kapu ≠ hogy bukni tud. **Egy seeded defect ≠ hogy a kapu bukni tud, amíg a pozitív kontroll nincs mellette.**
- Exit code 0 ≠ sikeres mérés. Üres kimenet ≠ nulla mérés ≠ sikertelen mérés.
- **Darabszám-egyezés ≠ halmazazonosság; a digest ≠ a mérés eredete; az L1 ≠ L2 ≠ L3.** A `PARTIAL` ≠ `PASS`.
- **Egyszeri mérés ≠ determinizmus-bizonyíték.** A kizárás ≠ a nemdeterminizmus megoldása.
- A teszt zöldje ≠ hogy a teszt bukni tud: a **regressziós** tesztet a javítás nélküli állapoton is futtasd; az **új szerződés** tesztjénél ellenpróbával mutasd, hogy tud bukni. A „nem létezik” miatti bukás nem bizonyíték.
- Egy sikeres helyi futás ≠ hogy a CI-kapu hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként.

## Verifikáció és bizonyítás

- Minden állításhoz a **parancs és a nyers kimenet**; minden mérés a pinelt környezetben, a kép-digest és az eszközverziók rögzítésével.
- **A valódi eszközzel mérj**, ne csak hamis kimenettel: a fixture-öket a valódi eszközkimenetből vedd fel és írd le az eredetüket; a származtatott esetek külön jelöltek.
- **Nem elég a helyi futás:** a #169 10. szabálya szerint egy CI-fázis csak akkor kész, ha GitHub Actions futás igazolja; a futás **run id-ját és headSha-ját** vesd egybe a tesztelt committal. A szándékosan hibás futáshoz külön, **nem mergelendő** ágat/draft PR-t használj, egyértelmű jelöléssel; a javított fejre **tiszta** bizonyító ágat építs (a PR-04 első bizonyító ága egy fixture-hibát is hordozott).
- **A CI-hibákat vizsgáld ki, ne tulajdonítsd környezetnek:** a PR-04-ben a „CI-hiba” a saját regresszióm volt (egy `.go` fixture a root modul csomagja lett). Egy bukó check okát a naplóból állapítsd meg, a `base`-szel összevetve.
- A workflow-szöveg olvasata ≠ futás: ahol csak olvastad, mondd ki. A teljes repó `pytest`-jét a CI `python` jobja futtatja; helyben a scratch venv-ben hiányozhatnak csomagok (`requests`): mondd ki.
- **Aláírás:** a cic-factory `main`-re közben mozdulhat; a gate `verify-signatures` szabálya szerint a tartalmat hozó merge aláíratlan, ezért a PR-ág legyen **naprakész a `main`-nel** a push előtt. A rebase érvényteleníti az aláírást: a kimenetet **frissen aláírt commitként** a `main` tetejére kell tenni.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-05-seeded-defects/output/`

- `output/pr05-report.md` — magyarul: vizsgált commitok; a klón tisztasága; a kiindulópont 1–5. pontjának **mérése** (mi igaz ma, mi nem); az A–E rész eredményei **mért adatokkal**; a seeded defect táblázat esetenként (származtatás, elvárt és kapott szint/üzenet, pozitív kontroll); az R- és N-tesztek és bizonyítékuk; a harness ellenpróbája; a független Go- és Rust-leltár értékelése; a három nemdeterminisztikus objektum vizsgálata; a #169 1–8. leképezése; GitHub Actions run id-k (zöld **és** szándékosan piros); claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`); nyitott döntések; amit nem mértél.
- `output/raw/` — nyers kimenetek és mérőscriptek (minden `.sh` első sora `#!/usr/bin/env bash`, a gate ShellCheck-et fut `--severity=error`-ral; a nyers fájlokból a helyi útvonalak és felhasználónevek kerüljenek ki).

A CIC_Relay módosítás a Relay-klónban, külön ágon, PR-ként (lásd lent).

## Definition of Done

- Mindkét repó commit-azonosítója és az ág leírva; a Relay `main` tartalmazza a `d38a1d5`-öt; a klón tiszta volt a mérések előtt (rögzítve).
- A 9 kötelező seeded defect eset (A.1–A.9, az A.4 és A.5 mindkét változatával) automatikusan fut, a várt szinten bukik, mind mellett pozitív kontroll.
- Az L3 halmazazonosságot ellenőriz; `PASS` csak igazolt teljességnél; a Rust-oldal független leltárral igazolt, vagy indokoltan `PARTIAL`.
- A három nemdeterminisztikus objektum kivizsgálva (vagy a nem megállapított rész kimondva); a rekord jelöli a `runs`-t.
- A harness ellenpróbája igazolt (a kiiktatott ellenőrzésre a megfelelő eset bukik); az R-tesztek a régi állapoton az elvárt okból buknak, az N-tesztek elfogadnak, konkrét üzenettel elutasítanak, és ellenpróbájuk megvan.
- A #169 1–8. próbája leképezve.
- A meglévő blokkoló kapuk, küszöbök és baseline-ok változatlanok (a diffben ellenőrizve); nincs új blokkoló kapu, nincs tesztkihagyás, nincs toolchain-csere.
- Valódi GitHub Actions run id a PR headSha-jára (zöld) és a szándékosan hibás futásra (a harness piros), vagy **nem mérve**.
- A CIC_Relay PR leírása pontosan azt állítja, ami mérve van.

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-05-seeded-defects` ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát nem módosítod (a tulajdonos zárja). A push előtt győződj meg róla, hogy az ág a `main` tetején áll (lásd „Aláírás”).
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-05-seeded-defects`) a friss klónból, az alapértelmezett ág a `main`. PR-t a `main`-re nyiss (`--base main` explicit). Nem mergelsz. A PR **egy** témájú legyen: seeded defect harness és a verifier keményítése; termékkód nincs. A szándékosan hibás (piros-út bizonyító) ágat **ne** mergeld, és ne nyiss belőle mergelhetőnek tűnő PR-t (draft, „DO NOT MERGE” cím, a munkaágra mutatva); a futás rögzítése után zárd le.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR leírásában. A Relay-repó csak merge-commitot enged.
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: ezt jelezd az outputban, az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet a push-t elutasítja; ilyenkor add oda a pontos parancsot (lehetőleg **egy scriptben**), ne kerüld meg.

## Nyelvi szabály

Dokumentáció magyarul. Parancsok, kód, YAML, shell angolul.
