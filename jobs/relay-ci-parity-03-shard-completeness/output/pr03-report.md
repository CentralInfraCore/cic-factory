# PR-03 jelentés — teljességi validáció és egységes kapu (shard-completeness)

Job: `relay-ci-parity-03-shard-completeness` · a CIC_Relay #169 PR-03 lépése.
Alap: `ref/pr01-*.md`, `ref/pr02-report.md`. **Küszöb, padló és baseline nem változott** (lásd 7.).

## 1. Vizsgált állapot

| | |
|---|---|
| CIC_Relay `main` | `7ac6e8027931ed94eeec328ff5217cce90d0ebdf` (tartalmazza a PR-02 merge-et; friss klón, `git status --short \| wc -l` = **0** a klónozás után és a mérések előtt) |
| Relay munkaág | `feature/relay-ci-parity-03-shard-completeness`, commit `275ebea` |
| Bizonyító (piros-út) ág | `ci-proof/relay-ci-parity-03-red-path`, commit `69e72d9` — **szándékosan hibás, nem mergelendő** |
| cic-primitive-forms | `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (`main`), csak referencia |
| Mérési környezet | `rust:1.96.1-bookworm@sha256:d99f7b31…c4abd8`, `cargo-mutants 27.1.0`; Go méréshez `golang:1.26.10`, `gremlins v0.6.0` |
| Hogyan futott | a jobot **ebben az interaktív sessionben** végeztem, nem a `run-job.sh`-val (a live workdir ága rendezetlen volt); friss klónon (`workspace/CIC_Relay-pr03/`), a régi `workspace/CIC_Relay/` klónt (piszkos, ok ismeretlen) nem használtam |

**Esemény a futás közben.** A scratch-kötet (16 GB `tmpfs`) betelt, a nyolc valódi shard futása a 7-esnél megszakadt (`outcomes.json` nélkül). A tulajdonos felszabadított helyet, a 7. shardot **újra futtattam**; a többi hét ép maradt (`raw/real-run-summary.txt`). Ez véletlenül egy valódi „hiányzó shard” eset volt is.

## 2. A feltárt riportformátumok (valódi eszközkimenet alapján)

| Mi | Mért |
|---|---|
| Mit tölt fel ma a CI a mutációs jobokból | **semmit.** Az egyetlen `upload-artifact` a `verify.yml` lefedettségi riportja. A shard és a chunk a kilépési kódjával jelez; nincs mit a tervhez hasonlítani |
| `cargo mutants --list --json` | 300 elem; mezők: `diff, file, function, genre, name, package, replacement, span`; a `name` (`fájl:sor:oszlop: replace f -> T with X`) **300/300 egyedi**, azonos a `--list` szöveges sorával |
| Jogos üres felsorolás (érvényes diff, nincs mutálható kód) | kilépési kód **0**, stdout **0 bájt** — *nem* `[]` (`raw/list-json-empty-and-failed.txt`) |
| Hibás felsorolás (olvashatatlan diff) | kilépési kód **6**, stdout 0 bájt |
| `mutants.out/outcomes.json` | `outcomes[]`: `scenario` = `"Baseline"` vagy `{"Mutant": {name, …}}`; `summary` ∈ `Success`, `CaughtMutant`, `MissedMutant`, `Timeout`, `Unviable`; plusz összesítők: `total_mutants, caught, missed, timeout, unviable` |
| A shard-futás azonosítói a tervhez képest | a `--shard k/8` outcomes-ainak `name` mezői **megegyeznek** a `--list` neveivel (mérve, lásd 3.) |
| Go (gremlins) | szöveges összegzés (`Killed: n, Lived: n, Not covered: n`, `Timed out: n`); a `gremlins_gate.py` már elemzi, de gépi riportot nem írt |

## 3. A valódi futás: a terv és a mérés egyezése (`raw/real-run-summary.txt`)

| Futás | Mutáns | caught | missed | timeout | unviable |
|---|---|---|---|---|---|
| FULL, egy folyamatban (5 perc) | 300 | 217 | 0 | 0 | **83** |
| 8 shard külön-külön (`--shard k/8`) összege | 300 | 217 | 0 | 0 | 83 |

A nyolc shard 7 × 38 + 34 = 300 ítéletet adott; a halmazuk **pontosan egyenlő** a tervével, minden mutáns egyszer szerepel.
Az `unviable` **nem egyenletes**: shard 4: 0, shard 2: 19. Fájlonként: `connections/src/vault/mod.rs` 16/40, `ffi/src/lib.rs` 13/47, `http-executor/src/lib.rs` 13/90, `connections/src/vault/port.rs` 9/17, `vault-adapter/src/lib.rs` 9/15 stb.

**Következmény az F2-re.** `caught/planned` = 217/300 = **72,33%**; `caught/(planned − unviable)` = 217/217 = 100%. Hogy a #169 „Rust mutation score >90%” célja melyik definícióra vonatkozik, **tulajdonosi döntés** (lásd 9.). A kapu mindkettőt kiírja.

## 4. Mit változtattam (CIC_Relay, commit `275ebea`, 13 fájl)

| Hely | Előtte | Utána |
|---|---|---|
| `scripts/quality_gate.py` (új) | — | terv-rekord, shard/chunk riport, `verify`, `check-coverprofile` |
| `mutation-pr.yml` | job-eredmények összesítése | `plan` rögzíti a tervet (Rust+Go), a shardok/chunkok riportot adnak, új `completeness` job, a `gate` ezt kötelezően kéri; `skipped` csak `PLAN_VALID_EMPTY`-vel fogadható el |
| `nightly.yml` | ugyanaz a hiány | ugyanaz; a `report` job `completeness != success` esetén hibát jelent |
| `scripts/gremlins_gate.py` | csak szöveges kimenet | `--report`: csomagonként `killed/lived/not_covered/timed_out` és `status`; **küszöbök változatlanok** |
| `scripts/mutation_plan.py` | a `#[cfg(test)]` változás 0 mutáns | diff-alapú felismerés → `rust_full`; `quality_gate.py` gate-logika |
| `verify.yml` | `go tool cover` az üres profilra is `0`-t ad | a profil külön ellenőrzése (`check-coverprofile`) a szám előtt |

## 5. F1–F3 megvalósítása

**F1 — azonosító-szerződés (`mutant-id/1`).** Az azonosító a cargo-mutants `name`-je. A terv az azonosítókat **rendezve és egyedien** tárolja, a digest a kanonikus alakból készül (nem a nyers listából), tehát a sorrend és a shard-kiosztás nem számít. Két különböző mutáns azonos azonosítóval **érvénytelen terv** (nem összeolvad). Szerződés-verzió, séma vagy eszközverzió eltérése piros.
**F2 — ítéletek (`mutation-policy/1`).** `caught`, `missed`, `timeout`, `unviable` külön számolva; a nevező a **tervezett** szám, az összegnek egyeznie kell vele. `missed` és `timeout` buktat; `unviable` **kiírt, nem buktat** (a kapu eddigi viselkedése). A kiskapu elleni védelem (review-megjegyzés): **nincs** futásidejű eltérés-kapcsoló; a szabály a kódban, verziózva van, és a `quality_gate.py` a gate-logika része (a módosítása a tervezőt FULL-ra eszkalálja és review-t igényel). Az `unviable` kezelésének megváltoztatása tehát szabály-verzióváltás, nem kivétel.
**F3 — terv-állapotok.** `PLAN_VALID_NONEMPTY`, `PLAN_VALID_EMPTY`, `PLAN_INVALID`, a kimenetben név szerint. Az üres-érvényes bizonyítéka a **terv-rekordba kötött** felsorolási eredmény: kilépési kód 0, a nyers kimenet 0 bájtja és annak sha256-ja, vagy a tervező kimondott döntése (`skipped` ok). Egy nulla bájtos fájl vagy egy hamisított `exit_code` nem elég. Hiányzó, sérült, digestjével nem egyező terv mindig piros. A `skipped` job nem bizonyíték: a kapu a terv állapotából dönt.

## 6. Negatív tesztek és a bukásuk bizonyítéka

| Futás | Eredmény | Nyers kimenet |
|---|---|---|
| az új tesztek (6 fájl), új kód | **171 passed**; a teljes `tests/test_tools` (helyben fordítható része) 205 passed, 3 skipped | `raw/new-tests-on-new-code.txt` |
| a workflow-, a tervező- és az enumeráció-tesztek a **régi** (`7ac6e80`) fán | **27 failed, 44 passed** | `raw/new-tests-on-old-code.txt` |

A 27 bukás oka **nem egyforma**, ezért szétválasztom:
- **A hibát magát reprodukálják** (a régi viselkedés elfogadja azt, amit nem szabadna):
  `assert 0 != 0` — a régi `gate` lépés minden job `success`-szel és `COMPLETENESS=failure`-rel is `exit 0`-t ad (stdout: `plan=success go=success rust=success baseline-guard=success`); `assert 'success' == 'failure'` — a régi nightly-riport sikert mond; `'false' == 'true'` — a régi tervező nem eszkalál `#[cfg(test)]`-re (3 teszt: a modulon belüli módosítás, az assert-törlés, a beszúrás az attribútum után; a másik kettő, a termékkód-módosítás és az új fájl, a régi fán is zöld).
- **Szerkezeti bukások** (a lépés/job nem létezik a régi fán): `no step 'rustplan'`, `no step 'goplan'`, `KeyError: 'completeness'` stb. Ezek azt igazolják, hogy az új szerkezet új, **nem** azt, hogy a régi hibás volt.
- A `test_quality_gate.py` a régi fán `ImportError`-ral bukna (a verifier nem létezett); ezt **nem** számítom bizonyítéknak, a verifier viselkedését a valódi adat (8.) és a 62+ egységteszt igazolja.

**Tanulság (PR-02 óta):** a bukás-teszteknél a konkrét hibaüzenetet ellenőrzöm; az `old3` fát commitoltam (különben `bad revision HEAD...HEAD` hamis bukást adott volna).

## 7. Küszöbök és baseline

`git diff` szerint a `gremlins_gate.py` küszöb-logikája (`DEFAULT`, `EPS`, `thresholds`, `evaluate`) **érintetlen**; a `.mutation-baseline.json` változatlan (`git diff --stat` üres); a `verify.yml` küszöbtábla (`min=…`) változatlan. A lefedettségi lépésben a **szám** továbbra is a `go tool cover`-ból jön.
Adósság-lista (nem oldottam meg küszöb-emeléssel): Go statement coverage **88,8%** (PR-01, a 90% alatt); **12 csomag** a mutációs baseline-ban a 90 alatti rögzített állapotú; Rust `caught/planned` **72,33%** (3. rész).

## 8. Lefedettségi riport: mért viselkedés (`raw/coverage-step-on-broken-profiles.txt`)

A mai `verify.yml` lépés (`set -euo pipefail`) valódi Go 1.26.10-zel:

| Profil | Mai viselkedés |
|---|---|
| üres fájl | `pc=[0]` → `FAIL: coverage below threshold` (**nulla mérésként olvassa**, csak a küszöb buktatja) |
| csak `mode:` sor | ugyanaz |
| `garbage` | `cover: bad mode line` (a `go tool cover` hibája) |
| hiányzó fájl | `cover: open …: no such file` |

Az új `check-coverprofile` ezt a profilt **önállóan** elutasítja (`no valid 'mode:'`, `no blocks`, `malformed block`), a küszöbtől függetlenül. A valódi, 2917 blokkos PR-01-es profilt elfogadja.

**Valódi adaton végzett hibainjektálás** (`raw/real-verify.txt`, 300 tervezett mutáns, 8 valódi shard): 1. teljes → zöld (`planned=300 caught=217 unviable=83`); 2. hiányzó shard → `missing shard report(s): [3] of 8`; 3. kétszer jelentett shard → `reported twice`; 4. egy hiányzó ítélet → `1 planned mutant(s) have no verdict`; 5. megváltoztatott név → `1 verdict(s) for mutants that are not in the plan`; 6. meghamisított terv → `PLAN_INVALID … does not match its digest`; 7. hiányzó terv → `PLAN_INVALID … missing`.

## 9. A PR-02 review két nyitott pontja

**`#[cfg(test)]` ugyanabban a forrásfájlban — mérve** (`raw/cfg-test-blind-spot.txt`): `http-executor/src/lib.rs` teszt-moduljának módosítása: **0** mutáns; egy assert **törlése** a teszt-modulban: **0** mutáns; ugyanazon fájl termékkódjának módosítása: 1 mutáns. A 0 mutánsos terv ráadásul *érvényes-üres* lenne, tehát az F3 sem fogná meg. A 11 érintett fájlban a teszt-modul a fájl hátsó felében kezdődik (`ffi/src/lib.rs`-ben két `#[cfg(test)]`-régió van: 588. és 1014. sor).
Megoldás (konzervatív, diff-alapú): ha a módosított `.rs` fájl diffje a régi vagy az új fájl első `#[cfg(test)]` során vagy az után ér el, a terv `rust_full`. Ez **túl-eszkalál**, ha termékkód követ egy ilyen attribútumot (biztonságos irány); **nem** eszkalál új fájlra (nincs mihez viszonyítani, a termékkódját az `--in-diff` mutálja). 5 teszt a próbák között.

**`tools/goastdump` (P8) — csak mérés és javaslat, a döntés a tulajdonosé** (`raw/goastdump-measurement.txt`): külön Go-modul (`go 1.22`), 505 sor (408 + 97 teszt); statement coverage **78,0%**; `gremlins v0.6.0` a modulon: 38 mutáns, 27 killed / 3 lived / 8 not covered, efficacy **90,00%**, mutant coverage **78,95%**, 4 másodperc. Megjegyzés: a gremlins a `testdata/sample.go`-t is mutálta. A root-modul alapküszöbével (90/90) a mutant coverage **elbukna**, tehát a bevonás baseline-bejegyzést vagy új teszteket igényelne. **A mai viselkedés (kimarad) változatlan.** Javaslat: ha bevonják, baseline-ratchettel induljon, és előbb a `testdata` kizárását kell tisztázni.

## 10. GitHub Actions

| Futás | Run id | Eredmény |
|---|---|---|
| Relay PR, zöld (`275ebea`) | **nem mérve** (a push és a PR a tulajdonosra vár) | — |
| Szándékosan hibás ág (`69e72d9`, 3. shard nem ad riportot) | **nem mérve** | — |

Amit a CI-futás fog mutatni (és most nem mérve): hogy a valódi GitHub-futásban a `completeness` jó, ha mindent beadnak, és piros, ha a 3. shard riportja hiányzik; hogy a `--in-diff`-es PR-útvonal azonosítói megegyeznek a tervével (a **teljes** útvonalat mértem valódi eszközzel, a diff-módot csak a fake-cargós lépésteszt és a `cargo mutants --in-diff` kézi próbák igazolják).

## 11. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A mutációs jobok ma nem adnak át riportot | implemented (mérve, szöveg) | `grep upload-artifact .github/workflows`: csak `verify.yml` | `grep -rn upload-artifact .github/workflows` a `7ac6e80`-on | alacsony |
| A valódi 8 shard a 300 tervezett mutánst pontosan egyszer fedi | implemented (valódi eszközzel mérve) | `raw/real-run-summary.txt`, `raw/real-verify.txt` 1. eset | `bash raw/realverify.sh` | `cargo-mutants 27.1.0`-ra érvényes; CI-ban nem mérve |
| Hiányzó/kétszeres shard, hiányzó/ismeretlen ítélet, meghamisított terv piros | implemented (valódi adaton) | `raw/real-verify.txt` 2–7 | uo. | alacsony |
| A jogos üres felsorolás 0 bájt, exit 0; a hibás exit 6 | implemented (mérve) | `raw/list-json-empty-and-failed.txt` | `bash raw/emptyjson.sh` | alacsony |
| A régi `gate` minden job `success` mellett is zöld hiányos mérésnél | implemented (mérve) | `raw/new-tests-on-old-code.txt`: `assert 0 != 0`, stdout `plan=success go=success rust=success…` | pytest a `7ac6e80` fán | alacsony |
| A `#[cfg(test)]` változásra az `--in-diff` 0 mutánst ad | implemented (mérve) | `raw/cfg-test-blind-spot.txt` | `bash raw/cfgtest.sh` | alacsony |
| A tervező felismeri a `#[cfg(test)]` változást | implemented (heurisztika, túl-eszkalál) | `test_cfg_test_*` (5 teszt) | pytest | közepes: a heurisztika fájl-szintű |
| Az `unviable` 83/300, a kapu kiírja, nem buktat | implemented | `raw/real-run-summary.txt`; `mutation-policy/1` | `quality_gate.py verify` kimenete | **a tulajdonosi döntés nyitott** |
| Az üres lefedettségi profilt a mai lépés `0`-nak olvassa | implemented (mérve) | `raw/coverage-step-on-broken-profiles.txt` | `bash raw/covcur.sh` | alacsony |
| Az új `check-coverprofile` a törött profilt a küszöbtől függetlenül elutasítja | implemented | `test_a_broken_coverage_profile_is_neither_zero_nor_success` (5 eset); valódi profilon elfogad | pytest | alacsony |
| A küszöbök, padlók, baseline változatlanok | implemented (diffben ellenőrizve) | `git diff` a `275ebea`-n; `.mutation-baseline.json` változatlan | `git diff 7ac6e80 275ebea -- .mutation-baseline.json` | alacsony |
| A `goastdump` a root-küszöbökkel elbukna | implemented (mérve, nem a gate-en át) | `raw/goastdump-measurement.txt` | `bash raw/goastdump.sh` | a gate saját futtatását nem mértem |
| A CI-ban zöld a `275ebea`-n | **nem mérve** | — | a Relay PR futása | magas, amíg nincs futás |
| A CI-ban piros a hibás ágon | **nem mérve** | — | a bizonyító ág futása | magas, amíg nincs futás |
| A diff-módú (`--in-diff`) shard-azonosítók egyeznek a tervvel | **nem mérve valódi eszközzel** | csak a fake-cargós lépésteszt | PR-futás | közepes |
| A heti `mutation.yml` (csak Go) | **nem kezelve** | — | PR-07 | alacsony |

## 12. Nyitott, tulajdonosi döntésre

1. **`unviable` kezelése:** 83/300 (27,7%). Most nem buktat, kiírt. Ha bukjon, vagy ha a pontszám nevezője a `planned − unviable` legyen, az szabály-verzióváltás (`mutation-policy/2`) és külön jóváhagyás.
2. **Rust mutation score definíciója a 90%-os célhoz** (72,33% vs 100%).
3. **`tools/goastdump`** bevonása.
4. Eszköz-verzió pin, nightly horgony, `deadcode` lépés, nightly `security` bukás (#160): változatlanul külön döntések; nem nyúltam hozzájuk.
5. A heti `mutation.yml` teljességi bekötése (PR-07).

## 13. Nem mérve / korlátok

- GitHub Actions: lásd 10.
- **Shard-fedezet a 8-as plafon fölött** (>320 mutáns): valódi eszközzel nem mértem; a verifier a shard-számtól független (egységteszt: 8 shard 5 mutánsra), és a 300-as terv a plafon alatt van.
- A valódi, egy folyamatban futó FULL és a külön shardok **ugyanazt** a 300-as halmazt adják, a diff-módú shard-futást (`--in-diff … --shard`) valódi eszközzel nem futtattam.
- A teljes repó `pytest`-je helyben nem fordítható (`requests` hiányzik a scratch venv-ben); a CI `python` jobja dönt.
- A Go-oldali teljesség a gremlins valódi futásával (chunk-riport) helyben nem mérve; a `gremlins_gate.py --report` a fake `gremlins`-szel tesztelt, a valódi kimenet-elemzés a már meglévő `measured()`.

## 14. Aláírás és push

A commitok a Vault `commit-msg` hook futásával készültek (aláírási metaadat a commit-üzenetben); az érvényességet **nem ellenőriztem**. Co-Authored-By vagy AI-re utaló sor nincs. A push-okat a tulajdonos futtatja (a környezet elutasítja). A szándékosan hibás ágból **nem** nyitok mergelhetőnek tűnő PR-t: draft, „DO NOT MERGE” címmel, a munkaágra mutatva, és futás után lezárom.
