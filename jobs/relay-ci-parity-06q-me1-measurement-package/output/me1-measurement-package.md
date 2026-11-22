# #212 — Az M-E1 mérőcsomag, 1. fázis (06q)

**Státusz: előkészítés (concept), szintetikus adatokkal tesztelt.** A csomagot **nem** szállítottam az X repóra, GitHubon nem futtattam, bizonyítékot nem töltöttem le. A platformviselkedés (az OIDC-token kiadása és lejárata, a JWKS, a claim-nevek, az artifact, a gyanús-workflow jelölés erre a workflow-ra) **dokumentált vagy a 0. fázisban mért más workflow-ra, ennél nem mért**. A csomag megléte ≠ működik a GitHubon; a szintetikus teszt ≠ mért platformviselkedés. **Az M-E1 ítéletét (PASS / FAIL / INCONCLUSIVE) a csomag nem mondja ki**, azt a tényleges mérés utáni jelentés teszi. A tényleges mérés külön tulajdonosi GO, a H1/H2 és a többi M-tétel, a valódi kulcsműveletek és a Relay-implementáció HOLD. K-5: 5/300.

**A mérőeszköz nem hozhat létre új biztonsági kockázatot annak vizsgálata közben** (a #89 review F1 elve): ezért a hiteles (érvényes) OIDC-token a lejáratáig sehol nem hozzáférhető, a bizalmi gyökér a bizonyítéktól elkülönített, és az önbevallás nem írhatja felül az aláírt bizonyítékot.

## 1. Az M-E1 a #81 szerint (hivatkozás, nem módosítás)

Forrás: `exploratory-measurement-plan.md` 3.E és 2.2; `execution-decision-package.md` K-7, 5.1.

| Mező | Tartalom (a #81-ből) |
|---|---|
| **H** | a platform olyan bizonyítékot ad egy futásról, amely hitelesen köti a futást a workflow-definícióhoz (útvonal, commit) és az azonossághoz, a tárgy szerzője által nem befolyásolható módon, és a kibocsátótól függetlenül ellenőrizhető |
| **Elrendezés** | leltár: a futás metaadatai, a platform által aláírt azonosító (tokenek és állítások), igazolások, ha a platform kínál; mindegyiknél: ki hozza létre, a PR szerzője befolyásolhatja-e, a független fél a kibocsátó közreműködése nélkül ellenőrizheti-e, mit köt (útvonal, SHA, azonosság, kísérlet) |
| **PK** | (U) szintetikus: két ismerten különböző bizonyíték-rekord, az összehasonlító észleli az eltérést; (J) két ismerten azonos rekordnál nem jelez eltérést. A kontroll nem függ attól, hogy a platform bizonyítéka valóban eltér-e |
| **Negatív** | S (más futás bizonyítéka), R (régi futás bizonyítéka), P (a PR szerzője módosítja) |
| **Ítélet** | PASS = van legalább egy bizonyíték-típus, amely a (workflow, commit, azonosság, futás) négyest hitelesen köti, a PR szerzője nem módosíthatja, és független fél ellenőrizheti; FAIL = csak a kibocsátó önbevallása elérhető; INCONCLUSIVE = az ellenőrizhetőség nem döntött el |

## 2. Mit tartalmaz a csomag

| Fájl | Szerep | Blob-SHA (`git hash-object`) |
|---|---|---|
| `payload/.github/workflows/me1-evidence.yml` | a mérendő futás: csak `workflow_dispatch`; (a) a workflow **önbevallása** (`context.json`), (b) a **platform által aláírt OIDC-token** (`aud=me1-evidence`). **A token csak a lejárata után kerül a feltöltendő könyvtárba** (lásd lent); `id-token: write` csak **job-szinten**, a workflow-szint `contents: read` | `873f9f38584db88e7bc93e118cb087b2adf35883` |
| `check-me1-workflow.py` | fail-closed ellenőrző: a teljes dokumentum és a teljes `run` test egyezik a jóváhagyott szöveggel | — |
| `harness/test-me1-body.py` | a `run` test szárazfutása hamis `curl`/`date`/`sleep`-pel: a token csak a lejárat után íródik ki, minden használhatatlan esetben fail-closed | — |
| `harness/fetch-me1.sh` | a bizonyíték gyűjtése: egy jóváhagyott kísérlet, a futás aktuális kísérlete a gyűjtés előtt és után ellenőrzött, az artifact azonosító és időablak alapján választott, `manifest.json`. **Nem tölti le a kibocsátó kulcsait** | — |
| `harness/fetch-jwks.sh` | a **bizalmi gyökér**: a kibocsátó nyilvános kulcsai **egyetlen új fájlba, a bizonyítékcsomagon kívülre** | — |
| `harness/read-me1.py` | az olvasó: a tokent **offline, tiszta Python RS256-tal** ellenőrzi a **külön megadott** (`--trusted-jwks`) kulcsokkal, és összeveti az API-metaadattal; PK-mód (`--pk`) | — |
| `harness/test-fetch-me1.py` | a gyűjtő lánc és a `fetch-jwks.sh` mockolt `gh`/`curl`-lel (nincs hálózat) | — |

### 2.1 A token kezelése (review F1)

Az OIDC-token **a lejáratáig hitelesítési adat**. A saját közönség (`aud=me1-evidence`) **önmagában nem zárja ki**, hogy más szolgáltatás, amely ezt a közönséget és a kibocsátót elfogadja, felhasználja; ezt a csomag **nem állítja**. Ezért a token **nem kerül nyilvános artifactba érvényes állapotban**:
1. a token csak shell-változóban él; a naplóba, fájlba nem íródik;
2. a `run` test kiolvassa a token `exp` állítását; ha az **hiányzik, nem szám, vagy 600 s-nál messzebb van**, a lépés **fail-closed** (nincs token, nincs feltöltés);
3. a lépés `exp + 120 s`-ig várakozik, majd **újra ellenőrzi az órát**; csak ha a lejárat + 120 s biztosan elmúlt, írja a tokent a feltöltendő könyvtárba;
4. az olvasó a **szerver által rögzített** artifact-létrehozási időt (`created_at`) is ellenőrzi: legalább `exp + 60 s` (óra-eltérés tartaléka); különben `NOT-MET`;
5. a `jq -e` és a JWT-alak ellenőrzése kizárja a `null`/üres/nem-JWT választ (a `test -s` ezt nem tette meg).

**Mit nem tudok állítani:** hogy a GitHub token-élettartama ≤ 600 s (nem mért; ha hosszabb, a workflow fail-closed leáll, és a mérés `NOT-READ`), és hogy a futtató órája és a szerveridő eltérése < 60 s (a szerveridő-ellenőrzés az olvasóban ezt külön igazolja). A teljes JWT megőrzése a független aláírás-ellenőrzés miatt szükséges (a review szerint is).

### 2.2 A bizalmi gyökér elkülönítése (review F2)

A kibocsátó nyilvános kulcsai **nem** a bizonyítékcsomagban vannak. A `manifest.json` digestje önmagában nem hitelesíti egy kulcs eredetét, ha a kulcs ugyanabban a cserélhető csomagban ül. Ezért a `read-me1.py` a kulcsokat a `--trusted-jwks FILE` kapcsolóból veszi, és **elutasítja** (`NOT-MET`), ha a fájl a bizonyítékkönyvtáron belül van. **A megbízható letöltés feltételei** (dokumentált, a tulajdonos felelőssége): a tulajdonos gépén, TLS-en, **közvetlenül a kibocsátótól**, a futás **után** (kulcsforgatás), a bizonyítékkönyvtáron **kívüli** fájlba (`fetch-jwks.sh`); a fájl SHA-256-ja a kiolvasás kimenetében szerepel. **Amit ez nem véd:** a tulajdonos gépének és a TLS-útvonalnak a sértetlenségét.

### 2.3 Az olvasó csatornái, és mit szabad következtetni (review F3, F4)

| Bizonyíték | Ki hozza létre | Ellenőrizhetőség | Az olvasó vizsgálata |
|---|---|---|---|
| API-futásmetaadat | a platform, kívülről olvasva | aláíratlan | útvonal+ref, head, futás, kísérlet; egyezik a manifesttel |
| OIDC-token állításai | a platform, **aláírva** | a kibocsátó nyilvános kulcsaival, a futás közreműködése nélkül | aláírás, `iss`, `aud`, kiadás ideje a kísérlet időablakán belül, **lejárat a publikálás előtt**, `repository`, `sha`, `run_id`, `run_attempt`, `workflow_ref`, `ref`, `sub`, `event_name` egyezik az API-metaadattal |
| `job_workflow_ref` | a platform (főleg újrahasznosítható workflow-nál dokumentált) | — | **nem kötelező**: hiánya `NOTE`, nem hibás kötés; ha jelen van, egyeznie kell |
| `context.json` | **maga a workflow**: önbevallás | a szerző befolyásolja | csak összevetés; az eltérés **`NOTE`**, nem érvényteleníti az aláírt bizonyítékot |
| P (PR-szerző befolyása) | — | pull_request-futás bizonyítéka kell | **NOT-READ** ebben a csomagban |

| Esemény | Megengedett következtetés (az olvasó kimenete) |
|---|---|
| az OIDC-token vagy a bizalmi gyökér nem olvasható | OIDC evidence **NOT-READ** (`INCOMPLETE (not read)`) |
| az aláírás, a kibocsátó, a közönség, az idő vagy a kötés hibás | OIDC evidence **NOT-MET** (`EVIDENCE NOT BOUND (NOT MET)`) |
| az OIDC-kötés igazolt | **EVIDENCE BOUND** |
| P nincs vizsgálva | **P NOT-READ** (`EVIDENCE BOUND, P NOT READ` a legerősebb ebben a csomagban) |
| a teljes bizonyíték-inventár hiányos | **M-E1 INCONCLUSIVE** (a jelentés mondja ki, nem az eszköz) |

**Egy token megszerezhetetlenségéből nem következik `FAIL`**, amíg a többi bizonyíték-típus vizsgálata nincs lezárva. A `FAIL` (csak önbevallás elérhető) a jelentés ítélete, a teljes inventár alapján.

## 3. A csomag ellenőrzése (helyi, szintetikus adatokkal)

```bash
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/check-me1-workflow.py \
  --selftest jobs/relay-ci-parity-06q-me1-measurement-package/output/payload/.github/workflows
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/test-me1-body.py
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/read-me1.py --selftest
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/test-fetch-me1.py
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/read-me1.py --pk
```

- **`check-me1-workflow.py`: 41 beültetett eltérés**, mind elutasítva, **a tiltott-token lista kikapcsolva is**. Köztük az F1-hez: várakozás nélküli feltöltés, a várakozás lejárta ellenőrzésének hiánya, kisebb biztonsági tartalék, a várakozás korlátjának hiánya, a token a várakozás előtt kiírva, `jq` `-e` nélkül, JWT-alak-ellenőrzés nélkül, `exp` típusának ellenőrzése nélkül, a token naplóba írása három módon, az `id-token` workflow-szinten.
- **`test-me1-body.py`: 14 ellenőrzés** (a `run` test szárazfutása): normál eset (`exp + 120 - most` várakozás, utána kiírás); az óra nem halad (nincs token); túl távoli lejárat (nincs várakozás, nincs token); régen lejárt token (nincs várakozás, kiírás); hiányzó, nem szám és `null` `exp`; a `curl` `null`, hiányzó, nem-JSON, nem-JWT és üres válasza (mind fail-closed, nincs token); a token nem jelenik meg a lépés kimenetében. **Tud bukni:** a várakozás nélküli törzsre 1 eset bukik.
- **`read-me1.py --selftest`: 96 ellenőrzés**, köztük az RS256-ellenőrző maga (érvényes aláírás elfogadva; más üzenet, más kulcs, megbillentett bit, csonkolt aláírás, apró modulus elutasítva); a PK (U)/(J); az S/R negatívok; minden állítás-eltérés; a token és a megbízható JWKS hibái; **F2:** a bizalmi gyökér hiánya `INCOMPLETE`, nem létező, nem JSON, kulcs nélküli, más kibocsátó kulcsát tartalmazó és **a bizonyítékcsomagon belüli** kulcsfájl elutasítva; a token, a kulcs és a manifest **teljes, belsőleg konzisztens cseréje** a csomagon belül elutasítva (a tulajdonos kulcsai döntenek), akkor is, ha a támadó kulcsfájlját adják meg bizalmi gyökérként; **F3:** az önbevallás eltérése és a nem-objektum önbevallás `NOTE`, az aláírt bizonyíték áll; **F4:** hiányzó `job_workflow_ref` `NOTE`, hibás `job_workflow_ref` `NOT-MET`; **F1:** a publikálás a lejárat előtt, 30 s-mal utána (tartalék: 60 s) elutasítva, pontosan `exp + 60 s` elfogadva; a manifest-író; a parancssori belépési pontok **alfolyamat-hívással**; az `--selftest` önállósága és a rekurzió-védő.
- **A teszt tud bukni:** (a) az aláírás-ellenőrzést `True`-ra cserélve a selftest 5 ponton elbukik; (b) a bizalmi gyökér elkülönítését kikapcsolva 1 ponton (a külön erre épített sor); (c) a lejárat-a-publikálás-előtt ellenőrzést kikapcsolva 2 ponton; mind ideiglenes másolaton, kilépési kód 1.
- **`test-fetch-me1.py`: 29 ellenőrzés**: az elfogadott 1. és 2. kísérlet végig a kiolvasásig (a bizonyítékkönyvtárban **nincs kulcsfájl**), 12 elutasítási ág, két eset, ahol a bizonyíték letöltődik, de **az olvasó utasítja el** (más kibocsátó kulcsai mint bizalmi gyökér; más commit állításai), és a `fetch-jwks.sh` (helyes JWKS megtartva; a `curl` hibája, nem JSON, nincs `keys`, üres `keys`, lista objektum helyett, meglévő kimeneti fájl: elutasítva).
- **Mért (helyi, szintetikus):** minden fenti, 2026-11-22. **Nem mért:** a valódi GitHub-token élettartama és formátuma, a `iat`/`exp` kezelése, a valódi JWKS (`kid`, kulcsforgatás), a `workflow_ref`/`sub` értékek pontos alakja, az artifact-letöltés és az időablakos kiválasztás a valódi API-n, a jelölés. **Az olvasó elvárásai a dokumentált claim-nevekre épülnek**; ha a valódi token mást ad, a javítás új, review-köteles commit, és az M-E1 addig nem értékelhető.

## 4. Tulajdonosi szállítás és futás (külön GO-k, a PR mergelése után)

A védett `main` miatt a fájl **PR-ral** kerül az X repóra (a 4.6b mintájára); a PR-on a `lab-gate` a `lab-gate-pr.yml`-től jelenik meg. A szállító szkript a jóváhagyott factory merge-commitból klónoz és a blobot ellenőrzi:

```bash
# deliver-me1.sh — owner-run, APPROVED_FACTORY_SHA = the merge commit of this PR (set after the merge)
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
FACTORY=/home/sinkog/sync/claude_factory/CIC/workdir/jobs/relay-ci-parity-01-inventory/workspace/cic-factory
: "${APPROVED_FACTORY_SHA:?}"
P=jobs/relay-ci-parity-06q-me1-measurement-package/output/payload/.github/workflows/me1-evidence.yml
WORK=$(mktemp -d)
git clone "git@github.com:$ORG/$X.git" "$WORK/repo"
git -C "$WORK/repo" checkout -b phase1-me1-evidence
git -C "$FACTORY" show "$APPROVED_FACTORY_SHA:$P" > "$WORK/repo/.github/workflows/me1-evidence.yml"
[ "$(git hash-object "$WORK/repo/.github/workflows/me1-evidence.yml")" = 873f9f38584db88e7bc93e118cb087b2adf35883 ] || { echo "blob mismatch" >&2; exit 1; }
git -C "$WORK/repo" add .github/workflows/me1-evidence.yml
git -C "$WORK/repo" commit -m "phase 1: me1-evidence workflow (M-E1 evidence inventory)"
echo "branch commit: $(git -C "$WORK/repo" rev-parse HEAD)"
```

A szkript **nem pushol**; a push, a PR és a merge a tulajdonosé (K-8). Utána olvasott ellenőrzés (én): a PR `headRefOid`, a `lab-gate` check, a blob a merge-commiton.

**A futás és a kiolvasás (külön GO):**

```bash
gh workflow run me1-evidence.yml --repo "$ORG/$X" --ref main
# a futás kb. 12 percig is tarthat: a workflow megvárja a token lejáratát, mielőtt a tokent kiírná (2.1)
# ha a futás action_required (a gyanús-workflow jelölés, P3): a jóváhagyás a tulajdonos döntése a weben, után a 2. kísérlet
bash .../harness/fetch-me1.sh RUN_ID ~/.cache/ci-lab/me1-raw/RUN_ID APPROVED_HEAD ATTEMPT
bash .../harness/fetch-jwks.sh ~/.cache/ci-lab/me1-trust/jwks-RUN_ID.json      # a bizonyítékkönyvtáron KÍVÜL
python3 -I .../harness/read-me1.py ~/.cache/ci-lab/me1-raw/RUN_ID --trusted-jwks ~/.cache/ci-lab/me1-trust/jwks-RUN_ID.json \
  --expect-repo "$ORG/$X" --expect-run-id RUN_ID --expect-attempt ATTEMPT --expect-head-sha APPROVED_HEAD
```

**A gyanús-workflow jelölés (P3) előre betervezve:** a 0. fázisban a GitHub a PK-workflow-t jelölte meg és jóváhagyásig nem futtatta (az ok nem ismert). Ez a workflow `id-token: write`-ot kér, és tokent kér le: **újabb visszatartás valószínű, de nem mért**. A jóváhagyás a tulajdonos döntése, a fájl áttekintése után; ugyanazon futásazonosítón 2. kísérlet jön létre. A gyűjtő és az olvasó az 1. és 2. kísérletet kezeli (utóbbit csak tartott 1. kísérlet után).

**Az S és R negatívok valódi bizonyítéka második futást (és az R-hez új commitot) igényel**; a P pull_request-futást. Ezek **nem részei** ennek a csomagnak, külön GO-t és (a P-hez) külön csomagot igényelnek. Az M-E1 ítélete addig legfeljebb `INCONCLUSIVE`.

## 5. K-5 előszámítás (becslés, nem mért) — a hatókör és a külön GO-hoz kötött lépések szétválasztva

| Lépés | GO-státusz | Kísérlet |
|---|---|---|
| **Ez a PR (előkészítés, szintetikus tesztek)** | **megvan** (a tulajdonos 2026-11-22-i GO-ja) | **0** (nem fut a labor X repón) |
| Szállítás: a PR `lab-gate-pr` futása és a post-merge `lab-gate-bootstrap` futás | külön GO | 2 |
| 1. mérési futás (a jelölés miatt legfeljebb 2 kísérlet) | külön GO | ≤ 2 |
| 2. mérési futás az S negatívhoz (legfeljebb 2 kísérlet) | külön GO | ≤ 2 |
| **A külön GO-hoz kötött lépések összesen** | | **≤ 6**, azaz a jelenlegi 5 mellett **legfeljebb ≈ 11 / 300** |

A kísérletenkénti számlálás a tulajdonos szabálya. **Leállási küszöbök (#82 4. szakasz):** ha egy tétel 3 egymás utáni futása magyarázatlanul eltérő eredményt ad, vagy a futások száma eléri a 250-et megoldatlan INCONCLUSIVE-okkal, a mérést szüneteltetni és a tulajdonost értesíteni kell. Sikertelen vagy hiányos eredménynél **nincs automatikus újrafuttatás**.

## 6. Nyers bizonyíték kezelése

A nyers bizonyíték a tulajdonos gépén marad (`~/.cache/ci-lab/me1-raw/RUN_ID`), a bizalmi gyökér külön (`~/.cache/ci-lab/me1-trust/`). Nekem a fail-closed átvizsgálás és a tulajdonosi átnézés után adható át; **kulcs vagy valódi hitelesítő adat nincs benne**. A bizonyítékban lévő OIDC-token a publikálás idején **már lejárt** (2.1), ezért nem hitelesítési adat; a tulajdonos ettől függetlenül döntheti el, hogy a teljes tokent vagy csak az állításait (payload) küldi.

## 7. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A workflow-fájl pontosan a jóváhagyott szöveg; az `id-token: write` az egyetlen jogosultság-kiterjesztés, job-szinten | mért (helyi) | `check-me1-workflow.py` `OK`; blob `873f9f38584db88e7bc93e118cb087b2adf35883` | `--selftest` | az ellenőrző a helyi fájlt méri; a GitHub elfogadása nem mért |
| Az ellenőrző tud bukni | mért (helyi) | 41 beültetett eltérés elutasítva, tiltott-token lista nélkül is | `--selftest` | a mutáns-készlet nem teljes |
| A token csak a lejárat után kerül a feltöltendő könyvtárba, és hiba esetén fail-closed | mért (helyi, hamis `curl`/`date`/`sleep`-pel) | `test-me1-body.py` 14/14; a várakozás nélküli törzsre 1 eset bukik | `python3 -I test-me1-body.py` | **a valódi token-élettartam és az óra nem mért**; ha az élettartam > 600 s, a futás fail-closed leáll |
| A hiteles token a lejáratig nem érhető el nyilvános artifactban | **következtetés a workflow szerkezetéből, nem mért a GitHubon** | a 2.1 pontok; az olvasó szerveridő-ellenőrzése | a futás utáni kiolvasás (`provably expired` sor) | az óra-eltérés és az élettartam nem mért; a saját közönség ezt **nem** védi |
| Az RS256-ellenőrző jól dönt | mért (helyi, szintetikus kulcsokkal) | érvényes elfogadva; 5 hibás eset elutasítva | `read-me1.py --selftest` | a valódi JWKS és `kid` kezelés nem mért |
| A bizalmi gyökér elkülönített, a csomagon belüli kulcsfájl elutasított, a teljes belső csere elutasított | mért (helyi, szintetikus) | 96/96; a szétválasztás kikapcsolva 1 ponton bukik | `--selftest`, mutáció | a tulajdonos gépe és a TLS-útvonal sértetlensége feltétel, nem védett |
| Az önbevallás eltérése nem érvényteleníti az aláírt bizonyítékot; a `job_workflow_ref` hiánya nem hibás kötés | mért (helyi, szintetikus) | `NOTE` esetek | `--selftest` | a valódi token claim-készlete nem mért |
| Az olvasó az állításokat az API-metaadattal veti össze és tud bukni | mért (helyi, szintetikus) | 96/96; kikapcsolt aláírás-ellenőrzés 5, kikapcsolt lejárat-ellenőrzés 2 ponton bukik | `--selftest`, mutáció | a valódi token állításainak pontos alakja nem mért |
| A PK: az összehasonlító észleli a beültetett eltérést és nem riaszt azonosnál | mért (helyi, szintetikus) | `--pk`, `--selftest` | `read-me1.py --pk` | — |
| A gyűjtő lánc az 1. és 2. kísérletet kezeli, és minden elutasítási ágban fail-closed; a kulcsok nem kerülnek a bizonyítékba | mért (mockolt) | `test-fetch-me1.py` 29/29 | `python3 -I test-fetch-me1.py` | a valódi API-válasz mezői nem mértek |
| A platform hiteles, független bizonyítékot ad a futásról (M-E1 H) | **nem állítom** | — | a tényleges mérés (külön GO) | az M-E1 ítélete a futás utáni jelentés tárgya |
| A PR-szerző nem befolyásolhatja a bizonyítékot (P) | **nem állítom, NOT-READ** | — | pull_request-futás bizonyítéka (külön csomag, külön GO) | — |
| A GitHub nem jelöli gyanúsnak az `id-token: write` workflow-t | **nem állítom** | — | a futás | a visszatartás valószínű; a K-5 számlálás ezt tartalmazza |
| Az X repó vagy az éles szervezet módosult | nem | nincs ilyen parancs; csak helyi fájlok | `git log` | — |

## 8. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét, és nem állítja, hogy a platform hiteles, független futási bizonyítékot ad.
- **Nem állítja,** hogy a saját közönség kizárja a token más szolgáltatásban történő felhasználását, és hogy a token élettartama ≤ 600 s.
- **Nem állítja,** hogy a GitHub elfogadja vagy a leírt módon futtatja a workflow-t; ezt csak a tulajdonosi PR és a futás mutatja meg.
- **Nem tartalmaz** futást, szállítást, bizonyíték-letöltést, H1/H2-t, M-A…M-D tételt, M-E2/E3/E5-öt, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem fedi** az artifact-attestációt (`attestations: write`, külön action): a #81 szerint a „platform által kínált igazolások" közé tartozik; **külön nyitott tétel marad**, felvétele külön döntés.
- **Nem módosítja** a #81–#88 tartalmát és a K-1–K-8 ajánlásokat.
