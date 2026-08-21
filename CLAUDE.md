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
orchestrátor: input.md + meta.yaml → commit main → push          [pending]
run-job.sh:   pending → running commit → workspace klón → feature branch
agent:        olvas jobs/<job-id>/ → ír output/ → commitol + pushol feature/<job-id>
run-job.sh:   agent exit 0 → awaiting_review                     [NEM done]
orchestrátor: validate-output.sh + review.md → done → merge main
```

**`agent_done` ≠ `done`.** Az agent exit 0-ja egy állítás az agentről: befejezte.
A `done` egy állítás a jobról: a kimenete elfogadható. A kettő különböző dolog,
és külön állapot tartozik hozzájuk. Az `awaiting_review`-ból `done`-ba kizárólag
a `/job-close` visz, mert csak az futtat output-kaput és csak az termel review
artifactot — a `run-job.sh` egyiket sem teszi, tehát nincs mire alapoznia.

### Git a bizalom forrása

A Vault-aláírt commit maga az igazolás (`commit-msg` hook, `cic-my-sign-key`).
Az agent a klónból commitol és pushol a feature branch-re — review artifact, nem véglegesítés.
Push `main`-re kizárólag az orchestrátor joga.

**Az orchestrátori review is bizonyítékot termel.** Minden réteg artifactot hagy
(aláírt commit, claim-evidence tábla, `deadcode` output, headSha) — kivéve régen a
review-t, ami egy chat-üzenet volt: aláíratlan, nem reprodukálható, a session végén
elveszett. Ezért kötelező a `jobs/<job-id>/review.md` (sablon: `/job-close` 4. pont).
Amihez nem tudsz verifikációs módszert írni, az a „nem igazolt" sorba megy.

---

## Job struktúra

```
jobs/
  index.yaml                  ← auto-generált állapottérkép (tools/update-index.sh)
  .schema/meta.yaml           ← kötelező mezők sémája
  <job-id>/
    input.md                  ← agent prompt (magyarul, git-tracked)
    meta.yaml                 ← lifecycle + usage (költség/turns/tokenek, git-tracked)
    review.md                 ← orchestrátori review artifact (kötelező merge előtt)
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
status: "pending"             # pending | running | awaiting_review | done | error
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
| `./tools/run-job.sh <job-id> [agent-id]` | **Előbb a `validate-spec.sh` kaput futtatja** — NO-GO esetén nem indul. `--skip-spec-gate` megkerüli, de a `meta.yaml` `spec_gate` mezőjébe `skipped` kerül. Végrehajtás: klón, running→awaiting_review, commit, push. **Nem zár le** — a `done` a `/job-close` dolga. Injektálja a `kb_focus`-t, `--max-turns` guardot ad, és JSON-ból kiírja a költséget a `meta.yaml`-ba |
| `./tools/validate-spec.sh <job-id>` | **Gépi kapu indítás előtt** (K1–K11). NO-GO → ne indítsd az agentet |
| `./tools/close-job.sh <job-id>` | **Az egyetlen `awaiting_review → done` átmenet.** Elutasít, ha a státusz nem `awaiting_review`, ha az output-kapu NO-GO, ha a `review.md` hiányzik/üres/befejezetlen, vagy ha a futás megkerülte a spec-kaput és a review ezt nem ismeri el. `--dry-run` csak ellenőriz |
| `./tools/validate-output.sh <job-id>` | **Gépi kapu merge előtt** (O1–O5). NO-GO → ne zárd le a jobot |
| `./tools/update-index.sh` | `jobs/index.yaml` újragenerálása (modell, költség, turns, `totals:`) |
| `~/.claude-personal/agents/new-agent.sh <név>` | Új izolált agent config létrehozása |

### A két gépi kapu

```
spec  →  validate-spec.sh   →  agent fut  →  validate-output.sh  →  emberi review  →  merge
         (K1–K11)                             (O1–O5)                (review.md)
```

Az elv: **amit gép el tud dönteni, azt döntse el a gép.** A drága figyelem (te / erős
modell) a tartalomra menjen, ne a formára. A `validate-output.sh` első éles futása pont
egy olyan hibát talált, amit emberi review és merge átengedett.

---

## Agent auth

```
~/.claude-personal/agents/<id>/
  .credentials.json       ← symlink → ~/.claude-personal/.credentials.json
  settings.json           ← izolált config, auto mode
```

Indítás: `CLAUDE_CONFIG_DIR=~/.claude-personal/agents/<id> claude --print "..." --mcp-config CIC/.mcp.json`

---

## Ökoszisztéma térkép

**Olvasd el session elején:** [`docs/ecosystem-map.md`](docs/ecosystem-map.md)

Tartalmaz: összes repo path + szerep, adatfolyam, relay architektúra, demo fázisok (CIC szerepe 8.1–8.4), MCP lefedettség, Vault signing lánc. Ne kelljen job-onként újra feltérképezni.

## Repo helyek (CIC ökoszisztéma)

A path-ok gép-specifikusak. Add meg `tools/env.sh`-ban (sablon: `tools/env.sh.example`).

| Alrendszer | Env var |
|---|---|
| `CIC-Relay` | `$CIC_RELAY_PATH` |
| `CIC-Schemas` | `$CIC_SCHEMAS_PATH` |
| `CIC-basic-knowledge` | `$CIC_KB_PATH` |
| MCP KB adat | `$CIC_MCP_KB_DATA` |
| MCP szerver | `$CIC_MCP_SERVER` |

---

## MCP szerver

A `cic-graph` MCP szerver konfigja: `CIC/.mcp.json` (stdio mód).
`run-job.sh` automatikusan átadja: `--mcp-config $CIC_MCP_CONFIG` (derive-olva vagy explicit).
Boot sequence: `kb_status` → `search_nodes` → státusz ellenőrzés.

---

## Felülvizsgált AI párbeszédek

| Fájl | Döntés |
|---|---|
| `CIC-Relay/theads/thead01` | OTel ≠ ProofTrace helyettesítő — külön rétegek |
| `CIC-Relay/theads/thead02` | Nested containment elvetett — file-referencia alapú gráf |
| `CIC/teads/relay-trust-todo.md` | Háromrétegű relay trust modell (L0–L7) |

Ezek döntési alapok — a `rejected` részeket ne tervezd újra.
