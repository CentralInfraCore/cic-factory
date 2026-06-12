# wasm-template-hardening — A wasm/main sablon release-blockereinek és tisztításának elvégzése

## Reasoning mód

**implementation** — a `wasm-template-finish` által felépített `wasm/main` sablon külső review
alapján azonosított hibáinak javítása. **Nem újratervezés** — a meglévő architektúra
(WASM ABI + wazero loadtest + buildHash-signing) marad, a varratokat kell eltüntetni.

## Kontextus

A base-repo `wasm/main` branch (HEAD: `5b231a3`) review-ja megerősített hibákat talált.
A PR #9 (`wasm/main` → `main`) merge-e ezek javításáig vár. A hibák egy része
**release-blocker** (a sablon "bizonyítható, aláírt modul" identitásával ellentétes),
a többi konzisztencia/higiénia.

**Kritikus tanulság, ami ezt a jobot is köti:** az előd 109 zöld tesztje elfedte, hogy a
`_validate_final_project_yaml` soha nem futott le valódi sémával — a teszt mockolta
(`tests/test_tools/test_infra_coverage.py:120`). **Zöld teszt mockolt kódúttal ≠ lefutott
kódút.** Ebben a jobban minden javított útvonalhoz mock nélküli, a valós fájlokkal futó
teszt vagy futtatás-kimenet kell.

## Munkakörnyezet — branch szabály (KÖTELEZŐ)

- base-repo klón a workspace-edbe, majd: **`wasm/f/hardening` branch a `wasm/main`-ből**.
- Minden base-repo commit a `wasm/f/hardening`-re. Push **kizárólag** `wasm/f/hardening`-re.
- PR: `gh pr create --base wasm/main --head wasm/f/hardening` — a PR bázisa a `wasm/main`
  típus-ág, NEM a repo `main`-je.
- A relay host ABI referencia: `CIC-Relay/core/cabinet/cicwasm.go` (klónozd a workspace-be).
- KB-fókusz: `c689` (iSDK contract), `c1503` (modul-release evidence).

## Feladat — javítási sorrend

### A. Release-blockerek

1. **`MANIFEST.sha256` újragenerálás + karbantarthatóság.** Most 14 fájl FAILED, és a
   WASM-fájlok (`module/`, `mk/wasm.mk`, `docs/*/wasm-module-authoring.md`) hiányoznak
   belőle. Generáld újra, ÉS adj `make` targetet (`manifest` + `manifest.verify` vagy
   ekvivalens), a `manifest.verify` kerüljön a CI-be — különben a következő változásnál
   ugyanide jutunk vissza. Döntsd el és dokumentáld: a `module.wasm` bináris benne van-e
   (nem determinisztikus build — ld. C.8 kockázat).
2. **`canonical_source_file` tisztázás.** A `run_validation()` defaultja `sources/index.yaml`,
   a repóban `schemas/index.yaml` van. A `project.yaml` adjon meg explicit
   `canonical_source_file`-t, és a `make validate` fusson zölden a builder konténerben.
   A futtatás-kimenetet idézd.
3. **`_validate_final_project_yaml()` javítás.** A `tools/infra.py:186` `schema["spec"]`-et
   feltételez, de a `project.yaml` szerinti `meta_schema_file` (`md.meta.schema.yaml`)
   top-level kulcsai `type/required/properties` — nincs `spec` kulcs → KeyError a
   finalize-ban. Javítsd úgy, hogy a ténylegesen használt sémafájl-szerkezettel működjön,
   ÉS írj **mock nélküli** tesztet, ami a repó VALÓS `md.meta.schema.yaml`-jával és egy
   valós szerkezetű `project.yaml` instance-szal futtatja végig a validációt (siker- és
   hiba-ággal). A meglévő mockolt tesztek maradhatnak, de nem helyettesítik ezt.

### B. Identitás és szerződés

4. **README identitás.** A `README.md`/`README.hu.md` fő identitása legyen
   "CIC WASM Module Template" — a schema compiler örökség másodlagos szakaszba kerüljön.
5. **Host-load teszt szigorítás** (`module/module_loadtest_test.go`): konkrét assertok —
   `error == null` ÉS `data.status == "ok"` a `get` opra; ismeretlen op → `INPUT` kódú
   error envelope; hibát adó handler → error envelope a megfelelő kóddal;
   `init`/`process`/`notify` null-success szerződés szerint; invalid JSON handler-output
   eset lefedve.
6. **Handler error typing.** A dokumentált kódok (`INPUT | RUNTIME | INTERNAL | RESOURCE |
   TIMEOUT`) most nem érhetők el a handlerből — a dispatcher mindent `RUNTIME`-ként csomagol
   (`module/abi.go`). Vezess be tipizált guest-hibát (pl. error type kóddal), a dispatcher
   ezt képezze le; default továbbra is `RUNTIME`. A doksit (`wasm-module-authoring.md` en+hu)
   igazítsd hozzá.

### C. Tisztítás

7. **`mk/golang.mk` örökség levágása.** `APP_NAME ?= cic-relay`, `golang.build-crt-parser`,
   `golang.build-canonicalize`, relay-specifikus coverage-szabályok (`cabinet: 95, ...`) —
   ami a WASM-sablonban értelmetlen, kerüljön ki vagy explicit "inherited/unused" izolációba.
   A `golang.quality` lánc (fmt-check/vet/lint/vuln a `module/`-ra) változatlanul zöld maradjon.
8. **`project.yaml` cert-higiénia.** A beégetett személyes/CA certificate- és signature-blokkok
   helyett template-placeholder (a séma-validációt túlélő formában). Dokumentáld, hogy éles
   értéket a release folyamat tölt.
9. **CI trigger igazítás.** A `.github/workflows/ci.yml` most csak `main`/`master`-re triggerel —
   a `wasm/main` és `wasm/f/**` push is triggereljen, a `pull_request` bázisok közé kerüljön
   be a `wasm/main`.

## Tiltott rövidítések (kötelező)

- **Zöld teszt mockolt kódúttal ≠ lefutott kódút.** Az A.3 javításhoz mock nélküli teszt
  kötelező; minden "implemented" állításnál jelezd, ha az érintett út csak mockon át fut.
- **A fájl léte ≠ működik.** A `make validate`, `manifest.verify`, `wasm.build`, `wasm.test`,
  `golang.quality`, `check`, `test` targeteket ténylegesen futtasd a builder konténerben,
  és a kimenetet (nem az exit code-ot) idézd — exit code 0 ≠ sikeres.
- **A MANIFEST újragenerálása önmagában ≠ megbízható manifest** — a `manifest.verify`
  CI-bekötése nélkül a drift visszatér; a bekötést grep-pel bizonyítsd.
- Hook-bypass, `--no-verify`, force-push tiltott.

## Reachability — kötelező bizonyíték

- `grep -rn` a kulcs-bekötésekre, a tesztfájlokat kizárva (`grep -v _test.go`):
  a tipizált error használata a dispatcherben (`module/abi.go`), a `manifest.verify` a
  CI-ben (`.github/workflows/ci.yml`), a `canonical_source_file` a `project.yaml`-ban.
- Minden `implemented` állításhoz production hívási hely `file:line` formában, vagy
  futtatás-kimenet a builder konténerből.
- A teljes verifikációs lánc kimenete: `make validate`, `make manifest.verify`,
  `make wasm.build`, `make wasm.test`, `make golang.quality`, `make check`, `make test`.

## Output

- `jobs/wasm-template-hardening/output/wasm-template-hardening-report.md` —
  claim-evidence tábla ezekkel az oszlopokkal:
  `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`
  (Bizonyíték: `file:line` vagy futtatás-kimenet), a review 9 pontja egyenként lefedve,
  a mock nélküli A.3 teszt futtatás-kimenetével.
- base-repo `wasm/f/hardening` pusholva + PR a `wasm/main` bázisra.

## Git instrukciók

- base-repo: commit + push **csak** `wasm/f/hardening`-re; PR bázis: `wasm/main`.
- cic-factory: commit + push **csak** `feature/wasm-template-hardening`-re.
- Main-re (és közvetlenül `wasm/main`-re) sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/f/hardening` branch a `wasm/main`-ből, minden munka ott
- [ ] A.1–A.3 release-blockerek javítva, futtatás-kimenettel igazolva
- [ ] A.3-hoz mock nélküli teszt a valós sémafájlokkal (siker- és hiba-ág)
- [ ] `manifest.verify` a CI-ben (grep-bizonyíték)
- [ ] B.4–B.6 és C.7–C.9 elvégezve vagy explicit indokolva, miért nem
- [ ] teljes verifikációs lánc zöld a builder konténerben, kimenetek idézve
- [ ] PR megnyitva (`wasm/f/hardening` → `wasm/main`)
- [ ] report + claim-evidence tábla a `feature/wasm-template-hardening`-en pusholva

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul** (kivéve a base-repo README/docs, ami en+hu párban él)
- Go/Makefile/shell/YAML, kódon belüli komment, commit message: **angolul**
