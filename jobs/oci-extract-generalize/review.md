# review — oci-extract-generalize

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-03T13:20:00Z
- Feature branch: `feature/oci-extract-generalize` (két repóban)
- Review-zott commitok: modul-repo `5c1e035`, cic-factory `502d623`

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | **GO** | két javítás után (K4 output-fájlnév, K8 claim-evidence oszlopok) |
| `tools/validate-output.sh` | **GO** | 4 fájl, egy WARN: 11 `file:line` nem oldható fel — a `tools/env.sh`-ban nincs path a modul-repóhoz. Ezeket kézzel ellenőriztem, lásd lent |
| CI (modul-repo) | **zöld** | `headSha: 5c1e0354dfc1a37aeeded15f078e4913f51de749` — **egyeztetve**: azonos a `5c1e035` modul-committal, ami a branch HEAD-je. Nem „van zöld futás", hanem ez a commit zöld |

**Figyelmeztetés a saját eljárásomról:** az első `validate-output.sh` futtatásom
tévedésből az agent klónjára ment (a shell munkakönyvtára egy korábbi `cd` után a
klónban maradt). A fenti GO a **live workdirben**, a branchről áthozott
fájlokon mért eredmény. Ugyanez a hiba észrevétlenül „jó az anyag" ítéletet
adhatott volna a klón alapján — pont az, amit a `/job-close` tilt.

## Amit ténylegesen ellenőriztem

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| A1 törés helye: `client.go:182` | `git show 6331e76:tools/oci-extract/client.go \| sed -n '182p'` | `return req, resp, req != "" && resp != ""` — **pontos egyezés** |
| A1 törés helye: `client.go:118` | ugyanaz, `118p` | `if !ok \|\| sel.Sel.Name != "HTTPRequest" \|\| len(call.Args) < 2 {` — **pontos egyezés** |
| A2 törés helye: `schema.go:38` | `git show 6331e76:tools/oci-extract/schema.go \| sed -n '38p'` | `create := byName["Create"+resource+"Details"]` — **pontos egyezés** |
| A2 törés helye: `policy.go:139` | ugyanaz, `139p` | `byName["Create"+resource+"Details"],` — **pontos egyezés** |
| „8047 `request.HTTPRequest`" | `grep -rho "request.HTTPRequest(" $(find $SDK -name '*_client.go' -not -path '*/common/*') \| wc -l` | **8047** — egyezik |
| „egyetlen `common.MakeDefaultHTTPRequest` szolgáltatás-kliensben" | `grep -rn "common.MakeDefaultHTTPRequest(" <318 service client>` | **1 találat**, `identity/identity_client.go:6816` — a sorszám is egyezik |
| „8048 a valós nevező" | 8047 + 1, a fenti két független mérésből | aritmetikailag konzisztens |
| A commit nem vitte be a T10-es `.yaml` sidecarokat | `git status --short` a modul-klónban | 11 untracked `.yaml` maradt, **egyik sincs a commitban** — explicit path-listás `git add` |
| Nincs be nem commitolt követett változás | `git status --short \| grep -v '^??'` | üres |

Egy pontatlanságot találtam, ami **nem** befolyásol számot: az output „319
kliensfájl"-t ír a mérés hatóköreként, de a 319-ből egy
(`common/auth/federation_client.go`) nem szolgáltatás-kliens. Ellenőriztem, hogy
**nulla műveletet termel** (`grep -nE "^func \(.*\) [A-Z][A-Za-z]*\(.*\).*Response"`
→ üres), tehát a 8048-as összeg érintetlen. A `service-assumptions.md` maga is
annotálja a `common/auth` elkülönítést, tehát tudatos, csak a hatókör-mondat laza.

## Amit NEM ellenőriztem

A csend nem azt jelenti, hogy rendben van.

- **Magát a 8048/8048 feloldást** — a nevezőt igazoltam függetlenül, azt **nem**,
  hogy az új resolver mind a 8048-at feloldja. Nem futtattam az extractort.
- **A per-szolgáltatás számokat** (271/271, 129/129, 145/145, 56/56, 456/456,
  54/54) — az agent `-audit` kimenetére támaszkodom.
- **Az osztályozás számait**: 639/570/264/8, a 323/1481 (21,8%), a 65/158, az
  1014 interface és a 470 `*Details`/`*Base`. Mind Python-szkriptes mérés az
  agent oldalán; a szkripteket nem futtattam újra.
- **A DoD 2–5 pontját**: `make check`, wasm build/test, `MANIFEST.sha256`
  regenerálás, `docs.link-check`. A zöld CI ezek egy részét lefedi, de én
  egyiket sem futtattam külön.
- **A regressziós tesztet** (`regression_test.go`, 221 sor) — hogy tényleg
  lefagyasztja a `vcn`/`subnet` mezőhalmazt, nem futtattam.
- **Az exit-4 / exit-5 viselkedést** — az `-audit` és a `-schema`/`-policy`
  nem-nulla kilépését nem hajtottam meg.
- **A `service-assumptions.md` A3 és A4 szakaszát** — az A1-et és A2-t olvastam
  végig; a másik kettőt csak a commit-üzenetből ismerem.
- **A `sweep-input.md` osztályozását tartalmilag** — elolvastam és koherens, de a
  benne lévő számokat nem verifikáltam.

## Amit érdemes kiemelni — nem hibaként

Az agent olyat is szállított, amit a spec nem kért, és ez a job legértékesebb
része: **a régi mérőszám önmagát igazolta.** Az `-audit` `missing=0`-t mutatott,
mert maga a *jelölthalmaz* volt szűkítve — a `ListRegions` már a szűrőn kiesett,
így sosem jelenhetett meg hiányként. Az SDK egészén ez `8047/8047`-nek látszott,
miközben a valóság `8047/8048`.

Az A2 pedig a legveszélyesebb osztály bizonyítéka: a régi kód **exit 0**-val adott
érvényes draft-07 sémát `required` lista nélkül, create és delete művelet nélkül —
„a schema that validates and is wrong", 1217 erőforrásból 570-et érintő
névkonvencióra építve.

A feloldás iránya konzisztens az ökoszisztéma logikájával: a lifecycle az **HTTP
felületből** derivál, nem a Go azonosítókból, a body-modell az SDK saját
`contributesTo:"body"` tagjéből — sosem névből.

## Nyitott tételek — nem blokkolók

1. **A `sweep-input.md` figyelmeztetése a következő jobnak**: ige-alapú keresés
   (`<Ige><R>` + `<Ige><R>Details`) ~90 igét ad, amelyek nagy része **akció**, nem
   create. A második job spec-je ezt ne rontsa el.
2. **Polimorf create-modellek (8 db)**: ma `exit 5`-tel jelentve, a konkrét
   implementációk **nincsenek** kibontva. Tudatos hatókör-korlát, döntést igényel.
3. **T10 él**: a `make build` 11 untracked, nem-ignorált `.yaml` sidecart hagyott
   a klónban. Az agent helyesen kerülte el, de a csapda megmaradt.
4. **A `tools/env.sh`-ból hiányzik a modul-repo path-ja** — ezért nem tudott az
   O5 egyetlen `file:line`-t sem feloldani. Felvehető, hogy a kapu legközelebb
   gépileg csinálja, amit most kézzel.

## Döntés

**MERGE.** A job pontosan a specifikált szűk kérdést döntötte el, méréssel:
az extractor service-specifikus volt, négy nevesített feltételezésen, és mind a
négy bizonyítékkal alátámasztva feloldásra került. A négy `file:line` hivatkozás,
amit független újraverifikációnak vetettem alá, kivétel nélkül pontos volt, és a
két SDK-mérés, amit magam is lefuttattam, számra egyezik. A CI a review-zott
committon zöld.
