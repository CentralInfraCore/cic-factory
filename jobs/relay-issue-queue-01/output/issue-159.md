# #159 — `CIC_TRUST_MODE` nincs default, `prod`-ban üres/betöltetlen trust store hiba

Alap: `CIC_Relay` `main@852594a`. Ág: `feature/relay-159-trust-mode-explicit`, helyi commit `a01d7d7` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/176, base `main`).

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- **"Nincs default" (1. pont): igaz volt.** `cmd/relay/pki_bootstrap.go` `resolveTrustMode` üres értékre `dev`-et adott WARN-nal; hívó: `cmd/relay/main.go:693`.
- **"`prod`-ban üres trust store néma kihagyás" (2. pont): részben elavult.** A `bootstrapPKI` `prod` ága már hibát ad `CIC_PLATFORM_CA_BUNDLE` nélkül, olvashatatlan úton és érvényes tanúsítvány nélküli bundle-re (`pki_bootstrap.go`, ROADMAP B3/p59 "Done"); három teszt fedi (`pki_bootstrap_test.go`). A `prod` ág `TrustStoreLoaded: true`-t ad, így a `bootstrap.go:538` néma kihagyása `prod`-ban ma nem érhető el.
- A néma kihagyás (`bootstrap.go:538`, `:71`) módfüggetlen: ha később valaki betöltetlen store-t ad át `prod`-ban, nincs védőháló. Ezt zártam be.
- Az issue "a compose is `dev`-et állít" állítása igaz (`docker-compose.yml:228`, `${CIC_TRUST_MODE:-dev}`). Ezt **nem** változtattam: a compose dev-only, expliciten adja át az értéket, és a `make relay.up`/`relay.ci` ezen megy; a megváltoztatása a CI-szál hatókörébe lógna.

## Mi változott

- `resolveTrustMode()` hibát ad hiányzó, üres vagy csak szóközből álló értékre; nincs default.
- Új `requireTrustStore`: `prod` + betöltetlen/nil store → hiba.
- Új `bootstrapTrust`: egyetlen indulási belépő (mód → store → védőháló); `main.go` ezt hívja, hiba esetén `Fatal`.
- Docs (README, `docs/{hu,en}/pipeline/relay-container.md`, `embedded/pki/README.md`, compose-komment) már nem állítanak `dev` defaultot.
- **Következmény:** a `Dockerfile.relay` image közvetlen `docker run`-ja `CIC_TRUST_MODE` nélkül mostantól indulási hibával áll meg. A compose-on át indítás (`make relay.up`) nem érintett.

## Hívási út (production, `file:line`)

`cmd/relay/main.go:693` `bootstrapTrust` → `cmd/relay/pki_bootstrap.go` `resolveTrustMode` → `bootstrapPKI` → `requireTrustStore`; hiba → `main.go:695` `Fatal`. `deadcode ./...`: nincs `pki_bootstrap`/`bootstrapTrust`/`requireTrustStore`/`resolveTrustMode` találat.

## "Javítás nélkül bukik" bizonyíték

A régi viselkedést (dev default, no-op védőháló) az új API alá ideiglenesen visszaállítva (scratchpad `159-without-fix-summary.txt`):

```
--- FAIL: TestResolveTrustMode_Empty_Error
--- FAIL: TestResolveTrustMode_Unset_Error
--- FAIL: TestBootstrapTrust_Unset_Error
--- FAIL: TestRequireTrustStore
--- PASS: TestBootstrapTrust_Prod_EmptyBundle_Error   (a régi kód is hibát ad)
```

A `TestBootstrapTrust_Prod_EmptyBundle_Error` **karakterizáló teszt**, nem védelem-bizonyíték: a viselkedés a javítás nélkül is megvan, ezért nem bukik. A `TestRequireTrustStore` a no-op védőhálóval bukik; `bootstrapPKI` miatt `bootstrapTrust`-on át `prod`+betöltetlen állapot nem állítható elő, ezért a védőháló közvetlen teszttel fedett.

## Helyi kapuk (Docker `golang:1.26.11`)

`gofmt -s -l` üres; `go vet ./...` üres; `staticcheck ./cmd/relay/` rc=0; `go test -count=1 ./...` minden csomag `ok` (köztük `TestEmbeddedTrustHasNoRepoKnownPrivateKey`, változatlanul); `symbolsgen` után `git diff context/SYMBOLS.md` üres.

## Nyitott kérdések

- Az issue "prod-ban üres/betöltetlen store → hiba" pontját a kód részben már teljesítette; a PR a védőhálót és a default eltávolítását adja.
- `dev` módban betöltetlen store (az ágyazott könyvtárban nincs gyökér-CA) továbbra is néma kihagyás; az issue ezt nem kéri, nem változtattam.

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `resolveTrustMode` üres értékre `dev`-re esett vissza | verified | Régi `pki_bootstrap.go:20-30`; a javítás nélküli futásban `TestResolveTrustMode_Empty_Error` bukik | Kódolvasás + a régi viselkedéssel futtatott teszt | alacsony |
| A `prod` ág üres/hiányzó bundle-re már hibát ad | verified | `pki_bootstrap.go` `TrustModeProd` ág; `TestBootstrapPKI_ProdMode_NoBundleEnv_Error`, `TestBootstrapTrust_Prod_EmptyBundle_Error` zöld javítás nélkül is | Kódolvasás + teszt | alacsony |
| A hiányzó mód indulási hibát okoz az éles úton | verified | `main.go:693` `bootstrapTrust` → `Fatal`; `TestBootstrapTrust_Unset_Error` | Teszt + hívási út | közepes: a `main()` maga nincs futtatva, a hívó `Fatal` ága nem tesztelt |
| `prod` + betöltetlen store nem juthat tovább | verified (közvetlen teszt) | `TestRequireTrustStore`; javítás nélkül bukik | Teszt | alacsony: a `bootstrapPKI` ma amúgy sem engedi |
| A compose `dev`-et ad át, ezt nem változtattam | verified | `docker-compose.yml:228` | Fájlolvasás | közepes: dev-only fájl, a default nélküli binárist expliciten kell indítani |
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/176 | `gh pr create` kimenet | alacsony |
