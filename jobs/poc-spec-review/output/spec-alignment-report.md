# Sub-job Spec Összehangoltsági Jelentés

Ellenőrzés dátuma: 2026-06-06
KB állapot: elérhető, friss (chunks.pkl, graph_nodes.pkl, faiss.index — mind létezik)
Szülő job: `poc-implementation-plan`

---

## Összefoglaló táblázat

| Sub-job | Plugin/Modul path | Trigger | Workflow YAML | Összesített ítélet |
|---|---|---|---|---|
| poc-infra-01 | n/a (IaC scriptek, nem relay modul) | n/a | n/a | ALIGNED |
| poc-observer-plugin-01 | `CIC-Relay/core/plugins/terraform_observer/` | Nincs explicit meghatározva (relay indítja) | poc.iac.observe.yaml — lépésstruktúra részlegesen helyes | **MISALIGNED** |
| poc-drift-detection-01 | Nincs path megadva (Go kód nincs elhelyezve) | Polling (10 sec) — implicit | Nincs workflow YAML előírva | PARTIAL |
| poc-rollback-01 | `CIC-Relay/core/nexus/iac/intent_watcher.go` (nexus, nem plugin) | git push intent/main → polling watcher | Nincs workflow YAML előírva | PARTIAL |
| poc-demo-script-01 | n/a (shell scriptek) | n/a | n/a | ALIGNED |
| poc-schema-signing-01 | `CIC-Relay/core/modules/schemacompile/` (helyes natív modul path) | n/a (natív modul, nem trigger-alapú) | Nincs új workflow — meglévő schemacompile pipeline használata | ALIGNED |

---

## Részletes elemzés — poc-infra-01

### Plugin/modul elhelyezés
- Spec állítása: nem ír elő relay modult — IaC scriptek (`jobs/poc-infra-01/output/iac/`)
- KB alap: n/a
- Ítélet: **ALIGNED**
- Megjegyzés: Ez a job infrastruktúrát épít, nem relay komponenst. A path-ok a cic-factory output könyvtárába mutatnak — ez helyes.

### Trigger mechanizmus
- Spec állítása: human manuálisan futtat (`terraform init`, `vault init.sh`)
- KB alap: n/a
- Ítélet: **ALIGNED**
- Megjegyzés: Nem relay-triggerelt folyamat, ez szándékos az 8.1 fázisban.

### Workflow YAML
- Spec állítása: `relay/config.yaml` — ez relay indítási konfig, nem workflow
- KB alap: n/a
- Ítélet: **ALIGNED**
- Megjegyzés: A relay config.yaml relay indítási paramétert állít be, nem workflow-t ír elő. Helyes.

---

## Részletes elemzés — poc-observer-plugin-01

### Plugin/modul elhelyezés — KRITIKUS PROBLÉMA

- Spec állítása: `CIC-Relay/core/plugins/terraform_observer/` könyvtárban kell a Go plugin-t létrehozni
- KB alap (c899, c906): A CIC plugin interfész dokumentációja szerint a relay `.so` fájlokat tölt be `plugin.Open()` + `Lookup()` segítségével. A natív modulok (`core/modules/<név>/`) a relay-jel együtt fordulnak Go csomagként. A külső `.so` pluginek `plugin.Open()`-nal töltődnek, és a Cabinet PluginDescriptor path mezőjével hivatkoznak rájuk (c785).
- KB alap (tényleges könyvtárstruktúra): A CIC-Relay `core/` alatt két releváns alcsoport létezik:
  - `core/modules/` — natív Go modulok (schemacompile, schemapipeline, certselfsigned, cibuild)
  - `core/nexus/` — nexus komponensek (iac, git, operator, recorder stb.)
  - `core/cabinet/` — Cabinet API és plugin regisztráció
  - **`core/plugins/` — NEM LÉTEZIK a relay-ben**
- Ítélet: **MISALIGNED**
- Megjegyzés: A `core/plugins/terraform_observer/` path nem létezik és nincs KB-ban dokumentálva. Az agent, aki ezt a specet végrehajtja, rossz könyvtárba dolgozna. A helyes megközelítés a spec szándékától függ:
  - Ha `.so` pluginként akarják betölteni: a Go kód bárhol lehet, de a build outputot (`terraform_observer.so`) a Cabinet PluginDescriptor `path` mezőjével kell konfigurálni, és a relay bootstrap-nek kell regisztrálni. A forráskód elhelyezése nincs szabványosítva, de a `core/plugins/` path félrevezető, mert a relay kódbázisban nem ez a mintázat.
  - Ha natív modulként akarják (a relay-jel együtt fordul): a helyes path `core/modules/terraform_observer/`, és `registerNativeComponents`-ben kell regisztrálni (c173 alapján).
  - A spec `go build -buildmode=plugin`-t ír elő (c906 kompatibilis), tehát `.so` pluginként szándékozott. Ekkor a forráskód elhelyezése nem a `core/plugins/` — ezt a path-ot a relay kódbázis nem ismeri.

### Relay workflow YAML struktúra

- Spec állítása: `CIC-Relay/core/workflows/poc.iac.observe.yaml` helyen, a lépések:
  ```
  assert_intent  → module: cic.iac.assert@1.0
  snapshot       → module: cic.iac.snapshot@1.0
  prooftrace     → module: cic.iac.prooftrace@1.0
  commit_state   → module: cic.iac.commit@1.0
  ```
- KB alap (c259, c254): A tényleges workflow YAML struktúra:
  ```yaml
  apiVersion: relay.cic.com/v1
  kind: Workflow
  metadata:
    name: test.flow
    version: '1.0'
  spec:
    steps:
    - test.schema@1.0
  ```
  A `steps[]` elemeinek formátuma a KB-ban: `- module.name@version` (egyszerű string lista), nem `- name: ...\n  module: ...` objektum struktúra.
- KB alap (c171, WorkflowFile struct): A WorkflowFile struct `cabinet.BaseBlock`-ra hivatkozik — a lépések pontosan hogyan vannak strukturálva a YAML-ban, a két elérhető minta alapján egyszerű string lista (nem name+module objektum).
- Ítélet: **PARTIAL**
- Megjegyzés: A spec `name: + module:` objektum struktúrát ír le a lépéseknél, de a KB-ban dokumentált és tesztelt YAML-ok egyszerű string listaként definiálják a lépéseket (`- module.name@version`). Ez eltérés, de lehet, hogy a WorkflowFile struct mindkettőt kezeli — KB-ból nem verifikálható egyértelműen. A `core/workflows/` path szintén nem verifikálható a KB-ból (a tesztadat `cmd/relay/testdata/workflows/`-ban van). A modul nevek (`cic.iac.assert@1.0` stb.) nem léteznek a KB-ban — ezek új modulok lennének.

### ProofTrace generálás

- Spec állítása: `chain_hash`: SHA-256(sourceDigest + workflowID + per-step hashes), `steps[]` input_hash + output_hash, `commit_record` actor/trace_head/pose_root, `pose_result: "SKIPPED"`
- KB alap (c263, proof_artifact.schema.yaml): A proof_artifact@1.0 schema pontosan ezt a struktúrát írja le:
  - `chain_hash`: SHA-256 over sourceDigest + workflowID + per-step (name, module, inputHash, outputHash) ✓
  - `steps[]`: name, module, input_hash, output_hash — mind kötelező ✓
  - `commit_record`: actor, id, pose_root, trace_head ✓ (a spec `commit_record.id` mezőt nem említ — ez PARTIAL)
  - `pose_result`: VERIFIED | DRIFT | SKIPPED ✓
- Ítélet: **ALIGNED** (a `commit_record.id` mező hiányzik a spec leírásából, de ez kisebb hiány)

### OIS obligation check

- Spec állítása: v1-ben stub (ALLOWED always), de a struktúra legyen kész
- KB alap (c2498): OIS(actor, action, context) formális modell — intent vs. obligation szétválasztás kötelező. Stub helyes v1-ben.
- Ítélet: **ALIGNED**

### Trigger mechanizmus

- Spec állítása: Nincs explicit trigger. A plugin betöltése relay-ből történik, de hogy mikor hívja a relay a `ObserveState` függvényt, nem derül ki.
- KB alap: A relay `/set` végpontján keresztül hívható a workflow (c286, API.Set metódus). Ki hívja a `poc.iac.observe` workflow-t a `/set` végponton?
- Ítélet: **PARTIAL**
- Megjegyzés: A spec nem határozza meg, mi triggereli az observe workflow-t a relay `/set` végpontján. Ez hiányos, de a PoC-ban human manuálisan triggerelheti — ezt pontosítani kellene.

---

## Részletes elemzés — poc-drift-detection-01

### Plugin/modul elhelyezés

- Spec állítása: Go kód (`DetectDrift` függvény), de nincs meghatározva, hogy hova kerül a forráskód.
- KB alap: n/a — a spec nem ad path-ot
- Ítélet: **PARTIAL**
- Megjegyzés: A spec Go kódot mutat be, de nem mondja meg, hogy natív modulba (`core/modules/`) vagy external `.so` pluginbe kerül. Ez a következő agentnek döntési pontot hagy — ami félrevezető. Konzisztens lenne az `poc-observer-plugin-01`-gyel (ott `.so` plugin), de ez nincs kimondva.

### Trigger mechanizmus

- Spec állítása: Periodic polling (10 sec interval), Proxmox API lekérdezés
- KB alap (c579, PollingWatcher): A `core/nexus/operator/watcher.yaml`-ban `PollingWatcher` struct létezik, ami periodikusan scanol könyvtárat. Ez az architektúra konzisztens a drift detection pollinggal.
- Ítélet: **ALIGNED**
- Megjegyzés: A polling mechanizmus létezik a nexus/operator-ban. A spec azonban nem mondja meg, melyik relay komponens futtatja a polling logikát — nexus operator-ba integrálva, vagy önálló goroutine?

### Drift típusok

- Spec állítása: `SOFT_DRIFT`, `RECONCILIABLE_DRIFT`, `HARD_DRIFT` típusok, `DetectDrift` függvény c2543 alapján
- KB alap (c2543): `NO_DRIFT`, `RECONCILIABLE_DRIFT`, `HARD_DRIFT` — a KB-ban `SOFT_DRIFT` NEM szerepel a drift diagnózis kimenetei között a c2543-ban.
- KB alap (c1815): `Soft drift`, `Reconcilable`, `Hard drift` — itt igen, de `SOFT_DRIFT` mint enum érték nincs a KB diagnosis logikájában.
- Ítélet: **PARTIAL**
- Megjegyzés: A spec a `DetectDrift` függvényben 3 ágat kezel: `NO_DRIFT`, `RECONCILIABLE_DRIFT`, `HARD_DRIFT` — ez egyezik a c2543 logikájával. A `SOFT_DRIFT` konstans a `DriftType` enum-ban megjelenik a specben mint lehetséges érték a commit JSON-ban, de a diagnózis logikában nincs explicit ág rá. Ez kisebb inkonzisztencia a spec szövegén belül.

### ProofTrace lánc folytonosság

- Spec állítása: HARD_DRIFT után az utolsó érvényes CommitRef megmarad (nem nullázódik)
- KB alap (c1823, c2436): A commit record append-only, a `prev` mező az előző trace-re mutat — a lánc folytonosságát ez biztosítja.
- Ítélet: **ALIGNED**

---

## Részletes elemzés — poc-rollback-01

### Plugin/modul elhelyezés

- Spec állítása: `CIC-Relay/core/nexus/iac/intent_watcher.go` — az `intent_watcher.go` a nexus/iac-ba kerül
- KB alap: A `core/nexus/iac/` könyvtár létezik (tényleges filesystem ellenőrzés). Az `UpstreamSource` (c523) és a `source_upstream.yaml` ott van. A nexus/iac Go kódja (`IaCSource` interface, `source_file.yaml`, c514) ebben a csomagban van.
- Ítélet: **ALIGNED**
- Megjegyzés: A nexus/iac helyes helyszín egy IaC-forrás-figyelő komponensnek. Ez nem plugin (`.so`), hanem natív Go kód a relay-ben — összhangban a nexus architektúrával.

### Trigger mechanizmus

- Spec állítása: Human: `git merge state/commit-3-ref` + `git push intent/main` → CIC intent/ ág polling (5 sec, git fetch + diff) → OIS check → terraform apply
- KB alap (c579, PollingWatcher): Polling mechanizmus létezik.
- KB alap (c286, API.Set): A relay `/set` végpontja a belépési pont séma-ellenőrzéshez és workflow futtatáshoz.
- Ítélet: **PARTIAL**
- Megjegyzés: A spec az `intent_watcher.go`-t önálló polling goroutine-ként írja le, de nem derül ki, hogyan kapcsolódik a relay Cabinet API-hoz. Az intent észlelése után hogyan kerül sor a `/set` hívásra (ha egyáltalán)? Ez nem ellentétes a KB-val, de hiányos specifikáció.

### OIS obligation check

- Spec állítása: `CheckObligation(actor, action, policy)` — v1 demo policy: ALLOWED ha actor == "relay-operator" && action == "rollback"
- KB alap (c2498): OIS formális modell — intent és obligation szétválasztása kötelező. A spec ezt helyesen alkalmazza.
- Ítélet: **ALIGNED**

### ProofTrace — rollback commit

- Spec állítása: `commit_record.trace_head` visszautal a #3 CommitRef-re
- KB alap (c263, c1823): `commit_record.trace_head` = ProofTrace event ID — a spec helyes módon hivatkozik vissza.
- KB alap (c263): `commit_record.id` = State hash (equals chain_hash for committed states) — a spec rollback ProofTrace JSON-jában `commit_record.id` mező nem szerepel.
- Ítélet: **PARTIAL**
- Megjegyzés: A rollback ProofTrace JSON-jából hiányzik a `commit_record.id` mező, ami a c263 schema szerint `chain_hash`-nek kell egyeznie. Ez kisebb kihagyás, de az implementáló agent eltekinthet tőle ha a sémát nem ismeri.

---

## Részletes elemzés — poc-demo-script-01

### Plugin/modul elhelyezés

- Spec állítása: Shell scriptek (`run-demo.sh`, `tmux-layout.sh`, `show-commit.sh`) a job output könyvtárában
- KB alap: n/a
- Ítélet: **ALIGNED**

### Trigger mechanizmus

- Spec állítása: `run-demo.sh` manuálisan futtatja a fázisokat, fázisok között 30 sec szünet
- KB alap: n/a
- Ítélet: **ALIGNED**

### Workflow YAML

- Spec állítása: nincs előírt relay workflow YAML — csak shell orchestráció
- KB alap: n/a
- Ítélet: **ALIGNED**

### `git verify-commit` — konzisztencia ellenőrzés

- Spec állítása: `git verify-commit HEAD` eredmény megjelenítése minden CommitRef-nél
- KB alap (c728, commit-signing): A relay Vault-alapú commit signing koncepcióval rendelkezik.
- Ítélet: **ALIGNED**
- Megjegyzés: A script feltételezi, hogy a state/ ág commitjai GPG/SSH-aláírással rendelkeznek. Ez a GitStateRecorder implementációtól függ.

---

## Részletes elemzés — poc-schema-signing-01

### Plugin/modul elhelyezés

- Spec állítása: `CIC-Relay/core/modules/schemacompile/schemacompile.go` módosítása
- KB alap (c442): A `schemacompile` csomag ténylegesen `core/modules/schemacompile/`-ban van, és pontosan ezt a három modult implementálja:
  - `cic.source.assert@1.0` (Layer 1 stub)
  - `cic.schema.build@1.0` (Layer 0.2)
  - `cic.artifact.sign@1.0` (Layer 2 — Vault signing)
- Ítélet: **ALIGNED**

### Vault integráció

- Spec állítása: `NewSignArtifactFunc` signer paraméter bekötése valós Vault kliensre, `cic_sign` = Vault-aláírt `build_hash`, `cic_signed_ca` = CICSourceCA cert chain PEM
- KB alap (c442): A `NewSignArtifactFunc` pontosan ezt a mechanizmust implementálja — `ArtifactSigner` interface, `nil` esetén stub mód. A `CertVerifyFunc` szintén létezik a csomagban.
- Ítélet: **ALIGNED**

### schemapipeline tesztelés

- Spec állítása: A négy lépéses pipeline (c453) futtatása docker alapon: `cic.pipeline.start → cic.pipeline.test → cic.pipeline.validate → cic.pipeline.release`
- KB alap (c453): Ez pontosan a schemapipeline csomag által implementált négy natív relay modul sorrend. A release output `cic.source.assert@1.0` inputja lesz.
- Ítélet: **ALIGNED**

### Trigger mechanizmus

- Spec állítása: nem trigger-alapú — a job Vault backend setup + Go kód módosítás
- KB alap: n/a
- Ítélet: **ALIGNED**

---

## KB alapú általános megállapítások

### A relay kétféle modulrendszere

A KB alapján (c899, c906, c442, c173) a relay modul architektúrája:

1. **Natív modul** (`core/modules/<név>/`): Go csomag, a relay-jel együtt fordul, `registerNativeComponents`-ben kerül regisztrálásra. Példák: schemacompile, schemapipeline, certselfsigned, cibuild.
2. **Külső `.so` plugin**: `plugin.Open()` + `Lookup()` segítségével töltődik be, `PluginDescriptor.path`-ban van hivatkozva (c785). A forráskód elhelyezése nincs szabványosítva a KB-ban, de a relay-en belüli `core/plugins/` path NEM létezik.

### Workflow YAML formátum

A KB-ban dokumentált és tesztelt YAML formátum (c259, c254):
```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: <name>
  version: '1.0'
spec:
  steps:
  - module.name@version
```
A `poc-observer-plugin-01` spec `name: + module:` objektum struktúrát ír le a steps-ben — ez nem egyezik a tesztadatokkal.

### proof_artifact@1.0 schema (c263)

Kötelező mezők: `workflow_id`, `source_digest`, `chain_hash`, `steps[]`, `timestamp`.
`commit_record.id` = chain_hash — ezt több spec nem tartalmazza.
`pose_result` enum: VERIFIED | DRIFT | SKIPPED (nem SKIPPED_v1 vagy hasonló).
