# claim-mapping.md — a `devel` sign/actuate-mockhoz kötött tesztek és assertionök új helye

**Job:** `o1-wp04b-module-send-migration` · **Bázis:** `cic-module-oracle-cloud` `devel` `ae3c962`
**Kérdés, amire ez a tábla válaszol:** a bizalmi határ áthelyezésével melyik **szerződéses
tulajdonság** hova került, és mi a bizonyíték. A tesztek száma és az assertionök helye változhatott;
**elvesztett tulajdonság nincs**.

## 0. A mérés, amiből a tábla áll

| Mérés | Parancs / napló | Eredmény |
|---|---|---|
| Teszt-leltár a portolás előtt/után | `go test -list ".*"`, `comm`; [`evidence/35-fresh-guest-and-inventory.log`](evidence/35-fresh-guest-and-inventory.log) | 141 → 151 teszt, **0 eltávolított** |
| Teljes suite a portolás után | [`evidence/34-suite-after-rebuild.log`](evidence/34-suite-after-rebuild.log) | 147 PASS / 0 FAIL / 4 SKIP |
| A 4 SKIP (fresh-guest) | [`evidence/43-wasm-final-artifact.log`](evidence/43-wasm-final-artifact.log) | mind a 4 PASS a **committolt** artifact ellen |
| Mock-felület használata a `devel`-en | [`evidence/04-mock-surface-inventory.txt`](evidence/04-mock-surface-inventory.txt) | 281 hivatkozás, 16 fájl |
| Negatív tesztek bevetett hibával | [`evidence/20-mutation-negative-tests.log`](evidence/20-mutation-negative-tests.log) | 5 hiba, mind a megnevezett okból bukik |
| SS-03 kódok a Relay saját kódja ellen | [`evidence/50-ss03-relay-measurement.log`](evidence/50-ss03-relay-measurement.log) | `POLICY_TARGET` / `POLICY_PATH` / `POLICY_METHOD` |

## 1. A kulcsdöntés: a mock a határ **host** oldalára került

A `devel` tesztjei két host-hívást (`cic-flow.sign`, `cic-flow.actuate`) hajtottak meg a guesten
keresztül. A migráció után a guestnek **egy** importja van (`cic-flow.send`), a signálás a hosté.

Ezért a `testCallHostSign` / `testCallHostActuate` **nem szűnt meg**, hanem **átkerült**
`module/cicflow_host.go`-ból `module/host_mock_test.go`-ba: ott már a **szimulált Relay** signere és
transportja, amit a `mockRelaySend` hajt meg. A `cicFlowMock` továbbra is rögzíti, mit *írt alá* és
mit *küldött el* a (szimulált) host — így a `devel` ~110 assertionje **ugyanazt a tulajdonságot**
ellenőrzi, mint korábban, 13 fájlban **változtatás nélkül**.

**Miért nem „olyan teszt, ami nem tud elbukni”:** a szimulált host csak akkor ír alá bármit, ha a
**guest production kódja** küldött neki kérést. Ezért a `signCount() == 0` ma is pontosan azt jelenti,
hogy *a guest nem küldött semmit* — a kapu-tesztek állítása érintetlen. Ahol viszont az assertion a
**mock saját képletét** ellenőrizte volna (kanonikus karakterlánc, `Authorization` tartalma), ott az
assertion **kikerült a modulból** (lásd 3. szakasz), mert ott valóban nem tudna elbukni guest-hiba
miatt.

## 2. Megőrzött tulajdonságok (az assertion a helyén maradt)

| # | Szerződéses tulajdonság | Hol volt (devel) | Hol van most | Bizonyíték |
|---|---|---|---|---|
| P-1 | M4a terv-kötés: a kapu **aláírás és küldés előtt** elutasít | `m4a_gate_test.go:308,319,615` (`signCount()==0 && actuateCount()==0`) | ugyanott, változatlanul; a számlálók a szimulált host lépéseit mérik, amit csak guest-kérés indíthat | `34-suite-after-rebuild.log` (M4a tesztek PASS) |
| P-2 | M3 registry-konform execute: lépésenként pontosan egy provider-kérés | `execute_registry_conformance_test.go:54,243` | ugyanott, változatlanul | ua. |
| P-3 | binding `resource_id` validáció: rossz id esetén semmi nem megy ki | `binding_resource_id_test.go:129,147,166,236,284` | ugyanott, változatlanul | ua. |
| P-4 | `poll` cél-útvonal szigorúság (M5): rossz bemenet → elutasítás kérés nélkül | `poll_contract_test.go:51,220` | ugyanott, változatlanul | ua. |
| P-5 | plan/create konformancia: terv-fázisban nincs kimenő kérés | `plan_create_conformance_test.go:76` | ugyanott, változatlanul | ua. |
| P-6 | `createdResourceID`: 2xx create id nélkül **bukik**, és **nincs újrapróbálkozás** (1 kérés) | `execute_create_id_test.go:228,274,304`, `execute_create_async_message_test.go:56` | ugyanott, változatlanul | ua. |
| P-7 | OCID-határok | `ocid_boundary_test.go:55` | ugyanott, változatlanul | ua. |
| P-8 | `If-Match` (optimista konkurencia) kimegy a mutáló kéréssel | `provider_test.go:330` (`r.Headers["if-match"]`) | ugyanott **és** közvetlenül a guest kérésén: `send_contract_test.go` (`request.headers["if-match"]=="etag-42"`) | `20-mutation-negative-tests.log` CONTROL |
| P-9 | a kérés a `base_path`-szal prefixelt teljes útvonalra megy | `execute_create_id_guest_test.go:112` (az aláírt stringen) | **új hely, ugyanaz a tulajdonság:** `execute_create_id_guest_test.go` most a guest `send` kérés `path`-ját állítja (`POST /20160918/vcns`), a kimenő URL assertion megmaradt | `34-suite-after-rebuild.log` |
| P-10 | a valódi wasm határon át is működik a teljes execute | `module_loadtest_test.go:TestHostLoadExecute` | ugyanott; az assertion a strukturált `send` kérésre mutat (method/host/path/intent/profile) | `34-suite-after-rebuild.log` |
| P-11 | valódi RSA-aláírás egy valódi TLS szerverig; rossz aláírást a szerver elutasít | `relay_integration_test.go:TestRelayIntegrationExecuteSigned`, `…RejectsBadSignature` | ugyanott; a `sign`/`actuate` függvény most a **szimulált host** signere/transportja (`mockRelaySend`-en keresztül), a guest csak `send`-et hív | `34-suite-after-rebuild.log` |
| P-12 | `observe` derivációk, `observed_at` jelenléte | `observe_derivation_test.go`, `observed_test.go` | ugyanott; `observed_at` immár `observedAtFormat`-tal (RFC 1123 GMT, változatlan alak) | ua. |
| P-13 | opt-in valódi OCI harness | `manual_real_oci_test.go` | ugyanott, változatlanul (a `sign`/`actuate` hookokat használja, amik most a host oldalán vannak) | compile + `golang.test.manual-real-oci` nem futott (opt-in, `REAL_OCI_TEST=1`) → **UNVERIFIED (szándékos)** |

## 3. Áthelyezett tulajdonságok (az assertion új helye a Relay)

Ezek **nem a guest tulajdonságai többé**. A modulban hagyva olyan tesztek lennének, amelyek a
teszt-mock saját képletét ellenőrzik — azaz guest-hibától nem tudnának elbukni. Ezért a modulból
**kikerültek**, és a Relay `pkg/hostsign/ociprofile` tesztjeiben élnek.

| # | Tulajdonság | Hol volt (devel) | Új hely (Relay, `pkg/hostsign/ociprofile`) | Mi maradt a modulban |
|---|---|---|---|---|
| R-1 | a kanonikus string alakja: `(request-target): <lowercase method> <target>`, `host:`, `date:` | `module/oci_sign.go` + `execute_create_id_guest_test.go:112`, `module_loadtest_test.go:401` | `ociprofile_test.go:45` (`TestCanonicalGolden`) | **negatív** állítás: a guest kérése nem tartalmaz `request-target`-et (`send_contract_test.go`) |
| R-2 | body-metódusnál az aláírt fejlécek bővülnek `x-content-sha256`/`content-type`/`content-length`-szel | `module/oci_sign.go` (`bodyMethod`, `ociCanonical`) | `ociprofile_test.go:54-55` | **negatív**: a guest kérésében ezek a kulcsok nem szerepelnek (teljes JSON-bejárás) |
| R-3 | `Authorization: Signature version="1",keyId=…,algorithm="rsa-sha256",headers=…,signature=…` | `module/oci_sign.go` (`ociAuthorization`) + `module_loadtest_test.go:411` | `ociprofile_test.go:47`, `:82` (`TestEndToEndVerifiesAsOCI`) | **negatív**: nincs `authorization` kulcs és nincs `rsa-sha256` a guest kérésében |
| R-4 | a `date` a host órájából jön | `provider.go` (`nowFunc().Format(ociTimeFormat)` a kérés építésénél) | `hostsign` engine + `ociprofile.Prepare(r, date)` | **negatív**: a guest kérésében nincs `date`; a `nowFunc` már csak `observed_at`-hoz kell |
| R-5 | a kulcsazonosító (`keyId`) a hoszté | `provider.go` (`binding.key_id` → `Authorization`) | `hostsign.Key.KeyID` (a guest nem nevezi meg) | `execBinding.KeyID` **informatív** marad (publikált kérés-séma), kommentben kimondva; a `send` kérés nem hordoz `key_id`-t (JSON-bejárás tiltja) |
| R-6 | cél-validáció **aláírás előtt** (SS-03) | nem létezett modul-oldalon | `hostsign.Policy.ValidateTarget` (`policy.go`), mérés: `evidence/50-…log` | a modul a host **kódját** jeleníti meg (`ss03_poll_create_denial_test.go`) |

**Megjegyzés R-1..R-3-hoz:** a formulák **nem tűntek el** a modul repóból: a
`module/host_mock_test.go` (teszt-only, `//go:build !wasip1`) tartja őket, mert a szimulált Relay
nélkül a modul tesztjei nem tudnák végighajtani a valódi guest-utat. Ez a fájl **nem fordul bele a
guestbe**, és a `TestGuestSourcesBuildNoAuthorization` mechanikusan tiltja, hogy bármelyik
nem-teszt forrásban megjelenjenek.

## 4. Megszűnt kód és ami helyette bizonyít

| Megszűnt | Volt-e rá külön teszt a `devel`-en? | Mivel bizonyított ma |
|---|---|---|
| `module/oci_sign.go` (teljes fájl, 70 sor) | **Nem** (nincs `oci_sign_test.go` a `devel`-en; csak közvetve, `mock.Signed`-en keresztül) | R-1..R-3 (Relay), plusz a modul negatív állításai |
| `firstNonEmpty` | nem | csak a régi `sign` válasz hibakezelését szolgálta; a `send` válasz saját `code`/`error` mezőivel dolgozik, `TestSendDeniedFailedAndErrorAreErrors` fedi |
| `wasmCicFlowSign`, `wasmCicFlowActuate` | `provider_test.go:53` (`imports` darabszáma) | `TestDescribeManifest` (most `[send]`), `TestProjectYAMLDeclaresOnlySend`, és a **lefordított** artifacton `TestWasmArtifactImportsOnlyCICFlowSend` |
| `ociTimeFormat` a production kódból | nem | `observedAtFormat` (csak `observed_at`-hoz); a kérés dátuma a hosté (R-4) |

## 5. Új tulajdonságok, amelyeket a `devel` nem tudott ellenőrizni

| # | Tulajdonság | Teszt | Bevetett hibával mérve |
|---|---|---|---|
| N-1 | a guest kérése **strukturált** és egyetlen host-birtokolt mezőt sem hordoz (teljes JSON-bejárás) | `TestSendRequestIsStructuredAndCarriesNoHostOwnedFields` | FAULT 3 (`authorization`+`date` beinjektálva) → bukik, megnevezve a mezőt |
| N-2 | `path` és `query` szétválasztva megy (az SS-03 külön validálja) | `TestSendQueryIsSplitFromPath` | FAULT 5 (szétválasztás kikapcsolva) → bukik |
| N-3 | mind a három kimenet helyesen olvasva; denial/failure **nem** siker | `TestSendDeniedFailedAndErrorAreErrors` | FAULT 1 (denial → siker) → bukik |
| N-4 | a host **megnevezett kódja** eljut a hívóig | `TestPollWorkRequestTargetIsDeniedWithPolicyPath`, `TestCreateIsDeniedWithPolicyMethod`, `TestDenialAndFailureKeepTheirOwnWording` | FAULT 2 (kód elhagyva) → mind a 4 altest bukik |
| N-5 | az `observe`/`poll` csak olvasást küld | `TestObservationOperationsOnlyIssueReads` | — (pozitív állítás; a `devel` M5 tesztjei fedik a negatívot) |
| N-6 | a **lefordított** artifact egyetlen `cic-flow` importja a `send` | `TestWasmArtifactImportsOnlyCICFlowSend` | a portolás előtti, elavult `module.wasm`-on **tényleg elbukott**: `[actuate sign]`, lásd `evidence/34-…` előtti futás és a 4. commit üzenete |
| N-7 | nincs aláírás-építés egyetlen nem-teszt forrásban sem | `TestGuestSourcesBuildNoAuthorization` | FAULT 3 → bukik (`provider.go still contains "authorization"`) |
