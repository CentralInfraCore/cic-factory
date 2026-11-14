# PR-02 jelentés — Rust mutánsfelsorolás fail-closed, tervező-vakfoltok

Job: `relay-ci-parity-02-mutation-planner` · a CIC_Relay #169 PR-02 lépése.
A PR-01 jelentés (`ref/pr01-*.md`) mérései az alap. **Küszöb vagy baseline nem változott.**

## 1. Vizsgált állapot

| | |
|---|---|
| CIC_Relay | ág `main`, commit `bc2c4e0a2eade4f798b51e03d2953304512960ed` (`gh api …/commits/main`: a PR-01 óta **nem mozdult**) |
| Relay munkaág | `feature/relay-ci-parity-02-mutation-planner`, commit `97dd5ebe881547f0717de6853650c8e0bccf8f0f` (helyi, a push a tulajdonosra vár) |
| cic-primitive-forms | `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (`main`), csak referencia, nem módosult |
| Toolchain a méréshez | `rust:1.96.1-bookworm@sha256:d99f7b31…c4abd8`, `cargo-mutants 27.1.0` (a CI **nem pinel**: a mérés a 27.1.0-ra érvényes) |

A munka egy **friss klónon** készült (`workspace/CIC_Relay-pr02/`, tiszta fa, 0 módosított fájl).
A PR-01 óta használt `workspace/CIC_Relay/` klón **ismét piszkos** (189 módosított `.yaml`, 6 nem követett fájl, a `cmd/relay/activator.yaml` módosítási ideje 2026-11-14 12:45); a tartalom sérült kinézetű (`cabinet.ModuleIDcabinet`, `cabinet.Setx`), az **ok továbbra sincs megállapítva**, ezért nem ezen mértem és nem ezt módosítottam.

## 2. A hiba újrareprodukálása a friss klónon

A PR-01 reprodukció (A/B/C) a friss klónon, valódi `cargo-mutants 27.1.0`-val megismételve a **javított** számlálóra (`raw/count-repro-real-cargo-mutants.txt`, `raw/countrepro.sh`). A régi `| grep -c . || true` forma viselkedését a PR-01 mérte (`ref/pr01-gate-defect-repro.md`), és a tesztek is újra előidézik (lásd 4.2, ellenpróba).

## 3. Mit változtattam (CIC_Relay, 8 fájl, commit `97dd5eb`)

### 3.1 A. Felsorolás fail-closed

| Hely | Előtte | Utána |
|---|---|---|
| `mutation-pr.yml` count lépés (`id: count`) | `n=$(cargo mutants --workspace --list --in-diff … \| grep -c . \|\| true)` | `n=$(python3 scripts/count_mutants.py --out /tmp/mutants.list -- cargo mutants … --list …) \|\| { echo "::error::…"; exit 1; }` |
| `nightly.yml` count lépés (`:146`, `:148`) | ugyanaz a minta, két ág | ugyanaz a számláló, a két ág (`--in-diff` / teljes) megmarad |
| `scripts/count_mutants.py` (új, 72 sor) | — | a felsoroló parancs **kilépési kódját előbb** ellenőrzi; sikeres + üres kimenet → `0`; hiba (nem 0 kilépés, vagy a parancs el sem indul) → kilépési kód 1, **stdout üres** |

A nyers felsorolást fájlba menti (`--out`), nem pipe-ol.

### 3.2 B. `mutation_plan.py`

| Vakfolt (PR-01 4.2) | Javítás |
|---|---|
| P1 csak teszt változott | a `_test.go` az **általa tesztelt csomagot** tervezi |
| P2 törölt fájl csendben kimarad (`--diff-filter=ACMR`) | `ACMRD` és `--no-renames`: a törlés a változáshalmaz része; a csomag tervbe kerül, ha maradt benne nem-teszt forrás |
| P3 `go.mod`, `go.sum`, `.gremlins.yaml` | `go_full`: a root modul **minden** csomagja |
| P4 gate-script | `go_full` **és** `rust_full` (gate-logika: a 3 script, `count_mutants.py`, `.mutation-baseline.json`, a 3 mutációs workflow) |
| P5 `Cargo.toml` | `rust_full`: a Rust mutánsok **nem** szűkülnek `--in-diff`-re (a PR-01 szerint a szűkített diff itt hány mutánst adna: nem mértem; most nem is szűkít) |
| P6 `testdata/*` | a `testdata`-t birtokló csomag tervbe kerül |
| P8 beágyazott modul | **változatlan** (továbbra is kimarad) |
| Rust teszt-fájl (`tests/`, `benches/`, `_test.rs`) | `rust_full`: a cargo-mutants a teszteket nem mutálja, ezért az `--in-diff` itt 0 mutánst tervezne |

Új kimenetek: `go_full`, `rust_full`, `full_reasons`. A workflow-k a `rust_full`-t a **shardokig** továbbviszik (különben a felsorolás FULL, a shard-futás szűkített lenne).

Két meglévő teszt **magát a vakfoltot állította** (`test_test_only_change_selects_nothing`, `test_testdata_vendor_and_non_go_are_ignored[testdata]`); ezeket a javított elvárásra cseréltem, nem töröltem őket a pirosuk miatt, hanem azért, mert a hibás viselkedést rögzítették (a #169 szerint a tesztváltozás nem tekinthető hatástalannak).

## 4. Negatív tesztek és a bukásuk bizonyítéka

### 4.1 A számláló valódi cargo-mutants ellen (`raw/count-repro-real-cargo-mutants.txt`)

```
A  valid, empty listing   count_mutants exit=0  n=[0]
B  unreadable --in-diff   count_mutants exit=1  n=[]   (cargo-mutants exit 6)
C  broken mutants.toml    count_mutants exit=1  n=[]   (cargo-mutants exit 1)
D  workflow form bash -e, B:  step exit code: 1
E  FULL listing           count_mutants exit=0  n=[300]  listing_lines=300
```

### 4.2 Az új tesztek az **új** és a **régi** (`bc2c4e0`) kódon

| Futás | Eredmény | Nyers kimenet |
|---|---|---|
| új tesztek, új kód (4 fájl) | **75 passed** | `raw/new-tests-on-new-code.txt` |
| a tervező-próba és a workflow-lépés tesztek, **régi** kód | **25 failed, 12 passed** | `raw/new-tests-on-old-code.txt` |

A régi kódon bukó 25 teszt: 12 tervező-teszt (P1, P2 ×2, P3 ×3, P4, P5, P6, Rust teszt-fájl, a Rust-forrás „szűk marad” és az „összefüggéstelen változás nem tervez semmit” teszt, utóbbi kettő a hiányzó `rust_full`/`full_reasons` kimenet miatt) és 13 workflow-teszt: a B/C felsorolási eset mindkét workflow-ban **8 eset, `assert 0 != 0`**, vagyis a lépés sikerrel tér vissza hibás felsorolásnál; 2 „pipe-olt/maszkolt felsorolás”, 2 „a számlálón át megy” és 1 „a shardok követik a módot” szöveg-teszt.
A régi kódon zöld marad (12 teszt), ahogy kell: P7 (új csomag), P8, P9 (ismeretlen base: fail-closed), csak-teszt csomag, az ellenpróba-tesztek, valamint a jogos-üres és a valódi-felsorolás eset (ezekben a régi forma helyesen viselkedik).

**Ellenpróba a teszt-harnessre.** A workflow-lépés tesztek a lépés `run:` szövegét YAML-ból kiveszik és `bash -e`-vel futtatják, hamis `cargo`-val (A/B/C eset). A `test_counter_test_*` tesztek a **régi** lépésszöveget ugyanezen a harnessen futtatva kimutatják, hogy B és C esetben `exit 0` és `shards=0`: a harness látja a hibát.

**Saját hibám, amit a próba kimutatott.** A harness első változata a régi kódon is „megbukott” a B/C tesztben, de **rossz okból**: a régi lépés `${{ … }}` kifejezést tartalmaz, amit a bash `bad substitution` hibával utasít el; és az üres git-fa miatt `bad revision 'HEAD...HEAD'` is kijött. A teszt tehát a maszkolást nem látta. Javítás: a harness behelyettesíti a kifejezést; a bukás-teszt a konkrét hibaüzenetet is megköveteli (`the Rust mutant listing failed`); az `old/` fát commitoltam. Az újramérés (25/12) már a valódi okot mutatja.

## 5. Egyéb mérések

- `ruff`, `black --check`, `isort --check-only`, `mypy` (6 fájl): tiszta. `bandit` (medium+): tiszta.
- `yamllint` a két workflow-n: `document-start` **figyelmeztetés** — a változtatás előtti állapoton is megvan (a `git stash`-elt fán mérve), nem az enyém.
- Kapcsolódó 7 teszt-fájl: **105 passed**. A repó teljes `pytest`-je a scratch venv-ben **nem futott le** (4 gyűjtési hiba: `No module named 'requests'`; a CI hash-ellenőrzött függőségekkel fut): a teljes csomag eredménye **nem mérve**, a CI futása dönt.
- A többi `|| true` besorolása (`grep -rn '|| true' .github/`):
  `verify.yml:31,89`, `mutation*.yml` `go mod download || true` — nem elfedő (PR-01); `verify.yml:105` `git merge-base … || true` — üres eredménynél `pkgs=./...`, vagyis **teljes** futásra esik vissza (fail-safe); `manifest-check.yml:20` `chmod +x … || true` — nem mért döntés. Egyiket sem módosítottam (nem felsorolási hibaosztály).

## 6. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A számláló sikertelen felsorolásnál nem ad `0`-t | implemented | `scripts/count_mutants.py`; `raw/count-repro-real-cargo-mutants.txt` B/C: exit 1, `n=[]` | `bash raw/countrepro.sh` pinelt konténerben | alacsony; csak cargo-mutants 27.1.0-ra mérve |
| A jogos üres felsorolás `0`, nem hiba | implemented | uo., A: exit 0, `n=[0]` | uo. | alacsony |
| A két workflow a számlálót használja, a hiba piros lépés | implemented (szöveg + harness) | `mutation-pr.yml`, `nightly.yml` count lépés; `test_failed_listing_fails_the_step` (8 eset) | `pytest tests/test_tools/test_mutation_workflow_enumeration.py` | **GitHub Actions-ban nem futott**: nem mérve |
| A teszt a régi kódon buktatja a hibát | implemented | `raw/new-tests-on-old-code.txt`: 25 failed | futtatás a `bc2c4e0` fán | alacsony |
| A tervező P1–P6 vakfoltokat kezeli, P7–P9 nem romlott | implemented (tervező szinten) | `tests/test_tools/test_mutation_plan_probes.py` (16 teszt) | pytest scratch git-repón | **a gremlins tényleges futása a megnőtt tervvel nem mérve** |
| FULL Rust felsorolás működik valódi eszközzel | implemented | E eset: 300 mutáns | `raw/countrepro.sh` | a 300 a mai állapot; a shard-teljesség a PR-03 |
| A shardok követik a `rust_full`-t | implemented (szöveg) | `RUST_FULL` env a shard-lépésekben; `test_the_shards_follow_the_planned_mode` | pytest | **GitHub Actions-ban nem futott**: nem mérve |
| A teljes CI zöld az új HEAD-en | **nem mérve** | — | a PR gate-futása | a PR még nincs megnyitva |
| A `cargo-mutants` CI-beli verziója egyezik a 27.1.0-val | **nem mérve** | a CI nem pinel | a futásban a `--version` kiírása | közepes |

## 7. Nyitott, jelentve (nem része a jobnak)

- **Rust `#[cfg(test)]` modul módosítása** ugyanabban a fájlban: a cargo-mutants a tesztkódot nem mutálja, az `--in-diff` itt 0 mutánst ad; ez a tervező szintjén fájlnév alapján nem ismerhető fel. **Nem mérve, nem kezelve.**
- A megnőtt terv költsége (`go_full`, `rust_full`) **nem mért**; a #169 és a tulajdonos szabálya szerint a futásidő nem érv a kapu ellen.
- Eszköz-verzió pin, nightly horgony (`nightly.yml:96-104`), `deadcode` lépés státusza: **külön döntés**, nem változtattam.
- A shard-teljesség (planned = measured) a **PR-03** feladata; ez a PR csak azt biztosítja, hogy a felsorolás hibája ne legyen `0`.
- A Relay `workspace/CIC_Relay/` klón ismétlődő piszkos állapota: ok ismeretlen (lásd 1.).

## 8. Aláírás és push

A Relay-commit a Vault `commit-msg` hook futásával készült (aláírási metaadat a commit-üzenetben); az aláírás érvényességét **nem ellenőriztem**. A commit szerzője a tulajdonos beállított git-identitása. Co-Authored-By vagy AI-re utaló sor nincs. A squash-merge trailert vihet a `main`-re: a merge módját a tulajdonos dönti.
A Relay-ág push-át és a PR-t a tulajdonos futtatja, ha a környezet elutasítja.
