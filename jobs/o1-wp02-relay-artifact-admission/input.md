# o1-wp02-relay-artifact-admission — WP-02: a Relay artifact-befogadás (#162): a modul-envelope hitelesítése a betöltő útvonalon

**Függőség:** WP-02: a WP-00 véglegesített vektoraira épül; kezdhető provizórikus vektorokkal (jelölve).

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp02-relay-artifact-admission/ref/`)

- A **normatív szöveg** a `ref/` alatti dokumentumok **korrekciós szakaszai** (01 §8, 02 §7, 03 §12, 04 §9); ahol egy korábbi szakasz ellentmond nekik, a korrekció az irányadó. A wire formátumok **elfogadottak (freeze)**, nem terveződnek újra; új architekturális kérdést csak **konkrét, mért blokkoló** esetén nyiss (a jelentésben, nem csendes döntésként).
- Rögzített alap: **CIC_Relay** `86ea1ab30e1f234ab294e51385f6f51bbff0aff9` (a `main` ágon); **cic-module-oracle-cloud** `ae3c96237839c9fd06649c918a2194a79ebd8cb1` (`devel`). Ellenőrizd, hogy a friss HEAD mennyire tér el, és jegyezd fel; a munkát a rögzített alapra építsd, eltérésnél jelentsd.
- A wire séma-fájlok és példák: `ref/schemas/`, `ref/examples/`; a közös vektorok: `ref/vectors/` (**TESZTKULCSOS, PROVIZÓRIUS**: nem release-aláírások; ne tekintsd normatívnak a `wasm_executed` értéket, lásd WP-00).

## Boot sequence (a KB használata és határai)

1. `mcp__cic-graph__kb_status`: rögzítsd a build idejét és a `stale` jelzőt. Ha nem elérhető: `NOT MEASURED`, folytasd a kódolvasással.
2. `search_nodes` az `axioms`, `symbols`, `contract`, `limits` kifejezésekre (az eredményt akkor is rögzítsd, ha üres).
3. A KB **tájékozódás, nem bizonyíték**: kódállításhoz a forrást olvasd. Minden KB-ból vett állítás a `claim-evidence` táblában külön jelölést kap (`Forrás: KB c#### (file_path)`).

## Forrás: konkrét helyek

A CIC-Relay helyi példánya: `${CIC_RELAY_PATH}` (csak olvasásra, tájékozódáshoz); a munkát a **saját klónodban**, a `workspace/` alatt végezd. A Go-eszközlánc a gépen nem natív: **docker**-en át futtasd (`golang` image; a Relay `go.mod` verziójával), és rögzítsd a pontos parancsot és verziót a jelentésben.

## Tiltott rövidítések: ezek NEM bizonyítékok

- ❌ „a fájl létezik” / „a teszt zöld” / „zöld CI” ≠ implemented · ❌ exit code 0 ≠ sikeres mérés (olvasd a kimenetet) · ❌ százalék a nevező és a parancs nélkül.
- ❌ **Olyan teszt, amely nem tud elbukni.** Minden új negatív tesztről mérd meg bevetett hibával, hogy elbukik-e, **és hogy a megnevezett okból bukik-e**: egy elutasítás csak akkor bizonyíték, ha a várt hibakóddal/üzenettel történik.
- ❌ Teszt, amely a production útvonalat megkerülő segédfüggvényt hajt meg. ❌ A production viselkedés megváltoztatása a teszt kedvéért. ❌ „symbol létezik + teszt zöld” ≠ implemented: **reachability** kell.
- ❌ Provizórikus (vektor/referencia), komponensszintű és production-integrációs bizonyíték összemosása: a jelentésben **külön oszlopban** jelöld.

## Háromszintű státusz és reachability

Minden állítás `implemented` / `scaffold` / `concept`, módszerrel bizonyítva. **Reachability artifact kötelező** minden „bekötött” állításhoz: a production hívási lánc `file:line` formában (`grep -rn "<Szimbólum>" --include="*.go" | grep -v "_test.go"`) **vagy** `deadcode ./...` kimenet; a bizonyítást a kimenetben mutasd.

## Output (kötelező fájlnevek, a `jobs/o1-wp02-relay-artifact-admission/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp02-relay-artifact-admission` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

**Függés:** a WP-00 vektorai véglegesedése után építs rájuk; addig a `ref/vectors` provizórikus. Ha a WP-00 eredménye még nincs a `cic-factory` `main`-jén vagy a Relay-ágon, a **provizórikus vektorokkal** dolgozz, és a jelentésben **jelöld**, melyik bizonyíték provizórikus.

Valósítsd meg a **#162** (CentralInfraCore/CIC_Relay) admission-t a `ref/01-…md` **V1–V7, §4 érintett fájlok, §5 acceptance, §8 ENV-01/02/03, 5a transzformáció-szerződés** szerint:
- a `loadModule` (`cmd/relay/bootstrap.go`) a `registerModuleCapability` **elé** kapja a V1–V6 ellenőrzést; **egyetlen beolvasás**: a hash-elt puffer az, amelyből a descriptor és a manifest-parse épül (nincs második fájlolvasás);
- a `verifyBuildHash` (`cic_flow_manifest.go`) **hívása a betöltő útvonalra kerül** (ma csak tesztből hívott: a hívási-út bizonyíték kötelező);
- `executed_wasm_sha256` a descriptor `WasmCode`-jából; a transzformáció a **meglévő** `stripWasmModuleFunc` (nem módosítod); `Checksum()` **változatlan**;
- az **aláíró jogosultsága** (`module:sign`) nem a kulcs puszta jelenlétéből; az **operátori pinelt trust bundle** (a `PKIAssets` gyökerei) a bizalmi horgony;
- a capability kötése `(module_id, envelope_digest)` (V7, ENV-03); `trust_state` `authenticated`/`transitional`/`dev` (D-1), a dev opt-in csak aláírásfájl nélküli modulra;
- a **`SetStripWasmModuleFunc` production útvonalon nem érhető el** (build tag vagy nem exportált seam; a választást indokold; teszt: a production build nem hívhatja), és ha a kimenet megváltozna, `EXECUTED_DIGEST_MISMATCH` az eredmény;
- a #155 viselkedése (aláíratlan és hibás PEM fail-closed) **nem romlik**.

**Nem része:** a ProofTrace (WP-05); valódi Vault-kulcs; production aktiválás (a #162 acceptance után külön döntés); a transzformáció átdefiniálása (backlog).

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-162-01…03 | más által épített modul érvényes tanúsítvánnyal; manifest az aláírás után módosítva; WASM cserélve: mind elutasított **a megnevezett hibakóddal** |
| AC-162-04 | újrahasznált `moduleID` más digesttel nem örökli a capabilityt |
| AC-162-05…07 | ismeretlen envelope-verzió; `key_id` ≠ SPKI; hiányzó `.sig` prodban `cic-flow`-t importáló modulra |
| AC-162-08, 10, 11 | dev opt-in `trust_state = dev`; pozitív eset; #155 nem romlik |
| AC-162-09 | a `verifyBuildHash` hívási útja `file:line` (nem csak teszt) |
| AC-162-12 | a stripelt bájtok eltérése az `executed_wasm_sha256`-tól elutasított akkor is, ha a nyers digest egyezik |
| AC-162-13 | `module:sign` jogosultság nélküli kulcs elutasított (`SIGNER_NOT_AUTHORIZED`) |
| AC-162-14, 14b | egyetlen beolvasás (TOCTOU-teszt: hash és példányosítás között nem cserélhető); a parse ugyanabból a pufferből |
| AC-162-15 | a `metadata.sign` önálló állítás marad |
| AC-162-16…19 | nyers módosítás, futtatott eltérés, a setter production-elérhetetlensége, TOCTOU |
