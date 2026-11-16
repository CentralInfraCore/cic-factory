# relay-ci-parity-06c-workflow-integrity — a kötelező ellenőrzések végrehajtásának kikényszerítése a vizsgált PR bizalmi határán kívül (CIC_Relay #212)

## Kontextus

A `CentralInfraCore/CIC_Relay` **#212** issue (másolat: `ref/issue-212-body.md`) a #195 / PR #201 (mergelve: `68117e6ac0c0c3b0acda4dd8a593c2c29252c75d`) utáni, **kötelező következő feladat**. A #201 a mérési **referenciát** védi (pinek, `surfaces`, `approvers` a base ágból; a `check-tools` scriptje a base-ről fut; a megváltozott pin-fájl csak HEAD- és digest-kötött jóváhagyással elfogadott). A **#207 proof PR** viszont reprodukálta, hogy ez **nem teszi kötelezővé az ellenőrzést**: a pull request törölte a referencia-lépést és a `check-tools` lépést a `coverage` jobból, **minden check zöld maradt**, a job `go1.26.10`-zel futott, miközben a pin go1.26.11 (`ref/pin-protection-report.md`, 4. és 7. szakasz).

**A feladat lényege (tulajdonosi kiemelés, `ref/owner-decisions-212-2026-11-17.md`): nem elég az ellenőrzési *szabályokat* védeni, az ellenőrzés *végrehajtásának kötelezettségét* is ki kell kényszeríteni**, olyan mechanizmussal, amelyet a vizsgált pull request nem módosíthat.

A trust-határ oka (mért, `ref/measured-repo-state-2026-11-17.md`): `pull_request` eseménynél a workflow-fájlok, a composite action és minden script **a PR-ből jön**; a kötelező státusz-checkek **név szerint** vannak a rulesetben, és a nevet bármely PR-beli job előállíthatja tartalom nélkül is. A jelenlegi ruleset: `required_status_checks` (`verify`, `coverage`, `python`, `rust`, `ffi`, `manifest`, `mutation-pr`), **nincs `workflows` szabály, nincs kötelező review**; az organizáció **free** csomagon van (org-szintű ruleset nem elérhető).

**Ez a spec külön felülvizsgálatra készül; a job indítása a spec review-ja és mergelése után történik.** A job implementációt ad (CIC_Relay workflow/script/teszt; PR a CIC_Relay felé) **csak az alábbi hatókörben**. **Új küszöb, toolchain-csere, tesztkihagyás és termékkód-módosítás nincs, és a repository-beállításokat (ruleset, branch protection, Actions-beállítások) a job nem módosítja**: azokra javaslatot ad, a tulajdonos hajtja végre.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits` fogalmakra. Ha a KB nem elérhető, mondd ki; a repó fájljai a forrás.
2. Olvasd el: `ref/issue-212-body.md`, `ref/owner-decisions-212-2026-11-17.md`, `ref/measured-repo-state-2026-11-17.md`, `ref/pin-protection-report.md` (3., 3b., 4., 7. szakasz), `ref/issue-169-body.md` („Development rules”, „Acceptance criteria”).
3. Friss klón: `$WORKSPACE/CIC_Relay/` (ág `main`). **Rögzítsd a commit-azonosítót**; a `main` tartalmazza a `68117e6`-ot, különben állj meg. **Ha a `workspace/` alatt már van `CIC_Relay*` mappa, ne azt használd** (egy ismeretlen háttérfolyamat `.yaml` kísérőfájlokat módosít a `.py`/`.go` fájlok mellett): új klón, **explicit útvonalas `git add`, soha nem `-A` vagy `-u`**, a `git status --short | wc -l` rögzítve a klónozás után, a mérések előtt és a végén.
4. **Kiindulási állapot (olvasd, ne higgy a specnek):** minden workflow (`.github/workflows/*.yml`), a composite action (`.github/actions/measurement-reference/action.yml`), `scripts/quality_gate.py` (`pin_reference`, `check-tools`), `scripts/baseline_guard.py`, `scripts/object_model.py`, `.measurement-tools.json`, és a ruleset (`gh api repos/CentralInfraCore/CIC_Relay/rulesets`). **A kötelező ellenőrzések leltára:** minden olyan job/lépés, amelynek a lefutása merge-feltétel (a rulesetben kötelező checkek, és azok a lépések, amelyek a minőségi ítéletet hozzák: referencia-lépés, `check-tools`, `baseline-guard`, mérések). Rögzítsd táblázatban: név, hol van definiálva (file:sor), ki tudja módosítani, a ruleset kötelezi-e.
5. **Reachability:** egy mechanizmusról csak akkor mondd, hogy bekötött, ha megvan a hívási út `file:line`-nal: `grep -rn <szimbólum> --include=*.py --include=*.yml --include=*.go . | grep -v "_test.go" | grep -v "/test_"`. A `fájl létezik` ≠ `a merge-feltétel része`.
6. **Mérési környezet:** helyi futásnál konténer `--user "$(id -u):$(id -g)"`-rel, cache a `~/.cache/relay-ci-parity-06c/` alatt (nem a 16 GB-os `/tmp`-n). A CI-viselkedést **valós GitHub Actions futás** igazolja.

## Státusz-definíciók (kötelező ellenőrzési móddal)

- **implemented (kikényszerített)** = a **valós GitHub Actions futásban** egy manipuláló PR **merge-blokkolt** (a kötelező check piros vagy hiányzik és emiatt a merge nem engedett), és ez **a PR által nem módosítható forrásból** jön; a futás naplója a bizonyíték. A script, a workflow vagy a teszt megléte nem elég.
- **scaffold** = kódban van, de a manipuláció nem blokkolt (feltételes ág, `continue-on-error`, nem kötelező check).
- **concept** = csak leírás.
- **dokumentált, reprodukált rés** = a manipuláció **valós futással** átmegy, pontosan leírva; az elhallgatott rés hiba, a kimondott nem.
- Ami nincs futtatva, az **nem mért**.

## Feladat

**A. A fenyegetési modell (kötelező, mérésre alapozva).** Táblázat: mit **tud** a vizsgált PR módosítani (workflow-fájlok, composite action, scriptek és tesztek, pin-fájl, job- és lépésnevek, `if:`, `continue-on-error`, `needs`, `matrix`, `env` (pl. `GOTOOLCHAIN`), `permissions`, a trigger `on:` és `paths` szűrői, új workflow-fájlok), és mit **nem** (a base ág tartalma, a repository ruleset, a GitHub által hitelesített identitások, egy base-ből futó workflow definíciója). Minden sorhoz: a mérés vagy a forráshely.

**B. A kötelezettség modellje.** Mondd ki, mi a „kötelező ellenőrzés végrehajtása”: (1) az ellenőrzés definíciója nem a PR-ből jön, (2) tényleg lefut **ugyanarra a PR-fejre**, (3) az eredménye a merge-feltételhez kötött, és (4) **nem helyettesíthető** azonos nevű, üres tartalmú jobbal. Az (1)–(4) mindegyikére külön bizonyíték kell.

**C. Megoldási lehetőségek kiértékelése (mérés, nem vélemény).** Legalább ezeket értékeld, **mindegyiknél a megvalósíthatóságot mérd**, és mondd ki, mi marad nyitva:
- (a) **repository-szintű `workflows` (required workflow) ruleset-szabály**: elérhető-e ezen a csomagon (az org-szintű nem, `ref/measured-repo-state-2026-11-17.md`); a próba **kísérleti repón, a tulajdonos engedélyével** történjen, nem az éles `main` rulesetjén;
- (b) **`pull_request_target` workflow a base-ből**, amely a PR-t **adatként** kezeli (a GitHub API-n át olvassa a PR fájljait és workflow-it, **a PR kódját nem checkouttolja és nem futtatja**), és a PR védett fájljainak módosítását (a **védett halmazon**, lásd D) csak HEAD- és digest-kötött jóváhagyással engedi (az #195 mintája), kötelező checkként;
- (c) **base-ben definiált reusable workflow**, amelyet a kötelező check hív, így a lépések definíciója nem a PR-ből jön;
- (d) **kötelező review / code owner review** a `.github/**`, `scripts/**`, `.measurement-tools.json` útvonalakra (a CODEOWNERS létezik, de nem kényszerít): mérd meg, hogy a **tulajdonos mint egyedüli fejlesztő** hogyan viszonyul hozzá (a saját PR-t nem approve-olhatja), és a bypass-lista mit jelent;
- (e) minden egyéb, amit a mérés felvet.

Minden lehetőségnél: mit véd, mit **nem** (maradék rés), mit igényel a tulajdonostól (beállítás), a **költség** (CI-idő, karbantartás), és az **új támadási felület** (pl. a `pull_request_target` token-jogosultsága és a fork-PR-ok kezelése; a `default_workflow_permissions: write` és a `can_approve_pull_request_reviews: true` mért értéke).

**D. A védett halmaz (kötelező).** A kötelező ellenőrzések **tranzitív zárlata**: mely fájlok határozzák meg, hogy a kötelező ellenőrzés lefut és mit ítél (workflow-fájlok, a composite action, a hívott scriptek, a pin-fájl, `go.mod`/`rust-toolchain.toml` mint a mért eszköz verziójának forrása, a tesztek, amelyek a kötelező checket adják, a ruleset kötelező check-nevei). Mérd a zárlatot **a kód alapján** (mit hív a job), ne feltételezd; a halmaz minden elemére: védett-e, hogyan, és mi a maradék rés. Az **action**, a **`GATE`/`MR_GATE` kiválasztás**, a **`BOOTSTRAP` mód**, az **`object_model.py`** és a **`baseline-guard`** integritását **külön-külön** vizsgáld, mindegyikhez saját negatív bizonyítással vagy dokumentált réssel.

**E. A javaslat.** A C és D alapján **egy ajánlott kombináció** (nem a legtöbb lehetőség, hanem amelyik a kötelezettséget kikényszeríti és a maradék rés kimondott), a **tulajdonostól kért pontos beállításokkal** (ruleset-JSON vagy lépéslista), és a **jogos workflow-módosítás útjával** (látható, tulajdonosi, HEAD-hez kötött jóváhagyás: az #195 mintája). A repository-beállításokat **ne módosítsd**.

**F. Az implementáció terve (a következő, külön job spec bemenete).** Nem implementálsz: a jelentésed végén leírod, milyen fájlok, milyen tesztek, milyen negatív proof PR-ek kellenek, és ezek **hogyan futnak mérhetően**. A **#207 a kötelező negatív bizonyíték**: ugyanaz a változás, amely ma zöld, a javítás után **elutasított**, a naplóban az okkal, és ellenpróbával (a védelem nélküli állapoton zöld).

## Kötelező negatív esetek (a tervnek mindegyikre elvárt eredményt kell adnia)

| Manipuláció | Elvárt eredmény |
|---|---|
| a referencia-lépés és a `check-tools` törlése egy jobból (**#207**) | **DENY** (merge-blokkolt) |
| egy kötelező job törlése a workflow-ból | **DENY** (a kötelező check hiányzik, a merge blokkolt) |
| azonos nevű, üres tartalmú job (a kötelező név hamisítása) | **DENY** |
| `if: false` / `continue-on-error: true` / `needs` eltávolítása egy kötelező lépésen | **DENY** |
| a trigger szűrőjének szűkítése (`paths`, `branches`), hogy a workflow ne fusson | **DENY** (hiányzó check blokkol) |
| a `GATE`/`MR_GATE` kiválasztása a PR saját scriptjére | **DENY** |
| a `BOOTSTRAP` mód erőltetése | **DENY** |
| az `object_model.py` lecserélése megengedő változatra | **DENY** vagy dokumentált, reprodukált rés |
| a composite action módosítása (másik ref/SHA, lépés-kihagyás) | **DENY** |
| új, kötelezőnek nevezett workflow a védett halmazon kívül | dokumentált viselkedés |
| jogos workflow-módosítás jóváhagyással | **átmegy és látható** |
| jóváhagyás utáni új push | **új jóváhagyás szükséges** |
| a kötelező ellenőrzések eltávolítása a **védett halmazon kívüli** úton (pl. teszt, amely a checket adja) | **DENY** vagy dokumentált, reprodukált rés |

A „dokumentált rés” **valós futással reprodukált**, nem következtetés.

## Nem része a jobnak (ne csináld)

- Új küszöb, toolchain-csere, tesztkihagyás, termékkód; a PR-07 (FULL/DIFF) tartalma; az #213 (commit-aláírás kikényszerítése) implementációja; a `base@0.8.0` kiadás; a közös hook v1 fallbackjének cseréje; a `cargo-mutants`/`cargo-llvm-cov` telepítési pin.
- **A repository-beállítások (ruleset, branch protection, Actions, CODEOWNERS-kikényszerítés) módosítása**: javaslat, nem beállítás.
- **A kísérleti repó** létrehozása vagy bármely külső erőforrás használata a tulajdonos engedélye nélkül.
- Ne írj olyan állítást, hogy „a workflow védett”, ha csak a **szabály** (pl. a pin) védett, a **végrehajtás kötelezettsége** nem.

## Negatív példák (ne így)

- A védelem **ugyanabból a workflow-ból** fut, amelyet a PR módosíthat, és ezt „base-ből futónak” nevezed (a jelenlegi `baseline-guard` és a referencia-lépés is ilyen).
- A `pull_request_target` workflow **checkouttolja és futtatja a PR kódját** (ez a kód futtatása a bizalmas tokennel: **tilos**).
- Egy **név szerinti** kötelező check védelemnek számít, miközben a nevet a PR bármely üres jobja előállíthatja.
- A kötelező check **csak akkor zöld**, ha a PR nem változtat semmit, de a változtatás nem jelent hibát.
- A teszt, amely a hiányzó lépést „elkapja”, **maga a PR-ből jön**, és ezt védelemnek nevezed.
- Az `object_model.py` védettnek mondva, miközben a verifier a PR-ből fut.

## Negatív tesztek és pozitív kontrollok

Minden esethez: **származtatás**, **elvárt eredmény**, **kapott**, **pozitív kontroll** (a változatlan állapot zöld), **ellenpróba** (a védelem nélküli állapoton a manipuláció átmegy). A proof PR-ek **szándékosan hibásak, draft, `[DO NOT MERGE]`**, a munkaágra mutatnak (vagy egy befagyasztott, védelem nélküli bázisra az ellenpróbákhoz); az evidence-t a **lezárás előtt** rögzítsd a jelentésben, a commit-azonosítókkal, hogy a PR-ek lezárása és az ágak törlése után is visszakereshetők legyenek. **A proof ágakat explicit fájllistával építsd** (`git add -- <fájlok>`), és ellenőrizd, hogy a diff nem tartalmaz generált `.yaml` kísérőfájlt.

## Mérési korlátok (a jelentésben kimondandó)

- Egy sikeres helyi futás ≠ hogy a CI-ben a manipuláció elutasított; ahol ezt állítod, **valós Actions futás** (run id, headSha) igazolja.
- A **fork-PR-ok** viselkedése (a repo nyilvános, `members_can_fork: true`) külön mérendő vagy nem mértként kimondandó.
- Az **ütemezett workflow-k** (`mutation.yml`, `nightly.yml`) PR-ben nem futnak; a bizonyításuk **a PR-07 elfogadási feltétele**: ebben a jobban csak azt mondd ki, mit igényelnek.
- Az **egyedüli fejlesztő** modell (a tulajdonos a saját PR-ját nem approve-olhatja) korlátozza a review-alapú megoldásokat: mérd és mondd ki.
- Idő és költség (CI-futásidő) rögzítve; a klón tisztasága előtte/alatta/utána.

## Elfogadási kritériumok

1. **A fenyegetési modell (A)** és **a kötelezettség modellje (B)** kész, a leltár (boot 4.) és a védett halmaz (D) **mérésre** alapozott, file:line hivatkozásokkal.
2. **A lehetőségek (C)** mindegyike **mérve** (megvalósíthatóság, mit véd, mit nem, költség, új felület); ahol a mérés tulajdonosi engedélyt igényel (kísérleti repó), az **kérésként** szerepel, nem megkerülve.
3. **Az ajánlás (E)** egyetlen, indokolt kombináció, a tulajdonostól kért pontos beállításokkal és a jogos módosítás útjával.
4. **A kötelező negatív esetek táblázata** mindegyik sorra elvárt eredményt ad, a **#207** negatív bizonyíték terve valós futásra szól, ellenpróbával.
5. **Az action, a `GATE`/`MR_GATE`, a `BOOTSTRAP`, az `object_model.py` és a `baseline-guard`** mindegyike külön elbírálva.
6. **Az implementáció terve (F)** konkrét: fájlok, tesztek, proof PR-ek, mérési módszer.
7. A meglévő blokkoló kapuk, küszöbök és baseline-ok **változatlanok**; nincs termékkód és **repository-beállítás-módosítás** a diffben.
8. Az **elvégzett próbák** (ha vannak) valós Actions futással, run id-vel, headSha-val dokumentáltak; a **`nem mért`** itt **nem lezárás**, hanem a nyitott tételek listájának eleme.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented; a workflow létezése ≠ hogy fut; a kapu ≠ hogy bukni tud; **egy név szerinti kötelező check ≠ hogy az ellenőrzés lefutott**; a script a base-ből fut ≠ hogy a **hívása** is a base-ből jön.
- **A szabály védelme ≠ a végrehajtás kötelezettségének védelme.**
- Illeszkedő hash ≠ eredet vagy jogosultság. Exit code 0 ≠ sikeres mérés.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként; a hívóhely olvasása ≠ futás.

## Verifikáció és bizonyítás

- Minden állításhoz a parancs és a nyers kimenet; **reachability**: minden bekötött mechanizmushoz a hívás `file:line`-nal és a futás naplója.
- **A CI-hibákat vizsgáld ki, ne tulajdonítsd környezetnek.** Egy bukó check okát a naplóból állapítsd meg; a proof ágak **hatásosságát** (a változtatás ténylegesen érvényesül-e, pl. a Go-verzió) **mérd le**, ne feltételezd: az #195 proofjai közül három hatástalan volt, mert a `go.mod` `toolchain` sora csak alsó korlát, és a `setup-go` szövege nem azt döntötte el, amit gondoltunk.
- **Valós jóváhagyás nélkül egy jóváhagyás-mechanizmus nem bizonyított:** az #195-ben a valódi GitHub-komment CRLF sorvéggel tárolódott, és ezt csak a valódi komment mutatta meg; ha a megoldás jóváhagyást használ, **valódi kommenttel** (a tulajdonos kiadja, te nem játszod el) bizonyítsd.
- **Aláírás:** a cic-factory `main`-re közben mozdulhat; az ág a `main` tetején álljon a push előtt; a rebase érvényteleníti az aláírást, az `--amend` a régi blokkot tartja: a kimenetet **frissen, új üzenettel aláírt commitként** készítsd el. A Relay-repó csak merge-commitot enged; a `main` mozgásakor a PR-ágba merge-eld be a `main`-t.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-06c-workflow-integrity/output/`

- `output/workflow-integrity-report.md` — magyarul: vizsgált commitok; a klón tisztasága; a leltár és a védett halmaz; a fenyegetési és kötelezettség-modell; a lehetőségek kiértékelése; az ajánlás a kért beállításokkal; a **kötelező negatív esetek táblázata** (származtatás, elvárt, kapott, pozitív kontroll, ellenpróba); a **korlátok**; az **implementáció terve**; **claim-evidence tábla**: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`; nyitott tulajdonosi döntések.
- `output/raw/` — nyers kimenetek és scriptek (minden `.sh` első sora `#!/usr/bin/env bash`, ShellCheck `--severity=error`; a helyi útvonalak és felhasználónevek kerüljenek ki), köztük `raw/reachability.txt` (a hívási utak file:line-nal).

A kísérleti proof PR-ek a CIC_Relay-ben, külön ágon.

## Definition of Done

- A commit-azonosítók, az ág és a klón tisztasága rögzítve.
- A leltár, a védett halmaz, a fenyegetési és a kötelezettség-modell mérésre alapozott.
- Minden megoldási lehetőség mérve, az ajánlás egyetlen kombináció, a kért beállítások pontosak, a repository-beállítás **nem módosított**.
- A kötelező negatív esetek mindegyikére elvárt eredmény és bizonyítási terv; a #207 mint negatív bizonyíték, ellenpróbával.
- Az action, a `GATE`/`MR_GATE`, a `BOOTSTRAP`, az `object_model.py`, a `baseline-guard` külön elbírálva.
- Az implementáció terve konkrét; a nyitott tulajdonosi döntések listázva.
- A meglévő kapuk, küszöbök, baseline-ok változatlanok; nincs termékkód.
- A jelentés pontosan azt állítja, ami mérve van; a `nem mért` tételek külön listán.

## Tulajdonosi döntések (a jobnak nem kell eldöntenie; a jelentés rögzíti, melyik érvényes)

| Kérdés | Opciók | A spec alapértelmezése |
|---|---|---|
| A kikényszerítés mechanizmusa | (a) repository `workflows` szabály, (b) base-ből futó `pull_request_target` integritás-ellenőr, (c) base reusable workflow, (d) kötelező review, vagy kombináció | a job **méri és javasol**; a döntés a spec review-ja után a tulajdonosé |
| A kísérleti repó a (a) lehetőség méréséhez | engedélyezett / nem | **kérés**, a job nem hoz létre magától |
| A jogos workflow-módosítás útja | #195-minta (HEAD- és digest-kötött jóváhagyás komment) vagy más | az #195-minta, a base-ből futó ellenőrrel |
| Merge-előfeltétel-e az implementáció a PR-07-hez | igen / nem | **igen** (a tulajdonos döntése: #212 → #213 → PR-07) |

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-06c-workflow-integrity` ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát nem módosítod (a tulajdonos zárja). Az ág a `main` tetején álljon.
- **CIC_Relay:** a proof PR-ek külön ágakon, **draft, „DO NOT MERGE”** címmel; **nem mergelsz**. A javítás implementációja **nem része ennek a jobnak**.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR leírásában.
- A `git push` hívást a tulajdonos futtatja, ha a környezet elutasítja; add oda a pontos parancsot (lehetőleg **egy scriptben**), ne kerüld meg.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**.
