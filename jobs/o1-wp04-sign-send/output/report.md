# o1-wp04-sign-send: jelentés

**Státusz:** a munka kész; a két draft PR nyitva, merge nem történt. Aláírás, countersign, release, publikáció nem történt (a Vault-aláírás helyén teszt-RSA-kulcs és számláló mock van).

| Repo | Ág | PR (draft) | Commitok |
|---|---|---|---|
| CIC_Relay | `feature/o1-wp04-sign-send` (alap: `main` `86ea1ab`) | https://github.com/CentralInfraCore/CIC_Relay/pull/232 | `292125a`, `84d842c` |
| cic-module-oracle-cloud | `feature/o1-wp04-sign-send` (alap: `devel` `ae3c962`) | https://github.com/CentralInfraCore/cic-module-oracle-cloud/pull/54 | `4f6db1f` |

**Alap-eltérés:** a push előtt `origin/main` = `86ea1ab…`, `origin/devel` = `ae3c962…`: nincs eltérés a rögzített alaptól.

**Commit-aláírás:** a scratch klónokban nincs a gyári commit-msg hook és nincs Vault-aláírás, a commit-identitás placeholder (`Your Name`). Ezt nem kerültem meg; a commitok aláíratlanok. A commit-üzenetekben nincs `Co-Authored-By` vagy AI-utalás.

## Környezet és parancsok

- Go: docker `golang:1.26.11` (Relay, a `go.mod` `toolchain go1.26.11`), `golang:1.25` (modul, `go 1.25.0`). Parancs: `docker run --rm -v <repo>:/src -v gocache:/root/go -w /src golang:<ver> sh -c '...'` (`GOFLAGS=-buildvcs=false` ahol `go list`/`go build` kell).
- WASM: `cic-module-oracle-cloud-builder:latest` (TinyGo 0.39.0): `tinygo build -o module.wasm -target wasip1 -scheduler=none .`
- Boot: `kb_status` build `2026-11-21T21:26:25Z`, `stale: false` (sources_dirty_now 1, behind_upstream 6 más repókon). `search_nodes`: `axioms` → c5384 (`axioms.yaml`), c6076; `symbols` → c2786, c4864; `contract` → c1158 (CONTRACT), c1151; `limits` → c110, c139. A KB tájékozódás volt; minden kódállítás forrásolvasásból és futtatásból származik, KB-ból vett állítás nincs a táblában.

## Mit építettem (rövid)

**Relay.** `cic-flow.send` host-import (egységes ABI, JSON). `pkg/hostsign` (varrat: `Engine.Handle` a kényszerített sorrenddel, `Policy.ValidateTarget` az SS-03 hat lépésével, `Record`/`InteractionsDigest`, `Log`) és `pkg/hostsign/ociprofile` (draft-cavage). Kompozíció a `cmd/relay/cic_flow_send.go`-ban; a send-modul csak a send-motort kapja (nincs nyers signer/egress), a send+sign/actuate együttes import a betöltéskor elutasított; operátori konfiguráció nélkül (`CIC_HOSTSIGN_POLICY`, `CIC_OCI_SIGN_KEY_ID`) a send-modul betöltéskor elutasított.

**Modul.** `actuateSigned` strukturált kérést küld (`method`, `host`, `path`, `query`, `intent{operation, resource_id, binding_digest}`, törzs, `if-match`); az `oci_sign.go` megszűnt; `abi.imports = cic-flow:[send]`; a `module.wasm` újraépítve és csak a `cic-flow.send`-et importálja (a lefordított artifactban mérve). `buildHash` frissítve, **nem aláírva**. `MANIFEST.sha256` regenerálva.

## Acceptance

Oszlopok: komponensszintű = a `pkg/hostsign` motor tesztelve a production `Handle` úton; production-integrációs = a `cmd/relay` regiszterén és a wazero host-modulon át; provizórius vektor = a ref/ közös vektorai (teszt-kulcsos, nem normatív).

| # | Eredmény | Komponensszintű bizonyíték | Production-integrációs | Provizórius vektor |
|---|---|---|---|---|
| AC-SS-01 | **PASS** | `TestAC_SS01_ResponseHasNoSignatureOrAuthorization` (`pkg/hostsign/engine_test.go`): a válasz kulcsai/értékei nem tartalmaznak aláírást/`Authorization`-t, a felsőválasz `Set-Cookie/Authorization/WWW-Authenticate/Signature/X-Content-Sha256` fejlécei nem jönnek vissza még hibás allowlist mellett sem; a felső kérés viszont hordozta a host-aláírást. Bevetett hiba M05, M06: elbukik. | `TestSend_ThroughRegistryAndHostFunction` (`cmd/relay/cic_flow_send_test.go`): a regiszter→host-függvény úton a válasz nem tartalmazza az aláírást | n/a |
| AC-SS-02 | **PASS** | `TestAC_SS02_ForbiddenHeaders` (8 eset, kis/nagybetű): `HEADER_FORBIDDEN`, signer-hívás 0, küldés 0, rekord. M02: elbukik | n/a | n/a |
| AC-SS-03 | **PASS** | `TestAC_SS03_ReferenceCases` (a 10 referencia-eset, a várt `POLICY_*` kóddal, signer 0, küldés 0, denied rekord), `TestAC_SS03_StepOrder` (sorrend), `TestAC_SS03_PathExactness` (10 eset). M01, M03, M19, M20: elbuknak | `TestSend_ThroughRegistryAndHostFunction` (DELETE megfigyelésben: `POLICY_METHOD`, nincs aláírás) | a 10 eset a referencia `validate_target` esetei (nem a vektorfájlból; a vektorfájl nem tartalmaz célvalidálási esetet) |
| AC-SS-04 | **PASS** | `TestAC_SS04_DateFromHostClock`: rögzített óra → a `date` fejléc és az aláírt sztring a host-óra értékét hordozza, óraléptetés követve; guest `date` → `HEADER_FORBIDDEN` aláírás nélkül. M04: elbukik | n/a | n/a |
| AC-SS-05 | **PASS** | `TestAC_SS05_DeniedAndFailedAreRecorded`: allowed/denied/failed(TRANSPORT_ERROR, SIGNER_ERROR) mind kap rekordot, a válasz `interaction_digest` = a rekord digestje; `TestFailures_TimeoutAndResponseTooLarge`; a 10 referenciaeset mindegyike pontosan 1 rekordot ad. M07: elbukik | `TestSend_*` (rekord a motor naplójában) | n/a |
| AC-SS-06 | **PASS** (host) + guest-oldali | `TestAC_SS06_ObservationProfileBlocksWrites` (POST/PUT/PATCH/DELETE, `ObservationOnly` policy: `POLICY_METHOD`, **aláírás előtt**, ellenkontroll: ugyanaz a kérés nem-megfigyelési policyban átmegy). Az `Engine` az `http.Request` módszerét is újra ellenőrzi küldés előtt (mélységi védelem). M08 bevetett hiba: a mélységi őr megtagad, de a signer már hívott, ezért a teszt elbukik (a sorrend is mérve) | modul: `TestObservationOperationsOnlyIssueReads` (observe/poll csak GET); MM3 elbukik | n/a |
| AC-SS-07 | **PASS** | `TestAC_SS07_CoreAndSeamDoNotImportProviderProfile`, `TestAC_SS07_ProviderProfileDoesNotImportCore` (`pkg/hostsign/arch_test.go`, `go list -deps`: tranzitív); `TestArchTestCanSeeEdges` bizonyítja, hogy az eszköz látja a valódi éleket. M24 (core importálja az ociprofile-t), M25 (ociprofile importál core-t): elbukik | `cmd/relay` a kompozíciós gyökér (importálja mindkettőt, ez szándékos) | n/a |
| AC-SS-08 | **PASS** | minden rekord `signing_profile_digest` = `Profile.Digest()` (a descriptor tartalmazza az azonosítót `http-signature:oci:draft-cavage@1`, az algoritmust és az aláírt fejléc-készleteket); `TestAC_SS05_...` és `TestEndToEndVerifiesAsOCI` ellenőrzi. M10: elbukik. Ismeretlen profilnál (`PROFILE_UNKNOWN`) a digest nulla-sentinel (a séma kötelezővé teszi) | n/a | n/a |
| AC-SS-09 | **PASS** | `TestInteractionVectors` (`pkg/hostsign/record_test.go`): a `chain-and-interaction-vectors.json` 3 esete: lista-digest és a rekord-bájtok (base64) **bájtra azonosak** a referenciával; `interactions-seq-gap` és `interactions-order-swapped` → `SEQ_GAP_OR_ORDER`; újsor/nem-ASCII → `BAD_VALUE`. M11, M12: elbukik | n/a | **provizórius** vektor (teszt-kulcsos): a rekord-lista digest nem használ kulcsot, de a vektorfájl státusza provizórius |

A teljes bevetett-hibás futás: `evidence/relay-mutations.log` (M01–M25, mind `DETECTED`, a bukó teszt neve és üzenete a naplóban; a kontroll mutáció nélkül zöld) és `evidence/module-mutations.log` (MM1–MM7, mind `DETECTED`). Egy korábbi futásban M19 (útvonal-előtag az egzakt egyezés helyett) **nem bukott**: ez egy hiányzó teszt volt, pótoltam (`TestAC_SS03_PathExactness`), az újrafuttatásban elbukik.

## Claim-evidence tábla

| Állítás | Státus | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `cic-flow.send` az éles host-felületen exportált | implemented | `cmd/relay/cic_flow_host_funcs.go:96` `WithFunc(perModule(reg, makeSendFn))`; `host_surface_test.go` (a production `productionHostSetup` felsorolja, tábla-bejegyzés `send`) | production-bekötésből felsoroló teszt + `grep` | alacsony |
| A send-motor elérhető a main-ből | implemented | hívási lánc: `main.go:744-747` `sendConfigFromEnv`/`configureSend` → `cic_flow_registry.go:158` `bindSend` (a `stageVerified`→`publish` úton) → `cic_flow_send.go:117` `hostsign.NewEngine`; `cic_flow_send.go:143` `deps.send.Handle`; `deadcode v0.44.0`: 0 sor az új szimbólumokra (`evidence/relay-quality.log`) | grep (nem-teszt) + `deadcode ./...` | alacsony. A `registerVerified`/`publishVerified` deadcode-jelzése előző állapot |
| Az SS-03 célvalidálás aláírás előtt fut | implemented | `pkg/hostsign/engine.go` `Handle` a policy lépése a `Prepare`/`Sign` előtt; mért: signer-számláló 0 minden elutasításnál | teszt + M01/M08 bevetett hiba | alacsony |
| Redirect másik hostra nem követhető | implemented | `TestRedirectToOtherHostIsNotFollowed`: valós `*http.Client`, a szerver 302-t ad evil.example.com-ra, a cél 0 találat, 302 visszaadva; M09 elbukik. A `NewEngine` az `*http.Client` másolatán letiltja a követést | teszt valós klienssel | közepes: más `Doer`-implementációnál (nem `*http.Client`) a szerződés a hívóé; az éles `newEgressClient` eleve nem követ |
| A guest request nem hordoz limitet/aláírást/dátumot | implemented | `DisallowUnknownFields` + tiltott fejléc-lista; `TestInvalidRequests` (10), M15, M16 | teszt + bevetett hiba | alacsony |
| Effective limit = min(operátori, profil); profil nem szélesíthet | implemented | `effectiveLimits`; `TestLimits`; M18 | teszt | alacsony |
| A send-modul nem kap nyers sign/actuate képességet | implemented | `cic_flow_registry.go` `deps = cicFlowDeps{send: eng}`; `TestSend_ModuleHasNoRawSignOrActuate` (még ha a wasm importálná, a host megtagad); `TestSend_LoadTimeRules`; M21, M22 | teszt + bevetett hiba | alacsony |
| Az OCI profil kanonikus formája azonos a régi guest-formával | implemented (komponensszintű) | `TestCanonicalGolden` (literál sztringek), `TestEndToEndVerifiesAsOCI`: valós RSA-kulcs, a fake OCI-végpont a kapott kérésből újraszámolja és ellenőrzi az aláírást; másik kulcs → 401 | teszt | közepes: **valódi OCI ellen nem mért** (UNVERIFIED) |
| Az Oracle guest csak `cic-flow.send`-et importál | implemented | `TestWasmArtifactImportsOnlyCICFlowSend` a lefordított `module.wasm`-on (`wazero` `ImportedFunctions`); MM7: a régi wasm elbukik (`[actuate sign]`) | teszt az artifacton | alacsony |
| A guest kérés a Relay szigorú dekóderén átmegy | implemented (mért, nem commitolt teszt) | `evidence/guest-requests.jsonl` (a modul 5 valódi kérése) → `evidence/guest-requests-through-engine.log`: observe/destroy/execute-PUT `completed`, **nincs `REQUEST_INVALID`** | átmeneti teszt (nem commitolva) | közepes: a futtatás nem része a CI-nek |
| Poll és create kérések kifejezhetők az SS-03 policyval | **concept / nem teljesül** | lásd nyitott blokkolók (1) | mért (`guest-requests-through-engine.log`: poll és create `POLICY_PATH`) | **magas** |
| A `profile_digest` a WP-03 ABI-profil digestje | **scaffold (INTERIM)** | `cic_flow_send.go`: a verifikált `project.yaml` sha256-ja áll helyén | kódolvasás | közepes |

## Mért

- `go test -count=1 -v ./pkg/hostsign/... ./cmd/relay/`: 371 `--- PASS`, 0 FAIL, 0 SKIP (`evidence/relay-tests.log`); a Relay `./core/... ./pkg/... ./cmd/...` regressziója zöld (`evidence/relay-regression.log`); modul: 51 `--- PASS`, 0 FAIL/SKIP (`evidence/module-tests.log`).
- `gofmt -l`, `go vet`, `staticcheck v0.6.1` tiszta a módosított csomagokon (`evidence/relay-quality.log`).
- 25 + 7 bevetett hiba, mind a megnevezett teszt/üzenet szerint bukik.
- A közös vektorokon a rekord-lista digest bájtra azonos.

## Nem mért (UNVERIFIED)

- Valódi Vault Transit-aláírás (tilos); a `SignOCI` pkcs1v15 útvonala nincs ezen a szinten futtatva.
- Valódi OCI-végpont elleni hívás; az OCI-elfogadás csak a fake végponton (az `oci-sign-demo` képletével azonos) mért.
- A teljes CI (`make quality`, `vuln`/govulncheck, mutáció- és proof-kapuk, `manifest-check`) nem futott; csak `gofmt`, `vet`, `staticcheck`, `deadcode`, a Go-tesztek.
- A `module.wasm` TinyGo-újraépítése nem bit-reprodukálható (a repó is kimondja); a `buildHash` a most épített artifactra áll, aláírás nélkül.
- Valós wazero guest ↔ valós Relay `send` host-függvény együttfuttatás nincs (a guest kérések alakja és a host `Handle` a fenti módon, a host-függvény `minMod`-on át, a wasm-guest egy mock hoston át mért külön-külön).
- A `profile_digest`, a policy-digest wire-formája (`CICHOSTPOLICYv1`, saját megvalósítási döntés) és a nulla-sentinel nem szerződéssel rögzített.

## Nyitott blokkolók és döntések (nem csendes döntés)

1. **Poll és create nem fejezhető ki az SS-03 egzakt-sablon szabállyal (mért).** A poll a work-request útvonalát (`/20160918/workRequests/<wr-id>`) hívja; a create útvonalának (`/20160918/vcns`) nincs `resource_id`-ja. Az SS-03 (6): a `path` pontosan az operáció `{resource_id}`-val behelyettesített sablonja. Mindkettő `POLICY_PATH` (`evidence/guest-requests-through-engine.log`). Szerződés-kiegészítés kell (pl. work-request azonosító mint második kötött azonosító; create-nél a cél-konténer mint `resource_id`). Nem találtam ki helyette semmit; a modul a poll `intent.resource_id`-jaként a `binding.resource_id`-t küldi.
2. **`binding_digest` forrása.** A modul új `execBinding.binding_digest` mezőt olvas; a hívónak (Relay/Cabinet) kell adnia. A forrás nincs rögzítve (a `binding-resource-id` szerződés D1–D5 döntései függőben).
3. **A policy forrása és formája.** Operátori JSON-fájl (`CIC_HOSTSIGN_POLICY`) és `CIC_OCI_SIGN_KEY_ID`; a "telepítési policy forrása" a README szerint nyitott, ez átmeneti megvalósítás. A key-azonosító (tenancy/user/fingerprint) eddig a guesttől jött, most operátori: ez viselkedésváltozás.
4. **Ismeretlen/hibás kérések.** A séma-érvénytelen kérés `REQUEST_INVALID` hibát kap és **nem kap rekordot** (nincs értelmezhető method/host); a `REQUEST_INVALID` nem része a válasz-sémának. Ha a rekord-kötelezettség erre is kiterjed, szerződés-pontosítás kell.
5. **`EGRESS_BLOCKED` két helyen:** a manifest-egress aláírás előtt; a dial-idejű blokkolt cím (SSRF-védelem) az aláírás után történik, ott a signer már hívott (rekord `denied`).
6. **Átmeneti `sign`/`actuate`:** a nem-send modulok számára a Relay továbbra is exportálja (a "dev módú átmeneti kezelés" a 03 §11 szerint nyitott; a WP-03 profil-dispatch dönt). A send-modul nem importálhatja őket (betöltéskor elutasított, hívásakor üres deps).
7. **Rekord-hatókör.** A `Log` modulonként él, `Drain()` indítja újra a `seq`-et; a ProofTrace lépés-kötése WP-05 (nem része).
8. **Válasz-puffer.** A guest 256 KiB-os kimeneti puffere kisebb a 1 MiB-os válasznál: a hívás megtörténik és rekordot kap, a guest `-1`-et lát (meglévő viselkedés, nem módosítottam).
9. **Az `Engine`-nek a `date` a `http.TimeFormat` (UTC)**, az eddigi guest `RFC1123 GMT` formátumával azonos.
10. A `MANIFEST.sha256` (modul) regenerálva a `git ls-files` alapján, a Makefile `manifest-update` receptje szerint (docker compose nélkül).

## Fájlok

Relay: `pkg/hostsign/{types,policy,record,engine}.go`, `pkg/hostsign/ociprofile/ociprofile.go`, tesztek: `engine_test.go`, `record_test.go`, `arch_test.go`, `ociprofile_test.go`, `testdata/chain-and-interaction-vectors.json` (provizórius másolat), `cmd/relay/cic_flow_send.go` (+ `_test.go`), módosított: `cic_flow_host_funcs.go`, `cic_flow_manifest.go`, `cic_flow_registry.go`, `egress_client.go`, `main.go`, `host_surface_test.go`.
Modul: `module/provider.go`, `cicflow_guest.go`, `cicflow_host.go`, `oci_sign.go` (törölve), `host_mock_test.go`, `send_contract_test.go`, `module_loadtest_test.go`, `relay_integration_test.go`, `provider_test.go`, `project.yaml`, `module/module.wasm`, `MANIFEST.sha256`, két doc.
Bizonyíték: `output/evidence/` (`relay-mutations.log`, `module-mutations.log`, `relay-tests.log`, `relay-regression.log`, `module-tests.log`, `relay-quality.log`, `guest-requests.jsonl`, `guest-requests-through-engine.log`).
