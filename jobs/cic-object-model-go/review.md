# review — cic-object-model-go

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-07
- Feature branch: `feature/cic-object-model-go` (cic-factory), commit `e9f00a8`
- A tesztelt `cic-object-model` HEAD: `9ae04c1`
- Futás: 25 + 58 turn (resume), $2,38 + $8,70 = **$11,08**, opus-5

## A futás anomáliája — és amit igazolt

Az első futás 25 turn után **session limitbe** futott („resets 7:50pm"), az
`agent-output.md` üresen jött létre. A `--resume` ugyanabban a session-ben
folytatta: **nem keletkezett új jsonl**, az eredeti `e07acbec-…` nőtt tovább.

Ez egyben a `--resume` mechanizmus mérése is: a szülő job resume-ja **24 token
friss inputot** használt 3 075 671 cache-olvasás mellett. A folytatás nem
tanulja újra a kontextust, hanem visszaolvassa.

## Amit ténylegesen ellenőriztem

| Állítás | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| Mind a 27 vektor lefut és átmegy | **magam futtattam** a konténerben: `go test ./conformance/ -v`, majd `grep -c "^    --- PASS"` és `grep -c FAIL` | **27 PASS, 0 FAIL** — igazolt, nem az agent állításából |
| **SD-004 (blocking) valós** | **magam mértem az adatból**: mind a 13 `materialization/*/expected.yaml` root-kulcsai, és a sémák `root:` blokkja | 13 vektorból **0**-nak van `shape` a rootján, miközben a séma `root: shape: object`-et deklarál. A root kulcsai: `cic`, `origin`, `values`. **Az INV-022 tehát mind a 13 vektorral ütközik** — igazolt |
| INV-032 típus-szintű garancia | `go test -run TestForgedObjectDoesNotCompile ./...` | `ok .../inv032` — igazolt |
| Nincs kerülő konstruktor | `grep -rn "func New\|func Must" --include=*.go \| grep -v _test.go \| wc -l` | **0** — igazolt |
| A konténer tényleg az agent fáját nézi | `docker inspect` a `/app` mountra | a workspace klónra mutat — a mai compose-projektnév csapda **ellenőrizve**, nem feltételezve |

## A job valódi terméke

**16 spec-defekt** (`SD-001`…`SD-016`): 4 blocking, 4 divergent, 5
underspecified, 3 editorial. Mindegyik kódhorgonyt kapott — `SD-nnn` komment
azon a helyen, ahol a döntés kényszerű volt.

A legfontosabb megállapítás a jelentés első bekezdésében áll, és pontosan az a
mondat, amiért ez a job létezett:

> **All 27 vectors pass.** That is not the same as "the specification is
> correct": in six places the corpus and the normative text disagree, and the
> corpus won.

A hat ütközés: SD-003, SD-004, SD-005, SD-009, SD-013, SD-014.

### SD-004 — amit magam is megmértem

`INV-022`: *a kanonikus node hordozza minden primitívet, amit a sémája
deklarál.* Minden vektor-séma `root: shape: object`-et deklarál. Egyetlen
`expected.yaml` sem hordoz `shape`-et a rootján.

Egyszerre `INV-021`: *a node ne hordozzon olyan tagot, ami nem `values`, nem
`origin` és nem primitív.* A root hordozza a `cic`-et, amit az `INV-033`
**megkövetel**.

Tehát a root a specifikáció szerint sérti az INV-021-et, és az INV-022
teljesítése a teljes korpuszt megbuktatná. Az agent mérése: a root deklarált
`shape`-jével **13/13 materializációs vektor bukik**, nélküle 13 megy át.

Ez nem stílushiba. **A ma reggel mergelt SPEC két invariánsa a saját korpuszával
ellentmond** — és ezt csak az implementálás mutathatta meg.

## Amit az agent kimondott, és ettől hihető

A claim-evidence tábla **hét** sort tesz a „nem igazolt / részleges" szakaszba,
köztük olyanokat, amiket könnyű lett volna elhallgatni:

- **A §8.6 `inherit` chain feloldás nem teljesül** — a tri-state `0` a
  PolicySurface-ből számolna újra, amit a §1 hatókörön kívülre tesz. Ez
  spec-defekt (SD-012), és **nem szűkítette csendben**. Pontosan az a pont,
  amit a spec gyanúsként megnevezett neki.
- **`StageReferenceResolution`-nek 0 production hivatkozása van** — a §8.2 fut,
  de nem dob hibát, mert a sémanyelvben nincs referencia-szintaxis (SD-009). A
  konstanst meghagyta és jelezte, nem törölte csendben.
- **A `golang.fmt-check` 0 fájlt nézett**, mert `git ls-files`-t használ, a `go/`
  pedig követetlen a klónban. Ezt észrevette és kézzel pótolta (`gofmt -s -l`),
  két fájl formázásra szorult.
- **`check_spec_vectors.py` nem futott** — nincs PyYAML a konténerben. Nem
  állította zöldnek.

Két helyen a **negatív irányt is megmérte**, ami ma a visszatérő téma:

- **mutáció-teszt a szakaszhatárra:** az `E_UNKNOWN_PRIMITIVE`-ot átrakta
  entry-validation-be → `invalid/006` azonnal bukott a `stage` mismatchre. A
  szakasz-assert tehát él, nem dekoráció.
- **`deadcode` élességének igazolása:** beszúrt egy `ProbeUnreachable`
  függvényt → a `deadcode` jelentette; eltávolítva újra üres. Enélkül az üres
  kimenet semmit nem bizonyítana.

## Amit NEM ellenőriztem

- **A 16 defekt mindegyikének helyességét.** Az SD-004-et végigmértem, a
  többit elolvastam. Hogy mind a 16 valódi spec-hiba és nem félreolvasás, azt
  nem igazoltam.
- **A Go implementáció helyességét azon túl, hogy a vektorok átmennek.** 27
  zöld vektor nem bizonyítja, hogy a materializer minden esetben helyes — csak
  hogy a korpuszon az.
- **Az SD-012 (`inherit` chain) megvalósíthatatlanságát.** Az érvelést
  elolvastam, nem próbáltam megcáfolni implementációval.
- **A `make golang.quality` teljes kimenetét** — az agent idézi, nem futtattam
  újra.

## Kockázat

A legnagyobb kockázatot az agent maga nevezte meg, és egyetértek:
**a 27/27 zöld félrevezető.** Hat helyen a korpusz és a normatív szöveg
ellentmond, és az implementáció a korpuszt követi (a SPEC §10 alapján
jogosan). Ha a szöveg nyerne, legalább négy ponton más kód kellene.

Ebből következik, hogy **a `SPEC.md` 0.1 nem fagyasztható be úgy, ahogy van.**
A hat ütközést el kell dönteni — szövegjavítás vagy vektorjavítás —, mielőtt a
Rust implementáció elindul. Ha a Rust ugyanezt a korpuszt futtatja változatlan
specen, a két implementáció egyformán rossz módon lesz „konform".

## Döntés

**MERGE** — a job teljesítette, amiért létezett, és többet is: nem zöld tesztet
szállított, hanem egy megmért listát arról, hol nem végrehajtható a
specifikáció. A 27/27 magam futtattam, az SD-004-et magam mértem az adatból, és
a claim-evidence tábla hét „nem igazolt" sora arra utal, hogy a többi állítás
is őszinte.

**A merge nem jelenti a spec elfogadását.** A következő lépés nem a Rust
implementáció, hanem a hat korpusz–szöveg ütközés eldöntése.
