# relay-build-test — Build Report

**Dátum:** 2026-06-07  
**Commit (CIC-Relay):** 32b2c21  
**Builder image:** golang:1.25.10 (docker-compose.yaml)

---

## Előkészítés

`docker compose -f docker-compose.yaml up -d builder` — **sikeres**

`make prepare` — **sikertelen** (sudo szükséges a `chown` lépéshez, terminál nélküli környezetben nem futtatható)  
Megoldás: `mkdir -p ./output/32b2c21` manuálisan létrehozva.

**Megjegyzés:** A Makefile két compose fájlt talál (`docker-compose.yml` és `docker-compose.yaml`). Az alapértelmezett a `.yml` (Python builder, `/app` mount), a Go builderhez a `.yaml` fájl szükséges (`/git-source` mount). Minden `make` parancs `COMPOSE_FILE=docker-compose.yaml` env variable-lal futott.

---

## Fázis 1 — Quality gates

### fmt-check

**Exit code:** 2 (FAIL)  
**Kimenet:**
```
cmd/relay/activator.go
cmd/relay/activator_test.go
cmd/relay/bootstrap.go
cmd/relay/bootstrap_test.go
cmd/relay/git_host_funcs_test.go
cmd/relay/main.go
cmd/relay/main_api_test.go
cmd/relay/middleware.go
cmd/relay/middleware_test.go
cmd/relay/pki_bootstrap.go
cmd/relay/proof_verify.go
core/cabinet/execution_recorder.go
core/cabinet/graph.go
core/cabinet/graph_test.go
core/cabinet/proof_trace.go
core/cabinet/proof_trace_test.go
core/cabinet/schema_validate.go
core/cabinet/schema_validate_test.go
core/cabinet/service.go
core/cabinet/service_integration_test.go
core/modules/certselfsigned/certselfsigned.go
core/modules/certselfsigned/certselfsigned_test.go
core/modules/cibuild/cibuild.go
core/modules/cibuild/cibuild_test.go
core/modules/schemapipeline/schemapipeline.go
core/nexus/iac/source_upstream.go
core/nexus/iac/validator_test.go
core/nexus/isolation/ipc_test.go
core/nexus/isolation/worker_subprocess.go
core/nexus/operator/bootstrap.go
core/nexus/operator/bootstrap_test.go
core/nexus/operator/lifecycle.go
core/nexus/operator/lifecycle_test.go
core/nexus/operator/watcher.go
core/nexus/recorder/workflow_recorder.go
core/nexus/types/types.go
pkg/obs/capture.go
pkg/obs/logrus_sink.go
pkg/obs/sink.go
pkg/obs/types.go
tools/sourcehash/main.go
Code not formatted. Run make fmt
```
**Értékelés:** 40 Go fájl nincs `gofmt -s` szerint formázva. CI-blokkoló.

### vet

**Exit code:** 0 (PASS)  
**Kimenet:**
```
Vet on: centralrelay/cmd/relay centralrelay/core/cabinet centralrelay/core/modules/certselfsigned
centralrelay/core/modules/cibuild centralrelay/core/modules/schemacompile centralrelay/core/modules/schemapipeline
centralrelay/core/nexus/crypto centralrelay/core/nexus/git centralrelay/core/nexus/iac
centralrelay/core/nexus/isolation centralrelay/core/nexus/operator centralrelay/core/nexus/recorder
centralrelay/core/nexus/sync centralrelay/core/nexus/types centralrelay/embedded/pki
centralrelay/pkg/canonicaljson centralrelay/pkg/merkle centralrelay/pkg/obs centralrelay/pkg/sourcedigest
centralrelay/tools/canonicalize centralrelay/tools/certutils centralrelay/tools/sourcehash centralrelay/tools/symbolsgen
```
Minden package átment, nincs vet hiba.

### lint-go

**Exit code:** 2 (FAIL)  
**Kimenet:**
```
sh: 1: staticcheck: not found
```
**Értékelés:** A `staticcheck` eszköz nincs telepítve a builder image-ben (golang:1.25.10 alap image). A lint-go target implicit függősége nincs kielégítve.

---

## Fázis 2 — Tesztek

### test-go

**Exit code:** 0 (PASS)  
**Kimenet (összefoglaló):**
```
ok  centralrelay/cmd/relay                     1.195s
ok  centralrelay/core/cabinet                  2.359s
ok  centralrelay/core/modules/certselfsigned   1.020s
ok  centralrelay/core/modules/cibuild          1.029s
ok  centralrelay/core/modules/schemacompile    1.026s
ok  centralrelay/core/modules/schemapipeline   1.028s
ok  centralrelay/core/nexus/crypto             10.875s
ok  centralrelay/core/nexus/git                1.199s
ok  centralrelay/core/nexus/iac                1.161s
ok  centralrelay/core/nexus/isolation          2.032s
ok  centralrelay/core/nexus/operator           2.012s
ok  centralrelay/core/nexus/recorder           1.146s
ok  centralrelay/core/nexus/sync               1.283s
ok  centralrelay/pkg/canonicaljson             1.015s
ok  centralrelay/pkg/merkle                    1.011s
ok  centralrelay/pkg/obs                       1.017s
ok  centralrelay/pkg/sourcedigest              1.021s
ok  centralrelay/tools/canonicalize            1.017s
ok  centralrelay/tools/certutils               1.060s
ok  centralrelay/tools/sourcehash              1.018s
ok  centralrelay/tools/symbolsgen              1.699s
```
Nincs FAIL, nincs panic. Race detector (`-race`) aktív volt.

### coverage

**Exit code:** 0 (PASS)  
**Coverage per package:**
```
cmd/relay:                    89.6%
core/cabinet:                 94.7%
core/modules/certselfsigned:  100.0%
core/modules/cibuild:         94.9%
core/modules/schemacompile:   91.3%
core/modules/schemapipeline:  94.0%
core/nexus/crypto:            94.7%
core/nexus/git:               93.5%
core/nexus/iac:               90.9%
core/nexus/isolation:         90.8%
core/nexus/operator:          90.6%
core/nexus/recorder:          87.1%
core/nexus/sync:              88.9%
pkg/canonicaljson:            96.7%
pkg/merkle:                   98.3%
pkg/obs:                      99.0%
pkg/sourcedigest:             85.7%
tools/canonicalize:           100.0%
tools/certutils:              83.0%
tools/sourcehash:             100.0%
tools/symbolsgen:             90.2%
```
Coverage profil: `output/32b2c21/coverage.out`  
HTML report: `output/32b2c21/coverage.html`

---

## Fázis 3 — Bináris build (PKI embed nélkül)

**Exit code:** 0 (PASS)  
**Parancs:**
```bash
go build -o /tmp/relay-test ./cmd/relay/...
```
**Eredmény:**
```
-rwxr-xr-x 1 root root 16M Jun  7 17:28 /tmp/relay-test
```
A bináris lefordult, 16MB. PKI cert embed nélkül.

---

## Fázis 4 — Teljes build (make build-relay)

**Állapot:** Vault részlegesen elérhető — **nem futtatható**

**Részletek:**
- `${XDG_RUNTIME_DIR}/vault/sign-token` és `server.crt` fájlok léteznek a hoston
- `VAULT_TOKEN` env variable nincs beállítva a shell környezetben
- `make build-relay` a `fetch-pki` target-nél áll meg: `VAULT_TOKEN: unbound variable`
- A Makefile-ban a `fetch-pki` script explicit `set -euo pipefail` miatt fail-fast

**Következtetés:** Vault szerver valószínűleg fut (pid fájl, token fájl jelen van), de a `VAULT_TOKEN` exportálása szükséges a shell session-ben a build futtatásához.

---

## Infrastruktúra megfigyelések

1. **Kettős compose fájl:** `docker-compose.yml` (Python/legacy) és `docker-compose.yaml` (Go builder) konfliktust okoz — docker compose mindig a `.yml`-t használja alapértelmezetten. A `COMPOSE_FILE=docker-compose.yaml` env variable megkerüli ezt.
2. **staticcheck hiányzik:** A `lint-go` target `staticcheck`-et hív, ami nincs a golang alap image-ben. Installálni kell: `go install honnef.co/go/tools/cmd/staticcheck@latest`.
3. **git safe.directory:** A builder container más user-ként fut — `git config --global --add safe.directory /git-source` szükséges első futtatáskor.
4. **make prepare sudo:** A `prepare` target `sudo chown` lépése terminál nélküli (nem-TTY) környezetben nem működik.
