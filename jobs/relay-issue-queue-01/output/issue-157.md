# #157 — `/v1/schema/compile` hitelesítés + bemenet-validáció + route-osztályozó teszt

Alap: `CIC_Relay` `main@d38a1d5`. Ág: `feature/relay-157-compile-auth`; PR: #181, **mergelve** (`c5ae320`, a jóváhagyott HEAD `208d4c3`-on, `--match-head-commit`); az issue lezárva.

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- **Igaz:** a `/v1/schema/compile` hitelesítés nélkül elérhető (`cmd/relay/main.go` régi `newMux`: kilenc közvetlen `mux.HandleFunc`). Az endpoint egy aláírt artifactot állít elő.
- **Igaz, és konkrét hatása van:** a `schema` és `version` mező ellenőrzés nélkül jut a `core/modules/schemacompile/schemacompile.go:217` `fmt.Sprintf` YAML-sablonjába (`name: %s`, `version: %s`), amelynek eredményét a relay aláírja. Az aláírt tartalomba így a mezőkön át YAML-kulcsok kerülhettek.
- **Az issue nem említi:** ugyanezt a workflow-t a `/set` is futtatja tetszőleges payloaddal, ezért a handlerbeli ellenőrzés önmagában kevés; a validációt a nyelőnél is el kellett végezni.
- **Nincs repón belüli hívója** a végpontnak (se szkript, se CI; csak a `docs/*/pipeline/source-provenance.md` említi), így a "fail closed, ha nincs konfigurálva" nem tör meg meglévő folyamatot.

## Mi változott

- `CIC_API_TOKEN`: a hitelesített útvonalak bearer tokenje. Állandó idejű összehasonlítás rögzített hosszú digesteken (a token és a hossza sem szivárog). Nincs konfigurálva = minden kérés 401 (fail closed); 16 karakternél rövidebb token indulási hiba. **mTLS nincs megvalósítva.**
- `schemacompile.ValidateSchemaRef`: szigorú formátum (`schema`: `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`, `version`: `^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$`). A HTTP handlerben 400 `invalid_field`, és ugyanez a nyelőben (`BuildSchema`).
- `apiRoutes`: egyetlen útvonal-tábla, a `newMux` csak ebből regisztrál. Minden útvonal vagy hitelesített, vagy kifejezetten, indoklással publikus. Tesztek: publikus útvonal indoklás nélkül bukik; hitelesített útvonal, amely hitelesítés nélkül elfogad kérést, bukik; ha a `newMux` más módon regisztrál (AST-vizsgálat: pontosan egy `Handle*` hívás), bukik.
- A többi útvonal (`/set`, `/v1/schemas/pipeline`, `/v1/repo/ci`, `/v1/proof/verify`, health/metrics) **publikus marad**, kifejezetten listázva; az issue csak a compile végpontot kéri.

## Hívási út (production, `file:line`)

`cmd/relay/main.go:195` `apiRoutes(s)` → `s.authenticated(...)` (`cmd/relay/api_auth.go`) → `compileHandler` → `schemacompile.ValidateSchemaRef` (`cmd/relay/compile_handler.go:67`) → `cabinet.Setx` → `BuildSchema` → `ValidateSchemaRef` (`schemacompile.go:217`). A token betöltése: `main.go:758` `apiTokenFromEnv`, `:766` `apiToken:`. `deadcode ./...`: nincs találat az új függvényekre.

## "Javítás nélkül bukik" bizonyíték

A régi viselkedés emulálva (a `authenticated` átengedi a kérést, a `ValidateSchemaRef` üres; scratchpad `157-without-fix-summary.txt`). Bukik: `TestCompile_Authentication`, `TestCompile_RejectsMalformedSchemaAndVersion`, `TestAPIRoutes_AreClassified`, `TestValidateSchemaRef`, `TestBuildSchema_RejectsYAMLInjection`. **Nem bukik az emulációban** (karakterizáló / szerkezeti): `TestAPITokenFromEnv` (új függvény), `TestCompileJSONErrorShapeUnchangedForValidRequests`, és `TestNewMux_RegistersOnlyThroughTheRouteTable` (az új `newMux`-ot vizsgálja; a régin, 9 `HandleFunc` hívással, bukna: ezt olvasással állapítottam meg, nem futtattam).

## Helyi kapuk (Docker `golang:1.26.11`)

`gofmt -s -l` üres; `go vet ./...` üres; `staticcheck` (cmd/relay, schemacompile) rc=0; `go test -count=1 ./...` minden csomag `ok`; `go test -race` ok; `symbolsgen` után a `SYMBOLS.md` változatlan, `MANIFEST.sha256` "no drift".

## Review F1 (2026-11-15): autorizáció a közös végrehajtási határon

Az első változat a `/v1/schema/compile` végpontot hitelesítette; a review F1-je szerint az autorizáció a végponthoz kötött, nem a védendő művelethez, a `/set` ugyanazt a workflow-t hitelesítés nélkül elérte. A tulajdonos döntése: az autorizáció a közös végrehajtási határra kerüljön, minden belépési útvonalon ugyanaz a jogosultsági döntés.

- **Megvalósítás:** `cabinet.WithProtectedModules` + `WithPrincipal`/`PrincipalFrom`: a `Setx` minden lépés előtt ellenőrzi, hogy a workflow tartalmaz-e védett komponenst; ha igen és a context-ben nincs hitelesített principal, `ErrUnauthorized` (nincs mellékhatás, korábbi védetlen lépés sem fut). A HTTP-réteg csak a principalt teszi a context-be.
- **Védett komponensek:** `cic.artifact.sign` és a kérésből kapott repót klónozó / make célt futtató modulok (`cic.pipeline.start/test/validate/release`, `cic.repo.build`, `ci.build`). Szándékosan több, mint az aláírás: különben a `/set` láncolhatná ugyanazokat, és megkerülné a végpontok hitelesítését.
- **Útvonalak:** compile, pipeline, repo CI = hitelesített; `/set` = új "opcionális" osztály (anonim: védetlen workflow fut; érvényes token: védett is; jelen lévő érvénytelen token = 401); ismeretlen osztály = hitelesített.
- **További review-pontok:** típushelyes YAML (`renderStubArtifact`; `1.0`, `true`, `1e3` átmegy a regexen, de sablonban nem string), token legalább 8 különböző karakter (sanity check, nem entrópia-bizonyíték), `CIC_API_TOKEN` dokumentálva (en/hu), compose és `tools/relay-ci.sh` frissítve.
- **Commit:** `208d4c3` (a main `8faf00c`-vel igazítva); a PR ezen a HEAD-en, zöld CI-vel mergelve `c5ae320`-ként.
- **Javítás nélkül bukik** (emulálva: a határ-ellenőrzés ki, a régi sablon; scratchpad `157b-without-fix-summary.txt`): a `/set` mindhárom védett workflow-ja anonim hívónak lefut; a határ-teszt, a `Setx` egységteszt és a típus-teszt bukik. A szerződést rögzítő, de a régi kódon is zöld tesztek: `SetStillServesUnprotectedWorkflowsAnonymously`, `UnknownAccessClassFailsClosed`, `ClassifyEveryNativeModule`, `OrdinaryValuesKeepTheFormerBytes`.
- **Viselkedésváltozás:** a pipeline és repo CI útvonalak, és a védett komponenst tartalmazó `/set` workflow-k tokent kérnek; a `make relay.ci` a `CIC_API_TOKEN`-t a környezetéből olvassa.
- **Nem része:** a `ci.build` sorsa (#101), a `/set` teljes hitelesítése, mTLS. Az integrációs mérés a #181-et is tartalmazó állapoton lefutott (`integration-measurement.md`, M10-M12).

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `/set` nem kerülheti meg a védett műveleteket (aláírás, klónozás, build) anonim vagy rossz tokennel | verified | `TestBoundary_SetCannotRunProtectedOperationsAnonymously` (3 workflow); a határ-ellenőrzés nélkül bukik | Valódi cabinet-szolgáltatás, számláló modulokkal, a muxon át | közepes: számláló modulok, nem a valódi aláíró |
| Minden belépési útvonal ugyanazt a döntést kapja | verified | `TestBoundary_EveryEntryPathRefusesAnonymousProtectedWork` (5 útvonal); `..._HandlerWithoutRouteAuth_StillRefusedAtTheBoundary` | Teszt | közepes: a pipeline/repo handler törzse minimális |
| Az ismeretlen útvonal-osztály nem lehet publikus | verified | `TestProtectRoute_UnknownAccessClassFailsClosed` | Teszt | alacsony |
| Minden natív modul osztályozott; elgépelt védett ID nem védhet semmit | verified | `TestProtectedModules_ClassifyEveryNativeModule` | A `registerNativeComponents` valódi modul-listáján | alacsony |
| A YAML-artifact értékei típushelyesek | verified | `TestRenderStubArtifact_*`; a régi sablonnal a `1.0` stb. bukik | Teszt | alacsony |
| A token-entrópia garantált | **cáfolt** | Csak hossz és 8 különböző karakter | Kódolvasás | közepes |
| A `ci.build` védelme helyes döntés | **nem igazolt** | A #101 nyitott | — | közepes |
| A #181 mergelve, az issue lezárva | verified | PR #181 MERGED `c5ae320`; issue #157 CLOSED (`gh`) | GitHub API | alacsony |

## Nyitott kérdések

- **mTLS** nem készült; csak bearer token.
- A többi útvonal hitelesítése külön döntés (README ismert korlát).
- Docs: a `CIC_API_TOKEN` a mergelt állapotban dokumentált (en+hu `relay-container.md`, `docker-compose.yml`, `tools/relay-ci.sh`; ellenőrizve `main@e43f2a8`-on).
- Egy hívó, amely eddig hitelesítés nélkül hívta a végpontot, mostantól 401-et kap, amíg a `CIC_API_TOKEN` nincs beállítva.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A compile végpont hitelesítés nélkül elérhető volt | verified | Régi `newMux` közvetlen regisztráció; `TestCompile_Authentication` javítás nélkül bukik | Kódolvasás + a régi viselkedéssel futtatott teszt | alacsony |
| A `schema`/`version` ellenőrzés nélkül jutott az aláírt YAML-sablonba | verified | `schemacompile.go:217` `fmt.Sprintf`; `TestBuildSchema_RejectsYAMLInjection` javítás nélkül bukik | Kódolvasás + teszt | alacsony |
| Hitelesítés nélkül, rossz vagy hiányzó tokennel 401 | verified | `TestCompile_Authentication` (10 eset) | Teszt a valódi muxon át | alacsony |
| Vezérlőkarakter / formátumon kívüli érték 400 | verified | `TestCompile_RejectsMalformedSchemaAndVersion` (14 eset) | Teszt | alacsony |
| Új útvonal nem kerülhet véletlenül hitelesítés nélkül | verified (részben) | `TestAPIRoutes_AreClassified`, `TestNewMux_RegistersOnlyThroughTheRouteTable` | Teszt + AST-vizsgálat | közepes: más regisztrációs módot (pl. másik mux) az AST-teszt nem lát |
| A token-összehasonlítás nem szivárogtat | verified (olvasat) | `subtle.ConstantTimeCompare` rögzített hosszú sha256 digeseken | Kódolvasás; időmérés nem készült | közepes |
| mTLS | **nem készült** | — | — | közepes |
| A többi útvonal hitelesített | **cáfolt** | Kifejezetten publikusként listázva, indoklással | Kódolvasás | közepes |
