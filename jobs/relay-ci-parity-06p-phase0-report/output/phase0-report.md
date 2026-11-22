# #212 — A 0. fázis zárójelentése (06p)

**Státusz: jelentés (dokumentum), a már megtörtént, olvasott eseményekről.** Nem végrehajtás, nem mérés. Minden eredmény **scratch (labor), nem production-igazolt**. **A `PK MET` kizárólag a mérőeszköz vizsgált pozitív kontrolljaira vonatkozik**: nem ítélet a platformtulajdonságról, nem előminősítés a H1/H2 hipotézisekre, és a 0. fázis fennmaradó biztonsági tételei (6. szakasz) külön státuszúak. Új mérés, új PK-futás, valódi kulcsművelet és Relay-implementáció **HOLD**.

## 1. Azonosítók (olvasott, 2026-11-22)

| Tétel | Azonosító |
|---|---|
| Labor-szervezet / X repó | `CIC-Security-Lab` (ingyenes, 2FA kötelező, alapjog nincs) / `ci-adversarial-lab` (nyilvános, `main`, nem archivált) |
| Y repó (`ci-identity-lab`) | **nincs létrehozva** (B sor, nem indult) |
| Bootstrap commit az X-ben | `0cbe31354e7f1b79dacc864c36d70018e6362dc5` (`lab-gate.yml` blob `ebdc21b0…`); futás 45032657726, `push`, `success` |
| Védett `main` (4.7), most olvasva | megkövetelt check `lab-gate`, `app_id` 15368 (Actions), `strict=false`, `enforce_admins=true`, PR-felülvizsgálat és korlátozás nincs |
| X PR #1 (4.6b csomag szállítása) | `headRefOid` `18a7267c34270b2783e09f58b4ed30c3dbf7e8a1`; `lab-gate` check 15368, `success`; futás 45044622079 (`lab-gate-pr`, `pull_request`); merge `3c1eabeafa6db5ccbd83b38a084407944a8c7869` (2026-11-22 16:36:54Z); post-merge futás 45044830647 (`lab-gate-bootstrap`, `push`, `success`) |
| Szállított blobok az X `main`-jén | `lab-gate-pr.yml` `ae50e51c…`, `pk-canary-channels.yml` `ede4968c…`, `lab-gate.yml` `ebdc21b0…`; pontosan e három fájl |
| PK-futás | 45045309607, `workflow_dispatch`, ág `main`, head `3c1eabeafa6db5ccbd83b38a084407944a8c7869` |
| — 1. kísérlet | `completed` / `action_required`, **0 job**, 16:42:14–16:42:16Z |
| — 2. kísérlet | `completed` / `success`, job `pk-channels` `success`, 17:08:31–17:08:47Z |
| PK artifact | 14763998724 (`pk-channels`, megőrzés 1 nap, a kísérlet időablakán belül létrehozott) |
| Repó-szintű titkok az X-en (olvasott, nevek) | `["CANARY_UNRESTRICTED"]` (a K1/K2/K3 környezeti titkok a környezetekben); szervezeti titok 0 |
| Factory merge-ek | #83 `505e639`, #84 `bf654d1`, #85 `7d83465`, #86 `31fbded`, #87 `38bf5e6` (post-merge gate-ek: 45043036972, 45050426384, 45053381633, mind `success`, a `headSha` a merge commit) |

## 2. A PK-ítélet (kizárólag a mérőeszközről)

A kiolvasás a javított olvasóval (#87) történt, a konkrét futáshoz kötve: `--expect-repo CIC-Security-Lab/ci-adversarial-lab --expect-run-id 45045309607 --expect-attempt 2 --expect-head-sha 3c1eabea… --expect-sha256 <a tulajdonos helyben számolt digestje>`. A nyers bizonyíték a tulajdonos gépén (`~/.cache/ci-lab/pk-raw/45045309607`), nem a repóban.

| # | Ellenőrzés | Eredmény | Megjegyzés |
|---|---|---|---|
| 1 | run binding | MET | futás 45045309607, 2. kísérlet, `workflow_dispatch`, `completed/success`, ág `main` |
| 2 | repository | MET | a független `--expect-repo` egyezik a manifesttel |
| 3 | run id | MET | a független `--expect-run-id` egyezik |
| 4 | attempt | MET | a független `--expect-attempt 2` egyezik |
| 5 | earlier attempts | MET | az 1. kísérlet `completed/action_required`, 0 job |
| 6 | artifact origin | MET | a 14763998724 a kísérlet időablakán belül jött létre (közvetett kötés, 7. szakasz) |
| 7 | approved head SHA | MET | `3c1eabea…` |
| 8 | summary binding | MET | **tulajdonosi tanúsítás** a 2. kísérletre (nem gépi bizonyíték) |
| 9 | U log | MET | az ismert, nem titokként regisztrált token egy kimeneti sorban |
| 10 | U artifact | MET | a fájl egyezik |
| 11 | U annotation | MET | a `message` mező egyezik |
| 12 | U summary | MET | a tulajdonos által másolt összegzés tartalmazza |
| 13 | U secret readable | MET | a titok hossza 43 |
| 14 | U secret digest | MET | egyezik a tulajdonos helyben számolt értékével (az érték nem hagyta el a gépet) |
| 15 | J masked | MET | a regisztrált titok a naplóban `***` |
| 16 | J secret names | MET | `["CANARY_UNRESTRICTED","github_token"]` |
| 17 | J no other canary: log | MET | 0 egyéb `CANARY-212-` előfordulás |
| 18 | J no other canary: annotation | MET | 0 |
| 19 | J no other canary: artifact | MET | 0 |
| 20 | J no other canary: summary | MET | 0 |

**Összesített: `PK MET` (20/20).** Jelentése: a mérőeszköz (a gyűjtés, a kötés és az olvasó) a vizsgált laborfeltételek mellett működik, és a bizonyítékot a konkrét futáshoz és kísérlethez kötötten, négy csatornán olvassa. **Nem jelenti:** a platformtulajdonság igazolását, a H1/H2 bármelyikének eredményét, production-igazolást.

## 3. Platformmegfigyelések (mért a labor X repón; **nem a PK ítélete**, nem általánosítható a Relay-re)

| # | Megfigyelés | Státusz |
|---|---|---|
| P1 | A **regisztrált titok** a naplóban maszkolt (`***`), a **nem regisztrált** token mind a négy csatornán látszik. | mért (labor, egy futás) |
| P2 | Környezet nélküli jobban a `secrets` kontextus kulcsai pontosan `["CANARY_UNRESTRICTED","github_token"]`: a K1/K2/K3 környezeti titkok nem látszottak. | mért (labor, egy futás); a K1/K2 (H1/H2) a 2. fázis tárgya, **ez nem azok ítélete** |
| P3 | A GitHub a `pk-canary-channels.yml`-t **gyanúsként jelölte**, jóváhagyásig nem futtatta: az 1. kísérlet `action_required`, 0 jobbal. Szöveg (a tulajdonos másolata): „GitHub detected that this workflow file may be malicious. It will not run until someone with write access approves it." **Az ok nem ismert** (a fájl titokkezelő elemei csak következtetett jelöltek: `toJSON(secrets)`, a titok kiírása; **nem mért**). | mért a tény; az ok nem ismert |
| P4 | A webes jóváhagyás **ugyanazon futásazonosítón új, 2. kísérletet** hozott létre: a bizonyíték azonosításához a futásazonosító önmagában nem elég. | mért (olvasott, `runs/ID/attempts/{1,2}`) |
| P5 | A `lab-gate-pr.yml` a PR-eseményen lefutott, a `lab-gate` check megjelent a PR-on (`app_id` 15368) és a védett `main` megkövetelte; a merge után a bootstrap workflow a `push` eseményen is lefutott. | mért (X PR #1) |
| P6 | A PR-eseményen a **PR saját változata** fut (a `lab-gate` ezért a PR által módosítható): **dokumentált, ebben a jelentésben nem mért**; az M-A tételek tárgya. | dokumentált, nem mért |

## 4. A mérőeszköz története (#85–#87, tartalmi review-körök)

| PR | Fej (review-kör) | Észrevétel és javítás |
|---|---|---|
| #85 (4.6b csomag) | `c27efa7` | F1 az ellenőrző nem teljes dokumentumegyezést vizsgált (a `run` test kötelező-sor-lista volt); F2 a bizonyíték nem volt futáshoz kötve; F3 a kanári-hiány csak a naplón ellenőrzött; F4 a digest opcionális → `a75babf` |
| #85 | `a75babf` | F2.1: az olvasó nem kérte független bemenetként a repót és a futásazonosítót → `def3d3f` (jóváhagyva, merge `7d83465`) |
| #86 (06n, kísérletkötés) | `b3be349` | F1 az artifact futásazonosító és név alapján választott; F2 az összegzés nem volt kísérlethez kötve; F3 fix `attempt 1` üzenet → `e4a135b` (jóváhagyva, merge `31fbded`) |
| #87 (06o, parancssori javítás) | `fddbbf1` | F1 hiányos CLI-tesztmátrix; F2 az `--selftest` más paranccsal kevert hívása; F3 a manifest állapotának tisztázása → `3d4be96` (jóváhagyva, merge `38bf5e6`) |

**Saját hibák, amelyeket a folyamat megtalált vagy a tulajdonos futtatása hozott elő:**
- **A kísérlet kódolva `1` volt** az olvasóban és a letöltőben (a #85-ben): a visszatartott workflow (P3, P4) előre nem látott eset volt; a fail-closed viselkedés elutasította a 2. kísérletet, a javítás a #86.
- **Az `--attach-summary` parancssori hívása `TypeError`-ral bukott** a #86 után: a `main()` hívása nem frissült az új paraméterhez; a selftest a függvényt hívta, nem a belépési pontot (a hibát a tulajdonos futtatása találta, a #87 javította 50 parancssori teszttel).
- **Generált `.yaml` melléktermékek kétszer bekerültek egy commitba** (06n, 06o): új commitban eltávolítva; azóta explicit fájllista.
- **Saját hibák hatása a bizonyítékra:** nincs; a bizonyíték könyvtára a hibák idején sértetlen volt, a kiolvasás a javított olvasóval történt.

Minden javítás külön PR, aláírt commit, tartalmi review és SHA-hoz kötött merge volt; a post-merge gate-ek zöldek, a jóváhagyott és mergelt fák egyeznek.

## 5. K-5 számlálás (tulajdonosi döntés: kísérletenként, konzervatívan)

| Számláló | Érték |
|---|---|
| Egyedi workflow-futások (olvasott, `total_count`) | 4: 45032657726 (bootstrap), 45044622079 (PR), 45044830647 (post-merge), 45045309607 (PK) |
| Futási kísérletek | **5** (a PK-futás 2 kísérlete) |
| Felhasznált K-5 keret | **5 / 300** |
| Fennmaradó | 295 |

A bootstrap futás nem mérési futás, külön rögzített; a konzervatív szabály szerint mégis beszámít. Ez a számlálási szabály a további mérésekre egységes. A teljes becslés (kb. 218 futás a 0–3. fázisra) **becslés, nem mért**.

## 6. A 0. fázis tételeinek **külön státusza**

| Tétel | Státusz | Megjegyzés |
|---|---|---|
| G0 kapu (szervezet, X repó, K-2, K-5, K-8, O-5 (a), védett ág alapállapota) | **teljesült** | a G0 12 sorából 9 olvasott és igazolt; a tulajdonos megerősítései: K-5 ACCEPT, K-8 ACCEPT, 11 (d) CONFIRMED (a tulajdonos szövege szerint; az éles repók konfigurációját a labor előkészítése során nem módosította) |
| Alapállapot-fájlok (K-6) | rögzítve, scan és átvizsgálás megtörtént | nyers fájlok a tulajdonos gépén |
| PK (harness önellenőrzés) | **`PK MET` (20/20)** | csak a mérőeszköz; lásd 2. szakasz |
| Platformmegfigyelések | rögzítve (3. szakasz) | nem a PK ítélete |
| B sor (Y repó, két App kulcs nélkül, gépi fiókok A/B, kanári-pár, O-4 szkriptek) | **nem indult** | a 2–3a kapuk előfeltétele; saját GO |
| K-4 (3): kap-e írási tokent a fork-PR-ból induló Relay-workflow | **nyitott, nincs olvasva** | az API nem adja; a tulajdonos olvassa a felületen |
| Külön biztonsági tétel: a Relay alapértelmezett workflow-jogosultsága `write`, `can_approve_pull_request_reviews: true` (olvasott, T-2) | **nyitott, nem módosítva** | nem a mérési terv része; a tulajdonos dönt |
| Külön biztonsági tétel: a régi szervezet 2FA-ja (#82 6. szakasz); az App `cic-integrity-scratch` kulcsának visszavonása (a korábbi mérési munka jegyzete szerint külön tétel) | **nyitott, nem módosítva** | nem a mérési terv része; a tulajdonos dönt |
| H1/H2, M-A…M-E mérések | **HOLD, nem indultak** | 1. fázis: külön GO |
| Valódi App-kulcs, 3b | **HOLD** | |
| Relay-implementáció, #212 lezárása, scratch repók törlése | **HOLD** | |

## 7. Korlátok

- **Manuális attestáció:** a job-összegzés csatornát az API nem szolgáltatja; a csatolt másolatot a tulajdonos tanúsította (a manifest jelöli). Nem gépi bizonyíték.
- **Közvetett artifact-kötés:** az API nem ad kísérletenkénti artifact-azonosítót; a kötés a kísérlet időablakára és az egyedi azonosítóra épül (a kiolvasó `artifact origin` ellenőrzése). A jelenlegi szűk PK-elfogadási modellben elfogadható, nem a GitHub által közvetlenül szolgáltatott kísérlet-azonosítás.
- **Kevés futás, egy platform-pillanatkép:** a P1–P4 egyetlen PK-futás két kísérletén, a P5 pedig az X repó külön PR- és post-merge futásain alapul. A megfigyelt viselkedések időbeli stabilitása nem mért.
- **A naplóformátum** a PK által olvasott sorokra igazolt, nem általában.
- **A gyanús-workflow jelölés oka nem ismert**; egy másik változat futtatása nélkül nem állapítható meg, és az új futás keretet fogyaszt (külön tétel, külön GO).
- **A repón kívüli wrapper** (`pk-run-212.sh`) a CI-ben nem tesztelt (technikai adósság, külön döntés).
- **Scratch ≠ production:** a Relay-re nem általánosítható.

## 8. Nyitott kérdések és a következő fázis (1. fázis) belépési feltételei

**Nyitott kérdések:** (a) a gyanús-workflow jelölés oka és hatása a későbbi mérő-workflow-kra (hasonló minták újabb visszatartást kaphatnak: a 2. fázis tervezésénél figyelembe veendő); (b) a K-4 (3) olvasás; (c) a külön biztonsági tételek kezelése (6. szakasz); (d) a B sor ütemezése (a 2–3a kapukhoz).

**Az 1. fázis belépési feltételei (a #82 5.1 és K-7 szerint):**
1. G0 teljesült, PK MET (**teljesült, ez a jelentés**).
2. Külön, kifejezett tulajdonosi GO az 1. fázisra, a mérések tételes felsorolásával. Az első mérendő tétel az M-E1 (K-7: MEASURE), az M-E2/E3/E5 az M-E1 PASS-tól függ.
3. Futási keret: 295 maradék; a #82 leállási küszöbei érvényesek; a kísérletenkénti számlálás.
4. Minden mérő-workflow új, review-köteles PR; a jelölés (P3) ismeretében a tulajdonosi jóváhagyás lehetősége előre betervezett.
5. A nyers kimenet a fail-closed scan és a tulajdonosi átnézés után kerül hozzám; kulcs vagy valódi hitelesítő adat nem.

**Nem teljesült, nem része ennek a jelentésnek:** a B sor és a 2–3. fázis kapui.

**A 2–3b fázisok belépési feltételei** (a döntési csomag 5.1 szakasza szerint, ide csak hivatkozva, új követelmény nélkül; mind HOLD, saját GO-val):
- **G2** (2. fázis): O-3 (A és B gépi fiók), az O-4 szkriptek (3.–9. sor), K-6.
- **G3a** (3a fázis): K-1 az Y repóra, O-2 (a) (két App, kulcs nélkül), O-5 (b) (kanári-pár), O-4 (1., 5. sor az Y-ra), a B1–B4 eredménye ismert.
- **G3b** (3b fázis, az egyetlen, amelyben valódi App-kulcs létezik): O-1 (installáció-felfüggesztés és visszaállítás), O-2 (b) (a kulcs létrehozása és lokális őrzése a tulajdonos gépén, E-3), a 3a fázis lezárása (M-D5 és M-B4 PASS vagy elfogadott kockázat); a kanáris fázisok lezárulnak, mielőtt a valódi kulcs létrejön (E-4).
- **Lezárás:** O-6 (a kulcsok visszavonása a tulajdonos által, az App-ok felfüggesztése, a repók archiválása; a törlés HOLD).

## 9. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A G0 teljesült | olvasott + tulajdonosi megerősítés | a runbook 4.8 és a 6. szakasz olvasásai; a tulajdonos szövege (K-5, K-8, 11 (d)) | API-olvasás; a tulajdonos megerősítése | a 11 (d) a tulajdonos kijelentése, nem általam olvasott |
| `PK MET` 20/20 | mért (labor) | 2. szakasz, a kiolvasás kimenete | `read-pk.py` a futáshoz, kísérlethez, head-hez kötve | a naplóformátum és az összegzés-csatorna korlátai (7.) |
| A PK a mérőeszközt, nem a platformtulajdonságot ítéli | tervezési tulajdonság | #81 2.2, a 2. és 3. szakasz szétválasztása | tartalmi review | a későbbi jelentés összemoshatja |
| A regisztrált titok maszkolt, a nem regisztrált látszik | mért (labor, egy futás) | P1 | PK-kiolvasás | nem általánosítható, egy futás |
| Környezet nélküli jobban a K1/K2/K3 nem látszik a kulcsok között | mért (labor, egy futás) | P2 | PK `J secret names` | a H1/H2 ítélete a 2. fázis tárgya, ez nem az |
| A GitHub gyanúsként jelölte a workflow-t, új kísérlet jött létre jóváhagyás után | mért a tény | P3, P4 | `runs/ID/attempts/{1,2}` olvasás, a tulajdonos másolata | az ok nem ismert |
| A `lab-gate` PR-eseményen is megjelenik, a védett `main` megköveteli | mért (labor) | P5, X PR #1 | API-olvasás | PR-változat forgathatósága (P6) nem mért |
| A mérőeszköz javításai (#85–#87) mind review-zva és SHA-hoz kötötten mergelve | olvasott | 4. szakasz, post-merge gate-ek | `gh pr view`, fa-egyezés, `gh run list` | — |
| K-5: 5/300 (kísérletenként) | olvasott | 5. szakasz, `total_count` 4, 2 kísérlet a PK-nál | `gh api actions/runs` | a konzervatív számlálás a tulajdonos szabálya |
| A Relay alapértelmezett workflow-jogosultsága `write`; a K-4 (3) nyitott | olvasott (T-2), nyitott (T-5) | runbook 2. szakasz | a tulajdonos olvassa a felületen | külön biztonsági tétel, nem módosítva |
| A 2–3b fázisok belépési feltételei (G2, G3a, G3b, lezárás) | hivatkozott, nem új követelmény | 8. szakasz, a döntési csomag 5.1 kapu-táblája | az 5.1 tábla összevetése | a feltételek a #82 állapotát tükrözik; a tulajdonos módosíthatja |
| A H1/H2 hipotézisek eredménye | **nem állítom** | — | az 1–2. fázis mérései, külön GO | — |
| Production-igazolás | **nem állítom** | — | — | scratch ≠ production |
| Az X vagy az éles szervezet módosult a jelentés készítésekor | nem | nincs ilyen parancs; csak olvasó API-hívások | `git log`, a tulajdonos futtatási jegyzete | — |

## 10. Mit nem állít ez a dokumentum

- **Nem állítja,** hogy a H1/H2 hipotézisek bármelyike igazolt vagy cáfolt; azokat nem mértük.
- **Nem állítja,** hogy a platform viselkedése production-igazolt vagy a Relay-re általánosítható.
- **Nem állítja,** hogy az összegzés-csatorna vagy az artifact-kötés gépileg teljes bizonyíték.
- **Nem tartalmaz** új mérést, új PK-futást, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem módosítja** a #82–#87 tartalmát és a K-1–K-8 ajánlásokat.
