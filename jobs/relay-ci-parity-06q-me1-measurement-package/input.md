# relay-ci-parity-06q-me1-measurement-package — az M-E1 mérőcsomag előkészítése (CIC_Relay #212, 14. lépés)

## Kontextus

A 0. fázis a mérőeszköz oldalán lezárt (#88, merge `48ec263`): G0 teljesült, `PK MET` 20/20. Az 1. fázis első mérendő tétele az **M-E1**: milyen hiteles futási bizonyíték áll rendelkezésre. Tulajdonosi GO (2026-11-22): az M-E1 mérőcsomag előkészítése külön PR-ban. **A hatókör kizárólag az előkészítés és a tesztelés szintetikus adatokkal**; a tényleges mérés külön tulajdonosi GO-t igényel. K-5: 5/300.

## Hatókör

**Kizárólag csomag és leírás (dokumentum, workflow-fájl, ellenőrző, gyűjtő, olvasó).** Nem hajtok végre semmit a labor X repón: nincs szállítás, futás, bizonyíték-letöltés. A csomag szállítása és a futás külön tulajdonosi GO. A H1/H2 és a többi M-tétel nem része.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (2.2 PK, 3.E M-E1)
- `jobs/relay-ci-parity-06j-execution-decision-package/output/execution-decision-package.md` (K-5, K-7, 4. szakasz leállási küszöbök, 5.1 kapuk)
- `jobs/relay-ci-parity-06p-phase0-report/output/phase0-report.md` (a 0. fázis eredménye, P3 megfigyelés)
- `jobs/relay-ci-parity-06o-attach-summary-cli/output/harness/read-pk.py`, `fetch-pk.sh`, `test-fetch-pk.py` (a bevált gyűjtési és kötési minta)

## Elfogadhatatlan rövidítések

- NEM fogadható el: az M-E1 ítéletének (PASS/FAIL/INCONCLUSIVE) előzetes kimondása; a csomag megléte ≠ működik a GitHubon, és a szintetikus teszt ≠ mért platformviselkedés.
- NEM fogadható el: a workflow önbevallásának (a saját `context.json`) hiteles bizonyítékként kezelése; az önbevallás csak összevetett adat.
- NEM fogadható el: az olvasó, amely nem tud bukni; a hamis, szintetikus aláírású és eltérő mezős bizonyítékot el kell utasítania.
- NEM fogadható el: a PR-szerző befolyásolásának (P) eldöntése pull_request-futás bizonyítéka nélkül; az `INCONCLUSIVE`/`NOT-READ` marad.
- NEM fogadható el: írási művelet az X repón vagy az éles szervezetben, futás indítása, bizonyíték letöltése; hitelesítő adat átadása nekem.

## Output

- `output/me1-measurement-package.md` — leírás, az M-E1 a #81 szerint, a csomag, a tulajdonosi szállítás és futás lépései, K-5 előszámítás, a gyanús-workflow jelölés (P3) előre betervezve, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`), mit nem állít
- `output/payload/.github/workflows/me1-evidence.yml`
- `output/check-me1-workflow.py` — fail-closed ellenőrző beültetett hibákkal
- `output/harness/read-me1.py`, `output/harness/fetch-me1.sh`, `output/harness/test-fetch-me1.py` — az olvasó, a gyűjtő és a mockolt lánc-teszt

## Git

Feature branch `feature/relay-ci-parity-06q-me1-measurement-package`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
