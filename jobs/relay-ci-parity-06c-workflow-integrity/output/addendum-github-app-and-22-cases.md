# #212 addendum — az R3 mérése, a dedikált GitHub App irány és a 22 elfogadási eset egységesítése

Kapcsolódik: `workflow-integrity-report.md` (cic-factory #72, `996d297`). **Ez az addendum nem módosítja a jóváhagyott jelentést; ahol eltér (az esetszám 20 → 22, az R3 státusza), ez az addendum a mérvadó.**
**Hatókör:** tervezés és mérés-előkészítés. **Nincs Relay-implementáció, nincs Relay repository-beállítás módosítás, nincs App létrehozva.** Az App-ot a tulajdonos hozza létre (lásd 5.); a méréseket első körben kizárólag a scratch repón végezzük.

## 1. Az R3 mért eredménye

Mérés (scratch PR21, head `eb7db727edebd7397536fc227223e6b6dca323c2`, `raw/r3/r3-missing-real-fake-green.txt`): a valódi `integrity` workflow-t a scratch repón **adminként kikapcsoltam**, a PR pedig egy azonos nevű, zöld `integrity` jobot szállított (új workflow-fájlban). Eredmény: `integrity=success` (app 15368), `verify=success`, **`mergeable_state=clean`**. A workflow-t utána visszakapcsoltam (`active`).

**Következtetés (mért + következtetés elkülönítve):**
- **Mért:** ha a valódi ellenőr nem fut, egy azonos nevű Actions-job a kötelező check-et kielégíti, mert a ruleset a check-et **névvel és az Actions integration ID-jával (15368)** köti, nem workflow-val.
- **Mért:** a valódi ellenőr kimaradását a mérésben **adminisztrátori művelet** (a workflow kikapcsolása) idézte elő; ebben a kísérletben ez volt az egyetlen kimaradási ok.
- **Következtetés, NEM mért:** hogy a PR **önmaga** nem tudja előidézni a valódi ellenőr kimaradását. A `pull_request_target` base-beli definíciója ezt valószínűsíti, de ennél erősebb állítás, mint amit a bizonyíték alátámaszt; **külön vizsgálandó** (pl. a PR által befolyásolható futtatási feltételek, a workflow-fájl állapota, kapacitás- és időzítési hatások, fork-eset). Amíg nem mért, **nem tekinthető mért tulajdonságnak**.
- **Nem mért:** a valódi ellenőr kimaradásának egyéb okai (fork-PR jóváhagyási kapu, futtató-kimaradás, a workflow automatikus kikapcsolása, Actions-szolgáltatás kimaradás). Ezek nem zárhatók ki.
- **Következtetés:** a (b) mechanizmus védelme ahhoz a feltételhez kötött, hogy a valódi ellenőrzés elindul; ez **nem kikényszerített tulajdonság**. A review szerint (cic-factory #72 újrareview, R3) ez az architektúra jelenlegi formájában nem elfogadható → **új architekturális döntés**: a tulajdonosi döntés a **dedikált GitHub App** irány (2. lehetőség).

## 2. Az elv

> Az ellenőrzött objektum nem rendelkezhet azzal a jogosultsággal, amellyel a saját ellenőrzésének sikerességét igazolja.

A GitHub-ruleset `required_status_checks.integration_id`-ja egy **App azonosítója**. A mai kötelező checkek mind 15368 (GitHub Actions) alatt vannak, ezért **bármely** Actions-job, amely a PR-ből fut, ugyanazt a nevet előállíthatja. Ha a kötelező `integrity` check-et egy **külön App** közli (saját `integration_id`), az Actions-job (15368) azt a kontextust nem elégítheti ki. Ez **egy független ellenőrzési bizalmi tartomány**.

## 3. A GitHub App bizalmi és jogosultsági modellje (terv)

**Szerepek:**

| Szereplő | Mit tehet | Mit nem |
|---|---|---|
| a vizsgált PR (szerző) | kódot, workflow-t, teszteket módosít; saját `pull_request` workflow-ja a repo-szintű secreteket **elérheti** (same-repo PR) | az App check-jét közvetlenül közölni; az App credential-jét olvasni (ez bizonyítandó, 4/e1–e4) |
| az App | check run-t közöl (`Checks: write`), olvassa a PR-t és a BASE-t (`Pull requests: read`, `Contents: read`, `Metadata: read`) | tartalmat írni, merge-elni, review-t adni, Actions-t indítani, secreteket olvasni |
| a tulajdonos | az App létrehozása/telepítése, a ruleset (kötelező check + `integration_id`), a jóváhagyás kommentek | – |
| a base-ből futó, App-ot hajtó komponens | a policy-t a BASE-ből olvassa, a PR-t adatként kezeli, az eredményt App-identitással közli | PR-kódot checkoutolni vagy futtatni |

**Minimális App-jogosultságok (javasolt):** `Checks: write`, `Pull requests: read`, `Contents: read`, `Metadata: read` (kötelező, csak olvasható). **Nem:** `Contents: write`, `Pull requests: write`, `Statuses`, `Actions`, `Administration`, `Secrets`, `Workflows`. Webhook-feliratkozás: csak ha a (ii) kivitelezést választjuk. Telepítés: **kezdetben kizárólag a scratch repón**, a Relay-re csak a bizonyítás és a külön döntés után.

**A credential védelme (a kritikus pont).** Egy App privát kulcsa Actions-secretként a same-repo PR saját workflow-jából olvasható, ezért a kulcsot a PR-től el kell zárni. Két kivitelezés, **mindkettő nem mért**:

| Kivitelezés | Hogyan véd | Költség / kockázat |
|---|---|---|
| **(i) védett Environment** | a kulcs egy `Environment` secretje, a *deployment branch* szabály csak a default ágat engedi; a `pull_request_target` workflow `GITHUB_REF`-je a base ág, a PR saját `pull_request` workflow-jáé `refs/pull/N/merge` → elvileg nem fér hozzá | a védelem a GitHub environment-szabályán múlik; **mérendő**, hogy a PR `pull_request` workflow-ja tényleg nem éri el (4/e1–e4), és hogy egy PR által módosított workflow sem szerezheti meg |
| **(ii) külső szolgáltatás** | az App webhook-ot egy külön gazdagépen futó szolgáltatás kapja, a kulcs ott van; az Actions-nek nincs köze | üzemeltetés (hosting, rendelkezésre állás, frissítés); a legerősebb elválasztás |

A javaslat: **első körben (i)** a scratch-ben (nincs új infrastruktúra), a (ii)-t értékelni, ha az (i) nem bizonyul elégségesnek.

## 4. Mit kell bizonyítani (scratch, valós futással) — a tulajdonos hat pontja

| # | Állítás | Mérési módszer | Elvárt | Státusz |
|---|---|---|---|---|
| a | A kötelező check az App identitásához kötött | a scratch ruleset `required_status_checks` bejegyzése `integration_id = <App id>`; check-runs listában `app.id` | a kontextus csak az App-tól származó check-kel teljesül | **nem mért** |
| b | Azonos nevű Actions-check nem helyettesíti az App check-jét | az R3-forgatókönyv (PR21 mintájára): az App check hiányzik, a PR azonos nevű Actions-jobot szállít | `mergeable_state` blokkolt, merge 405 | **nem mért** (az Actions-only ellenpróba mért: clean, 1.) |
| c | App-elérhetetlenség esetén a merge blokkolt | az App telepítésének ideiglenes felfüggesztése vagy az App-ot hajtó workflow kikapcsolása | a hiányzó kötelező check blokkol (a hiányzó check blokkolása mért: PR7) | **nem mért** az App-pal |
| c2 | **Már létező sikeres App-check, az App elérhetetlenné válik, és közben megváltozik a döntés alapjául szolgáló állapot** | 1. az App check zöld egy adott HEAD/BASE/policy hármasra; 2. az App-ot hajtó komponens elérhetetlenné tétele (az App telepítésének felfüggesztése); 3. az állapot megváltoztatása három külön esetben: (i) új push a PR-re, (ii) a BASE (`main`) mozgása, (iii) a policy változása a `main`-en; 4. merge-kísérlet mindháromnál | a korábbi zöld App-check **nem használható fel** az új állapotban: mindhárom esetben a merge blokkolt, amíg az App új, az új állapothoz kötött ítéletet nem közöl; a `strict: true` hatása **külön mérve** (a BASE/policy-mozgás `strict` mellett az update-branch után új HEAD-et kényszerít, ami új App-check nélkül hiányzó kötelező check; **ez következtetés, nem mért**) | **nem mért**; a `strict: true` önmagában **nem tekinthető teljes bizonyítéknak** |
| d | A döntés az egzakt HEAD, BASE és policy verzióhoz kötött | az App check `head_sha` = PR-fej, a közölt rekord (`external_id`/output) a BASE, a policy és az ellenőr sha256 értékét tartalmazza; párhuzamos push a futás közben | fail-closed, ha a HEAD/BASE a döntés előtt változott | **nem mért** |
| e0 | Az App jogosultságai minimálisak | a telepítési jogosultságok listája (a GitHub App beállításai és az installation `permissions` API-mezője) | csak a 3. pontban felsoroltak | **nem mért** |
| e1 | A PR **nem fér hozzá az App privát kulcsához** | egy same-repo PR `pull_request` workflow-ja és egy módosított workflow-ja megpróbálja kiolvasni az environment secretet (környezeti változó, fájl, naplózott érték, `secrets` kontextus, az environment-szabály megkerülése másik ágon/névvel) | az olvasás elutasított / üres minden úton | **nem mért** |
| e2 | A PR **nem fér hozzá az App installation tokenjéhez** | a token csak a base-ből futó, privilegizált jobban jön létre; a PR nem indíthat ilyen jobot saját kóddal; a token nem kerül naplóba, artifactba, cache-be, kimenetbe; PR-ből indított `workflow_run`/artifact-láncolás nincs | a PR-ből a token nem érhető el semmilyen csatornán | **nem mért** |
| e3 | A PR **közvetetten sem veheti rá a megbízható komponenst hamis SUCCESS közlésére** | negatív PR-készlet a PR által befolyásolt adatokra: kártékony fájlnevek (új sor, idézőjel, Unicode, nagyon hosszú útvonal), átnevezés, szimbolikus link, óriási PR (fájllista-csonkolás), a PR címe/ága/leírása a komponens bemeneteként, a policy parser-t célzó bemenet | a komponens minden esetben **fail-closed** (piros/hiányzó check), soha nem SUCCESS | **nem mért** |
| e4 | A PR **nem befolyásolhatja a privilegizált workflow végrehajtott kódját, konfigurációját vagy bemeneteinek értelmezését** | a privilegizált workflow definíciója, a hívott script és a policy a BASE-ből jön; a PR-adat **sosem** kerül shell-be/kifejezés-értékelésbe interpoláltan (környezeti változón át, szigorú validációval); nincs PR-kód checkout; a harmadik fél action-ök SHA-pinelve; nincs megosztott cache/artifact, amelyet a PR írhat és a privilegizált job olvas; **injekciós próba** (a PR címe/ága `$(…)` és `${{ … }}` tartalommal) | a próbák hatástalanok, a futás naplója bizonyítja | **nem mért** |
| | **Elfogadási feltétel (F1):** az e0–e4 **külön-külön** teljesülnie kell. A secret olvashatatlansága (e1) **önmagában nem bizonyítja** a bizalmi tartomány függetlenségét. | | | |
| f | A korábbi jóváhagyás állapotváltozáskor érvényét veszti | új push, BASE-változás, policy-változás a jóváhagyott PR-en | új ítélet szükséges | a (b)-mechanizmusra **mért** (PR12 új fej, PR11 strict), az App-pal **nem mért** |

**Állítás-fegyelem:** amíg a fenti sorok „nem mért"-ek, **kikényszerített App-védelmet nem állítunk**.

## 5. A tulajdonostól kért lépések (a job ezeket nem hajtja végre)

1. **GitHub App létrehozása** a `CentralInfraCore` szervezetben (Settings → Developer settings → GitHub Apps → New), név pl. `cic-integrity-scratch`, **webhook kikapcsolva** ((i) kivitelezés), jogosultságok: `Checks: Read & write`, `Pull requests: Read`, `Contents: Read`, `Metadata: Read`, semmi más; „Where can this App be installed": csak ez a szervezet.
2. **Telepítés** kizárólag a `CentralInfraCore/cic-scratch-212-public` repóra.
3. A **privát kulcs** (PEM) generálása; **a kulcsot nem küldöd ide és nem commitolod**. A scratch-ben egy `Environment` secretjeként állítod be (a tulajdonos futtatja):
   - `gh api -X PUT repos/CentralInfraCore/cic-scratch-212-public/environments/integrity-app` (az environment létrehozása; a *deployment branch* szabályt a `main`-re korlátozva a felületen vagy API-n, lásd mérés 4/e1–e4)
   - `gh secret set APP_PRIVATE_KEY --env integrity-app --repo CentralInfraCore/cic-scratch-212-public < kulcs.pem`
   - a `APP_ID` változó: `gh variable set APP_ID --env integrity-app --repo CentralInfraCore/cic-scratch-212-public --body <id>`
4. Az **App azonosítójának** megadása nekem (az `integration_id` a scratch rulesetbe és a méréshez).
5. A scratch repók **nem törlődnek**; a kulcs a mérés után **visszavonandó**.

Amíg ezek nincsenek meg, **az (a)–(f) mérések nem futnak**; előkészítés: a scratch `integrity` workflow App-os változata (App-token kérés `actions/create-github-app-token` jellegű lépéssel, a check-run közlése a Checks API-n; a lépés SHA-pinelt kell legyen), a negatív PR-készlet, a mérési script.

## 6. Nyitott kérdések (nem mérve)

- App-tulajdon és életciklus (ki felel a kulcsért; rotáció; a kulcs elvesztése esetén a kötelező check hiányzik, azaz minden PR blokkolt: ez **tervezett viselkedés**, de üzemeltetési kockázat, és külön „vészkijárat" kell, ami nem a PR-től függ).
- Az Actions-szolgáltatás kimaradása: az App-ot hajtó workflow ilyenkor nem fut → a kötelező check hiányzik → blokkolt (fail-closed); a (ii) kivitelezés ettől független lenne.
- A **fork-PR** és a **második identitás** mérése továbbra is nyitott (az #72 11. pontja).
- A **védett halmaz és a gate-et őrző tesztek** (8b), a **bootstrap trust** (9b) és az **R1/R2/R4** követelmények változatlanul érvényesek; az App irány a (b) mechanizmus **közlésének** identitását cseréli, a PR-adatként kezelése és a megfelelőségi vizsgálat marad.
- A (b) mechanizmus saját hibái (átnevezés, 21.) változatlanul javítandók.

## 7. A 22 elfogadási eset (egységesített lista; az implementációs job mindegyiket vegye figyelembe)

A jelentés §7 táblázata 22 sort tartalmaz (13 spec-sor + 2 jóváhagyás-határ + 5 integritás-önvédelem + 2 review-ből, az R1/R3), míg a §9b és §10 szövege még „20 proof-esetet" említ: **ez az addendum mérvadó, az implementáció 22 eset**.

| # | Eset | Elvárt | Scratch-mérés (mechanizmus) | Relay / App |
|---|---|---|---|---|
| 1 | referencia-lépés + `check-tools` törlése (#207) | DENY | mért (PR2) | terv |
| 2 | kötelező job törlése | DENY | közvetett (PR7) | terv |
| 3 | azonos nevű üres job | DENY | mért (PR4, valódi piros mellett) | terv; **App: 4/b** |
| 4 | `if`/`continue-on-error`/`needs` | DENY | közvetett; a strukturált vizsgálat R2 | terv |
| 5 | trigger-szűrő szűkítése | DENY | mért (PR7) | terv |
| 6 | `GATE`/`MR_GATE` a PR scriptjére | DENY | analóg mért (PR5) | terv |
| 7 | `BOOTSTRAP` erőltetése | DENY | nem mért | terv |
| 8 | `object_model.py` lecserélése | DENY vagy rés | nem mért | terv |
| 9 | composite action módosítása | DENY | közvetett | terv |
| 10 | új, „kötelezőnek nevezett" workflow | dokumentált / DENY | mért (PR4) | terv |
| 11 | jogos módosítás jóváhagyással | átmegy | mért (PR12) | terv |
| 12 | jóváhagyott, de nem megfelelő módosítás | DENY | mért (PR13) | terv |
| 13 | jóváhagyott módosítás, piros kötelező ellenőrzés | DENY | nem mért | terv |
| 14 | jóváhagyás utáni új push | új jóváhagyás | mért (PR12 új fej) | **App: 4/f** |
| 15 | ellenőrzés eltávolítása a védett halmazon kívül | DENY vagy rés | dokumentált rés, nem reprodukált | 8b |
| 16 | az integritás-ellenőr törlése | DENY | mért (PR3) | terv |
| 17 | az integritás-check nevének hamisítása | DENY | mért (PR4, valódi jelenlétében) | **App: 4/a, 4/b** |
| 18 | korábbi eredmény új HEAD-en | DENY | mért (fej-kötött) | **App: 4/d, 4/c2** |
| 19 | base változása az ellenőrzés után | újraértékelés | mért (PR10 rés `strict: false`; PR11 `strict: true`) | terv; **App: 4/c2** |
| 20 | a bizalmi konfiguráció módosítása | DENY / külön út | mért (PR6) | terv |
| 21 | védett útvonalról védetlenre átnevezés | DENY | **scratch környezetben javítva és regresszióval igazolva**: a hiba mért volt (PR20, `UNCHANGED`); a javított checker (`filename` és `previous_filename` is vizsgálva) a PR22-n DENY-t adott valós Actions-futással (run 44777884857, head `3bf1a408088f83844914ac06e05bbbd23001cd89`); lokális regresszió 7/7, a régi logikán 2 bukik. Relay-ben még nem mért | terv (R1 megvalósítandó) |
| 22 | hiányzó valódi ellenőrzés + azonos nevű zöld check | DENY | **mért: ELFOGADHATATLAN az Actions-only (b)-nél** (PR21, `clean`) | **App: 4/b, 4/c; kötelező, ez dönti el az irányt** |

Az implementációs jobnak mind a 22 eset elvárt eredményét **Relay-beli valós futással** kell igazolnia; a 22. eset az App irányban csak akkor teljesül, ha a 4/b és 4/c mérések az App-pal sikerülnek. Ha **nem** sikerülnek, az új architekturális döntés újra szükséges.

## 8. Mi történik most

| Tétel | Állapot |
|---|---|
| GitHub App bizalmi és jogosultsági modell | ez az addendum (3.) |
| R3 mérés előkészítése | ez az addendum (4., 5.); **a mérés az App létrehozására vár** |
| A 22 eset egységesítése | ez az addendum (7.) |
| 21. eset (átnevezés) scratch-regresszió | **PASS**, lásd 9. |
| Relay implementáció, éles repository-beállítások, #212 lezárása, scratch repók törlése | **HOLD** |

## 9. A 21. eset (átnevezés) scratch-regressziója

**Mért (scratch, `cic-scratch-212-public`):**

- A checker a `filename` mellett a `previous_filename`-et is a védettségvizsgálatba veszi; a jóváhagyási digest a teljes átmozgatást (régi és új név) köti.
- Lokális regressziós teszt: 7/7 sikeres. A régi egyező-logikán két teszt bukik (a védettből védetlenre átnevezés, és hogy a digest mindkét nevet köti).
- Telepítés a scratch main-re: a ruleset mentése, átmeneti kikapcsolása, a checker (c399c07) és a tesztek (a249a6d) feltöltése, a ruleset visszaállítása; a mentett és a visszaállított konfiguráció az `updated_at` kivételével azonos. Csak a scratch repót érintette.
- PR22 (`scripts/check.sh` → `notes/check.sh`, head `3bf1a408088f83844914ac06e05bbbd23001cd89`, base `a249a6d7f8224100fbae495ecd86eddb2897a77a`): a `integrity` futás (44777884857) `DENY: protected paths changed without a head- and digest-bound approval`; a `ci` futás (44777884772) és a `verify` check bukott; a `self-approve` futás (44777884832) sikeres, és `github-actions[bot]` APPROVED reviewt adott.
- A három futás lezárulása után a PR `mergeable_state` értéke `blocked` (`mergeable: true`), a head változatlan.

**Nem mért / korlát:**

- Hogy a `blocked` állapotot melyik szabály okozza külön-külön, izoláltan nem bizonyított; a bot-review a merge-et nem oldotta fel, miközben a required check-ek (`integrity`, `verify`) buktak.
- A `ci` bukásának oka (a `scripts/check.sh` a PR-ban átkerült) következtetés, a logja nem lett vizsgálva.
- A javítás Relay-beli megfelelője és a Relay-beli futás nem készült el: az implementáció HOLD.

Evidence: `raw/scratch/rename-regression/` (ruleset előtte/utána, telepítési commitok, PR22 adatai, integrity log-sorok, végső mergeable-állapot, a javított `integrity.py.txt` és a regressziós teszt `.txt` formában).
