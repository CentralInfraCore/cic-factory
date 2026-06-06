# Job létrehozása

Új job spec létrehozása a live workdir-ban.

## Kötelező lépések sorrendben

### 1. Könyvtárstruktúra

```bash
JOB_ID="<job-id>"
mkdir -p jobs/$JOB_ID/output
mkdir -p jobs/$JOB_ID/ref   # ha kell referencia anyag
touch jobs/$JOB_ID/output/.gitkeep
```

### 2. meta.yaml

A `.schema/meta.yaml` alapján. Kötelező mezők:
- `job_id` — egyedi, kebab-case
- `parent_job_id` — "" ha gyökér
- `level` — orchestrator | repo | domain
- `target.repo` — melyik repóra vonatkozik
- `kb_focus` — releváns cic-graph node ID-k (ha ismert)
- `workplace.repos` — mit kell klónozni (mindig: "cic-factory" + egyéb)
- `workplace.branch` — "feature/<job-id>"
- `status` — "pending"
- `timestamps.created` — ISO 8601

### 3. input.md

**Nyelv: magyar.**

Az `input.md` felépítése:
1. Kontextus — mi a feladat és miért
2. Boot sequence — mit kell a KB-ban feltérképezni (konkrét `search_query` és `search_nodes` hívások)
3. Feladat — mit kell elkészíteni
4. Output — fájlok listája és helye
5. Git instrukciók — push csak feature branch-re
6. Nyelvi szabály

**Alapszabály az input.md írásához:**
> Ne te kutasd fel a KB-t előre. Írj olyan instrukciókat, amelyek alapján az agent maga tárja fel amit szükséges.
> Ha nem tudod mi lesz a KB-ban — ez normális. Az agent feladata megtalálni.

### 4. Commit és push

```bash
bash tools/update-index.sh
git add jobs/$JOB_ID/ jobs/index.yaml
git commit -m "job: $JOB_ID — pending"
git push
```

## Ellenőrzőlista

- [ ] `meta.yaml` — minden kötelező mező kitöltve, status: pending
- [ ] `input.md` — magyarul, tartalmaz KB feltérképezési utasításokat
- [ ] `output/.gitkeep` — létezik
- [ ] `jobs/index.yaml` — frissítve
- [ ] Commitolva és pusholt main-re
