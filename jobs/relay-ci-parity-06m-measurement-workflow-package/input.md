# relay-ci-parity-06m-measurement-workflow-package — a 4.6b mérési workflow-csomag, 0. fázis (CIC_Relay #212, 10. lépés)

## Kontextus

A #83 (forgatókönyv) és a #84 (bootstrap) mergelve (505e639, bf654d1). A G0 technikailag teljesült az X repón (`ci-adversarial-lab`): bootstrap commit `0cbe3135…`, futás 45032657726 `success`, a védett `main` megköveteli a `lab-gate` checket (`strict=false`, `enforce_admins=true`). Tulajdonosi GO (2026-11-22): a 4.6b mérési workflow-csomag elkészítése külön PR-ban, aláírt committal és tartalmi review-val; K-5 ACCEPT, K-8 ACCEPT, G0 11(d) CONFIRMED (a tulajdonos szövege szerint).

## Hatókör

**Csak a 0. fázis (harness önellenőrzése, pozitív kontrollok).** A csomag két workflow-fájl, ezek ellenőrzője, és az eredményt olvasó harness-eszköz. **Nem** tartalmaz H1/H2 mérést (a K1/K2 környezetek nem használtak), nem hivatkozik a `CANARY_UNREFERENCED`-re, semmire, ami PR-szerzői kódot futtat privilegizált kontextusban (`pull_request_target`, `workflow_run`, `issue_comment`), és semmilyen környezetet. A fájlok az X repóba kerülnek, **a tulajdonos pusholja és PR-ozza (K-8)**; én nem írok az X repóra.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06k-phase0-owner-runbook/output/phase0-owner-runbook.md` (4.4–4.7, 4.8)
- `jobs/relay-ci-parity-06l-bootstrap-workflow/output/bootstrap-workflow.md` (2. szakasz megjegyzése a PR-eseményről)
- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (2.2 PK, 3.B M-B1/M-B2, 5. fázisok)
- `jobs/relay-ci-parity-06j-execution-decision-package/output/execution-decision-package.md` (K-5, 4.0 szerepek)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a PK ítélet összekeverése a platformtulajdonság ítéletével (a PK csak a mérőeszközről szól; a K1/K2/H1/H2 mérése nem ennek a csomagnak a tárgya).
- NEM fogadható el: az olvasó és az ellenőrző, amely nem tud bukni; beültetett hibák nélküli önteszt nem bizonyíték.
- NEM fogadható el: a csomag megléte vagy a helyi önteszt ≠ működik a GitHubon; a futási viselkedés és a napló formátuma dokumentált, nem mért, amíg a tulajdonos nem futtatta.
- NEM fogadható el: bármilyen hivatkozás a `CANARY_UNREFERENCED`, a `CANARY_BRANCHONLY`, a `CANARY_BRANCH_APPROVAL` titokra, `environment:`, nem SHA-hoz rögzített külső action, vagy írási jog.
- NEM fogadható el: írási művelet az X repón vagy az éles szervezetben a tulajdonos futtatása nélkül; hitelesítő adat átadása nekem.

## Output

- `output/measurement-workflow-package.md` — leírás, fájlok és blob-SHA-k, tulajdonosi szállítás (PR az X-en), a PK-futás és kiolvasás lépései, K-5 elszámolás, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/payload/.github/workflows/lab-gate-pr.yml`, `output/payload/.github/workflows/pk-canary-channels.yml`
- `output/check-lab-workflows.py` — fail-closed csomag-ellenőrző önteszttel
- `output/harness/read-pk.py`, `output/harness/fetch-pk.sh` — a PK kiolvasása

## Git

Feature branch `feature/relay-ci-parity-06m-measurement-workflow-package`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
