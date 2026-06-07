## Vault előkészítés

**VAULT_TOKEN elérhető:** igen
**Vault status:** Initialized=true, Sealed=false, Version=2.0.0, Storage=inmem

## CIC-Relay módosítások (blokkolók elhárítása)

A build pipeline futtatása során 3 probléma volt, amelyeket el kellett hárítani:

1. **schemapipeline_test.go** — `mockCall.args` unused field (staticcheck U1000) → eltávolítva
2. **go.mod / go.sum** — 4 govulncheck sebezhetőség → `golang.org/x/net` v0.53.0→v0.55.0, `github.com/go-jose/go-jose/v4` v4.1.1→v4.1.4 (+ transitív frissítések)
3. **docker-compose.yaml** — 2 Go stdlib sebezhetőség (go1.25.10) → builder/fixer image frissítve golang:1.25.11

## make build-relay

**Exit code:** 0
**fetch-pki:** sikeres — `embedded/pki/cic-source-ca.pem` létrehozva
**quality gate:** sikeres — fmt-check ✓, lint-go ✓, vet ✓, vuln ✓ (no vulnerabilities found)
**test-go:** sikeres — összes teszt PASS
**coverage:** sikeres — minden csomag a küszöb felett
**Bináris:** `output/8d7103a/cic-relay` — 11MB — sha256:`f47d7a44ee054402e6f516557d2eb5c29f0a2ee502250bdc8c5315fc8008552a`

## Bináris verifikáció

**PKI cert embedálva:** igen (3 × "BEGIN CERT" a binárisban)
**make manifest-src:** sikeres — `output/8d7103a/SOURCE.MANIFEST.sha256` létrehozva

## Coverage összesítő (coverage-check-pkgs)

| Csomag | Elért | Minimum |
|---|---|---|
| cmd/relay | 89.8% | 80% |
| core/cabinet | 94.7% | 93% |
| core/modules/certselfsigned | 100.0% | 99% |
| core/modules/cibuild | 94.9% | 94% |
| core/modules/schemacompile | 91.3% | 90% |
| core/modules/schemapipeline | 94.0% | 90% |
| core/nexus/crypto | 94.7% | 93% |
| core/nexus/git | 93.5% | 92% |
| core/nexus/iac | 90.9% | 90% |
| core/nexus/isolation | 90.8% | 90% |
| core/nexus/operator | 90.6% | 90% |
| core/nexus/recorder | 87.1% | 85% |
| core/nexus/sync | 88.9% | 88% |
| pkg/canonicaljson | 96.7% | 96% |
| pkg/merkle | 98.3% | 97% |
| pkg/obs | 99.0% | 97% |
| pkg/sourcedigest | 85.7% | 85% |
| tools/canonicalize | 100.0% | 99% |
| tools/certutils | 83.0% | 82% |
| tools/symbolsgen | 90.2% | 90% |
