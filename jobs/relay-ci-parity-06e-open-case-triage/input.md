# relay-ci-parity-06e-open-case-triage — a 11 nyitott eset és az N1–N7 kérdések besorolása és priorizálása (CIC_Relay #212, 2. lépés)

## Kontextus

A #76 (merge 1019757) rögzítette a három normatív követelményt (R-I, R-V, R-C, R-X). A tulajdonos GO-ja (2026-11-21): a mérési jelentés 11 nyitott esetét és a specifikáció N1–N7 kérdéseit közösen kell besorolni (P0–P3), prioritás szerint rendezni, és tételenként rögzíteni az érintett követelményt, a függőségeket, a meglévő bizonyítékot és korlátját, a lezáráshoz szükséges bizonyítékot és a javasolt végrehajtási sorrendet.

## Hatókör

**Kizárólag elemzés és tervezés.** Nincs scratch mérés, Relay-implementáció, éles konfiguráció, repository-beállítás módosítás.

## Forrás

- `jobs/relay-ci-parity-06d-decision-requirements-spec/output/decision-requirements-spec.md` (7. szakasz, N1–N7, R-I/R-V/R-C/R-X)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (3.4, 3.6, 5, 7. szakasz)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/` (nyers bizonyíték)
- Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt.

## Elfogadhatatlan rövidítések

- NEM fogadható el: a mérés létezése ≠ igazolt védelem, a konfiguráció létezése ≠ működik; a prioritás nem bizonyíték.
- NEM fogadható el: egy összevonás, amely elveszti az eredeti azonosítót.
- NEM fogadható el: következtetés mért állításként feltüntetve; a következtetést külön meg kell jelölni.

## Output

- `output/open-case-triage.md` — tételenként a fenti öt mező, összevonási térkép az eredeti azonosítókkal, függőségi gráf, végrehajtási sorrend, claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06e-open-case-triage`, aláírt commit, külön PR, tartalmi review; merge csak külön jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
