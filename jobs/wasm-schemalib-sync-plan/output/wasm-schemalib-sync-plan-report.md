# wasm-schemalib-sync-plan — `schemas/main` schemalib szinkron migrációs terv

## Induló HEAD-ek

- `base-repo` (`wasm/main`): `7a51952` — "Merge pull request #13 from CentralInfraCore/wasm/f/release-contracts"
  (tartalmazza a PR #12 `verify_release.py`, PR #13 `abi.schema.yaml`/`project.schema.yaml` `abi:` blokk,
  és PR #14 `finalize_release.py` DEPRECATED jelölést — ld. `git log --oneline -5 origin/wasm/main`)
- `CIC-Schemas` (`schemas/main`, job-specifikáció szerinti referencia): `2ec57c0` — "feat: unified compiler
  architecture — schemalib, repo_type routing, docs"

## ⚠️ Kritikus korrekció a job-specifikációhoz

A job input.md azt állítja, hogy a `2ec57c0` commit "a 509 soros `tools/infra.py`-t 84 sorra csökkentő
refaktor". **Ez nem igaz a `CIC-Schemas` repo aktuális állapotára.**

- `CIC-Schemas/tools/infra.py` mérete `2ec57c0`-nál: **481 sor** (`git show 2ec57c0:tools/infra.py | wc -l`),
  a szülő commit (`070b72f`) 466 sorról nőtt 481-re.
- `base-repo/tools/infra.py` mérete `wasm/main`-en (`7a51952`): **509 sor**.
- A teljes `git log --oneline --all -- tools/infra.py | head -5` és a soronkénti `wc -l` history
  (`2ec57c0`: 481, `070b72f`: 466, `1b6d857`: 456, `d34cc8f`: 359, ...) nem mutat 84 soros állapotot
  semelyik `infra.py`-verzióban a `CIC-Schemas` historyban.

A `schemalib`-alapú refaktor **nem** az `infra.py` drasztikus zsugorítása — hanem a fájl-szintű
*helper-függvények* (checksum/signing/cert-parsing/yaml-loading/validation) kiemelése a
`tools/schemalib/{artifact,loader,validator}.py` modulokba, és a `ReleaseManager` osztály
**bővítése** új `repo_type`-routing logikával (`_get_repo_type`, `_require_repo_type`,
`run_release_dependency`, `run_release_schema`, `_execute_schema_release`). Ez a riport ezt a
tényleges diffet térképezi fel — a "84 soros" méretcél a tervezés alapjaként **nem használható**,
és a sub-job bontásnál (3. pont) ennek megfelelően nem szerepel "infra.py 84 sorra csökkentése"
mint cél.

---

## 1. Diff-térkép

### Claim-evidence tábla — `tools/infra.py`

| Állítás | Státusz | Bizonyíték (base-repo / CIC-Schemas) | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info` modul-szintű függvények kiváltva `schemalib.artifact`-tal | confirmed | base-repo: `tools/infra.py:33-70` (modul-szintű def-ek) ↔ CIC-Schemas: `tools/schemalib/artifact.py:11-13` (`to_canonical_json`), `:27-29` (`get_sha256_hex`), `:38-71` (`parse_certificate_info`); CIC-Schemas `tools/infra.py:15-20` importálja ezeket, `tools/infra.py:25` `_parse_certificate_info = parse_certificate_info` back-compat alias | `grep -n "_parse_certificate_info\|to_canonical_json\|get_sha256_hex" CIC-Schemas/tools/infra.py CIC-Schemas/tools/schemalib/artifact.py` | alacsony — szignatúra azonos (`pem_cert_data -> (name,email)`, `data -> bytes`, `bytes -> hex`) |
| `load_and_resolve_schema`, `load_yaml`, `write_yaml` kiváltva `schemalib.loader`-rel | confirmed | base-repo: `tools/infra.py:73-123` ↔ CIC-Schemas: `tools/schemalib/loader.py:40-90` (`load_and_resolve_schema` — most JSON round-trip + `convert_to_json_serializable` is van, base-repo-ban nincs), `:93-106` (`load_yaml`), `:109-129` (`write_yaml`); CIC-Schemas `tools/infra.py:21` importálja | `grep -n "load_and_resolve_schema\|load_yaml\|write_yaml" CIC-Schemas/tools/infra.py base-repo/tools/verify_release.py:38` | **közepes** — `load_and_resolve_schema` viselkedése bővült (JsonRef proxy → plain dict JSON round-trip), a base-repo verzió `JsonRef.replace_refs` eredményt ad vissza nyersen (`tools/infra.py:82`: `return resolved_data` — JsonRef objektum, nem plain dict). `base-repo/tools/verify_release.py:54` (`schema = load_and_resolve_schema(schema_path)`) és `jsonschema_validate(instance=instance, schema=schema)` ettől függ — ha `schema` JsonRef helyett plain dict lesz, a `jsonschema.validate` hívás működhet ugyanúgy, de ezt futtatással kell igazolni (ld. 4. pont) |
| `ValidationFailureError` osztály áthelyezve `schemalib.validator`-ba | confirmed | base-repo: `tools/infra.py:27-30` (`class ValidationFailureError(ReleaseError)`) ↔ CIC-Schemas: `tools/schemalib/validator.py:13-15`; CIC-Schemas `tools/infra.py:22` importálja, `__all__`-ban exportálja (`tools/infra.py:29`) | `grep -n "ValidationFailureError" CIC-Schemas/tools/infra.py CIC-Schemas/tools/schemalib/validator.py base-repo/tools/infra.py` | alacsony — osztálynév és bázisosztály (`ReleaseError`) azonos |
| `ReleaseManager.__init__`, `_path`, `_check_base_branch_and_version`, `_check_api_accessibility` változatlan | confirmed | base-repo: `tools/infra.py:127-166` ↔ CIC-Schemas: `tools/infra.py:43-82` — szó szerint azonos kód | `diff <(sed -n '127,166p' base-repo/tools/infra.py) <(sed -n '43,82p' CIC-Schemas/tools/infra.py)` → nincs eltérés | nincs |
| `_validate_final_project_yaml`: hardcoded `project.schema.yaml` → `config.get("meta_schema_file", ...)`, `jsonschema.validate` → `schemalib.validator.run_validation`, **WASM `buildHash` kötelezőség-check eltávolítva** | confirmed | base-repo: `tools/infra.py:168-209` — `schema_path = self._path("project.schema.yaml")` (`:180`), `validate(instance=instance, schema=schema)` (`:192`), WASM-delta check `:196-200` (`if not instance.get("metadata", {}).get("buildHash"): raise ValidationFailureError(...)`) ↔ CIC-Schemas: `tools/infra.py:84-109` — `schema_path = self._path(self.config.get("meta_schema_file", "project.schema.yaml"))` (`:88-90`), `run_validation(instance, schema)` (`:102`), **nincs buildHash-check** | `grep -n "buildHash\|meta_schema_file\|project.schema.yaml" base-repo/tools/infra.py CIC-Schemas/tools/infra.py` | **magas** — két független eltérés egyszerre: (a) a buildHash-kötelezőség wasm-specifikus és elveszik, ld. 2. pont; (b) a `meta_schema_file` config-kulcs `wasm/main` `project.yaml`-jában `md.meta.schema.yaml`-re van állítva (`base-repo/project.yaml:47`), ami **nem** projekt-szintű schema — ld. 4. pont nyitott kérdés |
| `_execute_developer_preparation_phase`: checksum/signing logika `schemalib.artifact` primitívekre cserélve, `createdBy.name/email` kitöltési sorrend megváltozott | confirmed | base-repo: `tools/infra.py:211-350`, checksum: `to_canonical_json`+`get_sha256_hex` (`:246-247`), signing payload kézzel összeállítva (`:265-277`), `_parse_certificate_info` (`:262`) ↔ CIC-Schemas: `tools/infra.py:111-240`, checksum: `compute_spec_checksum` (`:143`), signing payload: `build_signing_payload(...)` (`:161-166`), `parse_certificate_info` (`:187`) — funkcionálisan ekvivalens, de a `createdBy` dict előbb `None`/`None` placeholderrel jön létre (`:177-182`), utána íródik felül (`:187-189`), míg base-repo egy lépésben tölti ki (`:291-296`) | `diff <(sed -n '244,302p' base-repo/tools/infra.py) <(sed -n '170,192p' CIC-Schemas/tools/infra.py)` | alacsony — a végeredmény `metadata` dict azonos kulcsokkal jön létre, de a kétlépéses `createdBy` build-up tesztelhető mellékhatás-különbség (mock sorrend a unit tesztekben) |
| `_resign_with_build_hash` metódus **megszűnt** `schemas/main`-ben | confirmed | base-repo: `tools/infra.py:352-385` (`def _resign_with_build_hash(self, project_yaml_path)`), hívás: `tools/infra.py:406` (`_execute_finalization_phase`-ből) ↔ CIC-Schemas: `grep -n "_resign_with_build_hash" CIC-Schemas/tools/infra.py` → **nincs találat** | `grep -n "_resign_with_build_hash" base-repo/tools/infra.py CIC-Schemas/tools/infra.py base-repo/tests/test_tools/test_infra_coverage.py` (a teszt `mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")`-t hív, `:121,208`) | **magas** — wasm-specifikus, ld. 2. pont. Megszűnése a `schemas/main` oldalon **elvárt** (schema repóknak nincs `buildHash`-uk), de wasm oldalon megtartandó |
| `_execute_finalization_phase`: `_resign_with_build_hash` hívás hiánya | confirmed | base-repo: `tools/infra.py:406` (`self._resign_with_build_hash(project_yaml_path)`, a `_validate_final_project_yaml()` után, a git commit előtt) ↔ CIC-Schemas: `tools/infra.py:256-260` — a `_validate_final_project_yaml()` után közvetlenül a git-commit blokk jön, nincs resign hívás | `diff <(sed -n '394-410p' base-repo/tools/infra.py) <(sed -n '249-262p' CIC-Schemas/tools/infra.py)` | magas — ld. 2. pont |
| `run_release_close` orchestráció azonos | confirmed | base-repo: `tools/infra.py:450-486` ↔ CIC-Schemas: `tools/infra.py:387-423` — szó szerint azonos | `diff <(sed -n '450,486p' base-repo/tools/infra.py) <(sed -n '387,423p' CIC-Schemas/tools/infra.py)` | nincs |
| `run_validation`: base-repo placeholder-implementáció → CIC-Schemas teljes schema-validátor-lánc, `repo_type="schema"`-ra gátolva | confirmed | base-repo: `tools/infra.py:488-509` — `# Placeholder for full validation logic` (`:497`), nincs repo_type-check ↔ CIC-Schemas: `tools/infra.py:449-482` — `self._require_repo_type("validate", "schema")` (`:451`), majd `get_validator_schema`+`run_validation` teljes lánc | `grep -n "_require_repo_type\|Placeholder" base-repo/tools/infra.py CIC-Schemas/tools/infra.py` | **magas** — `wasm/main` `project.yaml`-jában `repo_type` mező **nincs** (ld. project.schema.yaml diff alább), és a wasm modul `repo_type` értéke `schemas/main` saját `project.yaml`-ja szerint `module` lenne (`CIC-Schemas/project.yaml:114`: `repo_type: module`). Ha a `schemalib`-es `run_validation` `_require_repo_type("validate","schema")`-t hív, és `wasm/main`-en `make validate` ezt hívja (`base-repo/tools/compiler.py:209-212`: `args.command == "validate"` → `manager.run_validation()`), a hívás **`ReleaseError`-ral elhasal** `module` repo_type esetén. Ld. 4. pont nyitott kérdés: a wasm modul `make validate`-jének mi legyen az új tartalma? |
| `_get_repo_type`/`_require_repo_type`/`run_release_dependency`/`run_release_schema`/`_execute_schema_release` — **új** metódusok `schemas/main`-ben, wasm-nek nem közvetlenül relevánsak | confirmed | CIC-Schemas: `tools/infra.py:425-482` ↔ base-repo: nincs megfelelő | `grep -n "_get_repo_type\|_require_repo_type\|run_release_dependency\|run_release_schema\|_execute_schema_release" base-repo/tools/infra.py` → nincs találat | alacsony — additív, wasm modul `repo_type=module`-mal ezeket sosem hívja (`_require_repo_type` mindig `ReleaseError`-t dob `module`-ra) |

### Claim-evidence tábla — `tools/compiler.py`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `set-build-hash` subcommand **csak** `wasm/main`-en létezik, `schemalib`-es `compiler.py`-ban nincs | confirmed | base-repo: `tools/compiler.py:116-126` (parser def), `:133-160` (kezelő, stdlib-only hashlib+regex, explicit kommenttel: "Deliberately avoids importing tools.infra ... so this command works even before the builder's p_venv cache (infra.deps) has been populated", `:134-137`) ↔ CIC-Schemas: `grep -n "set-build-hash" CIC-Schemas/tools/compiler.py` → nincs találat | `grep -rn "set-build-hash\|set_build_hash" base-repo/mk/wasm.mk base-repo/tools/compiler.py` → hívási hely: `base-repo/mk/wasm.mk:29` (`python -m tools.compiler set-build-hash --file $(WASM_OUT) --project project.yaml`) | **magas** — ld. 2. pont, a wasm build-pipeline kritikus láncszeme |
| `validate` subcommand help-szövege és viselkedése eltér | confirmed | base-repo: `tools/compiler.py:103-105` (`help="Validate all schemas."`), `:209-212` (`logger.info("--- Running Schema Validation ---")`, `manager.run_validation()`, `logger.info("✓ All schemas are valid.")`) ↔ CIC-Schemas: `tools/compiler.py:104-106` (`help="Validate source schema against its declared validator."`), `:207-208`-nak megfelelő blokk — a `--- Running...`/`✓ All schemas...` log-sorok hiányoznak (a `run_validation()` belül logol) | `diff <(sed -n '103,105p' base-repo/tools/compiler.py) <(sed -n '104,106p' CIC-Schemas/tools/compiler.py)` | közepes — kozmetikai + a 2. pontban tárgyalt `_require_repo_type` miatt funkcionálisan is eltér |
| `release-dependency`, `release-schema`, `get-name` subcommandok **csak** `schemas/main`-ben, wasm-nek nem kell | confirmed | CIC-Schemas: `tools/compiler.py:118-150` (parser-ek), `:158-166`, `:212-217` (kezelők) ↔ base-repo: `grep -n "release-dependency\|release-schema\|get-name" base-repo/tools/compiler.py` → nincs találat | `grep -rn "get-name\|release-dependency\|release-schema" base-repo/Makefile base-repo/mk/` → nincs hívási hely | alacsony — additív, opcionális átvétel |
| `release`-parser és a fő `main()` try/except keret azonos | confirmed | base-repo: `tools/compiler.py:107-114, 162-231` ↔ CIC-Schemas: megfelelő blokkok szó szerint azonosak (csak a `validate`/`release-dependency`/`release-schema` elif-ágak térnek el) | `diff` a `main()` elejére/végére | nincs |

### Claim-evidence tábla — `tools/finalize_release.py`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A két fájl **funkcionálisan azonos** — csak a `wasm/main` PR #14-es DEPRECATED fejjegyzete az eltérés | confirmed | `diff base-repo/tools/finalize_release.py CIC-Schemas/tools/finalize_release.py` → 1 hunk, `base-repo/tools/finalize_release.py:17-24`: 8 soros `# DEPRECATED: ...` komment-blokk, ami hivatkozik `tools/infra.py:352-385`-re (`_resign_with_build_hash`) mint az aktív release-lánc részére | `diff base-repo/tools/finalize_release.py CIC-Schemas/tools/finalize_release.py`; `grep -rn "finalize_release" base-repo/Makefile base-repo/mk/ base-repo/.github` → nincs hívási hely (megerősíti a "dead code" állítást) | alacsony — ha a DEPRECATED komment `tools/infra.py:352-385`-re hivatkozik és az a metódus megszűnik a migráció során (ld. infra.py tábla), a komment szövegét frissíteni kell, de a fájl maga törölhető/megtartható döntés az orchestrátoré |

### Claim-evidence tábla — `project.schema.yaml`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `wasm/main` top-level `additionalProperties: false` + `required: [compiler_settings, abi]`, `schemas/main`-ben nincs `abi` | confirmed | base-repo: `project.schema.yaml:7-9` (`required: [compiler_settings, abi]`), `:9` (`additionalProperties: false`) ↔ CIC-Schemas: `project.schema.yaml` megfelelő blokkjában nincs `abi`, nincs top-level `additionalProperties: false` (a `diff` `7,9d6` és `9d6`-os törlés-sorai) | `diff base-repo/project.schema.yaml CIC-Schemas/project.schema.yaml` (1-9. sor körüli hunk) | magas — ld. 2. pont, az `abi:` blokk wasm-specifikus és nem törölhető |
| `metadata` blokk: `wasm/main` 9 extra mezőt definiál (`tags`, `validatedBy`, `createdBy`, `build_timestamp`, `validity`, `checksum`, `sign`, `buildHash`, `cicSign`, `cicSignedCA`), `schemas/main`-ben ezek **nincsenek** a `project.schema.yaml`-ban | confirmed | base-repo: `project.schema.yaml:47-133` (a teljes blokk, pl. `buildHash` `:99-104` `pattern: '^([a-f0-9]{64}|TBD)?$'`) ↔ CIC-Schemas: `diff` `47,133d42` — a teljes blokk hiányzik | `diff base-repo/project.schema.yaml CIC-Schemas/project.schema.yaml` (47-133. sor körüli hunk); `grep -n "buildHash" base-repo/project.yaml base-repo/mk/wasm.mk` — a `project.yaml:?` `metadata.buildHash` mező és a `mk/wasm.mk:29` `set-build-hash` írja | **magas** — ld. 2. pont; ezek nélkül `project.yaml` validáció elbukna a `wasm/main` `project.yaml`-ra (amely tartalmazza ezeket a mezőket) |
| `compiler_settings`: `schemas/main` `repo_type` enumot + 7 új mezőt (`source_dir` átpozicionálva, `main_branch`, `dependencies_dir`, `release_dir`, `validity_days`, stb.) ad hozzá, `wasm/main`-ben ezek nincsenek | confirmed | CIC-Schemas: `project.schema.yaml` `compiler_settings.properties` blokkjában `repo_type` (enum: `["schema","workflow","module"]`), `main_branch`, `dependencies_dir`, `release_dir`, `validity_days`, stb. ↔ base-repo: `grep -n "repo_type\|main_branch\|dependencies_dir\|release_dir\|validity_days" base-repo/project.schema.yaml` → nincs találat | `diff base-repo/project.schema.yaml CIC-Schemas/project.schema.yaml` (177-216. sor körüli hunk) | közepes — additív mezők, de a `repo_type` bevezetése közvetlenül hat a `_require_repo_type` viselkedésre (ld. infra.py tábla `run_validation` sora) |
| `compiler_settings.additionalProperties: false` `wasm/main`-en megvan, `schemas/main`-ben hiányzik | confirmed | base-repo: `project.schema.yaml:185` (`additionalProperties: false` a `compiler_settings` blokkban) ↔ CIC-Schemas: a megfelelő blokkban nincs `additionalProperties: false` | `diff` 185. sor körül | alacsony — ha `wasm/main` átveszi a `schemas/main` `compiler_settings` definícióját `additionalProperties: false` nélkül, az megengedőbb (nem szigorúbb) — visszafelé kompatibilis, de elveszik a wasm-oldali "typo a configban" elleni védelem, amíg vissza nem kerül |

---

## 2. wasm-specifikus réteg — mit KELL megtartani

A `450ac0c` óta (és a PR #12/#13/#14 által) bevezetett, **a `schemas/main` `2ec57c0`-ban nem létező**
elemek, amelyek a migráció során **nem törölhetők**:

### 2.1 `tools/infra.py:196-200` — `metadata.buildHash` kötelezőség-check

```python
if not instance.get("metadata", {}).get("buildHash"):
    raise ValidationFailureError(
        "metadata.buildHash is required and must be non-empty before "
        "finalization — run 'make wasm.build' to populate it."
    )
```

- Hívási hely: `_validate_final_project_yaml` (`tools/infra.py:168-209`), amit `_execute_finalization_phase`
  hív (`tools/infra.py:401`).
- A `schemalib`-es `_validate_final_project_yaml` (CIC-Schemas `tools/infra.py:84-109`) ezt **nem**
  tartalmazza, mert schema repóknak nincs `buildHash`-uk.
- **Beillesztési pont**: ha a `schemalib`-es `infra.py`-t veszi át `wasm/main`, ennek a checknek
  `_validate_final_project_yaml` végére (a `run_validation(instance, schema)` után, mielőtt
  `"✓ project.yaml is valid..."` logolódik) vissza kell kerülnie — vagy egy wasm-specifikus
  `ReleaseManager` subclass / hook-pont formájában, vagy `repo_type`-alapú elágazással
  (`if self._get_repo_type() == "module": ...`).

### 2.2 `tools/infra.py:352-385` — `_resign_with_build_hash`

```python
def _resign_with_build_hash(self, project_yaml_path):
    """Re-signs project.yaml metadata so the Vault signature also covers
    metadata.buildHash ..."""
```

- Hívási hely: `_execute_finalization_phase:406`, a `_validate_final_project_yaml()` után, a git
  commit előtt.
- `schemas/main`-ben **nincs megfelelője** — a schema-release flow (`_execute_schema_release`,
  CIC-Schemas `tools/infra.py:303-385`) egy lépésben számolja a checksumot és írja alá
  (`build_signing_payload` + `vault_service.sign`), nincs külön "resign buildHash után" fázis,
  mert schema artifactnak nincs binárisa/`buildHash`-a.
- **Beillesztési pont**: a `schemalib`-es `_execute_finalization_phase` (CIC-Schemas
  `tools/infra.py:242-301`) `_validate_final_project_yaml()` hívása (`:256`) és a git-dirty-check
  (`:262`) közé kell beszúrni egy `_resign_with_build_hash(project_yaml_path)` hívást — a metódus
  törzse átvehető a `schemalib.artifact.build_signing_payload`/`get_sha256_hex` primitívekkel
  átírva (a jelenlegi `to_canonical_json`+`hashlib` helyett).

### 2.3 `tools/compiler.py:116-160` — `set-build-hash` subcommand

```python
build_hash_parser = subparsers.add_parser(
    "set-build-hash",
    help="Compute sha256(artifact) and write it to project.yaml metadata.buildHash.",
    ...
)
```

- Hívási hely: `base-repo/mk/wasm.mk:29` — `python -m tools.compiler set-build-hash --file $(WASM_OUT)
  --project project.yaml`, a WASM build-pipeline (`make wasm.build`) lépése.
- A handler (`tools/compiler.py:133-160`) explicit "stdlib-only, no tools.infra import" megjegyzéssel
  (`:134-137`) — ez **független** az `infra.py`/`schemalib` migrációtól, mert szándékosan nem
  importál semmit a `tools.infra`-ból.
- **Beillesztési pont**: ez a blokk **változatlanul átemelhető** a `schemalib`-es `compiler.py`-ba —
  nincs ütközés, mert `args.command == "set-build-hash"` ág a `try:` blokk (és így a
  `ReleaseManager`/`schemalib` import-lánc) előtt fut le (`tools/compiler.py:133` < `:162`).

### 2.4 `project.schema.yaml:9, 215-216` — top-level `abi:` blokk és `required: [..., abi]`

```yaml
required:
  - compiler_settings
  - abi
additionalProperties: false
...
  abi:
    $ref: "abi.schema.yaml"
```

- Hívási hely: `base-repo/project.yaml:59` (`abi:` top-level kulcs), `base-repo/tools/verify_release.py:52-68`
  (`check_schema`: "1. project.yaml validates against project.schema.yaml (incl. abi.schema.yaml via $ref)"),
  `base-repo/module/abi_manifest_test.go` (a PR #13 leírása szerint — ld. `verify_release.py:126`
  `check_abi_exports`: "project.yaml abi.exports == module.wasm exports (module/abi_manifest_test.go)").
- `schemas/main`-ben nincs `abi.schema.yaml` fájl, és a `project.schema.yaml`-ban nincs `abi:` kulcs
  (`grep -n "abi" CIC-Schemas/project.schema.yaml` → nincs találat).
- **Beillesztési pont**: ha `wasm/main` átveszi a `schemas/main` `project.schema.yaml`
  `compiler_settings`/`metadata` struktúráját, a top-level `required:`/`additionalProperties: false`
  és az `abi:` `$ref` blokkot **vissza kell illeszteni** — ezek a `schemalib`-es schema-loadinggal
  (`load_and_resolve_schema`, amely `$ref`-eket resolve-ol, ld. infra.py tábla) kompatibilisek,
  mivel az `abi.schema.yaml` egy külön fájlra mutató `$ref`, amit `JsonRef.replace_refs`
  (`schemalib/loader.py:62-70`) ugyanúgy resolve-ol, mint a base-repo-s `load_and_resolve_schema`
  (`base-repo/tools/infra.py:73-87`, `JsonRef.replace_refs(unresolved_data, base_uri=base_uri)`).
  Funkcionális kompatibilitás → **nyitott kérdés**, ld. 4. pont (a `convert_to_json_serializable`
  JSON round-trip hatása az `abi.schema.yaml` `$ref`-re nincs futtatva ellenőrizve).

### 2.5 `project.schema.yaml:47-133` — `metadata` release-mezők (`buildHash`, `cicSign`, `cicSignedCA`, `sign`, `checksum`, `build_timestamp`, `validity`, `validatedBy`, `createdBy`, `tags`)

- Hívási helyek: `base-repo/project.yaml` `metadata:` blokk mind a 10 mezőt használja (placeholder
  `"TBD"` értékekkel template állapotban); `tools/infra.py:285-300` (`_execute_developer_preparation_phase`)
  és `:358-384` (`_resign_with_build_hash`) írja őket; `tools/verify_release.py:173-234`
  (`check_provenance`) olvassa őket riport céljából.
- `schemas/main` `project.schema.yaml`-jában ezek a mezők **nincsenek definiálva** a `metadata`
  blokkban (`diff` 47-133. sor) — ami azt jelenti, hogy ha `wasm/main` átvenné a `schemas/main`
  `project.schema.yaml` `metadata` blokkját változatlanul, a saját `project.yaml`-ja
  (amely ezeket a mezőket tartalmazza) **bukna** a `additionalProperties`/`required` validáción
  (ha azok be vannak állítva a `metadata` blokkban — ezt explicit ellenőrizni kell, ld. 4. pont,
  mert a `diff` nem mutatja `metadata.additionalProperties` értékét közvetlenül).
- **Beillesztési pont**: ezt a 87 soros blokkot szó szerint vissza kell másolni a migrált
  `project.schema.yaml` `metadata.properties` alá.

---

## 3. Migrációs sorrend és sub-job bontási javaslat

A "84 soros infra.py" cél törlésével a tényleges migráció **additív szinkronizáció**: a
`schemalib`-es primitívek importja + a `repo_type` routing bevezetése, **a wasm-specifikus
réteg (2. pont) megtartásával/visszaillesztésével**. Javasolt sorrend:

1. **`tools/schemalib/` package átemelése változatlanul** `wasm/main`-be (`CIC-Schemas/tools/schemalib/{__init__,artifact,loader,validator}.py` →
   `base-repo/tools/schemalib/`). Önállóan végezhető, kockázat: alacsony — új fájlok, semmi
   meglévőt nem érint, amíg nincs import rájuk.
   - **Önálló sub-job lehet**: igen (méret: 4 fájl, ~420 sor, tisztán additív).

2. **`tools/releaselib/exceptions.py` ellenőrzése** — `schemalib.loader`/`validator`
   `ConfigurationError`/`ReleaseError`-t importál (`from ..releaselib.exceptions import ...`,
   `schemalib/loader.py:13`, `schemalib/validator.py:8`); `base-repo/tools/releaselib/exceptions.py`
   (45 sor) és `CIC-Schemas/tools/releaselib/exceptions.py` (45 sor) sor-egyezését ellenőrizni kell
   (`wc -l` egyezik, de tartalom-diff nem volt a scope-ban — **nyitott kérdés**, ld. 4. pont).
   - **Az 1. lépéssel egy jobban végezhető** (gyors `diff`, ha eltér, igazítás).

3. **`tools/infra.py` cseréje a `schemalib`-alapú verzióra + a 2. pont wasm-specifikus
   visszaillesztései egyetlen lépésben**:
   - importok cseréje `schemalib.{artifact,loader,validator}`-ra (CIC-Schemas `tools/infra.py:1-39`
     mintájára),
   - `_validate_final_project_yaml`: `run_validation(instance, schema)` használata +
     **2.1 buildHash-check visszaillesztése**,
   - `_execute_finalization_phase`: **2.2 `_resign_with_build_hash` metódus és hívás
     visszaillesztése** (átírva `schemalib.artifact` primitívekre),
   - `_execute_developer_preparation_phase`: checksum/signing átírása
     `compute_spec_checksum`/`build_signing_payload`/`parse_certificate_info`-ra,
   - `run_validation`: **nyitott kérdés** (ld. 4. pont) — a `_require_repo_type("validate","schema")`
     gate miatt `wasm/main` `make validate`-jének új tartalmat kell adni, vagy a wasm
     `ReleaseManager.run_validation`-t felül kell írni `module` repo_type-ra.
   - **Nem bontható kisebb sub-jobra** kockázat-mentesen — a 3 wasm-specifikus visszaillesztés
     (2.1-2.3 közül 2.1+2.2) és az import-csere egymásra épül (mind az `_execute_finalization_phase`
     metódust érinti), külön commitokban próbálva átmenetileg törött állapotot eredményezne.
     **Egy jobban végzendő**, méret: ~480 sor cél-fájl + ~50 sor wasm-specifikus visszaillesztés.
     Kockázat: **magas** — a 4. pont nyitott kérdéseinek (különösen `meta_schema_file` és
     `run_validation`/`repo_type`) tisztázása **előfeltétel**, különben a `make release`
     finalizációs lánc némán más schema-fájlt validálna vagy `make validate` elhasalna.

4. **`tools/compiler.py` hívási helyek frissítése**:
   - `set-build-hash` subcommand **megtartása változatlanul** (2.3 — nincs ütközés).
   - `validate` subcommand: a 3. lépés `run_validation`-döntésétől függő szöveg/logika igazítása.
   - `release-dependency`/`release-schema`/`get-name` subcommandok átvétele **opcionális** —
     `wasm/main`-nek `repo_type=module` esetén `_require_repo_type` miatt ezek sosem futnának
     hasznosan, de a parser-definíció és `elif`-ágak hozzáadása ártalmatlan (additív).
   - **A 3. lépéssel egy jobban végzendő** (a `compiler.py` `validate`-ág a 3. lépés
     `run_validation`-implementációjától függ).

5. **`project.schema.yaml` szinkronizálása**: `schemas/main` `compiler_settings`/`repo_type`-bővítések
   átvétele + **2.4 (`abi:` blokk, top-level `required`/`additionalProperties`) és 2.5
   (`metadata` release-mezők) visszaillesztése**.
   - **Önálló sub-job lehet**: igen, de **csak a 3-4. lépés után** indítható, mert a `repo_type`
     mező bevezetése (és `wasm/main` `project.yaml`-jának `repo_type: module` beállítása) a
     `_require_repo_type`-gated `run_validation`/`run_release_*` metódusok viselkedését
     közvetlenül befolyásolja — sorrendi függőség, nem párhuzamosítható a 3. lépéssel.
   - Méret: ~90 sor visszaillesztés + ~40 sor új mező átvétel. Kockázat: közepes.

6. **`tests/test_tools/test_infra.py` és `test_infra_coverage.py` frissítése**:
   - `test_infra_coverage.py:121,208`: `mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")`
     — ha a 3. lépés visszaillesztette a metódust (2.2), ez a mock továbbra is működik; ha nem,
     a teszt `AttributeError`-ral elhasal.
   - Minden `tools.infra.load_and_resolve_schema`/`load_yaml`/`write_yaml`/`_parse_certificate_info`
     patch-pont (`test_infra_coverage.py:149,156,157,163,174,177,178,180,192,223,232`) továbbra is
     érvényes, mert ezek a nevek a CIC-Schemas `tools/infra.py` `__all__`/import-jaiban megvannak
     (`tools/infra.py:25-39`).
   - **A 3. lépéssel egy jobban végzendő** — a forráskód-csere és a teszt-igazítás nem
     választható szét a CI-zöld állapot megtartása mellett.

### Összefoglaló sorrend

```
1. tools/schemalib/ átemelés          [önálló sub-job, alacsony kockázat]
2. releaselib/exceptions.py diff-check [1-gyel egyben]
3. tools/infra.py csere + 2.1/2.2 visszaillesztés + run_validation döntés
   + tools/compiler.py validate-ág   [EGYBEN, magas kockázat — 4. pont
                                       tisztázása előfeltétel]
4. set-build-hash megtartás           [3-mal egyben, csak ellenőrzés]
5. project.schema.yaml szinkron + 2.4/2.5 visszaillesztés
                                       [3-4 UTÁN, közepes kockázat]
6. tesztek igazítása                  [3-mal egyben]
```

---

## 4. Kockázatok és nyitott kérdések

1. **`meta_schema_file` ütközés `_validate_final_project_yaml`-ban.**
   `CIC-Schemas/tools/infra.py:88-90` a `project.yaml` validálásához
   `self.config.get("meta_schema_file", "project.schema.yaml")`-t használ.
   `base-repo/project.yaml:47` (és `CIC-Schemas/project.yaml:117` is!) `meta_schema_file:
   md.meta.schema.yaml`-t állít be. `md.meta.schema.yaml` (mindkét repóban, `head -20`
   alapján azonos tartalom) egy `tags`/`related_nodes`/`category`/`entrypoint`/`used_in`/
   `description` mezőket megkövetelő dokumentációs meta-schema — **nem** alkalmas
   `project.yaml` (amelynek `metadata`/`spec`/`compiler_settings`/`abi` a struktúrája)
   validálására. `base-repo/tools/infra.py:171-176` explicit kommentben rögzíti, hogy
   `meta_schema_file` **nem** a `project.yaml` schema-ja, és ezért a base-repo verzió
   hardcode-olja `project.schema.yaml`-t (`:180`).
   → **Nyitott kérdés**: ez egy valódi regresszió a `schemas/main` `2ec57c0`-ban (azaz
   `_execute_finalization_phase` → `_validate_final_project_yaml` minden `repo_type`-ra
   rossz schema-fájlt töltene be és a `run_validation` `jsonschema.validate` hívása
   `md.meta.schema.yaml` ellen elhasalna `project.yaml`-on), vagy van egy köztes lépés/
   config, amit nem láttunk? Ezt csak **futtatással** (`make release` finalizációs ág
   egy teszt-checkout-on, vagy a `CIC-Schemas` saját `tests/test_tools/test_infra*.py`
   futtatásával) lehet eldönteni. Nem feltételezünk — ha a `CIC-Schemas` 182 teszte zöld
   `2ec57c0`-nál ezzel a konfiggal, az azt jelentené, hogy `_validate_final_project_yaml`
   útja a tesztekben sosem éri el ezt az ágat (mock?), nem hogy helyesen működik.

2. **`load_and_resolve_schema` JSON round-trip hatása `JsonRef` objektumokra.**
   A `schemalib.loader.load_and_resolve_schema` (CIC-Schemas `tools/schemalib/loader.py:40-90`)
   egy extra `convert_to_json_serializable` + `json.dumps`/`json.loads` round-tripet végez a
   `JsonRef.replace_refs` eredményén, amit a base-repo verzió (`tools/infra.py:73-87`) nem tesz
   meg (nyers `JsonRef` proxy objektumot ad vissza). `base-repo/tools/verify_release.py:54-61`
   ezt az eredményt adja át `jsonschema_validate(instance=instance, schema=schema)`-nak —
   funkcionálisan ekvivalensnek *kellene* lennie (a JSON round-trip plain dict-et ad, ami a
   jsonschema-nak jobb), de az `abi.schema.yaml` `$ref`-ek és bármilyen `datetime`-mező
   (`build_timestamp`) viselkedése a round-trip után **nincs futtatással ellenőrizve**.
   → **Nyitott kérdés**: futtatni kell `load_and_resolve_schema(base-repo/project.schema.yaml)`-t
   mindkét implementációval és diffelni az eredményt, mielőtt a csere megtörténik.

3. **`tools/releaselib/exceptions.py` tartalmi egyezés.**
   Mindkét repóban 45 sor, de a tartalmi `diff` nem készült el (a job time-boxban a fő fájlokra
   fókuszáltunk). `schemalib/loader.py` és `schemalib/validator.py` ebből importál
   (`ConfigurationError`, `ReleaseError`) — ha a két `exceptions.py` API-ja eltér (pl. más
   kivétel-hierarchia), a `schemalib` import közvetlenül törne `wasm/main`-en.
   → **Nyitott kérdés**: `diff base-repo/tools/releaselib/exceptions.py
   CIC-Schemas/tools/releaselib/exceptions.py` — ezt a sub-job 1-2. lépésében kötelezően el kell
   végezni, mielőtt a `schemalib` package-et átemelik.

4. **`run_validation` / `repo_type` gate hatása `make validate`-re.**
   `wasm/main` `project.yaml`-jában nincs `repo_type` mező (a `project.schema.yaml` sem
   definiálja). Ha a migráció bevezeti a `repo_type` enumot és `wasm/main` `project.yaml`-ja
   `repo_type: module`-ot kapna (ahogy `CIC-Schemas` saját `project.yaml:114`-ben is `module`),
   akkor a `schemalib`-es `run_validation` (`_require_repo_type("validate","schema")`,
   CIC-Schemas `tools/infra.py:451`) **mindig** `ReleaseError`-t dobna `wasm/main`-en
   `make validate`-re (`base-repo/tools/compiler.py:209-212` jelenleg ezt hívja).
   → **Nyitott kérdés**: mi legyen `make validate` új viselkedése `module` repo_type esetén?
   Lehetséges irányok (nem döntjük el): (a) `run_validation` kapjon egy `module`-ágat, ami a
   jelenlegi placeholder-logikát futtatja; (b) `wasm/main` `compiler.py` a `validate`
   subcommandot ne `manager.run_validation()`-re, hanem `_validate_final_project_yaml()`-re
   (vagy egy új, modul-specifikus metódusra) routolja. Ez architekturális döntés, amit az
   orchestrátornak kell meghoznia, a kód maga nem ad egyértelmű választ.

5. **`createdBy` mezőkitöltés kétlépéses build-up (CIC-Schemas) vs egylépéses (base-repo)
   — viselkedésbeli eltérés csak teszteléssel deríthető ki.**
   `CIC-Schemas/tools/infra.py:177-189` előbb `None`/`None` placeholdert ír `createdBy.name`/
   `email`-be, majd felülírja a `parse_certificate_info` eredményével. Ha bármely köztes
   logika (pl. `write_yaml` `dry_run` ág, `:194-198`) a `metadata` dict-et a `parse_certificate_info`
   hívás *előtt* olvasná, `None` értékeket kapna — de a kódban a `dry_run` log a `parse_certificate_info`
   *után* van (`:194` < `:187`? — nem, `:187` < `:194`, tehát sorrend helyes). Jelenlegi
   olvasat szerint nincs hibás ág, de ezt **egységteszttel** kell megerősíteni a migráció után,
   nem csak statikus olvasással.

6. **`project.schema.yaml` `metadata.additionalProperties`/`required` pontos értéke a
   `schemas/main` oldalon nincs idézve a riportban** (a `diff` csak a *hiányzó* blokkokat
   mutatta, nem a `schemas/main` `metadata` blokk teljes `required`/`additionalProperties`
   beállítását). Ha `schemas/main` `metadata.additionalProperties: false`-t használ és nem
   ismeri a wasm-specifikus mezőneveket, a 2.5 pontban leírt visszaillesztés *szükséges*
   feltétel, de **az is nyitott**, hogy a `required` lista is bővül-e (jelenleg base-repo
   `metadata.required`-jét nem idéztük teljes egészében). → A sub-job 5. lépésében a teljes
   `metadata` blokk `required`/`additionalProperties` mezőit explicit össze kell vetni, nem
   csak a `properties` listát.

---

## Definition of Done — önellenőrzés

- [x] `wasm/main` (`7a51952`) és `schemas/main` (`2ec57c0`) induló HEAD-jei rögzítve
- [x] 1. pont: claim-evidence tábla a 4 fájl diff-térképével, file:line hivatkozásokkal
- [x] 2. pont: wasm-specifikus megtartandó részek listája file:line-nal
- [x] 3. pont: sorrendezett migrációs/sub-job bontási javaslat
- [x] 4. pont: nyitott kérdések listája
- [ ] report a `feature/wasm-schemalib-sync-plan`-on pusholva (következő lépés)
