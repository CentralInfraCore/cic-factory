# Végrehajtási modell — Hogyan fut egy relay lépés?

**KB forrás:** `relay_pozicionalas.md`, `plugin_interface.md`, `wasm_isdk.md`, `graf_vegrehajtas.md`, `schema_kezeles.md`

---

## A 4 alapkérdés KB-alapú válasza

### 1. Mi a relay tényleges szerepe?

A relay egy **stateless végrehajtó motor** (c912 — `relay_pozicionalas.md`):

**MIT CSINÁL a relay:**
- Végrehajtja a deklarált műveleti gráfot
- Kiértékeli a függőségeket és állapotokat (StateRequirement)
- Pluginokon keresztül meghívja a konkrét műveleteket
- NextHops mezők alapján továbbhalad a gráfban

**MIT NEM CSINÁL a relay** (c914):
- ❌ nem hajt végre kódot közvetlenül
- ❌ nem ír fájlt, nem módosít konfigurációt
- ❌ nem tárol semmilyen belső állapotot
- ❌ nem old meg konfliktust vagy versenyhelyzetet
- ❌ nem tartalmaz állapotgépet
- ❌ nem módosítja a sémákat vagy gráfokat
- ❌ nem tanul, nem hoz döntést

### 2. Mi hajt végre egy konkrét műveletet?

A **plugin** (c899 — `plugin_interface.md`):

> "A relay komponensek nem tartalmaznak konkrét üzleti logikát vagy állapotkezelést – minden műveletet a dinamikusan betöltött `.so` fájlokban definiált pluginfüggvények végeznek el."

A plugin egy stateless, tiszta függvényhalmaz:
- Bemeneti állapotleírás alapján műveletet hajt végre
- Visszajelzést ad (siker, hiba, aktuális állapot)
- Nem tárol adatot, nem lép kapcsolatba más komponensekkel
- Csak a relay hívására működik

**Technikai betöltés** (c906): `plugin.Open()` + `Lookup()` — `.so` fájl dinamikus betöltés

**Plugin korlátai** (c908):
- ❌ nem tarthat fenn saját állapotot
- ❌ nem kommunikálhat más pluginokkal közvetlenül
- ❌ nem férhet hozzá külső forrásokhoz, hacsak az inputban nincs deklarálva

### 3. Hogyan kapcsolódik egy workflow lépés a tényleges végrehajtóhoz?

A séma az összekötő kapocs (c927 — `schema_kezeles.md`):

```
YAML workflow lépés
    → séma PluginRef mező meghatározza, melyik plugin melyik függvényét kell hívni
    → relay kiértékeli StateRequirement-t (előfeltétel-ellenőrzés)
    → relay ellenőrzi Dependencies-t
    → relay betölti a plugin.so-t (plugin.Open() + Lookup())
    → plugin függvény végrehajtja a konkrét műveletet
    → plugin visszajelzést ad
    → relay NextHops szerint folytatja a gráf traversal-t
```

### 4. Mi az iSDK és a host frame szerepe?

**WASM iSDK** (c943 — `wasm_isdk.md`):
- A WASM modulba linkelt könyvtár modul-fejlesztőknek
- Elrejti a memóriakezelést és ABI-t
- Egységes exportot biztosít (guest/modul oldal)

**Host frame** (c943):
- A relay/executor oldalon minimális réteg
- Diszpécser hívásait WASM-hívássá alakítja
- Kezeli a modul betöltését, szinkron hívást, limiteket és séma-validációt a hívás körül

> A YAML csak azt írja le, *mit* futtatunk és *milyen IO-kötésekkel*; a *hogyan* (ABI, memóriakezelés, pool, timeout) a host frame és/vagy policy dolga.

---

## A teljes végrehajtási lánc

```
input.md spec lépés
    ↓
relay.yaml / Workflow YAML
    (apiVersion: relay.cic.com/v1, kind: Workflow)
    ↓
Relay motor betölti a workflow-t
    (WorkflowFile → steps lista)
    ↓
Séma feldolgozás
    (PluginRef, StateRequirement, Dependencies, NextHops kiértékelés)
    ↓
[DÖNTÉSI PONT: lépés típusa]
    │
    ├── "core" lépés → beépített Go cabinet modul (pl. core.ping)
    │       ↓
    │   cabinet package (proof_trace.go, plugin.go, stb.)
    │
    └── "wasm" lépés → WASM modul betöltés
            ↓
        host frame (WASM executor)
            ↓
        iSDK (guest oldali ABI réteg)
            ↓
        WASM modul függvény (tényleges művelet)
    │
    ↓ (mindkét ágból)
Plugin visszajelzés (siker/hiba/aktuális állapot)
    ↓
ProofTraceStep rögzítése
    (cabinet.ProofTraceStep: name, module, inputHash, outputHash)
    ↓
ChainHash számítás
    (computeChainHash: CICCHAINv1 + sourceDigest + workflowID + per-step adatok)
    ↓
ProofTrace → ProofArtifact
    (ProofArtifactFromTrace → canonical JSON → MarshalProofArtifact)
    ↓
PoSE ellenőrzés (ha bekötve)
    ↓
CommitRef → state/ git ág commit
    ↓
ProofTrace kész (auditálható, kriptográfiailag hitelesített)
```

---

## Következmény a PoC tervezésre

**Kritikus felismerés:** A relay NEM az a hely, ahol az infra-műveletek implementálva vannak. Minden új PoC funkció (Terraform hívás, drift detektálás, rollback) **plugin formájában írandó**, nem Go kódként a relay core-ba.

A PoC v1 lépéseihez szükséges pluginok:
1. `terraform-apply` plugin → Terraform CLI hívása, állapot visszaolvasása
2. `drift-detector` plugin → ProofTrace vs. PBS összehasonlítás
3. `ois-validator` plugin → OIS intent/obligation ellenőrzés rollback előtt
4. `state-commit` plugin → state/ git ág commit automatizálás

Ezek mind `.so` (Go plugin) vagy WASM modulként implementálandók, a relay core-t nem érintve.

---

## Implementációs híd térkép

```
concept → code → runtime → audit
```

| Lépés | Státusz | Megjegyzés |
|---|---|---|
| relay motor (Go) | **implemented** | cic-relay binary, make build, RELAY_URL=... test-api |
| cabinet/proof_trace.go | **implemented** | ProofTrace, computeChainHash, ProofArtifact |
| WASM iSDK / host frame | **concept** | wasm_isdk.md dokumentált, runtime bridge hiányzik |
| terraform plugin | **concept** | nincs .so implementáció |
| drift-detector plugin | **concept** | iac_ontology_and_design.md szinten leírt |
| ois-validator | **concept** | OIS elv dokumentált, relay integráció hiányzik |
| state commit (git auto) | **concept** | state_commit_model.md szinten leírt |
| pki_verify bekötése | **scaffold** | CLAUDE.md: CICRootCA → leaf cert előfeltétel hiányzik |
| LocalWorker in-process | **scaffold** | CLAUDE.md: 3-process isolation + Vault szükséges |
| quorum döntési réteg | **concept** | nincs runtime megfelelő |
