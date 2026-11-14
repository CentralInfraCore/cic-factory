#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# work-open.sh: egy factory job interaktív végrehajtása a `work` alatt.
#
# A `work` helyett egy csonk fut (WORK_BIN), ami rögzíti a hívását; a direnv
# VALÓDI, hogy a profil-átadás (.envrc) a tényleges mechanizmuson mérődjön.
# A direnv allow-adatbázisa a teszt saját XDG_DATA_HOME-jába kerül, a gép
# sajátját nem érinti.

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

mkstub() {   # <fix>: a work csonkja
    cat > "$1/work" <<'STUB'
#!/usr/bin/env bash
if [[ "${1:-}" == info ]]; then
    [[ "${STUB_INFO_RC:-1}" -ne 0 ]] && exit "${STUB_INFO_RC:-1}"
    printf '{\n  "cwd": "%s",\n  "title": "%s"\n}\nstate dir: /x\n' "${STUB_INFO_CWD:-}" "${STUB_INFO_TITLE:-}"
    exit 0
fi
printf '%s\n' "$@" > "$STUB_LOG"
[[ -n "${STUB_RC:-}" ]] && exit "$STUB_RC"
exit 0
STUB
    chmod +x "$1/work"
}
wopen() {    # <fix> [extra args...] -- a work-open.sh a fixture-repóban, csonkkal
    local r="$1"; shift
    ( cd "$r/repo" && env HOME="$r/home" XDG_DATA_HOME="$r/xdg" WORK_BIN="$r/work" \
        STUB_LOG="$r/stub.log" CLAUDE_CONFIG_DIR=/some/other/profile \
        bash tools/work-open.sh t agent-01 "$@" ) >"$r/out.log" 2>&1
    echo $?
}
fixture() {
    local r; r=$(mkfactory); mkstub "$r"; mkdir -p "$r/xdg"
    printf '# T\n## Output\n`output/report.md`\n' > "$r/repo/jobs/t/input.md"
    commit_spec "$r"; echo "$r"
}

echo "Friss indítás"
R=$(fixture); WS="$R/repo/jobs/t/workspace"; CFG="$R/home/.claude-personal/agents/agent-01"
META_BEFORE=$(sha256sum "$R/repo/jobs/t/meta.yaml" | cut -d' ' -f1)
check "lefut" "0" "$(wopen "$R" --skip-spec-gate)"
check "  a cic-factory klón megvan"          "1" "$([ -d "$WS/cic-factory/.git" ] && echo 1 || echo 0)"
check "  a feature ágon áll"                 "feature/t" "$(git -C "$WS/cic-factory" branch --show-current)"
check "  a work ticketje task-t"             "1" "$(sed -n 2p "$R/stub.log" | grep -cx 'task-t')"
check "  a work --dir a workspace"           "1" "$(grep -cx -- "$WS" "$R/stub.log")"
check "  a prompt-fájl átadva"               "1" "$(grep -cx -- '--prompt-file' "$R/stub.log")"
check "  a meta.yaml érintetlen"             "$META_BEFORE" "$(sha256sum "$R/repo/jobs/t/meta.yaml" | cut -d' ' -f1)"
# A profil: a hívó környezetében MÁS profil van; az .envrc-nek a jobét kell adnia.
check "  .envrc a job profilját adja, nem a hívóét" "$CFG" \
      "$(cd "$WS" && XDG_DATA_HOME="$R/xdg" CLAUDE_CONFIG_DIR=/some/other/profile direnv exec "$WS" printenv CLAUDE_CONFIG_DIR)"
rm -rf "$R"

echo
echo "A prompt tartalma"
R=$(fixture); WS="$R/repo/jobs/t/workspace"
# a csonk a prompt-fájl ELÉRÉSI ÚTJÁT kapja, a fájl a kilépéskor törlődik: a
# prompt-fájl tartalmát a csonk másolja le
cat > "$R/work" <<'STUB'
#!/usr/bin/env bash
[[ "${1:-}" == info ]] && exit 1
while (( $# )); do [[ "$1" == --prompt-file ]] && cp "$2" "$STUB_LOG.prompt"; shift; done
STUB
chmod +x "$R/work"
wopen "$R" --skip-spec-gate >/dev/null
P="$R/stub.log.prompt"
check "  megnevezi az input.md-t a klónban"  "1" "$(grep -c "$WS/cic-factory/jobs/t/input.md" "$P")"
check "  megnevezi a feature ágat"           "1" "$([ "$(grep -c 'feature/t' "$P")" -ge 1 ] && echo 1 || echo 0)"
check "  kimondja, hogy nem run-job futás"   "1" "$(grep -c 'nem run-job.sh futásban' "$P")"
rm -rf "$R"

echo
echo "Spec-kapu"
R=$(mkfactory); mkstub "$R"; mkdir -p "$R/xdg"
printf 'semmi\n' > "$R/repo/jobs/t/input.md"; commit_spec "$R"
check "NO-GO spec: elutasít"                 "1" "$(wopen "$R")"
check "  a spec-kapu miatt, nem másért"      "1" "$([ "$(grep -c 'NO-GO' "$R/out.log")" -ge 1 ] && echo 1 || echo 0)"
check "  nem hozott létre workspace-t"       "0" "$([ -e "$R/repo/jobs/t/workspace" ] && echo 1 || echo 0)"
check "  a work-öt nem hívta"                "0" "$([ -e "$R/stub.log" ] && echo 1 || echo 0)"
rm -rf "$R"

echo
echo "Hiányzó direnv: kimondja, és nem hoz létre semmit"
# A CI-futtató nem hozza a direnv-et; az adapter ilyenkor hangosan áll meg.
R=$(fixture)
RC=$( ( cd "$R/repo" && env HOME="$R/home" XDG_DATA_HOME="$R/xdg" WORK_BIN="$R/work" DIRENV_BIN=/nincs/direnv \
    STUB_LOG="$R/stub.log" bash tools/work-open.sh t agent-01 --skip-spec-gate ) >"$R/out.log" 2>&1; echo $? )
check "elutasít"                             "1" "$RC"
check "  megnevezi a direnv-et"              "1" "$(grep -c 'direnv' "$R/out.log")"
check "  nem hozott létre workspace-t"       "0" "$([ -e "$R/repo/jobs/t/workspace" ] && echo 1 || echo 0)"
rm -rf "$R"

echo
echo "Meglévő workspace, nincs hozzá szál: nem nyúl hozzá"
R=$(fixture); WS="$R/repo/jobs/t/workspace"
mkdir -p "$WS/cic-factory"; echo canary > "$WS/cic-factory/CANARY"
check "elutasít"                             "1" "$(wopen "$R" --skip-spec-gate)"
check "  a canary túlélte"                   "1" "$([ -f "$WS/cic-factory/CANARY" ] && echo 1 || echo 0)"
check "  a work-öt nem hívta"                "0" "$([ -e "$R/stub.log" ] && echo 1 || echo 0)"
check "  megmondja, mi van benne"            "1" "$(grep -c 'nem git klón\|Üres vagy tiszta' "$R/out.log")"
rm -rf "$R"

echo
echo "Meglévő workspace, él hozzá szál: csak akkor él újra, ha job ÉS workspace egyezik"
revive() {   # <fix> <cwd> <title>
    local r="$1"
    ( cd "$r/repo" && env HOME="$r/home" XDG_DATA_HOME="$r/xdg" WORK_BIN="$r/work" STUB_LOG="$r/stub.log" \
        STUB_INFO_RC=0 STUB_INFO_CWD="$2" STUB_INFO_TITLE="$3" bash tools/work-open.sh t agent-01 ) >"$r/out.log" 2>&1
    echo $?
}
R=$(fixture); WS="$R/repo/jobs/t/workspace"; mkdir -p "$WS"
check "egyező cwd + title: újraéleszt"       "0" "$(revive "$R" "$WS" 'factory job: t')"
check "  open task-t, --dir NÉLKÜL"          "0" "$(grep -cx -- '--dir' "$R/stub.log")"
rm -rf "$R"
R=$(fixture); WS="$R/repo/jobs/t/workspace"; mkdir -p "$WS" "$R/other-ws"
check "ugyanaz a ticket, MÁSIK workspace: elutasít" "1" "$(revive "$R" "$R/other-ws" 'factory job: t')"
check "  a work open-t nem hívta"            "0" "$([ -e "$R/stub.log" ] && echo 1 || echo 0)"
check "  megnevezi az eltérést"              "1" "$(grep -c 'nem ehhez a jobhoz' "$R/out.log")"
rm -rf "$R"
R=$(fixture); WS="$R/repo/jobs/t/workspace"; mkdir -p "$WS"
check "ugyanaz a ticket, MÁSIK job (title): elutasít" "1" "$(revive "$R" "$WS" 'factory job: masik')"
check "  a work open-t nem hívta"            "0" "$([ -e "$R/stub.log" ] && echo 1 || echo 0)"
rm -rf "$R"
R=$(fixture); WS="$R/repo/jobs/t/workspace"; mkdir -p "$WS"
check "a szál cwd-je nem létezik: elutasít"  "1" "$(revive "$R" "/nincs/ilyen" 'factory job: t')"
rm -rf "$R"

echo
echo "A promptfájl életciklusa"
# a csonk a kapott --prompt-file ÚTJÁT is leírja, hogy a kilépés utáni létezése mérhető legyen
R=$(fixture)
cat > "$R/work" <<'STUB'
#!/usr/bin/env bash
[[ "${1:-}" == info ]] && exit 1
while (( $# )); do [[ "$1" == --prompt-file ]] && { echo "$2" > "$STUB_LOG.path"; [[ -s "$2" ]] && echo present > "$STUB_LOG.during"; }; shift; done
exit "${STUB_RC:-0}"
STUB
chmod +x "$R/work"
wopen "$R" --skip-spec-gate >/dev/null
PF=$(cat "$R/stub.log.path")
check "a work open alatt a fájl megvolt, tartalommal" "present" "$(cat "$R/stub.log.during" 2>/dev/null)"
check "  siker után a promptfájl törölve"    "0" "$([ -e "$PF" ] && echo 1 || echo 0)"
rm -rf "$R"
R=$(fixture)
cat > "$R/work" <<'STUB'
#!/usr/bin/env bash
[[ "${1:-}" == info ]] && exit 1
while (( $# )); do [[ "$1" == --prompt-file ]] && echo "$2" > "$STUB_LOG.path"; shift; done
exit 3
STUB
chmod +x "$R/work"
RC=$( ( cd "$R/repo" && env HOME="$R/home" XDG_DATA_HOME="$R/xdg" WORK_BIN="$R/work" STUB_LOG="$R/stub.log" \
    bash tools/work-open.sh t agent-01 --skip-spec-gate ) >"$R/out.log" 2>&1; echo $? )
PF=$(cat "$R/stub.log.path")
check "work open hibája: az exit kód átjön" "3" "$RC"
check "  hiba után is törölve a promptfájl"  "0" "$([ -e "$PF" ] && echo 1 || echo 0)"
rm -rf "$R"

echo
echo "Azonosító-határ"
R=$(fixture)
check "'../x' job-id elutasítva"             "1" "$( ( cd "$R/repo" && env HOME="$R/home" WORK_BIN="$R/work" bash tools/work-open.sh ../x ) >/dev/null 2>&1; echo $?)"
rm -rf "$R"

echo
echo "Az őr (run-job.sh) és az adapter .envrc-je"
R=$(fixture); WS="$R/repo/jobs/t/workspace"
wopen "$R" --skip-spec-gate >/dev/null
source "$SRC/lib-workspace-guard.sh"
check "tiszta workspace + az adapter .envrc-je: az őr nem lát lelet" "" "$(workspace_loss_report "$WS")"
echo 'export CLAUDE_CONFIG_DIR=/x; curl evil' > "$WS/.envrc"
check "  átírt .envrc: az őr blokkol"      "1" "$(workspace_loss_report "$WS" | grep -c '.envrc')"
printf 'export CLAUDE_CONFIG_DIR=/x\nrm -rf ~\n' > "$WS/.envrc"
check "  többsoros .envrc: az őr blokkol"   "1" "$(workspace_loss_report "$WS" | grep -c '.envrc')"
rm -rf "$R"

echo
echo "Eredmény: $pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
