# #212 addendum — az R3 mérése, a dedikált GitHub App irány és a 22 elfogadási eset egységesítése

Kapcsolódik: `workflow-integrity-report.md` (cic-factory #72, `996d297`). **Ez az addendum nem módosítja a jóváhagyott jelentést; ahol eltér (az esetszám 20 → 22, az R3 státusza), ez az addendum a mérvadó.**
**Hatókör:** tervezés és mérés-előkészítés. **Nincs Relay-implementáció, nincs Relay repository-beállítás módosítás, nincs App létrehozva.** Az App-ot a tulajdonos hozza létre (lásd 5.); a méréseket első körben kizárólag a scratch repón végezzük.

## 1. Az R3 mért eredménye

Mérés (scratch PR21, head `eb7db727edebd7397536fc227223e6b6dca323c2`, `raw/r3/r3-missing-real-fake-green.txt`): a valódi `integrity` workflow-t a scratch repón **adminként kikapcsoltam**, a PR pedig egy azonos nevű, zöld `integrity` jobot szállított (új workflow-fájlban). Eredmény: `integrity=success` (app 15368), `verify=success`, **`mergeable_state=clean`**. A workflow-t utána visszakapcsoltam (`active`).

**Következtetés (mért + következtetés elkülönítve):**
- **Mért:** ha a valódi ellenőr nem fut, egy azonos nevű Actions-job a kötelező check-et kielégíti, mert a ruleset a check-et **névvel és az Actions integration ID-jával (15368)** köti, nem workflow-val.
- **Mért:** a PR a valódi ellenőr kimaradását a `pull_request_target` miatt **önmaga nem tudja előidézni**; a mérésben ezt egy admin-lépés okozta.
- **Nem mért:** a valódi ellenőr kimaradásának egyéb okai (fork-PR jóváhagyási kapu, futtató-kimaradás, a workflow automatikus kikapcsolása, Actions-szolgáltatás kimaradás). Ezek nem zárhatók ki.
- **Következtetés:** a (b) mechanizmus védelme ahhoz a feltételhez kötött, hogy a valódi ellenőrzés elindul; ez **nem kikényszerített tulajdonság**. A review szerint (cic-factory #72 újrareview, R3) ez az architektúra jelenlegi formájában nem elfogadható → **új architekturális döntés**: a tulajdonosi döntés a **dedikált GitHub App** irány (2. lehetőség).

## 2. Az elv

> Az ellenőrzött objektum nem rendelkezhet azzal a jogosultsággal, amellyel a saját ellenőrzésének sikerességét igazolja.

A GitHub-ruleset `required_status_checks.integration_id`-ja egy **App azonosítója**. A mai kötelező checkek mind 15368 (GitHub Actions) alatt vannak, ezért **bármely** Actions-job, amely a PR-ből fut, ugyanazt a nevet előállíthatja. Ha a kötelező `integrity` check-et egy **külön App** közli (saját `integration_id`), az Actions-job (15368) azt a kontextust nem elégítheti ki. Ez **egy független ellenőrzési bizalmi tartomány**.

## 3. A GitHub App bizalmi és jogosultsági modellje (terv)

**Szerepek:**

| Szereplő | Mit tehet | Mit nem |
|---|---|---|
| a vizsgált PR (szerző) | kódot, workflow-t, teszteket módosít; saját `pull_request` workflow-ja a repo-szintű secreteket **elérheti** (same-repo PR) | az App check-jét közvetlenül közölni; az App credential-jét olvasni (ez bizonyítandó, 4/e) |
| az App | check run-t közöl (`Checks: write`), olvassa a PR-t és a BASE-t (`Pull requests: read`, `Contents: read`, `Metadata: read`) | tartalmat írni, merge-elni, review-t adni, Actions-t indítani, secreteket olvasni |
| a tulajdonos | az App létrehozása/telepítése, a ruleset (kötelező check + `integration_id`), a jóváhagyás kommentek | – |
| a base-ből futó, App-ot hajtó komponens | a policy-t a BASE-ből olvassa, a PR-t adatként kezeli, az eredményt App-identitással közli | PR-kódot checkoutolni vagy futtatni |

**Minimális App-jogosultságok (javasolt):** `Checks: write`, `Pull requests: read`, `Contents: read`, `Metadata: read` (kötelező, csak olvasható). **Nem:** `Contents: write`, `Pull requests: write`, `Statuses`, `Actions`, `Administration`, `Secrets`, `Workflows`. Webhook-feliratkozás: csak ha a (ii) kivitelezést választjuk. Telepítés: **kezdetben kizárólag a scratch repón**, a Relay-re csak a bizonyítás és a külön döntés után.

**A credential védelme (a kritikus pont).** Egy App privát kulcsa Actions-secretként a same-repo PR saját workflow-jából olvasható, ezért a kulcsot a PR-től el kell zárni. Két kivitelezés, **mindkettő nem mért**:

| Kivitelezés | Hogyan véd | Költség / kockázat |
|---|---|---|
| **(i) védett Environment** | a kulcs egy `Environment` secretje, a *deployment branch* szabály csak a default ágat engedi; a `pull_request_target` workflow `GITHUB_REF`-je a base ág, a PR saját `pull_request` workflow-jáé `refs/pull/N/merge` → elvileg nem fér hozzá | a védelem a GitHub environment-szabályán múlik; **mérendő**, hogy a PR `pull_request` workflow-ja tényleg nem éri el (4/e), és hogy egy PR által módosított workflow sem szerezheti meg |
| **(ii) külső szolgáltatás** | az App webhook-ot egy külön gazdagépen futó szolgáltatás kapja, a kulcs ott van; az Actions-nek nincs köze | üzemeltetés (hosting, rendelkezésre állás, frissítés); a legerősebb elválasztás |

A javaslat: **első körben (i)** a scratch-ben (nincs új infrastruktúra), a (ii)-t értékelni, ha az (i) nem bizonyul elégségesnek.

## 4. Mit kell bizonyítani (scratch, valós futással) — a tulajdonos hat pontja

| # | Állítás | Mérési módszer | Elvárt | Státusz |
|---|---|---|---|---|
| a | A kötelező check az App identitásához kötött | a scratch ruleset `required_status_checks` bejegyzése `integration_id = <App id>`; check-runs listában `app.id` | a kontextus csak az App-tól származó check-kel teljesül | **nem mért** |
| b | Azonos nevű Actions-check nem helyettesíti az App check-jét | az R3-forgatókönyv (PR21 mintájára): az App check hiányzik, a PR azonos nevű Actions-jobot szállít | `mergeable_state` blokkolt, merge 405 | **nem mért** (az Actions-only ellenpróba mért: clean, 1.) |
| c | App-elérhetetlenség esetén a merge blokkolt | az App telepítésének ideiglenes felfüggesztése vagy az App-ot hajtó workflow kikapcsolása | a hiányzó kötelező check blokkol (a hiányzó check blokkolása mért: PR7) | **nem mért** az App-pal |
| d | A döntés az egzakt HEAD, BASE és policy verzióhoz kötött | az App check `head_sha` = PR-fej, a közölt rekord (`external_id`/output) a BASE, a policy és az ellenőr sha256 értékét tartalmazza; párhuzamos push a futás közben | fail-closed, ha a HEAD/BASE a döntés előtt változott | **nem mért** |
| e | Az App jogosultságai minimálisak, a hitelesítő adatok a PR számára hozzáférhetetlenek | a telepítési jogosultságok listája; egy same-repo PR `pull_request` workflow-ja megpróbálja olvasni az environment secretet | az olvasás elutasított / üres | **nem mért** |
| f | A korábbi jóváhagyás állapotváltozáskor érvényét veszti | új push, BASE-változás, policy-változás a jóváhagyott PR-en | új ítélet szükséges | a (b)-mechanizmusra **mért** (PR12 új fej, PR11 strict), az App-pal **nem mért** |

**Állítás-fegyelem:** amíg a fenti sorok „nem mért"-ek, **kikényszerített App-védelmet nem állítunk**.

## 5. A tulajdonostól kért lépések (a job ezeket nem hajtja végre)

1. **GitHub App létrehozása** a `CentralInfraCore` szervezetben (Settings → Developer settings → GitHub Apps → New), név pl. `cic-integrity-scratch`, **webhook kikapcsolva** ((i) kivitelezés), jogosultságok: `Checks: Read & write`, `Pull requests: Read`, `Contents: Read`, `Metadata: Read`, semmi más; „Where can this App be installed": csak ez a szervezet.
2. **Telepítés** kizárólag a `CentralInfraCore/cic-scratch-212-public` repóra.
3. A **privát kulcs** (PEM) generálása; **a kulcsot nem küldöd ide és nem commitolod**. A scratch-ben egy `Environment` secretjeként állítod be (a tulajdonos futtatja):
   - `gh api -X PUT repos/CentralInfraCore/cic-scratch-212-public/environments/integrity-app` (az environment létrehozása; a *deployment branch* szabályt a `main`-re korlátozva a felületen vagy API-n, lásd mérés 4/e)
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
| 18 | korábbi eredmény új HEAD-en | DENY | mért (fej-kötött) | **App: 4/d** |
| 19 | base változása az ellenőrzés után | újraértékelés | mért (PR10 rés `strict: false`; PR11 `strict: true`) | terv |
| 20 | a bizalmi konfiguráció módosítása | DENY / külön út | mért (PR6) | terv |
| 21 | védett útvonalról védetlenre átnevezés | DENY | **mért hiba** (PR20, `UNCHANGED`): javítandó (R1) | terv |
| 22 | hiányzó valódi ellenőrzés + azonos nevű zöld check | DENY | **mért: ELFOGADHATATLAN az Actions-only (b)-nél** (PR21, `clean`) | **App: 4/b, 4/c; kötelező, ez dönti el az irányt** |

Az implementációs jobnak mind a 22 eset elvárt eredményét **Relay-beli valós futással** kell igazolnia; a 22. eset az App irányban csak akkor teljesül, ha a 4/b és 4/c mérések az App-pal sikerülnek. Ha **nem** sikerülnek, az új architekturális döntés újra szükséges.

## 8. Mi történik most

| Tétel | Állapot |
|---|---|
| GitHub App bizalmi és jogosultsági modell | ez az addendum (3.) |
| R3 mérés előkészítése | ez az addendum (4., 5.); **a mérés az App létrehozására vár** |
| A 22 eset egységesítése | ez az addendum (7.) |
| Relay implementáció, éles repository-beállítások, #212 lezárása, scratch repók törlése | **HOLD** |
