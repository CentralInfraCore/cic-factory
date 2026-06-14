# wasm-validation-gate-audit — Nyitott kérdés #1 és #4 felderítése

## Munkakörnyezet (futtatott)

- `CIC-Schemas` klón: checkout `2ec57c0` ("feat: unified compiler architecture —
  schemalib, repo_type routing, docs") — ez a referencia commit a sync-plan
  riportból.
- `base-repo` klón: `wasm/main` HEAD = `b7da285` ("Merge pull request #17 from
  CentralInfraCore/wasm/f/schemalib-transfer"). **Ez újabb, mint a sync-plan
  riport referenciája** (`7a51952`) — a `wasm-schemalib-transfer` job (PR #17)
  közben lezárult. Ennek hatása mindkét feladat válaszára releváns, lásd alább.
- Docker környezet-előfeltétel: a `CIC-Schemas/p_venv/` bind-mount könyvtárat a
  Docker daemon `root:root` tulajdonnal hozta létre, ami `setup` konténer
  futását `PermissionError: [Errno 13] Permission denied: '/app/p_venv/...'`-vel
  megakasztotta (`OSError: [Errno 18] Invalid cross-device link` →
  `shutil.move` fallback → permission hiba). Egyszeri javítás: `rmdir p_venv &&
  mkdir p_venv` (host oldalon, jelenlegi userrel) + `docker compose up setup`
  újrafutás. Ezután `pip install` sikeresen lezajlott, `docker compose exec
  builder python -m pytest ...` futtatható. Ez **nem** production fájl
  módosítás, kizárólag a host-oldali bind-mount könyvtár tulajdonjoga.

---

## Feladat A — `meta_schema_file` ütközés `_validate_final_project_yaml`-ban

### Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `CIC-Schemas/tools/infra.py:84-109` `_validate_final_project_yaml` a `meta_schema_file` configot (`md.meta.schema.yaml`, `CIC-Schemas/project.yaml:117`) adja át `load_and_resolve_schema`-nak, majd `run_validation(instance, schema)`-t hív (`tools/infra.py:102`) | ✅ megerősített | `tools/infra.py:84-109` statikus + futtatott | grep + futtatott szkript (lásd alább) | — |
| A `CIC-Schemas` saját tesztkészlete (`tests/test_tools/test_infra.py`, `tests/test_tools/test_infra_coverage.py`) **soha nem** futtatja `_validate_final_project_yaml`-t valódi `project.yaml`/schema fájlokkal | ✅ megerősített | `test_infra.py:188-201`, `test_infra_coverage.py:148-166` mind `load_and_resolve_schema`/`load_yaml`/`run_validation` mockolásával futnak; `test_infra.py:39` és `test_infra_coverage.py:51,65` fixture-jei `meta_schema_file: project.schema.yaml`-t adnak (sosem `md.meta.schema.yaml`-t) | `docker compose exec builder python -m pytest tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py -v -k validate_final` → 5 passed; coverage report: `tools/infra.py` "Missing" sorok között `102-103` (a `run_validation(instance, schema)` hívás sora) | — |
| `_validate_final_project_yaml` a **CIC-Schemas saját** `project.yaml`-jával (`meta_schema_file: md.meta.schema.yaml`) hívva `ValidationFailureError`-t dob: `"Validator schema 'unknown' is missing the 'spec' block: 'spec'"` | ✅ megerősített, **futtatva** | `/tmp/test_validate_a.py` futtatása `docker compose exec -T builder python3 < /tmp/test_validate_a.py` — teljes traceback lásd lent | eldobható szkript, `/tmp/` alatt, nincs commit | — |
| **Ugyanez a hiba** lép fel akkor is, ha `meta_schema_file`-t **explicit** `project.schema.yaml`-re állítjuk (a "helyes" értékre) | ✅ megerősített, **futtatva** | `/tmp/test_validate_a2.py` — azonos `ValidationFailureError: ... missing the 'spec' block: 'spec'` | eldobható szkript, `/tmp/` alatt, nincs commit | — |
| A gyökérok: `tools/schemalib/validator.py:113` `run_validation()` `validator_schema["spec"]`-t vár — ez a **schemalib-artifact dialektus** (`metadata:` + `spec:` blokkokkal, pl. `CIC-Schemas/schemas/index.yaml:1-17`), míg `project.schema.yaml` és `md.meta.schema.yaml` **nyers JSON Schema** dokumentumok (top-level kulcsaik: `['type','title','description','required','properties']` ill. `['type','required','properties']`, **nincs** `spec` kulcs) | ✅ megerősített | `python3 -c "import yaml; print(list(yaml.safe_load(open('project.schema.yaml')).keys()))"` → `['type','title','description','required','properties']`; `md.meta.schema.yaml` → `['type','required','properties']`; `validator.py:113,122-125` KeyError-kezelés | grep + python one-liner + forráskód idézet | — |
| `base-repo/wasm/main` HEAD (`b7da285`, post-PR#17) **már megoldotta** ugyanezt a problémát a **saját** (még nem schemalib-re migrált, 509 soros) `tools/infra.py`-jában: `_validate_final_project_yaml` (`base-repo/tools/infra.py:168-211`) hardcode-olja `project.schema.yaml`-t (NEM a `meta_schema_file` configot), és a sima `jsonschema.validate(instance=instance, schema=schema)`-t hívja (`infra.py:192`, `from jsonschema import validate` — `infra.py:15`), **nem** a schemalib `run_validation`-t. Explicit komment (`infra.py:170-178`) dokumentálja a `meta_schema_file` vs. `project.schema.yaml` kettősséget | ✅ megerősített | `base-repo/tools/infra.py:168-211` idézet (lásd lent) | grep + fájlolvasás, `base-repo` HEAD = `b7da285` | — |

### Futtatott bizonyíték — `/tmp/test_validate_a.py` (CIC-Schemas saját `project.yaml`, `meta_schema_file: md.meta.schema.yaml`)

```
$ docker compose exec -T builder python3 < /tmp/test_validate_a.py
INFO:test:Validating final project.yaml against schema...
Traceback (most recent call last):
  File "/app/tools/schemalib/validator.py", line 113, in run_validation
    validate(instance=instance, schema=validator_schema["spec"])
                                       ~~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'spec'
...
tools.schemalib.validator.ValidationFailureError: Validator schema 'unknown' is missing the 'spec' block: 'spec'
...
meta_schema_file from real project.yaml: md.meta.schema.yaml
RESULT: exception
ValidationFailureError : Final project.yaml validation failed: Validator schema 'unknown' is missing the 'spec' block: 'spec'
```

### Futtatott bizonyíték — `/tmp/test_validate_a2.py` (azonos config, de `meta_schema_file` felülírva `project.schema.yaml`-re)

```
$ docker compose exec -T builder python3 < /tmp/test_validate_a2.py
INFO:test2:Validating final project.yaml against schema...
RESULT: exception
ValidationFailureError : Final project.yaml validation failed: Validator schema 'unknown' is missing the 'spec' block: 'spec'
```

### base-repo's saját megoldása (b7da285) — `tools/infra.py:168-211`

```python
    def _validate_final_project_yaml(self):
        """Validates the project.yaml against the project.schema.yaml.

        Note: `compiler_settings.meta_schema_file` (e.g. md.meta.schema.yaml)
        is the meta-schema for *documentation/schema* metadata blocks
        (used by run_validation), not for project.yaml itself.
        project.yaml's own structure is always validated against the
        fixed `project.schema.yaml`, which is a plain JSON Schema (no
        top-level 'spec' wrapper).
        """
        self.logger.info("Validating final project.yaml against schema...")
        try:
            schema_path = self._path("project.schema.yaml")
            schema = load_and_resolve_schema(schema_path)
            ...
            validate(instance=instance, schema=schema)
            # WASM-delta (wasm-template-plan.md, sec. 2.2): ...
            if not instance.get("metadata", {}).get("buildHash"):
                raise ValidationFailureError(...)
            self.logger.info("✓ project.yaml is valid against the schema.")
        except ValidationFailureError:
            raise
        except (ConfigurationError, JsonSchemaValidationError) as e:
            raise ValidationFailureError(f"Final project.yaml validation failed: {e}")
        except Exception as e:
            raise ReleaseError(...)
```

### Végső válasz — Feladat A

**Nem regresszió a base-repo szempontjából, de valódi, lefedetlen hiba a
`CIC-Schemas` saját `tools/infra.py:84-109` kódjában.**

Indoklás:

1. A `CIC-Schemas` 84-soros, schemalib-alapú `_validate_final_project_yaml`
   (`tools/infra.py:84-109`) — amelyre a sync-plan riport 3. pontja a
   `base-repo/tools/infra.py` swap céljaként hivatkozik — **a saját
   `project.yaml`-jával futtatva is hibát dob**, függetlenül attól, hogy
   `meta_schema_file` `md.meta.schema.yaml` vagy `project.schema.yaml`. A hiba
   oka nem a két fájl tartalmi különbsége, hanem hogy `run_validation()`
   (schemalib/validator.py:113) egy **másik dialektust** (`metadata:`+`spec:`
   wrapper) vár, mint amit `project.schema.yaml`/`md.meta.schema.yaml`
   (nyers JSON Schema, `spec` kulcs nélkül) ad.
2. Ez a kódág **0%-os futtatott teszt-coverage**-gel rendelkezik
   (`tools/infra.py` "Missing": `102-103`) — minden vonatkozó teszt mockolja
   `load_and_resolve_schema`/`load_yaml`/`run_validation`-t, így a hiba a
   `CIC-Schemas` CI-jában soha nem jelentkezik.
3. **A `base-repo/wasm/main` (`b7da285`, post-PR#17) ezt már nem a
   `CIC-Schemas`-féle schemalib `_validate_final_project_yaml`-lal oldja meg**
   — saját, korábbi (509 soros) `tools/infra.py`-jában van egy **saját**
   `_validate_final_project_yaml`, amely explicit (kommentben dokumentált)
   módon **elkerüli** a `meta_schema_file`/`run_validation` utat, és a sima
   `jsonschema.validate()`-et hívja `project.schema.yaml`-lal. **Ez a kód már
   a jelenlegi `wasm/main` HEAD-en él** — tehát ha a sync-plan terve a
   `base-repo/tools/infra.py`-t a `CIC-Schemas` 84-soros verziójára cserélné
   **úgy, ahogy az most a `CIC-Schemas`-ban van**, ez **regressziót okozna**:
   elveszítené a `base-repo`-ban már meglévő, működő `_validate_final_project_yaml`-t
   (és a `buildHash`-ellenőrzést is, lásd `infra.py:194-199`), és lecserélné
   egy **bizonyítottan hibás** implementációra.

**Következmény a sync-plan sub-jobra**: a 3. pont (3+5. lépés: `tools/infra.py`
swap) terve nem veheti át 1:1 a `CIC-Schemas` `_validate_final_project_yaml`-ját
— ehhez előbb a `CIC-Schemas`-beli hibát kellene javítani (vagy a swap-nak meg
kellene tartania/áthoznia a `base-repo`-féle, már működő implementációt). Ez
orchestrátor-döntés, itt csak a tény van rögzítve.

---

## Feladat B — `run_validation`/`repo_type` gate vs. `make validate`

### Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `CIC-Schemas/tools/infra.py:451` `run_validation()` hívja `_require_repo_type("validate","schema")`-t (`infra.py:428-435`) | ✅ megerősített | `tools/infra.py:425-435,449-451` idézet | grep + fájlolvasás | — |
| `_get_repo_type()` (`infra.py:425-426`) `self.config.get("repo_type", "module")` — default `"module"`, ha a config nem ad meg `repo_type`-ot | ✅ megerősített | `infra.py:425-426` | fájlolvasás | — |
| `_require_repo_type("validate","schema")` `repo_type: module` (explicit VAGY default) esetén `ReleaseError`-t dob: `"Command 'validate' is only available for repo_type='schema'. This repo is configured as repo_type='module'."` | ✅ megerősített, **futtatva** | `/tmp/test_validate_b.py` — lásd lent | `docker compose exec -T builder python3 < /tmp/test_validate_b.py` | — |
| `CIC-Schemas` kódjában/tesztjeiben **0 találat** bármilyen `module`-specifikus ágra `run_validation`-ban vagy `_require_repo_type`-ban | ✅ megerősített | `grep -rn "_require_repo_type\|repo_type" tools/infra.py tools/compiler.py tests/` → csak `infra.py:425-451` (definíciók/hívások) és `test_infra.py:31` / `test_infra_coverage.py:62` (mindkettő `repo_type: schema` fixture-érték, "module" string sehol tesztben) | grep, file:line | — |
| `base-repo/wasm/main` (`b7da285`) jelenlegi `run_validation()` (`tools/infra.py:488-509`) **saját, placeholder** implementáció — **nem hívja** a `_require_repo_type`-ot és **nem** a schemalib `run_validation()`-t (`validator.py`); csak `load_and_resolve_schema(schemas/index.yaml)`-t hív és logol | ✅ megerősített | `base-repo/tools/infra.py:488-509` idézet | fájlolvasás | — |
| `base-repo/project.yaml` (`compiler_settings`, sor 44-49) **nincs** `repo_type` mező; van `meta_schema_file: md.meta.schema.yaml` (sor 47) és `canonical_source_file: schemas/index.yaml` (sor 48) | ✅ megerősített | `project.yaml:44-49` idézet | grep + fájlolvasás | — |

### Futtatott bizonyíték — `/tmp/test_validate_b.py`

```
$ docker compose exec -T builder python3 < /tmp/test_validate_b.py
repo_type from CIC-Schemas project.yaml: module
RESULT: exception
ReleaseError : Command 'validate' is only available for repo_type='schema'. This repo is configured as repo_type='module'.
repo_type default (no key set): module
RESULT2: exception
ReleaseError : Command 'validate' is only available for repo_type='schema'. This repo is configured as repo_type='module'.
```

(A teszt mindkét esetet lefedi: `CIC-Schemas/project.yaml` saját
`repo_type: module` értékével, és a `repo_type` kulcs teljes hiányával — a
default `"module"` is ugyanazt a `ReleaseError`-t adja.)

### base-repo's jelenlegi `run_validation` — `tools/infra.py:488-509`

```python
    def run_validation(self):
        """Runs offline validation on the canonical source schema."""
        self.logger.info("--- Running Schema Validation ---")
        source_file = self._path(
            self.config.get("canonical_source_file", "sources/index.yaml")
        )
        self.logger.info(f"Validating and resolving {source_file}...")
        try:
            source_data = load_and_resolve_schema(source_file)
            # Placeholder for full validation logic. Using the loaded data prevents the lint error.
            self.logger.info(
                f"Schema '{source_data.get('metadata', {}).get('name', 'N/A')}' loaded."
            )
            self.logger.info("✓ Schema validation logic to be fully implemented here.")
        except (ConfigurationError, JsonSchemaValidationError, ValueError) as e:
            self.logger.critical(f"VALIDATION FAILED: {e}")
            raise ReleaseError("Schema validation failed.") from e
        except Exception as e:
            self.logger.critical(f"UNEXPECTED ERROR during validation: {e}")
            raise ReleaseError("An unexpected error occurred during validation.") from e

        self.logger.info("✓ Validation successful.")
```

### Két irány — következmények (döntés NÉLKÜL)

**(a) `CIC-Schemas`-beli schemalib `run_validation`/`_require_repo_type` kapjon
`module`-ágat**

- Jelenleg `run_validation()` (`infra.py:449-482`) `schema`-repo-specifikus
  szemantikát implementál: betölti `canonical_source_file`-t
  (`load_and_resolve_schema`), kiolvassa `metadata.validatedBy.{name,version}`-t,
  lekéri a megfelelő validator schemát (`get_validator_schema`), és
  `run_validation(source_data, validator_schema)`-t hív rá.
- Egy `module`-ág hozzáadása megkövetelné, hogy definiáljuk: **mit jelent
  "validate" egy `module`-repo (pl. `wasm/main`) esetén**. A jelenlegi
  `canonical_source_file`/`validatedBy` modell `schema`-repókra (pl.
  `CIC-Schemas` saját `schemas/index.yaml:1-17`, ahol `metadata.validatedBy`
  egy meta-schema-ra mutat) van szabva — egy WASM binary-modulnak nincs
  "canonical source schema, amit egy validator schema ellen kell validálni"
  fogalma a jelenlegi `base-repo/project.yaml`-ban (a `canonical_source_file:
  schemas/index.yaml` ott valami mást jelölhet, de `repo_type: module`
  esetén a `validatedBy`-alapú útnak nincs megfelelője).
- Konkrét következmény: a `module`-ág vagy (i) teljesen más logikát
  implementálna (pl. csak `_validate_final_project_yaml`-t hívná — lásd (b)),
  vagy (ii) a `schema`-ági `canonical_source_file`+`validatedBy` modellt
  kellene `module`-okra kiterjeszteni, amihez `base-repo/project.yaml`-ban is
  `validatedBy` metaadatot kellene definiálni a `schemas/index.yaml`-hoz
  (jelenleg `validatedBy.name: "TBD"` — `base-repo/project.yaml:14` —
  placeholder).

**(b) `wasm/main` `compiler.py` `validate` subcommandja `_validate_final_project_yaml`-t
hívjon `run_validation()` helyett**

- Mit fed le ma `run_validation()` (`base-repo/tools/infra.py:488-509`), amit
  `_validate_final_project_yaml` **nem**:
  - `canonical_source_file` (`schemas/index.yaml`) betöltése és
    `load_and_resolve_schema`-val történő `$ref`-feloldása — ha bármelyik
    `$ref` törött vagy a YAML hibás, ez itt derülne ki. `_validate_final_project_yaml`
    ezt **nem** érinti, mert csak `project.yaml`-t validál.
  - (Megjegyzés: a jelenlegi `run_validation` maga is csak "placeholder" —
    `# Placeholder for full validation logic` — tehát ma is **semmilyen
    valódi schema-validációt nem végez** a `schemas/index.yaml` tartalmára,
    csak betölti és logol. Tehát (b) választása esetén a "elveszett
    validáció" ma még nem létező funkcionalitás elvesztése — de ha a
    sync-plan azt tervezi, hogy `run_validation`-t **schemalib-esítve**
    "teljessé" tegye (vagyis ez a placeholder válna a valódi
    schema-validáló úttá), akkor (b) választása ezt a jövőbeli funkciót
    zárná ki a `validate` subcommandból.)
  - `_validate_final_project_yaml` (mind a `base-repo` jelenlegi, mind a
    `CIC-Schemas` schemalib-verziója) **csak `project.yaml` struktúráját**
    ellenőrzi `project.schema.yaml` ellen (+ `base-repo`-nál a `buildHash`
    nem-üres ellenőrzést) — **nem** validálja a `schemas/index.yaml`
    tartalmát semmilyen módon.
- Ha (b)-t választjuk, és a `CIC-Schemas` schemalib `_validate_final_project_yaml`-ját
  hívnánk (a jelenlegi, hibás formájában), az **Feladat A** szerinti
  `ValidationFailureError: ... missing the 'spec' block`-ba futna — tehát (b)
  előfeltétele Feladat A hibájának javítása (vagy a `base-repo`-féle,
  már működő `_validate_final_project_yaml` megtartása).
- (b) esetén `_require_repo_type`/`repo_type` gate **nem releváns** a
  `validate` subcommandra — a `wasm/main` `project.yaml`-nak nem kellene
  `repo_type: module`-ot felvennie csak a `validate` parancs miatt (bár a
  `release-dependency`/`release-schema` parancsok `_require_repo_type`-ja
  Feladat B-n kívül eshet, ha azokat is a `wasm/main` használná).

### Végső megállapítás — Feladat B

- `repo_type: module` (explicit vagy default) + schemalib `run_validation()`
  hívás → **futtatott, reprodukált** `ReleaseError: "Command 'validate' is
  only available for repo_type='schema'. This repo is configured as
  repo_type='module'."`
- A `CIC-Schemas` kódbázisában **0 darab** `module`-specifikus ág van
  `run_validation`/`_require_repo_type`-ban (grep-bizonyíték fent) — a gate
  jelenleg kizárólag `schema`-repókra van szabva.
- `base-repo/wasm/main` jelenlegi `run_validation()` (`tools/infra.py:488-509`)
  egy **saját, gate nélküli placeholder**, amely független a `CIC-Schemas`
  schemalib `run_validation`-jától — ezért a gate-ütközés **ma még nem
  jelentkezik** `wasm/main`-ben, csak akkor válna problémává, ha a sync-plan
  swap után `wasm/main` `compiler.py`-ja a `CIC-Schemas`-féle
  `ReleaseManager.run_validation()`-t hívná `repo_type: module`-lal.
- (a) és (b) közötti döntés orchestrátor-szintű — mindkét irány konkrét,
  fent felsorolt következményekkel jár, és (b) Feladat A javítását is
  feltételezi.

---

## Összefoglalás a sync-plan sub-job specifikációjához

1. **Feladat A**: a `CIC-Schemas` 84-soros `_validate_final_project_yaml`
   (`tools/infra.py:84-109`) **bizonyítottan hibás** (futtatva: `KeyError:
   'spec'` → `ValidationFailureError`), 0% futtatott coverage-gel. A
   `base-repo/wasm/main` (`b7da285`) **már nem ezt használja** — saját,
   működő implementációja van. A 3+5. lépés (`tools/infra.py` swap) terve
   ezt figyelembe kell vegye: 1:1 swap regressziót okozna.
2. **Feladat B**: `repo_type: module` + schemalib `run_validation()` →
   reprodukált `ReleaseError`. `module`-ágra a `CIC-Schemas`-ban nincs
   semmilyen kezelés. (a)/(b) döntés szükséges, mindkettő következményei
   fent.
3. **Workspace-frissítés**: a `base-repo` HEAD (`b7da285`, post-PR#17 —
   `wasm-schemalib-transfer`) **újabb**, mint a sync-plan riport referenciája
   (`7a51952`). A sub-job specifikáció megírása előtt érdemes ellenőrizni,
   hogy a PR #17 milyen változásokat hozott a `base-repo/tools/infra.py`-ban
   a sync-plan riport feltételezéseihez képest — ezen audit Feladat A/B
   eredményei a `b7da285` állapotra vonatkoznak.
