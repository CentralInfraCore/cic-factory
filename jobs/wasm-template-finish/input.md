# wasm-template-finish — A megszakadt wasm-template-impl munka befejezése

## Reasoning mód

**implementation** — a `wasm-template-impl` job session-limit miatt megszakadt munkájának
befejezése a mentett munkaállapotból. **Ne kezdd elölről, ne tervezd újra.**

## Kontextus

A `wasm-template-impl` agent 2026-06-12 05:44Z-kor session limitbe ütközött. A base-repo
`wasm/main` sablon érdemi része elkészült (WASM-mag, `mk/wasm.mk`, builder image TinyGo-val,
`infra.py`/`compiler.py` buildHash-delta, CI workflow, schemas release-gerinc, top-Makefile
include-ok), és a `make wasm.build` a konténerben lefutott — de **commit, push, PR és report
nem történt meg**.

A teljes munkaállapot mentve:
```
${CIC_WORKDIR}/jobs/wasm-template-impl/workspace-saved/base-repo
```
(`wasm/main` branch; a változások staged állapotban vagy egy `wip: ... salvage` commitban —
ellenőrizd `git status` + `git log`-gal, mindkét eset lehetséges.)

## Elsődleges referenciák

1. **Az eredeti spec:** `jobs/wasm-template-impl/input.md` — annak **teljes DoD-ja,
   "Tiltott rövidítések" és "Reachability" szakasza erre a jobra változatlanul él.**
2. **A terv:** `jobs/wasm-template-design/output/wasm-template-plan.md` (a `main`-en, PR #20 mergelt).

## Feladat

### 1. Mentett állapot átvétele — NE klónozd újra a base-repo-t
A saját workspace-edbe másold a mentett klónt:
```bash
cp -a ${CIC_WORKDIR}/jobs/wasm-template-impl/workspace-saved/base-repo <sajat-workspace>/base-repo
```
Ellenőrizd: `wasm/main` branch aktív, a sablonfájlok megvannak (`module/`, `mk/wasm.mk`,
`mk/golang.mk` + top-Makefile include-ok, `tools/`, `.github/workflows/ci.yml`).

### 2. Git-állapot rendezése
- Ha a változások staged-ek: commitold értelmes, tematikus üzenettel.
- Ha `wip: ... salvage` commit van: `git reset --soft origin/main`, majd tiszta commit(ok).
- A commit message angolul, a base-repo konvenciói szerint.

### 3. Hiányok pótlása az eredeti DoD ellenében
Vesd össze az állapotot az eredeti `input.md` DoD-listájával. Ismert hiány:
- `docs/en/wasm-module-authoring.md` + `docs/hu/wasm-module-authoring.md`
Ellenőrizd továbbá: `project.yaml` `buildHash` mező ténylegesen íródik-e a `mk/wasm.mk`
targetből; az `infra.py` signing-delta lefedi-e a `buildHash`-t; a loadtest fájlnév/futtatás.

### 4. Build-verifikáció — újra, becsületesen
Az eredeti input 3. szakaszának szabályai élnek: a toolchain a builder konténerben van
(`docker compose exec builder ...`), a `make wasm.build` + `make wasm.test` **kimenetét**
(nem az exit code-ot) rögzítsd a claim-evidence táblába. Ha a Docker nem elérhető:
explicit CI-fallback, zöld build NEM feltételezve.

### 5. Push + PR
```bash
git push origin wasm/main
gh pr create --base main --head wasm/main
```
(review artifact — a merge-döntés a human/orchestrátoré)

### 6. Report
`jobs/wasm-template-finish/output/wasm-template-finish-report.md`:
- a **teljes eredeti DoD** claim-evidence táblája
  (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`, file:line vagy CI-job),
- a megszakadás + folytatás tényének rögzítése (mi készült az elődben, mi készült itt),
- reachability-bizonyítékok az eredeti input "Reachability" szakasza szerint.

## Tiltott rövidítések (kötelező)

- **A sablonfájl léte ≠ működő build.** A DoD build-lépéseit ténylegesen futtatva kell igazolni;
  ha a toolchain hiányzik, ezt explicit jelezd (CI-fallback), ne tételezd zöldnek.
- **Exit code 0 ≠ működik.** A build/test kimenetét olvasd és idézd.
- **Az előd munkájának léte ≠ verifikált állapot.** A mentett klónban talált fájlokra ugyanúgy
  bizonyíték kell (grep, build-kimenet), mintha most készültek volna — ne vedd át az előd
  állításait ellenőrzés nélkül.
- A `mk/golang.mk` attól, hogy a fájl ott van, **bekötetlen** (scaffold) — a top-Makefile
  include a bizonyíték (`grep -n "include mk/golang.mk" Makefile`).

## Reachability — kötelező bizonyíték

- `grep -rn` (a `_test.go`-t kizárva: `grep -v _test.go`) a kulcs-bekötésekre: a `mk/golang.mk`
  és `mk/wasm.mk` include a top-Makefile-ben; a `module/abi.go` exportált
  `Call`/`allocate`/`deallocate`; az `infra.py` signing-delta a `buildHash`-en.
- KB-fókusz az ABI-ellenőrzéshez: `c689`, `c1503` (a parent jobbal azonos), és a relay host ABI
  forrása: `CIC-Relay/core/cabinet/cicwasm.go`.
- A build-státuszt vagy lokál futtatás-kimenet, vagy a CI-check (PR) igazolja — `file:line` /
  CI-job-hivatkozás a claim-evidence táblában.

## Output

- `jobs/wasm-template-finish/output/wasm-template-finish-report.md`
- base-repo `wasm/main` pusholva + PR megnyitva

## Git instrukciók

- base-repo: push **csak** a `wasm/main` branch-re.
- cic-factory: commit + push **csak** a `feature/wasm-template-finish` branch-re.
- Main-re sehol nem pusholsz.

## Definition of Done

- [ ] mentett állapot átvéve, base-repo NEM lett újraklónozva üresen
- [ ] `wasm/main` tiszta commit(ok)ban, pusholva
- [ ] az eredeti `wasm-template-impl` DoD minden pontja teljesítve vagy explicit indokolva
- [ ] `docs/{en,hu}/wasm-module-authoring.md` megírva
- [ ] build-verifikáció futtatás-kimenettel vagy explicit CI-fallback
- [ ] base-repo PR megnyitva (`wasm/main` → `main`)
- [ ] report + teljes claim-evidence tábla a feature branch-en pusholva

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul**
- Go/Makefile/shell/YAML, kódon belüli komment, commit message: **angolul**
