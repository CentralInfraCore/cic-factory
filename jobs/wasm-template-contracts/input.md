# wasm-template-contracts — Reproducible build verify, ABI manifest, negatív tesztek, doc kontraktusok

## Reasoning mód

**implementation** — a `wasm-template-hardening` (PR #10, mergelve a `wasm/main`-be) folytatása.
Külső review (1. tier, alacsony kockázatú, wasm-scoped pontok) alapján. **Nem redesign** — az
örökölt compiler/infra réteghez (`tools/infra.py`, `tools/compiler.py`, `project.schema.yaml`)
NEM nyúlsz ebben a jobban (ld. "Nem ebben a jobban" szakasz).

## Munkakörnyezet — branch szabály (KÖTELEZŐ)

- base-repo klón a workspace-edbe, `git fetch origin wasm/main`, majd:
  **`wasm/f/contracts` branch a `wasm/main`-ből** (a `wasm/main` ekkor már tartalmazza a
  PR #10 + PR #11 CI-fixeket — `git log --oneline -3 origin/wasm/main`-nel ellenőrizd, hogy
  az `actions/checkout@v4`/`docker compose up -d builder` változások benne vannak-e; ha PR #11
  még nincs mergelve, ágazz a `wasm/f/ci-followup`-ból is, és jelezd a riportban).
- Minden base-repo commit a `wasm/f/contracts`-ra. Push **kizárólag** `wasm/f/contracts`-ra.
- PR: `gh pr create --base wasm/main --head wasm/f/contracts`.
- Relay host ABI referencia: `CIC-Relay/core/cabinet/cicwasm.go` (klónozd a workspace-be).
- KB-fókusz: `c689` (iSDK contract), `c1503` (modul-release evidence).

## Feladat

### 1. `make wasm.rebuild-verify`

Új make target (vagy ekvivalens tooling entrypoint), amely:
1. a hivatalos `wasm.build` útvonalon (`tinygo build -target wasip1 -scheduler=none`)
   újraépíti `module/module.wasm`-ot egy ideiglenes/scratch helyre (NE írja felül a
   commitolt `module.wasm`-ot, vagy ha felülírja, állítsa vissza/jelezze a diffet),
2. kiszámolja az új artifact SHA-256 hash-ét,
3. kiolvassa a `project.yaml` `metadata.buildHash` értékét,
4. összehasonlítja — eltérés esetén non-zero exit + érthető hibaüzenet,
5. kerüljön a CI-be (`.github/workflows/ci.yml`, külön step),
6. README/README.hu dokumentálja.

### 2. ABI-manifest a `project.yaml`-ban

Vezess be explicit `abi:` blokkot (name/version/exports/operations/envelopeVersion —
ld. a review promptban mellékelt minta). Validáld schema-val (`project.schema.yaml`
kiegészítése), ellenőrizd a host-load tesztben (`module/module_loadtest_test.go`), hogy a
WASM export-lista megegyezik a manifesttel — eltérés esetén a teszt bukjon. Dokumentáld
README-ben (en+hu).

### 3. Negatív ABI / memory-boundary tesztek

Bővítsd a `module/module_loadtest_test.go`-t (vagy `module/envelope_test.go`-t) ezekkel:
- invalid JSON input, unknown op, empty op, empty payload, túl nagy payload
- invalid pointer / length, pointer+length out-of-bounds (ha az ABI ezt direktben nem
  teszteli, dokumentáld a korlátot és tesztelj envelope/host-wrapper szinten)
- nil-success válasz stabil envelope-ként
- exportok tényleges megléte ellenőrzött (deadcode/grep `module/abi.go` exports)

### 4. Doc link fixek

Keress broken internal doc linkeket (`grep -rn` markdown linkekre a `docs/` alatt),
javítsd a típushibákat (pl. `git-managment.md` vs `git-management.md`), és adj egy
egyszerű CI lépést (`docs.link-check`) ami ezt ellenőrzi.

### 5. Standalone contract docs

`docs/contracts/wasm-abi.md`, `docs/contracts/envelope.md`, `docs/contracts/host-expectations.md`,
`docs/contracts/release-artifact.md` (en+hu, vagy legalább en, ha a hardening docs is csak
en+hu páros volt — kövesd a meglévő konvenciót). Tartalmazzák: várt WASM exportok,
allocate/deallocate/Call modell, JSON envelope be/ki, error kategóriák, ABI verzió,
release artifact bundle célállapot.

## Nem ebben a jobban (dokumentált jövőbeli munka — NE kezdj hozzá)

A review prompt további pontjai (2. és 3. tier) tudatosan KIMARADNAK ebből a jobból:

- **2. tier** (`verify-release` CLI, doc status model kiterjesztése minden szekcióra,
  CI gate-ek szétszedése egy general `quality` step alól) — külön jobként jön, ha ez a
  job lezárult.
- **3. tier** (`STAGE=template|development|release|final` validáció + külön schema fájlok,
  canonical release path tisztázás `tools/infra.py`/`compiler.py`-ban) — ez az **örökölt**
  `schemas/main` release-backbone-t érinti (ld. `wasm-template-finish` riport:
  "inherit schemas/main release backbone"). Mielőtt ide bármilyen agent hozzáér, orchestrátor-
  szintű döntés kell: szabad-e a wasm-ágnak saját release-modellt fejlesztenie (eltérve a
  schemas/main lineage-től), vagy ezt előbb upstream (schemas/main) kellene megcsinálni.
  **Ne implementáld, ne is tervezd újra ezt a jobban** — ha munkád közben olyan hiányt
  találsz, ami csak ide nyúlva javítható, dokumentáld a riportban "blocked by 3-tier
  architectural decision" megjegyzéssel, és ne nyúlj hozzá.

## Tiltott rövidítések (kötelező)

- **Zöld teszt mockolt kódúttal ≠ lefutott kódút.** Az ABI-manifest/export-egyezés és a
  rebuild-verify hash-összehasonlítás mock nélküli, valós build/artifact futtatás-kimenettel
  bizonyítva.
- **A fájl léte ≠ működik.** `make wasm.rebuild-verify`, `make wasm.test`, `make wasm.build`,
  `make manifest-verify`, `make check`, `make test` tényleges futtatás-kimenetét idézd.
- Hook-bypass, `--no-verify`, force-push, `tools/infra.py`/`tools/compiler.py`/
  `project.schema.yaml` módosítása — TILOS ebben a jobban.

## Reachability — kötelező bizonyíték

- `grep -rn` a kulcs-bekötésekre (kizárva `_test.go`): `abi:` blokk olvasása/validálása,
  `wasm.rebuild-verify` make target + CI step, `docs.link-check` CI step.
- Minden `implemented` állításhoz `file:line` vagy futtatás-kimenet.
- Teljes verifikációs lánc: `make validate`, `make manifest-verify`, `make wasm.build`,
  `make wasm.rebuild-verify`, `make wasm.test`, `make golang.quality`, `make check`, `make test`.

## Output

- `jobs/wasm-template-contracts/output/wasm-template-contracts-report.md` —
  claim-evidence tábla: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`,
  az 5 pont (1–5) egyenként lefedve, + "Nem ebben a jobban" pontok státusza
  (ha bármelyik 3-tier hiányba futottál, itt jelezd).
- base-repo `wasm/f/contracts` pusholva + PR a `wasm/main` bázisra.

## Git instrukciók

- base-repo: commit + push **csak** `wasm/f/contracts`-ra; PR bázis: `wasm/main`.
- cic-factory: commit + push **csak** `feature/wasm-template-contracts`-ra.
- Main-re és `wasm/main`-re sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/f/contracts` branch a `wasm/main`-ből (CI-fixeket tartalmazó HEAD-ből), minden munka ott
- [ ] 1–5 pont implementálva, futtatás-kimenettel igazolva
- [ ] ABI-manifest validálva + host-load tesztben export-egyezés ellenőrizve
- [ ] negatív ABI tesztek zöldek
- [ ] doc link-check CI-ben
- [ ] standalone contract docs léteznek
- [ ] teljes verifikációs lánc zöld a builder konténerben, kimenetek idézve
- [ ] PR megnyitva (`wasm/f/contracts` → `wasm/main`)
- [ ] report + claim-evidence tábla a `feature/wasm-template-contracts`-on pusholva
- [ ] "Nem ebben a jobban" 3-tier pontokhoz nem nyúltál — ha hiányt találtál, dokumentálva

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul** (kivéve a base-repo README/docs, ami en+hu párban él)
- Go/Makefile/shell/YAML, kódon belüli komment, commit message: **angolul**
