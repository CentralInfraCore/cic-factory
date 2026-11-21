# relay-ci-parity-06f-policy-boundary-spec — a policy normatív határa (N3) (CIC_Relay #212, 3. lépés)

## Kontextus

A #76 (R-I, R-V, R-C, R-X) és a #77 (besorolás, végrehajtási sorrend) lezárult. A besorolás 1. lépése az **N3**: mi tartozik a döntést meghatározó policyhoz (`P`), mi az ellenőrző implementációjához (`C`), hol vannak a kibocsátói és jóváhagyói jogosultságok, hogyan kezelendők a külső, örökölt és dinamikusan változó szabályok, mely változások érvénytelenítik a korábbi döntést, és mi nem része a policynak. Alapelv (tulajdonosi GO, 2026-11-22): **döntést befolyásoló tényező nem maradhat az állapotkötésen kívül.** A digest képzésének konkrét szabályai az N5 munkacsomag tárgya, nem ezé.

## Hatókör

**Kizárólag specifikáció, technológiafüggetlenül.** Nincs mérés, implementáció, Relay- vagy repository-beállítás módosítás.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:
- `jobs/relay-ci-parity-06d-decision-requirements-spec/output/decision-requirements-spec.md` (R-I, R-V, R-C, R-X, N1–N7)
- `jobs/relay-ci-parity-06e-open-case-triage/output/open-case-triage.md` (N3 tétel, 3.1, végrehajtási sorrend)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (3.6)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/` (scratch checker, policy, workflow)

## Elfogadhatatlan rövidítések

- NEM fogadható el: a policy fájl létezése ≠ a policy teljes határa; a fájl csak egy forrás.
- NEM fogadható el: a megvalósítás létezése ≠ működik; scratch osztályozási példa nem mérés.
- NEM fogadható el: egy tényező kihagyása indoklás nélkül; a kihagyást listázni és indokolni kell.
- NEM fogadható el: megvalósítási eszköz a normatív szakaszban.

## Output

- `output/policy-boundary-spec.md` — normatív határ (R-P.*), osztályozási teszt, érvénytelenítési tábla, kizárási lista indoklással; külön szakaszban a scratch osztályozási példa, a nyitott kérdések és a javasolt, nem igazolt megoldás; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06f-policy-boundary`, aláírt commit, külön PR, tartalmi review; merge csak külön jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
