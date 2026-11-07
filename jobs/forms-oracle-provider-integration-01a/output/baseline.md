# baseline.md — forms-oracle-provider-integration-01a

Reasoning mód: **audit**. Kód, séma, CI és `docs/**` egyetlen vizsgált repóban sem
módosult. Minden szám mellett ott van a parancs, a nevező és a rögzített commit.
A nem elvégzett vagy el nem végezhető mérés eredménye `NOT MEASURED`.

Mérés dátuma: **2026-11-07** (UTC+01:00).

---

## 0. Státusz-definíciók, ahogy itt használom

| Státusz | Mit jelent itt | Mivel bizonyítom |
|---|---|---|
| `implemented` | production kódban hívódik **és** teszt hajtja meg | hívó `fájl:sor` a production kódban (`_test.go` nélkül), plusz a meghajtó teszt |
| `scaffold` | kódban van, de production hívója nincs, vagy feltétel/build-tag mögött él | a 0 production találat, vagy a feltétel `fájl:sor` |
| `concept` | csak dokumentált | 0 production találat + a dokumentum helye |
| `NOT MEASURED` | nem mértem / nem mérhető | az ok és a szükséges feltétel |

---

## 1. Pin-tábla

A `cic-primitives` és a `cic-schema-registry` **nem mozgó ágon**, hanem a Forms
`corpus/pins.yaml`-jából kiolvasott commiton vizsgálva (`git checkout --detach`).

| Komponens | A pin forrása (fájl:sor) | A pin | Vizsgált commit | Jelenlegi HEAD (összehasonlítás) | `rev-list --count pin..HEAD` | Változott-e a releváns útvonalakon |
|---|---|---|---|---|---|---|
| `cic-module-oracle-cloud` | nincs pin — a job specje jelöli ki (`3e38886` vagy újabb) | `3e38886` (merge, #34) | `3e38886127b937dae00dd133ed0ce1ff4522106d` (`devel`) | ugyanaz | 0 | — |
| `cic-primitive-forms` | nincs pin — a job specje jelöli ki (≥ `2f02a75`) | `2f02a75` | `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (`main`) | ugyanaz | 0 | — |
| `cic-primitives` (grammar) | `corpus/pins.yaml:23-26` (`cic-primitives-73ae469-6a188078`, repo `cic-primitives`, ref `devel`) | `73ae4692f0680a316d367179ce057195a0031688` | `73ae4692…` (detached) | `origin/devel`; `origin/main` = `411ce807…` | `pin..origin/devel` = **16**; `pin..origin/main` = **5** | **Igen, de nem a normatív tartalomban:** `git diff --stat pin..origin/devel -- proposals/atom-grammar schemas/atomic schemas/aggregate LICENSE.md` → csak `P0-4-MIGRATION.md` (+12/-?) és `p0-4-contradiction-matrix.md` (2 sor). A pin `files:` listájában szereplő 12 fájl közül egy sem a `schemas/` vagy az `access_policy.py` |
| `cic-schema-registry` (`registry-network-space`) | `corpus/pins.yaml:49-53` | `6db77d4dca4ce3af3be66b3a7a85404fd0b63684` | `6db77d4…` (detached) | `origin/main` = `ac567aefb24970888aca3d7f350297ce2a78b687` | 7 | **Igen, kozmetikailag:** `git diff pin..origin/main -- general/network/network-space/network-space.yaml` → 1 sor, `modify: [OU=adapters, O=cic]` → `modify: ["OU=adapters,O=cic"]` (CertPattern egy-pattern lint, #162). A mezőkészlet változatlan |
| `cic-schema-registry` (`registry-network-interface`) | `corpus/pins.yaml:42-46` | ugyanaz a commit | ugyanaz | ugyanaz | 7 | ugyanaz az 1 soros CertPattern-változás |
| `CIC-Relay` (READ-ONLY) | nincs pin; a `$CIC_RELAY_PATH` élő checkoutja | — | `55a899fa708d29e84dc6386f9307fdc2bfe9e493`, ág: **`main`** | ugyanaz | 0 | — |
| OCI Go SDK | `oci-sdk.lock.yaml`, `mk/golang.mk:208` (`OCI_SDK_VERSION ?= v65.121.0`) | `v65.121.0` | **nem töltöttem le** (nincs rá szükség: a generált sémák commitolva vannak) | — | — | `NOT MEASURED` (SDK-letöltés hálózatot és a `make oci.generate` futását igényelné; a job tiltja az SDK-sweepet) |

**Pin-hash ellenőrzés (tényleges mérés).**
`sha256sum general/network/network-space/network-space.yaml` a `6db77d4` checkouton
→ `c9a4d14cf03e75ed6815519f9884f0621ce3ba6e70e49320b1639ac384c83b68` =
`corpus/pins.yaml:53` értéke. **Egyezik, bitre.**

**Lelet — eltérő szerződésverzió két komponens között.** A Forms a
`registry-network-space` pint a `6db77d4` commiten tartja. A
`cic-schema-registry` `origin/main`-je (`ac567ae`, 2026-10-21) **a pin után**
vezette be a `providers/oracle-cloud/network/network-space/network-space.correspondence.yaml`
fájlt és a `tools/registrylib/correspondence.py` applierét — azaz a VCN-leképezés
kódbeli helye **a pinelt állapotban még nem létezik**, a jelenlegi `main`-en
igen. Részletek: `contract-mapping.md` E-szakasz. A pin óta történt változás
**nem írja felül** a pinelt állapotról tett állításokat.

---

## 2. Mérési környezet (rögzítve)

| Tétel | Érték | Honnan |
|---|---|---|
| OS / kernel | Ubuntu 24.04.5 LTS, `Linux 7.0.0-38-generic x86_64` | `uname -srmo`, `/etc/os-release` |
| Go a **hoston** | **nincs** — `go: command not found`; `/usr/local/go`, `/usr/lib/go-*`, `~/sdk` sem létezik | `command -v go`, `find / -maxdepth 4 -name go -type f -perm -u+x` → 0 találat |
| Docker | `Docker version 29.9.2, build a82e528` | `docker --version` |
| Mérési konténer | `cic-module-oracle-cloud-builder:latest` (a modul saját builder image-e), Debian 13 (trixie) | `docker run --entrypoint sh … cat /etc/os-release` |
| Go a konténerben | `go version go1.25.0 linux/amd64` | konténeren belül |
| TinyGo | `tinygo version 0.39.0 linux/amd64 (using go version go1.25.0 and LLVM version 19.1.2)` | konténeren belül |
| staticcheck | `staticcheck 2025.1.1 (0.6.1)` | konténeren belül |
| govulncheck | `govulncheck@v1.1.4`, DB `https://vuln.go.dev` | konténeren belül |
| `deadcode` | **nincs előre telepítve**; `go install golang.org/x/tools/cmd/deadcode@latest` a konténerben sikerült (a toolchain `go1.26.10`-re váltott: `golang.org/x/tools@v0.52.0 requires go >= 1.26.0`) | mérési napló |
| `gremlins` | `gremlins version dev linux/amd64` (`go install github.com/go-gremlins/gremlins/cmd/gremlins@latest`) | mérési napló |
| `go-mutesting` | `github.com/zimmski/go-mutesting@latest` (= 2021-06-10 commit) telepíthető, **de futáskor pánikol** (lásd Q4) | mérési napló |
| `ineffassign` | **nincs** a builder image-ben, pedig a `mk/golang.mk` `golang.lint`-je nem is hívja (csak `staticcheck`-et) — a `forms-integration-direction.md:69` „ineffassign"-állítása nem igazolható a `mk/golang.mk`-ból | `mk/golang.mk:76-86` |
| Hálózat | Go modul-proxy **elérhető** a konténerből: `go get github.com/tetratelabs/wazero@v1.8.0` → `go: added …`, exit 0. `GOPROXY=https://proxy.golang.org,direct`. GitHub SSH elérhető (a négy klón sikerült) | mérési napló |
| `pytest` | a hoston `/home/sinkog/.local/bin/pytest` (Python 3.12.3); a rendszer-`python3`-ban nincs `pytest` modul | `python3 -m pytest` → `No module named pytest` |

**Nem szennyező mérés.** Minden Go/TinyGo/mutációs mérés a `git archive <commit> | tar -x`
módszerrel előállított **eldobható másolaton** futott (`/tmp/fo01a-scratch/module-3e38886`,
`/tmp/fo01a-scratch/forms-2f02a75`, `/tmp/fo01a-scratch/registry-6db77d4`,
`/tmp/fo01a-scratch/registry-ac567ae`), minden kimeneti fájl a repókon kívül
(`/tmp/fo01a-scratch/out/`). A `-mod=mod` és a `go install` csak ezekben a
másolatokban. A klónok végállapotát a `agent-output.md` 7. pontja idézi.

---

## 3. KB boot sequence — eredmény és a határai

`mcp__cic-graph__kb_status` (mérve 2026-11-07):

| Mező | Érték |
|---|---|
| `kb_loaded` | `true` (elérhető) |
| `build.built_at` / `updated_at` | **`2026-10-16T18:31:08Z`** |
| `stale` | **`false`** |
| `sources_not_current` | 0 |
| `sources_dirty_now` | 1 (`CentralInfraCore/CIC-basic-knowledge`) |
| **`sources_behind_upstream`** | **5** (`base/IaC` 81, `base/docs` 198, `base/mcp` 81, `base/schemas` 17, `base/workflows` 198) |
| `chunks` / `nodes` | 7830 / 7830 (build counts: 7829 chunk, 23 source) |
| `builder.commit` | `5a56ad8cac7548b9a6c0ee5227225d3ee3fdaeb6`, `dirty: true` |
| forrás-commit: **modul** | `cic-module-oracle-cloud` @ **`5d0a3278c6cc`** (`project_version: 0.1.0`) |
| forrás-commit: **Relay** | `CIC-Relay` @ **`55a899fa708d`** (`project_version: 0.7.3`) |

**A KB határai — újramérve, a spec állítása megerősítve.**

* A KB a modult `5d0a327`-nél tartja, a vizsgált `devel` HEAD `3e38886` — azaz a
  KB az `#33`/`#34` **előtti** állapot. A Relay commitja (`55a899f`) viszont
  **megegyezik** a vizsgált élő checkout commitjával.
* `search_nodes("cic-primitive-forms")` → **`{"result":[]}`**. A Forms nincs a KB-ban.
* A 23 forrás között `cic-schema-registry` **nem szerepel** (a listában
  `CIC-objs/cic-compute|cic-kubernetes|cic-network|cic-storage|cic-yang|cic-primitives`
  és `primitives-group` van).
* Ezért: **a KB nem bizonyíték a jelenlegi implementációra.** Minden KB-ból vett
  állítás legfeljebb `concept`/„nem igazolt", amíg kóddal nem támasztom alá; a
  `claim-evidence.md` ezeket `Forrás: KB c#### (file_path)` jelöléssel hordozza.

### 3.1 CIC boot kérdések (`search_nodes`) — az eredmény rögzítve

| Lekérdezés | Találat |
|---|---|
| `axioms` | 2: `n3558` `axioms.yaml` (yaml_file), `n4250` „📐 CICtor Axiómák (axioms.md)" (section) |
| `symbols` | 5: `n2138` `context/SYMBOLS.ALLOWPKGS`, `n3221` `generateSymbols` (go_func), 3 hozzá tartozó teszt |
| `contract` | 8 (mind `section`): `n722` CONTRACT, `n2013` iSDK API Contract (v1), `n2014` Contract & Schema, `n2506` Scope contract, `n2613` VM mint Host Contract, `n3771` Schema as Contract, `n3825`, `n4924` |
| `limits` | 5 (mind `section`): `n97` M44 Limits/budget, `n126`/`n2337` M4 LIMITS érvényesítés, `n724` LIMITS, `n7476` Timeouts and resource limits |
| `cic-primitive-forms` | **üres** |

`search_query("Oracle module provider ABI eight operations validate plan apply observe")`
a szemantikus keresésben **nem a modult adta vissza** (top-6: Relay
`core/nexus/iac/validator.yaml`, `conformance.yaml`, CIC-Schemas
`compiler-architecture-plan.md`, CIC-basic-knowledge `CICmeta.md`) — ez önmagában
is azt mutatja, hogy a modul ABI-ja nincs használható mélységben indexelve.

### 3.2 A `kb_focus` chunkok ellenőrzése fájlútvonal alapján

Mind a hat `get_chunk` lefutott, és a visszakapott `file_path` **egyezik** a spec
által megadottal. Egyik sem csúszott el.

| chunk | visszakapott `file_path` | Egyezik? | Megjegyzés |
|---|---|---|---|
| `c7529` | `./source/CentralInfraCore/cic-module-oracle-cloud/docs/design/architecture.md` | ✔ | section „Goal", 3–12. sor |
| `c7616` | `…/docs/design/specs/state-model.md` | ✔ | 36–55. sor, a Subnet state-példa és a `route_table ↔ route_table_id`, `public_ip_allowed == !prohibit_public_ip_on_vnic` megfelelés |
| `c7487` | `…/docs/contracts/en/wasm-abi.md` | ✔ | 1–6. sor |
| `c7668` | `…/module/contracts.yaml` | ✔ | **a `.yaml` kiterjesztés az indexelés műterméke**: a chunk tartalma a `module/contracts.go` `subnetSchemaJSON` go_var-ja (`//go:embed schemas/subnet.json`) |
| `c7675` | `…/module/correspondence.yaml` | ✔ | ugyanaz: `module/correspondence.go` `vcnCorrespondence` |
| `c7550` | `…/docs/design/primitives-alignment.md` | ✔ | 68–78. sor |

**Lelet (KB-elcsúszás, nem index-hiba).** A `c7668` leírása
`//go:embed schemas/subnet.json`-t mond, a `3e38886` tényleges kódja
`//go:embed schemas/core/subnet.json` (`module/contracts.go:20-21`). A séma-útvonal
`schemas/<service>/` alakra változott a `5d0a327` óta (`mk/golang.mk:203-207`
magyarázza a `core` service-könyvtárat). Ez a KB elavultsága, nem index-hiba.

---

## 4. A — Oracle modul leltár

### 4.1 A nyolc provider-művelet tényleges állapota

A `cic:provider` ABI op-készlete: `module/provider.go:46-49`
(`describe, validate, observe, plan, execute, poll, invoke, destroy`).

**A production hívó mind a nyolcra ugyanaz:** a guest dispatcher
`module/abi.go:35-54` (`switch op`). Az `abi.go` `//go:build wasip1` tag alatt
él (`module/abi.go:1`) — **ez nem scaffold-feltétel, hanem a szállított
artefaktum build-je**: a `module/module.wasm` a commitolt, aláírás-horgonyzott
termék (`project.yaml:41` `buildHash: 7080b342…`), és a `module_loadtest_test.go`
ezt a `.wasm`-ot tölti be wazero-val és hajtja át a valódi `Call` exporton.
Ezért a reachability-bizonyíték itt kettős: a dispatcher `fájl:sor` **és** a
wasm-szintű teszt.

| # | Op | Production hívó (fájl:sor) | Handler (fájl:sor) | Host-határ | Meghajtó teszt | Valós-OCI | Státusz |
|---|---|---|---|---|---|---|---|
| 1 | `describe` | `module/abi.go:37` | `module/provider.go:150` | none | `provider_test.go:25 TestDescribeManifest`; wasm: `module_loadtest_test.go:154 TestHostLoad`, `:232 TestHostLoadProviderOps`; `abi_manifest_test.go:83` | **verified** (`manual-verification.md:117`) | **implemented** |
| 2 | `validate` | `module/abi.go:39` | `module/provider.go:202` | none | `provider_test.go:91,103,115,125,424,445`; wasm: `module_loadtest_test.go:261 TestHostLoadValidateConformance` | **verified** (`:119`, `cic:network:subnet`) | **implemented** |
| 3 | `observe` | `module/abi.go:41` | `module/provider.go:827` | sign+send | `provider_test.go:357 TestObserve`, `:508 TestSignSendOpsRequireBinding/observe` | **verified** (`:118`, vcn + subnet) | **implemented** |
| 4 | `plan` | `module/abi.go:43` | `module/provider.go:410` | none | `provider_test.go:137,202,250,478` (7 alesettel: noop, noop-canonical, mutable-update, create-only-replace, action-managed, unmanaged, escalate-to-replace) | **verified** (`:120`, subnet) | **implemented** |
| 5 | `execute` | `module/abi.go:45` | `module/provider.go:972` | sign+send | `provider_test.go:284,321`; wasm+kripto: `module_loadtest_test.go:303 TestHostLoadExecute`, `relay_integration_test.go:38 TestRelayIntegrationExecuteSigned`, `:165 …RejectsBadSignature` | **verified** Create/Update/Delete (`:122-124`) | **implemented** |
| 6 | `poll` | `module/abi.go:47` | `module/provider.go:735` | sign+send | `provider_test.go:723,754` | **verified** (`:121`, Work Request, kind-agnosztikus) | **implemented** |
| 7 | `invoke` | `module/abi.go:49` | `module/provider.go:667` | sign+send | `provider_test.go:596,647,689` | **verified**, egy hamis-siker defekt megtalálva, javítva és **újramérve** valós OCI-n (`:126`) | **implemented** |
| 8 | `destroy` | `module/abi.go:51` | `module/provider.go:605` | sign+send | `provider_test.go:529,563` | **verified** szinkron (`DeleteVcn`/204) és aszinkron (`TerminateInstance`/204+WR) esetre (`:125`) | **implemented** |

**Negatív ABI-fedés is megvan** (nem csak a happy path):
`abi_negative_test.go:26` üres op, `:46`/`:68` üres payload, `:95` túlméretes
payload, `:125` memória-határsértés.

#### `deadcode ./...` — a kimenet, és amit nem tud megmondani

```
--- deadcode module/ (default build tags, host build)
deadcode: no main packages
--- deadcode module/ with -test (tests as roots)
(nincs kimenet)
--- deadcode module/ GOOS=wasip1 GOARCH=wasm
/app/module/cicflow_guest.go:30:12: undefined: allocate
/app/module/cicflow_guest.go:31:8: undefined: deallocate
/app/module/cicflow_guest.go:35:12: undefined: allocate
/app/module/cicflow_guest.go:36:8: undefined: deallocate
deadcode: packages contain errors   (exit 1)
--- deadcode tools/oci-extract
policy.go:143:6: unreachable func: ResourcePolicy
resolve.go:79:21: unreachable func: Resolution.Complete
schema.go:34:6: unreachable func: ResourceSchemas
```

Értelmezés, pontosan:

* **`module/` host-build:** `deadcode` `main` csomagot keres belépési pontnak. A
  `module` `package main`, de a `func main()` az `abi.go`-ban van, `wasip1` tag
  alatt — így a host-buildben nincs `main`, és a `deadcode` nem indul.
* **`module/` guest-build (`GOOS=wasip1`):** a `deadcode` a standard Go
  toolchain `go/packages`-ére épül, az `abi.go` viszont **cgo-t használ**
  (`import "C"`, `C.malloc`/`C.free`, `module/abi.go:8-9,19,24`), amit `wasip1`-re
  csak a TinyGo fordít. Ezért `allocate`/`deallocate` „undefined", és az elemzés
  elhasal. → **A `deadcode` a modul guest-buildjén `NOT MEASURED`, és a Q8
  bizonyítéknak a `deadcode` itt nem alkalmas eszköz.** Ami kellene hozzá: vagy
  egy TinyGo-aware reachability-eszköz, vagy az `allocate`/`deallocate`
  cgo-mentes újraírása (ez kódváltozás, nem ennek a jobnak a dolga).
* **`module/ -test`:** üres kimenet — a tesztekből mint gyökerekből nincs
  elérhetetlen függvény. Ez igaz, de gyenge jelzés: a tesztek gyökérnek
  számítása pont azt a kérdést mossa el, amit a Q8 fel akar tenni.
* **`tools/oci-extract`:** három exportált függvény elérhetetlen a `cmd/`
  belépési pontokból: `ResourcePolicy` (`policy.go:143`),
  `Resolution.Complete` (`resolve.go:79`), `ResourceSchemas` (`schema.go:34`).
  Ezek **scaffold** státuszúak (API-felület teszttel, production hívó nélkül).

### 4.2 A ténylegesen támogatott resource-készlet — újramérve

A várt készlet (VCN, Subnet, Instance) **megerősítve**, és **pontosan három**:
`module/contracts.go:17-28` három `//go:embed`-et tartalmaz, és
`embeddedSchemas` ez a három. A `supportedKinds()` (`provider.go:175`) ebből
származtat, nem kézi listából.

| Resource | Szerződés fájl | `$id` (config / state) | Operációk (name / method / role / path) | Kötelező mezők | Hívó fájl:sor | Tesztek | Valós-OCI igazolás |
|---|---|---|---|---|---|---|---|
| **VCN** | `module/schemas/core/vcn.json` | `cic:network:vcn-config` / `-state` | `CreateVcn POST create /vcns`; `GetVcn GET read /vcns/{vcnId}`; `UpdateVcn PUT update /vcns/{vcnId}`; `DeleteVcn DELETE delete /vcns/{vcnId}`; `ChangeVcnCompartment POST action …/changeCompartment`; `AddVcnCidr POST action …/addCidr` | `compartmentId` | `module/contracts.go:17-18` (embed) → `provider.go:176,222,424,675,788,835,980` | `provider_test.go` 137,478,529,563; `observed_test.go` 110 (9 fixture-eset); `module_loadtest_test.go` 232,261 | `observe`, `execute` Create/Update/Delete, `destroy` (szinkron) — `manual-verification.md:118,122-125` |
| **Subnet** | `module/schemas/core/subnet.json` | `cic:network:subnet-config` / `-state` | `CreateSubnet POST create /subnets`; `GetSubnet GET read /subnets/{subnetId}`; `UpdateSubnet PUT update /subnets/{subnetId}`; `DeleteSubnet DELETE delete /subnets/{subnetId}`; `ChangeSubnetCompartment POST action …` | `compartmentId`, `vcnId` | `module/contracts.go:20-21` | `provider_test.go:224 TestValidateSubnet`, `:250 TestPlanSubnet` | `observe`, `validate`, `plan`, `execute` Create/Delete — `manual-verification.md:118-120,122,124` |
| **Instance** | `module/schemas/core/instance.json` | `cic:compute:instance-config` / `-state` | `LaunchInstance POST create /instances`; `GetInstance GET read /instances/{instanceId}`; `UpdateInstance PUT update /instances/{instanceId}`; `TerminateInstance DELETE delete /instances/{instanceId}`; `ChangeInstanceCompartment POST action …` | `availabilityDomain`, `compartmentId` | `module/contracts.go:23-24` | `provider_test.go` (az Instance-fixture a `testdata/instance-fixture.json`); `manual_real_oci_test.go:829 TestManualDescribe` | `destroy` (aszinkron, `TerminateInstance`/204+WR), `invoke` (`ChangeInstanceCompartment`) — `manual-verification.md:125-127` |

Mezőszám és policy-megoszlás (a `jq`-val mérve a három `.json`-ból):

| Resource | config mezők | config policy-megoszlás | state mezők | state policy-megoszlás |
|---|---|---|---|---|
| VCN | 13 | `mutable` 5, `create-only` 4, `input-only` 3, `action-managed` 1 | 19 | `provider-computed` 9, `mutable` 5, `create-only` 4, `action-managed` 1 |
| Subnet | 16 | `mutable` 9, `create-only` 6, `action-managed` 1 | 23 | `mutable` 9, `provider-computed` 7, `create-only` 6, `action-managed` 1 |
| Instance | 35 | `mutable` 21, `create-only` 7, `input-only` 6, `action-managed` 1 | 36 | `mutable` 20, `provider-computed` 8, `create-only` 7, `action-managed` 1 |

Mérési parancs (nevezővel):
`jq -r '.config.properties | to_entries | map(.value."x-cic-policy") | group_by(.) | map("\(.[0]): \(length)") | .[]' module/schemas/core/<kind>.json`.

**`AddVcnCidr` lelet.** A VCN szerződésben szerepel `AddVcnCidr` mint
`role: action` (`POST /vcns/{vcnId}/actions/addCidr`), de **egyetlen config mező
sem hivatkozik rá** `x-cic-action`-ként (az egyetlen `action-managed` mező a
`compartmentId` → `ChangeVcnCompartmentDetails`). Azaz a `planProviderOps`
(`provider.go:362`) sosem fogja ezt az operációt tervbe tenni; csak
`Invoke`-kal, kézzel megnevezve érhető el. Ez megegyezik a registry
`network-space.yaml:54-58` megjegyzésével („az OCI-nak van rá valódi action-je,
csak a modul nem generálta le még — provider/modul gap"), és **részben
ellentmond** neki: az action **le van generálva**, csak nincs mezőhöz kötve.

### 4.3 A `normalizeObserved` — a legfontosabb egyedi lelet

`module/observed.go:68 normalizeObserved(kind string, o getOutcome) (normalizedObservation, bool)`

* **Production hívója: 0.** Mérés:
  `grep -rn "\bnormalizeObserved\b" --include="*.go" . | grep -v '_test\.go'` →
  két találat, mindkettő a saját definíciója/kommentje (`observed.go:66`, `:68`).
* A saját fejléce ezt ki is mondja (`observed.go:23-26`): *„implemented and
  unit-tested against the common VCN fixture (testdata/vcn-v1); **NOT wired into
  Observe** … Wiring it is a separate, deliberate ABI step."*
* Tesztekkel viszont **erősen** fedett: `observed_test.go` 10 teszt, köztük a
  9 fixture-eset (`TestNormalizeObservedMatchesTheFixture`), és négy
  szemantikai negatív kontroll (`…NeverClaimsMoreThanWasRead`,
  `APartialReadNeverFabricatesAValue`, `AnErrorAnswerIsNeverAuthoritativeAbsence`,
  `OnlyDeclaredFieldsAreEverAbsent`).

→ **Státusz: `scaffold`** (a spec definíciója szerint: kódban van, szándékosan
bekötetlen). Ami `implemented`: `effectiveConfig` (`provider.go:878`, hívó
`:860`) és `applyDerivations` (`correspondence.go:61`, hívó `provider.go:861`) —
ezeket az `Observe` valóban használja, de **coverage-osztályozás nélkül**.

Következmény, amit az `01b` nem kerülhet meg: **az `Observe` ABI-kimenete ma nem
hordoz `coverage`-et.** A „a hiányzó visszaolvasási képesség nem `null`" elvet a
`normalizeObserved` valósítja meg — és az nincs bekötve. Az `Observe` eredménye
(`provider.go:809 observation`) `state` + `effective_config` + `provenance`, a
coverage-mező nélkül.

### 4.4 A `primitives-alignment.md` két állításának újramérése

**(a) „nincs kódszintű kapcsolat a `cic-primitives`/`cic-yang` felé"
(`primitives-alignment.md:5-11`) — 2026-11-07-én, `3e38886`-on: IGAZ.**

Mérés a modul klónjában (`cd <modul>`):

| Minta | `grep -rn <minta> --include="*.go" . \| grep -v '_test\.go'` | `git grep` minden követett fájlban (típus szerint) |
|---|---|---|
| `cic-primitives` | **0 találat** | 12 × `.md` |
| `cic-yang` | **0 találat** | 9 × `.md` |
| `ManagedEntity` | **0 találat** | 7 × `.md` |
| `managed_entity` | **0 találat** | 1 × `.md` |
| `managed-entity` | **0 találat** | 1 × `.md` |
| `config-surface` | **4 találat**, mind angol próza / JSON-tag: `provider.go:811` (`json:"effective_config"` komment), `provider.go:824`, `provider.go:858`, `observed.go:58` | 5 × `.go`, 4 × `.md` |

A `config-surface` találatok nem a másik repó sémájára utalnak — pontosan az,
amit a `primitives-alignment.md:9-11` is mond. **Az állítás változatlanul áll.**

**(b) „a Relay forrásában nincs `cic-primitives` hivatkozás"
(`primitives-alignment.md:72-79`) — a Relay `55a899f`, `main` ágon.**

Ezt a spec szerint **olvasással** mértem, nem grepből következtetve: végigolvastam
a guest-határ teljes production útvonalát — `core/cabinet/cicwasm.go`
(`NewWasmManager`, `PreCompileModule`, `NewHostInstance`, `CicWasmHost.callGuest`),
`core/cabinet/service.go:215-263` (a WASM-végrehajtási ág),
`core/cabinet/stores.go:13-24` (`ModuleStore`/`SchemaStore`),
`cmd/relay/cic_flow_host_funcs.go` (229 sor, teljes),
`cmd/relay/cic_flow_manifest.go` (223 sor, teljes),
`cmd/relay/cic_flow_registry.go` (79 sor, teljes),
`cmd/relay/cic_flow_oci_signer.go` (47 sor, teljes),
`cmd/relay/main.go:640-686`, `cmd/relay/bootstrap.go:530-590`.

**Egyik olvasott fájlban sincs `cic-primitives`, `cic-yang`, `ManagedEntity`,
`ConfigSurface`, `StateSurface` vagy `OperationSurface` fogalom.** A Relay
séma-fogalma a `cabinet.Schema` (`core/cabinet/stores.go:20-24`: `Get`/`Put`/`Exists`
egy opak `*Schema`-ra), a modul-fogalma a `cabinet.ModuleDescriptor` — sem a
primitív-aggregátumokat, sem a `cic:…@vX.Y.Z` pinelt referenciákat nem ismeri.
**Az állítás a `55a899f`-en áll.**

---

## 5. B — Forms API leltár

### 5.1 Verzió, commit-pin, licenc, függőségkezelés

| Tétel | Mért érték | Bizonyíték |
|---|---|---|
| Commit (`main`) | `2f02a75592a4b0894a3b76891e9ba3741479a7c5`, 2026-11-05, „docs(p5): the admission contract, decisions D3 and D9 (design only) (#165)" | `git rev-parse HEAD`, `git log -1` |
| ≥ `2f02a75`? | **igen, pontosan az** — tartalmazza a `d43ffc2` Go-parser javítást (#163) és a P5 admission-szerződést (#165) | `git log` |
| Git tag | **nincs egyetlen tag sem** (`git tag` → üres kimenet) | `git tag` |
| Go modulútvonal | `github.com/CentralInfraCore/cic-primitive-forms/go`, `go 1.25` | `go/go.mod:1,3` |
| Go függőség | `gopkg.in/yaml.v3 v3.0.1` (direkt), `pgregory.net/rapid v1.3.0` (indirect, teszt-only), `gopkg.in/check.v1` (tranzitív) | `go/go.mod:5-7`; `go list -m all` |
| Rust verzió | `version = "0.0.0"`, `edition = "2021"` | `rust/Cargo.toml:3-4` |
| Rust függőségek | `saphyr-parser 0.0.6`, `sha2 0.10`; dev: `saphyr`, `serde_json`, `proptest`, `regex` | `rust/Cargo.toml:9-17` |
| **Licenc** | **Apache-2.0, egységesen** | lásd lent |

**Licenc — a `forms-integration-direction.md` állítása nem igazolható, és a
tényleges állapot más.**

A dokumentum (`forms-integration-direction.md:90`) azt írja: *„the Forms
repository is mixed (its own content CC BY-NC-SA 4.0, the adopted tooling
AGPL-3.0-or-later, two hooks MIT)"*. A `2f02a75`-ön mérve:

* `git ls-files | grep -iE 'licen|copying|notice|spdx'` → **egyetlen fájl: `LICENSE`**.
* `head -3 LICENSE` → `Apache License / Version 2.0, January 2004`.
* `README.md:81-83` → „## Licence — Apache-2.0. See [`LICENSE`](LICENSE)."
* `grep -rhno 'SPDX-License-Identifier:.*' . | sort | uniq -c` →
  **`69 Apache-2.0`**, és semmi más. Nulla AGPL, nulla MIT, nulla CC BY-NC-SA.
* `rust/Cargo.toml:5` → `license = "Apache-2.0"`.

→ **A Forms teljes egészében Apache-2.0** a vizsgált commiton. Ez az
`5.2 Licenc` pont alapfeltevését (a vegyes licenc) megdönti; a licenc-kérdés
következménye a 8. szakaszban. Ezt **nem javítottam** a modul dokumentumában
(a job tiltja); leletként rögzítem.

Egy pontosítás, hogy ne legyen félreérthető: a `LICENSE` fájl végén a
`Copyright [yyyy] [name of copyright owner]` placeholder az Apache-2.0 sablon
**appendixe** („APPENDIX: How to apply the Apache License"), nem kitöltetlen
jogosult — a repó licence maga a törzsszöveg.

**Hogyan hivatkozhatná a modul a Forms kódot — a lehetőségek és korlátaik.**
*(Csak mérés és döntés-előkészítés. `go.mod`/`go.sum`/`Cargo.toml` egyik repóban
sem módosult. Döntést nem hozok.)*

A kiindulás, ami ma van: **`module/go.mod:1` modulútvonala
`github.com/CentralInfraCore/wasm-module-template/module`** — a `base-repo`
sablonból örökölt név, ami **nem egyezik a repó valódi címével**
(`github.com/CentralInfraCore/cic-module-oracle-cloud`). A `tools/oci-extract`
go.mod-ja viszont már helyes
(`github.com/CentralInfraCore/cic-module-oracle-cloud/tools/oci-extract`). A
`module/go.mod` egyetlen `require`-je `github.com/tetratelabs/wazero v1.9.0` (és
az is csak a host-oldali teszthez kell).

| Lehetőség | Hogyan | Korlát / ami hozzá kell |
|---|---|---|
| **A. `require` + verzió (a direction §5.2 által preferált)** | `require github.com/CentralInfraCore/cic-primitive-forms/go vX.Y.Z` | **Ma nem kivitelezhető tagként:** a Forms repóban **nincs semmilyen git tag**, és a Go modul a repó `go/` alkönyvtárában van, tehát a tagnak `go/vX.Y.Z` alakúnak kellene lennie. Ami kell: a Forms tulajdonosa vágjon egy `go/vX.Y.Z` tagot |
| **B. `require` + pszeudo-verzió (commit-pin)** | `go get github.com/CentralInfraCore/cic-primitive-forms/go@2f02a75` → `v0.0.0-2026…-2f02a75592a4` | Működik tag nélkül is, és **pontosan commitra pinel** (amit a direction §5.2 kér). Korlát: a repó privát, tehát a CI-nek `GOPRIVATE`/`GONOSUMDB` + olvasási hitelesítés kell; a `go.sum` rögzíti a hasht |
| **C. `replace` + lokális útvonal** | `replace … => ../../cic-primitive-forms/go` | Fejlesztéshez megy, **CI-ben nem**: a Forms nincs a modul repójában, és a `replace` relatív útvonal a GitHub Actions checkoutjában nem létezik. A méréshez én is ezt használtam, de eldobható scratch könyvtárban |
| **D. Vendor** | `go mod vendor` vagy fájl-másolás | Az Apache-2.0 ezt megengedi (NOTICE/attribution mellett), de a modul repója CC BY-NC-SA 4.0 — a kettő egy fában külön licenc-döntés; továbbá a sablon `manifest-verify` gate minden követett fájlt hasheli, tehát a vendorolt fa a `MANIFEST.sha256`-ba kerül. Lemond a pin automatikus ellenőrzéséről |
| **E. Nem importálja (a Forms a hoston fut)** | a guest csak a már kiterjesztett, kanonikusan szerializált CIC-objektumot kapja | Ez **a direction 1.5 pontjában elfogadott irány** („The Forms engine does not move into the WASM guest"). Ekkor a modulnak **semmilyen Forms-importja nem kell**, csak a dekódolás; a TinyGo-mérés (lent) ennek a határnak a felmérése, nem a megvalósítása |

### 5.2 TinyGo/WASM-fordíthatóság — mért, nem feltételezett

A méréshez a **repókon kívüli** scratch könyvtárakat használtam
(`/tmp/fo01a-scratch/tinygo-probe`, `/tmp/fo01a-scratch/tinygo-min`,
`/tmp/fo01a-scratch/out`); a Forms `go/` fáját read-only mountként adtam be, a
próbaprogram go.mod-ja `replace`-szel mutatott rá. A célpont a `mk/wasm.mk:12,19`
szerinti `-target wasip1 -scheduler=none`.

| Próba | Mit importál | TinyGo build | Kimenet mérete |
|---|---|---|---|
| **Teljes felület** | `Parse`, `CanonicalBytes`, `CanonicalDigest` hívva; plusz függvényértékként referálva: `CompileSchema`, `Validate`, `Expand`, `Collapse`, `Normalize`, `NormalizeWithPolicy`, `ResolvePolicy`, `ParsePath`, `ResolvePath`, `SchemaIdentityOf`, `BindGrammar`, `PinnedGrammarVersion`, `Emit`, `Recognize`, `ApplyDefaults`, `MaterializeFlat`; típusok: `SchemaInput`, `CompiledSchema`, `PolicyResolution`, `PolicyNormalization`, `Context`, `Grammar`, `Shape`, `Provenance` | **sikeres**, exit 0 (`-target wasip1` és a legacy `-target wasi` is) | **1 468 919 B** (1,40 MiB) |
| **Minimális** | csak `Parse` + `CanonicalBytes` + `CanonicalDigest` | **sikeres**, exit 0 | **1 461 558 B** (1,39 MiB) |
| **Alapvonal** | `fmt.Println` egyetlen hívása, Forms nélkül | sikeres | **431 189 B** (0,41 MiB) |
| Referencia: a modul saját guestje | a commitolt `module/module.wasm` | — | **1 173 093 B** |

Olvasat: **a Forms Go csomagja TinyGo-val wasip1-re fordul**, és a kód-delta a
csupasz alapvonalhoz képest **≈ 1,03 MB** — gyakorlatilag azonos a minimális és
a teljes felületnél, mert a YAML-parser és a séma-fordító a `Parse`-on keresztül
már behúzódik (a TinyGo nem tudja kidobni). Azaz **nem lehet „csak egy kis
részét" importálni**: a `Parse` már a teljes költséget hozza.

**Függőségek.** `go list -deps github.com/CentralInfraCore/cic-primitive-forms/go`
nem-stdlib találatai: **`gopkg.in/yaml.v3`** és maga a csomag. Egyetlen külső
futásidejű függőség, a `yaml.v3`. (`pgregory.net/rapid` indirect, csak teszt.)
A próba `go mod tidy` utáni `go.mod`-ja: `require …/go v0.0.0` +
`require gopkg.in/yaml.v3 v3.0.1 // indirect`.

A modul saját guest-buildje 95 csomagot von be
(`GOOS=wasip1 GOARCH=wasm go list -deps ./... | wc -l` = 95).

**TinyGo reprodukálhatóság (külön mérés).** A `3e38886` guestjének újrafordítása
a builder konténerben:
`sha256(rebuild)=79c93797…` vs `sha256(commitolt)=7080b342…` — **nem
bitreprodukálható**, 1 176 324 B vs 1 173 093 B. Ez **pontosan az, amit a
`mk/wasm.mk:31-39` kimond** (issue #2: a TinyGo beégeti az absztolút build-utat);
a `wasm.repro-probe` ezért nem-fatális. A commitolt `buildHash`
(`project.yaml:41` = `7080b342…`) viszont **egyezik a commitolt bináris
hashével**, azaz a `wasm.integrity-verify` gate zöld.

### 5.3 A tényleges Forms Go API — a kódból idézve

A spec hét nevet kért. **Hat függvény, egy típus:** a `PolicyResolution`
**típus**, nem függvény; az őt előállító függvény a `ResolvePolicy`. Ez a név
a `forms-integration-direction.md:100` felsorolásában is függvényként szerepel
— leletként rögzítem.

A „hol hívódik a Forms **saját** production kódjában" oszlop mérése:
`grep -n "\b<Szimbólum>(" *.go | grep -v '_test\.go:'`, a saját deklarációs sort
és a kommenteket kizárva. Egy könyvtárnál a 0 production hívó normális (a
publikus API gyökér), de a Q8 pont pont ezt kéri számon, ezért külön jelölöm.

| Függvény / típus | Aláírás (fájl:sor) | Mit fogad / mit ad | Production hívó a Forms saját kódjában (fájl:sor) | Státusz |
|---|---|---|---|---|
| `Parse` | `go/parse.go:25` — `func Parse(text string) (*Node, error)` | egy YAML dokumentum szövege → `*Node` fa source-pozíciókkal; a hiba `*Error` | **9**: `access.go:102`, `emit.go:140`, `editscalar.go:27,66,182`, `patch.go:82`, `schema.go:141`, `sourcespan.go:191,207` | **implemented** |
| `ParseWith` | `go/parse.go:47` — `func ParseWith(text string, limits Limits) (*Node, error)` | ugyanaz + `Limits{MaxBytes, MaxDepth, MaxNodes}`; a default `1<<20 / 64 / 100_000` (`parse.go:20-22`) | 1: `parse.go:26` | **implemented** |
| `CompileSchema` | `go/schema.go:126` — `func CompileSchema(in SchemaInput) (*CompiledSchema, error)` | `SchemaInput{Bytes, SHA256, Grammar, Surface}` → `*CompiledSchema`. **Ellenőrzi a digestet** (`schema.go:131-133`), **a grammar-pint** (`:134-137`) és **elutasít minden `config_surface`-tól eltérő surface-t** (`:138-140`) | 2: `receipt.go:121`, `schemaidentity.go:103` | **implemented** |
| `Validate` | `go/validate.go:303` — `func Validate(node *Node, shape Shape, a []string) (*Validation, error)` | `node` (nil = hiányzó mező), `shape`, `a` = a kiterjesztett kulcskészlet A → `*Validation{Violations, DefaultCandidates}`. „Absent is not a value": `MISSING_MANDATORY` ≠ `NULL_NOT_ALLOWED` (`:292-294`) | 3: `defaults.go:52`, `editscalar.go:116`, `schema.go:392` | **implemented** |
| `Expand` | `go/expand.go:213` — `func Expand(doc *Node, shape Shape, a []string, g Grammar, ctx Context) (*Node, Provenance, error)` | kiterjesztett dokumentum + `Provenance` (pozíció → `Origin{AuthoredExpanded}`). „Expansion creates no authority (ADR 0010)": a `ctx` konzisztenciát ellenőriz, az eredményt nem változtatja (`:211-212`) | 1: `diff.go:178` | **implemented** |
| `Normalize` | `go/normalize.go:44` — `func Normalize(doc *Node, shape Shape, a []string, g Grammar, ctx Context) (*NormalizationResult, error)` | `*NormalizationResult{Object, Provenance, ValueOrigins}`. **Validál, mielőtt jár** (`:48` `refuseInvalid`); sosem szúr be defaultot kötelező mezőre, hiányzó kompozitba, vagy meglévő érték fölé (`:16-17`) | 2: `normalize.go:65` (`Renormalize`), `normalizewithpolicy.go:18` | **implemented** |
| `NormalizeWithPolicy` | `go/normalizewithpolicy.go:17` — `func NormalizeWithPolicy(doc *Node, c *CompiledSchema, a []string, g Grammar, ctx Context, unknown []string) (*PolicyNormalization, error)` | `Normalize` + `ResolvePolicy` **egy compiled schemával**, hogy a hívó ne párosíthassa a kettőt eltérő sémával (`:13-16`). Félig kész eredményt sosem ad | **0** — csak tesztből (`normalizewithpolicy_test.go`) | **scaffold** (API-gyökér, production hívó nélkül) |
| `ResolvePolicy` | `go/policyresolution.go:28` — `func ResolvePolicy(object *Node, root Shape, policy PolicySurface, surface string, a []string, g Grammar, unknown []string) (PolicyResolution, error)` | → `PolicyResolution`. „The result is data … the decision (a requestor, a certificate, an owner) is the Relay's" (`:9-10`) | 1: `normalizewithpolicy.go:22` | **implemented** |
| **`PolicyResolution` (típus)** | `go/policyresolution.go:20` — `type PolicyResolution map[string]PolicyEntry`; `PolicyEntry{Access, Modify EffectiveRule}` (`:15-17`) | kanonikus logikai útvonal → effektív hozzáférési/módosítási szabály | — | **implemented** (a `ResolvePolicy` adja) |

**A canonical path, origin és schema-binding típusai (a kódból):**

| Típus | Hely | Tartalom |
|---|---|---|
| `Node` | `go/node.go:47-55` | `Kind, Bool, Int int64, Str, Items []*Node, Entries []Entry, Pos *Pos` |
| `Pos` | `go/node.go:17-19` | `Line` (1-alapú), `Column` (1-alapú, Unicode kódpont), `Offset` (0-alapú, bájt) |
| `Kind` | `go/node.go:23-37` | `KindNull, KindBool, KindInt, KindStr, KindSeq, KindMap, KindUnsupported` |
| `Context` (origin/attestation) | `go/expand.go:45-49` | `Origin string, Attestation string, AttestedPositions []string`; a `check()` (`:51-82`) minden attesztált útvonalat **a sémához feloldva** ellenőriz, és `ORIGIN_ATTESTATION_MISMATCH`-et ad, ha a pozíció nem primitív |
| `Origin` / `Provenance` | `go/expand.go:95-101` | `Origin{AuthoredExpanded bool}`; `Provenance map[string]Origin`, a kanonikus logikai útvonal szerint (ADR 0006) |
| `ValueOrigin` | `go/defaults.go:31` | pozíció → `authored` vagy `default` |
| `SchemaInput` | `go/schema.go:66-75` | `Bytes []byte, SHA256 string, Grammar string, Surface string` |
| `CompiledSchema` | `go/schema.go:78-97` | `Kind, Namespace, Version, Digest, Grammar, Surface, DeclaredValidatedBy, Base, Policy PolicySurface, Root Shape, UsesItemChoice bool, UnevaluatedContracts []string` |
| path-kezelés | `go/pathtext.go:63 ParsePath`, `:283 FormatPath`, `:336 ResolvePath`; `go/listitem.go:148 PathOf` | kanonikus logikai útvonal szöveg ↔ szegmensek ↔ séma-feloldás |
| kanonikus bájtok | `go/canonical.go:38 CanonicalBytes`, `:47 CanonicalDigest` (`"sha256:" + SHA256Hex(b)`) | |
| séma-identitás | `go/schemaidentity.go:61 SchemaDigest`, `:64 SchemaName`, `:85 BindSchemaIdentity`, `:102 SchemaIdentityOf` | |

**Grammar-pin a kódban.** `go/schema.go:60-63`:
`var grammarProfiles = map[string]grammarProfile{ "cic-primitives-73ae469-6a188078": {ItemChoice: true, AccessGrammar: 1} }`
— **egyetlen bejegyzés**, pontosan a `corpus/pins.yaml:23` pin neve. Minden más
pinnév `GRAMMAR_PIN_UNKNOWN`. A komment ki is mondja: *„the temporary P0
compatibility profile of ADR 0002, not a release contract."*

### 5.4 Mit NEM támogat a Forms — explicit, a dokumentumból és a kódból

**`state_surface`: szándékosan kívül.** Nem csak dokumentált, hanem
**kódban kikényszerített**: `go/schema.go:138-140` —
`if in.Surface != "config_surface" { return nil, binding(SurfaceUnsupported) }`.
Dokumentum: `docs/P1-SUPPORTED-SUBSET.md:69` („Out of scope on purpose:
`state_surface`. A missing observation there is a coverage fact (ADR 0003 rule
8)"), `:123` (`SURFACE_UNSUPPORTED` minden nem-`config_surface`-ra, `ErrBinding`).
Bizonyított teszttel: `TestRealRegistrySchemas/state_surface_is_not_validated_as_authoring`
→ PASS (lásd 6.2).

→ **Nem írható le, hogy „a Forms validálja a state-et".** A cél-adatfolyam
(`forms-integration-direction.md:37`) „Forms state validation" lépése
**nem létezik** és nem is fog a `config_surface`-korláttal.

**`contract`: átmegy, nem értékelődik.** `docs/P1-SUPPORTED-SUBSET.md:352` —
„contracts are passed through and listed in `unevaluated_contracts`". Mérve: a
NetworkSpace fordításának eredménye `unevaluated_contracts: ["$.cidr_block"]`
(`testdata/p1/real-schemas.json`). **Azaz a `cidr_block`
`^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$` pattern-szerződését a Forms nem
érvényesíti.** Ez közvetlen következmény az `01b`-re.

**Nem támogatott YAML-konstrukciók** (`docs/P1-SUPPORTED-SUBSET.md:333-352`,
mind hiba, soha nem újraértelmezés):

| Konstrukció | Kód |
|---|---|
| anchor, alias, tag, merge key (`<<`), nem-skalár kulcs, egynél több dokumentum | `UNSUPPORTED_SYNTAX` |
| float-nak látszó plain skalár (`1.5`, `.5`, `5.`, `1e3`, `.inf`, `.nan`), hex/oktál (`0x1F`, `0o17`), vezető nullás egész, int64-en túli egész | `UNSUPPORTED_SYNTAX` |
| U+0085, U+2028, U+2029 bárhol a szövegben | `UNSUPPORTED_SYNTAX` (`parse.go:56-59`) |
| control karakterek, tab bárhol, BOM az első karakter után, direktíva (`%…`), dokumentumvég (`...`), nem-első `---` | `UNSUPPORTED_SYNTAX` |
| skalár ott, ahol mapping/lista van deklarálva; nem-record listaelem; lista recordon belül | `UNSUPPORTED_SYNTAX` (nincs szabály a szeletben) |
| **rossz típusú érték a presence-validációban** (string ott, ahol integer) | `UNSUPPORTED_SYNTAX` — **a registry-nek nincs rá kódja** (finding 4) |
| kiterjesztett Access node validált dokumentumban | `UNSUPPORTED_SYNTAX` (`validate.go:308-310`) |
| `choice` shape-típus, `number` és `bytes` skalártípus | `SCHEMA_SHAPE_UNSUPPORTED` séma-fordításkor |
| duplikált mapping-kulcs | `DUPLICATE_KEY` (a parse-fázis egyetlen szerződéses hibája, `parse.go:41-44`) |

**A P5 admission-szerződés: terv, nem kapu.** `docs/P5-ADMISSION-CONTRACT.md`
létezik (`#165`, 2026-11-05, „design only" a commit-üzenetben). A production
raw-YAML admission gate, a határozatlan konstrukciókra vonatkozó döntések és a
receipt API **nincsenek implementálva**. → **a rendszer nem végez admissiont.**

### 5.5 Mely Forms-függvények élnek production láncban — a teljes mérés

Mérési parancs (a Forms `go/` könyvtárában):
`grep -n "\b<Szimbólum>(" *.go | grep -v '_test\.go:'`, a saját deklaráció és a
kommentek kizárva. Nevező: a 48 exportált függvény közül a 32 lekérdezett.

**Production hívóval a Forms saját kódjában (`implemented`):**
`Parse` (9), `ParsePath` (6), `ResolvePath` (5), `CanonicalDigest` (5),
`CanonicalBytes` (4), `Validate` (3), `CompileSchema` (2), `ExpandPosition` (2),
`Normalize` (2), `ResolveRule` (2), `BindSchemaIdentity` (2), `SourceSpan` (2),
`ParseWith` (1), `Expand` (1), `ResolvePolicy` (1), `ApplyDefaults` (1),
`MaterializeFlat` (1), `EditScalar` (1).

**0 production hívó — csak tesztből elérhető (`scaffold`, a könyvtár publikus
API-gyökere):** `NormalizeWithPolicy`, `Collapse`, `Renormalize`, `Denormalize`,
`Emit`, `Recognize`, `Diff`, `Patch`, `BindGrammar`, `PinnedGrammarVersion`,
`ReadPolicySurface`, `SchemaIdentityOf`, `ReceiptFlatFixture`, `MapRelease`.

**Mit jelent és mit nem.** Egy könyvtárnál a publikus belépési pont 0 belső
hívója **nem** defekt — a hívó a könyvtár felhasználója. De a Q8 szabály
(„a szimbólum létezik + a teszt zöld ≠ implemented") pontosan arra kérdez rá,
hogy van-e **a modul** oldalán hívó. Ma nincs, egyikre sem: a modulnak nulla
Forms-importja van (4.4 (a) pont). Az `01b`-nek ezért minden általa használt
Forms-függvényhez **saját** hívási láncot kell felmutatnia.

---

## 6. D — Relay határ (READ-ONLY leltár)

Relay: `55a899fa708d29e84dc6386f9307fdc2bfe9e493`, ág `main`,
`git status --porcelain` = `?? .vscode/` (egy nem-követett könyvtár, nem tőlem),
`git diff --stat` = üres. **A Relayt nem módosítottam.** Minden alábbi állítás
**forrásolvasásból**, nem grepből.

### 6.1 A WASM host határ és a `Call` ABI

`core/cabinet/cicwasm.go:248-264` (`newCicWasmHost`): a Relay **pontosan három
exportot követel meg** a guesttől — `Call`, `allocate`, `deallocate`; bármelyik
hiánya `module '%s' does not export required ABI functions`.

`core/cabinet/cicwasm.go:300-384` (`callGuest`): a hívási konvenció
* három `writeStringToWasm` (op, auth-context, input), mindhárom a guest
  `allocate`-jével (`:388-406`), `defer deallocate` mindegyikre;
* `h.callFn.Call(ctx, opPtr, opLen, authPtr, authLen, dataPtr, dataLen)` (`:334`)
  — **hatparaméteres**, pontosan a modul `Call(opPtr, opLen, authPtr, authLen,
  dataPtr, dataLen uint64)` szignatúrája (`module/abi.go:28`);
* visszatérés: `packedResult`, `len = packed >> 32`, `ptr = uint32(packed)`
  (`:343-345`) — pontosan a modul `pack()`-je (`module/abi.go:65-72`);
* `packed == 0` → `("null","null")` (`:354-356`) — a modul `pack()` is 0-t ad üres
  bájtokra (`abi.go:66-68`);
* a válasz `{data, error}` JSON (`:363-366`) — pontosan a modul
  `guestResult` (`module/envelope.go:10-14`).
* timeout: `context.WithTimeout(ctx, h.timeout)` (`:301`), `DeadlineExceeded` →
  `TIMEOUT` hibajson (`:336-338`).

**→ Az ABI-mechanika (export-készlet, paraméterek, packed visszatérés,
{data,error} boríték, timeout) illeszkedik. `implemented` mindkét oldalon.**

### 6.2 **Az op-szókészlet NEM illeszkedik — ez a legfontosabb Relay-rés**

`core/cabinet/cicwasm.go:276-296`: a `CicWasmHost` **négy** metódust exportál, és
mindegyik **fix** op-stringet ad át:

```
Process → callGuest(ctx, "process", …)   :277
Get     → callGuest(ctx, "get",     …)   :283
Init    → callGuest(ctx, "init",    …)   :289
Notify  → callGuest(ctx, "notify",  …)   :295
```

`core/cabinet/service.go:18-24`: a `cicWasmHost` **interfész** is pontosan ez a
négy + `Close`.

`core/cabinet/service.go:229-243`: a production WASM-végrehajtási ág egy
`switch strings.ToLower(step.FunctionName)`, négy ággal (`init`, `process`,
`get`, `notify`), és a `default` ág:

```go
execErr = fmt.Errorf("WASM module %q does not support operation %q", step.ComponentID, step.FunctionName)
```

`grep -rn 'callGuest' --include="*.go" <Relay> | grep -v _test` → **csak a négy
fix hívás és a definíció.** Nincs production kód, amely tetszőleges op-stringet
adna át.

**Következmény.** A modul `Call`-ja a nyolc `cic:provider` op-stringre vár
(`module/abi.go:36-51`), és a `default` ágán
`marshalErr(CodeInput, "unknown op: "+op)`-ot ad (`abi.go:53`). A Relay ma vagy
`"process"`/`"get"`/`"init"`/`"notify"`-t küldene (→ a modul `unknown op`-ot ad),
vagy a `service.go:242` elutasítja a `describe`/`plan`/… nevű step-et, mielőtt a
guestig érne. **A nyolc provider-művelet a Relayen keresztül ma nem hajtható
végre.** → `relay-requirements.md` **R6**.

**Másodlagos lelet ugyanitt.** `service.go:228`:
`authContextJson := step.ComponentID` — a guestnek átadott „auth context" a
komponens azonosító **puszta stringje**, nem JSON auth-kontextus. A modul
minden handlerje `auth []byte`-ot kap és (ma) nem olvassa. Egy valódi
„validation is not authorization" határhoz ez a csatorna kell. → **R7**.

**Harmadik lelet.** `Process`, `Get`, `Init` production hívója **nincs** a
Relayben sem: a `service.go` `switch`-e mind a négyet elérhetővé teszi, de a
`grep`-pel mért egyetlen tényleges production hívás a
`service.go:240 host.Notify(...)` — a többi három ág csak a `switch`-ben van. A
`switch` maga production kód, tehát ez nem „dead code"; de azt jelenti, hogy a
guest-hívás **egyetlen** bizonyítottan járt útja a `notify`.

### 6.3 `cic-flow.sign` és `cic-flow.actuate`

`cmd/relay/cic_flow_host_funcs.go` — teljes olvasás (229 sor).

| Elem | Állapot | Bizonyíték |
|---|---|---|
| A `cic-flow` wazero host modul regisztrációja | **implemented** | `:74-91 registerCICFlowHostFunctions`, `b.Export("sign")` `:81`, `b.Export("actuate")` `:87`; ABI `(req_ptr, req_len, out_ptr, out_len) -> i32` `:68` |
| Production bekötés | **implemented** | `cmd/relay/main.go:664` `cicFlowReg := newCICFlowRegistry(buildOCIKeyResolver(), nil)`; `:667` `registerModuleCapability = cicFlowReg.registerVerified`; `:668-671` `wasmConfig.HostSetupFn = combineHostSetups(makeGitHostSetupFn(gitOps), makeCICFlowHostSetupFn(cicFlowReg))` |
| Per-modul fail-closed feloldás | **implemented** | `:97-105 perModule`: `reg.lookup(mod.Name())`; `!ok` → `"cic-flow: module has no verified capability"` |
| `sign` | **implemented**, de a signer **feltételes** | `:112-134`. `deps.sign == nil` → `"cic-flow: no signer configured"` (`:121-123`). A `deps.sign` csak akkor nem nil, ha `bindCICFlowDeps` feloldotta (`cic_flow_manifest.go:162-172`), ami **`resolve != nil`**-t kíván |
| `actuate` | **implemented** | `:141-198`. URL-séma-ellenőrzés `:153-156`; egress-ellenőrzés `:161-163`; a hívó **saját** `Authorization` fejléce verbatim továbbítva `:176-178` („caller's Authorization is carried verbatim") — ez az R2 magja |
| `buildOCIKeyResolver` | **scaffold — env-feltétel mögött** | `cmd/relay/cic_flow_oci_signer.go:31-36`: `if mount == "" \|\| keyName == "" { return nil }`, ahol `mount = os.Getenv("CIC_OCI_SIGN_MOUNT")`, `keyName = os.Getenv("CIC_OCI_SIGN_KEY")`. **Beállított env nélkül a `sign` inert.** A `main.go:658-660` komment ezt kimondja |

→ `cic-flow.sign`: **scaffold** (production úton bekötve, de két env változó
nélkül mindig `"no signer configured"`-öt ad).
`cic-flow.actuate`: **implemented** (a `doer` a `newCICFlowRegistry`
`nil`→`http.DefaultClient` defaultjával mindig jelen van,
`cic_flow_registry.go:37-40`).

### 6.4 Capability-manifest kikényszerítés és az egress policy

`cmd/relay/cic_flow_manifest.go` — teljes olvasás (223 sor).

| Elem | Állapot | Bizonyíték |
|---|---|---|
| A manifest beolvasása a modul `project.yaml`-jából | **implemented** | `:48-69` `moduleProject` + `parseModuleProject`; olvassa `metadata.buildHash`, `metadata.cicSign`, `abi.imports`, `capability_manifest` |
| `abi.imports ⊆ manifest` load-time ellenőrzés | **implemented** | `:192-201 checkImportsWithinManifest`: `sign` import + nincs `ops:[sign]` secret → hiba; `actuate` import + nincs egress → hiba. Hívó: `cic_flow_registry.go:68` |
| Per-modul egress policy | **implemented** | `:73-83 allows` (host + method + port + path, az első találat engedélyez); `:89-105 hostGlobMatch` (csak vezető `*.` suffix-glob; a puszta `*` és az infix wildcard **soha nem illeszkedik**); `:114-124 portAllowed` (üres lista → **csak 443**); `:126-136 pathAllowed` (prefix) |
| Sign-only handle kötés | **implemented** | `:144-157 grantsSign`/`signHandle` (az első `ops` közt `sign`-t hordozó handle); `:162-172 bindCICFlowDeps` |
| `buildHash` integritás | **scaffold — production hívója nincs** | `:205-214 verifyBuildHash`. `grep -rn 'verifyBuildHash' --include="*.go" <Relay>` → **3 találat `cic_flow_manifest_test.go`-ban (172, 175, 180) és 2 a definíciójában**. **Nulla production hívó.** |
| `cicSign` ellenőrzés | **concept** | `:51` `CICSign string \`yaml:"cicSign"\` // verified in R3b (pki_verify.go)`; `:16-18` „cryptographic verification of the declaration (cicSign against the CIC Root CA) is R3b … until then a module is untrusted and cic-flow stays inert" |
| Provenance-kapu a bekötés előtt | **implemented** | `cmd/relay/bootstrap.go:569-576`: `verifyCICFlowProvenance(cert, pkiAssets)` hibája esetén `"cic-flow capability not bound — provenance not verified"` (warn, a modul betöltődik capability nélkül); a `registerModuleCapability` hibája **elutasítja** a modult (`return fmt.Errorf(...)`, `:574`) |
| X.509 láncellenőrzés | **implemented, de trust-store-feltételes** | `bootstrap.go:545-562`: `cabinet.VerifyCertificateChain` EKU=CodeSigning + CRL. **De `:538-544`: ha `!pkiAssets.TrustStoreLoaded`, az ellenőrzés `"skipped"` (warn) — és akkor a `registerModuleCapability` blokk sem fut le** (az `else` ágon van) |

→ A `verifyBuildHash` **nem fut** production betöltéskor: a betöltött `.wasm` és
a `metadata.buildHash` egyezését a Relay nem ellenőrzi. → **R8**.

### 6.5 Trust-flow, séma- és modul-registry

* **Modul- és sématár:** `core/cabinet/stores.go:13-24` —
  `ModuleStore{Get,Put,Exists}` és `SchemaStore{Get,Put,Exists}`, mindkettő
  **in-memory PoC** implementációval (`:26` „--- In-memory implementations (PoC) ---").
  Nincs sem séma-verziókezelés, sem `schema_hash` ellenőrzés a boríték szintjén.
  → A modul `schemaPayload{schema_id, schema_version, schema_hash, encoding, data}`
  (`provider.go:57-63`) és `checkEnvelope` (`provider.go:300`) **a guestben**
  ellenőrzi a borítékot; a Relay oldalán ennek nincs megfelelője. → **R9**.
* **Trust-flow:** a `cic-flow` a `run_flow` FFI-úttól **szándékosan különálló,
  pure-Go** felület (`cic_flow_host_funcs.go:17-29`): „Sign-then-send opens
  nothing secret … so unlike `run_flow` this path needs no Rust airlock and is
  pure Go, like the `git` host module."
* **Audit/ProofTrace:** a modul `relay-requirements.md` R4 szerint a
  `HashChainedAuditSink`/`ChainedEntry` az FFI-úton létezik. A `cic-flow`
  útvonalon **a `cic_flow_host_funcs.go`-ban nincs audit-sink hívás** — a 229
  sorban sem `audit`, sem `ProofTrace`, sem `obs.` nem szerepel; a `TraceID`
  mezőt mindkét kérés fogadja (`:116`, `:148`), de a kód **nem használja fel
  semmire**. → **R10**.
* **Egress a guesten:** a modul `oci_sign.go` csak kanonikus stringet és
  `Authorization` fejlécet gyárt (`:36 ociCanonical`, `:66 ociAuthorization`); a
  hálózat a `callHostActuate`-en át megy (`provider.go:1069`). A guest `wasip1`
  oldalán ez a `//go:wasmimport cic-flow actuate` (`cicflow_guest.go:20-21`), a
  host-teszt oldalán injektálható függvény (`cicflow_host.go:13-30`). **A guest
  nem nyit közvetlen socketet** — ezt a `observed_test.go:264
  TestObservedGoDoesNotReachTheHost` külön ellenőrzi.

---

## 7. F — Minőségi szintek, Stage 0 mérés

Minden sor: a mért érték, a parancs, a nevező, a kizárások. A modul CI-je:
`.github/workflows/ci.yml` (89 sor), `mk/golang.mk` (245 sor), `mk/wasm.mk` (92 sor).

### 7.1 Amit a CI tényleg futtat (a `ci.yml`-ből kiolvasva)

| Lépés | `ci.yml` sor | Mire fordul |
|---|---|---|
| `make build` | 45 | docker image-ek |
| `make infra.deps` + `git diff --exit-code requirements.txt` | 51-53 | Python követelmény-drift |
| `make manifest-verify` | 56 | `MANIFEST.sha256` |
| `make docs.link-check` | 59 | `docs/**` belső linkek |
| `make check` | 62 | a sablon Python-oldali gate-je |
| `make golang.quality` | 65 | = `golang.fmt-check golang.lint golang.vet golang.vuln` (`mk/golang.mk:112`) — **csak `module/`** (`GO_MODULE_DIR ?= module`, `:39`) |
| `make oci.extract.test` | 68 | `cd tools/oci-extract && go vet ./... && go test ./...` (`mk/golang.mk:192-195`) — **nincs staticcheck, nincs govulncheck, nincs coverage** |
| `make wasm.build` | 71 | `tinygo build -o module.wasm -target wasip1 -scheduler=none` |
| `make wasm.integrity-verify` | 74 | `sha256(module.wasm) == project.yaml buildHash` |
| `make wasm.repro-probe` | 77 | **nem-fatális** (`-@`, `mk/wasm.mk:66`) |
| `make wasm.test` | 80 | `cd module && GOFLAGS=-mod=mod go test -v .` (`mk/wasm.mk:92`) — **nincs `-race`, nincs `-cover`** |
| `make test` | 83 | Python tesztek + htmlcov |

**Ami `make` target, de NEM CI-lépés:** `golang.test` (`-race`, `mk/golang.mk:115`),
`golang.coverage*` (`:156-172`), `golang.coverage-threshold` (`COVERAGE_MIN ?= 85`,
`:174-179`), `golang.test.manual-real-oci` (`:136`), `oci.generate` (`:209`),
`oci.audit` (`:237`).

### 7.2 A Q0–Q9 tábla — mért állapot

| # | Szint | Mért állapot a modulra (2026-11-07, `3e38886`) | Parancs / nevező / kizárás | Státusz |
|---|---|---|---|---|
| **Q0** | formátum, statikus analízis, sebezhetőség | `gofmt -s -l`: **0 fájl** `module/`-ban és `tools/oci-extract`-ban. `staticcheck ./...` `module/`: **0 találat**, exit 0. `go vet ./...`: **0**, exit 0. `govulncheck ./...` `module/`: **„No vulnerabilities found. Your code is affected by 0 vulnerabilities"**, mellette „4 vulnerabilities in packages you import and 56 in modules you require, but your code doesn't appear to call these" | `find . -name '*.go' \| xargs gofmt -s -l`; `GOFLAGS='-mod=mod -trimpath' staticcheck ./...` / `go vet ./...` / `govulncheck ./...`. Nevező `module/`: **1 csomag** (`go list ./...` → `github.com/CentralInfraCore/wasm-module-template/module`), 9 nem-teszt + 9 teszt `.go` fájl, host (`!wasip1`) build. Kizárás: a `wasip1`-only `abi.go` és `cicflow_guest.go` **nem elemződik** a host-buildben | **implemented** (CI-lépés: `ci.yml:65`) |
| Q0+ | ugyanaz `tools/oci-extract`-ra | `gofmt -s -l`: 0. `staticcheck ./...`: **0**, exit 0. `govulncheck ./...`: **1 stdlib sebezhetőség a saját kódból hívva** — „Found in: os@go1.25 / Fixed in: os@go1.25.8 / #1: cmd/oci-sweep/main.go:118:28: oci.main calls os.ReadDir" | ugyanazok a parancsok, `cd tools/oci-extract`. Nevező: **3 csomag** (root + `cmd/oci-extract` + `cmd/oci-sweep`) | **Lelet:** a CI itt **csak `go vet` + `go test`-et futtat** (`mk/golang.mk:195`), így ez a `govulncheck`-találat a CI-ben **nem jelenik meg**. Nem blokkoló (build-time eszköz, nem kerül a guestbe), de a Q0 „minden kódra" olvasata itt nem áll |
| **Q1** | unit tesztek (+ race) | `go test -v .` `module/`-ban: **PASS, 0 FAIL**, `ok … 2.814s`. Tesztek: **26 top-level `Test*`** a nem-manual fájlokban (+ 8 `TestManualRealOCI*` a `manual_real_oci` build-tag mögött, nem futott). `oci.extract.test`: `go vet ./...` exit 0; `go test ./...` → `ok …/tools/oci-extract 0.015s`, `cmd/oci-extract` és `cmd/oci-sweep` **„no test files"** | `cd module && GOFLAGS=-mod=mod go test -v .` (= `mk/wasm.mk:92`, a CI-vel azonos). Kizárás: `manual_real_oci` tag (nem futtatható, `REAL_OCI_TEST` nélkül `t.Skip`/`Fatal`) | **implemented, race nélkül** (CI: `ci.yml:80`) |
| Q1+ | race detektor | `go test -race -count=1 .`: **`ok … 25.017s`**, exit 0 — **a race detektor zölden fut, csak nincs CI-lépésben** | `cd module && GOFLAGS=-mod=mod go test -race -count=1 .`. A `golang.test` (`mk/golang.mk:115-125`) `RACE ?= 1`-gyel ezt futtatná, de a `ci.yml` nem hívja | **scaffold** (make target, nem CI-lépés) — és most **mérve, hogy átmenne** |
| **Q2** | sorlefedettség | **`module` csomag: 82,9%** (`coverage: 82.9% of statements`). **`tools/oci-extract` root: 88,7%**; `cmd/oci-extract` **0,0%**, `cmd/oci-sweep` **0,0%**; a három csomag együtt **56,3%** | `cd module && GOFLAGS=-mod=mod go test -covermode=atomic -coverprofile=/out/module-cover.out -cover .` és `cd tools/oci-extract && … ./...`; a profilok a repón kívül. Nevező: statements, `go tool cover -func` `total:` sora. Kizárás: `module/`-ban a `wasip1`-only fájlok (`abi.go`, `cicflow_guest.go`) **nincsenek a nevezőben** (nem fordulnak a host-buildben); `manual_real_oci_test.go` nem fut | **mért, nem gate-elt**. `golang.coverage-threshold` létezik `COVERAGE_MIN=85`-tel (`mk/golang.mk:174-179`), **de nem CI-lépés**. Megjegyzés: a mért 82,9% **a 85-ös küszöb alatt van** — ha ez CI-lépés lenne, ma piros |
| Q2 drift | a direction 82,7% / 88,7%-ot mért 2026-11-07-én | **82,9% vs 82,7% → +0,2 pp eltérés** a `module` csomagon; `tools/oci-extract` **88,7% = 88,7%, pontos egyezés** | a fenti parancsok, `3e38886`-on | **Eltérés jelezve.** Lehetséges ok: a direction nem adta meg a `-covermode`-ot; `atomic` és a default `set` mód statement-számolása eltérhet. Nem rekonstruálható az eredeti parancs megadása nélkül |
| Q2 leg-fedetlenebb | a `module` csomag `go tool cover -func` farka | `firstNonEmpty` (`provider.go:1143`) **0,0%**; `renderBody` (`:1092`) 77,8%; `actuateSigned` (`:1040`) 81,8%; `templatePath` (`:1128`) 88,9% | `go tool cover -func=/out/module-cover.out \| tail -5` | tény |
| **Q3** | ágazati lefedettség | **A modulban: nincs, és nem is mérhető ma.** **De újrahasznosítható Go eszköz LÉTEZIK a Formsban:** `tools/branchcov/` — a `cic-branch/1` definíciót közvetlenül megvalósító **AST-alapú enumerátor és instrumentáló**, külön `go/` és `rust/` résszel, Python adapterrel (`adapter.py`, `qualify.py`, `crosscheck_llvm.py`, `test_failclosed.py`). Az ADR 0009:93-100 kimondja, miért sajátot építettek: *„an AST-based enumerator and instrumenter that implements `cic-branch/1` directly. `gobco` and `gocove` do [not measure it]"*. CI-je: `.github/workflows/branchcov.yml` | `ls tools/branchcov`; `docs/adr/0009-branch-coverage-measurement-contract.md:22,70,84-105` | A modulra: **`NOT MEASURED`** (nincs eszköz bekötve). A „létezik-e újrahasznosítható eszköz" kérdésre: **IGEN**, a Forms `tools/branchcov`-ja, Apache-2.0 alatt. Átvétele a 8. szakasz licenc-pontja alá tartozik. **Ágazati lefedettséget a modulra nem állítok** |
| **Q4** | mutációs pontszám | lásd 7.3 — **részben mért**, és fontos: a szám **időtúllépés-érzékeny** | lásd 7.3 | lásd 7.3 |
| **Q5** | a kapu tud bukni (gate selftest, seeded defects) | **A modulban: nincs.** Egyetlen `make`/CI-lépés sem telepít szándékos hibát, hogy a gate pirosra váltását bizonyítsa. A Formsban megvan: `tools/seeded_defects.py`, `tools/test_seeded_select.py`, és a `quality-gate-selftest` + `seeded-defects` job (`docs/QUALITY-SHARDING.md:13`: „then the two seeded proofs that weakened tests turn it red"); a `tools/quality_gate.py:454-459` saját önteszt-vektorokat hordoz („exactly 90% line coverage is red", „90.01% is green") | `ls tools/` a modulban (nincs ilyen fájl); `grep -c seeded .github/workflows/ci.yml` = 0 | modul: **absent/concept**; Forms: implemented |
| **Q6** | közös vektorok, konstrukcióból fixált elvárások | **részben, és erősebben, mint a direction írja.** Létezik **közös, négy fejlesztési szál által osztott fixture**: `module/testdata/vcn-v1/` (9 eset), amelyet a modul **vendorolt** a `cic-factory` `fixtures/vcn-v1`-jéből (`SOURCE.md`: commit `e5978f50d2512c5ac7536b9d81ffb1f054b75525`, PR cic-factory#37), és a `TestVCNFixtureIsTheVendoredOne` (`observed_test.go:46`) a `MANIFEST.sha256`-ot ellenőrzi. A modul **a 3. szakaszt birtokolja** (`expected/observed.oci.json`), az elvárásokat **nem ő számolja**: a referencia-generátor a `cic-factory`-ban van (`README.md:5`, `generate.py` szándékosan nincs átmásolva) | `cat module/testdata/vcn-v1/{README.md,SOURCE.md}`; `go test -run TestNormalizeObservedMatchesTheFixture` → 9/9 PASS | **implemented a VCN read-irányra**; **absent** az input→request irányra (nincs vektorkészlet arra, hogy egy intentből milyen OCI kérés lesz) |
| **Q7** | claim-evidence és a bizonyíték-szabály | **részben.** `docs/design/manual-verification.md` (273 sor) kézzel vezeti a valós-OCI fedést, és a bizonyíték-fegyelmet komolyan veszi (három hibát talált és dokumentált: `percent_complete` int/float, `Invoke` hamis siker, 404 `provider_code` elvesztése). **Nincs** gépi `claim-evidence` rekord, nincs commit↔CI-head SHA kötés | `wc -l docs/design/manual-verification.md`; a dokumentum 18-20. sorának státusz-legendája | **partial** |
| **Q8** | reachability | **Ma nem követelmény a modulban.** És: a `deadcode` a guest-buildre **nem alkalmazható** (cgo, lásd 4.1). Amit a modul ehelyett tud: a `module_loadtest_test.go` a **valódi `module.wasm`-ot** tölti be wazero-val és hajtja át a `Call` exporton, plusz az `abi_manifest_test.go:83` ellenőrzi, hogy a `project.yaml` `abi.exports`-a egyezik a lefordított exportokkal | `deadcode` kimenet 4.1-ben; `module_loadtest_test.go:154,232,261,303` | **not required** ma; a `deadcode`-alapú bizonyítás **`NOT MEASURED`** a guestre (ok: cgo `abi.go`-ban) |
| **Q9** | determinizmus, nincs regresszió | **részben, mérve.** `MANIFEST.sha256` gate (`ci.yml:56`); WASM integritás (`ci.yml:74`, `sha256(module.wasm) == buildHash` → **egyezik**: `7080b342…`); reprodukálhatósági szonda **nem-fatális** (`mk/wasm.mk:63-77`) és általam mérve **NEM** reprodukál (`79c93797…` ≠ `7080b342…`) — ez a dokumentált, elfogadott állapot (issue #2). Ismételt futásra bitegyezést a **vektorokon** semmi nem ellenőriz | `tinygo build -o /out/module.wasm.probe …`; `sha256sum` | **partial** |

### 7.3 Q4 — mutációs megvalósíthatósági próba (az F legvége)

Három eszközt próbáltam, mindet az eldobható másolatban, a repón kívüli
kimenettel.

**(1) `github.com/zimmski/go-mutesting` (upstream) — NEM használható.**
`go install …@latest` sikerült (a legfrissebb commit 2021-06-10). Futtatva
`module/correspondence.go`-ra:

```
panic: runtime error: invalid memory address or nil pointer dereference [recovered, repanicked]
[signal SIGSEGV: segmentation violation code=0x1 addr=0x0 pc=0x5c4c92]
go/types.(*StdSizes).Sizeof(0x0, {0x82c400, 0xa19260})
	/usr/local/go/src/go/types/sizes.go:229
…
golang.org/x/tools/go/packages.(*loader).loadPackage(…)
	/root/go/pkg/mod/golang.org/x/tools@v0.0.0-20191018212557-ed542cd5b28a/…
```

Ok: a 2019-es vendorolt `golang.org/x/tools` nem tud Go 1.25 kódot típusozni.

**(2) A Forms által pinelt fork — ezt kell használni.** A Forms CI-je **nem** az
upstreamet használja:
`.github/workflows/p1-proof.yml:480,608,675,805` →
`spec: github.com/avito-tech/go-mutesting/cmd/go-mutesting@v0.0.0-20261002081621-9ce5f731e321`
(és `cargo-mutants@27.1.0` a Rust oldalon), a `.github/actions/cached-tool`-on
keresztül. A `tools/diff-mutation-local.sh:47` is az avito-fork-ot nevezi meg.
**Ezt a forkot nem próbáltam ki** (nem volt a telepített eszközök között, és
nem akartam további `go install`-t a mérési körbe húzni): a modulra
**`NOT MEASURED`**; ami kell hozzá: `go install github.com/avito-tech/go-mutesting/cmd/go-mutesting@v0.0.0-20261002081621-9ce5f731e321`.

**(3) `gremlins` — fut a modulon, és mért eredményt ad.**
`go install github.com/go-gremlins/gremlins/cmd/gremlins@latest` →
`gremlins version dev linux/amd64`.

| Futtatás | Parancs | Eredmény | Idő |
|---|---|---|---|
| dry-run | `cd module && gremlins unleash --dry-run .` | **Runnable: 159, Not covered: 58** (összesen **217 mutáns**), Mutator coverage **73,27%** | 97 ms (a konténer-körrel 11 s) |
| valódi, **default** timeout | `cd module && gremlins unleash .` | Killed **8**, Lived **0**, Not covered **58**, **Timed out 151**, Not viable 0 → „Test efficacy: 100.00%", Mutator coverage **12,12%** | 13,4 s |
| valódi, **10× timeout** | `cd module && gremlins unleash --timeout-coefficient 10 .` | Killed **159**, Lived **0**, Not covered **58**, **Timed out 0**, Not viable 0, Skipped 0 → **„Test efficacy: 100.00%", Mutator coverage 73,27%** | **57 s** |

**Mit állítok és mit nem.**

* **Megvalósítható:** igen. A `gremlins` telepíthető, lefut a modulon, 217
  mutánst ad, és 10-es timeout-koefficienssel **57 másodperc** alatt végez.
* **A szám, amit mértem:** a **159 lefuttatható mutáns közül 159 megölve, 0
  túlélő.** Nevező: 159. Parancs: `gremlins unleash --timeout-coefficient 10 .`
  a `module/` csomagon, `3e38886`-on, `gremlins version dev`.
* **Amit NEM állítok:** hogy a modul mutációs pontszáma 100%. A 217 mutánsból
  **58 „not covered"** — ezekre a `gremlins` nem is futtat tesztet, mert a sorok
  nincsenek lefedve; ezek **nem** számítanak bele az „efficacy"-be. A
  teljes mutáns-készletre vetített arány **159/217 = 73,27%**, és ez a
  „mutator coverage", nem pontszám. A direction Q4 szabálya szerint
  („Survived, timeout and equivalent mutants are reported in separate
  categories") ez a helyes bontás: **Killed 159 / Lived 0 / Not covered 58 /
  Timed out 0**.
* **A szám időtúllépés-érzékeny, ezért nem reprodukálható a koefficiens
  megadása nélkül:** default beállítással **151 mutáns time-outolt**, és akkor
  a kiírt „Test efficacy: 100.00%" mindössze 8 megölt mutánson állt. Ugyanaz a
  szöveg, 20-szor kevesebb tartalommal. Ez pontosan az a csapda, amit a
  direction Q4-pontja megnevez; **egy mutációs kaput nem lehet úgy bevezetni,
  hogy a timeout-beállítás nincs a kapu szerződésében.**
* **Nem futtattam** `gremlins`-t a `tools/oci-extract`-ra, és nem futtattam
  diff-scope-ban (nincs diff ebben a jobban). → `NOT MEASURED`.
* A `gremlins` **nem** a Forms eszköze: ha a cél a Forms Q4-szabályának átvétele
  (diff-kapu + éjszakai FULL, `docs/DELTA-DIFF-GATE.md`), akkor az avito-fork
  `go-mutesting` + `tools/mutation_shard_exec.sh` + `tools/quality_gate.py`
  hármas a referencia, nem a `gremlins`. A `gremlins` itt **megvalósíthatósági
  bizonyíték**, nem eszközválasztás. Döntést nem hozok.

### 7.4 Forms-oldali összehasonlító számok

| Tétel | Mért / olvasott |
|---|---|
| Forms gate-küszöb | **„strictly above 90%"**, sorlefedettség és mutációs pontszám, **mindkét nyelvre**; `tools/quality_gate.py:49` `THRESHOLD = 90  # percent, strictly exceeded`; `:7` „exactly 90.00% is red" |
| Forms diff-kapu szabály | `tools/quality_gate.py:358-359`: „more than 90% killed, all of them when there are fewer than DIFF_SMALL, and no mutants in the diff is green and says so" |
| Forms Q4 eszközök | `cargo-mutants@27.1.0` (Rust), `avito-tech/go-mutesting@v0.0.0-20261002081621-9ce5f731e321` (Go), `go-mutants` (pinned commit) a FAST módhoz |
| Forms Q3 eszköz | saját `tools/branchcov` (`cic-branch/1`, AST-alapú), `.github/workflows/branchcov.yml` |
| Forms Q5 | `tools/seeded_defects.py` + `quality-gate-selftest` és `seeded-defects` job |
| Forms Q7 | `docs/TEST-EVIDENCE.md`: **„implemented, not wired to any evidence source"** — a rekordformátum, a kanonikus JSON (RFC 8785 I-JSON részhalmaz), a verifier és a baseline-szabály megvan (`tools/test-evidence/`), a **termelés/publikálás/aláírás a B lépés, nincs meg** |
| Forms Q0–Q2 saját számai | **`NOT MEASURED`** általam. Ok: a Forms teljes Go tesztkészlete `CIC_PRIMITIVES_ROOT`-ot is kíván (`corpus_test.go:614`, `diff_corpus_test.go:176`, `diff_test.go:138,160,189,202,236,287,298,335,356,381,398,421` mind `t.Fatal`-lal bukik nélküle). A `coverprofile` ezért `total: 0.0%` — **ez nem a Forms lefedettsége**, hanem egy el nem indult futás. Mi kellene: `CIC_PRIMITIVES_ROOT=<cic-primitives @73ae469>` **és** `CIC_REGISTRY_ROOT=<registry @6db77d4>` egyidejű beállítása, plusz a `tools/grammar_identity.py verify` lefuttatása. A cél-szelethez tartozó egyetlen tesztet külön lefuttattam, és **PASS** (6.2 → `contract-mapping.md` C-szakasz) |

---

## 8. A licenckérdés

| Repó | Licenc | Bizonyíték |
|---|---|---|
| `cic-module-oracle-cloud` | **CC BY-NC-SA 4.0** | `LICENSE.md:3`; `project.yaml:6` `license: CC-BY-NC-SA-4.0`. © 2025 Sinkó Gábor Zoltán / OpenIntentSign / CentralInfraCore |
| `cic-primitive-forms` | **Apache-2.0, egységesen** | `LICENSE` (Apache 2.0 törzsszöveg), `README.md:81-83`, **69/69 SPDX-fejléc `Apache-2.0`**, `rust/Cargo.toml:5` |
| `cic-primitives` (pinelt, `73ae469`) | a pin maga hordozza: a `files:` lista **tartalmazza a `LICENSE.md`-t** (`corpus/pins.yaml:28`), „the licence of the pinned bytes is bound by the same manifest as the bytes" (`:2-4`) | `corpus/pins.yaml:1-4,28` |
| `cic-schema-registry` | CC BY-NC-SA 4.0 (a Forms `real_schema_test.go:3` így hivatkozik rá: „The file is CC BY-NC-SA 4.0 and is **not vendored**") | `real_schema_test.go:3` |

**Megállapítás.** A `forms-integration-direction.md:90` feltevése („the Forms
repository is mixed … the adopted tooling AGPL-3.0-or-later, two hooks MIT")
**a `2f02a75`-ön nem igazolható**: a repó egésze Apache-2.0. Ez a kérdést
**könnyebbé, nem nehezebbé** teszi — de nem jelentéktelenné, és nem én döntöm el.

Amit a mérés alapján a tulajdonos elé lehet tenni (**javaslat, nem döntés**):

1. **Apache-2.0 → CC BY-NC-SA 4.0 fába átvétel egyirányú kérdés.** Az
   Apache-2.0 megengedi a másolást és a módosítást, feltéve hogy a licenc és a
   NOTICE megmarad, és a változások jelezve vannak. A CC BY-NC-SA 4.0 viszont
   ShareAlike: a *származékos mű* egészére a CC-t kéri. Egy Apache-2.0 eszközt
   bemásolni egy CC BY-NC-SA fába tehát **nem licenckonfliktus**, de a bemásolt
   fájlok licencét **nem lehet CC-re váltani** — a kettő egy repóban él tovább,
   fájlonkénti SPDX-fejléccel, pontosan úgy, ahogy a `workdir` repója már
   megoldotta (`CIC/workdir/LICENSE.md`: „Ez a repo **vegyes**"). **Ennek a
   jogi megítélése a tulajdonosé.**
2. **Hivatkozás vagy pinelt letöltés a másolás helyett** — a direction által
   javasolt út, és a mérés megerősíti, hogy működik: a Forms CI-je maga is
   `.github/actions/cached-tool`-lal, **pinelt specifikációval** telepíti a
   mutációs eszközöket. A modul CI-je ugyanezt tehetné: a `branchcov`-ot és a
   `quality_gate.py`-t a Forms **pinelt commitjáról** tölti le a CI-ben, és nem
   commitolja be. Ez a `MANIFEST.sha256` gate-tel is kompatibilis (nem lesz új
   követett fájl).
3. **Amit külön kell eldönteni:** a `tools/branchcov` nem egy script, hanem egy
   Go+Rust+Python eszközfa saját `go.mod`/`Cargo.toml`-lal. Pinelt letöltése
   build-függőséget hoz a modul CI-jébe; a bemásolása a `MANIFEST.sha256`-ot és
   a licenc-fejléceket érinti.
4. A `cic-primitives` és a `cic-schema-registry` CC BY-NC-SA tartalmát a Forms
   **szándékosan nem vendorolja**, hanem env-változón át olvassa a pinelt
   checkoutból (`real_schema_test.go:3,67-71`). Ha az `01b` a NetworkSpace sémát
   akarja használni, **ugyanezt a mintát kövesse**, ne másolja be.

---

## 9. Mit NEM állítok ebben a dokumentumban

Hogy az integráció bármely része létezik a modul oldalán (a modulnak nulla
Forms-importja van, 4.4a). Hogy a Forms validálja a state-et (kódban tiltva,
5.4). Hogy az admission-szerződés kapu (5.4). Hogy a nyolc provider-művelet a
Relayen keresztül ma végrehajtható (6.2). Hogy a modul teljesíti a 90%-os sor-,
ágazati vagy mutációs szintet (a mért sorlefedettség 82,9% és 88,7%; az ágazati
nem mérhető; a mutáció 159/217 lefuttatható mutánson 100%-os efficacy, de
timeout-érzékeny és 58 mutáns fedetlen). Hogy a Forms eszközei bemásolhatók
ide (licenc-döntés, 8.). Bármit a valós OCI-ról, amit nem a
`manual-verification.md` rögzít.
