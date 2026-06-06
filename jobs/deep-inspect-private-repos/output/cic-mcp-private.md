# cic-mcp-private — Részletes Feltárás

**Dátum:** 2026-06-06
**Lokális elérési út:** `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private`
**Remote URL:** `git@github.com:CentralInfraCore/cic-mcp-private.git`
**Aktív branch:** `d/feature-chunk-dedup` (párhuzamosan: `main`)
**Python verzió:** 3.12 (pycache tanúsítja)

---

## Mi ez a repo?

A `cic-mcp-private` a **privát MCP szerver** a CIC ökoszisztéma AI-asszisztens integrációjához. Ez az a szoftver, amelyet az AI Claude asszisztens a CIC KB (tudásbázis) eléréséhez használ session-ök során. A `cic-graph` MCP szerver neve (FastMCP("cic-graph")).

A repo tartalmaz:
1. **MCP szerver** (`mcp-server/server.py`) — a KB-t expozáló Python FastMCP szerver
2. **KB indexáló** (`make_source.py`) — a forrás repókból KB-t épít (FAISS, BM25, NDJSON gráf)
3. **KB adatfájlok** (`kb_data/`) — előre buildelt index (pkl, json, sqlite)
4. **Forrás submodulok** (`source/`) — az összes CIC repo git submodule-ként

---

## Könyvtárstruktúra (3 szint)

```
MCPs/private/
  mcp-server/
    server.py            — FastMCP szerver (1643 sor, 25 tool, stdio + SSE)
    README.md            — rövid leírás
  kb_data/
    json/
      chunks.json        — szövegdarabok JSON formátumban
      graph_nodes.json   — KB gráf node-ok
      graph_edges.json   — KB gráf élek
      inverted_index.json — invertált index (token → chunk)
      metadata_index.json — metadata index
    pkl/
      chunks.pkl         — betöltött chunks pickle
      graph_nodes.pkl    — node-ok pickle
      graph_edges.pkl    — élek pickle
      inverted_index.pkl — invertált index pickle
      bm25.pkl           — BM25 index
      faiss.index        — FAISS vektoros index
      chunk_ids.pkl      — chunk ID-k (FAISS sorrendhez)
      model_name.pkl     — embedding model neve
      metadata_index.pkl — metadata index pickle
    edge_types.md        — éltípus dokumentáció
    .gitignore           — pkl és sqlite fájlok nem commitálva
  sqlite_data/
    knowledge_base.sqlite — SQLite KB (opcionális)
    db_schema.json        — SQLite séma leírás
    .gitignore
  source/                — git submodulok
    CentralInfraCore/
      base/              — base-repo worktree-k
      CIC-basic-knowledge/ — github_private (fogalmi KB)
      CIC-objs/          — domain schema repók
      CIC-Relay/         — CIC_Relay Go runtime
      CIC-Schemas/       — CIC_Schemas compiler
      schemas/           — CIC_Schemas postgresql + template worktree
    OpenIntentSign/
      github/            — OIS community repo
  docs/
    en/
      architecture.md    — angol architektúra
      concept/
    hu/
      architecture.md    — magyar architektúra
      concept/
  features/
    feature-001/spec.md
    feature-002/spec.md
  mk/
    infra.mk             — Makefile fragmentek
  make_source.py         — KB indexáló script
  Makefile               — build/test/run target-ek
  Dockerfile             — Python toolchain container
  docker-compose.yml
  project.yaml           — aláírt repo metaadat
  project.schema.yaml
  pyproject.toml
  pytest.ini
  requirements.in
  requirements.txt       — pin-elt Python deps
  renovate.json
  schemas.json           — schema leírás
  MANIFEST.sha256
  README.md
  LICENSE.md
  go.meta.schema.yaml
  md.meta.schema.yaml
  .mcp.json              — MCP szerver konfig (generált)
  .mcp.json.tpl          — MCP konfig sablon
  .gitmodules            — submodule lista
  IaC_PRIMITIVE_MEMO.md  — IaC primitív memó
  CLAUDE.md              — AI Claude instrukciók
  .claude/settings.local.json
```

---

## Entry Point — `mcp-server/server.py`

**FastMCP("cic-graph")** — a szerver neve `cic-graph`, ami megfelel a CLAUDE.md-ben hivatkozott `mcp__cic-graph__*` tool névtérnek.

### Indítás

```python
# stdio (alapértelmezett, Claude Code / AI asszisztens számára)
python mcp-server/server.py

# SSE HTTP server
python mcp-server/server.py --sse [--host 127.0.0.1] [--port 8000]
```

### KB betöltés

A `load_kb()` függvény (@lru_cache, egyszer tölt) betölti:
- chunks.pkl, graph_nodes.pkl, graph_edges.pkl, inverted_index.pkl
- FAISS index + chunk_ids.pkl
- BM25 index
- SentenceTransformer embedding model (`paraphrase-multilingual-MiniLM-L12-v2`, multilingual)
- metadata_index.pkl

**Env változók:** `KB_DATA_DIR`, `CHUNKS_PKL`, `NODES_PKL`, `EDGES_PKL`, `INVERTED_PKL`, `FAISS_INDEX`, `BM25_PKL`, `CHUNK_IDS_PKL`, `MODEL_NAME_PKL`, `METADATA_INDEX_PKL`, `TOPK`, `MAX_TOPK`, `MAX_NEIGHBORS`, `MAX_RESOLVE_MATCHES`, `ENABLE_SEARCH_CODE`

---

## MCP Tool Katalógus (25 tool)

### KB állapot és újratöltés
- `kb_status()` — KB fájlok elérhetősége és mtimes
- `reload_kb()` — force-reload (lru_cache törlés)

### Graph séma
- `list_edge_types()` — ismert éltípusok listája
- `list_node_types()` — ismert nodetípusok listája

### Keresés
- `search_token(token, top_k)` — invertált index alapú token keresés
- `search_query(query, top_k, threshold)` — hibrid keresés (BM25 + FAISS semantic, rule bonus-szal)
- `search_code(code_snippet, top_k)` — kód snippet keresés (ha `ENABLE_SEARCH_CODE=true`)
- `search_nodes(query, top_k)` — node keresés name/label/tags alapján

### Navigáció
- `resolve_path(file_path, mode, limit)` — fájl path alapú chunk lookup
- `get_chunk(chunk_id, max_chars)` — chunk tartalom lekérés
- `get_node(node_id)` — node lekérés ID alapján
- `neighbors(node_id, edge_type, limit)` — szomszéd node-ok (gráf bejárás)

### AI Context összerakás
- `focus_pack(query, depth, top_k, max_rules)` — kontextus csomag AI prompthoz (rule prioritization + seed nodes + BFS)
- `explain_node(node_id)` — node mélyített leírása (chunk + szomszédok)
- `find_nodes(...)` — node keresés több kritérium alapján (type, tag, category, used_in)
- `impact_analysis(node_id, max_depth)` — hatáselemzés (mit érint ez a node, BFS)
- `guided_path(topic, max_steps)` — irányított gráf bejárás témához

### Companion YAML kezelés
- `missing_companions(...)` — hiányzó .yaml companion fájlok azonosítása
- `update_companion(file_path, fields)` — companion YAML mezők frissítése

### Task Management (PROMPTMAP.yaml)
- `list_tasks(repo, sprint, status)` — task-ok listázása
- `get_next_task(repo, sprint)` — következő elvégzendő task
- `claim_task(task_id, repo)` — task lefoglalása
- `complete_task(task_id, repo, result_note)` — task lezárása
- `fail_task(task_id, reason, repo)` — task hibásra állítása

### Döntés rögzítés
- `record_decision(...)` — architektúrális döntés rögzítése (PROMPTMAP.yaml decision log)

---

## KB indexáló — `make_source.py`

A `make_source.py` feldolgozza az összes `source/` alkönyvtárban lévő forrást és felépíti a KB-t:

```python
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

**Forrás formátumok:**
- `.md` fájlok → szöveg chunk-ok (fejezetek szerint darabolva)
- `.yaml` companion fájlok → metadata enrichment (tags, category, used_in, status)
- Go `.go` fájlok → kód chunk-ok (ha YAML companion is létezik)
- NDJSON gráf fájlok (`_graph.ndjson`) → gráf node-ok és élek

**Output:**
- chunks.pkl, graph_nodes.pkl, graph_edges.pkl, inverted_index.pkl
- FAISS vektoros index (paraphrase-multilingual-MiniLM-L12-v2)
- BM25 index (tokenized)
- metadata_index.pkl

**Tokenizálás:** lowercase, alpha-only tokenek, CamelCase szétbontással (CentralInfraCore → Central Infra Core).

---

## Függőségek (`requirements.txt`, Python 3.11)

```
Fő közvetlen függőségek:
  faiss (via faiss-cpu)                — vektoros keresés
  sentence-transformers                — embedding model
  numpy                                — vektormalgebra
  rank_bm25                            — BM25 lexikális keresés
  mcp[fastmcp]                         — MCP protokoll (FastMCP szerver)
  pyyaml==6.0.3                        — YAML
  jsonschema==4.25.1
  cryptography==46.0.2
  requests==2.32.5
  semver==3.0.4

Fejlesztői eszközök (ugyanaz mint CIC_Schemas/CIC_Relay):
  pytest, black, mypy, ruff, isort, bandit, yamllint
```

---

## Git Branching

- `main` — stabil
- `d/feature-chunk-dedup` — aktív fejlesztés (chunk dedup logika)

**Utolsó commit-ok:**
- `fix: clean tokenizer output — strip punctuation, use basename in package chunks`
- `feat: improve KB indexability for Go YAML chunks`
- `feat: add AI reasoning protocol + impact_analysis and guided_path tools`
- `feat: add typed CIC-Schemas submodules pinned to release tags`

---

## Submodulok (`.gitmodules`)

Az összes CIC forrás repo submodule-ként van bekötve a `source/` alá — ez biztosítja, hogy a KB indexáláshoz mindig a helyes verzió álljon rendelkezésre.

---

## CIC Kapcsolódások

- **CIC-basic-knowledge (github_private)**: a fő KB forrás — NDJSON gráf, Markdown docs, YAML companion fájlok
- **CIC-Relay**: forrásként beindexált (Go fájlok + YAML companion-ok + docs); az MCP szerver expozálja a Relay architektúrát
- **CIC_Schemas**: forrásként beindexált (Python tools + docs + séma YAML-ok)
- **cic-primitives + domain repók**: a schemas/ submodulok révén beindexált
- **PROMPTMAP.yaml fájlok**: a task management eszközök (list_tasks, claim_task, complete_task) az összes repo PROMPTMAP.yaml-ját olvasnak — ez a CIC fejlesztési workflow gerince
