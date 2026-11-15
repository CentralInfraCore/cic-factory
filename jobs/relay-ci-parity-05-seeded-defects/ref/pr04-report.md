# PR-04 jelentés — objektumszintű, ellenőrizhető mérési modell

Job: `relay-ci-parity-04-object-level-measurement` · a CIC_Relay #169 PR-04 lépése. **Mind report-only**: nincs új blokkoló kapu,
nincs tesztkihagyás, **küszöb és baseline nem változott** (a `scripts/gremlins_gate.py` és a `.mutation-baseline.json` a diffben érintetlen).
Alap: `ref/owner-decisions-2026-11-14.md`, `ref/pr03-report.md`.

## 1. Vizsgált állapot

| | |
|---|---|
| CIC_Relay `main` | `852594ae6180828dac090038cc443a6ac3e57bd4` (tartalmazza a PR-03 merge-et); friss klón, `git status --short \| wc -l` = **0** a klónozás után és a mérések előtt |
| Relay munkaág | `feature/relay-ci-parity-04-object-level-measurement`: `c59f0a8` (az első CI-futás, Relay #174) → **`34043f7`** (a regresszió javítása, lásd 9.) |
| Bizonyító (piros-út) ágak | `ci-proof/relay-ci-parity-04-red-path` `497b508` (Relay #175, a `c59f0a8`-ra építve; **lezárva, nem mergelve**) és `ci-proof/relay-ci-parity-04-red-path-2` **`514d9e4`** (Relay **#178**, a javított `34043f7`-re építve; draft, DO NOT MERGE) — **szándékosan hibásak, nem mergelendők** |
| cic-primitive-forms | `2f02a75592a4b0894a3b76891e9ba3741479a7c5` (`main`), csak referencia |
| Mérési környezet | `rust:1.96.1-bookworm@sha256:d99f7b31…c4abd8` (rustc 1.96.1, `cargo-llvm-cov 0.9.1`, `cargo-mutants 27.1.0`, GNU `c++filt` Binutils 2.40), `golang:1.26.10` |
| Hogyan futott | ebben az interaktív sessionben (nem `run-job.sh`); a builddirek `~/.cache/relay-ci-parity-04/` alatt, **nem** a 16 GB-os `/tmp` tmpfs-en (a PR-03-ban az megtelt) |
| A Rust-mutációs bemenet | a PR-03 valódi 8-shardos futása (`7ac6e80`); a Rust-fa `7ac6e80` és `852594a` között **azonos** (`git diff --stat -- '*.rs' Cargo.*` üres) |

## 2. A feltárt eszköz-képességek (valódi kimenet alapján)

| Eszköz | Mért |
|---|---|
| `go test -coverprofile` | utasítás-lefedettség blokkonként; a modul 2917 blokk, **88,8%** (egyezik a PR-01-gyel); ág-lefedettség **nincs** |
| `tools/goastdump` kimenete | legfelső szintű deklarációk, **pozíció nélkül** → nem alkalmas span-hozzárendelésre; a `go.meta.gen.py` fogyasztja, ezért **nem módosítottam** |
| `cargo llvm-cov --json` | `data[0].functions`: 788 bejegyzés, **mangled v0 nevekkel** (`_RNvCs…`), régió-listával (`[sor,oszl,sor,oszl,count,…,kind]`); `branches: []` minden függvényben |
| **`cargo llvm-cov --branch` a pinelt stabil 1.96.1-en** | **elbukik**: `error: 1 nightly option were parsed` (`raw/llvm-cov-branch-on-stable.txt`) — a II.B mért válasza |
| demangling | a pinelt image **binutils `c++filt`-je** demangle-eli a v0-t (`cic_canonical[0]::tests::vectors_mirror_go`); a toolchain sysroot-ja nem tartalmaz LLVM-demanglert |
| ugyanaz a Rust-függvény | többször szerepel (**788 bejegyzés / 616 normalizált szimbólum / a tool saját összesítése 414**): per-binary crate-disambiguator, generikus példányok, closure-ök, tesztkód |
| `cargo mutants --list --json` | a `function.function_name` **modul-/típus-minősített** (`logic::echo`), nem puszta név; **2 mutánsnak nincs `function` mezője** (nem függvényen belüli) |
| `gremlins v0.6.0` | pozíciónként ír sorokat (`KILLED … at main.go:375:15`, csomag-relatív fájlnév), az összegzés mellett; **nem pinelt szöveges formátum** |

## 3. A modell: mit épít ma (valódi adaton, `raw/evidence-summary.json`)

`object-evidence/1`, digest `6bccf3fb…`, `mutation-policy/2`, commit `852594a`, fa `d2a15b0b…`.

| Egység | Objektum | Lefedettség `MEASURED` | `UNVERIFIABLE` | Mutáció | Teszt-kapcsolat |
|---|---|---|---|---|---|
| Go, root modul | 464 | 453 (utasítás) | **11**: 8 `FILE_NOT_IN_PROFILE`, 3 `NONDETERMINISTIC` | 464 `UNVERIFIABLE` (`TOOL_LIMIT`) | 464 `UNVERIFIABLE` (`TOOL_LIMIT`) |
| Go, `goastdump` (külön) | 15 | 15 (utasítás) | 0 | 15 `UNVERIFIABLE` (`TOOL_LIMIT`) | 15 `UNVERIFIABLE` (`TOOL_LIMIT`) |
| Rust | 196 | 196 (**régió**) | 0 | **141 `MEASURED`**, 55 `NOT_APPLICABLE` (`NO_MUTANTS_LISTED`) | 196 `UNVERIFIABLE` (`TOOL_LIMIT`) |
| **Összesen** | **675** | **664** | **11** | 141 / 55 / 479 | 0 / 0 / 675 |

- A 8 `FILE_NOT_IN_PROFILE` a `ffi_cgo` build-tag mögötti, az alapértelmezett buildben nem fordított változatok (`pkg/cicffi`, `cmd/relay/actuator_cgo.go`): a build-tag-es változat **külön objektum**, nem összeolvasztva.
- A 3 `NONDETERMINISTIC` (6 egymás utáni profil): `core/nexus/isolation.SubprocessWorker.Decrypt` (26–27 / 33), `core/nexus/operator.PollingWatcher.Watch` (14–16 / 16), `core/nexus/operator.scanDir` (12–13 / 14). Ez egyezik a PR-01 megfigyelésével (az `isolation` és az `operator` csomag szórt). Ezek **nem kaptak pontos értéket**.
- **Blokk-hozzárendelés (Go root):** 2807 hozzárendelt, **0 részleges**, **9 hozzá nem rendelhető** (függvényen kívüli blokk, pl. csomagszintű inicializáció), 3 profilfájl nincs a leltárban. `goastdump`: 134/134 hozzárendelt. **Arányosítás sehol nem történt.**
- **Rust mutánsok:** 300 listázott; 289 objektumhoz rendelve, **9 többértelmű** (nem választottam: nincs hozzájuk objektum-ítélet), 0 hozzá nem rendelhető, 2 függvényen kívüli. Objektumokra összegezve: **289 mutáns = 211 caught + 78 unviable** (0 missed, 0 timeout). A teljes terv 217 caught / 83 unviable: a különbség (6 caught + 5 unviable = 11) pontosan a 9 többértelmű és a 2 függvényen kívüli mutáns, tehát **minden mutáns elszámolt**.
- **Rust, 46 objektum** (a 141 mutánsos objektumból) minden mutánsa `unviable`: ezek elsődleges score-ja **`NOT_APPLICABLE (ALL_UNVIABLE)`**, nem 100%; a többi 95 objektum score-ja `MEASURED` és mind 100% (nincs 100% alatti). Ez a nulla-nevező szabály a valós adaton.
- **Teszt-kapcsolat:** 675/675 `UNVERIFIABLE` (`TOOL_LIMIT`): a per-teszt hozzárendelés a II.C szerint megvalósítható, de nem épült be (lásd 6.).

## 4. A három tulajdonosi döntés megvalósítása (`mutation-policy/2`)

| Döntés | Megvalósítás |
|---|---|
| `unviable` sem caught, sem missed; kötelező külön metrika; ma nem buktat | a `quality_gate.py verify` mindig kiírja: `unviable (mandatory metric, report-only): 83/300 = 27,67%`; a `missed` és a `timeout` ma is **buktat**, az `unviable` ma sem; szigorítás csak **`mutation-policy/3`**-mal |
| Rust score = `caught/(caught+missed)` | elsődleges: `rust score (primary, mutation-policy/2): caught/(caught+missed) = 217/217 = 100,00%`; a régi `caught/planned` (217/300 = 72,33%) **`legacy`** néven kiírva marad; a nevezőből kizárt `timeout` ma 0 egy zöld futásban (mert buktat) |
| `goastdump` a scope-ban, külön riportolás | `.measurement-scope.json`: `separate` osztály, **külön egység** (`unit: goastdump`) a rekordban és az összesítőben; a Go-átlagban **nem** jelenik meg |

**Nulla nevező** (`caught+missed == 0`): nem 100% és nem 0%: `NOT_APPLICABLE` (`NO_MUTANTS_PLANNED` / `ALL_UNVIABLE` / `NO_EVALUABLE_MUTANT`) vagy `UNVERIFIABLE` (`MEASUREMENT_MISSING`) — objektumszinten és globálisan is.

**Ütközés a mai kóddal, kimondva.** A PR-03 `mutation-policy/1` elsődleges értéke `caught/planned` volt; ez **definíció-változás**, ezért új policy-verzió (a rekord és a kapu verziója eltérésre piros). A buktató szemantika **nem szigorodott és nem gyengült**: a 90%-os score **jelentett érték**, nem helyettesíti a `missed == 0` szabályt (a mai kapu ennél szigorúbb). A PR-03 egy tesztjét (`mutation-policy/1` szövege) a policy/2-re kellett cserélnem.
**Az `unviable` figyelmeztető szint javaslata** (nem döntöttem el; a tulajdonos hagyja jóvá): a mért érték **27,67%** összesen, fájlonként 0 és ~60% között. Javaslat: *report-only* figyelmeztetés, ha az összesített arány a mért érték fölé emelkedik (pl. 33% fölött), mert a mostani érték a kiinduló ratchet-alap; a fájlonkénti szórás miatt fájl-szintű küszöböt **nem** javaslok.

## 5. Az ellenőrzés három szintje a valódi rekordon (`raw/verify-real.txt`)

| Eset | L1 | L2 | L3 |
|---|---|---|---|
| a valódi rekord, checkout és minden bemenet | `INTEGRITY_OK` | `BOUND_TO_INPUTS` | **`PARTIAL`** |
| ugyanaz bemenet és checkout nélkül | `INTEGRITY_OK` | **`NOT_CHECKED`** | `PARTIAL` |
| egy objektum törölve, a digest és az összesítő **következetesen újraszámolva** | **`INTEGRITY_OK`** | `BOUND_TO_INPUTS` | **`FAIL`** (`463 objects but 464 top-level func lines`) |
| egy bemeneti fájl megváltoztatva | `INTEGRITY_OK` | **`FAIL`** (`does not match the digest`) | — |
| a coverage `kind` = `branch` | **`FAIL`** (`not one of ('statement','line','region')`) | `NOT_CHECKED` | `NOT_CHECKED` |

**Az L3 bizonyítja és nem bizonyítja** (a valódi rekordon): *bizonyított:* a Go-objektumok száma egyezik a **független** `func`-sor-számlálással (root 464, `goastdump` 15), és minden, a `cargo-mutants` által ismert függvénynek van objektuma. *Nem bizonyított:* az a Rust-függvény, amelynek nincs mutánsa és nincs lefedettségi bejegyzése, függetlenül nem felsorolható. **Nincs egyetlen „VERIFIED”.** Az L1–L3 **nem** bizonyítja, hogy az eszközök valóban a megjelölt fán futottak: ez a PR-08/09 (hitelesítés) témája.

**Az L3 első valódi eredménye hiba volt, és ez jó.** A rekord első változatán az L3 `FAIL`-t adott (`ffi/src/lib.rs: cic_ffi_abi_version` ismert a `cargo-mutants`-nak, de nincs objektuma). Az ok **a saját teszt-kód felismerőm hibája** volt: „az első `#[cfg(test)]`-től a fájl végéig minden teszt” — az `ffi/src/lib.rs` 588. sorában fájl közepi `#[cfg(test)]`-elem van, utána produkciós kód. Az L1 ezt nem fogta volna meg (belsőleg konzisztens volt). Javítás: tokenizáló elem-span (a `#[cfg(test)]` által jelölt *elem* sorai, string/komment/char/raw-string/lifetime kezeléssel): `ffi/src/lib.rs` → (588–877), (1014–1163). Utána a Rust 190 → 196 objektum, `mutants_unmapped` 1 → 0, az L3 `PARTIAL`.

## 6. A II. rész: megvalósíthatósági jelentések (mérés és javaslat; **nincs bekötés**)

| Tétel | Mért | Javaslat / döntés |
|---|---|---|
| **II.A Go ág-lefedettség** | **mérve** (`raw/part2a-go-branch*.txt`), jelölt: `github.com/rillig/gobco` **v1.3.4** (forrás-instrumentáló, *feltétel-szintű* lefedettség). Pinelhető: `go install …@v1.3.4`, modul-hash `h1:4weHt9u2CyTOnEJ/7z6fAcHZvJHy1pNXm8danDh3TA8=` (a toolchain ellenőrzi). **Reprodukálható**: két futás kimenete azonos. **Három csomag:** `./pkg/merkle` utasítás **98,3%** ↔ gobco **19/22** feltétel (86,4%), 4,6 s; `./pkg/canonicaljson` **96,7%** ↔ **43/46** (93,5%), 3,5 s; `tools/goastdump` (külön modul) **78,0%** ↔ **104/160** (65,0%), 1,4 s. A kimenet soronként `fájl:sor:oszlop: condition "…" was N times true but never false`, tehát a függvény-spanhez hozzárendelhető. A natív `go test` utasítás-lefedettsége a tesztnél ~5 ms, a gobco ~1,4–4,6 s csomagonként (instrumentálás + fordítás); a teljes modul költsége **nem mért** | **Nem fogadtam el, a döntés a tulajdonosé.** Kockázatok, mérve: (1) a `gobco ./...` a **külön modulban** `nothing to instrument` üzenetet ad **0-s kilépési kóddal** (fail-open jel: csomagonként, `.`-tal kell hívni, és ez a kimenet `UNVERIFIABLE`, nem nulla); (2) tesztek nélküli csomagra `0/2` és 0-s kilépés (a „nincs mérés” és a „0%” azonos kimenet); (3) a `-branch` kapcsoló azonos számot ad más címkével (`Branch coverage: 19/22`): a név a **feltétel-szintet** takarja; (4) a modul-cache listájában **nincs LICENSE fájl** (README, go.mod, go.sum, forrásfájlok): a licenc **nem ellenőrzött**, ezt az elfogadás előtt tisztázni kell. Ha elfogadják: pinelt `v1.3.4`, report-only, csomagonként, a név `condition`, nem `branch` |
| **II.B Rust ág-lefedettség** | **mérve** (`raw/part2b-nightly-branch.txt`): a pinelt **stabil 1.96.1-en** a `--branch` elbukik (`1 nightly option were parsed`); a pinelt **`nightly-2026-07-01`-en** (`rustc 1.98.0-nightly f46ec5218 2026-06-30`, `llvm-tools-preview`) a `cargo llvm-cov --all --locked --branch --json` **kilépési kód 0, 87 s** (fordítással), `totals.branches`: **146 ág, 124 lefedett (84,93%)**, 66 függvényhez (a 788 bejegyzésből) van ág-rekord; a build-könyvtár 1,9 GB | **megvalósítható**, de a **nightly egy másik fordító** (1.98 vs 1.96.1): csak külön, **pinelt, report-only** lépésként ajánlom, és a régió-lefedettségből nem szabad belőle számolni; a döntés a tulajdonosé. Az ág-rekord objektumhoz rendelése (függvény-span) **nem épült be** |
| **II.C teszt–objektum hozzárendelés** | **Go mérve** (`./pkg/merkle`, 24 teszt): teljes csomag 298 ms; per-teszt profil 7047 ms (**~293 ms/teszt**); a per-teszt futások lefedett blokkjainak **uniója egyenlő** a teljes futáséval (25 = 25) → **pontos**; a modulban **817 teszt**. **Rust mérve** (`raw/part2c-rust-pertest.txt`, `cic-canonical` lib, stabil 1.96.1): 3 unit teszt; teljes futás 1127 ms; per-teszt **~646 ms/teszt**; a lefedett kód-régiók uniója **99 = 99** → **pontos** | mindkét nyelven megvalósítható; a **teljes modul/workspace költsége nem mért** (817 × ~0,3 s Go, a Rust workspace per-teszt futása csak egy crate lib-tesztjein mérve; az integrációs tesztek és a többi crate **nem mérve**) |
| **II.D változás-hatás** | **mérve:** Go csomagszint (`go list`): 31 csomag; pl. a `pkg/canonicaljson`-t 6, a `core/cabinet`-et 3 csomag importálja közvetlenül (tesztekkel együtt); Rust crate-szint (`cargo metadata`): 7 crate, a `connections` változása → `cic-ffi`, `connections`, `module`, `vault-adapter` | csak csomag-/crate-szintű hatást állítok; a **függvény-szintű tranzitív** hatás hívási-gráf eszközt igényel (**nem mérve**) → `UNVERIFIABLE`; semmit nem hagy ki belőle senki |
| **II.E Go per-mutáns kimenet** | **részben mérve:** a gremlins pozíciónként ír sorokat (a PR-03 `goastdump-measurement.txt`-ben is); a szöveg **nem pinelt**, stabilitását nem vizsgáltam | a Go mutáció-mező ezért `UNVERIFIABLE (TOOL_LIMIT)`; elemzett szöveg **nem** válhat blokkoló kapuvá |

## 7. A `goastdump` hiányzó lefedettségének osztályozása (döntés 3, `raw/goastdump-cover.out` + a rekord `uncovered` spanjei)

15 objektum, **7 teljesen lefedett**, **8-nál van kimaradt utasítás**. Az osztályozás a forrás **olvasatán** alapul (a sor és a blokk a rekordból); a *következményre* vonatkozó állítás **nem mért**.

| Objektum | Lefedett / összes | Kimaradt | Osztály |
|---|---|---|---|
| `main` | 0 / 11 | a teljes függvény (391–407) | **belépési pont** (usage-hiba, kimenet-kódolás): nincs teszt, ami futtatná |
| `call` | 18 / 26 | 231–236 (`IndexListExpr`/`ParenExpr` kicsomagolás), 246–253 és 262 (nem exportált szelektor; nem-azonosító receiver) | **AST-feldolgozás**: kevésbé gyakori szintaxis-alakok |
| `typeName` | 7 / 11 | 109–114 (`ParenExpr`, `IndexListExpr`), 120–122 (előre deklarált típus), 125 | AST-feldolgozás (109–114); **védelmi/alapértelmezett ág** (120–125) |
| `exprType` | 5 / 9 | 135–136 (`ParenExpr`), 141–144 (`new(T)`), 146 | AST-feldolgozás; alapértelmezett ág (146) |
| `identType` | 9 / 15 | 152–154 (`id.Obj == nil` védelem), 162–170 (deklarációs alakok), 177 | védelmi ág (152, 177); AST-feldolgozás (162–170) |
| `recvTypeName` | 4 / 7 | 270–275 (`ParenExpr`, `IndexListExpr`), 279 | AST-feldolgozás; alapértelmezett ág (279) |
| `dump` | 50 / 52 | 326–327 (import-útvonal `Unquote` hiba → `continue`), 331–332 (`_`/`.` import-alias) | **hibakezelés** (326); AST-feldolgozás (331) |
| `visit` | 10 / 11 | 204–206 (`n == nil` védelem) | védelmi ág |

A kimaradt ágak többsége **AST-feldolgozási alak vagy alapértelmezett „nincs típus” visszatérés**: ha a szintaxis-alak nem ismert, az eszköz „típus nélkül” hagyja a hivatkozást. Olvasatom szerint ez a generált meta-fájlokban **kevesebb hivatkozást** adna, nem hibás kimenetet — ez **következtetés a forrásból, nem mérés**. Teszt-bővítés nem része a jobnak.
A gremlins a `goastdump` `testdata/sample.go`-ját is mutálta (PR-03 mérés): a scope `test-data` osztálya kiveszi az objektummodellből **indoklással**; a gremlins viselkedését nem módosítottam.

## 8. Az R- és N-tesztek bizonyítéka

**R (a meglévő viselkedést módosítják/védik): a régi (`852594a`) fán** `raw/r-tests-on-old-code.txt`: **13 failed, 1 passed**. Szétválasztva:
- **7 a hibát reprodukáló bukás (CLI-kimenet szintjén, az elvárt okból):** R1 (`unviable` nem változtatja az elsődleges score-t), a legacy-sor, az `unviable` arány sora és a négy score-állapot — mind `AssertionError: no primary score line in the output` (a régi kimenet `rust score: caught/planned …`, nincs policy/2 elsődleges score és nincs `unviable` metrika).
- **6 szerkezeti bukás** (a `primary_score` / `unviable_ratio` függvény nem létezik a régi fán): ezek **nem** bizonyítékok.
- **Őrző:** `test_a_survivor_is_still_red_whatever_the_score_is` (`missed > 0` → piros) a régi fán **zöld**, az újon is.

**N (új szerződések): a régi állapotban nincs mit futtatni**, ezért a bizonyíték: (1) az új kódon **65 teszt zöld** (`raw/new-tests-on-new-code.txt`; a valós fixture-ön elfogad), (2) hibás bemenetre **konkrét üzenettel** utasít el, (3) **ellenpróba** (`raw/teeth.txt`): a verifier egy-egy ellenőrzését egy scratch-másolaton kiiktatva a hozzá tartozó teszt **bukik** — mind a **12** esetben (azonosító-ütközés, digest, összesítő-újraszámolás, eszközverzió, `branch` enum, osztályozatlan fájl, nemdeterminizmus, többértelmű mutáns, részleges blokk, nulla nevező, L2 bemenet-digest, L3 független számlálás). (4) A hibás bemenetek valós eszközkimenetből származtatottak (`tests/test_tools/fixtures/object_model/README.md`).

## 9. GitHub Actions: a futások és a CI-hibák kivizsgálása

Minden sor a **megadott headSha-hoz és run id-hoz** kötött. A GitHub `gh run list --commit <sha>` adta őket.

| PR | headSha | Workflow | Run id | Eredmény |
|---|---|---|---|---|
| Relay #174 | `c59f0a844f0779cbe02d37dff850334271e08145` | `manifest-check` | 43638326973 | success |
| | | `object-evidence` | 43638327223 | **success** |
| | | `verify` | 43638326995 | **failure** (`coverage`) |
| | | `mutation-pr` | 43638326975 | **failure** (`go (chunk 4)`, `completeness`, `mutation-pr`) |
| Relay #175 (draft, DO NOT MERGE) | `497b5080f4d21478211b963eec85adffeba079f9` | `object-evidence` | 43638400559 | **failure, az elvárt L3 FAIL** |
| | | `manifest-check` | 43638400551 | success |
| | | `mutation-pr` | 43638400497 | success |
| | | `verify` | 43638400517 | failure (`coverage`, ugyanaz az ok, mint a #174-en) |

### 9.1 A #174 `coverage` és `go (chunk 4)` bukása: **regresszió, a saját változtatásom okozta**

*Nem környezeti hiba és nem korábbi probléma.* Bizonyíték:
- A `coverage` naplója (run 43638326995): `centralrelay/tests/test_tools/fixtures/object_model: 0% (min 80%)` → `FAIL: coverage below threshold`.
- A `go (chunk 4)` naplója (run 43638326975): `FAIL ./tests/test_tools/fixtures/object_model: killed 0 … not covered 37; efficacy 0.00 (need 90.0)`. A `completeness` ezért bukott (a chunk riportja `fail`), és a `mutation-pr` gate ezért piros.
- **Ok:** a fixture `tests/test_tools/fixtures/object_model/goastdump-main.go` egy `package main` Go-fájl; a root modul saját csomagjának (`centralrelay/tests/test_tools/fixtures/object_model`) látja. A `base`-en (`origin/main`) ilyen fájl **nincs** (0), és a PR-03 teljes futása (#171, `275ebea`) zöld volt, tehát a hiba ezzel a PR-ral jött.
- **A scope-hibám ugyanebből:** a `*.go` szabály a fixture-t `production`-nak osztályozta; a zöld `object-evidence` futás (run 43638327223) **690** objektumot adott, a root egységben **479** (a helyi 464 + a fixture 15 függvénye). Ez a CI maga mutatta ki a hibás osztályozást.
- A #175-ön a `coverage` ugyanezért bukott (az ág a `c59f0a8`-ra épült), a `mutation-pr` ott azért zöld, mert a #175 diffje csak az `object-evidence.yml`, ami nem gate-logika.

**Javítás (`34043f7`):** (1) a Go- és a Rust-fixture forrás `.txt` kiterjesztésű (`goastdump-main.go.txt`, `cic-canonical-lib.rs.txt`): semmilyen eszköz nem lát bennük forrást; (2) `.measurement-scope.json`: a `tests/*` Go és Rust esetén `test-data` osztály, indoklással; (3) két őrző teszt: nincs `.go`/`.rs` fájl a `tests/` alatt a `testdata` kívül; a `tests/` alatti forrás a scope-ban nem `production`. **Helyi igazolás (mérve):** `go list ./...` a javított fán **31** csomag (mint a PR-04 előtt), fixture-csomag **0**; 53 teszt zöld.
**Amit ez a javítás nem érint:** blokkoló kapu, küszöb, baseline, termékkód — egyik sem változott.
**A javított fej CI-eredménye: mérve, lásd 9.4** (Relay #174, headSha `34043f790c2c313c4fcf74869cf6dced5f0435b3`: mind a négy workflow success).

### 9.2 A #175 piros útja: **bizonyítva**

A `object-evidence` workflow run **43638400559**, headSha **`497b5080f4d21478211b963eec85adffeba079f9`**: `L1 INTEGRITY_OK`, `L2 BOUND_TO_INPUTS`, **`L3 FAIL: go unit 'root': 476 objects but 479 top-level func lines in the source`**, `Process completed with exit code 1`. Vagyis egy belsőleg konzisztens, a bemeneteihez kötött, de **hiányos** rekordot csak az L3 (független számlálás) fogott meg, az L1 és az L2 nem — a spec szerinti szétválasztás a valódi GitHub-futásban is.
Megjegyzés a 479-re: a hiányzó fájl 3 függvényt vitt el, és a gyökér-egységben a fixture-fájl miatt 15 többlet-objektum volt (lásd 9.1). A **javított** fejre épített, tiszta bizonyító ág (`514d9e4`, Relay #178) ezt a zavaró tényezőt nem tartalmazza: **futása a 9.4-ben**. A #175-öt ezért lezártam, nem mergeltem.

### 9.3 A zöld `object-evidence` futás (#174, run 43638327223, `c59f0a8`)

A workflow az első valódi GitHub-futásán lefutott, `L1 INTEGRITY_OK`, `L2 BOUND_TO_INPUTS`; 690 objektum (root 479, `goastdump` 15, Rust 196); `go=go1.26.11`, `rustc=1.96.1`, `cargo-llvm-cov=0.9.1`, `cargo-mutants=27.1.0`. A Rust-objektumok száma (196) a helyi pinelt-image futással **egyezik**.

### 9.4 A javított fejek futásai (a végleges bizonyíték)

| PR | headSha | Workflow | Run id | Eredmény |
|---|---|---|---|---|
| Relay #174 (a PR-04 változtatása, javítva) | `34043f790c2c313c4fcf74869cf6dced5f0435b3` | `verify` | 43639935484 | **success** (benne a `coverage`) |
| | | `mutation-pr` | 43639935525 | **success** (6 Go-chunk success, `completeness` success) |
| | | `object-evidence` | 43639935498 | **success** |
| | | `manifest-check` | 43639935523 | success |
| Relay #178 (draft, DO NOT MERGE, tiszta piros út) | `514d9e489d7e1ec87fa097ce3cb4703c5ef66734` | `object-evidence` | 43639959355 | **failure, az elvárt L3 FAIL** |
| | | `verify` / `mutation-pr` / `manifest-check` | 43639959514 / 43639959358 / 43639959363 | success |

- **#174: a regresszió megszűnt.** A PR mind a 25 checkje zöld, nincs egyetlen bukás; a `coverage`, a 6 `go (chunk)`, a `completeness` és a `mutation-pr` is `success`.
- **A CI rekordja egyezik a helyi, pinelt-image rekorddal** (run 43639935498): **675 objektum**, root **464**, `goastdump` **15**, Rust **196** — pontosan a helyi számok. Az ubuntu-latest `c++filt`-je tehát ugyanazokat az objektumneveket adta, mint a pinelt image-é. `L1 INTEGRITY_OK`, `L2 BOUND_TO_INPUTS`, `L3 PARTIAL` (bizonyított: Go root 464 és `goastdump` 15 = független `func`-szám; minden `cargo-mutants`-függvénynek van objektuma). A CI-rekordban a root egység lefedettsége `MEASURED 456 / UNVERIFIABLE 8`, a helyi `453 / 11`-gyel szemben: a különbség a **3 nemdeterminisztikus objektum**, amelyeket csak az ismételt profilok mutatnak ki (a CI egy profilt készít).
- **#178: a piros út, tisztán.** Run 43639959355, headSha `514d9e489d7e1ec87fa097ce3cb4703c5ef66734`: `L1 INTEGRITY_OK`, `L2 BOUND_TO_INPUTS`, **`L3 FAIL: go unit 'root': 461 objects but 464 top-level func lines in the source`**; a bukó lépés: *Verify the record (L1 integrity, L2 binding to the inputs, L3 completeness)*, `exit code 1`. A #178 többi workflow-ja zöld, tehát **az egyetlen bukás a szándékos**. A hiányzó 3 függvény (464 − 461) a kihagyott utolsó produkciós fájlé, és a hiba a fixture-zavaró tényező nélkül jelentkezik.

## 10. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `--branch` stabil 1.96.1-en nem elérhető | implemented (mérve) | `raw/llvm-cov-branch-on-stable.txt` | `bash raw/discover_rust.sh` | alacsony |
| A valódi rekord 675 objektumot ad; 11 `UNVERIFIABLE`, mindegyik kódolt okkal | implemented (valódi adaton) | `raw/evidence-summary.json` | `bash raw/build_all.sh` | a helyi pinelt-image futás; a CI ugyanezeket a számokat adta (9.4) |
| Blokk-hozzárendelés arányosítás nélkül; 9 hozzá nem rendelhető blokk számolva | implemented | attribution a rekordban; `test_n11_*` | pytest | alacsony |
| A 3 nemdeterminisztikus objektum nem kap értéket | implemented (mérve, 6 futás) | rekord; `test_n9_*` | `bash raw/measure_go2.sh` | közepes: 6 futás nem bizonyítja a determinizmust a többi objektumra |
| Az L3 független számlálása hibát talált az első rekordban | implemented (mérve) | 5. szakasz | `object_model.py verify` | — |
| A konzisztensen meghamisított rekordot az L1 nem, az L3 megfogja | implemented (valódi adaton) | `raw/verify-real.txt` 3. eset | `bash raw/verify_real.sh` | alacsony |
| Az N-tesztek bukni tudnak | implemented (mérve, 12/12) | `raw/teeth.txt` | `python raw/teeth.py …` | alacsony |
| A `mutation-policy/2` elsődleges score-ja nem függ az `unviable`-től | implemented | `test_r1_*`; a régi fán buktat (7 CLI-teszt) | pytest a két fán | alacsony |
| Per-teszt Go hozzárendelés pontos és megvalósítható | implemented (mintán mérve) | `raw/part2-go.txt` | `bash raw/part2_go.sh` | **a teljes modul költsége nem mért** |
| A `goastdump` hiányosságai osztályozva | implemented (olvasat + rekord) | 7. szakasz | a rekord `uncovered` spanjei + forrás | a következmény nem mért |
| A diffben a blokkoló kapuk, a küszöbök és a baseline változatlanok | implemented | `git diff 852594a c59f0a8 -- .mutation-baseline.json scripts/gremlins_gate.py` üres | git | alacsony |
| A zöld `object-evidence` futás a `c59f0a8`-n | implemented (mérve) | 9.3: run 43638327223, headSha `c59f0a8…`, success; Rust-objektumok 196 = a helyi futás | `gh run view 43638327223 --log` | a `c59f0a8` a fixture-hibát tartalmazza (479 root objektum) |
| A #174 `coverage` és `go (chunk 4)` bukása a saját regressziónk | implemented (mérve) | 9.1: run 43638326995 és 43638326975 naplói; a base-en nincs ilyen fájl; helyi `go list` a javítás előtt/után | `gh run view … --log-failed` | alacsony |
| A javítás (`34043f7`) megszünteti a regressziót | implemented (CI-ban mérve) | 9.4: Relay #174, headSha `34043f79…`, `verify` 43639935484, `mutation-pr` 43639935525, `object-evidence` 43639935498, `manifest-check` 43639935523 mind success; 25/25 check zöld; helyben `go list` = 31 csomag | `gh run list -R CentralInfraCore/CIC_Relay --commit 34043f7…` | alacsony |
| A CI-ban futó rekord egyezik a helyi, pinelt-image rekorddal | implemented (mérve) | 9.4: 675 / 464 / 15 / 196 mindkét helyen; az ubuntu-latest `c++filt` ugyanazt a Rust-leltárat adta | összevetés | alacsony; a 3 nemdeterminisztikus objektum csak ismételt profilnál látszik |
| A CI-ban piros az L3 a hibás ágon (első bizonyító ág) | implemented (mérve) | 9.2: run 43638400559, headSha `497b5080…`, `L3 FAIL … 476 objects but 479 top-level func lines`, L1/L2 zöld | `gh run view 43638400559 --log-failed` | a fejen a fixture-hiba is benne volt |
| A CI-ban piros az L3 az új, tiszta bizonyító ágon | implemented (mérve) | 9.4: Relay #178, run 43639959355, headSha `514d9e48…`, `L3 FAIL … 461 objects but 464 top-level func lines`, L1/L2 zöld, a többi workflow zöld | `gh run view 43639959355 --log-failed` | alacsony |
| Go ág-lefedettség eszköz értékelése (II.A): `gobco v1.3.4` pinelhető, reprodukálható, feltétel-szintű | implemented (3 csomagon mérve) | `raw/part2a-go-branch*.txt`, 6. szakasz | `bash raw/part2a_gobranch3.sh` | a licenc nem ellenőrzött; a külön modulban `./...` 0-s kilépéssel „nothing to instrument”; **a teljes modul költsége nem mért** |
| Rust ág-lefedettség pinelt nightly-n (II.B) | implemented (mérve) | `raw/part2b-nightly-branch.txt`: `nightly-2026-07-01`, 146 ág / 124 lefedett, 87 s | `bash raw/part2b_nightly.sh` | másik fordító (1.98); az ág-rekord objektumhoz rendelése nem épült be |
| Függvény-szintű tranzitív hatás (II.D) | **nem mérve** | — | hívási-gráf eszköz | — |
| A Rust per-teszt hozzárendelés (II.C) | implemented (egy crate lib-tesztjein mérve) | `raw/part2c-rust-pertest.txt`: 3 teszt, union 99 = 99, ~646 ms/teszt | `bash raw/part2c_rust_pertest.sh` | **a workspace többi crate-je és az integrációs tesztek nem mérve** |
| A Go per-mutáns hozzárendelés (II.E) | **nem implementált** | — | — | alacsony |

## 11. Nyitott, tulajdonosi döntésre

1. **Az `unviable` figyelmeztető szintje** (4.) és a `mutation-policy/3` szigorítása.
2. **Go ág-lefedettség eszköze** (II.A: a `gobco v1.3.4` mért adatai a 6. szakaszban, a licenc tisztázandó) és **a Rust pinelt nightly-lépés** (II.B: mérve működik, másik fordító): mindkettő új, pinelendő eszköz, a döntés a tulajdonosé.
3. **A hozzá nem rendelhető 9 blokk és 9 többértelmű mutáns** kezelése (jelenleg számolt, nem kapott értéket).
4. **A per-teszt hozzárendelés** bevezetése (II.C) és költsége.
5. A PR-03-ból maradt: a diff-módú (`--in-diff … --shard`) valódi CI-futás és a heti `mutation.yml` bekötése (PR-07).

## 12. Nem mérve / korlátok

- GitHub Actions: lásd 9. A javított fej (`34043f7`) és a tiszta piros-út ág (`514d9e4`) futása **mért** (9.4). **Továbbra sem mért:** a diff-módú (`--in-diff … --shard`) valódi CI-futás (PR-03-ból maradt), az `object-evidence` mutációs mezője CI-ban (a verdiktekhez teljes futás kell), a Go ág-lefedettség eszköz és a Rust nightly-lépés CI-beli futása (mindkettő csak helyben mért).
- Az `object-evidence` CI-ban nem futtat mutációt (a teljes futás kell hozzá): a Rust-mutáció-mező ott `UNVERIFIABLE`.
- A Rust függvény-leltár **teljessége** független forrásból nem bizonyított (az L3 `PARTIAL`).
- A demangling a pinelt image `c++filt`-jére épül; az ubuntu-latest `c++filt`-jének kimenete **nem mért** (a verzió a rekordban van; eltérő formátum a `no demangled name` vagy más objektumnevek hibájához vezethet, ami a rekord hiánya, nem hallgatólagos siker).
- A `/tmp` tmpfs helyett `~/.cache/relay-ci-parity-04/`-t használtam (build-cache, másolatok; a nightly target 1,9 GB); a **tulajdonos döntse el, törölhető-e**.
- A teljes repó `pytest`-je helyben nem fordítható (`requests` hiányzik a scratch venv-ben); a CI `python` jobja dönt.

## 13. Aláírás és push

A commitok a Vault `commit-msg` hook futásával készültek (aláírási metaadat a commit-üzenetben); az érvényességet **nem ellenőriztem**. Co-Authored-By vagy AI-re utaló sor nincs. A push-okat a tulajdonos futtatja (a környezet elutasítja). A szándékosan hibás ágból **nem** nyitok mergelhetőnek tűnő PR-t: draft, „DO NOT MERGE” címmel, a munkaágra (nem a `main`-re) mutatva, a futás rögzítése után lezárva.
