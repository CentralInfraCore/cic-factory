# #166 — ágyazott modulok a közös `pkiAssets`-en (A változat: megvalósítva, PR push-ra vár)

Alap: `CIC_Relay` `main@852594a`. Kód- és doksiváltozás **nincs**, ág/PR nincs.

## Miért álltam meg

Az input.md szerint: ha az "ágyazott modul = konstrukciósan megbízott?" döntés nem olvasható ki a kódból és a dokumentumokból, megállok és kérdezek.

- A kód nem dönti el. `cmd/relay/embedded.go:7` az `embedded/pki` könyvtárat "dev trust anchor"-ként írja le, nem a modulok bizalmi alapjaként.
- A dokumentumok sem. `features/feature-011-oci-provider/r3-plan.md` kimondja, hogy az ágyazott dev CA és a modul-sidecar `.pem` **nem** a tervezett modul-bizalom a `cic-flow`-hoz; "konstrukciósan megbízott ágyazott modul" szándéknyilatkozatot a repóban nem találtam (`grep` "by construction|trusted by construction|embedded module" a `.md`/`.go` fájlokon).
- Az issue saját 2. javaslata feltételes ("ha megbízott…"), az 1. javaslat és a két acceptance pont viszont a közös `pkiAssets`-et feltételezi (paritás az embedded és az installed út között). A kettő nem egyszerre teljesíthető: ha az ágyazott modul megbízott konstrukció szerint, a "prod-ban az ágyazott CA-val aláírt modul elutasított mindkét úton" pont nem érvényes.

## Mit találtam a kódban (az issue szövegével szemben)

- **Igaz:** a `loadEmbeddedComponents` (`bootstrap.go:360`) saját `loadPKIAssets(pki, pkiPath)`-ot épít (`bootstrap.go:361`), nem kapja meg a `main.go:693` `bootstrapTrust` által adott objektumot; hívó: `main.go:730`. A `loadProvenanceAnchors` (`main.go:705`) csak a megosztott objektumra tölt, így az ágyazott út `verifyCICFlowProvenance`-e ("anchor not loaded", `pki_companion.go:70`) mindig elutasítana.
- **Az issue előfeltétele ma nem teljesül:** az `embedded/schemas` és `embedded/workflows` fájljai közt **nincs `kind: Module`** (`grep '^kind:'`: 3 Schema, 3 Workflow). A `loadModule` az ágyazott úton ma nem fut; a kétféle trust-kontextus eltérése tehát jelenleg nem hat egyetlen betöltött elemre sem. A `main.go:657` komment ("loadEmbeddedComponents populates cicFlowReg") ma nem igaz állítás az ágyazott fára.
- A hiba tehát **látens**: akkor válik ténylegessé, ha valaki ágyazott modult ad a binárishoz.

## A döntés, amire szükség van

Az ágyazott modulokra (ha lesznek) melyik a szándék?

- **A) Nem megbízottak konstrukció szerint:** ugyanazon a közös `pkiAssets`-en ellenőrzöttek, mint a telepítettek. Következmény: a `loadEmbeddedComponents` megkapja a `pkiAssets`-et (`main.go:730` + aláírás), a saját `loadPKIAssets` megszűnik; `prod`-ban a dev CA-val aláírt ágyazott modul elutasított, és mivel `failOnError=true`, a relay nem indul el. Az issue mindkét acceptance pontja ezt igényli.
- **B) Konstrukció szerint megbízottak** (a binárissal együtt aláírt tartalom): a kódban kimondott és tesztelt kivétel kell (nincs második trust store, nincs lánc-ellenőrzés), és a `cic-flow` capability az ágyazottaknak explicit szabállyal adott/megtagadott.

Ha az A: a változtatás kicsi és ma viselkedésváltozás nélküli (nincs ágyazott modul), a paritás-teszt szintetikus ágyazott modullal írható. Ha a B: más a teszt és más a PR-cím.

## Nyitott kérdések

- A / B döntés (tulajdonosi).
- A `main.go:657` komment javítandó, bármelyik döntés esetén.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `loadEmbeddedComponents` saját trust store-t épít | verified | `bootstrap.go:361`; hívó `main.go:730` nem ad át `pkiAssets`-et | Kódolvasás | alacsony |
| A provenance-horgonyok nem érik el az ágyazott utat | verified (olvasat) | `main.go:705` a megosztott objektumra tölt; `pki_companion.go:70` fail-closed | Kódolvasás, futtatás nélkül | közepes |
| Ma van ágyazott `kind: Module` | **cáfolt** | `grep '^kind:' cmd/relay/embedded/*/*.yaml`: 3 Schema + 3 Workflow, Module 0 | Parancskimenet | alacsony |
| A "megbízott-e az ágyazott modul" döntés a kódból/doksiból kiolvasható | **cáfolt** | `embedded.go:7` ("dev trust anchor"), `r3-plan.md` ellentmond a modul-bizalomnak; szándéknyilatkozat nincs | Kódolvasás + grep | — |
| (a stop-jelentés idején; a döntés után megvalósítva és tesztelve, lásd a "Döntés és megvalósítás" szakaszt) A prod-ban "csak ágyazott CA-val aláírt modul elutasított mindkét úton" | **nem igazolt** | Nincs ágyazott modul, amivel kipróbálható; a döntés (A/B) előfeltétel | — | magas |


## Döntés és megvalósítás (2026-11-15)

A tulajdonos oldali döntési javaslat (a beillesztett külső review nyomán, kérésként kezelve) az **A** változat: az ágyazott és a telepített komponensekre azonos bizalmi és ellenőrzési szabályok vonatkoznak; a beágyazottság önmagában nem ad többletjogosultságot; az eredet, a hitelesség és a jogosultság külön ellenőrzendő.

- `loadEmbeddedComponents` (`cmd/relay/bootstrap.go`) a közös `pkiAssets`-et kapja (mint a `loadInstalledComponents`); a saját `loadPKIAssets(embedded/pki)` megszűnt. Nil trust context hiba. Hívó: `cmd/relay/main.go:732`.
- Ma nincs ágyazott modul, így a ma betöltődő elemek viselkedése nem változik; a különbség az első ágyazott modulnál jelentkezik: prodban az operátor bundle-jén kívüli CA-val aláírt ágyazott modul elutasított, és az ágyazott modul is megkapja a provenance-horgonyokat (capability-kötés).
- Commit `faa83a4`, ág `feature/relay-166-shared-trust-context`, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/182 (base `main`).
- **Javítás nélkül bukik** (a régi, saját trust store-t építő loader emulálva; scratchpad `166-without-fix-summary.txt`): `TestEmbeddedAndInstalled_SameVerdictAndCapability/valid_signer` és `TestProd_..._RejectedOnBothPaths/signed_by_the_operator's_CA`. **Nem bukik** az emulációban: a két elutasítási eset (a beágyazott fejlesztői CA-k eleve nem a teszt-CA-k), ezért ezek a szerződést rögzítik, nem védelem-bizonyítékok.
- Kapuk: `gofmt`, `go vet`, `staticcheck`, `go test ./...`, `-race` tiszta; `SYMBOLS.md` és manifest változatlan.
- Nyitva: a "garbage signature file" eset ma mindkét úton betöltődik (lenient betöltés); ennek szigorítása a #155 prod fail-closed része.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az ágyazott út ugyanazt az ítéletet és capability-t adja, mint a telepített | verified | `TestEmbeddedAndInstalled_SameVerdictAndCapability` (4 eset); a valid-signer eset a régi loaderrel bukik | Teszt, azonos modulfájlokkal mindkét loaderen | közepes: ma nincs valódi ágyazott modul |
| Prodban az operátor bundle-jén kívüli CA-val aláírt modul mindkét úton elutasított | verified (szerződés) | `TestProd_ModuleSignedOutsideOperatorBundle_RejectedOnBothPaths` | Teszt; az emulációban is zöld (nem védelem-bizonyíték) | közepes |
| Az operátor CA-ja által aláírt modul mindkét úton elfogadott és megkapja a capability-t | verified | ugyanott, "signed by the operator's CA"; a régi loaderrel bukik | Teszt | alacsony |
| Az ágyazott fában ma nincs modul | verified | `grep '^kind:'`: 3 Schema, 3 Workflow | Parancskimenet | alacsony |
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/182 | `gh pr create` kimenet | alacsony |
