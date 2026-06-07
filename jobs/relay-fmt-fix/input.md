# relay-fmt-fix — Go forráskód formázás

## Háttér

A `relay-build-test` job kimutatta, hogy 40 Go fájl nincs `gofmt -s` szerint formázva a CIC-Relay repóban (commit 32b2c21). A `make fmt-check` CI-blokkoló hibával áll meg.

## Célod

Futtatni `make fmt-go`-t a CIC-Relay repóban a Docker builder containerben, majd commitolni az eredményt a CIC-Relay feature branch-re.

## Forrás

CIC-Relay repo: `${CIC_RELAY_PATH}`

## Elvégzendő lépések

```bash
cd ${CIC_RELAY_PATH}
COMPOSE_FILE=docker-compose.yaml docker compose up -d builder
COMPOSE_FILE=docker-compose.yaml make fmt-go
```

Ellenőrzés — ezután zöldre kell fordulnia:

```bash
COMPOSE_FILE=docker-compose.yaml make fmt-check
```

Ha fmt-check zöld (exit 0): commitold a változásokat a CIC-Relay feature branch-re:

```bash
git -C ${CIC_RELAY_PATH} checkout -b fix/gofmt
git -C ${CIC_RELAY_PATH} add -u
git -C ${CIC_RELAY_PATH} commit -m "style: apply gofmt -s to all Go files"
git -C ${CIC_RELAY_PATH} push -u origin fix/gofmt
```

## Output fájlok

`output/fmt-report.md` — Eredmény:

```markdown
## fmt-go futtatás
**Exit code:** 0 / 1
**Módosított fájlok száma:** N

## fmt-check ellenőrzés
**Exit code:** 0 / 1

## Git commit
**Branch:** fix/gofmt
**Commit hash:** ...
**Push:** sikeres / sikertelen
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| fmt-go lefutott | true/false | exit code | make fmt-go futtatva | alacsony |
| fmt-check zöld | true/false | exit code 0 | make fmt-check futtatva | közepes |
| változások commitolva | true/false | commit hash | git log | alacsony |

## Szabályok

- **Exit code 0 ≠ sikeres** — olvasd el a kimenetet
- Csak `git add -u` — ne adj hozzá új fájlokat
- Ne módosítsd a kódlogikát — csak formázás
