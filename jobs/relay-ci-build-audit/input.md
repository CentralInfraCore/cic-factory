# relay-ci-build-audit — mekkora a rés a „repo + commit → build_hash" felé

## Reasoning mód

**audit.** Nem tervezel, nem javasolsz architektúrát, nem írsz kódot.
Azt állapítod meg, ami **van**, és ami **nincs** — bizonyítékkal.

## Kontextus — miért fut ez a job

A cél (orchestrátori döntés, ne vizsgáld felül): a relay legyen egy Docker image,
ami kap egy git repót és egy commit id-t, végigviszi a CI folyamatot, és a kimenete
egy `build_hash`, amit a workflow vagy visszaad, vagy release-folyamatban beleír a
megfelelő fájlba.

Az orchestrátor előzetes felmérése szerint ennek több eleme **már létezik** a relayben.
A te feladatod **nem** az, hogy ezt elhidd, hanem hogy leellenőrizd és megmondd,
**pontosan mekkora a rés**. Egy interfész-spec fog erre épülni — ha te tévedsz, a spec is téved.

## Kemény korlát — a relay READ-ONLY

A `CIC-Relay` külön repo, **amit innen SOHA nem szerkesztünk**
(`cic-module-oracle-cloud/CLAUDE.md:39`). Ez a job **kizárólag olvas**.

- ❌ NE módosíts semmit a `${CIC_RELAY_PATH}` alatt
- ❌ NE hozz létre branchet, NE commitolj a relay repóban
- ❌ NE javasolj konkrét kódváltoztatást — a rés leírása a feladat, nem a betömése

## Forrás — konkrét path-ok

Minden alábbi a `${CIC_RELAY_PATH}` alatt (a relay lokális klónja):

```
core/modules/cibuild/cibuild.go        — a ci.build natív modul
core/modules/cibuild/cibuild.yaml      — a modul séma-leírója
cmd/relay/bootstrap.go:55              — ciBuildFuncs["build"] = cibuild.Execute
cmd/relay/pipeline_handler.go          — POST /v1/schemas/pipeline kezelő
cmd/relay/main.go:195                  — a route bekötése
cmd/relay/proof_verify.go              — ProofArtifact + VerifyProofArtifact
pkg/sourcedigest/                      — forrásfa-hash számítás
tools/sourcehash/main.go               — CLI a forrásfa-hashre
core/cabinet/workflow.yaml             — workflow deklaráció alakja
Dockerfile, docker-compose.yml         — a meglévő konténer
```

KB oldalról a `kb_focus` (meta.yaml) adja a kötelező első olvasást — a relay
végrehajtási modelljének fundamentumai. Ha a `cic-graph` MCP nem elérhető, azt
**írd le az outputban**, és dolgozz forráskódból; ne találd ki a KB tartalmát.

## Státusz-definíció — ellenőrzési módszerrel

Minden megállapításodat ezzel a három státusszal minősítsd:

- **implemented** — a szimbólum létezik ÉS production kódból hívódik.
  Bizonyítás kötelező: `grep -rn "<Név>" --include="*.go" | grep -v "_test.go"`
  és a **hívó fájl:sor** megadása. Ha csak a definíció jön vissza → nem implemented.
- **scaffold** — a kódban van, de bekötetlen VAGY feltételesen megkerült.
  Írd le a megkerülés helyét is (`if X == nil`, `if !Flag`, korai `return`).
- **concept** — dokumentált/deklarált, de nincs futó megfelelője.

Segédeszköz exportált szimbólumokhoz (erősebb a grepnél):
```bash
cd ${CIC_RELAY_PATH} && deadcode ./...   # ha elérhető; ha nem, írd le hogy nem futott
```

## Tiltott rövidítések — ezek NEM fogadhatók el

- **fájl létezése ≠ implemented** — a `cibuild.go` megléte önmagában semmit nem bizonyít
- **teszt zöld ≠ production hívja** — a `cibuild_test.go` nem hívási bizonyíték
- **regisztráció ≠ elérhető út** — a `bootstrap.go:55` regisztráció megmutatja hogy
  betöltődik, de NEM azt, hogy egy tényleges HTTP kérésből eljut odáig a vezérlés
- **exit code 0 ≠ sikeres** — ha bármit futtatsz, a kimenetet olvasd el, ne a kilépési kódot
- **KB leírás ≠ runtime** — amit a KB állít, azt a kódban kell viszontlátni

## Feladat — négy kérdés

### Q1 — Mit csinál ténylegesen a `ci.build` modul?

Olvasd el a `cibuild.go`-t és a `cibuild.yaml`-t. Válaszold meg:
- milyen bemenetet vár és milyen kimenetet ad (mezőnként)
- futtat-e tetszőleges parancsot / make célt, vagy rögzített lépéssort
- honnan veszi a bemeneti hasht és hova írja a kimeneti hasht
- van-e benne konténer- vagy izoláció-kezelés

### Q2 — Meddig jut el a bekötött pipeline út?

Kövesd végig: `main.go:195` → `pipelineHandler` → melyik workflow → melyik modulok
→ hol keletkezik a `ProofArtifact`. Válaszold meg:
- melyik workflow-t hajtja végre (név szerint), és az hol van deklarálva
- ez általános repo-CI út, vagy séma-specifikus (`cic.schemas.pipeline`)
- a `steps[]` mit tartalmaz egy tényleges futásnál (a kódból levezetve)

### Q3 — Tud-e a relay idegen repót + commit id-t fogadni?

Ez a leggyanúsabb pont. A `pipeline_handler.go:87-89` és a `main.go:333-337`
alapján a `source_digest` a relay **saját** forrásfájára számolódik, vagy a relay
build-commitjára esik vissza. Ellenőrizd:
- van-e BÁRMILYEN út, ahol a `source_digest` egy külső repo/commit alapján áll elő
- van-e git-művelet (clone/checkout) bárhol a production kódban
- a `pkg/sourcedigest.ComputeTreeHash` mit kap paraméterként a hívási helyeken

### Q4 — A rés

Ezek után: mi hiányzik ahhoz, hogy „repo URL + commit id be → `build_hash` ki" működjön?
Rés-tételenként: mi van most, mi kellene, és melyik fájlban/rétegben.
**Ne írj megoldást** — a rés leírása a feladat.

## Output

Három fájl, a `jobs/relay-ci-build-audit/output/` alá:

- `output/relay-ci-audit.md` — Q1, Q2, Q3 válaszai. Minden állítás mellé
  `fájl:sor`. Minden státusz-minősítés (implemented/scaffold/concept) mellé a
  konkrét grep parancs ÉS a kimenete idézve.
- `output/gap-analysis.md` — Q4. Táblázat: `Rés | Mi van most (fájl:sor) | Mi kellene | Réteg`
- `output/claim-evidence.md` — claim-evidence tábla pontosan ezekkel az oszlopokkal:

  ```
  | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
  ```

  A **Bizonyíték** oszlop `fájl:sor` vagy idézett parancs-kimenet legyen — nem próza.
  A **Kockázat** oszlopban írd le, ha egy állításban bizonytalan vagy, és miért.

### Reachability artifact — kötelező

Minden `implemented`-nek minősített szimbólumnál az outputban szerepeljen a
**production hívó fájl:sor**, VAGY a `deadcode ./...` kimenete. Ha a `deadcode`
nem elérhető, írd le, és akkor a grep-alapú call site kötelező.

## Amit NE csinálj

- ❌ Ne írj interfész-specet, ne tervezz API-t — az a következő job dolga
- ❌ Ne írd le, hogy „valószínűleg" vagy „feltehetően" — ha nem tudod, az a
  claim-evidence Kockázat oszlopába megy, konkrét megfogalmazással
- ❌ Ne másold be a teljes forrásfájlokat az outputba — idézz sorokat, hivatkozz sorral
- ❌ Ne minősíts semmit `implemented`-nek pusztán azért, mert regisztrálva van
- ❌ Ne módosíts semmit a relay repóban (lásd: kemény korlát)

## Git instrukciók

A cic-factory klónodban dolgozol. Commitolj és pusholj a `feature/relay-ci-build-audit`
branchre. **Main-re NEM.** A relay repóban semmit ne commitolj.

## Nyelvi szabály

Az output dokumentumok **magyarul**. Kódrészletek, parancsok, mezőnevek, fájlnevek angolul.
