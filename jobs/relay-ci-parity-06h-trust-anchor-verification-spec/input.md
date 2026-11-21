# relay-ci-parity-06h-trust-anchor-verification-spec — a bizalmi horgony és az ellenőrzési mechanizmus (N1/N2) (CIC_Relay #212, 5. lépés)

## Kontextus

Az N3 (#78) rögzítette, mi tartozik az állapotkötésbe; az N5 (#79) azt, hogyan képződnek a digestek. Az **N1** azt kérdezi, honnan jön az elvárt ellenőrző-digest úgy, hogy független legyen a kibocsátótól és a tárgy szerzőjétől (R-V.6); az **N2** azt, ki és hol végzi az R-V.4 összevetést, és teljesíthető-e az R-V.5 platformon belül. A besorolás szerint a kettő együtt dönthető (open-case-triage 3.1): a független verifier maga is kibocsátó, ezért a regressziónak natívan kikényszerített horgonyon kell végződnie. Tulajdonosi GO (2026-11-22): kizárólag a bizalmi horgony és az ellenőrzési mechanizmus normatív specifikációja, külön PR-ban.

## Hatókör

**Kizárólag specifikáció, technológiafüggetlenül.** Nincs mérés, implementáció, Relay- vagy repository-beállítás módosítás. Az algoritmus- és kódolásválasztás nem része.

## Forrás

Útvonalak a `/home/sinkog/sync/claude_factory/CIC/workdir/` alatt:
- `jobs/relay-ci-parity-06d-decision-requirements-spec/output/decision-requirements-spec.md` (R-I, R-V, R-C, R-X, N1, N2)
- `jobs/relay-ci-parity-06e-open-case-triage/output/open-case-triage.md` (3.1, N1/N2 tételek, végrehajtási sorrend)
- `jobs/relay-ci-parity-06f-policy-boundary-spec/output/policy-boundary-spec.md` (R-P.*)
- `jobs/relay-ci-parity-06g-digest-canonicalization-spec/output/digest-canonicalization-spec.md` (R-D.*)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/app-measurement-report.md` (3.1, 3.3, 3.6)
- `jobs/relay-ci-parity-06c-workflow-integrity/output/raw/app/integrity-app.yml.txt` (a scratch workflow)

## Elfogadhatatlan rövidítések

- NEM fogadható el: az ellenőrző saját digestjének önbevallása ≠ bizalmi horgony.
- NEM fogadható el: a verifier megléte ≠ működik; scratch megfigyelés nem mérés.
- NEM fogadható el: a verifier, amelyet a vizsgált tárgy (a PR) definiálhat, futtathat vagy módosíthat.
- NEM fogadható el: megvalósítási eszköz a normatív szakaszban.

## Output

- `output/trust-anchor-verification-spec.md` — normatív követelmények (R-A.* a horgonyra, R-M.* a mechanizmusra), a mechanizmusok osztályozása, a scratch megfigyelései (nem mérés), nyitott kérdések, javasolt-nem-igazolt megoldás; claim-evidence tábla, oszlopok: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`.

## Git

Feature branch `feature/relay-ci-parity-06h-trust-anchor-verification`, aláírt commit, külön PR, tartalmi review; merge csak külön jóváhagyással.

## Nyelvi szabály

Dokumentáció magyarul; kód, YAML, azonosítók angolul.
