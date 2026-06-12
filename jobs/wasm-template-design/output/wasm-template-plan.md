# `wasm/devel` base-repo sablon — TERV

> **Reasoning mód:** audit → tervezés.
> **Ez a dokumentum TERV, nem branch.** A `wasm/devel` tényleges feltöltése a követő
> `wasm-template-impl` job dolga (lásd 6. szakasz). Itt egyetlen sablonfájl sincs létrehozva
> a base-repo-ban — a terv leírja, *mit* kell létrehozni és *miből* öröklődik.

## 0. Bizonyíték-bázis (klónok, worktree-k)

| Forrás | Hol | Hogyan vizsgáltam |
|---|---|---|
| base-repo | `workspace/base-repo` (klón a `.git_repos/base-repo.git`-ből) | `git worktree add` → `schemas/devel`, `golang/devel` |
| `schemas/devel` | `/tmp/br-schemas` worktree | `find` + `grep -rn` (`_test` kizárva) |
| `golang/devel` | `/tmp/br-golang` worktree | `find` + `grep -rn` (`_test` kizárva) |
| relay host ABI | `CIC-Relay/core/cabinet/cicwasm.go` | `Read` + `grep -n` |
| relay guest minta | `CIC-Relay/core/cabinet/testdata/echo_json.go`, `Makefile` | `Read` + `grep -n` |
| iSDK contract | KB `c689` (`CIC-Relay/docs/en/concept/wasm_isdk.md`) | `mcp__cic-graph__get_chunk` |
| modul-release evidence | KB `c1503` (`cictor-relay_module-release-evidence.md`) | `mcp__cic-graph__get_chunk` |

**Toolchain-tény:** sem `go`, sem `tinygo` nincs a futtató környezet `PATH`-ján
(`command -v go` → "go NOT in PATH"; `tinygo version` → "tinygo NOT installed locally").
Ezért **egyetlen WASM build sem futott** ebben a jobban — minden build-állítás a
claim-evidence táblában `verifikáció szükséges` jelzéssel szerepel, nem ténymegállapításként.

---

## 1. Feltérképezés — `schemas/devel` és `golang/devel` (bizonyítékkal)

### 1.1 `schemas/devel` — a release-pipeline (ezt vesszük alapul)

A schemas-sablon a **legfejlettebb release-réteg**. A tényleges szerkezet eltér a job-spec
által vélt `release-check / release-prepare / release-close` make-target nevektől — az
**igazi** felület ennél tömörebb:

- **Make-szint:** csak két fő target van — `validate` és `release VERSION=X.Y.Z`
  (`/tmp/br-schemas/Makefile:65`, `:69`). Mindkettő delegál:
  `python -m tools.compiler validate` (`Makefile:67`) ill.
  `python -m tools.compiler release --version $(VERSION)` (`Makefile:80`).
- **A 3-fázisú release a Python rétegben él, nem make-targetekben:** a `ReleaseManager`
  (`tools/infra.py`) három fázist orchestrál:
  1. `_execute_developer_preparation_phase` (`infra.py:195`) — release-branch létrehozás,
     forrás-spec betöltés, checksum, Vault-aláírás, `project.yaml` írás, commit.
  2. **(build-rés)** — a fázis kilépéskor a release-branch-en hagyja a fejlesztőt, és
     **explicit utasítja**: „run your build process to generate artifacts and update
     `buildHash`" (`infra.py:312`).
  3. `_execute_finalization_phase` (`infra.py:336`) — `project.yaml` validálás, commit,
     annotált tag, merge `main`-be, branch-törlés.
  Az orchestrátor a `run_release_close` (`infra.py:397`), amely a **branch-állapot alapján**
  dönti el, melyik fázist futtatja (main → prepare; release-branch → finalize).
- **A signed artifact a schemas-ban:** a `metadata_for_signing` szótár
  (`infra.py:249`: `{name, version, checksum, build_timestamp}`), ahol
  `checksum = sha256(canonical_json(source spec))` (`infra.py:231`). A Vault transit-aláírás
  (`vault_service.sign`, `infra.py:263`) eredménye a `project.yaml` `metadata.sign` mezőjébe
  kerül (`infra.py:273`, write `infra.py:295`). **A `buildHash` mező létezik, de üresen
  íródik** (`infra.py:281`) — ezt a build-rés tölti ki. → **A schemas a forrás-spec
  checksumját írja alá, NEM egy bináris artifaktot.** (Ez a kulcs a WASM-deltához, lásd 2.2.)
- **Commit-szintű aláírás (ortogonális a release-től):** minden commit Vault transit-tal
  aláírt a `commit-msg` hook által — `KEY_NAME="cic-my-sign-key"`
  (`tools/git_hook_commit-msg.sh:13`), `transit/sign/${KEY_NAME}` (`:51`),
  `[signing-metadata]` trailer a commit-üzenetbe (`:76`).
- **Manifest-integritás:** `manifest-verify` (`Makefile:91`, `sha256sum -c MANIFEST.sha256`)
  és `manifest-update` (`Makefile:95`).
- **CLI:** `tools/compiler.py` argparse — `validate` subcommand (`compiler.py:103`),
  `release` subcommand `--version`-nel (`compiler.py:107`); dispatch
  `run_validation` (`compiler.py:170`) / `run_release_close` (`compiler.py:174`).

### 1.2 `golang/devel` — Go toolchain + quality réteg

- **A Go quality-targetek a `mk/golang.mk`-ban élnek:** `golang.fmt-check` (`mk/golang.mk:83`),
  `golang.lint` (staticcheck+ineffassign, `:87`), `golang.vet` (`:99`),
  `golang.vuln` (govulncheck, `:186`), összevont `golang.quality` (`:111`),
  `golang.coverage-check-pkgs` (per-package küszöb, `:169`), `golang.build` quality-gate-ekkel
  (`:240`), `golang.symbols` (`:114`).
- **⚠️ STÁTUSZ-FINOMSÁG (scaffold):** a `golang/devel` top-`Makefile` **kizárólag**
  `include mk/infra.mk`-t tartalmaz (`/tmp/br-golang/Makefile:9`) — **a `mk/golang.mk`-t
  SEHOL nem include-olja** (`grep -n include Makefile` → egyetlen találat). Tehát a Go
  quality-réteg a sablonban **fájlként jelen van, de bekötetlen** → ez a CIC háromszintű
  státusz szerint **scaffold**, nem implemented. A `validate`/`release` target a golang-ágban
  is a schemas-os `python -m tools.compiler`-re mutat (`/tmp/br-golang/Makefile:70`, `:74`).
- A job-spec által említett `scripts/{gen_manifest,quality,lint_local,fmt_local,ai_verify}.sh`
  **nem létezik** a `golang/devel`-ben (`ls /tmp/br-golang/scripts` → "No such file or
  directory") — a quality logika a `mk/golang.mk`-ban van, nem külön scriptekben. (A job-spec
  kontextusa itt elavult; a terv az ABT állapotot követi.)

### 1.3 Relay host ABI — amihez a guest-nek illeszkednie kell

- A host három exportált függvényt **követel** (`cicwasm.go:243-245`):
  `Call`, `allocate`, `deallocate`; hiányuk → „does not export required ABI functions"
  (`cicwasm.go:247`).
- Result-csomagolás: a guest `(size << 32) | pointer` packed `uint64`-et ad
  (`cicwasm.go:325`); a payload JSON `{data, error}` (`GuestResult struct`, `cicwasm.go:346`).
- A host op-onként hív: `Init/Process/Get/Notify` → `callGuest(ctx, "init|process|get|notify", …)`
  (`cicwasm.go:267-281`), tehát a guest `Call` **op-stringre dispatchel**.
- A host wazero + `wasi_snapshot_preview1`-et instantiál (`cicwasm.go:66`), és
  **`WithStartFunctions()`** — nem hívja a `_start`-ot, mert ezek libek, nem appok
  (`cicwasm.go:178`).
- Nyers guest-minta: `echo_json.go` — `//go:build wasip1` (`:1`), `//export allocate`
  C.malloc-kal (`:12-14`), `//export deallocate` C.free-vel (`:17`), `//export Call`
  op-dispatch-csel (`:25`), packelt return `(uint64(resultSize) << 32) | uint64(resultPtr)`
  (`:50`). **Ezt a boilerplate-et kell a sablonnak fejlesztő-barát formában elrejtenie.**
- **Build-tény:** a relay ezt a `.go`-t **TinyGo-val** fordítja:
  `tinygo build -o $@ -target wasi -scheduler=none $<`
  (`CIC-Relay/core/cabinet/Makefile:28`), a `test-wasm` target alatt (`:18`).

### 1.4 iSDK contract — `concept` státusz (KB)

KB `c689` (`docs/en/concept/wasm_isdk.md`, `tags: concept`): `Call(op, auth_context_json,
data_json) -> (data_json, error_json|null)`; op ∈ {init, process, get, notify};
hibakódok INPUT/RUNTIME/INTERNAL/RESOURCE/TIMEOUT; v1 **szinkron, WASI off, determinisztikus**.
A `notify` v1-ben opcionális stub. **Az iSDK guest-SDK jelenleg `concept`** — ez a sablon
lenne az első konkrét megtestesülése.

---

## 2. WASM-delta terv

### 2.1 Build-target döntés — **TinyGo (`-target wasip1 -scheduler=none`)**

**Döntés: TinyGo.** Nem std-Go `GOOS=wasip1`. Indoklás bizonyítékkal:

| Szempont | TinyGo `-target wasi/wasip1` | std-Go `GOOS=wasip1 GOARCH=wasm` |
|---|---|---|
| Bizonyított-e a relay-ben | **IGEN** — `core/cabinet/Makefile:28` ez az **egyetlen** parancs, ami a host által betöltött `.wasm`-ot előállítja | Nincs rá build-parancs a repóban |
| cgo `C.malloc`/`C.free` (a minta ABI alapja, `echo_json.go:14,:19`) | TinyGo wasi-libc-vel támogatja | std `GOOS=wasip1` **nem** támogat cgo-t C toolchain nélkül — az `allocate` jelenlegi alakja nem fordulna |
| Artifact-méret / determinizmus | kicsi, `-scheduler=none` → nincs goroutine-ütemező, illeszkedik a v1 szinkron/WASI-off contracthoz (`c689`) | teljes Go runtime + GC + scheduler, nagy bináris |
| WASI import-felület | `wasi_snapshot_preview1`-et emittál, a host pont ezt instantiálja (`cicwasm.go:66`) | szintén wasip1, de a fenti cgo-blokkoló miatt elesik |

**Pontosítás a build-tagre:** a minta `//go:build wasip1` taget hordoz (`echo_json.go:1`), a
relay viszont `-target wasi`-t használ. Hogy a build-tag garantáltan illeszkedjen, a sablon
**`-target wasip1`-et** írjon elő (TinyGo ≥ 0.31), és a `wasm-template-impl` job
**verifikációs lépése** ellenőrizze, hogy a használt TinyGo verzió a `wasip1` taget definiálja
(különben a sablon `wasi` taget használjon). Ez a finomság a kockázati oszlopban szerepel.

**Elvetett alternatíva (de fallback-ként megjelölve):** std-Go `GOOS=wasip1` akkor jöhet szóba,
ha egy modul olyan stdlib-et igényel, amit a TinyGo nem fed le — ekkor az `allocate`/`deallocate`
implementációt a Go runtime memory-export alapúra kell cserélni (nem cgo malloc). Ez a sablon
**v1-ben nem cél**, csak dokumentált kiút.

### 2.2 Signed release artifact — `.wasm` + meta-manifest, a buildHash aláírásával

**Mi kerül aláírásra:** **a `.wasm` ÉS a meta-manifest** (`project.yaml`), összekötve.

A schemas a *forrás-spec* checksumját írja alá (`infra.py:231,249`), a `buildHash` üresen marad
(`infra.py:281`). WASM-nál a tényleges artifact egy **bináris**, ezért a deltában:

1. A build-rés (a 3 fázis közötti lépés, `infra.py:312`) TinyGo-val előállítja a `.wasm`-ot,
   és **`buildHash = sha256(module.wasm)`**-t ír a `project.yaml`-be.
2. **WASM-specifikus kiterjesztés a finalization fázishoz:** a Vault-aláírásnak a `buildHash`-t
   **is fednie kell** (a schemas signing-blokkja jelenleg nem fedi). Mivel a bináris hash csak
   build után áll elő, az aláírást vagy (a) a finalization fázisba kell mozgatni a teljes
   `{name, version, checksum, buildHash, build_timestamp}` metadata fölött, vagy (b) egy második,
   `buildHash`-ra szóló aláírást kell adni. **Ajánlás: (a)** — egyetlen aláírás, amely
   forrás-spec + bináris-hash párt köt egységbe (provenance + integrity egyben).

**Illesztés a 3-fázisú release-be (változatlan branch-vezérlés, `infra.py:417-427`):**

```
main branch ──make release VERSION=x──▶ prepare fázis
                                         (source manifest checksum, release-branch létrehozás)
                                              │
                            release-branch ◀──┘  (itt vagy)
                                 │
                                 ├─ make wasm.build  (TinyGo → module.wasm, buildHash kitöltés)
                                 │
release-branch ──make release VERSION=x──▶ finalize fázis
                                         (project.yaml validál: buildHash kötelező + nemüres,
                                          teljes metadata aláírás, tag, merge main)
```

A **signed artifact tehát kettős**: a `module.wasm` (a futtatható) + a `project.yaml`
meta-manifest, amelynek `metadata.sign` mezője a `buildHash`-t is fedő Vault-aláírás. Ez
kielégíti a KB `c1503` supply-chain követelményét (csak aláírt, auditált forrásból származó
kód → artifact).

### 2.3 Guest ABI scaffold — az iSDK első váza

A sablon elrejti az `allocate`/`deallocate`/`Call` boilerplate-et (a host ABI-ja,
`cicwasm.go:243-245`), és a modul-szerzőnek csak a **domain-belépőket** (init/process/get/notify)
kell kitöltenie. Két fájlra bontva:

**`module/abi.go`** — ÚJ, a sablon adja, a szerző nem nyúl hozzá (az iSDK runtime-váza):

```go
//go:build wasip1

// Package main is the WASM guest entrypoint. abi.go is the iSDK boilerplate —
// it implements the host-required ABI (allocate/deallocate/Call) and dispatches
// op-strings to the domain handlers in handlers.go. DO NOT EDIT for normal modules.
package main

// #include <stdlib.h>
import "C"
import (
	"encoding/json"
	"unsafe"
)

func main() {}

//export allocate
func allocate(size uint32) uintptr { return uintptr(C.malloc(C.size_t(size))) }

//export deallocate
func deallocate(ptr uintptr, size uint32) { C.free(unsafe.Pointer(ptr)) }

// guestResult mirrors the host's GuestResult (cicwasm.go:346): {data, error}.
type guestResult struct {
	Data  json.RawMessage `json:"data"`
	Error json.RawMessage `json:"error"`
}

//export Call
func Call(opPtr, opLen, authPtr, authLen, dataPtr, dataLen uint32) uint64 {
	op := readString(opPtr, opLen)
	auth := readBytes(authPtr, authLen)
	data := readBytes(dataPtr, dataLen)

	var out []byte
	var derr error
	switch op { // op-dispatch — host: cicwasm.go:267-281
	case "init":
		out, derr = Init(auth, data)
	case "process":
		out, derr = Process(auth, data)
	case "get":
		out, derr = Get(auth, data)
	case "notify":
		out, derr = Notify(auth, data)
	default:
		return pack(marshalErr("INPUT", "unknown op: "+op))
	}
	if derr != nil {
		return pack(marshalErr("RUNTIME", derr.Error()))
	}
	return pack(marshalData(out))
}

// pack mirrors the host contract: (size << 32) | pointer  (cicwasm.go:325).
func pack(b []byte) uint64 {
	if len(b) == 0 {
		return 0 // host treats packed 0 as null/empty (cicwasm.go:337)
	}
	ptr := allocate(uint32(len(b)))
	copy(unsafe.Slice((*byte)(unsafe.Pointer(ptr)), len(b)), b)
	return (uint64(uint32(len(b))) << 32) | uint64(ptr)
}

// readString/readBytes/marshalData/marshalErr — helper bodies omitted in the PLAN;
// the impl job fills them. Contract: marshalErr emits {"error":{"code","message"}},
// marshalData emits {"data":<raw>}.  Error codes ∈ INPUT|RUNTIME|INTERNAL|RESOURCE|TIMEOUT (c689).
```

**`module/handlers.go`** — ÚJ, **üres slot a modul-szerzőnek** (a domain-logika):

```go
//go:build wasip1

package main

// Domain handlers — implement your module here. Each returns (dataJSON, error).
// Signatures match the iSDK contract c689: (auth_context_json, data_json) -> (data_json, error).
// v1 is synchronous, deterministic, WASI-off (no external I/O).

func Init(auth, data []byte) ([]byte, error)    { /* TODO: bring-up/config */ return nil, nil }
func Process(auth, data []byte) ([]byte, error) { /* TODO: main op */ return nil, nil }
func Get(auth, data []byte) ([]byte, error)     { /* TODO: idempotent read */ return nil, nil }
func Notify(auth, data []byte) ([]byte, error)  { /* TODO: v1 stub */ return nil, nil }
```

**Verifikációs lépés (kötelező, nem feltételezett):** a sablon akkor „működik", ha
(1) `make wasm.build` zöld (TinyGo `module.wasm`-ot emittál), **és** (2) a host betölti:
`NewWasmManager` + `NewHostInstance` nem ad „does not export required ABI functions" hibát
(`cicwasm.go:247`), **és** (3) egy `Call("get", …)` `{data,error}` JSON-t ad vissza. Ez egy
go-test a sablonban (`module_loadtest`), amely a relay `cabinet` csomagjára épül — a
`wasm-template-impl` job DoD-ja.

---

## 3. Teljes `wasm/devel` fájllista forrás-megjelöléssel

| Fájl | Forrás | Megjegyzés |
|---|---|---|
| `Makefile` | öröklött `schemas/devel`-ből + ÚJ wasm targetek | `validate`/`release`/`manifest-*` öröklött; **ÚJ:** `include mk/wasm.mk`, `wasm.build`, `wasm.test` |
| `mk/infra.mk` | öröklött `schemas/devel`-ből | konténer-lifecycle, fmt/lint/check |
| `mk/wasm.mk` | **ÚJ (WASM-specifikus)** | TinyGo build (`-target wasip1 -scheduler=none`), `.wasm` checksum → buildHash, `wasm.test` (host-load) |
| `tools/compiler.py` | öröklött `schemas/devel`-ből | release CLI (`validate`/`release`) |
| `tools/infra.py` | öröklött `schemas/devel`-ből + ÚJ delta | **ÚJ delta:** finalization signing kiterjesztése `buildHash`-re (2.2) |
| `tools/finalize_release.py` | öröklött `schemas/devel`-ből | release finalizálás |
| `tools/releaselib/{git_service,vault_service,exceptions}.py` | öröklött `schemas/devel`-ből | Vault transit + git műveletek |
| `tools/git_hook_commit-msg.sh` | öröklött `schemas/devel`-ből | commit-szintű Vault aláírás (`cic-my-sign-key`) |
| `tools/vault-sign-agent.sh`, `tools/vault-rootCA-sign-agent.sh` | öröklött `schemas/devel`-ből | ideiglenes Vault signing szerver |
| `tools/init-hooks.sh`, `tools/init_from_template.sh` | öröklött `schemas/devel`-ből | hook bekötés, sablon-init |
| `mk/golang.mk` | öröklött `golang/devel`-ből (**és bekötve!**) | fmt-check/lint/vet/vuln a guest `.go`-ra; a schemas-ágban nincs, a golang-ágban scaffold — itt **wire-olni kell** (delta) |
| `module/abi.go` | **ÚJ (WASM-specifikus)** | iSDK boilerplate — allocate/deallocate/Call + op-dispatch (2.3) |
| `module/handlers.go` | **ÚJ (WASM-specifikus)** | üres init/process/get/notify slotok a szerzőnek |
| `module/module_loadtest.go` | **ÚJ (WASM-specifikus)** | host-load smoke test a relay `cabinet` ABI-ja ellen |
| `project.yaml` | öröklött `schemas/devel`-ből + ÚJ mező-szemantika | **ÚJ:** `buildHash` kötelező+nemüres a finalize előtt; spec a modul accepts/produces sémája |
| `project.schema.yaml` | öröklött `schemas/devel`-ből | meta-séma |
| `docker-compose.yml`, `Dockerfile` | öröklött `golang/devel`-ből + ÚJ delta | **ÚJ delta:** TinyGo + wat2wasm a builder image-be |
| `MANIFEST.sha256` | öröklött `schemas/devel`-ből | forrás-integritás |
| `docs/{en,hu}/…` | öröklött (sablon-doksi) + ÚJ | **ÚJ:** `wasm-module-authoring.md` (hogyan tölts ki handlers.go-t) |
| `.github/workflows/ci.yml` | öröklött `schemas/devel`-ből + ÚJ delta | **ÚJ delta:** `wasm.build` + `wasm.test` lépés |
| `.gitignore`, `.editorconfig`, `.yamllint`, `renovate.json`, `pyproject.toml`, `requirements*.txt`, `pytest.ini` | öröklött `schemas/devel`-ből | toolchain-konfig |
| `README.md`, `README.hu.md`, `LICENSE*` | öröklött + ÚJ tartalom | WASM-modul sablon leírás |

**Összegzés:** a release-gerinc (`tools/`, `mk/infra.mk`, `project*.yaml`, hookok) **schemas/devel**-ből
öröklött; a Go-quality (`mk/golang.mk`) **golang/devel**-ből öröklött **és bekötendő**; a
WASM-mag (`module/`, `mk/wasm.mk`, signing-delta, builder-image TinyGo) **ÚJ**.

---

## 4. Claim-evidence tábla

> A „Bizonyíték" oszlop minden implemented/scaffold állításnál `file:line`. A reachability
> artifact a fenti `grep -rn` kimenetekből (`_test` kizárva).

| Állítás | Státusz | Bizonyíték (file:line) | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A schemas release Make-felülete `validate` + `release VERSION=` (NEM `release-check/prepare/close` targetek) | implemented | `/tmp/br-schemas/Makefile:65,69,80` | `make help` / target-grep | A job-spec elnevezés elavult; a 3 fázis a Python-rétegben van |
| 3-fázisú release a `ReleaseManager`-ben (prepare/build-rés/finalize) | implemented | `infra.py:195,312,336,397` | pytest `tests/test_tools/test_infra.py` (KB szerint zöld, lokálisan nem futtattam) | Lokális futtatás nem történt |
| A schemas a **forrás-spec checksumját** írja alá, a `buildHash` üres | implemented | `infra.py:231,249,263,281` | kód-olvasás + dry-run `make release DRY_RUN=1` | `buildHash` üres → bináris nincs lefedve (WASM-delta indoka) |
| Commit-szintű Vault aláírás (`cic-my-sign-key`, transit) | implemented | `git_hook_commit-msg.sh:13,51,76` | commit + `[signing-metadata]` trailer ellenőrzés | Vault elérhetőség futásidőben |
| Manifest-integritás target-ek | implemented | `/tmp/br-schemas/Makefile:91,95` | `make manifest-verify` | — |
| Go quality-réteg targetjei léteznek (`golang.quality` stb.) | scaffold | `mk/golang.mk:83,87,99,111,169,186,240` | `grep` a targetekre | — |
| **A `golang/devel` top-Makefile NEM include-olja a `mk/golang.mk`-t** → a Go-quality bekötetlen | scaffold | `/tmp/br-golang/Makefile:9` (csak `include mk/infra.mk`) | `grep -n include Makefile` → 1 találat | A wasm/devel-ben wire-olni KELL, különben dead |
| `scripts/*.sh` (job-spec által vélt) nem létezik golang/devel-ben | tény (hiány) | `ls /tmp/br-golang/scripts` → "No such file or directory" | `ls`/`find` | Job-spec kontextus elavult |
| Host 3 exportált ABI függvényt követel (Call/allocate/deallocate) | implemented | `cicwasm.go:243,244,245,247` | go-test `cabinet` csomag | — |
| Result packelés `(size<<32)|ptr`, payload `{data,error}` | implemented | `cicwasm.go:325,346` | host-load smoke test | — |
| Host op-onként hív (init/process/get/notify) | implemented | `cicwasm.go:267,271,275,279` | kód-olvasás | — |
| Host wazero + wasi_snapshot_preview1, `WithStartFunctions()` (nem `_start`) | implemented | `cicwasm.go:66,178` | kód-olvasás | — |
| Guest minta: allocate/deallocate/Call cgo-malloc-kal | implemented (testdata) | `echo_json.go:1,12,17,25,50` | `Read` | Nyers boilerplate — a sablon elrejti |
| **A relay a guest `.go`-t TinyGo-val fordítja** (`-target wasi -scheduler=none`) | implemented | `CIC-Relay/core/cabinet/Makefile:28` (+ `:13,18`) | `make test-wasm` (toolchain szükséges) | TinyGo nem volt telepítve → build nem futott |
| iSDK contract (Call/op/error-codes/v1-szinkron) | **concept** | KB `c689` (`docs/en/concept/wasm_isdk.md`) | KB `get_chunk` | Nincs runtime megfelelője — ez a sablon lenne az első |
| WASM modul supply-chain: csak aláírt forrásból artifact | concept | KB `c1503` (`module-release-evidence.md`) | KB `get_chunk` | — |
| **A wasm/devel sablon build-je zöld + host betölti** | **terv (nem verifikált)** | — (nincs még fájl) | `wasm-template-impl` DoD: `make wasm.build` + host-load test | **go/tinygo nincs PATH-on; egyetlen build sem futott** |

---

## 5. Nyitott híd (bridge detector)

```
concept (iSDK c689) → code (module/abi.go — ÚJ, még nem létezik) → runtime (cicwasm.go ABI) → audit (signed project.yaml + buildHash)
```

A modell létezik (host ABI implemented, iSDK contract dokumentált), de az **implementációs híd
itt szakad meg:** `module/abi.go` + `mk/wasm.mk` **még nem létezik** a base-repo egyetlen
branch-én sem (`git branch -a` → nincs `wasm/*`). A `wasm-template-impl` job zárja ezt a hidat.

---

## 6. Követő job spec-vázlat — `wasm-template-impl`

**Cél:** a jelen terv alapján létrehozni a base-repo `wasm/devel` sablon-branchét, és
verifikálni, hogy egy belőle gyártott modul ténylegesen lefordul (TinyGo) és betölthető a
relay host-frame-be.

**Mit rakjon a `wasm/devel`-re (a 3. szakasz fájllistája szerint):**
- `module/abi.go` (iSDK boilerplate, 2.3 váz kitöltve), `module/handlers.go` (üres slotok),
  `module/module_loadtest.go` (host-load smoke test a `cabinet` ABI ellen).
- `mk/wasm.mk` — `wasm.build` (TinyGo `-target wasip1 -scheduler=none`),
  `wasm.test` (host-load), `.wasm` sha256 → `project.yaml.buildHash`.
- A schemas release-gerinc öröklése (`tools/`, `mk/infra.mk`, `project*.yaml`, hookok) +
  **`infra.py` signing-delta**: a finalization fázis aláírása fedje a `buildHash`-t (2.2/a).
- `mk/golang.mk` öröklése **és bekötése** a top-Makefile-be (a golang/devel scaffold-hibájának
  javítása).
- builder image: TinyGo + wat2wasm (`docker-compose.yml`/`Dockerfile` delta).
- doksi: `docs/{en,hu}/wasm-module-authoring.md`.

**Definition of Done:**
- [ ] `wasm/devel` branch létrehozva, push (review artifact, nem main).
- [ ] `make wasm.build` **zöld** — TinyGo `module.wasm`-ot emittál (a build ténylegesen lefut).
- [ ] `make wasm.test` **zöld** — a relay `cabinet` host (`NewHostInstance`) betölti a `.wasm`-ot
      „does not export required ABI functions" hiba nélkül (`cicwasm.go:247`), és egy `Call("get")`
      `{data,error}` JSON-t ad.
- [ ] `make release VERSION=… DRY_RUN=1` a prepare→finalize láncot a `buildHash`-t is fedő
      aláírással szimulálja.
- [ ] `mk/golang.mk` bekötve (a top-Makefile include-olja), `make golang.quality` zöld a
      `module/`-ra.
- [ ] TinyGo build-tag verifikálva: a használt TinyGo verzió `-target wasip1` mellett a `wasip1`
      build-taget definiálja (különben `-target wasi` + tag-igazítás).

**Tiltott rövidítés a követő jobnak:** a sablonfájl léte ≠ működő build. A DoD két zöld
build-lépést (`wasm.build`, `wasm.test`) **ténylegesen futtatva** követel meg — nem
feltételezve.
