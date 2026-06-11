# Relay audit-trail lánc (`nexus/recorder`) — feltérképezés és véleményezés

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 6. rész).
Előzmények: `dev-environment-assessment.md`, `kb-synthesis.md`,
`ai-optimization-plan.md`, `relay-module-layer-map.md`, `relay-reconcile-loop-map.md`.

Jelleg: **réteg-leírás és véleményezés**, nem biztonsági audit. A ProofTrace
perzisztálási láncát térképezi fel (recorder → Vault-signed git commit).

Forrás: `CIC-Relay/core/nexus/recorder/{recorder,workflow_recorder}.go`;
KB: `reality/drift_taxonomy.md`, `reality/state_commit_model.md`;
döntés: Q3 (self-contained trust), Q4 (Vault signing).

---

## A lánc: ProofTrace → self-contained Vault-signed git commit

```
Setx → ProofTrace{WorkflowID, SourceDigest, Steps, ChainHash, Timestamp}
   → recorder.Record(ctx, workflowID, trace)          [non-fatal a Setx-ben]
   → WorkflowRecorder.Record: expected{RunID, ts}, actual = trace
   → GitStateRecorder.RecordState:
        expected.json + actual.json + meta.json
        → manifest (fájl→sha256) → manifestHash → CryptoService.Sign (Vault Transit)
        → signature.meta
        → git add . → git commit --allow-empty → HEAD hash
```

---

## Négy feltérképezési megfigyelés

### 1. Az aláírás a tartalom-manifesten van, nem a git commiton
A Vault-aláírás a `manifest` (fájlnevek + tartalom-hashek) SHA256-án van
(recorder.go:122–123), és külön fájlként (`signature.meta`) **bekerül a commitba**.
Minden snapshot **hordozza a saját tartalmának aláírását** — self-contained,
git-független bizonyíték. Konkrét megfelelője a Q3 döntésnek (*"trust az
objektumban van, minden objektum hordozza a saját bizonyítékát"*).

Külön minta a cic-factory commit-msg-hook signingjához képest: ott a
git-mechanizmus írja alá a commitot, itt a **tartalom** van aláírva — a relay a
hordozhatóbb (git-független) utat választja.

### 2. A working tree mindig csak az utolsó állapot — a történet a git-láncban él
A fájlnevek **fixek** (`expected.json`, `actual.json`, `meta.json`), nincs run-id a
névben. Minden `RecordState` **felülírja** az előzőt, `git add .` + commit
`--allow-empty`. A teljes audit-történet = `git log`; egy adott run ProofTrace-ét
csak `git show <commit>:actual.json` adja vissza. A git mint **append-only audit
log** — elegáns, de a történet kizárólag a commit-láncból olvasható, a munkafából
soha.

### 3. Két külön lánc, amit a drift-taxonómia nem lát egységesen
Van a **ProofTrace.ChainHash** (a workflow-n *belüli* step-lánc,
`computeChainHash`) és a **git commit parent-lánc** (a run-ok *közötti* lánc). De a
`ProofTrace` **nem tartalmaz `prev`-pointert** az előző trace-re (struct:
WorkflowID/SourceDigest/Steps/ChainHash/Timestamp).

A KB drift-taxonómia "chain drift"-je (fork = két event ugyanarra a `prev`-re;
replay) **explicit `prev`-event-láncot feltételez**. Itt a run-ok közötti "prev"
*implicit* (git parent), nem *explicit* (nincs a trace-ben). A fork-drift
git-szinten nem ugyanaz a fogalom (a git nem enged két commitot egy parentre
ugyanazon a branchen). A taxonómia event-lánc modellje és a git-commit-lánc
**nem 1:1** — a "chain drift" detektálás runtime-megfelelője nem nyilvánvaló.

### 4. Az "expected vs actual" séma workflow-úton fél-üres
A `RecordState` szignatúrája `(expected, actual)` — pontosan a drift-összevetés
alakja. De a `WorkflowRecorder` az `expected`-et csak `{RunID, Timestamp}`-ból
gyártja (workflow_recorder.go:33–36, a Graph nil), az `actual` a teljes
ProofTrace. Workflow-végrehajtásnál az `expected.json` **placeholder** — nincs
valódi expected-vs-actual összevetés, csak az actual rögzítése.

---

## Vélemény

A perzisztencia-**váz kész és tiszta**: Vault-signed, self-contained (a bizonyíték a
tartalomhoz tapad), append-only git-audit-log, determinisztikus manifest. A
happy-path mentén ez a session során látott egyik legbefejezettebb lánc.

De ugyanaz a minta köszön vissza, mint mindenhol:

> **a séma/csatorna implemented, a drift-tartalom scaffold.**

| Réteg | Kész (implemented) | Hiányzó (scaffold/concept) |
|---|---|---|
| WASM host-frame | auth-csatorna (külön param) | tartalom (ComponentID placeholder) |
| nexus/operator | apply (desired→activate) | observe→compare (drift) |
| nexus/recorder | `expected vs actual` interfész | workflow-úton az `expected` üres |

Mindhárom ugyanazt a határvonalat rajzolja:

> **A relay rögzíti, hogy mi történt (actual + Vault-bizonyíték), de nem veti össze
> azzal, aminek történnie kellett volna (expected/desired).**

A drift-taxonómia gazdag `concept`-je a típusokban már jelen van (`ExpectedState`,
`RecordState(expected, actual)`), de a runtime az `actual`-t rögzíti; az `expected`
oldal a következő réteg — pontosan a `poc-drift-detection-01` és a D-009
ExecutionSurface területe.

---

## A session feltérképezési íve — összegzés

Négy független réteg vizsgálata egyetlen határvonalra mutat:

1. **primitives→relay híd** (D-009 ExecutionSurface nyitott bridge),
2. **natív↔WASM aszimmetria** (`relay-module-layer-map.md`),
3. **reconcile-kör felső fele** (`relay-reconcile-loop-map.md`),
4. **audit-trail expected-placeholder** (ez a dokumentum).

→ **A relay deklaratív/végrehajtási/perzisztálási váza kész és koherens; a
valós-állapot-visszacsatolás (observe actual → compare → drift → reconcile →
self-healing) a következő, még meg nem épült réteg.** Ez a rendszer jelenlegi
határvonala koncepció és runtime között — nem hiányosság, hanem tudatos, a 8.4
fázisra és a relay-modell érésére váró sorrend.
