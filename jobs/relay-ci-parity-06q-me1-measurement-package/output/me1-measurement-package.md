# #212 — Az M-E1 mérőcsomag, 1. fázis (06q)

**Státusz: előkészítés (concept), szintetikus adatokkal tesztelt.** A csomagot **nem** szállítottam az X repóra, GitHubon nem futtattam, bizonyítékot nem töltöttem le. A platformviselkedés (az OIDC-token kiadása, a JWKS, az artifact, a gyanús-workflow jelölés a `id-token: write` workflow-ra) **dokumentált vagy a 0. fázisban mért más workflow-ra, ennél a workflow-nál nem mért**. A csomag megléte ≠ működik a GitHubon; a szintetikus teszt ≠ mért platformviselkedés. **Az M-E1 ítéletét (PASS / FAIL / INCONCLUSIVE) a csomag nem mondja ki**, azt a tényleges mérés utáni jelentés teszi. A tényleges mérés külön tulajdonosi GO, a H1/H2 és a többi M-tétel, a valódi kulcsműveletek és a Relay-implementáció HOLD. K-5: 5/300.

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
| `payload/.github/workflows/me1-evidence.yml` | a mérendő futás: csak `workflow_dispatch`; (a) a workflow **önbevallása** (`context.json`: repó, futás, kísérlet, SHA, ref, workflow-ref, esemény), (b) a **platform által aláírt OIDC-token** egy saját közönséggel (`aud=me1-evidence`), mindkettő artifactként (megőrzés 1 nap) | `2efdb089541989f328646e46b616e6f00da865ab` |
| `check-me1-workflow.py` | fail-closed ellenőrző: a teljes dokumentum és a teljes `run` test egyezik a jóváhagyott szöveggel | — |
| `harness/fetch-me1.sh` | a bizonyíték gyűjtése: egy jóváhagyott kísérlet, a futás aktuális kísérlete a gyűjtés előtt és után ellenőrzött, az artifact azonosító és időablak alapján választott, az API-metaadat és a **kibocsátó nyilvános kulcsai (JWKS) a tulajdonos gépéről**, a `manifest.json` mindent a futáshoz köt | — |
| `harness/read-me1.py` | az olvasó: a tokent **offline, tiszta Python RS256-tal** ellenőrzi a JWKS ellen, és összeveti az API-metaadattal és az önbevallással; PK-mód (`--pk`) | — |
| `harness/test-fetch-me1.py` | a gyűjtő lánc mockolt `gh`/`curl`-lel (nincs hálózat) | — |

**A `id-token: write` a csomag egyetlen jogosultság-kiterjesztése** (`contents: read` mellett): az OIDC-token kéréséhez szükséges, job-szinten, és az ellenőrző kifejezetten ezt az egyet engedi (a 06m ellenőrzőjének tiltólistáján `id-token` szerepelt, mert a PK-hoz nem kellett). **A review-nak ezt külön mérlegelnie kell.** A token a saját közönségére (`me1-evidence`) szól, rövid életű, nem használható más szolgáltatásnál; az artifactban (nyilvános repó, 1 nap) tárolt token a lejárat után nem használható. A naplóba **nem** kerül (a tiltott-token lista és a beültetett hibák ezt védik).

**Az olvasó csatornái és a kimenete:**

| Bizonyíték | Ki hozza létre | Ellenőrizhetőség | Az olvasó vizsgálata |
|---|---|---|---|
| API-futásmetaadat | a platform, kívülről olvasva | aláíratlan | útvonal+ref, head, futás, kísérlet; egyezik a manifesttel |
| OIDC-token állításai | a platform, **aláírva** | a kibocsátó nyilvános kulcsaival, a futás közreműködése nélkül | aláírás, `iss`, `aud`, kiadás ideje a kísérlet időablakán belül, `repository`, `sha`, `run_id`, `run_attempt`, `workflow_ref`, `job_workflow_ref`, `ref`, `sub`, `event_name` mind egyezik az API-metaadattal |
| `context.json` | **maga a workflow**: önbevallás | a szerző befolyásolja | csak összevetés az aláírt állításokkal; **soha nem bizonyíték önmagában** |
| P (PR-szerző befolyása) | — | pull_request-futás bizonyítéka kell | **NOT-READ** ebben a csomagban |

**Eredmény-címkék:** `EVIDENCE NOT BOUND (NOT MET)`, `INCOMPLETE (not read)`, `EVIDENCE BOUND, P NOT READ` (a legerősebb, amit ez a csomag adhat), `EVIDENCE BOUND, ALL READ` (csak, ha a P is olvasott; ebben a csomagban nem elérhető). **A P-t egyetlen workflow_dispatch futás nem dönti el**, ezért az M-E1 ítélete a futás után legfeljebb `INCONCLUSIVE (P)` vagy, ha a token nem kapható, `FAIL` lehet: ez **javasolt olvasat**, nem a tool kimenete.

## 3. A csomag ellenőrzése (helyi, szintetikus adatokkal)

```bash
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/check-me1-workflow.py \
  --selftest jobs/relay-ci-parity-06q-me1-measurement-package/output/payload/.github/workflows
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/read-me1.py --selftest
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/test-fetch-me1.py
python3 -I jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/read-me1.py --pk
```

- **`check-me1-workflow.py`: 33 beültetett eltérés** (extra trigger, `pull_request`, hiányzó vagy más `id-token`, többlet írási jog, környezet, titokhivatkozás, esemény-adat, nem rögzített vagy más action/SHA, más közönség, a token naplóba írása három módon, ártalmatlan többletutasítás, más kérés-URL, megváltozott vagy hiányzó kontextus-mező, hiányzó `set -e` vagy üresség-ellenőrzés, hosszabb megőrzés, `self-hosted`, második job, duplikált kulcs, `yes` mint `on`, üres és érvénytelen YAML …), mind elutasítva, **a tiltott-token lista kikapcsolva is** (a szerkezeti egyezés önmagában elég).
- **`read-me1.py --selftest`: 79 ellenőrzés**, köztük: az RS256-ellenőrző maga (érvényes aláírás elfogadva; más üzenet, más kulcs, megbillentett bit, csonkolt aláírás, apró modulus elutasítva); a PK (U) minden mezőre beültetett eltérés észlelve, (J) azonos rekord nem jelez; **S/R negatívok** (más futás, más repó, más head, más kísérlet elvárása elutasítva); az állítások egyenkénti eltérése (futás, kísérlet, SHA, repó, esemény, workflow-ref, job-workflow-ref, ref, subject, kibocsátó, közönség, időablak előtti és utáni kiadás, lejárat, hiányzó mező); a token hibái (más kulccsal aláírt, ismeretlen `kid`, `alg: none`, `HS256`, aláírás után módosított tartalom, nem JWT); a JWKS hibái (üres, más típus, kétszeres `kid`); az önbevallás eltérése; az API↔manifest eltérés; elavult és felesleges fájl; az elvárások hiánya `INCOMPLETE`; a manifest-író; a parancssori belépési pontok **alfolyamat-hívással**, az `--selftest` önállósága és a rekurzió-védő.
- **A teszt tud bukni:** az aláírás-ellenőrzést `True`-ra cserélve (ideiglenes másolat) a selftest 4 ponton elbukik, kilépési kód 1.
- **`test-fetch-me1.py`: 21 ellenőrzés**: az elfogadott 1. és 2. kísérlet végig a kiolvasásig, 13 elutasítási ág (későbbi kísérlet, közben változó kísérlet, időablakon kívüli, több vagy nulla artifact, más head, a kibocsátó kulcsai nem érhetők el, meglévő kimeneti könyvtár …), valamint két eset, ahol a bizonyíték letöltődik, de **az olvasó utasítja el** (más kibocsátó kulcsai; más commit állításai).
- **Mért (helyi, szintetikus):** minden fenti, 2026-11-22. **Nem mért:** a valódi GitHub-token formátuma, a `iat`/`exp` kezelése, a valódi JWKS (a `kid`, a kulcsforgatás), a `workflow_ref`/`job_workflow_ref`/`sub` értékek pontos alakja a valódi tokenben, az artifact-letöltés és az időablakos kiválasztás a valódi API-n. **Az olvasó elvárásai a dokumentált claim-nevekre épülnek**; ha a valódi token mást ad, a javítás új, review-köteles commit, és az M-E1 addig nem értékelhető.

## 4. Tulajdonosi szállítás és futás (külön GO, a PR mergelése után)

A védett `main` miatt a fájl **PR-ral** kerül az X repóra (a 4.6b mintájára). A PR-on a `lab-gate` check a `lab-gate-pr.yml`-től jelenik meg. A szállító szkript a jóváhagyott factory merge-commitból klónoz és a blobot ellenőrzi:

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
[ "$(git hash-object "$WORK/repo/.github/workflows/me1-evidence.yml")" = 2efdb089541989f328646e46b616e6f00da865ab ] || { echo "blob mismatch" >&2; exit 1; }
git -C "$WORK/repo" add .github/workflows/me1-evidence.yml
git -C "$WORK/repo" commit -m "phase 1: me1-evidence workflow (M-E1 evidence inventory)"
echo "branch commit: $(git -C "$WORK/repo" rev-parse HEAD)"
```

A szkript **nem pushol**; a push, a PR és a merge a tulajdonosé (K-8). Utána olvasott ellenőrzés (én): a PR `headRefOid`, a `lab-gate` check, a blob a merge-commiton.

**A futás és a kiolvasás (külön GO):**

```bash
gh workflow run me1-evidence.yml --repo "$ORG/$X" --ref main
# ha a futás action_required (a gyanús-workflow jelölés, P3): a jóváhagyás a tulajdonos döntése a weben, után a 2. kísérlet
bash .../harness/fetch-me1.sh RUN_ID ~/.cache/ci-lab/me1-raw/RUN_ID APPROVED_HEAD ATTEMPT
python3 -I .../harness/read-me1.py ~/.cache/ci-lab/me1-raw/RUN_ID \
  --expect-repo "$ORG/$X" --expect-run-id RUN_ID --expect-attempt ATTEMPT --expect-head-sha APPROVED_HEAD
```

**A gyanús-workflow jelölés (P3) előre betervezve:** a 0. fázisban a GitHub a PK-workflow-t jelölte meg és jóváhagyásig nem futtatta (az ok nem ismert). Ez a workflow `id-token: write`-ot kér, és tokent kér le: **újabb visszatartás várható, de nem mért**. A jóváhagyás a tulajdonos döntése, a fájl áttekintése után; ugyanazon futásazonosítón 2. kísérlet jön létre. A gyűjtő és az olvasó az 1. és 2. kísérletet kezeli (utóbbit csak tartott 1. kísérlet után).

**Az S és R negatívok valódi bizonyítéka második futást (és az R-hez új commitot) igényel**; a P pull_request-futást. Ezek **nem részei** ennek a csomagnak, külön GO-t és (a P-hez) külön csomagot igényelnek. Az M-E1 ítélete addig legfeljebb `INCONCLUSIVE`.

## 5. K-5 előszámítás (becslés, nem mért)

| Tétel | Kísérlet |
|---|---|
| Szállítás: a PR `lab-gate-pr` futása és a post-merge `lab-gate-bootstrap` futás | 2 |
| 1. mérési futás (a jelölés miatt legfeljebb 2 kísérlet) | ≤ 2 |
| 2. mérési futás az S negatívhoz (legfeljebb 2 kísérlet) | ≤ 2 |
| **Összesen** | **≤ 6**, azaz a jelenlegi 5 mellett **legfeljebb ≈ 11 / 300** |

A kísérletenkénti számlálás a tulajdonos szabálya. **Leállási küszöbök (#82 4. szakasz):** ha egy tétel 3 egymás utáni futása magyarázatlanul eltérő eredményt ad, vagy a futások száma eléri a 250-et megoldatlan INCONCLUSIVE-okkal, a mérést szüneteltetni és a tulajdonost értesíteni kell. Sikertelen vagy hiányos eredménynél **nincs automatikus újrafuttatás**.

## 6. Nyers bizonyíték kezelése

A nyers bizonyíték a tulajdonos gépén marad (`~/.cache/ci-lab/me1-raw/RUN_ID`). Nekem a fail-closed átvizsgálás és a tulajdonosi átnézés után adható át; **kulcs vagy valódi hitelesítő adat nincs benne**. Az OIDC-token egy saját közönségű, lejárt, aláírt JWT (nem titok, de a tulajdonos döntheti el, hogy a teljes tokent vagy csak az állításait (payload) küldi).

## 7. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A workflow-fájl pontosan a jóváhagyott szöveg, a `id-token: write` az egyetlen jogosultság-kiterjesztés | mért (helyi) | `check-me1-workflow.py` `OK`; blob `2efdb089…` | `--selftest` | az ellenőrző a helyi fájlt méri; a GitHub elfogadása nem mért |
| Az ellenőrző tud bukni | mért (helyi) | 33 beültetett eltérés elutasítva, tiltott-token lista nélkül is | `--selftest` | a mutáns-készlet nem teljes |
| A workflow törzse a várt kimenetet adja | mért (helyi, hamis környezettel és hamis `curl`-lel futtatva) | `context.json`, `oidc-token.jwt` a várt tartalommal | helyi szárazfutás | a valódi `ACTIONS_ID_TOKEN_REQUEST_*` viselkedés nem mért |
| Az RS256-ellenőrző jól dönt | mért (helyi, szintetikus kulcsokkal) | érvényes elfogadva; 5 hibás eset elutasítva | `read-me1.py --selftest` | a valódi JWKS és `kid` kezelés nem mért |
| Az olvasó az állításokat az API-metaadattal veti össze és tud bukni | mért (helyi, szintetikus) | 79/79; a kikapcsolt aláírás-ellenőrzés 4 ponton bukik | `--selftest`, mutáció | a valódi token állításainak pontos alakja nem mért |
| A PK: az összehasonlító észleli a beültetett eltérést és nem riaszt azonosnál | mért (helyi, szintetikus) | `--pk`, `--selftest` | `read-me1.py --pk` | — |
| A gyűjtő lánc az 1. és 2. kísérletet kezeli, és minden elutasítási ágban fail-closed | mért (mockolt) | `test-fetch-me1.py` 21/21 | `python3 -I test-fetch-me1.py` | a valódi API-válasz mezői nem mértek |
| A platform hiteles, független bizonyítékot ad a futásról (M-E1 H) | **nem állítom** | — | a tényleges mérés (külön GO) | az M-E1 ítélete a futás utáni jelentés tárgya |
| A PR-szerző nem befolyásolhatja a bizonyítékot (P) | **nem állítom, NOT-READ** | — | pull_request-futás bizonyítéka (külön csomag, külön GO) | — |
| A GitHub nem jelöli gyanúsnak az `id-token: write` workflow-t | **nem állítom** | — | a futás | a visszatartás valószínű; a K-5 számlálás ezt tartalmazza |
| Az X repó vagy az éles szervezet módosult | nem | nincs ilyen parancs; csak helyi fájlok | `git log` | — |

## 8. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét, és nem állítja, hogy a platform hiteles, független futási bizonyítékot ad.
- **Nem állítja,** hogy a GitHub elfogadja vagy a leírt módon futtatja a workflow-t; ezt csak a tulajdonosi PR és a futás mutatja meg.
- **Nem tartalmaz** futást, szállítást, bizonyíték-letöltést, H1/H2-t, M-A…M-D tételt, M-E2/E3/E5-öt, kulcsműveletet, App-kulcsot vagy Relay-implementációt.
- **Nem fedi** az artifact-attestációt (`attestations: write`, külön action): a #81 szerint a „platform által kínált igazolások" közé tartozik; **felvétele külön döntés**, a leltár erre a csomagra szűkített.
- **Nem módosítja** a #81–#88 tartalmát és a K-1–K-8 ajánlásokat.
