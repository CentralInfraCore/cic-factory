# relay-ci-parity-06v-me1-p-implementation — a P-a/P-b és P-c/V közös megvalósítási csomagja (CIC_Relay #212, 19. lépés)

## Kontextus

A P és S/R mérési terv (#92, merge `5ba9f5c`) és a P-c mérési terv (#93, merge `3116a7d`) mergelt. A tulajdonos rögzítette a D1–D8 és D-c1–D-c6 döntéseket (2026-11-23): D8 a teljes #81 követelmény marad, a P-a/P-b önmagában nem M-E1 PASS; D-c1 a P-c biztonsági követelménye a biztonságos hibaállapot; D-c2 előre rögzített döntési politika és konkrét futásazonosság, a checks API csak felderítés és keresztellenőrzés; D-c6 NEM: a P-c/V önmagában nem elég, a P-c/F is kell a teljes PASS-hoz. Tulajdonosi GO (2026-11-23): a P-a/P-b és P-c/V közös megvalósítási csomagjának elkészítése, **kizárólag szintetikus tesztekkel, új GitHub Actions-futás és X-repó írás nélkül**. M-E1: `INCONCLUSIVE`. K-5: 8/300.

## Hatókör

**Megvalósítás és szintetikus tesztek.** Nem indítok Actions-futást, nem írok az X repóba, nem nyitok PR-t, nem töltök le bizonyítékot, nem futtatom a tulajdonosi szkripteket valódi környezetben (a tesztek helyi bare repóval és hamis `gh`-val futnak). A `pull_request`-futások még nem mért állításainak szemantikája **hipotézis**. A P-c/F nem része a csomagnak, és teljes M-E1 PASS nem mondható ki. **A GO nem terjed ki** a megvalósítás merge-ére, az X-repóbeli PR-nyitásra, a D6/R2/R4 mérésekre, a B sorra és bármilyen új futásra.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06t-me1-p-sr-design/output/me1-p-sr-design.md` (1.1 P-a/P-b/P-c, 2. hipotézisek H1–H8, 3. protokoll, 5. kontrollok, 6. kritériumok)
- `jobs/relay-ci-parity-06u-me1-p-c-design/output/me1-p-c-design.md` (V1–V6, a döntési politika, K/P/S állításosztályok, 7. a megvalósítási csomag tartalma)
- `jobs/relay-ci-parity-06r-sub-claim-fix/output/harness/read-me1.py`, `fetch-me1.sh`, `fetch-jwks.sh`, `test-fetch-me1.py` (az alap)
- `jobs/relay-ci-parity-06q-me1-measurement-package/output/payload/.github/workflows/me1-evidence.yml` és `check-me1-workflow.py`, `harness/test-me1-body.py` (a P1/P2 alapja, a lejárat-kapus törzs)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a `pull_request`-futás állításalakjainak (`sub`, `ref`, `sha`, `workflow_ref`, `workflow_sha`, `job_workflow_sha`, `head_sha`, a futás `path` és `head_branch` mezője) mértként kezelése; az olvasó profilja csak mért értékekre épülhet, addig a szintetikus fixtúra hipotézis-jelölt.
- NEM fogadható el: a „legfrissebb futás" szabály döntési politikaként; a checks API csak felderít és keresztellenőriz; a tokenen belüli egyezés ≠ a jóváhagyott workflow-azonosság.
- NEM fogadható el: az a negatív kontroll, amelyet csak a közönség, az idő vagy a manifest-szerkezet utasít el; a megvalósítás ≠ működik, amíg a kontrollok bukásra is nem bizonyítottak (mutációs ellenőrzés), és a zöld teszt ≠ sikeres mérés.
- NEM fogadható el: érvényes (le nem járt) token bármely csatornán; a P-c/V eredmény kimondása teljes P-c igazolásként; a teljes M-E1 PASS kimondása.
- NEM fogadható el: Actions-futás, PR-nyitás vagy írás az X repón vagy az éles szervezetben; hitelesítő adat átadása nekem.

## Output

- `output/p-implementation.md` — mit valósít meg a csomag, a hipotézisek kezelése, a döntési politika és a felderítés, az állításosztályok, a kontrollok, a tesztek és a mutációs ellenőrzések eredménye, a tulajdonosi folyamat (külön GO-kkal), K-5, korlátok, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)
- `output/payload/p1/.github/workflows/me1-evidence.yml`, `output/payload/p2/.github/workflows/me1-evidence-twin.yml`, `output/check-me1-p-workflows.py`
- `output/harness/read-me1.py`, `fetch-me1.sh`, `fetch-jwks.sh`, `me1-controls.py`, `test-fetch-me1.py`, `test-pcv.py`, `test-me1-body.py`
- `output/owner/deliver-p-probe.sh`, `output/owner/open-p-probe-pr.sh`, `output/owner/test-owner-scripts.py`

## Git

Feature branch `feature/relay-ci-parity-06v-me1-p-implementation`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl (generált `.yaml` melléktermékek miatt).

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
