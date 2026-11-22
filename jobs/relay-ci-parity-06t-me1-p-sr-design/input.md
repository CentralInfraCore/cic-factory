# relay-ci-parity-06t-me1-p-sr-design — az M-E1 P és S/R mérőcsomag terve (CIC_Relay #212, 17. lépés)

## Kontextus

Az M-E1 első mérési részlépése lezárt (#91, merge `a79f2a1`): a platform által aláírt OIDC-bizonyíték a vizsgált laborfutásban hitelesen köti a (workflow útvonal+ref, commit, azonosság, futás, kísérlet) négyest (`EVIDENCE BOUND`), de az M-E1 ítélete **nyitott, előzetesen `INCONCLUSIVE`**: a P (a PR szerzőjének befolyása a bizonyítékra) `NOT-READ`, az S/R negatívok és az artifact-attestáció nyitott. Tulajdonosi GO (2026-11-22): a P és S/R mérőcsomag **tervezése, kizárólag tervezés**: a mérési protokoll, a bizalmi határok, a negatív kontrollok, az elfogadási kritériumok és a K-5 keretigény előzetes rögzítésével; **érvényes token semmilyen csatornán nem publikálható**; a végrehajtás külön GO. K-5: 8/300.

## Hatókör

**Kizárólag terv (dokumentum).** Nem készítek workflow-fájlt, szkriptet vagy kódot, nem indítok futást, nem nyitok PR-t az X repón, nem töltök le bizonyítékot. A terv döntési pontokat (D1–D7) rögzít a tulajdonosnak; a megvalósítás külön csomag, külön GO, külön review.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06i-exploratory-measurement-plan/output/exploratory-measurement-plan.md` (2.2 PK és negatív osztályok R/S/P, 3.E M-E1)
- `jobs/relay-ci-parity-06j-execution-decision-package/output/execution-decision-package.md` (K-5, 4. szakasz leállási küszöbök, 5.1 kapuk)
- `jobs/relay-ci-parity-06s-me1-partial-report/output/m-e1-partial-report.md` (a mért megfigyelések, a bizalmi határ, az M-E1 állapota)
- `jobs/relay-ci-parity-06r-sub-claim-fix/output/harness/read-me1.py`, `fetch-me1.sh`, `fetch-jwks.sh` (a meglévő olvasó és gyűjtő)
- `jobs/relay-ci-parity-06q-me1-measurement-package/output/payload/.github/workflows/me1-evidence.yml` (a lejárat-kapus publikálás referenciája)

## Elfogadhatatlan rövidítések

- NEM fogadható el: érvényes (le nem járt) OIDC-token bármely csatornán (napló, artifact, annotáció, összegzés, komment, PR, cache); a saját közönség ≠ hozzáférési korlát.
- NEM fogadható el: a pull_request-eseményre vonatkozó állításalakok (`sub`, `ref`, `sha`, `workflow_ref`, `event_name`) mértként kezelése; ezek dokumentált, nem mért hipotézisek, amíg a futás nem mutatja.
- NEM fogadható el: a negatív kontroll, amelyet a közönség (`aud`) vagy a manifest eltérése önmagában elutasít; az elutasítás okai között a kötő állításoknak (`workflow_ref`, `ref`, `sha`, `event_name`, `sub`) szerepelniük kell.
- NEM fogadható el: a terv megléte ≠ működik, és a terv elfogadása ≠ sikeres mérés; az M-E1 ítéletének (PASS/FAIL/INCONCLUSIVE) előzetes kimondása.
- NEM fogadható el: a same-repo PR eredményének kiterjesztése fork-PR-ra, és a labor eredményének általánosítása a Relay-re vagy a production-re; írási művelet az X repón vagy az éles szervezetben a tulajdonos nélkül.

## Output

- `output/me1-p-sr-design.md` — a fenyegetési modell és a bizalmi határok, a hipotézisek, a mérési protokoll és mátrix, a token-kezelés szabályai, a negatív kontrollok, az elfogadási kritériumok és az ítélet-leképezés, a K-5 keretigény, a megvalósítási csomag tartalma, a tulajdonosi döntési pontok, a kockázatok, claim-evidence tábla (`| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`)

## Git

Feature branch `feature/relay-ci-parity-06t-me1-p-sr-design`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással. A commitba **csak explicit fájllistával** kerül fájl.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, parancsok, azonosítók angolul.
