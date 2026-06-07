# relay-lint-setup — staticcheck telepítése a builder image-be

## Háttér

A `relay-build-test` job kimutatta, hogy a `make lint-go` target `staticcheck: not found` hibával áll meg — az eszköz nincs a `golang:1.25.10` alap builder image-ben.

## Célod

A `staticcheck` telepítését beépíteni a CIC-Relay build infrastruktúrájába úgy, hogy a `make lint-go` a builder containerben megbízhatóan futtatható legyen.

## Forrás

CIC-Relay repo: `${CIC_RELAY_PATH}`
Érintett fájlok: `Makefile`, `docker-compose.yaml`, esetleg `mk/infra.mk`

## Elemzési feladat

Először döntsd el a legjobb megközelítést:

**A) `prepare` target bővítése:**
```makefile
prepare: infra-init
    @mkdir -p $(BUILD_DIR)
    @sudo chown ...
    $(call GO_EXEC, go install honnef.co/go/tools/cmd/staticcheck@latest)
```

**B) Dockerfile bővítése** (ha van külön Dockerfile a builderhez):
```dockerfile
RUN go install honnef.co/go/tools/cmd/staticcheck@latest
```

**C) `lint-go` target javítása** — auto-install ha hiányzik:
```makefile
lint-go:
    $(call GO_EXEC, \
        command -v staticcheck || go install honnef.co/go/tools/cmd/staticcheck@latest; \
        staticcheck ./...)
```

Nézd meg a meglévő Makefile és docker-compose.yaml struktúráját, és válaszd a legkevésbé invazív megközelítést.

## Elvégzendő lépések

1. Elemzés: melyik A/B/C opció illik legjobban a meglévő struktúrába
2. Módosítás elvégzése
3. Ellenőrzés:
```bash
cd ${CIC_RELAY_PATH}
COMPOSE_FILE=docker-compose.yaml make lint-go
```
4. Ha lint-go exit 0: commit + push feature branch-re

## Output fájlok

`output/lint-setup-report.md`:

```markdown
## Kiválasztott megközelítés
[A/B/C + indoklás]

## Módosított fájlok
[fájlnév + diff összefoglaló]

## lint-go futtatás eredménye
**Exit code:** 0 / 1
**Kimenet:** [staticcheck találatok vagy "nincs hiba"]

## Git commit
**Branch:** fix/staticcheck-setup
**Commit hash:** ...
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| staticcheck elérhető a containerben | true/false | `command -v staticcheck` kimenet | docker exec futtatva | közepes |
| lint-go átmegy | true/false | exit code + kimenet | make lint-go futtatva | közepes |
| változások commitolva | true/false | commit hash | git log | alacsony |

## Szabályok

- **Exit code 0 ≠ sikeres** — olvasd el a staticcheck kimenetét, keress valódi linthibát
- Ne tiltsd le a lint szabályokat — csak az infrastruktúrát javítsd
- Ha staticcheck valódi hibát talál a kódban: rögzítsd az outputban, de ne javítsd (külön job)
