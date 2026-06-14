# wasm-schemalib-sync-plan — `schemas/main` schemalib szinkron migrációs terv

## Reasoning mód

**audit** — ez egy tervező/feltáró job, **nem implementáció**. A
`wasm-release-pipeline-audit` riport B) döntési pontját hajtja végre: az
orchestrátor úgy döntött, hogy a `wasm/main` release-backbone-ot
(`tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py`,
`project.schema.yaml`) szintre kell hozni a `CIC-Schemas/schemas/main`
`schemalib`-alapú primitíveivel (`tools/schemalib/{artifact,loader,validator}.py`,
commit `2ec57c0`, 2026-03-21 — a 509 soros `tools/infra.py`-t 84 sorra
csökkentő refaktor).

Ez a job **nem írja át** a kódot — egy konkrét, sorszintű migrációs tervet
készít, amelyből az orchestrátor egy vagy több implementációs sub-jobot tud
specifikálni.

Háttér: `cic-factory/jobs/wasm-release-pipeline-audit/output/wasm-release-pipeline-audit-report.md`
(pont 2-3, "Döntési kérdés" B) szakasz, KB node `c1295`) és GitHub issue
`CentralInfraCore/base-repo#16`. A `base-repo` workspace abszolút path-ja:
`/home/sinkog/sync/claude_factory/CIC/workdir/jobs/wasm-schemalib-sync-plan/workspace/base-repo`.

## Munkakörnyezet

- `base-repo` klón: `wasm/main` HEAD (`git log --oneline -3 origin/wasm/main`
  — jegyezd fel a riportban, hogy melyik commitból indultál; ekkor már
  tartalmazhatja a PR #15 MANIFEST hotfixet is).
- `CIC-Schemas` klón: `schemas/main`, fókuszban a `2ec57c0` commit
  (`tools/schemalib/{artifact,loader,validator}.py` és az ezt használó
  `tools/infra.py` 84 soros verziója).
- Csak olvasol/elemzel — **nem commitolsz/pusholsz semmit a `base-repo`-ba**.
  A `cic-factory` klónba írod az output report-ot, és pusholod a
  `feature/wasm-schemalib-sync-plan`-ra.

## Feladat

### 1. Diff-térkép: `wasm/main` jelenlegi vs. `schemas/main` `schemalib`-alapú állapot

A 4 érintett fájlra (`tools/infra.py`, `tools/compiler.py`,
`tools/finalize_release.py`, `project.schema.yaml`):
- Mi van `wasm/main`-en (file:line szintű hivatkozással, jelenlegi
  `0454bb0`-alapú monolitikus verzió).
- Mi a `schemas/main` `2ec57c0` megfelelője (`tools/schemalib/*.py` +
  84 soros `infra.py`), file:line hivatkozással.
- Konkrét API-eltérések: mely függvények/osztályok szűntek meg, melyek
  kerültek át `schemalib`-be, mely hívási helyek (`tools/compiler.py`,
  `mk/*.mk`, `Makefile`) érintettek.

### 2. wasm-specifikus réteg — mit KELL megtartani

A `wasm/main`-en a `450ac0c` óta és az ebben a sessionben merge-elt PR-ek
(#12 `tools/verify_release.py`, #13 `abi.schema.yaml` + `project.schema.yaml`
`abi:` blokk, #14 `tools/finalize_release.py` `# DEPRECATED` jelölés) olyan
wasm-specifikus kiegészítéseket vezettek be, amik **nincsenek**
`schemas/main`-ben (azok generic schema-compiler repo, nem WASM-modul
template). Soroljad fel file:line szinten, mely wasm-specifikus
kódrészek/schema-blokkok azok, amik a migráció során **nem törölhetők**, és
hogy a `schemalib`-alapú `infra.py`/`project.schema.yaml` mellett hogyan
illeszthetők be (pl. `project.schema.yaml` `$ref: abi.schema.yaml` blokkja
hogyan viszonyul a `schemalib`-es schema-loadinghoz).

### 3. Migrációs sorrend és sub-job bontás (javaslat)

Adj egy konkrét, sorrendezett listát a szükséges lépésekről (pl. "1. lépés:
`tools/schemalib/` package átemelése változatlanul; 2. lépés:
`tools/infra.py` 84 sorosra cserélése + import-ok igazítása;
3. lépés: `tools/compiler.py` hívási helyek frissítése; ..."), és minden
lépéshez jelezd: önálló sub-job lehet-e (méret/kockázat alapján), vagy egy
jobban kell elvégezni. **Ne hozz létre sub-job specet** — csak a bontási
javaslatot írd le, az orchestrátor dönt a végleges felosztásról.

### 4. Kockázatok és nyitott kérdések

Sorold fel, mi az, amit nem lehet a kódból egyértelműen levezetni (pl.
viselkedésbeli eltérés a `schemalib`-es és a régi `infra.py` validáció
között, amit csak teszteléssel/futtatással lehet kideríteni) — ezekhez NE
adj saját feltételezést, jelezd nyitott kérdésként.

## Tiltott rövidítések (kötelező)

- **A két fájl létezése (azonos névvel/struktúrával) ≠ kompatibilis API.**
  Minden "ez átvehető változatlanul" állításhoz add meg a konkrét
  import/hívási láncot mindkét oldalon (file:line), ami igazolja, hogy a
  hívó kód (`tools/compiler.py`, `Makefile`, `mk/*.mk`) ugyanazt az
  interfészt várja.
- **"A `schemalib` modernebb" ≠ "a wasm-specifikus kiegészítések
  automatikusan kompatibilisek vele."** Minden #12/#13/#14 PR-ben bevezetett
  wasm-specifikus kódrészhez/schema-blokkhoz explicit ellenőrizd, hogy a
  `schemalib`-es `infra.py`/`project.schema.yaml` struktúrája hova illesztené
  be — ha nem világos, jelezd nyitott kérdésként (4. pont), ne találgass.
- Ne módosíts kódot sem `base-repo`-ban, sem `CIC-Schemas`-ban — ez tervező
  job.

## Reachability — kötelező bizonyíték

- Minden "ez a függvény/osztály megszűnt és X-be került" állításhoz: a régi
  hívási hely (`grep -rn "<NévA>" base-repo/tools base-repo/mk
  base-repo/Makefile`) és az új megfelelő hely `CIC-Schemas`-ban
  (`grep -rn "<NévB>" CIC-Schemas/tools`), mindkettő file:line idézve.
- A wasm-specifikus kódrészekhez (2. pont) a jelenlegi production call site
  file:line-nal (pl. `tools/verify_release.py:NN` honnan importál
  `tools/infra.py`-ból).
- Ez a réteg Python (`tools/*.py`), nem Go — a `_test.go`/`deadcode ./...`
  ellenőrzés nem releváns; a call-chain bizonyíték `grep -rn` + file:line
  hivatkozás Python import-okra és hívásokra vonatkozik.

## Output

- `jobs/wasm-schemalib-sync-plan/output/wasm-schemalib-sync-plan-report.md`
  — tartalmazza:
  - claim-evidence táblát (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`) az 1-2. pontra,
  - a 3. pont sorrendezett migrációs/sub-job bontási javaslatát,
  - a 4. pont nyitott kérdéseit.

## Git instrukciók

- `base-repo`, `CIC-Schemas`: csak olvasás, nincs commit/push.
- `cic-factory`: commit + push **csak** `feature/wasm-schemalib-sync-plan`-ra.
- Main-re sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/main` és `schemas/main` induló HEAD-jei rögzítve a riportban
- [ ] 1. pont: claim-evidence tábla a 4 fájl diff-térképével, file:line
      hivatkozásokkal mindkét oldalon
- [ ] 2. pont: wasm-specifikus megtartandó részek listája file:line-nal
- [ ] 3. pont: sorrendezett migrációs/sub-job bontási javaslat
- [ ] 4. pont: nyitott kérdések listája
- [ ] report a `feature/wasm-schemalib-sync-plan`-on pusholva

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, kommentek: **angolul**
