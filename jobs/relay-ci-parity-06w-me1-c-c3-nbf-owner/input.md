# relay-ci-parity-06w-me1-c-c3-nbf-owner — a C-c3 (V3) szerződés pontosítása és megvalósítása: az `nbf` K-követelmény, a `repository_owner` P-osztály (CIC_Relay #212, 20. lépés)

## Kontextus

A 06v harness P/S invariancia mérése (2026-11-24, `~/.cache/ci-lab/pcf-ps/RESULT.md`, sha256 `b923617ec6de4bbddc67afb0232f77e13461f38e4b9371717fb9ee97d4821eca`) két megállapítást adott: **F-PS-1** a `read-me1.py` az `nbf`-et nem értékeli, holott a #93 V3 K-táblájának `iat/exp/nbf` sora az időablakhoz köti (36/38 `MET`, a 2 `NOT-MET` az `nbf`); **F-PS-2** a `repository_owner` osztályozatlan. A tulajdonos 2026-11-24-én mindkettőről döntött: az `nbf` K-követelmény marad (a történeti bizonyíték az eredeti futás időkontextusában értékelendő, nem az aktuális órához képest; `nbf ≤ iat + 60 s`, `iat < exp`, óraeltérés legfeljebb 60 s), a `repository_owner` P osztályú, a `repository_owner_id` K marad. Tulajdonosi GO: a két döntés dokumentálása és a célzott megvalósítás, külön regressziós bizonyítással, külön ágon, automatikus merge nélkül.

## Hatókör

**Szerződés-pontosítás, célzott verifier-módosítás, tesztek, újramérés.** A 06v harness és a #93 **érintetlen**; a módosítás a 06w saját `output/harness` másolatán él. Az eredeti **36/38** mérés történeti tény, nem minősül át. Nincs új GitHub Actions dispatch, nincs P-c/F, R2/R4, V4/B lane, PR-merge vagy lezárás, nincs éles konfigurációmódosítás. A K-5 nem változik (offline munka). A szerződést lazítani nem szabad; ahol a döntés szövege nem mondja ki (NumericDate, a tolerancia hatóköre), az értelmezést ki kell mondani, és a szigorúbb irányt kell választani.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06u-me1-p-c-design/output/me1-p-c-design.md` (V3 osztály-tábla, C-c3)
- `jobs/relay-ci-parity-06v-me1-p-implementation/output/harness/` (az alap; érintetlen marad)
- `~/.cache/ci-lab/pcf-ps/RESULT.md` és `E3/results-table.txt` (a mérési megállapítások)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a szerződés illesztése a jelenlegi teszteredményekhez; az eredeti 36/38 utólagos átminősítése; a K-időmezők „bármely bájtváltozás = `NOT-MET`” szabályának fenntartása az időmezőkre (a döntés a szemantikai megsértést kéri).
- NEM fogadható el: üres vagy mindig igaz ellenőrzés; a megvalósítás ≠ működik, amíg a kontrollok bukásra is nem bizonyítottak (mutációs ellenőrzés); a zöld teszt ≠ sikeres mérés.
- NEM fogadható el: az aktuális rendszeridő bármilyen szerepe a történeti bizonyíték elfogadásában.
- NEM fogadható el: egy új, nem indokolható piros ellenőrzés elfedése; minden megváltozott kimenetel megnevezése és indoklása.

## Output

- `output/c-c3-contract-amendment.md` — a szerződés-pontosítás (N1–N8 normatív szabályok, az I1–I4 értelmezések, az osztályok, a mérési elvárások a megvalósítás előtt rögzítve)
- `output/c-c3-nbf-owner.md` — mit változtattunk, a regressziós és az új tesztek eredménye, a mutációs ellenőrzés, a valódi állításkészletes újramérés, korlátok, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/harness/read-me1.py`, `me1-controls.py`, `test-pcv.py`, `test-fetch-me1.py`, `test-me1-body.py`, `fetch-me1.sh`, `fetch-jwks.sh` (a 06v másolata, a `read-me1.py` és a `test-pcv.py` módosításával)
- `output/remeasure/` — az újramérés szkriptje, a kimenetek és a digestek

## Git

Feature branch `feature/relay-ci-parity-06w-me1-c-c3-nbf-owner`, aláírt commit, **nincs push és nincs automatikus merge**; a PR és a merge külön tulajdonosi döntés. A commitba **csak explicit fájllistával** kerül fájl (generált `.yaml` melléktermékek miatt).

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
