# PoC séma design — döntési dokumentum

Elemzett forrásokból levezetett döntések.
Elemzett fájlok: `cic-schemas-audit/output/schemas-overview.md`, `primitives/release/cic-primitives-v0.1.5.yaml`

---

## Séma struktúra döntések

### Formátum

A `cic-relay-config` séma pontosan követi a CIC-Schemas kétblokkos struktúráját:
- `metadata` blokk: azonosítás, aláírás, validátor referencia
- `spec` blokk: feloldott JSON Schema (nincs `$ref`)
- `cic_countersign` blokk: CICSourceCA ellenjegyzés (a primitives mintájára)

**Eltérés a CIC-Schemas postgresql sémától:** A CIC-Schemas sémákban `createdBy.certificate` szöveg + PEM formátum (`Certificate:\n  Data:\n  ...` prefix). A relay-config PoC esetén a `createdBy.certificate` csak PEM formátumot tartalmaz — a szöveg prefix elhagyható, mert:
1. A relay verifier PEM-t vár (`pki_verify.go` — `x509.CertPool`)
2. A compiler szöveg-formátuma display-only, nem verifikációs követelmény
3. A primitives `release.createdBy.certificate` is PEM formátumot használ

### `metadata` mezők PoC-hoz

| Mező | Érték | Indok |
|---|---|---|
| `name` | `cic-relay-config` | Relay saját konfigurációjának sémája |
| `version` | `v0.1.0_poc` | PoC jelzés, nem production release |
| `validatedBy.name` | `template-schema` | Megegyezik a CIC-Schemas template validátorral |
| `validatedBy.version` | `v0.9.5_2025` | Legutolsó ismert stable verzió |
| `validatedBy.checksum` | placeholder | Valódi checksum a template-schema release artifactból |
| `checksum` | placeholder | `spec` blokk kanonikus JSON SHA256 hexje |
| `sign` | `vault:v1:<base64>` placeholder | Vault transit ECDSA P-256 aláírás, `metadata_sha256` felett |
| `build_timestamp` | ISO8601 UTC | Build ideje |
| `createdBy` | Gabor Zoltan Sinko adatai | CIC-Schemas és primitives azonos person |

---

## `cic_countersign` integráció

### Valós struktúra (primitives v0.1.5 alapján)

A job spec `cic_countersign` leírása **nem teljes** — a valódi struktúra `authority` wrappert tartalmaz:

```yaml
cic_countersign:
  authority:
    name: CIC Source CA
    certificate: |          # PEM formátum, NEM "Certificate: Data:" text prefix
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
    root_certificate: |     # Root CA PEM
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
  signed_payload: build_hash   # mi lett ténylegesen aláírva (pointer, nem érték)
  sign: vault:v1:<base64>      # CICSourceCA privátkulcs aláírása
```

A PoC artifactban pontosan ezt a struktúrát használjuk — `authority` wrapper kötelező.

### `certificate` formátum döntés

**PEM formátum** — nem text prefix.

Indok:
1. A primitives v0.1.5 `cic_countersign.authority.certificate` PEM formátumot használ
2. A `release.createdBy.certificate` primitives-ban szintén PEM
3. A relay `pki_verify.go` `x509.CertPool` API-t hív, ami PEM-et vár
4. A text prefix (`Certificate:\n  Data:\n  ...`) csak a CIC-Schemas `createdBy.certificate` display convention — verifikációs kódba nem megy be

### `signed_payload` döntés — `metadata_sha256`

**Döntés:** `cic_countersign.signed_payload = "metadata_sha256"`

A primitives `"build_hash"`-t ír alá — ami az egész release tartalmának hash-e.
A CIC-Schemas modellben a `metadata.sign` a **metadata blokk SHA256**-át írja alá (a metadata SHA256-ját, amely tartalmazza a spec checksum-ot is).

A PoC-ban a `cic_countersign.sign` ugyanezt a `metadata_sha256` értéket írja alá, mert:

1. **Relay-oldalon már rendelkezésre áll:** a `metadata.sign` verifikálásakor a relay újraszámolja a `metadata_sha256`-ot — nincs szükség extra hash számításra a countersign ellenőrzésnél
2. **Teljes artifact coverage:** a `metadata_sha256` magában foglalja a `metadata.checksum`-ot (spec SHA256), tehát transitív módon fedezi a spec tartalmát is
3. **Két-fél attestáció azonos digest felett:** a Vault kulcs (`cic-my-sign-key`) + CICSourceCA CA egymástól független kulcsokkal, ugyanazon `metadata_sha256` felett írnak alá — ez erősebb mint két különböző digest
4. **Chain:** `spec content → checksum → metadata_sha256 → sign (Vault) + cic_countersign (CA)`

**Alternatíva amit elvettük:** `"checksum"` (csak a spec hash) — elvettük, mert a countersign akkor csak a spec-et fedné, a metadata-t (verziót, validatedBy-t) nem.

---

## Relay verifikációs sorrend

### Verifikáció lépései sorrendben

1. **`checksum` ellenőrzés** *(PoC minimum — implemented)*
   - `spec` blokk → kanonikus JSON (sorted keys, no whitespace) → SHA256 hex
   - Összehasonlítás `metadata.checksum`-mal
   - Megvéd: spec tartalom módosítás ellen

2. **`sign` ellenőrzés** *(scaffold — Vault dependency)*
   - Metadata blokk (checksum nélkül, sign nélkül) → SHA256 → base64 → `metadata_sha256`
   - Vault `/v1/transit/verify/cic-my-sign-key` hívás (`prehashed: true`)
   - Megvéd: metadata módosítás, forged checksum ellen

3. **`cic_countersign` ellenőrzés** *(scaffold — CA trust setup)*
   - `cic_countersign.authority.certificate` → PEM parse → public key kinyerés
   - `metadata_sha256` (azonos a 2. lépésből) → ECDSA verify a kinyert public key-jel
   - `cic_countersign.authority.root_certificate` → CA chain verify
   - Megvéd: csomagcsere ellen (source attestation)

### PoC minimum vs scaffold

| Lépés | PoC státusz | Indok |
|---|---|---|
| checksum verify | **PoC minimum — implementálandó** | Vault-independens, tisztán Go crypto/sha256, nincs külső függőség |
| sign verify (Vault) | **scaffold** | Vault dev szerver elérhetőség szükséges; PoC első körben elhagyható |
| cic_countersign CA verify | **scaffold** | CA trust store setup szükséges; Go `x509.CertPool` + ECDSA verify — második lépés |

**Indok:** A checksum verify már önmagában tamper-detectable védelmet ad a spec ellen. A sign + countersign a source identity-t adja hozzá — ez a PoC demójához opcionális, de az éles rendszerhez kötelező.

---

## `poc/v1` branch terv

### Branch struktúra a CIC-Schemas repóban

```
poc/v1/
  schemas/
    index.yaml                    ← séma forrás (nem feloldott, $ref-ekkel)
  source/
    relay-config.yaml             ← JSON Schema fragment (a spec tartalma)
  release/
    cic-relay-config-v0.1.0_poc.yaml  ← signed release artifact (placeholder aláírásokkal)
  dependencies/
    template-schema-v0.9.5_2025.yaml  ← copy/symlink a base/main-ről
  tools/                          ← symlink a base branch tools/-jára
  Makefile                        ← symlink a base branch Makefile-jára
  dependency.yaml                 ← (opcionális, relay verziót tartalmazhat)
```

### Tools kezelés

**Döntés:** A `tools/` és `Makefile` a base branch-ről **symlink** — nem másolat.

Indok:
1. A CIC-Schemas base branch tartalmazza a compiler.py, release.sh, vault-sign-agent.sh-t
2. Másolat maintainability problémát okozna (divergens tool verzió)
3. A `poc/v1` branch cherry-pick-kel tartható szinkronban a base-szel

### Létrehozandó fájlok (új tartalom)

- `schemas/index.yaml` — relay-config séma forrás
- `source/relay-config.yaml` — JSON Schema fragment
- `release/cic-relay-config-v0.1.0_poc.yaml` — ez a dokumentum `poc-schema-example.yaml` outputja

---

## Nyitott kérdések

| Kérdés | Blokkoló? | Megjegyzés |
|---|---|---|
| Mi a `validatedBy.checksum` pontos értéke? | Nem — placeholder elegendő a PoC-hoz | A `template-schema-v0.9.5_2025.yaml` spec SHA256-ja kell; CIC-Schemas repóból kiolvasható |
| A PoC Vault dev szerver elérhető-e a relay teszthez? | Scaffold-hoz igen | `vault-sign-agent.sh` indítással megoldható; PoC minimum (checksum) Vault nélkül fut |
| CA-countersign Go-side interface: `pki_verify.go` bővítendő-e? | Scaffold döntés | A meglévő `VerifyOptions + x509.CertPool` alap megvan; countersign-specifikus wrapper hiányzik |
| `poc/v1` branch mikor kerül origin-re? | Orchestrátor döntés | Az agent a tervdokumentumot és a minta artifactot adja — a branch creation az orchestrátor feladata |
