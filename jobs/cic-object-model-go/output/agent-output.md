# cic-object-model-go — agent output

## Összefoglaló

A `cic-object-model` `SPEC.md` 0.1 Go referencia-implementációja elkészült, és
**a 27 konformancia-vektor mind lefutott: 27 futott, 27 átment, 0 bukott.**

A job igazi célja nem a Go kód volt, hanem az, hogy kiderüljön: végrehajtható-e
a `SPEC.md`. A válasz: **igen, de tizenhat helyen nem magától** — hat ponton a
normatív szöveg és a vektorkorpusz ellentmond egymásnak, és a korpusz nyert
(SPEC §10 a konformanciát a vektorokhoz igazodásként definiálja).

A fő termék az [`spec-defects.md`](spec-defects.md) — 16 sor.

## Vektor-statisztika

| Csoport | Futott | Átment | Bukott |
|---|---|---|---|
| `materialization/` | 13 | 13 | 0 |
| `invalid/` | 8 | 8 | 0 |
| `validation/` | 6 | 6 | 0 |
| **Összesen** | **27** | **27** | **0** |

A `t.Run` nevek (a `go test -v` kimenetéből):

```
TestCorpusSize                                            (corpus: 27 vectors)
TestMaterialization/001_origin_yaml
TestMaterialization/002_origin_schema
TestMaterialization/003_origin_sealed
TestMaterialization/004_origin_sealed_schema
TestMaterialization/005_closure_structured
TestMaterialization/006_closure_opaque
TestMaterialization/007_normalize_scalar
TestMaterialization/008_normalize_list
TestMaterialization/009_normalize_map
TestMaterialization/010_normalize_empty_object
TestMaterialization/011_discriminator_envelope
TestMaterialization/012_discriminator_payload_keywords
TestMaterialization/013_access_inherit_injection
TestInvalid/001_sealed_yaml_conflict
TestInvalid/002_sealed_yaml_schema_conflict
TestInvalid/003_closure_undeclared
TestInvalid/004_schema_declares_values_child
TestInvalid/005_origin_in_authoring_input
TestInvalid/006_unknown_primitive
TestInvalid/007_sealed_missing_path
TestInvalid/008_cyclic_primitive_declaration
TestValidation/001_origin_yaml_schema_conflict
TestValidation/002_origin_empty
TestValidation/003_origin_not_terminal
TestValidation/004_documentation_member
TestValidation/005_default_member
TestValidation/006_missing_model_version
```

Ezen felül (nem vektor, forrás-szintű): `TestForgedObjectDoesNotCompile`,
`TestNoExportedConstructor`, `TestINV031Boundary/{a..g}`,
`TestINV034ModelVersion`, `TestCanonicalYAMLIsACopy`.

### Miért nem hiszem el a saját zöldemet — mutáció-teszt

Az első futás 27/27 zöld volt. Ez pontosan az a minta, amit a job „tiltott
rövidítések" szakasza gyanúsnak nevez, ezért **a futtatót megcáfolhatóságra
ellenőriztem**: szándékosan elrontottam a kódot, és megnéztem, hogy tényleg
pirosra vált-e.

| Mutáció | Várt hatás | Mért hatás |
|---|---|---|
| `inherit: true` injektálás kivéve (INV-025) | 011 + 013 bukik | **bukott: 011, 013** |
| `E_UNKNOWN_PRIMITIVE` átrakva entry-validation-be | `invalid/006` bukik szakaszra | **`stage: got entry-validation, want primitive-evaluation`** |
| Root node kapja meg a deklarált `shape`-jét (INV-022 szó szerint) | materializációs vektorok buknak | **13/13 bukott** |

A harmadik mutáció első két próbálkozása **nem** bukott — kiderült, hogy a
root-kihagyást két helyen kellett volna egyszerre feloldani. Ez maga is
eredmény: megmutatta, hogy melyik kódhely a tényleges döntéspont, és a harmadik
sor mérése az SD-004 defekt empirikus alapja (nem állítás, hanem mérés).

Mutáns-maradvány ellenőrizve: `grep -rn MUTANT go/` → nincs találat.

## Amit implementáltam

### A) Materializer — `go/objectmodel/`

A SPEC §8 pipeline **szakaszonként külön fájlban**, a normatív sorrendben:

| Fájl | Szakasz |
|---|---|
| `schema.go` | séma-betöltés (INV-010, INV-015, INV-005) — a §8 által nem definiált `schema-load` |
| `entry.go` | §8.1 entry validation |
| `refs.go` | §8.2 external reference resolution |
| `template.go` | §8.3 sealed / template expansion |
| `construct.go` | §8.4 recursive node construction |
| `defaults.go` | §8.5 schema value and default materialization |
| `primitives.go` | §8.6 primitive evaluation |
| `validate.go` | §8.7 final validation |
| `canonical.go` | §8.8 canonicalization |

A szakaszhatárok valódiak: minden szakasz külön függvény az előző kimenetén,
nincs összeolvasztás. Ezt a 2. mutáció igazolja — a jó kód rossz szakaszban
bukást okoz.

### B) Vektorfuttató — `go/conformance/conformance_test.go`

Vektoronként egy `t.Run`. Nincs Go-specifikus fixture: ugyanazokat a YAML
fájlokat olvassa, amiket a Rust implementáció fog. A futtató **állítja is a
korpusz méretét** (13/8/6 = 27), így a „0 vektor futott, exit 0" nem tud
csendben átmenni. Minden materializációs vektornál lefut egy INV-030
determinizmus-ellenőrzés is (kétszeri materializálás, byte-összehasonlítás).

### C) INV-032 — típus-szintű garancia

`objectmodel.CanonicalObject` egy **nem exportált marker metódust** hordozó
interfész, a konkrét típus mezői nem exportáltak, exportált konstruktor nincs.
A `go/inv032/testdata/forge/` egy szándékosan nem forduló csomag; a teszt
`go build`-del futtatja és a fordítási hibára állít:

```
forge.go:26:37: cannot use Forged{} (value of struct type Forged) as
  objectmodel.CanonicalObject value in variable declaration: Forged does not
  implement objectmodel.CanonicalObject (missing method sealedByMaterializer)
forge.go:31:2: cannot refer to unexported field path in struct literal of type objectmodel.Node
forge.go:32:2: cannot refer to unexported field origin in struct literal of type objectmodel.Node
```

Ez erősebb, mint amit a SPEC előír („unexported constructor in Go") — az
önmagában nem elég, mert a nulla érték kívülről is előáll. **Egy rés marad,
amit Go-ban semmi nem zár: a nil interfész-érték.** Ezt nem hallgattam el:
SD-016, és a `module.Execute` futásidőben utasítja vissza.

### D) Modulhatár — `go/module/`

A `docs/spec-vector-map.md` az INV-031-hez kimondottan az implementációtól kér
integrációs tesztet klózonként („one integration test per clause"). Megvan:
`TestINV031Boundary/a..g`, hét al-teszt.

### E) CLI — `go/cmd/cic-materialize/`

Nélküle a `deadcode ./...` értelmetlen (main package híján minden exportált
szimbólum triviálisan elérhetetlen). Egyben valódi production call site is.

## Amit NEM implementáltam, és miért

1. **§8.6 „resolve `inherit` chains for `access`"** — nem implementálható 0.1-ben.
   Az INV-025 `0` állapota a PolicySurface-ből számol újra, amit a §1 hatókörön
   kívülre tesz és a `docs/decision-delta.md` kifejezetten elhalaszt. Ez egy
   normatív MUST, amit ez az implementáció **nem teljesít** — SD-012. Nem
   szűkítettem csendben: a `claim-evidence.md`-ben „nem igazolt" sor.

2. **§8.2 reference resolution** — a szakasz jelen van és a sorrendben fut, de
   nincs mit feloldania: a vektor-sémanyelvben nincs referencia-szintaxis
   (SD-009). Nem rövidítés, hanem a 0.1 hatóköre.

3. **Nem módosítottam** a `SPEC.md`-t, a `conformance/` vektorokat, a
   `docs/spec-vector-map.md`-t, a hat `CIC-objs` repót; nem hoztam létre GitHub
   repót, nem nyitottam PR-t; nem írtam Rustot és `mk/rust.mk`-t.

## Ismert korlátok

- **A `tools/check_spec_vectors.py` nem futott le**: a builder konténerben
  nincs PyYAML (`ModuleNotFoundError: No module named 'yaml'` — a `p_venv`
  nincs feltöltve). Ez a repo környezetének állapota, nem a Go munkáé, de nem
  állítom, hogy a spec↔vektor gate zöld — nem mértem.
- **`StageReferenceResolution` exportált konstansnak nincs production
  hivatkozása** (0 használat), mert a §8.2 nem dob hibát. A `deadcode`
  konstansokat nem elemez, ezért ezt külön írom le, nem hallgatom el.
- **A `golang.fmt-check` semmit nem ellenőrzött**, mert `git ls-files`-t
  használ, a `go/` fájljai pedig a `cic-object-model` klónban követetlenek.
  Ezért közvetlenül futtattam `gofmt -s -l`-t (két fájlt formázni kellett,
  utána tiszta). A cél-repóban commit után a gate magától is fogni fog.
- **A sealed lista-elemek template `content`-ből** implementálva vannak, de
  egyetlen vektor sem fedi őket.
- A `go/objectmodel/*.yaml` companion metaadat-fájlokat a repo generátora
  készítette; nem kézzel írtam őket.

## A `kb_focus` chunkokról

Mindhárom létezik és nem üres. A `file_path`-ok:

| Chunk | `file_path` | Tartalom |
|---|---|---|
| `c4135` | `CIC-basic-knowledge/docs/hu/repos/cic-primitives.md` | „**Hét** irreducibilis atom" |
| `c4255` | `CIC-objs/cic-compute/ai/DECISIONS.md` (+5 testvér) | D-003, „**7 atom**", 2026-04-30 |
| `c4367` | `CIC-objs/cic-yang/ai/DECISIONS.md` (+4 testvér) | D-011, „Access: a **8.** atom", 2026-05-04 |

A szülő job mérése megerősítve, sőt pontosítható: **a KB-snapshot önmagán
belül is elavult** — `c4135` és `c4255` hetet mond, `c4367` (négy nappal
későbbi döntés) hozzáteszi a nyolcadikat. Az irányadó a `SPEC.md` §6.1, ami
nyolcat mond, és az implementáció nyolc atommal dolgozik
(`go/objectmodel/schema.go`, `primitiveSet`).

## A `cic-object-model` klón

```
git clone git@github.com:CentralInfraCore/cic-object-model.git
9ae04c1 Merge pull request #1 from CentralInfraCore/devel   ← a várt commit
```

A klónban fejlesztettem és futtattam, **nem commitoltam bele**. A kész
implementáció az `output/go/` alatt van; a `cic-object-model` repóba emelés az
orchestrátoré.
