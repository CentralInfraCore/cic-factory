# base-repo elemzés

## Main branch tartalma és szerepe

A `main` branch a **"Template Factory"** koncepció megvalósítása (`docs/en/architecture.md`):

- A repo nem végtermék, hanem **sablon**, amiből downstream ("Production") repók készülnek.
- A sablon szíve egy **egységes `tools/compiler.py`**, ami kettős szerepet tölt be:
  1. **Template Maintainer** szerep (base-repo-ban futtatva): a `project.yaml` validálása és "finalizálása" új template-verzió release-elésekor.
  2. **Product Manufacturer** szerep (downstream repóban futtatva): aláírt artifact előállítása a downstream saját release-folyamatában — ugyanazzal a `compiler.py`-jal.
- A `project.yaml` a központi konfiguráció: `metadata` (verzió, checksum, Vault aláírás, CIC cert lánc) + `compiler_settings` (component_name, Vault key/cert nevek, meta-schema fájl).
- Jelenlegi `main` állapot: `project.yaml.metadata.version: 0.7.3` (`project.yaml:5`).
- A release artifact maga a **frissen aláírt `project.yaml`** + egy annotated git tag (`<component>@v<version>`) — nincs külön build output (pl. binary, zip).

A `main` Python/Docker-alapú schema-compiler + Vault-signing infrastruktúra: `Makefile`, `mk/infra.mk`, `tools/compiler.py`, `tools/infra.py`, `tools/releaselib/`, `project.schema.yaml`, `renovate.json`, `requirements.in/.txt`, `tests/`.

## Release folyamat — lépések sorban

A jelenlegi (aktív) release-folyamat **`make release VERSION=X.Y.Z`** → `tools/compiler.py release --version X.Y.Z` → `ReleaseManager.run_release_close()` (`tools/infra.py:397`).

A folyamat **két fázisú**, és a jelenlegi git branch alapján dönt (`tools/infra.py:397-433`):

1. **Developer preparation phase** (`_execute_developer_preparation_phase`, `tools/infra.py:195-334`) — `main`-ről indítva:
   - Ellenőrzi, hogy a working tree tiszta (`is_dirty()`, `tools/infra.py:199-203`).
   - Létrehoz egy release branch-et: `<component>/releases/v<version>` (vagy `releases/v<version>`, ha `component_name == "main"`) — `tools/infra.py:206-217`.
   - Betölti és validálja a forrás schema-t, kiszámolja a checksumot (`tools/infra.py:220-232`).
   - Lekéri a felhasználói és a CIC Root CA certet Vault-ból (`tools/infra.py:234-244`).
   - Vault-tal aláírja a metaadatokat (`vault_service.sign(...)`, `tools/infra.py:263-265`).
   - Frissíti a `project.yaml.metadata`-t (`version`, `checksum`, `sign`, `createdBy`, `build_timestamp`), `buildHash`/`cicSign`/`cicSignedCA.certificate` mezőket üresen hagyva (`tools/infra.py:268-296`).
   - Commitol a release branch-re: `"release: Prepare <component> v<version> for build"` (`tools/infra.py:298-303`).
   - Kiírja: "ACTION REQUIRED" — manuálisan futtatni kell a build-et (`buildHash` kitöltése), commitolni, majd újra futtatni `make release VERSION=...`-t (`tools/infra.py:308-315`).

2. **Finalization phase** (`_execute_finalization_phase`, `tools/infra.py:336-395`) — a release branch-ről indítva (második futás):
   - Validálja a végső `project.yaml`-t a `project.schema.yaml` ellen (`_validate_final_project_yaml`, `tools/infra.py:168-193`).
   - Ha vannak még nem commitolt build-artifact változások, commitolja: `"release: Finalize <component> v<version> build artifacts"` (`tools/infra.py:355-368`).
   - Létrehoz egy **annotated git tag**-et: `<component>@v<version>` (`tools/infra.py:374-380`).
   - Visszaváltja a `main_branch`-re (`project.yaml.metadata.main_branch`, default `"main"`) és **`--no-ff` merge**-eli a release branch-et (`tools/infra.py:382-389`).
   - Törli a release branch-et (`tools/infra.py:390-391`).

### Vault signing kapcsolódása

- A `_execute_developer_preparation_phase` Vault-ból kéri le a felhasználó certjét és a CIC Root CA certet (`vault_cert_mount`/`vault_cert_secret_name`/`vault_cert_secret_key` a `project.yaml.compiler_settings`-ből, `tools/infra.py:234-243`), majd a `vault_key_name` (`cic-my-sign-key`) kulccsal aláírja a metadata-hash-t (`tools/infra.py:263-265`).
- A `tools/finalize_release.py` egy **külön, ideiglenes** eszköz: a fájl elején FIXME jelzi, hogy "temporary solution... until a secure, closed-source build environment ('relay') and a central signing API are available" (`tools/finalize_release.py:9-15`). Ez a `cicSign`/`cicSignedCA.certificate` mezőket tölti fel egy *második*, központi (CIC Root CA) Vault-aláírással, és validálja, hogy `checksum == buildHash` (`tools/finalize_release.py:213-225`).
- A `tools/release.sh` egy **legacy** script (`schemas/index.yaml`-alapú, `template-schema@vX.Y.Z` tag-eket generál) — a `Makefile`-ban már ki van kommentezve, megjegyzéssel: "The release.sh script is no longer needed as its functionality has been integrated into compiler.py" (`Makefile`: `release:` cél, kikommentezett `@tools/release.sh project.yaml` sor).

### `template-schema` vs base release tag

- A `template-schema@vX.Y.Z` tag-formátum a **legacy `tools/release.sh`** útból származik (`SCHEMA_NAME` = a `schemas/index.yaml` `metadata.name` mezője, `tools/release.sh` 51-67. sor: `TAG_NAME="${SCHEMA_NAME}@${VERSION}"`).
- Az **aktuális** `compiler.py release` út tag-formátuma `<component_name>@v<version>` (`tools/infra.py:374`), ahol `component_name` a `project.yaml.compiler_settings.component_name` (jelenleg `base`, `project.yaml:24-25`).
- A két mechanizmus **különböző tag-névteret** használ (`template-schema@...` vs `base@v...` / `schemas@v...`); a repóban talált tag-ek (`base@0.5.0`, `schemas@v0.9.0`) egyik formátumnak sem felelnek pontosan meg ("v" prefix hiánya `base@0.5.0`-nál) — lásd "Nyitott kérdések".

## Branch struktúra és specializáció logikája

```
git branch -a (origin):
  HEAD -> origin/main
  IaC/devel
  d/feature-001, d/feature-002, d/feature-006
  devel
  docs/main
  fix/createdby-signing
  golang/devel, golang/main
  main
  mcp/devel
  renovate/all-dependencies
  schemas/devel, schemas/main
  tmp
  wasm/main
  workflows/main
```

- A `docs/en/architecture.md` szerint a fejlesztés `df/xxx` branch-eken folyik, `main`-ből vagy egy specializációs branch-ből (pl. `schemas/f/1`) ágazva el; a template release `main`-ből történik tag-gel; a downstream repók a Renovate PR-eket a saját `df/xxx` branch-eikre kapják.
- **`schemas/main`** — a `main`-hez **majdnem azonos** (csak az `ai/` könyvtár hiányzik belőle, `diff <(git ls-tree main) <(git ls-tree origin/schemas/main)` 5 sor eltérés). A `git merge-base main origin/schemas/main` a `d286cb8` commit ("Merge pull request #6 from CentralInfraCore/fix/createdby-signing", 2026-03-21) — ez a `main` HEAD-jéhez közeli, vagyis a `schemas/main` **friss és jól szinkronizált** specializáció. A `schemas/main` history-jában látható release-merge commitok (`base/releases/v0.7.1`, `base/releases/v0.7.3`) igazolják, hogy a `main`-ből rendszeresen, release-enként **merge**-eli a frissítéseket (nem rebase).
- **`golang/main`** és **`golang/devel`** — **teljesen más fájlstruktúra**, mint a `main`: nincs `project.yaml`, `tools/compiler.py`, `renovate.json`, `mk/infra.mk`; helyette `tools/canonicalize/`, `tools/symbolsgen/`, `tools/certutils/`, `scripts/*.sh`, `.github/workflows/verify.yml` + `manifest-check.yml`, saját `Makefile` (Go-builder/fixer docker compose mintával).
  - A `git merge-base main origin/golang/main` = `133e5ca` ("git magic") — ez **régi**, jóval **a `project.yaml`/`compiler.py` egységesítés előtti** állapot a `main`-en. Tehát a `golang/main` **nem kapta meg** a `main` mai release-architektúráját (Vault-aláírt `project.yaml`, `compiler.py release`), csak egy nagyon korai `main`-állapotból ágazott el, és attól kezdve önálló életet él (saját Go-tooling, saját CI).
  - **`golang/main` ≠ "main + golang specializáció"** a jelenlegi architektúra szerint — ez egy **elavult/divergens ág**, ami nem a jelen "Template Factory" minta szerint épül.

### Tag-ek hozzárendelése

- `base@0.5.0` → commit `be0617888654a5cfb764bd62a37d4aee22bd6ee8` ("release: 0.5.0", 2025-10-18). Ez a commit a `main`, `devel`, `schemas/main`, `schemas/devel` ágakon mind elérhető (régi, közös ős).
- `schemas@v0.9.0` → commit `c3491c96f06200a32ecf140777891cfbbd740de5` ("Merge pull request #5 from CentralInfraCore/schemas/devel"), ugyanúgy minden fő ágon elérhető.
- **Mindkét tag régi, közös ősi commitra mutat** — nem a `main` jelenlegi HEAD-jére (`18534919...`, `project.yaml.version: 0.7.3`). A `0.7.x` release-ekhez tartozó tag-ek (`base@v0.7.0/0.7.1/0.7.3`, lásd CIC-Relay merge-commit-üzenetei) **nincsenek** a lokális tag-listában — lásd "Nyitott kérdések".

## Renovate logika

- A `renovate.json` (`base-repo` `main`) tartalma:
  ```json
  {
    "$schema": "https://docs.renovatebot.com/renovate-schema.json",
    "extends": ["config:recommended"],
    "pip-compile": { "enabled": true },
    "packageRules": [
      { "matchUpdateTypes": ["major","minor","patch","pin","digest"], "groupName": "all dependencies" }
    ]
  }
  ```
- Ez a konfig **csak a saját repo dependency-frissítéseit** (pip-compile, github-actions stb.) csoportosítja — **nem tartalmaz semmilyen git-tag-alapú manager-konfigot**, amivel a `base@vX.Y.Z` tag-eket downstream repókban követni lehetne.
- A `docs/en/architecture.md` Renovate-fejezete csak **koncepcionálisan** írja le ("Renovate updates" a diagramon, "Renovate detects the new tag and opens a PR") — **konkrét implementáció (pl. `git-tags` datasource + `regexManagers` a `project.yaml` verzióra) a base-repo-ban nem található**.
- → Ez **nyitott kérdés**, lásd lent.

## CIC-Relay adaptálhatóság

- **Releváns sablon**: a feltételezett `golang/main` **NEM** releváns — elavult, divergens ág (lásd fent). A valóságban a CIC-Relay **a `base-repo` `main`-jét** követi közvetlenül: a CIC-Relay repóban van egy `base` git remote (`origin → CentralInfraCore/base-repo`-ra mutató remote, `remotes/base/main`, `remotes/base/golang/main`, `remotes/base/schemas/main` stb.), és a CIC-Relay `main` history-ja tartalmazza:
  ```
  58fe838 Merge branch 'base/releases/v0.7.3' for release 0.7.3 --- [signing-metadata] ...
  1d5ac04 Merge branch 'base/releases/v0.7.1' for release 0.7.1 --- [signing-metadata] ...
  14009c2 Merge branch 'base/releases/v0.7.0' for release 0.7.0 --- [signing-metadata] ...
  69f87f0 Merge branch 'base/releases/v0.6.0' for release 0.6.0 --- [signing-metadata] ...
  ```
  Ez azt jelenti, hogy **a CIC-Relay már megkapta a base-repo release-mintáját egészen v0.7.3-ig**, manuális `git merge base/releases/vX.Y.Z` útján (nem Renovate-en keresztül).
- **CIC-Relay `project.yaml`** létezik, és `compiler_settings.component_name: base` — ugyanazt a `project.yaml`/`project.schema.yaml` szerkezetet használja, mint a base-repo, verziója is `0.7.3` (megegyezik a base-repo `main` jelenlegi verziójával).
- **Már átkerült és azonos fájl**: `mk/infra.mk` — **byte-azonos** a base-repo `main:mk/infra.mk` és a CIC-Relay `mk/infra.mk` között (`diff` üres).
- **Átkerült, de módosított fájl**: `tools/git_hook_commit-msg.sh` — a CIC-Relay verziója a base-repo `main` verziójához képest egy extra blokkal bővült:
  ```diff
  + # Skip Vault signing in CI — no local Vault available (Renovate, GitHub Actions)
  + [[ "${CI:-}" == "true" ]] && exit 0
  ```
  (CIC-specifikus CI-kiegészítés, nem kerülhet vissza módosítás nélkül a base-repo-ba, illetve frissítéskor a CIC-Relay-nek meg kell tartania ezt a blokkot.)
- **Nem kerülhetnek át változtatás nélkül**: `Makefile` (CIC-Relay saját, Go-specifikus, `-include mk/infra.mk`-val bővíti, nem helyettesíthető a base-repo Python-orientált `Makefile`-jával), `renovate.json` (CIC-Relay-nek saját, Go/gomod-specifikus manager-csoportjai vannak, lásd `relay-delta.md`), `.github/workflows/*` (CIC-Relay saját `verify.yml`/`renovate.yml`/`manifest-check.yml`-je van, eltér a base-repo `main:.github/workflows/ci.yml`-től).
- **CIC-Relay Makefile vs base-repo `main` Makefile**: nem overlapping a tartalom — a base-repo `main` Makefile Python/Docker schema-compiler célokat definiál (`validate`, `release`, `manifest-verify` stb.), a CIC-Relay Makefile Go-build/test/release célokat (`build-relay`, `release-relay`, `test-go` stb.), de **mindkettő `include mk/infra.mk`-t használ**, ami azonos — ez a **közös, megosztott réteg**.

## Nyitott kérdések

1. **A `0.6.0`–`0.7.3` release tag-ek hiánya a base-repo lokális klónjából**: A CIC-Relay merge-commit-üzenetei (`Merge branch 'base/releases/v0.7.3' for release 0.7.3`) azt jelzik, hogy ezek a release branch-ek/tag-ek léteztek a base-repo-ban, de a `git tag -l` és `git ls-remote --tags origin` a lokális base-repo klónban csak `base@0.5.0` és `schemas@v0.9.0`-t mutat. Nem tudom megmondani lokális adatokból, hogy (a) a `_execute_finalization_phase` által létrehozott `<component>@v<version>` tag-eket valaki utólag törölte, (b) a tag-ek léteznek a remote-on, de ez a lokális klón nem fetch-elte le mindet, vagy (c) a CIC-Relay merge-commit-ek nem tag-re, hanem egy (később törölt) release branch-re hivatkoztak. → Ehhez a base-repo remote teljes tag-listáját (`gh api repos/CentralInfraCore/base-repo/tags`) kellene lekérni.
2. **Renovate git-tag-alapú propagáció konkrét konfigja**: a `docs/en/architecture.md` koncepcionálisan leírja, hogy Renovate figyeli a base-repo tag-jeit, de **semmilyen `renovate.json`-ban (sem base-repo, sem CIC-Relay) nincs ehhez tartozó `regexManagers`/`git-tags`-datasource konfiguráció**. Nem tudom megmondani, hogy ez (a) tervezett, de még nincs implementálva, vagy (b) a manuális `git merge base/releases/vX.Y.Z` minta a *szándékolt* végleges folyamat, és a Renovate-es leírás az architecture.md-ben elavult/aspirational.
3. **`base@0.5.0` (nincs "v" prefix) vs `<component>@v<version>` tag-formátum**: a kódban implementált formátum `v`-vel kezdődik (`base@v0.7.3`), de a meglévő `base@0.5.0` tag nem. Nem tudom megmondani, hogy ez egy korai, a jelenlegi kódnál régebbi tag (valószínű, mert a hozzá tartozó commit `be0617888` egy nagyon korai "release: 0.5.0" commit), vagy egy manuálisan, más eszközzel létrehozott tag.
4. **`template-schema@vX.Y.Z` (legacy `release.sh`) tag-ek létezése**: nincs ilyen tag a repóban — nem tudom megmondani, hogy ezt az utat valaha is használták-e production release-hez, vagy csak `schemas/`-specifikus fejlesztési kísérlet volt.
5. **A `wasm/main` branch protection 404-et adott** (`gh api .../branches/wasm/main/protection` → "Branch not protected"), miközben a feladatleírás szerint *minden* `*/main` branch protected. Ez ellentmond a rögzített ténynek — vagy a `wasm/main` egy kivétel (még nincs rajta protection), vagy 2026-06-09 után jött létre és nem kapta meg automatikusan a szabályt. Nem tudom megmondani, melyik.
