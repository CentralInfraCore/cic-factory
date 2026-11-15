# PR-05 jelentés — seeded defectek és a CI önellenőrzése

Job: `relay-ci-parity-05-seeded-defects` · a CIC_Relay #169 PR-05 lépése. Alap: `ref/owner-decisions-pr05-2026-11-15.md`, a spec (cic-factory #56, `cefa9a5`).
**Report-only:** nincs új blokkoló kapu, nincs tesztkihagyás, nincs toolchain-csere. A `scripts/gremlins_gate.py`, a `.mutation-baseline.json` és a coverage-baseline a diffben **nem szerepel** (`git diff --name-only origin/main...HEAD | grep -cE 'gremlins_gate|mutation-baseline|coverage-baseline'` = 0).
A Relay-implementáció mergelése a tulajdonos döntése szerint **HOLD** a következő review-ig; ebben a jelentésben semmi nem állítja, hogy mergelt.

## 1. Vizsgált állapot

| | |
|---|---|
| CIC_Relay `main` | `9629baf` (tartalmazza a PR-04 merge-et és a `d38a1d5`-öt) |
| Relay munkaág | `feature/relay-ci-parity-05-seeded-defects`: `8dd858b` (első implementáció) → **`e5e2ccd`** (F1 javítás) → Relay PR **#183**, **MERGELVE** merge-committal **`7386565669c84b3c2477425e6b0d3332e752432a`**, az ellenőrzött `e5e2ccd` fejhez kötve (`--match-head-commit`) |
| Bizonyító (piros-út) ág | `ci-proof/relay-ci-parity-05-red-path` **`c1a23d2`** → Relay **#184** (draft, a `8dd858b`-re építve) — **szándékosan hibás; LEZÁRVA merge nélkül** |
| Diff (`8dd858b`; az F1 commit +124/−3, 3 fájl) | 8 fájl, +1627/−65: `scripts/object_model.py`, `scripts/seeded_defects.py`, `scripts/mutation_plan.py` (+1 sor), a workflow, 4 tesztfájl; termékkód nincs |
| Mérési környezet | pinelt `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`, `golang:1.26.10`, konténerek `--user "$(id -u):$(id -g)"`-rel, cache `~/.cache/relay-ci-parity-05` (felhasználói tulajdon, 4,2 GB) |
| **A klón tisztasága** | **Nem volt tiszta.** A `CIC_Relay-pr05` klónban `git status --short` 212 bejegyzést mutat: 189 módosított és 23 nem követett `.yaml` fájl (a korábbi PR-ekben is megfigyelt jelenség). Az ok **nem megállapított**; a CI a pusholt commitot futtatta, nem ezt a munkafát. A diff-ellenőrzések `origin/main...HEAD` alapúak, ezért ettől függetlenek. |
| Aláírás | friss klón: placeholder identitás, Vault-aláírás nincs; a tulajdonos pótolja |
| Futtatás | ebben az interaktív sessionben (nem `run-job.sh`) |

## 2. A kiindulópont mérése (PR-04 verifier, valódi fixture-ökön) — `raw/baseline-weaknesses.txt`

| # | Gyengeség | Mért |
|---|---|---|
| W1 | darabszám ≠ halmaz | egy objektum cseréje azonos darabszámnál: L1 OK, L2 OK, **L3 PARTIAL** (FAIL kellett volna) |
| W2 | L3 sosem PASS | becsületes rekord minden bemenettel: mindig `PARTIAL` (a Rust-oldalnak nincs független leltára) |
| W3 | újrapecsételt értékhamisítás | `18/26 → 26/26`, digest és összegzés újraszámolva: **L1 OK, L2 OK, L3 PARTIAL**; pecsételés nélkül csak az L1 fogja meg |
| W4 | duplikátum | azonos id kétszer: L1 FAIL; **más id ugyanarra a forrásobjektumra**, darabszám kiegyenlítve: mindhárom szint átmegy |
| W5 | determinizmus | a `MEASURED` lefedettségi mező nem hordoz `runs`-t |

## 3. Mit változtattam (`scripts/object_model.py`, `8dd858b`)

- **L2 újralevezetés:** a rekord értékeit a bemenetekből másodszor, **más algoritmussal** számolja ki (Go: rendezett függvénykezdetekre `bisect`; Rust: régiók újraaggregálása), és hasonlítja (`REDERIVATION_MISMATCH`). Nem ismétli ugyanazt a transzformációt.
- **L3 halmazazonosság:** Go: független leltár (regex a 0. oszlopú `func` sorokra, **nem** `go/ast`); Rust: csak szabad függvények; impl/trait/mod/beágyazott `fn` `unmapped` → a Rust marad `PARTIAL`. Szimmetrikus különbség (`SET_MISMATCH`), `MISSING_UNIT`. **`COMPLETE_FOR_SCOPE` csak igazolt teljességnél.**
- **Saját diagnosztikai kódok:** DUPLICATE_ID, DIGEST_MISMATCH, COMMIT_MISMATCH, INPUT_DIGEST_MISMATCH, REDERIVATION_MISMATCH (az A.5b külön kódja), SET_MISMATCH, MISSING_UNIT, MISSING_FIELD, BAD_DETERMINISM.
- **Sémaverzió:** `object-evidence/1` → **`/2`** (új kötelező `runs`, `determinism`). Döntés: a /2 nem fogadja el a /1-et; a rekord rövid életű CI-artifact, nincs tárolt /1 fogyasztó (nem mért: külső fogyasztó hiánya csak a repóra igaz).
- **Determinizmus-jelölés:** `NOT_SHOWN` | `OBSERVED_STABLE`, `STABLE_MIN_RUNS = 20`. A 20 azonos futás **megfigyelt stabilitás**, nem matematikai determinizmus. Indok: a hármas szabály szerint 20 azonos futás 95%-os biztonsággal kizárja a ≳15%-os billegési arányt; ennél ritkább billegést nem zár ki.
- **Builder-javítás (valódi hiba, a re-derivációval találtam a valós main-en):** a csak nulla-utasításos blokkú Go objektum (pl. `pkg/obs.NoopSink.Record*`, üres törzs) `MEASURED 0/0` volt; most `NOT_APPLICABLE NO_STATEMENTS`. R-teszt: `test_r_pr05_an_object_with_only_zero_statement_blocks_is_not_a_measurement`.

## 4. Seeded defect harness (`scripts/seeded_defects.py`) — valódi rekord, valódi bemenetek

Eredmény a valós Relay `main` rekordján (675 objektum), helyben és a CI-ban azonos — `raw/seeded-defects.txt`, `raw/ci-183-green-object-evidence-43692319961.txt`:

| Eset | Hiba | Elvárt | Kapott kód |
|---|---|---|---|
| kontroll | becsületes rekord | L1 OK, L2 OK, L3 PARTIAL | egyezik |
| A.1 | objektum törölve (újrapecsételve) | L3 FAIL | `SET_MISMATCH` |
| A.2 | nem létező objektum beszúrva | L3 FAIL | `SET_MISMATCH` |
| A.3 | csere, darabszám azonos | L3 FAIL | `SET_MISMATCH` |
| A.4a | duplikátum, azonos id | L1 FAIL | `DUPLICATE_ID` |
| A.4b | ugyanaz a forrásobjektum más id alatt, darabszám kiegyenlítve | L3 FAIL | `SET_MISMATCH` |
| A.5a | érték módosítva, nincs újrapecsételés | L1 FAIL | `DIGEST_MISMATCH` |
| A.5b | érték módosítva **és újrapecsételve** | L2 FAIL | `REDERIVATION_MISMATCH` |
| A.6 | másik commit bizonyítéka | L2 FAIL | `COMMIT_MISMATCH` |
| A.7 | hamisított bemeneti digest | L2 FAIL | `INPUT_DIGEST_MISMATCH` |
| A.8a | kötelező mező hiányzik | L1 FAIL | `MISSING_FIELD` |
| A.8b | egy kötelező egység minden objektuma hiányzik | L3 FAIL | `MISSING_UNIT`, `MUTANT_FUNCTION_MISSING` |
| A.9a | egyszer látott lefedettség „stabilnak" mondva | L1 FAIL | `BAD_DETERMINISM` |
| A.9c | hamis stabilitás (`runs=20`, `OBSERVED_STABLE`), újrapecsételve (az F1 javítással, `e5e2ccd`) | L2 FAIL | `REDERIVATION_MISMATCH` |
| A.9b | futások között eltérő lefedettség | NOT_STABLE | egyezik |

A rekord stabilitása a valós main-en: `NOT_STABLE`, 0/662 mért lefedettség látott ≥ 20 futásban (mind egyszeri). **A rekord tehát nem állítja stabilnak magát.**

### 4a. Review F1 — hamis stabilitási állítás (A.9c), `e5e2ccd`

A review megállapította, hogy a `_cmp_cov` nem hasonlította össze a `runs` és `determinism` mezőket: egy egyszeri mérés rekordja `runs=20`, `OBSERVED_STABLE` állítással, újrapecsételve átment volna L1-en és L2-n. **A hiba valódi volt** (a régi verifieren az A.9c `L2=BOUND_TO_INPUTS`, kód nélkül átcsúszik: `raw/f1-tests-on-previous-verifier.txt`, 5 új teszt bukik).

| Elem | Javítás |
|---|---|
| bemenetek | az építő minden ismételt Go-profilt bemenetként köt (`go-coverprofile-repeat:<unit>:<i>`), digesttel |
| újralevezetés | `derive_go_coverage` / `derive_rust_coverage` a kötött profilokból számolja a `runs`-t és a `determinism`-t |
| összehasonlítás | `_cmp_cov` hasonlítja a `runs`-t és `determinism`-t is (`REDERIVATION_MISMATCH`) |
| új eset | **A.9c**: újrapecsételt hamis stabilitás → `L2 FAIL REDERIVATION_MISMATCH`; saját „fog" (a `runs/determinism` összehasonlítás kiiktatására az A.9c átcsúszik) |

Mérve: helyben a valós rekordon (`raw/f1-real-record-local.txt`) és a CI-ban `e5e2ccd`-n (`object-evidence` **43698718231**, `raw/ci-183-f1-green-object-evidence-43698718231.txt`): a becsületes verdiktek változatlanok (L1 OK, L2 OK, L3 PARTIAL, `NOT_STABLE`), mind a 14 eset a várt szinten és kóddal elkapva.

**Dokumentált korlát (review):** húsz bemeneti profil megléte **nem bizonyít húsz független végrehajtást**: a verifier a kötött fájlokból számol, de azt, hogy a fájlok tényleg különálló futásokból jöttek, nem látja. A futások eredetének igazolása az evidence provenance (PR-08) feladata; addig az `OBSERVED_STABLE` csak annyit állít, hogy a megadott profilok azonosak.

### 4b. Review F2 — a piszkos munkafa

`raw/f2-dirty-clone-probes.txt`: tiszta klónon sem a klónozás, sem az aláíró commit-hook, sem a `pytest tests/`, sem a teljes `go test ./...` nem hozta létre a módosított `.yaml` fájlokat. **Az ok nem megállapított**; a tartalom a `tools/go.meta.gen.py` kimenetére hasonlít (hipotézis, nem bizonyíték: külső folyamat generálja a companion YAML-okat). A mérések tiszta klónban (`relay2`) futottak, ahol csak a PR-05 fájlok tértek el.

## 5. A harness ellenpróbája és a CI piros útja

**Helyi „fogak" tesztek:** a `test_seeded_defects.py` 10 horgonya egy izolált **másolatban** iktat ki egy-egy ellenőrzést; a megfelelő esetnek át kell csúsznia. A termékfát nem módosítja.

**Valódi piros CI-futás (#184, `c1a23d2`):** a Go halmaz-összehasonlítás (`if have != want:`) helyett `if False:` — szándékos hiba.

| Futás | Eredmény | Bizonyíték |
|---|---|---|
| `object-evidence` **43692321957** | **failure**, a bukó lépés: „Seeded defects on the real record"; **A.1, A.2, A.3, A.4b nem elkapva** (L3 PARTIAL, nincs kód), a többi eset OK; L1/L2 zöld | `raw/ci-184-red-object-evidence-43692321957.txt` |
| `verify` **43692321934** (`python` job) | failure, **9 teszt bukik**, mind a halmazellenőrzéshez/fogakhoz tartozik: A.1, A.2, A.3, A.4b, az összes-eset teszt, az R-teszt (count-only vs. set), a különbség-megnevezés, a másolat-zöld kontroll, a „go set comparison" fog | `raw/ci-184-red-python-43692321934.txt` |
| `mutation-pr`, `manifest-check` | success | — |

Zöld (#183, `8dd858b`, az első implementáció): `object-evidence` **43692319961**, `verify` **43692319972**, `mutation-pr` **43692319971**, `manifest-check` **43692319946** — mind success. Az `object-evidence` workflow report-only, **nem required check**.
**Zöld az F1 javítás után (#183, `e5e2ccd9943aafe35487d9c6da5f8c4447723f4b`):** `verify` 43698718316, `mutation-pr` és a shardok 43698718242, `manifest-check` 43698718275, `object-evidence` 43698718231 — mind success (25/25 check).
**Main a merge után (`7386565669c84b3c2477425e6b0d3332e752432a`):** `verify` 43701778146 success, `manifest-check` 43701778106 success, kézi `object-evidence` 43701788247 success (`raw/ci-main-7386565-object-evidence-43701788247.txt`: L3 `PARTIAL`, a harness minden kontrollja becsületes, minden hiba elkapva). A `mutation-pr` PR-only, a mainen nem futott.
Megjegyzés: a #184 két piros workflow-ja a draft ág saját vizsgálati eredménye; a #183-at nem érinti.

## 6. R- és N-tesztek bizonyítéka

- **R-tesztek a régi (PR-04) fán** — `raw/r-tests-on-old-code.txt`: **3 bukik, 43 átmegy**: `test_n11_a_block_inside_one_object_is_attributed`, `test_n9_an_object_whose_coverage_differs_between_runs_is_nondeterministic`, `test_r_pr05_an_object_with_only_zero_statement_blocks_is_not_a_measurement`. A harmadik a valódi builder-hibát mutatja; az első kettő bukási okát (feltehetően a `runs`/`determinism` mezők hiánya) a nyers kimenet hibaüzenetéből ebben a jelentésben nem elemeztem külön.
- **A.3 régi vs. új:** régi: `L3 PARTIAL` (átmegy); új: `L3 FAIL SET_MISMATCH` (§2 W1, §4 A.3).
- **N-tesztek:** valódi fixture-ök elfogadása, konkrét elutasító üzenetek, fogak (§5).
- Helyben a kapcsolódó fájlokon 325 teszt zöld; black, isort, ruff, mypy, bandit tiszta. A teljes repó `pytest`-jét a CI `python` jobja futtatta (#183: zöld). **Nem mért:** ebben a klónban a rendszer-pythonban nincs `pytest`; a helyi futásokat a mérési venv-ben végeztem.

## 7. Független leltár értékelése

**Go:** megvalósítva (regex, `go/ast` nélkül), a valós main-en halmazazonos: root 464, goastdump 15 (`proven: … IDENTICAL … a set, not a count`).

**Rust — döntés: indokoltan `PARTIAL`.** Mérés (`raw/rustdoc-compare.txt`, pinelt `nightly-2026-07-01`, rustdoc JSON `format_version 60`, kb. 41 s, 7 crate): 293 függvényelem (53 szabad, 85 inherent, 155 trait); a rekordban 196 objektum; (crate, név) szerint **172 egyezik**, **121 rustdoc-elem `#[derive]`-generált**, **24 rekord-objektum nincs a rustdocban**. Osztályozó réteg nélkül a pontos azonosság nem állítható, ezért a Rust marad `PARTIAL`; a `PARTIAL` nincs átnevezve. A `syn`-alapú leltár **nem mért**. Szabad függvényekre van független leltár.

**Megállapítás (nincs javítva, `object-id` szerződési döntést igényel):** 5 `#[no_mangle]` függvény crate nélküli id-t kap (`rust:cic_ffi_abi_version`, `_connection_request`, `_free`, `_ping`, `_run_flow`).

## 8. A három nemdeterminisztikus Go-objektum — `raw/determinism-go-20runs.txt`

20 azonos futás ugyanazon a fán (`9629baf`), 2917 blokkból **3 változik**, mind `core/nexus/operator/watcher.go`: 303–305 (3/20 futásban fedett), 310–312 (2/20), 373–375 (5/20); a `scanDir` és a `PollingWatcher.Watch` hibaágai. **Ok-besorolás:** időzítési verseny a 10–20 ms-os polling goroutine és a teszt-takarítás között — a forrásból és a tesztekből **következtetve, nem nyomkövetve**. A `SubprocessWorker.Decrypt` ebben a 20 futásos mintában nem változott; hogy ritkábban változik-e, nem megállapított. A kizárás nem a nemdeterminizmus megoldása.

## 9. A #169 „Self-testing" 1–8. próbájának leképezése

| # | Próba | Fedés |
|---|---|---|
| 1 | gyengített teszt-készlet → a lefedettségi kapu piros | **Nem fedett** a PR-05-ben: valós eszköz + a termékfa szándékosan gyengített másolata kell; a költség nem mért. Nyitott (PR-06 jelölt) |
| 2 | túlélő mutáns → a mutációs kapu piros | **Nem fedett** ugyanezért; a PR-03 gate-tesztjei csak egységteszt-szintűek |
| 3 | hiányzó shard → a FULL nem lehet sikeres | **Hivatkozással:** PR-03 completeness-kapu + a 7 hibainjektálás (PR-03 jelentés); a valódi piros CI-futás a PR-04-ben a `#178`; egységteszt-szintű + valós CI egy esetre |
| 4 | duplikált vagy hamisított verdikt elutasítva | **Fedett valós rekorddal:** A.4a, A.4b, A.5a, A.5b |
| 5 | hiányzó/olvashatatlan lefedettségi riport nem nulla és nem siker | **Hivatkozással:** PR-04 `test_a_failed_inventory_file_is_an_error` stb. (egységteszt); valós artifacton nem |
| 6 | hibás tervező nem hagyhat ki tesztet | **Hivatkozással:** PR-02 tervező-tesztek; a PR-05 `GATE_LOGIC_PATHS` bővítés a verifier-t is FULL-eszkalálóvá teszi (egységteszt) |
| 7 | hibás evidence nem lehet `VERIFIED` | **Fedett:** A.1–A.9 valós rekorddal; a kimenet nem használ „VERIFIED" szót, szintenként állít |
| 8 | módosított/ismeretlen eszközverzió használhatatlan | **Nem fedett** új esettel; a PR-02/04 verziópin-ellenőrzése csak egységteszt |

## 10. Claim-evidence tábla

| Állítás | Státus | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A 13 eset a várt szinten és kóddal bukik (az A.9c-vel 14, lásd 4a) | mért | `raw/seeded-defects.txt`, CI 43692319961 (`8dd858b`) | valódi rekord, pinelt kép | alacsony |
| Az A.9c (hamis stabilitás) a régi verifieren átcsúszik, az újon elkapva | mért | `raw/f1-tests-on-previous-verifier.txt`, CI 43698718231 (`e5e2ccd`) | régi és új verifier | a `runs` a kötött profilokból jön, a futások függetlenségét nem bizonyítja |
| A harness piros, ha a verifier gyengül | mért | CI 43692321957 (`c1a23d2`) + 43692321934 | szándékosan hibás ág | a gyengítés egyetlen fajtája (Go halmaz); a többi csak „fogak"-teszt |
| A.3 régen átment, most bukik | mért | `raw/baseline-weaknesses.txt` vs. §4 | régi és új fa | alacsony |
| R-tesztek a régi fán buknak | mért | `raw/r-tests-on-old-code.txt` (3/43) | régi fa másolata | alacsony |
| Go-leltár halmazazonos | mért (main `9629baf`) | verify.txt | független regex | a regex a függvények szintaxisára épít |
| Rust L3 `PARTIAL`, indokolt | mért | `raw/rustdoc-compare.txt` | rustdoc JSON | `syn` nem mért |
| 3 nemdeterminisztikus objektum | mért, ok következtetett | `raw/determinism-go-20runs.txt` | 20 futás | az ok nem nyomkövetett |
| `STABLE_MIN_RUNS = 20` elégséges | megfigyelés, nem bizonyíték | hármas szabály | statisztikai becslés | ritka billegés átcsúszhat |
| Termékkód, kapuk, küszöbök változatlanok | mért | diff-ellenőrzés (§ fent) | `git diff --name-only` | alacsony |
| Az 1., 2., 8. próba lefedve | **nem** | §9 | — | nyitott |

## 11. Nyitott döntések és amit nem mértem

- Tulajdonosi döntés: az 1., 2., 8. próba (valós eszköz + gyengített termékfa-másolat) külön PR-ban? A költség nem mért.
- `object-id` szerződés a 5 crate nélküli `#[no_mangle]` id-ra.
- A Rust független leltár a `syn`-nal: nem mért.
- A `unviable` figyelmeztetési szint (33% javaslat), `mutation-policy/3`, `gobco` (licenc) továbbra is HOLD; a heti `mutation.yml` bekötése PR-07.
- A Relay #183 **mergelve** (`7386565`, a tulajdonos kifejezett utasítására, a review MERGE GO-ja után); a #184 lezárva merge nélkül.
- A futások eredetének igazolása (húsz profil ≠ húsz független futás): PR-08 (evidence provenance).
- Takarítás (tulajdonos): `sudo rm -rf ~/.cache/relay-ci-parity-04/{target-nightly,target,target-pt,gp,gc}` és a PR-03 `target-full`. A `backup/pr04-before-rebuild` ág megmarad. A `meta.yaml` státuszát nem érintettem.
- A klón 212 piszkos bejegyzésének oka nem megállapított (§4b).
