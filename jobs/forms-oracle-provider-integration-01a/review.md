# review — forms-oracle-provider-integration-01a

- Reviewer: orchestrátor (Claude Sonnet 5.5), tulajdonosi jóváhagyással a lezárásra
- Dátum: 2026-11-07
- Feature branch: feature/forms-oracle-provider-integration-01a
- Review-zott commit: 22849fa14936077ec7cffd56e3b12872c12ffc75 (szülő: b62f624); a négy végleges output blobjai a remote ágon és a live másolatban azonosak
- run_id: 0b7613d1-da11-46d3-8d9e-b1734ee01aa5 (3. kísérlet, kontrollált `--resume`); az 1. kísérlet 0 tokenes `error` volt, a 2. a fiókhasználati limitbe ütközött (részletek: `ref/run-history.md`)

## Minősítés

**CONDITIONAL GO — partial baseline accepted.** A job adminisztratívan lezárul mint baseline-felmérés. A `done` NEM azt jelenti, hogy a Forms–Oracle integráció elkészült, nem implementációs elfogadás, és nem engedélyezi az 01b-t.

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | GO | a spec K1–K11 szerint validált, két review (CONDITIONAL GO, majd GO); az élő `input.md` a resume alatt nem változott (a resume-hoz a workspace-másolatba került egy hatókör-blokk, lásd `ref/run-history.md`) |
| `tools/validate-output.sh` | GO | az előírt életciklus-helyen (élő `jobs/<id>/output/`), 4 fájl; O5 figyelmeztetés: 46 hivatkozás oldható fel, 275 nem |
| CI | n/a | a job dokumentum-kimenetet termel, kódot nem; a feature branch nem merge-elt a `main`-be |

## Amit ténylegesen ellenőriztem

| Állítás / tárgy | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| A változtathatatlan bemenetek a resume alatt nem változtak | SHA-256 a resume előtt és után (`baseline.md` b66da3e5…, `contract-mapping.md` a876924c…, `agent-output.md`) | azonos, 3/3 |
| Nem történt agent-push; a feature branch a jóváhagyott push előtt nem volt a remoten | `git ls-remote --heads` 0 találat a futás után; a workspace push URL letiltva; push csak a tulajdonos GO-ja után | igazolt |
| A hatókör betartása a resume alatt | a session jsonl tool-hívásainak feldolgozása: csak olvasó `sed`/`grep`/`cat` és egy heredoc-írás outputonként | nem történt docker/go test/mutáció/push; az agent szándékát közvetetten igazolja a „Hatókör világos" sor, a hatókör-blokk közvetlen beolvasása nem kimutatott |
| Hitelesítő-link a futások után | `readlink` a profil `.credentials.json`-ján | változatlan |
| `origin/main` a lezárás előtt | `git fetch` + `rev-parse` | 3060773, nem változott az utolsó ellenőrzés óta |
| NetworkSpace pin-hash | `git cat-file -p 6db77d4:…/network-space.yaml \| sha256sum` | c9a4d14c…3b68 = `corpus/pins.yaml:53` |
| Modul VCN-szerződés | `vcn.json` @3e38886 | 13 config, 19 state, `required: [compartmentId]` |
| Registry 6db77d4..ac567ae változás | `git diff` a kánonikus NetworkSpace-en | egyetlen kozmetikai sor; a correspondence-fájl új |
| `Execute` create-út, `resource_id` követelmény | kódolvasás `module/provider.go:972,1013,1092`, `:667-680` | create-hez nem kell `resource_id`; az execution result nem ad vissza OCID-t |
| Relay op-szókészlet | `core/cabinet/cicwasm.go:277,283,289,295`, `service.go:~229-243` vs `module/abi.go:~36-51` | a 4 és a 8 nem metszi egymást; a Forms-hivatkozás sem a modulban, sem a Relayben nincs |
| `normalizeObserved` production hívója | grep a nem-teszt kódban | 0 hívó; beültetett hiba (a forrás-jelenlét ellenőrzés törlése) mind az 55 tesztet túléli |
| Lefedettség, race, statikus ellenőrzés | `go test -cover` (default és atomic), `-race`, `gofmt`/`vet`/`staticcheck` a builder image-ben | module 82,7%, oci-extract 88,7%, cmd/* 0,0%; race zöld; a három ellenőrzés tiszta |
| Forms licenc | `LICENSE` + SPDX-fejlécek @2f02a75 | Apache-2.0, 69 fejléc, nincs AGPL; a javítás: cic-module-oracle-cloud PR #35 (nyitott) |
| Mintavételes tesztek | `TestRealRegistrySchemas` (registry 6db77d4), `TestNormalizeObservedMatchesTheFixture`, `TestVCNFixtureIsTheVendoredOne`, a registry correspondence-tesztek | 4/4, 9/9, PASS, 40 PASS |
| O5 hivatkozások osztályozása | pinelt commitokra feloldó script a 232 különböző hivatkozásra, sorszám a fájlhosszon belül | 107 teljes útvonal; 109 csak fájlnév, egyetlen jelölt; 9 többértelmű; 7 nem oldható fel úgy, ahogy írva van; 0 fájlon kívüli sor |
| AM-sorok tartalmi mintája | 14 véletlen sor (seed 7) a teljes útvonalú hivatkozást hordozókból | 14/14 releváns sorra mutat, 0 ellentmondás, 3 gyenge (deklarációra mutat: `stores.go:13`, `contracts.go:17`, `provider.go:812`) |

## NOT INDEPENDENTLY VERIFIED (NIV) — elfogadási állításba nem kerülhet

- a `module` csomag sorlefedettsége: az orchestrátor 82,7%-ot mért, az agent 82,9%-ot; az előbbi reprodukált
- a top-level tesztszám: 55 + 7 manuális (orchestrátor) vs 26 + 8 (agent); a számolási szabály nincs kimondva
- a mutációs eredmény (gremlins, 159/217, timeout-érzékeny); újrafuttatása HOLD
- `govulncheck` (a modul tiszta; az `oci-extract`-nál 1 stdlib-lelet, az `os` csomagban, javítva go1.25.8-ban)
- Q3 ágazati lefedettség, Q6 közös vektorok vendorolt másolata, Q9 determinizmus/reprodukálhatósági szonda

## Az O5 korlátai

A feloldható hivatkozás nem egyenlő a bizonyított állítással. 232 különböző `file:line` közül 9 többértelmű (pl. `service.go:18`, `policy.go:143`, `resolve.go:79`, `main.go:640/658`), 7 nem oldható fel úgy, ahogy le van írva: 4 darab `app/module/cicflow_guest.go` (a konténerbeli `module/cicflow_guest.go`), 2 darab `cic-primitive-forms/go/schema.go` (a Forms `go/schema.go`) és 1 Go-stdlib hivatkozás a builder image-ből (nem ellenőrizhető). A 109 csak-fájlnevű hivatkozás környezet nélkül nem egyértelmű. A kimenetek változtathatatlanok, a javítás későbbi revízió dolga.

## Nyitott döntések — az 01b előfeltételei, nem az 01a hiányosságai

- **M2** (`compartmentId` eredete): `PROPOSED / OWNER DECISION REQUIRED`. Javasolt irány: binding (a modul `provider-abi.md:73` design-doksija is ezt mutatja), de az `execBinding` nem hordozza, és nincs bizonyított Relay-oldali feloldás. Kell hozzá a binding tulajdonosa, az érték forrása és a jogosultsági határ; végleges ABI-változtatás nincs elfogadva.
- **R1** (Relay 4 művelet ↔ provider 8 művelet): nyitott, mechanizmus nincs választva. Először tisztázni kell, hogy a Relay `process/get/init/notify` interfésze általános életciklus-interfész-e, amely mögött a provider nyolc művelete diszpécselhető, vagy ABI-szintű bővítés kell. A négy művelet átnevezése nyolcra nem elfogadható megoldás.
- **Kötelező 01b blokkoló teszt:** hiányzó `ipv6CidrBlocks` esetén nem keletkezhet belőle levezetett `isIpv6Enabled=false`; a teszt a production `Observe` útvonalat hajtja meg, nem csak a `normalizeObserved`-et.

## Amit NEM ellenőriztem

- A teljes mutációs mérést, a `govulncheck`-et, a Q3/Q6/Q9 sorokat, az egész `tools/oci-extract` hívási gráfját.
- A 109 csak-fájlnevű és a 9 többértelmű hivatkozást egyenként; a 41 teljes útvonalú AM-sorból 14-et néztem meg tartalmilag, a maradék 27-et és az `AM-run` sorok nagy részét nem futtattam újra.
- A Docker-alapú méréseket az agent környezetében; az enyéim a builder image-ben, eldobható másolaton futottak.
- A licenc-szakasz jogi tartalmát (az Apache-2.0 fájlok CC BY-NC-SA fába kerülhetőségét): tulajdonosi döntés.
- A #35 PR tartalmát a `devel`-ben (nem merge-elt).
- Hogy az agent a hatókör-blokkot a saját olvasatából vette-e át; csak a viselkedése és a saját jelentése támasztja alá.

## Döntés

ELFOGADVA RÉSZLEGES BASELINE-KÉNT (CONDITIONAL GO): a négy output a hash-ekkel rögzített, felhasználható baseline és az 01b tervezési bemenete; a feature branch NEM mergelődik a `main`-be, a #35 merge-e, az 01b indítása és a mutációs újramérés külön tulajdonosi döntés marad.
