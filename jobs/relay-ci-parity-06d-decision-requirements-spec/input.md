# relay-ci-parity-06d-decision-requirements-spec — a három normatív követelmény formális specifikációja (CIC_Relay #212 következő szakasz, 1. lépés)

## Kontextus

A #212 mérési szakasza lezárult (cic-factory #73, #74, #75). Három, egymást nem helyettesítő követelmény bizonyult szükségesnek: kibocsátói hitelesség, döntési érvényesség, bemeneti teljesség. A tulajdonos döntése (2026-11-21): ezek technológiafüggetlen, normatív követelmények; a GitHub App, a ruleset és az Actions csak megvalósítási eszköz. Az érvényességi követelmény köti az ellenőrzött állapotot, az alkalmazott policyt és az ellenőrző implementációját; a digest rögzítése önmagában nem bizonyítja az érvényességet, az ellenőrzés és az eltérés következménye is definiálandó.

## Hatókör

**Kizárólag specifikációs munkacsomag.** Nincs implementáció, nincs scratch mérés, nincs Relay-változás, nincs repository-beállítás módosítás. A 11 nyitott eset osztályozása, az állapotkötés megoldási terve és az elfogadási kritériumok aktualizálása **külön, későbbi lépés**.

## Forrás

Konkrét path-ok (repo-relatív, `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt):

- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (§1, §3, §3.6, §7)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/addendum-github-app-and-22-cases.md`
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/` (nyers bizonyíték)

## Elfogadhatatlan rövidítések

A következők NEM fogadhatók el:

- NEM fogadható el: a digest puszta rögzítése ≠ érvényesség; az ellenőrzés nélküli digest nem bizonyíték.
- NEM fogadható el: scratch mérés ≠ éles védelem; mérési állítás csak mért esetre vonatkozhat.
- NEM fogadható el: megvalósítási eszköz (App, ruleset, Actions) a normatív követelményben.
- NEM fogadható el: a megvalósítás létezése ≠ működik; egy konfiguráció megléte ≠ sikeres védelem, csak mért eset állítható.

## Output

- `output/decision-requirements-spec.md` — a specifikáció: normatív követelmények; mért tulajdonságok; nyitott kérdések; javasolt, nem igazolt megoldások (négy külön szakasz), claim-evidence táblával, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch (`feature/relay-ci-parity-06d-decision-requirements-spec`), aláírt commit, külön PR, tartalmi review; merge csak külön jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
