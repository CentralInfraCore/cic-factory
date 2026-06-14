# wasm-validation-gate-audit — Nyitott kérdés #1 és #4 felderítése

## Reasoning mód

**audit** — kísérleti/felderítő, **nem implementáció**. A cél két nyitott
architektúrális kérdés megválaszolása **futtatott bizonyítékkal**, mielőtt a
`wasm-schemalib-sync-plan` riport (3. pont, 3+5. lépés: `tools/infra.py` swap
+ `tools/compiler.py` validate-routing) sub-job specje megírható.

Forrás: `cic-factory/jobs/wasm-schemalib-sync-plan/output/wasm-schemalib-sync-plan-report.md`,
"4. Kockázatok és nyitott kérdések" szakasz, 1. és 4. pont. KB node `c1295`.

## Munkakörnyezet

- `CIC-Schemas` klón: `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/wasm-validation-gate-audit/workspace/CIC-Schemas`,
  checkout `2ec57c0` (a sync-plan riport referencia commitja).
- `base-repo` klón: `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/wasm-validation-gate-audit/workspace/base-repo`,
  `wasm/main` HEAD.

---

## Feladat A — Nyitott kérdés #1: `meta_schema_file` ütközés `_validate_final_project_yaml`-ban

**Háttér:** `CIC-Schemas/tools/infra.py:88-90` a `project.yaml` validálásához
`self.config.get("meta_schema_file", "project.schema.yaml")`-et használ.
`CIC-Schemas/project.yaml:117` és `base-repo/project.yaml:47` is
`meta_schema_file: md.meta.schema.yaml`-t állít be — ez egy dokumentációs
meta-schema (`tags`/`related_nodes`/`category`/`entrypoint`/`used_in`/
`description` mezőkkel), **nem** alkalmas a `project.yaml`
(`metadata`/`spec`/`compiler_settings`/`abi` struktúra) validálására.
`base-repo/tools/infra.py:171-180` ezt explicit kommenttel hardcode-olja ki
(`project.schema.yaml`-t használ, nem a `meta_schema_file` értékét).

**Kérdés:** a `CIC-Schemas/tools/infra.py:88-90` `_validate_final_project_yaml`
útja a `CIC-Schemas` saját tesztkészletében **valóban lefut-e** ezzel a
configgal (`meta_schema_file: md.meta.schema.yaml`), és ha lefut, **mi
történik** — `jsonschema.validate` hibát dob `project.yaml` ellen
`md.meta.schema.yaml`-lal, vagy van valami köztes lépés amit a statikus
olvasás nem mutatott?

**Lépések:**

1. `cd CIC-Schemas && git log --oneline -3` — rögzítsd a tényleges checkout
   commitot.
2. `grep -rn "_validate_final_project_yaml\|meta_schema_file" tools/infra.py
   tests/` — listázd az összes hívási helyet és teszt-referenciát file:line-nal.
3. Futtasd a release/finalize-ágat fedő teszteket (pl. `tests/test_tools/test_infra*.py`,
   vagy amit a 2. pont grep felfed) a builder konténerben (`docker compose exec
   builder python -m pytest <path> -v` vagy `make test` ha az egész suite
   szükséges) — **idézd a teljes releváns kimenetet** (PASS/FAIL/SKIP soronként
   a `_validate_final_project_yaml`-t érintő tesztekre).
4. Ha a tesztek **nem** futtatják le ezt az ágat éles `project.yaml`-lal (mock-olva
   van, vagy `meta_schema_file` mást kap a tesztfixture-ben), **igazold ezt
   konkrét fixture/mock kóddal** (file:line idézet a tesztből).
5. Ha **futtatható** valódi `project.yaml`-lal: írj egy minimál, **eldobható**
   Python szkriptet (`/tmp/` alá, NEM commitolva semelyik repóba), amely
   meghívja `_validate_final_project_yaml`-t (vagy az azt hívó metódust) a
   `CIC-Schemas/project.yaml`-jával, és **idézd a teljes traceback-et vagy
   sikeres kimenetet**.

**Elvárt válasz a riportban:** "valódi regresszió" VAGY "nem regresszió, mert
[konkrét ok, file:line bizonyítékkal]" — találgatás nélkül, futtatott
kimenettel alátámasztva.

---

## Feladat B — Nyitott kérdés #4: `run_validation`/`repo_type` gate vs. `make validate`

**Háttér:** `CIC-Schemas/tools/infra.py:451` a `run_validation`-ban
`_require_repo_type("validate","schema")`-t hív. `CIC-Schemas/project.yaml:114`
`repo_type: module`. `base-repo/project.yaml`-ban **nincs** `repo_type` mező,
és `base-repo/tools/compiler.py:209-212` a `validate` subcommand mögött
`manager.run_validation()`-t hívja.

**Kérdés:** ha `wasm/main` `project.yaml`-ja megkapná a `repo_type: module`
mezőt és a `schemalib`-es `run_validation`-t hívná, **pontosan milyen hibát**
dob `_require_repo_type("validate","schema")` — és van-e a `CIC-Schemas`
kódban/tesztekben már létező `module`-ágra utaló kezelés?

**Lépések:**

1. `grep -rn "_require_repo_type\|repo_type" CIC-Schemas/tools/infra.py
   CIC-Schemas/tools/compiler.py CIC-Schemas/tests/` — listázd file:line-nal
   az összes definíciót, hívási helyet és teszt-referenciát.
2. Olvasd el `_require_repo_type` teljes implementációját (file:line) — milyen
   `repo_type` értékekre **nem** dob hibát `("validate","schema")` esetén?
3. Írj egy minimál, **eldobható** Python szkriptet (`/tmp/` alá, NEM commitolva),
   amely `repo_type: module`-bal hívja `run_validation`-t (minimál
   `project.yaml`/`project.schema.yaml` fixture-rel, pl. a `CIC-Schemas` saját
   `project.yaml`-jával) — **idézd a pontos kivételt/hibaüzenetet vagy a
   sikeres kimenetet**.
4. Dokumentáld: van-e a `CIC-Schemas` kódjában **bármilyen** `module`-specifikus
   ág `run_validation`-ban vagy `_require_repo_type`-ban (file:line, vagy "nincs,
   0 találat" + grep-bizonyíték).

**Elvárt válasz a riportban:** a két lehetséges irány (a) `run_validation`
kapjon `module`-ágat, vagy (b) `wasm/main` `compiler.py` ne `run_validation`-t,
hanem `_validate_final_project_yaml`-t hívja a `validate` subcommandhoz —
**ne válassz köztük** (ez orchestrátor-döntés), de a riportban soroljad fel
minden ismert következményt (pl. (b) esetén mi marad ellenőrizetlen, amit
`run_validation` ma lefedne).

---

## Tiltott rövidítések (kötelező)

- **Statikus olvasás ≠ működik.** "A kód statikus olvasása alapján X-nek
  kellene lennie" nem elfogadható válasz — mindkét kérdésre **futtatott**
  bizonyíték (teszt-output, traceback, vagy explicit mock/fixture-idézet)
  szükséges.
- **Ne módosíts** semmilyen production fájlt (`tools/infra.py`,
  `tools/compiler.py`, `project.schema.yaml`, `project.yaml`) sem a
  `CIC-Schemas`, sem a `base-repo` klónban. Az eldobható kísérleti szkriptek
  `/tmp/` alá kerülnek, **nem** kerülnek commitba semelyik repóban.
- **Ne dönts** (a) vs (b) között a Feladat B-ben — sorold fel a
  következményeket, a döntés az orchestrátoré.
- Ha egy teszt/kísérlet futtatása Docker-előfeltételt igényel (`docker compose
  exec builder` / `docker compose run --rm setup`), ezt egyszeri,
  környezet-előfeltételként végezd el és jelezd a riportban.

---

## Reachability / futtatási bizonyíték

Ez Python réteg (`tools/*.py`, `tests/*.py`), nem Go — a `_test.go`/`deadcode
./...` ellenőrzés nem releváns. A bizonyíték helyette: **minden állításhoz
konkrét, idézett parancssor + kimenet** (pytest output, traceback, vagy grep
eredmény file:line-nal). Pusztán a kód elolvasása alapján tett állítás
**FAIL**.

---

## Output

`jobs/wasm-validation-gate-audit/output/wasm-validation-gate-audit-report.md`:

- Claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`)
  mindkét feladatra (A és B).
- Feladat A: végső válasz — "regresszió" vagy "nem regresszió + ok", futtatott
  bizonyítékkal.
- Feladat B: a két irány (a)/(b) következményei, futtatott bizonyítékkal
  alátámasztva, döntés NÉLKÜL.

## Git instrukciók

- `cic-factory`: commit + push **csak** `feature/wasm-validation-gate-audit`-ra.
- `base-repo` és `CIC-Schemas`: **semmilyen módosítás, semmilyen commit/push**
  — tisztán olvasás + `/tmp/` alatti eldobható szkriptek.

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, parancsok, commit message: **angolul**
