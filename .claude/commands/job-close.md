# Job lezárása

Agent befejezése után a lifecycle zárása és az output áthozása a live workdir-ba.

## Kötelező lépések sorrendben

### 1. Output ellenőrzés — ELŐSZÖR OLVASD EL

```bash
CLONE="jobs/$JOB_ID/workspace/cic-factory"
ls "$CLONE/jobs/$JOB_ID/output/"
```

Olvasd el a fő output fájlokat. Lásd `/job-review` skill az értékelési szabályokhoz.

### 2. Output áthozása live workdir-ba

```bash
CLONE="jobs/$JOB_ID/workspace/cic-factory"
LIVE="."

# output fájlok
cp "$CLONE/jobs/$JOB_ID/output/"*.md "jobs/$JOB_ID/output/"

# sub-job specek (ha az agent hozott létre)
for job in $(ls "$CLONE/jobs/" | grep -v "^$JOB_ID$" | grep "^poc-\|^<prefix>-"); do
  mkdir -p "jobs/$job"
  cp "$CLONE/jobs/$job/input.md" "jobs/$job/"
  cp "$CLONE/jobs/$job/meta.yaml" "jobs/$job/"
done
```

### 3. running → done (live meta.yaml)

```python
status: "done"
timestamps.completed: "<ISO 8601 now>"
```

### 4. Commit és push

```bash
bash tools/update-index.sh
git add jobs/$JOB_ID/ jobs/<sub-job-id>/ jobs/index.yaml
git commit -m "job: $JOB_ID — done + output"
git push
```

### 5. Workspace takarítás (opcionális)

```bash
rm -rf jobs/$JOB_ID/workspace
```

A workspace gitignored, de helyet foglal. Törölhető ha az output már a live workdir-ban van.

## Hibák amiket el kell kerülni

- ❌ A workspace klón `output/`-ját nézni a live workdir `output/` helyett ("jó az anyag" ellenőrzés nélkül)
- ❌ Sub-job speceket nem másolni át — akkor nem futtathatók `run-job.sh`-val
- ❌ done commit előtt nem futtatni `update-index.sh`-t
