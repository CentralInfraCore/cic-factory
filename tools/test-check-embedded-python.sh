#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-embedded-python.sh mindkét szabálya, fixture-ökön amik szándékosan
# sértik. A repón futtatva ma zöld — az önmagában nem bizonyítja, hogy tud
# pirosat adni. Éppen ez a hiba, ami miatt ez a kapu létezik: a core/@v0.1.1
# gate is zöld volt, 109 assertionnel, egy törött finalizer fölött.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

# Külön git repo, hogy a `git ls-files` a fixture-t lássa és ne az igazit.
mkroot() {
    local r; r=$(mktemp -d)
    mkdir -p "$r/tools"
    cp "$SRC/check-embedded-python.sh" "$r/tools/"
    git -C "$r" init -q
    git -C "$r" config user.email t@t; git -C "$r" config user.name t
    echo "$r"
}
commit() { git -C "$1" add -A >/dev/null 2>&1; git -C "$1" commit -qm x --no-verify >/dev/null 2>&1; }
run() { bash "$1/tools/check-embedded-python.sh" >"$1/out.log" 2>&1; echo $?; }

echo "0. Tiszta fixture → GO (különben a többi eset semmit nem mond)"
R=$(mkroot)
cat > "$R/tools/ok.sh" <<'FIX'
#!/usr/bin/env bash
python3 - "$1" <<'PYEOF'
import sys
print(sys.argv[1])
PYEOF
FIX
commit "$R"
check "exit 0" "0" "$(run "$R")"
check_log "  GO-t mond" "check-embedded-python: GO" "$R/out.log"
rm -rf "$R"

echo
echo "E1 — a core/@v0.1.1 hibája visszahelyezve"
# Szó szerint a v0.1.1 alakja: a lease_expires három sora négy szóközzel
# beljebb, egy nem behúzott utasítás után.
R=$(mkroot)
cat > "$R/tools/run-job.sh" <<'FIX'
#!/usr/bin/env bash
python3 - "$META" "$NEW_STATUS" <<'PYEOF'
import sys, re
meta_path, status = sys.argv[1], sys.argv[2]
with open(meta_path) as f:
    content = f.read()

content = re.sub(r'^status:.*$', f'status: "{status}"', content, flags=re.MULTILINE)
    # The run is over, so the lease is meaningless.
    content = re.sub(r'^lease_expires:.*$', 'lease_expires: ""', content, flags=re.MULTILINE)
with open(meta_path, "w") as f:
    f.write(content)
PYEOF
FIX
commit "$R"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a fájlt és a heredoc kezdetét" "tools/run-job.sh:2" "$R/out.log"
check_log "  megnevezi a hibát" "IndentationError" "$R/out.log"
# A heredocon belüli sorszám nem az, amit a szerkesztő mutat. A kapunak a
# fájl valódi sorára kell mutatnia -- itt a 10-esre, a behúzott re.sub-ra.
check_log "  a fájl valódi sorára mutat" "tools/run-job.sh:10" "$R/out.log"
check_log "  NO-GO-t mond" "check-embedded-python: NO-GO" "$R/out.log"
rm -rf "$R"

echo
echo "E1 — a hiba a backslash-szel tört parancs mögött is látszik"
# A run-job.sh :570 blokkja három soron át sorolja az argumentumokat, a
# heredoc csak a harmadik sor végén nyílik. Egy soronkénti kereső átlépné.
R=$(mkroot)
cat > "$R/tools/multi.sh" <<'FIX'
#!/usr/bin/env bash
python3 - "$A" "$B" \
         "$C" "$D" \
         "$E" <<'PYEOF'
import sys
def f():
return 1
PYEOF
FIX
commit "$R"
check "exit 1" "1" "$(run "$R")"
check_log "  a heredoc kezdetét jelenti, nem a parancsét" "tools/multi.sh:4" "$R/out.log"
rm -rf "$R"

echo
echo "E2 — python3-nak adott heredoc nem-PY határolóval"
# E1 önmagában ezt nem látná: pontosan ez a vakfolt, amit E2 zár.
R=$(mkroot)
cat > "$R/tools/hidden.sh" <<'FIX'
#!/usr/bin/env bash
python3 - <<'EOF'
import sys
def f():
return 1
EOF
FIX
commit "$R"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a határolót" "<<EOF" "$R/out.log"
check_log "  megmondja miért baj" "E1 nem látja" "$R/out.log"
rm -rf "$R"

echo
echo "Nem-Python heredoc nem esik a szabály alá"
R=$(mkroot)
cat > "$R/tools/shell.sh" <<'FIX'
#!/usr/bin/env bash
cat <<'EOF'
this is not python
def f():
return 1
EOF
FIX
commit "$R"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "A még nem addolt script is ellenőrzés alá esik"
# check-docs.sh ugyanebbe a csapdába sétált bele: a kapu az új fájlon
# hallgatott, és csak `git add` után szólalt meg.
R=$(mkroot)
commit "$R"
cat > "$R/tools/uncommitted.sh" <<'FIX'
#!/usr/bin/env bash
python3 - <<'PYEOF'
def f():
return 1
PYEOF
FIX
check "exit 1" "1" "$(run "$R")"
rm -rf "$R"

echo
echo "A <<- alak tabjait levágja fordítás előtt"
R=$(mkroot)
printf '#!/usr/bin/env bash\npython3 - <<-'"'"'PYEOF'"'"'\n\timport sys\n\tprint(1)\n\tPYEOF\n' > "$R/tools/dash.sh"
commit "$R"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
