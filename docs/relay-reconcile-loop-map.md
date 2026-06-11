# Relay reconcile-kör (`nexus/operator`) — feltérképezés és véleményezés

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 5. rész).
Előzmények: `dev-environment-assessment.md`, `kb-synthesis.md`,
`ai-optimization-plan.md`, `relay-module-layer-map.md`.

Jelleg: **réteg-leírás és véleményezés**, nem biztonsági audit. A drift-taxonómia
(KB concept) és a `nexus/operator` runtime viszonyát térképezi fel.

Forrás: `CIC-Relay/core/nexus/operator/{watcher,lifecycle,bootstrap}.go`;
KB: `reality/drift_taxonomy.md`, `reality/state_commit_model.md`;
döntések: primitives D-009, memória Q1 (notice-trigger), ecosystem-map 8.1–8.4.

---

## A lelet egy mondatban

A `nexus/operator` **nem a drift-taxonómia runtime-ja** — egy GitOps-szerű,
fájl-diff alapú, egyirányú **apply-watcher**. A `grep "drift"` a kódon: nulla
találat.

---

## A tényleges működési modell

```
PollingWatcher.Watch → scanDir (könyvtár) → emitDiff(prev, curr)
   → Event{Create|Update|Delete} CSAK a változott fájlokra
   → Operator.Run event-loop → handleEvent → onApply / onDelete
   → onApply: YAML parse → Kind-dispatch (Host | Service)
        Host    → bootstrap token (HMAC) → lifecycle.OnboardHost
        Service → resource-enként: validate → desired=="present"? →
                  depsReady? → activator.Activate
```

A legtisztább bizonyíték `onApplyService`-ben (watcher.go:190–231): a feltétel-lánc
`validate → desired=present → depsReady → Activate` **sehol nem kérdezi le a valós
világ állapotát**, és nem hasonlít össze semmit. Ha `desired=present` és a
függőségek megvannak, `Activate` lefut — függetlenül attól, hogy a resource a
valóságban **már aktív-e**.

---

## A döntő különbség: edge-triggered, nem level-triggered

A KB drift-taxonómiája (`NO_DRIFT` / `RECONCILIABLE_DRIFT` / `HARD_DRIFT`) egy
**level-triggered reconcilert** feltételez: folyamatosan összeveti a *valós
állapotot* a *lánc által levezetett állapottal*, és visszaállítja az eltérést.

A `nexus/operator` ezzel szemben **edge-triggered**: csak a *deklarációs fájl
változásának élére* reagál (`emitDiff` prev vs curr — két egymást követő scan
különbsége, nem desired vs actual).

Az observe→compare→apply hármasból (amit a primitives `kubernetes-pod.yaml`
`derivation_chain` runtime-szekciója ígért):

| Lépés | Állapot |
|---|---|
| **observe** (actual world) | hiányzik — a watcher a deklarációs fájlokat figyeli, nem a provider-t |
| **compare** (drift) | hiányzik — nincs összevetés, nincs kategorizálás |
| **apply** | megvan — de feltétel nélküli, nem drift-vezérelt |

**Konkrét következmény: nincs self-healing.** Ha egy resource a valóságban
elsodródik (eltűnik), de a deklarációs fájl változatlan marad, az operator **nem
veszi észre** — nem emittál eventet, mert a fájl-diff üres. A rendszer a
*deklaráció* változására reagál, nem a *valóság* eltérésére.

---

## Ez nem hiányosság — illeszkedik a rögzített döntésekhez

A `nexus/operator` becsületes jelen-állapota koherensen illeszkedik:

- **Stateless notice-trigger modell** (memória Q1): külső trigger → notice →
  workflow. A watcher a fájl-változás triggerét adja.
- **8.1–8.3 observer-fázis** (ecosystem-map): a CIC nem avatkozik a végrehajtásba,
  csak figyel/rögzít. Az aktív, valós-állapotú reconcile a **8.4** lenne — még nincs.
- **`poc-drift-detection-01` pending**: a tényleges drift-detektálás (ProofTrace vs
  PBS) még meg nem épült réteg.
- **Primitives D-009**: az ExecutionSurface (reconciliation, failure_policy) nyitott
  bridge — a reconcile-kör bezárása erre vár.

---

## Vélemény

Maga az operator **tiszta, jól strukturált event-orchestrátor**: watch → diff →
parse → kind-dispatch → validate → deps → activate, plusz a host-onboarding
lifecycle (bootstrap token, HMAC, registry). Ami megvan, az szilárd.

De a "reconcile kör" **a koncepcióban él, a kódban még nem zárul be**. A jelenlegi
`nexus/operator` a kör **felső fele**: desired-deklaráció → apply. Az alsó fele
(observe actual → compare → drift-kategória → korrekció) hiányzik, és tudatosan a
relay-modell érésére + a 8.4 fázisra vár. A drift-taxonómia ezért a session során
vizsgált rétegek közül **a legtisztább `concept`**: gazdagon dokumentált
(chain/state drift, soft/reconciliable/hard, policy-mátrix), de a
runtime-megfelelője egy edge-triggered apply-watcher, nem a level-triggered
reconciler, amit a taxonómia feltételez.

---

## Összeér a session korábbi leleteivel

Három független megfigyelés ugyanazt mutatja:

1. **primitives→relay híd** (D-009, ExecutionSurface nyitott bridge),
2. **natív↔WASM aszimmetria** (`relay-module-layer-map.md`: jelen vs szándék),
3. **reconcile-kör felső-fél állapota** (ez a dokumentum).

→ **A relay deklaratív/végrehajtási váza kész; a valós-állapot-visszacsatolás
(drift, reconciliation, self-healing) a következő, még meg nem épült réteg.**
Ez a rendszer jelenlegi határvonala koncepció és runtime között.
