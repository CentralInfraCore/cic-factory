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

---

## Tooling-réteg — 2026-08-03 (oci-extract-generalize futásból)

### T9 — `meta.yaml` `agent.config_dir` halott konfiguráció `[drift]`
**Bizonyíték:** `tools/run-job.sh:31` `AGENT_ID="agent-01"` a default, és a
`tools/run-job.sh:33-38` ciklus a **parancssori argumentumból** veszi az agentet
(`AGENT_CONFIG="$HOME/.claude-personal/agents/$AGENT_ID"`, `run-job.sh:47`).
A `meta.yaml` `agent.config_dir` mezőjét **semmi nem olvassa** — grep-pel egyetlen
hivatkozás sincs rá a `run-job.sh`-ban.

→ Ha az orchestrátor elfelejti átadni az agent-id-t, a job **csendben a default
`agent-01`-gyel fut**, miközben a spec mást deklarál. A `oci-extract-generalize`
esetén ez a `cic-module-wasm-claude` agent lett volna — a modul-repo saját
`CLAUDE.md`-je szerint kizárólag az az agent építheti azt a repót.

**Ugyanaz a hibaosztály, mint a T3** (`agent.model` szintén halott volt, amíg
`run-job.sh:41` ki nem olvasta). A séma deklarál valamit, a futtató figyelmen
kívül hagyja.

**Teendő:** `run-job.sh` olvassa ki a `agent.config_dir`-t a `meta.yaml`-ból
(a `MODEL` mintájára), a parancssori argumentum maradjon felülbíráló. Ha egyik
sincs → `agent-01` és **kiírt figyelmeztetés**, ne néma default.

### T10 — `make build` untracked, nem-ignorált artifactokat hagy `[drift]`
**Cél-repo:** `cic-module-oracle-cloud` (és feltehetően minden `base-repo`
származék — ellenőrizendő).

**Bizonyíték:** a `oci-extract-generalize` agent-klónjában a `make build` után
`git status` ~55 untracked `.yaml` fájlt mutat, minden `.go`/`.py` mellé egyet
(`module/provider.yaml`, `tools/oci-extract/client.yaml`, `tests/*.yaml`, …).
Tartalmuk KB-ingest formátum (`package` / `description` / `tags` / `objects`).
- `git check-ignore -v module/provider.yaml` → **nincs találat**, tehát nem ignorált
- a live repóban `git ls-files | grep -c '^module/.*\.yaml$'` → **0**, és a fájlok
  a lemezen sem léteznek → nem szándékosan követett artifactok

→ Egy `git add -A` mind az 55-öt becommitolná. Mivel a `MANIFEST.sha256` képlete
`git ls-files`-ra épül, a generált szemét bekerülne az **aláírt manifestbe** is.

**Teendő:** eldönteni, hogy ezek build-artifactok (→ `.gitignore`) vagy szándékos
KB-forrás (→ tracked + dokumentált). Addig is: az agent-promptokban `git add -A`
helyett explicit path-listás `git add`.

### T11 — `--resume` soha nem működött ebben a workdirben `[done]` (2026-08-03)
**Bizonyíték:** `tools/run-job.sh:49` a projekt-slugot így képezte:
```
PROJECT_SLUG=$(echo "$WORKDIR" | sed 's#/#-#g')
```
Ez **csak a `/`-t** cseréli kötőjelre. A Claude Code viszont az **aláhúzást is**
kötőjelre cseréli a projekt-könyvtár nevében. Mivel ez a workdir a
`/home/sinkog/sync/claude_factory/...` alatt él, a két útvonal eltért:

```
valódi    ~/.claude-personal/agents/<id>/projects/-home-sinkog-sync-claude-factory-CIC-workdir
derivált  ~/.claude-personal/agents/<id>/projects/-home-sinkog-sync-claude_factory-CIC-workdir
```

Következmény: `[ERROR] Session jsonl nem található: …` — a `--resume` **minden
eddigi próbálkozáson elbukott**, nem most romlott el. A
`project_wasm_template_state` memória „session-limit restart minta dokumentálva"
tétele tehát dokumentált volt, de élesben soha nem futott le.

**Felszínre hozta:** a `oci-extract-generalize` első futása, ami 51/50 turn-nél
munka közben állt le, és pont ezt az utat igényelte a folytatáshoz.

**Megoldva:** `run-job.sh:49` → `sed 's#[/_]#-#g'` (commit `17135e0`).
Verifikálva: a derivált útvonal megtalálja a `9f0ba8b7-…jsonl`-t, és a resume
lefutott (`68cb3e7`, max-turns 100, meglévő workspace újrahasználva).

**Tanulság — ez a nap negyedik példája ugyanarra:** olyan azonosító, ami nincs a
tartalmához kötve, némán másra mutat. KB chunk-id (`project_mcp_connect_fix`),
`agent.config_dir` (T9), `make build` sidecarok (T10), és ez. Egyik sem hangosan
bukott — mind csendben. Ahol a factory azonosítót *származtat* string-műveletből,
ott ellenőrizni kell, hogy a származtatott dolog **létezik-e**, és hangosan
elbukni, ha nem.
