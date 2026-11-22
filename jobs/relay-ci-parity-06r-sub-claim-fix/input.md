# relay-ci-parity-06r-sub-claim-fix — az M-E1 olvasó `sub`-elvárásának javítása (CIC_Relay #212, 15. lépés)

## Kontextus

Az első M-E1 mérési futás (45063800073, a labor X repó, `me1-evidence.yml`, 1. kísérlet, `success`) bizonyítékának kiolvasása `EVIDENCE NOT BOUND (NOT MET)` lett egyetlen sor miatt: a token `sub` állítása a **numerikus tulajdonos- és repó-azonosítót is tartalmazza** (`repo:OWNER@OWNERID/REPO@REPOID:ref:refs/heads/main`), az olvasó a dokumentált egyszerű alakot várta (`repo:OWNER/REPO:ref:refs/heads/main`). Az azonosítók egyeznek az API-éval és a `repository_id`/`repository_owner_id` állításokkal; a többi 21 ellenőrzés `MET` (a PR-leírás és ez a szöveg eredetileg tévesen 22-t írt; javítva a 06s jelentésben, errata). A hiba az olvasó dokumentációra épülő elvárásában volt, nem a platformbizonyíték kötésében. Tulajdonosi GO (2026-11-22): az olvasó `sub`-elvárásának javítása külön PR-ban. K-5: 8/300.

## Hatókör

**Kizárólag az olvasó javítása és a hozzá tartozó tesztek, leírás.** Nem indítok új futást, nem töltök le új bizonyítékot, nem módosítom az X repót. A meglévő bizonyítékot a javítás mergelése után a tulajdonos olvastatja újra. A javított olvasó új job alatt él (a 06q a történeti állapot). Az M-E1 ítélete nyitott; a P (PR-szerző befolyása) `NOT-READ` marad.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06q-me1-measurement-package/output/harness/read-me1.py`, `fetch-me1.sh`, `fetch-jwks.sh`, `test-fetch-me1.py` (a javítandó, mergelt változat)
- `jobs/relay-ci-parity-06q-me1-measurement-package/output/me1-measurement-package.md`

## Elfogadhatatlan rövidítések

- NEM fogadható el: a `sub` ellenőrzés kikapcsolása vagy "mindent elfogad" lazítás; az azonosítós alakban a számoknak az API-éval **egyezniük kell**.
- NEM fogadható el: az első, `NOT-MET` kiolvasás elhallgatása vagy átírása; a jelentésben az első és a javított olvasat külön szerepel.
- NEM fogadható el: a javított olvasó előzetes (helyi) futásának mérési eredményként kezelése; a javítás megléte ≠ működik a valódi platformon, és a zöld teszt ≠ sikeres mérés (a javítás ≠ az M-E1 ítélete).
- NEM fogadható el: az `EVIDENCE BOUND` olvasatból az M-E1 `PASS` következtetése; a P `NOT-READ`, az ítélet legfeljebb `INCONCLUSIVE`.
- NEM fogadható el: új futás, bizonyíték-letöltés, írási művelet az X repón vagy az éles szervezetben; hitelesítő adat átadása nekem.

## Output

- `output/sub-claim-fix.md` — a mért megfigyelés (a valódi token szerkezete), a javítás, a tesztek, az újraolvasás terve, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/harness/read-me1.py`, `output/harness/fetch-me1.sh`, `output/harness/fetch-jwks.sh`, `output/harness/test-fetch-me1.py`

## Git

Feature branch `feature/relay-ci-parity-06r-sub-claim-fix`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
