# wasm-finalize-release-deprecation — `finalize_release.py` dead-code jelölés

## Reasoning mód

**implementation**, kis scope — a `wasm-release-pipeline-audit` riport A) opciójának
végrehajtása. A riport igazolta:

- `tools/finalize_release.py:188-201` egy `checksum != buildHash` egyenlőségi
  ellenőrzést tartalmaz, ami **dead code** a production láncban (`grep -rn
  "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` → 0 találat,
  csak `tests/test_tools/test_finalize_release.py` importálja).
- A `CIC-Schemas/docs/en/compiler-architecture-plan.md` (~648-654. sor, KB node
  `n1295`/`c1295`, "Step 10 — Mark `finalize_release.py` for deletion") explicit
  tervet ad: *"Add a prominent `# DEPRECATED: Use relay API when available.`
  comment block. Track relay readiness as a separate milestone; delete on
  relay GA."*
- Jelenleg `base-repo/tools/finalize_release.py:8-15` csak egy `# FIXME: This
  script is a temporary solution...` kommentet tartalmaz — a tervezett
  `# DEPRECATED` jelölés hiányzik.

**Ez NEM a B) vagy C) döntés** (schemas/main lineage szinkron, verify-release
v2) — azok orchestrátor-szintű döntésre várnak, és nincsenek ebben a jobban.

## Munkakörnyezet — branch szabály (KÖTELEZŐ)

- base-repo klón, `git fetch origin wasm/main` — HEAD ekkor már tartalmazhatja
  PR #13-at (`wasm-template-release-contracts`, `89835ca`) is, ha az addig
  mergelve lett. `git log --oneline -3 origin/wasm/main`-nel ellenőrizd és
  jelezd a riportban melyik HEAD-ből indultál.
- Branch: **`wasm/f/finalize-deprecation`** a `wasm/main`-ből.
- Push **kizárólag** ide. PR: `gh pr create --base wasm/main --head
  wasm/f/finalize-deprecation` (ha a `gh`/remote korlát miatt nem megy,
  dokumentáld — az orchestrátor megnyitja).

## Feladat

### 1. `# DEPRECATED` jelölés a `tools/finalize_release.py`-ban

A `CIC-Schemas` terv mintáját kövesd: a fájl tetején (a meglévő `# FIXME`
komment mellé vagy helyett — döntsd el melyik a tisztább, indokold) adj hozzá
egy jól látható blokkot, kb.:

```python
# DEPRECATED: This module is dead code on the production release path
# (no Makefile/mk/*.mk/.github/workflows/*.yml call site — verified via
# `grep -rn "finalize_release"`). The active release chain is
# `make release` -> tools.compiler -> tools.infra.ReleaseManager
# (see tools/infra.py:352-385 for the checksum+buildHash signing model).
# Track relay-readiness as a separate milestone; delete this module on
# relay GA (cf. CIC-Schemas compiler-architecture-plan.md, "Step 10").
```

Ne törölj kódot, ne módosíts logikát — csak a deprecation-jelölést add hozzá.
A `tests/test_tools/test_finalize_release.py`-nak továbbra is futnia kell
változatlanul.

### 2. Dokumentáció — `docs/contracts/{en,hu}/release-artifact.md`

A `release-artifact.md` jelenleg nem hivatkozik `finalize_release.py`-ra
(ellenőrizd `grep -n "finalize_release"`-lel — a riport szerint 0 találat).
Adj hozzá egy rövid bekezdést (a meglévő three-phase / canonical release path
leírás mellé), ami megemlíti: `tools/finalize_release.py` deprecated, dead
code, a tényleges lánc `infra.ReleaseManager`. Cél: a jövőbeli olvasó ne
találja meg a fájlt és gondolja, hogy az aktív.

### 3. README megjegyzés (opcionális, ha releváns helye van)

Ha a README Makefile Commands szakaszában bármilyen utalás van
`finalize_release`-re, jelöld deprecated-nek. Ha nincs (a riport szerint
nincs production call-site, így valószínűleg README sincs rá), ezt a pontot
hagyd ki és jelezd N/A-ként a riportban.

## Tiltott rövidítések (kötelező)

- **Ne törölj `finalize_release.py`-t vagy a tesztjét.** A relay-readiness
  milestone (a `CIC-Schemas` terv szerint) előfeltétele a törlésnek — ez nem
  ennek a jobnak a hatóköre.
- **A `# DEPRECATED` komment léte ≠ implemented.** A riportban a komment
  szövegét idézd file:line-nal, ÉS futtasd `make test`-et és `make check`-et
  a módosítás után — `EXIT=0` ≠ sikeres, ha a komment hiányzik vagy rossz
  helyre került; mindkét bizonyíték (idézet + futtatás-kimenet) kötelező.
- Ne nyúlj `tools/infra.py`/`tools/compiler.py`/`project.schema.yaml`-hoz.

## Reachability — kötelező bizonyíték

- `grep -n "DEPRECATED" tools/finalize_release.py` — a riportban idézve
  file:line-nal.
- `grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` —
  ismételd meg a job végén, igazold hogy még mindig 0 találat (azaz a
  deprecation-jelölés nem vezetett be új call-site-ot véletlenül). Ez a
  base-repo Python eszköz, nem Go — a `_test.go`/`deadcode` ellenőrzés nem
  releváns; a `tests/test_tools/test_finalize_release.py` egyetlen importálóként
  továbbra is futnia kell zölden (`make test`).
- `make test` és `make check` futtatás-kimenete (`EXIT=0`).

## Output

- `jobs/wasm-finalize-release-deprecation/output/wasm-finalize-release-deprecation-report.md`
  — claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`),
  1-3 pont lefedve (3. pont lehet N/A indoklással).
- base-repo `wasm/f/finalize-deprecation` pusholva + PR a `wasm/main` bázisra
  (vagy dokumentált korlát).

## Git instrukciók

- base-repo: commit + push **csak** `wasm/f/finalize-deprecation`-ra; PR bázis: `wasm/main`.
- cic-factory: commit + push **csak** `feature/wasm-finalize-release-deprecation`-ra.
- Main-re és `wasm/main`-re sehova nem pusholsz.

## Definition of Done

- [ ] `wasm/f/finalize-deprecation` branch a `wasm/main`-ből, minden munka ott
- [ ] `tools/finalize_release.py` tartalmaz `# DEPRECATED` blokkot, file:line idézve
- [ ] `docs/contracts/{en,hu}/release-artifact.md` megemlíti a deprecation-t
- [ ] `make test` és `make check` zöld (`EXIT=0`), kimenet idézve
- [ ] `grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` → 0 (megismételve)
- [ ] PR megnyitva (`wasm/f/finalize-deprecation` → `wasm/main`) vagy dokumentált korlát
- [ ] report a `feature/wasm-finalize-release-deprecation`-on pusholva

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, kommentek, commit message: **angolul**
