# relay-ci-parity-01-inventory — Relay CI inventory és objektumszintű gap-analízis

## Kontextus

A `CentralInfraCore/CIC_Relay` tesztelési és CI-rendszerét fel kell zárkóztatni a
`CentralInfraCore/cic-primitive-forms` minőségbiztosítási modelljére. A teljes feladat
a CIC_Relay **#169** issue-ban él (másolat: `ref/issue-169-body.md`); az egy tízlépéses
PR-sorozat. **Ez a job csak a PR-01-et fedi: inventory és objektumszintű gap-analízis.**

Ez **mérés és dokumentáció, nem implementáció.** A Relay forráskódját, workflow-it és
scriptjeit ebben a jobban nem módosítod, nem nyitsz PR-t a CIC_Relay felé.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`,
   `limits` fogalmakra. A státuszt (implemented / scaffold / concept) node- vagy fájlszinten
   támaszd alá, különben ne állítsd tényként.
2. Olvasd el az issue-t: `ref/issue-169-body.md`.
3. Klónozd (read-only célra) a két repót a workspace-be:
   `$WORKSPACE/CIC_Relay/` és `$WORKSPACE/cic-primitive-forms/`. Ezeket nem commitolod a
   cic-factory ágra, és nem pusholsz beléjük. **Rögzítsd mindkettő pontos commit-azonosítóját
   és az ágat**, amit vizsgálsz.

## Források és módszer

- Helyi tájékozódási klónok (csak olvasásra, lehetnek elavultak): `${CIC_RELAY_PATH}`,
  `~/sync/git.partners/CentralInfraCore/`. **A mérés a workspace-beli friss klónon megy**
  (`$WORKSPACE/CIC_Relay/`), nem a helyin: a helyi klónok lemaradtak, és a CIC_Relay
  alapértelmezett ága `main` (a `devel` elavult). Az ágat és a commitot rögzítsd.
- **Reachability (Go forráskód):** egy Go szimbólumról vagy scriptről csak akkor mondd, hogy
  production-hívott, ha megvan a hívási út: `grep -rn <szimbólum> --include=*.go . | grep -v _test.go`
  VAGY `deadcode ./...` kimenet. A kimenetben production call site `file:line` kell.
  A `symbol létezik` ≠ `production hívja`. Ugyanez a CI-scriptekre: a workflow-ból hívott
  script `file:line`-ja, nem a script puszta léte.

## Feladat

Térképezd fel és hasonlítsd össze:

**A. A Relay meglévő tesztrendszere** — a `.github/workflows/{verify,mutation-pr,mutation,
nightly,manifest-check}.yml`, `scripts/{mutation_plan,gremlins_gate,baseline_guard}.py`,
`.mutation-baseline.json`, `.mutation-cost.json` és minden, ami a Go/Rust tesztfuttatáshoz,
coverage-hez és mutációhoz tartozik.

**B. A Forms referencia** — `p1.yml`, `p1-proof.yml`, `nightly.yml`, `proof-plan.yml`,
`evidence.yml`, `evidence-probes.yml`, `quality_gate.py`, `coverage_gate.py`, `diff_gate.py`,
`seeded_defects.py`, `tools/test-evidence/`, `tools/proof-plan/`, `docs/DELTA-DIFF-GATE.md`,
`docs/FAST-FULL.md`, `docs/TEST-EVIDENCE.md`.

**C. Objektumszintű gap-analízis**, amely objektumonként megkülönböztet:
már működő ellenőrzést · hiányzó tesztet · hibás CI-kaput · nem mért területet ·
implementációs hiba miatt jelenleg nem teljesíthető követelményt.

**D. A legnagyobb kockázatú kapuhiba reprodukálása.** Az issue szerint a `mutation-pr.yml`
és a `nightly.yml` Rust mutánsfelsorolásánál a `grep -c ... || true` elfedheti a felsoroló
parancs hibáját. Reprodukáld (parancs + kimenet), és mondd ki: hibás felsorolás mikor ad
nulla mutánst. **Javítani nem kell**, az PR-02.

**E. Mérési scope javaslat**: a production kód, a tesztsegédek, a generált fájlok és a
kísérleti, nem bekötött komponensek szétválasztása. A javaslat ne zárjon ki indokolatlanul
csomagot vagy fájlt; minden kizárásnak legyen oka.

**F. Aktuális mért állapot**, ha reprodukálhatóan mérhető: Go statement coverage, Rust line
coverage. Amit nem tudsz lemérni, azt jelöld **nem mérve** (ne becsülj).

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented. A workflow létezése ≠ hogy fut, és a kapu ≠ hogy bukni tud.
- Exit code 0 ≠ sikeres mérés. Üres kimenet ≠ nulla mutáns ≠ sikertelen felsorolás.
- Egy sikeres futás ≠ hogy a kapu hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként.

## Output

Fájlok a klónban: `jobs/relay-ci-parity-01-inventory/output/`

- `output/inventory-and-gap-analysis.md` — a teljes jelentés, a következő fejezetekkel:
  vizsgált commitok · Relay inventory · Forms referencia · gap-analízis objektumonként ·
  a reprodukált kapuhiba · scope-javaslat · mért állapot · javaslat a PR-02-re.
- Az `inventory-and-gap-analysis.md`-ben **claim-evidence tábla**:
  `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`, ahol a Státusz
  `implemented` / `scaffold` / `concept` / `nem mérve`, a Bizonyíték pedig `file:line` vagy
  parancs és kimenet.
- `output/gate-defect-repro.md` — a D pont parancsai és nyers kimenetei.

## Definition of Done

- Mindkét repó commit-azonosítója le van írva.
- Minden állítás mögött file:line vagy futtatott parancs áll.
- A D pont reprodukciója megtörtént, vagy ki van mondva, hogy miért nem lehetett.
- A nem mért terület **nem mérve**, nem becslés.

## Git instrukciók

- Commit és push **csak** a `feature/relay-ci-parity-01-inventory` ágra a cic-factory
  klónban. Main-re, devel-re nem pusholsz; merge-et nem csinálsz.
- A CIC_Relay és a Forms klónjába nem commitolsz és nem pusholsz.
- Vault-aláírás: a friss klónban a commit-msg hook nem feltétlenül él; az aláírást a
  tulajdonos pótolja, ezt jelezd az outputban.

## Nyelvi szabály

Dokumentáció magyarul. Parancsok, kód, YAML, shell angolul.
