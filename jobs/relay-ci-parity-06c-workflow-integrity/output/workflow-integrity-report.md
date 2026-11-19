# #212 — a kötelező ellenőrzések végrehajtásának kikényszerítése: felmérés, kísérletek, ajánlás

Job: `relay-ci-parity-06c-workflow-integrity` · Issue: CentralInfraCore/CIC_Relay#212 · Spec: cic-factory #71 (`5a67563`).
**Hatókör:** felmérés, kísérlet, tervezés. **Nincs implementáció, a Relay-ben nincs módosítás, a repository-beállítások (Relay) nem módosultak.** A kísérletek eldobható scratch repókon futottak (tulajdonosi engedéllyel).

## 1. Vizsgált állapot

| Tétel | Érték |
|---|---|
| CIC_Relay `main` | `5c56e1ad82c3e5ea3e8f73098958b4460db38e5c` (tartalmazza a `68117e6`-ot) |
| Relay-klón | friss klón, `git status --short \| wc -l` = **0** a klónozás után |
| cic-factory `main` | `5a675633d64c66b1ef80db3a915d0caf2215d10b` |
| Scratch repók | `CentralInfraCore/cic-scratch-212-public` (id 1464313339), `-private` (1464313413), `-workflows` (1464314081) |
| Relay ruleset (olvasva, nem módosítva) | id 26873807: `required_status_checks` (verify, coverage, python, rust, ffi, manifest, mutation-pr; **mind integration_id 15368 = GitHub Actions**), `strict_required_status_checks_policy: false`, `non_fast_forward`, `deletion`; nincs `workflows`, nincs review szabály |
| Relay Actions-beállítás | `default_workflow_permissions: write`, `can_approve_pull_request_reviews: true`, `sha_pinning_required: false` |

A scratch publikus repó beállításai a Relay-ével egyeznek (workflow permissions write / approve true), ezért a mérések átvihetők.

**Módszertani megjegyzés (kimondva):** a scratch repók tartalmát a GitHub API-n át (nem `git push`-sal) töltöttem, mert a környezet a push-t nekem nem engedi; ez kizárólag a három eldobható repót érinti. A scratch repó rulesetjét a kísérletek között átállítottam (`disabled` két main-commit idejére: policy-szigorítás, CODEOWNERS; csak review-szabályos változat a (d)-hez; `strict` false/true). A közvetlen main-commit a kötelező checkek miatt elutasított volt („2 of 2 required status checks are expected"). Mindez csak a scratch repón történt; a Relay rulesetje nem módosult.

## 2. A kötelező ellenőrzések leltára (olvasva a kódból)

| Kötelező check | Definíció | Ki módosíthatja | A ruleset kötelezi |
|---|---|---|---|
| `verify` | `.github/workflows/verify.yml:18` | a PR (a `pull_request` a PR saját fájlját futtatja) | igen, név + 15368 |
| `coverage` | `verify.yml:74` | a PR | igen |
| `python` | `verify.yml:207` | a PR | igen |
| `rust` | `verify.yml:273` | a PR | igen |
| `ffi` | `verify.yml:322` | a PR | igen |
| `manifest` | `.github/workflows/manifest-check.yml:12` | a PR | igen |
| `mutation-pr` | `.github/workflows/mutation-pr.yml:359-360` (`gate` job, `name: mutation-pr`, `needs: [plan, go, rust, completeness, baseline-guard]`) | a PR (a `needs` lista is) | igen |
| referencia-lépés + `check-tools` | `.github/actions/measurement-reference/action.yml`; hívás pl. `verify.yml:92,96,304,308`, `mutation-pr.yml:65,70,189,193,246,250` | a PR (action és workflow) | csak közvetve (a lépés a kötelező jobokban van) |
| `baseline-guard` | `mutation-pr.yml:335` (a script a base-ből, **a hívás a PR-ből**) | a PR | közvetve (a `gate` `needs`-én át) |
| `object-evidence` | `.github/workflows/object-evidence.yml:28` | a PR | **nem kötelező** (report-only), `object_model.py` ott fut a PR-ből |
| `gate-selftest`, `mutation`, `nightly`, `renovate` | nem kötelező / ütemezett | a PR | nem |

Mért tény (#207, `ref/pin-protection-report.md`): a PR a `coverage` jobból törölte a referencia- és a `check-tools` lépést, **minden check zöld maradt** — a szabály védett, a végrehajtás kötelezettsége nem.

### Hívási utak (reachability, Relay `5c56e1a`; a teljes lista: `raw/reachability.txt`)

- `scripts/quality_gate.py:978` (`cmd_check_tools`) és `scripts/quality_gate.py:934` (`cmd_pin_reference`) a workflow-k `python3 "$MR_GATE" check-tools …` lépéséből hívódik (`.github/workflows/verify.yml:96`, `:308`); a `MR_GATE` kiválasztása az action-ben (`.github/actions/measurement-reference/action.yml`) történik, azaz a PR-ből jön.
- `scripts/quality_gate.py:806` (`pin_reference`) és `scripts/quality_gate.py:793` (`find_approval`): a jóváhagyás-keresés; a mechanizmus mintája az `integrity.py`-nek (`raw/scratch/integrity.py.txt`).
- `scripts/baseline_guard.py:65` (`main`) a `mutation-pr.yml:357` sorból hívódik, a base-ből kiolvasott példányon; a hívás és a `needs` a PR-ből jön.
- `scripts/object_model.py:1672` (`main`), `scripts/object_model.py:1626` (`cmd_verify`) a `object-evidence.yml:98` sorból hívódik; a `object-evidence` **nem kötelező check**.

## 3. Fenyegetési modell (A)

| A vizsgált PR **tudja** módosítani | Forrás / mérés |
|---|---|
| minden `.github/workflows/*.yml` (job, lépés, `if`, `continue-on-error`, `needs`, `matrix`, `env`, `permissions`, `on:`/`paths`/`branches`) | #207; scratch PR2 (lépéstörlés), PR3 (törlés), PR7 (szűrő), PR4 (új fájl) |
| a composite action | az action a PR-ből jön (`action.yml` fejléc: „this action and the workflow that calls it come from the pull request itself") |
| `scripts/**`, tesztek, `.measurement-tools.json`, `go.mod`, `rust-toolchain.toml` | a PR fája |
| a job- és lépésnevek, így **azonos nevű üres job** | scratch PR4 (n3) |
| új workflow-fájlok | scratch PR4 |
| a `GITHUB_TOKEN` jogosultsága a **saját workflow-jában**: önjóváhagyás | scratch PR14 (d1), PR15 (d2): a PR saját workflow-ja `github-actions[bot]`-ként APPROVE-ot adott, és a PR mergelt |

| A PR **nem** tudja módosítani | |
|---|---|
| a base ág tartalma; a ruleset; a GitHub-identitások | az olvasott ruleset; a `pull_request_target` definíciója: a PR nem írja felül (scratch PR3: az ellenőr törlése mellett az ellenőr a base-ből lefutott és DENY) |
| egy `pull_request_target` workflow definíciója és checkoutja | scratch §6 (a futás a **default ág** workflow-ját és scriptjét használta) |

## 4. A kötelezettség modellje (B)

„Végrehajtás" = (1) a definíció nem a PR-ből jön, (2) ugyanarra a fejre lefut, (3) az eredménye merge-feltétel, (4) azonos nevű üres job nem helyettesíti. Három külön dolog (F2):

| | Mit ad | Bizonyítva (scratch) |
|---|---|---|
| (i) jogosultság a védett halmaz módosítására | tulajdonosi, head- és digest-kötött komment | PR12: valódi tulajdonosi komment → `APPROVED_UPDATE` (run 44554697230) |
| (ii) a módosított változat megfelelősége | statikus megfelelőségi vizsgálat (`verify` job létezik, nem feltételes, futtatja a checket, a trigger nem szűrt) | PR13: valódi komment **mellett** DENY („conformance: job 'verify' does not run scripts/check.sh") |
| (iii) a végrehajtás és eredménye | a kötelező checkek ténylegesen futnak és zöldek | a `verify`/`integrity` required check mindkettő (mergeable_state, merge 405) |

A jóváhagyás **csak az (i)-et adja**; nem CI-eredmény.

## 5. A megoldási lehetőségek kiértékelése (C) — mérve

| | Megvalósítható? | Mit véd | Mit nem | Költség / új felület |
|---|---|---|---|---|
| **(a) repository `workflows` ruleset** | **a vizsgált konfigurációban nem sikerült aktiválni** (mért); **nem bizonyított, hogy nem támogatott**. Privát repó: HTTP 403 „Upgrade to GitHub Pro or make this repository public". Publikus repó: HTTP 422 `Invalid parameter workflows: Workflow error at index 0:` — **ugyanaz az üzenet** a helyes, a nem létező útvonalú, a rossz repo-id-jú, a rövid ref-es és az üres listás próbára is (5 variáns, a workflow a saját és egy külön publikus repóban); az **ok nem diagnosztizált** | – | – | `raw/scratch/rulesets-probe.txt`. A (a) **nem mért** értelemben marad nyitva: ha a csomag változik, újramérendő |
| **(b) base-ből futó `pull_request_target` integritás-ellenőr** | **igen, mérve** | a védett halmaz minden módosítását jóváhagyáshoz köti (head+digest); a PR-t adatként kezeli (nincs checkout, nincs PR-kód futtatás); a jóváhagyott módosítást is megfelelőségi vizsgálatnak veti alá | a védett halmazon **kívüli** út (tesztek gyengítése); base-változás `strict: false` mellett; fork-PR nem mért | egy `pull_request_target` workflow (token: `contents: read`, `pull-requests: read`); karbantartás: a policy; új támadási felület: a `pull_request_target` token (a scratch-ben nincs secret) |
| **(c) base-beli reusable workflow** | **önmagában NEM véd (mérve)** | a lépések definíciója a hívott fájlból jön | a **hívó** a PR-ből jön: PR17-en a PR a `uses:` ref-et a `permissive` ágra állította, a megengedő reusable **lefutott és zöld** (`reusable-call / reusable-check=success`); a PR-t csak az (b) `integrity` check blokkolta | csak (b)-vel együtt értelmes |
| **(d) kötelező review / code owner** | **a mért beállításokkal megkerülhető** | emberi felülvizsgálat | a PR saját workflow-ja `github-actions[bot]`-ként approve-ol (PR14: `required_approving_review_count: 1` → merged; PR15: `require_code_owner_review: true` + `CODEOWNERS * @sinkog` mellett is merged — az ok **nem diagnosztizált**: a PR szerzője egyben a code owner, második identitás nincs). Az egyedüli fejlesztő a saját PR-ját nem approve-olhatja (422 „Can not approve your own pull request"). **`can_approve_pull_request_reviews: false` megállítja** (PR16: `approve=failure`, a PR nem mergelhető review nélkül) | a tulajdonos számára blokkoló: a saját PR-ját nem approve-olhatja → bypass vagy második identitás kellene; nem mért |
| **(e) `strict_required_status_checks_policy: true`** | **igen, mérve** (lásd 7.) | a base-változás utáni újraértékelés | – | minden PR naprakészen tartandó (update-branch + újrafutás) |

## 6. Mért, a tervet meghatározó tény: a `pull_request_target` a default ág definícióját használja

PR18 (scratch) egy **nem-default** ágra (`frozen-base`) irányult, amelyen az `integrity.yml` egy `FROZEN-BASE-VARIANT…` jelzést kiíró változata volt. A futás (44556567050) **nem** írta ki a jelzést, `base=` a **main** csúcsa (`0b3631c`), nem a `frozen-base` csúcsa (`2b0d46a`).
**Következmény:** a Relay-ben a mechanizmus csak a **`main`-re kerülve** hat; a proof PR-ek **nem használhatnak befagyasztott, védelem nélküli bázis-ágat** az ellenpróbához (ahogy a #195-nél), és az **implementációs PR-t maga a mechanizmus nem védheti** (bootstrap: ugyanaz a probléma, mint a #195-nél, egyszeri, a main-re kerülés után tiltott). Az ellenpróbát scratch repó vagy a bevezetés előtti állapot adja.

## 7. A kötelező negatív esetek (a spec 20 sora)

`Mért` = valós Actions futás a scratch repón (run id-k: `raw/scratch/runs.tsv`, PR→head: `raw/scratch/pr-results.tsv`, verdikt-sorok: `raw/scratch/integrity-log-lines.txt`). `Terv` = a Relay-ben bizonyítandó az implementációs jobban.

| # | Manipuláció | Elvárt | Kapott (scratch) | Pozitív kontroll | Ellenpróba |
|---|---|---|---|---|---|
| 1 | referencia-lépés + `check-tools` törlése (**#207**) | DENY | analóg: a `verify` jobból a check-lépés törlése (PR2): `verify=success`, `integrity=failure`, **merge 405** „Required status check integrity is failing" | PR1: `clean` | csak `verify` kötelező → PR2 `unstable` (mergelhető) |
| 2 | kötelező job törlése | DENY | **közvetett**: a hiányzó kötelező check blokkol (PR7: `verify` hiányzik → `blocked`); a törlés mint védett módosítás ugyanaz a mechanizmus (PR2). Külön job-törlő PR **nem készült** | – | – |
| 3 | azonos nevű, üres job | DENY | PR4: a hamis `integrity=success` mellett a valódi `integrity=failure` **blokkol**, merge 405 | – | – |
| 4 | `if: false` / `continue-on-error` / `needs` eltávolítása | DENY | **közvetett** (védett módosítás → DENY, PR2 mechanizmus; megfelelőségi vizsgálat az `if`/`continue-on-error`/`needs` ellen kódban: `raw/scratch/integrity.py.txt`). Külön PR **nem készült** | – | – |
| 5 | trigger-szűrő szűkítése | DENY | PR7: `paths` szűrő → `verify` nem fut, `integrity=failure`, `blocked` | – | – |
| 6 | `GATE`/`MR_GATE` a PR scriptjére | DENY | analóg: az ellenőr scriptjének lecserélése (PR5): a base-script futott, DENY. A Relay `GATE` kiválasztása **nem mért** (Terv) | – | – |
| 7 | `BOOTSTRAP` erőltetése | DENY | **nem mért** (Terv); az action `.github/**` alatt van → védett halmaz | – | – |
| 8 | `object_model.py` lecserélése | DENY vagy rés | **nem mért**; `object-evidence` **nem kötelező**: a verifier a PR-ből fut → **scaffold**, védett halmazba (`scripts/**`) tartozik | – | – |
| 9 | composite action módosítása | DENY | **közvetett** (`.github/**` védett; PR2 mechanizmus); Relay-action **nem mért** (Terv) | – | – |
| 10 | új, „kötelezőnek nevezett" workflow | dokumentált | PR4: új `fake.yml` → DENY (új fájl a védett `.github/` alatt) | – | – |
| 11 | jogos módosítás jóváhagyással | átmegy | PR12, valódi tulajdonosi komment, `APPROVED_UPDATE` (run 44554697230), `clean` | – | – |
| 12 | jóváhagyott, de a kötelező ellenőrzést elhagyó módosítás | DENY | PR13: komment mellett DENY „conformance: job 'verify' does not run scripts/check.sh" | – | – |
| 13 | jóváhagyott módosítás, a kötelező ellenőrzések nem futnak/pirosak | DENY | **nem mért külön** (a piros `verify` required check blokkolna; nem futtatva) | – | – |
| 14 | jóváhagyás utáni új push | új jóváhagyás | PR12 új fejen (`43474da`): `integrity=failure`, `blocked` | – | – |
| 15 | ellenőrzések eltávolítása a védett halmazon **kívül** (pl. teszt) | DENY vagy rés | **dokumentált rés, NEM reprodukálva**: lásd 8. | – | – |
| 16 | az integritás-ellenőr workflow törlése | DENY | PR3: az ellenőr a base-ből lefutott, `integrity=failure`, merge 405 | – | – |
| 17 | az integritás-check nevének hamisítása | DENY | PR4 (lásd 3.) | – | – |
| 18 | korábbi eredmény felhasználása új HEAD-en | DENY | az eredmény fej-kötött (a `pull_request_target` futás `head_sha` = PR-fej; az új fejen új futás kell); PR12 új fején a régi jóváhagyás nem érvényes | – | – |
| 19 | base változása az ellenőrzés után | újraértékelés / rés | **rés reprodukálva `strict: false` mellett**: policy-szigorítás után a korábban zöld PR10 (`docs/x.txt`, ma már védett, jóváhagyás nélkül) **mergelt**, az ellenőrzés nem futott újra. **`strict: true` mellett**: PR11 merge 405 „2 of 2 required status checks are expected", az update-branch után az ellenőrzés újrafutott és `failure` | – | `strict: false` = a rés |
| 20 | a bizalmi konfiguráció módosítása | DENY / külön út | PR6: `policy.json` önjóváhagyó hozzáadása → DENY (a base-policy dönt) | – | – |
| 21 (új, review) | védett útvonalról védetlen útvonalra átnevezés | DENY | **a scratch ellenőr hibája, mért**: PR20 (`scripts/check.sh` → `notes/check-moved.sh`) `UNCHANGED` / `integrity=success` (run 44560294600); a PR csak a `verify` bukása miatt blokkolt. A PR19 (cél: a már védett `docs/`) érvénytelen próba volt (DENY a cél miatt), nem bizonyíték | – | – |
| 22 (új, review) | hiányzó valódi ellenőrzés + hamis zöld azonos nevű check | DENY | **nem mért** (R3) | – | – |

## 8. A védett halmaz és a maradék rés (D)

A zárlat a kódból (a `verify.yml` a következőket hívja: `go vet`, `go test`, `make verify`, `python -m pytest/ruff/mypy/…`, `cargo …`, `scripts/quality_gate.py`, `scripts/gen_manifest.sh`; a `mutation-pr.yml` a `plan`/`completeness`/`baseline-guard` scripteket):

| Elem | Védett (a javasolt (b)-vel) | Megjegyzés |
|---|---|---|
| `.github/workflows/*`, `.github/actions/**`, `.github/CODEOWNERS` | igen (`.github/`) | |
| `scripts/quality_gate.py`, `baseline_guard.py`, `gremlins_gate.py`, `mutation_plan.py`, `gen_manifest.sh`, `object_model.py` | igen (`scripts/`) | az `object_model.py` verifiere nem kötelező check része |
| `.measurement-tools.json`, `.measurement-scope.json`, `.mutation-baseline.json`, `go.mod`, `rust-toolchain.toml`, `Cargo.lock`, `renovate.json` | **fel kell venni a policyba** (nem `.github/`/`scripts/` alatt vannak) | |
| a ruleset kötelező check-nevei | a ruleset (tulajdonosi); a PR nem módosíthatja | |
| **a tesztek és a termékkód** (a `go test`/`pytest`/`cargo test` tartalma) | **részben védhető: a gate-et őrző tesztek (A osztály) védettek lehetnek, a termék-tesztek (B osztály) nem** — lásd 8b | a PR jogosan módosítja; egy teszt törlése/gyengítése zöld marad. Ezt csak a ratchet-baseline (mutation, coverage) és az **emberi review** fogja meg; a (d) a mért beállításokkal megkerülhető. **Kimondott maradék rés (#15), nem reprodukált.** |

Külön elbírálás (kért):

| Komponens | Elbírálás | Státusz |
|---|---|---|
| composite action | `.github/actions/**` védett; a `MODE`-választás és a `GATE` a PR-ből jött: védett halmazba kerül | scaffold a mai állapotban, a javaslattal védett |
| `GATE`/`MR_GATE` kiválasztás | a `pin-reference` jelenlét-ellenőrzés a PR action-jében van; védett halmaz | mai állapotban rés (#207), javaslattal védett |
| `BOOTSTRAP` | a választás a PR action-jében; védett halmaz; a #201 egyszeri bootstrap-tilalma csak ha az action a base-ből jön | mai állapotban rés, javaslattal védett |
| `object_model.py` | `object-evidence` **nem kötelező**; a verifier a PR-ből fut | scaffold; a kötelezővé tétele külön döntés |
| `baseline-guard` | a script a base-ből, a **hívás és a `needs` a PR-ből** (`mutation-pr.yml:361`) | mai állapotban rés; javaslattal védett |

## 8b. A védett halmaz határa (pontosítás a review kérésére)

**Alapelv:** a *termékkód természetes változtatása* és az *ellenőrzési mechanizmus gyengítése* két külön osztály. Az első szabadon változik (review + CI), a második csak a jóváhagyási úton.

A halmaz a Relay kódjából (`git grep` a `5c56e1a`-n; `raw/protected-set-measurement.txt`) így határolható el:

| Osztály | Mi tartozik bele (mért listából) | Kezelés |
|---|---|---|
| **A. A gate szemantikáját meghatározó** | `.github/**`; `scripts/*.py` és `scripts/*.sh` (`quality_gate.py`, `baseline_guard.py`, `gremlins_gate.py`, `mutation_plan.py`, `object_model.py`, `gate_selftest.py`, `seeded_defects.py`, `gen_manifest.sh`); a gate-et ellenőrző tesztek: `tests/test_tools/**` (köztük `test_quality_gate*.py`, `test_pin_reference.py`, `test_baseline_guard.py`, `test_mutation_plan*.py`, `test_mutation_policy.py`, `test_mutation_workflow_enumeration.py`, `test_gate_selftest.py`, `test_seeded_defects.py`, `test_object_*`, a `fixtures/` és a `seeded_bundle.py`); a konfigurációk: `.measurement-tools.json`, `.measurement-scope.json`, `.mutation-baseline.json`, `go.mod`, `rust-toolchain.toml`, `pytest.ini`, `pyproject.toml`, `.yamllint`, `Makefile`, `Cargo.lock`, `renovate.json` | **védett**: módosítás csak head+digest kötött tulajdonosi jóváhagyással, megfelelőségi vizsgálattal |
| **B. Termékkód és termék-tesztek** | Go/Rust forrás és `*_test.go`, Rust tesztek, `tests/` alatt a `test_tools/`-on kívüli tesztek | **nem védett** (természetes változás); a gyengítést a ratchet-baseline-ok (A osztály, védett) és az emberi review fogja meg |
| **C. Egyéb** | dokumentáció, `MANIFEST.sha256` (a `manifest` check ellenőrzi) | nem védett |

**Miért tartoznak a `tests/test_tools/**` tesztek az A osztályba:** a `python` kötelező job a `pytest`-et futtatja (`.github/workflows/verify.yml:257`, `pytest.ini` `testpaths = tests`), és ezek a tesztek őrzik a workflow-bekötést (pl. hogy minden mérő job a referencia-lépés és a `check-tools` után mér: `tests/test_tools/test_quality_gate.py`, `test_pin_reference.py`). Egy PR, amely ezeket a teszteket törli vagy gyengíti, a #207-hez hasonlóan zöld marad. Az #195 proofjai is a saját teszt-táblájukat szerkesztették, hogy átmenjenek (ez mért).

**Mit mértem és mit nem (kimondva):**
- **Mért (scratch):** az útvonal-előtag alapú védelem működik, és új policy-vel azonnal érvényes: `docs/` felvétele a védett előtagok közé után a `docs/y.txt`-t módosító PR (PR11) a branch-frissítés után `integrity=failure` és blokkolt lett. Nem-védett útvonal (VERSION, `notes/`) módosítása `UNCHANGED` (PR1, PR15, PR16; a PR14 a `.github/` alatti fájl miatt DENY volt, de a review-only ruleset idején nem volt kötelező az `integrity`).
- **NEM mért:** az A osztály fenti **listája** a Relay-ben nem lett kikényszerítve; a lista a kód olvasásából származik. A zárlat **teljességét** (hogy nincs-e olyan fájl, amelyet egy kötelező job olvas, de a policy nem fed) a bevezetéskor **gépi önellenőrzésnek** kell bizonyítania (minden, a kötelező jobok lépéseiben hivatkozott útvonal illeszkedjen a policy-re, vagy legyen kimondva, miért nem); ez az ellenőrzés még nincs megírva, **nem futott**.
- **Kikényszerített védelem nem állítható** a B osztály gyengítése ellen: ott a védelem a baseline + review, és a (d) review a mért beállításokkal megkerülhető (PR14/PR15). A B osztály gyengítése **nyitott kockázat**, nem lezárt rés.
- A „természetes változás" és a „gyengítés" közötti határ **nem gépi**: a ratchet-baseline megfogja a mért mutáció/coverage csökkenést, de a tesztek *lecserélése* azonos számú, gyengébb ellenőrzésre nem biztosan. Ezt nem mértem.

## 9. Az ajánlás (E)

**Egy kombináció:**
1. **(b)** egy `integrity` workflow `pull_request_target`-tel, a base-ből, a PR-t adatként kezelve; kötelező check (`integrity`, integration_id 15368); a védett halmaz minden módosítása head+digest kötött tulajdonosi jóváhagyás nélkül DENY; jóváhagyás mellett is megfelelőségi vizsgálat. A jóváhagyás formátuma az #195-é (egy komment fedheti az #195 pin-fájl és a védett halmaz változását).
2. **(e)** `strict_required_status_checks_policy: true` (a base-változás utáni újraértékelés).
3. **`can_approve_pull_request_reviews: false`** (E2).

**A tulajdonostól kért pontos beállítások (a job nem módosította őket):**
```
ruleset 26873807: required_status_checks += {"context":"integrity","integration_id":15368}
ruleset 26873807: strict_required_status_checks_policy: true
repo Actions:     can_approve_pull_request_reviews: false
repo Actions:     default_workflow_permissions: read  (lásd E2)
```
**Sorrend:** előbb az `integrity` workflow kerül a `main`-re (a bevezető PR-t a mechanizmus még nem védi; egyszeri bootstrap), és **csak ezután** kerül a `integrity` a kötelező checkek közé (különben minden PR blokkolt lenne).

**Nem választott:** (a) a vizsgált konfigurációban nem aktiválható (az ok nem diagnosztizált, a nem-támogatás nem bizonyított); (c) önmagában nem véd; (d) nem bízható rá a védelem a mért beállításokkal.

**Maradék rés (kimondva):** (1) a tesztek/termékkód gyengítése (8. táblázat); (2) fork-PR **nem mért**; (3) az `integrity` workflow `actions/checkout@v4` mutable tag-je (a `sha_pinning_required: false`); (4) a repository-admin (tulajdonos) a rulesetet kikapcsolhatja; (5) `strict: true` költsége: minden PR-t naprakészen kell tartani.

### E2. A jogosultsági felület keményítése (nem blokkoló, a döntés tulajdonosi)

| Beállítás | Javaslat | Kompatibilitás (olvasott kód; **futással nem mért**) |
|---|---|---|
| `can_approve_pull_request_reviews` | `false` | **mérve hatásos** (PR16). Renovate a `RENOVATE_TOKEN` PAT-ot használja (`renovate.yml:35`), nem a `GITHUB_TOKEN`-t: nem érinti |
| `default_workflow_permissions` | `read` | A `verify.yml` és a `manifest-check.yml` **nem deklarál `permissions:`-t** (a default-ra támaszkodnak); olvasott kódjuk csak checkout/teszt/build (nincs `gh`, `git push`). A `renovate.yml` job-szintű `contents: write`/`pull-requests: write`-ot deklarál, a `report` `issues: write`-ot — **nem érinti**. **Futással nem mért**: a bevezetés előtt egy proof PR kell a `permissions: contents: read` workflow-szintű beírásával. **A scratch-ben a repo-szintű `read` kérés `write`-ra maradt (az org-szint `write` korlátozhat) — nem diagnosztizált** |
| `sha_pinning_required` | `true` a bevezetés után, külön elemzéssel | a mai workflow-k mutable tag-ekre hivatkoznak (`actions/checkout@v4`, `renovatebot/github-action@v46.1.15`, `taiki-e/install-action@v2`, `actions/setup-go@v5`): bekapcsolás előtt minden hivatkozást SHA-ra kell pinelni; **nem mért** |

## 9b. Bootstrap trust (pontosítás a review kérésére)

**Probléma:** a még nem működő integritásvédelem nem igazolhatja a saját telepítését, és a későbbi módosítása ugyanilyen bizalmi esemény. Két külön esemény: **(I) az első telepítés**, **(II) a mechanizmus későbbi módosítása**.

**Mért alapok:** (1) a `pull_request_target` a **default ág** workflow-ját használja (PR18) → a mechanizmus a `main`-re kerüléssel lép életbe, a bevezető PR-t még nem védi; (2) a hiányzó kötelező check blokkol (PR7) → ha az `integrity` a workflow előtt kerül a kötelezők közé, **minden PR blokkolt lesz**; (3) a scratch-ben a sorrend (workflow a mainen, utána a kötelezővé tétel) működött (PR1 `clean`); (4) a policy önjóváhagyása elutasított (PR6), az ellenőr törlése/lecserélése elutasított (PR3, PR5) — **azaz a telepítés utáni módosítások védettek**.

**Javasolt, nem mért folyamat** (a Relay-ben még **nem futott**):

| Lépés | Tartalom | Bizonyíték |
|---|---|---|
| 1. Rögzített HEAD | az implementációs PR HEAD-je rögzítve (commit-azonosító a PR-ben és a jóváhagyásban) | a PR leírása; `--match-head-commit` a merge-nél |
| 2. Tulajdonosi jóváhagyás | a tulajdonos a diffet átnézi, és **HEAD- és digest-kötött kommentet** ad az #195 formátumában; a mechanizmus nem igazolja önmagát | valódi komment (nem Claude írja) |
| 3. Merge a `main`-re | az `integrity` workflow még **nem kötelező check** | merge-commit, post-merge futás |
| 4. Merge utáni negatív bizonyítás | a már élő mechanizmussal a 20 sor Relay-beli proof PR-jei (draft, DO NOT MERGE), köztük a **#207**, run id-vel és headSha-val | a jelentés run-táblája |
| 5. Aktiválás | **csak a 4. sikere után** a tulajdonos felveszi az `integrity`-t a kötelező checkek közé és `strict: true`-t állít | a ruleset-JSON előtte/utána |
| 6. Aktiválás utáni negatív bizonyítás | az ellenőr törlése és a név hamisítása a **kötelezővé tett** állapotban is blokkolt; stale evidence a tényleges Relay-konfigurációban | run id-k |
| 7. Későbbi módosítás | a mechanizmus (workflow, script, policy) módosítása ugyanazon az úton (jóváhagyás + megfelelőség), és a **regressziós proof-készlet újrafuttatása** a módosított változaton | run id-k |

**Állítás-fegyelem:** amíg az 1–7 lépés a Relay-ben nem futott, **kikényszerített bootstrap-védelmet nem állítok**. A scratch (3) és (4) pont csak a mechanizmus-szintű viselkedést igazolja.

## 10a. Implementációs követelmények és elfogadási feltételek (a #72 review F1–F5 alapján)

A scratch `integrity.py` **kísérleti**; az alábbiak az éles implementáció kötelező követelményei és **elfogadási feltételei**. A `strict: true` szükséges, de **egyik pontot sem bizonyítja önmagában**.

**R1 (F1) — az ellenőr eredménye és a vizsgált állapot azonossága.** A kísérleti ellenőr a HEAD-et az eseményből veszi, de a módosított fájlok listáját a PR *futás közbeni* API-állapotából olvassa (`raw/scratch/integrity.py.txt`: `api(f"repos/{REPO}/pulls/{PR}/files")`). A kettő nem feltétlenül azonos állapot. Követelmény:
- a változáshalmaz az **egzakt HEAD és BASE** commitokból számolt (pl. `compare/BASE...HEAD` API vagy git-diff két rögzített commit között), nem a PR aktuális állapotából;
- az ellenőr a döntés **publikálása előtt** újraolvassa a PR HEAD-jét és BASE-ét, és ha eltér a futás elején rögzítettől, **fail-closed** (a check pirossal végződik, újrafuttatás kell);
- a **policy és az ellenőr verzióazonossága** a rekordban: a futás kiírja a BASE commit, a policy sha256 és az ellenőr script sha256 értékét, és a döntés ezekhez kötött (a scratch a base- és policy-digestet kiírja; az ellenőr-script digestje **nincs** kiírva, a követelmény új);
- **hiányos fájllista**: a GitHub a PR-fájllistát korlátozza (a `pulls/{n}/files` legfeljebb 3000 fájlt ad); ha a lista lehetséges csonkolása jelezhető vagy a mennyiség a határhoz ér, fail-closed;
- **átnevezés (mért hiba a scratch ellenőrben, PR20):** a scratch ellenőr csak a `filename`-et vizsgálja, a `previous_filename`-et **nem**. A `scripts/check.sh` → `notes/check-moved.sh` átnevezés `UNCHANGED: no protected path touched` verdiktet kapott (run 44560294600), `integrity=success`; a PR csak véletlenül maradt blokkolt, mert a `verify` a hiányzó script miatt bukott. Követelmény: **mind az új, mind a régi útvonalat** (`filename` és `previous_filename`) vizsgálni, és a védett halmazból kivitt fájl **védett módosításnak** számít. Ez a scratch ellenőr **ismert hiányossága**, az éles implementációban külön negatív teszt kell rá.

**R2 (F2) — a megfelelőségi ellenőrzés szemantikája.** A scratch megfelelőségi vizsgálat szöveges jelenlétet néz (`"scripts/check.sh" in run`, nincs `if`/`continue-on-error`/`needs` kulcs, a trigger nem szűrt). Ez a kísérlethez megfelelő, az éles implementációhoz **nem elegendő**. Az éles ellenőrnek **a hívás jelenlétén túl** vizsgálnia kell:
- a tényleges végrehajtást (a lépés valóban lefut: `if` a job-on, a lépésen és az őket szülő szinten, `continue-on-error` minden szinten, `timeout`, `shell`-felülírás, a lépés `run`-ja nem egy kimenet- vagy `|| true`-szerű elnyelő parancs);
- a hibakezelést (`set -e`/`pipefail`, a kilépési kód nem nyelődik el, a `gate` jobnál a `needs` eredmény-ellenőrzés, `if: always()` esetén a tényleges `success` vizsgálat, ahogy a `mutation-pr.yml:359-380` is csinálja);
- a függőségeket (`needs`, matrix, a `check-tools`/referencia-lépés a mérés *előtt* fut, ahogy a `tests/test_tools/test_quality_gate.py` őrzi);
- a használt bemenetek eredetét (a script, a pin-fájl és a referencia a BASE-ből jön; `MR_GATE`/`MODE` nem a PR-ből választott; env-felülírás, pl. `GOTOOLCHAIN`, nem módosítja a mért eszközt);
- a **YAML tényleges szemantikáját** (strukturált elemzés, nem szöveg-keresés; anchor/alias, többsoros `run`, reusable workflow `uses:` ref és annak a BASE-ben rögzített volta).
A jelentés elfogadási feltétele: minden itt felsorolt irányra **negatív teszt**, amelynek a szöveges jelenlétvizsgálat **átmenne**, a strukturált nem.

**R3 (F3) — hiányzó valódi ellenőrzés mellett megjelenő hamis check (kötelező negatív eset).** A PR4 a *valódi piros + hamis zöld = blokkolt* esetet igazolta. A **fordított** (*hiányzó valódi + hamis zöld*) **még nem mért**; ez **külön kötelező negatív eset és elfogadási feltétel**: a valódi `integrity` nem fut le (pl. a base-beli workflow nem indul el, vagy a futás nem jön létre) és a PR egy azonos nevű, zöld jobot szállít; elvárt: a merge blokkolt. A tervezett mérés: scratch-ben a base `integrity.yml` ideiglenes eltávolítása (tulajdonosi karbantartással) vagy a trigger kikapcsolása mellett a hamis job zöldje nem elég; a kapott eredmény ebben a szakaszban **nem szerepel**.

**R4 (F4) — az aktiválási időszak.** A workflow mergelése (9b/3. lépés) és a kötelezővé tétele (9b/5. lépés) között **átmenetileg nincs kikényszerített védelem**, ebben az időszakban más PR sem mergelhető kontrollálatlanul. Követelmények: (i) az időszak **a lehető legrövidebb és tulajdonosi**: a 3–5. lépés egy megfigyelt, soros folyamat, amely alatt **más PR nem mergelhető** (a tulajdonos a merge-eket befagyasztja); (ii) az időszak kezdete és vége **rögzítve** (commit-azonosító, ruleset előtte/utána); (iii) az **aktiválás utáni negatív bizonyítás** (9b/6. lépés) **kötelező lezárási feltétel**: enélkül a #212 nem zárható.

**R5 (F5) — a workflows ruleset megítélése.** A pontos állítás: **a vizsgált konfigurációban nem sikerült aktiválni**, a HTTP 422 oka nem diagnosztizált; ez **nem azonos** azzal, hogy bizonyítottan nem támogatott. Az ajánlás emiatt nem az (a)-ra épül, de a döntés **újramérhető** (pl. csomag-váltás után, vagy ha a GitHub a hibaüzenetet pontosítja).

## 10. Az implementáció terve (F) — a következő, külön job bemenete

**Fájlok (CIC_Relay):** `.github/workflows/integrity.yml` (`pull_request_target`, base-checkout, minimális token), `scripts/integrity.py` (a `raw/scratch/integrity.py.txt` Relay-re igazítva: védett halmaz a 8. szerint, megfelelőségi vizsgálat a kötelező jobokra: létezik, nem feltételes, a `check-tools`/referencia-lépés jelen van, trigger nem szűrt, `needs` a `mutation-pr` `gate`-ben), `integrity-policy.json` (védett halmaz, jóváhagyók), `tests/test_tools/test_integrity.py`, a `quality_gate.py` jóváhagyás-formátumának összehangolása, MANIFEST/SYMBOLS frissítés.
**Tesztek:** a 7. táblázat mind a 20 sora egységtesztként + proof PR-ként; a megfelelőségi vizsgálat táblázatvezérelt tesztjei.
**Proof PR-ek (draft, DO NOT MERGE, a `main`-re mutatnak, mert a §6 szerint befagyasztott bázis nem használható):** #207 ismétlése (a javított állapoton DENY); a 20 sor Relay-beli ismétlése; fork-PR (külön fiókkal, ha lesz); az ütemezett workflow-k (`mutation.yml`, `nightly.yml`) bizonyítása **a PR-07 elfogadási feltétele**: ebben a jobban csak azt mondom ki, hogy a `pull_request_target` az ütemezett futásra nem hat, azokhoz külön kikényszerítés kell.
**Ellenpróba:** a bevezetés előtti `main` (az #207 ma zöld), és a scratch repó.
**Mérési módszer:** valós Actions run id, headSha, `mergeable_state` és merge-kísérlet (405) — ahogy a scratch-ben.
**Valódi jóváhagyás:** a tulajdonos kommentje szükséges (a CRLF-lecke az #195-ből; a scratch-ben a komment `\r`-t kezelő regexszel mért).

## 11. Nem mért / nyitott

- **Bootstrap (9b):** az 1–7 lépés a Relay-ben nem futott; a védett halmaz teljességét bizonyító gépi önellenőrzés (8b) nincs megírva.
- (a) workflows rule: a hiba oka nem diagnosztizált; a Relay csomagján nem tudható, hogy a funkció később elérhető-e.
- **Fork-PR** viselkedés (`members_can_fork: true`): nem mért (második fiók kell).
- Code-owner szabály viselkedése: az ok nem diagnosztizált (a szerző = a code owner); második identitással mérendő.
- A Relay saját `GATE`/`MR_GATE`, `BOOTSTRAP`, `object_model.py`, action manipulációi: Relay-ben **nem futtatva**.
- **Hiányzó valódi + hamis zöld azonos nevű check** (R3), a policy+ellenőr verzióazonosság, az egzakt HEAD/BASE változáshalmaz és a fájllista-csonkolás kezelése: nem mért (R1).
- Külön job-törlő (#2), `if`/`continue-on-error`/`needs` (#4), jóváhagyott-piros (#13) PR nem készült.
- A `default_workflow_permissions: read` Relay-beli hatása nem futtatva.
- Ütemezett workflow-k (`mutation.yml`, `nightly.yml`): nem része a jobnak (PR-07 feltétele).
- Idő/költség: a scratch futások ~20–60 s-ek; a Relay-beli költség nem mért.

## 12. Claim-evidence tábla

| Állítás | Státus | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A #207 hézag ma nyitott (a lépéstörlés zöld marad) | mért (#195 jelentés) | `ref/pin-protection-report.md` §4, §7 | valós Actions futás | – |
| (a) a vizsgált konfigurációban nem sikerült aktiválni (nem bizonyított, hogy nem támogatott) | mért | `raw/scratch/rulesets-probe.txt` (403 / 422 ×5) | API-hívások | ok nem diagnosztizált |
| (b) a PR-t DENY-olja, ha a védett halmazt módosítja | mért (scratch) | PR2–PR7; `pr-results.tsv`, `integrity-log-lines.txt`; merge 405 | valós Actions + merge-kísérlet | scratch ≠ Relay |
| (b) a jóváhagyás head- és digest-kötött, a megfelelőség külön ítélet | mért (scratch) | PR12 APPROVED_UPDATE, PR13 DENY, PR12 új fej DENY | valódi tulajdonosi komment | – |
| A scratch ellenőr az átnevezést (`previous_filename`) nem látja | mért (hiba) | PR20, run 44560294600: `UNCHANGED` | valós futás | az éles ellenőrnek mindkét útvonalat vizsgálnia kell (R1) |
| Azonos nevű hamis job nem fedi el a valódi hibát | mért | PR4: `integrity` failure+success → blocked, 405 | check-runs + merge | fordított eset (hiányzó valódi, jelen lévő hamis) nem mért |
| `pull_request_target` a default ág definícióját használja | mért | PR18, run 44556567050 | marker-változat | – |
| `strict: false` mellett a stale zöld PR mergelhető | mért (rés) | PR10 merged, policy-szigorítás után | valós merge | – |
| `strict: true` újraértékelést ad | mért | PR11: 405, update-branch után failure | valós futás | költség |
| (d) a PR saját tokenjével megkerülhető | mért | PR14/PR15 merged, reviewer `github-actions[bot]` | valós merge | code owner eset oka nem diagnosztizált |
| `can_approve_pull_request_reviews: false` megállítja az önjóváhagyást | mért | PR16: `approve=failure`, nem mergelhető | valós futás | – |
| (c) önmagában nem véd | mért | PR17: megengedő reusable zöld | valós futás | – |
| A Relay-beli proof PR-ek nem használhatnak befagyasztott bázist | mért következmény | PR18 | marker-változat | – |
| A termék-tesztek (B osztály) gyengítése a (b)-vel nem fogható meg | **következtetés, nem mért** | 8b | – | nyitott kockázat |
| A gate-et őrző tesztek és konfigurációk (A osztály) útvonal-alapon védhetők | **mechanizmus mért (scratch PR11), a Relay-listát nem kényszeríti semmi** | 8b, `raw/protected-set-measurement.txt` | git grep a Relay-n; scratch futás | a lista teljessége nem bizonyított |
| A bootstrap sorrendje (workflow előbb, kötelezővé tétel később) | **mechanizmus-szinten mért (scratch), a Relay-ben nem futott** | 9b; PR1, PR7 | scratch | az 1–7 lépés nem bizonyított |
| E2 kompatibilitás (permissions read, Renovate) | **olvasott kód, futással nem mért** | `renovate.yml`, `verify.yml`, `manifest-check.yml` | – | bevezetés előtt proof PR kell |

## 13. Nyitott tulajdonosi döntések és kérések

| Kérdés | Javaslat |
|---|---|
| A kikényszerítés mechanizmusa | (b)+(e)+`can_approve: false` |
| A scratch repók törlése | a három repó (`cic-scratch-212-*`) eldobható; a törléshez nincs `delete_repo` jogosultságom — tulajdonosi lépés; vagy maradhatnak a további mérésekhez |
| Második identitás a fork-PR és a code-owner mérésekhez | kérés |
| A beállítások módosítása (9.) | az implementáció bevezetése után, a megadott sorrendben |
| A `sha_pinning_required` | külön elemzés után |
| Merge-előfeltétel a PR-07-hez | igen (a tulajdonos döntése: #212 → #213 → PR-07) |
