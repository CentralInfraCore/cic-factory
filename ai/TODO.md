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

### T1 — A 7→8 atom átmenet félbemaradt `[drift]`
**Bizonyíték:**
- `schemas/atomic/access.yaml` — az Access atom **él**, teljes (field-szintű
  mTLS CertPattern jogosultság, `default_injection` information hiding,
  `inherit: 0/true/false` reset-lánc).
- `schemas/aggregate/config-surface.yaml:64` — még a régi világban:
  *"Jövőbeli atomic: PolicyRef (nem része az első 7 atomnak)"*, az `access`
  slot `type: TBD`.
- `ai/ROADMAP.md` Phase 3 (3.1–3.7) **csak 7 atomot** sorol — Access nincs benne,
  pedig a fájl létezik → a roadmap lezárása után, dokumentálatlanul került be.
- `managed-entity.yaml:31` viszont **már hivatkozik** az Access atomra
  (`used_by: [policy_surface, minden field értéke implicit]`).

→ A sémakészlet önellentmondó: ManagedEntity már 8-atomos, ConfigSurface + ROADMAP
+ ecosystem-map még 7-atomos.

**Teendő:**
1. `config-surface.yaml`: `access` slot `type: TBD` → `type: Access` +
   `atomic_ref: schemas/atomic/access.yaml`; "nem része az első 7 atomnak" törlés
2. `ai/ROADMAP.md`: Phase 3.8 — Access atom utólagos felvétele
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
