# CLAUDE.md

Ez a fájl a `cic-factory` **CIC-specifikus** kontextusát tartalmazza: hogyan
használja a CIC a gyárat.

**A működési modell nem itt van.** A job lifecycle, az állapotgép, a job-struktúra
és a gépi kapuk a [`SPEC.md`](SPEC.md)-ben élnek — az a
[`cic-factory-core`](https://github.com/CentralInfraCore/cic-factory-core)-ból
átvett specifikáció. Azt olvasd el először; ez a fájl csak azt teszi hozzá, ami
CIC.

A szülő (`CIC/CLAUDE.md`) az ökoszisztéma-szintű kontextus: boot sequence,
reasoning módok, háromszintű státusz.

---

## Nyelvi szabály

- Dokumentáció, Claude-utasítások, agent promptok: **magyarul**
- Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**

---

## Honnan jön a tooling

A `tools/`, a `.claude/commands/`, a `jobs/.schema/` és a `SPEC.md` **nem itt
készül**. A `cic-factory-core` adja ki release tagen, és ez a repo merge-eli.

A jelenlegi verziót a [`dependency.yaml`](dependency.yaml) rögzíti.

**Amit ezekben itt módosítasz, azt a következő átvétel felülírja.** Ha a magban
van a hiba, ott javítsd — a `cic-factory-core` issue-i között.

Kivétel: `tools/relay-build-test.sh` — CIC-Relay buildet hajt, szándékosan nem
került a magba.

---

## Ökoszisztéma térkép

**Olvasd el session elején:** [`docs/ecosystem-map.md`](docs/ecosystem-map.md)

Tartalmaz: összes repo path + szerep, adatfolyam, relay architektúra, demo
fázisok (CIC szerepe 8.1–8.4), MCP lefedettség, Vault signing lánc. Ne kelljen
job-onként újra feltérképezni.

---

## Repo helyek (CIC ökoszisztéma)

A path-ok gép-specifikusak. Add meg `tools/env.sh`-ban (sablon:
`tools/env.sh.example`).

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
A `run-job.sh` automatikusan átadja: `--mcp-config $CIC_MCP_CONFIG` (derive-olva
vagy explicit). Boot sequence: `kb_status` → `search_nodes` → státusz ellenőrzés.

A `meta.yaml` `kb_focus` mezője `cic-graph` `focus_pack` node-id-ket vár.

---

## Agent auth

```
~/.claude-personal/agents/<id>/
  .credentials.json       ← symlink → ~/.claude-personal/.credentials.json
  settings.json           ← izolált config, auto mode
```

Indítás: `CLAUDE_CONFIG_DIR=~/.claude-personal/agents/<id> claude --print "..." --mcp-config CIC/.mcp.json`

Új agent: `~/.claude-personal/agents/new-agent.sh <név>`

---

## Felülvizsgált AI párbeszédek

| Fájl | Döntés |
|---|---|
| `CIC-Relay/theads/thead01` | OTel ≠ ProofTrace helyettesítő — külön rétegek |
| `CIC-Relay/theads/thead02` | Nested containment elvetett — file-referencia alapú gráf |
| `CIC/teads/relay-trust-todo.md` | Háromrétegű relay trust modell (L0–L7) |

Ezek döntési alapok — a `rejected` részeket ne tervezd újra.

---

## Licenc

Ez a repo **vegyes**: a saját tartalma CC BY-NC-SA 4.0, az átvett tooling
AGPL-3.0-or-later, két hook MIT. Minden forrásfájl SPDX-fejlécet hordoz — lásd
[`LICENSE.md`](LICENSE.md).
