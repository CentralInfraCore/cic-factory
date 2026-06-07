# Claim Evidence — relay-full-build

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| Vault token elérhető | true | `/run/user/1000/vault/sign-token` olvasható (95 byte), vault status: Initialized=true Sealed=false | `cat + test -n`, `vault status` https://localhost:18200 | kritikus |
| fetch-pki sikeres | true | `embedded/pki/cic-source-ca.pem` létrejött, make exit 0 | `make fetch-pki` futtatva, VAULT_ADDR+TOKEN exportálva | kritikus |
| make build-relay átmegy | true | exit code 0, bináris: `output/8d7103a/cic-relay` 11MB | `make quality test-go coverage coverage-check-pkgs` + binary build futtatva | kritikus |
| bináris PKI certtel épül | true | `strings output/8d7103a/cic-relay \| grep -c "BEGIN CERT"` = 3 | bináris string inspect | közepes |

## Blokkolók és elhárításuk

| Blokkoló | Probléma | Megoldás |
|---|---|---|
| `VAULT_TOKEN: unbound variable` | Az előző futásban nem volt exportálva | `export VAULT_TOKEN=$(cat /run/user/1000/vault/sign-token)` + VAULT_ADDR beállítva |
| `prepare: sudo chown` | Non-interaktív sudo nem engedélyezett | Az output/ már sinkog-tulajdon, manuálisan `mkdir -p output/8d7103a` |
| staticcheck U1000 lint | `mockCall.args` field unused | Eltávolítva `schemapipeline_test.go`-ból |
| govulncheck 4 sebezhetőség | go-jose v4.1.1 + x/net v0.53.0 | `go get` frissítette v4.1.4 és v0.55.0-ra |
| govulncheck 2 stdlib seb. | go1.25.10 net/textproto + crypto/x509 | docker-compose.yaml: golang:1.25.10 → golang:1.25.11 |
| git safe.directory | Új container, mount ownership mismatch | `git config --global --add safe.directory /git-source` |

## Bináris adatok

```
Path:   /home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay/output/8d7103a/cic-relay
Size:   11MB
SHA256: f47d7a44ee054402e6f516557d2eb5c29f0a2ee502250bdc8c5315fc8008552a
PKI:    3 × "BEGIN CERT" (strings inspect)
SBOM:   output/8d7103a/SOURCE.MANIFEST.sha256
```
