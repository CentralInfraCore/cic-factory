# wasm-release-pipeline-audit — Riport

Reasoning mód: **audit** (feltérképezés, nincs implementáció).
Vizsgált bázis: `origin/wasm/main` @ `e06ed9c` (PR #11+#12 mergelve, ellenőrizve
`git log --oneline -3 origin/wasm/main`-nel). `CIC-Schemas` klón: `main` @
`27925c5`. Mindkét repo `git status` clean a riport végén, nincs commit/push
beléjük.

---

## TL;DR

A külső review gyanúja **részben megalapozott, de a kockázat más helyen van,
mint amire a review mutatott**:

- `tools/finalize_release.py` valóban tartalmaz egy `checksum == buildHash`
  ellenőrzést, ami konceptuálisan kérdéses (két különböző bizonyítékot
  hasonlít egyenlőségre) — **de ez a kód `make`/CI útvonalon sehonnan nincs
  hívva, csak a saját tesztje importálja**. Dead code a production
  pipeline-on.
- `tools/infra.py` (ami a tényleges, futó `make release` lánc) **nem**
  hasonlítja össze `checksum`-ot és `buildHash`-t — két különálló mezőként
  kezeli, amit egyetlen aláírás fed le (`_resign_with_build_hash`,
  `infra.py:352-385`). Ez a réteg konceptuálisan helyes.
- A valódi, eddig fel nem ismert probléma: a base-repo (`wasm/main`)
  `tools/infra.py` / `tools/compiler.py` / `tools/finalize_release.py` /
  `project.schema.yaml` **a 2025-12-02-i (`0454bb0`) pre-schemalib állapotot
  tartalmazzák**, miközben a `schemas/main` (`CIC-Schemas`) 2026-03-21-én
  (`2ec57c0`) egy `schemalib`-alapú, refaktorált architektúrára váltott. A
  2026-06-12-i `450ac0c` "inherit schemas/main release backbone" commit
  **nem érintette** ezt a négy fájlt — csak docs/README/Makefile-cheatsheet/
  `schemas/index.yaml`/`tools/release.sh` stb. került át. A `wasm/main`
  release-backbone-ja kb. **fél évvel régebbi**, mint a `schemas/main`
  jelenlegi állapota, az "inherit" commit ígérete ellenére.

---

## 1. `finalize_release.py` vs `infra.py` — checksum/buildHash

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `finalize_release.py` egyenlőségi `checksum == buildHash` ellenőrzést végez | **implemented** (kódban él) | `tools/finalize_release.py:188-201`:<br>`checksum = metadata.get("checksum")`<br>`build_hash = metadata.get("buildHash")`<br>`if checksum != build_hash: raise ValueError("Validation failed: 'checksum' and 'buildHash' do not match!")` | `Read tools/finalize_release.py` | Konceptuálisan félrevezető elnevezés/komment ("Validating checksum against buildHash") — de l. lent: nincs production call-site |
| `finalize_release.py` nincs production útvonalon hívva | **implemented** (dead code, igazolt) | `grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` → **0 találat**. Egyetlen import: `tests/test_tools/test_finalize_release.py:12: from tools import finalize_release` (mock-olt Vault, unit teszt). A fájl maga is `# FIXME: This script is a temporary solution...` (finalize_release.py:8-15) | `grep -rn "finalize_release" --include="*" .` (kizárva `.git/`) | **dead code a CI/Makefile láncban** — nem keverhető a "implemented és aktív" státusszal |
| `infra.py` **nem** hasonlítja össze `checksum`-ot és `buildHash`-t egyenlőségre | **implemented**, aktív | `infra.py:246-248`: `checksum = get_sha256_hex(spec_bytes)` ahol `spec_bytes = to_canonical_json(source_data["spec"])` — ez a **forrás-spec** (`schemas/index.yaml` `spec` blokkjának) hash-e.<br>`infra.py:297`: `"buildHash": ""` — placeholder a developer-prep fázisban, később `make wasm.build`/`wasm.buildhash` tölti ki `module.wasm` sha256-jával.<br>`infra.py:352-356` (`_resign_with_build_hash` docstring): *"a single signature binds source-spec checksum + binary buildHash together (provenance + integrity in one signature)"* — explicit nem-egyenlőségi modell.<br>`infra.py:196-200` (`_validate_final_project_yaml`): csak azt követeli meg, hogy `buildHash` **nem üres**, egyenlőségi ellenőrzés nincs. | `Read tools/infra.py` 180-410 | Nincs — ez a réteg a reviewer által elvárt "két külön bizonyíték, egy aláírás" modellt implementálja |
| `infra.py` production call-site igazolva | **implemented** | `Makefile:82`: `make release VERSION=...` → `python -m tools.compiler release ...` → `tools/compiler.py:9`: `from .infra import ReleaseManager`; `tools/compiler.py:200`: `manager = ReleaseManager(...)`; `tools/compiler.py:214-215`: `elif args.command == "release": manager.run_release_close(...)` | `grep -n "infra\.\|ReleaseManager" Makefile mk/*.mk .github/workflows/*.yml tools/compiler.py` | — |

**Konklúzió 1. ponthoz:** A két fájl **nem ugyanazt a kontraktust** képviseli.
`finalize_release.py` egy elvetett/elavult (de törlésre még nem jelölt)
egyenlőségi modellt tartalmaz a `checksum`/`buildHash` mezőkre — ez **azonos
azzal a konceptuális hibával, amire a külső reviewer rámutatott** (forrás-spec
checksum ≠ bináris buildHash, az egyenlőség véletlen lenne). De ez a réteg
**nincs aktív pipeline-elem** — a tényleges `make release` láncot `infra.py`
futtatja, ami a két mezőt helyesen, külön bizonyítékként kezeli egy közös
aláírás alatt.

---

## 2. `project.schema.yaml` / release-mezők eredete — `schemas/main` lineage

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| base-repo `tools/infra.py`/`compiler.py`/`finalize_release.py`/`project.schema.yaml` a pre-`schemalib` (2025-12-02) állapotot tartalmazzák | **implemented** (igazolt commit-history) | `git -C base-repo log --diff-filter=A --oneline -- tools/infra.py` → `0454bb0 rebuild Makefile devel` (2025-12-02). Ugyanez a commit hozta be `finalize_release.py`/`compiler.py`/`project.schema.yaml`-t is (egy csomagban). | `git log --diff-filter=A --oneline -- tools/infra.py`, `git show -s --format="%ci %s" 0454bb0` |  |
| `schemas/main` (`CIC-Schemas`) 2026-03-21-én `schemalib`-alapú refaktort kapott, ami `infra.py`-t 509→84 sorra csökkentette és kiemelte `tools/schemalib/{artifact,loader,validator}.py`-be | **implemented** `CIC-Schemas/main`-en | `git -C CIC-Schemas log --oneline --all -- tools/infra.py` → `2ec57c0 feat: unified compiler architecture — schemalib, repo_type routing, docs` (2026-03-21). `diff CIC-Schemas/tools/infra.py base-repo/tools/infra.py` → 425 soros diff; CIC-Schemas oldalon `from .schemalib.artifact import (build_signing_payload, compute_spec_checksum, generate_signed_artifact, parse_certificate_info)` és `from .schemalib.validator import ValidationFailureError, get_validator_schema, run_validation` — ezek a függvények base-repo `infra.py`-jában inline-ban élnek (`to_canonical_json`, `get_sha256_hex`, `_parse_certificate_info`, `load_and_resolve_schema` mind a fájlban, nem külön modulban). | `diff CIC-Schemas/tools/infra.py base-repo/tools/infra.py` |  |
| `CIC-Schemas/project.schema.yaml` `compiler_settings` blokkja deklarálja `repo_type` (enum: `schema`/`workflow`/`module`) + modul-specifikus mezőket (`canonical_source_file`, `component_name`, `main_branch`, `dependencies_dir`, `release_dir`, `cic_root_ca_key_name`, `vault_cert_mount`, `vault_cert_secret_name`, `vault_cert_secret_key`, `cic_root_ca_secret_name`, `validity_days`); base-repo `project.schema.yaml` `compiler_settings.properties` csak 4 mezőt deklarál (`meta_schemas_dir`, `source_dir`, `meta_schema_file`, `vault_key_name`) | **implemented** mindkét oldalon, de **divergens** | `CIC-Schemas/project.schema.yaml:86-141` (`compiler_settings`, `required: [repo_type, meta_schemas_dir, source_dir, meta_schema_file, vault_key_name]`, majd `repo_type` enum + a felsorolt mezők) vs. `base-repo/project.schema.yaml:86-103` (`compiler_settings`, `required: [meta_schemas_dir, source_dir, meta_schema_file, vault_key_name]`, csak 4 property). `diff CIC-Schemas/project.schema.yaml base-repo/project.schema.yaml` → a hiányzó blokk a `<` (CIC-Schemas) oldalon. | `diff CIC-Schemas/project.schema.yaml base-repo/project.schema.yaml`, `Read` mindkét fájl 1-110. sor |
| base-repo `project.yaml`-ban már HASZNÁLT `compiler_settings` mezők (`component_name`, `canonical_source_file`, `vault_cert_mount`, `vault_cert_secret_name`, `vault_cert_secret_key`, `cic_root_ca_key_name`) formálisan **nincsenek deklarálva** a base-repo `project.schema.yaml`-ban | **implemented**, de schema-rés | `base-repo/project.yaml` `compiler_settings:` blokk: `component_name: wasm-module`, `canonical_source_file: schemas/index.yaml`, `vault_cert_mount: cic-my-sign-key`, `vault_cert_secret_name: crt`, `vault_cert_secret_key: bar`, `cic_root_ca_key_name: cic-root-ca-key` — ezekre a `base-repo/project.schema.yaml:86-103` `compiler_settings.properties` nem ad explicit definíciót (csak a CIC-Schemas oldali, frissebb schema deklarálja). `additionalProperties` nincs `false`-ra állítva, így a `jsonschema.validate` **nem buktatja el** ezeket — de a kontraktus dokumentálatlan/eltérő a `schemas/main`-től. | `grep -n "compiler_settings" -A12 base-repo/project.yaml`, `grep -n "additionalProperties" base-repo/project.schema.yaml` (nincs találat) |
| `450ac0c` ("feat(wasm): inherit schemas/main release backbone") **nem** módosította `tools/infra.py`/`tools/compiler.py`/`tools/finalize_release.py`/`project.schema.yaml`-t, a commit-message ígérete ellenére | **implemented**, igazolt | `git -C base-repo show --stat 450ac0c` → érintett fájlok: `.editorconfig`, `README.{hu,md}`, `configs/schemas/.gitkeep`, `docs/{en,hu}/{makefile-cheatsheet,workflow}.md`, `md.meta.schema.yaml`, `mk/infra.mk` (+4 sor), `requirements.{in,txt}`, `schemas/index.yaml`, `source/.gitkeep`, `tools/__init__.py`, `tools/init_from_template.sh`, `tools/release.sh` — **`tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py`, `project.schema.yaml` nincs a listában**. | `git -C base-repo show --stat 450ac0c` |  |

**Konklúzió 2. ponthoz:** A `wasm/main` release-backbone-ja **nem divergál
előre** (nincs wasm-specifikus bővítés, ami ellentmondana `schemas/main`-nek)
— hanem **el van maradva** kb. 6 hónapnyi `schemas/main` refaktortól
(`schemalib`, `repo_type` routing, bővített `project.schema.yaml`). A
`450ac0c` "inherit" commit ezt a réteget nem hozta át, csak a docs/template
réteget. A `wasm/main` `project.yaml` már most is olyan `compiler_settings`
mezőket használ (`canonical_source_file`, `vault_cert_mount`, stb.), amelyeket
a saját, elavult `project.schema.yaml`-ja nem deklarál — csak azért nem bukik
a validáció, mert a schema permisszív (`additionalProperties` nincs
korlátozva).

---

## 3. Canonical release path — mai tényleges állapot

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| `make release VERSION=X.Y.Z` → `tools.compiler release` → `infra.ReleaseManager` — ez a **futó** release-validációs lánc | **implemented** | `Makefile:82`: `builder python -m tools.compiler release --version $(VERSION) $(COMPILER_CLI_ARGS)`; `tools/compiler.py:9,200,214-215` | `grep -n "tools.compiler\|ReleaseManager" Makefile tools/compiler.py` |  |
| `make validate` → `tools.compiler validate` → `manager.run_validation()` | **implemented** | `Makefile:69`: `builder python -m tools.compiler validate $(COMPILER_CLI_ARGS)`; `tools/compiler.py:209-212` | ua. |  |
| `wasm.buildhash` / `wasm.rebuild-verify` a "build-gap" fázist fedik, `metadata.buildHash`-t számolnak/ellenőriznek `module.wasm`-ból | **implemented** | `mk/wasm.mk:26` (`wasm.buildhash` → `tools.compiler set-build-hash --file $(WASM_OUT) --project project.yaml`), `mk/wasm.mk:36-52` (`wasm.rebuild-verify`: rebuild scratch path, `sha256sum`, összevetés `grep -E "^[[:space:]]*buildHash:"`-pel kinyert értékkel) | `Read mk/wasm.mk` |  |
| `docs/contracts/en/release-artifact.md` explicit a `tools/infra.py` három-fázisú modelljére épít (prepare / build-gap / finalize), nem önálló/divergáló réteg | **implemented** (dokumentum szinten) | `docs/contracts/en/release-artifact.md:58-72`: *"`tools/infra.py` / `tools/compiler.py` implement a three-phase release process (`make release VERSION=X.Y.Z`): 1. prepare ... 2. build-gap ... 3. finalize — checksum and Vault-sign the release."* és *"This template's `wasm.build` / `wasm.rebuild-verify` / ABI-manifest checks fit into the **build-gap** phase"* | `Read docs/contracts/en/release-artifact.md` 58-99 |  |
| `docs/contracts/en/release-artifact.md` "Target state" (buildHash + ABI manifest + MANIFEST.sha256 + signed bundle) explicit **a meglévő invariánsokra épül**, nem helyettesíti `infra.py`-t; bundle-formátum/`verify-release` CLI **explicit ki van zárva** a jelen scope-ból | **concept** (dokumentált, nincs runtime) | `docs/contracts/en/release-artifact.md:85-98`: *"The target state for a release artifact ... builds on these three invariants ... Defining that bundle format, a `verify-release` CLI ... are **out of scope for this job**"* | `Read` ua. |  |
| `finalize_release.py` nem szerepel a `docs/contracts/en/release-artifact.md` három-fázisú leírásában | **implemented** (hiány igazolva) | `grep -n "finalize_release" docs/contracts/en/release-artifact.md` → 0 találat; a "finalize" fázist `infra.py`/`compiler.py` fedi a doksi szerint | `grep -n "finalize_release" docs/contracts/en/release-artifact.md` |  |

**Konklúzió 3. ponthoz:** A jelenlegi, tényleg futó release-lánc:
`make release` → `tools.compiler` → `infra.ReleaseManager` (prepare/finalize)
+ `make wasm.buildhash`/`wasm.rebuild-verify` (build-gap, wasm-specifikus).
`finalize_release.py` ezen kívül áll, nincs hívva, és a kontraktus-dokumentum
sem hivatkozik rá. A `docs/contracts/{en,hu}/release-artifact.md` "Target
state" szakasza **kompatibilis kiterjesztés** a jelenlegi `infra.py`-modell
fölött — nem egy attól független/divergáló réteg, és a bundle-formátum
definiálását maga a dokumentum is jövőbeli, külön munkának jelöli.

---

## KB háromszintű státusz tábla

| Node | Forrás | Tartalom | Státusz | Megjegyzés |
|---|---|---|---|---|
| `n1284` / `c1284` — "6.5 `finalize_release.py` Migration Path" | `CIC-Schemas/docs/en/compiler-architecture-plan.md` (schemas/main lineage, ~561-578. sor) | A dokumentum 4 "permanens logikai felelősséget" sorol fel `finalize_release.py`-hoz, **#1-ként**: *"Verify `checksum == buildHash` (build integrity gate)"*. A migrációs terv szerint ezek a felelősségek relay API call-lá válnak, ha `compiler_settings.cic_relay_url` be van állítva. | **concept** | Ez a doksi maga is a `checksum == buildHash` egyenlőségi modellt rögzíti mint tervezett célt — ami konceptuálisan ugyanaz a probléma, amire a reviewer rámutatott, csak **schemas/main doksi-szinten**, nem `wasm/main` kód-szinten. A `wasm/main` `infra.py` ezzel **nem egyezik** (külön mezőként kezeli) — ld. 1. pont. |
| `n1295` / `c1295` — "Step 10 — Mark `finalize_release.py` for deletion" | `CIC-Schemas/docs/en/compiler-architecture-plan.md` (~648-654. sor) | *"Add a prominent `# DEPRECATED: Use relay API when available.` comment block. Track relay readiness as a separate milestone; delete on relay GA."* | **scaffold** (terv van, kód-szintű deprecation-jelölés még nincs) | `base-repo/tools/finalize_release.py` jelenleg csak egy `# FIXME: This script is a temporary solution...` kommentet tartalmaz (8-15. sor) — a tervezett `# DEPRECATED` jelölés **nincs** átvéve. A relay-readiness milestone (Vault/relay API) nincs implementálva — `_check_api_accessibility` (`infra.py:155`) léte alapján van valamilyen API-elérhetőség check, de `finalize_release.py` önálló, Vault-env-alapú script maradt. |
| `n1346` / `c1346`, `n1357` / `c1357` (HU megfelelők) | `CIC-Schemas/docs/hu/compiler-architecture-plan.md` | Az `n1284`/`n1295` magyar megfelelői, tartalmilag azonos | **concept** / **scaffold** | l. fent |
| `c1503` (job-spec hivatkozás, "modul-release evidence") | — | `get_node("c1503")` → `null` | **nem található** | A megadott node-id nem létezik a jelenlegi KB-ban (`kb_status` szerint a KB friss, `graph_nodes.pkl` betöltve, de `c1503` nincs benne). `search_nodes`/`search_query` "checksum buildHash release pipeline" / "schemalib unified compiler architecture" / "wasm release artifact contract buildHash" kulcsszavakra **0 találat** — a `wasm/main` ág saját kontraktus-dokumentumai (`docs/contracts/{en,hu}/release-artifact.md`, `wasm-template-plan.md`) **nincsenek indexelve** a KB-ban. |

---

## Döntési kérdés az orchestrátor számára

**A) `finalize_release.py` jelenleg dead code a production láncban, törölhető
vagy `# DEPRECATED` jelölhető — a wasm-specifikus munka (`infra.py`/
`compiler.py`/`wasm.mk` réteg felett) folytatható, mert ez a réteg már most
helyesen kezeli a checksum/buildHash szétválasztást.**
Hivatkozás: `tools/finalize_release.py:188-201` (egyenlőségi check) vs.
`grep -rn "finalize_release" Makefile mk/*.mk .github/workflows/*.yml` (0
találat) vs. `tools/infra.py:246-248,297,352-385` (helyes szétválasztás,
aktív call-site `tools/compiler.py:200,214-215`).

**B) A `wasm/main` release-backbone (`tools/infra.py`, `tools/compiler.py`,
`tools/finalize_release.py`, `project.schema.yaml`) ~6 hónapja nem
szinkronizált `schemas/main`-nel (`0454bb0` @ 2025-12-02 vs. `CIC-Schemas`
`2ec57c0` @ 2026-03-21, `schemalib`-refaktor). A `450ac0c` "inherit
schemas/main release backbone" commit (2026-06-12) ezt a réteget nem hozta
át. Mielőtt a `wasm-template-release-contracts` job (vagy bármilyen további
wasm-specifikus schema/release munka) tovább épül `project.schema.yaml`/
`infra.py` fölé, érdemes eldönteni: ezt a szinkronizációs adósságot most
behozzuk (upstream `schemalib` átemelése a `wasm/main`-be), vagy tudatosan
elhalasztjuk és a jelenlegi (régebbi) `infra.py`-modell fölé épülünk tovább,
felvállalva a `compiler_settings` schema-rést (l. 2. pont, `additionalProperties`
permisszivitás miatt jelenleg nem hibázik, de dokumentálatlan).**
Hivatkozás: `git -C base-repo log --diff-filter=A --oneline -- tools/infra.py`
→ `0454bb0`; `git -C CIC-Schemas log --oneline --all -- tools/infra.py` →
`2ec57c0`; `git -C base-repo show --stat 450ac0c` (fájllista, infra.py/
compiler.py/finalize_release.py/project.schema.yaml hiánya); `diff
CIC-Schemas/project.schema.yaml base-repo/project.schema.yaml` (`compiler_settings.repo_type`
és a modul-specifikus mezők hiánya base-repo oldalon).

**C) A `docs/contracts/{en,hu}/release-artifact.md` "Target state" (signed
bundle, `verify-release` CLI) explicit kompatibilis kiterjesztésnek van
jelölve `infra.py` három-fázisú modellje fölött, és a bundle-formátum
definiálását a dokumentum maga is külön, jövőbeli jobnak jelöli ("out of
scope for this job"). Ebből a szempontból **nincs azonnali divergencia**, ami
blokkolná a `wasm-template-release-contracts` jelen state-ét — de a B) pont
szinkronizációs adóssága hatással lehet arra, hogy a jövőbeli `verify-release`
CLI melyik `infra.py`/`schemalib` API-ra épüljön (a régi monolitikus vagy az
új `schemalib`-alapú).**
Hivatkozás: `docs/contracts/en/release-artifact.md:58-98`.

---

## Sub-job spec

Nem hoztam létre sub-job specet. A B) opció (`schemas/main` → `wasm/main`
release-backbone szinkronizáció) explicit orchestrátor-döntést igényel
(scope, ütemezés, és hogy a `schemalib`-migráció a `wasm/main`-en vagy előbb
egy közös upstream lépésben történjen) — ez nem ebből a riportból
levezethető egyértelmű "kövezetkező lépés", hanem maga a döntési kérdés
tárgya.

---

## Definition of Done — checklist

- [x] `finalize_release.py` vs `infra.py` checksum/buildHash logika file:line
      szinten azonosítva, call-site grep-pel igazolva (dead code)
- [x] `schemas/main`/`CIC-Schemas` összehasonlítás konkrét fájl-párokkal
      (`tools/infra.py`, `tools/compiler.py`, `tools/finalize_release.py`,
      `project.schema.yaml`)
- [x] canonical release path leírva (mi fut tényleg ma)
- [x] döntési kérdés A/B/C opciókkal, hivatkozásokkal
- [x] KB háromszintű státusz tábla
- [x] base-repo és CIC-Schemas változatlan (`git status` clean)
- [ ] report a `feature/wasm-release-pipeline-audit`-on pusholva (következő lépés)
