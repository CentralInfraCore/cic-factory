# #162: artifact-hitelesítés: implementációs határ, érintett fájlok, acceptance

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## 1. A probléma (a #162 szövege és a mérések)

A cic-flow capability kötése a `loadModule` → `registerModuleCapability` útvonalon az **aláíró tanúsítványt** hitelesíti (X.509 lánc + CICSourceCA), **nem** a modult és **nem** a manifestet. A `.pem` egy nyilvános tanúsítvány; a `capability_manifest` (egress, secrets) a tanúsítvány puszta jelenlétével "hitelesített". A `verifyBuildHash` csak tesztből hívott.

**Új, a signing oldalon mért tény:** a modul release-folyamata (`tools/infra.py:254` `_resign_with_build_hash`) a Vault-kulccsal `sha256(kanonikus JSON {name, version, checksum, build_timestamp, buildHash})`-t ír alá (`metadata.sign`). Ez a **`buildHash`-t (= a nyers WASM sha256-ja) lefedi**, de **a `capability_manifest`-et és az `abi` blokkot nem**: a manifest utólagos szerkesztését semmilyen jelenlegi aláírás nem fogja meg. A `metadata.cicSign` (CIC ellenjegyzés) lefedettsége **UNVERIFIED** (a repóban placeholder; a termelő kódot nem olvastam). A #162 nyitott kérdése ("létezik-e az aláírás máshol?") ezzel részben megválaszolt: a modul-oldali aláírás létezik, de **nem a szükséges burkot** köti.

## 2. A javasolt burok (`ModuleReleaseEnvelope` v1; wire: `schemas/module-release-envelope.schema.json`)

```json
{"kind":"ModuleReleaseEnvelope","envelope_version":1,"module_id":"cic-module-oracle-cloud@0.1.0",
 "wasm_sha256":"sha256:…","executed_wasm_sha256":"sha256:…","manifest_digest":"sha256:…","signer":{"key_id":"sha256:…","alg":"ecdsa-p256-sha256"}}
```

| Mező | Jelentés | Forrás |
|---|---|---|
| `wasm_sha256` | a **nyers** WASM sha256-ja (D-10: = `metadata.buildHash` = `wasmDigest`) | a signing oldal számolja; a Relay a betöltött bájtokból újraszámolja |
| `manifest_digest` | **ENV-01:** a **teljes betöltött release-manifest fájl NYERS bájtjainak** sha256-ja (a `<modul>.yaml`, egyetlen beolvasott puffer; nincs YAML/JSON-kanonizálás, nincs részleges lefedés: a `capability_manifest`, az `abi`, a `metadata` és minden más mező együtt). A detached aláírás miatt nincs önhivatkozás: a manifestet előbb véglegesíteni kell, utána készül az envelope | a Relay ugyanabból a pufferből számolja, amelyből parse-ol |
| `executed_wasm_sha256` | a **ténylegesen példányosított** (kanonikus, stripelt) WASM bájtok sha256-ja. **Mért:** a `ModuleDescriptor.WasmCode` a `canonicalWasm`, nem a nyers fájl (`core/cabinet/module_descriptor.go`, a descriptor-építés), a wazero ezt fordítja (`cicwasm.go:153`); a nyers digest tehát **nem** a futtatott bájtok identitása | a signing oldal számolja; a Relay a descriptor-ból újraszámolja |
| `signer.key_id` | az aláíró tanúsítvány nyilvános kulcsának sha256-ja | a `.pem` tanúsítványból |
| `module_id` | `név@verzió` | információs, a regisztrációs kulcs része |

**Az aláírt tartomány (byte-pontos, nem JSON-újraszerializálás):** `CICMODENVv1\n` tartomány-sor, majd rögzített sorrendben `module_id=`, `wasm_sha256=`, `executed_wasm_sha256=`, `manifest_digest=`, `signer_key_id=` sorok, LF-lezárással, kisbetűs hexával. Példa: `examples/valid/envelope-signed-bytes.txt`; a builder ellenőrzi: kulcssorrend-független, és bármely mező egy karakteres változása megváltoztatja a bájtokat. Ez **egy javaslat a kanonikus forma nyitott kérdésére** (R7): szándékosan nem JSON, hogy ne legyen újraszerializálási kétértelműség.

**Az aláírt tartomány követelményei (a review ellenőrzőlistája) és a referencia-parser:** karakterkódolás: ASCII (a UTF-8 részhalmaza), explicit; sortörés kizárólag LF, CR elutasított; a végső LF kötelező; a mezők sorrendje rögzített (`module_id`, `wasm_sha256`, `executed_wasm_sha256`, `manifest_digest`, `signer_key_id`); duplikált, ismeretlen és hiányzó mező elutasított; az értékbe ágyazott sortörés elutasított (az új sor mezőként értelmeződik, ismeretlen mezőként bukik); digest: kizárólag `sha256:` + 64 kisbetűs hex; domain separation: `CICMODENVv1`. A `build_o1_schemas.py` szigorú referencia-parsere 12 esetet ellenőriz (`validation-report.txt`), az emit→parse→emit körút azonos. Ez **szerződés-szintű önkonzisztencia**, nem független második implementáció.

**Aláírás:** detached, `<modul>.sig`, a `.pem` tanúsítvány kulcsával, a burok **kanonikus bájtjainak** sha256-ján. Az `envelope_version` ismeretlen értéke elutasítás. A **kanonizálás nyitott** (közös az admission szerződéssel); a Go oldalon a `pkg/canonicaljson` a jelölt (MÉRT: a csomag létezik), a Rust oldalon a `cic-canonical` csak a számokat fedi.

## 3. Az ellenőrzési algoritmus (a Relay betöltő útvonalán)

| Lépés | Ellenőrzés | Hiba |
|---|---|---|
| V1 | a burok és a `.sig` jelen van, a séma szerint érvényes, a verzió ismert | `ENVELOPE_MISSING`, `ENVELOPE_INVALID`, `ENVELOPE_VERSION` |
| V2 | a `.sig` érvényes a `.pem` tanúsítvány kulcsán a burok kanonikus bájtjaira; `signer.key_id` = a tanúsítvány kulcsa | `SIGNATURE_INVALID`, `KEY_MISMATCH` |
| V3 | a tanúsítványlánc a meglévő (EKU, CRL, SPKI, CICSourceCA) szabályok szerint | a mai hibák |
| V2b | a `signer.key_id` **nem jogosultsági bizonyíték**: az aláíró `module:sign` jogosultsága a trust bundle authority-kötéséből jön (admission A1), a kulcs puszta jelenléte egy tanúsítványban nem elég | `SIGNER_NOT_AUTHORIZED` |
| V4 | **egyetlen beolvasás:** a hash-elt bájtpuffer **ugyanaz**, amelyből a descriptor épül (nincs második fájlolvasás); `sha256(nyers) = envelope.wasm_sha256 = wasmDigest = metadata.buildHash` (**itt hívandó a `verifyBuildHash`**), és `sha256(descriptor.WasmCode) = envelope.executed_wasm_sha256` | `WASM_DIGEST_MISMATCH`, `EXECUTED_DIGEST_MISMATCH` |
| V5 | `sha256(a betöltött manifest nyers bájtjai) = envelope.manifest_digest`, és a parse **ugyanabból a pufferből** történik (nincs második olvasás); **kötelező AC-162-14b** | `MANIFEST_DIGEST_MISMATCH` |
| V6 | prod: ha a modul `cic-flow`-t importál és bármelyik lépés sikertelen: **elutasítás**, nem "capability nélküli betöltés" | `MODULE_REJECTED` |
| V7 | **ENV-03:** a capability kötése a **hitelesített envelope-identitáshoz**: `envelope_digest = sha256(CICMODENVv1 aláírt bájtok)`, amely mind a hat mezőt (`module_id`, `wasm_sha256`, `executed_wasm_sha256`, `manifest_digest`, `signer_key_id`, `signer_alg`) lefedi; a regisztrációs kulcs `(module_id, envelope_digest)`, nem a `moduleID` és nem egy részhalmaz. `authenticated` állapotban a ProofTrace `executed.envelope_digest` kötelező | — |

A **trust_state** (D-1): a V1–V7 teljesülése `authenticated`; a mai, V1–V2 és V4–V5 nélküli út `transitional`; dev mód `dev`. A V6 miatt a trusted követelményt nem teljesítő modul **nem** kerül automatikusan `transitional`-ba.

## 4. Érintett fájlok (CIC_Relay `86ea1ab`)

| Fájl | Mi történik | Mért kiindulás |
|---|---|---|
| `cmd/relay/bootstrap.go` | a `loadModule` (499–620) a `registerModuleCapability` hívása (592–598) **elé** kapja a V1–V6 ellenőrzést; a nem aláírt dev-út (605–617) marad, `trust_state = dev` | a `wasmDigest` ellenőrzés már itt van; a `.pem` csak tanúsítványként olvasott |
| `cmd/relay/cic_flow_manifest.go` | `moduleProject` bővül a burok-mezőkkel; új `verifyEnvelope`; a `verifyBuildHash` (319) **hívása** a betöltő útvonalra kerül; a manifest-digest számítás | a `moduleProject` (≈115) a YAML `capability_manifest`/`abi` mezőit már parse-olja |
| `cmd/relay/cic_flow_registry.go` | a kötés kulcsa `(module_id, envelope_digest)` (ENV-03); a `publish` (140–175) az `envelope_digest`-et **minden** `authenticated` modulra rögzítse (ma csak git-szabályosra: F8) | a `bindingFor` (127) ma csak git-grantes modulnál ad kötést |
| `cmd/relay/pki_companion.go` | a `verifyCICFlowProvenance` (69–84) változatlanul újrahasznosított (V3) | — |
| `cmd/relay/bootstrap.go` `PKIAssets` (311–333) | a V2 a már betöltött tanúsítvány kulcsát használja; a trust bundle és az operátori trust domain (admission) **később** köthető ide | `Roots`, `SourceRoots` már a külsőleg betöltött bizalmi gyökér |
| Tesztek: `cic_flow_integration_test.go`, `module_identity_negative_test.go`, `bootstrap_test.go`, `shared_trust_context_test.go`, `git_capability_test.go` | az acceptance negatív tesztjei ide | léteznek `loadModule`-t hívó tesztek |
| **Modulrepó** (`tools/infra.py:254–`, release-folyamat) | a **signing oldal** előállítja a burkot és a `.sig`-et; **[J], előfeltétel** | a mai aláírt halmaz nem fedi a manifestet |

**Nem érintett:** a ProofTrace, a dispatch (Cabinet), a `sign`/`actuate` host-függvények (D-11 külön), a reprodukálható build (nem előfeltétel: a bizalom az integritáson, nem a reprodukción alapul, `release-artifact.md`).

## 5. Acceptance kritériumok (negatív tesztek; a #162 négy tesztje + kiegészítés)

| # | Kritérium |
|---|---|
| AC-162-01 | **érvényes tanúsítvány mellett más által épített modul** (az aláírás nem a bemutatott burokra) → nincs capability, prodban elutasítva |
| AC-162-02 | a **manifest az aláírás után módosítva** (szélesebb egress, extra secrets) → elutasítva (`MANIFEST_DIGEST_MISMATCH`) |
| AC-162-03 | a **WASM cseréje** úgy, hogy a YAML és a tanúsítvány marad → elutasítva (`WASM_DIGEST_MISMATCH`) |
| AC-162-04 | **újrahasznált `moduleID` más digesttel** nem örökli a korábbi modul capabilityjét (a kötés a hitelesített identitáshoz) |
| AC-162-05 | ismeretlen `envelope_version` → elutasítva |
| AC-162-06 | a burok `key_id`-je nem a `.pem` kulcsa → `KEY_MISMATCH` |
| AC-162-07 | hiányzó `.sig` prodban, `cic-flow`-t importáló modulra → elutasítva (nem capability nélküli betöltés) |
| AC-162-08 | dev opt-in, nem aláírt modul → nincs capability, a futás `trust_state = dev`, trusted állítást nem hordozhat |
| AC-162-09 | a `verifyBuildHash` a betöltő útvonalról hívott (nem csak teszt): hívási-út bizonyíték (`file:line`) |
| AC-162-10 | pozitív: érvényes burok, aláírás, lánc és egyező digestek → capability kötve a hitelesített identitáshoz, `trust_state = authenticated` |
| AC-162-11 | a #155 viselkedése (aláíratlan és hibás PEM fail-closed) nem romlik |
| AC-162-12 | a stripelt (kanonikus) bájtok eltérése az `executed_wasm_sha256`-tól elutasított akkor is, ha a nyers digest egyezik |
| AC-162-13 | egy tanúsítványban jelen lévő, de `module:sign` jogosultság nélküli kulccsal aláírt burok elutasított (`SIGNER_NOT_AUTHORIZED`) |
| AC-162-14 | a betöltés a hash-elt puffert használja (TOCTOU-teszt: a fájl a hash és a descriptor-építés között cserélve nem juthat be) |
| AC-162-15 | a `metadata.sign` önálló állítás marad (nem szűnik meg); az envelope hiánya vagy hibája nem hallgatja el, és megléte nem pótolja az envelope-ot |

A tesztekhez **nem kell Vault**: egy tesztben generált ECDSA kulcs és tanúsítványlánc elég (a Relay PKI-tesztjei már így működnek, UNVERIFIED a pontos segédfüggvények).

## 5a. A nyers → futtatott WASM transzformáció szerződése (a `CICMODENVv1` része)

**Mért (`core/cabinet/validate.go:28–45`, `module_descriptor.go`):** a transzformáció a wabin `binary.DecodeModule(raw, CoreFeaturesV2)` → `CustomSections = nil` → `binary.EncodeModule`: **dekódolás + custom szekciók elhagyása + újrakódolás**, nem puszta bájt-szintű szekció-eltávolítás. Következmények: (1) az eredmény a **wabin verziójától és a CoreFeatures-től függ**; (2) egy független (pl. Python) producer ezt nem tudja bájtra pontosan reprodukálni a Relay ugyanazon könyvtára nélkül; (3) a függvény egy **cserélhető változó** (`SetStripWasmModuleFunc`, "tesztcélra"), tehát a futtatott bájtok identitása futásidőben módosítható.

**Szerződés (javaslat; a `CICMODENVv1` tartomány része, nem új mező):** a `CICMODENVv1` kimondja a transzformáció **azonosságát**: `wasm-canon/v1` = custom szekciók elhagyása a wabin-alapú újrakódolással, rögzített wabin verzió- és CoreFeatures-értékkel, amelyet a **közös conformance vektorok** (nyers WASM → várt `executed_wasm_sha256`) pinnelnek. Más transzformáció vagy más wabin-viselkedés **csak új envelope-verzióval** (`CICMODENVv2`) lehet érvényes; nincs "eltérő transzformáció, mégis sikeres befogadás". Producer és consumer **ugyanazt a könyvtárat/implementációt** használja (a vektorok bizonyítják); a független producer-implementáció a vektorokon bukik, ha eltér.

**Tulajdonosi döntés-javaslat (2026-11-27, elfogadásra váró; a PoC-ban a jelenlegi transzformáció marad):**

| Kérdés | Döntés |
|---|---|
| `wasm-canon/v1` | a **meglévő** Relay-transzformáció normatív szerződése; nem új kanonizáció |
| wabin-verzió | a Relay ténylegesen feloldott verziója. **Mért (CIC_Relay `86ea1ab`):** `github.com/tetratelabs/wabin v0.0.0-20230304001439-f6f874872834` (`go.mod:13`, `go.sum:60–61`, h1 hash-ek ott); a `go list -m all` ebben a környezetben nem futott (nincs hálózat), a feloldott gráf teljes ellenőrzése **UNVERIFIED**; frissebb verzió nem választandó |
| CoreFeatures | a jelenlegi tényleges konfiguráció: `wasm.CoreFeaturesV2` (`validate.go:33`) |
| bájtszintű szekció-eltávolításra váltás | **nem** a PoC keretében; külön backlog (érinti a `Checksum()`-ot és minden meglévő digestet) |
| `Checksum()` | változatlan; a meglévő artifact-identitások változatlanok |
| `SetStripWasmModuleFunc` | **mért: csak tesztek hívják** (`validate_test.go`), production hívó nincs; a production útvonalon a hitelesített transzformációt nem módosíthatja (kényszerítés: lásd AC-162-18) |
| nyers és transzformált digest | az ellenőrzésük kötelező (V4) |

**Minősítés:** a `wasm-canon/v1` **referencia-implementációhoz kötött** transzformáció. A pinelt wabin, a CoreFeatures és a conformance vektorok **nem** teljes, implementációfüggetlen kanonizációs specifikáció; **független implementálhatóságot nem állítunk**. Egy független producer a vektorokon bukik, ha eltér. A producernek nem kell a teljes Relay-t behúznia: elég egy **szűk, újrahasznosítható transzformációs komponens** (a wabin + a `strip` függvény), **ha** a függőségi vizsgálat ezt alátámasztja (**UNVERIFIED**, a WP-01 része).

**Kötelező ellenpróbák (AC-162-16…19):** (16) a nyers artifact módosítása elutasított; (17) a futtatott reprezentáció eltérése (más transzformáció-kimenet) elutasított; (18) a `SetStripWasmModuleFunc` a production útvonalon nem érhető el (kényszerítés: build tag vagy nem exportált seam, a WP-02 dönti el; tesztelve), és ha mégis megváltoztatná a kimenetet, az `EXECUTED_DIGEST_MISMATCH` elutasít; (19) az ellenőrzés és a példányosítás között az artifact nem cserélhető (lásd AC-162-14).

## 5b. Az öt invariáns (review) és hol teljesül

| Invariáns | Hely |
|---|---|
| az envelope a manifest teljes tartalmát köti | `manifest_digest` = a teljes release-manifest nyers bájtjai (ENV-01); AC-162-02 |
| a kulcsazonosító nem jogosultsági bizonyíték | V2b, AC-162-13 |
| az aláírt tartomány és a kanonikus reprezentáció egyértelmű | a byte-pontos `CICMODENVv1` tartomány (fenti), AC-162-05 |
| a ténylegesen ellenőrzött bájtok kerülnek betöltésre | V4 egyetlen beolvasás, `executed_wasm_sha256`, AC-162-12/14 |
| a runtime capability az ellenőrzött identitáshoz kötődik | V7, AC-162-04 |

## 6. Hatás és kapcsolat

- **D-1:** a #162 lezárása a manifest-deklarált dispatch aktiválásának előfeltétele; a `transitional` kivezetési szabálya a #162 **után** külön rögzítendő.
- **D-10:** a `wasm_sha256` a nyers digest; a `Checksum()` változatlan.
- **Admission (A1):** a modul hitelessége a közös A1 szemantika egy példánya: a `PKIAssets` bizalmi gyökerei a trust bundle anchorjainak felelnek meg (lásd `05-admission-reuse.md`).
- **#156, #158:** nem ennek a csomagnak a tárgya.

## 7. Nyitott [O]/[J]

1. A burok kanonikus formája (közös az admission szerződéssel).
2. ~~A `manifest_digest` pontos tartalma~~ **Lezárva (ENV-01):** a teljes release-manifest nyers bájtjai; nincs YAML–JSON kanonizálás.
3. A `.sig` előállítása a modulrepó release-folyamatában és a `metadata.cicSign` szerepe (a CIC ellenjegyzés fedje-e a burkot).
4. A `transitional` kivezetése.

## 8. Review-korrekciók ENV-01–03 (2026-11-27; normatív, felülírja az előző szakaszok ellentétes szövegét)

**ENV-01 (teljes manifest-kötés).** `manifest_digest` = a teljes betöltött release-manifest fájl nyers bájtjainak sha256-ja; a producer a manifest véglegesítése után készíti és írja alá az envelope-ot. A `metadata.sign` és `metadata.cicSign` meglévő jelentése **nem változik** automatikusan; az utóbbi tényleges lefedettsége **UNVERIFIED**. A korábbi `manifest_artifact_digest` / `manifest_protected_digest` / `manifest_binding` megkülönböztetés a ProofTrace V2-ben megszűnik: a nyers bájtok digestje definíció szerint az egyetlen manifest-identitás.

**ENV-02 (aláírás-formátum).**

| Elem | Szabály |
|---|---|
| algoritmus | az envelope `signer.alg` mezője és az aláírt tartomány `signer_alg=` sora kötelező; megengedett: `ecdsa-p256-sha256` (ECDSA P-256, SHA-256, ASN.1 DER aláírás), `ed25519` (tiszta Ed25519, 64 nyers bájt); más érték elutasított. A `signer.alg` egyezzen a tanúsítvány kulcstípusával (V2) |
| mit ír alá | az aláírt tartomány (`CICMODENVv1…`) bájtjait (ECDSA: a bájtok SHA-256 digestjén; Ed25519: a bájtokon) |
| `.sig` fájl | egyetlen sor: az aláírás RFC 4648 §4 szerinti standard base64-e (kitöltéssel, szóközök nélkül) és LF; más kódolás elutasított |
| `key_id` | `sha256:` + az aláíró tanúsítvány **DER-kódolt SubjectPublicKeyInfo**-jának sha256-ja, kisbetűs hex; a V2 a tanúsítványból újraszámolja |
| **UNVERIFIED** | hogy a tényleges fejlesztői (Vault) kulcs melyik algoritmusú: a WP-01 ezt méri **először**; ha a kulcs más típusú, az engedélyezőlista bővítése **review-pont**, nem csendes döntés |

**ENV-03 (végrehajtási identitás).** A V7 (fent): a capability az `envelope_digest`-hez kötött; a ProofTrace V2 ezt az értéket hordozza. Az `executed_wasm_sha256` benne van a kötött identitásban.

**A transzformáció-szerződés** (5a) változatlan. **Referencia-ellenőrzés:** `validation-report.txt` (aláírt tartomány: 13 eset, kulcssorrend-függetlenség, mező-érzékenység, körút).
