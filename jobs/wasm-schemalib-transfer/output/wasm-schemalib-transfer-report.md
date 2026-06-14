# wasm-schemalib-transfer — `tools/schemalib/` package átemelése

## Munkakörnyezet

- `base-repo` (`wasm/main`): klónozva `wasm/main` HEAD `7a51952` (Merge PR #13,
  "release-contracts") — megegyezik a `wasm-schemalib-sync-plan` riport
  induló HEAD-jével, nem fut rajta semmilyen újabb commit.
- `CIC-Schemas`: klónozva, checkout `2ec57c0` ("feat: unified compiler
  architecture — schemalib, repo_type routing, docs") — a job-spec és a
  `wasm-schemalib-sync-plan` riport referencia commitja.
- Branch: `wasm/f/schemalib-transfer`, ágazva `wasm/main`@`7a51952`-ből,
  pusholva a `base-repo` lokális mirror remote-ra.

---

## Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `tools/schemalib/{__init__,artifact,loader,validator}.py` byte-azonosan átemelve | confirmed | `diff -rq CIC-Schemas/tools/schemalib base-repo/tools/schemalib` → üres kimenet (ld. lent) | `diff -rq` | nincs |
| Az új package additív, "dead" — semmilyen meglévő `base-repo/tools/*.py`/Makefile/mk nem importál belőle | confirmed | `grep -rn "schemalib" tools/ Makefile mk/` (recursive, az új `tools/schemalib/*.py` fájlokat is beleértve) → **0 találat** | ld. "Reachability" szakasz | nincs — ez a lépés önmagában semmilyen wasm-specifikus problémát nem old meg a tervből, csak előfeltétel |
| `tools/releaselib/exceptions.py` a két repóban tartalmilag azonos, a `schemalib.loader`/`schemalib.validator` `ConfigurationError`/`ReleaseError` importja base-repo-n is feloldódik | confirmed | `diff base-repo/tools/releaselib/exceptions.py CIC-Schemas/tools/releaselib/exceptions.py` → üres kimenet (exit 0); mindkét osztály jelen van (`class ReleaseError`, `class ConfigurationError(ReleaseError)`) | `diff` + `grep -n "^class" tools/releaselib/exceptions.py` | nincs — **nem volt szükség módosításra** |
| Az új package importálható hiba nélkül a builder konténerben | confirmed | `python -c "from tools.schemalib import artifact, loader, validator"` → `OK` (ld. lent) | builder konténerben futtatva, `p_venv` deps-szel | nincs |
| `make test` zöld | confirmed | `112 passed`, `EXIT=0` (ld. lent) | `make test` a builder konténerben | nincs |
| `make check` **NEM** zöld az új fájlokkal | confirmed | `infra.lint` (`ruff`) hibát dob: `F401 ConfigurationError imported but unused` a `tools/schemalib/validator.py:7`-ben; `infra.fmt` (`black`/`isort`) 4 fájlt reformázna | `make check` teljes kimenet (ld. lent) | **közepes** — ld. "Nyitott kérdés" alább |

---

## 1. `diff -rq` — byte-azonosság

```
$ diff -rq CIC-Schemas/tools/schemalib base-repo/tools/schemalib
(üres kimenet)
```

A 4 fájl (`__init__.py`, `artifact.py`, `loader.py`, `validator.py`) byte-azonosan
átemelve. Commit: `5272ed2` a `wasm/f/schemalib-transfer` branch-en.

---

## 2. Reachability — 0 külső hívás

```
$ grep -rn "schemalib" tools/ Makefile mk/
(üres kimenet)
```

Recursive grep, lefedi az új `tools/schemalib/*.py` fájlokat (saját belső
relatív importjaikkal: `from .artifact import ...`, `from ..releaselib.exceptions
import ...` — ezek nem tartalmazzák a literál `"schemalib"` stringet) és
minden meglévő `tools/*.py`, `Makefile`, `mk/*.mk` fájlt. **0 találat** —
a package ebben a lépésben szándékosan dead/inert, `tools/infra.py`,
`tools/compiler.py` és `project.schema.yaml` nem importál belőle (ezt külön
is ellenőriztem):

```
$ grep -rn "schemalib" tools/infra.py tools/compiler.py project.schema.yaml
(üres kimenet)
```

---

## 3. `tools/releaselib/exceptions.py` diff-check

```
$ diff base-repo/tools/releaselib/exceptions.py CIC-Schemas/tools/releaselib/exceptions.py
(üres kimenet, exit 0)
```

**Nincs eltérés** — a két repóban a fájl tartalmilag (és byte-szinten) azonos.
A `wasm-schemalib-sync-plan` riport "Nyitott kérdés 3"-a ezzel lezárva: az
átemelt `schemalib/loader.py` (`from ..releaselib.exceptions import
ConfigurationError, ReleaseError`) és `schemalib/validator.py` (ugyanaz az
import) **mindkét osztályt megtalálja** a base-repo `exceptions.py`-ban:

```
$ grep -n "^class" tools/releaselib/exceptions.py
1:class ReleaseError(Exception):
9:class GitStateError(ReleaseError):
15:class GitServiceError(ReleaseError):
21:class VersionMismatchError(ReleaseError):
27:class ConfigurationError(ReleaseError):
33:class VaultServiceError(ReleaseError):
39:class ManualInterventionRequired(ReleaseError):
```

→ **Nem volt szükség módosításra** ebben a fájlban.

---

## 4. Import-teszt és `make test`

Builder konténer felállítása: a `p_venv` cache hiányzott (`make infra.deps` /
`docker compose run --rm setup`), ezt a job végrehajtotta (egyszeri,
környezet-előfeltétel, a feladat tartalmától független lépés).

```
$ docker compose exec builder python -c \
  "from tools.schemalib import artifact, loader, validator; print('OK', ...)"
OK /app/tools/schemalib/artifact.py /app/tools/schemalib/loader.py /app/tools/schemalib/validator.py
```

```
$ make test
...
============================= 112 passed in 0.96s ==============================
EXIT=0
```

Coverage report megemlíti az új fájlokat 0%-os lefedettséggel (`tools/schemalib/*.py`
— elvárt, mert jelenleg semmi nem hívja őket), a meglévő 112 teszt mindegyike
változatlanul zöld.

---

## 5. `make check` — **nem zöld** az új fájlokkal

```
$ make check
--- Formatting Python code with Black and Isort ---
reformatted /app/tools/schemalib/__init__.py
reformatted /app/tools/schemalib/validator.py
reformatted /app/tools/schemalib/artifact.py
reformatted /app/tools/schemalib/loader.py

All done! ✨ 🍰 ✨
4 files reformatted, 22 files left unchanged.
Fixing /app/tools/schemalib/__init__.py
Skipped 100 files
--- Linting Python code with Ruff ---
F401 [*] `..releaselib.exceptions.ConfigurationError` imported but unused
 --> tools/schemalib/validator.py:7:37
  |
5 | from jsonschema import validate
6 |
7 | from ..releaselib.exceptions import ConfigurationError, ReleaseError
  |                                     ^^^^^^^^^^^^^^^^^^
8 | from .artifact import compute_spec_checksum
9 | from .loader import load_and_resolve_schema
  |
help: Remove unused import: `..releaselib.exceptions.ConfigurationError`

Found 1 error.
[*] 1 fixable with the `--fix` option.
make: *** [mk/infra.mk:37: infra.lint] Error 1
```

`EXIT=1` (`infra.lint` hibája miatt `infra.check` megszakad, `infra.typecheck`
és `infra.security` nem is fut le).

### Nyitott kérdés — kötelező dokumentálás, NEM javítva ebben a jobban

A `make check` hibája **két, egymástól független** ok miatt jelentkezik, és
mindkettő **a CIC-Schemas forrásból átemelt fájlokban** él, nem a base-repo
meglévő kódjában:

1. **`black`/`isort` reformázná mind a 4 fájlt** (import-sorrend és egy üres
   sor a `loader.py`-ban). A `CIC-Schemas` repo nyilván más `black`/`isort`
   konfiggal (vagy más verzióval) lett formázva, mint amit a base-repo
   `infra.fmt` használ.
2. **`ruff` F401 hibát dob** a `tools/schemalib/validator.py:7`-ben: a
   `ConfigurationError` import nem használt — ez a `CIC-Schemas` forrásban is
   így van (a fájl byte-azonos), tehát ez **a `CIC-Schemas` forrásban már
   meglévő lint-hiba**, amit a base-repo szigorúbb (vagy egyszerűen aktívan
   futtatott) `ruff` lint-konfigja most felfed.

**Mindkét probléma javítása fájlmódosítást igényelne** a most átemelt
`tools/schemalib/*.py` fájlokban — ez **ellentmondana** a jelen job
"byte-azonos átemelés" kötelező DoD-pontjának (`diff -rq` üres). A job ezért
**szándékosan nem javítja** ezt — a végállapot a byte-azonos másolat
(`diff -rq` üres, ld. 1. pont), és a `make check` `EXIT=1` állapotát
**dokumentált, ismert korlátként** hagyja a következő (import-bekötő)
sub-job számára.

**Javaslat a következő lépéshez**: amikor a sub-job `tools/infra.py`/
`tools/compiler.py` ténylegesen importál a `schemalib`-ből, ott már
elkerülhetetlen a fájlok módosítása (legalább az import-sorok hozzáadása) —
ekkor a `black`/`isort`/`ruff` igazítás (a `ConfigurationError` unused import
törlése a `validator.py`-ból, ha a sub-job nem használja máshogy) **természetes
melléklépésként** elvégezhető, anélkül hogy megsértené egy "byte-azonos
átemelés" kritériumot (mert az a kritérium ott már nem érvényes).

---

## Definition of Done

- [x] `wasm/f/schemalib-transfer` branch a `wasm/main`-ből (`7a51952`)
- [x] `tools/schemalib/{__init__,artifact,loader,validator}.py` byte-azonosan átemelve, `diff -rq` üres
- [x] `tools/releaselib/exceptions.py` diff dokumentálva — nincs eltérés, nem volt szükség igazításra
- [x] `grep -rn "schemalib" ...` igazolja: 0 külső hívás a meglévő kódból
- [x] `make test` zöld (`EXIT=0`, 112 passed); `make check` **EXIT=1** — dokumentált, ismert korlát (ld. fent), nem javítva, mert javítása megsértené a byte-azonosság DoD-pontot
- [ ] PR megnyitva (`wasm/f/schemalib-transfer` → `wasm/main`) — **korlát**: a `base-repo` remote (`origin`) egy lokális mirror
  (`/home/sinkog/sync/git.partners/CentralInfraCore/.git_repos/base-repo.git`),
  nem GitHub — a branch pusholva a mirror-ra (commit `5272ed2`), a GitHub PR
  létrehozása az orchestrátor feladata (mirror → GitHub push), mint a korábbi
  jobokban.
- [x] report a `feature/wasm-schemalib-transfer`-on pusholva

## Commitok

- `base-repo` (`wasm/f/schemalib-transfer`, pusholva a lokális mirror-ra):
  - `5272ed2` — "feat(tools): add schemalib package from CIC-Schemas schemas/main"
