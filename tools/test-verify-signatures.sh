#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# verify-signatures.sh accept/reject behaviour, on commits signed here with a
# throwaway EC key rather than with Vault. The message format is the hook's, so
# the verifier cannot tell the difference -- and the suite needs no Vault, no
# token and no network, which is what makes it runnable in CI.
#
# Running the verifier over the real history proves only that today's commits
# pass. What has to be shown is that a tampered one does not.

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

KEYDIR=$(mktemp -d)
trap 'rm -rf "$KEYDIR"' EXIT
openssl ecparam -name prime256v1 -genkey -noout -out "$KEYDIR/key.pem" 2>/dev/null
openssl req -new -x509 -key "$KEYDIR/key.pem" -out "$KEYDIR/cert.pem" -days 2 \
    -subj "/C=HU/O=test/CN=test" 2>/dev/null

# Same computation as the hook and the verifier: deterministic tar of the tree.
tree_digest() {
    local repo="$1" tree="$2" tmp
    tmp=$(mktemp -d)
    git -C "$repo" archive --format=tar "$tree" | tar -xf - -C "$tmp"
    tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
        -cf - -C "$tmp" . | openssl dgst -sha256 -binary | openssl base64 -A
    rm -rf "$tmp"
}

# Appends the metadata block the commit-msg hook would have written.
sign_head() {
    local repo="$1" digest sig
    digest=$(tree_digest "$repo" "HEAD^{tree}")
    printf '%s' "$digest" | base64 -d > "$KEYDIR/d.bin"
    openssl pkeyutl -sign -inkey "$KEYDIR/key.pem" -in "$KEYDIR/d.bin" -out "$KEYDIR/s.der" 2>/dev/null
    sig="vault:v1:$(base64 -w0 < "$KEYDIR/s.der")"
    {
        git -C "$repo" log -1 --format=%B
        printf -- '---\n[signing-metadata]\nkey = test\nsignature = %s\nhash-algorithm = sha256\ndigest = %s\n\n[certificate]\n' "$sig" "$digest"
        cat "$KEYDIR/cert.pem"
    } > "$KEYDIR/msg"
    git -C "$repo" commit -q --amend -F "$KEYDIR/msg" --no-verify
}

mkrepo() {
    local r; r=$(mktemp -d)
    git -C "$r" init -q
    git -C "$r" config user.email t@t; git -C "$r" config user.name t
    git -C "$r" config commit.gpgsign false
    mkdir -p "$r/tools"; cp "$SRC/verify-signatures.sh" "$r/tools/"
    printf 'a\n' > "$r/a.txt"
    git -C "$r" add -A; git -C "$r" commit -q -m "init" --no-verify
    echo "$r"
}
add_signed() {
    printf '%s\n' "$2" > "$1/f-$2.txt"
    git -C "$1" add -A; git -C "$1" commit -q -m "change $2" --no-verify
    sign_head "$1"
}
run() { bash "$1/tools/verify-signatures.sh" "${@:2}" >"$1/out.log" 2>&1; echo $?; }

echo "0. Helyesen aláírt commit átmegy (különben a többi eset semmit nem mond)"
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD); add_signed "$R" one
check "exit 0" "0" "$(run "$R" --range "$BASE..HEAD")"
check_log "  GO" "verify-signatures: GO" "$R/out.log"
rm -rf "$R"

echo
echo "1. A fa megváltozik az aláírás után → a digest nem illik"
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD); add_signed "$R" one
# Az üzenet marad, a fa módosul: pontosan az az eset, amit a kiemelés is okozott.
printf 'hamisitva\n' > "$R/a.txt"
git -C "$R" add -A
git -C "$R" commit -q --amend --no-edit --no-verify
check "exit 1" "1" "$(run "$R" --range "$BASE..HEAD")"
check_log "  a digest-eltérést nevezi meg" "a digest NEM a saját fájára illik" "$R/out.log"
rm -rf "$R"

echo
echo "2. Hiányzó aláírás-metaadat"
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD)
printf 'x\n' > "$R/b.txt"; git -C "$R" add -A
git -C "$R" commit -q -m "unsigned change" --no-verify
check "exit 1" "1" "$(run "$R" --range "$BASE..HEAD")"
check_log "  ezt mondja" "nincs aláírás-metaadat" "$R/out.log"
rm -rf "$R"

echo
echo "3. Elrontott aláírás, helyes digesttel"
# A digest stimmel, de a signature bájtjai mások: csak az ECDSA-ellenőrzés fogja
# meg. Enélkül a verifier egy hamisított aláírást is átengedne.
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD); add_signed "$R" one
git -C "$R" log -1 --format=%B | sed 's|^signature = vault:v1:.|signature = vault:v1:X|' > "$KEYDIR/bad"
git -C "$R" commit -q --amend -F "$KEYDIR/bad" --no-verify
check "exit 1" "1" "$(run "$R" --range "$BASE..HEAD")"
check_log "  az ECDSA-ellenőrzés fogja meg" "az ECDSA aláírás NEM érvényes" "$R/out.log"
rm -rf "$R"

echo
echo "4. Merge commit, ami nem hoz tartalmat → rendben aláírás nélkül is"
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD)
git -C "$R" checkout -q -b side; add_signed "$R" side
git -C "$R" checkout -q -; git -C "$R" merge -q --no-ff -m "Merge side" side --no-verify
check "exit 0" "0" "$(run "$R" --range "$BASE..HEAD")"
check_log "  így is nevezi" "merge, nem hoz tartalmat" "$R/out.log"
rm -rf "$R"

echo
echo "5. Merge commit, ami SAJÁT tartalmat hoz és nincs aláírva"
# Ez a lyuk: ha valaki merge közben belejavít, az a tartalom egyetlen aláírás
# alá sem esik.
R=$(mkrepo); BASE=$(git -C "$R" rev-parse HEAD)
git -C "$R" checkout -q -b side2; add_signed "$R" side2
git -C "$R" checkout -q -
git -C "$R" merge -q --no-ff --no-commit side2 >/dev/null 2>&1
printf 'kezzel becsempeszve\n' > "$R/smuggled.txt"
git -C "$R" add -A; git -C "$R" commit -q -m "Merge side2" --no-verify
check "exit 1" "1" "$(run "$R" --range "$BASE..HEAD")"
check_log "  a becsempészést jelenti" "merge tartalmat hoz és nincs aláírva" "$R/out.log"
rm -rf "$R"

echo
echo "5b. Üres vagy feloldhatatlan tartomány NEM lehet GO"
# Enélkül egy elgépelt range csendben átmegy: a kapu zöld lenne, miközben
# semmit nem ellenőrzött. Ez a legalattomosabb fajta fail-open, mert épp a
# verifikáció hiányát rejti el.
R=$(mkrepo)
check "üres tartomány → elutasít" "1" "$(run "$R" --range HEAD..HEAD)"
check_log "  kimondja, hogy ez nem rendben van" "ÜRES vagy feloldhatatlan" "$R/out.log"
check "nem létező ref → elutasít" "1" "$(run "$R" --range nincsilyen..HEAD)"
rm -rf "$R"

echo
echo "6. Tag aláírt commiton / merge commiton"
R=$(mkrepo)
git -C "$R" checkout -q -b side3; add_signed "$R" side3
git -C "$R" checkout -q -; git -C "$R" merge -q --no-ff -m "Merge side3" side3 --no-verify
git -C "$R" tag rel/@bad HEAD
# Az aláírt commitot néven kell megfogni. A `rev-list -1 --no-merges HEAD`
# csábító, de a merge ELSŐ szülőjét járja előbb — itt az init-et adná vissza,
# nem a side3 aláírt csúcsát.
git -C "$R" tag rel/@good side3
check "merge commiton → elutasít" "1" "$(run "$R" --tag rel/@bad)"
check_log "  megmondja mit tegyél" "tedd az aláírt szülőre" "$R/out.log"
check "aláírt commiton → átmegy" "0" "$(run "$R" --tag rel/@good)"
rm -rf "$R"

echo
echo "==== $pass PASS / $fail FAIL ===="
[[ "$fail" -eq 0 ]]
