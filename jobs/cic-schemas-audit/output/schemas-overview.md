# CIC-Schemas repó — teljes áttekintés

Elemzett repó: `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Schemas`
Elemzés időpontja: 2026-06-08

---

## Branch modell

A repó `<service>/<version>/<stage>` hierarchiát alkalmaz:

| Branch minta | Jelentés |
|---|---|
| `main` | Repo-szintű alap — sablonok, tooling, meta-sémák |
| `postgresql/vN/dev` | Adott PostgreSQL verzió fejlesztési ága |
| `postgresql/vN/main` | Adott PostgreSQL verzió stabil/release ága |

Jelenleg létező service/version kombinációk (origin remote):
- `postgresql/v14/main`, `postgresql/v14/dev`
- `postgresql/v15/main`, `postgresql/v15/dev`
- `postgresql/v16/main`, `postgresql/v16/dev`
- `postgresql/v17/main`, `postgresql/v17/dev`
- `postgresql/v18/main`, `postgresql/v18/dev`

`base` remote — megosztott alap template branch-ek:
- `base/main`, `base/devel`, `base/docs/main`, `base/schemas/main`, `base/schemas/devel`, `base/golang/main`, `base/golang/devel`, `base/mcp/devel`, `base/workflows/main`
- `base/IaC/devel` — Infrastructure as Code ág
- `base/d/feature-001`, `base/d/feature-002`, `base/d/feature-006` — feature ágak
- `base/fix/createdby-signing` — fix ág

`origin/CICmeta/devel` — meta-szintű fejlesztési ág.

**Release ciklus:**
1. `postgresql/vN/dev` → fejlesztés
2. `make release-schema VERSION=vX.Y.Z_YEAR` → automatikusan létrehozza és törli a `postgresql/releases/vX.Y.Z_YEAR` branch-et, git tag: `postgresql@vX.Y.Z_YEAR`
3. `git push origin postgresql@vX.Y.Z_YEAR` → publikus

Ismert tagek: `postgresql@v0.14.0_2025` … `postgresql@v0.18.0_2025`, `base@0.5.0`, `schemas@v0.9.0`, `template-schema@v0.9.5_2025`

---

## Könyvtár struktúra

```
CIC-Schemas/
├── schemas/
│   └── index.yaml           ← Kanonikus forrás-séma (main belépési pont)
├── source/                  ← JSON Schema fragmentumok ($ref target-ek)
│   ├── postgresql.conf.yaml
│   ├── pg_hba.conf.yaml
│   ├── pg_ident.conf.yaml
│   ├── postgresql.auto.conf.yaml
│   └── parameters.yaml
├── release/                 ← Aláírt release artifactok
│   └── postgresql-v0.18.0_2025.yaml
├── dependencies/            ← Meta-sémák (validátorok) — aláírt
│   └── template-schema-v0.9.5_2025.yaml
├── tools/                   ← Build tooling
│   ├── compiler.py          ← Python build/sign/release logika
│   ├── release.sh           ← Shell wrapper a teljes release folyamathoz
│   ├── vault-sign-agent.sh  ← Lokális Vault dev szerver indítása
│   ├── git_hook_commit-msg.sh ← Commit-msg Vault signing hook
│   ├── init_from_template.sh
│   ├── init-hooks.sh
│   ├── postgres_settings.py
│   ├── releaselib/          ← Python release lib
│   └── schemalib/           ← Python schema lib
├── features/                ← Feature spec dokumentumok
│   ├── feature-001/spec.md
│   └── feature-002/
├── configs/                 ← Runtime/Docker konfigok
├── docs/                    ← Dokumentáció (en/, hu/ alkönyvtárak)
├── dependency.yaml          ← Runtime függőség (postgres: 18.1-alpine3.22)
├── docker-compose.yml       ← Dev build environment
├── Dockerfile               ← Builder image
├── Makefile                 ← Build automatizálás
└── md.meta.schema.yaml      ← Markdown fájlok KB metaadat sémája (AI/graph)
```

**Fontos:** A `source/` fájlok tiszta JSON Schema fragmentumok — nincs `metadata` wrapper-ük. Ezeket a `schemas/index.yaml` hivatkozza `$ref`-ekkel.

---

## Séma formátum

**Formátum:** YAML (két blokkos struktúra)

### Két blokk:

**`metadata`** — kötelező minden verzióban:
- `name` — séma neve (pl. `postgresql`)
- `version` — szemantikus verzió, mintázat: `vMAJOR.MINOR.PATCH_YEAR` vagy `vMAJOR.MINOR.dev`
- `description` — rövid leírás
- `owner` — felelős (pl. `Gabor Zoltan Sinko`)
- `tags` — kategóriacímkék listája
- `validatedBy` — melyik meta-séma validálta (name + version + checksum)

**Release-only metadata mezők** (dev verzióban nem lehet jelen):
- `createdBy` — aláíró személyazonossága (name, email, certificate PEM, issuer_certificate PEM)
- `build_timestamp` — ISO8601 UTC
- `validity` — from/until dátumok (support lifecycle)
- `checksum` — SHA256 hex a `spec` blokk kanonikus JSON tartalmáról
- `sign` — Vault transit aláírás (format: `vault:v1:<base64>`)

**`spec`** — maga a JSON Schema definíció (JSON Schema draft szabvány, YAML szintaxissal)

### Verzióminták:
- Dev: `v0.18.dev` — nem ereszthető release-re
- Release: `v0.18.0_2025` — production artifact

### `$ref` referenciák:
A `schemas/index.yaml` `$ref`-ekkel hivatkozza a `source/` fájlokat:
```yaml
spec:
  properties:
    postgresql_conf:
      $ref: '../source/postgresql.conf.yaml'
    pg_hba_conf:
      $ref: '../source/pg_hba.conf.yaml'
```
A compiler `load_and_resolve_schema()` ezeket build időben feloldja — a release artifactban már inlined, feloldott forma van.

### Meta-séma önhivatkozás (bootstrap):
A `template-schema` önmagát validálja (`validatedBy.name == metadata.name`). Ez a trust gyökere — a compiler felismeri és nem keres külső validátort.

---

## Build → Sign → Publish pipeline

### Make célok sorrendben:

| Lépés | Parancs | Leírás |
|---|---|---|
| 1. | `make infra.deps` | Python deps telepítése p_venv-be |
| 2. | `make up` | Docker dev konténer indítása |
| 3. | `make validate` | Forrás-séma validálása (nincs aláírás) |
| 4. | `make test` | Python compiler unit tesztek |
| 5. | `make check` | fmt + lint + typecheck (Black, Ruff, MyPy, yamllint) |
| 6. | `make release-schema VERSION=vX.Y.Z_YEAR` | Teljes release folyamat |

### `release-schema` belső lépései (`tools/release.sh`):
1. Git working directory clean ellenőrzés
2. Pre-release validate futtatás (`compiler.py validate`)
3. Schema name kiolvasása (`compiler.py get-name`)
4. `<name>/releases/<VERSION>` branch létrehozása
5. `compiler.py release-schema --source schemas/index.yaml --version <VERSION>`:
   - Validálás a deklarált meta-sémával
   - Spec SHA256 checksum kiszámítás
   - Vault aláírás kérés
   - Tanúsítvány lekérés Vault KV-ból
   - Artifact összeállítás és végső validálás
   - Írás: `release/<name>-<version>.yaml`
6. `git add` → `git commit --no-verify` (hook skip, a hook maga aláír, circular lenne)
7. `git tag -a <name>@<version>`
8. Vissza az eredeti branch-re → release branch törlése
9. Manuális: `git push origin <name>@<version>`

---

## Signing mechanizmus

**Két szintű aláírás:**

### 1. Release artifact aláírás (compiler.py)
- **Kulcs:** `cic-my-sign-key` (Vault transit engine, ECDSA P-256)
- **Folyamat:**
  1. `spec` blokk → kanonikus JSON (sorted keys) → SHA256 hex → ez lesz a `checksum`
  2. Metadata blokk összeállítása (checksum hozzáadva, sign/checksum kizárva, build_timestamp beírva)
  3. Metadata SHA256 → base64 → küldés Vault transit `/v1/transit/sign/cic-my-sign-key`-re (`prehashed: true`)
  4. Vault visszaad: `vault:v1:<base64_signature>`
  5. Tanúsítvány lekérés KV-ból: `/<KEY_NAME>/data/crt` és `/<KEY_NAME>/data/CICRootCA`
  6. OpenSSL parse → CN és email kinyerése
  7. Final artifact: `checksum` + `sign` + `build_timestamp` + `createdBy` beírva
  8. Végső validálás az `index.yaml` meta-meta-sémával

### 2. Git commit-msg aláírás (hook)
- **Kulcs:** ugyanaz (`cic-my-sign-key`)
- **Folyamat:**
  1. Staged tartalom → determinisztikus tar archive (sorted, fixed mtime/owner)
  2. tar | SHA256 | base64 → ez a `digest`
  3. Vault transit sign call (ugyanolyan mint release)
  4. Tanúsítvány lekérés KV-ból
  5. Commit message végéhez fűzés:
     ```
     ---
     [signing-metadata]
     key = cic-my-sign-key
     signature = vault:v1:...
     hash-algorithm = sha256
     digest = <base64>
     
     [certificate]
     <PEM>
     ```

### Vault infrastruktúra (`vault-sign-agent.sh`):
- Lokális HashiCorp Vault dev szerver (HTTPS, self-signed cert, 127.0.0.1:18200)
- Transit secrets engine engedélyezve
- Kulcs importálás: `openssl pkey` → `vault transit import`
- KV v2 mount a `cic-my-sign-key` path alatt (certificate store)
- Sign policy: csak `transit/sign/cic-my-sign-key` engedélyezett
- Token file: `$XDG_RUNTIME_DIR/vault/sign-token`

**Státusz:** Az aláírás **implemented** — a compiler.py, release.sh és vault-sign-agent.sh kész, futtatható. Vault elérhetőség build-time követelmény.

---

## OCI publikálás

**Nincs OCI publikálás.**

A `ghcr.io`, `docker push`, `oci`, `registry` kulcsszavakra végzett keresés csak Docker Compose build environment referenciákat adott vissza — registry push nem található.

**A terjesztés kizárólag git-alapú:**
- Release artifact: `release/<name>-<version>.yaml` commitolva git-be
- Terjesztés: `git push origin <name>@<version>` (annotated tag push)
- Fogyasztó rendszerek a git repóból olvassák a release artifactot

**Docker szerepe:** csak a build environment izolálása (builder konténer) — nem az artifact terjesztésének csatornája.

---

## PostgreSQL séma példa

**Vizsgált állapot:** `postgresql@v0.18.0_2025` (tag, `release/postgresql-v0.18.0_2025.yaml`)

### Forrás struktúra (schemas/index.yaml):
```yaml
metadata:
  name: postgresql
  version: v0.18.dev
  description: "..."
  owner: Gabor Zoltan Sinko
  tags: [template, meta-schema]
  validatedBy:
    name: template-schema
    version: v0.9.5_2025
  validity:
    from: "2025-11-12T00:00:00Z"
    until: "2026-11-12T00:00:00Z"

spec:
  type: object
  required: [metadata, spec]
  properties:
    metadata:
      # ... részletes metadata JSON Schema
    spec:
      properties:
        postgresql_conf:
          $ref: '../source/postgresql.conf.yaml'
        pg_hba_conf:
          $ref: '../source/pg_hba.conf.yaml'
        pg_ident_conf:
          $ref: '../source/pg_ident.conf.yaml'
        postgresql_auto_conf:
          $ref: '../source/postgresql.auto.conf.yaml'
```

### Source fájl struktúra (pl. source/postgresql.conf.yaml):
Tiszta JSON Schema fragment, metadata wrapper nélkül:
```yaml
type: object
description: "Schema for PostgreSQL configuration settings..."
properties:
  connection:
    type: object
    properties:
      max_connections:
        type: integer
        description: "Sets the maximum number of concurrent connections."
        default: 100
        minimum: 1
        maximum: 262143
      port:
        type: integer
        description: "Sets the TCP port the server listens on."
        default: 5432
        minimum: 1
        maximum: 65535
      listen_addresses:
        type: string
        description: "Sets the host name or IP address(es) to listen to."
        default: '*'
  authentication:
    # ... postgresql auth beállítások
```

### Release artifact (release/postgresql-v0.18.0_2025.yaml):
```yaml
metadata:
  name: postgresql
  version: v0.18.0_2025
  validatedBy:
    name: template-schema
    version: v0.9.5_2025
    checksum: 31d6ad98eb3da9a...   ← meta-séma spec SHA256
  checksum: 1151b3af0c28424...     ← spec blokk SHA256
  sign: vault:v1:MEUCIGrk9l...    ← Vault ECDSA aláírás
  build_timestamp: '2025-11-18T16:29:10.278890+00:00'
  createdBy:
    name: Gabor Zoltan Sinko
    email: sgz@centralinfracore.hu
    certificate: "Certificate:\n  Data:\n  ..." + PEM
    issuer_certificate: "-----BEGIN CERTIFICATE-----\n..."
spec:
  type: object
  # ... feloldott (inlined) full spec, $ref-ek nélkül
```

**Megjegyzés:** A release artifactban a `spec` blokk teljesen feloldott — az összes `$ref` be van inline-olva. Ez az a tartalom, amelynek SHA256-ja a `checksum` mező.

---

## Release artifact tartalma

Egy release artifact a következőket tartalmazza:
1. **Teljes metadata** — beleértve createdBy tanúsítványláncot (leaf + root CA)
2. **Aláírás** — Vault transit ECDSA P-256 (`vault:v1:` prefix)
3. **Checksum** — a spec blokk SHA256 hexje
4. **validatedBy.checksum** — a validátor meta-séma spec SHA256-ja (tamper detection)
5. **Feloldott spec** — összes `$ref` inline-olva, olvasható JSON Schema

**Integrációs bizonyítékok:**
- A fogyasztó ellenőrizheti: spec checksum újraszámítható → tamper detection
- A fogyasztó ellenőrizheti: aláírás verifikálható a createdBy certificate-tel
- A tanúsítványlánc: leaf certificate → `CIC Root CA`

---

## PoC relevanciák

| Témakör | Mit jelent a PoC-nak |
|---|---|
| **Branch = service verzió** | A `postgresql/v18/main` branch adja a context-et — ugyanaz a repóban több service jövőre `postgresql/v18/...` + `redis/v7/...` mintával fut |
| **`validatedBy` lánc** | A PoC-ban a relay-nek tudnia kell melyik meta-sémával validált a séma — ez a bizalom alapja |
| **Nincs OCI** | A relay nem OCI registry-ből húzza a sémákat — git repository pull vagy local path a forrás |
| **Vault dependency** | A signing Vault elérhetőséget igényel — PoC-ban ez lehet mock vagy dev Vault |
| **`checksum` + `sign` dupla védelem** | A spec tamper detectable (checksum), az egész artifact identity-kötött (sign) — relay verifikálhat |
| **Meta-séma önvalidáció** | A trust root a meta-séma; bootstrapping nem igényel külső validator-t |
| **`dependency.yaml`** | A runtime függőség (postgres image verzió) a séma verziójától független — a relay ezeket összekötő kapocs |
| **Release tag = canonical ID** | A `postgresql@v0.18.0_2025` tag az egyértelmű azonosítója a sémának — erre lehet hivatkozni relay-side |
