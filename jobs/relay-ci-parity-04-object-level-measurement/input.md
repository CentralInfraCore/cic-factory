# relay-ci-parity-04-object-level-measurement — objektumszintű, ellenőrizhető mérési modell

## Kontextus

A `CentralInfraCore/CIC_Relay` **#169** issue (másolat: `ref/issue-169-body.md`) tízlépéses PR-sorozat.
**Ez a job a PR-04-et fedi:** „Branch coverage and object-level measurement”, záró feltétel:
*scope-hoz kötött, ellenőrzött küszöbök*.

Előzmények (mind mergelve, a `main` CI zöld):

- PR-01 (cic-factory #47): inventory és gap-analízis — `ref/pr01-inventory-and-gap-analysis.md`.
- PR-02 (CIC_Relay #170; cic-factory #48, #49): a Rust felsorolás fail-closed, a tervező eszkalál.
- PR-03 (CIC_Relay #171; cic-factory #50–#52): teljességi verifier, terv-állapotok — `ref/pr03-report.md`.
  A Relay `main` fej: `852594ae6180828dac090038cc443a6ac3e57bd4`; a cic-factory `main` fej: `752ada86ba10758dd08c3ce9860fee84427fc37e`.

**A PR-04 célja nem a coverage növelése.** A cél a mérés **objektumszintű, ellenőrizhető modelljének** kialakítása:
bizonyítható legyen, hogy az egyes produkciós objektumok (függvény, metódus) milyen ellenőrzést kaptak, és ahol ez
nem bizonyítható, ott ez **explicit `UNVERIFIABLE`** legyen, ne hallgatólagos siker. A Relay CI fejlesztésének nem az
a célja, hogy ugyanazokat a százalékokat adja, mint a Forms, hanem hogy **ugyanazzal a bizonyítási szigorral** tudjon
állításokat tenni a saját kódjáról.

**Ez a spec külön felülvizsgálatra készül; a job indítása a spec review-ja és mergelése után történik.** A PR-04
implementációt ad (a CIC_Relay scriptjeit, workflow-it és tesztjeit módosítja, és PR-t nyit a CIC_Relay felé), de
**csak a lenti I. rész hatókörében**; a II. rész megvalósíthatósági mérés és javaslat, nem bekötés.

## Tulajdonosi döntések (kötelezőek; szó szerint: `ref/owner-decisions-2026-11-14.md`)

1. **Unviable.** Az `unviable` mutáns **sem `caught`, sem `missed`** eredménynek nem számít. **Külön, kötelező metrikaként**
   szerepel. A jelenlegi érték (83/300) **nem buktat**. A későbbi szigorítás **kizárólag `mutation-policy/2` verzióváltással**
   történhet.
2. **Rust mutation score.** A score alapja `caught / (caught + missed)`. **Minden más** mutációs státusz (timeout, unviable)
   kezelését és a nevezőből való kizárását **külön dokumentálni kell**. A 90%-os küszöb ennek alapján értelmezendő.
3. **`tools/goastdump`.** Bekerül a PR-04 mérési scope-jába, **külön riportolással** (nem tűnhet el a Go-átlagban).

Mit jelent ez a gyakorlatban (és hol ütközhet a mai kóddal — olvasd el, ne feltételezd):

- A `scripts/quality_gate.py` ma `caught/planned` és `caught/(planned−unviable)` értéket ír ki (`mutation-policy/1`).
  A döntés szerinti elsődleges score `caught/(caught+missed)`. Ez a kiírt metrika és a policy **definíciójának** változása,
  tehát **új policy-verzió** (`mutation-policy/2`), nem csendes csere. A **buktató szemantika nem szigorodik**: `missed` és
  `timeout` ma is buktat, az `unviable` ma sem.
- **Ne gyengítsd** a mai kaput. A `missed > 0` ma piros; egy 90%-os score-küszöb **gyengébb** lenne ennél. A 90% tehát
  **jelentett, ratchetes** érték, nem a `missed == 0` szabály helyettesítője. Ezt a jelentésben mondd ki.
- A `timeout` ma buktat, és ezért zöld futásban 0; a nevezőből való kizárása így most nem változtat a számon, de a szabályt
  rögzítsd (mi történik, ha a `timeout` policy később változik).
- Az `unviable` arányra **figyelmeztető (nem buktató) szintet** javasolj a mért adat alapján (ma 83/300 = 27,7%; fájlonként
  nagyon eltérő: több fájlon 0, máshol 40–60% körüli; pl. `vault-adapter/src/lib.rs` 9/15, `executor/src/lib.rs` 5/9, lásd `ref/pr03-report.md` 3.). A szint értékét **ne találd ki**: mérésből, indokolva javasold, a tulajdonos hagyja jóvá.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits` fogalmakra. A státuszt
   (implemented / scaffold / concept) node- vagy fájlszinten támaszd alá, különben ne állítsd tényként.
2. Olvasd el: `ref/owner-decisions-2026-11-14.md`, `ref/issue-169-body.md` („Quality gates”, „Development rules”,
   „Differential and fuzz testing” nem, de „Self-testing” és „CI evidence” igen), `ref/pr03-report.md` (különösen 3., 8., 9., 12., 13.),
   `ref/pr01-inventory-and-gap-analysis.md` 4.4 és 6.–7.
3. Olvasd el a **Forms referenciát** (csak olvasásra, **nem másolandó**): `tools/coverage_gate.py` (`cic-coverage-report/1`,
   ADR 0009), `tools/quality_gate.py`, `tools/test-evidence/`, `tools/proof-plan/`, `docs/TEST-EVIDENCE.md`,
   `docs/DELTA-DIFF-GATE.md`. A tanulság a **szigor**, nem a kód.
4. Klónozz friss klónként: `$WORKSPACE/CIC_Relay/` (alapértelmezett ág `main`; a `devel` elavult) és
   `$WORKSPACE/cic-primitive-forms/`. **Rögzítsd a pontos commit-azonosítókat és az ágat.** A Relay `main` tartalmazza a
   `852594a`-t; ha nem, állj meg és jelezd. **Ha a `workspace/` alatt már van `CIC_Relay` mappa, ne azt használd** (korábbi
   jobokból piszkos lehet; ok ismeretlen): új, tiszta klónt készíts, és a `git status --short | wc -l` kimenetét rögzítsd
   a klónozás után **és** a mérések előtt.
5. Helyi tájékozódási klónok (csak olvasásra, lehetnek elavultak): `${CIC_RELAY_PATH}`,
   `~/sync/git.partners/CentralInfraCore/`. **A mérés a friss klónon megy**, nem a helyin.
6. **Reachability (Go forráskód):** egy Go szimbólumról vagy scriptről csak akkor mondd, hogy production-hívott, ha megvan a
   hívási út: `grep -rn <szimbólum> --include=*.go . | grep -v _test.go` VAGY `deadcode ./...` kimenet, production call site
   `file:line`-nal. A `symbol létezik` ≠ `production hívja`. Ugyanez a CI-scriptekre: a workflow-ból hívott script `file:line`-ja.
7. **Derítsd fel te**, ne feltételezd, mit tud ténylegesen a mérőeszköz (a valódi kimenet alapján, a pinelt környezetben):
   `go test -coverprofile`/`-covermode`, `go tool covdata`, a `gremlins v0.6.0` kimenete (per-mutáns pozíció van-e, `--output`
   van-e), `cargo llvm-cov` (`export --format=json` függvény- és régió-szintje, a `--branch` kapcsoló stabil toolchainen),
   `cargo mutants --list --json` (`function.span`). A mérési környezet: `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`,
   `golang:1.26.x` (a `verify.yml` Go-verziója), `cargo-mutants 27.1.0`, `gremlins v0.6.0`.

## Feladat — I. rész: közvetlenül megvalósítható (a meglévő, pinelt eszközökkel)

Minden itt szereplő funkció **report-only**: nem vezet be új blokkoló kaput (lásd „Nem része”).

### I.A `mutation-policy/2` (a döntések rögzítése)

- A policy-t **verziózott, dokumentált szabályként** rögzítsd (a kódban és egy dokumentumban): minden mutációs státusz
  (`caught`, `missed`, `timeout`, `unviable`) kezelése, a score képlete, a nevező, a buktató szemantika.
- A `quality_gate.py` kiírja: `caught`, `missed`, `timeout`, `unviable` külön; az elsődleges score-t `caught/(caught+missed)`;
  az `unviable` arányt külön kötelező metrikaként; a policy verzióját. A régi `caught/planned` érték **marad kiírva** (a
  folytonosság és az átláthatóság miatt), de nem elsődleges.
- **A policy változása gate-logika változás:** a tervező FULL-ra eszkalál (a `quality_gate.py` már a `GATE_LOGIC_PATHS`-ban van).
- Negatív teszt: az `unviable` mutáns **nem változtatja** a score-t; a `timeout` nem tűnik el; a policy-verzió eltérése a
  riport és a kapu közt piros.

### I.B Mérési scope (`measurement-scope/1`)

- Verziózott, review-hoz kötött scope-fájl: **produkciós kód**, **tesztsegédek**, **generált fájlok**, **kísérleti / nem bekötött**
  komponensek szétválasztva (a PR-01 6. szakasza a kiindulás). **Minden kizárásnak oka van**, kizárás indoklás nélkül nem fogadható el.
- A scope-fájl változása gate-logika változás (a tervező eszkalál). Nincs csendes kizárás: ami nincs a scope-ban és nincs
  kizárva indoklással, az hiba.
- A `tools/goastdump` **bekerül** a scope-ba, **külön szakaszban/metrikával** (döntés 3). A root-modul alapküszöbei **nem**
  vonatkoznak rá automatikusan: a bevonás **report-only**, a küszöb-viszony csak megjelenik. (A PR-03 mérése: 78,0% statement
  coverage, mutant coverage 78,95% a root-küszöbökkel elbukna; ez **tájékoztató**, nem új blokkoló kapu.)
- A gremlins a `testdata` fájlokat is mutálta a `goastdump`-on (`testdata/sample.go`): ezt mérd meg, és javasolj indokolt kezelést
  (kizárás **indoklással**), ne tüntesd el csendben.

### I.C Objektum-leltár (`object-id/1`) — stabil kulcsok

- **Go:** produkciós függvények és metódusok a `go/ast`-ből (a `tools/goastdump` már a `go/ast` front-end, ennek kiterjesztése vagy
  használata megengedett; **mérd meg**, mit ad). **Rust:** a leltár forrása a `cargo llvm-cov export` függvény-listája
  (a le nem futott függvények is szerepelnek-e: **mérd meg**) és a `cargo mutants --list --json` `function` mezője; az eltérés
  (egyikben szerepel, másikban nem) **explicit jelölt**.
- A **kulcs-szerződés verziózott** (`object-id/1`), dokumentált és tesztelt: mi alkotja az azonosítót (csomag/crate, modul-útvonal,
  típus, függvénynév), mit **nem** (a sorszám és a fájl-pozíció attribútum, nem kulcs, hogy a sorok eltolódása ne cserélje le az
  azonosítót). Két különböző objektum azonosítója **nem eshet egybe**; ha az eszközkimenetben ez előfordulhat (túlterhelés, azonos
  nevű closure, `init`), a szerződés kezelje, és legyen rá teszt.
- A leltár **rendezett, egyedi, digestelt** (a PR-03 `mutation-plan/1` mintája).

### I.D Függvény-szintű lefedettség-hozzárendelés

- **Go:** a `coverprofile` blokkjait a függvény-spanekre képezd le: objektumonként lefedett/összes utasítás.
- **Rust:** az `llvm-cov export` függvény-szintű adata (sor- és **régió**-lefedettség).
- **Elnevezési fegyelem:** amit a stabil eszközök adnak, az **utasítás-**, **sor-** és **régió**-lefedettség. **Ne nevezd „branch coverage”-nek**,
  ami nem az (a séma számára a mérés fajtája felsorolt, megkülönböztetett mező; lásd a negatív teszteket).
- A `go test` lefedettségének nem-determinizmusa **ismert** (PR-01: több csomag szórt ismétlésnél): **ismételd a mérést** (legalább 5×),
  rögzítsd a tartományt; a nem determinisztikus objektum **jelölt**, és nem kap pontos értéket.

### I.E Mutációs bizonyíték hozzárendelése objektumhoz

- **Rust:** a `cargo mutants` `outcomes.json` ítéletei a mutáns `function`/`file`/`span` alapján az objektumhoz (a PR-03 terv-rekordja már
  köti az azonosítókat). Objektumonként: `caught`, `missed`, `timeout`, `unviable` **külön**.
- **Go:** a gremlins pozíciónként ad-e ítéletet, vagy csak csomag-összegzést: **mérd meg**. Ha csak összegzést ad, a Go objektumszintű
  mutációs bizonyíték a **II. részbe** tartozik, és a Go objektumok mutációs mezője **`UNVERIFIABLE`** (indokkal), nem üres, nem `0`.

### I.F `UNVERIFIABLE` — a nem hozzárendelhető objektumok

Minden objektumhoz **minden bizonyíték-mező** (lefedettség, mutáció, teszt-kapcsolat) a következők egyike:
`MEASURED` (mért érték), `NOT_APPLICABLE` (indokolt), `UNVERIFIABLE` (az **ok** felsorolt kódja, pl. `NO_TOOL`, `NO_MAPPING`,
`NONDETERMINISTIC`, `TOOL_LIMIT`). **Hiányzó mező nincs**; hiányzó mérés sosem válik `MEASURED`-dé vagy implicit sikerré.
Az objektumok, a mezők és az okok **darabszáma** a riportban kötelező.

### I.G Kanonikus bizonyíték-rekord (`object-evidence/1`)

- Egy rekord: a commit és a fa azonossága, a **bemenetek digestjei** (coverprofile, `llvm-cov` JSON, `outcomes.json`, a PR-03 terv
  digestje, a scope-fájl digestje), az **eszközverziók** (Go, rustc, cargo-mutants, gremlins, llvm-cov), az objektumok rendezett
  listája a mezőállapotokkal, az összesítők, a **rekord digestje** (kanonikus JSON, a PR-03 mintája).
- **Offline verifier** (a `quality_gate.py` mintájára): a rekord épségét, a sémát, a digestet, az összesítők egyezését az objektumokkal,
  a bemeneti digestek jelenlétét ellenőrzi. Megváltoztatott vagy ismeretlen eszközverzió → a rekord **használhatatlan** (nem „figyelmeztetés”).
- A rekord **mérési kimenet**, nem publikáció (a közzététel PR-08/09).

### I.H Globális és objektumszintű metrikák elkülönítése

- A riportban és a kapu kimenetében **két külön szakasz**: globális (csomag/crate-szintű) és objektumszintű; **nem egyesülnek egyetlen
  „success/verified” értékké**. Egy globálisan zöld, de `UNVERIFIABLE` objektumokat tartalmazó mérés **ezt mutatja**.
- A meglévő blokkoló kapuk (a `verify.yml` per-csomag padlói, a Rust `--fail-under-lines 90`, a mutációs ratchet, a PR-03
  `completeness`) **változatlanok**. Az új objektumszintű kimenet **nem blokkoló**, és **nem required check**.

### I.I A `goastdump` hiányzó lefedettségének osztályozása (döntés 3)

A 78%-os coverage **önmagában nem bizonyítja**, hogy kritikusan gyenge. A hiányzó utasításokat/ágakat **objektumonként** sorold be:
AST-feldolgozás · hibakezelés · diagnosztikai/kevésbé lényeges ág · elérhetetlen kód. Az osztályozás **indoklott, ellenőrizhető** (a
függvény-spanhez és a coverprofile-blokkhoz kötve), nem általános megjegyzés. A `goastdump` a `go.meta.gen.py` front-endje
(a `verify.yml` `python` jobjának megjegyzése: `tools/go.meta.gen.py reads Go through tools/goastdump (go/ast)`): hogy a hibája mit érint (a generált meta fájlok helyessége), azt az osztályozásban jelezd; teszt-bővítés **nem** része a jobnak.

## Feladat — II. rész: további mérőeszközt vagy instrumentációt igényel (megvalósíthatósági mérés és javaslat; **nincs bekötés bizonyítatlanul**)

Minden tétel kimenete: **mért megvalósíthatósági jelentés** a valódi eszközzel, pinelt környezetben, és **javaslat** a tulajdonosnak.
Új eszköz csak akkor kerülhet **report-only** CI-lépésbe, ha a verziója pinelhető, a mérés reprodukálható és a származása indokolt;
különben a státusz `UNVERIFIABLE`/„nem megvalósítható most”, indoklással.

- **II.A Go ág-lefedettség.** A Go natív eszköze **utasítás-lefedettséget** ad, nem ágat. Értékelj legalább egy jelölt eszközt
  (forrás-instrumentáló ág-lefedettség) a **származás, pinelhetőség, reprodukálhatóság, költség** szempontjából; mérd meg 2–3 csomagon, a
  `goastdump`-on is. Hasonlítsd a natív utasítás-lefedettséghez. A döntés a tulajdonosé; **nincs elfogadás**.
- **II.B Rust ág-lefedettség.** Mérd meg, hogy a `cargo llvm-cov --branch` (vagy az LLVM ág-instrumentáció) a **pinelt stabil** 1.96.1-en
  elérhető-e (várhatóan nightly kell: **állítsd, ne tippeld**). Ha nightly kell, értékeld egy **külön, pinelt, report-only** nightly-lépés
  költségét/kockázatát; a döntés a tulajdonosé. Addig a **régió-lefedettség** a rendelkezésre álló közelítés, és **így is nevezendő**.
- **II.C Objektum–teszt hozzárendelés (teszt-kapcsolat).** Hogy melyik teszt melyik objektumot fedi: Go `-run` szerinti per-teszt
  profil, Rust per-teszt-bináris/`--test` szerinti profil. **Mérd meg** a költséget és a megvalósíthatóságot egy mintán; ahol nem feloldható,
  a teszt-kapcsolat `UNVERIFIABLE` (`NO_MAPPING`/`TOOL_LIMIT`).
- **II.D Változás-hatás (change impact).** Csak azt állítsd, ami ellenőrizhető: Go csomag-szintű függőségi zárlat (`go list -deps`), Rust
  crate-szintű (`cargo metadata`). A **függvény-szintű tranzitív** hatás hívási-gráf eszközt igényel: értékeld a megvalósíthatóságot; ahol nincs
  eszköz, `UNVERIFIABLE`. A hatás-kimutatás **tájékoztató**; **semmit nem hagy ki** belőle senki és semmi (lásd „Nem része”).
- **II.E Go per-mutáns kimenet.** Ha az I.E szerint a gremlins nem ad pozíciónkénti ítéletet, értékeld, hogy ez más módon (kimeneti
  formátum, ha van; a pozíciósorok elemzése, ha a kimenet ezt stabilan adja) megbízhatóan előállítható-e. Elemzett, nem pinelt kimeneti
  szöveg **nem** válhat új blokkoló kapuvá.

## Nem része a jobnak (ne csináld)

- **Automatikus tesztkihagyás, reuse-optimalizáció, proof-aware tervező** (PR-10): semmi nem hagyható ki a mérés vagy a hatás-kimutatás alapján.
- **Új, bizonyítatlan objektumszintű blokkoló kapu.** Az objektumszintű kimenet report-only.
- **Küszöb vagy baseline lazítása**, kizárás a scope-ba tolva; új numerikus küszöb bevezetése bizonyítás nélkül.
- Termékkód módosítása; a Forms reuse-kernelének portolása.
- A PR-03 jelentésének nyitott pontjai közül: a diff-módú (`--in-diff … --shard`) valódi CI-futás és a heti `mutation.yml` teljességi bekötése
  a **PR-07** témája; a nightly `security` bukás (Relay #160), az eszköz-verzió pin és a `deadcode` lépés státusza külön döntés.
  Ha szükségesnek látod, **jelentsd**, ne változtasd.
- A mérés **publikációja** (GitHub App, attestation, védett ág): PR-08/09.
- A CIC_Relay külső beállításainak (ruleset, branch protection, required check) módosítása.

## Negatív tesztek (kötelezőek)

**Minden negatív teszt a javítás előtti állapoton is lefusson, és ott az ELVÁRT OKBÓL BUKJON** — nyers kimenettel. A bukás-tesztben a
konkrét hibaüzenetet is ellenőrizd (a PR-02/03 tanulsága: rossz okból is lehet piros: `bad substitution`, üres git-fa, `ImportError`).
A bukás-bizonyíték szétválasztandó: **a hibát reprodukáló** bukás vs. **szerkezeti** („a lépés nem létezik”) bukás; csak az első bizonyíték.

1. **Azonosító-ütközés:** két különböző objektum azonos `object-id/1`-gyel → elutasítva.
2. **Hozzárendelhetetlen objektum:** `UNVERIFIABLE` (konkrét okkóddal), **nem** `MEASURED`, nem üres, nem sikeres.
3. **Hiányzó vagy olvashatatlan bemenet** (coverprofile, `llvm-cov` JSON, `outcomes.json`): **nem nulla mérés és nem siker**; a rekord nem keletkezik.
4. **Meghamisított rekord:** megváltoztatott digest, törölt objektum, módosított összesítő, hiányzó bemeneti digest → a verifier elutasítja.
5. **Ismeretlen vagy módosított eszközverzió** → a rekord használhatatlan.
6. **Elnevezési fegyelem:** egy riport, amely régió/utasítás-lefedettséget `branch`-ként jelöl, **elutasított** (a séma enum-ja).
7. **Globális ≠ objektumszintű:** globálisan zöld mérés `UNVERIFIABLE` objektumokkal **nem** jelenhet meg egyetlen „verified/success” értékként.
8. **Policy:** az `unviable` nem változtatja a score-t; a `timeout` nem tűnik el; a `mutation-policy` verzió-eltérése riport és kapu közt piros;
   a `missed > 0` továbbra is piros (a 90%-os score nem gyengíti).
9. **Scope:** indoklás nélküli kizárás elutasítva; a scope-fájlban nem szereplő produkciós fájl hiba (nem csendes kihagyás).
10. **Nem-determinizmus:** ingadozó Go-lefedettségű objektum `NONDETERMINISTIC`, nem kap pontos értéket.

## Mérési korlátok (a jelentésben kimondandó)

- **Statement ≠ branch.** Amit nem ág-mérő eszköz mér, az nem ág-lefedettség; a név a mérés fajtáját követi.
- **Rust régió-lefedettség** nem ág-lefedettség; a `--branch` stabil toolchainen való (nem)elérhetőségét **mérd**, ne tippeld.
- A Go-lefedettség **nem determinisztikus** egyes csomagokon (PR-01): ismétlés, tartomány, jelölés.
- **Lemezhely.** A korábbi jobban a 16 GB-os `/tmp` (tmpfs, RAM) **megtelt** (több Rust `target` könyvtár és Relay-másolat), a futás megszakadt.
  Egy közös `CARGO_TARGET_DIR`-t használj, a másolatokat és cache-eket mérés után töröld, és ahol lehet, a `/tmp`-en kívüli kötetet használd. Rögzítsd a
  felhasznált helyet.
- **Idő és költség** (a Go per-teszt profil, a nightly toolchain, a gremlins) mérendő és jelentendő; a futásidő nem érv a szigor ellen, de a
  megvalósíthatóság adata.
- Az **ugyanazon commit** mérése reprodukálható legyen: pinelt kép-digest, eszközverziók, a kimenetek digestje.

## Elfogadási kritériumok

1. A három tulajdonosi döntés **a kódban és a dokumentumban** megvan (`mutation-policy/2`), a buktató szemantika **nem szigorodott és nem gyengült**.
2. A `measurement-scope/1` fájl verziózott, minden kizárásnak oka van, a `goastdump` külön szakaszban szerepel.
3. Az `object-id/1` szerződés dokumentált, tesztelt; a Go és a Rust objektumleltár **mért** számokkal (hány objektum, hány hozzárendelhető, hány `UNVERIFIABLE`, miért).
4. Minden objektum minden bizonyíték-mezője `MEASURED`/`NOT_APPLICABLE`/`UNVERIFIABLE`; **nincs hiányzó mező**.
5. Az `object-evidence/1` rekord kanonikus, digestelt; az offline verifier a 4.–5. negatív tesztet elutasítással teljesíti.
6. A II. rész minden tételére van **mért megvalósíthatósági jelentés** és javaslat; ami nem megvalósítható, az indoklással `UNVERIFIABLE`/nem megvalósítható.
7. A `goastdump` hiányzó lefedettsége **objektumonként osztályozott**, ellenőrizhető indoklással.
8. A **tíz negatív teszt** mind a javítás előtti állapoton **az elvárt okból** bukik (nyers kimenet), és az új kódon zöld.
9. A meglévő blokkoló kapuk **változatlanok** (a diffben ellenőrizve); az új kimenet nem required check.
10. **Valódi GitHub Actions futás** a PR fejére (zöld), és legalább egy **szándékosan hibás, nem mergelendő** futás (pl. meghamisított rekord, vagy hiányzó bemenet) **piros** — run id-kkal; különben **nem mérve**.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented. A workflow létezése ≠ hogy fut, és a kapu ≠ hogy bukni tud.
- Exit code 0 ≠ sikeres mérés. Üres kimenet ≠ nulla mérés ≠ sikertelen mérés.
- **Statement- vagy régió-lefedettség ≠ ág-lefedettség.** A név a mérés fajtáját kövesse.
- **Mért érték hiánya ≠ 0 és ≠ siker:** a hiányzó bizonyíték `UNVERIFIABLE`, nem hallgatólagos megfelelés.
- Minden shard `success` ≠ minden tervezett mutáns kapott ítéletet; globális zöld ≠ objektumszintű bizonyíték.
- Egy sikeres helyi futás ≠ hogy a CI-kapu hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.
- A teszt zöldje ≠ hogy a teszt bukni tud: a negatív tesztet a javítás nélküli állapoton is futtasd, és ellenőrizd, hogy az elvárt okból bukik.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként.

## Verifikáció és bizonyítás

- Minden állításhoz a **parancs és a nyers kimenet**; minden mérés a pinelt környezetben, a kép-digest és az eszközverziók rögzítésével.
- **A valódi eszközzel mérj**, ne csak hamis kimenettel: a fixture-öket (Go `coverprofile`, `llvm-cov` JSON, `outcomes.json`, gremlins kimenet) a
  valódi eszközből vedd fel, és írd le az eredetüket; a származtatott esetek külön jelöltek.
- **Nem elég a helyi futás:** a #169 10. szabálya szerint egy CI-fázis csak akkor kész, ha GitHub Actions futás igazolja; a futás **run id-ját és
  headSha-ját** vesd egybe a tesztelt committal. A szándékosan hibás futáshoz külön, **nem mergelendő** ágat/draft PR-t használj, egyértelmű jelöléssel.
- A workflow-szöveg olvasata ≠ futás: ahol csak olvastad, mondd ki.
- Amit nem mértél, az **nem mérve**, nem becslés. A teljes `pytest`-et a CI `python` jobja futtatja hash-ellenőrzött függőségekkel; helyben a scratch
  venv-ben hiányozhatnak csomagok (`requests`): mondd ki.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-04-object-level-measurement/output/`

- `output/pr04-report.md` — magyarul: vizsgált commitok; a klón tisztasága; a feltárt eszköz-képességek (valódi kimenet alapján); az I. rész funkciói
  (előtte/utána, mért számokkal); a II. rész **megvalósíthatósági jelentései** és javaslatai (tulajdonosi döntésekhez); a tíz negatív teszt és a bukásuk
  bizonyítéka **az elvárt okból** (a hibát reprodukáló és a szerkezeti bukás szétválasztva); a `goastdump` osztályozás; a policy-döntések
  megvalósítása és az ütközések (mi változott a `mutation-policy/1`-hez képest); GitHub Actions run id-k (zöld **és** szándékosan piros);
  claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`); nyitott döntések; amit nem mértél.
- `output/raw/` — nyers kimenetek és mérőscriptek (minden `.sh` első sora `#!/usr/bin/env bash`, a gate ShellCheck-et fut `--severity=error`-ral;
  a nyers fájlokból a helyi útvonalak és felhasználónevek kerüljenek ki).

A CIC_Relay módosítás a Relay-klónban, külön ágon, PR-ként (lásd lent).

## Definition of Done

- Mindkét repó commit-azonosítója és az ág leírva; a Relay `main` tartalmazza a `852594a`-t; a klón tiszta volt a mérések előtt (rögzítve).
- A három döntés megvalósítva és dokumentálva; a buktató szemantika változatlan (diffben ellenőrizve); az ütközések kimondva.
- I.A–I.I mért, tesztelt, report-only; a II. rész minden tétele mért megvalósíthatósági jelentéssel és javaslattal lezárva.
- Az `UNVERIFIABLE` darabszámok és okok riportálva; nincs hiányzó mező, nincs hallgatólagos siker.
- A tíz negatív teszt a javítás előtti állapoton az elvárt okból bukik, nyers kimenettel.
- Valódi GitHub Actions run id a PR headSha-jára (zöld), és a szándékosan hibás futásra (piros), vagy **nem mérve**.
- A CIC_Relay PR leírása pontosan azt állítja, ami mérve van; nincs új blokkoló kapu, nincs tesztkihagyás.

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-04-object-level-measurement` ágra. Main-re, devel-re nem pusholsz; merge-et nem
  csinálsz. A job `meta.yaml` státuszát nem módosítod (a tulajdonos zárja).
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-04-object-level-measurement`) a friss klónból, az alapértelmezett ág a `main`. PR-t a `main`-re nyiss
  (`--base main` explicit). Nem mergelsz. A PR **egy** témájú legyen: objektumszintű mérési modell; termékkód nincs. A szándékosan hibás (piros-út bizonyító)
  ágat **ne** mergeld, és ne nyiss belőle mergelhetőnek tűnő PR-t (draft, „DO NOT MERGE” cím, a munkaágra mutatva); a futás rögzítése után zárd le.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR leírásában. A Relay-repó csak merge-commitot enged.
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: ezt jelezd az outputban, az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet a push-t elutasítja; ilyenkor add oda a pontos parancsot, ne kerüld meg.

## Nyelvi szabály

Dokumentáció magyarul. Parancsok, kód, YAML, shell angolul.
