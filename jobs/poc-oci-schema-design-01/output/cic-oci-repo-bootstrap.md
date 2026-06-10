# `cic-oci` — repo bootstrap terv

> Státusz: **concept** (terv, nincs implementálva). A `cic-oci` repó még nem létezik.
> Alapja: a `cic-compute` repó tényleges szerkezete (klónozva referenciaként,
> `workspace/cic-compute/`) + a `poc-system-plan/input.md` lezárt OCI döntései.

---

## 1. Remote-ok

```
origin  git@github.com:CentralInfraCore/cic-oci.git
base    git@github.com:CentralInfraCore/cic-primitives.git
```

Megjegyzés a referencia-klón alapján: a ténylegesen létező `cic-compute` repóban
(`workspace/cic-compute/`) a klónozott állapotban **csak `origin` remote** látszik
(`git remote -v` → egyetlen sor), és nincsenek tag-ek a sekély klónban. A
`project.yaml`-ban viszont explicit szerepel:

```yaml
x-cic:
  repo_type: domain
  base_primitive: cic-primitives@v0.1.0
```

Vagyis a `base` remote / `cic-primitives@vX.Y.Z` függőség **deklaratív** (a
`project.yaml`-ban rögzített verziófüggés), nem feltétlenül élő git remote a
mindennapi munkában. A `cic-oci` bootstrapnél mindkettőt érdemes felvenni:
- `base` remote a kezdeti `git merge -s ours --allow-unrelated-histories base/main`
  (vagy hasonló, a `cic-compute` történetében használt) sablon-átvételhez,
- utána a `project.yaml`-ban rögzített `base_primitive: cic-primitives@v0.1.0`
  verziőcímke a tényleges függőség-jelölő — ez a `dependency.yaml`-ban is megjelenik
  (`cic-compute/dependency.yaml` mintájára).

---

## 2. Branch-séma

A `CIC/CLAUDE.md`-ben és a job input-ban szereplő tábla egy **megfigyelt, de nem
egységesen alkalmazott** mintát ír le (`network`, `yang` repókban jelenik meg
explicit `<domain>/main` / `<domain>/devel` / `<domain>/releases/vX.Y.Z` branch-ekkel).
A ténylegesen klónozott `cic-compute` ezzel szemben egyetlen `main` branch-csel él
(`project.yaml: main_branch: compute/main` — vagyis a branch *neve* `main`, de a
`project.yaml` szemantikus címkéje `compute/main`).

**Javaslat `cic-oci`-ra — a `cic-compute` mintát követve, minimalista induláskor:**

| Branch | Cél | Megjegyzés |
|---|---|---|
| `main` | egyetlen aktív fejlesztési és release branch | `project.yaml: main_branch: oci/main` (szemantikus címke, nem külön git branch) |
| `feature/<job-id>` | agent munka (cic-factory minta) | csak a `cic-factory` workflow-hoz, nem `cic-oci` saját konvenciója |

**Opcionális, ha a projekt növekszik (a `network`/`yang` mintát követve, csak ha
indokolt — pl. párhuzamos v0.x / v1.x fejlesztés):**

| Branch | Cél |
|---|---|
| `devel` | `base/devel`-t követi (cic-primitives upstream sync) |
| `oci/devel` | aktív fejlesztés |
| `oci/main` | stabil, release-re kész |
| `oci/releases/v0.1.0` | hosszú életű release branch, hotfixekhez |

A v0.1.0 induláshoz **az egyszerű `main`-only modell elegendő** — a
`oci/releases/vX.Y.Z` bevezetését csak akkor javasoljuk, amikor az első release
után hotfix-igény merül fel egy korábbi verzión, miközben `main` már tovább halad.

---

## 3. Tag-séma

A duplikált tag-konvenció (`cic-<domain>@X.Y.Z` + `<domain>/@vX.Y.Z`) a
`cic-primitives` örökölt történetében jelenik meg (`primitives/@v0.1.x`,
`base@0.5.0`, `schemas@v0.9.0` — ezek `base` merge-ekből származnak, tehát
**örökölt tag-ek lesznek `cic-oci`-ban is**, amint a `base` remote-ot egyszer
mergeljük).

**`cic-oci` saját tag-jei v0.1.0-tól:**

```
cic-oci@0.1.0      ← elsődleges release tag (CIC-Schemas compiler ezt várja)
oci/@v0.1.0        ← domain-szemantikus alias tag (a `project.yaml: main_branch: oci/main`
                      címkézési konvenciót tükrözi)
```

A `tools/release.sh` (cic-compute mintából átvéve) Vault Transit aláírást végez a
staged tartalom snapshot-ján (`git write-tree` → `git archive` → tar → sign) —
ugyanez a mechanizmus `cic-oci`-ban változtatás nélkül átvehető, a `KEY_NAME`
(`cic-my-sign-key`) megegyezik.

---

## 4. Mit kell átemelni a `base-repo` / `cic-primitives` template-ből

A `cic-compute` referencia-klón (`workspace/cic-compute/`) gyökérszerkezete alapján
a következő elemek **változtatás nélkül vagy minimális domain-átírással** átveendők:

| Elem | Forrás | `cic-oci`-beli teendő |
|---|---|---|
| `CLAUDE.md` | `cic-compute/CLAUDE.md` (= `cic-primitives` boot sequence sablon) | domain-specifikus szakasz hozzáadása (OCI scope, `cic-oci` státusz-térkép) |
| `project.yaml` | `cic-compute/project.yaml` | `name: cic-oci`, `description`, `main_branch: oci/main`, `repository url`, `x-cic.base_primitive: cic-primitives@v0.1.0` |
| `project.schema.yaml`, `md.meta.schema.yaml` | változatlanul | meta-séma validáció — nem domain-specifikus |
| `dependency.yaml`, `dependencies/` | `cic-compute` mintája | `cic-primitives@v0.1.0` függőség rögzítése |
| `Makefile` | változatlanul | `validate`, `release`, `repo.init` célok közösek |
| `tools/compiler.py` | változatlanul | a séma-compiler nem domain-specifikus |
| `tools/git_hook_commit-msg.sh`, `tools/init-hooks.sh`, `tools/vault-sign-agent.sh`, `tools/release.sh` | változatlanul | Vault Transit signing (`cic-my-sign-key`) — azonos kulcs minden domain repóban |
| `docker-compose.yml`, `Dockerfile` | változatlanul (vagy minimális image-név csere) | dev környezet |
| `LICENSE.md`, `LICENSE.yaml`, `LICENSE.meta.yaml` | változatlanul | `CC-BY-NC-SA-4.0` |
| `.mcp.json` | változatlanul | `cic-graph` MCP elérés |
| `feature-list.md`, `docs/`, `ai/` | sablon → domain tartalommal feltöltve | `ai/SYSTEM_CONTEXT.md`, `ai/PROMPTMAP.yaml`, `ai/DECISIONS.md` — OCI domain kontextussal |
| `tests/` | sablon struktúra átvétele | OCI séma validációs tesztek |

### `schemas/` struktúra (részletek a `cic-oci-schema-plan.md`-ben)

```
schemas/
  index.yaml          ← cic-primitives/schemas/index.yaml (meta-séma, változatlan átvétel)
  atomic/              ← cic-primitives/schemas/atomic/* releváns subset átvétele
  aggregate/           ← cic-primitives/schemas/aggregate/* releváns subset átvétele
  domain/              ← OCI-specifikus DomainComposition-ök ELŐTT egy köztes réteg
                          (a cic-compute mintát követve: domain/cloud-instance.yaml stb.
                          — l. cic-oci-schema-plan.md "domain vs examples" kérdés)
  examples/            ← OCI DomainComposition minták (reality check + dokumentáció)
  examples/invalid/    ← negatív tesztesetek (cic-compute/cic-primitives mintából átvéve)
```

---

## 5. Első release tartalma (v0.1.0)

A `poc-system-plan` szerint a v1 demo egyetlen **OCI Compute Instance** lifecycle-t
demonstrál (create → observe → drift → rollback). Ennek megfelelően a v0.1.0
release **minimális köre**:

### Kötelező (v0.1.0 — blokkolja a `poc-observer-plugin-01`-et)

- `schemas/atomic/` — a `OciComputeInstance`-hoz szükséges atomok átvétele:
  `Shape`, `Role`, `Behavior`, `Contract`, `Address`, `Identity`, `Event`
  (az `Access` atom csak akkor kell, ha policy_surface-t is definiálunk — l. schema-plan)
- `schemas/aggregate/` — `ManagedEntity`, `ConfigSurface`, `StateSurface`,
  `OperationSurface` (a `PolicySurface` opcionális v0.1.0-ban, mivel az OIS
  v1 "allow all" — nincs domain-szintű policy_surface tartalom)
- `schemas/examples/oci-compute-instance.yaml` — **1 db** kidolgozott
  `DomainComposition` (ez a jelen job reality-check terméke, l.
  `oci-compositions/oci-compute-instance.yaml`)

### Nem kötelező v0.1.0-hoz, de a teljes OCI domainhez kell (következő job: `poc-oci-schema-design-02`)

- `OciCompartment`, `OciVcn`, `OciSubnet`, `OciSecurityList` `DomainComposition`-ök
- `NotificationSurface` / `BindingSurface` formális aggregate (jelenleg
  `cic-primitives`-ben **concept** — a `ManagedEntity` slot-jai `Event[]` /
  `Address[]` típusként hivatkoznak rájuk, dedikált aggregate fájl nélkül,
  l. `cic-primitives/schemas/aggregate/managed-entity.yaml` `notification_surface`
  és `binding_surface` slot leírása: "Jövőbeli ... aggregate fogja köré burkolni")

### Reality check követelmény (ez a job adja)

Az `OciComputeInstance` `state_surface` mezőinek **1:1 egyezniük kell** a
`poc-system-plan/input.md`-ben rögzített `actual_state.json` sémával:

```
instance_id, lifecycle_state, shape, ocpus, memory_gb,
public_ip, private_ip, vcn_id, security_rules_hash, collected_at
```

Ez a `cic-oci-schema-plan.md` táblázatában és az `oci-compositions/oci-compute-instance.yaml`
fájlban van kidolgozva.

---

## Bridge-státusz összefoglaló

| Elem | Státusz | Megjegyzés |
|---|---|---|
| `cic-oci` repó létezése | **concept** | nincs létrehozva, ez a job csak tervet ad |
| `cic-primitives` atomic/aggregate sémák | **implemented** | `workspace/cic-primitives/schemas/` — léteznek, validálhatók |
| `cic-compute` mint bootstrap-minta | **implemented** | `workspace/cic-compute/` — teljes, működő domain repo struktúra |
| `NotificationSurface`/`BindingSurface` dedikált aggregate | **concept** | `managed-entity.yaml` slot-szinten kezeli, önálló aggregate fájl nincs |
| Branch/tag elaborate séma (`oci/devel`, `oci/releases/vX.Y.Z`) | **concept** | a `cic-compute` valós repó ezt nem alkalmazza, csak `main` |
