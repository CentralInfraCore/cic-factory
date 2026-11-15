# #164 — CRL aláírás és frissesség ellenőrzés

Alap: `CIC_Relay` `main@852594a`. Ág: `feature/relay-164-crl-verification`, helyi commit `08cea68` (pusholva, PR: https://github.com/CentralInfraCore/CIC_Relay/pull/179, base `main`).

## Mit találtam a kódban (állítás-ellenőrzés az issue szövegével szemben)

- **Igaz:** a `checkRevocation` (`core/cabinet/pki_verify.go`) csak a kibocsátó nevét és a sorozatszámot hasonlította; aláírást és `NextUpdate`-et nem ellenőrzött. Az olvashatatlan CRL blokk csak WARN volt és kimaradt (`cmd/relay/bootstrap.go`, régi 661–666. sor). Üres CRL-halmazra nil. Üres pin-halmazra is nil.
- **Az issue nem mondja, de a kódban így van — ez a legfontosabb lelet:** `prod` módban **soha nem töltődött be CRL**. A `bootstrapPKI` prod ága `CRLs: []`-t állított, és a `CIC_PLATFORM_CA_BUNDLE`-ből csak tanúsítványokat olvasott (`AppendCertsFromPEM`). A revokáció tehát mindkét módban gyakorlatilag inert volt (dev: az ágyazott könyvtárban nincs CRL). Ezt a javítás nélküli futás is igazolja: a "visszavont levél újraindítás után is elutasított" teszt a régi prod úton azért bukik, mert nincs betöltött CRL.
- **Az SPKI-pin konfigurációnak nincs forrása:** a `PinnedSPKIs` sehol nincs kitöltve éles kódban (`grep`: csak a `VerifyOptions` mező és a teszt). A pin tehát nem "üres alapértelmezés", hanem bekötetlen.

## Mi változott

- `cabinet.VerifyCRLSignature`: a CRL-nek egy a trust store-beli CA tanúsítvánnyal kell hitelesülnie (kibocsátó-név egyezés + `CheckSignatureFrom`). Aki nem hitelesül, **minden módban** eldobódik, a bejegyzései nem használhatók.
- `cabinet.CRLFreshness` + `VerifyOptions.CRLFreshness` + `CheckCRLFresh`: a `NextUpdate` utáni (vagy `NextUpdate` nélküli) CRL-t a **hitelesítéskor** utasítja el, ha a szabály be van állítva. Ez azért fontos, mert a relay futás közben is hitelesít (`certVerify`): a betöltés után elavult CRL megbízhatatlanná válik. A `nil` szabály a régi viselkedést adja (dev).
- `prod`: a CRL-ek `X509 CRL` blokkokként a `CIC_PLATFORM_CA_BUNDLE`-ben utaznak; olvashatatlan, nem hitelesített vagy elavult CRL **indulási hiba**. `CIC_CRL_MAX_STALENESS` explicit türelmi idő (alapértelmezés: nincs; érvénytelen érték indulási hiba).
- `dev` lenient: rossz aláírás → WARN + eldobás; olvashatatlan vagy elavult → WARN.
- `prod` kimondja, mi nincs bekapcsolva: "nincs CRL a bundle-ben" és "az SPKI-pin halmaz üres" WARN.
- A frissességi szabály a három `VerifyOptions` helyen átadódik (`bootstrap.go:78`, `:554`, `pki_companion.go:78`).

## Explicit kibocsátó-policy (2026-11-15, a tulajdonosi döntés nyomán: fail-closed + explicit issuer policy)

A korábbi "hiányzó CRL" határjelzés feloldva. Prodban a `CIC_CRL_REQUIRED_ISSUERS` **kötelezően deklarálandó**: `none` (explicit: egy kibocsátó sem követel CRL-t, WARN), `all` (a bundle minden CA tanúsítványa) vagy CA-tanúsítvány SHA-256 ujjlenyomatok vesszős listája. Beállítatlan = indulási hiba. Egy követelt kibocsátóhoz a bundle-ben kell egy **pontosan tőle származó**, hiteles és friss CRL; az érvényes, de üres CRL megfelel. Hiányzó CRL, lejárt, hibás aláírású és idegen kibocsátótól származó CRL = indulási hiba; a bundle egyetlen CA-jára sem illeszkedő ujjlenyomat is hiba (az elírás ne ejtsen el követelményt). A dev lenient marad és figyelmen kívül hagyja a beállítást (tesztelt eltérés).

Commit `2437a5f` ugyanazon az ágon (`feature/relay-164-crl-verification`, a #179 ága), pusholva; a PR-leírás frissítve. Javítás nélkül (emulálva: a deklaráció nem kötelező, a kikényszerítés üres; scratchpad `164b-without-fix-summary.txt`) bukik: `IssuerPolicyMustBeDeclared`, a táblázat `required, missing`, `required (all), missing`, `declared fingerprint matches no CA` sora. A lejárt / hibás aláírású / idegen kibocsátós sorok az emulációban is zöldek, mert azokat a #179 korábbi rétege tartja.

Viselkedésváltozás: egy prod relay, amely eddig CIC_CRL_REQUIRED_ISSUERS nélkül indult volna, mostantól nem indul, amíg a policy deklarálva nincs.

Továbbra sincs: SPKI-pin forrás (külön döntés).

## Hívási út (production, `file:line`)

`cmd/relay/main.go:694` `bootstrapPKI` → prod ág → `parseBundleCRLs` / `acceptCRLs` (`cmd/relay/pki_crl.go`) → `cabinet.VerifyCRLSignature` / `CheckCRLFresh`. Hitelesítés: `cmd/relay/bootstrap.go:78` és `:554` (`CRLFreshness: pkiAssets.CRLFreshness`), `cmd/relay/pki_companion.go:78` → `cabinet.VerifyCertificateChain` → `checkRevocation` → `CheckCRLFresh`. `deadcode ./...`: nincs találat az új függvényekre.

## "Javítás nélkül bukik" bizonyíték

A régi viselkedés az új API alá emulálva (aláírás- és frissesség-ellenőrzés kikapcsolva, a prod ág a régi módon nem tölt CRL-t; scratchpad `164-without-fix-summary.txt`). Bukik: `TestBootstrapPKI_Prod_CRL_ForeignKeySignature_Error`, `TestLoadPKIAssets_Dev_CRL_ForeignKeySignature_NotUsed`, `TestBootstrapPKI_Prod_CRL_UnknownIssuer_Error`, `TestBootstrapPKI_Prod_CRL_Stale_Error`, `TestBootstrapPKI_Prod_InvalidTolerance_Error`, `TestBootstrapPKI_Prod_CRL_Unparsable_Error`, `TestBootstrapPKI_Prod_RevokedLeafStaysRejectedAfterRestart`, `TestBootstrapPKI_Prod_NoCRL_NoPins_AreVisible`, `TestVerifyCRLSignature`, `TestCheckCRLFresh`, `TestVerifyCertificateChain_StaleCRL`. **Nem bukik** (karakterizáló): `TestCrlToleranceFromEnv` (új függvény).

## Helyi kapuk (Docker `golang:1.26.11`)

`gofmt -s -l` üres; `go vet ./...` üres; `staticcheck` (cabinet, cmd/relay) rc=0; `go test -count=1 ./...` minden csomag `ok`; `symbolsgen` lefuttatva (3 új szimbólum), `MANIFEST.sha256` újragenerálva és a CI-lépéssel azonos `diff`: "no drift".

## Nyitott kérdések

- A "hiányzó CRL" szemantika (fent) tulajdonosi döntés.
- **Merge-sorrend:** a #177 és a #164 is módosítja a `context/SYMBOLS.md`-t és a `MANIFEST.sha256` SYMBOLS-sorát; a második merge után a kettő újragenerálása kell (nem kézi összefésülés).
- A prod bundle mostantól CRL-blokkokat is tartalmazhat, de a meglévő bundle-ök CRL nélkül változatlanul indulnak (csak WARN).

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A CRL aláírását és frissességét semmi nem ellenőrizte | verified | `pki_verify.go` régi `checkRevocation`; a javítás nélküli emulációban `TestVerifyCRLSignature`, `TestCheckCRLFresh` bukik | Kódolvasás + a régi viselkedéssel futtatott teszt | alacsony |
| Prod módban sosem töltődött be CRL | verified | Régi `pki_bootstrap.go` prod ág `CRLs: []`; `TestBootstrapPKI_Prod_RevokedLeafStaysRejectedAfterRestart` javítás nélkül bukik (0 CRL) | Kódolvasás + teszt | alacsony |
| Idegen kulccsal aláírt CRL bejegyzései nem használhatók | verified | `TestLoadPKIAssets_Dev_CRL_ForeignKeySignature_NotUsed` (a hamis CRL nem tudja visszavonni a levelet); prod: `..._ForeignKeySignature_Error` | Teszt | alacsony |
| Elavult CRL prod-ban hiba, explicit türelmi idővel engedhető | verified | `TestBootstrapPKI_Prod_CRL_Stale_Error` (`""` → hiba, `3h` → siker) | Teszt | közepes: a türelmi idő üzemeltetői döntés |
| Olvashatatlan CRL prod-ban indulási hiba | verified | `TestBootstrapPKI_Prod_CRL_Unparsable_Error` | Teszt | alacsony |
| Visszavont levél újraindítás után is elutasított | verified | `TestBootstrapPKI_Prod_RevokedLeafStaysRejectedAfterRestart` (két egymás utáni induláson) | Teszt (a "restart" a bundle újraolvasása, nem folyamat-újraindítás) | közepes |
| Futás közben elavuló CRL megbízhatatlanná válik | verified | `TestVerifyCertificateChain_StaleCRL` (ugyanaz a CRL két órával később elutasított) | Teszt, injektált órával | közepes: `main()` nem futott |
| Hiányzó / lejárt / hibás aláírású / idegen kibocsátós CRL egy követelt kibocsátóra prodban hiba | verified | `TestBootstrapPKI_Prod_IssuerPolicy_Table` (11 sor); hiányzó sor és deklarálatlan policy a policy nélkül bukik | Teszt a valódi `bootstrapPKI`-n át | közepes: új kötelező env változó |
| SPKI-pin forrás létezik | **cáfolt** | `PinnedSPKIs` sehol nincs kitöltve éles kódban | `grep -rn PinnedSPKIs` | közepes |
| A PR nyitva van | verified | https://github.com/CentralInfraCore/CIC_Relay/pull/179 | `gh pr create` kimenet | alacsony |
