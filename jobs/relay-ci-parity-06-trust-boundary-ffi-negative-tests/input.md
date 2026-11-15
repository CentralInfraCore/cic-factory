# relay-ci-parity-06-trust-boundary-ffi-negative-tests — hiányzó önellenőrző próbák és a bizalmi határok negatív tesztjei

## Kontextus

A `CentralInfraCore/CIC_Relay` **#169** issue (másolat: `ref/issue-169-body.md`) tízlépéses PR-sorozat.
**Ez a job a PR-06-ot fedi:** „Trust-boundary and FFI negative tests”, záró feltétel: *kritikus szerződések tesztelve, eltérések rögzítve*.
A tulajdonos döntése szerint a PR-06 **kötelező bemenete** a #169 „Self-testing” még nem igazolt **1., 2. és 8. próbája** (`ref/owner-decisions-pr06-2026-11-15.md`).

Előzmények (a PR-01–PR-05 mergelve; a Relay `main` a PR-05 merge-commitot `7386565669c84b3c2477425e6b0d3332e752432a` tartalmazza):

- PR-02/03: fail-closed felsorolás, teljességi verifier; PR-04: objektumszintű mérési modell; PR-05: 14 seeded defect eset, az L2 újralevezetés — `ref/pr04-report.md`, `ref/pr05-report.md`.
- A PR-05 **9. szakaszának leképezése** mondja ki, mi nem fedett: **1.** (gyengített teszt-készlet → lefedettségi kapu piros), **2.** (túlélő mutáns → mutációs kapu piros), **8.** (módosított/ismeretlen eszközverzió használhatatlan). A 3–7. próba a PR-02/03/04/05 tesztjeivel fedett (a lefedés szintjét a PR-05 jelentés 9. szakasza rögzíti).

**Ez a spec külön felülvizsgálatra készül; a job indítása a spec review-ja és mergelése után történik.** A PR-06 implementációt ad
(CIC_Relay scriptek, tesztek, report-only workflow és tesztek; PR a CIC_Relay felé), de **csak az alábbi hatókörben**.
**Új küszöb, új blokkoló kapu, toolchain-csere és tesztkihagyás nincs.** Termékkódot a job nem módosít: ha egy negatív teszt hiányzó termék-garanciát tár fel, **rögzítsd, és külön, célzott PR-ban javítandó** — ne rejtsd tesztkizárással (#169, „Relay-specific trust boundaries”, utolsó pont).

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits` fogalmakra. A státuszt (implemented / scaffold / concept) node- vagy fájlszinten támaszd alá. Különösen: `pki_verify.go` és `UpstreamSource` **scaffold** — a hiányzó bekötés nem hiba, és a negatív teszt nem állíthatja, hogy a láncellenőrzés élő.
2. Olvasd el: `ref/owner-decisions-pr06-2026-11-15.md`, `ref/issue-169-body.md` („Self-testing”, „Relay-specific trust boundaries”, „Development rules”, „Acceptance criteria”), `ref/pr05-report.md` (9., 10., 11.), `ref/pr04-report.md`.
3. Olvasd el a **Forms referenciát** (csak olvasásra, **nem másolandó**): `tools/quality_gate.py` (`selftest`), `tools/seeded_defects.py`, `docs/FAST-FULL.md`. A tanulság a szigor, nem a kód.
4. Friss klón: `$WORKSPACE/CIC_Relay/` (alapértelmezett ág `main`) és `$WORKSPACE/cic-primitive-forms/`. **Rögzítsd a commit-azonosítókat és az ágat.** A Relay `main` tartalmazza a `7386565`-öt; ha nem, állj meg és jelezd. **Ha a `workspace/` alatt már van `CIC_Relay*` mappa, ne azt használd** (a PR-05 mérésekor az egyik klón 189 módosított és 23 nem követett `.yaml` fájllal piszkos volt, az ok **nem megállapított**): új, tiszta klónt készíts, és a `git status --short | wc -l` kimenetét rögzítsd a klónozás után **és** a mérések előtt, **és a végén is**.
5. **Reachability (Go és Rust):** egy szimbólumról csak akkor mondd, hogy production-hívott, ha megvan a hívási út `file:line`-nal (Go: `grep -rn <szimbólum> --include=*.go . | grep -v _test.go` vagy `deadcode ./...`; Rust: a hívó `file:line`). A `symbol létezik` ≠ `production hívja`.
6. **Mérési környezet:** `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`, `golang:1.26.x` (a `verify.yml` Go-verziója), `cargo-mutants 27.1.0`, `cargo-llvm-cov 0.9.1`. **Konténert `--user "$(id -u):$(id -g)"`-rel futtass**, cache a `~/.cache/relay-ci-parity-06/` alatt (nem a 16 GB-os `/tmp`-n), hogy a takarítás `sudo` nélkül menjen.

## Feladat — A. rész: a #169 1., 2. és 8. próbája (kötelező, tulajdonosi döntés)

Mindegyik **valódi eszközzel** és a termékfa **izolált, szándékosan gyengített másolatán** fut; a termékfát és a repó bizonyítékait nem módosíthatja. **Minden negatív eset mellett pozitív kontroll** (a hibátlan másolat zöld), és a harness **ellenpróbája** (a kiiktatott ellenőrzésre a megfelelő eset bukik) a PR-05 mintájára.

- **A.1 (1. próba) — gyengített teszt-készlet.** A másolatból törölj/kikapcsolj tesztet úgy, hogy a lefedettség csökkenjen; a valódi lefedettségi kapu (`scripts/…` a PR-04/05 modellel és a meglévő küszöbbel) **pirosra vált**. Nem kerül sor küszöb módosítására; a „piros” a meglévő küszöb alatti érték. **Mérd meg a költséget** (futásidő, lemez).
- **A.2 (2. próba) — túlélő mutáns.** A másolatban ültess egy olyan hibát, amelyet a tesztek nem fognak meg, és a valódi mutációs eszköz (`cargo-mutants` / `gremlins`) **túlélő mutánst** jelent; a mutációs kapu **pirosra vált** (a `missed` a meglévő szabály szerint bukik). **Mérd meg a költséget.**
- **A.8 (8. próba) — módosított vagy ismeretlen eszközverzió.** A tervben/rekordban rögzített eszközverziótól eltérő vagy ismeretlen verzióval készült eredmény **automatikusan használhatatlan** (nem elfogadott, nem nulla, nem siker): legalább a `cargo-mutants`, a `cargo-llvm-cov`, a Go és a `gremlins`; a meglévő `tool_version` egyezés-ellenőrzés (`scripts/quality_gate.py`) és az `object-evidence` `TOOL_UNKNOWN` a kiindulópont. **Tulajdonosi döntés: minden minőségi döntést befolyásoló eszközre fail-closed** (az eltérő vagy ismeretlen verzió eredménye nem elfogadott, nem nulla, nem siker). **Mérd meg, hogy mely eszközre van tényleges ellenőrzés és melyikre nincs**; amelyikre nincs, a hiányt **a meglévő kapun/verifieren belüli ellenőrzéssel** pótold (ez nem küszöbmódosítás és nem új, önálló blokkoló kapu/required check), és mindegyikre legyen pozitív kontroll és ellenpróba.
- **Költség és munkamegosztás.** Ha a futásidő indokolja, a workflow **kézi indítású** (`workflow_dispatch`), report-only, **nem required check**, de **lefut legalább egyszer** a PR fejére, és a run id rögzített. A futásidő nem érv a szigor ellen, de a megvalósíthatóság adata.
- A 3–7. próbánál ahol a lefedés csak egységteszt (nem valódi artifacton futó seeded defect), azt a jelentés **kimondja**; új eset csak akkor kerül be, ha a mérés hiányt mutat.

## Feladat — B. rész: a bizalmi határok negatív tesztjei (#169 „Relay-specific trust boundaries”)

A #169 négy területe: **(1)** modul-azonosság és jogosultság, **(2)** végrehajtás és erőforráskorlátok, **(3)** workflow- és proof-lánc, **(4)** FFI, Vault, release. A fájlok a #169-ben vannak (`cmd/relay/bootstrap.go`, `cic_flow_registry.go`, `cic_flow_manifest.go`, `core/cabinet/pki_verify.go`; `cic_flow_host_funcs.go`, `core/modules/httpcap/`, `http-executor/`, `core/cabinet/cicwasm.go`; `core/cabinet/service.go`, `cmd/relay/proof_verify.go`, `core/nexus/recorder/`; `ffi/src/lib.rs`) — **ellenőrizd, hogy léteznek-e és mit tesznek**, ne higgy a spec szövegének.

1. **Először mérj, ne írj:** területenként (1–4) **térképezd fel**, mely negatív tesztek léteznek ma (fájl:függvény), és mely #169-es eset (rossz tanúsítványlánc, módosított WASM, manipulált capability-manifest, hiányzó/érvénytelen aláírás, jogosulatlan capability; átirányítás, belső címek, DNS-változás, időtúllépés, válaszméret, WASM-memória, erőforrás-felszabadítás; részleges végrehajtás, megszakítás, párhuzamos rögzítés, sérült lánchash, hiányzó aláírás, állapotfolytonosság; FFI: tulajdonjog, null, hibás hossz, dupla felszabadítás, panic-határ) **nem fedett**. Ez a **hiánytérkép** a jelentés része.
2. **Hatókör (tulajdonosi döntés):** a **hiánytérkép mind a négy területre** elkészül; a negatív tesztek **implementációja az (1) modul-azonosság és jogosultság és a (4) FFI** területre szól. A (2) és (3) területre implementáció **nincs**, csak a hiánytérkép. Ne bővítsd a hatókört magadtól.
3. **Biztonsági leletek:** egy új sérülékenység **reprodukciós részletei** (kihasználási lépések, működő bemenetek) **nem kerülhetnek nyilvános jelentésbe, PR-leírásba vagy CI-naplóba**; a jelentés a lelet fajtáját, az érintett fájlt és a javítás szükségességét rögzíti, a részleteket a tulajdonosnak privát csatornán add át.
4. Minden új negatív teszthez: a **hibátlan eset pozitív kontrollja**; a teszt **buktatható** (a vizsgált ellenőrzés kiiktatásával a teszt bukik — „a teszt zöldje ≠ hogy a teszt bukni tud”); a **hiányzó termék-garancia** rögzítése (nem teszt-kizárás) és külön PR javaslata.
5. A **szétválasztott állapotok** nem olvadhatnak egy `success`/`verified` értékbe: a végrehajtás sikeres; a bizonyíték létezik; strukturálisan konzisztens; kriptográfiailag hitelesített; a megadott bizalmi szabály szerint elfogadható. Ahol a Relay ma egyet ad, azt a hiánytérkép rögzítse.
6. **Vault/FFI környezet:** izolált, reprodukálható, **valódi kulcs és termelési jogosultság nélkül**. A **Vault-aláírás/ellenjegyzés a tulajdonos dolga** — a job nem ér valódi Vault-hoz.

## Nem része a jobnak (ne csináld)

- Új küszöb, új blokkoló kapu, tesztkihagyás, toolchain-csere, `continue-on-error`/`|| true` egy kötelező kapuban.
- Termékkód módosítása (hiányzó garancia → külön PR); a `scripts/gremlins_gate.py`, `.mutation-baseline.json`, coverage-baseline módosítása.
- A PR-08 feladata: a futások **eredetének** igazolása (húsz profil ≠ húsz független végrehajtás); a PR-09/10 tárgya: evidence-publikálás, proof-aware planner.
- A `syn`-alapú Rust-leltár értékelése: **külön job** (tulajdonosi döntés). Az öt crate nélküli `#[no_mangle]` azonosító: **külön, verziózott szerződési PR** (tulajdonosi döntés). Egyikhez sem nyúlsz; ha a munka során érintkezel velük, rögzítsd.
- A Forms-kód másolása; külső repo-beállítás (branch protection) módosítása.

## Negatív tesztek és pozitív kontrollok

Minden eset: **származtatás** (valódi eszközkimenetből vagy a termékfa izolált másolatából), **elvárt szint/üzenet**, **kapott**, **pozitív kontroll**, **ellenpróba**. A regressziós tesztet a javítás nélküli állapoton is futtasd (R-teszt), az új szerződés tesztjét ellenpróbával mutasd buktathatónak (N-teszt); a „nem létezik” miatti bukás nem bizonyíték.

## Mérési korlátok (a jelentésben kimondandó)

- **Statement ≠ branch**; a nightly csak mérés. **Egyszeri mérés ≠ determinizmus.** Az `OBSERVED_STABLE` csak annyit állít, hogy a megadott profilok azonosak, **nem** azt, hogy húsz független futás volt (PR-08).
- **Lemezhely és tulajdon:** rögzítsd a felhasznált helyet; konténer `--user`-rel; a cache a felhasználó könyvtárában.
- **Idő és költség** (A.1, A.2): mérendő és jelentendő.
- **Reprodukálhatóság:** pinelt kép-digest, eszközverziók, kimenetek digestje; a klón tisztasága a mérések előtt, alatt és után.

## Elfogadási kritériumok

1. A **hiánytérkép** (B.1) kész: területenként mi fedett (fájl:függvény) és mi nem.
2. Az **A.1, A.2, A.8** valódi eszközzel, izolált gyengített másolaton fut, a várt szinten bukik, **mindegyik mellett pozitív kontroll és ellenpróba**; a költség mért.
3. A B. rész elfogadott hatókörében minden új negatív teszt **buktatható** (ellenpróba), pozitív kontrollal; a feltárt hiányzó garanciák **rögzítettek**, nem kizárva.
4. A meglévő blokkoló kapuk, küszöbök, baseline-ok **változatlanok** (a diffben ellenőrizve); nincs új blokkoló kapu, nincs tesztkihagyás; a harness **nem required check**.
5. **Valódi GitHub Actions futás** a PR headSha-jára (zöld, run id) és legalább egy **szándékosan hibás, nem mergelendő** futás, amelyen a megfelelő harness/teszt piros. Az **A.1, A.2 és A.8 kötelező valós futásánál** a `nem mérve` státusz **dokumentálható, de nem jelenti a feladat sikeres lezárását**: a job ilyenkor nyitott marad, és a hiányt a jelentés a lezárás akadályaként nevezi meg.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented; a workflow létezése ≠ hogy fut; a kapu ≠ hogy bukni tud; **egy seeded defect ≠ hogy a kapu bukni tud, amíg a pozitív kontroll nincs mellette**.
- **Illeszkedő hash ≠ eredet vagy jogosultság.** A magas lefedettség vagy egy zöld egységteszt ≠ bizonyított biztonsági tulajdonság.
- Exit code 0 ≠ sikeres mérés; üres kimenet ≠ nulla mérés ≠ sikertelen mérés.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként. Egy sikeres helyi futás ≠ hogy a CI hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.

## Verifikáció és bizonyítás

- Minden állításhoz a parancs és a nyers kimenet, pinelt környezetben.
- **Nem elég a helyi futás:** a #169 10. szabálya szerint egy CI-fázis csak akkor kész, ha GitHub Actions futás igazolja; a **run id-t és a headSha-t** vesd egybe a tesztelt committal. A szándékosan hibás futáshoz külön, **nem mergelendő** ágat/draft PR-t használj, egyértelmű jelöléssel, a munkaágra mutatva; a futás rögzítése után zárd le.
- **A CI-hibákat vizsgáld ki, ne tulajdonítsd környezetnek.** Egy bukó check okát a naplóból állapítsd meg.
- A workflow-szöveg olvasata ≠ futás: ahol csak olvastad, mondd ki. A teljes repó `pytest`-jét a CI `python` jobja futtatja; helyben hiányozhatnak csomagok (`requests`, `pytest-mock`): mondd ki.
- **Aláírás:** a cic-factory `main`-re közben mozdulhat; a PR-ág legyen naprakész a `main`-nel a push előtt. **A rebase érvényteleníti az aláírást, és egy `--amend` a régi aláírási blokkot megtartja**: a kimenetet **frissen, új üzenettel aláírt commitként** a `main` tetejére kell tenni.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-06-trust-boundary-ffi-negative-tests/output/`

- `output/pr06-report.md` — magyarul: vizsgált commitok; a klón tisztasága (előtte/alatta/utána); a hiánytérkép (B.1); az A.1, A.2, A.8 eredménye mért adatokkal és költséggel; esetenkénti táblázat (származtatás, elvárt, kapott, pozitív kontroll, ellenpróba); R- és N-teszt bizonyíték; feltárt hiányzó termék-garanciák; a #169 1–8. próba frissített leképezése; GitHub Actions run id-k (zöld **és** szándékosan piros); claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`); nyitott döntések; amit nem mértél.
- `output/raw/` — nyers kimenetek és scriptek (minden `.sh` első sora `#!/usr/bin/env bash`, ShellCheck `--severity=error`; a nyers fájlokból a helyi útvonalak és felhasználónevek kerüljenek ki).

A CIC_Relay módosítás a Relay-klónban, külön ágon, PR-ként.

## Definition of Done

- Mindkét repó commit-azonosítója és az ág leírva; a klón tisztasága rögzítve (előtte/alatta/utána).
- Hiánytérkép kész; A.1, A.2, A.8 valós eszközzel, pozitív kontrollal és ellenpróbával; a költség mért.
- A B. rész elfogadott hatókörében a negatív tesztek buktathatók, a hiányzó garanciák rögzítettek, nem kizártak.
- A meglévő blokkoló kapuk, küszöbök, baseline-ok változatlanok; nincs új blokkoló kapu, tesztkihagyás, toolchain-csere; termékkód nincs a diffben.
- Valódi GitHub Actions run id a PR headSha-jára (zöld) és a szándékosan hibás futásra (piros). Az A.1, A.2, A.8 kötelező valós futásánál a **`nem mérve` nem lezárás**: a job nyitott marad.
- A CIC_Relay PR leírása pontosan azt állítja, ami mérve van.

## Végleges tulajdonosi döntések (review, 2026-11-15; `ref/owner-decisions-pr06-2026-11-15.md`)

| Tétel | Döntés |
|---|---|
| B rész | implementáció: modul-azonosság és FFI; **hiánytérkép mind a négy területre** |
| `syn`-alapú Rust-leltár | **külön job**, nem része a PR-06-nak |
| Öt crate nélküli `#[no_mangle]` azonosító | **külön, verziózott szerződési PR**, nem része a PR-06-nak |
| A.8 | **minden minőségi döntést befolyásoló eszközre fail-closed** |
| Biztonsági leletek | reprodukciós részletek nem kerülhetnek nyilvános jelentésbe/CI-naplóba |
| DoD | az A.1, A.2, A.8 kötelező valós futásánál a `nem mérve` nem lezárás |

Nyitott marad (a job nem dönti el, a jelentés rögzíti): az ismeretlen verzió állapotának **neve** az `object-evidence` modellben (`unusable` vagy `unverifiable`) — a viselkedés fail-closed, a név az implementáció és a review dolga.

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-06-trust-boundary-ffi-negative-tests` ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát nem módosítod (a tulajdonos zárja). Az ág a `main` tetején álljon (lásd „Aláírás”).
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-06-trust-boundary-ffi-negative-tests`) friss klónból, PR a `main`-re (`--base main` explicit). Nem mergelsz. A PR **egy** témájú: önellenőrző próbák és negatív tesztek; termékkód nincs. A szándékosan hibás ágat **ne** mergeld; draft, „DO NOT MERGE” cím, a munkaágra mutatva; a futás rögzítése után zárd le.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR leírásában. A Relay-repó csak merge-commitot enged.
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: jelezd az outputban, az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet elutasítja; add oda a pontos parancsot (lehetőleg **egy scriptben**), ne kerüld meg.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**.
