# relay-build-test — CIC-Relay build és teszt folyamat

## Célod

Végigfuttatni a CIC-Relay saját build toolchain-jét (`make` célok, Docker builder container) és dokumentálni mi megy át, mi nem, mi Vault-függő.

A cél nem a kód olvasása — hanem a tényleges futtatás és az eredmény rögzítése.

## Forrás

CIC-Relay repo helye: `${CIC_RELAY_PATH}`

Ez egy lokális git repo, Docker Compose konfigurációval és Makefile-lal. Minden Go futtatás a builder containerben történik (`docker compose exec -T builder`).

## Előkészítés

```bash
cd ${CIC_RELAY_PATH}
docker compose up -d builder
make prepare
```

Ha `docker compose up -d` sikertelen: rögzítsd a hibát és állj meg.

## Futtatandó fázisok sorrendben

### Fázis 1 — Quality gates (Vault nélkül)

```bash
cd ${CIC_RELAY_PATH}
make fmt-check
make vet
make lint-go
```

Minden célt futtass külön, gyűjtsd a kimenetét és exit code-ját.

### Fázis 2 — Tesztek (Vault nélkül)

```bash
cd ${CIC_RELAY_PATH}
make test-go
```

Ha van coverage target és a test-go átment:
```bash
make coverage
```

### Fázis 3 — Bináris build (Vault nélkül, PKI embed nélkül)

`make build-relay` Vault-ot igényel (`fetch-pki`). Helyette:

```bash
docker compose exec -T builder sh -c '
  cd /git-source &&
  go build -o /tmp/relay-test ./cmd/relay/...
'
```

Ha ez sikeres: a bináris lefordult, PKI cert embed nélkül.

### Fázis 4 — Teljes build (opcionális, csak ha VAULT_ADDR és VAULT_TOKEN elérhető)

```bash
cd ${CIC_RELAY_PATH}
make build-relay
```

Ha Vault nem elérhető: jegyezd fel mint "Vault-függő, nem futtatható" — ez nem hiba.

## Cleanup

```bash
cd ${CIC_RELAY_PATH}
docker compose down
```

## Output fájlok

`output/build-report.md` — Fázisok eredménye:

```markdown
## Fázis 1 — Quality gates
### fmt-check
**Exit code:** 0 / 1
**Kimenet:**
[teljes kimenet vagy releváns részlet]

### vet
...

### lint-go
...

## Fázis 2 — Tesztek
### test-go
**Exit code:** 0 / 1
**Kimenet:**
[PASS/FAIL sorok, panic-ok ha van]

## Fázis 3 — Bináris build
**Exit code:** 0 / 1
**Kimenet:**
[fordítási hibák ha van]

## Fázis 4 — Teljes build
**Állapot:** Vault elérhető / nem elérhető — nem futtatható
```

`output/claim-evidence.md` — Kötelező táblázat:

```markdown
| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| fmt-check átmegy | true/false | exit code + kimenet | make fmt-check futtatva | alacsony/közepes |
| go vet átmegy | true/false | exit code + kimenet | make vet futtatva | alacsony/közepes |
| lint-go átmegy | true/false | exit code + kimenet | make lint-go futtatva | közepes |
| test-go átmegy | true/false | exit code + PASS/FAIL sorok | make test-go futtatva | kritikus |
| bináris lefordul | true/false | exit code + binary path | go build futtatva | kritikus |
| teljes build | true/false/vault-függő | exit code vagy hibaüzenet | make build-relay | közepes |
```

Minden sort töltsd ki a tényleges futtatás eredménye alapján.

## Szabályok

- **Fájl létezése ≠ működik** — minden állítás mögé tényleges futtatási eredmény kell
- **Exit code 0 ≠ sikeres** — olvasd el a kimenetet, keress rejtett hibát (`FAIL`, `panic`, `error`)
- Ha egy fázis megáll (exit code != 0): rögzítsd a teljes hibaüzenetet, folytasd a következő fázissal ahol lehet
- Docker container-t indítás után cleanup-pal zárd (`docker compose down`)
- Ne módosítsd a CIC-Relay forrást
