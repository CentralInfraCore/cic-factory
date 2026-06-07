# CIC_Schemas — Részletes Feltárás

**Dátum:** 2026-06-06
**Lokális elérési út:** `${CIC_SCHEMAS_PATH}`
**Remote URL:** `git@github.com:CentralInfraCore/CIC_Schemas.git`
**Aktív branch:** detached HEAD (commit: `27925c5` — `fix: adapt project.yaml for CIC-Schemas (repo_type=schema, template-schema)`)
**Párhuzamos worktree-k:** `schemas/postgresql` és `schemas/template` ugyanerről a remote-ról (különböző branch-ek)

---

## Státusz

**Aktív fejlesztés.** Az utolsó commit egy `base-repo` remote-merge-t követ: a CIC_Schemas beolvasztotta a base repo séma sablonjait, majd adaptálta a `project.yaml`-t. A `postgresql` és `template` worktree-k ugyanennek a repónak eltérő branch-ei.

---

## Könyvtárstruktúra (3 szint)

```
CIC-Schemas/
  configs/
    schemas/              — meta-schema konfigok (.gitkeep, üres — séma artifact-ok runtime kerülnek ide)
  docs/
    en/
      architecture.md    — angol architektúra leírás
      compiler-architecture-plan.md  — részletes compiler terv
      workflow.md        — fejlesztői munkafolyamat
      makefile-cheatsheet.md
      concept/           — fogalmi dokumentáció
    hu/
      architecture.md    — magyar architektúra leírás
      compiler-architektura-terv.md
      workflow.md
      makefile-cheatsheet.md
      concept/
  features/
    feature-001/spec.md  — feature spec
    feature-002/spec.md  — feature spec
  mk/
    infra.mk             — Makefile fragmentek (shared infrastruktúra target-ek)
  schemas/
    index.yaml           — schema index
  source/
    .gitkeep             — forrás sémák helye (runtime kerülnek ide)
  tests/
    compiler/            — compiler tesztek
    infra/               — infra tesztek
    test_compiler.py     — compiler unit tesztek
    test_tools/
      test_compiler.py
      test_finalize_release.py
      test_infra_coverage.py
      test_infra.py
      test_releaselib/
      test_schemalib_artifact.py
      test_schemalib_loader.py
      test_schemalib_validator.py
  tools/
    compiler.py          — fő CLI entry point (release workflow orchestrátor)
    finalize_release.py  — release finalizálás
    infra.py             — ReleaseManager
    go.meta.gen.py       — Go .meta.yaml companion fájl generátor
    init_from_template.sh
    init-hooks.sh        — git hook telepítő
    git_hook_commit-msg.sh
    release.sh
    vault-sign-agent.sh  — lokális Vault dev szerver indítása (signing)
    vault-rootCA-sign-agent.sh
    schemalib/
      artifact.py        — checksum számítás, artifact összerakás
      loader.py          — YAML séma betöltés + $ref feloldás (jsonref)
      validator.py       — jsonschema validáció + validator integrity ellenőrzés
    releaselib/
      vault_service.py   — Vault Transit signing + KV secret lekérés (HTTP REST)
      git_service.py     — git műveletek (commit, tag, push)
      exceptions.py      — ReleaseError, VaultServiceError, ConfigurationError, ManualInterventionRequired
  go.meta.schema.yaml    — Go fájl companion metadata séma
  md.meta.schema.yaml    — Markdown companion metadata séma
  Makefile               — build/test/release target-ek
  Dockerfile             — Python toolchain container
  docker-compose.yml     — fejlesztői Docker környezet
  project.yaml           — repo metaadat + Vault signing adat (kriptográfiailag aláírt)
  project.schema.yaml    — project.yaml validátor séma
  pyproject.toml         — Python projekt konfig
  pytest.ini
  requirements.in        — Python direct dependencies
  requirements.txt       — pin-elt Python függőségek (pip-compile, Python 3.11)
  renovate.json          — dependency bot konfig
  MANIFEST.sha256        — fájl checksum manifest
  README.md
  README.hu.md
  feature-list.md
  .github/workflows/
    ci.yml               — CI pipeline
  .editorconfig
  .yamllint
  .gitignore
```

---

## Entry Point — `tools/compiler.py`

A `tools/compiler.py` a fő CLI. Betölti a `project.yaml`-t, majd a `compiler_settings` szekció alapján routing-ol:

```python
from .infra import ReleaseManager
from .releaselib.git_service import GitService
from .releaselib.vault_service import VaultService
```

**Fő funkcionalitás:**
- `validate` — séma validáció (schemalib.validator.run_validation)
- `release` — teljes release workflow (validate → sign → git commit/tag → push)
- `release-dependency` — függőség séma release
- `init` — repo inicializálás sablonból

---

## Szoftver architektúra

### Rétegek

```
compiler.py (CLI)
  └── infra.py (ReleaseManager)
        ├── schemalib/loader.py    — YAML betöltés + $ref feloldás (jsonref)
        ├── schemalib/validator.py — jsonschema validáció + integrity check
        ├── schemalib/artifact.py  — artifact összerakás, checksum (SHA256)
        ├── releaselib/vault_service.py — Vault Transit signing (HTTP)
        └── releaselib/git_service.py  — git commit/tag/push
```

### Validator integrity mechanizmus

A `validator.py` tartalmaz egy kritikus biztonsági ellenőrzést:
- Minden validator séma tartalmaz `metadata.checksum = SHA256(canonical_json(spec))` mezőt
- Betöltés előtt: `verify_validator_integrity()` ellenőrzi a checksumot
- Ha eltér: `ValidationFailureError` — egy módosított validator csendesen elfogadhat érvénytelen sémákat
- Self-validation (bootstrap) esetén: a séma saját magát validálja

### Vault signing folyamat

```
1. Séma YAML betöltés + $ref feloldás
2. SHA256(canonical_json(spec)) → checksum mező
3. Vault Transit sign (prehashed SHA256, base64 encoded)
   → signature: "vault:v1:..." formátum
4. project.yaml frissítés (sign, buildHash, cicSign mezők)
5. git commit + tag + push
```

A `VaultService` HTTP REST-en kommunikál a Vault-tal (`/v1/transit/sign/<key_name>`). A privát kulcs soha nem kerül ki a Vault-ból — csak a signature.

---

## Függőségek (`requirements.txt`, Python 3.11)

```
Fő közvetlen függőségek (requirements.in alapján):
  jsonschema==4.25.1      — JSON Schema validáció
  jsonref==1.1.0          — $ref feloldás YAML sémákban
  cryptography==46.0.2    — kriptográfiai műveletek
  pyopenssl==25.3.0       — TLS cert kezelés
  requests==2.32.5        — Vault HTTP API
  pyyaml==6.0.3           — YAML parsing
  semver==3.0.4           — szemantikus verziókezelés

Fejlesztői eszközök:
  pytest==8.4.2 + pytest-cov + pytest-mock
  black==25.11.0          — kódformázás
  mypy==1.18.2            — típusellenőrzés
  ruff==0.14.4            — linter
  isort==7.0.0            — import rendezés
  bandit==1.9.2           — biztonsági analízis
  yamllint==1.37.1        — YAML lint
```

---

## CI/CD (`.github/workflows/ci.yml`)

Push/PR-re `main` és `master` branch-ekre:
1. Docker image build (`make build`)
2. `requirements.txt` drift check (`make infra.deps && git diff --exit-code`)
3. Code quality (`make check`): black, mypy, ruff, isort, bandit, yamllint
4. Tesztek + coverage (`make test`)
5. HTML coverage report artifact feltöltés

---

## project.yaml — Aláírt Metaadat

A `project.yaml` nem egyszerű konfig — tartalmaz:
- `metadata.checksum` — build artifact checksum
- `metadata.sign` — Vault Transit signature (`vault:v1:...`)
- `metadata.buildHash` — build hash Vault signature
- `metadata.cicSign` — CIC-specifikus aláírás
- `metadata.cicSignedCA` — aláíró CA tanúsítvány (CIC Root CA, ECDSA P-256)
- `metadata.createdBy.certificate` — creator X.509 cert (Gabor Zoltan Sinko, sgz@centralinfracore.hu)
- `compiler_settings` — a compiler konfigurációja (Vault mount, key name, meta schema paths)

Ez a struktúra igazolja, hogy a CIC_Schemas repo maga is a saját release pipeline-ján megy át.

---

## Worktree-k

| Worktree | Branch | Path | Tartalom |
|---|---|---|---|
| CIC-Schemas (main) | HEAD detached at 27925c5 | `CIC-Schemas/` | Template branch séma infrastruktúra |
| schemas/postgresql | postgresql | `schemas/postgresql/` | PostgreSQL schema definíció + signed release |
| schemas/template | template | `schemas/template/` | Meta-schema sablon, minden séma artifact alap |

---

## CIC Kapcsolódások

- **CIC-Relay**: a Relay betölti a CIC_Schemas által előállított és aláírt séma YAML-okat. A `cabinet.ValidateSchema()` az aláírás és schema ID alapján fogadja el.
- **cic-primitives**: a schema tooling (compiler.py) elvben feldolgozza a cic-primitives alapú sémákat is — de a közvetlen import nem azonosítható.
- **base-repo**: a CI workflow, Makefile struktúra, mk/infra.mk és a tool réteg sablonja `remote-merge`-gel kerül ide.
- **cic-mcp-private**: a KB tartalmaz CIC_Schemas fogalmakat; az MCP szerver expozálja a signing workflow dokumentációját.
