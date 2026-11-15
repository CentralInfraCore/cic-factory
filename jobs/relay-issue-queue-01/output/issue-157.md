# #157 — `/v1/schema/compile` hitelesítés + bemenet-validáció + route-osztályozó teszt

Alap: `CIC_Relay` `main@d38a1d5`. Ág: `feature/relay-157-compile-auth`, helyi commit `fce9d2a` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/181, base `main`).

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

## Nyitott kérdések

- **mTLS** nem készült; csak bearer token.
- A többi útvonal hitelesítése külön döntés (README ismert korlát).
- Docs: a `CIC_API_TOKEN` az env-táblákba nem került (a szomszédos sorokat a #176, #177, #179 is módosítja; merge-konfliktus), follow-up a merge-ek után.
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
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/181 | `gh pr create` kimenet | alacsony |
