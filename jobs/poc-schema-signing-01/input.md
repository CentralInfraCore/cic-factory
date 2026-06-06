# poc-schema-signing-01 — CICSourceCA Vault signing aktiválás

## Kontextus

Szülő job: `poc-implementation-plan` — olvasd el az `output/status-matrix.md`-t (schemacompile és schemapipeline sorok).

**Előfeltétel:** `poc-infra-01` kész (Vault szükséges).
**Párhuzamos:** `poc-observer-plugin-01`-gyel párhuzamosan futhat.

## Jelenlegi állapot (scaffold)

A schemacompile modul három lépése (c442):
- `cic.source.assert@1.0` — stub mode (PKI chain verify nincs bekötve)
- `cic.schema.build@1.0` — stub artifact generálás
- `cic.artifact.sign@1.0` — `cic_sign="unavailable"`, `cic_signed_ca="stub:pending"`

A `verification_root` (Merkle-gyök) mindig érvényes, de a Vault aláírás hiányzik.

## Feladat

### 1. Vault PKI backend setup

`jobs/poc-schema-signing-01/output/vault-setup.sh`:
```bash
# Vault PKI engine aktiválás
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# CICSourceCA root cert generálás
vault write pki/root/generate/internal \
  common_name="CICSourceCA" \
  ttl=87600h

# CIC relay key beállítás
vault write pki/roles/cic-relay-sign \
  allowed_domains="relay.cic.local" \
  allow_subdomains=true \
  max_ttl=720h
```

### 2. schemacompile Vault integráció

A `CIC-Relay/core/modules/schemacompile/schemacompile.go` módosítása:
- `NewSignArtifactFunc` signer paraméter bekötése valós Vault kliensre
- `cic_sign` = Vault által aláírt `build_hash`
- `cic_signed_ca` = CICSourceCA cert chain PEM

Szükséges: `github.com/hashicorp/vault/api` Go kliens.

### 3. CertVerifyFunc implementálás

```go
// CertVerifyFunc bekötése valós PKI verifikációhoz
func VaultCertVerify(cert *x509.Certificate) error {
    // CICSourceCA root cert-tel való chain verify
    // ...
}
```

### 4. schemapipeline tesztelés

A négy lépéses pipeline (c453) futtatása docker alapon:
```
cic.pipeline.start → cic.pipeline.test → cic.pipeline.validate → cic.pipeline.release
```

A release output: signed artifact → cic.source.assert input.

### 5. Ellenőrzési feltételek (Definition of Done)

- [ ] `cic_sign` valós Vault aláírást tartalmaz (nem "unavailable")
- [ ] `cic_signed_ca` valós CICSourceCA PEM (nem "stub:pending")
- [ ] `verification_root` Merkle-gyök érvényes és reprodukálható
- [ ] `cic.schema.compile` workflow end-to-end fut
- [ ] `git verify-commit` az aláírt artifact commitján érvényes

## Megjegyzések

- Ez a job **párhuzamos** — nem blokkolja a 8.1–8.4 demo fázisokat
- A PoC v1 demonstráció `pose_result: "SKIPPED"` mellett is meggyőző — ez a job a trust layer teljességét adja hozzá
- Layer 0.2 (CIC-Schemas compiler) és Layer 2 (CICSourceCA cert chain) egyszerre kerül bekötésre

## Nyelvi szabály

- Dokumentáció: **magyarul**
- Go kód, shell script, YAML: **angolul**
