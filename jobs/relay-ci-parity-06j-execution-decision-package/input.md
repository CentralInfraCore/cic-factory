# relay-ci-parity-06j-execution-decision-package — végrehajtási döntési csomag a feltáró mérésekhez (CIC_Relay #212, 7. lépés)

## Kontextus

A #81 lezárta a feltáró mérések tervét (26 mérési tétel, 1 dokumentált megfigyelhetőségi korlát). A terv 6. és 7. szakasza tulajdonosi beavatkozásokat (O-1…O-6) és nyitott kérdéseket (K-1…K-7) sorol. Tulajdonosi GO (2026-11-22): **végrehajtási döntés-előkészítés**, kizárólag a K-1–K-7 és az O-1–O-6 rendezésére készített döntési csomag; tételenként ajánlás, indoklás, előfeltételek és erőforrásigény; cél, hogy a tényleges mérés előtt valamennyi tulajdonosi döntés egy helyen meghozható legyen.

## Hatókör

**Kizárólag döntési csomag.** Nincs mérés, kulcsművelet, repólétrehozás, konfigurációmódosítás, implementáció. A csomag nem hoz döntést a tulajdonos helyett; ajánlást ad, a döntés a tulajdonosé. Írási művelet a mérési környezeten nem történik; az egyetlen környezeti tevékenység néhány **csak olvasó** metaadat-lekérdezés (a repók láthatósága, a szervezet csomagja), amelyek eredménye „olvasott" jelöléssel szerepel.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (2.5, 3. szakasz, 5. fázistábla, 6. O-lista, 7. K-lista)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (2. szakasz: a korábbi scratch környezet, az App, a jogosultságok)
- `jobs/relay-ci-parity-06e-open-case-triage/output/open-case-triage.md` (3.3, 5. szakasz: a 4. lépés)

## Elfogadhatatlan rövidítések

- NEM fogadható el: ajánlás indoklás nélkül ≠ döntési csomag; az ajánlás a tulajdonos döntése helyett nem tekinthető meghozottnak.
- NEM fogadható el: a becsült erőforrásigény mértként való jelentése; a becslés ≠ mérés.
- NEM fogadható el: hitelesítő adat, kulcs vagy token átadása nekem a csomag részeként; a csomag a kulcs nem hozzám kerülésére épül.
- NEM fogadható el: a döntési csomag megléte ≠ működik; a jóváhagyott ajánlás ≠ sikeres mérés, és a tulajdonosi előkészítés ≠ elvégzett végrehajtás.
- NEM fogadható el: bármilyen írási művelet a mérési környezeten (repó, App, beállítás) a döntés előtt.
- NEM fogadható el: a dokumentált (de ebben a sessionben nem ellenőrzött) platformviselkedés mértként való jelölése.

## Output

- `output/execution-decision-package.md` — döntési összefoglaló (egy üzenetben jóváhagyható), tételenkénti ajánlás (K-1–K-7, O-1–O-6, plusz az új K-8), indoklás, alternatívák, előfeltételek, erőforrásigény, visszafordíthatóság, függőségi sorrend, kockázatok; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06j-execution-decision-package`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
