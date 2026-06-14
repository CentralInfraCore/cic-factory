# wasm-finalize-release-deprecation — riport

## Reasoning mód

**implementation** — a `wasm-release-pipeline-audit` riport A) opciójának
végrehajtása: `tools/finalize_release.py` jelölése deprecated dead code-ként,
a `CIC-Schemas` `compiler-architecture-plan.md` "Step 10" tervének mintája
szerint. A B) és C) opció (schemas/main lineage szinkron, verify-release v2)
nem ennek a jobnak a hatóköre.

## Munkakörnyezet

- base-repo klón: `jobs/wasm-finalize-release-deprecation/workspace/base-repo`
- `git fetch origin wasm/main` → HEAD: `e06ed9c` ("Merge pull request #12 from
  CentralInfraCore/wasm/f/contracts"). A PR #13
  (`wasm-template-release-contracts`, `89835ca`) ekkor **még nem** volt
  mergelve `wasm/main`-be — ebből a HEAD-ből indultam.
- Branch: `wasm/f/finalize-deprecation`, létrehozva `origin/wasm/main`-ből.
- Push: `wasm/f/finalize-deprecation` → origin (csak ez, `wasm/main`-re nem).

## Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `tools/finalize_release.py` most már tartalmaz egy jól látható `# DEPRECATED` blokkot | **implemented** | `tools/finalize_release.py:17` — `# DEPRECATED: This module is dead code on the production release path` (a teljes blokk a 17–23. sorban, a meglévő `# FIXME` blokk alatt, a 8–15. sor megtartva) | `grep -n "DEPRECATED" tools/finalize_release.py` → `17:# DEPRECATED: This module is dead code on the production release path` | alacsony — csak komment, logika nem változott |
| A `# FIXME` komment megmaradt, a `# DEPRECATED` mellette él, nem helyette | **implemented** | `tools/finalize_release.py:8-23` — a `# FIXME` blokk (8–15) és az új `# DEPRECATED` blokk (17–23) egymás után, üres sorral elválasztva. Indoklás: a `# FIXME` a *miért íródott meg eredetileg* kontextust adja (relay-előtti ideiglenes megoldás), a `# DEPRECATED` a *jelenlegi státuszt* (dead code, nincs call site) — a kettő kiegészíti egymást, nem redundáns | manuális diff-ellenőrzés | alacsony |
| `docs/contracts/en/release-artifact.md` megemlíti a `finalize_release.py` deprecation-t | **implemented** | A "Three-phase release (prepare / build-gap / finalize)" szakasz után új bekezdés: *"`tools/finalize_release.py` is **deprecated and dead code** on this path: ... the **finalize** phase above is implemented by `tools.infra.ReleaseManager` (see `tools/infra.py:352-385`'s checksum + `buildHash` signing model) ... marked `# DEPRECATED` in the module itself."* | `grep -n "finalize_release" docs/contracts/en/release-artifact.md` → 1 találat (az új bekezdésben) | alacsony |
| `docs/contracts/hu/release-artifact.md` megemlíti a `finalize_release.py` deprecation-t | **implemented** | A "Háromfázisú release" szakasz után új bekezdés, magyarul, ugyanazokkal a hivatkozásokkal (`tools/infra.py:352-385`, CIC-Schemas Step 10) | `grep -n "finalize_release" docs/contracts/hu/release-artifact.md` → 1 találat | alacsony |
| README-ben nincs `finalize_release` hivatkozás, így nincs ott javítandó | **N/A** (igazolt hiány) | `grep -ni "finalize" README.md` → 0 találat | `grep -ni "finalize" README.md`; exit 1 | nincs |
| A `finalize_release.py` és a tesztje (`tests/test_tools/test_finalize_release.py`) nem törölve, a teszt zölden fut | **implemented** | `make test` kimenet: `112 passed`, a coverage táblában `tools/finalize_release.py  129  2  98%` (lefedett, futtatott modul) | `make test` → `EXIT=0`, lásd alább a teljes kimenet farkát | alacsony |
| `make check` zöld a módosítás után (formázás/lint/typecheck/bandit) | **implemented** | `make check` kimenet: Black "21 files left unchanged", Ruff "All checks passed!", MyPy "Success: no issues found in 21 source files", Bandit "No issues identified." | `make check` → `EXIT=0`, lásd alább a teljes kimenet | alacsony |
| A deprecation-jelölés nem vezetett be új production call site-ot | **implemented** | `grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` → 0 találat (ismételve a módosítás után, megegyezik az audit riport eredeti megállapításával) | `grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml`; exit 1 | nincs |
| PR megnyitva `wasm/f/finalize-deprecation` → `wasm/main` | **scaffold / blokkolt** | A push sikeres volt (`wasm/f/finalize-deprecation -> wasm/f/finalize-deprecation`), de `gh pr create` hibázott: *"none of the git remotes configured for this repository point to a known GitHub host."* A base-repo origin egy lokális filesystem path (`/home/sinkog/sync/git.partners/CentralInfraCore/.git_repos/base-repo.git`), nem GitHub remote — a `gh` CLI nem tudja PR-t nyitni. Dokumentálva, az orchestrátor nyissa meg a PR-t a megfelelő GitHub remote-on. | `gh pr create --base wasm/main --head wasm/f/finalize-deprecation ...` → hibaüzenet | közepes — a branch él és pusholva van, csak a PR-objektum hiányzik |

## `make test` kimenet (releváns rész)

```
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.11.15-final-0 _______________

Name                                Stmts   Miss  Cover   Missing
-----------------------------------------------------------------
tools/__init__.py                       0      0   100%
tools/check_doc_links.py               43     43     0%   9-67
tools/compiler.py                     120     26    78%   37, 71, 138-160, 164, 181-182, 223-227, 231
tools/finalize_release.py             129      2    98%   90, 195
tools/infra.py                        252     36    86%   66-70, 85, 98-101, 120-121, 157-166, 216, 345, 358-385, 498-501, 509
tools/releaselib/__init__.py            0      0   100%
tools/releaselib/exceptions.py         16      0   100%
tools/releaselib/git_service.py        85      0   100%
tools/releaselib/vault_service.py      75      4    95%   109-112, 167-170
-----------------------------------------------------------------
TOTAL                                 720    111    85%
============================= 112 passed in 0.86s ==============================
EXIT=0
```

## `make check` kimenet (releváns rész)

```
--- Formatting Python code with Black and Isort ---
All done! ✨ 🍰 ✨
21 files left unchanged.
Skipped 101 files
--- Linting Python code with Ruff ---
All checks passed!
--- Linting YAML files with yamllint ---
--- Running static type checking with MyPy ---
Success: no issues found in 21 source files
--- Running security checks with Bandit ---
Test results:
	No issues identified.
Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
EXIT=0
```

(A kimenetből kihagyva a `docker-compose.yml` "version" obsolete warning,
ami a yamllint/docker tool-okból jön — Compose-attribútum, nem a job
módosításával összefüggő, már a baseline-ban is megjelenik. A tényleges
check-lépések mindegyike zölden zárt.)

## Bridge detector

```
concept (CIC-Schemas compiler-architecture-plan.md, Step 10)
  → code (tools/finalize_release.py:17-23, # DEPRECATED blokk)
  → runtime (make test / make check zöld, a modul továbbra is futtatható és tesztelt)
  → audit (docs/contracts/{en,hu}/release-artifact.md hivatkozza a deprecation-t)
```

A lánc most végig él: a koncepció (relay-readiness milestone-ig megtartani,
deprecation-jelöléssel) kódba van írva, a runtime (tesztek, lint, typecheck)
nem sérült, és a dokumentáció (audit-szint) hivatkozza a státuszt. A
**törlés** (a koncepció második fele) továbbra is `concept` szinten marad —
ez a relay GA-tól függő, jövőbeli job hatóköre.

## Tiltott rövidítések — betartva

- `tools/finalize_release.py` és `tests/test_tools/test_finalize_release.py`
  nem törölve, a teszt zölden fut (lásd `make test` kimenet).
- A `# DEPRECATED` komment léte mellett `make test` és `make check` is
  lefutott, mindkettő `EXIT=0`.
- `tools/infra.py`, `tools/compiler.py`, `project.schema.yaml` nem módosult
  (`git diff --cached --stat` csak a 3 célzott fájlt mutatja).

## Git állapot

- base-repo: commit `4b27eca` a `wasm/f/finalize-deprecation` branch-en,
  pusholva `origin/wasm/f/finalize-deprecation`-ra. `wasm/main`-re nem
  pusholtam.
- PR `wasm/f/finalize-deprecation` → `wasm/main`: **nem létrehozva** — a `gh`
  CLI nem ismeri fel a GitHub remote-ot (lokális filesystem-alapú origin).
  Az orchestrátornak kell megnyitnia a PR-t a megfelelő GitHub remote-on,
  a branch már pusholva van.
