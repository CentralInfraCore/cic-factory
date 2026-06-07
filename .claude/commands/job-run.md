# Job futtatása

Egy pending job elindítása Agent tool-lal.

## Kötelező lépések sorrendben

### 0. Spec validáció — KÖTELEZŐ, agent indítás előtt

Futtasd le: `/job-validate <job-id>`

- **GO** → folytasd a következő lépéssel
- **NO-GO** → javítsd az input.md-t, futtasd újra a validátort, ne lépj tovább

Az agent indítása NO-GO esetén tilos.

### 1. pending → running (live meta.yaml)

```python
# meta.yaml frissítés
status: "running"
timestamps.started: "<ISO 8601 now>"
```

```bash
bash tools/update-index.sh
git add jobs/$JOB_ID/meta.yaml jobs/index.yaml
git commit -m "job: $JOB_ID — running"
git push
```

**Ez a commit jön ELŐBB — az agent indítása UTÁN.**

### 2. Workspace klón

```bash
WORKSPACE="jobs/$JOB_ID/workspace"
rm -rf "$WORKSPACE"
mkdir -p "$WORKSPACE"
git clone git@github.com:CentralInfraCore/cic-factory.git "$WORKSPACE/cic-factory"
git -C "$WORKSPACE/cic-factory" checkout -b feature/$JOB_ID
```

A `workspace/` gitignored — nem kerül a repóba.

### 3. Agent indítása — Agent tool-lal (NEM run-job.sh)

Az Agent tool örökli a session MCP konfigurációját (`cic-graph` elérhető).
A `run-job.sh` `claude --print`-et használ — annak nincs MCP hozzáférése.

Az agent promptban kötelező megadni:
```
cic-factory klón: `jobs/$JOB_ID/workspace/cic-factory`
Feature branch: `feature/$JOB_ID`
```

Az agent a `jobs/$JOB_ID/input.md`-t olvassa a klónból.

### 4. Várakozás

Az agent háttérben fut. Értesítés érkezik befejezéskor — ne pollozd.

## Hibák amiket el kell kerülni

- ❌ running commit UTÁN indítani az agentet (fordított sorrend)
- ❌ run-job.sh használata Agent tool helyett (nincs MCP)
- ❌ `~/.claude-personal/agents/.../workspace/` path — a workspace `jobs/$JOB_ID/workspace/`
- ❌ Az agent promptban nem adod meg a klón path-ját
