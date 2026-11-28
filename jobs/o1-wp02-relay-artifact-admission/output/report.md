# o1-wp02-relay-artifact-admission: jelentés (#162, ModuleReleaseEnvelope befogadás)

**A jelentés készítője:** az orchestrátor, az agent megszakadása után (a végrehajtó agent az API 5 órás korlátjába ütközött). A jelentés a Relay-ágon pusholt commitból (`12cfa2e`), a draft PR-ból (#233), az agent által mentett bizonyíték-naplókból (`output/evidence/`) és a draft PR CI-eredményéből készült. **Amit az orchestrátor maga ellenőrzött:** a PR fejcommitja egyezik a pusholt commit-tal, a CI minden jobja zöld (lásd alább), a naplók tartalma. **Amit nem futtatott újra:** a helyi Go-tesztek, a bevetett hibák; ezek az agent naplóin alapulnak.

## Rögzített bemenetek és eredmény

| Elem | Érték |
|---|---|
| CIC_Relay alap | `86ea1ab30e1f234ab294e51385f6f51bbff0aff9` (`main`; a mérés idején a friss HEAD is ez) |
| Feature commit | `12cfa2ed96b20908f13a64581e86f1339c54b2c3` |
| Draft PR | **https://github.com/CentralInfraCore/CIC_Relay/pull/233** (`--base main`, `mergeable`) |
| CI (a `12cfa2e` headSha-n) | minden job `pass`; egyetlen `skipping`: `rust (shard …)` mátrix-job. A `go` (2 chunk), `coverage`, `docgate`, `ffi`, `manifest`, `object-evidence`, `verify`, `baseline-guard`, `completeness`, `mutation-pr`, `python`, `rust` zöld |
| Környezet | docker `golang:1.26.11` (`sha256:957952ae…`) |
| Commit-aláírás | **a commitok nem Vault-aláírtak** (a végrehajtó klónban nem volt gyári hook; a valódi aláírás kívül esik a job hatókörén) |
| Provizórikus bizonyíték | az O-1 envelope-vektorok **provizórikusak, tesztkulcsosak**; a velük kapcsolatos eredmények külön jelölve |

## Implementált viselkedés (V1–V7)

A `loadModule` a capability kötése **előtt**, az **egyszer beolvasott** pufferekből ellenőrzi a `<modul>.envelope.json` + detached `<modul>.sig` párost (`cmd/relay/module_admission.go`). V1 forma/verzió; V2 algoritmus ↔ kulcstípus, `key_id` = sha256(SPKI), kanonikus egysoros base64 `.sig`, aláírás; V2b `module:sign` jogosultság az operátor által pinelt kötésekből (`CIC_MODULE_SIGN_AUTHORITIES`); V3 a meglévő lánc-szabályok (#155) és a CICSourceCA provenance (nélküle `transitional`); V4 nyers digest = envelope = `wasmDigest` = `metadata.buildHash` (**a `verifyBuildHash` a betöltő útvonalon van**) és `sha256(descriptor.WasmCode)` = `executed_wasm_sha256`; V5 a manifest-fájl nyers bájtjainak digestje; V6 prod/nem beállított trust módban a nem `authenticated` cic-flow modul elutasított; V7 a grantek kulcsa `(module_id, envelope_digest)`. A `trust_state` (`authenticated`/`transitional`/`dev`) naplózott, csak az `authenticated` kap capabilityt. A `SetStripWasmModuleFunc` csak `-tags cic_test_seams` alatt fordul; a `stripWasmModuleFunc` és a `Checksum()` **változatlan**.

**Viselkedésváltozás (jelezve):** a csak `.pem`-mel (envelope nélkül) rendelkező modul már nem kap `cic-flow` vagy `git` capabilityt; prodban a cic-flow-t importáló elutasított. **A production aktiválás a WP-01 envelope-jaitól függ, ez nem része a PR-nak.**

## Acceptance (AC-162-01…19)

Státusz: a megnevezett teszt a helyi naplóban (agent) és a CI `go` jobokban zöld, a bizonyítás **komponensszintű**, provizórikus vektorokkal ahol jelölve. A negatív tesztek megnevezett okát a 17 bevetett hiba bizonyítja (lent).

| AC | Teszt | Státusz | Megjegyzés |
|---|---|---|---|
| 01 más által épített modul érvényes tanúsítvánnyal | `TestAdmission_AC01_…` | PASS | bevetett hiba M01 |
| 02 manifest az aláírás után módosítva | `…AC02_…` | PASS | M02 |
| 03/16 WASM cserélve, nyers módosítás | `…AC03_AC16_…` | PASS | M03 |
| 04 újrahasznált `moduleID` nem örököl | `…AC04_…` | PASS | M09, M13 |
| 05 ismeretlen envelope-verzió | `…AC05_…` | PASS | M05 |
| 06 `key_id` ≠ SPKI | `…AC06_…` | PASS | M06 |
| 07 hiányzó `.sig` prodban | `…AC07_…` | PASS | M08 |
| 08 dev opt-in, `trust_state=dev` | `…AC08_…` | PASS | M12 |
| 09 a `verifyBuildHash` hívási útja | `…AC09_…` + reachability | PASS | `module_admission.go:320`; M11 |
| 10 pozitív eset | `…AC10_…` | PASS | |
| 11 #155 nem romlik | `…AC11_…` | PASS | M17 |
| 12/17 futtatott reprezentáció eltér | `…AC12_AC17_…` | PASS | M04 |
| 13 `SIGNER_NOT_AUTHORIZED` | `…AC13_…` | PASS | M07 |
| 14/14b/19 egyetlen beolvasás, TOCTOU | `…AC14_AC19_…` | PASS | M10 |
| 15 `metadata.sign` önálló marad | `…AC15_…` | PASS | |
| 18 a setter production-elérhetetlen | `…AC18_…` + fordítási próba | PASS | production build: `undefined: cabinet.SetStripWasmModuleFunc`; `-tags cic_test_seams`: build rc=0; M16 |

Kiegészítő tesztek: `Ed25519Signer`, `EnvelopeAndSignatureForm` (M15), `EnvelopeModuleIDMustMatchManifest` (M13), `RSASignerCanNotSignAnEnvelope`, `TestO1EnvelopeVectors_Provisional` (**26/26, provizórikus**), `…WabinExecutedRepresentation`.

## Bevetett hibák (a megnevezett okból bukás)

17 mutáció (M01–M17), **mind a megnevezett teszten bukott** (`30-fault-injection.txt`, `RESULT: FAILED as required` ×17; mind a forrás visszaállítva). A mutációk: aláírás-ellenőrzés kikapcsolva, manifest-/nyers-/futtatott digest, verziók, `key_id`, jogosultság, prod-szabály, V7-kötés, második fájlolvasás, a `verifyBuildHash` hívás eltávolítása, dev-út, `module_id`, algoritmus-típus, `.sig`-forma, a setter visszakerülése, #155.

## Claim-evidence

| Állítás | Státus | Bizonyíték | Verifikációs módszer | Kockázat | Bizonyíték-szint |
|---|---|---|---|---|---|
| a V1–V7 ellenőrzés a betöltő útvonalon van | implemented | `module_admission.go:320`, `41-reachability-grep.txt`; AC09 + M11 | grep a nem-teszt kódban; a hívás eltávolítása elbuktatja a tesztet | a production aktiválás a WP-01 envelope-jaitól függ | komponensszintű |
| a `verifyBuildHash` a betöltő útvonalra került | implemented | `cic_flow_manifest.go:319` definíció, `module_admission.go:320` hívás | reachability grep | — | komponensszintű |
| a setter production-ban elérhetetlen | implemented | `40-ac18-compile-probe.txt` | production build hibája; `-tags cic_test_seams` build | a `cic_test_seams` teszt nincs a CI-ban | komponensszintű |
| a #155 viselkedése nem romlik | implemented | AC11 + M17; CI zöld | teszt + bevetett hiba | — | komponensszintű |
| a vektorokon 26/26 a várt kód | implemented (provizórikus) | `10-vectors*.txt`; `TestO1EnvelopeVectors_Provisional` | teszt a közös vektorokon | a vektorok provizórikusak, a WP-00 korrigált vektorára kell átállni | **provizórikus** |
| a wabin-viselkedés eltér a referenciától | mért | `11-wabin-vs-reference.txt` | a `wasm_raw` és javított változata is elutasítva; nem-`name` custom szekcióval a referencia-bájtok egyeznek | lásd W-1 (WP-00) | mért |
| `go vet`, `staticcheck`, `gofmt`, docgate (Go-rész) tiszta | mért | `60-final-gates.txt`, `51-docgate-go.txt` | helyi futtatás docker-ben; a CI docgate is `pass` | — | komponensszintű |
| lefedettség: `cmd/relay` 91,7%, `core/cabinet` 94,2% | mért | `50-coverage-race-symbols.txt` | `go test -cover`, `-race` zöld | — | komponensszintű |
| production-integrációs bizonyíték | **nincs** | — | — | az envelope-ok előállítása (WP-01) hiányzik | **production-integráció: nem mért** |

## Mért / nem mért / nyitott blokkolók

**Mért:** a fentiek (CI zöld a `12cfa2e`-n; AC-162-01…19 tesztjei; 17 bevetett hiba; vet/staticcheck/gofmt; deadcode-diff `22-deadcode-diff.txt`).

**Nem mért (UNVERIFIED):**
- valódi Vault-kulcs / valódi aláírt envelope (WP-01 feladata); a Vault-kulcs algoritmusa nem mért itt;
- a `cic_test_seams` címkés teszt **nincs a CI-ban**;
- a `go vet ./...` / `deadcode ./...` a teljes repón helyben a megnevezett csomagokon futott, a CI-é teljes;
- a WP-00 **korrigált vektorára** való átállás (a jelenlegi vektorok a W-1 szerint hibás nyers modult tartalmaznak, amit ez a job is mért).

**Nyitott blokkolók / döntések:**
1. **W-1 (WP-00 és ez a job is mérte):** a vektorok `wasm_raw` modulja hibásan kódolt; a wabin a `name` custom szekciót újrakódolja. A `wasm-canon/v1` szövegének pontosítása tulajdonosi döntés (a transzformációt nem módosítottuk).
2. **Production aktiválás:** a WP-01 envelope-jai nélkül minden `cic-flow`-t importáló modul prodban elutasított, ez a szándékolt fail-closed viselkedés, de az aktiválás sorrendjét a tulajdonosnak kell rögzítenie.
3. **Commit-aláírás:** a commitok nem Vault-aláírtak; ha a lánc aláírása követelmény, újra kell készíteni hookkal (nem amenddel).
4. **ProofTrace:** az `executed.envelope_digest` bekötése a WP-05 dolga.

**Nem része (HOLD):** valódi Vault-aláírás, countersign, release, publikáció, merge, production aktiválás.

---

## Review-kör 1 (külső review a `12cfa2e` fejre; javítások a `28042aa` és `87bb1e3` commitban)

A külső review F1–F6 leleteit a PR `12cfa2e` fejére adta; a javítást az orchestrátor végezte (a végrehajtó agent megszakadt). Ez a szakasz a fenti jelentés kiegészítése, **a fenti AC-táblák a `12cfa2e`-re vonatkoztak**.

| Lelet | Javítás | Bizonyíték |
|---|---|---|
| F1 strict JSON | szigorú olvasó az envelope-ra (ismeretlen, kis/nagybetűben eltérő, duplikált kulcs, záró adat); azonos algoritmus a #234 olvasójával, külön másolat (két ág, `package main`); a hiányzó/ismeretlen verzió továbbra is `ENVELOPE_VERSION` | `TestAdmissionReview_F1_*`; M31–M34 |
| F2 transitional vs. sikertelen hitelesítés | verifikált envelope + hiányzó CICSourceCA-provenance → `PROVENANCE_UNVERIFIED` elutasítás dev és prod módban; csak az envelope nélküli modul transitional. **Három, a lefokozást elváró meglévő teszt az új szabályra módosult** (`TestLoadModule_CICFlow_FailClosedWithoutSourceCA`, a két git-teszt): ezek a review szándékát rögzítették, nem lazítás | `TestAdmissionReview_F2_*`; M36 |
| F3 WASM-import ↔ manifest | a végrehajtott wasm tényleges `cic-flow`/`git` importjai deklaráltak kell legyenek (`IMPORT_UNDECLARED`); a V6 a tényleges importokra is érvényes | `TestAdmissionReview_F3_*`; M37 |
| F4 konfig-olvasó | a `module:sign` jogosultsági fájl ugyanazt a szigorú olvasót használja, a bemenet végét is ellenőrzi | `TestAdmissionReview_F4_*`; M35 |
| F5 vektorok | a végleges `wasm-canon/v1` vektor (WP-00); a `executed` bájtok **kötelező assertion** szerint egyeznek a Relay saját transzformációjával | `TestO1EnvelopeVectors_ExecutedIsTheRelaysTransformation`; M39b |
| F6 CI | **egyetlen, additív lépés** a `verify.yml`-ban a `cic_test_seams` konfigurációra (`go vet` + `go test` a két csomagon), **külön commit** (`87bb1e3`); meglévő kapu, küszöb, mutation/proof/trust követelmény nem módosult | a lépés a GitHub CI-n még nem futott: **UNVERIFIED** |
| F4 (trust bundle, freshness, anti-rollback) | **nem része**: a komponensszintű `CIC_MODULE_SIGN_AUTHORITIES` marad; a teljes production admission külön státusz | — |

**Kapuk (helyi, docker `golang:1.26.11`):** `go test ./...` ok; `-race` és `-tags cic_test_seams` ok; lefedettség `core/cabinet` 94,2%, `cmd/relay` 91,5%; gofmt, vet (mindkét konfiguráció), staticcheck, docgate 0 hiányzó. **Bevetett hibák:** M31–M37 és M39b a megnevezett teszten bukik; **M38 egyenértékű mutáns** (a hiányzó verzió a struct-ellenőrzésből ugyanazt az `ENVELOPE_VERSION` kódot adja), M39 első változata gyenge mutáció volt (a digest-egyezés a bájt-egyezést is jelenti), M39b váltotta.

**Nyitott / UNVERIFIED:** a GitHub CI a `87bb1e3` fejre; a `verify.yml` új lépése CI-n; a trust bundle digest-pin, minimális verzió, freshness és anti-rollback (production admission); a közös strict-JSON csomag (követő lépés, ha a #233 és a #234 egyaránt landolt); a teljes kötés a #234 `ModuleProfileBinding.EnvelopeDigest` mezőjéhez (integrációs ág).
