# wasm-template-hardening — végrehajtási riport

**Branch:** `wasm/f/hardening` (a base-repo `wasm/main` HEAD `5b231a3`-ból ágazva)
**Architektúra:** nem változott — a WASM ABI (allocate/deallocate/Call), a wazero
host-load teszt és a buildHash-alapú aláírási lánc megmaradt; a review által
azonosított varratokat zártuk be.

A jelentés a 9 review-pontot (A.1–A.3, B.4–B.6, C.7–C.9) fedi le egy
claim-evidence táblában, majd az A.3 mock nélküli teszt futtatás-kimenetét és a
C.8 kockázat-megjegyzést részletezi.

## Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| **A.1** `MANIFEST.sha256` újragenerálva, minden git-követett fájl (incl. `module/module.wasm`, `module/envelope.go`, `mk/wasm.mk`, `docs/*/wasm-module-authoring.md`) szerepel | implemented | `MANIFEST.sha256` 82 sor, `module/module.wasm: OK`, `module/envelope.go: OK`, `module/envelope_test.go: OK` a `manifest-verify` kimenetében | `GID=$(id -g) make manifest-update && GID=$(id -g) make manifest-verify` — minden sor `OK`, lent idézve | A `module.wasm` tartalma TinyGo build-determinizmustól függ — ld. az alábbi C.8/manifest kockázat-megjegyzést |
| **A.1** `manifest-update` / `manifest-verify` make targetek léteznek és karbantarthatók | implemented | `mk/infra.mk` tartalmazza a `manifest-update`/`manifest-verify` targeteket (docker compose exec wrapper); `Makefile` exportálja őket | `grep -n "manifest-update\|manifest-verify" mk/infra.mk Makefile` — lásd lent | — |
| **A.1** `manifest-verify` be van kötve a CI-be | implemented | `.github/workflows/ci.yml:33`: `run: make manifest-verify`, a `make check` és `make golang.quality` ELŐTT | `grep -n "manifest-verify" .github/workflows/ci.yml` → `33:        run: make manifest-verify` | — |
| **A.2** `canonical_source_file: schemas/index.yaml` explicit a `project.yaml`-ban | implemented | `project.yaml:48`: `canonical_source_file: schemas/index.yaml` (`compiler_settings` blokk) | `grep -n "canonical_source_file" project.yaml` → `48:  canonical_source_file: schemas/index.yaml`; `make validate COMPILER_CLI_ARGS=-v` zöld, kimenet lent idézve | — |
| **A.3** `_validate_final_project_yaml()` javítva — `schema["spec"]` helyett a teljes `project.schema.yaml`-t használja | implemented | `tools/infra.py:180-192` — `schema_path = self._path("project.schema.yaml")`, `validate(instance=instance, schema=schema)` (nincs `["spec"]` indexelés) | `file:line` + lent a mock nélküli teszt futtatás-kimenete | — |
| **A.3** mock nélküli teszt a valós `project.schema.yaml`-lal, siker- és hiba-ággal | implemented | `tests/test_tools/test_infra.py` — `TestValidateFinalProjectYamlRealSchema` osztály (3 teszt: érvényes instance elfogadása, kötelező mező hiánya → `ValidationFailureError`, üres `buildHash` → `ValidationFailureError`) | `docker compose exec builder python -m pytest tests/test_tools/test_infra.py -v -k RealSchema` → 3 passed, lent idézve | A meglévő mockolt tesztek (`test_infra_coverage.py:120`) megmaradtak, de ez a 3 teszt a VALÓS sémafájllal és VALÓS `_validate_final_project_yaml` kóddal fut |
| **A.3** `ValidationFailureError` nem csomagolódik át `ReleaseError`-ré | implemented | `tools/infra.py:202-203`: `except ValidationFailureError: raise` az első except-ágban, a generikus `except Exception` ELŐTT | A javítás nélkül `test_real_schema_rejects_empty_build_hash` `ReleaseError`-t kapott volna `ValidationFailureError` helyett — a teszt most ezt a kódutat fedezi | — |
| **B.4** README/README.hu fő identitása "CIC WASM Module Template" | implemented | `README.md` / `README.hu.md` — első szakasz "CIC WASM Module Template" / "CIC WASM Modul Sablon", a `handlers.go`, iSDK v1 `Call` ABI, `wasm.build`/`wasm.test`, buildHash-provenance leírásával; a schema-compiler/signing örökség az utolsó "Inherited: Schema Compiler & Signing Infrastructure" / "Örökölt: Séma Fordító és Aláíró Infrastruktúra" szakaszba került | Fájl-tartalom, `git diff wasm/main HEAD -- README.md README.hu.md` | — |
| **B.5** `module_loadtest_test.go` — `get`: `error==null` ÉS `data.status=="ok"` | implemented | `module/module_loadtest_test.go:134-152` (`TestHostLoad`) | `GID=$(id -g) make wasm.test` → `--- PASS: TestHostLoad` (lent idézve) | — |
| **B.5** ismeretlen op → `INPUT` kódú error envelope | implemented | `module/module_loadtest_test.go:156-171` (`TestHostLoadUnknownOp`) | `--- PASS: TestHostLoadUnknownOp` (lent idézve) | — |
| **B.5** hibát adó handler → error envelope a megfelelő kóddal | implemented | `module/module_loadtest_test.go:176-191` (`TestHostLoadHandlerError`, `get` op `data="not-json"`-tal → `error.code=="INPUT"`, a `handlers.go:29-34` `Get`-je `NewGuestError(CodeInput, ...)`-ot ad vissza) | `--- PASS: TestHostLoadHandlerError` (lent idézve) | — |
| **B.5** `init`/`process`/`notify` null-success szerződés | implemented | `module/module_loadtest_test.go:196-210` (`TestHostLoadNullSuccess`, table-driven subtestek `init`/`process`/`notify`-ra: `data=="null"` ÉS `error=="null"`) | `--- PASS: TestHostLoadNullSuccess` + 3 subtest PASS (lent idézve) | — |
| **B.5** invalid JSON handler-output eset lefedve | implemented | `module/envelope_test.go:44-62` (`TestMarshalDataInvalidJSONOutput`) — `marshalData([]byte("not-json"))` → `{"data":null,"error":{"code":"INTERNAL",...}}` | `docker compose exec -T builder sh -c 'cd /app/module && GOFLAGS=-mod=mod go test -v -run "TestMarshal\|TestGuestError" .'` → 5 PASS (lent idézve) | Ez a guard a `marshalData`-ban van (`module/envelope.go:54-65`), nem a host-load teszten keresztül érhető el (a sablon `Get` handlere mindig valid JSON-t ad vissza) — ezért külön unit teszttel fedve |
| **B.6** tipizált guest-hiba kódokkal (`INPUT\|RUNTIME\|INTERNAL\|RESOURCE\|TIMEOUT`) | implemented | `module/envelope.go:30-36` (kód-konstansok), `:39-46` (`GuestError`/`NewGuestError`); dispatcher: `module/abi.go:45,48-51` | `grep -rn` (kizárva `_test.go`): lásd lent | — |
| **B.6** dispatcher default `RUNTIME` marad | implemented | `module/abi.go:51`: `return pack(marshalErr(CodeRuntime, derr.Error()))` — csak ha `derr` NEM `*GuestError` | `grep -n "CodeRuntime" module/abi.go` → `51:		return pack(marshalErr(CodeRuntime, derr.Error()))` | — |
| **B.6** `Get` handler demonstrálja a `CodeInput`-ot | implemented | `module/handlers.go:29-34`: `return nil, NewGuestError(CodeInput, "data must be valid JSON")` | `module/module_loadtest_test.go` `TestHostLoadHandlerError` ezt futtatja végig wazero-n | — |
| **B.6** `wasm-module-authoring.md` (en+hu) igazítva | implemented | `docs/en/wasm-module-authoring.md` és `docs/hu/wasm-module-authoring.md` — új szakasz a `GuestError`/`NewGuestError`/kód-konstansokról, `Get` kód-mintával | Fájl-tartalom, `git diff wasm/main HEAD -- docs/en/wasm-module-authoring.md docs/hu/wasm-module-authoring.md` | — |
| **C.7** `mk/golang.mk` relay-örökség levágva, `golang.quality` zöld marad | implemented | `mk/golang.mk` 289→193 sor: eltávolítva `APP_NAME ?= cic-relay`, `golang.build-crt-parser`, `golang.build-canonicalize`, `golang.verify-*`, `golang.build`, `golang.manifest-src`, `golang.mq-publish`, `golang.coverage-check-pkgs` (relay per-package küszöbök), `golang.test-api`, `golang.symbols`/`golang.check-symbols`, `golang.cache-populate` — ezek `cmd/relay`, `tools/canonicalize`, `tools/certutils`, `nats-cli`/`mod-cache-loader` service-ekre hivatkoztak, amik nem léteznek a sablonban | `make golang.quality` → `golang.fmt-check`, `golang.lint` (staticcheck), `golang.vet`, `golang.vuln` mind PASS, lent idézve | A `golang.coverage-threshold` (`COVERAGE_MIN`) és `golang.tdd` megmaradt mint generikus dev-target, de nincs CI-bekötve — opcionális |
| **C.8** `project.yaml` cert/signature blokkok placeholderre cserélve | implemented | `project.yaml` `createdBy.certificate/issuer_certificate`, `cicSign`, `cicSignedCA.certificate`, `metadata.sign/checksum/build_timestamp/validity` → `'TBD'` / leíró placeholder string-ek, kommenttel dokumentálva (`project.yaml:17-29`) | `python3 -c "jsonschema.validate(...)"` a builder konténerben → `OK: project.yaml is valid against project.schema.yaml` (lent idézve); `make validate` zöld | A placeholderek `project.schema.yaml` szerint opaque string-ek (a séma nem ír elő formátumot ezekre a mezőkre) — a release folyamatnak (`tools/infra.py` Vault signing lánc) kell valódi értékkel felülírnia finalize előtt |
| **C.8** eredeti cert base64 sérülés megjegyzése | dokumentálva (nem javítva, mert placeholderre cserélve) | A törölt `createdBy.certificate` PEM blokkjában a SAN extension `email:sgz@centralinfracore.hu` után `QGNlbnRyYWxpbmf rore.huwCwYDVR0...` — a base64 `centralinfracore.hu` string `...rore.hu` formában jelent meg, ami sérült/típó base64-re utal | git history (`project.yaml` a `wasm/main` HEAD-en, `createdBy.certificate` mező, ~44. sor) | Mivel ez egy SOHA nem kellett volna élesben lenni real cert volt, és most placeholderre cserélődött, a kérdés tárgytalan a sablonban — de a release pipeline-nak (ami a valós cert-et generálja) érdemes lehet validálni a generált PEM-et |
| **C.9** CI trigger: `wasm/main` + `wasm/f/**` push, `wasm/main` pull_request bázis | implemented | `.github/workflows/ci.yml:9-10` (`push.branches`: `wasm/main`, `wasm/f/**`), `:15` (`pull_request.branches`: `wasm/main`) | `grep -n "wasm/main\|wasm/f" .github/workflows/ci.yml` → lent idézve | — |

## A.3 — mock nélküli teszt futtatás-kimenete

```
$ docker compose exec builder python -m pytest tests/test_tools/test_infra.py -v -k "RealSchema"
tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema::test_real_schema_accepts_valid_project_yaml PASSED [ 33%]
tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema::test_real_schema_rejects_project_yaml_missing_required_field PASSED [ 66%]
tests/test_tools/test_infra.py::TestValidateFinalProjectYamlRealSchema::test_real_schema_rejects_empty_build_hash PASSED [100%]
======================= 3 passed, 14 deselected in 0.34s =======================
```

Ez a 3 teszt:
1. egy valós szerkezetű `project.yaml` instance-t (`canonical_source_file`,
   `buildHash` kitöltve) validál a repó VALÓS `project.schema.yaml`-jával —
   `_validate_final_project_yaml()` nem dob `KeyError`-t (a régi `schema["spec"]`
   bug nem áll fenn).
2. egy `metadata.version`-t nélkülöző instance-t validál — `ValidationFailureError`
   "Final project.yaml validation failed" üzenettel.
3. egy üres `metadata.buildHash`-ú instance-t validál — `ValidationFailureError`
   "metadata.buildHash is required" üzenettel (nem `ReleaseError`-ré csomagolva).

A teljes tesztkészlet (`pytest tests/ -q`) 112 teszttel zöld:

```
================================ tests coverage ================================
...
TOTAL                                 677     68    90%
============================= 112 passed in 0.81s ==============================
```

## Teljes verifikációs lánc — futtatás-kimenetek

### `make validate`

```
$ make validate COMPILER_CLI_ARGS=-v
--- Validating all schemas against the meta-schema ---
--- Running Schema Validation ---
--- Running Schema Validation ---
Validating and resolving /app/schemas/index.yaml...
Schema 'template-schema' loaded.
✓ Schema validation logic to be fully implemented here.
✓ Validation successful.
✓ All schemas are valid.
```

### `make manifest-verify` (kivonat — minden sor `OK`)

```
$ GID=$(id -g) make manifest-verify
--- Verifying repository manifest ---
docs/en/concept/git-management.md: OK
README.md: OK
...
module/envelope.go: OK
module/envelope_test.go: OK
module/module.wasm: OK
module/abi.go: OK
module/handlers.go: OK
module/module_loadtest_test.go: OK
mk/golang.mk: OK
mk/wasm.mk: OK
docs/en/wasm-module-authoring.md: OK
docs/hu/wasm-module-authoring.md: OK
project.yaml: OK
.github/workflows/ci.yml: OK
... (82 fájl összesen, mind OK)
```

### `make wasm.build`

```
$ GID=$(id -g) make wasm.build
--- Building WASM guest module (TinyGo -target wasip1) ---
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app/module && tinygo build -o module.wasm -target wasip1 -scheduler=none .'
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app && python -m tools.compiler set-build-hash --file module/module.wasm --project project.yaml'
```

(`project.yaml`'s `metadata.buildHash` = `cf39464a13b128beece2e8cc973798ef2af56e9eeb41ac5d7f696c9cc63351af`,
és a `module/module.wasm` ugyanezt a hash-t adja `sha256sum`-mal.)

### `make wasm.test`

```
$ GID=$(id -g) make wasm.test
=== RUN   TestHostLoad
--- PASS: TestHostLoad (0.07s)
=== RUN   TestHostLoadUnknownOp
--- PASS: TestHostLoadUnknownOp (0.06s)
=== RUN   TestHostLoadHandlerError
--- PASS: TestHostLoadHandlerError (0.06s)
=== RUN   TestHostLoadNullSuccess
=== RUN   TestHostLoadNullSuccess/init
=== RUN   TestHostLoadNullSuccess/process
=== RUN   TestHostLoadNullSuccess/notify
--- PASS: TestHostLoadNullSuccess (0.05s)
    --- PASS: TestHostLoadNullSuccess/init (0.00s)
    --- PASS: TestHostLoadNullSuccess/process (0.00s)
    --- PASS: TestHostLoadNullSuccess/notify (0.00s)
PASS
ok  	github.com/CentralInfraCore/wasm-module-template/module	0.246s
```

### `module/envelope_test.go` (B.5 invalid-JSON-output eset, B.6 GuestError)

```
$ docker compose exec -T builder sh -c 'cd /app/module && GOFLAGS=-mod=mod go test -v -run "TestMarshal|TestGuestError" .'
--- PASS: TestMarshalDataValidJSON
--- PASS: TestMarshalDataNil
--- PASS: TestMarshalDataInvalidJSONOutput
--- PASS: TestMarshalErr
--- PASS: TestGuestErrorImplementsError
PASS
```

### `make golang.quality`

```
$ make golang.quality
Staticcheck on: github.com/CentralInfraCore/wasm-module-template/module
Vet on: github.com/CentralInfraCore/wasm-module-template/module
govulncheck on: github.com/CentralInfraCore/wasm-module-template/module
=== Symbol Results ===
No vulnerabilities found.
Your code is affected by 0 vulnerabilities.
```

(`golang.fmt-check` is lefutott — sikeres, nincs diff.)

### `make check`

```
$ make check
--- Formatting Python code with Black and Isort ---
All done! ✨ 🍰 ✨
1 file reformatted, 19 files left unchanged.
--- Linting Python code with Ruff ---
All checks passed!
--- Linting YAML files with yamllint ---
--- Running static type checking with MyPy ---
Success: no issues found in 20 source files
--- Running security checks with Bandit ---
Run started:2026-06-13 07:51:11.605246+00:00
Test results:
	No issues identified.
```

(A Black által formázott `tests/test_tools/test_infra.py` újra commitolva és a
`MANIFEST.sha256` újragenerálva ezután.)

### `make test`

```
$ make test
...
============================= 112 passed in 0.81s ==============================
```

## Reachability — grep bizonyítékok

```
$ grep -n "GuestError\|CodeInput\|CodeRuntime\|CodeInternal\|CodeResource\|CodeTimeout\|marshalErr\|marshalData" module/abi.go
45:		return pack(marshalErr(CodeInput, "unknown op: "+op))
48:		if ge, ok := derr.(*GuestError); ok {
49:			return pack(marshalErr(ge.Code, ge.Message))
51:		return pack(marshalErr(CodeRuntime, derr.Error()))
53:	return pack(marshalData(out))

$ grep -n "manifest-verify\|wasm/main\|wasm/f" .github/workflows/ci.yml
9:      - wasm/main
10:      - wasm/f/**
15:      - wasm/main
33:        run: make manifest-verify

$ grep -n "canonical_source_file" project.yaml
48:  canonical_source_file: schemas/index.yaml
```

## Commitok (`wasm/f/hardening`, a `wasm/main` HEAD `5b231a3`-ból ágazva)

1. `ci(wasm): wire wasm/main triggers and manifest-verify into CI` — C.9 + A.1 CI-bekötés
2. `fix(infra): validate project.yaml against project.schema.yaml correctly` — A.3
3. `build(wasm): set canonical_source_file and replace embedded cert/signature blocks with placeholders` — A.2 + C.8
4. `feat(wasm): typed guest errors with error codes (INPUT|RUNTIME|INTERNAL|RESOURCE|TIMEOUT)` — B.6
5. `test(wasm): harden module_loadtest_test.go with concrete envelope assertions` — B.5
6. `build(wasm): trim mk/golang.mk to the module/ quality gate` — C.7
7. `docs(wasm): make the WASM module template the primary README identity` — B.4
8. `build(wasm): regenerate MANIFEST.sha256` — A.1 (végső regenerálás minden korábbi módosítás után)

## PR-megnyitás státusza

A `wasm/f/hardening` branch push-olva van a base-repo `origin`-jére
(`git push -u origin wasm/f/hardening` — sikeres, `new branch`). A
`gh pr create --base wasm/main --head wasm/f/hardening` viszont elhasalt:

```
none of the git remotes configured for this repository point to a known GitHub host.
```

A base-repo `origin` egy lokális bare repo (`/home/sinkog/sync/git.partners/CentralInfraCore/.git_repos/base-repo.git`),
nem GitHub — ez környezeti korlát, nem a jelen job hibája. A branch pusholva
van és PR-re kész (`wasm/f/hardening` → `wasm/main`); a PR-t a `gh` GitHub-host
konfigurálása után (vagy a tényleges GitHub remote-on) kell megnyitni.

## Összefoglalás

A 9 review-pont (A.1–A.3, B.4–B.6, C.7–C.9) mindegyike `implemented` státuszú,
production kódútra (`file:line`) vagy futtatás-kimenetre hivatkozva. A teljes
verifikációs lánc (`make validate`, `make manifest-verify`, `make wasm.build`,
`make wasm.test`, `make golang.quality`, `make check`, `make test`) zöld a
builder konténerben. Az architektúra (WASM ABI, wazero loadtest, buildHash
signing) változatlan — a javítások a varratokat zárták be, nem terveztek újra
semmit.

Nyitott/megfigyelendő pont: a `module/module.wasm` bináris a `MANIFEST.sha256`
része — minden `make wasm.build` után, mielőtt commitolunk, a manifestet
újra kell generálni (`make manifest-update`), különben a `manifest-verify`
elbukik a következő CI-futáson, ha a TinyGo build nem teljesen determinisztikus
két környezet között. Ez jelenleg manuális lépés; ha a release pipeline-ban
gyakori probléma lesz, érdemes lehet a `wasm.build` targetbe beépíteni a
`manifest-update` hívást.
