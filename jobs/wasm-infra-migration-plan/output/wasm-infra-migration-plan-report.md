# wasm-infra-migration-plan — `tools/infra.py` / `tools/compiler.py` / `project.schema.yaml` migrációs terv

## Induló állapotok (ellenőrizve)

- `base-repo` (`wasm/main`): **`b7da285`** — "Merge pull request #17 from
  CentralInfraCore/wasm/f/schemalib-transfer" — **megegyezik** az input.md-ben
  jelzettel.
- `CIC-Schemas` (`schemas/main`, referencia): **`2ec57c0`** — "feat: unified
  compiler architecture — schemalib, repo_type routing, docs" — megegyezik.

**Fontos korrekció a sync-plan riport óta**: a `wasm-schemalib-transfer` job
(PR #17) **már átemelte** `base-repo/tools/schemalib/{__init__,artifact,
loader,validator}.py`-t (4 fájl) és ellenőrizte, hogy
`base-repo/tools/releaselib/exceptions.py` **bit-azonos**
`CIC-Schemas/tools/releaselib/exceptions.py`-jal (sync-plan 4. pont, nyitott
kérdés #3 — **lezárva**, `diff` üres).

Azonban **`base-repo/tools/infra.py` (509 sor) még nem importálja** ezeket az
új `tools/schemalib/` modulokat — a modul-szintű primitívek
(`to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`,
`load_and_resolve_schema`, `load_yaml`, `write_yaml`, `ValidationFailureError`)
**duplikáltan** élnek `infra.py:27-123`-ban. Ez a jelen job tényleges scope-ja:
ezeket az importokra cserélni, a `repo_type`-routing kérdést (2. előre
eldöntött korlát szerint) **nem** bevezetni, és a `project.schema.yaml`
szinkronizálását elvégezni a wasm-specifikus réteg megtartásával.

A `base-repo/tools/schemalib/{artifact,loader,validator}.py` a PR #17 során
**enyhén eltérő formázással** (whitespace, import-sorrend, egy extra
defenzív `or "Unknown"`/`or "unknown@example.com"` fallback
`parse_certificate_info`-ban) került át — funkcionálisan ekvivalens vagy
**szigorúbb** a `CIC-Schemas` 2ec57c0-as verziójához képest (lásd 1. tétel).

---

## Claim-evidence tábla (1-8. tétel)

| # | Állítás (ADOPT/PRESERVE/SKIP + cél file:line) | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|---|
| 1 | **ADOPT**: `infra.py:27-70` (dup. `ValidationFailureError`, `to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`) → import `from .schemalib.artifact import to_canonical_json, get_sha256_hex, parse_certificate_info` + `from .schemalib.validator import ValidationFailureError` + `_parse_certificate_info = parse_certificate_info` back-compat alias | confirmed | `base-repo/tools/infra.py:27-70` (duplikált def-ek) ↔ `base-repo/tools/schemalib/artifact.py:11-13,25-27,35-66` (már létező, transzferált primitívek, `parse_certificate_info:63` defenzívebb: `name or "Unknown", email or "unknown@example.com"` siker-ágon is, szemben `infra.py:65`-tel ahol siker-ágon nincs fallback) | `grep -n "^def to_canonical_json\|^def get_sha256_hex\|^def _parse_certificate_info\|^class ValidationFailureError" base-repo/tools/infra.py base-repo/tools/schemalib/{artifact,validator}.py` | alacsony — a `schemalib`-es `parse_certificate_info` **szigorúbb** (extra fallback), nem szűkebb; a `_parse_certificate_info = parse_certificate_info` alias megtartja a `tests/test_tools/test_infra_coverage.py:180` `mocker.patch("tools.infra._parse_certificate_info", ...)` patch-pontot |
| 2 | **ADOPT**: `infra.py:73-123` (dup. `load_and_resolve_schema`/`load_yaml`/`write_yaml`) → `from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml` | confirmed, **futtatva** | `base-repo/tools/infra.py:73-123` ↔ `base-repo/tools/schemalib/loader.py:39-131` (már transzferált, `CIC-Schemas/tools/schemalib/loader.py`-jal csak whitespace-eltérés) | `/tmp/test_load_and_resolve_compare.py` futtatása — ld. lent | **alacsony** — futtatva: mindkét implementáció `base-repo/project.schema.yaml`-t (incl. `abi:` `$ref`) azonos plain-dict-té oldja fel, és `jsonschema.validate(instance=<base-repo/project.yaml>, schema=...)` **mindkét esetben hiba nélkül lefut** |
| 3 | **ADOPT**: `infra.py:244-302` (`_execute_developer_preparation_phase` checksum/signing) → `compute_spec_checksum`/`build_signing_payload`/`parse_certificate_info` (`schemalib.artifact`), `createdBy` kétlépéses build-up (CIC-Schemas minta) | confirmed, **futtatva** | `base-repo/tools/infra.py:246-301` ↔ `CIC-Schemas/tools/infra.py:143-192` | `/tmp/test_createdby_buildup_compare.py` futtatása — ld. lent; `pytest tests/test_tools/test_infra.py::TestReleaseManager::test_developer_preparation_phase_success` — **PASS** (lásd lent) | alacsony — futtatva: a két build-up variáns **bit-azonos végeredmény dict**-et ad; a kétlépéses verzióban (CIC-Schemas `infra.py:177-189`) **nincs** köztes olvasás a `None`/`None` placeholder és a felülírás között |
| 4 | **PRESERVE**: `_resign_with_build_hash` (`base-repo/tools/infra.py:352-385`), hívás `_execute_finalization_phase`-ből (`:406`) — **megerősítve** a `b7da285`-ön. Belső törzs ADOPT-olja a `to_canonical_json`/`get_sha256_hex`-et az 1. tételben importált `schemalib.artifact`-ból (csak az import-forrás változik, a logika nem) | confirmed | `base-repo/tools/infra.py:352-385` (`def _resign_with_build_hash`), hívás `:406` | `grep -n "_resign_with_build_hash" base-repo/tools/infra.py CIC-Schemas/tools/infra.py` → base-repo: 2 találat (def `:352`, hívás `:406`); CIC-Schemas: 0 találat | magas — wasm-kritikus; **FIGYELEM**: az 1-2. tétel miatt `infra.py` eleje ~91 sorral csökken (97 sor törölve, ~6 sor import hozzáadva) → `_resign_with_build_hash` és hívása **el fog csúszni** kb. `261-294` / `~315`-re. Re-grep kötelező az implementációs job-ban |
| 5 | `finalize_release.py` DEPRECATED komment (8 soros blokk, `base-repo/tools/finalize_release.py:17-24`) `tools/infra.py:352-385`-re hivatkozik — **PRESERVE a komment, de a hivatkozott sortartomány frissítendő** az 1-2. tételben leírt sor-eltolódás miatt | confirmed | `base-repo/tools/finalize_release.py:17-24` idézet lent | `grep -n "tools/infra.py:352-385\|DEPRECATED" base-repo/tools/finalize_release.py` | alacsony — tisztán dokumentációs frissítés, nincs funkcionális hatás; ha elmarad, a komment téves sorszámra mutat, de nem tör semmit |
| 6 | **SKIP**: `_get_repo_type`/`_require_repo_type`/`run_release_dependency`/`run_release_schema`/`_execute_schema_release` (CIC-Schemas `tools/infra.py:303-385,425-482`) — ne kerüljenek át `base-repo/tools/infra.py`-ba | confirmed | `CIC-Schemas/tools/infra.py:303-385` (`_execute_schema_release`), `:425-435` (`_get_repo_type`/`_require_repo_type`), `:437-447` (`run_release_dependency`/`run_release_schema`) ↔ `base-repo`: 0 találat | `grep -rn "_get_repo_type\|_require_repo_type\|run_release_dependency\|run_release_schema\|_execute_schema_release\|repo_type" base-repo/tools/ base-repo/project.yaml base-repo/Makefile base-repo/mk/` → **0 találat** | alacsony — additív, de a 2. előre eldöntött korlát szerint `wasm/main` `validate`-je `_validate_final_project_yaml`-t hívja, nem `run_validation`-t; ezeket a metódusokat `repo_type=module` esetén sosem hívná semmi → tiszta holt kód lenne, ha átvennénk |
| 7 | **ADOPT** (részleges) + **PRESERVE** (részleges): `project.schema.yaml` `compiler_settings` blokk — vedd át a `CIC-Schemas` `repo_type` enumot + additív mezőket (`main_branch`, `dependencies_dir`, `release_dir`, `validity_days`, `cic_root_ca_secret_name`, stb.), de **tartsd meg** `compiler_settings.additionalProperties: false`-t (`base-repo/project.schema.yaml:185`). `base-repo/project.yaml` `compiler_settings`-be **fel kell venni `repo_type: module`-ot** (önkonzisztencia miatt — ha a schema `required`-jébe bekerül `repo_type`, a `project.yaml`-nak is rendelkeznie kell vele) | confirmed | `base-repo/project.schema.yaml:177-216` ↔ `CIC-Schemas/project.schema.yaml:86-141` (`repo_type` `:90,96-99`); `base-repo/project.yaml` `compiler_settings` (jelenleg nincs `repo_type` kulcs) | `diff` a két `compiler_settings` blokkon (lent); `grep -n "repo_type" base-repo/project.yaml` → 0 találat | közepes — a `repo_type: module` mező felvétele **operatívan inert** (a 2. korlát miatt `_require_repo_type` sosem fut wasm/main-en), de **szükséges** a schema-konzisztenciához, ha a `required` lista `repo_type`-ot is tartalmazza |
| 8 | **PRESERVE**: `project.schema.yaml:47-133` `metadata` blokk 9 extra wasm-mezője (`tags`, `validatedBy`, `createdBy`, `build_timestamp`, `validity`, `checksum`, `sign`, `buildHash`, `cicSign`, `cicSignedCA`) + top-level `required: [metadata, compiler_settings, abi]` (`:5-8`) + `additionalProperties: false` (`:9`) + `abi:` `$ref` (`:215-216`) — **megerősítve** a jelenlegi `b7da285`-ön | confirmed | `base-repo/project.schema.yaml:5-9` (top-level `required`+`additionalProperties`), `:47-133` (metadata extra mezők, `tags` `:47` → `cicSignedCA` `:125-133`), `:215-216` (`abi: $ref`) ↔ `CIC-Schemas/project.schema.yaml`: nincs `abi`, nincs top-level `additionalProperties: false`, a `metadata` blokkban nincs a 9 extra mező (`diff` `47,133d42` és `7,9d6`/`9d6`) | `diff base-repo/project.schema.yaml CIC-Schemas/project.schema.yaml` (teljes diff lent) | magas — ezek nélkül `base-repo/project.yaml` (amely mind a 9 mezőt + `abi:`-t tartalmazza) elbukna a validáción |

---

## Migrációs tábla

| Tétel | Döntés | Forrás file:line (CIC-Schemas / base-repo schemalib) | Cél file:line (base-repo `tools/infra.py`, jelenlegi `b7da285`-ön) | Indoklás |
|---|---|---|---|---|
| 1. Modul-szintű primitívek (`to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`, `ValidationFailureError`) | **ADOPT** (import-csere) | `base-repo/tools/schemalib/artifact.py:11-13,25-27,35-66`; `base-repo/tools/schemalib/validator.py` (`ValidationFailureError` class); import-minta: `CIC-Schemas/tools/infra.py:15-25` | `infra.py:27-70` törlés → import-blokk (`infra.py:1-24` után) | A `schemalib` package már transzferálva (PR #17); az `infra.py` csak nem importálja még. Duplikáció megszüntetése, defenzívebb `parse_certificate_info` öröklése |
| 2. `load_and_resolve_schema`/`load_yaml`/`write_yaml` | **ADOPT** (import-csere) | `base-repo/tools/schemalib/loader.py:39-131`; import-minta: `CIC-Schemas/tools/infra.py:21` | `infra.py:73-123` törlés → `from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml` | Futtatva igazolt funkcionális ekvivalencia (`/tmp/test_load_and_resolve_compare.py`) — `abi.schema.yaml` `$ref` resolution és `jsonschema.validate` mindkét variánssal sikeres |
| 3. `_execute_developer_preparation_phase` checksum/signing | **ADOPT** | `CIC-Schemas/tools/infra.py:143-192` (`compute_spec_checksum`, `build_signing_payload`, kétlépéses `createdBy`) | `infra.py:246-301` (jelenlegi: checksum `:246-247`, certs `:250-263`, signing `:265-282`, `createdBy` `:291-296`) — átírás után **shiftelt** sorszámokon | Futtatva igazolt: bit-azonos végeredmény `metadata` dict, nincs intermediate-read kockázat |
| 4. `_resign_with_build_hash` + hívás | **PRESERVE** (törzs ADOPT-olja a `schemalib.artifact` importokat) | n/a — `schemas/main`-ben nincs megfelelő | `infra.py:352-385` (def), hívás `:406` — **shiftelt** kb. `261-294`/`~315`-re az 1-2. tétel miatt | Wasm-kritikus, sync-plan + validation-gate-audit megerősítette; `to_canonical_json`/`get_sha256_hex` immár az 1. tételben importált `schemalib.artifact`-ból jön, törzs logika változatlan |
| 5. `finalize_release.py` DEPRECATED komment | **PRESERVE** (sorhivatkozás frissítendő) | n/a | `finalize_release.py:17-24` — a benne hivatkozott `tools/infra.py:352-385` → frissítendő az új (shiftelt) `_resign_with_build_hash` sortartományra | Dokumentációs pontosság — a komment funkcionálisan nem hat semmire |
| 6. `_get_repo_type`/`_require_repo_type`/`run_release_dependency`/`run_release_schema`/`_execute_schema_release` | **SKIP** | `CIC-Schemas/tools/infra.py:303-385,425-482` | — (nem kerül át) | 0 grep-találat hívásra `base-repo`-ban; a 2. korlát szerint `validate` nem `run_validation`-t hívja → ezek holt kód lennének |
| 7a. `project.schema.yaml` `compiler_settings.repo_type` enum + additív mezők | **ADOPT** | `CIC-Schemas/project.schema.yaml:90,96-99,109-141` (`repo_type`, `main_branch`, `canonical_source_file`, `dependencies_dir`, `release_dir`, `cic_root_ca_key_name`, `cic_root_ca_secret_name`, `validity_days`, stb.) | `base-repo/project.schema.yaml:177-214` (`compiler_settings.properties` blokk kiegészítése) | Additív, konzisztencia `schemas/main`-nel; `repo_type` mező felvétele a séma `required`-jébe |
| 7b. `compiler_settings.additionalProperties: false` | **PRESERVE** | n/a — `schemas/main`-ben hiányzik | `base-repo/project.schema.yaml:185` — megtartás | Wasm-oldali config-typo védelem; megengedőbbé tenni regresszió lenne |
| 7c. `base-repo/project.yaml` `compiler_settings.repo_type: module` felvétele | **ADOPT** (új mező a project.yaml-ban) | `CIC-Schemas/project.yaml:114` (`repo_type: module` minta) | `base-repo/project.yaml` `compiler_settings:` blokk (jelenleg ~44-49. sor) — `repo_type: module` hozzáadása | Ha 7a. bekerül és `repo_type` a `required` listában van, `project.yaml`-nak is kell hogy legyen — önkonzisztencia, de a 2. korlát miatt `_require_repo_type` sosem fut |
| 8a. `project.schema.yaml` top-level `required`/`additionalProperties` + `abi:` `$ref` | **PRESERVE** | n/a — `schemas/main`-ben nincs `abi.schema.yaml` | `base-repo/project.schema.yaml:5-9,215-216` — megtartás változatlanul | Wasm ABI-kontraktus (`module/abi_manifest_test.go`), törlése `make wasm.test`-et törne |
| 8b. `project.schema.yaml` `metadata` 9 extra mezője | **PRESERVE** | n/a — `schemas/main`-ben nincs | `base-repo/project.schema.yaml:47-133` — megtartás változatlanul | `base-repo/project.yaml` mind a 9 mezőt használja; `tools/infra.py:285-300`/`_resign_with_build_hash` írja, `verify_release.py:173-234` (`check_provenance`) olvassa |

---

## Futtatott bizonyítékok

### 2. tétel — `load_and_resolve_schema` viselkedés-összehasonlítás

Szkript: `/tmp/test_load_and_resolve_compare.py` (eldobható, nem commitolva).
Mindkét implementáció `base-repo/project.schema.yaml`-t (amely `abi:`
`$ref: "abi.schema.yaml"`-t tartalmaz) tölti be, majd a kapott `schema`-t
`jsonschema.validate(instance=<base-repo/project.yaml>, schema=...)`-nak adja.

```
=== VARIANT A: base-repo tools/infra.py:73-87 (raw JsonRef) ===
type(schema_a) = <class 'dict'>
top-level keys = ['type', 'title', 'description', 'required', 'additionalProperties', 'properties']
schema_a['properties']['abi'] resolved? True -> keys=['type', 'title', 'description', 'required', 'additionalProperties']
jsonschema.validate(instance, schema_a) -> OK (no exception)

=== VARIANT B: CIC-Schemas tools/schemalib/loader.py:39-85 (JSON round-trip) ===
type(schema_b) = <class 'dict'>
top-level keys = ['type', 'title', 'description', 'required', 'additionalProperties', 'properties']
schema_b['properties']['abi'] resolved? True -> keys=['type', 'title', 'description', 'required', 'additionalProperties']
jsonschema.validate(instance, schema_b) -> OK (no exception)

=== DIFF: variant A vs variant B (resolved schema, JSON-serialized) ===
IDENTICAL
```

**Következtetés**: a `schemalib`-es `load_and_resolve_schema` JSON
round-trip-je **nem** változtatja meg a `base-repo/project.schema.yaml`
(incl. `abi.schema.yaml` `$ref`) feloldott alakját — a két implementáció
bit-azonos eredményt ad, és `base-repo/tools/verify_release.py:54-61` (amely
`load_and_resolve_schema` eredményét adja `jsonschema_validate`-nek) **nem
törne** a 2. tétel ADOPT-jától.

### 3. tétel — `createdBy` build-up sorrend-összehasonlítás

Szkript: `/tmp/test_createdby_buildup_compare.py` (eldobható, nem commitolva).

```
Variant A (base-repo, single-step): {'name': 'wasm-module-template', 'version': '1.0.0', 'checksum': '...', 'sign': 'FAKE_SIGNATURE', 'build_timestamp': '2026-06-14T00:00:00+00:00', 'createdBy': {'name': 'Test User', 'email': 'test@user.com', 'certificate': 'FAKE_USER_CERT_PEM', 'issuer_certificate': 'FAKE_CA_CERT_PEM'}, 'buildHash': '', 'cicSign': '', 'cicSignedCA': {'certificate': ''}}

Variant B (CIC-Schemas, two-step):   {'name': 'wasm-module-template', 'version': '1.0.0', 'checksum': '...', 'sign': 'FAKE_SIGNATURE', 'build_timestamp': '2026-06-14T00:00:00+00:00', 'createdBy': {'name': 'Test User', 'email': 'test@user.com', 'certificate': 'FAKE_USER_CERT_PEM', 'issuer_certificate': 'FAKE_CA_CERT_PEM'}, 'buildHash': '', 'cicSign': '', 'cicSignedCA': {'certificate': ''}}

IDENTICAL final dict: True

Intermediate-read risk: any code reading metadata['createdBy'] between
dict-creation and the two assignment lines in variant B would observe
{'name': None, 'email': None, ...} -- variant A has no such window.
grep for any such intermediate read in CIC-Schemas tools/infra.py:170-192:
177:                "createdBy": {
188:            metadata["createdBy"]["name"] = cert_name
189:            metadata["createdBy"]["email"] = cert_email
```

A `grep` 0 köztes hivatkozást talált `metadata["createdBy"]`-ra a
dict-létrehozás (`:177`) és a felülírás (`:188-189`) között — nincs
intermediate-read kockázat.

### Meglévő teszt-suite — `base-repo/tests/test_tools/` (lokális venv, nem Docker)

```
$ python3 -m pytest tests/test_tools/test_infra.py tests/test_tools/test_infra_coverage.py -q --no-cov
collected 31 items
tests/test_tools/test_infra.py .................                         [ 54%]
tests/test_tools/test_infra_coverage.py ..............                   [100%]
============================== 31 passed in 0.35s ==============================
```

Ez **31/31 zöld** a jelenlegi (migráció előtti) `b7da285` állapoton — ez a
baseline, amit a migrációs sub-jobnak fenn kell tartania. (Megjegyzés:
Docker/`docker compose` helyett lokális venv-ben futott — `pip install -r
requirements.txt` egy `/tmp/wasm-infra-venv`-be, ez nem production fájl.)

`tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema`
(a `wasm-schemalib-transfer` job által hozzáadott, mock-mentes teszt a valós
`project.schema.yaml`/`project.yaml`-lal) **már lefedi** a 4. tétel
(`_validate_final_project_yaml`, PRESERVE) regressziómentességét — ezt a
sub-jobnak futtatva is ellenőriznie kell minden infra.py-edit után.

### 6. tétel — `_get_repo_type` stb. reachability `base-repo`-ban

```
$ grep -rn "_get_repo_type|_require_repo_type|run_release_dependency|run_release_schema|_execute_schema_release|repo_type" \
    base-repo/tools/ base-repo/project.yaml base-repo/Makefile base-repo/mk/
(0 találat)
```

---

## Idézetek

### `base-repo/tools/finalize_release.py:17-24` (DEPRECATED komment)

```python
# DEPRECATED: This module is dead code on the production release path
# (no Makefile/mk/*.mk/.github/workflows/*.yml call site — verified via
# `grep -rn "finalize_release"`). The active release chain is
# `make release` -> tools.compiler -> tools.infra.ReleaseManager
# (see tools/infra.py:352-385 for the checksum+buildHash signing model).
# Track relay-readiness as a separate milestone; delete this module on
# relay GA (cf. CIC-Schemas compiler-architecture-plan.md, "Step 10").
```

A komment `tools/infra.py:352-385`-re hivatkozik — ez a `_resign_with_build_hash`
**jelenlegi** (migráció előtti) sortartománya. Az 1-2. tétel ADOPT-jai
(~91 sornyi törlés `infra.py` elejéről) miatt ez **el fog csúszni** — a
sub-jobnak az edit után `grep -n "_resign_with_build_hash" tools/infra.py`-vel
meg kell határoznia az új sortartományt, és ezt a kommentet frissítenie kell
rá (pl. `tools/infra.py:261-294`, becsült — pontos érték az edit után).

### `project.schema.yaml` diff — base-repo (`b7da285`) vs CIC-Schemas (`2ec57c0`), tömörített

A teljes `diff base-repo/project.schema.yaml CIC-Schemas/project.schema.yaml`
162 sor; a fő hunk-ok:

```diff
7,9d6
<   - compiler_settings
<   - abi
< additionalProperties: false          # PRESERVE (8a)
20d16
<     additionalProperties: false      # metadata blokk, nem érintett
47,133d42
< ... 9 extra metadata mező (tags..cicSignedCA) ...   # PRESERVE (8b)
180a90
>       - repo_type                     # ADOPT (7a) -> project.schema.yaml required-be
185d94
<     additionalProperties: false      # PRESERVE (7b), compiler_settings blokk
187c96
<       component_name:
---
>       repo_type:                      # ADOPT (7a)
192c102
<       meta_schema_file:
---
>       source_dir:
194c104
<       canonical_source_file:
---
>       meta_schema_file:
196d105
<       (canonical_source_file leírás eltér)
200c109
<       cic_root_ca_key_name:
---
>       component_name:
202,203c111,118
>       main_branch / canonical_source_file / dependencies_dir /
>       release_dir / cic_root_ca_key_name / validity_days  # ADOPT (7a), additív
213,216c135,141
>       cic_root_ca_secret_name / validity_days              # ADOPT (7a)
<   abi:
<     $ref: "abi.schema.yaml"           # PRESERVE (8a)
```

(A teljes, nyers `diff` kimenet `/tmp/project_schema_diff.txt`-ben él az
agent workspace-ben, eldobható — a fenti tömörítés lefedi a migrációs tábla
7a/7b/8a/8b tételeit.)

---

## Sorrendezett lépéslista a következő (implementációs) sub-jobnak

Minden lépés után futtatandó: `python3 -m pytest tests/test_tools/ -q --no-cov`
(lokális venv, ld. fent — vagy `make check`/`make test` Docker-ben, ha
elérhető). A `TestValidateFinalProjectYamlRealSchema` és a 31 jelenlegi teszt
**mindvégig zöld** kell maradjon.

1. **Import-blokk bővítése** (`infra.py:1-24`):
   - hozzáadás: `from .schemalib.artifact import to_canonical_json, get_sha256_hex, parse_certificate_info`
   - hozzáadás: `from .schemalib.loader import load_and_resolve_schema, load_yaml, write_yaml`
   - hozzáadás: `from .schemalib.validator import ValidationFailureError`
   - hozzáadás: `_parse_certificate_info = parse_certificate_info` (back-compat alias, közvetlenül az import-blokk után)
   - megtartandó importok: `requests`, `yaml`, `from OpenSSL import crypto` ha máshol is kell — **ellenőrizni**, hogy `infra.py:168-385` (a PRESERVE-elt `_validate_final_project_yaml`/`_resign_with_build_hash`) nem hivatkozik-e közvetlenül `JsonRef`/`hashlib`/`base64`-ra, amit eddig a (most törlendő) modul-szintű def-ek hoztak be — ha igen, ezeket az importokat meg kell tartani vagy hozzáadni.

2. **Törlés**: `infra.py:27-70` (dup. `ValidationFailureError`, `to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`) — 1. tétel.

3. **Törlés**: `infra.py:73-123` (dup. `load_and_resolve_schema`, `load_yaml`, `write_yaml`) — 2. tétel.

4. **Re-grep**: `_validate_final_project_yaml`, `_execute_developer_preparation_phase`,
   `_resign_with_build_hash`, `_execute_finalization_phase` új sorszámai a
   2-3. lépés utáni `infra.py`-ban — frissítsd a 4-5. tétel sorhivatkozásait
   ehhez a jegyzethez (nem kódba, csak a sub-job saját jegyzeteibe).

5. **`_execute_developer_preparation_phase` átírása** (3. tétel) —
   `to_canonical_json(source_data["spec"])` + manual digest →
   `compute_spec_checksum(source_data["spec"])` + `build_signing_payload(...)`;
   `_parse_certificate_info` → `parse_certificate_info`; `createdBy`
   kétlépéses build-up (CIC-Schemas `infra.py:170-192` minta). **PRESERVE**
   marad minden wasm-mező (`buildHash`, `cicSign`, `cicSignedCA`).

6. **`_resign_with_build_hash` belső átírása** (4. tétel, PRESERVE) — csak
   `to_canonical_json`/`get_sha256_hex` hivatkozás-forrás cseréje az 1.
   lépésben importált `schemalib.artifact`-ra; a metódus törzse és hívási
   helye (`_execute_finalization_phase`-ből) **nem** mozdul.

7. **`finalize_release.py:17-24` DEPRECATED komment frissítése** (5. tétel) —
   az új `_resign_with_build_hash` sortartományra.

8. **`tests/test_tools/test_infra_coverage.py:121,208`** —
   `mocker.patch("tools.infra.ReleaseManager._resign_with_build_hash")` —
   ha a 6. lépés megtartja a metódust (igen, PRESERVE), ez a mock
   változatlanul működik. Minden `tools.infra.load_and_resolve_schema`/
   `load_yaml`/`write_yaml`/`_parse_certificate_info` patch-pont
   (`test_infra_coverage.py:149,156,157,163,174,177,178,180,192,223,232`)
   **érvényes marad**, mert ezek a nevek importtal `tools.infra`
   névtérben is elérhetők lesznek.

9. **`project.schema.yaml` szinkronizálás** (7a/7b/8a/8b tételek) — a
   `compiler_settings` blokk additív mezőinek átvétele +
   `additionalProperties: false` megtartása (7b) + top-level
   `required`/`additionalProperties`/`abi:` megtartása (8a) + `metadata`
   9 extra mező megtartása (8b). **Csak a 2-8. lépés után** — a `repo_type`
   mező bevezetése `required`-be megköveteli a `project.yaml` 10. lépését.

10. **`base-repo/project.yaml`** `compiler_settings:` blokk — `repo_type: module`
    mező felvétele (7c tétel), hogy a 9. lépés `repo_type`-`required`-je
    ne bukjon el a `_validate_final_project_yaml` (PRESERVE-elt, 4. tétel)
    validáción.

11. **`tools/compiler.py`** — **NINCS módosítás szükséges** a 2. előre
    eldöntött korlát miatt (`validate` subcommand már `_validate_final_project_yaml`-on
    keresztül validál — illetve jelenleg `manager.run_validation()`-t hívja,
    amely a PRESERVE-elt, saját placeholder implementáció marad, 6. tétel
    SKIP miatt nincs `_require_repo_type`-gate). `set-build-hash` subcommand
    (`compiler.py:116-160`) **változatlan** marad (2.3, korábbi audit által
    megerősítve).

12. **Végső teszt-futtatás**: `python3 -m pytest tests/test_tools/ -q --no-cov`
    — 31/31 PASS elvárt (baseline, lásd fent). Ha Docker elérhető:
    `make check`/`make test`/`make validate`/`make wasm.build`/
    `make wasm.rebuild-verify`/`make verify-release` is ajánlott, de a
    sub-job time-boxon belül a pytest-suite zöld állapota a minimum
    elfogadási kritérium.

---

## Definition of Done — önellenőrzés

- [x] `base-repo` (`b7da285`) és `CIC-Schemas` (`2ec57c0`) induló állapot
  ellenőrizve, eltérés a korábbi riportokhoz képest dokumentálva
  (schemalib már transzferálva, `infra.py` még nem importálja)
- [x] Claim-evidence tábla mind a 8 tételre, file:line hivatkozásokkal
  (mindkét repóra)
- [x] Migrációs tábla ADOPT/PRESERVE/SKIP döntésekkel és indoklással
- [x] 2. és 3. pont futtatott bizonyítéka idézve (`/tmp/test_load_and_resolve_compare.py`,
  `/tmp/test_createdby_buildup_compare.py`)
- [x] Meglévő 31 teszt PASS baseline rögzítve (lokális venv)
- [x] 6. pont reachability grep — 0 találat, SKIP megerősítve
- [x] Sorrendezett lépéslista a következő sub-jobnak
- [ ] Riport a `feature/wasm-infra-migration-plan`-on pusholva (következő lépés)
