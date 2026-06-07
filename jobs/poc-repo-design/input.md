# poc-repo-design — PoC repó struktúra terv

## Kontextus

A CIC ökoszisztémában a PoC megvalósításához új komponensek kellenek. Az eddigi elemzések
(bridge-map, relay-coverage, corrections) alapján ismert mi van meg és mi hiányzik.

**A feladatod:** tervezd meg a repó struktúrát — melyik komponens hol él, mit örököl,
mit implementál. A cél: a meglévő CIC mintákat követni, ne találj fel újat.

## Boot sequence

1. `kb_status`
2. `search_nodes` → `["base-repo", "relay", "schema", "iac", "plugin", "primitives"]`

## Háttér — amit tudni kell

**Meglévő CIC repó minták** (olvasd el a KB-ból):

```
search_query("base-repo remote-merge Makefile CI template inherit")
search_query("cic-primitives domain repo inherit interface")
search_query("CIC-Schemas branch postgresql template worktree")
search_query("IaCSource ActualState interface relay nexus")
search_query("relay native module core modules register bootstrap")
search_query("plugin so buildmode external load components")
```

**Eddigi elemzések output fájljai** (a te klónodban):
```
jobs/poc-plan-bridge-review/output/bridge-map.md       ← komponens státuszok
jobs/poc-plan-bridge-review/output/relay-coverage.md   ← relay meglévő képességek
jobs/poc-bridge-check/output/corrections.md            ← korrekciók
```

**Ismert repó struktúra:**
- `base-repo` → Makefile, CI, docs sablon (remote-merge-gel öröklődik minden repóba)
- `cic-primitives` → meta-séma alap, 7 atom; domain repók ebből deriválnak
- `cic-compute`, `cic-network`, `cic-storage`, `cic-kubernetes`, `cic-yang` → provider domain repók
- `CIC-Schemas` → schema compiler + Vault signing; `postgresql` és `template` branch-ek
- `CIC-Relay` → Go runtime: `core/cabinet`, `core/nexus`, `core/modules`, `cmd/relay`

## Feladat

### 1. Repó térkép megtervezése

Tervezd meg az alábbi komponensek elhelyezését:

**Provider adapterek** (actual state collector — Proxmox, VyOS, OpenSwitch):
- Külön repó (mint cic-compute/cic-network mintájára)?
- Vagy CIC-Relay `core/modules/` alá natív modulként?
- Mit örökölnek a base-repo-ból?
- Milyen interfészt implementálnak (IaCSource? ActualStateCollector? mindkettő?)?
- Hogyan töltődnek be a relay-be (.so plugin vagy natív modul)?

Kérdezd le:
```
search_query("IaCSource interface nexus iac relay")
search_query("ActualState collector observer relay nexus")
search_query("core modules native register bootstrap relay")
search_query("plugin so external load components relay")
```

**PoC sémák** (desired_state, actual_state, drift, pose, state_commit, actor, intent):
- CIC-Schemas `poc/v1` branch-en (mint postgresql)?
- Vagy CIC-Relay embedded schema-ként?
- Vault signing szükséges?

Kérdezd le:
```
search_query("CIC-Schemas branch worktree schema compile sign")
search_query("relay embedded schema config relay.config")
```

**Relay belső modulok** (pose verifier, drift classifier, state commit writer):
- Ezek `core/nexus/` alá kerülnek (mint nexus/crypto, nexus/git, nexus/iac)?
- Vagy `core/cabinet/` alá (mint proof_trace.go)?
- Milyen meglévő Go interfészt implementálnak?

Kérdezd le:
```
search_query("nexus package relay internal components structure")
search_query("cabinet internal proof trace workflow relay")
```

### 2. Öröklési térkép

Minden új repóhoz/branch-hez definiáld:

```
[repó/branch neve]
  örököl: [honnan, mit — base-repo remote-merge? cic-primitives séma? CIC-Relay interface?]
  implementál: [milyen interfészt vagy sémát]
  betöltődik: [hogyan — native module, .so plugin, schema artifact]
  függőség: [mi kell előtte]
```

### 3. Dependency order

Melyik repó/branch melyik után jöhet létre/implementálódhat? Függőségi gráf
(topológiai sorrend — mi blokkolja mit).

### 4. Interface definíciók

Az új repókhoz szükséges Go interfészek — ezek a CIC-Relay-ben definiálandók,
az adapterek implementálják. Add meg a minimális interfész szignatúrát:

```go
// ActualStateCollector — provider adapter interface
type ActualStateCollector interface {
    Collect(ctx context.Context) (*ActualState, error)
    Provider() string
}
```

Ha a KB-ban már van erre vonatkozó definíció — hivatkozz rá (chunk ID).

---

## Output

**`jobs/poc-repo-design/output/repo-plan.md`**

Felépítés:
```
# PoC Repó Struktúra Terv

## Összefoglaló táblázat

| Repó / Branch | Típus | Örököl | Implementál | Betöltés módja |
|---|---|---|---|---|
| cic-proxmox | új repó | base-repo, CIC-Relay interface | ActualStateCollector | natív modul |
| ... | ... | ... | ... | ... |

## Öröklési térkép

[minden egységre részletes leírás]

## Dependency order

[topológiai sorrend]

## Interface definíciók

[Go interfész vázlatok KB hivatkozásokkal]

## Megjegyzések

[ahol a CIC minta alapján döntés szükséges — ne döntsd el helyettünk, jelezd]
```

---

## Git instrukciók

```bash
cd jobs/poc-repo-design/workspace/cic-factory
git add jobs/poc-repo-design/output/
git commit -m "job: poc-repo-design — repo plan"
git push origin feature/poc-repo-design
```

**Push csak `feature/poc-repo-design` branch-re. Soha ne pusholj `main`-re.**

## Nyelvi szabály

- Output fájl: **magyarul**
- Go kód, interfész definíciók: **angolul**
