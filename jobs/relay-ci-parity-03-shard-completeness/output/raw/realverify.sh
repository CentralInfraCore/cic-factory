#!/usr/bin/env bash
# PR-03: the plan and the 8 real shard outcomes of CIC_Relay 7ac6e80 (cargo-mutants 27.1.0) against scripts/quality_gate.py.
# usage: realverify.sh <real-output-dir> <work-dir>      (run from the CIC_Relay checkout)
O=$1; W=$2; rm -rf "$W"; mkdir -p "$W/reports"
echo "### plan record from the real 'cargo mutants --list --json' output of the full tree"
python3 scripts/quality_gate.py plan-rust --out "$W/rust-plan.json" --tool-version 27.1.0 -- cat "$O/list.json"
digest=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['digest'])" "$W/rust-plan.json")
echo "### bind the 8 real shard outcomes to the plan"
for k in 0 1 2 3 4 5 6 7; do
  python3 scripts/quality_gate.py wrap-shard --plan-digest "$digest" --shard $k --shards 8 \
    --outcomes "$O/shards/$k/mutants.out/outcomes.json" --out "$W/reports/shard-$k.json"
done
v() { python3 scripts/quality_gate.py verify --rust-plan "$W/rust-plan.json" --rust-reports "$W/reports" --rust-shards 8; echo "exit=$?"; }
echo; echo "### 1. complete run"; v
echo; echo "### 2. a shard report is missing (shard 3 never ran)"
mv "$W/reports/shard-3.json" "$W/s3.bak"; v; mv "$W/s3.bak" "$W/reports/shard-3.json"
echo; echo "### 3. a shard is reported twice"
cp "$W/reports/shard-2.json" "$W/reports/shard-2-again.json"; v; rm "$W/reports/shard-2-again.json"
echo; echo "### 4. a planned mutant has no verdict (one outcome dropped from shard 5, counters kept consistent)"
python3 - "$W/reports/shard-5.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); o=d["outcomes"]
i=next(i for i,r in enumerate(o["outcomes"]) if r["scenario"]!="Baseline")
row=o["outcomes"].pop(i); v={"CaughtMutant":"caught","Unviable":"unviable"}[row["summary"]]
o[v]-=1; o["total_mutants"]-=1; json.dump(d,open(p,"w"))
PY
v; python3 scripts/quality_gate.py wrap-shard --plan-digest "$digest" --shard 5 --shards 8 --outcomes "$O/shards/5/mutants.out/outcomes.json" --out "$W/reports/shard-5.json"
echo; echo "### 5. a verdict is tampered with (one mutant name changed by a character in shard 1)"
python3 - "$W/reports/shard-1.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
r=next(r for r in d["outcomes"]["outcomes"] if r["scenario"]!="Baseline"); r["scenario"]["Mutant"]["name"]+="x"; json.dump(d,open(p,"w"))
PY
v; python3 scripts/quality_gate.py wrap-shard --plan-digest "$digest" --shard 1 --shards 8 --outcomes "$O/shards/1/mutants.out/outcomes.json" --out "$W/reports/shard-1.json"
echo; echo "### 6. the plan is tampered with (one mutant removed from the plan file, digest kept)"
python3 - "$W/rust-plan.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["ids"].pop(); d["count"]-=1; json.dump(d,open(p,"w"))
PY
v
echo; echo "### 7. the plan file is missing"
mv "$W/rust-plan.json" "$W/plan.bak"; v; mv "$W/plan.bak" "$W/rust-plan.json"
