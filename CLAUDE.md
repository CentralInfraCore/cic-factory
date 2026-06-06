# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Mi ez a könyvtár

A `cic-factory` a CIC ökoszisztéma hierarchikus agent factory-ja. Git-követett job-ok, domain-specializált kontextus, izolált agent workspace-ek.

A szülő (`CIC/CLAUDE.md`) tartalmazza az ökoszisztéma-szintű kontextust (boot sequence, reasoning módok, háromszintű státusz). Azt olvasd el először.

---

## Nyelvi szabály

- Dokumentáció, Claude-utasítások, agent promptok: **magyarul**
- Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**

---

## Működési modell

### Szerepek

| Szereplő | Hol él | Mit csinál |
|---|---|---|
| Orchestrátor (te + Claude) | live `workdir/` | job spec létrehozás, review, merge döntés |
| Agent | `jobs/<job-id>/workspace/cic-factory/` (klón) | klónban dolgozik, feature branch-re commitol és pushol |

### Job lifecycle

```
orchestrátor: input.md + meta.yaml → commit main → push
run-job.sh:   pending → running commit → workspace klón → feature branch
agent:        olvas jobs/<job-id>/ → ír output/ → commitol + pushol feature/<job-id>
orchestrátor: review GitHubon → merge main
```

### Git a bizalom forrása

A Vault-aláírt commit maga az igazolás (`commit-msg` hook, `cic-my-sign-key`).
Az agent a klónból commitol és pushol a feature branch-re — review artifact, nem véglegesítés.
Push `main`-re kizárólag az orchestrátor joga.

---

## Job struktúra

```
jobs/
  index.yaml                  ← auto-generált állapottérkép (tools/update-index.sh)
  .schema/meta.yaml           ← kötelező mezők sémája
  <job-id>/
    input.md                  ← agent prompt (magyarul, git-tracked)
    meta.yaml                 ← lifecycle: pending | running | done | error (git-tracked)
    ref/                      ← referencia anyagok (opcionális, git-tracked)
    workspace/                ← gitignored; agent klónjai élnek itt
      cic-factory/            ← git clone + feature/<job-id> branch
      <egyéb repo>/           ← ha a job más repót is igényel
```

### Sub-job lifecycle

Az agent a cic-factory klónjában (`workspace/cic-factory/`) hozza létre a sub-job speceket:
```
workspace/cic-factory/jobs/<sub-job-id>/input.md + meta.yaml
```
Ezek a feature branch-re kerülnek. Merge után az orchestrátor a live workdir `jobs/<sub-job-id>/`-ban látja — és `run-job.sh <sub-job-id>`-val futtathatja.

### meta.yaml kötelező mezők

```yaml
schema_version: "1.0"
job_id: ""
parent_job_id: ""             # "" ha gyökér
level: ""                     # orchestrator | repo | domain
target:
  repo: ""
  path: ""                    # domain szinten kötelező
kb_focus: []                  # cic-graph focus_pack node-id-k
promptmap_ref: ""
agent:
  config_dir: ""              # ~/.claude-personal/agents/<id>
  model: ""
workplace:
  repos: []                   # pl. ["CIC-Relay"] — workspace/<repo>/ alá klónozva
  branch: ""                  # feature/<job-id>
status: "pending"             # pending | running | done | error
error_message: ""
timestamps:
  created: ""
  started: ""
  completed: ""
```

---

## Eszközök

| Parancs | Mit csinál |
|---|---|
| `./tools/run-job.sh <job-id> [agent-id]` | Teljes lifecycle: klón, running→done, commit, push |
| `./tools/update-index.sh` | `jobs/index.yaml` újragenerálása |
| `~/.claude-personal/agents/new-agent.sh <név>` | Új izolált agent config létrehozása |

---

## Agent auth

```
~/.claude-personal/agents/<id>/
  .credentials.json       ← symlink → ~/.claude-personal/.credentials.json
  settings.json           ← izolált config, auto mode
```

Indítás: `CLAUDE_CONFIG_DIR=~/.claude-personal/agents/<id> claude --print "..." --mcp-config CIC/.mcp.json`

---

## Repo helyek (CIC ökoszisztéma)

| Alrendszer | Forrás path |
|---|---|
| `CIC-Relay` | `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay` |
| `CIC-Schemas` | `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Schemas` |
| `CIC-basic-knowledge` | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/source/CentralInfraCore/CIC-basic-knowledge` |
| MCP KB adat | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/kb_data/pkl` |
| MCP szerver | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/mcp-server/server.py` |

---

## MCP szerver

A `cic-graph` MCP szerver konfigja: `CIC/.mcp.json` (stdio mód).
`run-job.sh` automatikusan átadja: `--mcp-config /home/sinkog/sync/claude_factory/CIC/.mcp.json`
Boot sequence: `kb_status` → `search_nodes` → státusz ellenőrzés.

---

## Felülvizsgált AI párbeszédek

| Fájl | Döntés |
|---|---|
| `CIC-Relay/theads/thead01` | OTel ≠ ProofTrace helyettesítő — külön rétegek |
| `CIC-Relay/theads/thead02` | Nested containment elvetett — file-referencia alapú gráf |
| `CIC/teads/relay-trust-todo.md` | Háromrétegű relay trust modell (L0–L7) |

Ezek döntési alapok — a `rejected` részeket ne tervezd újra.
