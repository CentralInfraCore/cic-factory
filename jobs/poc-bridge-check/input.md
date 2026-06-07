# poc-bridge-check — Bridge térkép visszaellenőrzése KB-val

## Kontextus

A `poc-plan-bridge-review` job két output fájlt produkált:
- `bridge-map.md` — 35 komponens státusza (implemented/scaffold/concept/missing), KB chunk hivatkozásokkal
- `relay-coverage.md` — a meglévő relay képességek lefedettségi térképe

A feladatod: **minden KB chunk hivatkozást és státusz állítást visszaellenőrizni** a `cic-graph` MCP-vel.
Ne tervezz, ne javasolj — csak ellenőrizz és dokumentálj.

## Boot sequence — KÖTELEZŐ

1. `kb_status` — KB elérhető és friss?
2. `search_nodes` → `["axioms", "symbols", "contract", "limits"]`

## Ellenőrizendő fájlok (a te klónodban)

```
jobs/poc-plan-bridge-review/output/bridge-map.md
jobs/poc-plan-bridge-review/output/relay-coverage.md
```

## Feladat

### 1. Output fájlok elolvasása

Olvasd el mindkét fájlt. Gyűjtsd össze:
- Minden chunk hivatkozást (cXXXX formátum)
- Minden státusz állítást (implemented / scaffold / concept / missing)
- Minden bridge törési pont állítást

### 2. KB visszaellenőrzés

**Minden chunk hivatkozásnál:**
- `get_node(cXXXX)` vagy `get_chunk(cXXXX)` — valóban létezik?
- A node típusa egyezik-e az állítással? (go_struct, go_func, doc, go_interface)
- A tartalom alátámasztja-e az állított státuszt?

**Különösen ellenőrizd:**

Implementált komponensek:
```
get_node("c357")   — ValidateSchema
get_node("c1127")  — canonicaljson.ToJSON
get_node("c349")   — ProofTrace go_struct
get_node("c594")   — GitStateRecorder.RecordState
get_node("c479")   — VaultCryptoService
```

Scaffold komponensek:
```
get_node("c580")   — Watcher interface
get_node("c533")   — IaCValidator
get_node("c509")   — IaCSource interface
get_node("c601")   — WorkflowRecorder.Record
get_node("c480")   — CryptoService interface
```

Concept komponensek:
```
get_node("c2582")  — PBS állapotfa (PoSE alap)
get_node("c2585")  — Drift jelzés / H(logical)==H(physical)
get_node("c2536")  — Drift Taxonomy
get_node("c1823")  — The Commit Record
get_node("c2303")  — Trust Anchor Lifecycle
get_node("c1715")  — OIS Obligation
```

Missing komponensek — ellenőrizd hogy valóban nincs-e KB node:
```
search_query("RelayHeader relay header schema envelope")
search_query("TerraformState terraform state schema relay")
search_query("RollbackRequest rollback request schema")
search_query("PolicyDecision policy decision OIS schema")
search_query("emitOperatorInstruction operator instruction relay emit")
search_query("post apply observation workflow terraform trigger")
```

### 3. Ítélet

Minden ellenőrzött állításnál:

| Ítélet | Jelentés |
|---|---|
| `CONFIRMED` | KB alátámasztja az állítást |
| `PARTIAL` | részben igaz, de pontosítás szükséges |
| `INCORRECT` | az állítás téves — más státusz vagy chunk |
| `UNVERIFIABLE` | a chunk létezik, de tartalma nem dönti el egyértelműen |

## Output

**`jobs/poc-bridge-check/output/check-report.md`**

Felépítés:
```
# Bridge Térkép Visszaellenőrzés

## Összefoglaló
[CONFIRMED/PARTIAL/INCORRECT/UNVERIFIABLE darabszám]

## Ellenőrzött állítások

### [komponens neve]
- Állítás (bridge-map.md): státusz = X, KB node: cYYYY
- KB visszaellenőrzés: get_node("cYYYY") → [típus, tartalom kivonat]
- Ítélet: CONFIRMED | PARTIAL | INCORRECT | UNVERIFIABLE
- Megjegyzés: [ha eltérés van]
```

**`jobs/poc-bridge-check/output/corrections.md`** — csak ha van INCORRECT

Minden hibás állításnál: mi a helyes státusz és miért.

## Git instrukciók

```bash
cd jobs/poc-bridge-check/workspace/cic-factory
git add jobs/poc-bridge-check/output/
git commit -m "job: poc-bridge-check — check report"
git push origin feature/poc-bridge-check
```

**Push csak `feature/poc-bridge-check` branch-re. Soha ne pusholj `main`-re.**

## Nyelvi szabály

- Ez a fájl és az output fájlok: **magyarul**
- YAML, JSON, shell, kódrészletek: **angolul**
