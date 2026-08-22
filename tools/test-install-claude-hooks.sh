#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Running an installer twice is a normal thing to do -- after adding an agent,
# after a config change, or because it is not obvious whether it already ran.
# This one grew the hook list every time: 13 entries, then 17.
#
# "Run it N times and compare" is cheap enough that the defect should never have
# survived, so the suite is mostly that.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}

# The installer resolves the agent dir under $HOME, so each case gets its own.
setup() {
    local root="$1"
    mkdir -p "$root/home/.claude-personal/agents/agent-01"
    echo "$root"
}
install() { ( HOME="$1/home" bash "$SRC/install-claude-hooks.sh" agent-01 ) >"$1/out.log" 2>&1; echo $?; }
settings() { echo "$1/home/.claude-personal/agents/agent-01/settings.json"; }
entries()  { python3 -c "
import json,sys
h=json.load(open(sys.argv[1])).get('hooks',{})
print(sum(len(v) for v in h.values()))" "$(settings "$1")"; }

echo "1. Kétszeri futtatás után ugyanaz a fájl"
T=$(mktemp -d); setup "$T" >/dev/null
check "első futás sikeres" "0" "$(install "$T")"
FIRST=$(entries "$T"); cp "$(settings "$T")" "$T/after-first.json"
check "második futás sikeres" "0" "$(install "$T")"
check "  a bejegyzésszám nem nő" "$FIRST" "$(entries "$T")"
if cmp -s "$T/after-first.json" "$(settings "$T")"; then
    echo "  PASS  a settings.json bájtra azonos"; ((pass++))
else
    echo "  FAIL  a settings.json megváltozott a második futáson"; ((fail++)); fi

echo "  (első futás: $FIRST bejegyzés)"

echo
echo "2. Ötszöri futtatás sem sodródik"
for _ in 1 2 3; do install "$T" >/dev/null; done
check "öt futás után is ugyanannyi" "$FIRST" "$(entries "$T")"
rm -rf "$T"

echo
echo "3. A markert nem hordozó bejegyzések is cserélődnek"
# Ez volt a hiba lényege: a tools/hooks/* script-hívásokban nincs "[CIC]", így a
# régi predikátum nem ismerte fel őket, és minden futáson újra hozzáfűződtek.
T=$(mktemp -d); setup "$T" >/dev/null
install "$T" >/dev/null
UNMARKED=$(python3 -c "
import json,sys
h=json.load(open(sys.argv[1]))['hooks']
n=0
for entries in h.values():
    for e in entries:
        cmds=[k.get('command','') for k in e.get('hooks',[])]
        if cmds and not any('[CIC]' in c for c in cmds): n+=1
print(n)" "$(settings "$T")")
check "van marker nélküli bejegyzés (különben a teszt semmit nem bizonyít)" "4" "$UNMARKED"
install "$T" >/dev/null
check "  második futás után is csak ennyi" "4" "$(python3 -c "
import json,sys
h=json.load(open(sys.argv[1]))['hooks']
n=0
for entries in h.values():
    for e in entries:
        cmds=[k.get('command','') for k in e.get('hooks',[])]
        if cmds and not any('[CIC]' in c for c in cmds): n+=1
print(n)" "$(settings "$T")")"
rm -rf "$T"

echo
echo "4. Idegen hookot nem bánt"
T=$(mktemp -d); setup "$T" >/dev/null
cat > "$(settings "$T")" <<'EOF'
{
  "model": "opus",
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo not-ours"}]}
    ]
  }
}
EOF
install "$T" >/dev/null
check "az idegen hook megmarad" "1" "$(python3 -c "
import json,sys
h=json.load(open(sys.argv[1]))['hooks']['PreToolUse']
print(sum(1 for e in h for k in e.get('hooks',[]) if k.get('command')=='echo not-ours'))" "$(settings "$T")")"
check "a nem-hook beállítás megmarad" "opus" "$(python3 -c "
import json,sys; print(json.load(open(sys.argv[1])).get('model',''))" "$(settings "$T")")"
install "$T" >/dev/null
check "  második futás után is egy példány" "1" "$(python3 -c "
import json,sys
h=json.load(open(sys.argv[1]))['hooks']['PreToolUse']
print(sum(1 for e in h for k in e.get('hooks',[]) if k.get('command')=='echo not-ours'))" "$(settings "$T")")"
rm -rf "$T"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
