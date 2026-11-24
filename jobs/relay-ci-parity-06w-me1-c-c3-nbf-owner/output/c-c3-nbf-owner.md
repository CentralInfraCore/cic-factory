# #212 M-E1 — a C-c3 szerződés pontosításának megvalósítása: `nbf` (K), `repository_owner` (P) — 06w jelentés

**Státusz: megvalósítva és helyben mérve (implemented, szintetikus + a valódi állításkészletekből származtatott kontrollokkal); push, PR és merge nincs.** Ez a jelentés a `c-c3-contract-amendment.md` (sha256 `d02ab728cd56de604211324e4738d3fac2ad99b8a426733113e04eac27e928af`) megvalósítását írja le. A szerződés-pontosítás digestjét és időpontját a megvalósítás **előtt** rögzítettem (`output/remeasure/PREIMPL-DIGESTS.txt`, 2026-11-24T20:47:19Z). A 06v harness és a #93 érintetlen; az eredeti **36/38** mérés történeti tény marad, ez a jelentés egy **külön azonosított, újabb mérési állapotról** szól. Nem M-E1 ítélet: az M-E1 INCONCLUSIVE, a P sor `NOT-READ`, a P-c/F nem mért.

## 1. Mi változott

**`output/harness/read-me1.py`** (a 06v másolatából, 5 helyen; a többi fájl a 06v-tal bájtra azonos: `me1-controls.py`, `fetch-me1.sh`, `fetch-jwks.sh`, `test-fetch-me1.py`, `test-me1-body.py`):
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:69` `TOLERANCE` 120 → **60** s; `:70` új `NBF_SKEW = 60`.
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:100` új `numeric_date()`: nem logikai, nem negatív **egész** (I1; szigorúbb, mint az RFC 7519).
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:397` az `iat`/`exp` ellenőrzése a `numeric_date()`-et használja (a "bool" kizárás az `exp`-re is kiterjed).
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:401` új sor: **`OIDC not-before (nbf) present, valid, consistent with iat`**: `numeric_date(nbf)` és `nbf <= iat + NBF_SKEW`. Nincs alsó korlát (I4). Az `iat < exp` összefüggés továbbra is az `OIDC issued inside the attempt window` sor része.
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:682` `P_CLAIMS` + `repository_owner` (16 K + 9 P + 3 S); a `repository_owner_id` változatlanul K.
- `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:913` a szintetikus `good_claims()` a valódi alakot hordozza: `repository_owner`, `nbf = iat - 300`.

**`output/harness/test-pcv.py`:** `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/test-pcv.py:182` kezdettel új blokk (39 ellenőrzés: V3t időszemantika és határértékek, V3o `repository_owner`), és 10 új beültetett hiba a `MUTATIONS` listában (`jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/test-pcv.py:338`).

## 2. Az értelmezések és az új megállapítás (kimondva)

- **I1 NumericDate = nem logikai, nem negatív egész.** Szigorítás; a valódi tokenek egészet hordoznak.
- **F-T-1 (új megállapítás, az én megvalósításom közben): a 06v kód az `iat` ablakánál 120 másodperc toleranciát használt, a döntés szerint az óraeltérés legfeljebb 60 másodperc.** A 06w a toleranciát 60-ra szigorítja. A valódi bizonyítékokban az `iat` az ablak kezdete után 7–8 másodperccel, a vége előtt 425–429 másodperccel van (A, B, P1, P2), tehát a szigorítás egyetlen valódi bizonyítékot sem érint. **Ez értelmezés:** ha a tulajdonos a 60 másodpercet csak az `nbf`–`iat` összefüggésre értette, a 120 visszaállítása külön döntés. A szigorúbb irányt választottam (a szerződés lazítása tilos volt).
- **I3 a K-idő szabály:** az időmezőknél a szemantikai megsértés számít; a nem-idő K-állításoknál (16) a "bármely változás `NOT-MET`" szabály változatlan.

## 3. Regresszió: a 06v minden korábbi ellenőrzése a 06w harnessen

| Készlet | 06v (baseline, ugyanazon a gépen) | 06w | Eltérés |
|---|---|---|---|
| `read-me1.py --selftest` | 120 ok / 0 FAIL | 120 ok / 0 FAIL | nincs |
| `me1-controls.py --selftest` | 50 / 0 | 50 / 0 | nincs |
| `test-pcv.py --selftest` | 106 / 0 | **145 / 0** | +39 új, mind ok; a 106 régi azonosító mind jelen van, státuszuk azonos |
| `test-pcv.py --mutations` | 23/23 elfogva | **33/33 elfogva** | +10 új beültetett hiba |
| `test-fetch-me1.py` | 64 / 0 | 64 / 0 | nincs (egy címke véletlen tmp-könyvtárnevet tartalmaz, ezért az azonosító-összevetésben 1 "hiányzó" + 1 "új" sor: nem valódi eltérés) |
| `test-me1-body.py <workflow>` | 23 / 0 | 23 / 0 | nincs |

**Nincs egyetlen korábbi ellenőrzés, amelynek kimenetele a szerződés miatt szükségszerűen változott volna, és nincs indokolatlan új piros.** A 06v `test-me1-body.py` alapértelmezett workflow-útvonala (`harness/../payload/.github/workflows/me1-evidence.yml`) a 06v-ban nem létezik (a payload `p1/` és `p2/` alatt van): ez egy **már létező 06v hiba**, a teszt a workflow-t nem a verifiert méri; ezért mindkét példányon explicit útvonallal futtattam, a hibát nem javítottam (hatókörön kívül).

## 4. Új tesztek (39) és a beültetett hibák (10)

- **V3t nbf:** `iat`, `iat+60` (határérték) elfogadva; `iat+61`, `iat+1 000 000`, hiányzó, string, `true`, `null`, tört, negatív `nbf` → `NOT-MET`; `iat-10 000` és `0` elfogadva (nincs alsó korlát); az `iat+61` esetben **csak** az `nbf` sor bukik; a megengedett tartományon belüli változtatás egyetlen sor státuszát sem változtatja.
- **V3t iat/exp:** hiányzó `iat`/`exp`, `exp = iat`, `exp < iat`, nem egész `iat`/`exp` → `NOT-MET`.
- **V3t tolerancia:** `iat = ablak_kezdet − 60` és `ablak_vég + 60` → a sor `MET`; `−61` és `+61` → `NOT-MET`. **Artifact:** `exp + 60` → `MET`, `exp + 59` → `NOT-MET`.
- **V3t aktuális idő (N7):** a verdikt és minden sor státusza azonos, ha a `time.time` 1970-re, 2030-ra és 2096-ra van állítva; statikusan a `read-me1.py`-ban nincs `time.time(`, `datetime.now`, `utcnow`, `time.monotonic`, `date.today`.
- **V3o `repository_owner`:** 16 K + 9 P + 3 S, a névmező P és nem K, az azonosító K; a tokenmező mind osztályozott; a név megváltoztatása (4 érték), eltávolítása, és mind a 12 P/S állítás együttes megváltoztatása → a verdikt és minden sor státusza változatlan; a P-jelentés sor felsorolja.
- **Beültetett hibák (mind elfogva):** az `nbf` figyelmen kívül hagyása; hiányzó `nbf` elfogadása; határérték-eltolás (`<` a `<=` helyett); 61 s tolerancia; az `nbf` összevetése az aktuális órával; a 120 s tolerancia visszaállítása; az aktuális óra bevonása az `iat` elfogadásába; tört NumericDate elfogadása; a `repository_owner` K-ként kötése; a `repository_owner` kivétele a P osztályból.

## 5. A C-c3 újramérése a valódi állításkészleteken (06w; a 06v mérés a `pcf-ps/` alatt változatlan)

Eljárás: a 06v-ban használt származtatott kontroll (a valódi futás valódi állításkészlete, eldobható teszt-kulccsal újraaláírva, az evidence másolatán), a 06w harnessen, a 06w szemantikával. Minden korábbi evidence-fa (A, A2, B) változatlan (`remeasure/trees-before.txt`, a futás előtt és után azonos).

| Tétel | 06v (2026-11-24, változatlan) | 06w |
|---|---|---|
| E2 valódi állítások osztályozása | NOT-MET (`repository_owner`) | **MET** (4 token × 31 állítás, osztályozatlan: nincs) |
| E3a származtatott baseline | 2/2 | **2/2** |
| E3b 16 nem-idő K-állítás | 32/32 | **32/32** |
| `nbf` | 2 NOT-MET (a változtatás elfogadva) | a szemantika szerint: lásd E3t |
| E3t K-idő szemantika (11 eset × 2 alap) | nem létezett | **22/22 MET**: `iat` ablakon kívül, `exp` túl késő, `exp = iat`, `nbf` az `iat+60` fölött (`+61`, `+1 000 000`), hiányzó, string, tört → `NOT-MET` a megfelelő soron; `nbf = iat+60`, `= iat`, `= iat−10 000` → elfogadva, minden sor státusza azonos |
| E3c P/S változtatás, 12 állítás (a `repository_owner`-rel) külön és együtt | 24/24 (11 állítás) | **26/26** |
| E4 valós P/S értékek A vs B | `run_number`, `jti` tér el | ugyanez; a `repository_owner` azonos |

## 6. Korlátok (nem elrejtve)

1. A származtatott kontroll teszt-kulcsos újraaláírás: nem egy valódi, issuer által aláírt token átírt állítással (az lehetetlen).
2. **A 60 másodperces tolerancia értelmezése (F-T-1) a tulajdonos megerősítésére vár.**
3. Az `nbf` szemantika csak felső korlátot ír elő (I4); alsó korlátot a verifier nem ellenőriz.
4. Az újramérés ugyanarra az egy szervezetre, egy commitra, két valódi futásra (A, B) és a P1/P2 osztályozásra vonatkozik; a P sor továbbra is `NOT-READ`, a P-c/F nem mért, az R2/R4, a V4/B lane nem futott.
5. A `test-me1-body.py` alapértelmezett útvonal-hibája (06v) nem javított.
6. A harness mellé a hookok generált `*.yaml` melléktermékeket hoztak létre; ezek nincsenek a commitban (explicit fájllista).
7. A 06w nincs mergelve, és a `jobs/index.yaml` nincs frissítve; a PR és a merge külön tulajdonosi döntés.

## 7. Claim-evidence

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Az `nbf` K-követelményként kötelező, érvényes NumericDate és `nbf ≤ iat + 60` | implemented | `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:401` (sor), `:70` (`NBF_SKEW`), `:100` (`numeric_date`); `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/test-pcv.py:182` blokk, `remeasure/tests/pcv-selftest.txt` (145/0) | határérték- és negatív tesztek, 4 beültetett hiba elfogva | az alsó korlát nincs (I4, szerződés szerint) |
| Az óraeltérés legfeljebb 60 s az `iat` ablaknál | implemented (értelmezés, F-T-1) | `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:69`, `:397`; V3t határérték tesztek (±60 / ±61) | határérték tesztek, a 120 s visszaállítása elfogva | a tulajdonos más értelmezése esetén lazítás külön döntés |
| A történeti bizonyíték elfogadása nem függ az aktuális rendszeridőtől | implemented | `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/test-pcv.py:228` (óra 1970/2030/2096), statikus ellenőrzés a `read-me1.py` forrásán | órahamisítás + kódszkennelés, 2 beültetett hiba elfogva | csak a verifier kódja, nem a hívó környezet |
| A `repository_owner` P osztályú, a `repository_owner_id` K | implemented | `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/read-me1.py:682`; `jobs/relay-ci-parity-06w-me1-c-c3-nbf-owner/output/harness/test-pcv.py:250` (12 P/S együtt) | invariancia tesztek, 2 beültetett hiba elfogva | a név változásával a bizonyíték értelmezése emberi feladat marad |
| Nincs regresszió a 06v ellenőrzésein | measured | `remeasure/baseline-06v/*`, `remeasure/tests/*` (azonosító-összevetés: 0 hiányzó, 0 státuszváltozás) | ugyanazon a gépen futtatott baseline és az új készlet összevetése | a baseline az én futtatásom, független újrafuttatás nincs |
| A C-c3 a valódi állításkészleteken a 06w szemantikával teljesül | measured (származtatott) | `remeasure/E3/results-table.txt`, `remeasure/derived_ps_06w.py` | valódi állításkészlet teszt-kulcsos újraaláírással, evidence-másolaton | nem valódi, issuer által aláírt átírt token |
| Az eredeti 36/38 mérés változatlan | verified | `~/.cache/ci-lab/pcf-ps/RESULT.md` (sha256 `b923617ec6de4bbddc67afb0232f77e13461f38e4b9371717fb9ee97d4821eca`), a 06v harness fájljai érintetlenek | digest és `cmp` | nincs |
| A P-c/F és a P sor | NOT-READ | `c-c3-contract-amendment.md` 6. szakasz | nem mértük, a B lane és új futás kell | az M-E1 INCONCLUSIVE marad |

## 8. Digestek

- `output/harness/read-me1.py` (06w): `7ccd9c6b60ac3d87fe12965f741dbb212f4150cb0246b15f3e0e02c9bac3d7ac` (06v: `994fdbf1a6a15b4e1127250ea2c7e96d79195b85baa986a2a57884b379d3f471`)
- `output/harness/test-pcv.py` (06w): `9abf4ae185540b3e83864c3d4940bb39c5f3a50e0b7aeaace3ba5347c6b0b786` (06v: `70041a34a310fff9f784a90ce36eb594489b929a942fa04721c933debcf2b016`)
- `output/c-c3-contract-amendment.md`: `d02ab728cd56de604211324e4738d3fac2ad99b8a426733113e04eac27e928af`
- `output/remeasure/SHA256SUMS`: `b00c9f3f0490977484f2567df80ed09b880ae96ced7824dee997da3f78c43422` (a SHA256SUMS a `remeasure/` könyvtár fájljait listázza; ez a jelentés és a harness fájlok digestje fent)
