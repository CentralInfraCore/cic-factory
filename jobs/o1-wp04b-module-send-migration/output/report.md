# WP-04b jelentés — az Oracle modul `cic-flow.send` migrációja a `devel` ae3c962 bázisra

**Job:** `o1-wp04b-module-send-migration` · **Végrehajtó:** factory agent ·
**Kezdés (UTC):** 2026-11-28 16:18 · **Cél-repó:** `cic-module-oracle-cloud`

> Ez a jelentés inkrementálisan készül: minden szakasz a hozzá tartozó commitban
> kerül be, a nyers parancskimenetek az `output/evidence/` alatt.

---

## 0. A Git-bázis mechanikus igazolása (B-1..B-6)

Nyers napló: [`evidence/10-git-base-verification.log`](evidence/10-git-base-verification.log),
[`evidence/11-pr54-state.log`](evidence/11-pr54-state.log).

### B-1 — az előírt base elérése

```
$ git merge-base feature/o1-wp04b-module-send-migration ae3c96237839c9fd06649c918a2194a79ebd8cb1
ae3c96237839c9fd06649c918a2194a79ebd8cb1

$ git rev-parse feature/o1-wp04b-module-send-migration
ae3c96237839c9fd06649c918a2194a79ebd8cb1
```

A merge-base **pontosan az előírt base** (`ae3c962`), mert az ág a munka kezdetén
azonos vele. **B-1: PASS.**

### B-2 — a munkacsomag saját deltája a munka kezdetén

```
$ git rev-list --count ae3c962..feature/o1-wp04b-module-send-migration
0

$ git diff --stat ae3c962 feature/o1-wp04b-module-send-migration
(üres kimenet)
```

A kiinduló állapot deltája nulla: a bázis igazolása előtt semmi nem került az
ágra. **B-2: PASS** (a záró delta a jelentés 5. szakaszában).

### B-3 — a cél-ág (`devel`) előrehaladása és a PR-állapot

```
$ git rev-parse origin/devel
ae3c96237839c9fd06649c918a2194a79ebd8cb1

$ git rev-list --count ae3c962..origin/devel
0
```

A `devel` feje a mérés idején **azonos az előírt base-szel**: nincs elavult
eltérés, a job a `devel` csúcsára épül. (A `git fetch --prune` egyetlen
frissítést hozott: `origin/integration/o1` 7704e66..e4eebc8 — ez nem a bázis.)

A régi WP-04 PR (#54) mért állapota:

```
$ gh pr view 54 --json number,title,baseRefName,headRefName,mergeable,mergeStateStatus,state,isDraft
{"baseRefName":"devel","headRefName":"feature/o1-wp04-sign-send","isDraft":true,
 "mergeStateStatus":"DIRTY","mergeable":"CONFLICTING","number":54,"state":"OPEN",
 "title":"O-1 WP-04: migrate the Oracle guest to cic-flow.send"}
```

### B-4 — a #54 elavult bázisának szétválasztása a saját deltától

```
$ git merge-base origin/feature/o1-wp04-sign-send ae3c96237839c9fd06649c918a2194a79ebd8cb1
5d0a3278c6cc68f4808edacb8ee4300299af3153

$ git rev-list --count ae3c962..origin/feature/o1-wp04-sign-send
2

$ git rev-list --count 5d0a327..origin/devel
63
```

A mérés megerősíti a `ref/o1-integration-findings-2026-11-28.md`-t: a #54
tényleges merge-base-e `5d0a327`, **63 commit-tal a `devel` mögött**; a #54 saját
hozzájárulása 2 commit. A #54 saját deltája (`git diff --stat 5d0a327
origin/feature/o1-wp04-sign-send`):

```
 MANIFEST.sha256                                |  23 +--
 docs/design/specs/provider-abi.md              |   4 +-
 docs/design/specs/relay-sign-send-interface.md |  10 ++
 module/cicflow_guest.go                        |  23 +--
 module/cicflow_host.go                         |  21 +--
 module/host_mock_test.go                       | 170 ++++++++++++++++++
 module/module.wasm                             | Bin 1173093 -> 1173869 bytes
 module/module_loadtest_test.go                 |  65 +++----
 module/oci_sign.go                             |  70 --------
 module/provider.go                             | 182 ++++++++++++-------
 module/provider_test.go                        |   6 +-
 module/relay_integration_test.go               |  13 +-
 module/send_contract_test.go                   | 240 +++++++++++++++++++++++++
 project.yaml                                   |  14 +-
 14 files changed, 621 insertions(+), 220 deletions(-)
```

A `ref/wp04-own-delta.patch` ebből 13 fájlt tartalmaz (a `module.wasm` bináris
kihagyva) — ez a portolás bemenete. **B-4: PASS.**

### B-5 / B-6

- **B-5:** a #54 `CONFLICTING/DIRTY` — a rajta futott zöld CI **nem** acceptance.
  A WP-04b záró PR-jára a `MERGEABLE` követelmény a 7. szakaszban mérve.
- **B-6:** minden fenti érték parancskimenet, nem ágens-állítás.

### Megjegyzés a környezetről (mért, nem workaround)

- A factory `PostToolUse` hookja (`python3 $CIC_WORKDIR/tools/hooks/log-event.py`)
  **minden** Bash-hívásnál hibára fut, mert a `CIC_WORKDIR` környezeti változó
  üres: `python3: can't open file '/tools/hooks/log-event.py'`. Ezt nem kerültem
  meg és nem írtam át; jelentem.
- **Commit-aláíró hook nincs elérhető** a `cic-factory` klónban: `.git/hooks/`
  csak `*.sample` fájlokat tartalmaz, a `core.hooksPath` és a `commit.gpgsign`
  nincs beállítva. A commitok így **aláírás nélkül** készülnek — nem kerültem meg
  semmit, ez a mért környezeti állapot.
- A `cic-factory` klón git-identitása placeholder volt (`Your Name
  <you@example.com>`); a job elején valós lokális identitásra állítottam
  (`git config user.name/user.email`, repo-lokálisan).
- A `ref/` könyvtárban a job `input.md` által hivatkozott `ref/schemas/`,
  `ref/examples/` és `ref/vectors/` **nincs jelen** (csak a négy `.md` és a
  `.patch`). A wire szerződés így a `ref/wp04-own-delta.patch` és a
  `docs/design/specs/relay-sign-send-interface.md` alapján kerül portolásra; a
  séma-fájl szerinti validáció **UNVERIFIED (bemenet hiányzik)**.

---

## 1. A portolás módja (AC-04b-2)

A #54 **nem** merge-elve és nem egészben cherry-pickelve került át: a `ref/wp04-own-delta.patch`
13 fájlos deltáját **kézzel** vezettem át, hunkonként értékelve, hogy a `devel` időközbeni
viselkedése (M3/M4a kapuk, `pollTargetPath`, `createdResourceID` + 202/Work Request ág,
`executeSteps`) sértetlen maradjon. (Egy korábbi futás `git merge origin/feature/o1-wp04-sign-send`-del
indult, konfliktusos fákat hagyva és commit nélkül; a modul-klón ezért `devel ae3c962`-re lett
visszaállítva — a mostani ág ettől a tiszta ponttól épül.)

Hat commit, mindegyik külön pushol (`feature/o1-wp04b-module-send-migration`):

| Commit | Tartalom |
|---|---|
| `1e670e7` | `cic-flow.send` az egyetlen host import (guest + host seam, `project.yaml` `abi.imports`, 2 spec) |
| `3ad1630` | `provider.go`: strukturált kérés, `oci_sign.go` törlése, `observedAtFormat` |
| `144b293` | a mock a határ host oldalára; `host_mock_test.go`, `send_contract_test.go`, `ss03_poll_create_denial_test.go`, `host_codes_test.go` |
| `96b3eab` | a committolt `module.wasm` újraépítése a portolt forrásból + `buildHash` + `MANIFEST.sha256` |
| `d175c4e` | docgate: a két új konstans dokumentálása, az artifact újraépítése erről a forrásról |
| `e591433` | az SS-03 elutasítási kódok a Relay tényleges viselkedéséhez igazítva |

A `cic-factory` oldalon a jelentés, a `claim-mapping.md` és az `evidence/` naplók a
`feature/o1-wp04b-module-send-migration` ágon.

**A portolás eltérései a #54 szövegétől (szándékos, indokolt):**

1. A #54 a `module/oci_sign.go` tartalmát a `host_mock_test.go`-ba tette, de **megtartotta** a
   `testCallHostSign`/`testCallHostActuate` neveket; én is így tettem — ez az, ami 13 teszt-fájlt
   változtatás nélkül hagy. Ezen túl a mock **a guest strukturált kérését is rögzíti**
   (`Sent`/`sendCount()`/`lastSend()`), és kapott egy `Refuse` horgot, hogy a host **megnevezett
   kóddal** utasíthasson el — a #54-ben ez nem volt meg, és nélküle az AC-04b-5 nem mérhető.
2. A #54 a két érintett spec-fájlba **magyar** bekezdést illesztett; ezek a fájlok (`docs/design/specs/`)
   végig angolok, ezért a felülírás-jegyzetet **angolul** írtam (a jelentés magyar, a repo-szabály
   szerint).
3. A #54 `host_mock_test.go`-ja a `body_sha256`-ot a base64 digestből állította elő, és egy
   `_ = strconv.Itoa` maradékot tartalmazott; nálam a `body_sha256` hex (a Relay alakja), a maradék
   nincs benne.
4. A #54 `send_contract_test.go`-ja a `wasmPath` / `projectYAMLPath` neveket és egy `path`-alapú
   `pollRequest`-et használt; a `devel` `pollTargetPath`-ja miatt a poll `work_request_id`-vel megy,
   és az artifact-utat a `devel` `wasmBinaryPath()`-ja adja.

## 2. Claim–evidence tábla

Jelölések — **Szint:** `implemented` / `scaffold` / `concept`. **Bizonyíték-típus:** `komponens`
(modul-teszt), `relay` (a Relay saját tesztje/kódja), `artifact` (a lefordított wasm), `provizórius`
(teszt-kulcsos/mock). A teljes assertion-megfeleltetés: [`claim-mapping.md`](claim-mapping.md).

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A guest egyetlen `cic-flow` host importja a `send` | implemented | `artifact`: `TestWasmArtifactImportsOnlyCICFlowSend` a committolt `module.wasm`-on; az elavult binárison `[actuate sign]`-nal **elbukott** | wazero `CompileModule` + `ImportedFunctions()`; `evidence/34`, `evidence/43` | — |
| A guest nem épít aláírást / `Authorization`-t / dátumot / kanonikus stringet / kulcsot | implemented | `komponens`: `TestSendRequestIsStructuredAndCarriesNoHostOwnedFields` (teljes JSON-bejárás), `TestGuestSourcesBuildNoAuthorization` | bevetett hibával mérve (FAULT 3): mindkettő bukik, megnevezve a mezőt — `evidence/20` | a tiltólista felsorolás-alapú: új host-birtokolt mező felvételekor bővíteni kell |
| `module/oci_sign.go` (guest-oldali signálás) megszűnt | implemented | `komponens`: a fájl törölve (70 sor), `git diff --stat`; a formula csak teszt-fájlban él | `evidence/60`, `grep` nem-teszt forrásokon | — |
| Az `actuateSigned` production útvonalon be van kötve mind az 5 művelethez | implemented | `komponens`+reachability: `provider.go:713 destroy`, `:801 invoke`, `:867 poll`, `:1111 observe`, `:1429 execute` → `:1738 callHostSend` | `grep -rn --include="*.go" | grep -v _test.go` — `evidence/60` | — |
| A kérés alakja a Relay `wireRequest` v1-je | implemented | `relay`: `CIC_Relay pkg/hostsign/engine.go:91-103` (olvasva), `types.go` | a struct-ot a host oldalról vettem, nem feltételeztem | a Relay `trace_id`-t is fogad; a guest nem küld — opcionális mező |
| `path`/`query` szétválasztva megy (SS-03 külön validálja) | implemented | `komponens`: `TestSendQueryIsSplitFromPath` | FAULT 5 → bukik — `evidence/20` | a guest nem URL-dekódol: a `query` értékek nyersen mennek át |
| A denial/failure/host-error **nem** siker, és a host kódját viszi | implemented | `komponens`: `TestSendDeniedFailedAndErrorAreErrors`, `TestDenialAndFailureKeepTheirOwnWording` | FAULT 1 és 2 → bukik — `evidence/20` | — |
| `poll` és `create` a host policy-jén elutasítva, megnevezett kóddal | implemented | `relay`: `hostsign.Policy.ValidateTarget` mérés → `POLICY_TARGET` (ahogy a modul küldi), `POLICY_PATH` / `POLICY_METHOD` (ha az operáció neve a policy-ban van); `komponens`: a két teszt mind a két kódra | `evidence/50` (Relay-kód ellen futtatott próba), `evidence/20` (FAULT 2) | a modul-oldali teszt a host elutasítását **mockolja**; az élő Relay-integráció nem része ennek a jobnak |
| A `devel` viselkedése megőrizve (M3/M4a, `pollTargetPath`, `createdResourceID`, `executeSteps`) | implemented | `komponens`: 0 eltávolított teszt (141→151), teljes suite 147 PASS / 0 FAIL | `go test -list` diff + teljes futás — `evidence/34`, `evidence/35`; property-szintű megfeleltetés: `claim-mapping.md` 2. szakasz | — |
| A kanonikus string és az `Authorization` a hoszté | implemented (Relay-oldalon) | `relay`: `pkg/hostsign/ociprofile/ociprofile_test.go:45,47,54,55,82` (`TestCanonicalGolden`, `TestEndToEndVerifiesAsOCI`) | a Relay tesztjeinek olvasása; **ebben a jobban nem futtattam őket** | → UNVERIFIED-ként is jelölve a 4. szakaszban |
| A committolt artifact integritása (`sha256` == `buildHash`) | implemented | `artifact`: `tools/wasm_integrity_gate.sh` → `OK` | a repo saját kapuja a pinelt imageben — `evidence/43` | — |
| A wasm bitreprodukálható | **nem áll** (mért) | `artifact`: 6 build egy forrásból → **3 különböző** digest | `evidence/31`, `evidence/32`, `evidence/42` | a különbség forrása: az `embed/file_<digest>` szimbólumok sorrendje (a string-táblák azonosak, 300/1 287 908 bájt) |
| A committolt artifact a jelenlegi forrásból készült | implemented (viselkedés-alapú) | `artifact`: a 4 fresh-guest teszt + az import-teszt a **committolt** binárison PASS | `evidence/43`; digest-egyezéssel **nem** bizonyítható (lásd fenn) | elvi rés: a viselkedési egyezés nem bijekció; a repo trust-modellje integritást ír elő, nem reprodukciót |
| SS-03 nem módosult | implemented | `relay`: a Relay repóban **nulla** változás; a próba egy eldobható másolatban fordult | `evidence/50` fejléce; a Relay klón `git status` érintetlen | — |

## 3. Mért környezeti tények és eszközhibák (nem megkerülve)

| # | Tény | Hatás |
|---|---|---|
| E-1 | A factory `PostToolUse` hookja (`python3 $CIC_WORKDIR/tools/hooks/log-event.py`) **minden** Bash-híváskor hibára fut: a `CIC_WORKDIR` üres → `can't open file '/tools/hooks/log-event.py'` | a job eseménynaplózása nem működött; nem írtam át és nem tiltottam le |
| E-2 | Commit-aláíró hook **nincs**: `.git/hooks/` csak `*.sample`, `core.hooksPath` és `commit.gpgsign` nincs beállítva egyik klónban sem; a job saját előzmény-commitja (`a9f3128`) is `%G? = N` | a commitok aláírás nélküliek — ezt jelentem, nem kerültem meg |
| E-3 | A `cic-factory` klón identitása placeholder volt (`Your Name <you@example.com>`) | repo-lokálisan valós identitásra állítva a munka elején |
| E-4 | `python -m tools.compiler set-build-hash` **nem futtatható** sem a pinelt builder imageben, sem a hoszton: a `tools/compiler.py` modul-szinten importálja a `yaml`-t, a `tools.schemalib` pedig a `pyOpenSSL`-t, holtest a parancs dokumentáltan stdlib-only, és az imageben nincs `p_venv` | a `buildHash` a dokumentált művelettel (sha256 + az egyetlen `buildHash` sor) került be, utána a repo **saját** integritás-kapuja igazolta. Javítás-javaslat: a `set-build-hash` ágat lazy importtal elválasztani |
| E-5 | A `make` wasm/teszt céljai `docker compose exec builder`-t használnak, futó compose-szolgáltatással és `p_venv`-vel | a pinelt **builder imaget** közvetlenül futtattam ugyanazokkal a parancsokkal; minden parancs a naplókban szerepel |
| E-6 | A job `input.md` a `ref/schemas/`, `ref/examples/`, `ref/vectors/` könyvtárakra hivatkozik; ezek **nincsenek** a `ref/`-ben | a wire-szerződést a `ref/wp04-own-delta.patch` és a Relay `pkg/hostsign` olvasott kódja alapján portoltam; **séma-fájl szerinti validáció: UNVERIFIED (bemenet hiányzik)** |
| E-7 | A Relay rögzített bázisa (`86ea1ab`, `main`) **nem** tartalmazza a `pkg/hostsign`-t: az a 4 rákövetkező commitban jött létre (`git merge-base --is-ancestor` igazolt, `git diff --stat 86ea1ab HEAD -- pkg/hostsign` = 20 fájl, +3412) | a host-oldali olvasás a Relay `main` fejéről (`2a645a9`) történt, nem `86ea1ab`-ről — a job bemenete ennyiben elavult |
| E-8 | `staticcheck`/`govulncheck` a `golang:1.25` imageben nem telepíthető (Go ≥ 1.26-ot kérnek) | `staticcheck` a **builder image saját, pinelt** binárisával futott (2025.1.1, clean); `govulncheck` **UNVERIFIED** (CI futtatja) |

## 4. Lokális kapuk: mi futott és mi nem (AC-04b-7)

| CI-lépés | Lokálisan | Eredmény / ok |
|---|---|---|
| `make manifest-verify` | ✅ futott | `sha256sum -c MANIFEST.sha256`: minden tracked fájl OK — `evidence/36` |
| `make wasm.integrity-verify` | ✅ futott | `OK: artifact integrity verified` — `evidence/43` |
| `make wasm.test-fresh` (4 kötelező teszt) | ✅ ekvivalens futott | mind a 4 PASS scratch buildre **és** a committolt artifactra — `evidence/35`, `evidence/43` |
| `make wasm.test` / `make test` (go) | ✅ futott | 147 PASS / 0 FAIL / 4 SKIP, majd a 4 SKIP is PASS — `evidence/34`, `evidence/43` |
| `make wasm.build` | ✅ futott | TinyGo 0.39.0, pinelt image — `evidence/31`, `evidence/33` |
| `make wasm.repro-probe` | ✅ futott | **nem reprodukálható** (3 digest / 6 build) — `evidence/42` |
| `make docs.link-check` | ✅ futott | minden belső link feloldódik — `evidence/46` |
| `docgate` (külön CI job) | ✅ futott | 0 nem dokumentált deklaráció; **a CI-ben is zöld** (45 s) — `evidence/41` |
| `golang.fmt-check`, `golang.vet` | ✅ futott | mindkettő tiszta — `evidence/44` |
| `golang.lint` (`staticcheck`) | ✅ futott | 2025.1.1, clean — `evidence/45` |
| `golang.vuln` (`govulncheck`) | ❌ **UNVERIFIED** | a tool Go ≥ 1.26-ot kér, a modul `go 1.25.0` — `evidence/44` |
| `make check` (`infra.fmt/lint/typecheck/security`: ruff, yamllint, mypy) | ❌ **UNVERIFIED** | nincs `p_venv`, a hoszton nincs ruff/mypy — `evidence/47` |
| `make test` → `infra.test` (pytest) | ❌ **UNVERIFIED** | nincs pytest a hoszton, nincs `p_venv` — `evidence/47` |
| `make oci.extract.test` | ❌ **UNVERIFIED** | nem futtattam (a job nem érinti a `tools/oci-extract`-ot) |
| `golang.test.manual-real-oci` | ❌ **UNVERIFIED (szándékos)** | opt-in, valódi OCI hitelesítőt kér (`REAL_OCI_TEST=1`) — a job tiltja a valódi aláírást |
| Relay `pkg/hostsign` tesztek (`ociprofile_test.go`) | ❌ **UNVERIFIED** | olvastam, nem futtattam; a Relay mutation ratchet ebben a jobban nem módosul |

## 5. A munkacsomag saját deltája (B-2, B-4 — záró mérés)

```
$ git merge-base HEAD ae3c96237839c9fd06649c918a2194a79ebd8cb1
ae3c96237839c9fd06649c918a2194a79ebd8cb1

$ git rev-list --count ae3c962..HEAD
6

$ git diff --stat ae3c962 HEAD
 MANIFEST.sha256                                |  33 +--
 docs/design/specs/provider-abi.md              |   5 +-
 docs/design/specs/relay-sign-send-interface.md |  12 ++
 module/cicflow_guest.go                        |  44 ++--
 module/cicflow_host.go                         |  38 ++--
 module/cicflow_mock_test.go                    | 126 ++++++++++--
 module/execute_create_id_guest_test.go         |  15 +-
 module/host_codes_test.go                      |  21 ++
 module/host_mock_test.go                       | 246 +++++++++++++++++++++++
 module/module.wasm                             | Bin 1173093 -> 1287908 bytes
 module/module_loadtest_test.go                 |  36 ++--
 module/oci_sign.go                             |  70 -------
 module/provider.go                             | 227 ++++++++++++++-------
 module/provider_test.go                        |   6 +-
 module/relay_integration_test.go               |  15 +-
 module/send_contract_test.go                   | 267 +++++++++++++++++++++++++
 module/ss03_poll_create_denial_test.go         | 167 ++++++++++++++++
 project.yaml                                   |  14 +-
 18 files changed, 1077 insertions(+), 265 deletions(-)
```

Nyers napló: [`evidence/60-final-branch-state.log`](evidence/60-final-branch-state.log). A delta a
**merge-base és az ág csúcsa** között értelmezett, tehát teljes egészében a munkacsomag eredménye:
elavult bázisból származó eltérés nincs (`git rev-list --count ae3c962..origin/devel` = 0).

## 6. A három WASM-állítás (AC-04b-6) — külön mérve

**Környezet:** `cic-module-oracle-cloud-builder:latest` (`sha256:b5a3b64b…`), TinyGo **0.39.0**
(go1.25.0, LLVM 19.1.2). Parancs:
`tinygo build -o <out> -target wasip1 -scheduler=none .` a `module/`-ben.

### Állítás 1 — a committolt artifact integritása: **PASS**

```
artifact sha256:        88ff6b03befeb87630b7e34611ec34455b7f82cda83828757836301f96f408eb
project.yaml buildHash: 88ff6b03befeb87630b7e34611ec34455b7f82cda83828757836301f96f408eb
OK: artifact integrity verified
```

A repo saját kapujával (`tools/wasm_integrity_gate.sh`), a pinelt imageben —
[`evidence/43`](evidence/43-wasm-final-artifact.log). Az örökölt (devel) állapot szintén PASS volt
(`7080b342…`) — [`evidence/30`](evidence/30-wasm-claim1-and-builder.log).

### Állítás 2 — bitreprodukálhatóság: **NEM ÁLL** (mért, nem feltételezett)

Ugyanabból a forrásból, ugyanabban a pinelt imageben, hat egymás utáni build **három** különböző
digestet adott:

| Build | digest |
|---|---|
| d | `13a1f41280af4f83a62e01a690f1e4ca56d600014a2dad4ef7458e08fb7dc00a` |
| e | `88ff6b03befeb87630b7e34611ec34455b7f82cda83828757836301f96f408eb` |
| f | `13a1f412…` |
| g | `13a1f412…` |
| h | `6d1bffaa1e97c6b74cb1ec0e91447cbbd8d345c2bd87b862c96b0ae8dfe96bec` |
| i | `88ff6b03…` (**ez a committolt**) |

Gyakoriság: 3 × `13a1f412`, 2 × `88ff6b03`, 1 × `6d1bffaa`.

**A különbség forrása (mért):** két korábbi build (`a`, `b`) összehasonlítása szerint
**300 bájt tér el 1 287 908-ból**, három régióban, miközben a **string-táblák azonosak**
(`strings | sort -u` diff üres). Az eltérő régiókban a szintetikus `embed/file_<digest>`
szimbólumnevek **sorrendje** más — vagyis a `//go:embed`-elt séma-fájlok szimbólumai
nemdeterminisztikus sorrendben kerülnek a név-szekciókba. Ez a repo által ismert jelenség (issue #2),
ezért a `wasm.repro-probe` szándékosan nem kapu, csak jelzés.
Naplók: [`evidence/31`](evidence/31-wasm-rebuild-repro.log),
[`evidence/32`](evidence/32-wasm-repro-difference.log),
[`evidence/42`](evidence/42-wasm-claim3-recheck.log).

> **Figyelmeztetés az eredeti job-szöveghez:** a „két egymás utáni build bájtazonos?” kérdés önmagában
> **félrevezető mérés** ebben a környezetben: két build *véletlenül* egyezhet (nálam `a` és `c`
> egyezett, majd `d`..`i` három digestet adott). Legalább 5–6 build kell, hogy a jelenség látszódjon.

### Állítás 3 — a jelenlegi forrás megfelel-e a committolt wasm-nak: **PASS, viselkedés-alapon** (digest-alapon nem eldönthető)

Mivel a build nem reprodukálható, az „újrafordított digest = committolt digest” **nem** használható
bizonyítékként (egy nem egyező digest itt nem jelent forrás-eltérést). Amit mértem:

- a committolt bináris **ebben a futásban, ebből a forrásfából** készült a pinelt toolchainnel
  (`evidence/43`);
- a committolt artifact **viselkedése** megfelel a forrásnak: a négy `wasm.test-fresh` kötelező
  teszt (`TestHostLoadExecuteCreateCarriesOCID`, `…WithoutIDFails`, `…RefusesDuplicateID`,
  `TestHostLoadExecuteUpdateHasNoResourceID`) **és** `TestWasmArtifactImportsOnlyCICFlowSend`
  a `CIC_MODULE_WASM_PATH=module/module.wasm` beállítással, azaz **a committolt binárison** PASS
  (`evidence/43`).

**Elvi rés, kimondva:** a viselkedési egyezés nem bijekció — nem zárja ki, hogy egy *másik* forrás is
átmenne. A repo trust-modellje ezért integritásra épít (aláírt `buildHash`), nem reprodukcióra.

## 7. Központi (CI) acceptance

**Draft PR:** <https://github.com/CentralInfraCore/cic-module-oracle-cloud/pull/56>
(`--base devel`, head `e59143396d86babf4fbf401fcc2352ed55d546ee`)

```
$ gh pr view 56 --json mergeable,mergeStateStatus,headRefOid,isDraft
{"headRefOid":"e59143396d86babf4fbf401fcc2352ed55d546ee","isDraft":true,
 "mergeStateStatus":"CLEAN","mergeable":"MERGEABLE"}

$ gh pr checks 56
docgate         pass  50s
lint_and_test   pass  3m55s
lint_and_test   pass  3m50s

$ gh run view 46166669300 --json headSha,conclusion
{"conclusion":"success","headSha":"e59143396d86babf4fbf401fcc2352ed55d546ee"}
```

A `lint_and_test` job **a head SHA-ra** zöld, és azok a kapuk is lefutottak benne, amelyeket lokálisan
nem tudtam futtatni (nyers napló: [`evidence/70-ci-lint-and-test.log`](evidence/70-ci-lint-and-test.log)):

```
✓ Verify repository manifest
✓ Verify committed WASM artifact integrity (hash == buildHash, before any build)
✓ Fresh guest - build to a scratch path and require the real-WASM tests to pass
✓ Check internal documentation links
✓ Run code quality checks            ← make check (ruff, yamllint, mypy, security) — lokálisan UNVERIFIED volt
✓ Run Go quality gate (module/)      ← golang.quality, benne a govulncheck — lokálisan UNVERIFIED volt
✓ Test the OCI schema extractor (tools/oci-extract)
✓ Build WASM guest module (TinyGo)
✓ WASM reproducibility probe (non-fatal, issue #2)
✓ Host-load test against the relay cabinet ABI
✓ Run tests and generate coverage report
```

Két nem-blokkoló annotáció a futásban (mindkettő a repo meglévő állapota, nem ez a delta):
Node.js 20 deprecation az `actions/checkout@v4` / `upload-artifact@v4`-nél, és „No files were found
with the provided path: htmlcov/”.

## 8. Nyitott blokkolók és javaslatok (nem csendes döntések)

| # | Tétel | Miért nyitott | Javaslat |
|---|---|---|---|
| B-I | Az `ss03-poll-create-deviation.md` a `poll`-ra `POLICY_PATH`-ot, a `create`-re `POLICY_METHOD`-ot ír. **Mérve** a tényleges kód `POLICY_TARGET`, mert a `ValidateTarget` az operáció-nevet ellenőrzi először, és a `poll` / `execute` nem szerepel a megfigyelési policy `operations`-ában. | A dokumentum és a kód eltér; a modul-teszt most **mind a két** kódra fel van készítve | az eltérésleírás javítása: az elsőként jelentett kód `POLICY_TARGET`; a `POLICY_PATH`/`POLICY_METHOD` csak akkor, ha az operáció neve a policy-ban van. **Tulajdonosi döntés, nem a jobé.** |
| B-II | `tools/compiler.py` modul-szintű `yaml` (és `tools.schemalib` → `pyOpenSSL`) importja miatt a dokumentáltan stdlib-only `set-build-hash` nem futtatható `p_venv` nélkül (E-4) | a release-folyamat egy lépése nem elérhető a pinelt imageben | a `set-build-hash` ág lazy importtal való leválasztása, vagy `p_venv` az imagebe |
| B-III | A wasm nem bitreprodukálható: az `embed/file_<digest>` szimbólumsorrend nemdeterminisztikus (6 build / 3 digest) | a „forrás ↔ artifact” egyezés digest-alapon nem igazolható | ha szükséges: az `embed`-elt fájlok determinisztikus sorrendbe kényszerítése (explicit `//go:embed` lista) vagy a TinyGo issue követése (#2). A trust-modell ettől nem változik. |
| B-IV | A job bemenete a Relay `86ea1ab` bázist írja, de a `pkg/hostsign` csak az azt követő 4 commitban jött létre (E-7) | a „rögzített alap” elavult a host-oldali olvasáshoz | a WP-04b-hez tartozó Relay-bázis frissítése a jelentésben szereplő `2a645a9`-re (vagy az `integration/o1`-re) |
| B-V | `ref/schemas/`, `ref/examples/`, `ref/vectors/` nincs a `ref/`-ben (E-6) | a wire-séma szerinti validáció nem futtatható | a job-ref kiegészítése, vagy a követelmény törlése a job-specből |
| B-VI | A factory event-hook minden hívásnál hibázik (`CIC_WORKDIR` üres, E-1); commit-aláíró hook nincs (E-2) | a job nyomvonala nem naplózódik, a commitok aláírás nélküliek | a `run-job.sh` adja át a `CIC_WORKDIR`-t; az aláíró hook telepítése a job-klónokba |

## 9. Elfogadási kapu (AC)

| # | Kritérium | Eredmény | Bizonyíték |
|---|---|---|---|
| **AC-04b-1** | a bázis mechanikusan igazolt, a PR `MERGEABLE` | **PASS** | `merge-base HEAD ae3c962` = `ae3c962`; `rev-list --count ae3c962..origin/devel` = 0 (nincs elavult eltérés); `gh pr view 56` → `MERGEABLE` / `CLEAN` — `evidence/10`, `evidence/60`, 7. szakasz |
| **AC-04b-2** | a #54 saját delta-ja visszakövethetően átvezetve | **PASS** | 6 commit, egyenként pusholva; a #54 ága változatlan (nincs force push); a kézi port indoklása és a 4 szándékos eltérés az 1. szakaszban — `evidence/60` |
| **AC-04b-3** | a `devel` tesztjei és funkcionalitása megőrizve; a `claim-mapping.md` minden régi tulajdonságra ad helyet vagy indoklást | **PASS** | 141 → 151 teszt, **0 eltávolított**; 147 PASS / 0 FAIL / 4 SKIP, a 4 SKIP is PASS a committolt artifactra; 13 megőrzött + 6 áthelyezett + 4 megszűnt tulajdonság levezetve — `claim-mapping.md`, `evidence/34`, `evidence/35`, `evidence/43` |
| **AC-04b-4** | a guest egyetlen host importja a `cic-flow.send`; nincs aláírás/`Authorization`/dátum/kulcs a guest-kérésben, **a compiled artifacton ellenőrizve** | **PASS** | `TestWasmArtifactImportsOnlyCICFlowSend` a committolt `module.wasm`-on (wazero `ImportedFunctions()`); az elavult binárison `[actuate sign]`-nal elbukott; a negatív mezőállítások FAULT 3-mal mérve — `evidence/43`, `evidence/20` |
| **AC-04b-5** | `poll` és `create` célzott negatív teszttel elutasítva, **a megnevezett kóddal** | **PASS** | modul-oldal: `ss03_poll_create_denial_test.go` (4 altest, `POLICY_TARGET` + `POLICY_PATH` / `POLICY_METHOD`), FAULT 2-vel mérve; Relay-oldal: `hostsign.Policy.ValidateTarget` ellen futtatott mérés — `evidence/50`, `evidence/20`. **SS-03 nem módosult.** |
| **AC-04b-6** | a három WASM-állítás külön mérve (vagy nevesítve UNVERIFIED) | **PASS** (1: PASS · 2: **mért negatív eredmény** · 3: viselkedés-alapon PASS, digest-alapon nem eldönthető) | 6. szakasz; `evidence/30`, `31`, `32`, `33`, `42`, `43` |
| **AC-04b-7** | lokális kapuk futtatva és jelentve (kihagyottak névvel), CI zöld a head SHA-ra | **PASS** | 11 lokális kapu lefutott, 5 nevesítve UNVERIFIED (`govulncheck`, `make check`, `pytest`, `oci.extract.test`, manual-real-OCI) — ezek közül négy a CI-ben zöld; `docgate` + 2× `lint_and_test` **pass** a head SHA-n (`e591433`) — 4. és 7. szakasz, `evidence/70` |

**Összegzés:** mind a 7 elfogadási kritérium **PASS**. UNVERIFIED maradt (nevesítve): a Relay
`pkg/hostsign` tesztjeinek futtatása (csak olvasva), a séma-fájl szerinti wire-validáció (bemenet
hiányzik), az opt-in valódi OCI harness (a job tiltja), és lokálisan a `govulncheck` (a CI-ben zöld).
A HOLD-tételek (SS-03 módosítás, create/update/delete aktiválás, valódi Vault-aláírás, countersign,
release, merge) nem kerültek hozzá.
