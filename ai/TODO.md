# cic-factory — TODO (felfedezett driftek)

> Forrás: orchestrátor audit-session 2026-06-11 (ökoszisztéma felmérés + primitives audit)
> Konvenció: minden tétel hordozza a file:line bizonyítékot, a státuszt és a cél-repót.
> A cic-factory az orchestrátor gyűjtőrepója — a külső repókra vonatkozó leletek innen
> mennek tovább job-ként.

---

## Státusz jelölések

- `[implemented]` — kódban él, tesztek fedik
- `[scaffold]` — kódban/sémában van, bekötés szándékosan hiányzik
- `[concept]` — nincs runtime/séma megfelelő
- `[drift]` — a réteg ellentmond magának vagy a dokumentációnak

---

## Séma-réteg → cél-repo: `cic-primitives`

### T1 — A 8. atom (Access) propagációja lemaradt `[drift]`
**Pontosítás:** az Access mint 8. atom **lezárt, dátumozott döntés** —
`ai/DECISIONS.md` D-011 (2026-05-04). Nem dokumentálatlan beszúrás; a drift
szűkebb: a downstream artifactok nem propagálták a D-011-et.

**Bizonyíték:**
- `schemas/atomic/access.yaml` — az Access atom **él**, teljes (field-szintű
  mTLS CertPattern jogosultság, `default_injection` information hiding,
  `inherit: 0/true/false` reset-lánc); `managed-entity.yaml:31` **már hivatkozik** rá.
- DE `schemas/aggregate/config-surface.yaml:64` még a régi világban:
  *"Jövőbeli atomic: PolicyRef (nem része az első 7 atomnak)"*, `access` slot `type: TBD`.
- `ai/ROADMAP.md` Phase 3 (3.1–3.7) **csak 7 atomot** sorol — Access nincs benne.
- `docs/ecosystem-map.md` (98–104) és az orchestrátor memória **7 atomot** mond.

→ Önellentmondás: ManagedEntity + DECISIONS (D-011) már 8-atomos; ConfigSurface +
ROADMAP + ecosystem-map még 7-atomos. A döntés megvan, a propagáció hiányzik.

**Teendő:**
1. `config-surface.yaml`: `access` slot `type: TBD` → `type: Access` +
   `atomic_ref: schemas/atomic/access.yaml`; "nem része az első 7 atomnak" törlés
2. `ai/ROADMAP.md`: Phase 3.8 — Access atom felvétele D-011 hivatkozással
3. orchestrátor oldal: `docs/ecosystem-map.md` (98–104) 7 → 8 atom + memória

### T2 — Scaffold slotok nincsenek gépileg jelölve `[scaffold]`
**Bizonyíték:** `managed-entity.yaml` — `capability_surface: type: TBD` (104–110),
`notification_surface` nyers `Event[]` (83–91), `lifecycle_surface` sealed inline
állapotgép, nem önálló aggregate (112–123). A scaffold-státusz csak prózában.

**Teendő:** `status: scaffold` (vagy `maturity:`) mező slot-szinten, hogy a
háromszintű státusz gépileg olvasható legyen a sémából.

---

## Tooling-réteg → cél-repo: `cic-factory` (ez a repo)

### T3 — Modell-rétegzés halott konfiguráció `[done]` (2026-06-11)
**Bizonyíték:** `meta.yaml` tartalmaz `agent.model` mezőt, de `tools/run-job.sh:106`
a `claude --print`-et `--model` flag nélkül indította; `agents/agent-01/settings.json`
nem állít `model`-t → minden agent-job a default (drága) modellen futott.
**Megoldva:** `run-job.sh:41` kiolvassa a `MODEL`-t a meta.yaml-ból, `run-job.sh:104-112`
feltételes `--model` flaggel adja át (üres → default). Sonnet agent implementálta,
orchestrátor review elkapott egy üres-tömb expanziós bugot (`${MODEL_FLAG[@]:-}` →
szemét üres argumentum), javítva `${MODEL_FLAG[@]}`-ra. Hátralévő P1-rész:
`agent-01/settings.json` default model + `validate-spec.sh` K-check üres mezőre.

### T4 — kb_focus kihasználatlan `[scaffold]`
**Bizonyíték:** `meta.yaml` `kb_focus` lista a `run-job.sh` prompt-építésében
(78. sor körül) sehol — az agent maga keres.
**Teendő:** `ai-optimization-plan.md` P2.

### T5 — Költség-guard hiánya `[concept]`
**Bizonyíték:** `run-job.sh:106` — nincs `--max-turns`, nincs token-mérés;
`index.yaml` csak duration-t rögzít.
**Teendő:** `ai-optimization-plan.md` P3.

---

## KB indexelő → cél-repo: `cic-mcp-private`

### T6 — KB chunk-minőség `[drift]`
**Bizonyíték:** `make_source.py` section-szintű chunkolása fejléc-only chunkokat
termel (c2205 = 6 soros cím, c2878 = 5 soros cím); `related_nodes` path-alapú,
nem node-id.
**Teendő:** `ai-optimization-plan.md` P4 — min. chunk-méret / fejléc+törzs
összevonás, `related_nodes` node-id feloldás, opcionális `get_doc` MCP tool.

---

## Elvi feszültség → cél-repo: `CIC-Relay` (ai/TRUST_TODO.md kontextus)

### T7 — 6. axióma ⟷ implementált CA-lánc `[concept]`
**Bizonyíték:** `axioms.md` 6. axióma: *"Nincs szükség központi hitelesítő
hatóságra — CA-alapú rendszerekkel inkompatibilis"*; szemben a ténylegesen
implementált Root→Intermediate→Source CA-lánccal (`CIC-Relay/ai/TRUST_TODO.md`
"Ami már megvan": CA Hierarchy implemented). A quorum-rootca válasz (7/26 Shamir)
**concept**.
**Teendő:** dokumentált interim döntés (DECISIONS / teads) — a CA-lánc tudatos
átmenet a quorum-trust megvalósulásáig, ne maradjon kezeletlen ellentmondásként.

---

## Ismert nyitott bridge (NEM hiba — tudatos döntés, követésre)

### T8 — primitives `DomainComposition` → relay végrehajtás `[concept]`
**Ez NEM felfedezett hiba — lezárt, dátumozott döntés:** `cic-primitives/ai/DECISIONS.md`
**D-009** (2026-04-30): *"ExecutionSurface szándékosan hiányzik... nyitott bridge marad
amíg a Relay modell nincs."* A helyes sorrend explicit: előbb relay execution modell,
abból visszavezetni az ExecutionSurface slot-jait — nem fordítva.

**Kontextus (verifikáció a döntés mellé, 2026-06-11):** a híd ténylegesen nyitott:
- relay `core/cabinet/types.go:21` `SchemaDef` = `StateRequirement/Dependencies/NextHops`
  (végrehajtási gráf-node); a relay Go+YAML kódban **nulla** primitives-referencia.
- `cic-primitives/tools/compiler.py` (422 sor) csak validál+aláír — **nincs** yang/
  restconf/emit fordító; a `kubernetes-pod.yaml` `derivation_chain` **kézi illusztráció**
  ("reality check"), nem generált kimenet.
- D-003 (`DECISIONS:43`): a primitívekből *"bármilyen target formátum generálható"* —
  a fordító tehát tervezett, de még nem létezik.

**Tervezett irány (orchestrátor megerősítés):** a szolgáltatás-leíró sémák (jelenleg
CIC-Schemas saját formátum, szolgáltatás-oldalról megfogva) primitives-formátumra
konvergálnak. Függőségi lánc: relay execution modell érik (PoC cert-flow) → D-009
ExecutionSurface visszavezethető → szolgáltatás-sémák primitives-re hozhatók
végrehajtási szemantikával. A config/state/binding surface-ek már most felvehetők
(nem relay-függők); csak a végrehajtási rész vár az ExecutionSurface-re.

**Teendő:** nincs azonnali akció — követni, amikor a relay execution modell stabil,
D-009 feloldható. A `derivation_chain` "reality check" megfogalmazását érdemes
egyértelműsíteni (kézi illusztráció, nem automatikus leképezés), hogy ne keltsen
generált-kimenet benyomást.
