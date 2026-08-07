# cic-object-model-go — a Go referencia-implementáció

## Ki vagy

**Te vagy a végrehajtó agent.** Te írod meg a Go implementációt. Nem te
indítottad a jobot, és nincs mire várnod. Ahol a szöveg „az orchestrátor"-t
említi, az egy másik szereplő.

## Reasoning mód

**implementation** — de olvasd el előbb a „Mi ennek a jobnak az igazi célja"
szakaszt, mert ez nem hétköznapi implementációs job.

---

## Mi ennek a jobnak az igazi célja

A `cic-object-model` repo `SPEC.md`-je 34 számozott invariánst rögzít, és a
`conformance/` 27 vektort tartalmaz. **Egyik vektor sem futott le soha.** A
szülő job (`cic-object-model-spec`) ezt kimondottan „megírva, nem futtatva"
státusszal adta át.

Ebből következik, hogy a te dolgod nem elsősorban Go-t írni. A te dolgod:

**Te vagy az első dolog a világon, ami kiderítheti, hogy a SPEC.md
végrehajtható-e.**

Egy spec, amit senki nem implementált, hipotézis. Ahol kétértelmű,
önellentmondó, vagy megvalósíthatatlan, azt **te fogod először látni** — és az
a legértékesebb dolog, amit ez a job termelhet. Egy jól dokumentált
spec-hiba többet ér, mint egy zöld teszt, ami elfedi.

**Ezért: ha a SPEC.md hibás, azt jelentsd, ne kerüld meg.** Ne írj olyan kódot,
ami „valahogy működik" egy ellentmondásos szabály körül. A `docs/spec-defects.md`
sor a fő deliverable, nem a szégyenfal.

---

## Boot sequence

1. `kb_status` — elérhető a KB?
2. Olvasd el a `kb_focus` chunkjait (`c4135`, `c4255`, `c4367`). **A chunk-id
   nem stabil** — mindegyiknél ellenőrizd a `file_path`-t. Ha nem egyezik, az id
   elavult; keresd meg tartalom alapján és írd le az outputban.
   **FIGYELEM:** a szülő job megmérte, hogy a live repók D-003-a **8 atomot**
   mond (2026-05-04-én bővítve), miközben `c4255` még 7-et. A KB-snapshot ezen
   a ponton elavult. Ütközésnél a `SPEC.md` az irányadó, nem a KB.
3. Olvasd el a `cic-object-model` repóban, ebben a sorrendben:
   - `SPEC.md` — **egyben, elejétől a végéig**, mielőtt bármit kódolnál
   - `conformance/README.md` — a vektorformátum és a `templates:` konstrukció
   - `docs/spec-vector-map.md` — melyik invariánst melyik vektor fedi
   - `docs/decision-delta.md` — mit vált fel a modell, és miért
4. Olvasd végig mind a 27 vektort. A `meta.yaml`-ok `invariants:` mezője köti
   őket a specifikációhoz.

**Amíg ez nem történt meg, ne írj Go kódot.**

---

## A feladat

### A) A materializer

`go/` alá, `go.mod` modullal. A `mk/golang.mk` már ide van irányítva
(`GO_MODULE_DIR ?= go`), nem kell Makefile-t módosítanod.

Implementáld a `SPEC.md` §8 pipeline-ját, lépésenként elkülönítve:

```
entry validation → reference resolution → sealed/template expansion →
recursive node construction → schema value/default materialization →
primitive evaluation → final validation → canonicalization
```

A lépéssorrend **normatív**: egy későbbi lépés nem láthat olyan inputot, amit
egy korábbi eldobott volna. A `conformance/*/expected-error.yaml` minden hibánál
megadja a `stage:` mezőt — **a jó kód a jó szakaszban dobja a jó hibát.** A
helyes hibakód rossz szakaszban: bukás.

### B) A vektorfuttató

Egy Go teszt, ami a `conformance/` teljes korpuszát végigfuttatja, és
vektoronként külön `t.Run`-t ad. Ne egy nagy teszt legyen — vektoronként egy,
hogy a bukás megnevezze magát.

A vektorok implementáció-függetlenek (YAML be, YAML ki). **Ne írj Go-specifikus
fixture-t** — a Rust implementáció ugyanezt a korpuszt fogja futtatni, és ha
eltérnek, az a spec hibája, nem a nyelvé.

### C) INV-032 — a típus-szintű garancia

`SPEC.md` INV-032: a modul inputjának típusa `Validated<Canonical<CICObject>>`,
és ilyen érték **csak a core materializer által** legyen előállítható.

Ez a `docs/spec-vector-map.md`-ben kimondottan **„nem vektorizálható"**-ként
szerepel: egy YAML fájl nem tudja bizonyítani, hogy egy típus nem
konstruálható. Ezért ez a te forrás-szintű feladatod:

- a típus konstruktora és mezői **nem exportáltak**
- egy külön package-ben lévő teszt, ami **fordítási hibával** bukik, ha valaki
  kívülről próbálja megkonstruálni (`go build` a testdata-ra, vagy
  `go/analysis`-alapú ellenőrzés)
- `grep -rn 'func New\|func Must' go/ | grep -v _test.go` — mutasd meg, hogy
  nincs exportált konstruktor, ami megkerüli a materializert

### D) Spec-hibák jelentése

`docs/spec-defects.md` a `cic-object-model` klónodban. Minden találatra:

| # | Hely (`SPEC.md` §, INV-nnn) | Mi a probléma | Miért nem tudtam megkerülni | Javaslat |

Kategóriák, amiket kifejezetten keress:
- **kétértelműség** — két értelmezés, mindkettő megfelel a szövegnek, de más
  outputot ad
- **önellentmondás** — két invariáns egyszerre nem teljesíthető
- **hiányzó szabály** — egy vektor olyan viselkedést vár, amit egyetlen
  invariáns sem ír elő
- **rossz vektor** — az `expected.yaml` nem következik a specből

Konkrét gyanús pontok, ahol a szülő job maga is bizonytalan volt (nézd meg
őket, de ne korlátozódj rájuk):
- `SPEC.md` §4.3 diszkriminátor-táblája: a `list` shape sorában egy mapping
  envelope-nak minősül — de mi van, ha a lista elemei maguk mappingek?
- INV-022 („minden deklarált primitívet materializálni kell") és a vektorok
  `expected.yaml`-jai: minden node hordoz `shape`-et, de a `role`-t csak ott,
  ahol a séma deklarálja. Konzisztens ez?
- INV-025 per-operation `inherit`: mi a szemantika, ha `access.read.inherit`
  és `access.modify.inherit` eltér? A spec ezt kimondottan a PolicySurface-re
  halasztja — implementálható így?

---

## Tiltott rövidítések

- **A fájl létezése ≠ implemented.** Egy `materializer.go`, ami létezik, nem
  implementáció — a lefutott vektorok teszik azzá.
- **`go build` sikere ≠ működik.** A fordítás nem viselkedés.
- **`exit code 0` a teszttől ≠ sikeres**, ha 0 vektor futott. A vektorszámot
  **mondd ki**: hány futott, hány ment át, hány bukott. A `t.Run` nevek
  listáját mellékeld.
- **A skipped teszt nem átmenő teszt.** Ha egy vektort nem tudsz futtatni, az
  bukás vagy spec-hiba — nem `t.Skip`.
- **Az „exportált szimbólum létezik" ≠ „a production hívja".** A call-chain
  ellenőrzéshez `grep -rn` + `_test.go` kizárás, VAGY `deadcode ./...` output.
- **A spec megkerülése nem megoldás.** Ha egy invariánst nem tudsz teljesíteni,
  az `docs/spec-defects.md` sor, nem egy `if` a kódban.

## Hard constraintek

1. **Ne módosítsd a `SPEC.md`-t, a `conformance/` vektorokat és a
   `docs/spec-vector-map.md`-t.** Ha hibásak, azt jelentsd. A spec javítása
   külön döntés, nem implementációs mellékhatás.
2. **Ne módosítsd a hat `CIC-objs` repót** (`primitives-group/` alatt).
3. **Ne hozz létre GitHub repót**, és ne nyiss PR-t.
4. Ne implementálj Rustot — az a `cic-object-model-rust` job.
5. Ne írj `mk/rust.mk`-t.

---

## DoD

| # | Amit teljesíteni kell | Mivel igazolod |
|---|---|---|
| 1 | `go/` fordul, `make golang.quality` zöld | a parancs kimenete, nem az exit code önmagában |
| 2 | Mind a 27 vektor lefut | a futtató kimenete: futott/átment/bukott szám + `t.Run` nevek |
| 3 | Minden bukó vektor vagy javított kód, vagy `docs/spec-defects.md` sor | a két lista uniója fedje le a bukásokat |
| 4 | INV-032 forrás-szinten kikényszerítve | a nem-fordulást bizonyító teszt + `grep -rn` output |
| 5 | A pipeline szakaszhatárai megtartva | minden `expected-error.yaml` `stage:` mezője egyezik a dobás helyével |
| 6 | `docs/spec-defects.md` létezik (üresen is, kimondva, hogy nem találtál) | fájl |
| 7 | `deadcode ./...` vagy production call site (file:line) minden exportált szimbólumra | az output |

**Amit nem tudsz igazolni, az a claim-evidence táblában „nem igazolt" sorba
megy.** Ha egy DoD-pont a spec hibája miatt teljesíthetetlen, azt **mondd ki** —
ne szűkítsd csendben.

---

## Output

A `jobs/cic-object-model-go/output/` alá, a cic-factory klónodban:

### `output/agent-output.md`
Mit csináltál, mit nem, és miért. A vektor-statisztika és a spec-hibák
összefoglalója ide jön.

### `output/claim-evidence.md`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |

Minden DoD-pont egy sor.

### `output/go/`
A teljes Go implementáció (a `cic-object-model` repóba emelendő).

### `output/spec-defects.md`
A spec-hibák listája — ez a job legfontosabb terméke, ha van benne sor.

---

## Git

- A cic-factory klónodban dolgozol, `feature/cic-object-model-go` ágon.
- Commitolj és pushold a feature branchre. **PR-t ne nyiss**, `main`-re ne pushold.

## Nyelvi szabály

- Go kód, komment, `SPEC.md`-re hivatkozás, `docs/spec-defects.md`: **angolul**
- `output/agent-output.md`, `output/claim-evidence.md`: **magyarul**
