# #212 — Az M-E1 olvasó `sub`-elvárásának javítása (06r)

**Státusz: javítás (helyi, szintetikus és a valódi token szerkezetével tesztelt).** A 06q olvasóját javítja, a 06q tartalma nem módosul. **Az M-E1 ítélete nyitott**: a P (PR-szerző befolyása) `NOT-READ`, ezért az ítélet legfeljebb `INCONCLUSIVE` lehet, amíg pull_request-futás bizonyítéka nincs. A javított olvasó eredménye **a merge után a tulajdonos által újraolvasott** bizonyíték eredménye; az itt idézett előzetes futás nem a mérési eredmény. K-5: 8/300.

## 1. Az első valódi olvasat (mért, labor X repó, 2026-11-22)

A futás: 45063800073, `workflow_dispatch`, `headSha` `4d432f5e8250948af83ff909a7314eeddadb1c29`, 1. kísérlet, `completed / success`; a GitHub **nem tartotta vissza** (a PK-workflow-tól eltérően). Az `me1 collect` lépés 19:59:13Z–20:06:14Z (≈ 7 perc), az artifact (14770618752) létrehozása 20:06:16Z. A bizonyíték a tulajdonos gépén (`~/.cache/ci-lab/me1-raw/45063800073`), a bizalmi gyökér külön (`~/.cache/ci-lab/me1-trust/jwks-45063800073.json`, SHA-256 `5f8164c9…`).

**Az első kiolvasás (a 06q olvasójával): `EVIDENCE NOT BOUND (NOT MET)`**, 22 sor `MET`, 1 `NOT-MET`, 1 `NOTE`, 1 `NOT-READ`. A `NOT-MET` sor: „OIDC binds ref and subject (identity)": a `ref` `refs/heads/main`, a `sub` `repo:CIC-Security-Lab@359862858/ci-adversarial-lab@1467589211:ref:refs/heads/main`, az olvasó viszont `repo:CIC-Security-Lab/ci-adversarial-lab:ref:refs/heads/main`-t várt. Ez az olvasat és az indoka a jelentésben megőrzendő.

**A valódi token (mért; a fejléc `alg` `RS256`; az `actor`, `actor_id`, `jti` értékét nem rögzítem):**

| Állítás | Érték |
|---|---|
| állításnevek (31) | `actor`, `actor_id`, `aud`, `base_ref`, `check_run_id`, `event_name`, `exp`, `head_ref`, `iat`, `iss`, `job_workflow_ref`, `job_workflow_sha`, `jti`, `nbf`, `ref`, `ref_protected`, `ref_type`, `repository`, `repository_id`, `repository_owner`, `repository_owner_id`, `repository_visibility`, `run_attempt`, `run_id`, `run_number`, `runner_environment`, `sha`, `sub`, `workflow`, `workflow_ref`, `workflow_sha` |
| `iss`, `aud` | `https://token.actions.githubusercontent.com`, `me1-evidence` |
| élettartam | `exp − iat` = **300 s**; `nbf` = `iat − 300 s` |
| `sub` | `repo:CIC-Security-Lab@359862858/ci-adversarial-lab@1467589211:ref:refs/heads/main` (az **azonosítós alak**) |
| `repository_id`, `repository_owner_id` | `1467589211`, `359862858` (szövegként); az API `repository.id` és `owner.id` értéke azonos |
| `job_workflow_ref` | **jelen van** (nem újrahasznosítható workflow-nál is), egyezik a `workflow_ref`-fel |
| `workflow_sha`, `job_workflow_sha`, `sha` | mind `4d432f5e…`, a futás head-je |
| `ref_type`, `ref_protected`, `repository_visibility`, `runner_environment` | `branch`, `true`, `public`, `github-hosted` |

**Amit nem tudok:** hogy az azonosítós `sub` szervezeti/repó beállítás vagy a platform általános viselkedése (egy szervezetben, egy futáson mért); hogy a viselkedés időben stabil-e.

## 2. A javítás

| Elem | 06q | 06r |
|---|---|---|
| `sub` | csak `repo:OWNER/REPO:ref:refs/heads/main` | **mindkét alak**: az egyszerű, és az azonosítós `repo:OWNER@OWNERID/REPO@REPOID:ref:...`, utóbbiban a számok **pontosan az API `owner.id`/`repository.id` értékei** |
| `repository_id`, `repository_owner_id` | nem vizsgált | **kötelező kötés** az API azonosítóira; hiányuk, eltérésük vagy a szám-típus (nem szöveg) `NOT-MET` |
| `workflow_sha`, `job_workflow_sha` | nem vizsgált | ha jelen van: egyeznie kell a futás head-jével; hiánya `NOTE` |
| `ref_type`, `ref_protected`, `repository_visibility`, `runner_environment` | nem vizsgált | **jelentve (`NOTE`), nem ítélve** |

Az API-oldali azonosítók a letöltött `api/run.json`-ból jönnek; ha az API nem ad azonosítót, az azonosítós alak nem igazolható (`NOT-MET`). A `fetch-me1.sh`, `fetch-jwks.sh` változatlan másolat.

## 3. Ellenőrzés (helyi)

```bash
python3 -I jobs/relay-ci-parity-06r-sub-claim-fix/output/harness/read-me1.py --selftest
python3 -I jobs/relay-ci-parity-06r-sub-claim-fix/output/harness/test-fetch-me1.py
```

- **`read-me1.py --selftest`: 120 ellenőrzés**, köztük az új esetek: az azonosítós alak elfogadva; az egyszerű alak továbbra is elfogadva; az azonosítós alak hibás repó-, hibás tulajdonos-azonosítóval, felcserélt azonosítókkal, nem numerikus azonosítóval, csak az egyik azonosítóval, záró többlettel, más repónévvel, környezeti subject-tel; hiányzó `sub`; az API azonosító nélkül (az azonosítós alak nem igazolható); az azonosító-állítások eltérése, hiánya és szám-típusa; az API azonosítói eltérnek a tokenétől; `workflow_sha`/`job_workflow_sha` eltérése és hiánya; az informatív állítások jelentve és nem ítélve; **a valódi token 31 állításos szerkezete mint regressziós fixtúra** (a nevek és a nem érzékeny értékek a valódi futásról, szintetikus aláírással).
- **A teszt tud bukni** (ideiglenes másolat, kilépési kód 1): az azonosítós alak azonosító-ellenőrzés nélkül 8 ponton; az `repository_id` kötés kikapcsolva 3 ponton; a `workflow_sha` kötés kikapcsolva 2 ponton bukik.
- **`test-fetch-me1.py`: 29 ellenőrzés** (változatlan lánc).
- **Előzetes, helyi, csak olvasó futás a valódi bizonyítékon** (a mergelés előtt, **nem a mérési eredmény**): `EVIDENCE BOUND, P NOT READ`; a `sub`, a két azonosító-kötés és a `workflow_sha`/`job_workflow_sha` sor `MET`. A hivatalos újraolvasás a merge után, a tulajdonos futtatásával történik.

## 4. Az újraolvasás terve (a merge után, külön lépés)

A meglévő bizonyítékot újraolvassuk, **új futás és új letöltés nélkül**: `me1-run-212.sh read 45063800073 1` (a tulajdonosi szkript a 06r harnessre és a merge-commitra frissítendő, blob-egyezés-ellenőrzéssel). A jelentés az **első olvasatot (`NOT MET`, a `sub`-elvárás miatt)** és a javított olvasatot külön rögzíti. **Az M-E1 ítélete a javított olvasat után is nyitott** (P `NOT-READ`).

## 5. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A valódi token `sub` állítása az azonosítós alakú | mért (labor, egy futás) | 1. szakasz, a token olvasása | a tulajdonos gépén lévő bizonyíték olvasása | beállítás vagy általános viselkedés: nem ismert |
| Az azonosítók a tokenben és az API-ban egyeznek | mért (labor, egy futás) | `repository_id` 1467589211, `owner_id` 359862858 mindkét oldalon | a `read-me1.py` két kötéssora | egy futás |
| A token élettartama 300 s, a lejárat-kapu a várt időrendben működött | mért (labor, egy futás) | `exp − iat` = 300; az artifact 20:06:16Z, `exp` után ≥ 60 s | a `read-me1.py` lejárat-sora | az élettartam stabilitása nem mért |
| Az első kiolvasás `NOT MET` volt, oka az olvasó dokumentációra épülő elvárása | mért | 1. szakasz | az első kimenet | — |
| A javított olvasó mindkét `sub`-alakot elfogadja, az azonosítókat az API-hoz köti | mért (helyi) | 120/120; mutációk 8/3/2 ponton buknak | `--selftest` | a valódi platform más alakot is adhat |
| A javított olvasó a valódi bizonyítékon `EVIDENCE BOUND, P NOT READ` (előzetes) | mért (helyi, csak olvasó, **nem a mérési eredmény**) | az előzetes kimenet | a merge utáni újraolvasás | — |
| A platform hiteles, független bizonyítékot ad a futásról (M-E1 H) | **nem állítom** | — | a jelentés teljes inventár alapján | az ítélet nyitott |
| A PR-szerző nem befolyásolhatja a bizonyítékot (P) | **nem állítom, NOT-READ** | — | pull_request-futás bizonyítéka (külön csomag, külön GO) | — |
| Az X repó vagy az éles szervezet módosult | nem | nincs ilyen parancs | `git log` | — |

## 6. Mit nem állít ez a dokumentum

- **Nem mondja ki** az M-E1 ítéletét; az `EVIDENCE BOUND` nem `PASS`.
- **Nem állítja,** hogy az azonosítós `sub` minden szervezetben, minden időben így néz ki.
- **Nem tartalmaz** új futást, új letöltést, H1/H2-t, M-A…M-D tételt, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem módosítja** a #81–#89 tartalmát és a K-1–K-8 ajánlásokat.
