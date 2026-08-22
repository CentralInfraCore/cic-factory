#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Egy fixture szabályonként, mindegyik sérti azt az egyet. A sémát a valós
# adatokon futtatni nem elég: 48 érvényes meta ugyanúgy néz ki egy működő és egy
# mindent elfogadó validátor mellett.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SRC/.." && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

mkroot() {
    local r; r=$(mktemp -d)
    mkdir -p "$r/tools" "$r/jobs/.schema" "$r/jobs/t"
    cp "$SRC/validate-meta.sh" "$r/tools/"
    cp "$ROOT/jobs/.schema/meta.schema.json" "$ROOT/jobs/.schema/meta.yaml" "$r/jobs/.schema/"
    echo "$r"
}

# Érvényes meta a sablonból, kitöltött kötelező mezőkkel.
mkmeta() {
    python3 - "$1" <<'PY'
import sys, yaml
root = sys.argv[1]
d = yaml.safe_load(open(f"{root}/jobs/.schema/meta.yaml", encoding="utf-8"))
d["job_id"] = "t"; d["level"] = "repo"; d["status"] = "pending"
d["agent"]["model"] = "claude-sonnet-5"
d["workplace"]["branch"] = "feature/t"
yaml.safe_dump(d, open(f"{root}/jobs/t/meta.yaml", "w", encoding="utf-8"), sort_keys=False)
PY
}
edit() { python3 - "$1" "$2" <<'PY'
import sys, yaml
root, expr = sys.argv[1], sys.argv[2]
p = f"{root}/jobs/t/meta.yaml"
d = yaml.safe_load(open(p, encoding="utf-8"))
exec(expr, {"d": d})
yaml.safe_dump(d, open(p, "w", encoding="utf-8"), sort_keys=False)
PY
}
run() { bash "$1/tools/validate-meta.sh" "${@:2}" >"$1/out.log" 2>&1; echo $?; }

echo "0. Érvényes meta átmegy (különben a többi eset semmit nem mond)"
R=$(mkroot); mkmeta "$R"
check "exit 0" "0" "$(run "$R" t)"
rm -rf "$R"

echo
echo "1. Elgépelt mezőnév — ez volt a template legnagyobb vakfoltja"
R=$(mkroot); mkmeta "$R"; sed -i 's/^status:/statsu:/' "$R/jobs/t/meta.yaml"
check "exit 1" "1" "$(run "$R" t)"
check_log "  megnevezi az ismeretlen mezőt" "'statsu' was unexpected" "$R/out.log"
rm -rf "$R"

echo
echo "2. Érvénytelen status — az enum eddig kommentben élt"
R=$(mkroot); mkmeta "$R"; edit "$R" "d['status']='finished'"
check "exit 1" "1" "$(run "$R" t)"
check_log "  enum-hibát mond" "is not one of" "$R/out.log"
rm -rf "$R"

echo
echo "3. Üres agent.model — a job csendben a default modellen futna"
R=$(mkroot); mkmeta "$R"; edit "$R" "d['agent']['model']=''"
check "exit 1" "1" "$(run "$R" t)"
check_log "  a mezőt nevezi meg" "agent.model" "$R/out.log"
rm -rf "$R"

echo
echo "4. Hiányzó kötelező blokk"
R=$(mkroot); mkmeta "$R"; edit "$R" "d.pop('workplace')"
check "exit 1" "1" "$(run "$R" t)"
check_log "  megmondja mi hiányzik" "'workplace' is a required property" "$R/out.log"
rm -rf "$R"

echo
echo "5. job_id, ami nem lehet könyvtárnév"
R=$(mkroot); mkmeta "$R"; edit "$R" "d['job_id']='../escape'"
check "exit 1" "1" "$(run "$R" t)"
rm -rf "$R"

echo
echo "6. Érvénytelen spec_gate"
R=$(mkroot); mkmeta "$R"; edit "$R" "d['spec_gate']='maybe'"
check "exit 1" "1" "$(run "$R" t)"
rm -rf "$R"

echo
echo "7. A deprecated promptmap_ref tolerálva — 51 régi meta hordozza"
R=$(mkroot); mkmeta "$R"; edit "$R" "d.update(promptmap_ref='')"
check "exit 0" "0" "$(run "$R" t)"
rm -rf "$R"

echo
echo "8. A sablon és a séma kulcsai együtt mozognak"
R=$(mkroot)
check "egyező sablon → OK" "0" "$(run "$R" --template)"
# Mező a sémába, a sablonba nem: pontosan a drift, ami háromszor megtörtént.
python3 - "$R" <<'PY'
import json, sys
p = f"{sys.argv[1]}/jobs/.schema/meta.schema.json"
s = json.load(open(p)); s["properties"]["uj_mezo"] = {"type": "string"}
json.dump(s, open(p, "w"), indent=2)
PY
check "  séma előrement → elutasít" "1" "$(run "$R" --template)"
check_log "    megnevezi" "a sémában van, a sablonból hiányzik: uj_mezo" "$R/out.log"
rm -rf "$R"

echo
echo "9. Maga a séma is ellenőrzött"
# Egy elrontott séma mindent elfogadna: a leghalkabb hiba, ami itt lehet.
R=$(mkroot); mkmeta "$R"
python3 -c "
import json,sys
p=f'$R/jobs/.schema/meta.schema.json'
s=json.load(open(p)); s['properties']['status']['enum']='nem-lista'
json.dump(s,open(p,'w'))"
check "hibás séma → elutasít" "1" "$(run "$R" t)"
check_log "  a sémát hibáztatja" "maga a séma érvénytelen" "$R/out.log"
rm -rf "$R"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
