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
1. **natív vs WASM aszimmetria** — jelen vs szándék,
2. **workflow-step vs séma-gráf kettősség** — a végrehajtó egyszerűbb, mint a
   deklaratív modell.

Egyik sem hiba; mindkettő egy fejlődő rendszer becsületes pillanatképe.

A legmegfontolásra érdemesebb pont a `go.meta.gen.py`: nem mert hibás, hanem mert
az AI-réteg bemenete rajta áll. A viszonya a célhoz (hű kódkép) érdemes lenne
tudatos döntésként rögzíteni.
