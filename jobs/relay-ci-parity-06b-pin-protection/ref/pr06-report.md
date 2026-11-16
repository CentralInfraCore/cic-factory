# PR-06 jelentés — önellenőrző próbák (1, 2, 8) és bizalmi határ negatív tesztek

Job: `relay-ci-parity-06-trust-boundary-ffi-negative-tests` · a CIC_Relay #169 PR-06 lépése. Alap: spec (cic-factory #60, `8b48e5c`), `ref/owner-decisions-pr06-2026-11-15.md`.
**Új küszöb, baseline, blokkoló kapu és toolchain-csere nincs; termékkód nincs** (a `ffi/src/lib.rs` csak a `#[cfg(test)]` blokkban változott). A job `meta.yaml` státuszát nem érintettem. A Relay PR-ok mergelése a tulajdonos döntése (MERGE HOLD az együttes review-ig).

## 1. Vizsgált állapot

| | |
|---|---|
| CIC_Relay `main` | `7386565669c84b3c2477425e6b0d3332e752432a` (PR-05 merge-commit; az első mérések bázisa) → **`e43f2a826ca2adee717a0a7ae18ca220016fb7c1`** (PR #190 után; az aktuális integrált állapot, lásd 5b.) |
| Relay munkaág / PR | `feature/relay-ci-parity-06-trust-boundary-ffi-negative-tests` → **#191**, fej **`45427e92a2561fafcfd4e78700b801d2f97d4ed4`** (a `main` `e43f2a8` beolvasva; a korábbi mérési fej `62f300451186fda988a152a66259ba6ad1747e8d`) (`--base main`, nem mergelve; a fej története: `0fe1ccc` → `ab411d1` → `be7c2e4` → `62f3004`, az első iterációk run id-i a `raw/ci-first-iteration/` mappában) |
| Bizonyító (piros-út) PR-ok | **#192** `ci-proof/…-red-selftest` `7666846b6eee80f1419c9f7b370789711b747dee` · **#193** `…-red-tools` `c444e2d030f2038e96f85fc9ca142c2f813496b2` · **#194** `…-red-identity` `97e0860bfe51152740565ebb5ef55ebfb61d64b4` (újraépítve az új fejre; a korábbi fejek: `e1bd162`, `3ddcd56`, `4bb1699`, az alábbi 5. szakasz ezekre vonatkozik) — mind draft, **DO NOT MERGE**, a munkaágra mutatnak, **szándékosan hibásak**; a lezárás a bizonyíték rögzítése után, merge nélkül történik |
| Diff a `main`-hez (`62f3004`) | 22 fájl, **0 `.yaml`**; a `scripts/gremlins_gate.py`, `.mutation-baseline.json`, `scripts/baseline_guard.py` **0 sor**; a négy meglévő workflow-ban (`verify`, `mutation-pr`, `mutation`, `nightly`) **0 törölt sor**, csak lépés-hozzáadás; termékkód: a `ffi/src/lib.rs` egyetlen hunkja a `mod tests` blokkban (1160. sortól), a `cmd/relay` diffje csak az új tesztfájl |
| Mérési környezet | `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`, `golang:1.26.10` (helyben), a CI a `go1.26.11`-et használja; konténerek `--user "$(id -u):$(id -g)"`-rel, cache `~/.cache/relay-ci-parity-06` (3,7 GB, felhasználói tulajdon, `sudo` nélkül törölhető) |
| A klón tisztasága | friss klón: `git status --short \| wc -l` = **0** a klónozás után és a mérések előtt. A munka során a munkafa **161 generált `.yaml` bejegyzéssel** (150 módosított + 11 nem követett companion) piszkolódott: lásd 8. A méréseket másolatokon (`copy_tree`) és konténerben futtattam, a CI a pusholt commitot futtatta |
| Aláírás | friss klón: a commit-hook a tulajdonos Vault-kulcsával aláírt (Vault-aláírás ténylegesen volt); a CICSourceCA-ellenjegyzés a tulajdonosé |
| KB (MCP) | a `cic-graph` `kb_status` és `search_nodes` hívása a session alatt „Invalid request parameters" hibát adott; KB-állításra nem hivatkozom, a státusz fájl- és tesztszintű bizonyítékra épül |
| Futtatás | interaktív sessionben, nem `run-job.sh` |

## 2. Összefoglaló

| Rész | Eredmény | Bizonyíték |
|---|---|---|
| **A.8** eszközverzió fail closed | kész, minden mérő jobban | #191 zöld (27/27), `raw/ci/191-tools-pinned.txt`; #193 piros a várt okból |
| **A.1** gyengített suite → a valódi kapu piros | kész (Go + Rust) | #191 `gate-selftest` zöld, `raw/ci/191-gate-selftest.txt`; #192 piros |
| **A.2** túlélő mutáns → a valódi kapu piros | kész (Go + Rust) | ugyanott |
| **B** negatív tesztek (modul-azonosság, FFI) | kész | #191 zöld, `raw/teeth-*.txt`; #194 piros a várt okból |
| **B** hiánytérkép mind a négy területre | kész (4. szakasz), néhány sor név szerinti keresésen alapul | 4. szakasz |

## 3. A.8 (8. próba) — minden minőségi döntést befolyásoló eszköz fail closed

**Kiindulópont (mért, forrásolvasás):** az `object-evidence` rekord rögzítette az eszközverziókat, de **bármelyiket elfogadta** (csak `unknown`/üres bukott). A mutációs kapu csak a cargo-mutants **tervezett és mért** verzióját hasonlította egymáshoz; `gremlins`, Go, `cargo-llvm-cov` és `rustc` ellenőrzése a kapukban **nem volt**. A `gremlins` bináris `gremlins version dev linux/amd64`-et ír magáról: a verzió a bináris kimenetéből **nem állapítható meg**.

**Megoldás:** `.measurement-tools.json` (`measurement-tools/1`) rögzíti az eszközöket; `scripts/quality_gate.py check-tools` kilép 1-gyel:
- **UNUSABLE** — a verzió ismert, de nem a pinelt (`[TOOL_UNUSABLE]`);
- **UNVERIFIABLE** — a verzió nem állapítható meg, hiányzik, `unknown`, vagy az eszköz nincs pinelve (`[TOOL_UNVERIFIABLE]`, `[TOOL_NOT_PINNED]`).
A pin értékek a main `object-evidence` futásából valók (run 43701788247): `go1.26.11`, `rustc 1.96.1`, `cargo-llvm-cov 0.9.1`, `cargo-mutants 27.1.0`, `objinventory/1`, `c++filt` Ubuntu 2.46. A `gremlins` a **modulverzióval és a tartalom-hash-sel** van pinelve (`go version -m`: `v0.6.0 h1:3G2ROO0I…`).

| Job | Mérés előtt ellenőrzött eszközök | Zöld futás (#191, felület, run) |
|---|---|---|
| `mutation-pr` plan | rustc, cargo-mutants (`mutation-rust`) | 43726067141 |
| `mutation-pr` go (6 chunk) | go, gremlins (`mutation-go`) | 43726067141 |
| `mutation-pr` rust (8 shard) | rustc, cargo-mutants (`mutation-rust`) | 43726067141 |
| `verify` coverage (Go) | go (`coverage-go`) | 43726067164 |
| `verify` rust (lefedettség) | rustc, cargo-llvm-cov (`coverage-rust`) | 43726067164 |
| `mutation.yml`, `nightly.yml` (go, rust, plan) | ugyanez | **nem futott** ebben a PR-ban (ütemezett workflow-k): csak a szöveg-szintű teszt és az `quality_gate` egységtesztek fedik |
| `object-evidence` verifier | a rekord `tools` mezője (`object-evidence`, `TOOLS_PINNED`, `--mode quality`) | 43726067147 |
| `gate-selftest` go / rust | go, gremlins / rustc, cargo-llvm-cov, cargo-mutants (`gate-selftest-go` / `-rust`) | 43726067136 |

Tesztek: eszközönkénti elutasítás (módosított, hiányzó, `unknown`, nem pinelt), rossz pin-fájl hiba (nem üres pinhalmaz), pin–workflow egyezés (`go-version`, `gremlins@`, `rust-toolchain.toml`), **minden mérő jobban** ott van a lépés és **a mérés előtt** (`test_every_job_that_measures_checks_its_tools_before_it_measures`), seeded esetek `P8.a–P8.d` pozitív kontrollal és „foggal".

**Korlátok (kimondva):**
- A verifier a rekord **deklarált** verzióját veti össze a pinnel; hogy az eszköz tényleg az volt, az provenance (PR-08).
- A pin-fájl a PR fájlfáján van: egy PR módosíthatja. A `baseline-guard` a `gremlins_gate.py`-t és a baseline-t védi a bázisról, a pin-fájlt **nem**. A fájl változása gate-logic változás (a tervező FULL-ra eszkalál), de ez nem védelem a rosszindulatú PR ellen. **Külön, nyomon követett feladat: CIC_Relay issue #195** (a review elfogadási kritériumaival: a PR ne módosíthassa egyoldalúan az ellenőrzés referenciáját; elkülönített jóváhagyási út a pin-frissítésnek; a manipuláció elutasítását negatív proof PR bizonyítja; az ellenőrzés rögzíti a felhasznált referencia commitját és digestjét). A PR-06-ba építése a review döntése.
- `cargo-mutants` és `cargo-llvm-cov` telepítése továbbra is pin nélkül megy (`taiki-e/install-action`): egy új kiadás a kapukat **fail-closed pirosra viszi** (ez a kért viselkedés, de üzemeltetési következménye van: a pin frissítése kézi lépés).

**A review utáni szerződés (F1, F2; `62f3004`):**
- **F1 — a kihagyott eszközdeklaráció nem csúszhat át.** A pin-fájl `surfaces` része felületenként megnevezi a **kötelező** eszközkészletet (`coverage-go`, `coverage-rust`, `mutation-go`, `mutation-rust`, `gate-selftest-go`, `gate-selftest-rust`, `object-evidence`). A `check-tools` **kötelező `--surface`-t** kap; a felület egy kötelező eszközének hiánya `UNVERIFIABLE` (`[TOOL_UNVERIFIABLE] … it is not declared`). Minden workflow-hívás megnevezi a felületét (`raw/ci/191-tools-pinned.txt`: `tools pinned (mutation-go): go=…, gremlins=…`). Tesztek: **minden felület minden kötelező eszközére egy negatív eset** (az eszköz kihagyva → exit 1, `UNVERIFIABLE`, az eszköz neve a kimenetben) és mellette a teljes készlet **pozitív kontrollja**; hiányzó `--surface` → exit 2; ismeretlen felület → hiba; a per-job teszt ellenőrzi, hogy minden mérő job **pontosan** a felületének eszközeit deklarálja.
- **F2 — a két mód explicit.** `object_model.py verify --mode quality|diagnostic` (kötelező). `quality`: a pin-konfiguráció **kötelező**, hiánya `UNVERIFIABLE` (`[TOOL_PINS_MISSING]`) és nem nulla kilépés; `diagnostic`: a pinek elhagyhatók, az eredmény `NOT_CHECKED`, ami **nem pass**. Az `object-evidence` workflow `--mode quality`-vel fut (43726067147: `tools TOOLS_PINNED`, `P8.a`–`P8.e` OK). Seeded eset `P8.e` pozitív kontrollal és „foggal" (`raw/ci/191-object-evidence.txt`).

## 4. A.1 és A.2 (1. és 2. próba) — a valódi kapu utasítja el

`scripts/gate_selftest.py` + report-only `gate-selftest.yml` (`pull_request` a gyakorolt fájlokra és kézi indítás; **nem required check**, küszöböt nem állít). A kapu a **valódi**:
- Go lefedettség: a `verify.yml` „Per-package coverage thresholds" lépésének `run:` szkriptje **változatlanul kibontva** és futtatva (a küszöb a fájlé);
- Rust lefedettség: `cargo llvm-cov --all --locked --fail-under-lines 90`, a `verify.yml` lépéséből kibontva;
- Go mutáció: `scripts/gremlins_gate.py` (a per-csomag ratchet);
- Rust mutáció: `cargo mutants --workspace --in-diff` (a PR-kapu módján).
Minden defekt **izolált másolaton** fut, mindegyik mellett **pozitív kontroll**, a várt hibának a **kapu saját jelzését** kell hoznia (nem csak nem nulla kilépést), és a harness igazolja, hogy a checkout `git status`-a előtte és utána azonos.

| Eset | Kontroll | Defekt | Kapott (#191, run 43726067136) |
|---|---|---|---|
| P1-go | `pkg/merkle: 98.3% (min 97%)`, exit 0 | a csomag tesztjei kiürítve | exit 1, `pkg/merkle: 0% (min 97%)`, `FAIL: coverage below threshold` |
| P1-rust | 98,45% sor, exit 0 | minden teszt letiltva | exit 1, 4,97% sor (< 90) |
| P2-go | killed 23, lived 0, efficacy 100,00, exit 0 | ugyanaz a kód assert nélküli tesztel | exit 1, killed 14, **lived 9**, efficacy **65,38 < 90,0** |
| P2-rust | 15 caught, exit 0 | ugyanaz a kód assert nélküli tesztel | exit 2, **15 missed** |

**Költség (mért, #191, `raw/ci/191-checks.tsv`):** Go job 59 s, Rust job 151 s. Helyben a négy eset együtt ~2 perc melegített cache-sel.
**Fogak:** ha a kapu maga gyengül (az `pkg/merkle` küszöb 97→0), a Go lefedettségi eset **piros** lesz (`test_the_go_coverage_case_is_green_on_the_real_gate_and_goes_red_when_the_gate_is_weakened`); a három valódi gyengítés a #192-n.
**Korlátok:** a P2-rust a `cargo mutants --in-diff` parancsot futtatja a **szkriptben rögzített alakban**, nem a `mutation-pr.yml` lépésének kibontott szkriptjét, és **nem** a teljes `mutation-pr` aggregációt (`completeness`, `gate`); a `cargo-mutants`-nak nincs küszöbe, az ítélet a kilépési kód (2 = missed). Ez a gyengébb pont a Go-oldalhoz képest.

## 5. A negatív kontrollok (szándékosan hibás PR-ok) — pontosan az elvárt okból buknak-e

A #191 a `62f3004` fejen **27/27 check zöld** (`raw/ci/191-checks.tsv`; run-ok: verify 43726067164, mutation-pr 43726067141, object-evidence 43726067147, gate-selftest 43726067136, manifest-check 43726067046). A proof PR-ok fejei csak a szándékos hibát hordozzák a munkaághoz képest (`git diff` fájlok: #192 `verify.yml`, `gremlins_gate.py`; #193 `.measurement-tools.json`; #194 `bootstrap.go`, `ffi/src/lib.rs`).

**#192 — gyengített valódi küszöbök (`e1bd162`), run 43726070268 (gate-selftest) / 43726070248 (verify).** `gate-selftest` go (job 132848158555) és rust (132848158958): **P1-go, P2-go, P1-rust FAIL** (a gyengített kapu átengedte a hibát: `exit 0`, `0% (min 0%)`, `lived 9`, 4,97% sor); **P2-rust OK marad** (nincs küszöb, nem gyengíthető ugyanígy). A `python` job (132848158523) 6 tesztje bukik, mind a gyengített küszöbhöz kötött (`test_baseline_guard`×3, `test_gremlins_gate::test_thresholds_default_and_baseline`, `test_quality_gate::test_gremlins_gate_reports_a_failing_and_a_garbled_package`, a Go „fog" teszt). `raw/ci/192-*.txt`.

**#193 — eltérő Go-pin (`3ddcd56`), run 43726070118 (mutation-pr) / 43726070116 (gate-selftest) / 43726070075 (verify) / 43726070100 (object-evidence).** Minden Go-mérő job `[TOOL_UNUSABLE] 'go' was 'go1.26.11', the pinned version is 'go1.26.10'`-zel bukik: `coverage` (132848157694), `mutation-pr` go chunk 0–5 (pl. 132848780375), `gate-selftest` go (132848158440); az `object-evidence` (132848158517) `tools UNUSABLE`; a `completeness` a hiányzó chunk-riportok miatt (`missing chunk report(s): [0, 1, 2, 3, 4, 5] of 6`, 132850197274); a `python` job 5 pin-teszttel (132848157927). **A Rust jobok (shardok, `rust`, `rust (coverage gate, cargo-mutants)`), a `plan`, `manifest`, `baseline-guard`, `ffi` és a `verify` zöldek maradnak.** `raw/ci/193-*.txt`. A proof PR-ok minden checkjének run- és job-azonosítója: `raw/ci/proof-checks.tsv`.

**#194 — no-op láncellenőrzés + hatástalan FFI panic-védelem (`4bb1699`), run 43726070510 (verify) / 43726070628 (mutation-pr) / 43726070647 (object-evidence).**
- **Go (verify `coverage`, 132848159023):** **csak a negatív tesztek** buknak: `…SignerCertificate…/expired_signer`, `/signer_that_is_not_valid_yet`, `/revoked_signer`, `RejectedSigner_LeavesNoModuleRegistered`, és a régebbi `PKIVerification_WrongChain`, `_WrongEKU`, `TestEmbeddedAndInstalled…/untrusted_chain`, `/wrong_EKU`, `TestProd_ModuleSignedOutsideOperatorBundle…`; **a pozitív kontrollok zöldek maradnak**.
- **Rust:** a `rust` job (132848158941) a **„Test (locked)"** lépésen bukik, **pontosan egy** teszttel: `tests::a_panic_in_the_core_is_contained_and_reported_as_a_rejection` (29 sikeres, 1 sikertelen); ugyanez a teszt bukik a mutációs shardok „Unmutated baseline" fázisában (shard 0: 132848552003, shard 1: 132848552006). **A rustfmt (format check) és a Clippy (-D warnings) lépés ebben a jobban `success`.**
- A `python`, `verify`, `plan`, `manifest`, `baseline-guard`, a shard 2–7 és `ffi` zöldek. `raw/ci/194-*.txt`.

**F3 helyesbítés (a review szerint).** A jelentés korábbi változata azt írta, hogy a #194 `rust` jobja a `failed to gather coverage` üzenettel bukott, és a konkrét teszt nevét nem olvastam ki. A review függetlenül megállapította, hogy a **korábbi** fejen (`2859bb2`, run 43722012343, job 132835840001) a `rust` job a **rustfmt ellenőrzésen** bukott, nem a negatív FFI-teszten: a defekt egy sorvégi megjegyzést tartalmazott, amelyet a rustfmt elutasított, a tesztlépések már nem futottak le. **Ez a megállapítás helyes, a korábbi állításom hibás volt.** A defektet átírtam úgy, hogy a `rustfmt`, a `gofmt` és a `clippy -D warnings` is elfogadja (az első javítási kísérletem típushibás volt, E0282), a proof ágat újraépítettem; a fenti #194 eredmények már a javított fejre (`4bb1699`) vonatkoznak, ahol a bukás oka a teszt.

*A proof PR-ok korábbi futásai* (`ab411d1`, `be7c2e4`, `0fe1ccc` bázison; run-ok a `raw/ci-first-iteration/`-ben): más okokat is hordoztak (lint-hibák, 21 generált companion `.yaml`, a #194 első változata a pozitív kontrollokat is megbuktatta). Ezért javítottam a munkaágat, és építettem újra a proof ágakat; **a jelentés eredményei az újraépített fejekre vonatkoznak.**

## 5b. Az aktuális integrált állapot (a review utáni igazítás a `main` `e43f2a8` fejére)

A független review (APPROVE) egyetlen merge-előfeltételt hagyott: a Relay `main` közben `7386565`-ről `e43f2a82...`-re mozdult (PR #190: `cmd/relay/hardening_integration_test.go` új, `cmd/relay/egress_client_test.go` +29/-1 sor, csak tesztek). **Funkcionális változtatás nem történt.**

- **#191:** a `main` (`e43f2a826ca2adee717a0a7ae18ca220016fb7c1`) beolvasva merge committal (nincs rebase, így a korábbi aláírt commitok érintetlenek), új fej **`45427e92a2561fafcfd4e78700b801d2f97d4ed4`**. Ütközés nem volt. A diff a `main`-hez képest változatlan tartalmú (0 `.yaml`, a #190 két fájlja nem része). **27/27 check zöld** (`raw/ci-rebased-e43f2a8/191-checks.tsv`); run-ok (`191-runs.tsv`, mind `headSha` = `45427e9`): verify 43754489776, mutation-pr 43754489964, object-evidence 43754489767, gate-selftest 43754489768, manifest-check 43754489799. A gate-selftest az új bázison is mind a négy esetet (go-cov, rust-cov, go-mut, rust-mut) kontrollal és defekttel lefuttatta.
- **A proof ágak** a munkaág új fejére építve, csak a szándékos hibával (a régi fejek helyben `backup/*-on-62f3004` néven megmaradtak): **#192 `7666846b6eee80f1419c9f7b370789711b747dee`**, **#193 `c444e2d030f2038e96f85fc9ca142c2f813496b2`**, **#194 `97e0860bfe51152740565ebb5ef55ebfb61d64b4`**; mind draft, DO NOT MERGE, nyitva. A teljes check-lista: `raw/ci-rebased-e43f2a8/proof-checks.tsv` (74 sor).

| Proof | Mérve az új bázison | Egyezik a korábbival |
|---|---|---|
| #192 | gate-selftest: **P1-go FAIL** (`pkg/merkle: 0% (min 0%)`), **P2-go FAIL** (`lived 9`, 65,38), **P1-rust FAIL** (4,97%); P2-rust OK (nincs küszöb); a kontrollok OK (run 43754492291, job 132935486229 / 132935486012; `192-selftest-*.txt`) | igen; 3 piros job: go, rust, python |
| #193 | `[TOOL_UNUSABLE] 'go' was 'go1.26.11', the pinned version is 'go1.26.10'` (job 132935486040; `193-tools.txt`); 12 piros Go-oldali job; minden Rust-job zöld | igen |
| #194 | Rust: `tests::a_panic_in_the_core_is_contained_and_reported_as_a_rejection` FAILED (job 132935484684; `194-rust.txt`), 8 piros job; Go: a negatív tesztek és a régebbi `PKIVerification_WrongChain/_WrongEKU`, `TestEmbeddedAndInstalled…`, `TestProd_ModuleSignedOutsideOperatorBundle…` bukik (job 132935484964; `194-go-coverage.txt`); a `python`, `verify`, `plan`, `ffi`, `manifest`, `baseline-guard` zöld | igen, **plusz**: az új `main` `TestHardeningIntegration_ProdComponentsOnBothLoadPaths` tesztje is (3 alteszt) elkapja a hibát — a #190 és a PR-06 negatív tesztjei egymást erősítik |

Megjegyzés: a #194 Go chunk 0 job csak a saját chunkjában futó tesztek bukását mutatja; a teljes lista a `coverage` jobból van (`194-go-coverage.txt`).

## 5c. A végső integrált állapot (a `main` `62cb1e5` fejére igazítva) és a merge

A review (APPROVE, MERGE READY) az `45427e9` fejre szólt. Közben a Relay `main` `e43f2a8`-ról `62cb1e50fcfa0d48d0c2a98a8f3a59332943c9d0`-ra mozdult (40 commit, 48 fájl; köztük a #197, amely a modulbetöltést fail-closedra írta át, a `cmd/relay/bootstrap.go`-t is). A korábbi fejre mért zöld ezért nem bizonyította az aktuális kombinációt, így a merge előtt újra igazítottam és újra mértem. **Funkcionális változtatás nem történt.**

- **#191:** a `main` (`62cb1e5`) merge committal beolvasva, új fej **`d41b4c5798b1fa09a0e64e15fea72a1dd12c9c0a`**, 0 yaml, a diff tartalma változatlan. **27/27 check zöld** (`raw/ci-rebased-62cb1e5/191-checks.tsv`; run-ok `191-runs.tsv`, mind `headSha` = `d41b4c5`: verify 43947165630, mutation-pr 43947165605, object-evidence 43947165536, gate-selftest 43947165647, manifest-check 43947165623).
- **Proof ágak** az új fejre építve: #192 `d7f8c1337271ba0b93ab9f0e4bb5ada54293cf1f`, #193 `6c93c0032bdd11d651777842276612b81260c24a`, #194 `95447e65a9150ea3c95d041e1b0dbc81ab2dcbe3`. A #194 `bootstrap.go` defektje a #197 miatt új helyre került (a `loadModule` láncellenőrzése), azonos konstrukcióval; a Go-fordítást a CI ellenőrizte, helyben nem volt toolchain.

| Proof | Mérve a `62cb1e5` bázison | Egyezik |
|---|---|---|
| #192 | P1-go FAIL (`pkg/merkle: 0% (min 0%)`), P2-go FAIL (a túlélő mutánsok miatt), P1-rust FAIL (4,97%); kontrollok OK; P2-rust OK (nincs küszöb); 3 piros job | igen |
| #193 | `[TOOL_UNUSABLE] 'go' was 'go1.26.11', the pinned version is 'go1.26.10'`; 12 piros Go-oldali job; minden Rust-job zöld | igen |
| #194 | Rust: `a_panic_in_the_core_is_contained_and_reported_as_a_rejection` FAILED (29 sikeres, 1 sikertelen); 8 piros job; Go: a negatív tesztek, a `TestHardeningIntegration_ProdComponentsOnBothLoadPaths` és az új **#197 `TestModuleSigning_DecisionTable`** (signer a trust store-on kívül / rossz key usage, PROD és DEV, embedded és installed) is bukik | igen, plusz a #197 tesztjei |

A nyers evidence: `raw/ci-rebased-62cb1e5/` (`proof-checks.tsv` 74 sor, `192-selftest-*.txt`, `193-tools.txt`, `194-rust.txt`, `194-go-coverage.txt`).

**Merge és lezárás (a tulajdonos engedélyével, 2026-11-16):**
- Relay **#191 MERGELVE**, merge commit **`c18fef2d15bd503bb7c0861bf9dd2e7d80a2da85`**, a mért `d41b4c5` fejhez kötve (`--match-head-commit`). A post-merge main CI eredménye: lásd az alábbi sort, ha rögzítve van; ha nincs, akkor nem mért.
- Relay **#192–#194 lezárva merge nélkül**, a proof ágak és a #191 feature ága a távolról törölve; az evidence fent van rögzítve.
- **A #197 és a nyitott tétel:** a 6. szakasz „aláíratlan modul figyelmeztetéssel betöltődik (`bootstrap.go:534`)" megállapítása az `e43f2a8`-ra vonatkozott; a #197 ezt azóta visszautasításra cserélte (`Refuse unsigned and badly signed modules at load`). A tétel ennek megfelelően **nem aktuális**, a jelentés többi szövege az akkori állapotot írja le.

## 6. B — a négy bizalmi terület hiánytérképe

Státusz-szabály: a **production reachability dönt** (nem a dokumentáció). Eszköz: `deadcode ./cmd/relay` (golang.org/x/tools v0.52.0), 101 elérhetetlen függvény, `raw/deadcode-cmd-relay.txt`. A `deadcode` csak a `cmd/relay` belépési pontból néz; más belépési pontot (`tools/*`, `cic-ffi`) nem.

### (1) Modul-azonosság és jogosultság — implementáció: kész
| Eset | Állapot |
|---|---|
| rossz tanúsítványlánc, rossz EKU, hiányzó trust store pool | **fedett** (`core/cabinet/pki_verify_test.go`: untrusted root, incomplete chain, wrong EKU; `bootstrap_test.go`: `PKIVerification_WrongChain/_WrongEKU`) |
| lejárt / még nem érvényes / visszavont aláíró `loadModule`-nál | **új, #191** (`module_identity_negative_test.go`), pozitív kontrollal, foggal |
| WASM bájt eltérés a YAML digesttől / méret | **fedett** (`bootstrap_test.go` `wasm digest mismatch`, `wasm size mismatch`) |
| CRL hamis / elavult / ismeretlen kiadó | **fedett** (`pki_crl_test.go`) |
| nem engedélyezett capability, túldeklarált import | **fedett** (`TestCICFlowRegistry_RegisterVerified_OverDeclared`, `TestLoadModule_RejectsOverDeclaredCICFlow`) |
| hiányzó aláírás-fájl | **a viselkedés** betölti a modult figyelmeztetéssel (`bootstrap.go:534`), prodban is; nincs rá teszt: **rögzítve, nem tesztelve** (szándékosnak tűnik: a cic-flow képességet csak a provenance adja), a tulajdonos dönt |
| SPKI-pinning | **a modell létezik, de az implementációs híd itt megszakad:** `core/cabinet/pki_verify.go` és tesztje megvan, de **a `bootstrap.go:562` opciói nem adnak `PinnedSPKIs`-t** és a `PKIAssets`-ben nincs ilyen mező; `grep -rn PinnedSPKI` production hívó nélkül |
| `pki_verify.go` státusza | a `CLAUDE.md` **scaffold**-nak írja, de a `deadcode` szerint a `VerifyCertificateChain`, `CheckCRLFresh`, `VerifyCRLSignature`, `checkRevocation`, `checkSPKIPinning` **elérhetők** a `cmd/relay`-ból (hívók: `bootstrap.go:80`, `:562`, `pki_companion.go:73`). Prodban kötelező (`pki_bootstrap.go:35` `requireTrustStore`), devben trust store nélkül auditnaplós kihagyás (`bootstrap.go:559`). **Status: implemented**, feltételes dev-kihagyással. A dokumentáció elavult |
| `moduleProject.verifyBuildHash` | a `deadcode` szerint **elérhetetlen** a `cmd/relay`-ból (`cic_flow_manifest.go:205`), csak teszt hívja: scaffold |

**Biztonsági lelet (a részletek NEM ebben a jelentésben):** a modul-azonosság területén **egy hiányzó production-garancia-jelölt** van rögzítve (a modul tartalmának aláírás-kötése). A reprodukciós részleteket a spec szerint privát csatornán, a tulajdonosnak adtam át; a javítás **külön, célzott PR** feladata. A jelentés csak a lelet fajtáját és az érintett fájlt (`cmd/relay/bootstrap.go`, `loadModule`) rögzíti.

### (2) Végrehajtás és erőforráskorlátok — implementáció: nincs (hiánytérkép)
*A nevek szerinti keresésen alapul: „nem találtam név szerint" nem bizonyítja a hiányt.*
| Eset | Állapot |
|---|---|
| átirányítás, belső címek, méretkorlát, időtúllépés, resolver, host-fejléc | **fedett** (Rust `http-executor`: `redirects_are_returned_not_followed`, `ssrf_predicate_*`, `hostname_resolving_to_private_ip_is_blocked_by_resolver`, `oversized_response_body_is_refused_with_limit_exceeded`, `slow_endpoint_times_out_as_unavailable`, `mismatched_host_header_is_denied`) |
| Go: kimenő kérés tiltása | **fedett** (`TestMakeActuateFn_EgressDenied`, `_EmptyEgressDeniesAll`) |
| WASM időtúllépés, guest-hiba utáni felszabadítás | **fedett** (`TestCicWasmHost_Process_Timeout`, `_Process_TrapDealloc`) |
| WASM memóriahasználat-korlát | **nem találtam név szerint** |
| DNS-eredmény megváltozása az ellenőrzés és a kapcsolódás között | **nem találtam név szerint** (a „guarded resolver" léte megvan) |
| `httpcap.ActuatorFunc.RunFlow` | `deadcode`: **elérhetetlen** a `cmd/relay`-ból |

### (3) Workflow- és proof-lánc — implementáció: nincs (hiánytérkép)
| Eset | Állapot |
|---|---|
| sérült lánchash, hamis/hiányzó aláírás, tartalom-manipuláció | **fedett** (`TestVerifyChain_Detects*`, `_NoSignedCommits`, `_CorruptSignatureMeta`; `TestVerifyProofArtifact_*`) |
| párhuzamos rögzítés | **fedett** (`TestSignAndCommit_ConcurrentRecordsKeepChainVerifiable`) |
| részleges végrehajtás, megszakítás, állapotfolytonosság | **nem találtam név szerint** |
| `ProofArtifactFromTrace`, `MarshalProofArtifact`, `ProofFromActuation` | `deadcode`: **elérhetetlenek** a `cmd/relay`-ból (a `VerifyProofArtifact` elérhető) |
| a nem összemosható állapotok (végrehajtás sikere / létezik bizonyíték / szerkezeti konzisztencia / kriptográfiai hitelesség / bizalmi szabály) | a Relay ma ezeket nem különíti el egy értékben: **rögzítve**, nincs teszt |

### (4) FFI, Vault, release — implementáció: FFI kész
| Eset | Állapot |
|---|---|
| üres bemenet, null `out_len`, túlméretes, pontosan a határon, hibás JSON, üres subject, `free(null)`, ABI-verzió | **fedett** (a meglévő 12 teszt) |
| **panic a magban**, **üres core-eredmény**, **null pointer nem nulla hosszal**, **minden elutasítás nullázza az `out_len`-t**, **nulla hosszú `free` nem szabadít fel élő puffert** | **új, #191** (5 teszt, 30/30 zöld, clippy `-D warnings` és rustfmt tiszta) |
| dupla felszabadítás, hosszeltérés a pointerhez képest | **nem tesztelhető UB nélkül** (a szerződés: pontosan egyszer, pontosan a visszaadott pár): rögzítve |
| a panic-védelem release-ben | a `release` profil `panic = "abort"`: a `catch_unwind` háló csak **unwind** buildben él (teszt, dev); release-ben a folyamat leáll. **Rögzítve, nem tesztelve** |
| Vault/release láncszemek | **nem érintettem** (külön job; valódi kulcs nélkül) |

**A „fogak"** (`raw/teeth-module-identity.txt`, `raw/teeth-ffi.txt`): a láncellenőrzés kihagyására az `expired_signer` esik; a CRL-ek el nem adására a `revoked_signer`; a panic-védelem eltávolítására az `a_panic_…`; az üres-eredmény ellenőrzés kivételére az `an_empty_core_result_…`; a null-guard kivételére a teszt-folyamat összeomlik (a teszt nem tud átmenni); az `out_len` nullázás kivételére az `every_rejection_path_…`. **A `free(…, 0)` tesztjére nincs megbízható fog** (a hibás változat UB).

## 7. A #169 1–8. próbájának frissített leképezése

| # | Próba | Fedés |
|---|---|---|
| 1 | gyengített suite → lefedettségi kapu piros | **fedett** valódi kapuval (A.1), #191 zöld, #192 piros |
| 2 | túlélő mutáns → mutációs kapu piros | **fedett** valódi eszközzel (A.2); Rust: a `--in-diff` parancs, nem a teljes aggregáció |
| 3 | hiányzó shard → a FULL nem lehet sikeres | PR-03 hivatkozás + #193 `completeness` (`missing chunk report(s)`) |
| 4 | duplikált/hamisított verdikt | PR-05 (A.4, A.5) |
| 5 | hiányzó/olvashatatlan riport | PR-04 egységtesztek; valós artifacton nem |
| 6 | hibás tervező | PR-02 tesztek; a PR-06 a `gate_selftest.py`-t gate-logic útvonallá tette |
| 7 | hibás evidence nem lehet VERIFIED | PR-05 (A.1–A.9), a `tools` ítélet |
| 8 | módosított/ismeretlen eszközverzió | **fedett** (A.8), minden mérő jobban; `mutation.yml`/`nightly.yml` csak szöveg- és egységszinten |

## 8. Amit menet közben találtam (hibák, tanulságok)

- **Lint-hibák a #191 első futásán** (`0fe1ccc`): ruff F401 (használatlan `textwrap`), staticcheck ST1008 (hiba nem utolsó visszatérési érték). Javítva `ab411d1`-ben. Tanulság: a CI pinelt eszközeit teljes tiszta exporton kell futtatnom push előtt.
- **A generált companion `.yaml` fájlok (az F2 oka):** a `984e2cd` commit `git add -A scripts tests …`-szel **21 generált companion `.yaml`-t** vitt be (17 új, 4 módosított), a `yamllint` ezekre bukott. A környezetben **fut egy folyamat, amely minden létrehozott vagy módosított `.py`/`.go` mellé companion `.yaml`-t generál** (a PR-05-ben ez okozta a 212 piszkos bejegyzést). A folyamat **pontos nevét nem azonosítottam**; a jelenség reprodukálható az én fájlkezelésemhez kötve (a PR-05 explicit útvonalas `git add`-jával nem került be semmi). Javítás `be7c2e4`. **Szabály:** nincs `git add -A`/`.`, csak explicit útvonal.
- **A #194 első hibás változata a pozitív kontrollokat is megbuktatta** (a `verified` log eltűnt): a bizonyító hiba szándékosan úgy lett átírva, hogy a no-op ellenőrzés sikert jelent.
- **Megosztott cargo target = hamis negatív az FFI „fog"-scriptben.** A `teeth_ffi.sh` egy újrafuttatásakor a **módosítatlan** másolat 8 teszten bukott (`out_len` maradt 9), pedig a forrás változatlan: a `/tgt` target könyvtár egy korábbi, mutált másolat artifactjait őrizte, a friss target könyvtárral 30/30 zöld. A `fog` korábbi (mind OK) eredményei nem érintettek (a mutált teszt a megnevezett teszten bukott), de a script mostantól minden futás előtt `cargo clean -p cic-ffi`-t futtat (`raw/teeth_ffi.sh`, `raw/teeth-ffi.txt` az új, tiszta kimenet). Ugyanaz a szabály, mint a mutációs harnessnél: a mutáns ne osszon cache-t a vizsgált futással.
- **A teszt-szuite tiszta exporton** (git nélkül) 11 tesztje bukik (`HEAD...HEAD`): ez a `git archive` exporté, nem a repóé.
- **A review F1 és F2 valódi hiányosság volt.** A `check-tools` csak a kapott eszközöket ellenőrizte (egy elhagyott `--tool` átcsúszott), a verifier pedig pin nélkül `NOT_CHECKED`-et adott sikertelen kilépés nélkül. Mindkettő javítva (3. szakasz).
- **A #194 `rust` jobja a rustfmt-en bukott** (F3): a bizonyítékot a defekt formázási hibája szennyezte; javítva, a hibás változat előtt `cargo fmt --check` és `clippy -D warnings` helyben, mielőtt pusholtam.
- **A cic-factory #64 gate-je háromszor bukott a `main` mozgása miatt** (a GitHub tesztmerge-e tartalmat hoz, és aláíratlan): minden alkalommal friss, egy-commitos, aláírt újraépítés az aktuális `main` tetejére. Egyszer egy **nem determinisztikus teszt** (`tools/test-run-job-boundaries.sh`, „az aposztrófos is") bukott a változatlan SHA-n, az újrafuttatás zöld: **cic-factory issue #67**, a gyökérok ismeretlen.

## 9. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A #191 teljesen zöld a `45427e9`-en (a `main` `e43f2a8` beolvasva) | mért | `raw/ci-rebased-e43f2a8/191-checks.tsv`, `191-runs.tsv` (27 check, 5 run, headSha `45427e9`); a korábbi `62f3004`: `raw/ci/191-checks.tsv` | GitHub Actions | alacsony |
| A valódi Go lefedettségi kapu elutasítja a gyengített suite-ot | mért | 191-gate-selftest.txt (98,3% → 0%) | a workflow lépés változatlan kibontva | csak `pkg/merkle` |
| A valódi Rust lefedettségi kapu elutasítja | mért | 98,45% → 4,97% | `cargo llvm-cov --fail-under-lines 90` | — |
| A gremlins ratchet elutasítja a túlélő mutánst | mért | lived 9, efficacy 65,38 < 90 | `gremlins_gate.py` | egy planted függvény |
| A `cargo mutants` missed-et jelez | mért | 15 missed, exit 2 | — | a teljes aggregáció nem fedett |
| Minden mérő jobban fail-closed eszközellenőrzés | mért (PR-jobok); szöveg-szint (`mutation.yml`, `nightly.yml`) | 191-tools-pinned.txt, 3 teszt | CI + egységteszt | a pin a PR fáján van |
| A #193 az eszközverzió miatt bukik | mért | 193-tools.txt | négy job naplója | — |
| A #192 azért bukik, mert a kapu gyengült | mért | 192-selftest-*.txt | gate-selftest FAIL sorok | — |
| A #194 pontosan a negatív teszteken bukik | mért (Go, Rust shard); nem olvastam ki (Rust `rust` job tesztneve) | 194-go.txt, 194-rust.txt | job-naplók | kimondva |
| `pki_verify.go` production-elérhető | mért | `deadcode-cmd-relay.txt` + `bootstrap.go:80,562` | `deadcode ./cmd/relay` | csak a `cmd/relay` belépés |
| SPKI-pinning nincs bekötve | mért | `grep -rn PinnedSPKI` | forrás | — |
| Egy felület kötelező eszközének kihagyása `UNVERIFIABLE` (F1) | mért (helyben, tesztek) + CI-ben a per-job teszt | `test_check_tools_a_required_tool_that_is_not_declared_is_unverifiable[*]`, `…declares exactly the surface`, 191-tools-pinned.txt | negatív eset felületenként és kötelező eszközönként, pozitív kontrollal | a felületek listája a pin-fájlban van (a PR módosíthatja) |
| Quality módban a hiányzó pin `UNVERIFIABLE`, kilépés 1 (F2) | mért | `test_n_f2_*`, `P8.e`, 43726067147 | CLI-teszt + seeded eset foggal | a `diagnostic` mód a kötelező `--mode`-dal választható |
| A #194 `rust` jobja most a teszten bukik, nem a formázáson (F3) | mért | job 132848158941: „Test (locked)", 29/1; rustfmt és Clippy `success` | job lépés-eredmények | — |
| (2), (3) területen nincs teszt a felsorolt esetekre | **nem bizonyított** | név szerinti keresés | — | magas |
| A biztonsági lelet valódi és kihasználható | **nem mértem**, forrásolvasás | privát átadás | — | magas |
| Új küszöb/baseline/blokkoló kapu nincs | mért | diff-ellenőrzés (0 sor, 0 törölt workflow-sor) | `git diff` | — |

## 10. Nyitott döntések és amit nem mértem

- **A pin-fájl védelme** egy PR-ral szemben: **CIC_Relay issue #195** (a `baseline-guard` kiterjesztése a bázis-másolatra vagy ezzel egyenértékű, külön jóváhagyási út, negatív proof PR). Nem része a PR-06-nak, hacsak a review másképp nem dönt.
- **`cargo-mutants` / `cargo-llvm-cov` pinelése a telepítésnél** (jelenleg újabb kiadás = fail-closed piros).
- **Az öt crate nélküli `#[no_mangle]` azonosító** és a **`syn`-leltár**: külön PR/job (tulajdonosi döntés); **nem érintettem**.
- **A (2) és (3) terület** implementációja és a név szerint nem talált esetek: tulajdonosi döntés.
- **A biztonsági lelet** javítása külön, célzott PR.
- **Az aláíratlan modul prodban betölt** viselkedés: szándékos-e.
- **Nem mértem:** a `mutation.yml` és `nightly.yml` tényleges futását az új lépésekkel; a teljes `mutation-pr` aggregáció seeded tesztelését; a Vault/release láncszemeket; a lelet kihasználhatóságát.
- **Takarítás:** `~/.cache/relay-ci-parity-06` (3,7 GB) felhasználói tulajdonú, `sudo` nélkül törölhető.
