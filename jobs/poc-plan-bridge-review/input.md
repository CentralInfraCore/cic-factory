# poc-plan-bridge-review — Bridge térképezés a CIC működési elvei alapján

## A feladat lényege

A `ref/poc-plan.md` egy implementációs tervet tartalmaz a PoC-hoz. Ez a terv cél-orientáltan
gondolkodik: "mit kell megépíteni". A te feladatod más: **ne a tervet fogadd el kiindulásnak,
hanem a KB-t.**

A kérdés nem az, hogy "mi hiányzik a tervből". A kérdés:

> A KB-ban dokumentált CIC fogalmak és komponensek közül melyiknek mi a státusza,
> és hol szakad meg a bridge a `concept → code → runtime → audit` láncban?

## Boot sequence — KÖTELEZŐ

1. `kb_status` — KB elérhető és friss?
2. `search_nodes` → `["axioms", "symbols", "contract", "limits"]` — kanonikus invariánsok betöltése
3. `search_nodes` → `["relay", "prooftrace", "pose", "drift", "ois", "schema", "iac"]`
4. Olvasd el: `focus_pack(["relay", "prooftrace", "pose", "drift"])` — teljes kontextus

**Amíg ez nem teljesült, ne állíts semmit az architektúráról.**

## Reasoning mód: audit

Ez nem `implementation` és nem `immersion` — ez `audit`.

- Keresd a KB-ban az egyes fogalmakat
- Állapítsd meg a háromszintű státuszt: **implemented / scaffold / concept**
- Azonosítsd ahol a lánc megszakad
- Ne tervezz, ne javasolj megépítendőt — csak térképezd fel ami van és ami hiányzik

## A Bridge Detector szabálya

Ha a lánc egy ponton megszakad:

```
concept → code → runtime → audit
```

Ne azt mondd: "hiányzik X" — azt mondd:
**"X fogalma dokumentált (node ID: cXXXX), de a bridge itt szakad meg: [hol]"**

## Feladat

### 1. Olvasd el a ref/poc-plan.md-t

Ez tartalmazza azokat a komponenseket (sémák, modulok, workflowk, relay funkciók) amelyekről
a terv azt állítja, hogy kellenek. Ezeket használd kiindulópontként a KB kereséshez —
de ne mint "hiánylista", hanem mint "fogalom-lista amiket a KB-ban keresni kell".

### 2. KB-alapú státusz meghatározás

Minden komponens-csoportra kérdezd le a KB-t:

**Sémák:**
```
search_query("Actor schema identity trust anchor relay")
search_query("Intent declare obligation actor")
search_query("ProofTrace ProofTraceEvent chain schema")
search_query("DesiredState TerraformState ActualState IaC schema")
search_query("Drift taxonomy schema NO_DRIFT SOFT HARD CHAIN")
search_query("PoSE Proof of State Existence schema verification")
search_query("StateCommit commit record schema immutable")
search_query("RollbackRequest rollback intent schema")
search_query("PolicyDecision OIS obligation decision schema")
```

**Relay funkciók:**
```
search_query("relay validate canonicalize hash sign")
search_query("relay observe actual state collector")
search_query("relay compare logical physical state")
search_query("relay buildProofTrace commitState")
search_query("relay readIntentBranch intent watcher")
```

**Workflowk:**
```
search_query("post apply observation workflow terraform")
search_query("drift observation workflow manual physical")
search_query("rollback intent workflow OIS obligation apply")
```

**Modulok:**
```
search_query("canonical json normalizer deterministic hash")
search_query("PBS root hash calculator physical state")
search_query("GitStateRecorder WorkflowRecorder state commit writer")
search_query("OIS policy evaluator obligation motor runtime")
search_query("trust anchor registry actor key PEM")
```

### 3. Bridge térkép elkészítése

Minden komponensnél döntsd el:

| Státusz | Mikor |
|---|---|
| **implemented** | KB-ban node + kódreferencia (go_struct, go_func) + CI |
| **scaffold** | kódban van, de bekötetlen — előfeltétel hiányzik |
| **concept** | KB-ban dokumentált, nincs runtime megfelelő |
| **missing** | KB-ban sincs — a terv találta fel, nem a CIC fogalomrendszere |

A `missing` különösen fontos: ha egy komponens nem szerepel a KB-ban, az azt jelenti,
hogy a terv eltért a CIC saját fogalomrendszerétől.

### 4. A relay meglévő képességeinek feltérképezése

Kérdezd le, mi van már a relay-ben:
```
search_query("cabinet validate schema relay implemented")
search_query("canonicaljson pkg relay implemented")
search_query("proof_trace cabinet chain_hash implemented")
search_query("GitStateRecorder nexus recorder implemented")
search_query("IaCLoader nexus iac implemented")
search_query("VaultCryptoService nexus crypto sign implemented")
```

Ezekre az a kérdés: **a meglévő relay képességek lefedik-e a terv relay funkcióit?**
Ha igen — nem kell újat írni, csak bekötni (scaffold → implemented).

---

## Output

### Kötelező fájlok

**`jobs/poc-plan-bridge-review/output/bridge-map.md`**

Felépítés:
```
# CIC Bridge Térkép — PoC komponensek

## Összefoglaló

| Státusz | Darab |
|---|---|
| implemented | X |
| scaffold | X |
| concept | X |
| missing (KB-ban sincs) | X |

## Bridge lánc ahol megszakad

[diagram: melyik lánc-ponton szakad meg az egyes komponenseknél]

## Komponensek státusza

### [komponens neve]
- KB node: cXXXX (vagy: nincs KB node)
- Státusz: implemented | scaffold | concept | missing
- Bridge törési pont: concept | code | runtime | audit
- Bizonyíték: [chunk ID + miért]
- Megjegyzés: [ha scaffold — mi az előfeltétel]
```

**`jobs/poc-plan-bridge-review/output/relay-coverage.md`**

A relay meglévő képességeinek térképe: mi van már implementálva a relay-ben ami
lefedi a terv relay funkcióit — és mi az amit valóban meg kell még írni.

---

## Git instrukciók

```bash
cd jobs/poc-plan-bridge-review/workspace/cic-factory
git add jobs/poc-plan-bridge-review/output/
git commit -m "job: poc-plan-bridge-review — bridge map"
git push origin feature/poc-plan-bridge-review
```

**Push csak `feature/poc-plan-bridge-review` branch-re. Soha ne pusholj `main`-re.**

---

## Nyelvi szabály

- Ez a fájl és az output fájlok: **magyarul**
- YAML, JSON, shell, kódrészletek: **angolul**
