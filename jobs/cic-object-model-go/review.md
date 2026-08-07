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

---

## Utóirat — az SD-004 diagnózisa hiányos, és a `cic` definiálatlan

A review után az orchestrátor és a felhasználó átnézte az SD-004-et. Két
korrekció, amit az implementáló agent nem talált meg:

### 1. A `cic` sehol nincs definiálva

A `SPEC.md` **egyetlen** helyen említi (`:688`), egy példakód-blokkban az
INV-033 alatt:

```yaml
cic:
  model: "0.1"
```

Az invariáns szövege csak ennyi: *„Every canonical CIC object MUST carry the
model version it conforms to."* Sehol nincs kimondva, hogy a `cic` **mi** (tag,
boríték, keret), **hol** ül (node-on belül, mellette, felette), hogy a név
kötelező-e, és hogy a „carry" tartalmazást jelent-e vagy csak kiolvashatóságot.

**Ezért az SD-004 rosszul van diagnosztizálva.** Nem két invariáns
ellentmondása: egy **hiányzó definíció**, amit a korpusz kitalálva töltött be —
a `cic`-et a root node tagjává tette —, és ez a találgatás ütközik az
INV-021-gyel. A defekt gyökere az INV-033, nem az INV-021/022.

A felhasználó értékelése: a példa maga rossz — úgy néz ki, mintha a séma adatai
ülnének a metaadatok között. A szándékot egyikünk sem tudja rekonstruálni, és
nem is találgatjuk tovább.

### 2. A `metadata:`/`spec:` konvenció itt NEM alkalmazható

Az orchestrátor először azt javasolta, hogy a `cic` a `metadata:` alá kerüljön,
a `metadata:`/`spec:` keretre hivatkozva, amit mind a nyolc atomic primitív, a
`schemas/index.yaml` és az új repo saját `spec/index.yaml`-je is használ.

**Ez tévedés volt.** Az a keret **séma-artifactok** konvenciója — kézzel írt,
leíró dokumentumoké. A conformance `expected.yaml` viszont **materializált
példány**, amit a library *előállít*. Más kategória; a séma-artifact keretét
ráhúzni ugyanaz a hibaosztály, mint konvenciót átvinni oda, ahol nem az van.

Ez a repo az **alapobjektum-libet** építi, nem az alapobjektumok által leírt
szabályrendszert — a kettő keretezése nem cserélhető fel.

### Ami a keret kérdésétől függetlenül áll

1. A `cic` nem lehet a node tagja — nem az INV-021 miatt, hanem mert **nem az
   objektumról szól**.
2. A rootnak hordoznia kell a deklarált `shape`-jét, ha egyszer közönséges node.

Mindkettő korpusz-hiba.

### Nyitott döntés — a lib alapkérdése, nem korpusz-részlet

Az INV-033 a lib szintjén állít valamit, de legalább három dolgot jelenthet:

- a **példány** hordozza a modellverziót (a korpusz kimondatlanul ezt választotta)
- a **típus** hordozza (a lib tudja, nem az adat)
- a **szerializáció** hordozza (csak wire/fájl szinten létezik)

Ettől függ, hogy a `cic` egyáltalán létezik-e adatként. Amíg ez nincs eldöntve,
az SD-004 nem javítható — és a Rust implementáció sem indulhat, mert ugyanerre
a hézagra futna rá.

---

## SD-017 (orchestrátori) — az INV-033 a saját nyelvtanában kielégíthetetlen, és ütközik az INV-034-gyel

Ez a defekt a review során keletkezett, nem az implementáló agenttől. Erősebb
állítás, mint a fenti „a `cic` definiálatlan": **nem hiányos, hanem
teljesíthetetlen** — és nem vélemény, hanem a `SPEC.md` §2.1-ből és a D-003-ból
levezetve.

| | |
|---|---|
| **Hol** | `SPEC.md` §11 (INV-033), §2.1 (INV-001…INV-004), §6.1 (INV-021) |
| **Súlyosság** | **blocking** |
| **Viszony** | ez az SD-004 gyökéroka; az SD-004 a tünetet írja le |

### A levezetés

A §2.1 a node-nyelvtant **zártként** definiálja:

```
CICNode := { values, origin, <primitive>: CICNode }
```

Az INV-021 nem külön szabály, csak ennek újramondása. Ha a `cic` nem lehet
node-tag, akkor a modellverzió három helyen élhetne az objektumban, és
mindhárom zárva van:

1. **`values` alatt** — akkor domain adat, nem verzió.
2. **primitívként** — kilencedik atom kellene. A D-003 nyolcat rögzít, és az
   `origin` esetében épp strukturális okból utasítottuk el a kilencediket
   (végtelen regresszió). Ráadásul a verzió nem a payload szemantikáját írja le,
   ami a §2.1 szerint minden nem-`values` tag dolga.
3. **negyedik tagfajtaként** — akkor a nyelvtan nem zárt, és elveszik az az
   érv, amiért bármely útvonalra hash képezhető, ACL örököltethető és evidence
   hivatkozhat rá.

Marad, hogy **a verzió nem az objektumban van**. Ez nem kompromisszum: a
modellverzió arról szól, *milyen nyelvtan szerint olvasd az egészet* — fogalmilag
kívül van a payload szemantikáján.

### Az ütközés az INV-034-gyel

Az INV-034 **már most is** átadási tulajdonságként kezeli a verziót:

> *„A module MUST declare the model version it consumes, and a host MUST NOT
> hand a module an object of a version the module has not declared."*

Itt a verzió a **hoszt–modul átadás** tulajdonsága. Az INV-033 ugyanezt az
objektum tulajdonságaként követeli. A két invariáns ugyanarról a tényről két
különböző helyet jelöl ki.

### Miért nem javítható korpusz-szerkesztéssel

Az SD-004 javaslatai (a `cic` testvérré tétele, vagy az INV-021/022
hatókör-szűkítése) a tünetet kezelnék. Amíg az INV-033 azt mondja, hogy az
**objektum** hordozza a verziót, minden implementációnak muszáj lesz valahova
betennie — és a nyelvtanban nincs hova. A korpusz éppen ezért találta ki a
`cic` tagot: nem hanyagságból, hanem mert az invariáns ezt követelte tőle.

### Javaslat (döntés, nem levezetés)

Az INV-033 fogalmazódjon át úgy, hogy a verzió a szerializációs/átadási keret
tulajdonsága, az INV-034-gyel összhangban — vagy törlődjön, és az INV-034
maradjon az egyetlen verzió-invariáns. Ha marad valamilyen dokumentum-szintű
verzió-hordozó, azt **külön kell definiálni**, névvel és hellyel, nem
példakód-blokkban.

**Amíg ez nincs eldöntve, az SD-004 nem javítható**, és a Rust implementáció
sem indulhat: ugyanerre a hézagra futna rá, és a két implementáció egyformán
rossz módon lenne „konform".
