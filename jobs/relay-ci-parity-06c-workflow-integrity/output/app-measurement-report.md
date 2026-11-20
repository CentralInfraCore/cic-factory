# #212 — A GitHub App alapú mérések összesített jelentése (scratch)

**Státusz: mérési jelentés, tartalmi review-ra előkészítve. Nem normatív, nem implementációs jóváhagyás.**
A jelentés a `cic-scratch-212-public` eldobható repository-n végzett méréseket foglalja össze. Az eredmények **scratch környezetben mértek**, nem éles (Relay) környezetben igazolt védelmek. A Relay-ben nem változott semmi.

Az #73-ban rögzített addendum (`addendum-github-app-and-22-cases.md`) hat bizonyítandó állítására (4/a–4/f, c2, e0–e4) ez a jelentés ad mért választ, ahol mérni tudtunk. Ahol nem, ott a „Nyitott" szakasz sorolja fel.

---

## 1. Három önálló, normatív követelmény

A mérések három, egymást **nem helyettesítő** követelményt támasztottak alá. Mindháromhoz van reprodukálható, valós GitHub-futással mért ellenpélda.

| Követelmény | Mért ellenpélda | Szükséges védelem |
|---|---|---|
| **Kibocsátó hitelessége** (ki állítja, hogy az ellenőrzés lefutott) | A1, E3s (és a korábbi R3, PR21: az Actions-only kötésnél hamis zöld `clean`) | A required check az App identitásához (`integration_id` 5852604) kötve |
| **Döntés érvényessége** (a döntés érvényes-e a mostani környezetben) | C2b, C2c (`strict: false` mellett a régi zöld elfogadott BASE- és policy-változás után) | `strict_required_status_checks_policy: true` + állapotkötés (HEAD, BASE, policy digest a döntésben) |
| **Bemenet teljessége** (a döntés alapjául szolgáló adat teljes-e) | E3 / PR37 (3002 fájlos PR, a védett fájl kimaradt a listából, hamis SUCCESS) | Teljességvizsgálat, hiányos bemenetnél fail-closed (`INCOMPLETE_CHANGESET`) |

Elv: *egy hiteles bizonyíték nem feltétlenül érvényes bizonyíték; az érvényesség a bizonyíték és az aktuális döntési környezet viszonya.* A három követelmény külön-külön szükséges; egyik sem pótolja a másikat (például az App-identitás nem véd a hiányos bemenet ellen, a `strict` nem véd a hamis kibocsátó ellen).

**A `strict: true` korlátja (nem mért):** nem bizonyított a változatlan HEAD és változatlan BASE mellett bekövetkező külső policy-változás kezelése (például a policy forrása nem a BASE ág). Ez nyitott korlát, lásd 7. szakasz.

---

## 2. Mérési környezet

- **Repository:** `CentralInfraCore/cic-scratch-212-public` (eldobható, publikus). Éles kulcsot és éles repository-beállítást nem érintett.
- **App:** `cic-integrity-scratch`, App ID `5852604`, telepítve a szervezetben `repository_selection: selected`. Jogosultságok: `checks: write`, `contents: read`, `metadata: read`, `pull_requests: read`. Webhook és esemény nincs (`events: []`).
- **Hitelesítő anyag:** a privát kulcs az `integrity-app` environment secretje (`APP_PRIVATE_KEY`), az `APP_ID` ugyanott változó. A deployment branch szabály csak a `main` ágat engedi. A kulcsot nem láttuk, nem kerül commitba (a raw evidence-ben titokszűrés lefutott).
- **Workflow:** `.github/workflows/integrity-app.yml` (`raw/app/integrity-app.yml.txt`), `pull_request_target`, a `main` ágról fut, a PR-t adatként olvassa. Az action-ök commit-SHA-ra pinelve: `actions/checkout` v4.3.1 → `34e114876b0b11c390a56381ad16ebd13914f8d5`, `actions/create-github-app-token` v1.12.0 → `d72941d797fd3113feb6b93fd0dec494b13a2547` (ez utóbbi commit GitHub-aláírása nem ellenőrzött, `verified=false`; `raw/app/pins-resolved.txt`).
- **Checker:** `scripts/integrity.py` a scratch main-en; a végleges változata `raw/app/integrity-final.py.txt`. Kulcshelyek: `load_changeset` (`scripts/integrity.py:45`), `protected_changes` (`scripts/integrity.py:80`), az `INCOMPLETE_CHANGESET` deny (`scripts/integrity.py:111`).
- **Ruleset (eredeti, a mérés kezdetén):** `verify` és `integrity`, mindkettő `integration_id` 15368 (GitHub Actions), `strict_required_status_checks_policy: true`. A méréshez az `integrity` az `5852604`-hez lett kötve; a mérés végén visszaállítva.
- **Main alakulása a mérés alatt:** `7c8f247` (App-workflow) → `88571a8` (PR33 merge, BASE-mozgás) → `ee44cae` (policy-változás, `extra/` védett) → `1abfd1f`, `cf23467` (csonkolás-javítás és tesztek).

**Bizonyíték típusa** a következőkben: **Actions** = tényleges GitHub Actions-futás a scratch repón (futásazonosító és head megadva); **API** = a GitHub API válasza; **lokális** = a gépen futtatott teszt vagy mock.

---

## 3. Mérési eredmények

### 3.1 Kibocsátó hitelessége és alap működés

| Eset | PR (head) | Bizonyíték | Eredmény |
|---|---|---|---|
| App-token és App-identitású check-run | PR23 (`8a3c2be`), run 44797660531 | Actions | PASS: `integrity` check-run `app=cic-integrity-scratch` (`app_id 5852604`); ugyanazon a fejen külön `integrity` az Actions-identitással (`15368`) |
| Pozitív kontroll, kötés előtt | PR24 (`1f6d0b7bec8f715d029144a20634978c0dd9a611`) | Actions | App-check `success`, `clean` |
| Pozitív kontroll, aktív kötéssel | PR31 (`4abce8da8bf4a1e8fcbc8d23c65bbc5238268abe`) | Actions | App-check `success`, `clean` |
| **A1:** hamis, mindig zöld Actions `integrity`, App-check hiányzik | PR25 (`d724dffe4ff78e53013faef7cf41c0428304e2a7`) | Actions | PASS: `blocked` (a PR21-nél ugyanez `clean` volt az Actions-only kötésnél) |
| **A2:** App-tokenhiba (`APP_ID` törölve) + hamis zöld Actions | PR26 (`9daa113a5e5c3a223a89187b630d30da8d762f46`), run 44799144815 | Actions | PASS: `Input required and not supplied: app-id`, App-check nincs, `blocked` |
| **E3s:** hamis commit status `integrity=success`, App-check hiányzik | PR36 (`6fbad1cbeb4b1eb89cd410c90fa5f690b1e5c04b`) | Actions + API | PASS: a status (`github-actions[bot]`) nem elégíti ki az App-kötést, `blocked` |

**A1/A2 korlát:** a „blocked" ok-okozati állítása a kontrasztra épül (jelenléttel `clean`, hiányában `blocked`); más szabály izolált hatását nem mértük. Az A2 „App elérhetetlen" tokenhibát jelent, **nem** az installáció felfüggesztését.

### 3.2 Döntési szabályok (A3–A6)

| Eset | PR (head) | Bizonyíték | Eredmény |
|---|---|---|---|
| **A3:** védett `scripts/check.sh` módosítás jóváhagyás nélkül | PR27 (`b5c0be85009e251a09bcf8f92528b9ce6b949509`) | Actions | PASS: App-check `failure`, `blocked`; közben a `verify` `success` |
| **A4:** jóváhagyott, megfelelő `ci.yml` módosítás | PR29 (`982590f871b4b609eb0e77b4d122c26dd3f00bcd`), run 44800424847 | Actions | PASS: `APPROVED_UPDATE`, App-check `success`, `clean` |
| **A5:** jóváhagyott, nem megfelelő módosítás (feltételes `verify`) | PR30 (`9ac8ce1b2c9bc2959469a28e4bc8f17df9377f0f`), run 44800431929 | Actions | PASS: `DENY: conformance: job 'verify' is conditional`, `blocked` |
| **A6:** átnevezés védett útvonalról védetlenre | PR28 (`2738649fe16af988979762c2e673dbe9e4a1e3d6`) | Actions | PASS: `DENY`, a log mindkét nevet mutatja; **a `verify` is bukott**, így az App-check önálló hatása itt nem izolált |

A jóváhagyó kommenteket a tulajdonos írta (`raw/app/post-approvals-a4-a5.sh.txt`); a digest a checker logjával egyezett (`raw/app/checker-digests.txt`). A4-nél az újrafuttatás (re-run) a jóváhagyás után ugyanazon a fejen történt; a korábbi bukott check-run a `filter=all` lekérdezéssel látszik (19:15:35Z `failure`, 19:17:12Z `success`), az alapértelmezett lekérdezés a legújabbat mutatja. **Megfigyelés:** a legutóbbi check-run határozza meg a merge-állapotot.

**Az átnevezési hiba külön lezárása:** a scratch checker korábban nem vizsgálta a `previous_filename`-et (PR20, `UNCHANGED`); a javított változat a PR22-n `DENY`-t adott (run 44777884857, head `3bf1a408088f83844914ac06e05bbbd23001cd89`), lásd `raw/scratch/rename-regression/`.

### 3.3 C2: a korábbi zöld érvényessége

A zöld App-check létezett, az App elérhetetlen volt (`APP_ID` törölve), és külön változott a HEAD, a BASE, illetve a policy. Mindkét `strict` értéknél mértünk.

| Változás | PR (head) | `strict: true` | `strict: false` |
|---|---|---|---|
| **c2a: új HEAD** | PR31 → `0e235e629c4803be1bed949ab3af4005dc89de6d` | `behind` (a BASE mozgása is blokkol, nem izolált) | **`blocked`** (izolált: új fejen nincs App-check) |
| **c2b: BASE-mozgás** (PR33 merge, `88571a8`) | PR32 (`d01f1223f810e8c9c71376464a15b7cdcc5f2882`) | `behind` | **`clean`**: a régi base-hez kötött zöld elfogadott |
| **c2c: policy-változás** (`extra/` védett, `ee44cae`) | PR34 (`6ef2de95f79639bb76e1824cb18fc8f0dc750fe8`) | `behind` | **`clean`**: a PR a már védett `extra/c2c.md`-t módosítja, mégsem értékelte újra a GitHub |
| **`strict: true` + `update-branch`** | PR34 → `9b1b884e55f463f1385864c23d4a3cdc15b58ab7` | `blocked`: új fejen nincs App-check, `app-integrity` `failure` | — |

Bizonyíték típusa: API (`mergeable_state`) és Actions. **Következtetés a mért konfigurációkról:** az App-kötés a hamis kibocsátót kizárja, a döntés időbeli érvényességét viszont **nem** védi; ehhez a `strict: true` kell. A Relay inventáriuma szerint ott a `strict_required_status_checks_policy` jelenleg `false`; a Relay-beli viselkedést itt nem mértük.

### 3.4 Bizalmi izoláció (E-sorozat)

| Eset | PR (head) | Bizonyíték | Eredmény |
|---|---|---|---|
| **E0:** minimális jogosultság | — | API | A telepítés jogosultságai pontosan a négy kért. Túlnyújtási kísérletet **nem** végeztünk |
| **E1/E2:** a PR nem éri el a kulcsot/tokent | PR35 (`5692db813b3fab2b3edcf2aa54ceb19e87739b69`), run 44805260679 | Actions | PASS: az environment-es job `Branch "refs/pull/35/merge" is not allowed to deploy to integrity-app`; az environment nélküli job `SECRET-ABSENT` |
| **E3:** hostile fájlnevek + védett változás | PR38 (`b37ae5940fddbb33ac70b8148e302f34771d2610`) | Actions | PASS: DENY, `blocked` |
| **E3:** policy-parser hibája | — | lokális | PASS: hibás vagy hiányzó `policy.json` esetén `exit=1` (Actions-futás nem készült) |
| **E4:** a PR átírja a privilegizált workflow-t; hostile cím és ágnév | PR39 (`fb760e430a8d69bc5e6b03cc62068b173793c17f`) | Actions | PASS: a base workflow futott (DENY, `failure`); az injekció nem hajtódott végre (`INJECT`, `uid=` nincs a logban), `blocked` |
| **E3: nagy PR** | PR37 (`2ef1bc10faa5b1b987e1574766ad980e4839118d`) | Actions | **FAIL (eredeti hiba), lásd 4. szakasz** |

---

## 4. Az eredeti hiba, a javítás és a mérési határ

### 4.1 Eredeti hiba (PR37): hamis SUCCESS hiányos bemenettel

A PR 3002 fájlt módosít: 3001 védetlen `notes/big/…` fájlt és a védett `scripts/check.sh`-t (az ábécé szerint utolsó). A pull request `changed_files` értéke 3002; a files API legfeljebb 3000 fájlt ad vissza, a védett fájl kimaradt (0 találat a `scripts/` alatt). A checker nem hasonlította össze a két számot:

- `UNCHANGED: no protected path touched`, App-check `success`, `mergeable_state` `clean`.

Ez hiteles kibocsátótól származó, a bemenet hiánya miatt téves zöld. A PR-t nem merge-eltük. Az eredeti állapot változatlan bizonyítéka: `raw/app/pr37-original/` (check-run JSON, a PR állapota a javítás előtt), `raw/app/pr37-huge.txt`.

### 4.2 Javított állapot: `INCOMPLETE_CHANGESET`

A javított checker (`scripts/integrity.py:45`) fail-closed, ha:
- az API-hívás vagy egy lapozás hibázik;
- a PR feje az ellenőrzés közben elmozdult;
- a `changed_files` hiányzik vagy érvénytelen;
- a `changed_files` eléri a 3000-es listázási limitet;
- a lapozás nem fejeződik be;
- a listázott fájlok száma eltér a `changed_files` értékétől.

A diagnosztikai kód: `DENY: INCOMPLETE_CHANGESET: …` (`scripts/integrity.py:111`).

### 4.3 Mérési határ

**2999 fájl elfogadható, 3000-től elutasítás** (a 3000-es limitet a checker szándékosan hiányosnak tekinti, mert a listázás nem bizonyítja a teljességet).

| Eset | PR (head) | Bizonyíték | Eredmény |
|---|---|---|---|
| 2999 védetlen fájl | PR40 (`59a4c7dd0060a5a36774bbce826a91b383888293`), run 44806259114 | Actions | SUCCESS (`UNCHANGED`), `clean` |
| 3000 fájl | PR41 (`0da7ee1b6be1ebdd924c675c2bdbcb65f6e8f6dd`), run 44806274404 | Actions | DENY (`INCOMPLETE_CHANGESET: changed_files=3000 …`), `blocked` |
| 3001 fájl | PR42 (`8e2124db1b02b2d4c14889391cd6f70d2003a193`), run 44806287658 | Actions | DENY, `blocked` |
| 3002 fájl, kimaradó védett fájl | PR37 (újranyitva), run 44806310552 | Actions | DENY: App-check `failure` (a `mergeable_state` `behind`, mert a BASE közben elmozdult) |
| Normál PR (5 fájl) | PR43 (`de5d34bc653b58a4512ba9e84367f6834567e611`), run 44806297463 | Actions | SUCCESS, `clean` |
| `changed_files` és listázott elemszám eltérése | — | **lokális mock** | DENY |
| Lapozási hiba, API-hiba, elmozdult head, hiányzó számláló | — | **lokális mock** | DENY |

Lokális regresszió: 20 teszt, mind sikeres (`raw/app/test_integrity-final.py.txt`: 7 az átnevezésre, 13 a teljességre). A régi viselkedésen a 13 teljességi tesztből 8 bukik és 1 hibát ad. Az eltérés-, lapozási és API-hiba esete **csak lokálisan mért**, Actions-ben természetes módon nem előidézhető.

A PR37 újranyitása (zárás, majd nyitás) új eseményt indított a javított base-sel. A korábbi, hamis `success` check-run a `filter=all` lekérdezéssel látszik.

---

## 5. Megfigyelések, amelyek nem követelmények

- Az `app-integrity` Actions-job állapota (`success`) **nem** az integritás-döntés; azt az App-check hordozza. A job szándékosan nem bukik a DENY-ra, ezért a job nem lehet required check.
- A legutóbbi App-check határozza meg a merge-állapotot: egy újrafuttatás felülírhat egy korábbi bukást (A4). Ez a jóváhagyás utáni újraértékelés mechanizmusa, de azt is jelenti, hogy az újrafuttatást kiváltó jogosultság döntési jogosultság; ezt nem értékeltük.
- Az `app-integrity` workflow nem használ cache-t vagy artifactot (**átvizsgálással, nem méréssel** állítjuk).

---

## 6. Visszaállítás

- **Konfiguráció: megtörtént és ellenőrzött.** A ruleset az eredeti állapotban (`verify` és `integrity` is `15368`, `strict: true`); a mentett és a visszaállított konfiguráció az `updated_at` kivételével azonos (`raw/app/ruleset-orig-for-binding.json.txt`, `ruleset-final.json.txt`). Az eredeti `integrity` workflow újra engedélyezve, az `integrity-app` engedélyezve (`workflow-states-final.txt`). Az `APP_ID` változó és az `APP_PRIVATE_KEY` secret jelen van.
- **A repository tartalma szándékosan NEM lett visszaállítva.** A scratch main tartalmaz a méréshez szükséges változásokat: a `policy.json` (benne az `extra/`), a javított `scripts/integrity.py`, a tesztek és az `integrity-app.yml`. A mérési PR-ok nyitva maradnak bizonyítékként (kivéve a PR33-at, amelyet a BASE mozgatásához merge-eltünk). A scratch repók megmaradnak.
- A kulcs visszavonása és az App törlése a mérések lezárása után tulajdonosi lépés.

---

## 7. Nyitott, még nem mért esetek

Egyik sem tekinthető igazoltnak:

1. **Az App-kiesés teljes köre:** az installáció felfüggesztése (ehhez App-JWT, vagyis a privát kulcs kellene) külön eset a tokenhibától. Mért csak a tokenhiba.
2. **Fork-PR és második identitás.**
3. **E0 túlnyújtási kísérlet:** a tényleges token-hatókör nincs próbálva a nem engedélyezett műveletekre.
4. **E3 további bemenetek:** újsor-tartalmú fájlnév és a digest-ütköztetés; szimbolikus link a védett útvonalon jóváhagyás mellett; a policy-parser hibája Actions-ben.
5. **A teljességi hibák Actions-beli esete** (eltérés, lapozási hiba, API-hiba): csak lokális mock.
6. **Time-of-check/time-of-use:** a head-elmozdulás ellenőrzése csak az ellenőrzés elején történik; az ellenőrzés és a merge közötti időablakra nem mértünk.
7. **A `strict: true` korlátja:** a változatlan HEAD és BASE mellett bekövetkező külső policy-változás kezelése.
8. **Az újrafuttatás jogosultsága** (5. szakasz) mint döntési jogosultság.
9. **A `blocked` állapot szabályonkénti izolálása** (A1–A3, A6: a PR több szabályon is bukhat; a kontraszt-érvelés erős, de nem izolált mérés).
10. **Relay-specifikus esetek:** GATE/BOOTSTRAP/`object_model.py`/action manipulációk, Renovate/permissions kompatibilitás, a bootstrap-eljárás hét lépése, a védett halmaz teljessége, job-törlés és `if`/`needs` manipulációk, a Relay-beli `strict` viselkedés.
11. **A code-owner szabály korábbi, diagnosztizálatlan viselkedése** (a (d) kísérletben), és a repo-szintű `default_workflow_permissions` eltérése.

---

## 8. Mi következik (javaslat a review-nak, nem döntés)

A review feladata annak meghatározása, hogy a három követelményt hogyan emeljük át a CIC normatív architektúrájába. A mérések alapján a javaslat tárgya:

- App-identitáshoz kötött kötelező integritás-check;
- `strict_required_status_checks_policy: true`;
- a HEAD, BASE és policy digest rögzítése a döntési evidence-ben;
- fail-closed működés hiányzó vagy hiányos bemenetnél (`INCOMPLETE_CHANGESET`).

**HOLD (változatlan):** Relay-implementáció, éles konfiguráció módosítása, az #212 lezárása, scratch repók törlése, e jelentés merge-elése review előtt.

---

## 9. Evidence jegyzék

`raw/app/` (a pontos útvonalak: `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/`):

- Eredeti hiba: `pr37-original/`, `pr37-huge.txt`, `e3-e4-results.txt`.
- Javítás: `integrity-final.py.txt`, `test_integrity-final.py.txt`, `fix-install-commits.txt`, `ruleset-before-fix-deploy.json.txt`, `ruleset-after-fix-deploy.json.txt`.
- Regresszió: `regression-prs.txt`, `regression-results.txt`.
- C2: `c2-*.txt`, `c2a-*.txt`, `c2c-*.txt`.
- A/E-sorozat: `pr23*`–`pr36*`, `pr38-names.txt`, `pr39-e4.txt`, `e1-*.txt`, `e3-parser-local.txt`.
- Ruleset-mentések: `ruleset-*.json.txt`; végállapot: `ruleset-final.json.txt`, `workflow-states-final.txt`.
- Workflow és próbák: `integrity-app.yml.txt`, `e1-probe.yml.txt`, `status-probe.yml.txt`, `negative-pr-set.md`, `pins-resolved.txt`.

A korábbi, a #72–#74 PR-okban merge-elt rész: `workflow-integrity-report.md`, `addendum-github-app-and-22-cases.md`, `raw/scratch/`, `raw/scratch/rename-regression/`.
