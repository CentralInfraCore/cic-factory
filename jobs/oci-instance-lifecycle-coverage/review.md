# review — oci-instance-lifecycle-coverage

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-05
- Feature branch: `feature/oci-instance-lifecycle-coverage` (cic-factory + cic-module-oracle-cloud)
- Review-zott commit: `558c9571e1a2ca49ae8504b512530ab4f2ae08b0` (modul repo),
  `2eafe39` (cic-factory, csak `output/`)

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | GO | a job indítása előtt futott (K1–K11) |
| `tools/validate-output.sh` | GO | 1 WARN: O5 — 8/8 `file:line` feloldhatatlan. **Nem az output hibája**: a `validate-output.sh` `ROOTS` listája (`:127-130`) csak a workdir/Relay/Schemas/KB gyökereket ismeri, a `cic-module-oracle-cloud`-ot nem. Kézzel feloldottam őket (lásd lent) |
| CI (modul repo) | zöld | `gh run list --branch feature/oci-instance-lifecycle-coverage --json headSha,conclusion` → `success`, headSha `558c9571e1a2ca49ae8504b512530ab4f2ae08b0` — **egyezik** a review-zott committal |

## Amit ténylegesen ellenőriztem

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| CI zöld, headSha egyezik | `gh run list --branch ... --json headSha,conclusion,status` (saját lekérdezés, nem az agent kimenetének átvétele) | `{"conclusion":"success","headSha":"558c957...","status":"completed"}` — **igazolt** |
| `instance.json` szállítva van (nem scratch fixture) | `git show --stat HEAD` | `module/schemas/core/instance.json  \| 500 +++++` a commitban; `ls -la module/schemas/core/` → 17228 byte — **igazolt** |
| Reachability: az `instance` kontraktus production úton elérhető | `grep -n "instanceSchemaJSON\|cic:compute:instance" module/*.go \| grep -v _test.go`, majd a lánc kiolvasása | `contracts.go:24` (embed) → `contracts.go:28` (`embeddedSchemas`) → `contracts.go:89` `resourceContracts()` (a `:95` `for _, raw := range embeddedSchemas`) → `provider.go:158` `ResourceKinds: supportedKinds()` → `provider.go:175` `supportedKinds()`. Nincs teszt-only referencia — **igazolt** |
| `TestManualRealOCIDestroy` a **valódi** `Destroy()`-t hívja, nem `Execute()`-ot | `grep -n "= Destroy(nil" module/manual_real_oci_test.go` | `:591  resultJSON, err := Destroy(nil, destroyReqJSON)` — **igazolt** (ez a job lényegi állítása) |
| `TestManualRealOCIInvoke` a valódi `Invoke()`-ot hívja | `grep -n "= Invoke(nil" module/manual_real_oci_test.go` | `:695  resultJSON, err := Invoke(nil, invokeReqJSON)` — **igazolt** |
| Mindkét új teszt env-guard mögött van | `sed`/`grep` a teszt törzsére | `:553` és `:651` — `if os.Getenv("REAL_OCI_TEST") == "" { t.Skip(...) }`, a `manual_real_oci` build tag mellett — **igazolt** |
| `egress_hosts` nem változik resource kind szerint | `provider.go:155-180` elolvasva | `EgressHosts: []string{"*.oraclecloud.com"}` — egyetlen statikus wildcard, nincs kind-alapú elágazás — **igazolt** (az agent állítása helyes) |
| A branch alapja és merge célja | `git log --oneline origin/devel..HEAD` | egyetlen commit (`558c957`) a `devel` fölött → merge cél: `devel`, nem `main` — **igazolt** |
| A commit nem szennyezett (nincs `git add -A`, nincs companion-yaml) | `git show --stat HEAD` | 10 fájl, mind szándékos (`MANIFEST.sha256`, 2 doc, `mk/golang.mk`, `contracts.go`, teszt, `module.wasm`, `instance.json`, `oci-sdk.lock.yaml`, `project.yaml`) — **igazolt** |
| `make oci.generate` byte-azonosan hagyja `vcn.json`/`subnet.json`-t | nem futtattam újra | **nem igazolt** — az agent futtatta és `git diff`-fel mutatta; a commit fájllistája konzisztens vele (egyik sem szerepel a diffben), ez közvetett megerősítés |
| A lock-hash kapu és az `oci-extract -diff` kapu bukik szándékos törésen (mindkét irány) | nem futtattam újra | **nem igazolt** — az agent állítása, kimenetekkel a claim-evidence táblában |
| `describe()` `resource_kinds` tartalmazza `cic:compute:instance`-t | nem futtattam a `TestManualDescribe`-ot | **nem igazolt futtatással** — de a fenti reachability-lánc kódszinten szükségszerűvé teszi (az `embeddedSchemas` tömbből származik) |
| `make check` / `golang.quality` / `wasm.*` / `manifest-verify` / `docs.link-check` zöld | nem futtattam újra | **nem igazolt közvetlenül** — a CI zöld a pontos committon, ami ezek nagy részét lefedi |
| `Destroy()`/`Invoke()` valós OCI ellen fut és sikeres | — | **NEM igazolt, és nem is volt a job hatóköre.** Ez az orchestrátor nyitott lépése — `output/orchestrator-verification.md` A/B/C recept |

## Amit NEM ellenőriztem

- Nem futtattam le a modul repo egyetlen make targetjét sem lokálisan (a CI-re és az
  agent claim-evidence táblájára támaszkodtam ott, ahol fent „nem igazolt" áll).
- Nem olvastam át az `instance.json` mind az 500 sorát — csak a méretét, a commitban
  való meglétét és az `invoke-scope.md`-ben idézett `action-managed` mező-kiíratást.
- Nem ellenőriztem a `docs/design/manual-verification.md` és `roadmap.md` szövegének
  minden módosított sorát — a `poll` sor `verified`-re állítását a `4e577c8` commit
  üzenete alapján fogadtam el, nem független futtatásból.
- Nem ellenőriztem, hogy a `mk/golang.mk` `oci.generate` `NET_CLIENT`/`COMPUTE_CLIENT`
  szétválasztása egy tiszta környezetben (docker cache nélkül) is lefut.
- Nem ellenőriztem a `module.wasm` binárist a `project.yaml` `buildHash`-hez —
  az agent állítja (`wasm.integrity-verify`, `0f45626a...`), a CI is futtatja.

## Megjegyzés a job futásáról (nem az output hibája)

A `run-job.sh` wrapper SIGPIPE-ra meghalt (a futás `| head`-en át indult), így a
`usage:` blokk (költség, tokenek) elveszett — az agent árván futott tovább és
befejezte a munkát. A `meta.yaml` `usage:` blokkja ezt dokumentálja; a `turns: 306`
a session logból számolt érték. A wrapper javítása (`trap '' PIPE` + `finalize`
EXIT trap) a live workdirben **uncommitted** — külön commitba kívánkozik, nem
ebbe a jobba.

## Utóélet — az orchestrátori verifikáció (2026-08-05, a merge után)

A review „nem igazolt" sorai közül az egyik lezárva. Az `output/orchestrator-verification.md`
**A receptje** lefuttatva a POC trial tenancy ellen (`eu-frankfurt-1`, commercial realm):

| Lépés | Mérés |
|---|---|
| `Execute(CreateVcn)` eldobható VCN-re | `http_status: 200` |
| **`Destroy()`** ugyanarra | `Destroy resolved operation label: DeleteVcn`, `http_status: 204`, `succeeded` |
| `oci network vcn get` utána | `404 NotAuthorizedOrNotFound` |
| `oci network vcn list` | üres |

A **B recept** is lefuttatva, élő Always Free `VM.Standard.E2.1.Micro` instance-en:

| Lépés | Mérés |
|---|---|
| `Destroy()` | `Destroy resolved operation label: **TerminateInstance**`, `204`, `status: **accepted**`, + `work_request_id` |
| `Poll()` a Destroy saját Work Requestjén | `IN_PROGRESS 0% terminal:false` → `SUCCEEDED 100% terminal:true` |
| `oci compute instance get` | `TERMINATED` |

A claim-evidence tábla „`TestManualRealOCIDestroy` valós OCI ellen fut és sikeres —
**NEM igazolt** (közepes kockázat)" sora ezzel **igazolt**, mindkét úton: szinkron
(`DeleteVcn`/`succeeded`) és aszinkron (`TerminateInstance`/`accepted`).

Amit a B a VCN-futáson felül rögzít: a `resolveOp` **szerep szerint** választ a
beágyazott kontraktusból, nem névalak alapján (`TerminateInstance`, nem
`DeleteInstance`) — ez az `oci-lifecycle-role-bridge` hibaosztálya, most valós
OCI-n igazolva. És a lánc végig zárt: `Destroy` → `work_request_id` → `Poll` →
terminális, nem CLI-vel gyártott Work Requesten.

Dokumentálva: `cic-module-oracle-cloud` PR #20 (`verify/destroy-real-oci`),
két commit — `24e15ea` (A) és `883c10a` (B). Tenancy takarítva, üres.

**Nyitva marad:**
- **C recept** (`Invoke` / `ChangeInstanceCompartment`) — ehhez második compartment kell.
- **Hibás út**: egy OCI által *elutasított* törlés (függő erőforrás, jogosultsághiány)
  nem futott — a `Destroy()` hibaleképezése fixture-szinten marad. Mindkét futás
  happy-path volt.

Futtatási buktató, amit a job outputja nem tudhatott: a recept host Go toolchaint
feltételez, de a Go a builder konténerben van, és a `docker-compose.yml` nem mountolja
a `$HOME/.oci`-t. A `mk/golang.mk` a repo alatti gitignore-olt kulcs-path-ot javasolja —
de a `.gitignore`-ban nincs `*.pem` szabály. Egyszeri `docker compose run --rm -v
$OCI_KEY_PATH:/run/oci-key.pem:ro builder` volt a megoldás.

## Döntés

**MERGE** — a job három szállítandója (Instance séma, `Destroy()` harness,
`Invoke()` harness + scoping döntés) igazoltan elkészült, a legfontosabb állítás
(a valódi `Destroy()` handler hívása, nem `Execute()`) forráskódszinten
ellenőrizve, a CI zöld a pontos committon. A két „nem igazolt" sor — `Destroy`/
`Invoke` valós OCI ellen — a job explicit hatókörén kívül esett, és
`output/orchestrator-verification.md`-ben futtatható recepttel át van adva az
orchestrátornak. Ez nyitott tétel marad, nem a merge blokkolója.
