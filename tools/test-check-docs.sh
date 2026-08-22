#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# check-docs.sh mindkét szabálya, olyan fixture-ökön, amik szándékosan sértik.
# A repón futtatva ma zöld — az önmagában nem bizonyítja, hogy tud pirosat adni.

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
    mkdir -p "$r/tools" "$r/jobs/.schema"
    cp "$SRC/check-docs.sh" "$r/tools/"
    printf 'job_id: ""\nstatus: "pending"\n' > "$r/jobs/.schema/meta.yaml"
    git -C "$r" init -q
    git -C "$r" config user.email t@t; git -C "$r" config user.name t
    echo "$r"
}
commit() { git -C "$1" add -A >/dev/null 2>&1; git -C "$1" commit -qm x --no-verify >/dev/null 2>&1; }
run() { bash "$1/tools/check-docs.sh" >"$1/out.log" 2>&1; echo $?; }

echo "0. Tiszta fixture → GO (különben a többi eset semmit nem mond)"
R=$(mkroot); printf '# Doc\n\nsima szöveg\n' > "$R/a.md"; commit "$R"
check "exit 0" "0" "$(run "$R")"
check_log "  GO-t mond" "check-docs: GO" "$R/out.log"
rm -rf "$R"

echo
echo "D1 — törött relatív link"
R=$(mkroot); printf '# Doc\n\n[nincs ilyen](docs/hianyzik.md)\n' > "$R/a.md"; commit "$R"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a fájlt és a sort" "a.md:3" "$R/out.log"
rm -rf "$R"

echo
echo "D1 — a létező linket nem jelenti, a külsőt sem"
R=$(mkroot)
mkdir -p "$R/docs"; printf 'x\n' > "$R/docs/van.md"
printf '# Doc\n\n[van](docs/van.md)\n[web](https://example.com/nincs.md)\n[horgony](docs/van.md#szakasz)\n' > "$R/a.md"
commit "$R"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "D2 — dokumentum újradefiniálja a sémát"
R=$(mkroot)
printf '# Doc\n\n```yaml\njob_id: "x"\nstatus: "pending"\n```\n' > "$R/a.md"; commit "$R"
check "exit 1" "1" "$(run "$R")"
check_log "  megnevezi a fájlt" "a.md: yaml blokk újradefiniálja" "$R/out.log"
rm -rf "$R"

echo
echo "D2 — részleges idézés nem duplikáció"
# Egyetlen mező bemutatása legitim; csak az együttes job_id + status számít
# séma-újradefiniálásnak.
R=$(mkroot)
printf '# Doc\n\n```yaml\nstatus: "pending"\n```\n\nés prózában a job_id: is\n' > "$R/a.md"; commit "$R"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "D2 — a séma maga nem sérti a saját szabályát"
R=$(mkroot); printf '# Doc\n' > "$R/a.md"; commit "$R"
check "exit 0" "0" "$(run "$R")"
rm -rf "$R"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
