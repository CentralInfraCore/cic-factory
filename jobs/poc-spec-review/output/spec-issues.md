# Spec hibák — javítandó input.md-k

Ez a fájl kizárólag a `MISALIGNED` ítéletű speceket tartalmazza, illetve az egyéb specek komoly (`PARTIAL`) pontjait amelyek a következő agent munkáját meghiúsíthatják.

---

## poc-observer-plugin-01 — Plugin path: `core/plugins/` nem létezik

### Mi a hiba

A spec `CIC-Relay/core/plugins/terraform_observer/` könyvtárba írja elő a Go plugin forráskódját. Ez a path nem létezik a CIC-Relay kódbázisban és nincs KB-ban dokumentálva.

### Hibás sor a specben

```
`CIC-Relay/core/plugins/terraform_observer/` könyvtárban:
```

### Helyes megközelítés KB alapján

**c906** (plugin_interface.md): A relay `.so` fájlokat tölt be `plugin.Open()` + `Lookup()` segítségével. A `go build -buildmode=plugin` helyes — ez `.so` típusú plugint jelent.

**c785** (Cabinet_Specification.md): A PluginDescriptor `path` mezője a `.so` fájl elérési útját tartalmazza. A relay runtime a Cabinet descriptor alapján tölti be a plugint — nem a forráskód helye, hanem a build output `.so` fájl helye számít.

**c173** (bootstrap.yaml, registerNativeComponents): A natív modulok `core/modules/` alá kerülnek és `registerNativeComponents`-ben regisztrálódnak. Ha natív modult akar a spec, a helyes path: `CIC-Relay/core/modules/terraform_observer/`.

**Tényleges relay könyvtárstruktúra** (filesystem ellenőrzés alapján):
```
CIC-Relay/core/
  cabinet/        — Cabinet API és plugin regisztráció
  modules/        — natív Go modulok (schemacompile, schemapipeline, certselfsigned, cibuild)
  nexus/          — nexus komponensek (iac, git, operator, recorder, ...)
```
`core/plugins/` — NEM LÉTEZIK.

### Hatás

Ha egy agent ezt a specet végrehajtja, `CIC-Relay/core/plugins/terraform_observer/` könyvtárat hoz létre, ami nem illeszkedik a relay kódbázis struktúrájába. A relay bootstrap nem fogja megtalálni és regisztrálni a modult.

### Javasolt javítás

Az `input.md` érintett részét az alábbira kell módosítani (az architektúra döntéstől függően két opció):

**A opció — külső `.so` plugin (az eredeti szándék szerint):**
```
### 1. Go plugin (.so)

A plugin forráskódja az agent munkakörnyezetében, pl. `iac-plugins/terraform_observer/` könyvtárban:

```go
// go build -buildmode=plugin -o terraform_observer.so .
func ObserveState(input json.RawMessage) (json.RawMessage, error)
```

A build output (`terraform_observer.so`) a relay bootstrap konfigurációjában regisztrálódik
PluginDescriptor-on keresztül. A `.so` fájl elhelyezése a relay config szerint.
```

**B opció — natív modul (ha a relay-jel együtt kell fordulnia):**
```
### 1. Natív relay modul

`CIC-Relay/core/modules/terraform_observer/` könyvtárban:

```go
// Natív modul — registerNativeComponents-ben regisztrálódik
func ObserveState(input json.RawMessage) (json.RawMessage, error)
```
```

---

## poc-observer-plugin-01 — Workflow YAML lépés struktúra eltérés

### Mi a hiba

A spec a workflow YAML `steps[]` elemeit `name: + module:` objektum struktúraként írja le. A KB-ban dokumentált és tesztelt workflow YAML-ok egyszerű string listaként definiálják a lépéseket.

### Hibás rész a specben

```yaml
spec:
  steps:
    - name: assert_intent
      module: cic.iac.assert@1.0
    - name: snapshot
      module: cic.iac.snapshot@1.0
```

### Helyes megközelítés KB alapján

**c259** (test_workflow.yaml):
```yaml
spec:
  steps:
  - test.schema@1.0
```

**c254** (order.workflow.yaml):
```yaml
spec:
  steps:
  - 'run: user'
```

A steps formátuma string lista. Ha a WorkflowFile struct (c171) elfogad objektum struktúrát is, ezt a KB nem igazolja — az agent rossz YAML-t hozna létre, amit a relay nem tud értelmezni.

### Hatás

A relay a workflow YAML parse-olásakor hibát dobhat, ha a steps formátum nem egyezik a WorkflowFile struct elvárásával.

### Javasolt javítás

```yaml
spec:
  steps:
  - cic.iac.assert@1.0
  - cic.iac.snapshot@1.0
  - cic.iac.prooftrace@1.0
  - cic.iac.commit@1.0
```

Ha a step-eknek name-re is szükségük van, ezt a WorkflowFile struct forráskódjából kell ellenőrizni (nem csak KB-ból).

---

## poc-observer-plugin-01 — `commit_record.id` mező hiánya a ProofTrace JSON-ban

### Mi a hiba

A spec a ProofTrace `commit_record`-ban nem tartalmazza az `id` mezőt.

### Hibás rész a specben

```go
"commit_record": {
    "actor": actor,
    "trace_head": "<prooftrace_id>",
    "pose_root": "<new_pbs_hash>"
}
```

### Helyes megközelítés KB alapján

**c263** (proof_artifact.schema.yaml):
```yaml
commit_record:
  id:
    description: State hash (equals chain_hash for committed states).
    type: string
  actor: ...
  trace_head: ...
  pose_root: ...
```

A `commit_record.id` = chain_hash a committed state esetén. Ez kötelező mező a sémában.

### Hatás

Ha az agent a specben szereplő struktúrát implementálja, a `VerifyProofArtifact` (c246) ellenőrzése sikertelen lehet — a `commit_record.id == chain_hash` feltétel nem teljesül.

### Javasolt javítás

```go
"commit_record": {
    "id": "<chain_hash>",  // = chain_hash mező értéke
    "actor": actor,
    "trace_head": "<prooftrace_id>",
    "pose_root": "<new_pbs_hash>"
}
```

Ez vonatkozik a `poc-rollback-01` specben szereplő rollback ProofTrace JSON-ra is.

---

## poc-drift-detection-01 — Go kód elhelyezése nincs meghatározva

### Mi a hiba

A spec Go kódot (`DetectDrift`, PBS polling logika) mutat be, de nem mondja meg, hova kerül a forráskód és milyen komponens kontextusában fut.

### Hiányos rész a specben

A spec csak a Go kód logikáját írja le, de nem definiálja:
- Natív relay modul (`core/modules/`) vs. nexus komponens (`core/nexus/`) vs. önálló service
- Regisztrálás módja a relay-ben

### Hatás

Az agent saját belátása szerint helyezi el a kódot — inkonzisztencia a relay architektúrával.

### Javasolt javítás

Explicit elhelyezés meghatározása, pl.:
```
A drift detekció logikája a `CIC-Relay/core/nexus/iac/drift_detector.go` fájlba kerül,
mint a nexus/iac csomag része. Nem önálló relay modul — a poc-observer-plugin-01
által létrehozott observer hívja közvetlenül.
```

---

## poc-rollback-01 — `commit_record.id` hiánya a rollback ProofTrace-ban

### Mi a hiba

A rollback ProofTrace JSON-jából hiányzik a `commit_record.id` mező (ugyanaz a probléma mint poc-observer-plugin-01-ben).

### Hibás rész a specben

```json
{
  "commit_record": {
    "id": "<chain_hash>",
    ...
  }
}
```

Megjegyzés: a spec tartalmazza az `"id": "<chain_hash>"` sort — ez rendben van! A poc-rollback-01 specben ez a mező jelen van. Fenti hibaleírás csak a poc-observer-plugin-01-re vonatkozik.

### Ítélet felülvizsgálat

A poc-rollback-01 rollback ProofTrace JSON-ja (a spec 4. pontjában) tartalmazza:
```json
"commit_record": {
    "id": "<chain_hash>",
    "trace_head": "<prooftrace_id>",
    "pose_root": "<new_pbs_hash>"
}
```
Ez **helyes** — ALIGNED a c263 sémával. (Az actor mező hiányzik — PARTIAL, de nem kritikus.)

---

## Összefoglalás — kritikusság szerint

| Hiba | Sub-job | Súlyosság | Az agent hibát követ el ha... |
|---|---|---|---|
| `core/plugins/` nem létezik | poc-observer-plugin-01 | **KRITIKUS** | rossz könyvtárba ír, relay nem találja a modult |
| Workflow YAML steps formátum eltérés | poc-observer-plugin-01 | **MAGAS** | relay nem tudja parse-olni a workflow-t |
| `commit_record.id` hiánya | poc-observer-plugin-01 | **KÖZEPES** | VerifyProofArtifact ellenőrzés sikertelen |
| Go kód elhelyezés nincs meghatározva | poc-drift-detection-01 | **KÖZEPES** | ad-hoc elhelyezés, inkonzisztens architektúra |
