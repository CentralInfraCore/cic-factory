# relay-ci-parity-06g-digest-canonicalization-spec — az S/B/P/C digestek képzése és kanonizálása (N5) (CIC_Relay #212, 4. lépés)

## Kontextus

Az N3 (a #78, merge d60321b) rögzítette, hogy *mi* tartozik az állapotkötésbe. Az N5 azt rögzíti, **hogyan képződnek** az S/B/P/C digestek: determinisztikus, egyértelmű kanonizálás, domain separation, típus- és verzióazonosítás, a függőségi lezárás és a digestképzés teljessége, a szemantikai egyenértékűség konzervatív kezelése, fail-closed viselkedés, pozitív és negatív konformanciatesztek *terve*, és a kapcsolódás az N3 határhoz.

## Hatókör

**Kizárólag tervezési specifikáció.** Nincs implementáció, mérés, Relay-módosítás, repository-beállítás módosítás. A konformanciatesztek tervezettek, nem megírtak és nem futtatottak.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:
- `jobs/relay-ci-parity-06f-policy-boundary-spec/output/policy-boundary-spec.md` (R-P.*, 2.1–2.3.2, N3.4, N3.5)
- `jobs/relay-ci-parity-06d-decision-requirements-spec/output/decision-requirements-spec.md` (R-V.1, R-V.6, R-V.7, R-C.6, N5)
- `jobs/relay-ci-parity-06e-open-case-triage/output/open-case-triage.md` (N5 tétel, sorrend)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/integrity-final.py.txt` (a scratch digest-képzés kódja, 100. és 116. sor)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a digest rögzítése ≠ érvényesség; a digest képzési szabálya nélküli digest nem bizonyíték.
- NEM fogadható el: a terv létezése ≠ működik; tervezett teszt nem futtatott teszt.
- NEM fogadható el: implicit normalizálás (sorvég, Unicode, szóköz), amelyet a szabály nem nevez meg.
- NEM fogadható el: megvalósítási eszköz a normatív szakaszban; a scratch kódolvasás nem mérés.

## Output

- `output/digest-canonicalization-spec.md` — normatív szabályok (R-D.*), a konformanciateszt-terv (azonosított tesztesetekkel), kapcsolódás az N3-hoz, a scratch digest-képzés megfigyelései (kódolvasás, nem mérés), nyitott kérdések, javasolt-nem-igazolt megoldás; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06g-digest-canonicalization`, aláírt commit, külön PR, tartalmi review; merge csak külön jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
