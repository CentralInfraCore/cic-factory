#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# A workspace törlése előtti őr a run-job.sh-ban.
#
# Egy friss futás `rm -rf`-fel törli a workspace-t. Ott élhet egy interaktív
# szál (pl. `work`), és a klónokban lehet nem commitolt vagy pusholatlan munka.
# Az őr előtt ez szó nélkül elveszett. A mérés a valódi belépési ponton megy
# (run-job.sh, echo runner), és minden elutasításnál canary fájllal bizonyítja,
# hogy a törlés TÉNYLEG nem történt meg -- nem csak a kilépési kódot nézi.
#
# --force a job-átvétel kapuja, nem a törlésé: külön mérve, hogy nem írja felül.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SRC/.." && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}

mkfactory() {
    local r; r=$(mktemp -d)
    mkdir -p "$r/repo/tools/runners" "$r/repo/jobs/.schema" "$r/repo/jobs/t/output" \
             "$r/home/.claude-personal/agents/agent-01"
    # env.sh KIVÉVE: az a gép saját konfigja, gitignored, és a run-job.sh
    # sourceolja. Bemásolva a fixture nem hermetikus -- a futtató gépének
    # FACTORY_PROMPT_VARS és CIC_* értékei felülírnák azt, amit a teszt állít
    # be. A magban ez nem látszik (ott csak env.sh.example van); egy átvevő
    # repóban viszont minden ilyen eset elbukik.
    for f in "$SRC"/*.sh; do
        [[ "$(basename "$f")" == "env.sh" ]] && continue
        cp "$f" "$r/repo/tools/" 2>/dev/null
    done
    cp "$SRC"/runners/*.sh "$r/repo/tools/runners/"
    cp "$ROOT"/jobs/.schema/*.json "$ROOT"/jobs/.schema/meta.yaml "$r/repo/jobs/.schema/"
    python3 - "$r" <<'PY'
import sys, yaml
root = sys.argv[1]
d = yaml.safe_load(open(f"{root}/repo/jobs/.schema/meta.yaml", encoding="utf-8"))
d["job_id"] = "t"; d["level"] = "repo"; d["status"] = "pending"
d["agent"]["model"] = "echo-model"
d["agent"]["config_dir"] = f"{root}/home/.claude-personal/agents/agent-01"
d["workplace"]["branch"] = "feature/t"
class Q(str): pass
yaml.add_representer(Q, lambda dd, x: dd.represent_scalar("tag:yaml.org,2002:str", str(x), style='"'))
def quote(o):
    if isinstance(o, dict):  return {k: quote(v) for k, v in o.items()}
    if isinstance(o, list):  return [quote(v) for v in o]
    if isinstance(o, str):   return Q(o)
    return o
yaml.dump(quote(d), open(f"{root}/repo/jobs/t/meta.yaml", "w", encoding="utf-8"),
          sort_keys=False, allow_unicode=True)
PY
    git init -q --bare --initial-branch=main "$r/remote.git"
    git -C "$r/repo" init -q
    git -C "$r/repo" config user.email t@t
    git -C "$r/repo" config user.name t
    git -C "$r/repo" config commit.gpgsign false
    git -C "$r/repo" remote add origin "$r/remote.git"
    git -C "$r/repo" add -A
    git -C "$r/repo" commit -q -m init --no-verify
    git -C "$r/repo" branch -M main
    git -C "$r/repo" push -q -u origin main
    echo "$r"
}
commit_spec() { git -C "$1/repo" add -A >/dev/null 2>&1; git -C "$1/repo" commit -qm spec --no-verify >/dev/null 2>&1; }
# `env` és nem csupasz értékadás: a "$@"-ből kibontott NAME=VALUE a bash
# számára parancsnév, nem értékadás -- az első változatban a futás el sem
# indult, és a "nincs benne a titok" assertionök egy üres fájlon mentek át.
run_job() {
    local r="$1"; shift
    ( cd "$r/repo" && env HOME="$r/home" CIC_AGENT_RUNNER=echo "$@" \
        bash tools/run-job.sh t agent-01 --skip-spec-gate ) >"$r/run.log" 2>&1
    echo $?
}
# Az agent-output a workspace-klónban keletkezik, nem a live fában.
prompt_of() { cat "$(find "$1" -name 'agent-output*.md' 2>/dev/null | head -1)" 2>/dev/null; }
# Ami nincs, abban semmi nincs benne. Minden szivárgás-mérés előtt le kell
# mérni, hogy a prompt egyáltalán megszületett.
prompt_len() { prompt_of "$1" | wc -c; }

commit_spec() { git -C "$1/repo" add -A >/dev/null 2>&1; git -C "$1/repo" commit -qm spec --no-verify >/dev/null 2>&1; }
# `env` és nem csupasz értékadás: a "$@"-ből kibontott NAME=VALUE a bash
# számára parancsnév, nem értékadás -- az első változatban a futás el sem
# indult, és a "nincs benne a titok" assertionök egy üres fájlon mentek át.
run_job() {
    local r="$1"; shift
    ( cd "$r/repo" && env HOME="$r/home" CIC_AGENT_RUNNER=echo "$@" \
        bash tools/run-job.sh t agent-01 --skip-spec-gate ) >"$r/run.log" 2>&1
    echo $?
}
# Az agent-output a workspace-klónban keletkezik, nem a live fában.
prompt_of() { cat "$(find "$1" -name 'agent-output*.md' 2>/dev/null | head -1)" 2>/dev/null; }
# Ami nincs, abban semmi nincs benne. Minden szivárgás-mérés előtt le kell
# mérni, hogy a prompt egyáltalán megszületett.
prompt_len() { prompt_of "$1" | wc -c; }


# Első futás: létrehozza a workspace-t. A második futásnál a státusz-őr
# (awaiting_review) miatt kell a --force; ez nem a törlés őre.
first_run() { run_job "$1" >/dev/null; }
second_run() {   # <fix> [extra run-job args...]
    local r="$1"; shift
    ( cd "$r/repo" && env HOME="$r/home" CIC_AGENT_RUNNER=echo \
        bash tools/run-job.sh t agent-01 --skip-spec-gate --force "$@" ) >"$r/run2.log" 2>&1
    echo $?
}
fresh() {
    local r; r=$(mkfactory)
    printf '# T\n## Output\n`output/report.md`\n' > "$r/repo/jobs/t/input.md"
    commit_spec "$r"
    first_run "$r"
    # Az agent a promptja szerint commitol és pushol a feature ágra; az echo
    # runner nem, ezért itt utánozzuk. Enélkül az output a klónban nem
    # commitolt marad -- amit az őr HELYESEN jelez, de a "tiszta" esethez nem jó.
    local c="$r/repo/jobs/t/workspace/cic-factory"
    git -C "$c" add -A >/dev/null
    git -C "$c" -c user.email=t@t -c user.name=t -c commit.gpgsign=false commit -qm output --no-verify
    git -C "$c" push -q origin HEAD:refs/heads/feature/t >/dev/null 2>&1
    echo "$r"
}

echo "Tiszta, pusholt workspace: az őr nem gátol (nincs hamis elutasítás)"
R=$(fresh)
WS="$R/repo/jobs/t/workspace"
check "a workspace az első futás után megvan" "1" "$([ -d "$WS/cic-factory" ] && echo 1 || echo 0)"
check "tiszta workspace-nél a második futás lefut" "0" "$(second_run "$R")"
rm -rf "$R"

echo
echo "Nem commitolt munka a klónban"
R=$(fresh); WS="$R/repo/jobs/t/workspace"
echo canary > "$WS/cic-factory/CANARY-DIRTY"
check "elutasít" "1" "$(second_run "$R")"
check "  a canary túlélte" "1" "$([ -f "$WS/cic-factory/CANARY-DIRTY" ] && echo 1 || echo 0)"
check "  megnevezi a nem commitolt változást" "1" "$(grep -c 'nem commitolt változás' "$R/run2.log")"
check "  a --force a törlést NEM írja felül" "1" "$([ -f "$WS/cic-factory/CANARY-DIRTY" ] && echo 1 || echo 0)"
rm -rf "$R"

echo
echo "Pusholatlan commit a klónban"
R=$(fresh); WS="$R/repo/jobs/t/workspace"
echo canary > "$WS/cic-factory/CANARY-UNPUSHED"
git -C "$WS/cic-factory" add -A >/dev/null
git -C "$WS/cic-factory" -c user.email=t@t -c user.name=t -c commit.gpgsign=false commit -qm local --no-verify
check "elutasít" "1" "$(second_run "$R")"
check "  a canary túlélte" "1" "$([ -f "$WS/cic-factory/CANARY-UNPUSHED" ] && echo 1 || echo 0)"
check "  megnevezi a pusholatlan commitot" "1" "$(grep -c 'pusholatlan commit' "$R/run2.log")"
rm -rf "$R"

echo
echo "Élő folyamat a workspace-ban (pl. interaktív szál)"
R=$(fresh); WS="$R/repo/jobs/t/workspace"
echo canary > "$WS/cic-factory/CANARY-LIVE"
git -C "$WS/cic-factory" add -A >/dev/null; git -C "$WS/cic-factory" -c user.email=t@t -c user.name=t -c commit.gpgsign=false commit -qm c --no-verify
git -C "$WS/cic-factory" push -q origin HEAD:refs/heads/keep-live 2>/dev/null
( cd "$WS/cic-factory" && exec sleep 60 ) &
SLEEPER=$!
sleep 0.3
check "elutasít (a klón tiszta és pusholt, mégis)" "1" "$(second_run "$R")"
check "  a canary túlélte" "1" "$([ -f "$WS/cic-factory/CANARY-LIVE" ] && echo 1 || echo 0)"
check "  megnevezi az élő folyamatot" "1" "$(grep -c 'élő folyamat' "$R/run2.log")"
kill "$SLEEPER" 2>/dev/null; wait "$SLEEPER" 2>/dev/null
rm -rf "$R"

echo
echo "Nem ellenőrizhető tartalom (nem git klón)"
R=$(fresh); WS="$R/repo/jobs/t/workspace"
mkdir -p "$WS/valami" && echo canary > "$WS/valami/CANARY-PLAIN"
check "elutasít" "1" "$(second_run "$R")"
check "  a canary túlélte" "1" "$([ -f "$WS/valami/CANARY-PLAIN" ] && echo 1 || echo 0)"
rm -rf "$R"

echo
echo "--force-clean: tudatos törlés, kiírja mit veszít"
R=$(fresh); WS="$R/repo/jobs/t/workspace"
echo canary > "$WS/cic-factory/CANARY-DIRTY"
check "lefut" "0" "$(second_run "$R" --force-clean)"
check "  a canary eltűnt (új klón)" "0" "$([ -f "$WS/cic-factory/CANARY-DIRTY" ] && echo 1 || echo 0)"
check "  kiírta, mit veszít" "1" "$(grep -c 'nem commitolt változás' "$R/run2.log")"
rm -rf "$R"

echo
echo "Eredmény: $pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
