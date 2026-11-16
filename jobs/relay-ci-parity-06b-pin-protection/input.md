# relay-ci-parity-06b-pin-protection — a mérőeszköz-pinek védelme az ellenőrzött PR-rel szemben (CIC_Relay #195)

## Kontextus

A `CentralInfraCore/CIC_Relay` **#195** issue (másolat: `ref/issue-195-body.md`) a #169 PR-06 (Relay #191, mergelve: `c18fef2d15bd503bb7c0861bf9dd2e7d80a2da85`) utáni, **külön kötelező fejlesztés**. A PR-06 a mérőeszközöket a `.measurement-tools.json`-ban pinelte, és minden mérő job fail closed (`scripts/quality_gate.py check-tools --surface …`, `object_model.py verify --mode quality`). A jelentés (`ref/pr06-report.md`) a korlátot kimondta, a PR-06 review pedig külön, tulajdonosilag jóváhagyott feladatnak jelölte.

**A rés.** A pin-fájl és benne a `surfaces` (melyik mérő felülethez mely eszközök tartoznak) **ugyanabban a fában él, amelyet a kapuk olvasnak**. Az ellenőrzött PR ugyanabban a változásban módosíthatja a pint és az eszközbeállítást (workflow `setup-go`, telepítési lépés), így **maga határozza meg az elfogadási referenciáját**. Ma csak a `scripts/gremlins_gate.py` és a `.mutation-baseline.json` védett a bázis-commitból (`baseline-guard`, `mutation-pr.yml`: a script a `git show "$BASE_SHA:…"`-ból fut). A pin-fájl nem. Egy olyan ellenőrzés, amelynek referenciáját az ellenőrzött változás átírhatja, csak azt bizonyítja, hogy a változás önmagával konzisztens (`ref/issue-195-body.md`).

A sorozat helye (`ref/issue-169-body.md`): a PR-07 (FULL/DIFF integráció, nightly hibajelentés), PR-08 (evidence record), PR-09 (publikáció) **mind a pin-fájlt olvassák**. A tulajdonos döntése: **előbb a #195, aztán a PR-07.**

**Ez a spec külön felülvizsgálatra készül; a job indítása a spec review-ja és mergelése után történik.** A job implementációt ad (CIC_Relay scriptek, tesztek, a meglévő `baseline-guard` kiterjesztése; PR a CIC_Relay felé), **csak az alábbi hatókörben**. **Új küszöb, toolchain-csere, tesztkihagyás és termékkód-módosítás nincs.**

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`, `limits` fogalmakra. Ha a KB nem elérhető (a PR-06-ban az `Invalid request parameters` hibát adta), mondd ki a jelentésben; a repó fájljai a forrás.
2. Olvasd el: `ref/issue-195-body.md`, `ref/pr06-report.md` (3. szakasz: A.8 és a korlátok; 5c.), `ref/owner-decisions-pr06-2026-11-15.md`, `ref/issue-169-body.md` („Development rules”, „Acceptance criteria”).
3. Friss klón: `$WORKSPACE/CIC_Relay/` (ág `main`). **Rögzítsd a commit-azonosítót**; a `main` tartalmazza a `c18fef2`-t, különben állj meg. **Ha a `workspace/` alatt már van `CIC_Relay*` mappa, ne azt használd** (egy ismeretlen háttérfolyamat `.yaml` kísérőfájlokat generál a `.py`/`.go` fájlok mellé, és a klónt piszkossá teszi; a `yamllint` ezek miatt bukott): új klón, **explicit útvonalas `git add`, soha nem `-A`**, a `git status --short | wc -l` rögzítve a klónozás után, a mérések előtt és a végén.
4. **Kiindulási állapot (olvasd, ne higgy a specnek):** `scripts/quality_gate.py` (`check-tools`, `load_tool_pins`, `tool_pin_findings`), `.measurement-tools.json`, `scripts/baseline_guard.py`, `.github/workflows/mutation-pr.yml` (`baseline-guard` job, `BASE_SHA`), és a **minden** `check-tools` hívás helye: `grep -rn "check-tools" .github scripts | grep -v "_test.go" | grep -v "/test_"` (a Go- és Python-tesztfájlok kizárva). Rögzítsd a hívóhelyek számát és eseményeit (`pull_request`, `push`, `schedule`, `workflow_dispatch`): a bázis-commit csak PR-nél van; a többi eseménynél a referencia **a vizsgált commit maga**, és ezt a jelentésnek ki kell mondania.
5. **Reachability:** egy szimbólumról csak akkor mondd, hogy production-hívott/bekötött, ha megvan a hívási út `file:line`-nal (`grep -rn <szimbólum> --include=*.py --include=*.yml --include=*.go . | grep -v "_test.go" | grep -v "/test_"`). A `szimbólum létezik` ≠ `a workflow hívja`.
6. **Mérési környezet:** a PR-06 pinelt környezete (`.measurement-tools.json`); helyi futásnál konténer `--user "$(id -u):$(id -g)"`-rel, cache a `~/.cache/relay-ci-parity-06b/` alatt (nem a 16 GB-os `/tmp`-n).

## Státusz-definíciók (kötelező ellenőrzési móddal)

- **implemented** = a védelem **valódi GitHub Actions futásban** érvényesül: a check a PR-en lefut, a referenciát a bázis-commitból olvassa (parancs és nyers kimenet a naplóból), és egy **szándékosan manipuláló PR piros**. A script és a teszt megléte nem elég.
- **scaffold** = kódban van, de nincs workflow-hívás vagy feltételesen kikerülhető (`if` ág, `continue-on-error`, `needs` nélküli job).
- **concept** = csak leírás.
- Egy állítás **nem mért**, ha nem futtattad; ezt a jelentésben ki kell mondani.

## Feladat

**A. A referencia a bázis-commitból (acceptance 1).** A `.measurement-tools.json` (`tools` és `surfaces`) **a pull request bázis-commitjából** olvasódjon, ne az ellenőrzött fából — ugyanazzal a mintával, mint a `baseline-guard`. Minden mérő felület (a #195 és a PR-06 jelentés szerinti `check-tools --surface …` hívások, az `object-evidence` verifier) ezt használja. A pin-fájl **a PR-ben szereplő változata nem referencia**, hanem **vizsgált tárgy**: eltérése a bázistól külön, látható eredmény. Push/schedule eseménynél a referencia a vizsgált commit; ezt a jelentés rögzíti, nem csendes.

**B. Szándékos pin-frissítés útja (acceptance 2).** Legyen **külön, látható, tulajdonosi jóváhagyású** út, hogy egy jogos eszközfrissítés (pl. Go-verzióemelés) lehetséges maradjon: a pin-módosítás a PR-ben **megállítja** a zöld utat (piros vagy „owner approval required” állapot), amíg a jóváhagyás nincs meg. **A jóváhagyás mechanizmusa tulajdonosi döntés** (lásd lent); a job a döntött mechanizmust implementálja, nem választ helyette. Egy tool-bump és egy manipuláció ugyanabban az eredményben **nem lehet megkülönböztethetetlen**.

**C. Negatív bizonyíték (acceptance 3).** **Szándékosan hibás, nem mergelendő draft PR**, amely a pin-fájlt **és** az eszközbeállítást együtt módosítja úgy, hogy a PR-ben konzisztens (pl. a pin és a `setup-go` verzió együtt változik), és amelyet az új védelem **elutasít**. Mellé **pozitív kontroll** (a változatlan pin zöld) és **ellenpróba** (a védelem nélküli állapoton ugyanez a PR zöld lenne: R-teszt). Mérd le, hogy a PR-06 #193 esete (a pin eltér a beállítástól) továbbra is a saját okából piros.

**D. A check eredménye rögzíti a referenciát (acceptance 4).** A kimenet és a (PR-08-ig csak szöveges) rekord mondja ki: **melyik referencia-commitot** és **melyik digestet** (a pin-fájl SHA-256-ja) használta. Hiányzó vagy olvashatatlan referencia **fail closed**, nem csendes visszaesés a fabeli fájlra.

**E. Korlátok kimondása.** Állapítsd meg és mondd ki, **mit nem véd** a megoldás. Különösen: a `pull_request` eseménynél a **workflow-fájl maga is az ellenőrzött PR-ből jön**, így a PR a `check-tools` lépést ki is törölheti vagy más argumentumokkal hívhatja; a `baseline-guard` ugyanezt a korlátot hordozza (a script a bázisból fut, a hívása a PR workflow-jában van). Mérd le (izolált másolaton vagy negatív proof PR-rel), hogy ez ma fennáll-e, és **ne állítsd, hogy a pin-védelem a manipulációt egészében megszünteti**. A teljes megoldás (required workflow / repository ruleset / `pull_request_target` a bázis workflow-jával) **repó-beállítás és biztonsági döntés**, nem ennek a jobnak a hatóköre: rögzítsd mint ajánlott következő lépést.

## Nem része a jobnak (ne csináld)

- Új küszöb, új minőségi kapu az eddigi `baseline-guard` kiterjesztésén túl; az eddigi blokkoló kapuk gyengítése; toolchain-csere; tesztkihagyás.
- A `cargo-mutants` és `cargo-llvm-cov` **pinelése** (a `taiki-e/install-action` pinje): **külön tétel**, ne keverd ide (a #195 is külön említi).
- Repó-beállítás (branch protection, ruleset, CODEOWNERS) **módosítása**: ez tulajdonosi döntés és beállítás; a job javasolhat, nem állíthat.
- A PR-07..PR-10 tartalma, a `syn`-leltár, az öt `#[no_mangle]` azonosító.
- Termékkód (`cmd/`, `core/`, `ffi/` nem-teszt kód) módosítása.
- **Ne írj olyan állítást, hogy a pin „védett”, ha csak a fabeli fájl egyezését ellenőrzöd.** Illeszkedő hash ≠ eredet.

## Negatív példák (ne így)

- A pin-fájl hash-ét a **PR fájljából** számolod és azt nevezed referenciának: ez a mostani rés.
- A védelem csak akkor zöld, ha a pin **nem változik**, de a megváltozott pin nem jelent hibát: ez nem védelem, hanem a változás hiányának jelzése.
- A negatív PR olyan, amelyet bármely mostani check is elutasítana (pl. a pin eltér a setuptól): ez nem bizonyítja az új védelmet.
- A bázis-commit olvasása hibánál csendben a fabeli fájlra esik vissza.

## Negatív tesztek és pozitív kontrollok

Minden esethez: **származtatás**, **elvárt eredmény**, **kapott**, **pozitív kontroll**, **ellenpróba** (a védelem nélküli állapoton a manipuláció átmegy). Kötelező esetek (legalább): (1) a pin módosítása a setuppal együtt → elutasítva; (2) csak a `surfaces` szűkítése (egy eszköz kivétele egy felületről) → elutasítva; (3) csak egy eszköz verziójának emelése jóváhagyás nélkül → megállít; (4) jóváhagyott frissítés → átmegy és látható; (5) hiányzó/olvashatatlan bázis-referencia → fail closed; (6) a pin-fájl törlése → elutasítva; (7) push/schedule esemény → a referencia a vizsgált commit, kimondva a kimenetben.

## Mérési korlátok (a jelentésben kimondandó)

- Egy sikeres helyi futás ≠ hogy a CI manipulációnál pirosra vált; ahol ezt állítod, **GitHub Actions** futás igazolja (run id, headSha).
- A `schedule`/`push` események workflow-jai PR-ben nem futnak (`mutation.yml`, `nightly.yml` check-lépései): ezek **csak szöveggel és egységteszttel** fedettek, ha nem tudod valóban futtatni; mondd ki.
- A korlát (E) mérése: a mérés eredménye, nem következtetés.
- Lemezhely, idő és költség rögzítve; a klón tisztasága előtte/alatta/utána.

## Elfogadási kritériumok

1. A pin és a `surfaces` **bázis-commitból** olvasódik minden `check-tools` és `object-evidence` hívásnál (a hívóhelyek listája és a változatlanul maradó esetek indoklása).
2. A pin-módosítás **látható és megállít**; a jóváhagyott frissítés útja létezik és tesztelt.
3. A manipuláló PR **valós GitHub Actions futáson piros** (negatív proof PR), pozitív kontrollal és ellenpróbával.
4. A check kimenete rögzíti a **referencia-commitot és a digestet**; hiányzó referencia fail closed.
5. A korlát (E) **mért és kimondott**; a jelentés nem állít többet, mint amit a védelem tesz.
6. A meglévő blokkoló kapuk, küszöbök, baseline-ok és a `scripts/gremlins_gate.py` változatlanok (diffben ellenőrizve); nincs tesztkihagyás, nincs termékkód a diffben, **nincs repó-beállítás-módosítás**.
7. Valódi GitHub Actions run id a PR headSha-jára (zöld) és a negatív proof PR-re (piros); a `nem mért` itt **nem lezárás**.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented; a workflow létezése ≠ hogy fut; a kapu ≠ hogy bukni tud; **egy negatív teszt ≠ hogy a kapu bukni tud, amíg a pozitív kontroll és az ellenpróba nincs mellette**.
- **Illeszkedő hash ≠ eredet vagy jogosultság.**
- Exit code 0 ≠ sikeres mérés; üres kimenet ≠ nulla mérés.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként; a hívóhely olvasása ≠ futás.
- A script a bázisból fut ≠ hogy a **hívása** is a bázisból jön.

## Verifikáció és bizonyítás

- Minden állításhoz a parancs és a nyers kimenet; **reachability**: minden bekötött védelemhez a workflow-hívás `file:line`-nal és a futás naplója.
- **A CI-hibákat vizsgáld ki, ne tulajdonítsd környezetnek.**
- **Aláírás:** a cic-factory `main`-re közben mozdulhat; az ág a `main` tetején álljon a push előtt; a rebase érvényteleníti az aláírást, az `--amend` a régi blokkot tartja: a kimenetet **frissen, új üzenettel aláírt commitként** készítsd el. A Relay-repó csak merge-commitot enged; a `main` mozgásakor a PR-ágba merge-eld be a `main`-t (nem rebase).
- A negatív proof PR evidence-ét a jelentés rögzítse **a lezárás és az ág törlése előtt**.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-06b-pin-protection/output/`

- `output/pin-protection-report.md` — magyarul: vizsgált commitok; a klón tisztasága; a kiindulási állapot (hívóhelyek táblázata esemény szerint); a megoldás és a **jóváhagyási út**; az esetek táblázata (származtatás, elvárt, kapott, pozitív kontroll, ellenpróba); **a korlát (E) mérése**; **claim-evidence tábla**: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`; nyitott döntések.
- `output/raw/` — nyers kimenetek és scriptek (minden `.sh` első sora `#!/usr/bin/env bash`, ShellCheck `--severity=error`; a helyi útvonalak és felhasználónevek kerüljenek ki).

A CIC_Relay módosítás külön ágon, PR-ként (`--base main`).

## Definition of Done

- A commit-azonosítók, az ág és a klón tisztasága rögzítve.
- A referencia a bázis-commitból olvasódik; a pin-módosítás látható és megállít; a jóváhagyott út tesztelt.
- A manipuláló negatív proof PR valós futáson piros, pozitív kontrollal és ellenpróbával.
- A check rögzíti a referencia-commitot és a digestet; a hiányzó referencia fail closed.
- A korlát (E) mért és kimondott; a repó-beállítás javaslat (nem módosítás) szerepel.
- A meglévő kapuk, küszöbök, baseline-ok változatlanok; nincs termékkód és repó-beállítás a diffben.
- Valós run id (zöld és piros); a `nem mért` nem lezárás.
- A PR leírása pontosan azt állítja, ami mérve van.

## Tulajdonosi döntések (a jobnak nem kell eldöntenie; a jelentés rögzíti, melyik érvényes)

| Kérdés | Opciók | A spec alapértelmezése |
|---|---|---|
| A jóváhagyás mechanizmusa (B) | (a) a pin-módosító PR-t csak a tulajdonos által fogadott, PR-címke/`CODEOWNERS`-jóváhagyás oldja fel; (b) külön, csak a pin-fájlt módosító PR és külön check, a tulajdonos review-jával; (c) a pin-frissítés csak aláírt, a bázisból ellenőrzött commit | a job **a (b)-t javasolja és implementálja csak a kiválasztott opciót**; a döntést a tulajdonos hozza a spec review-jában |
| Workflow-eredetű korlát (E) | repó-beállítás (required workflow / ruleset) most, vagy külön tulajdonosi lépésben | **külön lépés**, a job csak mér és javasol |
| `cargo-mutants` / `cargo-llvm-cov` pin | ebben a jobban vagy külön | **külön** |

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-06b-pin-protection` ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát nem módosítod (a tulajdonos zárja). Az ág a `main` tetején álljon.
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-06b-pin-protection`) friss klónból, PR a `main`-re (`--base main` explicit). Nem mergelsz. A PR **egy** témájú. A szándékosan hibás ágat **ne** mergeld; draft, „DO NOT MERGE” cím, a munkaágra mutatva; a futás rögzítése után zárd le.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR leírásában.
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: jelezd; az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet elutasítja; add oda a pontos parancsot (lehetőleg **egy scriptben**), ne kerüld meg.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**.
