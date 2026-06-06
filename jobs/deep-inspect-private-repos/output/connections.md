# Keresztkapcsolatok — A Négy CIC Repo Összefüggése

**Dátum:** 2026-06-06

---

## Repók és Szerepük

| Repo | Helyi neve | Szerepkör |
|---|---|---|
| `CIC_Relay` | CIC-Relay | Runtime végrehajtó (Go) |
| `CIC_Schemas` | CIC-Schemas | Schema compiler + signing (Python) |
| `cic-mcp-private` | MCPs/private | KB indexáló + MCP szerver (Python) |
| `github_private` | CIC-basic-knowledge | Fogalmi KB forrás (NDJSON + Markdown + YAML) |

---

## Adatfolyam — Felső Szintű

```
github_private (fogalmi gráf + docs)
    │
    │  [make_source.py indexálja]
    ▼
cic-mcp-private / kb_data/pkl/
    │
    │  [MCP stdio/SSE protokoll]
    ▼
AI asszisztens (Claude) ← → fejlesztő
    │
    │  [döntések, tervezés, kód]
    ▼
CIC_Schemas (Python compiler + Vault signing)
    │
    │  [aláírt YAML artifact-ok]
    ▼
CIC_Relay (Go runtime betölti, validálja, futtatja)
```

---

## Részletes Keresztkapcsolatok

### 1. `github_private` → `cic-mcp-private`

**Kapcsolat típusa:** Forrás → Indexált KB

A `CIC-basic-knowledge` submodule-ként él a `MCPs/private/source/CentralInfraCore/CIC-basic-knowledge/` alatt. A `make_source.py` feldolgozza:
- NDJSON gráf node-okat és éleket
- Markdown fájlokat (chunk-okra bontja)
- YAML companion metadata-t (tags, category, status, used_in)

**Output:** `kb_data/pkl/` — FAISS + BM25 + inverted_index + graph_nodes + graph_edges pickle fájlok.

**Konkrét mechanizmus:**
```python
# make_source.py
process_md_file(file_path)  # md → chunks
load_companion_yaml(md_path)  # .yaml → metadata
# + NDJSON gráf feldolgozás
```

**Szinkronizáció:** A `cic-mcp-private` `main` branch commit-jei között rendszeresen frissítik a submodule pointert (`chore: update all source submodules to latest commits`).

---

### 2. `CIC_Schemas` → `CIC_Relay`

**Kapcsolat típusa:** Artifact producer → Artifact consumer

A CIC_Schemas előállítja a Vault-aláírt YAML séma artifact-okat. A CIC_Relay ezeket betölti és validálja a `core/cabinet` rétegen keresztül.

**Betöltési mechanizmus (Relay oldalon):**
```go
// cmd/relay/bootstrap.go / loadEmbeddedComponents()
cabinet.NewAPI(cabinetSvc).Set(ctx, &SetPayload{...})
// a schema ID-k "relay.config@1.0", "ci.build@1.0" stb. formátumúak
```

**Validáció:**
```go
// core/cabinet/validate.go
cabinet.ValidateSchema([]string{"relay.config@1.0"}, configMap)
// $schema kulcs alapján azonosítja a sémát
```

**Signing lánc:**
- CIC_Schemas: `tools/releaselib/vault_service.py` → `VaultService.sign(digest_b64, key_name)` → `vault:v1:...` signature
- CIC_Relay: `core/nexus/crypto/VaultCryptoService` → ugyanolyan Vault Transit kulcsot használ

**Megjegyzés:** A közvetlen import nem létezik — a kapcsolat artifact-alapú (signed YAML fájlok). A Relay nem importálja a Schemas Python kódját.

---

### 3. `CIC_Relay` → `cic-mcp-private` (KB-n keresztül)

**Kapcsolat típusa:** Kód → Dokumentált fogalom → KB node

A Relay forráskódja (`.go` fájlok + companion `.yaml` fájlok) beindexált a `make_source.py` által. Az MCP szerver így expozálni tudja a Relay architektúra fogalmait.

**Konkrét flow:**
```
CIC-Relay/core/cabinet/proof_trace.go
    + proof_trace.yaml (companion)
        → make_source.py → chunks.pkl + graph_nodes.pkl
            → search_query("ProofTrace chain_hash") → AI asszisztens kontextus
```

**Különleges szerepű fájlok:**
- `context/CONTRACT.md` — kanonikus kontraktus, rule-bonus-szal prioritizált
- `context/SYMBOLS.md` — szimbólum lista, rule-bonus-szal prioritizált
- `context/LIMITS.md` — limitek, rule-bonus-szal prioritizált
- `ai/SYSTEM_CONTEXT.md`, `ai/ROADMAP.md` — AI session-ökben kötelező kontextus

---

### 4. `CIC_Schemas` → `cic-mcp-private` (KB-n keresztül)

**Kapcsolat típusa:** Python tool kód + docs → Indexált KB

Hasonlóan a Relay-hez, a CIC_Schemas Python tool-jai és dokumentációi beindexáltak.

**Különösen fontos:**
- `tools/vault-sign-agent.md` — signing workflow leírás
- `docs/en/architecture.md` — schema compiler architektúra
- `docs/en/workflow.md` — fejlesztői workflow
- `tools/schemalib/validator.py` — validator integrity logika

---

### 5. `github_private` → `CIC_Relay` (fogalmi szinten)

**Kapcsolat típusa:** Concept dokumentáció → Runtime implementáció

A `github_private` fogalmi dokumentációi (különösen `docs/*/reality/`) leírják azokat a koncepciókat, amelyeket a Relay implementál. Ez nem kód-import — hanem architektúrális konzisztencia.

**Példák:**
- `ProofTrace` fogalom dokumentálva a KB-ban → implementálva a `core/cabinet/proof_trace.go`-ban
- `trusted state` fogalom → `core/nexus/crypto` Vault signing
- `deterministic execution` fogalom → `pkg/canonicaljson` + WASM kanonizálás

**Bridge státusz (CLAUDE.md terminológiában):**
```
concept (github_private) → implemented (CIC_Relay)
                        ↑
                   bridge megvan: code + tests
```

---

### 6. `cic-mcp-private` → Fejlesztő (task management)

**Kapcsolat típusa:** PROMPTMAP.yaml olvasás → Task lifecycle

Az MCP szerver `list_tasks`, `claim_task`, `complete_task`, `fail_task`, `record_decision` eszközei az összes repo `ai/PROMPTMAP.yaml` fájljait olvassák. Ez az egész CIC fejlesztési workflow gerince:

**Érintett PROMPTMAP.yaml fájlok:**
- `CIC-Relay/ai/PROMPTMAP.yaml`
- `CIC-Schemas/ai/PROMPTMAP.yaml` (ha létezik)
- `cic-primitives/ai/PROMPTMAP.yaml`
- Más domain repók `ai/` könyvtárai

---

## Shared Infrastructure (base-repo)

Mindhárom kód-repo (`CIC_Relay`, `CIC_Schemas`, `cic-mcp-private`) és az összes domain repo ugyanabból a `base-repo`-ból vette át a következőket `remote-merge`-gel:

| Komponens | Tartalom |
|---|---|
| `mk/infra.mk` | Makefile fragmentek |
| `.github/workflows/` | CI workflow sablonok |
| `tools/compiler.py` | Schema compiler CLI |
| `tools/releaselib/` | Vault + Git service |
| `tools/vault-sign-agent.sh` | Signing agent |
| `project.yaml` struktúra | Aláírt metaadat formátum |
| `md.meta.schema.yaml` | Markdown companion séma |
| `go.meta.schema.yaml` | Go companion séma |

Ez azt jelenti, hogy a **Python tool réteg** (`compiler.py`, `releaselib/`, `schemalib/`) minden CIC repóban jelen van — de az `authoritative` implementáció a `CIC_Schemas` repóban él.

---

## Vault — Keresztülívelő Függőség

A HashiCorp Vault mind a három kód-repo architektúrájában megjelenik:

| Repo | Vault szerepe |
|---|---|
| `CIC_Schemas` | Schema YAML artifact signing (Transit), cert tárolás (KV v2) |
| `CIC_Relay` | ProofTrace workflow signing (Transit), bootstrap PKI, dev Vault |
| `cic-mcp-private` | Indirekt: a release-elt KB artifact-okat validálja a Relay |

**Közös Vault kulcsnév konvenció:**
- `cic-dev-sign-key` — fejlesztői Transit kulcs
- `cic-my-sign-key` — fejlesztői signing kulcs (project.yaml-ban)
- `cic-root-ca-key` — Root CA kulcs

---

## PKI Lánc — Teljes Kép

```
CIC Root CA (embedded: embedded/pki/root_ca.pem)
    │
    └── Intermediate CA (embedded/pki/intermediate_ca.pem)
            │
            └── CIC Source CA (embedded/pki/cic-source-ca.pem)
                    │
                    └── Developer cert (project.yaml / createdBy.certificate)
                            Subject: CN=Gabor Zoltan Sinko
                            SANs: email:sgz@centralinfracore.hu
```

A PKI lánc bootstrap probléma (SYSTEM_CONTEXT.md-ből): a `pki_verify.go` bekötése scaffold állapotban van, mert a CA lánc teljes üzemeltetési infrastruktúrája (Vault PKI engine, cert megújítás) még nem bootstrapped.

---

## Összefoglalás: Mit Csinál Melyik Repo

```
github_private:
  → Fogalmakat definiál (mi a ProofTrace, mi a trusted state)
  → Gráf node-okat és éleket generál (NDJSON)
  → YAML companion metadatával gazdagítja a tartalmát

cic-mcp-private:
  → Beindexálja az összes forrást (make_source.py)
  → Expozálja a KB-t az AI asszisztensnek (25 MCP tool)
  → Kezeli a fejlesztési workflow-t (task management, PROMPTMAP)
  → Tartja a submodule pointer-eket az összes forrás repóra

CIC_Schemas:
  → Validálja a YAML séma fájlokat (schemalib)
  → Vault-tal aláírja a schema artifact-okat (releaselib)
  → Git-en keresztül publikálja a signed release-eket
  → Template-et ad az összes domain repó számára

CIC_Relay:
  → Betölti és validálja a signed schema artifact-okat
  → WASM modul végrehajtás (wazero)
  → ProofTrace hash-lánc képzés és signing
  → HTTP API :8080 (a rendszer futtatható runtime-ja)
```
