# relay-ci-parity-06i-exploratory-measurement-plan — a feltáró mérések terve (CIC_Relay #212, 6. lépés)

## Kontextus

A #76–#80 PR-ok rögzítették a követelményeket (R-I, R-V, R-C, R-X), a policy határát (R-P), a digest-szabályokat (R-D), a bizalmi horgonyt és az ellenőrzési mechanizmust (R-A, R-M). A triázs (open-case-triage 5. szakasz) szerint a következő a **feltáró mérések** szakasza: a jelenlegi viselkedés megmérése, mielőtt az állapotkötés megoldási terve készül. Ez a munkacsomag **csak a mérési tervet** készíti el. Tulajdonosi GO (2026-11-22): öt terület (TOCTOU; E1/E2 csatornák; visszavonás és installációfelfüggesztés; két független kibocsátói azonosság együttes kikényszerítése; a tényleges futási azonosság bizonyíthatósága), kiegészítve: visszajátszási és bizonyítékhelyettesítési negatív próbák, minden tételhez egyértelmű PASS / FAIL / INCONCLUSIVE kritérium, visszavezethetőség a normatív követelményekre.

## Hatókör

**Kizárólag terv.** Nincs mérés, nincs kulcsművelet, nincs implementáció, nincs Relay- vagy repository-beállítás módosítás, nincs algoritmus- vagy kódolásválasztás. A mérési tételek leírása a későbbi, külön GO-t igénylő végrehajtás bemenete.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:

- `jobs/relay-ci-parity-06d-decision-requirements-spec/output/decision-requirements-spec.md` (R-I, R-V, R-C, R-X)
- `jobs/relay-ci-parity-06e-open-case-triage/output/open-case-triage.md` (3.1–3.3, G1–G3, 5. szakasz: a 4. lépés)
- `jobs/relay-ci-parity-06f-policy-boundary-spec/output/policy-boundary-spec.md` (R-P.*)
- `jobs/relay-ci-parity-06g-digest-canonicalization-spec/output/digest-canonicalization-spec.md` (R-D.*)
- `jobs/relay-ci-parity-06h-trust-anchor-verification-spec/output/trust-anchor-verification-spec.md` (R-A.*, R-M.*)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (2. és 3. szakasz: a korábbi scratch mérések)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/integrity-app.yml.txt` (a scratch workflow)

## Elfogadhatatlan rövidítések

- NEM fogadható el: egy mérési tétel pozitív kontroll nélkül ≠ mérés (egy mérés, amely nem tud bukni, nem bizonyít).
- NEM fogadható el: INCONCLUSIVE kimenet PASS-ként vagy FAIL-ként való jelentése; a terv megléte ≠ működik.
- NEM fogadható el: a scratch eredmény production-igazoltként való kezelése; a tervben szereplő várt eredmény ≠ mért eredmény.
- NEM fogadható el: éles kulcs, éles repository vagy a Relay érintése; tulajdonosi kulcsműveletet a terv nem végezhet el.
- NEM fogadható el: megvalósítási eszköz a követelményekre való hivatkozásban (a követelmények technológiafüggetlenek maradnak).

## Output

- `output/exploratory-measurement-plan.md` — közös szabályok, öt terület mérési tételei (hipotézis, követelmény-hivatkozás, elrendezés, pozitív kontroll, negatív esetek köztük visszajátszás és bizonyítékhelyettesítés, PASS/FAIL/INCONCLUSIVE kritérium, tulajdonosi lépés), visszavezetési mátrix, tulajdonosi beavatkozások jegyzéke, nyitott kérdések; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06i-exploratory-measurement-plan`, aláírt commit, külön PR, tartalmi review; merge csak külön, SHA-hoz kötött jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
