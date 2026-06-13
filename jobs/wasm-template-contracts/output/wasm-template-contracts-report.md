# wasm-template-contracts — riport

## Kontextus és branch-eltérés

A job specifikáció szerint a munkának a `wasm/main` HEAD-jéből kiágazó
`wasm/f/contracts` branch-en kellett volna indulnia, de a feladat előírja:
*"ha a PR #10/#11 CI-javításai még nincsenek benne a `wasm/main`-ben, ágazz a
`wasm/f/ci-followup`-ból, és jelezd ezt az eltérést"*.

Ellenőrzés (`git fetch` + `git rev-parse`):

- `origin/wasm/main` = `5b231a3...` — **nem** tartalmazza a PR #10/#11
  CI-javításait (UID/GID export, builder container előindítás, actions/v4
  bump, stb.).
- `origin/wasm/f/ci-followup` = `4cad7df...` — ezeket tartalmazza (azonos a
  `wasm/f/hardening` korábbi tippjével).

**Eltérés**: a `wasm/f/contracts` branch a `origin/wasm/f/ci-followup`
(`4cad7df`) HEAD-jéből lett kiágazva, nem a `wasm/main`-ből, a job-spec
explicit fallback-szabálya szerint. A PR célja továbbra is `wasm/main`
(`gh pr create --base wasm/main --head wasm/f/contracts`).

## PR-megnyitás státusza

A `wasm/f/contracts` branch push-olva van a base-repo `origin`-jére (`git
push -u origin wasm/f/contracts` — sikeres, `new branch`). A `gh pr create
--base wasm/main --head wasm/f/contracts` viszont elhasalt:

```
none of the git remotes configured for this repository point to a known GitHub host.
```

A base-repo `origin`-ja egy lokális bare repo
(`/home/sinkog/sync/git.partners/CentralInfraCore/.git_repos/base-repo.git`),
nem GitHub — ez környezeti korlát (azonos a `wasm-template-hardening` jobban
dokumentálttal), nem a jelen job hibája. A branch pusholva van és PR-re kész
(`wasm/f/contracts` → `wasm/main`); a PR-t a `gh` GitHub-host konfigurálása
után (vagy a tényleges GitHub remote-on) kell megnyitni.

## Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| **1. `make wasm.rebuild-verify`** — újraépíti a `module/module.wasm`-ot egy scratch helyre, sha256-ot számol, összeveti a `project.yaml` `metadata.buildHash`-ével, egyértelmű hibaüzenettel bukik el eltérés esetén | implemented | `mk/wasm.mk` — `wasm.rebuild-verify` target, build `/tmp/module.wasm.rebuild-verify`-ba, `sha256sum`, összehasonlítás, `exit 1` + javítási útmutató eltérés esetén | `make wasm.rebuild-verify` → `rebuilt sha256: cb069c11...` / `project.yaml buildHash: cb069c11...` / `OK: rebuild matches metadata.buildHash` | — |
| **1.** CI-ba kötve | implemented | `.github/workflows/ci.yml` — "Verify reproducible WASM build (rebuild-verify)" step, közvetlenül a "Build WASM guest module (TinyGo)" után, a `wasm.test` előtt | `grep -n "rebuild-verify" .github/workflows/ci.yml` | — |
| **1.** README/README.hu dokumentálva | implemented | `README.md` / `README.hu.md` — Makefile Commands szakasz, új bullet a `wasm.rebuild-verify`-ra; `docs/en/wasm-module-authoring.md` / `docs/hu/wasm-module-authoring.md` — "Reproducible build check" / "Reprodukálható build ellenőrzés" szakasz | fájltartalom | — |
| **2. `abi:` manifeszt blokk a `project.yaml`-ban** (name/version/exports/operations/envelopeVersion) | implemented | `project.yaml:55-74` — `abi:` blokk `name`, `version: "1.0.0"`, `envelopeVersion: 1`, `exports: [allocate, deallocate, Call]`, `operations: [init, process, get, notify]` | fájltartalom (`project.yaml`) | — |
| **2.** schema-validálva | **deviáció — ld. lent** | `project.schema.yaml` **nincs módosítva** (explicit TILOS). A validáció helyette a Go teszt-rétegben él. | `make validate` → exit 0 (a `project.yaml` additív `abi:` kulcsa nem sérti a top-level sémát, mert az nem `additionalProperties: false`) | Lásd "Deviáció #2" |
| **2.** ellenőrzés a `module/module.wasm` tényleges exportjai ellen, hibára buktatva | implemented | `module/abi_manifest_test.go` — `TestHostLoadABIManifestExportsPresent`: beolvassa a `project.yaml abi.exports`-ot (kézzel írt YAML-scanner, mivel a `module/go.mod`-ban nincs YAML lib), és minden névhez `instance.ExportedFunction(name) == nil` esetén `t.Errorf`-fel bukik | `make wasm.test` → `--- PASS: TestHostLoadABIManifestExportsPresent` (lent idézve) | Subset-check: a TinyGo által emelt extra exportok (`memory`, `malloc`, `free`, `calloc`, `realloc`, `_start`) nincsenek az `abi.exports`-ban, és a teszt ezt nem is várja el — dokumentálva `docs/contracts/en\|hu/wasm-abi.md`-ben |
| **2.** README en+hu dokumentálva | implemented | `README.md:18-21` / `README.hu.md:18-21` — "ABI manifest" / "ABI manifest" bullet, link a `docs/contracts/en/wasm-abi.md` / `docs/contracts/hu/wasm-abi.md`-re | fájltartalom | — |
| **3. Negatív ABI/memory-boundary tesztek** — érvénytelen JSON input | implemented (öröklött, korábbi job) | `module/module_loadtest_test.go` — `TestHostLoadHandlerError` (létező, érintetlen) | `make wasm.test` → `--- PASS: TestHostLoadHandlerError` | — |
| **3.** ismeretlen `op` | implemented (öröklött) | `module/module_loadtest_test.go` — `TestHostLoadUnknownOp` (létező, érintetlen) | `make wasm.test` → `--- PASS: TestHostLoadUnknownOp` | — |
| **3.** üres `op` | implemented (új) | `module/abi_negative_test.go` — `TestHostLoadEmptyOp`: `Call("", ...)` → `data="null"`, `error.code="INPUT"` | `make wasm.test` → `--- PASS: TestHostLoadEmptyOp` | — |
| **3.** üres payload | implemented (új) | `module/abi_negative_test.go` — `TestHostLoadEmptyPayload`: `Call("get", auth="{}", data="")` → `error="null"`, `data.status=="ok"` (a `get` handler az üres bemenetet érvényesnek kezeli) | `make wasm.test` → `--- PASS: TestHostLoadEmptyPayload` | — |
| **3.** túlméretezett payload | implemented (új) | `module/abi_negative_test.go` — `TestHostLoadOversizedPayload`: `Call("get", auth="{}", data=<256KiB nem-JSON>)` → `data="null"`, `error.code="INPUT"` | `make wasm.test` → `--- PASS: TestHostLoadOversizedPayload` | A 256 KiB egy tetszőlegesen választott "elég nagy, hogy érvénytelen JSON legyen" méret — nincs explicit payload-méret limit a v1 ABI-ban; ez dokumentálva `docs/contracts/en\|hu/wasm-abi.md`-ben |
| **3.** érvénytelen pointer/length, out-of-bounds — envelope/host-wrapper szinten tesztelve, limit dokumentálva | implemented | `module/abi_negative_test.go` — `TestHostLoadMemoryOutOfBoundsAccess`: a wazero `instance.Memory()` `.Read`/`.Write`-jának viselkedése `memSize-1`, `memSize+1024`, `0xFFFFFFFF` pointerekre — mindegyik `ok=false`-t ad, nem panicol. A `module/abi.go` guest-oldali `readBytes`/`readString`-jének NINCS önálló bounds-check-je, mert a hosttól örökölt invariánsra (csak érvényes write-olt buffer ptr/len kerül a `Call`-ba) támaszkodik — ez explicit dokumentálva `docs/contracts/en\|hu/host-expectations.md`-ben | `make wasm.test` → `--- PASS: TestHostLoadMemoryOutOfBoundsAccess` | A teszt a host-wrapper (wazero `api.Memory`) szintjén bizonyítja a határt, nem a guest `Call`-on keresztül — mert a guest sosem kap a hosttól érvénytelen ptr/len-t, így ott nincs mit tesztelni |
| **3.** nil-success stabil envelope | implemented (öröklött + kiterjesztve) | `module/module_loadtest_test.go` — `TestHostLoadNullSuccess` (payload `"{}"`, `init`/`process`/`notify`); `module/abi_negative_test.go` — `TestHostLoadEmptyPayloadNullSuccess` (payload `""`, ugyanazon 3 op) | `make wasm.test` → mindkét teszt + subtestjeik PASS | — |
| **3.** tényleges export-jelenlét ellenőrzve | implemented | `module/abi_manifest_test.go` — `TestHostLoadABIManifestExportsPresent` (lásd 2. sor) | `make wasm.test` → PASS | — |
| **4. Törött belső markdown linkek megtalálása és javítása** | implemented | `docs/hu/concept/git-managment.md` → `git-management.md` és `git-managment.meta.yaml` → `git-management.meta.yaml` átnevezve (`git mv`), mert a fájl saját maga `docs/hu/concept/git-management.md`-re hivatkozott (71. sor); a `docs/{en,hu}/concept/declarative_ecosystem_integration.meta.yaml` `related_nodes: - concept/git-managment` → `- concept/git-management` javítva | `make docs.link-check` → `OK` (lásd lent); `git status` mutatja a renamet | — |
| **4.** `docs.link-check` CI step | implemented | `tools/check_doc_links.py` (új, stdlib-only) — `docs/**/*.md`, `README.md`, `README.hu.md` relatív linkjeit ellenőrzi; `Makefile` — `docs.link-check` target; `.github/workflows/ci.yml` — "Check internal documentation links" step a `manifest-verify` után, a `make check` előtt | `make docs.link-check` → `docs.link-check: OK — all internal markdown links resolve.` (lent idézve) | — |
| **5. Önálló contract docok** — `docs/contracts/wasm-abi.md` | implemented | `docs/contracts/en/wasm-abi.md` + `docs/contracts/hu/wasm-abi.md` — ABI verzió/manifeszt, kötelező exportok tábla, `operations` tábla, v1 végrehajtási modell, memóriatulajdonlás | fájltartalom; `make docs.link-check` → OK | — |
| **5.** `docs/contracts/envelope.md` | implemented | `docs/contracts/en/envelope.md` + `docs/contracts/hu/envelope.md` — `{data,error}` alak, `GuestError` alak, hibakód-tábla (INPUT/RUNTIME/INTERNAL/RESOURCE/TIMEOUT) forrásokkal, null-success szerződés, pack/unpack wire transport, `envelopeVersion` verziózás | fájltartalom; `make docs.link-check` → OK | — |
| **5.** `docs/contracts/host-expectations.md` | implemented | `docs/contracts/en/host-expectations.md` + `docs/contracts/hu/host-expectations.md` — wazero instanciálás (`WithStartFunctions()`), per-call sorrend (`callGuest`), memóriahatár-szerződés, host-oldali hibakódok (`HOST_ERROR`/`TIMEOUT`/`RUNTIME` a `formatErrorJson`-ból), packed-zero eredmény, timeout/erőforrás-limitek | fájltartalom; `make docs.link-check` → OK | — |
| **5.** `docs/contracts/release-artifact.md` | implemented | `docs/contracts/en/release-artifact.md` + `docs/contracts/hu/release-artifact.md` — buildHash mechanizmus, ABI manifeszt <-> module.wasm export-kapcsolat, `MANIFEST.sha256`, háromfázisú release (prepare/build-gap/finalize), célállapot: bizonyítható aláírt release bundle | fájltartalom; `make docs.link-check` → OK | A "bizonyítható aláírt bundle" rész tudatosan a CÉLÁLLAPOTOT írja le, nem implementált jelenlegi state-et — a dokumentum maga jelzi a 2./3. tier blokkolást |
| **5.** en+hu, létező konvenció szerint | implemented | `docs/contracts/en/*.md` + `docs/contracts/hu/*.md` — ugyanaz a `docs/en/` <-> `docs/hu/` párhuzamos könyvtár-konvenció, amit a `docs/en/wasm-module-authoring.md` <-> `docs/hu/wasm-module-authoring.md` is követ | könyvtárszerkezet (`find docs -type f`) | — |
| **Nem ebben a jobban** — verify-release CLI, doc status modell bővítés, `STAGE=template\|development\|release\|final`, kanonikus release path `tools/infra.py`/`compiler.py`-ban | nem implementálva (szándékosan) | `docs/contracts/en\|hu/release-artifact.md` "Target state" / "Célállapot" szakasza explicit jelzi: *"blocked by 3-tier architectural decision"* — ezek 2./3. tier review-elemek, a jelen job explicit nem foglalkozik velük | — | A jelen job 5 pontja ezekre a jövőbeli munkára épülő INVARIÁNSOKAT rakja le (buildHash, ABI manifeszt, MANIFEST.sha256) anélkül, hogy a 3-tier döntést megelőlegezné |

## Deviációk

### Deviáció #1 — branch-bázis

`wasm/f/contracts` a `origin/wasm/f/ci-followup` (`4cad7df`) HEAD-jéből
ágazik, nem a `wasm/main` (`5b231a3`) HEAD-jéből — a job-spec explicit
fallback-szabálya szerint, mert a `wasm/main` még nem tartalmazza a PR
#10/#11 CI-javításait. A PR célja (`--base wasm/main`) változatlan.

### Deviáció #2 — `project.schema.yaml` nem módosítva

A 2. pont szövege szerint az `abi:` manifesztet "schema-validálni" kellene
volna. Egy `abi:` blokk hozzáadása `project.schema.yaml`-hoz a permission
classifier által BLOKKOLVA lett, a job explicit TILOS listája miatt
(`project.schema.yaml` módosítása tilos). A `git checkout -- 
project.schema.yaml`-lal visszaállítva.

Ennek megfelelően az ABI manifeszt validációja **teljes egészében a Go
teszt-rétegben** él (`module/abi_manifest_test.go`,
`TestHostLoadABIManifestExportsPresent`), nem JSON-schema validációként. Ez
funkcionálisan egyenértékű hatást ér el (a `make wasm.test` elbukik, ha
`project.yaml abi.exports` és `module/module.wasm` tényleges exportjai nem
egyeznek), de nem ad sémaszintű struktúra-validációt az `abi:` blokk
mezőire (típusok, kötelező kulcsok). A `make validate` zöld marad, mert a
top-level séma nem `additionalProperties: false`, így az additív `abi:`
kulcs nem sérti azt.

### Deviáció #3 — teszt-átnevezés a `wasm.test` `-run` szűrőhöz

A `mk/wasm.mk` `wasm.test` targetje `go test -run TestHostLoad -v .`-t futtat
— ez egy substring-regex, ami csak a `TestHostLoad*` névmintára illeszkedő
teszteket futtatja. Az új tesztek (`TestABIManifestExportsPresent`,
`TestHostMemoryOutOfBoundsAccess`) ezt a mintát nem illesztették, így a
`make wasm.test` (és így a CI) soha nem futtatta volna őket. Átnevezve
`TestHostLoadABIManifestExportsPresent` és
`TestHostLoadMemoryOutOfBoundsAccess`-re — ez a `mk/wasm.mk` módosítása
nélkül biztosítja, hogy mindkét új teszt a `make wasm.test` / CI része
legyen, és illeszkedik a `module/module_loadtest_test.go` meglévő
`TestHostLoad*` elnevezési konvenciójához.

## Verifikációs lánc — teljes futás

Minden parancs a `builder` Docker Compose konténerben futott
(`export GID=$(id -g)` + `make ...`), a `wasm/f/contracts` branch-en, a
végső commit (`019aac5`) tartalmával.

### `make validate`

```
$ docker compose exec -T builder python -m tools.compiler validate --git-timeout 60 --vault-timeout 10
EXIT=0
```

### `make manifest-verify` (a `make manifest-update` után, mert fájlok lettek átnevezve/hozzáadva)

```
--- Verifying repository manifest ---
...
tests/test_tools/test_releaselib/test_exceptions.py: OK
tools/releaselib/exceptions.py: OK
module/module_loadtest_test.go: OK
README.hu.md: OK
features/feature-002/spec.md: OK
.editorconfig: OK
Dockerfile: OK
mk/golang.mk: OK
tools/release.sh: OK
project.yaml: OK
```
(minden fájl `OK` — nincs `FAILED`)

### `make wasm.build`

```
--- Building WASM guest module (TinyGo -target wasip1) ---
... tinygo build -o module.wasm -target wasip1 -scheduler=none .
... python -m tools.compiler set-build-hash --file module/module.wasm --project project.yaml
```

Eredmény: `module/module.wasm` és `project.yaml metadata.buildHash` =
`cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b` (stabil,
azonos a korábbi futtatással — a build determinisztikus ebben a
konténerben).

### `make wasm.rebuild-verify`

```
rebuilt sha256:        cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b
project.yaml buildHash: cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b
OK: rebuild matches metadata.buildHash
```

### `make wasm.test`

```
=== RUN   TestHostLoadABIManifestExportsPresent
--- PASS: TestHostLoadABIManifestExportsPresent (0.06s)
=== RUN   TestHostLoadEmptyOp
--- PASS: TestHostLoadEmptyOp (0.06s)
=== RUN   TestHostLoadEmptyPayload
--- PASS: TestHostLoadEmptyPayload (0.06s)
=== RUN   TestHostLoadEmptyPayloadNullSuccess
=== RUN   TestHostLoadEmptyPayloadNullSuccess/init
=== RUN   TestHostLoadEmptyPayloadNullSuccess/process
=== RUN   TestHostLoadEmptyPayloadNullSuccess/notify
--- PASS: TestHostLoadEmptyPayloadNullSuccess (0.07s)
    --- PASS: TestHostLoadEmptyPayloadNullSuccess/init (0.00s)
    --- PASS: TestHostLoadEmptyPayloadNullSuccess/process (0.00s)
    --- PASS: TestHostLoadEmptyPayloadNullSuccess/notify (0.00s)
=== RUN   TestHostLoadOversizedPayload
--- PASS: TestHostLoadOversizedPayload (0.06s)
=== RUN   TestHostLoadMemoryOutOfBoundsAccess
--- PASS: TestHostLoadMemoryOutOfBoundsAccess (0.06s)
=== RUN   TestHostLoad
--- PASS: TestHostLoad (0.06s)
=== RUN   TestHostLoadUnknownOp
--- PASS: TestHostLoadUnknownOp (0.06s)
=== RUN   TestHostLoadHandlerError
--- PASS: TestHostLoadHandlerError (0.09s)
=== RUN   TestHostLoadNullSuccess
=== RUN   TestHostLoadNullSuccess/init
=== RUN   TestHostLoadNullSuccess/process
=== RUN   TestHostLoadNullSuccess/notify
--- PASS: TestHostLoadNullSuccess (0.06s)
    --- PASS: TestHostLoadNullSuccess/init (0.00s)
    --- PASS: TestHostLoadNullSuccess/process (0.00s)
    --- PASS: TestHostLoadNullSuccess/notify (0.00s)
PASS
ok  	github.com/CentralInfraCore/wasm-module-template/module	0.639s
```

9 top-level teszt, mindegyik PASS (a 2 új teszt: `TestHostLoadABIManifestExportsPresent`,
`TestHostLoadMemoryOutOfBoundsAccess`; a `TestHostLoadEmptyOp`,
`TestHostLoadEmptyPayload`, `TestHostLoadEmptyPayloadNullSuccess`,
`TestHostLoadOversizedPayload` szintén újak).

### `make golang.quality`

```
... gofmt -s -l → (üres, formázva)
... staticcheck → (nincs hiba)
... go vet → (nincs hiba)
... govulncheck → "Your code is affected by 0 vulnerabilities."
```

### `make check`

```
... bandit: No issues identified (1204 LOC, 0 issue)
... black/ruff/mypy: OK
```

### `make test`

```
112 passed
TOTAL coverage: 85%
```

(a `tools/check_doc_links.py` 0% coverage-vel jelenik meg — nincs pytest
teszt rá, csak a `make docs.link-check` futtatja; ez egy önálló, stdlib-only
segédszkript, nem a `tests/` csomag része)

### `make docs.link-check`

```
--- Checking internal documentation links ---
docs.link-check: OK — all internal markdown links resolve.
```

## Commit és push

Egyetlen commit a `wasm/f/contracts` branch-en (`019aac5`), a `wasm/f/ci-followup`
(`4cad7df`) tetejére:

```
wasm: contracts hardening — rebuild-verify, ABI manifest, negative tests, contract docs
```

25 fájl módosítva/hozzáadva (1217 beszúrás, 18 törlés), beleértve:
- `mk/wasm.mk`, `.github/workflows/ci.yml`, `Makefile`, `README.md`,
  `README.hu.md`
- `project.yaml` (új `abi:` blokk + frissített `buildHash`)
- `module/module.wasm` (újraépítve, azonos méret, új hash)
- `module/abi_manifest_test.go`, `module/abi_negative_test.go` (új)
- `tools/check_doc_links.py` (új)
- `docs/contracts/en/{wasm-abi,envelope,host-expectations,release-artifact}.md`
- `docs/contracts/hu/{wasm-abi,envelope,host-expectations,release-artifact}.md`
- `docs/hu/concept/git-managment.{md,meta.yaml}` → `git-management.{md,meta.yaml}` (rename)
- `docs/{en,hu}/concept/declarative_ecosystem_integration.meta.yaml`,
  `docs/{en,hu}/wasm-module-authoring.md`, `MANIFEST.sha256` (frissítve)

A branch push-olva `origin/wasm/f/contracts`-ra. A PR megnyitása (`gh pr
create --base wasm/main --head wasm/f/contracts`) a környezeti korlát miatt
(lásd "PR-megnyitás státusza") nem futtatható ebben a környezetben — a
branch PR-re kész.

## Összefoglalás

Mind az 5 deliverable `implemented`, kivéve a 2. pont schema-validációs
részét, amely a `project.schema.yaml`-ra vonatkozó explicit TILOS miatt a
Go teszt-rétegbe lett áthelyezve (Deviáció #2) — funkcionálisan egyenértékű
build-time gate-tel (`make wasm.test` elbukik export-eltérésnél), de séma-
szintű mezővalidáció nélkül. A "Nem ebben a jobban" pontok (verify-release
CLI, doc status modell, STAGE-validáció, kanonikus release path) szándékosan
nincsenek implementálva vagy újratervezve — a `docs/contracts/en|hu/release-
artifact.md` célállapot-leírása ezekre épít majd egy jövőbeli, 3-tier
architekturális döntés utáni jobban.

A teljes verifikációs lánc (`validate`, `manifest-verify`, `wasm.build`,
`wasm.rebuild-verify`, `wasm.test`, `golang.quality`, `check`, `test`,
`docs.link-check`) zöld a builder konténerben. Az architektúra (WASM ABI,
wazero loadtest, buildHash signing) változatlan — a munka a varratokat zárta
be, nem tervezett újra semmit.
