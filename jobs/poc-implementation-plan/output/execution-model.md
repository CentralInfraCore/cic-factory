# Végrehajtási modell — CIC PoC demonstráció

KB alapok: c900, c912, c914, c927, c940, c943, c947, c899, c2589, c2436, c263, c2616, c2498, c2543, c2618, c1312, c442, c453, c189

---

## 1. A relay pontos pozíciója

A relay **sémaérzékeny végrehajtási csomópont** (c2589), amely:

- nem tartalmaz állapotgépet, nem tárol adatot, nem tanul, nem hoz döntést (c912)
- nem hajt végre kódot közvetlenül, nem ír fájlt, nem módosít konfigurációt (c914)
- végrehajtja a deklarált műveleti gráfot, kiértékeli a függőségeket, pluginokon keresztül hívja a műveleteket, `NextHops` szerint halad (c912)
- axiom: nem szűrhet, csak továbbíthat és validálhat (c2114)

**Következmény a PoC-ra:** a relay a demonstráció egyetlen fázisában sem a „tettes" — minden fizikai infrastruktúra-műveletet vagy a human (Terraform), vagy az általa meghívott plugin végez. A CIC megfigyel, rögzít és igazol.

---

## 2. Végrehajtási lánc fázisanként

```
add.md demo lépés → [ki indítja?] → relay workflow → plugin (.so / WASM) → ProofTrace
```

### 8.1 fázis — Terraform up (Infrastruktúra felhúzása)

```
Human → terraform apply
  ↓ (Terraform elvégzi a fizikai provizionálást)
CIC Observer:
  → OIS-Intent deklaráció rögzítése (actor, action, policy)
  → OIS(actor, action, context) ellenőrzés (c2498)
  → ProofTrace esemény létrehozása:
       id = SHA-256(payload), prev=null, signature=actor_key
       { actor, intent, schemaRef, payload, canonicalHash, signature, ts } (c2436)
  → GitStateRecorder commit → state/ ág:
       infra.tf.json (desired)
       actual_state.json (PBS snapshot)
       prooftrace.json
  → CommitRef #1 (c2616)
```

**CIC szerepe: OBSERVER + RECORDER** — a Terraformot a human futtatja. A CIC az eredményt rögzíti.

---

### 8.2 fázis — Kézi módosítások (drift keletkezése)

```
Human → kézi módosítás (szabály, erőforrás, konfig)
  ↓
CIC Observer:
  → PBS (Physical Base State) gyökér-hash olvasása
  → Drift diagnózis (c2543):
       if canonical_state(prooftrace) == pbs_root_hash → NO_DRIFT
       else if derivable_diff(prooftrace, pbs) → RECONCILIABLE_DRIFT
       else → HARD_DRIFT
  → state/ ág új commit:
       drift: true | false
       drift_type: SOFT_DRIFT | RECONCILIABLE_DRIFT
       actual_state.json (frissített)
       ProofTrace lánc folytatása (prev = előző id)
```

**CIC szerepe: OBSERVER + RECORDER** — minden egyes kézi beavatkozás automatikusan auditált eseménnyé válik. A CIC nem avatkozik be, csak rögzít.

Drift osztályok (c1815):
| Típus | Leírás | Reakció |
|---|---|---|
| SOFT_DRIFT | ideiglenes eltérés | wait and retry |
| RECONCILIABLE | javítható ismert flow-val | repair workflow |
| HARD_DRIFT | strukturális divergencia | escalation |

---

### 8.3 fázis — Infrastruktúra törlése (Hard Drift)

```
Human → terraform destroy (vagy kézi törlés)
  ↓
CIC Observer:
  → PBS gyökér-hash = null (fizikailag semmi nem létezik)
  → HARD_DRIFT rögzítése:
       canonical_state(prooftrace) ≠ derivable(pbs=null)
  → state/ ág commit:
       drift: true, drift_type: HARD_DRIFT
       actual_state.json: {} (üres)
       ProofTrace lánc: utolsó érvényes CommitRef megmarad
```

**CIC szerepe: OBSERVER + RECORDER** — a törlést a human hajtja végre. A CIC „nem felejt": a lánc utolsó igazolt CommitRef-je megmarad, a törlés is commitált tény.

---

### 8.4 fázis — Rollback (Intent deklarálása + Terraform apply)

```
Human → git merge state/commit-3-ref → intent/main → git push

CIC Actor:
  → intent/ ág push észlelése (GitSource figyelő)
  → OIS ellenőrzés:
       intent    = "restore to commit-3 state"
       obligation = check(actor, policy, time)
       if ALLOWED → state' = reduce(state, intent)
                    trace  = ProofTrace(intent, obligation, state')
       else → ERROR(PERMISSION_DENIED) (c2498)
  → Ha engedélyezett: Terraform apply triggerelése a meghatározott állapot alapján
  → Új ProofTrace: CommitRef visszautal #3-ra
```

**CIC szerepe: ACTOR** — ez az egyetlen fázis, ahol a CIC aktívan beavatkozik. Az OIS-ellenőrzés után a rendszer triggereli a Terraform apply-t.

**Összefoglalás:**

| Fázis | Ki csinálja a fizikai műveletet | CIC szerepe |
|---|---|---|
| 8.1 Terraform up | Human (terraform apply) | Observer + Recorder |
| 8.2 Kézi módosítások | Human (direkt infra változtatás) | Observer + Recorder |
| 8.3 Infra törlés | Human (terraform destroy) | Observer + Recorder |
| 8.4 Rollback | CIC triggereli Terraformot | **Actor** (OIS-engedély után) |

---

## 3. Primitívek és schema rendszer

### BaseBlock / relay schema mező-minta

A relay a `StateRequirement`, `Dependencies`, `PluginRef`, `NextHops` mezők alapján vezérli a végrehajtást (c927):

```yaml
# Minta: egy relay workflow lépés felépítése
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: cic.iac.observe
  version: "1.0"
spec:
  steps:
    - name: assert_source
      module: cic.source.assert@1.0    # PluginRef
      StateRequirement: source_ready
      Dependencies: []
      NextHops:
        - build_schema
    - name: build_schema
      module: cic.schema.build@1.0
      StateRequirement: assert_ok
      Dependencies: [assert_source]
      NextHops:
        - sign_artifact
    - name: sign_artifact
      module: cic.artifact.sign@1.0
      StateRequirement: build_ok
      Dependencies: [build_schema]
      NextHops: []
```

Valós példa (c189 — beágyazott workflow):
```yaml
# cic.schema.compile workflow
steps:
  - cic.source.assert@1.0.assert(input) -> assert_result
  - cic.schema.build@1.0.build(assert_result) -> artifact
  - cic.artifact.sign@1.0.sign(artifact) -> signed_artifact
```

### ManagedEntity primitív (c2801)

Minden domain objektum (VM, hálózat, storage) a `ManagedEntity` aggregát-primitívből specializálódik:

- `identity` (required) — típusazonosság, kind/namespace/version
- `config_surface` (required) — írható desired state
- `state_surface` (required) — csak olvasható actual state
- `operation_surface` (defaulted) — végrehajtható műveletek
- `policy_surface` (defaulted) — jogosultsági szabályok
- `lifecycle_surface` (sealed) — create → active → degraded → terminating → terminated

### CIC-Schemas signing workflow (c1312, c442, c453)

```
CIC-Schemas repo → make release VERSION=v1.0.0
  ↓ schemapipeline (relay workflow):
  cic.pipeline.start@1.0    — git clone + tree_digest
  cic.pipeline.test@1.0     — make test (container)
  cic.pipeline.validate@1.0 — make validate (container)
  cic.pipeline.release@1.0  — make release → signed_artifact
  ↓
  cic.source.assert@1.0     — cert verifikáció (CICDeveloperCA)
  cic.schema.build@1.0      — schema build
  cic.artifact.sign@1.0     — Vault signing → cic_sign + verification_root
```

Az aláírt artifact mezői: `build_hash`, `cic_sign`, `cic_signed_ca`, `verification_root` (Merkle-gyök).

**Jelenlegi állapot:** `cic_sign = "unavailable"` ha Vault nincs bekötve (stub mode — scaffold). `verification_root` mindig érvényes.

---

## 4. Plugin betöltési mechanizmus

### Go .so plugin (aktuális, implemented)

```go
// A relay plugin.Open() + Lookup() segítségével tölti be (c906)
plugin.Open("./plugins/terraform_observer.so")
plugin.Lookup("ObserveState")
```

- `go build -buildmode=plugin` → `.so` fájl
- Exportált függvények pontos szignatúrával
- Stateless: nincs belső állapot, nincs külső kapcsolat (c900)

### WASM iSDK (scaffold/concept, v2+)

- iSDK (guest): WASM modulba linkelt könyvtár, elrejti ABI-t (c943)
- Host keret: WASM-hívássá alakítja a diszpécser hívásait, kezeli timeout/limit/séma-validációt (c943)
- API-szerződés (c947):

```
Call(op: "init"|"process"|"get"|"notify",
     auth_context_json: JSON,
     data_json: JSON)
  -> (data_json: JSON, error_json: JSON|null)
```

v1: szinkron hívás, WASI off, `notify` stub. v2-ben async.

---

## 5. ProofTrace struktúra

```
ProofTrace = {
  id:           SHA-256(payload),
  actor:        identity,
  intent:       OIS intent deklaráció,
  schemaRef:    schema azonosító,
  payload:      esemény adat,
  canonicalHash: determinisztikus hash,
  signature:    actor privát kulcsával aláírt,
  prev:         előző trace id (lánc),
  ts:           RFC3339 timestamp
}
```
(c2436)

A proof_artifact schema (c263) a relay workflow-ok kimenetét rögzíti:
- `chain_hash`: SHA-256 over sourceDigest + workflowID + per-step hashes
- `steps[]`: name, module, input_hash, output_hash
- `commit_record`: ProofTrace anchor + PBS root hash + PoSE eredmény
- `pose_result`: VERIFIED | DRIFT | SKIPPED
