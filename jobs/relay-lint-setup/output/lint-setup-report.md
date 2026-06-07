## Kiválasztott megközelítés

**C — auto-install a `lint-go` target-ben, ha a tool hiányzik**

Indoklás:
- A `tdd` target ugyanezt a mintát alkalmazza (`command -v reflex || go install ...`) — konzisztens a meglévő kóddal
- Nincs egyedi Dockerfile (B kiesik) — az összes service a stock `golang:1.25.10` image-t használja
- A `prepare` target build-könyvtárakat inicializál, nem tool-okat telepít (A nem odavaló)
- Az auto-install csak akkor fut, ha a tool tényleg hiányzik — a `~/tmp/cache/CIC-Relay/go/bin:/go/bin` volume-mount miatt telepítés után persists a cache-ben

## Módosított fájlok

**`CIC-Relay/Makefile`** — `lint-go` target, +1 sor:

```diff
 lint-go: ## Run Go static linters (staticcheck, ineffassign)
 	mkdir -p $(BUILD_DIR) && $(call GO_EXEC, \
 		set -euo pipefail; \
+		command -v staticcheck >/dev/null 2>&1 || GOFLAGS="" go install honnef.co/go/tools/cmd/staticcheck@v0.6.1; \
 		PKGS="$$(go list ./... | grep -v /vendor/)"; \
```

Megjegyzések:
- `GOFLAGS=""` szükséges az install lépésnél, mert a globális `GOFLAGS` `-mod=readonly` flaget tartalmaz, ami nem engedélyez module-on kívüli tool telepítést
- A `@v0.6.1` verzió a `cache-populate` target-tel konzisztens
- A `command -v` + `|| install` minta biztonságos `-e` shell flag mellett: ha a check sikertelen, az `||` branch fut (nem exit)

## lint-go futtatás eredménye

**Exit code:** 1 (staticcheck lint hiba található a kódban)

**Kimenet:**
```
go: downloading honnef.co/go/tools v0.6.1
...
Staticcheck on: centralrelay/cmd/relay centralrelay/core/cabinet ...
core/modules/schemapipeline/schemapipeline_test.go:27:2: field args is unused (U1000)
```

**Értékelés:** A `staticcheck` sikeresen települt és futott. Az exit code 1 nem infrastruktúra-probléma — valódi lint hibát talált a kódban. Az `args` mező `schemapipeline_test.go:27`-ben unused (U1000 = unused code). Ez külön job tárgya.

## Git commit

**Repo:** CentralInfraCore/CIC_Relay  
**Branch:** fix/staticcheck-setup  
**Commit hash:** 8d7103a  
**Push:** origin/fix/staticcheck-setup ✓
