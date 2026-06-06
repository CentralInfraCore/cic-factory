# poc-spec-review — Sub-job spec architektúrális ellenőrzés

## Kontextus

A `poc-implementation-plan` job 6 sub-job specet hozott létre. A `poc-output-review` job az
output fájlokat (execution-model.md, status-matrix.md stb.) ellenőrizte a KB-val — a sub-job
speceket nem. Ez a job azt a vak foltot zárja be.

**Feladatod:** minden sub-job `input.md`-jét ellenőrizni a `cic-graph` KB-val szemben.
Ne tervezz, ne írj kódot — csak ellenőrizz és dokumentálj.

**Ellenőrizendő spec fájlok** (a te klónodban):
```
jobs/poc-infra-01/input.md
jobs/poc-observer-plugin-01/input.md
jobs/poc-drift-detection-01/input.md
jobs/poc-rollback-01/input.md
jobs/poc-demo-script-01/input.md
jobs/poc-schema-signing-01/input.md
```

---

## Boot sequence

1. `kb_status` — KB elérhető és friss?
2. `search_nodes` → `["relay", "plugin", "wasm", "prooftrace", "ois", "iac", "schema"]`
3. Olvasd el a relay plugin betöltési mechanizmusát:
   - `search_query("relay plugin load plugin.Open Lookup buildmode")` → c906 vagy közeliek
   - `search_query("relay native module core modules cabinet")` → c912 vagy közeliek
   - `search_query("WASM iSDK host frame guest")` → c940, c943

---

## Feladat

### 1. Minden spec elolvasása

Olvasd el mind a 6 `input.md`-t. Minden specnél gyűjtsd össze:
- Fájl/könyvtár path-ok ahol kódot kell írni
- Relay workflow YAML-ok neve és struktúrája
- Plugin/modul referenciák (module neve, betöltési mód)
- Trigger mechanizmus (ki hívja, mikor, hogyan)
- KB chunk hivatkozások (c-számok) ha vannak

### 2. Ellenőrzési szempontok spec-enként

Minden specnél az alábbi kérdéseket válaszold meg a KB alapján:

**A) Plugin/modul elhelyezés — a legkritikusabb szempont**

A relay kétféle modult ismer:
- **Natív modul** (`core/modules/<név>/`): a relay-jel együtt fordul, Go csomag
- **Külső `.so` plugin**: `plugin.Open()`-nal töltődik, `/etc/cic-relay/components.d` alól

Ha egy spec `core/plugins/` path-ot ír → **MISALIGNED** (ez a path nem létezik a relay-ben).
Ha egy spec `core/modules/<név>/` path-ot ír → ellenőrizd, hogy valóban natív modult csinál-e.
Ha egy spec `/etc/cic-relay/components.d` vagy külső path-ot ír → **ALIGNED** (helyes `.so` elhelyezés).

Kérdezd le: `search_query("relay core modules native plugin external load path")` és
`search_query("components.d plugin install relay")`.

**B) Relay workflow YAML struktúra**

Ha a spec workflow YAML-t ír elő, ellenőrizd:
- `search_query("relay workflow YAML apiVersion kind spec steps module")` → c927 vagy közeliek
- A module nevek formátuma helyes-e? (pl. `cic.iac.observe@1.0`)
- A lépések (`steps[]`) struktúrája megfelel-e a KB-ban dokumentált sémának?

**C) Trigger mechanizmus**

Ki hívja a relay `/set` végpontját a spec szerint?
- Human manuálisan? Script? Operator polling? Terraform hook?
- Ha nincs meghatározva → **PARTIAL** (hiányos spec, de nem feltétlenül hibás)
- Ha ellentmond a KB-ban rögzített végrehajtási modellnek → **MISALIGNED**

**D) OIS / obligation check**

Ha a spec OIS-t említ:
- `search_query("OIS obligation check actor action context intent")` → c2498
- Helyes-e a stub vs. full implementation megkülönböztetés?

**E) ProofTrace / GitStateRecorder**

Ha a spec ProofTrace-t vagy GitStateRecorder-t említ:
- `search_query("ProofTrace chain_hash GitStateRecorder commit")` → c2436, c590, c600
- Konzisztens-e a chain_hash leírása a c263-as proof_artifact sémával?

### 3. Összehangoltsági ítéletek

| Ítélet | Jelentés |
|---|---|
| `ALIGNED` | KB-konzisztens, végrehajtható |
| `PARTIAL` | részben rendben, de hiány vagy pontosítás szükséges |
| `MISALIGNED` | architektúrálisan hibás — a spec alapján a következő agent rossz helyre dolgozna |
| `UNVERIFIABLE` | KB-ban nincs rá node, de logikailag konzisztens |

---

## Output

### Kötelező fájlok

**`jobs/poc-spec-review/output/spec-alignment-report.md`**

Felépítés:
```
# Sub-job Spec Összehangoltsági Jelentés

## Összefoglaló táblázat

| Sub-job | Plugin/Modul path | Trigger | Workflow YAML | Összesített ítélet |
|---|---|---|---|---|
| poc-infra-01 | ... | ... | ... | ALIGNED/PARTIAL/MISALIGNED |
| poc-observer-plugin-01 | ... | ... | ... | ... |
| ...

## Részletes elemzés — <job-id>

### Plugin/modul elhelyezés
- Spec állítása: [idézet]
- KB alap: [search_query eredmény, chunk ID]
- Ítélet: ALIGNED | PARTIAL | MISALIGNED | UNVERIFIABLE
- Megjegyzés: [ha hibás, pontosan mi és mi lenne a helyes]

### Trigger mechanizmus
...

### Workflow YAML
...
```

**`jobs/poc-spec-review/output/spec-issues.md`** — csak ha van MISALIGNED

Felépítés:
```
# Spec hibák — javítandó input.md-k

## <job-id> — <témakör>

- Mi a hiba: [konkrétan]
- Hibás sor a specben: [idézet]
- Helyes megközelítés KB alapján: [chunk ID + magyarázat]
- Hatás: ha így futtatják, az agent [ezt csinálja rosszul]
- Javasolt javítás: [konkrét szöveg ami az input.md-be kerülhetne]
```

---

## Git instrukciók

```bash
cd jobs/poc-spec-review/workspace/cic-factory
git add jobs/poc-spec-review/output/
git commit -m "job: poc-spec-review — spec alignment report"
git push origin feature/poc-spec-review
```

**Push csak `feature/poc-spec-review` branch-re. Soha ne pusholj `main`-re.**

---

## Nyelvi szabály

- Ez a fájl és az output fájlok: **magyarul**
- YAML, JSON, shell, kódrészletek: **angolul**
