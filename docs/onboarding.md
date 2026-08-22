# cic-factory — Onboarding

Ez a dokumentum segít megérteni a cic-factory rendszert és elindulni a használatával.

---

## Mi ez a rendszer?

A **cic-factory** a CIC ökoszisztéma fejlesztési workflow automatizálója. A lényege:

- A fejlesztési feladatok **job-ként** definiálhatók (`input.md` + `meta.yaml`)
- Minden jobot egy **izolált agent workspace**-ben hajt végre egy AI agent
- Az agent a saját klónjában dolgozik, **feature branch-re commitol** — soha nem ír a live `workdir/`-ba
- Az orchestrátor (fejlesztő + AI) review-olja és mergeli a feature branch-et

A bizalom alapja a **Vault-aláírt commit** — minden commit kriptográfiailag igazolható.

---

## A két szereplő

| Szereplő | Hol él | Mit csinál |
|---|---|---|
| **Orchestrátor** | live `workdir/` | job spec létrehozás, review, merge döntés |
| **Agent** | `jobs/<job-id>/workspace/cic-factory/` (klón) | olvas, dolgozik, commitol + pushol feature branch-re |

Az agent **soha nem push-ol `main`-re** — ez kizárólag az orchestrátor joga.

---

## Job lifecycle

```
1. Orchestrátor: input.md + meta.yaml → commit + push main
2. run-job.sh:   pending → running → workspace klón → feature branch
3. Agent:        olvas jobs/<job-id>/ → ír output/ → commit + push feature/<job-id>
4. Orchestrátor: review GitHubon → merge main
```

### Job struktúra

```
jobs/
  <job-id>/
    input.md        ← agent prompt (magyarul)
    meta.yaml       ← lifecycle állapot + konfig
    output/         ← agent által létrehozott eredmény
    workspace/      ← gitignored; agent klónjai élnek itt
```

---

## Első job futtatása

### 1. Környezet beállítása

```bash
cp tools/env.sh.example tools/env.sh
# Szerkeszd meg: állítsd be a CIC repo path-okat
```

### 2. Job spec létrehozása

A `meta.yaml` a sémából induljon, ne kézzel írt másolatból — így nem maradhat le
róla mező, amit később vezettek be:

```bash
mkdir -p jobs/pelda-job
cp jobs/.schema/meta.yaml jobs/pelda-job/meta.yaml
```

Ezután töltsd ki benne:

| mező | mit |
|---|---|
| `job_id` | `"pelda-job"` |
| `level` | `orchestrator` \| `repo` \| `domain` |
| `target.repo` | melyik repót érinti |
| `agent.config_dir` | az izolált agent config könyvtára |
| `agent.model` | **kötelező** — enélkül a spec-kapu K10-en bukik |
| `workplace.branch` | `feature/pelda-job` |
| `timestamps.created` | ISO 8601 |

A `status` maradjon `pending`; onnantól a lifecycle írja. A `spec_gate`, a
`lease_expires` és a `usage` szintén gépi mezők — ne töltsd őket kézzel.

`jobs/pelda-job/input.md`: az agent promptja magyarul.

### 3. Commitolás és futtatás

```bash
./tools/update-index.sh
git add jobs/pelda-job/ jobs/index.yaml
git commit -m "job: pelda-job — pending"
git push origin main
./tools/run-job.sh pelda-job agent-01
```

A `run-job.sh` sikeres futás után `awaiting_review` állapotot hagy, nem `done`-t.
Az agent exit 0-ja azt jelenti, hogy az agent befejezte — nem azt, hogy a kimenet
elfogadható. A `done`-hoz output-kapu és review artifact kell.

### 4. Review és merge

```bash
gh pr list --repo CentralInfraCore/cic-factory
# Review a feature branch output/ mappájában
# Merge GitHubon
```

### 5. Lezárás

```bash
/job-close pelda-job     # output-kapu + review.md + awaiting_review → done
```

---

## AI-asszisztált megértés

A rendszer megértéséhez ajánlott a teljes `workdir/` könyvtárat egy AI-val (pl. Claude Code) végigolvastatni. A helyes megközelítés:

### Mit adj a AI-nak induló kontextusként

1. **`CLAUDE.md`** — a működési modell, szerepek, kötelező boot sequence
2. **`SPEC.md`** — a lifecycle, a kapuk és a job-struktúra
3. **`jobs/index.yaml`** — az összes eddigi job állapota
4. Egy konkrét kész job mappája (pl. `jobs/cic-schemas-audit/`) — lifecycle példa

### Helyes kérdések AI-nak

- *"Magyarázd el a job lifecycle-t a run-job.sh alapján"*
- *"Mi a különbség az orchestrátor és az agent szerepe között?"*
- *"Hogyan hozzak létre egy új jobot ami a CIC-Relay-t auditálja?"*

### Amit kerülj

- Ne kérdezd az AI-t a rendszer állapotáról a kód elolvasása nélkül — a scaffold ≠ implemented különbség csak a kódból derül ki
- Az agent output (`output/` mappa) nem végleges döntés — mindig review után mergelhető csak

### Boot sequence AI sessionben

Ha Claude Code-dal dolgozol ezen a rendszeren, a session elején kötelező:

```
1. kb_status ellenőrzés (cic-graph MCP)
2. search_nodes → axioms, symbols, contract, limits
3. Háromszintű státusz azonosítása: implemented | scaffold | concept
```

**Amíg ez nem teljesült, ne tegyél tényállításokat az architektúráról.**

---

## Eszközök

| Parancs | Mit csinál |
|---|---|
| `./tools/run-job.sh <job-id> [agent-id]` | Teljes lifecycle automatizálás |
| `./tools/update-index.sh` | `jobs/index.yaml` újragenerálása |
| `~/.claude-personal/agents/new-agent.sh <név>` | Új izolált agent config |

---

## Tovább olvasnivaló

- [`CLAUDE.md`](../CLAUDE.md) — orchestrátor-szintű kontextus
- [`SPEC.md`](../SPEC.md) — a factory működési modellje: lifecycle, kapuk, job-struktúra
- [`jobs/.schema/meta.yaml`](../jobs/.schema/meta.yaml) — a `meta.yaml` mezői
- [`CLAUDE.md`](../CLAUDE.md) — hogyan dolgozz ezen a repón

A CIC-specifikus kontextus — ökoszisztéma-térkép, repo path-ok, MCP szerver — a
[`cic-factory`](https://github.com/CentralInfraCore/cic-factory) repóban él, nem
itt.
