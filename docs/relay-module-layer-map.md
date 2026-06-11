# Relay modul-feldolgozó réteg — feltérképezés és véleményezés

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 4. rész).
Előzmények: `dev-environment-assessment.md`, `kb-synthesis.md`, `ai-optimization-plan.md`.

Jelleg: **réteg-leírás és véleményezés**, nem biztonsági audit/buglista. A konkrét
hibajegyek (ha kellenek) az `ai/TODO.md`-be tartoznak; ez a dokumentum a réteg
karakterét és illeszkedését térképezi fel.

Forrás: `CIC-Relay/tools/go.meta.gen.py`, `CIC-Relay/core/cabinet/service.go`,
`types.go`; boot sequence chunk-ok (c781/c912/c927).

---

## Két különböző "modul-feldolgozás" — más cél, más irány

| | `go.meta.gen.py` | `service.go:Setx()` |
|---|---|---|
| Irány | forrás → tudás (KB) | séma → valóság (runtime) |
| Szerep | Go-forrásból meta-YAML váz az MCP-indexeléshez | a relay futó modul-dispatch szíve |
| Kihez szól | az AI-réteg (amin Claude/ChatGPT látja a kódot) | a végrehajtott workflow |
| Karakter | könnyűsúlyú, regex, 1 függőség (PyYAML) | lépés-szintű bizonyíthatóság |

A kettőt érdemes nem összemosni: az egyik azt határozza meg, **mit lát az AI a
kódról**, a másik azt, **hogyan hajtódik végre a deklarált gráf**.

---

## 1. `go.meta.gen.py` — a forrás→tudás híd

**Tudatosan könnyűsúlyú döntés.** Regex-alapú, nem AST; a doc maga elismeri a
korlátot (*"too fragile without AST"*). Vállalt csere: lemond a pontosságról az
egyszerűségért és a függőtlenségért.

**Skeleton-generátor, nem értelmező.** A szemantikus mezőket (`category`,
`used_in`, `related_nodes`, `implements`) szándékosan üresen hagyja "human
completion"-re. A tervezői álláspont: a gép a **vázat** adja, az ember a
**jelentést**. Ez konzisztens a `conversation_driven_system` filozófiával (az AI
formalizál, a döntés emberi).

**Véleményezés.** Ez egy alulbecsült, de kritikus elem: az egész AI-asszisztált
munkafolyam **bemenete** ezen áll. A regex-váz pontatlansága (lossy projekció a
forrásból) visszahathat a rád bízott elemzésekre. Nem mert hibás — hanem mert a
viszonya a célhoz (teljes, hű kódkép) megérne egy tudatos döntést: *meddig elég a
regex-váz, és hol kezd a pontatlansága számítani?* Az AST-alapú változat
(`go/parser` egy apró Go helper) ezt megszüntetné, ha/amikor a pontosság ára
megéri. Kapcsolódik: `ai/TODO.md` T6 (KB chunk-minőség) — a probléma nem csak a
chunkolás, hanem a meta-kinyerés is.

---

## 2. `service.go:Setx()` — a séma→valóság híd

**A concept→runtime híd itt BE VAN kötve** (szemben a primitives→relay híddal,
D-009, ami nincs). Ez a c912/c927 koncepció futó megfelelője.

**Feltérképezési lelet: a deklaratív gráf ≠ a végrehajtó.** A boot sequence szerint
a relay `StateRequirement/PluginRef/NextHops` mentén halad. De a tényleges `Setx`
**nem ezeket futtatja**: a `SchemaDef` (StateRequirement/NextHops) a
séma-deklaráció, a `Setx` viszont a `Workflow.Steps`-et parse-olja
`ExecutionGraph`-fá, és step-enként `ComponentID.FunctionName(InputKey) →
OutputKey` dispatch-el. Tehát a **deklaratív gráf-modell** (séma) és a
**szekvenciális step-végrehajtó** (workflow) két külön mechanizmus; a runtime
jelenleg a step-szekvenciát hajtja végre. Nem hiba — érettségi pillanatkép: a
koncepció gazdagabb, mint a jelenlegi végrehajtó.

**A mag karaktere: lépés-szintű bizonyíthatóság.** Minden step: input-hash →
dispatch → output-hash → ProofTrace-lépés; a végén chain-hash. A relay nem utólag
naplóz, hanem a végrehajtás *közben* építi a bizonyítékot. Ez a CIC központi
ígérete kódban — erős és koherens.

**Dispatch-kettősség: jelen vs szándék.** Natív Go modul (gyors, beágyazott,
reflect-hívás) vs WASM (sandboxolt, izolált, init/process/get/notify életciklus),
egy interfész mögött — a workflow nem tudja, melyiket hívja. Tiszta absztrakció.
DE a két ág **nem egyenrangúan érett**: a WASM-ág körültekintőbb (timeout-kezelés,
JSON-marshal határ, explicit művelet-enum), a natív ág nyersebb (szinkron hívás,
kevesebb védőkorlát). Olvasat: a **WASM-út a stratégiai cél** (valódi izoláció), a
**natív-út a most-működő pragmatizmus** — egybevág a rögzített döntéssel (Go .so
helyett fordításidőben linkelt natív modul; `plugin.Open` sehol). A natív ág a
jelen, a WASM ág a szándék.

**Beépített álláspont: elérhetőség vs bizonyíthatóság.** A `recorder` "non-fatal"
(a végrehajtás nem áll meg, ha a Vault-rögzítés elhasal, csak warningol). Tudatos
kompromisszum — a rendszer inkább fut, mint hogy hiányzó audit miatt leálljon.
Filozófiailag vitatható (a "lassú igazság" szigorúbb olvasata szerint nyom nélkül
nem volna szabad végrehajtani), üzemeltetésileg pragmatikus. Fontos tudni, hogy ez
álláspont, nem véletlen.

---

## 3. `cicwasm.go` — a WASM host-frame (a dispatch szándék-fele)

A `Setx` WASM-ágának másik fele: a `cicwasm.go` (416 sor, wazero-alapú). A session
során látott **legérettebb izolációs réteg** — és érdemben árnyalja a 2. szakasz
"jelen vs szándék" megfigyelését: a szándék már megépült, nem koncepció.

**Nyelvfüggetlen ABI: egyetlen belépő + op-dispatch.** A guest **egyetlen** `call`
függvényt exportál, plusz `allocate`/`deallocate`-et. A négy művelet
(Init/Process/Get/Notify) nem négy export — egyetlen `call`-on mennek át, az `op`
stringgel megkülönböztetve (`callGuest`, 317). Bármely nyelvből fordított WASM
implementálhatja, ha kihozza az `allocate`/`deallocate`/`call` hármast. Ez a
"nyelvfüggetlen modul" ígéret konkrét alapja.

**Memória-tulajdon a guesté.** A host nem nyúl közvetlenül a guest heap-jéhez: a
három bemenő stringet (op, auth, input) a guest **saját** `allocate`-jén keresztül
írja be (`writeStringToWasm`, 369), és minden blokkot `defer deallocate`-tel
takarít — a result-ot is. A dealloc-hibák non-fatal (warn), konzisztensen a
recorder filozófiájával.

**Eredmény-szerződés.** A guest packed `uint64`-et ad vissza:
`(size << 32) | pointer` (325–328); a host kiolvassa, JSON `{data, error}`-ként
parse-olja. `packed == 0` → tiszta null-eset. Determinisztikus.

**Stateless, de amortizált.** A *compiled module* LRU-cache-elt (a fordítás drága),
de minden híváshoz **friss instance** nyílik (`NewHostInstance`). Az állapot nem
hordozódik át hívások között — a c912 "a relay stateless" elv kódban.

### Két pontosítás a 2. szakaszhoz (a host-frame fényében)

**(a) A natív↔WASM aszimmetria oka világos — valódi, kikényszerített timeout.**
A `callGuest` `context.WithTimeout` (284) + a runtime `WithCloseOnContextDone(true)`
(62) együtt **ténylegesen megszakítja** a WASM-végrehajtást
(`DeadlineExceeded → TIMEOUT`, 319). Ezt a natív ág nem tudja. Tehát nem "a natív
ág hibás" — a WASM-út megkapta az izolációt, sandboxot, megszakíthatóságot, tiszta
memória-tulajdont; a natív-út a beágyazott pragmatizmus. A szándék már **kész**,
nem koncepció.

**(b) Az auth-csatorna létezik — korábbi "gyanús" megfigyelés korrigálva.**
A `callGuest` az `authContextJson`-t **külön, elsőrangú paraméterként** adja át a
guestnek (op + **auth** + input, három független string). A `Setx`-ben látott
`authContextJson := step.ComponentID` nem hiányzó auth, hanem **egy kész csatorna,
amit jelenleg a ComponentID-vel töltenek fel placeholderként**. Pontos állapot:
**a csatorna implemented, a tartalom scaffold** — érdemben jobb, mint amit a `Setx`
önmagában mutatott.

---

## Illeszkedés — a séma→workflow→modul→ProofTrace lánc runtime-zárása

```
Cabinet (séma / modul / workflow registry — c781)
   → Setx: workflow feloldása → ExecutionGraph
   → step-enként: modul feloldása → input-validáció → dispatch (natív | WASM)
   → minden step: ProofTrace-lépés (input/output hash)
   → chain-hash → recorder (Vault-signed, non-fatal ha Vault nincs)
```

---

## Összegző vélemény

**Szilárd vázú, peremein még érlelődő réteg.** A mag (lépés-szintű
ProofTrace-építés, dispatch-absztrakció, registry-alapú feloldás) pontosan az,
amit a koncepció ígér — itt a concept→runtime híd be van kötve.

A karaktere két helyen árulja el, hol tart:
1. **natív vs WASM aszimmetria** — jelen vs szándék. A host-frame (3. szakasz)
   fényében: a szándék-oldal (WASM-izoláció, valódi timeout, auth-csatorna) **már
   megépült** — tudatos kétsebességes architektúra, ahol a jövő kész, csak a jelen
   még a gyorsabb, kevésbé védett natív úton fut. Nem féltermék.
2. **workflow-step vs séma-gráf kettősség** — a végrehajtó egyszerűbb, mint a
   deklaratív modell.

Egyik sem hiba; mindkettő egy fejlődő rendszer becsületes pillanatképe. A
host-frame (`cicwasm.go`) a session során látott legkiforrottabb kódrész —
felülírja azt a benyomást, hogy a relay "peremein nyers".

A legmegfontolásra érdemesebb pont a `go.meta.gen.py`: nem mert hibás, hanem mert
az AI-réteg bemenete rajta áll. A viszonya a célhoz (hű kódkép) érdemes lenne
tudatos döntésként rögzíteni.
