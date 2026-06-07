# relay-build-test — Claim Evidence Table

**Dátum:** 2026-06-07  
**Commit (CIC-Relay):** 32b2c21  
**Verifikációs környezet:** Docker builder (golang:1.25.10), `docker-compose.yaml`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| fmt-check átmegy | **false** | Exit code 2; 40 fájl nem formázott (`gofmt -s -l` lista) | `COMPOSE_FILE=docker-compose.yaml make fmt-check` futtatva | közepes — CI-blokkoló, de nem fordítási hiba |
| go vet átmegy | **true** | Exit code 0; mind a 23 package átment, nincs vet hiba | `COMPOSE_FILE=docker-compose.yaml make vet` futtatva | alacsony |
| lint-go átmegy | **false** | Exit code 2; `staticcheck: not found` — az eszköz nincs a builder image-ben | `COMPOSE_FILE=docker-compose.yaml make lint-go` futtatva | közepes — infrastruktúra hiány, nem kódhiba |
| test-go átmegy | **true** | Exit code 0; mind a 21 tesztelt package PASS, race detector aktív | `COMPOSE_FILE=docker-compose.yaml make test-go` futtatva | kritikus ✓ |
| coverage elkészül | **true** | Exit code 0; coverage 83.0%–100.0% minden package-ben | `COMPOSE_FILE=docker-compose.yaml make coverage` futtatva | alacsony |
| bináris lefordul | **true** | Exit code 0; `/tmp/relay-test` létrejött, 16MB | `go build -o /tmp/relay-test ./cmd/relay/...` a containerben | kritikus ✓ |
| teljes build (make build-relay) | **vault-függő** | Exit code 2; `fetch-pki` lépésnél: `VAULT_TOKEN: unbound variable` | `COMPOSE_FILE=docker-compose.yaml make build-relay` futtatva | közepes — Vault token export hiányzik |

## Összefoglalás

- **Kritikus állítások (test + binary):** mindkettő teljesül
- **Quality gate hibák:** 2 db
  - `fmt-check`: kódformázás eltérés (make fmt-mal javítható)
  - `lint-go`: `staticcheck` nem telepített a builder image-ben (infrastruktúra probléma)
- **Vault-függő:** `make build-relay` csak `VAULT_TOKEN` env exportálása után futtatható
