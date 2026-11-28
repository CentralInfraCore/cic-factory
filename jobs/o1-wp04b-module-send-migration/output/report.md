# WP-04b jelentés — az Oracle modul `cic-flow.send` migrációja a `devel` ae3c962 bázisra

**Job:** `o1-wp04b-module-send-migration` · **Végrehajtó:** factory agent ·
**Kezdés (UTC):** 2026-11-28 16:18 · **Cél-repó:** `cic-module-oracle-cloud`

> Ez a jelentés inkrementálisan készül: minden szakasz a hozzá tartozó commitban
> kerül be, a nyers parancskimenetek az `output/evidence/` alatt.

---

## 0. A Git-bázis mechanikus igazolása (B-1..B-6)

Nyers napló: [`evidence/10-git-base-verification.log`](evidence/10-git-base-verification.log),
[`evidence/11-pr54-state.log`](evidence/11-pr54-state.log).

### B-1 — az előírt base elérése

```
$ git merge-base feature/o1-wp04b-module-send-migration ae3c96237839c9fd06649c918a2194a79ebd8cb1
ae3c96237839c9fd06649c918a2194a79ebd8cb1

$ git rev-parse feature/o1-wp04b-module-send-migration
ae3c96237839c9fd06649c918a2194a79ebd8cb1
```

A merge-base **pontosan az előírt base** (`ae3c962`), mert az ág a munka kezdetén
azonos vele. **B-1: PASS.**

### B-2 — a munkacsomag saját deltája a munka kezdetén

```
$ git rev-list --count ae3c962..feature/o1-wp04b-module-send-migration
0

$ git diff --stat ae3c962 feature/o1-wp04b-module-send-migration
(üres kimenet)
```

A kiinduló állapot deltája nulla: a bázis igazolása előtt semmi nem került az
ágra. **B-2: PASS** (a záró delta a jelentés 5. szakaszában).

### B-3 — a cél-ág (`devel`) előrehaladása és a PR-állapot

```
$ git rev-parse origin/devel
ae3c96237839c9fd06649c918a2194a79ebd8cb1

$ git rev-list --count ae3c962..origin/devel
0
```

A `devel` feje a mérés idején **azonos az előírt base-szel**: nincs elavult
eltérés, a job a `devel` csúcsára épül. (A `git fetch --prune` egyetlen
frissítést hozott: `origin/integration/o1` 7704e66..e4eebc8 — ez nem a bázis.)

A régi WP-04 PR (#54) mért állapota:

```
$ gh pr view 54 --json number,title,baseRefName,headRefName,mergeable,mergeStateStatus,state,isDraft
{"baseRefName":"devel","headRefName":"feature/o1-wp04-sign-send","isDraft":true,
 "mergeStateStatus":"DIRTY","mergeable":"CONFLICTING","number":54,"state":"OPEN",
 "title":"O-1 WP-04: migrate the Oracle guest to cic-flow.send"}
```

### B-4 — a #54 elavult bázisának szétválasztása a saját deltától

```
$ git merge-base origin/feature/o1-wp04-sign-send ae3c96237839c9fd06649c918a2194a79ebd8cb1
5d0a3278c6cc68f4808edacb8ee4300299af3153

$ git rev-list --count ae3c962..origin/feature/o1-wp04-sign-send
2

$ git rev-list --count 5d0a327..origin/devel
63
```

A mérés megerősíti a `ref/o1-integration-findings-2026-11-28.md`-t: a #54
tényleges merge-base-e `5d0a327`, **63 commit-tal a `devel` mögött**; a #54 saját
hozzájárulása 2 commit. A #54 saját deltája (`git diff --stat 5d0a327
origin/feature/o1-wp04-sign-send`):

```
 MANIFEST.sha256                                |  23 +--
 docs/design/specs/provider-abi.md              |   4 +-
 docs/design/specs/relay-sign-send-interface.md |  10 ++
 module/cicflow_guest.go                        |  23 +--
 module/cicflow_host.go                         |  21 +--
 module/host_mock_test.go                       | 170 ++++++++++++++++++
 module/module.wasm                             | Bin 1173093 -> 1173869 bytes
 module/module_loadtest_test.go                 |  65 +++----
 module/oci_sign.go                             |  70 --------
 module/provider.go                             | 182 ++++++++++++-------
 module/provider_test.go                        |   6 +-
 module/relay_integration_test.go               |  13 +-
 module/send_contract_test.go                   | 240 +++++++++++++++++++++++++
 project.yaml                                   |  14 +-
 14 files changed, 621 insertions(+), 220 deletions(-)
```

A `ref/wp04-own-delta.patch` ebből 13 fájlt tartalmaz (a `module.wasm` bináris
kihagyva) — ez a portolás bemenete. **B-4: PASS.**

### B-5 / B-6

- **B-5:** a #54 `CONFLICTING/DIRTY` — a rajta futott zöld CI **nem** acceptance.
  A WP-04b záró PR-jára a `MERGEABLE` követelmény a 7. szakaszban mérve.
- **B-6:** minden fenti érték parancskimenet, nem ágens-állítás.

### Megjegyzés a környezetről (mért, nem workaround)

- A factory `PostToolUse` hookja (`python3 $CIC_WORKDIR/tools/hooks/log-event.py`)
  **minden** Bash-hívásnál hibára fut, mert a `CIC_WORKDIR` környezeti változó
  üres: `python3: can't open file '/tools/hooks/log-event.py'`. Ezt nem kerültem
  meg és nem írtam át; jelentem.
- **Commit-aláíró hook nincs elérhető** a `cic-factory` klónban: `.git/hooks/`
  csak `*.sample` fájlokat tartalmaz, a `core.hooksPath` és a `commit.gpgsign`
  nincs beállítva. A commitok így **aláírás nélkül** készülnek — nem kerültem meg
  semmit, ez a mért környezeti állapot.
- A `cic-factory` klón git-identitása placeholder volt (`Your Name
  <you@example.com>`); a job elején valós lokális identitásra állítottam
  (`git config user.name/user.email`, repo-lokálisan).
- A `ref/` könyvtárban a job `input.md` által hivatkozott `ref/schemas/`,
  `ref/examples/` és `ref/vectors/` **nincs jelen** (csak a négy `.md` és a
  `.patch`). A wire szerződés így a `ref/wp04-own-delta.patch` és a
  `docs/design/specs/relay-sign-send-interface.md` alapján kerül portolásra; a
  séma-fájl szerinti validáció **UNVERIFIED (bemenet hiányzik)**.
