# o1-wp04-sign-send — WP-04: a `cic-flow.send` host-képesség, a host-oldali célvalidálás, a host-interakció rekord és az Oracle guest migrációja

**Függőség:** WP-04: azonnal indítható; a rekord-interfész a WP-05 bemenete.

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp04-sign-send/ref/`)

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

## Output (kötelező fájlnevek, a `jobs/o1-wp04-sign-send/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp04-sign-send` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

A `ref/03-…md` (**§3–§8, §12 SS-01–05 normatív**) és az ADR-tervezet szerint, **két repóban** (Relay + modul), mindkettőn külön feature-branch és draft PR:

**Relay:** új host-import **`cic-flow.send`** az **egységes ABI-val** (`(req_ptr, req_len, out_ptr, out_len) → i32`, JSON); a host lépései **kényszerített sorrendben**: séma-validálás → **policy/célvalidálás aláírás ELŐTT** (SS-03: a `ref/` `validate_target` hat lépése, hibakódok `POLICY_*`) → kanonikus karakterlánc a signing profile-lal → Vault-aláírás (**itt is: teszt-kulcs / mock, valódi Vault-aláírás nem**) → kontrollált HTTP (a manifest ∩ policy egress; **redirect másik hostra nem követhető**) → **host-interakció rekord** (SS-04, wire: `ref/schemas/host-interaction-record`, lista-digest `CICHOSTINTv1`) → válasz a guestnek (**aláírás vagy `Authorization` soha**; SS-02 válaszfejléc-allowlist, operátori; SS-05 limitek operátori felső korlátja, a guest kérés limitet nem hordozhat). A provider-specifikus signing profile **elkülönített Go csomag** (D-11: `pkg/hostsign` varrat + `pkg/hostsign/ociprofile`; **függőségi teszt:** a `core/...` és a `pkg/hostsign` nem importálja az `ociprofile`-t, az `ociprofile` nem importál `core/...`-t).

**Modul (Oracle):** az `actuateSigned` a kanonikus karakterlánc és az `Authorization` összeállítása helyett a **strukturált kérést** küldi (`method`, `host`, `path`, `intent{operation, resource_id, binding_digest}`, törzs); az `abi.imports` a `cic-flow.send`-et tartalmazza, a `sign`/`actuate` kikerül. A megfigyelési profilban a guest **írási** kérést nem tud kijuttatni.

**Nem része:** a ProofTrace-be írás részletei (a host-interakció rekord a WP-05 bemenete: a közös interfészt itt a schema rögzíti, a Cabinet-oldali bekötés WP-05); valódi Vault-aláírás, countersign, production aktiválás.

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-SS-01 | a host-függvény válasza **nem** tartalmaz aláírást vagy `Authorization` fejlécet (válasz-séma + teszt) |
| AC-SS-02 | tiltott kérés-fejléc `HEADER_FORBIDDEN`, **aláírás nélkül** (a Vault-mock hívásszámlálója 0) |
| AC-SS-03 | a policyn kívüli host/útvonal/módszer/cél/binding **aláírás előtt** elutasított, a megnevezett `POLICY_*` kóddal; 10 referencia-eset |
| AC-SS-04 | a `date` a host órájából jön; a guest által adott elutasított |
| AC-SS-05 | a megtagadott és a sikertelen hívás **host-interakció rekordot** kap (`denied`/`failed`) |
| AC-SS-06 | megfigyelési profilban a guest írási kérést nem tud kijuttatni (a kimenő kéréseken kényszerítve) |
| AC-SS-07 | függőségi teszt: a Relay mag nem importálja a provider-profilt |
| AC-SS-08 | a signing profile azonossága és digestje a host-interakció rekordban |
| AC-SS-09 | a rekord-lista digest a közös vektorokon azonos; seq-hézag/sorrendcsere elutasított |
