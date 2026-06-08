# Relay integráció terv — séma verifikáció

---

## Meglévő relay infrastruktúra

| Fájl | Szerepe |
|---|---|
| `cmd/relay/pipeline_handler.go` | POST /v1/proof — Wasm aktiváció |
| `cmd/relay/proof_verify_handler.go` | POST /v1/proof/verify — proof artifact verifikáció |
| `cmd/relay/proof_verify.go` | `VerifyProofArtifact()` — chain_hash recompute, lépés ellenőrzés |
| `core/cabinet/schema.go` | `NewSchema()` — séma létrehozás és checksum számítás |
| `core/cabinet/schema_validate.go` | `ValidateSchema()` — `$schema` key ellenőrzés |
| `core/cabinet/pki_verify.go` | `VerifyOptions`, `x509.CertPool` — CA chain verify infrastruktúra |
| `core/cabinet/checksum_seam.go` | Checksum számítás belépési pontja |

A relay jelenleg **nem** végez séma betöltést git-ből, sem `checksum`/`sign`/`cic_countersign` ellenőrzést — ezek hiányzó hidak.

---

## Schema betöltés — git alapú

### Betöltési folyamat

```
CIC-Schemas repo (git)
  → git pull / local path olvasás
  → release/<name>-<version>.yaml beolvasás
  → YAML parse → SchemaArtifact struct
  → verifikáció (ld. alább)
  → cabinet.NewSchema() → Cabinet-be regisztrálás
```

### Célzott Go fájl (új)

**`cmd/relay/schema_loader.go`**

```go
package main

// SchemaArtifact a CIC-Schemas release artifact YAML struktúrája.
type SchemaArtifact struct {
    Metadata     SchemaMetadata     `yaml:"metadata"`
    Spec         map[string]any     `yaml:"spec"`
    CICCountersign *CICCountersign  `yaml:"cic_countersign,omitempty"`
}

type SchemaMetadata struct {
    Name           string           `yaml:"name"`
    Version        string           `yaml:"version"`
    ValidatedBy    ValidatedBy      `yaml:"validatedBy"`
    Checksum       string           `yaml:"checksum"`
    Sign           string           `yaml:"sign"`
    BuildTimestamp string           `yaml:"build_timestamp"`
    CreatedBy      CreatedBy        `yaml:"createdBy"`
}

type ValidatedBy struct {
    Name     string `yaml:"name"`
    Version  string `yaml:"version"`
    Checksum string `yaml:"checksum"`
}

type CreatedBy struct {
    Name               string `yaml:"name"`
    Email              string `yaml:"email"`
    Certificate        string `yaml:"certificate"`
    IssuerCertificate  string `yaml:"issuer_certificate"`
}

type CICCountersign struct {
    Authority    CICAuthority `yaml:"authority"`
    SignedPayload string      `yaml:"signed_payload"`
    Sign         string       `yaml:"sign"`
}

type CICAuthority struct {
    Name            string `yaml:"name"`
    Certificate     string `yaml:"certificate"`
    RootCertificate string `yaml:"root_certificate"`
}

// LoadSchemaArtifact beolvas egy release artifact YAML fájlt a megadott path-ról.
func LoadSchemaArtifact(path string) (*SchemaArtifact, error)

// SchemaArtifactVerifier interface — a verifikáció lépéseit definiálja.
type SchemaArtifactVerifier interface {
    VerifyChecksum(artifact *SchemaArtifact) error         // PoC minimum
    VerifySign(artifact *SchemaArtifact) error             // scaffold: Vault dependency
    VerifyCountersign(artifact *SchemaArtifact) error      // scaffold: CA trust setup
}
```

---

## Verifikáció sorrendben

### 1. Checksum verify — PoC minimum, implementálandó

**Hol:** `cmd/relay/schema_loader.go` → `VerifyChecksum()`

```
artifact.Spec → canonical JSON (encoding/json, sorted keys) → SHA256 hex
== artifact.Metadata.Checksum ?
```

**Go csomag:** `crypto/sha256`, `encoding/json`  
**Vault dependency:** nincs  
**Státusz:** PoC-hoz implementálandó

### 2. Sign verify — scaffold

**Hol:** `cmd/relay/schema_loader.go` → `VerifySign()` + `cmd/relay/pki_bootstrap.go` Vault client

```
metadata blokk (Checksum, Sign kizárva) → canonical JSON → SHA256 → base64 → metadata_sha256
Vault POST /v1/transit/verify/cic-my-sign-key body:
  {"input": "<metadata_sha256>", "signature": "<artifact.Metadata.Sign>", "prehashed": true}
```

**Vault kulcs:** `cic-my-sign-key` (ECDSA P-256)  
**Meglévő Vault client:** `pki_bootstrap.go` — vizsgálandó, hogy tartalmaz-e transit verify hívást  
**Státusz:** scaffold — Vault dev szerver elérhetőség szükséges

### 3. CICCountersign verify — scaffold

**Hol:** `cmd/relay/schema_loader.go` → `VerifyCountersign()` + `core/cabinet/pki_verify.go` bővítés

```
artifact.CICCountersign.Authority.Certificate → PEM parse → x509.Certificate → ECDSA public key
metadata_sha256 (ugyanaz mint a 2. lépésből) → ECDSA verify
artifact.CICCountersign.Authority.RootCertificate → PEM parse → x509.CertPool
x509.Certificate.Verify(VerifyOptions{Roots: rootPool})
```

**Meglévő infrastruktúra:** `core/cabinet/pki_verify.go` — `VerifyOptions`, `checkRevocation()`, `checkSPKIPinning()`  
**Új wrapper:** `VerifyArtifactCountersign(artifact *SchemaArtifact, expectedPayloadName string) error`  
**Státusz:** scaffold — `pki_verify.go` bővítése szükséges, CA trust store setup

---

## Interface javaslat

```go
// SchemaLoader felelős a CIC-Schemas release artifact betöltéséért és verifikálásáért.
type SchemaLoader struct {
    repoPath    string                  // helyi git repo path
    vaultClient *VaultClient            // nil = sign verify skip
    verifyLevel SchemaVerifyLevel       // ChecksumOnly | ChecksumAndSign | Full
}

type SchemaVerifyLevel int
const (
    ChecksumOnly      SchemaVerifyLevel = iota  // PoC minimum
    ChecksumAndSign                              // + Vault sign verify
    FullVerification                             // + CICCountersign CA verify
)

func (l *SchemaLoader) Load(name, version string) (*cabinet.Schema, error)
```

### Integráció a relay bootban

**`cmd/relay/bootstrap.go`** — `SchemaLoader` inicializálás a server startup sorrendbe illesztve:

```go
schemaLoader := NewSchemaLoader(cfg.SchemasRepoPath, vaultClient, ChecksumOnly)
schema, err := schemaLoader.Load("cic-relay-config", "v0.1.0_poc")
if err != nil {
    return nil, fmt.Errorf("relay-config schema load failed: %w", err)
}
```

---

## Fájlok összefoglalója

| Fájl | Módosítás | Státusz |
|---|---|---|
| `cmd/relay/schema_loader.go` | **Új fájl** — betöltés + checksum verify | PoC minimum |
| `cmd/relay/bootstrap.go` | Bővítés — `SchemaLoader` init + relay-config load | PoC minimum |
| `core/cabinet/pki_verify.go` | Bővítés — `VerifyArtifactCountersign()` wrapper | scaffold |
| `cmd/relay/pki_bootstrap.go` | Vizsgálandó — van-e Vault transit verify hívás | scaffold |

---

## PoC minimum scope

A relay séma verifikáció PoC-minimum implementációja:

1. `cmd/relay/schema_loader.go` megírása — `LoadSchemaArtifact()` + `VerifyChecksum()`
2. `cmd/relay/bootstrap.go` bővítése — `cic-relay-config@v0.1.0_poc` betöltés + checksum verify a startup-ban
3. A Vault sign verify és CA countersign verify scaffold marad — a struct-ok és az interface már definiált, az implementáció blokkoló nélkül hozzáadható

Ez a három lépés elegendő ahhoz, hogy a relay induláskor ellenőrizze saját konfigurációjának spec integritását.
