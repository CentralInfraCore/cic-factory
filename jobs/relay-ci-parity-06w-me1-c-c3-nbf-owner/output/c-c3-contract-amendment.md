# #212 M-E1 — a C-c3 (V3) szerződés pontosítása: az `nbf` K-követelmény és a `repository_owner` P-osztály (06w)

**Státus: szerződés-pontosítás (concept → a 06w megvalósítással implemented, lásd `c-c3-nbf-owner.md`).** Ez a dokumentum **nem írja át** a #93 (`jobs/relay-ci-parity-06u-me1-p-c-design/output/me1-p-c-design.md`, V3 és C-c3) szövegét, és nem minősíti át a 06v harness korábbi mérési eredményeit. A #93 és a 06v harness érintetlen; ez a dokumentum **külön azonosított, újabb szerződés-állapotot** rögzít, és a 06w harness ehhez tartozik.

## 1. Eredet

Tulajdonosi architekturális döntések, 2026-11-24, két mérési megállapítás nyomán (`~/.cache/ci-lab/pcf-ps/RESULT.md`, sha256 `b923617ec6de4bbddc67afb0232f77e13461f38e4b9371717fb9ee97d4821eca`):

- **F-PS-1:** a `read-me1.py` az `nbf`-et sehol nem értékeli, holott a #93 V3 K-táblájának utolsó sora (`iss`, `aud`, aláírás, `iat`/`exp`/`nbf`) az időablakhoz köti. Mért: 36/38 `MET`, a 2 `NOT-MET` az `nbf`.
- **F-PS-2:** a `repository_owner` (a tulajdonos neve) a #93 osztály-táblájában nincs osztályozva; a verifier figyelmen kívül hagyja.

**Döntés 1.** Az `nbf` K-követelmény marad. A történeti OIDC-bizonyítékot az eredeti futás időkontextusában kell vizsgálni, nem a verifier aktuális órájához képest.
**Döntés 2.** A `repository_owner` P osztályú (információs, nem döntésképző); a `repository_owner_id` K marad.

## 2. Normatív szabályok (a döntés szerint)

| # | Szabály |
|---|---|
| N1 | Az `nbf` kötelező, érvényes NumericDate. |
| N2 | Az `iat` és az `exp` kötelező, érvényes NumericDate. |
| N3 | Időbeli sorrend: `nbf ≤ iat + 60 s` **és** `iat < exp`. |
| N4 | Az elfogadott óraeltérés legfeljebb 60 másodperc. A 60 másodperc a tolerancia, nem általános felmentés a többi időbeli ellenőrzés alól. |
| N5 | Az `iat` a jóváhagyott futási időablakba esik. |
| N6 | Az `exp` az artifact létrejötte előtt legalább 60 másodperccel lejárt. |
| N7 | Az aktuális rendszeridő nem része a történeti bizonyíték elfogadási feltételének. |
| N8 | `repository_owner_id`: K (kötelező kötés az API owner azonosítójához és a politikához). `repository_owner`: P (jelentve, nem ítélve); értékének változása nem változtatja a verdiktet, és semmilyen K-állítás nem származtatható belőle. |

## 3. Értelmezések (kimondva, mert a döntés szövege nem mondja ki külön)

- **I1 — NumericDate.** A verifierben érvényes NumericDate = **nem logikai (bool), nem negatív egész szám** (JSON egész). Ez szigorúbb, mint az RFC 7519 (amely tört számot is enged); a valódi tokenek egész értéket hordoznak, és az `iat`/`exp` ellenőrzése eddig is egész számot követelt. Szigorítás, nem lazítás.
- **I2 — az óraeltérés (N4) hatóköre.** A döntés táblája az óraeltérést általános korlátként nevezi meg (legfeljebb 60 s). A 06v kód az `iat` időablakánál 120 másodperces toleranciát használt (`TOLERANCE = 120`), ami a normatív 60 másodpercnél **nagyobb**. A 06w a toleranciát **60 másodpercre szigorítja**. Mért indok: a valódi bizonyítékokban az `iat` az ablak kezdete után 7–8 másodperccel van, az ablak vége előtt 425–429 másodperccel (A, B, P1, P2), tehát a szigorítás egyetlen valódi bizonyítékot sem érint. Ez **értelmezés**: ha a tulajdonos az N4-et csak az `nbf`–`iat` összefüggésre értette, a 120 másodperc visszaállítása külön döntés (a szigorítás a szerződés felé biztonságos irány).
- **I3 — a C-c3 K-szabály pontosítása az időmezőkre.** A korábbi "bármely K-állítás megváltoztatása kötelezően `NOT-MET`" szabály a **nem-idő K-állításokra** (16 db: `repository`, `repository_id`, `repository_owner_id`, `workflow_ref`, `job_workflow_ref`, `event_name`, `ref`, `sub`, `sha`, `workflow_sha`, `job_workflow_sha`, `run_id`, `run_attempt`, `check_run_id`, `iss`, `aud`) **változatlanul érvényes**. Az **időmezőkre** (`iat`, `exp`, `nbf`) a szemantikai szerződés megsértése számít, nem a bájtérték változása: a megengedett tartományon belüli változtatásnak nem kell elutasításhoz vezetnie (de nem is tilos), a tartományon kívülinek `NOT-MET`-et kell adnia.
- **I4 — az `nbf` alsó határa nincs.** Az N3 csak felső korlátot ad (`nbf ≤ iat + 60 s`); a valódi tokenekben `nbf = iat − 300`. Alsó korlátot a szerződés nem ír elő, ezért a verifier nem is ellenőriz (nem találom ki).

## 4. Osztályok a pontosítás után

| Osztály | Állítások | Szabály |
|---|---|---|
| **K (16, nem-idő)** | `repository`, `repository_id`, `repository_owner_id`, `workflow_ref`, `job_workflow_ref`, `event_name`, `ref`, `sub`, `sha`, `workflow_sha`, `job_workflow_sha`, `run_id`, `run_attempt`, `check_run_id`, `iss`, `aud` | a politikához / API-hoz kötött; bármely változtatás `NOT-MET` |
| **K-idő (3)** | `iat`, `exp`, `nbf` | az N1–N7 szabályokhoz kötött; a szemantikai megsértés `NOT-MET` |
| **P (9)** | `actor`, `actor_id`, `ref_type`, `ref_protected`, `repository_visibility`, `runner_environment`, `run_number`, `jti`, **`repository_owner`** | jelentve, nem ítélve; változtatásuk nem változtatja a verdiktet |
| **S (3)** | `workflow`, `head_ref`, `base_ref` | a verifier nem használja; változtatásuk nem változtatja a verdiktet |

A valódi tokenek 31 állításából 31 osztályozott (16 + 3 + 9 + 3).

## 5. A mérési elvárások (rögzítve a megvalósítás ELŐTT)

1. **Nincs regresszió:** a 06v harness minden korábbi, zöld ellenőrzése a 06w harnessen is zöld marad, **kivéve** azokat, amelyek kimenetele a fenti szerződés miatt szükségszerűen változik; ezeket a jelentésben egyenként meg kell nevezni és indokolni. Egy nem indokolható új piros ellenőrzés regresszió.
2. **Az `nbf` szemantika (új tesztek):** hiányzó `nbf` → `NOT-MET`; nem egész / logikai / null / tört / negatív `nbf` → `NOT-MET`; `nbf = iat + 60` → elfogadva (határérték); `nbf = iat + 61` és `nbf = iat + 1 000 000` → `NOT-MET`; `nbf = iat − 300` (valódi) és `nbf = iat − 10 000` → elfogadva; hiányzó `iat` / `exp` → `NOT-MET`; `exp = iat` és `exp < iat` → `NOT-MET`.
3. **Időablak és tolerancia (határérték):** `iat = ablak_kezdet − 60` és `ablak_vég + 60` → elfogadva; `−61` és `+61` → `NOT-MET`.
4. **Az `exp` és az artifact (határérték):** artifact létrejötte `exp + 60` → elfogadva; `exp + 59` → `NOT-MET`.
5. **Aktuális rendszeridő (N7):** ugyanaz a bizonyíték, ugyanaz a verdikt, ha az óra (`time.time`) a távoli múltra / jövőre van állítva; a `read-me1.py` kódjában nincs az elfogadást befolyásoló aktuális-idő olvasás (statikus ellenőrzés).
6. **`repository_owner` (N8):** változtatása → a verdikt és minden sor státusza változatlan; a P-jelentés sor (`claim classes P and S`) felsorolja; a valódi tokenek mind a 31 állítása osztályozott.
7. **Kikényszerítés:** az `nbf`-ellenőrzés és a P-besorolás kikapcsolása/megtörése (beültetett hibák) a tesztmátrixban bukást okoz (mutációs ellenőrzés), az `nbf`-re legalább: figyelmen kívül hagyás, aktuális időhöz mérés, határérték-eltolás; a `repository_owner`-re: K-ként kötés.
8. **A C-c3 mátrix újramérése** a valódi állításkészletekkel (A2/policy A, B/policy B), a 06v-os mérés változatlan megőrzésével: a 16 nem-idő K-állítás 16/16 `NOT-MET`, az `iat`/`exp` kiterjesztett esetek `NOT-MET`, az `nbf` tartományon kívüli változtatása `NOT-MET` és a tartományon belüli **nem** utasít el, a P/S (12 állítás, a `repository_owner`-rel) 12/12 és az összes együtt változatlan.

## 6. Ami NEM változik, és ami nem része

- A 06v harness, a #93 és a 06v `p-implementation.md` érintetlen; a **36/38** eredmény történeti tény marad, nem minősül át.
- Nem része: új GitHub Actions dispatch, P-c/F, R2/R4, V4/B lane, PR-merge vagy lezárás, a verdikt-szabályok bármilyen más módosítása.
- A K-5 nem változik (offline munka).
