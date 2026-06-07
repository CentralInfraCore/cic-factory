# Private Source Directory — Rendszerszintű Áttekintés

**Dátum:** 2026-06-06
**Forráskönyvtár:** `${CIC_PARTNERS_ROOT}/MCPs/private/source/`

---

## A rendszer egésze

A private source könyvtár a **CentralInfraCore (CIC)** ökoszisztéma lokális, privát másolatát tartalmazza — git submodule/worktree struktúrában. Az egész rendszer egy ProofTrace-alapú, auditálható infrastruktúra-végrehajtási platform, amelynek középpontjában a deklaratív, kriptográfiailag igazolható állapotkezelés áll.

A könyvtárszerkezet két szervezetet/namespace-t fed le:

- **CentralInfraCore** — a platform összes runtime, schema és tudásbázis komponense
- **OpenIntentSign** — a platformot megalapozó nyílt bizalmi és validációs filozófia

---

## Szervezeti struktúra

```
source/
  CentralInfraCore/
    base/           → base-repo (git.CentralInfraCore/base-repo) — 6 worktree branch-en
    CIC-basic-knowledge/  → github_private — AI-natív fogalmi KB, gráf-alapú dok.
    CIC-objs/       → 6 schema domain repo (cic-primitives + 5 domain)
    CIC-Relay/      → CIC_Relay — Go runtime (ProofTrace végrehajtó)
    CIC-Schemas/    → CIC_Schemas — Schema compiler + Vault signing
    schemas/        → CIC_Schemas 2 worktree-je (postgresql, template)
  OpenIntentSign/
    github/         → .github — OIS umbrella/community repo
```

---

## Rétegek és összefüggések

### 1. Fogalmi alap (CIC-basic-knowledge)
Az `CIC-basic-knowledge` repo (`github_private`) az AI-natív fogalmi tudásbázis. Nem kód — deklaratív szemantikai gráf. NDJSON-alapú gráfstruktúra, YAML meta-annotációkkal. Ez az a réteg, amelyből a `cic-graph` MCP KB-ja táplálkozik.

### 2. Infrastruktúra template (base)
A `base-repo` (`git@github.com:CentralInfraCore/base-repo.git`) az összes többi repo sablonja. Egyszerre több branch-en él (worktree-k: `base`, `docs`, `golang`, `IaC`, `schemas`, `workflows`). A domain repók `remote-merge` módon veszik át a Makefile-t, .github/ struktúrát, CI workflow-kat stb.

### 3. Schema primitívek és domain objektumok (CIC-objs)
- **cic-primitives** — a meta-séma réteg. 7 irreducibilis atom (Shape, Role, Behavior, Contract, Address, Identity, Event) + aggregate kompozíciók. Minden domain objektum ebből vezethető le.
- **cic-compute** — VM, bare metal, cloud instance domain (ManagedEntity specializáció; saját fejlesztési fázissal: Phase 3 commit-ig eljutott).
- **cic-kubernetes** (0.1.3), **cic-network** (0.1.2), **cic-storage** (0.1.2), **cic-yang** (0.1.2) — ezek is cic-primitives worktree-k különböző release branch-eken. A README/SYSTEM_CONTEXT még a primitives sablont mutatja — a domain-specifikus tartalom a schemas/ könyvtárban él.

### 4. Schema compiler és signing (CIC-Schemas)
A `CIC_Schemas` repo biztosítja a schema érvényesítési és kriptográfiai aláírási infrastruktúrát. HashiCorp Vault-alapú signing — private kulcs soha nem kerül ki a Vault-ból. A `schemas/` könyvtár két worktree-je (`postgresql`, `template`) ugyanennek a repónak a különböző branch-ei.

### 5. Runtime (CIC-Relay)
A `CIC_Relay` Go-alapú (Go 1.24) runtime. Kulcsfüggőségek: wazero (WASM végrehajtás), HashiCorp Vault API (ProofTrace aláírás), watcher-alapú workflow feldolgozás. Három fő csomag:
- `cmd/relay` — HTTP API (:8080), bootstrap
- `core/cabinet` — schema/module/workflow registry, WASM végrehajtó
- `core/nexus` — IaC loader, Git recorder, Vault crypto, sync, isolation, operator

### 6. Nyílt bizalmi modell (OpenIntentSign)
Az OIS (`.github`) repo az umbrella/community pozíció — specifikáció, nem implementáció. A CIC platform mögötti filozofiai alap: "egy infrastruktúra bizonyítsa be saját érvényességét".

---

## Kapcsolódási térkép

```
OpenIntentSign (.github)
    ↓ [filozofiai alap]
CIC-basic-knowledge (fogalmi KB / AI relay)
    ↓ [séma réteg]
base-repo (template → remote-merge)
    ↓
cic-primitives (7 atom + aggregate)
    ↓ [domain specializáció]
cic-compute, cic-kubernetes, cic-network, cic-storage, cic-yang, cic-yang
    ↓ [compiled + signed]
CIC-Schemas (compiler + Vault signing)
    ↓ [runtime betöltés]
CIC-Relay (ProofTrace végrehajtó / WASM / Go)
```

---

## Fontos megfigyelések

1. **A cic-objs repók (cic-kubernetes, cic-network, cic-storage, cic-yang) README-je és SYSTEM_CONTEXT-je még a cic-primitives sablont mutatja** — domain-specifikus tartalom fejlesztés alatt áll.

2. **A base-repo 6 worktree-n él** — ez szándékos: minden ág egy-egy sablon-területet (docs, golang, IaC, schemas, workflows) kezel, amelyek `remote-merge`-gel kerülnek a domain repókba.

3. **A CIC-Schemas repo kétféleképpen jelenik meg**: közvetlenül (`CIC-Schemas/`) és worktree-ként (`schemas/postgresql`, `schemas/template`) — ezek eltérő branch-ek (postgresql, template branch-ek vs. a fő CIC-Schemas branch).

4. **A cic-compute az egyetlen domain repo, amely ténylegesen eltér** a primitives sablontól: saját commit history-val rendelkezik (Phase 1-3 fejlesztés), saját `project.yaml`-lal.

5. **Minden submodule `.git` fájlként van tárolva** (worktree pointer) — a tényleges git metadata a szülő repo `.git/modules/` könyvtárában él.
