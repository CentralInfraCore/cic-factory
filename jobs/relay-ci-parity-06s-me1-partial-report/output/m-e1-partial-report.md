# #212 — Az M-E1 részjelentés, 1. fázis (06s)

**Státusz: jelentés (dokumentum) a már megtörtént, olvasott eseményekről.** Minden eredmény **scratch (labor), egy futásból, egy szervezetből, egy platform-pillanatképből**; nem production-igazolt, és **nem általánosítható** (4. szakasz). **Az M-E1 végső ítélete nyitott**: előzetesen `INCONCLUSIVE`, mert a P (a PR szerzőjének befolyása) `NOT-READ`, az S/R negatívok és az artifact-attestáció nyitott. A jelentés nem mondja ki sem a `PASS`-t, sem a `FAIL`-t. Új mérés, új futás, H1/H2, M-A…M-D, valódi App-kulcs és Relay-implementáció **HOLD**. K-5: 8/300 (292 maradék).

## 1. Azonosítók (olvasott, 2026-11-22)

| Tétel | Azonosító |
|---|---|
| Labor / X repó | `CIC-Security-Lab` / `ci-adversarial-lab` (nyilvános); repó-azonosító 1467589211, tulajdonos-azonosító 359862858 |
| Szállítás az X-re (PR #2) | `headRefOid` `6b88c9c34837fb54e3068ea092fb8a475a2a1719`; `lab-gate-pr` futás 45062640050 (`success`); merge `4d432f5e8250948af83ff909a7314eeddadb1c29` (19:48:33Z); post-merge `lab-gate-bootstrap` 45062842372 (`success`); a `me1-evidence` nem indult el automatikusan |
| Blobok az X `main`-jén | `lab-gate.yml` `ebdc21b0…`, `lab-gate-pr.yml` `ae50e51c…`, `pk-canary-channels.yml` `ede4968c…`, `me1-evidence.yml` `9030b6f1759297f344052ada7757ba22e80cd5af`; pontosan e négy fájl |
| Az M-E1 mérési futás | 45063800073, `workflow_dispatch`, ág `main`, head `4d432f5e…`, **1. kísérlet**, `completed / success`; indítás 19:59:05Z (a tulajdonos szkriptje, egyetlen indítás), létrehozás 19:59:06Z, befejezés 20:06:18Z |
| A job lépései | `Set up job` 19:59:11–13Z; **`me1 collect` 19:59:13Z–20:06:14Z (≈ 7 perc)**; `me1 artifact` 20:06:14–16Z |
| Artifact | 14770618752 (`me1-evidence`), létrehozva **20:06:16Z**, megőrzés 1 nap |
| Bizonyíték helye | a tulajdonos gépén: `~/.cache/ci-lab/me1-raw/45063800073` (nyers), `~/.cache/ci-lab/me1-trust/jwks-45063800073.json` (bizalmi gyökér, **külön**, SHA-256 `5f8164c9696c27837ad18c5fe7c7022a433bd5390183e8ff15c74d82233270f4`, 4 kulcs) |
| Factory merge-ek | #89 `e69b01cc5822e98cc9ae1fdde6a5fe88a8048079` (jóváhagyott fej `3d384a1`, post-merge gate 45061787202), #90 `a4be7ce05a1271a9c9c6112f4b449b468b407255` (jóváhagyott fej `f3db1ab`, post-merge gate 45067122627); a jóváhagyott és mergelt fák egyeznek |

## 2. A két olvasat (külön rögzítve; az elsőt nem írtam át)

**Mindkét olvasat ugyanazon a nyers bizonyítékon és ugyanazon a bizalmi gyökéren történt, új futás és új letöltés nélkül.**

### 2.1 Az első olvasat: a 06q olvasójával — `EVIDENCE NOT BOUND (NOT MET)`

Összesen 24 sor: **21 `MET`, 1 `NOT-MET`, 1 `NOTE`, 1 `NOT-READ`.**

- **`MET` (21):** a futás-, repó-, futásazonosító- és kísérletkötés, a korábbi kísérletek, az artifact eredete, a jóváhagyott head, a külön bizalmi gyökér, az API↔manifest egyezés; az **RS256 aláírás érvényes** a kibocsátó kulcsaival; a kibocsátó és a közönség (`me1-evidence`); a kiadás ideje az időablakon belül; **a token bizonyíthatóan lejárt az artifact szerveroldali létrehozása előtt**; a `repository`, `run_id`, `run_attempt`, `sha`, `workflow_ref`, `event_name`, `job_workflow_ref` állítás egyezik az API-metaadattal.
- **`NOT-MET` (1):** „OIDC binds ref and subject (identity)": a `ref` `refs/heads/main`, a `sub` viszont `repo:CIC-Security-Lab@359862858/ci-adversarial-lab@1467589211:ref:refs/heads/main`, az olvasó `repo:CIC-Security-Lab/ci-adversarial-lab:ref:refs/heads/main`-t várt.
- **`NOTE` (1):** az önbevallás (`context.json`) azonos az aláírt állításokkal. **`NOT-READ` (1):** P.
- **Az ok:** az olvasó dokumentációra épülő elvárása tévedett (a `sub` a numerikus tulajdonos- és repó-azonosítót is hordozza). **Nem a platformbizonyíték kötése hibás.** A #89 review ezt előre jelezte (a claim-nevek dokumentáltak, nem mértek); a valódi token cáfolta az elvárást.

### 2.2 A javított olvasat: a 06r olvasóval (#90) — `EVIDENCE BOUND, P NOT READ`

Összesen 29 sor: **26 `MET`, 2 `NOTE`, 1 `NOT-READ`.**

- **Újonnan `MET` (az 1-hez képest):** a `sub` mindkét alakot elfogadja, az azonosítós alakban a számok **pontosan az API `owner.id`/`repository.id` értékei**; a `repository_id` és a `repository_owner_id` állítás kötelezően egyezik az API-val; a `workflow_sha` és a `job_workflow_sha` egyezik a head-del.
- **`NOTE` (2):** az informatív állítások (`ref_type` `branch`, `ref_protected` `true`, `repository_visibility` `public`, `runner_environment` `github-hosted`) jelentve, nem ítélve; az önbevallás azonos az aláírt állításokkal. **`NOT-READ` (1):** P.
- A mergelés előtt egy **előzetes, helyi, csak olvasó** futás ugyanezt adta; ez nem volt mérési eredmény, a hivatalos olvasat a merge utáni (a tulajdonos futtatásával).

### 2.3 Az olvasó hibája és javítása

A 06q olvasója a `sub` alakját a dokumentációból feltételezte. A javítás **nem lazítás**: két pontos szövegalak, wildcard és általános regex nélkül; az azonosítós alakban a számok az API-hoz kötöttek; a kötött azonosító-állítások kötelezők. A javítás **erősebb identitáskötést** ad, mint az eredeti elvárás. A regressziós fixtúra a valódi token 31 állításos szerkezete (szintetikus aláírással). A tesztek tudnak bukni: az azonosító-ellenőrzés nélküli `sub` 8, az `repository_id` kötés kikapcsolva 3, a `workflow_sha` kötés kikapcsolva 2 ponton bukik.

## 3. A valódi token (mért; az `actor`, `actor_id`, `jti` értékét nem rögzítem)

| Állítás | Érték |
|---|---|
| fejléc | `alg` `RS256`, `typ` `JWT`, `kid` jelen |
| állításnevek (31) | `actor`, `actor_id`, `aud`, `base_ref`, `check_run_id`, `event_name`, `exp`, `head_ref`, `iat`, `iss`, `job_workflow_ref`, `job_workflow_sha`, `jti`, `nbf`, `ref`, `ref_protected`, `ref_type`, `repository`, `repository_id`, `repository_owner`, `repository_owner_id`, `repository_visibility`, `run_attempt`, `run_id`, `run_number`, `runner_environment`, `sha`, `sub`, `workflow`, `workflow_ref`, `workflow_sha` |
| `iss`, `aud` | `https://token.actions.githubusercontent.com`, `me1-evidence` (a mérés saját közönsége) |
| élettartam | `exp − iat` = **300 s**; `nbf` = `iat − 300 s` |
| `sub` | `repo:CIC-Security-Lab@359862858/ci-adversarial-lab@1467589211:ref:refs/heads/main` (**azonosítós alak**) |
| `repository_id`, `repository_owner_id` | `1467589211`, `359862858` (szövegként); az API azonos |
| `job_workflow_ref` | **jelen van** (nem újrahasznosítható workflow-nál is); egyezik a `workflow_ref`-fel |
| `workflow_sha`, `job_workflow_sha`, `sha` | mind a futás head-je, `4d432f5e…` |

## 4. Mért megfigyelések és korlátaik (**egy futás, egy szervezet, egy platform-pillanatkép; nem általánosítható**)

| # | Megfigyelés | Státusz | Korlát |
|---|---|---|---|
| O1 | A GitHub **nem tartotta vissza** a `me1-evidence` futást (nincs `action_required`, nincs 2. kísérlet), a 0. fázis PK-workflow-jával ellentétben. | mért (egy futás) | az ok ismeretlen; a visszatartás döntési szabálya nem ismert, a viselkedés időbeli stabilitása nem mért |
| O2 | A token élettartama 300 s; a lejárat-kapus publikálás a várt időrendben történt (a lépés ≈ 421 s = 300 + 121). | mért (egy futás) | az élettartam stabilitása nem mért; a workflow 600 s-nál messzebbi lejáratnál fail-closed leállt volna |
| O3 | A `sub` a numerikus tulajdonos- és repó-azonosítót is tartalmazza. | mért (egy futás) | az ok ismeretlen: szervezeti/repó-beállítás vagy általános viselkedés; más szervezetre nem következtethető |
| O4 | A `job_workflow_ref` állítás **jelen van** egy nem újrahasznosítható workflow-ban is. | mért (egy futás) | a #89 review szerint dokumentáltan elsősorban reusable workflow-nál értelmezett; ez egy megfigyelés, nem szabály |
| O5 | A platform az artifact-létrehozás idejét szerveroldalon rögzíti, és a token `exp`-jénél legalább 60 s-mal későbbi időpontra esett. | mért (egy futás) | az óraeltérés tartaléka a 60 s; a szerveridő megbízhatósága előfeltétel |
| O6 | A token és az API-metaadat azonos azonosítókat hordoz (`repository_id`, `repository_owner_id`, `run_id`, `run_attempt`, `sha`). | mért (egy futás) | mindkettő a GitHubtól származik (5. szakasz) |

**Általánosítási tilalom:** egyik megfigyelésből sem következik, hogy a platform más szervezetben, más repóban, más időben, más workflow-típusnál (pull_request, reusable, környezetes) ugyanígy viselkedik. A Relay-re nem általánosítható. A scratch (labor) eredmény nem production-igazolt.

## 5. A bizalmi határ

Az aláírás ellenőrzése a futás kódjától és szerzőjétől függetlenül végezhető el (a kibocsátó kulcsaival, a futás közreműködése nélkül végeztük). **Ez nem igazolja a bizonyíték előállításának, kiválasztásának vagy publikálásának szerzői befolyástól való mentességét**: ez utóbbi a P vizsgálat nyitott kérdése (`NOT-READ`), a kriptográfiai ellenőrzés függetlensége és a bizonyíték befolyásolhatatlansága két külön tulajdonság. **Az ellenőrzés bizalmi gyökere továbbra is a GitHub**: a token és az API-metaadat, amellyel összevetettük, ugyanattól a platformtól származik. A bizonyíték erejének feltételei:

1. **A kibocsátó nyilvános kulcsai** a tulajdonos gépén, TLS-en, közvetlenül a kibocsátótól, a futás után, a bizonyítékcsomagon **kívül** (külön fájlban, a csomagon belüli kulcsfájl elutasított). A tulajdonosi gép és a TLS-útvonal sértetlensége feltétel, nem védett.
2. **A GitHub őszintesége** mint kibocsátó és API: az eredmény nem igazolja, hogy a GitHub nem hamisítaná a bizonyítékot.
3. **Az órák:** a lejárat-kapu a futtató és a szerver óráira épül (60 s tartalék).
4. **A bizonyíték nem publikálható érvényes tokennel:** a token csak lejárta után került a nyilvános artifactba (O2, O5).
5. **Az önbevallás** (`context.json`) nem bizonyíték önmagában; eltérése `NOTE`, nem érvényteleníti az aláírt bizonyítékot (itt azonos volt).

## 6. A mérőcsomag története (#89–#90) és a saját hibák

| PR | Fej (review-kör) | Észrevétel és javítás |
|---|---|---|
| #89 (06q) | `ed31a38` | **F1 (HIGH): érvényes OIDC-token nyilvános artifactban**: a saját közönség és az 1 napos megőrzés nem hozzáférési korlát. F2: a bizalmi gyökér a bizonyítékcsomagban volt. F3: a token megszerezhetetlenségéből `FAIL` következtetés. F4: a `job_workflow_ref` kötelezővé tétele → `8339d14` |
| #89 | `8339d14` | **F5**: a várakozás a szigorú ellenőrzés határáig volt számolva, a normál futás az egyenlőségen elutasíthatta volna a publikálást → `3d384a1` (jóváhagyva) |
| #90 (06r) | `f3db1ab` | nincs blokkoló észrevétel (jóváhagyva) |

**Saját hibák és hatásuk:**
- **A token publikálása (F1):** a javítás előtt a csomag érvényes tokent tett volna nyilvános artifactba; a review találta meg, **a csomag a javítás előtt nem futott**, tehát nem keletkezett kitettség.
- **Az F5 határérték:** a normál futás elbukhatott volna egy egyenlőségen; a javítás közben a **600 s-os korlát** hibás határát (720 helyett 721) magam találtam meg; a szimulált óra tesztje a régi határral 9 ponton bukik.
- **A `sub`-elvárás:** a dokumentációból feltételeztem; a valódi token cáfolta (2.1). A bizonyítékra nem volt hatása, az olvasat javítva.
- **Errata (téves számok az eddigi közléseimben, jelen jelentésben javítva):** az első olvasatnál **21** `MET` sor volt, nem 22 (a 06r `input.md` és `sub-claim-fix.md` is 22-t írt: ebben a PR-ban javítva); a második olvasatnál **26** `MET` sor volt, nem 28 (ez csak a közlésemben szerepelt).
- Korábban (06n/06o): generált `.yaml` melléktermékek kétszer kerültek egy commitba, az `--attach-summary` parancssori hívás hibás volt; mindkettő javítva, a bizonyítékra nem hatott.

## 7. Az M-E1 állapota

| Vizsgálat | Eredmény |
|---|---|
| Platformaláírás (RS256, a kibocsátó kulcsaival, offline) | `MET` |
| Futás- és kísérletkötés | `MET` |
| Commit- és workflow-kötés (`sha`, `workflow_ref`, `job_workflow_ref`, `workflow_sha`) | `MET` |
| Repó- és tulajdonos-identitás (`repository`, `repository_id`, `repository_owner_id`, `sub`) | `MET` |
| Lejárat-kapus publikálás | `MET` |
| P: a PR szerzője nem befolyásolhatja a bizonyítékot | **`NOT-READ`** (pull_request-futás bizonyítéka kell) |
| S/R negatívok (más futás, régi futás bizonyítéka) | **nyitott** (második futás és új commit kell) |
| Artifact-attestáció (platform-igazolás) | **nyitott** (külön döntés; nincs a csomagban) |
| **M-E1 végső ítélet** | **nyitott; előzetesen `INCONCLUSIVE`** |

**Az ítélet a #81 szerint:** PASS = van legalább egy bizonyíték-típus, amely a négyest hitelesen köti, a PR szerzője nem módosíthatja, és független fél ellenőrizheti; FAIL = csak a kibocsátó önbevallása érhető el; INCONCLUSIVE = az ellenőrizhetőség nem döntött el. **Itt:** hiteles, aláírt bizonyíték van (tehát a `FAIL` nem indokolt), de a PR-szerző-feltétel (P) nem vizsgált (tehát a `PASS` nem mondható ki). Az ítélet a P és az S/R mérése után adható.

## 8. K-5 számlálás (kísérletenként, a tulajdonos szabálya)

| # | Futás | Kísérlet |
|---|---|---|
| 1 | 45032657726 bootstrap (`push`) | 1 |
| 2 | 45044622079 X PR #1 `lab-gate-pr` | 1 |
| 3 | 45044830647 post-merge bootstrap | 1 |
| 4–5 | 45045309607 PK (1. kísérlet visszatartva, 2. kísérlet `success`) | 2 |
| 6 | 45062640050 X PR #2 `lab-gate-pr` | 1 |
| 7 | 45062842372 post-merge bootstrap | 1 |
| 8 | 45063800073 M-E1 | 1 |

**Egyedi futás 7, kísérlet 8: felhasznált keret 8 / 300, fennmaradó 292.** Az újraolvasások és a helyi tesztek nem fogyasztanak keretet. **A következő (P és S/R) csomag előszámítása becslés, nem mért, és saját tervezést igényel:** szállítás 2 kísérlet, egy második `workflow_dispatch` futás az S-hez, egy pull_request-futás a P-hez, egy új commit utáni futás az R-hez; nagyságrendileg **legfeljebb ≈ 7 kísérlet**, a gyanús-workflow jelölés (O1 szerint nem biztos) nélkül.

## 9. Nyitott kérdések és a következő csomag belépési feltételei

**Nyitott kérdések:** (a) az azonosítós `sub` oka (O3); (b) a visszatartás szabálya (O1); (c) a P: egy pull_request-eseményen futó workflow `id-token: write` jogosultsága és a PR-szerző befolyása; (d) az S/R negatívok; (e) az artifact-attestáció felvétele; (f) a K-4 (3) olvasás a Relay felületén, a Relay alapértelmezett `write` workflow-jogosultsága és a régi szervezet 2FA-ja (külön biztonsági tételek, nem módosítva); (g) a B sor.

**A P és S/R mérőcsomag belépési feltételei (tervezési tétel, külön GO):** (1) a jelen jelentés lezárt és mergelt; (2) külön tervezés a pull_request-futás **biztonsági modelljéről** (a P csomagban a PR szerzője kontrollálja a workflow-t: a token-kérés és a publikálás szabályait előre, review-val kell rögzíteni, a #89 F1 tanulságával: érvényes token sehol sem publikálható); (3) külön tulajdonosi GO a szállításra és a futásokra; (4) a K-5 előszámítás a tulajdonosi szabály szerint.

## 10. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A futás 45063800073 az első kísérletben sikeres, a GitHub nem tartotta vissza | mért (labor) | 1. szakasz, `runs/ID/attempts/1` olvasás | API-olvasás | egy futás |
| A token RS256-aláírása érvényes a kibocsátó külön fájlban tartott kulcsaival | mért (labor, egy futás) | 2.2 `OIDC signature` sor | `read-me1.py` a tulajdonos gépén | a tulajdonosi gép és a TLS sértetlensége feltétel |
| A token a (workflow útvonal+ref, commit, azonosság, futás, kísérlet) négyest köti, egyezik az API-val | mért (labor, egy futás) | 2.2, 26 `MET` sor | `read-me1.py` | mindkét oldal a GitHubtól származik |
| A token lejárt az artifact szerveroldali létrehozása előtt (≥ 60 s) | mért (labor, egy futás) | `exp` 1795377853, artifact 20:06:16Z | `read-me1.py` lejárat-sora | az óra- és élettartam-stabilitás nem mért |
| Az első olvasat `NOT MET` volt az olvasó dokumentációra épülő elvárása miatt, a javított olvasat `EVIDENCE BOUND, P NOT READ` | mért | 2.1, 2.2 | a két kimenet | — |
| A `sub` azonosítós alakú | mért (egy futás, egy szervezet) | 3. szakasz | token-olvasás | az ok és az általánosság ismeretlen |
| A P (PR-szerző befolyása) | **nem állítom, NOT-READ** | — | pull_request-futás bizonyítéka (külön csomag, külön GO) | — |
| Az S/R negatívok, az artifact-attestáció | **nyitott** | — | külön csomag | — |
| Az M-E1 ítélete | **nem állítom; előzetesen INCONCLUSIVE** | 7. szakasz | a P és az S/R mérése után | — |
| A platform viselkedése más szervezetben, időben, workflow-típusnál | **nem állítom** | — | nincs | az általánosítás tilos |
| A saját hibák (token-publikálás, F5, `sub`-elvárás, számlálási errata) | rögzített | 6. szakasz, a #89–#90 review-k | git-történet, PR-ok | — |
| K-5: 8/300 | olvasott | 8. szakasz | `gh api actions/runs`, a futások listája | a konzervatív számlálás a tulajdonos szabálya |
| Az X vagy az éles szervezet módosult a jelentés készítésekor | nem (**végrehajtási naplóra alapozott állítás**) | a jelentés készítésekor csak olvasó API-hívások és helyi fájlműveletek futottak; az X repón írást kizárólag a tulajdonos végzett (szállítás, merge, futás), a saját parancsaim naplója szerint | a session végrehajtási naplója és a tulajdonos futtatási jegyzete; a `git log` ezt **nem** bizonyítja | a napló az én oldalam; a tulajdonosi műveletek külön naplója az övé |

## 11. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét; az `EVIDENCE BOUND` nem `PASS`.
- **Nem állítja,** hogy a platform hiteles, független (a GitHubtól független) bizonyítékot ad; a bizonyíték a GitHub aláírására épül.
- **Nem általánosít:** egy futás, egy szervezet, egy pillanatkép; nem production-igazolt, a Relay-re nem általánosítható.
- **Nem tartalmaz** új mérést, új futást, bizonyíték-letöltést, H1/H2-t, M-A…M-D tételt, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem módosítja** a #81–#90 tartalmát és a K-1–K-8 ajánlásokat; a 06r két fájljában csak a téves szám (22 → 21) javítva.
