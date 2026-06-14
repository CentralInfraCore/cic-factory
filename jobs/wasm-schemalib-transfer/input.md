# wasm-schemalib-transfer — `tools/schemalib/` package átemelése

## Reasoning mód

**implementation**, kis scope — a `wasm-schemalib-sync-plan` riport
(`cic-factory/jobs/wasm-schemalib-sync-plan/output/wasm-schemalib-sync-plan-report.md`,
3. pont, 1-2. lépés, KB node `c1295`) végrehajtása: a `tools/schemalib/`
package **változatlan** átemelése `CIC-Schemas/schemas/main`-ből
`wasm/main`-be, additív lépésként.

A terv szerint ez a lépés **önállóan végezhető, alacsony kockázatú**: új
fájlok, semmi meglévőt nem érint, amíg `tools/infra.py` nem importál belőlük
(az importálás a tervben **külön, magas kockázatú** sub-job — ezt a jobot NEM
ez végzi).

## Munkakörnyezet

- `base-repo` klón: `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/wasm-schemalib-transfer/workspace/base-repo`,
  `wasm/main` HEAD (ellenőrizd `git log --oneline -3 origin/wasm/main` —
  ekkor már tartalmazhatja a `wasm-schemalib-sync-plan` által hivatkozott
  `7a51952`-ön túli commitokat, jegyezd fel melyik HEAD-ből indultál).
- `CIC-Schemas` klón: `schemas/main`, commit `2ec57c0` (a
  `wasm-schemalib-sync-plan` riport ezt vette referenciának).
- Branch: `wasm/f/schemalib-transfer` a `wasm/main`-ből.

## Feladat

### 1. `tools/schemalib/` package átemelése

Másold át változatlanul:
- `CIC-Schemas/tools/schemalib/__init__.py`
- `CIC-Schemas/tools/schemalib/artifact.py`
- `CIC-Schemas/tools/schemalib/loader.py`
- `CIC-Schemas/tools/schemalib/validator.py`

→ `base-repo/tools/schemalib/` alá, byte-azonosan (`diff -q` legyen üres
mindkét oldalon).

**Ne módosíts más fájlt** — a `tools/infra.py`, `tools/compiler.py`,
`project.schema.yaml`, `tools/finalize_release.py` jelenleg **semmit nem
importál** az új package-ből, ez egy tisztán additív, "dead" package-hozzáadás
ebben a lépésben. Ennek a ténynek a **bizonyítása kötelező** (ld. Reachability).

### 2. `tools/releaselib/exceptions.py` diff-check

A `wasm-schemalib-sync-plan` riport (4. pont, "Nyitott kérdés 3") szerint
mindkét repóban 45 sor, de tartalmi diff nem készült el — a `schemalib.loader`
és `schemalib.validator` ebből importál (`ConfigurationError`, `ReleaseError`).

- `diff base-repo/tools/releaselib/exceptions.py CIC-Schemas/tools/releaselib/exceptions.py`
  — idézd a riportban a teljes diff-outputot (vagy "nincs eltérés", ha üres).
- Ha **van** eltérés, és az eltérés azt jelenti, hogy az újonnan átemelt
  `schemalib/loader.py`/`validator.py` `from ..releaselib.exceptions import
  ConfigurationError, ReleaseError` importja `base-repo`-n **elhasalna**
  (`ImportError`/`AttributeError`), igazítsd a `base-repo/tools/releaselib/exceptions.py`-t
  a hiányzó osztály(ok) hozzáadásával — **csak additív hozzáadás**, meglévő
  osztályt/szignatúrát ne módosíts.
- Ha **nincs** eltérés vagy az eltérés nem érinti `schemalib` importjait,
  ne módosíts semmit, és dokumentáld a diff-et "nincs hatás" indoklással.

### 3. Ellenőrzés — `make test` / `make check`

Az új `tools/schemalib/` package importálható-e hiba nélkül (pl.
`python -c "from tools.schemalib import artifact, loader, validator"` a
builder konténerben), és `make test` / `make check` továbbra is zöld
(`EXIT=0`) — az új fájlok jelenléte nem törhet meg semmit, mert nincs hívó.

## Tiltott rövidítések (kötelező)

- **A fájlok megléte (`tools/schemalib/*.py` átkerült) ≠ implemented
  migráció.** Ez a job a teljes migráció egy **additív, izolált** lépése —
  a riportban explicit írd le, hogy `tools/infra.py`/`tools/compiler.py`/
  `project.schema.yaml` **nem importál** az új package-ből (`grep -rn
  "schemalib" base-repo/tools/*.py` az új fájlokon kívül → 0 találat), így
  ez a lépés önmagában **nem** old meg semmilyen wasm-specifikus problémát
  a tervből — csak előfeltétel a következő (magas kockázatú) lépéshez.
- **`make test`/`make check` `EXIT=0` ≠ a schemalib package helyesen
  működik.** Az `EXIT=0` itt azt bizonyítja, hogy az új fájlok jelenléte nem
  tör el semmit — a schemalib API helyességét csak a következő (import-bekötő)
  lépés teszteli majd, amikor `tools/infra.py` ténylegesen hívja.
- Ne nyúlj `tools/infra.py`/`tools/compiler.py`/`project.schema.yaml`/
  `tools/finalize_release.py`-hoz.
- Ne törölj semmit `CIC-Schemas`-ból vagy `base-repo`-ból.

## Reachability — kötelező bizonyíték

- `diff -rq CIC-Schemas/tools/schemalib base-repo/tools/schemalib` — a
  riportban idézve, üres kimenet várt (byte-azonos átemelés).
- `grep -rn "schemalib" base-repo/tools/*.py base-repo/Makefile
  base-repo/mk/*.mk` — a riportban idézve: csak az új
  `base-repo/tools/schemalib/*.py` fájlok saját belső importjai (egymás
  között) jelenhetnek meg, **semmi más** `base-repo/tools/*.py` fájl nem
  hivatkozhat rá. Ez a base-repo Python eszköz, nem Go — a `_test.go`/
  `deadcode` ellenőrzés nem releváns; a grep maga a reachability-bizonyíték
  (0 külső hívás = a package ebben a lépésben szándékosan dead/inert).
- `diff base-repo/tools/releaselib/exceptions.py
  CIC-Schemas/tools/releaselib/exceptions.py` — teljes output idézve.
- `make test` és `make check` futtatás-kimenete (`EXIT=0`).

## Output

- `jobs/wasm-schemalib-transfer/output/wasm-schemalib-transfer-report.md`
  — claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs
  módszer | Kockázat`), lefedve az 1-3. pontot.
- base-repo `wasm/f/schemalib-transfer` pusholva + PR a `wasm/main` bázisra
  (vagy dokumentált korlát, mint az előző jobokban: lokális mirror →
  GitHub push az orchestrátor feladata, ha `gh pr create` nem ismeri fel a
  remote-ot).

## Git instrukciók

- base-repo: commit + push **csak** `wasm/f/schemalib-transfer`-ra; PR bázis: `wasm/main`.
- cic-factory: commit + push **csak** `feature/wasm-schemalib-transfer`-ra.
- Main-re és `wasm/main`-re sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/f/schemalib-transfer` branch a `wasm/main`-ből
- [ ] `tools/schemalib/{__init__,artifact,loader,validator}.py` byte-azonosan átemelve, `diff -rq` üres
- [ ] `tools/releaselib/exceptions.py` diff dokumentálva (és igazítva, ha szükséges)
- [ ] `grep -rn "schemalib" ...` igazolja: 0 külső hívás a meglévő kódból
- [ ] `make test` és `make check` zöld (`EXIT=0`), kimenet idézve
- [ ] PR megnyitva (`wasm/f/schemalib-transfer` → `wasm/main`) vagy dokumentált korlát
- [ ] report a `feature/wasm-schemalib-transfer`-on pusholva

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, kommentek, commit message: **angolul**
