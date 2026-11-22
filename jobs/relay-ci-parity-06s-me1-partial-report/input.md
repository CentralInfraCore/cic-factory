# relay-ci-parity-06s-me1-partial-report — az M-E1 részjelentés (CIC_Relay #212, 16. lépés)

## Kontextus

Az első M-E1 mérési futás (45063800073, a labor X repó, `me1-evidence.yml`, 1. kísérlet, `success`) bizonyítékát a tulajdonos letöltötte és két olvasóval kiolvasta: a 06q olvasójával `EVIDENCE NOT BOUND (NOT MET)` (a `sub` dokumentációra épülő elvárása miatt), a javított 06r olvasóval (#90, merge `a4be7ce`) `EVIDENCE BOUND, P NOT READ`. Tulajdonosi GO (2026-11-22): az M-E1 részjelentés elkészítése külön PR-ban, a rögzített hatókörrel; **az M-E1 végső ítélete nyitott marad**. K-5: 8/300.

## Hatókör

**Kizárólag jelentés (dokumentum), plusz az errata két mergelt fájlban.** Nem hajtok végre semmit az X repón vagy az éles szervezetben, nem indítok futást, nem töltök le bizonyítékot, nem mondom ki az M-E1 ítéletét, és nem tervezek bele új mérést (a P és az S/R mérőcsomag tervezési tétel, külön GO).

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (3.E M-E1, 2.2 PK)
- `jobs/relay-ci-parity-06q-me1-measurement-package/output/me1-measurement-package.md`
- `jobs/relay-ci-parity-06r-sub-claim-fix/output/sub-claim-fix.md`
- `jobs/relay-ci-parity-06p-phase0-report/output/phase0-report.md` (a 0. fázis eredménye, a P3 megfigyelés)

## Elfogadhatatlan rövidítések

- NEM fogadható el: az M-E1 `PASS`-ának vagy `FAIL`-jének kimondása; az `EVIDENCE BOUND` ≠ `PASS`, az olvasó zöld kimenete ≠ sikeres M-E1 mérés, a P `NOT-READ`, az ítélet előzetesen `INCONCLUSIVE`.
- NEM fogadható el: az egyetlen futásból, egy szervezetből, egy platform-pillanatképből származó megfigyelések általánosítása; a mért megfigyelés ≠ platformtulajdonság, és a labor ≠ production.
- NEM fogadható el: az első, `NOT MET` olvasat elhallgatása vagy átírása; a két olvasat külön szerepel, az olvasó hibájával és javításával.
- NEM fogadható el: a platform-eredet hitelesség összemosása a GitHubtól való függetlenséggel; a bizonyíték a GitHub aláírásán és a tulajdonosi gép sértetlenségén alapul.
- NEM fogadható el: új mérés, új futás, bizonyíték-letöltés, írási művelet az X repón vagy az éles szervezetben; hitelesítő adat vagy a tokenből az `actor`/`jti` értéke.

## Output

- `output/m-e1-partial-report.md` — azonosítók, a két olvasat, a valódi token szerkezete, mért megfigyelések és korlátaik, a mérőcsomag története és a saját hibák (errata), az M-E1 állapota, a bizalmi határ, K-5, nyitott kérdések, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)

## Git

Feature branch `feature/relay-ci-parity-06s-me1-partial-report`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
