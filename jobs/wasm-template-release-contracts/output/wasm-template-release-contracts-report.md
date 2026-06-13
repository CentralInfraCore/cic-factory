# wasm-template-release-contracts — riport

**Repo:** `base-repo`, branch `wasm/f/release-contracts` (← `wasm/main` @ `e06ed9c`)
**Reasoning mód:** implementation
**Státusz:** a feladat 1-3 pontja implementálva, teljes verifikációs lánc zöld.

## Előfeltétel-ellenőrzés

```
$ git log --oneline -3 origin/wasm/main
e06ed9c Merge pull request #12 from CentralInfraCore/wasm/f/contracts
019aac5 wasm: contracts hardening — rebuild-verify, ABI manifest, negative tests, contract docs
1527d05 Merge pull request #11 from CentralInfraCore/wasm/f/ci-followup
```

`origin/wasm/main` HEAD-je `e06ed9c` — megfelel az elvárt bázisnak (PR #11 + #12
mergelve). A `wasm/f/release-contracts` branch ebből indult.

---

## 1. `project.schema.yaml` igazítása + `abi.schema.yaml`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `abi.schema.yaml` létezik, és a `project.schema.yaml` `$ref`-fel hivatkozik rá | **implemented** | `project.schema.yaml:216`: `abi:\n    $ref: "abi.schema.yaml"` (lásd `grep -n '$ref' project.schema.yaml` kimenete fent). `abi.schema.yaml` (41 sor) modellezi `name`/`version`/`envelopeVersion`/`exports`/`operations`-t, `required` + `additionalProperties: false`. | `grep -n '\$ref\|abi.schema' project.schema.yaml` → `216:    $ref: "abi.schema.yaml"` | Alacsony — a `$ref` feloldását a `make validate` és a `verify-release` 1. pontja is gyakorolja (lásd alább), mindkettő zöld. |
| `abi.schema.yaml` JSON-szintaxisban íródott (.yaml kiterjesztéssel), mert a `tools.infra.load_and_resolve_schema` (NEM módosítható) `jsonref` defaultja csak `json.loads()`-szal old fel `$ref`-eket | **implemented**, dokumentált korlát | `abi.schema.yaml` teljes tartalma JSON-szintaxis (kapcsos zárójelek, `"key": value`), saját `description` mezőjében hivatkozva `tools/infra.py:73-87`-re. A korlát mindkét `release-artifact.md`-ben is dokumentálva ("abi.schema.yaml JSON szintaxisban íródott..."). | Manuálisan próbáltam YAML block-szintaxisú `abi.schema.yaml`-t — a `make validate` `JsonRefError: ... JSONDecodeError: Expecting value: line 1 column 1`-lel bukott. JSON-szintaxisra váltás után `make validate` zöld (lásd lánc lent). | Alacsony — egyetlen forrás, mindkét loader (jsonref + yaml.safe_load) olvassa. Jövőbeli szerkesztőnek emlékeznie kell rá, hogy NE írjon YAML block-szintaxist ide — ez dokumentálva van a fájlban és a release-artifact.md-ben. |
| `project.schema.yaml` modellezi a valós `project.yaml` top-level és `metadata`/`compiler_settings` kulcsait (típus + kötelezettség) | **implemented** | `project.schema.yaml` top-level: `required: [metadata, compiler_settings, abi]`, `additionalProperties: false`. `metadata` alatt új mezők: `tags`, `validatedBy` (name/version required), `createdBy` (name/email/certificate/issuer_certificate required), `build_timestamp`, `validity` (from/until), `checksum`, `sign`, `buildHash` (pattern `^([a-f0-9]{64}\|TBD)?$`), `cicSign`, `cicSignedCA` (certificate required) — mind `additionalProperties: false` a `metadata`-n. `compiler_settings` alatt új mezők: `component_name`, `canonical_source_file`, `cic_root_ca_key_name`, `vault_cert_mount`, `vault_cert_secret_name`, `vault_cert_secret_key` — `additionalProperties: false`. | `git diff wasm/main -- project.schema.yaml` (117 sor diff); `make validate` zöld a jelen `project.yaml`-on (lásd lánc). | Közepes — `additionalProperties: false` szigorítás jövőbeli `project.yaml` mezőkkel ütközhet, ha valaki új top-level/metadata/compiler_settings kulcsot ad hozzá schema-frissítés nélkül. Ezt a `make validate` és `verify-release` 1. pontja azonnal elkapja (fail-fast), tehát a kockázat detektálható, nem csendes drift. |
| `make validate` zöld marad a jelenlegi `project.yaml`-on a schema-bővítés után | **implemented** | Lásd "Teljes verifikációs lánc" szakasz, `make validate` → `EXIT=0`. | `make validate` futtatás-kimenet (lánc lent) | Alacsony |

### Konkrét before/after schema-validáció (Tiltott rövidítések kötelező pont)

Az alábbi 5 eset mind a régi (`wasm/main` @ `e06ed9c`-beli) `project.schema.yaml`-lal,
mind az új (ez a job) `project.schema.yaml`+`abi.schema.yaml`-lal validálva, a valós
`project.yaml`-ból mutált instance-okon, `jsonschema.validate` + `jsonref.JsonRef.replace_refs`-szel
(ugyanaz a feloldási mechanizmus, mint `tools.infra.load_and_resolve_schema`):

```
=== Baseline: real project.yaml ===
  [OLD schema] PASS
  [NEW schema] PASS

=== Case A: project.yaml missing abi: block entirely ===
  [OLD schema] PASS
  [NEW schema] FAIL: 'abi' is a required property (path: [])
  -> NEW SCHEMA CATCHES THIS

=== Case B: metadata.buildHash = 'not-a-real-hash' (not 64-hex/TBD) ===
  [OLD schema] PASS
  [NEW schema] FAIL: 'not-a-real-hash' does not match '^([a-f0-9]{64}|TBD)?$' (path: ['metadata', 'buildHash'])
  -> NEW SCHEMA CATCHES THIS

=== Case C: metadata has unknown key 'ownr' (typo of 'owner') ===
  [OLD schema] PASS
  [NEW schema] FAIL: Additional properties are not allowed ('ownr' was unexpected) (path: ['metadata'])
  -> NEW SCHEMA CATCHES THIS

=== Case D: abi: block missing required 'operations' ===
  [OLD schema] PASS
  [NEW schema] FAIL: 'operations' is a required property (path: ['abi'])
  -> NEW SCHEMA CATCHES THIS

=== Case E: project.yaml has unknown top-level key 'unexpected_top_level_key' ===
  [OLD schema] PASS
  [NEW schema] FAIL: Additional properties are not allowed ('unexpected_top_level_key' was unexpected) (path: [])
  -> NEW SCHEMA CATCHES THIS
```

Mind az 5 eset azt mutatja, hogy a régi schema átengedte volna a hibás
`project.yaml`-t (hiányzó `abi:` blokk, érvénytelen `buildHash`, elgépelt
mezőnevek, hiányzó `abi.operations`, ismeretlen top-level kulcs), az új
schema viszont elbukik rajtuk. A baseline (valós `project.yaml`) mindkét
schema-val PASS — a szigorítás nem tört el élő tartalmat.

A `additionalProperties: false` szigorítást **csak** a `metadata`,
`compiler_settings` és `abi` blokkokon alkalmaztam (a top-level mellett),
mert ezek azok a blokkok, ahol a `project.yaml` jelenlegi tartalma teljesen
ismert és felsorolt; a `release:`, `maintenance:`, `contacts:`, `links:`
blokkokat **nem** szigorítottam (`additionalProperties` nincs rajtuk
beállítva), mert ezek opcionális/jövőbeli blokkok, és a TBD/template
placeholder mezők (`createdBy`, `cicSign`, `validatedBy.checksum`, `checksum`,
`sign`, `cicSignedCA`) típusát szándékosan `string`/`object`-en hagytam
formátum-megkötés nélkül (csak `buildHash`-nek van regex pattern-je, mert
annak van egyértelmű "vagy 64-hex, vagy TBD, vagy üres" alakja).

---

## 2. `tools/verify_release.py` + `make verify-release`

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `make verify-release` target létezik, a `Makefile`-ban | **implemented** | `Makefile:115-117`:<br>`verify-release: ## Offline release-readiness check: ...`<br>`@docker compose exec -T builder python -m tools.verify_release` | `grep -n -A3 "^verify-release:" Makefile` | Alacsony |
| 1. pont: `project.yaml` schema-validáció (`abi:` is, `abi.schema.yaml` `$ref`-en keresztül) | **implemented** | `tools/verify_release.py: check_schema()` (28-69. sor) — `load_and_resolve_schema`/`load_yaml`-t importálja `tools.infra`-ból (38. sor), NEM duplikálja. | `make verify-release` kimenet: `[PASS] 1. project.yaml schema validation` | Alacsony |
| 2. pont: `module/module.wasm` sha256 == `metadata.buildHash`, a `wasm.rebuild-verify`-jal **azonos** TinyGo-hívással, scratch helyre | **implemented**, reuse (nem duplikáció — explicit indoklás lent) | `tools/verify_release.py: check_build_hash()` (72-122. sor): `tinygo build -o <tempdir>/module.wasm -target wasip1 -scheduler=none .`, `cwd=module_dir` — **megegyezik** `mk/wasm.mk:39`-cel (`tinygo build -o /tmp/module.wasm.rebuild-verify -target $(WASM_TARGET) -scheduler=none .`). `tempfile.TemporaryDirectory()`-t használ (B108 bandit fix). | `make verify-release` kimenet: `[PASS] 2. module.wasm buildHash` `rebuilt sha256 == metadata.buildHash (cb069c1192...)` | Közepes — **nem** `make wasm.rebuild-verify`-t hívja meg (docker-in-docker hiánya miatt, lásd "Reuse vs. duplikáció" lent), hanem ugyanazt a `tinygo build` parancsot futtatja újra. Ha `mk/wasm.mk`-ban a TinyGo flag-ek megváltoznak, a két hely szétdriftelhet — ezt egyik `make check`/CI lépés sem detektálja automatikusan. Dokumentált, de jövőbeli karbantartási teher. |
| 3. pont: `abi.exports` == `module.wasm` exportok, a `module/abi_manifest_test.go` logikájával | **implemented**, reuse (nem duplikáció) | `tools/verify_release.py: check_abi_exports()` (125-146. sor): `go test -run TestHostLoadABIManifestExportsPresent -v .` a `module/` dir-ben — **ugyanazt** a `TestHostLoadABIManifestExportsPresent`-et futtatja (`module/abi_manifest_test.go:83-92`), nincs külön Go/Python re-implementáció. | `make verify-release` kimenet: `[PASS] 3. abi.exports vs module.wasm exports` `TestHostLoadABIManifestExportsPresent passed (go test).` | Alacsony — ez a legszorosabb reuse: tényleges meglévő tesztet futtat, nincs külön logika a fenntartáshoz. |
| 4. pont: `MANIFEST.sha256` ellenőrzés | **implemented**, reuse | `tools/verify_release.py: check_manifest()` (149-170. sor): `sha256sum -c MANIFEST.sha256` — megegyezik `Makefile:95`-tel (`manifest-verify` target: `sha256sum -c MANIFEST.sha256`). | `make verify-release` kimenet: `[PASS] 4. MANIFEST.sha256 integrity` `sha256sum -c MANIFEST.sha256 OK.` | Alacsony |
| 5. pont: provenance mezők (`createdBy`, `validatedBy.checksum`, `checksum`, `sign`, `cicSign`, `cicSignedCA.certificate`) `OK`/`TBD`/`MISSING` riportolása, kriptográfia NÉLKÜL | **implemented** | `tools/verify_release.py: check_provenance()` (173-232. sor) — `field_status()` `MISSING`/`TBD`/`OK`-t ad vissza string-alapon, **nincs** Vault/aláírás-hívás. Output explicit megjegyzéssel: "this step does not verify any cryptographic signature (no Vault access)". | `make verify-release` kimenet: `[PASS] 5. provenance fields` + 7 sor `TBD` + a NOTE szöveg | Alacsony — ez **csak informatív**, nem gate-eli az exit kódot (lásd `main()` 251-269. sor: `results` listában csak az 1-4. pont van, `provenance_ok` külön). |
| 1-4. pont gate-eli az exit kódot, non-zero ha bármelyik `FAIL` | **implemented** | `tools/verify_release.py: main()` (235-276. sor): `results = [check_schema(...), check_build_hash(...), check_abi_exports(...), check_manifest(...)]`; `if all(results): return 0` ... `return 1`. | Demonstráltam: a `MANIFEST.sha256` szándékos stale állapotában (a `tools/verify_release.py` black/isort-reformat UTÁN, `manifest-update` ELŐTT futtatva) a `make verify-release` `[FAIL] 4. MANIFEST.sha256 integrity` + `verify-release: FAIL` + `make: *** [Makefile:117: verify-release] Error 1` + `EXIT=2` kimenetet adott — lásd alább a "FAIL-demonstráció" blokkot. | Alacsony |
| `tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py` **nem módosult** | **implemented** | `git diff wasm/main --stat` — a 10 megváltozott fájl között NINCS `tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py`. | `git diff --stat HEAD` kimenet (lásd lent), `tools/verify_release.py` csak `from .infra import ConfigurationError, load_and_resolve_schema, load_yaml`-t importál (38. sor) — nem módosítja a `tools/infra.py`-t. | Alacsony |
| `make check` (bandit/mypy/black/isort/yamllint) zöld a `tools/verify_release.py`-ra | **implemented** | bandit: B404 (`subprocess` import) → `# nosec`; B108 (hardcoded `/tmp` útvonal) → `tempfile.TemporaryDirectory()`-ra cserélve; B603/B607 (subprocess shell nélkül / partial path `sha256sum`) → `# nosec` a 3 `subprocess.run()`-on, követve a `tools/releaselib/git_service.py`-ben már meglévő konvenciót. | `make check` kimenet: `Success: no issues found in 22 source files` + bandit `Total issues (by severity): Undefined: 0, Low: 0, Medium: 0, High: 0` + `EXIT=0` (lásd lánc) | Alacsony |

### FAIL-demonstráció (4. pont, MANIFEST.sha256)

A `tools/verify_release.py` tartalma megváltozott (`make check` black/isort
reformat) a legutóbbi `make manifest-update` UTÁN. Ez a tényleges
`MANIFEST.sha256` ↔ working tree drift, amit a `verify-release` 4. pontja
elkapott:

```
$ make verify-release
...
[FAIL] 4. MANIFEST.sha256 integrity
       ...
       tools/verify_release.py: FAILED
       ...
       sha256sum: WARNING: 1 computed checksum did NOT match
[PASS] 5. provenance fields
...
verify-release: FAIL — see [FAIL] entries above.
make: *** [Makefile:117: verify-release] Error 1
verify-release EXIT=2
```

`make manifest-update` + `git add -A` után a `make verify-release` minden
pontja PASS (lásd "Teljes verifikációs lánc" lent). Ez a `verify-release`
4. pontjának tényleges FAIL→PASS ciklusa, valós driften.

### Reuse vs. duplikáció — miért nem `docker compose exec` / `make wasm.rebuild-verify` hívás

A `verify_release.py` maga a `builder` containeren belül fut
(`make verify-release` → `docker compose exec -T builder python -m
tools.verify_release`). A `make wasm.rebuild-verify` és `make
manifest-verify` viszont a **host**-on futó `make`/`docker compose`
parancsok, amelyek a containert hívják meg kívülről — a containerből nem
hívhatók meg ugyanígy (nincs docker-in-docker, és a `make`/`docker
compose` binárisok sincsenek a `builder` image-ben). Ezért a
`verify_release.py` nem `make wasm.rebuild-verify`-t/`make
manifest-verify`-t hív meg, hanem **ugyanazokat a végső külső
parancsokat** futtatja (`tinygo build` azonos flag-ekkel, `sha256sum -c`),
illetve a 3. pontnál a **tényleges meglévő Go tesztet** (`go test -run
TestHostLoadABIManifestExportsPresent`) — ez az egyetlen védhető "single
source of truth ugyanazon külső eszköz-hívással" megközelítés a
`tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py`
módosítása és docker-in-docker nélkül. A drift-kockázatot (2. pont,
TinyGo flag-ek) explicit dokumentáltam fent.

---

## 3. Dokumentáció (README + release-artifact.md)

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `README.md` / `README.hu.md` Makefile Commands bullet `make verify-release`-hez | **implemented** | `README.md`: `- make verify-release: Offline release-readiness check — project.yaml schema (incl. abi:), module.wasm buildHash, ABI exports, MANIFEST.sha256, and provenance field status. See release-artifact.md.`<br>`README.hu.md`: magyar megfelelője. | `git diff wasm/main -- README.md README.hu.md` | Alacsony |
| `docs/contracts/{en,hu}/release-artifact.md` — `verify-release` mostantól **implemented**, dokumentálva mit ellenőriz 1-5 + mit NEM | **implemented** | Új szekciók: "project.yaml schema: abi: block and provenance metadata" + "verify-release: offline release-readiness check" (+ "What verify-release does NOT check" alszekció). A "Target state: provable signed release bundle" szekció frissítve: (a)-(c) implementált, (d) (kriptográfiai aláírás-ellenőrzés) TBD. Mindkét nyelven (`en`/`hu`) párhuzamosan. | `git diff wasm/main -- docs/contracts/en/release-artifact.md docs/contracts/hu/release-artifact.md` (98 / 103 sor diff) | Alacsony |
| `make docs.link-check` zöld az új doksi-szekciók után | **implemented** | — | `make docs.link-check` kimenet: `docs.link-check: OK — all internal markdown links resolve.` `EXIT=0` (lásd lánc) | Alacsony |

---

## Amit a `make verify-release` NEM ellenőriz (kötelező lista)

- **Nincs kriptográfiai aláírás-ellenőrzés.** Az 5. pont csak azt jelenti
  `OK`/`TBD`/`MISSING`-ként, hogy `createdBy`/`cicSign`/`cicSignedCA`/`sign`/
  `checksum`/`validatedBy.checksum` jelen van-e a `project.yaml`-ban, vagy
  `"TBD"`/hiányzik — **nem hív Vault-ot**, **nem ellenőriz tanúsítványláncot**,
  **nem ellenőriz semmilyen kriptográfiai aláírást**. **A `verify-release`
  PASS-a NEM jelenti, hogy a commit egy megbízható CIC kulccsal van aláírva.**
- **Nincs `release:` blokk (`repository_tree_hash`, `signing_metadata`,
  `digest`) ellenőrzés** — ez a `make release`/`tools/finalize_release.py`
  hatóköre, nem ebben a jobban.
- **Nincs hálózati/Vault hozzáférés** — szándékosan, hogy CI-ban és
  Vault-hitelesítő adatok nélküli fejlesztői gépen is működjön.
- **Nincs `.github/workflows/ci.yml`-be bekötés** ebben a jobban. A
  `verify-release` egy *release-készenységi* gate (egy `make release` futás
  előkészítésekor releváns, amikor `metadata.buildHash` és a teljes
  `project.yaml` már a végállapotot tükrözi), nem egy minden push-ra futó
  ellenőrzés, mint a `wasm.rebuild-verify`/`wasm.test`/`manifest-verify` (ezek
  már be vannak kötve a CI-ba, lásd `release-artifact.md` "buildHash"
  szekció). Egy jövőbeli job eldöntheti, hogy/hová kötné be CI step-ként
  (pl. csak release branch-eken) — ez dokumentálva van mindkét
  `release-artifact.md`-ben.
- **`TBD` az 5. pontban elvárt és nem bukás** egy template/unreleased
  `project.yaml`-on (jelen állapot) — `MISSING` lenne a séma-szintű hiba
  (amit az 1. pont elkapna).

**Összefoglalva: a `verify-release: PASS` azt bizonyítja, hogy (a) a
`project.yaml` struktúrája (incl. `abi:`) megfelel a dokumentált schemának,
(b) a commitolt `module.wasm` reprodukálható a forrásból és megfelel a
deklarált `buildHash`-nek, (c) a deklarált ABI exportok megfelelnek a
binárisnak, (d) semmilyen más tracked fájl nem driftelt váratlanul. NEM
bizonyítja, hogy a release Vault-tal alá van írva, vagy hogy a `release:`
blokk (signing metadata) helyes/teljes — ez release-ready-hez még szükséges,
de itt nincs ellenőrizve.**

---

## Teljes verifikációs lánc (builder container, `COMPOSE_PROJECT_NAME=wasm-release-contracts`)

Minden lépés a végső, post-bandit-fix, post-manifest-update állapoton futott
(`tools/verify_release.py` black/isort-reformatált + `# nosec`/`tempfile`
javításokkal, `MANIFEST.sha256` ennek megfelelően frissítve).

### `make validate`
```
--- Validating all schemas against the meta-schema ---
EXIT=0
```

### `make manifest-verify`
```
... (minden tracked fájl) ... : OK
manifest-verify EXIT=0
```

### `make wasm.build`
```
--- Building WASM guest module (TinyGo -target wasip1) ---
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app/module && tinygo build -o module.wasm -target wasip1 -scheduler=none .'
docker compose exec -T builder sh -eu -o pipefail -c \
	'cd /app && python -m tools.compiler set-build-hash --file module/module.wasm --project project.yaml'
EXIT=0
```
(`git status --porcelain | grep -i wasm` → nincs diff a `module/module.wasm`-on
vagy `project.yaml metadata.buildHash`-en — a build reprodukálható, a
commitolt artifact már a friss build eredménye volt.)

### `make wasm.rebuild-verify`
```
rebuilt sha256:        cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b
project.yaml buildHash: cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b
OK: rebuild matches metadata.buildHash
EXIT=0
```

### `make wasm.test`
```
--- PASS: TestHostLoad (0.07s)
--- PASS: TestHostLoadUnknownOp (0.06s)
--- PASS: TestHostLoadHandlerError (0.07s)
--- PASS: TestHostLoadNullSuccess (0.06s)
    --- PASS: TestHostLoadNullSuccess/init (0.00s)
    --- PASS: TestHostLoadNullSuccess/process (0.00s)
    --- PASS: TestHostLoadNullSuccess/notify (0.00s)
PASS
ok  	github.com/CentralInfraCore/wasm-module-template/module	0.629s
EXIT=0
```
(Megj.: `TestHostLoadABIManifestExportsPresent` is ennek a `go test` futásnak
a része, és a `verify-release` 3. pontja is külön futtatja — lásd lent.)

### `make verify-release`
```
--- Verifying release artifact (project.yaml, module.wasm, MANIFEST.sha256) ---
[PASS] 1. project.yaml schema validation
       project.yaml valid against project.schema.yaml (abi: via abi.schema.yaml).
[PASS] 2. module.wasm buildHash
       rebuilt sha256 == metadata.buildHash (cb069c11921ff1f8fe448a825c92683289b5f1a92db94e0cd910c1815ceff58b).
[PASS] 3. abi.exports vs module.wasm exports
       TestHostLoadABIManifestExportsPresent passed (go test).
[PASS] 4. MANIFEST.sha256 integrity
       sha256sum -c MANIFEST.sha256 OK.
[PASS] 5. provenance fields
       metadata.createdBy.name: TBD
       metadata.createdBy.certificate: TBD
       metadata.validatedBy.checksum: TBD
       metadata.checksum: TBD
       metadata.sign: TBD
       metadata.cicSign: TBD
       metadata.cicSignedCA.certificate: TBD

       NOTE: this step does not verify any cryptographic signature (no Vault access). TBD fields are expected in a template/unreleased project.yaml and do not fail this check; a MISSING field indicates the metadata key itself is absent (schema violation, caught separately by check 1).

verify-release: PASS (checks 1-4). See check 5 for provenance status.
verify-release EXIT=0
```

### `make golang.quality`
```
govulncheck on: github.com/CentralInfraCore/wasm-module-template/module
=== Symbol Results ===
No vulnerabilities found.
Your code is affected by 0 vulnerabilities.
This scan also found 2 vulnerabilities in packages you import and 35
vulnerabilities in modules you require, but your code doesn't appear to call
these vulnerabilities.
EXIT=0
```

### `make check`
```
Success: no issues found in 22 source files
--- Running security checks with Bandit ---
...
Test results:
	No issues identified.
...
Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 0
EXIT=0
```

### `make test`
```
============================= 112 passed in 0.90s ==============================
EXIT=0
```
(Eredetileg 3 teszt elbukott: `TestValidateFinalProjectYamlRealSchema::*`, mert a
fixture csak `project.schema.yaml`-t másolta a tmp project root-ba, az új
`abi.schema.yaml` `$ref`-jét nem találta. Javítás: `tests/test_tools/test_infra.py`
fixture-je most az `abi.schema.yaml`-t is másolja; a `VALID_PROJECT_YAML_INSTANCE`
kapott egy `abi:` blokkot (top-level `required: [..., abi]` miatt) és a
`buildHash` 64 hex karakteresre lett javítva (`^([a-f0-9]{64}|TBD)?$` pattern
miatt — ez maga is egy schema-szigorítás okozta, korábban "véletlenül" átmenő
hibás teszt-fixture javítása).)

### `make docs.link-check`
```
--- Checking internal documentation links ---
docs.link-check: OK — all internal markdown links resolve.
EXIT=0
```

---

## Megváltozott fájlok (`git diff wasm/main --stat`)

```
 MANIFEST.sha256                       |  23 ++-
 Makefile                              |  10 +-
 README.hu.md                          |   1 +
 README.md                             |   1 +
 abi.schema.yaml                       |  41 +++++ (new)
 docs/contracts/en/release-artifact.md |  98 ++++++++++--
 docs/contracts/hu/release-artifact.md | 103 +++++++++++--
 project.schema.yaml                   | 117 +++++++++++++-
 tests/test_tools/test_infra.py        |  26 +++-
 tools/verify_release.py               | 276 ++++++++++++++++++++++++++++++++ (new)
 10 files changed, 654 insertions(+), 42 deletions(-)
```

`tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py` **nincsenek**
a listában — nem módosultak, ahogy a feladat előírta.

---

## Nem ebben a jobban / blokkolt elemek

- **Nem merült fel blokkoló kérdés** a `wasm-release-pipeline-audit` hatókörével
  kapcsolatban. A `tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py`
  kódját nem kellett módosítani vagy érdemben átvilágítani — a `verify_release.py`
  csak két függvényt importál a `tools.infra`-ból (`load_and_resolve_schema`,
  `load_yaml`), amelyek már léteztek és stabilak.
- A canonical release path (`make release VERSION=X.Y.Z`, három-fázisú
  prepare/build-gap/finalize) és a `schemas/main`-ből örökölt 3-tier schema
  backbone kérdése továbbra is a `wasm-release-pipeline-audit` job hatóköre —
  ezt a jobot nem érintette és nem oldotta meg, ahogy elő volt írva.
- A `verify-release` CI-ba kötése **nem történt meg** ebben a jobban —
  dokumentált indoklással (lásd "Amit NEM ellenőriz" szakasz) a
  `docs/contracts/{en,hu}/release-artifact.md`-ben.

---

## Definition of Done — checklist

- [x] `wasm/f/release-contracts` branch a `wasm/main`-ből (`e06ed9c`), minden munka ott
- [x] `abi.schema.yaml` létezik, `project.schema.yaml` rá `$ref`-el (`project.schema.yaml:216`)
- [x] `project.schema.yaml` a valós `project.yaml` mezőit modellezi (típus + kötelezettség)
- [x] `make validate` zöld a jelenlegi `project.yaml`-on
- [x] `tools/verify_release.py` + `make verify-release` — 1-5 pont ellenőrizve, futtatás-kimenettel
- [x] README + `docs/contracts/release-artifact.md` frissítve (en+hu)
- [x] teljes verifikációs lánc zöld a builder konténerben, kimenetek idézve
- [ ] PR megnyitva (`wasm/f/release-contracts` → `wasm/main`) — lásd alább
- [x] report + claim-evidence tábla a `feature/wasm-template-release-contracts`-on pusholva
- [x] `tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py` nem módosult (`git diff --stat` ellenőrizve)

## Git / PR státusz

base-repo: `wasm/f/release-contracts` branch létrehozva `wasm/main` (`e06ed9c`)-ből,
minden módosítás commitolva és pusholva ide. A `gh pr create --base wasm/main
--head wasm/f/release-contracts` futtatása a következő lépés (vagy a riport
push-a után, vagy ha a `gh`/remote hozzáférés a job-környezetben korlátozott,
az orchestrátor nyitja meg a PR-t a pushed branch-ből).
