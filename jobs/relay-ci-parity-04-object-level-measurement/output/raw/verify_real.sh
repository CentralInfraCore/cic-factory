#!/usr/bin/env bash
# PR-04: the offline verifier on the real record, and on the same data after deliberate tampering (N13).
git config --global --add safe.directory /w
cd /s/scripts
inp=""
for n in go-inventory:root:/out/go-inventory-prod.json go-coverprofile:root:/out/go-cover.out go-inventory:goastdump:/out/goastdump-inventory.json \
         go-coverprofile:goastdump:/out/goastdump-cover.out llvm-cov-json::/out/llvm-cov.json rust-mutant-list::/p03/list.json scope::/s/.measurement-scope.json; do
  IFS=: read -r a b c <<<"$n"; name="$a${b:+:$b}"; inp="$inp --input $name=$c"
done
for k in 0 1 2 3 4 5 6 7; do inp="$inp --input rust-outcomes:$k=/p03/shards/$k/mutants.out/outcomes.json"; done
V="python3 object_model.py verify --record"
S="--root /w --scope /s/.measurement-scope.json --rust-list /p03/list.json"
echo "### 1. the real record, with the checkout and every input (L1/L2/L3)"; $V /out/evidence.json $S $inp; echo "exit=$?"
echo; echo "### 2. the same record, no checkout and no inputs: L2 must be NOT_CHECKED, L3 only PARTIAL"; $V /out/evidence.json; echo "exit=$?"
echo; echo "### 3. an object removed, the digest and the summary recomputed consistently (an attacker who fixes the record)"
python3 - <<'PY'
import json,sys; sys.path.insert(0,"/s/scripts"); import object_model as om
r=json.load(open("/out/evidence.json")); r["objects"].pop(5); r["summary"]=om.summarize(r["objects"])
r["digest"]=om.canonical_digest({k:v for k,v in r.items() if k!="digest"}); json.dump(r,open("/tmp/forged.json","w"))
PY
$V /tmp/forged.json $S $inp; echo "exit=$?"
echo; echo "### 4. an input file changed after the measurement (the coverage profile)"
cp /out/go-cover.out /tmp/go-cover.changed; echo "example.com/x/a.go:1.1,2.2 1 1" >> /tmp/go-cover.changed
inp2=$(echo "$inp" | sed 's#go-coverprofile:root=/out/go-cover.out#go-coverprofile:root=/tmp/go-cover.changed#')
$V /out/evidence.json $S $inp2; echo "exit=$?"
echo; echo "### 5. a record whose coverage kind says 'branch'"
python3 - <<'PY'
import json,sys; sys.path.insert(0,"/s/scripts"); import object_model as om
r=json.load(open("/out/evidence.json")); o=next(o for o in r["objects"] if o["coverage"]["state"]=="MEASURED"); o["coverage"]["kind"]="branch"
r["summary"]=om.summarize(r["objects"]); r["digest"]=om.canonical_digest({k:v for k,v in r.items() if k!="digest"}); json.dump(r,open("/tmp/branch.json","w"))
PY
$V /tmp/branch.json; echo "exit=$?"
