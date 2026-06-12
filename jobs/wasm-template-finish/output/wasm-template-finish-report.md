# `wasm-template-finish` — jelentés

## 1. A megszakadás és a folytatás ténye

A `wasm-template-impl` agent 2026-06-12 05:44Z-kor session limitbe ütközött. A mentett
klónban (`jobs/wasm-template-impl/workspace-saved/base-repo`, `wasm/main` branch,
`HEAD = c176f25 "wip: wasm/main template snapshot (agent session-limit cutoff, work
salvage)"`, `git status` clean) **az alábbiak már elkészültek**:

- a teljes fájllista a terv 3. szakasza szerint (module/, mk/wasm.mk, mk/golang.mk,
  release-gerinc a schemas/main-ből, builder image TinyGo-val, CI workflow alap,
  schemas/index.yaml stb.),
- `module/module.wasm` (668068 byte) **már lefordítva és commitolva** — tehát a
  predecessor ténylegesen futtatott egy `make wasm.build`-et a konténerben.

**Ami hiányzott** (ez volt e job feladata):
- `docs/{en,hu}/wasm-module-authoring.md` — nem létezett.
- `mk/golang.mk` be volt másolva, de `make golang.vet`/`golang.lint`/`golang.vuln`
  **ténylegesen nem futott le zölden** — a `cd /app`-ra épülő `GO_EXEC`/`GO_FIXER`
  a repo-gyökeret nézte, ahol nincs `go.mod` (a Go modul `module/`-ban van) →
  `pattern ./...: directory prefix . does not contain main module`.
- `staticcheck`/`govulncheck` bináris hiányzott a builder image-ből.
- `.github/workflows/ci.yml`-ben **nem** volt `wasm.build`/`wasm.test`/`golang.quality`
  lépés.
- `tools/compiler.py`-ban a `ReleaseManager`/`GitService`/`VaultService`/
  `ManualInterventionRequired`/`ReleaseError`/`yaml` nevek **nem voltak importálva**
  (ruff F821 — 7 hiba), és a teszt-suite emiatt 9 ERROR-t dobott
  (`mocker.patch("tools.compiler.ReleaseManager")` → AttributeError).
- `tools/infra.py` buildHash-delta (`_resign_with_build_hash` + a finalize-validáció
  buildHash-követelménye) megvolt, de **4 teszt elbukott** rá (a régi
  `VALID_PROJECT_YAML` fixture nem tartalmazott `buildHash`-t, és a finalize-tesztek
  nem mockolták `_resign_with_build_hash`-t / `write_yaml`-t).
- `make validate` (`python -m tools.compiler validate`) hibázik:
  `File not found: /app/sources/index.yaml` — ez **a `schemas/main`-ből öröklött,
  preexistáló hiba** (a `schemas/main` `project.yaml`-ja sem ad meg
  `canonical_source_file`-t, és a default `sources/index.yaml` ott sincs, csak
  `source/`). Nem ez a job hozta be, és nem volt az eredeti DoD része — itt csak
  kockázatként rögzítve.

**Mit csinált ez a job:** a mentett klónt átvette (nem klónozott újra), a fenti
hiányokat pótolta, a salvage-commitot `git reset --soft origin/main` után 3
tematikus commitba rendezte, és a teljes build/test/lint láncot **valódi
futtatással** verifikálta a builder konténerben.

## 2. Claim-evidence tábla (az eredeti `wasm-template-impl` DoD szerint)

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `wasm/main` branch a base-repo `main`-jéből | implemented | `git log origin/main..HEAD` → 3 commit (450ac0c, 254efea, 5b231a3) `wasm/main`-en | `git log --oneline -5` (workspace/base-repo) | **Push blokkolva** — ld. 4. szakasz |
| `module/abi.go` — allocate/deallocate/Call + op-dispatch | implemented | `module/abi.go:18-65` (`//export allocate`, `//export deallocate`, `//export Call`, op switch init/process/get/notify) | `grep -n "//export\|^func " module/abi.go` | — |
| `module/handlers.go` — üres init/process/get/notify slotok | implemented | `module/handlers.go:9-30` | `Read` | `Get` defaultból `{"status":"ok"}`-ot ad (loadtest miatt) |
| `module/module_loadtest_test.go` — host-load smoke test a cabinet ABI ellen | implemented | `module/module_loadtest_test.go:1-124`, wazero + `wasi_snapshot_preview1`, `WithStartFunctions()`, ABI export-check, `Call("get")` round-trip | **lefuttatva**, ld. 3. szakasz | — |
| `mk/wasm.mk` — `wasm.build` (TinyGo `-target wasip1 -scheduler=none`), `wasm.buildhash`, `wasm.test` | implemented | `mk/wasm.mk:16,26,34` | **lefuttatva**, ld. 3. szakasz | — |
| Release-gerinc öröklve `schemas/main`-ból (`tools/`, `mk/infra.mk`, `project*.yaml`, hookok) | implemented | `git diff origin/schemas/main..HEAD -- tools/ mk/infra.mk` — `tools/__init__.py`, `tools/init_from_template.sh`, `tools/release.sh`, `mk/infra.mk` változatlanul átvéve | `git show` diff | — |
| `infra.py` signing-delta a `buildHash`-en (finalize aláírás fedi) | implemented | `tools/infra.py:190-194` (finalize megköveteli a nem-üres `buildHash`-t), `tools/infra.py:344-377` (`_resign_with_build_hash`: `metadata_for_signing` tartalmazza a `buildHash`-t, Vault `sign` újra hívva) | pytest `tests/test_tools/test_infra.py`, `test_infra_coverage.py` — **109 passed**, ld. 3. szakasz | — |
| `mk/golang.mk` öröklve **és bekötve** (`make golang.quality` célozható és **zöld**) | implemented | `Makefile:5` (`include mk/golang.mk`), `mk/golang.mk:38-49` (`GO_MODULE_DIR ?= module`, `GO_EXEC`/`GO_FIXER` → `cd /app/$(GO_MODULE_DIR)`) | **`make golang.quality` lefuttatva, zöld** (ld. 3. szakasz) | A `golang/main`-ből öröklött `mk/golang.mk` `cd /app`-ot feltételezett — ez a wasm-specifikus delta (`GO_MODULE_DIR`), nélküle `go vet`/`lint`/`vuln` `directory prefix . does not contain main module` hibával bukott |
| CI (`.github/workflows/ci.yml`) `wasm.build`+`wasm.test`+`golang.quality` lépéssel | implemented | `.github/workflows/ci.yml:33,36,39` | `grep -n wasm .github/workflows/ci.yml` | A lépések helyi futtatása zöld (ld. 3.); a CI-run maga a PR megnyitásával validálódik |
| Build-verifikáció: `make wasm.build` zöld, TinyGo `module.wasm`-ot emittál | **implemented (lokál futtatás-kimenettel)** | `module/module.wasm` (668068 byte), `project.yaml.metadata.buildHash` rekonstrukciója `sha256` = `5649514b3a15...` | **lefuttatva**, ld. 3. szakasz — `docker compose exec builder tinygo build -o module.wasm -target wasip1 -scheduler=none .` | A build **nem byte-determinisztikus** (két egymást követő build különböző hash-t adott azonos méret mellett — TinyGo build-metadata/timestamp); a `wasm.test` mindkét build-bel zölden lefutott |
| Build-verifikáció: `make wasm.test` zöld, host betölti, `Call("get")` `{data,error}`-t ad | **implemented (lokál futtatás-kimenettel)** | `=== RUN TestHostLoad` / `Call("get") -> data={"status":"ok"} error=null` / `--- PASS: TestHostLoad (0.06s)` | **lefuttatva**, ld. 3. szakasz | — |
| Base-repo PR megnyitva (`wasm/main` → `main`) | **NEM teljesült** | — | — | A `git push origin wasm/main` egy CIC PreToolUse hook (`\b(main|master)\b` regex a push-parancson) miatt **blokkolva** — a hook nem különbözteti meg a `wasm/main` típus-ágat a valós `main`-től. Ld. 4. szakasz |
| `docs/{en,hu}/wasm-module-authoring.md` | implemented | `docs/en/wasm-module-authoring.md`, `docs/hu/wasm-module-authoring.md` (új fájlok, e job hozta létre) | `Read` | — |
| `make validate` (`python -m tools.compiler validate`) | **scaffold / preexistáló hiba** | `VALIDATION FAILED: File not found: /app/sources/index.yaml` | lokál futtatás | A `schemas/main` `project.yaml`-ja sem ad meg `canonical_source_file`-t, és ott sincs `sources/` (csak `source/`) — ez **a schemas-gerinc öröklött hibája**, nem ezé a jobé; a `wasm-template-impl`/`-finish` DoD-ja nem érintette a `validate` targetet |

## 3. Build/test-futtatások — teljes kimenet

A builder konténer (`base-repo-builder-1`, image TinyGo 0.39.0 + Go 1.25.0 +
staticcheck 0.6.1 + govulncheck 1.1.4 — ez utóbbi kettőt e job adta hozzá a
Dockerfile-hoz) elérhető és futtatható volt (`docker compose up -d builder`).

### 3.1 `make wasm.build`

```
--- Building WASM guest module (TinyGo -target wasip1) ---
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app/module && tinygo build -o module.wasm -target wasip1 -scheduler=none .'
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app && python -m tools.compiler set-build-hash --file module/module.wasm --project project.yaml'
✓ metadata.buildHash = <sha256(module.wasm)>
```

Két egymást követő futás `module.wasm` mérete mindkétszer **668068 byte**, de a
sha256 eltért (`5649514b3a15aa8c58c3ae4039cfbd54e3e3169cb4f2b458c53f8f8a3987d68e` vs.
`c00a54acfbf5833847e9f7528b1c8da3aa7de77d1d8f4e77d6bdbc0ab656ffc0`) — a TinyGo build
nem byte-determinisztikus (build-metadata/timestamp). A repóban a predecessor
build-jét (`5649514b...`) hagytuk meg; a `project.yaml.metadata.buildHash` a
sablon dokumentált alapállapota szerint `""` (a `wasm.buildhash` tölti ki a
release build-résben, `mk/wasm.mk:26-31`, `tools/infra.py:344-377`).

### 3.2 `make wasm.test`

```
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app/module && GOFLAGS=-mod=mod go test -run TestHostLoad -v .'
=== RUN   TestHostLoad
    module_loadtest_test.go:110: Call("get") -> data={"status":"ok"} error=null
--- PASS: TestHostLoad (0.06s)
PASS
ok  	github.com/CentralInfraCore/wasm-module-template/module	0.068s
```

A `module/go.sum` (új fájl) a `go test` által letöltött `tetratelabs/wazero
v1.9.0` checksumait rögzíti — nélküle a build nem reprodukálható.

### 3.3 `make golang.quality` (= fmt-check + lint + vet + vuln, `module/`-ra)

```
--- fmt-check ---  (nincs eltérés, exit 0)
--- lint (staticcheck) ---
Staticcheck on: github.com/CentralInfraCore/wasm-module-template/module
(nincs hiba, exit 0)
--- vet ---
Vet on: github.com/CentralInfraCore/wasm-module-template/module
(nincs hiba, exit 0)
--- vuln (govulncheck) ---
govulncheck on: github.com/CentralInfraCore/wasm-module-template/module
=== Symbol Results ===
No vulnerabilities found.
Your code is affected by 0 vulnerabilities.
This scan also found 0 vulnerabilities in packages you import and 37
vulnerabilities in modules you require, but your code doesn't appear to call
these vulnerabilities.
```

Mielőtt e job javította, `golang.vet`/`lint`/`vuln` a `pattern ./...: directory
prefix . does not contain main module or its selected dependencies` hibával
bukott (a `cd /app`-ra épülő `GO_EXEC`/`GO_FIXER`, miközben a Go modul
`module/`-ban van), és `staticcheck`/`govulncheck` `Permission denied`-del
bukott (a build-időben `/root/go/bin`-be installált binárisokhoz a futásidejű
nem-root user nem fért hozzá). Mindkettőt javítottuk:
`mk/golang.mk:38-49` (`GO_MODULE_DIR ?= module`) és `Dockerfile`
(`GOBIN=/usr/local/bin go install ...`).

### 3.4 `make check` (Python: black/isort, ruff, yamllint, mypy, bandit)

```
--- Formatting Python code with Black and Isort ---
All done! ✨ 🍰 ✨  — 20 files left unchanged, Skipped 101 files
--- Linting Python code with Ruff ---
All checks passed!
--- Linting YAML files with yamllint ---  (nincs hiba)
--- Running static type checking with MyPy ---
Success: no issues found in 20 source files
--- Running security checks with Bandit ---
Test results: No issues identified. (1149 LOC, 0/0/0/0 issues)
```

Mielőtt e job javította, `infra.lint` (ruff) **7 F821 (undefined name)**
hibával bukott `tools/compiler.py`-ban (`ReleaseManager`, `GitService`,
`VaultService`, `ManualInterventionRequired`, `ReleaseError`, `yaml` —
sehol nem voltak importálva). Javítás: top-level importok hozzáadva
(`tools/compiler.py`), a `schemas/main` mintáját követve — ez a `tools.compiler`
modul attribútumait is elérhetővé teszi a teszt-suite `mocker.patch
("tools.compiler.ReleaseManager")`-féle hívásainak (ld. 3.5).

### 3.5 `make test` (pytest + coverage)

```
TOTAL                                 675     69    90%
============================= 109 passed in 0.66s ==============================
```

Mielőtt e job javította: **6 failed, 9 error** (94 passed).
- A 9 ERROR (`test_compiler.py::TestMainCLI::*`, `TestLogging::*`) az imént
  leírt hiányzó importok miatt volt (`mocker.patch("tools.compiler.X")` →
  AttributeError, mert `X` nem létezett modul-attribútumként).
- 4 FAILED (`test_infra.py::test_finalization_with_dirty_repo`,
  `test_finalization_phase_success`, `test_infra_coverage.py::
  test_finalization_dry_run`, `test_finalization_with_dirty_repo`) a
  buildHash-delta miatt: a `VALID_PROJECT_YAML` fixture nem tartalmazott
  `metadata.buildHash`-t (→ `_validate_final_project_yaml` elutasította), és
  a finalize-tesztek nem mockolták `_resign_with_build_hash`/`write_yaml`-t
  (→ a valós metódus `/fake/project/project.yaml`-t próbálta írni).
  Javítás: `VALID_PROJECT_YAML` kapott `buildHash: deadbeef`-et, a
  finalize-tesztek pedig mockolják `_resign_with_build_hash`-t és
  `write_yaml`-t.
- 2 FAILED (`test_compiler.py::TestConfigLoader::test_load_project_config_*`)
  — ezek a hiányzó top-level importok mellékhatásai voltak, a fix után
  automatikusan passed.

## 4. Nyitott pont — `wasm/main` push blokkolva

A `git push origin wasm/main` egy CIC-szintű `PreToolUse` Bash-hook miatt
**megbukik**:

```
BLOCKED [CIC]: push to main/master is not allowed. Agents may only push to
feature/<job-id> branches.
```

A hook regex-e (`\b(main|master)\b`) a `wasm/main` branch-nevet is megtalálja
(a `/` szóhatár), tehát **nem tudja megkülönböztetni a típus-ágat
(`wasm/main`, mint a már létező `golang/main`/`schemas/main`) a valós
`main`-től**. Ez nem ennek a jobnak a hibája, és nem oldható meg
hook-bypass-szal (tiltott rövidítés).

**A munka helyben, commitolva, push-olatlanul vár** itt:
```
/home/sinkog/sync/claude_factory/CIC/workdir/jobs/wasm-template-finish/workspace/base-repo
```
branch: `wasm/main`, `HEAD = 5b231a3`, 3 tiszta commit `origin/main` felett:

```
450ac0c feat(wasm): inherit schemas/main release backbone for the WASM template
254efea feat(wasm): add WASM guest module core, builder toolchain, golang.mk wiring and buildHash signing
5b231a3 docs(wasm): add WASM module authoring guide (en/hu)
```

**Javasolt következő lépés (orchestrátor/human jogkör):** a hook
finomítása (pl. kizárólag a pontos `main`/`master` ref-re illeszkedjen, ne
a `*/main` mintára), majd `git push origin wasm/main` +
`gh pr create --base main --head wasm/main` a fenti klónból.

## 5. Reachability-bizonyítékok

```
$ grep -n "^include" Makefile
4:include mk/infra.mk
5:include mk/golang.mk
6:include mk/wasm.mk

$ grep -n "//export\|^func " module/abi.go | grep -v _test.go
16:func main() {}
18://export allocate
19:func allocate(size uint32) uintptr {
23://export deallocate
24:func deallocate(ptr uintptr, size uint32) {
40://export Call
41:func Call(opPtr, opLen, authPtr, authLen, dataPtr, dataLen uint32) uint64 {
... (pack/readString/readBytes/marshalData/marshalErr helperek)

$ grep -n "buildHash\|_resign_with_build_hash" tools/infra.py | grep -v _test.go
188-194: finalize megköveteli a nem-üres metadata.buildHash-t
289: prepare fázis buildHash: "" -t ír
344-377: _resign_with_build_hash — Vault sign a buildHash-et is fedi
398: _execute_finalization_phase hívja _resign_with_build_hash-t

$ grep -n "GO_MODULE_DIR" mk/golang.mk
42:GO_MODULE_DIR ?= module
45,48: GO_EXEC/GO_FIXER -> cd /app/$(GO_MODULE_DIR)

$ grep -n "wasm\|golang.quality" .github/workflows/ci.yml
33:        run: make golang.quality
36:        run: make wasm.build
39:        run: make wasm.test
```

KB-fókusz (ABI-ellenőrzéshez): `c689` (iSDK contract, concept — ez a sablon az
első konkrét megtestesülése), `c1503` (modul-release evidence / supply-chain).
A relay host ABI forrása (`CIC-Relay/core/cabinet/cicwasm.go:243-247,325,346,
267-281`) — ennek a kontraktnak felel meg `module/abi.go` és
`module/module_loadtest_test.go`, a `wasm.test` futtatás-kimenete ezt
igazolja (3.2. szakasz).

## 6. Definition of Done — `wasm-template-finish`

- [x] mentett állapot átvéve, base-repo NEM lett újraklónozva üresen
- [x] `wasm/main` tiszta commit(ok)ban (3 tematikus commit, `git reset --soft
      origin/main` után) — **pusholva NEM lett**, ld. 4. szakasz
- [x] az eredeti `wasm-template-impl` DoD minden pontja teljesítve vagy
      explicit indokolva (ld. 2. szakasz táblázat)
- [x] `docs/{en,hu}/wasm-module-authoring.md` megírva
- [x] build-verifikáció futtatás-kimenettel (`wasm.build`, `wasm.test`,
      `golang.quality`, `check`, `test` — mind lefuttatva, ld. 3. szakasz)
- [ ] base-repo PR megnyitva (`wasm/main` → `main`) — **blokkolva a CIC
      push-hook miatt**, ld. 4. szakasz
- [x] report + teljes claim-evidence tábla a feature branch-en pusholva
