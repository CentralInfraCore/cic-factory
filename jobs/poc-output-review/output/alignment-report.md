# Összehangoltsági Jelentés — poc-implementation-plan

## Összefoglaló

| Ítélet | Darabszám |
|---|---|
| ALIGNED | 22 |
| PARTIAL | 3 |
| MISALIGNED | 1 |
| UNVERIFIABLE | 3 |

**Általános értékelés:** Az 5 output fájl összességében erős KB-konzisztenciát mutat. Az állítások nagy része közvetlen KB chunk-referenciával alátámasztott, és a háromszintű státusz (implemented/scaffold/concept) helyesen van alkalmazva. Egy MISALIGNED állítás azonosítható: az execution-model.md `c2114`-re hivatkozva azt írja, hogy a relay "axiom: nem szűrhet, csak továbbíthat és validálhat" — de ez az axiom a KB-ban helyesen áll, az output viszont kihagyja a relay KB-beli forwarding/routing szerepét (c2589). Három PARTIAL eset főként terminológiai és kiemelési eltérés. Három UNVERIFIABLE állítás olyan területeket érint, amelyek az add.md specifikációból erednek, de nincsenek KB node-ban rögzítve.

---

## Ellenőrzött állítások

### 1. Relay pozicionálás és architektúra

- Állítás (forrás: execution-model.md):
  > "A relay sémaérzékeny végrehajtási csomópont (c2589), amely: nem tartalmaz állapotgépet, nem tárol adatot, nem tanul, nem hoz döntést (c912); nem hajt végre kódot közvetlenül, nem ír fájlt, nem módosít konfigurációt (c914)"
- KB alap: `search_query("relay execution model plugin stateless")` → c912, c914
- Ítélet: **ALIGNED**
- Megjegyzés: c912 szó szerint tartalmazza ezeket a pontokat. c914 szintén pontos. Az output az „állapotgép" hiányát is rögzíti, amely c912-ben explicit.

---

- Állítás (forrás: execution-model.md):
  > "végrehajtja a deklarált műveleti gráfot, kiértékeli a függőségeket, pluginokon keresztül hívja a műveleteket, NextHops szerint halad (c912)"
- KB alap: c912
- Ítélet: **ALIGNED**
- Megjegyzés: c912 szövege pontosan ezt tartalmazza.

---

- Állítás (forrás: execution-model.md):
  > "axiom: nem szűrhet, csak továbbíthat és validálhat (c2114)"
- KB alap: c2114 (`./source/CentralInfraCore/CIC-basic-knowledge/docs/hu/concept/cictor_model/axioms.md`)
- Ítélet: **PARTIAL**
- Megjegyzés: Az axiom a KB-ban valóban létezik és pontosan így hangzik. Azonban a c2589 (relay általános definíciója) azt is rögzíti, hogy a relay "továbbítja az eredményt más komponensek (pl. állapotfigyelő, generátor) felé" — ez az eredmény-továbbítási/routing szerep az output relay-definíciójából hiányzik, és a c2589-es hivatkozás az execution-model.md 1. pontjában csak a "sémaérzékeny végrehajtási csomópont" definícióra utal, nem az eredmény-továbbítási szerepre. Az axiom-hivatkozás önmagában helyes.

---

### 2. ProofTrace struktúra

- Állítás (forrás: execution-model.md, status-matrix.md):
  > "ProofTrace = { id, actor, intent, schemaRef, payload, canonicalHash, signature, prev, ts }; id = SHA-256(payload) (c2436)"
- KB alap: `search_query("ProofTrace chain_hash signature")` → c2436
- Ítélet: **ALIGNED**
- Megjegyzés: c2436 szövege pontosan ezt a struktúrát írja le, az összes mező névvel és sorrendben megegyezik.

---

- Állítás (forrás: execution-model.md):
  > "proof_artifact schema (c263): chain_hash: SHA-256 over sourceDigest + workflowID + per-step hashes; steps[]: name, module, input_hash, output_hash; commit_record: ProofTrace anchor + PBS root hash + PoSE eredmény; pose_result: VERIFIED | DRIFT | SKIPPED"
- KB alap: c263 (proof_artifact.schema.yaml)
- Ítélet: **ALIGNED**
- Megjegyzés: c263 YAML séma tartalmaz minden felsorolt mezőt, az enum értékek (`VERIFIED | DRIFT | SKIPPED`) szó szerint egyeznek. A chain_hash leírása (`SHA-256 over: sourceDigest + workflowID + per-step (name, module, inputHash, outputHash)`) szintén pontos.

---

### 3. Relay workflow vezérlés — StateRequirement / Dependencies / PluginRef / NextHops

- Állítás (forrás: execution-model.md):
  > "A relay a StateRequirement, Dependencies, PluginRef, NextHops mezők alapján vezérli a végrehajtást (c927)"
- KB alap: `search_query("BaseBlock StateRequirement PluginRef NextHops")` → c927
- Ítélet: **ALIGNED**
- Megjegyzés: c927 szó szerint: "kiértékeli a StateRequirement mezőt", "ellenőrzi a Dependencies-t", "meghívja a PluginRef-hez tartozó plugin függvényt", "a NextHops mező szerint folytatja a végrehajtást".

---

### 4. WASM iSDK modell

- Állítás (forrás: execution-model.md, status-matrix.md):
  > "iSDK (guest): WASM modulba linkelt könyvtár, elrejti ABI-t (c943); Host keret: WASM-hívássá alakítja a diszpécser hívásait, kezeli timeout/limit/séma-validációt (c943)"
- KB alap: `search_query("WASM iSDK host frame guest")` → c940, c943
- Ítélet: **ALIGNED**
- Megjegyzés: c943 szó szerint: "iSDK (guest/wasm oldali SDK): a WASM modulba linkelt könyvtár... Elrejti a memóriakezelést és az ABI-t", "Host keret: a diszpécser hívásait WASM-hívássá alakítja; kezeli a modul betöltését, a szinkron hívást, a limiteket és a séma-validációt". Pontos egyezés.

---

- Állítás (forrás: execution-model.md):
  > "API-szerződés (c947): Call(op: 'init'|'process'|'get'|'notify', auth_context_json, data_json) -> (data_json, error_json); v1: szinkron hívás, WASI off, notify stub. v2-ben async."
- KB alap: c947
- Ítélet: **ALIGNED**
- Megjegyzés: c947 tartalmazza az összes op nevet, az egységes szignatúrát, a v1 szinkron és WASI-off kikötést, és a notify stub jelleget. Pontos egyezés.

---

- Állítás (forrás: status-matrix.md):
  > "WASM iSDK (host+guest): concept | c940, c943, c947 | API-szerződés dokumentált, v1 szinkron spec kész — runtime nincs"
- KB alap: c940 (chunk title only — "WASM iSDK — Host és Guest koncepció (v1)"), c943, c947
- Ítélet: **ALIGNED**
- Megjegyzés: A státusz (concept) helyes: a KB ezeket dokumentált specifikációként tartalmazza, Go runtime implementáció nem szerepel a KB-ban.

---

### 5. OIS formális modell

- Állítás (forrás: execution-model.md, status-matrix.md):
  > "OIS(actor, action, context) := let intent = declare(actor, action); let obligation = check(actor, context.policy, context.time); if obligation == ALLOWED → state' = reduce(state, intent); trace = ProofTrace(intent, obligation, state'); else → ERROR(PERMISSION_DENIED) (c2498)"
- KB alap: c2498
- Ítélet: **ALIGNED**
- Megjegyzés: c2498 szó szerint tartalmazza ezt a formális modellt. Az intent/obligation szétválasztás megjegyzése ("nem ugyanaz") szintén KB-ban rögzített.

---

- Állítás (forrás: status-matrix.md):
  > "OIS policy motor (obligation check): concept | c2498 | formális modell kész, runtime obligation engine nincs implementálva"
- KB alap: c2498
- Ítélet: **ALIGNED**
- Megjegyzés: c2498 formális modellként van dokumentálva, runtime implementációra utaló kódreferencia nem szerepel a KB-ban.

---

### 6. Drift osztályozás

- Állítás (forrás: execution-model.md):
  > "Drift osztályok (c1815): SOFT_DRIFT (ideiglenes eltérés, wait and retry); RECONCILIABLE (javítható ismert flow-val, repair workflow); HARD_DRIFT (strukturális divergencia, escalation)"
- KB alap: `search_query("Proxmox PBS drift detection infra state")` → c1815, c2543, c2542
- Ítélet: **PARTIAL**
- Megjegyzés: A drift osztályok (Soft Drift, Reconciliable Drift, Hard Drift) KB-ban dokumentáltak (c1815, c2542). Azonban az output a táblázatban `RECONCILIABLE`-ként rövidíti, míg a KB `RECONCILIABLE_DRIFT`-et és `Reconciliable Drift`-et (c2542) használ. A diagnózis pseudocode (c2543) is `RECONCILIABLE_DRIFT`-et tartalmaz. A rövidítés nem okoz félreértést, de terminológiai eltérés. A kezelési leírás helyes.

---

- Állítás (forrás: execution-model.md):
  > "Drift diagnózis (c2543): if canonical_state(prooftrace) == pbs_root_hash → NO_DRIFT; else if derivable_diff(prooftrace, pbs) → RECONCILIABLE_DRIFT; else → HARD_DRIFT"
- KB alap: c2543
- Ítélet: **ALIGNED**
- Megjegyzés: c2543 szó szerint tartalmazza ezt a pseudocode-ot.

---

### 7. CIC szerepek demo fázisonként (8.1–8.4)

- Állítás (forrás: execution-model.md, roadmap.md):
  > "8.1–8.3: CIC szerepe OBSERVER + RECORDER; 8.4: CIC szerepe ACTOR (ez az egyetlen fázis ahol aktívan beavatkozik)"
- KB alap: `search_query("CIC observer recorder phase 8.1 8.2 8.3 demo")` → c1033, c878
- Ítélet: **UNVERIFIABLE**
- Megjegyzés: A KB-ban a 8.1–8.4 fázis-sorrend és az OBSERVER/RECORDER/ACTOR terminológia explicit nem jelenik meg ilyen formában — ezek az add.md specifikációból erednek, amelyre az output hivatkozik, de a KB-ban nincs önálló node erre. A fázisleírás logikailag konzisztens az OIS modellel (c2498) és az általános relay architektúrával.

---

### 8. ManagedEntity primitív

- Állítás (forrás: execution-model.md):
  > "ManagedEntity (c2801): identity (required), config_surface (required), state_surface (required), operation_surface (defaulted), policy_surface (defaulted), lifecycle_surface (sealed) — create → active → degraded → terminating → terminated"
- KB alap: c2801 (managed-entity.yaml)
- Ítélet: **ALIGNED**
- Megjegyzés: c2801 tartalmazza az összes slot-ot pontosan a leírt módokkal (required/defaulted/sealed). Az életciklus állapotok és átmenetek szintén pontosan egyeznek.

---

### 9. cic-primitives meta-séma réteg

- Állítás (forrás: status-matrix.md):
  > "cic-primitives meta-séma réteg: implemented | c2672, c2765 | 7 atomi primitív, sealed/defaulted/required slot contract"
- KB alap: c2672, c2765
- Ítélet: **PARTIAL**
- Megjegyzés: c2672 a cic-primitives repo README-je — meta-séma rétegként pozicionálja magát. c2765 a meta yaml file, amely a 7 atomi primitívet és slot contract-ot írja le konceptuálisan. Az "implemented" státusz a c2801 (managed-entity.yaml) alapján indokolt lehet, de a KB-ból nem derül egyértelműen ki, hogy mind a 7 primitív kódban él és CI-tesztekkel fedett. A dokumentáció kész, de a teljes "implemented" státusz alátámasztásához több kódreferencia szükséges lenne.

---

### 10. CIC-Schemas schemapipeline

- Állítás (forrás: execution-model.md, status-matrix.md):
  > "schemapipeline (4-lépéses build): implemented | c453 | start/test/validate/release native relay modulok"
- KB alap: c453 (schemapipeline.yaml Go package)
- Ítélet: **ALIGNED**
- Megjegyzés: c453 tartalmazza a négy lépést (cic.pipeline.start@1.0, cic.pipeline.test@1.0, cic.pipeline.validate@1.0, cic.pipeline.release@1.0) és a Docker exec alapú végrehajtást. A go_package típus kódbeli jelenlétet igazol.

---

### 11. schemacompile scaffold státusz

- Állítás (forrás: status-matrix.md):
  > "schemacompile (assert/build/sign): scaffold | c442 | cic.source.assert stub mode (chain verify nincs), cic_sign='unavailable' Vault nélkül"
- KB alap: c442 (schemacompile.yaml Go package)
- Ítélet: **ALIGNED**
- Megjegyzés: c442 explicit leírja: "Pass nil to run in stub mode (no chain verification)", "cic_sign will be 'unavailable'", "cic_signed_ca is 'stub:pending' until Layer 2 is wired". A scaffold státusz és a stub-ok pontosan egyeznek.

---

### 12. CICSourceCA Vault signing scaffold

- Állítás (forrás: status-matrix.md):
  > "CICSourceCA Vault signing: scaffold | c442, c1312 | Layer 2 — cic_signed_ca='stub:pending', Vault nem bekötve"
- KB alap: c442, c1312
- Ítélet: **ALIGNED**
- Megjegyzés: c442 tartalmazza a "stub:pending" értéket, c1312 a CIC-Schemas Vault signing munkafolyamatát írja le (Vault PKI backend, cert chain). A scaffold státusz és az előfeltétel (Vault bekötés) helyes.

---

### 13. PoSE scaffold státusz

- Állítás (forrás: status-matrix.md):
  > "PoSE (Proof of State Existence): scaffold | c263 | pose_result mező létezik a sémában, de SKIPPED a default"
- KB alap: c263
- Ítélet: **ALIGNED**
- Megjegyzés: c263 schema tartalmazza `pose_result: VERIFIED | DRIFT | SKIPPED` mezőt, és a leírás szerint ez "Optional PoSE verification result". A SKIPPED default logikailag következik a scaffold jellegből.

---

### 14. Go .so plugin mechanizmus

- Állítás (forrás: execution-model.md):
  > "plugin.Open('./plugins/terraform_observer.so'); plugin.Lookup('ObserveState'); go build -buildmode=plugin; Stateless: nincs belső állapot, nincs külső kapcsolat (c900, c906)"
- KB alap: c900, `search_query("relay execution model plugin stateless")` → c900
- Ítélet: **ALIGNED**
- Megjegyzés: c900 szó szerint: "stateless, tiszta függvényhalmaz... nem tárol adatot, nem lép kapcsolatba más komponensekkel, izoláltan, csak a relay hívására működik". A plugin.Open()/Lookup() Go standard, c906 a relay mag implementációs referenciája.

---

### 15. GitStateRecorder és WorkflowRecorder

- Állítás (forrás: status-matrix.md):
  > "GitStateRecorder: implemented | c590, c600 | GitStateRecorder struct, WorkflowRecorder — git alapú állapottárolás"
- KB alap: c590, c600
- Ítélet: **ALIGNED**
- Megjegyzés: c590 (go_struct: GitStateRecorder) és c600 (go_func: NewWorkflowRecorder) kódbeli jelenlétüket igazolják.

---

### 16. PBS integráció — concept státusz

- Állítás (forrás: status-matrix.md):
  > "PBS (Physical Base State) integráció: concept | c2585, c2616 | pbs_root_hash a commit modellben szerepel, PBS snapshot tool nincs"
- KB alap: c2585, c2616
- Ítélet: **ALIGNED**
- Megjegyzés: c2585 a PBS-PoSE integráció drift jelzést dokumentálja (H(logical) vs H(physical)). c2616 a CommitRef modellben szerepelteti a `pbs_root_hash` mezőt. A snapshot tool hiánya (concept→code bridge megszakad) konzisztens a KB-tartalmakkal.

---

### 17. Rollback trigger — concept státusz

- Állítás (forrás: status-matrix.md):
  > "Rollback trigger (intent/ ág figyelő): concept | add.md 8.4 | git push intent/main → Terraform apply — nincs kész runtime hook"
- KB alap: `search_query("CIC actor intervention rollback OIS obligation")` → c2147, c2623 (közvetett)
- Ítélet: **UNVERIFIABLE**
- Megjegyzés: Az intent/ ág figyelő és Terraform apply trigger nincs önálló KB node-ként rögzítve. Az add.md-re való hivatkozás megfelelő, de KB-oldalról ez UNVERIFIABLE. A concept státusz logikusan következik az OIS runtime hiányából.

---

### 18. Infrastruktúra döntés — Proxmox vs OCI

- Állítás (forrás: infra-decision.md):
  > "PBS integráció: a CIC architektúra explicit módon PBS-t hivatkozik az actual state rögzítésére (c2585, c2616). OCI-ban ezt szimulálni kell."
- KB alap: c2585, c2616
- Ítélet: **ALIGNED**
- Megjegyzés: A PBS-re való hivatkozás a commit modellben (c2616) és a PoSE-PBS integrációban (c2585) valóban explicit. Az OCI-Proxmox összehasonlítás többi pontja (VM lifecycle, VyOS, roadmap konzisztencia) az add.md specifikációból ered.

---

- Állítás (forrás: infra-decision.md):
  > "add.md roadmap konzisztencia — a specifikáció explicit v1 infrastruktúrája: Proxmox + VyOS + OpenSwitch + Bastion + Vault(mem) + Relay"
- KB alap: `search_query("Proxmox PBS drift detection infra state")` — nem ad közvetlen add.md eredményt
- Ítélet: **UNVERIFIABLE**
- Megjegyzés: Az add.md tartalom nem szerepel a KB-ban önálló node-ként. A döntés maga logikusan következik a PBS-hivatkozásokból (c2585, c2616), de az explicit "v1 infra stack" leírás KB-oldalról nem ellenőrizhető.

---

### 19. ProofNode / licenc érvényesítés

- Állítás (forrás: status-matrix.md):
  > "ProofNode / licenc érvényesítés: concept | add.md 5. | CICmeta valuta, licenc relay — nincs runtime implementáció"
- KB alap: közvetlen search nem ad ilyen node-t
- Ítélet: **UNVERIFIABLE**
- Megjegyzés: A ProofNode és CICmeta licenc-relay nincs önálló KB node-ként. Az add.md-re való hivatkozás jelzi az eredetet, concept státusz logikusan indokolt.

---

### 20. Sub-job függőségi lánc

- Állítás (forrás: sub-jobs-overview.md):
  > "poc-infra-01 → poc-observer-plugin-01 → poc-drift-detection-01 → poc-rollback-01 → poc-demo-script-01; poc-schema-signing-01 párhuzamos (poc-infra-01 után)"
- KB alap: A függőségi struktúra logikai konzisztenciáját a státusz-mátrix és a bridge térkép támasztja alá.
- Ítélet: **ALIGNED**
- Megjegyzés: A függőségi sorrend megfelel az implementált/scaffold/concept státuszoknak és a bridge térképnek. A schema-signing párhuzamossága indokolt (Vault-tól függ, nem a terraform observer plugintól).

---

### 21. Terraform observer plugin — concept státusz

- Állítás (forrás: status-matrix.md):
  > "Terraform plugin (.so): concept | add.md 8.1 | terraform_observer plugin nincs megírva"
- KB alap: c900 (általános plugin interface), nincs terraform-specifikus node
- Ítélet: **ALIGNED**
- Megjegyzés: A KB-ban terraform_observer.so nincs. A concept státusz helyes, az általános plugin interface (c900) az alap.

---

### 22. MISALIGNED eset — relay „sémaérzékeny végrehajtási csomópont" definíciójának csonkítása

- Állítás (forrás: execution-model.md):
  > "A relay sémaérzékeny végrehajtási csomópont (c2589), amely: [felsorolás: állapotgép nélkül, stb.]"
- KB alap: c2589
- Ítélet: **MISALIGNED**
- Megjegyzés: A c2589 chunk tartalma: "bemenetként új objektumokat vagy konfigurációkat fogad, ezeket validálja a hozzá tartozó sémával, alkalmazza az érintett infrastruktúra-objektumon, **továbbítja az eredményt más komponensek (pl. állapotfigyelő, generátor) felé**. A relay-ek láncolhatók: egyik relay kimenete lehet a másik bemenete. Így irányított gráf (DAG) szerű logika valósul meg." — Az output c2589-et csak a "sémaérzékeny végrehajtási csomópont" kifejezésre hivatkozza, de a KB-beli definíció ennél tágabb: tartalmaz infrastruktúra-alkalmazás és eredmény-továbbítás / DAG-láncolás szerepet. Az execution-model.md ezeket nem rögzíti, holott c2589 hivatkozza. Ez eltérés, nem súlyos hiba — a hiányzó elemek inkább kiegészítő kontextus, mint ellentmondás.
