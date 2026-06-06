# poc-output-review — KB összehangoltsági ellenőrzés

## Kontextus

A `poc-implementation-plan` job 5 output fájlt produkált a PoC implementációs tervről.
A feladatod: minden lényeges állítást ellenőrizni a `cic-graph` MCP KB-val szemben.
Ne tervezz, ne javasolj — csak ellenőrizz és dokumentálj.

**Output fájlok helye** (a te klónodban):
```
jobs/poc-implementation-plan/output/execution-model.md
jobs/poc-implementation-plan/output/status-matrix.md
jobs/poc-implementation-plan/output/infra-decision.md
jobs/poc-implementation-plan/output/roadmap.md
jobs/poc-implementation-plan/output/sub-jobs-overview.md
```

---

## Boot sequence

1. `kb_status` — KB elérhető és friss?
2. `search_nodes` → `["axioms", "symbols", "contract", "limits"]` — kanonikus kontextus betöltése

---

## Feladat

### 1. Output fájlok elolvasása

Olvasd el mind az 5 fájlt. Gyűjtsd össze az ellenőrizendő állításokat:
- Architektúrális állítások (pl. "a relay stateless végrehajtó motor")
- Implementációs státuszok (pl. "X komponens implemented/scaffold/concept")
- CIC szerepek demo fázisonként (8.1–8.4)
- Infrastruktúra döntések (pl. Proxmox vs OCI)
- Plugin/WASM végrehajtási modell leírása
- ProofTrace struktúra és chain_hash leírása
- cic-primitives atom-ok és BaseBlock/StateRequirement/PluginRef/NextHops primitívek

### 2. KB ellenőrzés

Minden állítás-csoporthoz kérdezd le a KB-t:

```
search_query("relay execution model plugin")
search_query("BaseBlock StateRequirement PluginRef NextHops")
search_query("ProofTrace chain_hash signature")
search_query("WASM iSDK host frame")
search_query("CIC observer recorder phase 8.1 8.2 8.3")
search_query("CIC actor intervention phase 8.4 rollback OIS")
search_query("Proxmox PBS drift detection")
search_query("cic-primitives atom Shape Role Behavior Contract Address Identity Event")
search_query("drift detection infra state")
```

Ha egy állításhoz nem találsz KB node-ot: jelöld `UNVERIFIABLE`-ként — nem feltétlenül hiba.

### 3. Összehangoltsági értékelés

Minden ellenőrzött állításnál döntsd el:

| Ítélet | Jelentés |
|---|---|
| `ALIGNED` | KB-ban ugyanez áll, konzisztens |
| `PARTIAL` | részben fedésben, de eltérés vagy hiány van |
| `MISALIGNED` | az output állítása ellentmond a KB-nak |
| `UNVERIFIABLE` | nincs KB node erre a területre |

---

## Output

### Kötelező fájlok

**`jobs/poc-output-review/output/alignment-report.md`**

Felépítés:
```
# Összehangoltsági Jelentés — poc-implementation-plan

## Összefoglaló
[ALIGNED/PARTIAL/MISALIGNED/UNVERIFIABLE darabszám + általános értékelés]

## Ellenőrzött állítások

### [témakör]
- Állítás (forrás: execution-model.md / status-matrix.md / ...):
  > [idézet az outputból]
- KB alap: [search_query amit használtál] → [chunk ID vagy node ID]
- Ítélet: ALIGNED | PARTIAL | MISALIGNED | UNVERIFIABLE
- Megjegyzés: [ha eltérés van, pontosan mi]

...
```

**`jobs/poc-output-review/output/issues.md`** — csak ha van MISALIGNED vagy súlyos PARTIAL

Felépítés:
```
# Eltérések — poc-implementation-plan

## [témakör]
- Mi az eltérés
- KB forrás (chunk ID)
- Output forrás (fájl + sor)
- Javaslat: újrafuttatás más input.md-vel? Vagy elfogadható eltérés?
```

---

## Git instrukciók

```bash
# a klónod gyökerében (jobs/poc-output-review/workspace/cic-factory/)
git add jobs/poc-output-review/output/
git commit -m "job: poc-output-review — alignment report"
git push origin feature/poc-output-review
```

**Push csak `feature/poc-output-review` branch-re. Soha ne pusholj `main`-re.**

---

## Nyelvi szabály

- Ez a fájl és az output fájlok: **magyarul**
- YAML, JSON, shell: **angolul**
