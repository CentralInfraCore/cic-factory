# O-1 integráció: első mechanikus összevezetés (2026-11-28)

## Relay (`integration/o1`, draft PR CIC_Relay #236, `500dd76`)

Az öt Relay-PR a rögzített head SHA-n, PR-onként egy összevezetési commit:

| Sorrend | PR | Konfliktus | Feloldás |
|---|---|---|---|
| 1 | #231 | nincs | — |
| 2 | #233 | nincs | — |
| 3 | #234 | `MANIFEST.sha256`, `context/SYMBOLS.md` (generált) | az egyik oldal, majd külön mechanikus újragenerálás |
| 4 | #232 | `cic_flow_host_funcs.go` (import-pár), `cic_flow_registry.go` (a #233 `flowGrant` térképe + a #232 `send` mezője) | mindkét oldal megtartva |
| 5 | #235 | `MANIFEST.sha256`, `SYMBOLS.md` (generált), `core/cabinet/service.go` (a #234 és #235 mezői) | mindkét blokk megtartva |

**Az összevezetett fa mért eredménye (helyi, docker golang:1.26.11):** `go build`, `go vet` (mindkét konfiguráció), gofmt, staticcheck, docgate (140 fájl, 0 hiányzó): tiszta; `go test ./...` minden csomag ok; `cic_test_seams` build ok; `-race` ok az érintett csomagokon. **Szerződéses eltérés nem derült ki a Relay-oldalon:** a két valódi ütközés a #232 és a #233 közös `cicFlowRegistry` típusán, illetve a #234 és #235 közös `cabinetService` típusán volt, és mindkettő additív volt. A GitHub CI az integrációs ágra: UNVERIFIED (a PR most nyílt).

## Modul (`integration/o1`, csak a #55 merge-elve)

A WP-01 (#55) tisztán összevezethető. **A WP-04 modul-PR (#54) nem.**

**Lelet (INT-blokkoló):** a #54 ága **nem a jelentett `devel` `ae3c962` alapra épült**, hanem az `5d0a327`-re (a merge-base), amely **63 commit-tal elmarad** a `devel`-től. A PR a GitHubon `CONFLICTING / DIRTY`. Az ágens jelentésében szereplő "base `devel` `ae3c962`, unchanged at push" állítás **téves volt** (a PR-ok korábban zöld CI-je egy elavult alapon futott).

A devel azóta érdemben megváltozott a #54 által módosított kódon: a `provider.go`-ban megjelent az M3 (a terv a registryhez kötve), az M4a (`checkPlanBinding`, `planFromRequest`), a `createdResourceID` 202/Work Request kezelése, a `pollTargetPath`, az `executeSteps` dátum-paraméterrel. Az ütközés öt fájlban van (`cicflow_guest.go` 2, `cicflow_host.go` 1, `provider.go` 4, `module_loadtest_test.go` 3 hunk, `MANIFEST.sha256`), és **nem mechanikus**: a WP-04 migrációt (`cic-flow.send`, strukturált kérés) a jelenlegi `devel` logikájára kell **szemantikusan újraportolni**, majd a `module.wasm`-ot a pinelt TinyGo-val újra kell fordítani és a `buildHash`-t frissíteni (a committolt wasm az elavult forrásból készült).

**Következmény a szerződésre:** a WP-04 jelentett blokkolója (a `poll` és `create` kérés nem fejezhető ki a fagyasztott SS-03 pontos útvonal-sablonnal) a jelenlegi `devel`-en **is** fennáll (a `pollTargetPath` Work Request útvonalat használ, a create-nek nincs `resource_id`-ja). Ez a **tulajdonosi döntésre váró szerződés-kiterjesztés** (SS-03 poll/create) előfeltétele a modul-oldali integrációnak.

**Nem javítottam csendben:** a #54 ágát nem írtam át, force push nem történt. A javasolt út: (1) tulajdonosi döntés az SS-03 poll/create kiterjesztésről, (2) a #54 szemantikus újraportolása a `devel`-re külön commitokban, (3) wasm újrafordítás és `buildHash`, pinelt TinyGo-val, (4) a #54 PR frissítése a `devel` bemerge-elésével (nem force push).

## Amit ez a Factory működéséről mutat

A párhuzamos, szerződésvezérelt fejlesztés a **Relay-oldalon** (új fájlok, additív típusbővítés) ütközésmentesen összeállt. A **modul-oldalon**, ahol egy meglévő, közben továbbfejlesztett kódot kellett átalakítani, az ágens egy elavult alapra dolgozott, és ezt a jelentése nem mutatta; ezt csak az integráció tárta fel. Tanulság: a PR jelentésnek tartalmaznia kell a `git merge-base` és a `gh pr view --json mergeable` eredményét.

## A modul-portolás méretének mérése (WP-04b javaslat)

A #54 saját delta-ja (a merge-base `5d0a327` és a csúcs között, az elavult bázis eltéréseit leszámítva): **12 fájl, 609 beszúrás, 218 törlés** (`cicflow_guest.go`, `cicflow_host.go`, `provider.go`, `module_loadtest_test.go`, `provider_test.go`, `relay_integration_test.go`, új: `host_mock_test.go`, `send_contract_test.go`; törölve: `oci_sign.go`; újrafordított `module.wasm`; `project.yaml`).

**Miért nem mechanikus:** a `devel` azóta a modul tesztjeit egy általánosított sign/actuate mock köré építette (`cicflow_mock_test.go`, 204 sor): **15 tesztfájl, kb. 110 hivatkozás** (`provider_test.go` 30, `execute_create_id_test.go` 11, `binding_resource_id_test.go` 10, `execute_create_id_guest_test.go` 9, `m4a_gate_test.go` 7, …), amelyek a `Signed[]`/`lastActuate()` jelenségeket állítják. A `cic-flow.send` migráció ezeket mind érinti: az aláírt karakterlánc és az `Authorization` többé nem a guest oldalán keletkezik, a mock `send`-kérést fogad.

**Javaslat:** külön, saját acceptance-szel rendelkező job (**WP-04b: a modul `cic-flow.send` migrációjának újraportolása a `devel` `ae3c962`-re**): (1) a #54 saját delta-ja kiemelve, (2) új `cicFlowMock` `send`-képességgel, a meglévő tesztek átírva az új kérés/válasz-szerződésre, a tesztek **szándékát** megőrizve (nem lazítva), (3) a `module.wasm` és a `buildHash` a pinelt TinyGo 0.39.0-val újrafordítva (a modul Dockerfile és a helyi `cic-module-oracle-cloud-builder` image), a digest-ellenőrzés és a forrásból reprodukálhatóság külön mérve, (4) a `poll`/`create` kérések kifejezhetősége az SS-03 kiterjesztésétől függ (**tulajdonosi döntés**), addig ezek a hívások `POLICY_PATH` elutasítást kapnak, amit a tesztnek ki kell mondania, nem elfedni.

**Állapot:** a modul `integration/o1` csak a #55-öt tartalmazza; a #54 **nincs** benne, az ág nem módosult, force push nem történt.
