# claim-evidence — cic-object-model-go

Minden DoD-pont egy sor. Amit nem tudtam igazolni, az kimondva „nem igazolt".

Minden parancs a `cic-object-model` klónban, a `builder` konténerben futott
(`docker compose exec -T builder sh -c 'cd /app/go && …'`). A klón HEAD-je:
`9ae04c1`.

## DoD

| # | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|---|
| 1 | `go/` fordul, `make golang.quality` zöld | **igazolt** | `go build ./...` néma; `make golang.quality` végigfutott: staticcheck 5 csomagon, `go vet` 5 csomagon, `govulncheck`: „Your code is affected by 0 vulnerabilities" | A parancs teljes kimenete, nem az exit code. **Fenntartás:** a `golang.fmt-check` `git ls-files`-t használ, a `go/` fájljai pedig követetlenek a klónban → az a lépés 0 fájlt nézett. Ezt külön pótoltam: `gofmt -s -l .` közvetlenül | A gate a cél-repóba emelés + commit után fog a fmt-re is valóban ráfutni. Két fájl formázásra szorult (`errors.go`, `forge.go`), javítva, újrafuttatva tiszta |
| 2 | Mind a 27 vektor lefut | **igazolt** | `go test -v ./conformance/`: 27 futott, 27 átment, 0 bukott. `TestCorpusSize` naplója: „corpus: 27 vectors". Teljes `t.Run` névlista az `agent-output.md`-ben | A futtató **állítja** a csoportonkénti darabszámot (13/8/6); ha a korpusz mérete változik, `t.Fatalf`. Így a „0 vektor futott, exit 0" nem tud átmenni | Alacsony |
| 3 | Minden bukó vektor vagy javított kód, vagy defektsor | **igazolt (üres halmaz)** | 0 bukó vektor. A két lista uniója triviálisan fedi | Lásd #2 | — |
| 4 | INV-032 forrás-szinten kikényszerítve | **igazolt** | `TestForgedObjectDoesNotCompile` átment, a fordító hibaüzenetével a naplóban: „missing method sealedByMaterializer" + 2× „cannot refer to unexported field". `grep -rn 'func New\|func Must' go/ \| grep -v _test.go` → **0 találat** | A teszt `go build`-et futtat a `testdata/forge` csomagra, és **hibát követel**; ha fordulna, `t.Fatalf`. Ellenőrzi azt is, hogy a hiba tényleg a marker metódus miatt van, nem véletlen build-törés miatt | **Ismert rés:** a nil interfész-érték Go-ban nem tiltható (SD-016). Futásidőben `module.Execute` fogja meg |
| 5 | A pipeline szakaszhatárai megtartva | **igazolt** | Mind a 14 hibavektor `stage:` mezője egyezik. A futtató külön asserttel nézi: `if string(got.Stage) != want.Error.Stage` | **Mutáció-teszt:** az `E_UNKNOWN_PRIMITIVE`-ot átraktam entry-validation-be → `invalid/006` azonnal bukott: „stage: got entry-validation, want primitive-evaluation". A szakasz-assert tehát él, nem dekoráció | A `schema-load` szakaszt a §8 nem definiálja (SD-002); a vektorok mégis megkövetelik. A vektorokat követtem |
| 6 | `output/spec-defects.md` létezik | **igazolt** | `output/spec-defects.md`, **16 defekt** (SD-001…SD-016), súlyozva: 4 blocking, 4 divergent, 5 underspecified, 3 editorial | Fájl. Minden defekt kódhorgonyt kapott (`SD-nnn` komment azon a helyen, ahol a döntés kényszerű volt) | — |
| 7 | `deadcode ./...` vagy production call site minden exportált szimbólumra | **részben igazolt** | `deadcode ./...` → **üres kimenet** (nincs elérhetetlen függvény) | **Először igazoltam, hogy az eszköz él**: beraktam egy `ProbeUnreachable` függvényt → `deadcode` jelentette („objectmodel/probe.go:4:6: unreachable func"); eltávolítva újra üres. Enélkül az üres kimenet semmit nem bizonyítana | **Nem fedett:** a `deadcode` függvényeket elemez, konstansokat nem. `StageReferenceResolution`-nek **0 production hivatkozása van** (a §8.2 nem dob hibát) — lásd lent |

## Nem igazolt / részleges — kimondva

| Állítás | Miért nem igazolt |
|---|---|
| **A §8.6 minden MUST-ja teljesül** | Nem teljesül. A „resolve `inherit` chains for `access` (INV-025)" nem implementálható 0.1-ben: a tri-state `0` a PolicySurface-ből számol újra, amit a §1 hatókörön kívülre tesz. Ez **spec-defekt (SD-012), nem implementációs hiány** — és nem szűkítettem csendben. Vektor sem fedi: a `materialization/013` feloldatlanul, szó szerint rögzíti az `inherit` értékeket |
| **`StageReferenceResolution` exportált konstansnak van hívási helye** | Nincs: 0 használat. A §8.2 szakasz fut, de nem dob hibát, mert a sémanyelvben nincs referencia-szintaxis (SD-009). A konstans a normatív szakasz nevét dokumentálja. Meghagytam és jelzem, nem töröltem csendben |
| **A `tools/check_spec_vectors.py` spec↔vektor gate zöld** | Nem mértem. A builder konténerben nincs PyYAML (`ModuleNotFoundError: No module named 'yaml'`, a `p_venv` nincs feltöltve). Környezeti állapot, nem a Go munka része — de nem állítom zöldnek |
| **A `make conformance` cél zöld** | Nem futtattam külön; a `golang.test`-et hívja, ami átment. A `make conformance` `mk/rust.mk` hiányában a Go ágra esik |
| **INV-030 byte-azonosság két implementáció között** | Nem igazolható és nem is teljesíthető: a §8.8 nem definiál kanonikus szerializációt (SD-010). Amit igazoltam: **implementáción belüli** determinizmus — minden materializációs vektornál kétszer materializálok és byte-ra hasonlítok. A vektor-összehasonlítás **parse-olt szerkezeten**, nem byte-on történik |
| **A sealed lista-elemek template `content`-ből** | Implementálva, de **egyetlen vektor sem fedi**. Nem futtatott kód-út |
| **Undeclared skalár elutasítása** | Szigorúbb, mint amit az INV-029 kimond („an object"). Döntés, nem levezetés — SD-008 |

## Kockázat-összefoglaló

A legnagyobb kockázat nem a kódban van, hanem abban, hogy **a 27/27 zöld
félrevezető lehet**. Hat helyen a korpusz és a normatív szöveg ellentmond
egymásnak, és az implementáció a korpuszt követi (SPEC §10 alapján). Ha a
`SPEC.md` szövege nyerne, ebből legalább a SD-003, SD-004, SD-005 és SD-013
ponton **más kód kellene** — a SD-004 esetében mérten mind a 13 materializációs
vektor bukna.

Ezért a `spec-defects.md` a fő termék, nem a zöld teszt. A Rust implementáció
ugyanezt a korpuszt fogja futtatni; ha ugyanezekre a pontokra fut rá, az
megerősítés, nem duplikáció.
