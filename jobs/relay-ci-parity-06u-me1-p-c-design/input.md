# relay-ci-parity-06u-me1-p-c-design — az M-E1 P-c mérési terve (CIC_Relay #212, 18. lépés)

## Kontextus

A P és S/R mérési terv (#92, merge `5ba9f5c`) a P-t három tulajdonságra bontotta: **P-a** (elfogadtathatóság), **P-b** (módosíthatóság), **P-c** (a bizonyíték előállításának, kiválasztásának, elnyomásának és publikálásának szerzői befolyása), és kimondta, hogy a **P-c nem vizsgált**. A tulajdonosi irány (2026-11-23): a #81 teljes P-követelménye marad érvényben (D8), a PASS a P-c-hez kötött, ezért a P-c külön mérési tervet kap. Tulajdonosi GO (2026-11-23): a P-c külön mérési tervének kidolgozása, **kizárólag tervezés**. A D1–D8 formális rögzítése a tulajdonosnál nyitott; a terv a D8 teljes követelményével mint munkafeltevéssel dolgozik. M-E1: előzetesen `INCONCLUSIVE`. K-5: 8/300.

## Hatókör

**Kizárólag terv (dokumentum).** Nem készítek workflow-fájlt, szkriptet vagy kódot, nem indítok futást, nem töltök le bizonyítékot, nem módosítom az X repót. A terv a megvalósítás tartalmát és a tulajdonosi döntési pontokat rögzíti; a megvalósítás és a mérés külön GO. A terv csak olvasó, nyilvános metaadat-lekérdezésekből és a tulajdonos gépén már meglévő bizonyítékból merít ténylegesen mért tényeket.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06t-me1-p-sr-design/output/me1-p-sr-design.md` (1.1 a P három tulajdonsága, 2. fenyegetési modell, 6. elfogadási kritériumok, 9. D1–D8)
- `jobs/relay-ci-parity-06s-me1-partial-report/output/m-e1-partial-report.md` (a mért megfigyelések, a bizalmi határ)
- `jobs/relay-ci-parity-06r-sub-claim-fix/output/harness/read-me1.py`, `fetch-me1.sh` (a meglévő olvasó és gyűjtő)
- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (3.E M-E1, 2.2 PK)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a P-c „megoldottnak" minősítése azzal, hogy a szerző befolyása az elérhetőségre nulla; a szerző egy írási jogú azonosítóval **mindig elnyomhat** (futást törölhet, megszakíthat, artifactot törölhet), a követelmény ezért biztonságos hibaállapot, nem a lehetőség hiánya, és ezt a terv kimondja és a tulajdonosnak jóváhagyásra teszi.
- NEM fogadható el: a szerző lehetőségeinek (megszakítás, törlés, újraindítás, szöveg-választás) mértként jelölése; a platform ezen képességei dokumentált, nem mért tények, mert a mérésükhöz második (alacsonyabb jogú) azonosító kell, amely nincs (B sor).
- NEM fogadható el: a szerző által választott szövegek (`workflow`, `actor`, `head_ref`) kötő állításként használata; a terv megléte ≠ működik, és a terv elfogadása ≠ sikeres mérés.
- NEM fogadható el: érvényes (le nem járt) token bármely csatornán; az M-E1 ítéletének (PASS/FAIL/INCONCLUSIVE) előzetes kimondása; a laborbeli eredmény általánosítása a Relay-re vagy a production-re.
- NEM fogadható el: új futás, bizonyíték-letöltés, írási művelet az X repón vagy az éles szervezetben a tulajdonos nélkül.

## Output

- `output/me1-p-c-design.md` — a P-c meghatározása és a tulajdonosi jóváhagyást igénylő értelmezése, a fenyegetési modell (a szerző feltételezett képességei), a mért és dokumentált tények szétválasztása, a verifier-tulajdonságok és kontrolljaik, a mérési protokoll, a token-kezelés, az elfogadási kritériumok és az ítélet-leképezés, a K-5 keretigény, a megvalósítási csomag tartalma, a tulajdonosi döntési pontok, kockázatok, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)

## Git

Feature branch `feature/relay-ci-parity-06u-me1-p-c-design`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
