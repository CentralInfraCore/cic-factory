# wasm-template-impl — A base-repo `wasm/main` sablon feltöltése a terv alapján

## Reasoning mód

**implementation** — a `wasm-template-design` terv konkrét megvalósítása: a base-repo
`wasm/main` sablon-branch létrehozása és feltöltése, build-verifikációval.

## Elsődleges referencia — a TERV

`jobs/wasm-template-design/output/wasm-template-plan.md` — ez a job ennek a tervnek a
**végrehajtása**, ne tervezd újra. A terv tartalmazza: a build-target döntést (TinyGo),
a signed-artifact deltát (buildHash-aláírás), a guest ABI scaffold vázát
(`module/abi.go` + `handlers.go`), a teljes fájllistát forrás-megjelöléssel (3. szakasz),
és a DoD-ot (6. szakasz).

**Ha a terv nem elérhető a `main`-ről:** a `wasm-template-design` PR (#20) még nem
mergelt — ekkor olvasd a tervet a cic-factory klónban a `feature/wasm-template-design`
branch-ről (`git show feature/wasm-template-design:jobs/wasm-template-design/output/wasm-template-plan.md`).

## Cél

A base-repo egy multi-branch sablon-repo (`golang/main`, `schemas/main`, …). **Nincs
`wasm/*` branch.** Hozz létre egy **`wasm/main` branch-et a base-repo `main`-jéből**, és
töltsd fel a WASM-modul-repo sablonnal a terv 3. szakaszának fájllistája szerint.

## Feladat

### 1. Branch
A base-repo klónban: `wasm/main` ← `origin/main` (a közös base-ből, mint a `golang/main`).

### 2. A sablon feltöltése (terv 3. szakasz fájllistája)
- **WASM-mag (ÚJ):** `module/abi.go` (a 2.3 iSDK boilerplate kitöltve — allocate/deallocate/Call
  + op-dispatch, a host ABI-hoz: `CIC-Relay/core/cabinet/cicwasm.go:243-247`), `module/handlers.go`
  (üres init/process/get/notify slotok), `module/module_loadtest.go` (host-load smoke test a
  relay `cabinet` ABI ellen), `mk/wasm.mk` (`wasm.build` TinyGo `-target wasi/wasip1 -scheduler=none`,
  `wasm.test`, `.wasm` sha256 → `project.yaml.buildHash`).
- **Release-gerinc öröklése `schemas/main`-ból:** `tools/` (compiler.py, infra.py, finalize_release.py,
  releaselib/, vault-sign-agent, git_hook_commit-msg.sh, init-hooks.sh), `mk/infra.mk`,
  `project*.yaml`, hookok. **`infra.py` signing-delta:** a finalization fázis aláírása fedje a
  `buildHash`-t is (terv 2.2/a).
- **Go-quality öröklése `golang/main`-ból ÉS bekötése:** `mk/golang.mk` — és a top-`Makefile`
  **include-olja** (a `golang` branch scaffold-hibájának javítása, terv 1.2).
- **Builder image:** TinyGo + wat2wasm a `docker-compose.yml`/`Dockerfile`-ba.
- **CI + doksi:** `.github/workflows/ci.yml` `wasm.build` + `wasm.test` lépéssel;
  `docs/{en,hu}/wasm-module-authoring.md`.

### 3. Build-verifikáció — a builder Docker konténerben (becsületesen)
**A toolchain a builder Docker image-ben van, NEM a host PATH-on** — a schemas/golang
sablon minden make-targetje konténerben fut (`schemas` minta: `validate:` →
`docker compose exec builder python -m tools.compiler …`). A `command -v tinygo` a hoston
üres, de ez **nem** jelenti, hogy nincs toolchain — a build a konténerben megy.

- **Builder image delta:** a `Dockerfile`/`docker-compose.yml`-be kerüljön **TinyGo + wat2wasm**
  (terv 3. fájllista). A `mk/wasm.mk` targetjei a builder konténerben futnak
  (`docker compose exec builder tinygo build … -target wasi/wasip1 -scheduler=none`),
  a schemas konténer-mintát követve.
- **HA a Docker + builder elérhető:** `make up` (builder build), majd `make wasm.build`
  (TinyGo `module.wasm` a konténerben) és `make wasm.test` (host-load a relay `cabinet`-tel).
  A **kimenetet** (nem az exit code-ot) rögzítsd a claim-evidence táblába.
- **HA a Docker sem elérhető a futtató környezetben:** **NE állíts zöld build-et.** Ekkor a
  build-verifikáció a base-repo **CI-re hárul** (`.github/workflows/ci.yml`, ami szintén a
  konténerben buildel) — a sablon + CI feltöltése a feladat, a zöld build a PR CI-checkjében
  igazolódik. A claim-evidence táblában a build-sorok státusza `verifikáció szükséges (CI)`,
  NEM ténymegállapítás. A toolchain-elérhetőséget (`docker` jelen van-e) explicit rögzítsd.

### 4. Push + PR
- `git push origin wasm/main`.
- Nyiss PR-t a base-repo-ban: `gh pr create --base main --head wasm/main` — review artifact
  (a base-repo branch-konvenció szerint a `wasm/main` típus-ág; a merge-döntés a human/orchestrátoré).

## Tiltott rövidítések (kötelező)

- **A sablonfájl léte ≠ működő build.** A DoD build-lépéseit ténylegesen futtatva kell igazolni;
  ha a toolchain hiányzik, ezt explicit jelezd (CI-fallback), ne tételezd zöldnek.
- **Exit code 0 ≠ működik.** Olvasd a build/test kimenetet.
- A `golang` quality-réteg attól, hogy a fájl ott van, **bekötetlen** (scaffold) — a top-Makefile
  include-ja a bizonyíték, hogy implemented lett.

## Reachability — kötelező bizonyíték

- `grep -rn` (a `_test.go`-t kizárva, `grep -v _test.go`) a kulcs-bekötésekre: a `mk/golang.mk`
  include a top-Makefile-ben; a `module/abi.go` exportált `Call`/`allocate`/`deallocate`;
  az `infra.py` signing-delta a `buildHash`-en.
- A build-státuszt vagy lokál futtatás-kimenet, vagy a CI-check (PR) igazolja — `file:line` /
  CI-job-hivatkozás az output claim-evidence táblában.

## Output

- `jobs/wasm-template-impl/output/wasm-template-impl-report.md` — implementációs jelentés +
  **claim-evidence tábla** ezekkel az oszlopokkal: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat` (a Bizonyíték oszlop file:line vagy CI-job). Minden build/implemented állításhoz reachability-artifact, a toolchain-hiány explicit jelezve.
- A base-repo `wasm/main` branch pusholva + PR.

## Definition of Done

- [ ] `wasm/main` branch létrehozva a base-repo `main`-jéből, push (review artifact)
- [ ] WASM-mag (`module/abi.go`+`handlers.go`+`module_loadtest.go`, `mk/wasm.mk`) a sablonban
- [ ] release-gerinc öröklve `schemas/main`-ból + `infra.py` buildHash-signing delta
- [ ] `mk/golang.mk` öröklve **és bekötve** a top-Makefile-be (`make golang.quality` célozható)
- [ ] CI (`.github/workflows/ci.yml`) `wasm.build`+`wasm.test` lépéssel
- [ ] build-verifikáció: lokál zöld futtatás-kimenet, VAGY (toolchain hiányában) explicit CI-fallback — **zöld build nem feltételezve**
- [ ] base-repo PR megnyitva (`wasm/main` → `main`)
- [ ] claim-evidence tábla minden státusz-állításhoz, a toolchain-hiány becsületesen jelezve

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul**
- Go/Makefile/shell/YAML, kódon belüli komment: **angolul**
