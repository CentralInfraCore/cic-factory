# CIC Ökoszisztéma Térkép

Kanonikus referencia — agent session-ök között nem kell újra feltérképezni.
Forrás: `jobs/map-private-source`, `jobs/deep-inspect-private-repos` output-ok (2026-06-06).

---

## Repo áttekintés

| ID | Helyi path | Remote | Szerep |
|---|---|---|---|
| `cic-relay` | `${CIC_RELAY_PATH}` | `CIC_Relay.git` | Runtime végrehajtó (Go 1.24) |
| `cic-schemas` | `.../CIC-Schemas` | `CIC_Schemas.git` | Schema compiler + Vault signing (Python) |
| `cic-schemas/postgresql` | `.../schemas/postgresql` | `CIC_Schemas.git` (branch: postgresql) | PostgreSQL schema példa + signed release |
| `cic-schemas/template` | `.../schemas/template` | `CIC_Schemas.git` (branch: template) | Meta-schema sablon |
| `cic-basic-knowledge` | `.../MCPs/private/source/CentralInfraCore/CIC-basic-knowledge` | `github_private.git` | Fogalmi KB forrás (NDJSON + MD + YAML) |
| `cic-mcp-private` | `.../MCPs/private` | (private) | KB indexáló + MCP szerver (Python, 25 tool) |
| `cic-primitives` | `.../CIC-objs/cic-primitives` | `cic-primitives.git` | Meta-séma réteg: 7 atom + aggregate-k |
| `cic-compute` | `.../CIC-objs/cic-compute` | `cic-compute.git` | Compute domain (VM, bare metal, cloud) |
| `cic-kubernetes` | `.../CIC-objs/cic-kubernetes` | `cic-kubernetes.git` | Kubernetes domain (cluster, pod, service) |
| `cic-network` | `.../CIC-objs/cic-network` | `cic-network.git` | Network domain (switch, VLAN, routing) |
| `cic-storage` | `.../CIC-objs/cic-storage` | `cic-storage.git` | Storage domain (volume, pool, filesystem) |
| `cic-yang` | `.../CIC-objs/cic-yang` | `cic-yang.git` | YANG domain (hálózati konfig) |
| `base-repo` | `.../base` | `base-repo.git` | Sablon repo: Makefile, CI, docs struktúra |
| `ois-github` | `.../OpenIntentSign/github` | `OpenIntentSign/.github.git` | OIS trust modell spec (nem implementáció) |
| `cic-factory` | `${CIC_WORKDIR}` | `cic-factory.git` | Agent factory (ez a repo) |

**Megjegyzés:** Minden CIC-objs repo a `cic-primitives`-re épül. A `base-repo` `remote-merge`-gel adja át Makefile/CI sablonokat az összes repónak.

---

## Adatfolyam

```
github_private (NDJSON gráf + MD docs)
    │ make_source.py indexálja
    ▼
cic-mcp-private/kb_data/pkl/     ← FAISS + BM25 + graph_nodes + graph_edges
    │ MCP stdio protokoll
    ▼
AI asszisztens (Claude) ←→ fejlesztő

CIC_Schemas (Python compiler + Vault signing)
    │ aláírt YAML artifact-ok
    ▼
CIC_Relay/core/cabinet  ← betöltés + ValidateSchema()
    │ wazero WASM végrehajtás
    ▼
ProofTrace (chain_hash + Vault Transit signature)
```

---

## CIC-Relay architektúra — amit agenteknek tudni kell

**A relay stateless végrehajtó motor. Nem hajt végre kódot közvetlenül.**

| Réteg | Csomag | Funkció |
|---|---|---|
| HTTP API | `cmd/relay` | `:8080`, `/set`, `/v1/schema/compile`, `/healthz` |
| Végrehajtó | `core/cabinet` | Schema/module/workflow registry, wazero WASM, ProofTrace |
| Natív modulok | `core/modules/` | `certselfsigned`, `cibuild`, `schemacompile`, `schemapipeline` |
| GitOps | `core/nexus/git` | ExecGitOps, RepoRegistry, git host functions WASM-nak |
| IaC betöltő | `core/nexus/iac` | FileSource, GitSource, IaCLoader, IaCValidator |
| Crypto | `core/nexus/crypto` | Vault Transit signing (ProofTrace) |
| Operator | `core/nexus/operator` | PollingWatcher, Lifecycle, Operator |
| Recorder | `core/nexus/recorder` | GitStateRecorder → Vault-signed audit commit |

**Plugin rendszer:** A valódi végrehajtók `.so` fájlok (Go plugin, `plugin.Open()` + `Lookup()`). A WASM modulok iSDK (guest) + host frame (executor) kettőssel futnak.

**Amit NEM csinál a relay core:**
- ❌ nem hajt végre Terraform-ot közvetlenül
- ❌ nem ír kódot `core/nexus/` alá sem domain logikát — az pluginokban él
- ❌ nem az agenteknek kell `.go` fájlokat írni a `core/` alá új domain logikáért

---

## CIC-Schemas architektúra

```
CIC_Schemas/
  tools/compiler.py          — schema compiler CLI
  tools/releaselib/
    vault_service.py         — VaultService.sign() → vault:v1:... signature
    git_service.py           — release commit-ok
  tools/schemalib/validator.py — séma validáció
  docs/en/
    architecture.md          — schema compiler architektúra
    workflow.md              — fejlesztői workflow
  schemas/postgresql/        — PostgreSQL schema példa (branch: postgresql)
  schemas/template/          — meta-schema sablon (branch: template)
```

**Signing lánc:** `VaultService.sign(digest_b64, key_name)` → `vault:v1:...` — a privát kulcs soha nem kerül ki a Vault-ból.

---

## cic-primitives — 7 irreducibilis atom

`Shape`, `Role`, `Behavior`, `Contract`, `Address`, `Identity`, `Event`

Minden domain objektum (compute, kubernetes, network, storage, yang) ebből vezethető le. Nem IaC tool, nem YANG leíró — meta-séma réteg.

Elérési út: `schemas/atomic/` (7 atom YAML), `schemas/aggregate/`, `schemas/domain/`, `schemas/adapters/`, `schemas/examples/`

---

## PoC demo fázisok — CIC szerepe

| Fázis | Terraform | CIC szerepe |
|---|---|---|
| 8.1 | Kézzel futtatja a fejlesztő | Observer/recorder — figyel, rögzít |
| 8.2 | Kézzel futtatja a fejlesztő | Observer/recorder |
| 8.3 | Kézzel futtatja a fejlesztő | Observer/recorder |
| 8.4 | CIC triggereli | Aktív beavatkozás: `intent/` branch push → OIS check → Terraform apply |

**Kritikus:** 8.1–8.3-ban a CIC nem avatkozik be a végrehajtásba. Ne tervezz CIC→Terraform triggert ezekbe a fázisokba.

---

## MCP (cic-graph) KB lefedettség

A `cic-graph` MCP szerver 25 tool-lal érhető el. KB tartalmaz:
- `context/CONTRACT.md`, `SYMBOLS.md`, `LIMITS.md` — kanonikus axiómák (rule-bonus prioritizálva)
- Relay architektúra fogalmak (ProofTrace, cabinet, nexus)
- Domain objektum sémák (primitives, compute, kubernetes, network, storage, yang)
- PROMPTMAP.yaml task-ok minden repo `ai/` könyvtárából

**MCP konfig:** `CIC/.mcp.json` (stdio mód) — Agent tool örökli a session config-ot. `run-job.sh` nem örökli (explicit `--mcp-config` flag szükséges).

---

## Vault — keresztülívelő függőség

| Repo | Vault szerepe | Kulcsnév |
|---|---|---|
| CIC_Schemas | Schema artifact signing (Transit) | `cic-my-sign-key`, `cic-dev-sign-key` |
| CIC_Relay | ProofTrace signing, PKI bootstrap | `cic-root-ca-key` |
| cic-factory | Commit-msg hook signing | `cic-my-sign-key` |

**PKI lánc:** `Root CA → Intermediate CA → CIC Source CA → Developer cert`
(`CN=Gabor Zoltan Sinko`, `email:sgz@centralinfracore.hu`)

**Scaffold figyelmeztetés:** `pki_verify.go` bekötése scaffold — CA lánc üzemeltetési infrastruktúrája (Vault PKI engine) még nem bootstrapped.

---

## repo-specifikus AI kontextus fájlok

Minden repóban (ahol van) az `ai/` könyvtár tartalmaz:
- `ONBOARDING.md` — hogyan állj neki
- `SYSTEM_CONTEXT.md` — kötelező session kontextus
- `PROMPTMAP.yaml` — task-ok listája (MCP-n keresztül elérhető)
- `DECISIONS.md` — döntési log
- `ROADMAP.md` — milestone térkép

Ezeket az agent **olvashatja a klónból** — nem kell MCP-n keresztül előkeresni.

---

## Háromszintű státusz (emlékeztető)

| Státusz | Jelentés |
|---|---|
| **implemented** | kódban él, tesztek fedik, CI zöld |
| **scaffold** | kódban van, szándékosan bekötetlen — előfeltétel hiányzik |
| **concept** | dokumentált, nincs runtime megfelelő |

Scaffold nem hiba — szándékos és előfeltételhez kötött.

---

*Frissíteni: ha új repo csatlakozik, vagy architektúrális döntés változik. Forrás: `jobs/map-private-source/output/repos.yaml` + `jobs/deep-inspect-private-repos/output/`.*
