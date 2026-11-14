# Relay CI inventory és objektumszintű gap-analízis (PR-01)

Job: `relay-ci-parity-01-inventory` · issue: `CentralInfraCore/CIC_Relay#169` (másolat: `ref/issue-169-body.md`)
Jelleg: **mérés és dokumentáció.** A Relay forrását, workflow-it és scriptjeit nem módosítottam, a CIC_Relay felé PR-t nem nyitottam.
Nyers kimenetek és a mérő scriptek: `output/raw/`. A kapuhiba reprodukciója külön: `output/gate-defect-repro.md`.

> **Aláírás:** a cic-factory klónban a `commit-msg` hook lefutott és aláírási metaadatot fűzött a commitüzenethez („Commit message updated with signing metadata”). A hook aláírásának érvényességét **nem ellenőriztem**; a tulajdonos verifikálja. A CIC_Relay és a Forms klónba nem commitoltam.

## 1. Vizsgált commitok

| Repó | Ág | Commit | Megjegyzés |
|---|---|---|---|
| `CentralInfraCore/CIC_Relay` | `main` (alapértelmezett ág) | `bc2c4e0a2eade4f798b51e03d2953304512960ed` (2026-11-14T09:17:20+01:00) | friss klón a workspace-ben, `--depth` nélkül |
| `CentralInfraCore/cic-primitive-forms` | `main` | `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (2026-11-05T14:10:07+01:00) | friss klón, csak olvasásra |

**A mérő környezet.** A gépen nincs `go`/`cargo`; minden mérés Docker konténerben, a Relay által pinelt képekkel futott
(`golang:1.26.11@sha256:6327cb29…e9c6ba`, `rust:1.96.1-bookworm@sha256:d99f7b31…abd8`, a `docker-compose.yml:14-15` szerint),
a repó **másolatán**. Eszközök: `cargo-mutants 27.1.0`, `cargo-llvm-cov 0.9.1`, `deadcode@v0.44.0`, `govulncheck@v1.1.4` (a CI pinjei, ahol van).

**Egy bizonytalanság a mérés tisztaságáról.** A Relay klón a klónozás pillanatában **nem volt tiszta**: 189 módosított tracked `.yaml` fájl és 6 untracked fájl
(a `*.go`/`*.rs`/`*.py` fájlokat nem érintette; `git status --short | grep -v '\.yaml$'` üres volt). Az okát **nem állapítottam meg**. A módosítás patchét
elmentettem (a scratchpadbe, nem commitolom), a klónt `git checkout -- . && git clean -fd`-vel visszaállítottam, és a Go-méréseket **a tiszta fán megismételtem**.
Ezért a jelentés Go-számai a tiszta fára vonatkoznak; a piszkos fán kapott számok csak két csomagnál tértek el (lásd 7.), és ez a nemdeterminizmussal
magyarázható, nem a fa állapotával (6 ismétléssel mérve).

## 2. A Relay meglévő tesztrendszere (A)

### 2.1 Workflow-k

| Workflow | Trigger | Mit csinál | Kötelező check? |
|---|---|---|---|
| `verify.yml` | PR (`**`), push `main` | jobok: `verify` (gofmt, vet, staticcheck, govulncheck, deadcode, symbol drift, golden), `coverage`, `python`, `rust`, `ffi` | igen: `verify`, `coverage`, `python`, `rust`, `ffi` |
| `manifest-check.yml` | PR, push `main` | `MANIFEST.sha256` drift | igen: `manifest` |
| `mutation-pr.yml` | PR | diff-mód mutáció: `plan` → `go` (gremlins) + `rust` (cargo-mutants shardok) + `baseline-guard` → `gate` | igen: `mutation-pr` |
| `nightly.yml` | cron 01:30 UTC, dispatch | `security` (govulncheck, cargo-deny advisories), `plan`+`go`+`rust` inkrementális mutáció az utolsó sikeres éjszaka óta, `report` (issue) | nem |
| `mutation.yml` | cron kedd 09:00 UTC, dispatch | FULL: `plan --all` + Go gremlins chunkok + Rust cargo-mutants 4 shard + `report` | nem (a fájl maga írja: `mutation.yml:18`) |
| `renovate.yml` | — | függőség-frissítés; ebben a jobban nem vizsgáltam | — |

A kötelező check-lista a `main` aktív rulesetjéből jön (`gh api repos/CentralInfraCore/CIC_Relay/rulesets/26873807`): `required_status_checks` =
`verify, coverage, python, rust, ffi, manifest, mutation-pr`; `strict_required_status_checks_policy: false`; további szabály: `deletion`, `non_fast_forward`.
**Pull-request/review szabály és commit-aláírás szabály nincs a rulesetben.** Klasszikus branch protection nincs (`404 Branch not protected`). A beállítást nem
módosítottam.

### 2.2 Scriptek és konfig

| Fájl | Szerep | Megjegyzés |
|---|---|---|
| `scripts/mutation_plan.py` (169 sor) | a diffből: mely Go csomagok és kell-e Rust | lásd 4.2 |
| `scripts/gremlins_gate.py` (180 sor) | gremlins csomagonkénti ratchet-kapu | fail-closed a nem értett kimenetre (`gremlins_gate.py:146-149`), timeout-dominancia elutasítás (`:103-106`) |
| `scripts/baseline_guard.py` (93 sor) | a baseline csak szigorodhat | a BASE commitból futtatva (`mutation-pr.yml` `baseline-guard`) |
| `.mutation-baseline.json` | 12 csomag < 90-es rögzített állapota | rögzítve `main@dcbdde9`, 2026-11-09 (**nem általam mért**) |
| `.mutation-cost.json` | költségbecslés a chunkoláshoz | csak elosztásra |
| `.gremlins.yaml` | gremlins küszöb 90/90 | a CLI-küszöb nem érvényesül (a fájl kommentje szerint v0.6.0-ban) |
| `.cargo/mutants.toml` | 4 `exclude_re` | `cic_ffi_abi_version -> 1`, `connect_mtls`, `flow::live::`, `flow::run_live` — mind a nem-default `live-vault` feature kódja |
| `scripts/ci_report.sh` | issue nyitás/zárás | a nightly/weekly jelentés |
| `tests/test_tools/test_{mutation_plan,gremlins_gate,baseline_guard}.py` | a három kapu-script Python tesztje | a `python` jobban fut (`pytest`, `verify.yml:238`); **én nem futtattam** |

### 2.3 Tesztfuttatás, lefedettség

- **Go:** `verify.yml` `coverage` job. PR-on teljes modul (`./...`), push-on a módosított csomagok + fordított függőségeik (`tools/affected`, `verify.yml:95-112`).
  Profil: `go test -race -covermode=atomic -coverprofile` (`:117`), de a küszöböt **csomagonként, külön `go test -coverprofile` futás** számolja (`:142-148`), `case` táblából
  (`:149-171`, alap `min=80`). Egy csomag, amelynek a tesztje elbukik, **nem lépődik át** (`:140-147`, ez fail-closed).
  Kihagyott csomagok: `core/nexus/types`, `embedded/pki`, `tools/sourcehash`, `tools/statechain-demo`, `tools/trustflow-demo`, `tools/oci-sign-demo`, `pkg/cicffi` (`:131-139`).
  **Modul-szintű Go statement coverage küszöb nincs.**
- **Rust:** `rust` job: `cargo fmt`, `clippy -D warnings --all-features`, `cargo test --all --locked`, `cargo llvm-cov --all --locked --fail-under-lines 90` (`verify.yml:276-277`), `cargo-deny`.
  A tesztek és a coverage **default feature-ökkel** futnak.
- **FFI:** `ffi` job: `cargo build -p cic-ffi --release`, majd `go test -tags ffi_cgo ./pkg/cicffi/...` (`verify.yml:306-312`). A `make test-ffi` ezen felül
  `./cmd/relay/...`-t is futtatja a taggel (`Makefile:374`) — **a CI `ffi` job nem**.
- **Python:** ruff, black, isort, mypy, yamllint, bandit, `pytest --cov=tools --cov-fail-under=80` (`pytest.ini`), `tools/goastdump` külön modul tesztje.
- **Mutáció:** Go gremlins `v0.6.0` (CI, `mutation-pr.yml`/`mutation.yml`/`nightly.yml`), a `Makefile:506` alapértelmezése `v0.5.1` — **verzióeltérés** CI és helyi között.
  Rust cargo-mutants verzió **nincs pinelve** a CI-ben (`taiki-e/install-action@v2`, `tool: cargo-mutants`).

## 3. A Forms referencia (B)

A Forms `2f02a75`-n (tools és workflow-k mérete: `p1.yml` 1577 sor, `p1-proof.yml` 1813 sor — az utóbbi a `p1.yml`-ből generált, `tools/proof-plan/gen_p1_proof.py`).
Ami a PR-sorozat szempontjából lényeges, **olvasat alapján** (a Forms CI-t nem futtattam):

| Elem | Mit tesz | Forrás |
|---|---|---|
| `quality_gate.py` | coverage + mutáció együtt, szigorúan >90%, fail-closed: hiányzó/olvashatatlan riport, üres mérés, pontosan 90.00% mind piros; `REPORT_INCONSISTENT`, `INCOMPLETE_SHARDS` | `tools/quality_gate.py:1-50` (735 sor) |
| `quality_gate.py selftest` | seeded-fault bizonyíték, hogy a kapu minden okból tud bukni (a doksi szerint 92 hiba, ebből 24 új) | `tools/quality_gate.py:11,450`; `docs/FAST-FULL.md` |
| `coverage_gate.py` | ág-lefedettség (`cic-coverage-report/1`, ADR 0009) | `tools/coverage_gate.py:1-40` |
| `diff_gate.py` | diff-mód: terméksor-diff, tesztváltozás osztályozás (addíció / módosított teszt coverage-szűkítéssel / FULL), bizonytalanság → FULL | `tools/diff_gate.py:1-40`; `docs/DELTA-DIFF-GATE.md` §2 |
| `seeded_defects.py` | szándékos hibák izolált másolatban; a tesztnek buknia kell, build-hiba nem számít detektálásnak | `tools/seeded_defects.py:1-30`; ~344 definíciósor (`grep -c '^    ("rust"\|^    ("go"'`, **nem futtatva**) |
| Felsorolás fail-closed | a diff-plan `|| true` mintái kijavítva; `go_list_count.py` csak summary-sorral lezárt futást hisz el | `docs/FAST-FULL.md` „Measurement plumbing"; `tools/go_list_count.py:1-33` |
| Shardolás | `shard_count.py`, `shard_plan.py`; minden listázott mutáns pontosan egy shardban | `tools/shard_count.py`; `docs/QUALITY-SHARDING.md` |
| Evidence | `test-evidence/1` rekord, kanonikus JSON, két független implementáció (Python + Go) 63 vektoron, offline verifier, validity key | `docs/TEST-EVIDENCE.md`; `tools/test-evidence/` |
| Proof-aware terv | `proof-plan`, `compare_runs.py` | `tools/proof-plan/`; `.github/workflows/proof-plan.yml` |
| Toolchain pin | cargo-mutants `27.1.0`, go-mutesting commit, Go/Rust pin, action-ök **SHA-ra pinelve** | `.github/workflows/p1.yml` (`plan`, `quality-mutation-rust`) |

**A Forms maga sem hibátlan a referenciaként:** a Forms `plan` jobja a classic FULL-hoz ma is `grep -c '^PASS ' || true`-t használ
(`.github/workflows/p1.yml`, `plan` job, `id: c`); ott viszont a sort `test "$rust" -gt 0 && test "$go" -gt 0` követi, ami a nulla darabszámot **piros**ra
fordítja. A Relay-ben ugyanez a nulla darabszám **kihagyást** jelent (`gate-defect-repro.md`). A különbség ténybeli, a Forms-minta tehát nem másolható mechanikusan.

## 4. Objektumszintű gap-analízis (C)

Jelölések: **M** = már működő ellenőrzés · **H** = hiányzó teszt · **K** = hibás CI-kapu · **N** = nem mért terület · **I** = implementációs hiba/állapot miatt jelenleg nem teljesíthető követelmény.
A „nem mérve” itt azt jelenti, hogy ebben a jobban nem mértem; az állítás tárgya nem feltétlenül hiányzik.

### 4.1 CI-kapuk és mérési útvonalak

| Objektum | Besorolás | Indoklás és bizonyíték |
|---|---|---|
| Rust mutánsfelsorolás (`mutation-pr.yml:65`, `nightly.yml:146,148`) | **K** | `\| grep -c . \|\| true` a felsoroló hibáját nullának olvassa (`gate-defect-repro.md`: A/B/C eset, `n=0` mindháromra); a `rust` job `skipped`, a kapu a `skipped`-et elfogadja |
| `mutation_plan.py` diff-tervező | **K** (a DIFF-követelményhez képest) | `go: []` mérve P1 (csak `_test.go` változik), P2 (nem-teszt `.go` törlés), P3 (`go.mod`, `.gremlins.yaml`), P4 (`scripts/gremlins_gate.py`), P6 (`testdata/`), P8 (beágyazott modul); `rust: true` csak P5-ben (Cargo.toml); a PR-workflow az `--in-diff`-nek csak a `*.rs` diffet adja, így a függőségváltozás mutációs hatása nem mért. Nincs FULL-eszkaláció teszt-segéd, fixture, függőség, build-beállítás vagy kapu-logika változásra. Részletek 4.2. |
| `mutation_plan.py` hibás git-diff | **M** | ismeretlen `--base`: `CalledProcessError`, a script kilépési kódja 1 (P9) — itt fail-closed |
| `gremlins_gate.py` | **M** (+ részben K lásd lent) | nem értett kimenet → FAIL (`:146-149`); timeout-dominancia → FAIL (`:103-106`); a számok újraellenőrzése a gremlins saját küszöbe mellett (`:9-12`); Python teszt létezik (`tests/test_tools/test_gremlins_gate.py`, nem futtattam) |
| `baseline_guard.py` | **M** | BASE-ből futtatott, csak szigorodhat (`baseline_guard.py:225-242`); a workflow-fájl saját változata a saját PR-jében fut — a fájl maga is megnevezi (`mutation-pr.yml` komment) |
| Go mutáció: tervezett és mért mutánsok egyezése | **H** | `gremlins_gate.py` csak a futtatott csomagok eredményét ítéli; nincs terv-vs-mért mutánsszám-ellenőrzés, nincs duplikált/hiányzó ítélet-ellenőrzés |
| Rust mutáció: shardok teljessége | **H** | minden shard a **saját** mutánskészletét számolja (`cargo mutants --shard`, `nightly.yml:222-225`, `mutation-pr.yml` `rust` job), a tervezett `--list`-hez nem köti semmi, nincs közös lista és nincs „minden mutáns pontosan egy shardban” ellenőrzés; a `mutation.yml` shardszáma fix `4` (`:85,99`). Forms-ban ez `INCOMPLETE_SHARDS` |
| Rust mutáció: nem default kód | **N** | `.cargo/mutants.toml`: `live-vault` feature-ös kód kizárva (4 `exclude_re`); a kommentek szerint indokolt (cfg-kompilált-ki), a `live-vault` kód viszont semelyik CI-mérésben nem szerepel (sem mutáció, sem llvm-cov) |
| Nightly `plan` horgony | **K** (következmény) | a „legutóbbi sikeres éjszaka” a `plan` job sikeréből jön (`nightly.yml:96-104`); ha a Rust felsorolás hibája `plan`-t zöldre hagyja, a következő éjszaka az **előrelépett** commitról indul: a kihagyott Rust diff soha nem kerül újra tervezésbe. (Workflow-olvasat; GitHub futásban nem reprodukáltam.) |
| `deadcode ./...` lépés (`verify.yml:57-58`) | **K** | a lépés **nem tud elbukni**: mérve exit `0`, 106 `unreachable func` sor (`raw/deadcode-output.txt`). Maga a reachability-eszköz hasznos, a CI-lépés viszont diagnosztikai ellenőrzés, nem quality gate. A 106 találat nem jelenti, hogy mind hibás vagy eltávolítandó (tesztsegédek, injektált/cgo-s, tag mögötti kód is köztük van) |
| `go mod download \|\| true` (`verify.yml:31,89`, `mutation*.yml`) | **M** (nem elfedő) | a későbbi build/test a hiányzó modult úgyis bukásra viszi; elfedést nem találtam |
| Nightly `security` job | **I**/**N** | 2026-11-11…14 négy egymás utáni éjszakán **failure** (`gh run list`; run id: 42983215543, 43184259217, 43392774302, 43572627224; issue #160 nyitva). Az ok **nincs megállapítva**: a logok nem voltak elérhetők; a `govulncheck` a `bc2c4e0`-n **tiszta** (`raw`/scratch: `No vulnerabilities found.`), tehát a hiba valószínűleg a `cargo-deny advisories` — **nem mérve** |
| Nightly jelentés (`ci_report.sh`) | **M** | a hiba issue-t nyit és frissít (#160, 2026-11-11 óta nyitva) |
| Workflow szintű önteszt (YAML-logika) | **H** | a három kapu-scriptnek van Python tesztje, de a workflow-ok shell-logikájának (felsorolás, `case` kapuk, horgony) nincs tesztje; seeded-defect és quality-gate-selftest nincs (`git ls-files | grep -iE 'seeded|selftest'` üres) |
| Eszköz-verzió ellenőrzés | **K/H** | cargo-mutants, cargo-llvm-cov: nincs pin; gremlins: CI `v0.6.0` vs Makefile `v0.5.1`; GitHub action-ök tag-re (`@v4`, `@v5`, `@v2`), nem SHA-ra pinelve. Az „ismeretlen eszközverzió automatikusan használhatatlan” (issue 8. próba) nincs |

### 4.2 A `mutation_plan.py` mért vakfoltjai (P1–P9)

Eszköz: `python3 scripts/mutation_plan.py --base <base> --head HEAD` egy scratch másolaton, helyi commitokkal (`-c core.hooksPath=/dev/null`); minden próba után `git reset --hard`.
Kimenet (`go:` / `rust:` sor):

| Próba | Változás | `go` | `rust` |
|---|---|---|---|
| P1 | csak `core/cabinet/*_test.go` | `[]` | `false` |
| P2 | nem-teszt `.go` fájlok törlése | `[]` (`changed files: 0`: a törlés ki van szűrve, `mutation_plan.py:33` `--diff-filter=ACMR`) | `false` |
| P3 | `go.mod`, `.gremlins.yaml` | `[]` | `false` |
| P4 | `scripts/gremlins_gate.py` | `[]` | `false` |
| P5 | `Cargo.toml` | `[]` | `true` (az `--in-diff` csak a `*.rs` diffet kapja, `mutation-pr.yml:64`; hogy ilyenkor hány mutánst ad, **nem mértem**) |
| P6 | `core/cabinet/testdata/*.go` | `[]` (`:58` `testdata` kihagyva) | `false` |
| P7 | új csomag `pkg/newpkg` | `[{"id":0,"pkgs":"./pkg/newpkg"}]` | `false` |
| P8 | beágyazott modul `tools/goastdump` | `[]` (`:61`) | `false` |
| P9 | ismeretlen `--base` | script kilépési kód 1 (fail-closed) | — |

Tehát: a tervező **a teszt-változást a mutációs eredményt nem érintő változásnak kezeli** (az issue szerint ezt nem szabad: `ref/issue-169-body.md`, „`mutation_plan.py` must not treat test-only changes as unable to change the mutation result”), és
kapu-/függőség-/build-változásra nem eszkalál. Az új csomag viszont tervbe kerül (P7: **működő** ellenőrzés). Ezek a próbák a **tervezőt** mérték, nem a teljes PR-gate-et:
hogy a PR-ben ez ténylegesen zöldre fut-e, GitHub-futásban nem mértem.

### 4.3 Trust-boundary objektumok (az issue szerinti lista)

A státuszt a hívási út dönti (**reachability**): `deadcode ./...` + non-test `grep`. A `deadcode` az **alapértelmezett build-tag-ekkel** számol (nincs `ffi_cgo`).

| Objektum | Státusz | Hívási út / bizonyíték | Teszt | Besorolás |
|---|---|---|---|---|
| `core/cabinet/pki_verify.go` `VerifyCertificateChain` | **implemented** (feltételesen hívott) | `cmd/relay/bootstrap.go:79` és `:553` (az utóbbi a modul-elutasítási út, `outcome: "rejected"`), `cmd/relay/pki_companion.go:73`; mindkét `bootstrap.go` hívás csak `pkiAssets.TrustStoreLoaded` esetén él (`bootstrap.go:71`, ill. a `:538` ág `else`-e). **Ha nincs betöltött trust store, a modul-aláírás ellenőrzése kimarad** (`bootstrap.go:538-545`: `outcome: "skipped"`, `reason: "trust ecosystem not bootstrapped"`, csak `Warn` log) — a dokumentált, szándékos viselkedés (a `CLAUDE.md` is leírja), de a „skip ≠ pass” elv szerint a `skipped` állapotot a Relay nem teszi elfogadási kritériummá. A `CLAUDE.md` „scaffold” térképe (`pki_verify.go` bekötése) a függvény elérhetőségével **ütközik** (a `deadcode` nem jelzi unreachable-nek). Hogy az éles telepítésben a `TrustStoreLoaded` igaz-e, **nem mérve** | `TestVerifyCertificateChain` (`core/cabinet/pki_verify_test.go:47`), eseteit (rossz lánc/CRL/SPKI-pin) nem soroltam fel | **M** (hívott, tesztelt), **N**: a negatív esetek teljessége |
| `cmd/relay/cic_flow_manifest.go` `verifyBuildHash` | **tesztelt, de nem production-hívott** | `deadcode`: `cic_flow_manifest.go:205:25: unreachable func: moduleProject.verifyBuildHash`; non-test `grep`: nincs hívó. Tesztek: `cic_flow_manifest_test.go:172-180` | van, de csak a tesztből hívja | **I**: „módosított WASM” negatív követelmény a production úton nem teljesíthető, amíg a függvényt semmi nem hívja |
| `cmd/relay/proof_verify.go` `VerifyProofArtifact` | **implemented** | `cmd/relay/proof_verify_handler.go:63` | — | **M** |
| `ProofArtifactFromTrace`, `MarshalProofArtifact` (`proof_verify.go:142,162`), `ProofTraceStepFromActuation`, `ProofFromActuation` (`core/cabinet/proof_trace.go:41,74`) | **nem production-hívott** | `deadcode` unreachable | — | **I/N**: a bizonyíték-előállítás és a verifier közti híd megszakad |
| `core/cabinet/validate.go` `SetStripWasmModuleFunc` | teszt-segéd | `deadcode` unreachable; kommentje szerint tesztelési célra | — | **M** (kizárási jelölt a scope-ban: lásd 6.) |
| `core/modules/httpcap` `ActuatorFunc.RunFlow` | **production-hívott csak a cgo buildben** | `httpcap.go:11,24`: az actuátort a `cicffi.RunFlow` adja; `cmd/relay/actuator_cgo.go:1` `//go:build ffi_cgo`; `deadcode` (default tag) unreachable | `httpcap_test.go` | **N**: a production (cgo) út nincs sem coverage-ben, sem mutációban |
| `cmd/relay/actuator_cgo.go` (+ teszt) | **tag mögött** | `//go:build ffi_cgo`; a CI `ffi` job csak `./pkg/cicffi/...`-t futtatja a taggel (`verify.yml:311-312`), a `make test-ffi` a `./cmd/relay/...`-t is (`Makefile:374`) | `actuator_cgo_test.go` létezik | **K/N**: a `cmd/relay` cgo fájlok semelyik CI-jobban nem futnak |
| `pkg/cicffi` | **tag mögött** | `bridge_stub.go` `//go:build !ffi_cgo`; Go coverage default tag-gel **44.4%** (4/9 utasítás, csak a stub); a `ffi` jobban nincs coverage-mérés | ABI-határonkénti pozitív+negatív teszt lefedettsége **nem mérve** | **N** |
| `cmd/relay/bootstrap.go`, `cic_flow_registry.go`, `cic_flow_manifest.go`, `cic_flow_host_funcs.go` | **implemented** | build-tag nincs (`grep -l '^//go:build'` a fájlokra üres); a csomag `cmd/relay` Go coverage 91.14% | `cmd/relay` teszt-fájlok (23) | **M** a lefedettségre; a negatív esetek (manipulált manifest, jogosulatlan capability) teljessége **nem mérve** |
| `http-executor` (Rust) erőforráshatárok | **implemented** | tesztek: `redirects_are_returned_not_followed`, `oversized_response_body_is_refused_with_limit_exceeded`, `hostname_resolving_to_private_ip_is_blocked_by_resolver`, `oversized_request_body_is_refused_before_any_call` (`http-executor/src/lib.rs`, `http-executor/tests/`) | sor-lefedettség 97.60% (`http-executor/src/lib.rs`) | **M**; a Go-oldali azonos szabály azonos vektorokkal: **H** (a Go `httpcap` 16 utasítás, az actuátort injektálják) |
| `core/nexus/recorder` (proof recording) | **implemented** | Go coverage 86.44% (153/177) — **a 90% alatt**, a CI-padló 85 (`verify.yml:161`) | párhuzamos rögzítés, megszakítás tesztjei **nem mérve** | **N/H** |
| `core/cabinet/service.go`, `cicwasm.go` (WASM erőforráshatár, memóriahasználat) | **implemented** | `core/cabinet` coverage 93.39% | WASM memória/erőforrás-felszabadítás negatív tesztje **nem mérve** | **N** |

### 4.4 További Go csomagok (statement coverage és mutáció-ratchet)

A „CI-padló” a `verify.yml:149-171` táblából, a „mért” a saját, tiszta fás per-csomag futásból (`raw/go-per-package-coverage-clean-tree.txt`).
A „mutáció (baseline)” a `.mutation-baseline.json` **rögzített** értéke (2026-11-09, nem általam mért).

| Csomag | mért stmt cov | CI-padló | baseline: efficacy / mutant-coverage | Megjegyzés |
|---|---|---|---|---|
| `core/nexus/recorder` | 86.4 | 85 | nincs (≥90 követelmény) | a mért < 90, de a padló 85 → a CI zöld |
| `core/nexus/sync` | 88.9 | 88 | 84.62 / 100 | |
| `pkg/sourcedigest` | 85.7 | 85 | 77.78 / 100 | |
| `tools/certutils` | 83.0 | 82 | nincs | |
| `core/nexus/isolation` | 90.8 / 92.0 (ingadozik) | 90 | nincs | 6 futásból 3-3 |
| `core/nexus/operator` | 92.2 / 90.6 (ingadozik) | 90 | 88.57 / 97.22 | 6 futásból 4 / 2 |
| `core/nexus/git` | 93.5 | 92 | 65.00 / 95.24 | a legrosszabb mutációs hatásfok |
| `pkg/obs` | 98.1 | 97 | 80.00 / 83.33 | |
| `core/nexus/iac` | 94.9 | 90 | 88.71 / 95.38 | |
| `pkg/cicffi` | 44.4 (default tag) | kihagyva | 100 / 10.00 | lásd 4.3 |
| `tools/oci-sign-demo`, `statechain-demo`, `trustflow-demo` | 0.0 | kihagyva | 0 / 0 (nem fedett mutánsok) | demó belépési pontok |
| `core/modules/cibuild` | 94.9 | 94 | 100 / 87.5 | |
| `tools/symbolsgen` | 90.2 | 90 | 100 / 89.19 | |

A baseline szerint **12 csomag** (a 31-ből) a gremlins-ratchet alatt marad a 90-es cél alatt; az `mutation-pr` ezeket nem a 90-hez, hanem a rögzített állapothoz mérve engedi át.
Ez dokumentált, ideiglenes ratchet (a fájl kommentje: „Only ever raise a baseline”) — de a „Go mutation score >90%” cél **jelenleg nem teljesül**, a hiány pontos listája a fenti baseline-tábla.

## 5. A reprodukált kapuhiba (D)

Teljes, nyers anyag: `output/gate-defect-repro.md`. Összefoglaló:

- A `cargo mutants --list` három esete a **stdout-on megkülönböztethetetlen** (mind 0 bájt): jogos üres (kilépési kód 0), nem olvasható diff (6), hibás konfig (1).
- A workflow-sor (`bash -e`, `| grep -c . || true`) mindhárom esetre `n=0`, a következmény `shards=0` → a `rust` job `skipped` → a kapu `skipped`-et elfogad.
- **Mikor ad hibás felsorolás nulla mutánst:** mérve, minden olyan esetben, amikor a felsoroló nem ír stdout-ra, a kilépési kódtól függetlenül. Mérve: nem olvasható diff-fájl, hibás cargo-mutants konfig.
  Nem mérve (csak feltételezett): diff-eltérés a forrástól, eszköztelepítési hiba, memória/idő.
- A javítás nem a `|| true` puszta elhagyása (a jogos üres eset is megbuktatná a lépést) és nem a `pipefail` (a `|| true` mellett hatástalan): a felsorolás **kilépési kódját** kell előbb ellenőrizni.
- **Nem reprodukáltam** GitHub Actions-ban; a „kapu zöld” a workflow-logika olvasata.

## 6. Mérési scope javaslat (E)

Elv: az alap az **összes** csomag/crate; kizárás csak okkal, és a kizárás listája **verziózott fájlban, review-val módosítható** legyen. A javaslat **nem zár ki** csomagot a cél elérése
érdekében — az alábbi osztályozás a mért állapotból jön, a „debt” oszlop a kizárás **helyett** hiánylista.

| Osztály | Elemek | Javaslat | Ok / bizonyíték |
|---|---|---|---|
| **Production** | `cmd/relay`, `core/cabinet`, `core/modules/*`, `core/nexus/*`, `pkg/*` (kivéve `cicffi`, külön osztály), Rust: `connections`, `vault-adapter`, `module`, `ffi`, `executor`, `http-executor`, `cic-canonical` | **mérni, 90% cél** | ezek 3704/3997 = **92.67%** (21 csomag, tiszta fa, default tag) |
| **Production, tag mögött** | `cmd/relay/actuator_cgo*.go`, `pkg/cicffi` (`ffi_cgo`) | külön mérési profil `-tags ffi_cgo`-val a `ffi` jobban, **nem** kizárás | a default-profil 44.4%-ot ad, ez nem hiány a kódban, hanem a mérési profil hiánya |
| **Production, feature mögött** | Rust `live-vault` (`connect_mtls`, `flow::live`, `flow::run_live`) | külön profil `--features live-vault`-tel, vagy dokumentált, időkorlátos kivétel | ma sem coverage, sem mutáció nem látja; a `.cargo/mutants.toml` kommentjei szerint indokolt a default-buildben, de a kizárás állandósítása elfedné |
| **Tesztsegéd** | `cmd/relay/main_test_helper.go`, `core/cabinet/mock_wasm_manager.go`, `pkg/obs/capture.go`, `SetStripWasmModuleFunc`, `pkg/canonicaljson.SetToJSONMock` | **mutációból és coverage-ből kizárható, ha** a fájl nem tartalmaz production-hívott kódot | a `deadcode` mindet `unreachable`-nek jelzi (`raw/deadcode-output.txt`); a kizárás **fájlonként, ok-mezővel** |
| **Generált** | `context/SYMBOLS.md`, `MANIFEST.sha256`, `*.yaml` kísérő-metaadatok (a klónban 189 ilyen fájl módosult a klónozáskor) | kizárni a mérésből; **a generátor kapuja** (`symbol drift`, `manifest-check`) fedi | a drift-ellenőrzés `verify.yml:60-63`, `manifest-check.yml` |
| **Kísérleti / nem bekötött** | `tools/*-demo` (`oci-sign-demo`, `statechain-demo`, `trustflow-demo`) | coverage-ből ma is kihagyva (`verify.yml:135-137`), a baseline 0%-ot tart; javaslat: **explicit, indoklással ellátott kizárás** a verziózott scope-fájlban, és a `make demo*` célok mint külön ellenőrzés | a demó belépési pontok `main` csomagok; nem production futtatási út |
| **Nem root modul** | `tools/goastdump` (külön `go.mod`) | a mutációs tervező szándékosan kihagyja (`mutation_plan.py:61`); a `python` job `go test`-je fedi | **mutáció nem fedi**: scope-fájlban nevesíteni |
| **Nem Go/Rust** | Python `tools/`, `scripts/` | külön mérés (`pytest --cov=tools`, padló 80); a `scripts/` **nincs** a `--cov=tools` alatt | a három kapu-script a `scripts/`-ben van → a kapu-logika Python-lefedettsége **nem mérve** |

A scope-fájl formája (javaslat PR-03/04-re): egy verziózott, review-val módosítható fájl, minden bejegyzése `path`, `class`, `reason`, `measured_by` mezőkkel; a kapu
**elbukik**, ha egy tracked forrásfájl se a scope-ban, se a kizárások között nem szerepel.

## 7. Aktuális mért állapot (F)

Minden mérés a `bc2c4e0` tiszta fáján, a pinelt konténerben. A parancsok: `raw/gocov.sh`, `raw/rustcov.sh`.

| Metrika | Érték | Mi tartozik hozzá | Megjegyzés |
|---|---|---|---|
| **Go statement coverage, minden csomag** | **88.77%** (3906/4400, 29 csomag a profilban) | `go test -count=1 -coverprofile ./...` (`go tool cover -func`: `88.8%`) | a **90% alatt**; a modul-szintű küszöböt a CI nem ellenőrzi |
| Go statement coverage, demó `main`-ek nélkül | 92.54% (3906/4221) | kizárva: `trustflow-demo`, `statechain-demo`, `oci-sign-demo` | csak tájékoztató számítás a profilból; a kizárás itt **javaslat**, nem döntés |
| Go statement coverage, `cmd`+`core`+`pkg` | 92.67% (3704/3997, 21 csomag) | | |
| Go tesztek | mind a 31 csomagnál sikeres (0 `TESTFAIL`) | | `-race` **nincs** mérve (a CI `-race`-szel fut) |
| Go coverage nemdeterminizmus | `isolation` 90.8/92.0, `operator` 92.2/90.6 | 6 ismétlés/csomag (`raw/go-coverage-repeat.txt`); `recorder`, `sync` stabil | az ok **nincs** vizsgálva; az `operator` a padló (90) fölött, de a ratchet-padlók 90 közelében érzékenyek |
| **Rust line coverage** | **98.47%** (2644/2685) | `cargo llvm-cov --all --locked`, default feature-ök, 12 forrásfájl | a `live-vault` kód nincs a nevezőben |
| Rust region coverage | 97.65% (4617/4728) | | |
| Rust function coverage | 96.62% (400/414) | | |
| Rust tesztek | `cargo test --all --locked`: kilépési kód 0, minden `test result: ok` | | |
| **Go branch coverage** | **nem mérve** | a Go nem ad ág-metrikát; ehhez külön eszköz kell | Forms: `coverage_gate.py`, `cic-coverage-report/1` |
| **Rust branch coverage** | **nem mérve** | az `llvm-cov` `branches` számlálója 0/0 | ág-mérés nincs bekapcsolva |
| **Go/Rust mutáció pontszám (FULL)** | **nem mérve** | a rögzített baseline (2026-11-09) létezik, de **nem általam mért** | a Rust listázott mutánsok száma **300** (`cargo mutants --workspace --list`), ez felsorolás, nem ítélet |
| **`-race`, atomic Go coverage** | **nem mérve** | | |
| **`-tags ffi_cgo` Go coverage** | **nem mérve** | a Rust staticlib építését és a cgo-s futást nem végeztem el | |
| **Rust ABI-határonkénti pozitív/negatív teszt** | **nem mérve** | | |
| **`cargo-deny`** | **nem mérve** | a nightly `security` bukásának lehetséges oka | |
| `govulncheck ./...` | tiszta (`No vulnerabilities found.`, exit 0) | a `bc2c4e0`-n, 2026-11-14 | a nightly bukások commitja `13b8425`, a `bc2c4e0` egy committal újabb |
| `deadcode ./...` | exit **0**, 106 `unreachable` sor | `raw/deadcode-output.txt` | lásd 4.1 |

## 8. Javaslat a PR-02-re

Kötelező, fail-closed szétválasztások (a PR-02 a mérési útvonalak hibáit javítja, **egyetlen javítás sem lazít küszöböt**):

1. **Felsorolás:** a `cargo mutants --list` kimenetét fájlba, a kilépési kódot **előbb** ellenőrizni; üres-de-érvényes eset külön (`n=0` csak sikeres felsorolásból). Három workflow-sor: `mutation-pr.yml:65`, `nightly.yml:146,148`.
   Negatív teszt: A/B/C eset (`gate-defect-repro.md`) → B és C legyen piros.
2. **Eszköz-verzió pin:** `cargo-mutants` (27.1.0 mérve), `cargo-llvm-cov`; `Makefile` `GREMLINS_VERSION` igazítása a CI-hoz — csak ha külön döntés.
3. **`mutation_plan.py`:** a P1–P6, P8 vakfoltokra eszkaláció FULL-ra, vagy a tesztváltozásra a módosított teszt által végrehajtott termékkód bevonása (Forms: `docs/DELTA-DIFF-GATE.md` §2.1–2.2); törölt fájl (P2) ne legyen csendes; minden esethez negatív teszt, ami az előző hibát reprodukálja.
4. **Nightly horgony:** a „legutóbbi sikeres éjszaka” ne a `plan` sikeréből, hanem a **mért** eredményből számolódjon (Forms: `tools/nightly_last_full.py`).
5. **`deadcode` lépés:** vagy kimenet-ellenőrzéssel kapuvá tenni (a 106 sor ismert: baseline), vagy kimondani, hogy tájékoztató; a mostani állapotban a lépés zöld jelzése félrevezető.

A PR-02-be **nem** való: Go/Rust shard-teljességi ellenőrzés (PR-03), ág-lefedettség (PR-04), seeded defects (PR-05), a `verifyBuildHash` bekötése (termékkód-javítás, külön PR a #169 szabálya szerint).

**Nyitott, a PR-02 előtt a tulajdonos döntésére:** a nightly `security` bukás oka (#160); a `clone`-kori piszkos fa oka; hogy a `TrustStoreLoaded` igaz-e az éles telepítésben; a CLAUDE.md scaffold-térkép frissítése (`pki_verify.go` ma bekötött).

## 9. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `mutation-pr.yml:65`, `nightly.yml:146,148` `\| grep -c . \|\| true` a felsorolás hibáját nullának olvassa | implemented (a hiba) | `gate-defect-repro.md` 2. szakasz: `n=0` az A/B/C esetre; `raw/d-repro-run2.txt` | `bash -e` emuláció konténerben, cargo-mutants 27.1.0 | **magas**: a Rust mutáció csendben kimarad |
| A `rust` job `skipped`, a `mutation-pr` kapu elfogadja | implemented (workflow-olvasat) | `mutation-pr.yml:114,187`; `nightly.yml:193,251` | olvasat; GitHub futásban **nem mérve** | magas |
| A hiba a nightly horgonyt előreviszi | implemented (workflow-olvasat) | `nightly.yml:96-104` | olvasat; futásban nem mérve | közepes |
| A cargo-mutants telepítése nincs pinelve a CI-ben | implemented | `mutation-pr.yml:55-57,131-133`; `nightly.yml:130-132,210-212`; `mutation.yml:93-96` | olvasat | közepes |
| Go statement coverage (minden csomag) 88.77% | implemented (mért) | `raw/go-total-coverprofile.out`; `raw/gocov.sh` | `go test -count=1 -coverprofile ./...`, pinelt konténer, tiszta fa | a küszöbbel (90) szemben alatta marad |
| Go `cmd`+`core`+`pkg` coverage 92.67% | implemented (mért, számított) | a profilból összegezve (`raw/go-total-coverprofile.out`) | profil-összegzés | alacsony |
| `isolation` és `operator` coverage futásról futásra ingadozik | implemented (mért) | `raw/go-coverage-repeat.txt` | 6 ismétlés/csomag | közepes (reprodukálhatóság), ok nem ismert |
| Rust line coverage 98.47% | implemented (mért) | `raw/rust-llvm-cov-table.txt`; `cargo llvm-cov --json` totals | `cargo llvm-cov --all --locked`, default feature-ök | a `live-vault` kód nincs a nevezőben |
| Rust és Go branch coverage | nem mérve | llvm-cov `branches` 0/0; Go-nak nincs | — | magas (cél: >90% branch) |
| Mutáció pontszám (Go, Rust) | nem mérve | csak a rögzített baseline (nem általam mért) | — | magas |
| 12 csomag a mutációs baseline-ban a 90 alatti rögzített állapotú | implemented (rögzített, nem mért) | `.mutation-baseline.json`; 4.4 tábla | olvasat | közepes |
| `deadcode ./...` kilépési kódja 0, 106 sor | implemented (mért) | `raw/deadcode-output.txt` | `deadcode@v0.44.0`, pinelt konténer | közepes: nem kapu |
| `verifyBuildHash` nem production-hívott | implemented (mért) | `deadcode`: `cic_flow_manifest.go:205`; non-test grep üres; tesztek `cic_flow_manifest_test.go:172-180` | `deadcode` + `grep -rn verifyBuildHash --include=*.go . \| grep -v _test.go` | magas (trust-boundary) |
| `VerifyCertificateChain` production-hívott | implemented | `cmd/relay/bootstrap.go:79,553`, `pki_companion.go:73` | non-test `grep`; a `:79` feltételes (`TrustStoreLoaded`) | közepes; az éles `TrustStoreLoaded` nem mérve |
| A `CLAUDE.md` „pki_verify.go scaffold” állítása elavult | implemented (ellentmondás) | lásd az előző sor | olvasat | alacsony (doksi) |
| `cmd/relay` cgo fájlok nincsenek a CI `ffi` jobban | implemented | `verify.yml:311-312` vs `Makefile:374`; `actuator_cgo.go:1` | olvasat | közepes |
| `mutation_plan.py` P1–P6, P8: `go: []` | implemented (mért) | 4.2 tábla; a próba parancsok a jelentésben | scratch másolat, helyi commitok | magas |
| `mutation_plan.py` ismeretlen base-re fail-closed | implemented (mért) | P9: kilépési kód 1 | | — |
| A nightly `security` 2026-11-11…14 bukik; ok ismeretlen | implemented (a bukás), nem mérve (az ok) | `gh run list` (run id-k 4.1) ; issue #160 nyitva | `gh` API, olvasás | közepes |
| `govulncheck` a `bc2c4e0`-n tiszta | implemented (mért) | `raw`/scratch kimenet | `govulncheck@v1.1.4`, pinelt konténer | alacsony |
| A `main` rulesetje 7 kötelező check, PR/aláírás szabály nincs | implemented | `gh api .../rulesets/26873807` | `gh` API, olvasás | közepes |
| A Relay-ben nincs seeded-defect, quality-gate self-test, evidence, proof-aware réteg | concept (nincs runtime megfelelő) | `git ls-files \| grep -iE 'seeded\|selftest'` üres; a Forms ezeket tartalmazza | file-lista | magas (cél a #169 PR-05/08/10) |
| A Forms kapui fail-closed-ak és önteszteltek | nem mérve (olvasat) | `tools/quality_gate.py:1-50`; `docs/FAST-FULL.md` | **a Forms CI-t és selftestet nem futtattam** | referenciaként: alacsony |
| A klón klónozáskor 189 módosított `.yaml`-t hordozott | implemented (mért) | patch + `git status`; a patch nincs commitolva | `git status --short` | alacsony; az ok nem ismert |
| `connect_mtls`, `flow::live`, `flow::run_live` mutációból kizárt | implemented | `.cargo/mutants.toml` | olvasat | közepes (nem mért terület) |

## 10. Amit ez a jelentés nem állít

- Nem állítja, hogy a mért coverage-szám a CI-ben is ugyanez: a CI `-race -covermode=atomic` profilt és push-on szűkített csomagkört használ, én nem.
- Nem állítja, hogy a GitHub Actions-ban a felsorolási hiba ténylegesen zöld PR-t ad: ezt nem futtattam.
- Nem állítja, hogy a hívási utak az éles telepítésre igazak: a `deadcode` az alapértelmezett build-tag-ekkel, a `main` csomagokból számol.
- A Forms-ról szóló sorok olvasaton alapulnak, nem a Forms futtatásán.
