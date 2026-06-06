# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Mi ez a könyvtár

Ez a `workdir` a CIC ökoszisztéma Claude Code session-jainak munkaterülete. Önmagában nem tartalmaz forráskódot — a tényleges repók a git.partners repositoryban élnek, és a `pack-workspace.sh` csomagolja ide őket szükség szerint.

A szülő könyvtár (`CIC/CLAUDE.md`) tartalmazza az ökoszisztéma-szintű kontextust (boot sequence, reasoning módok, bridge detector, háromszintű státusz). Azt olvasd el először.

---

## Nyelvi szabály

- Dokumentáció, Claude-utasítások, agent promptok: **magyarul**
- Forráskód, YAML, JSON, shell script, változónevek, kódon belüli komment: **angolul**

---

## Repo helyek

| Alrendszer | Forrás path |
|---|---|
| `base-repo` | `/home/sinkog/sync/git.partners/CentralInfraCore/base-repo` |
| `CIC-Relay` | `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay` |
| `CIC-Schemas` | `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Schemas` |
| `CIC-basic-knowledge` | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/source/CentralInfraCore/CIC-basic-knowledge` |
| MCP KB adat | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/kb_data/pkl` |
| MCP szerver | `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/mcp-server/server.py` |

---

## MCP szerver

A `.claude/settings.local.json` automatikusan aktiválja a `cic-graph` MCP szervert. Az MCP szerver stdio módban fut — nincs HTTP port, a konfiguráció a szülő `CIC/.mcp.json`-ben él.

---

## Workspace csomag

Ha a repókat ide kell másolni (pl. archív módú munkához):

```bash
cd /home/sinkog/sync/claude_factory/CIC/CIC-Relay
./pack-workspace.sh          # kimenet: ../CIC-Relay-workspace.tar.gz
```

---

## Felülvizsgált AI párbeszédek (theads / teads)

| Fájl | Tartalom |
|---|---|
| `CIC-Relay/theads/thead01` | OTel vs. ProofTrace — elfogadott: külön rétegek, OTel nem helyettesítő |
| `CIC-Relay/theads/thead02` | IaC szerkezet — elvetett: nested containment; elfogadott: file-referencia alapú gráf |
| `CIC/teads/relay-trust-todo.md` | Háromrétegű relay trust modell (L0–L7) — scaffold/concept állapottérkép |

Ezek döntési alapok — ne tervezd újra a `rejected` részeket.
