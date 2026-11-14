#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Az aláírás a COMMITHOZ van kötve, nem csak a fához (#44).
#
# A mért hiba: a v2 manifest csak a fát kötötte. Egy A repóban készült aláírt
# blokk változtatás nélkül átment egy MÁSIK repó MÁSIK commitján, MÁS üzenettel
# — mert a két fa azonos volt. A `verify-signatures.sh` GO-t adott rá.
#
# Ez a suite a VALÓDI hookot futtatja valódi `git commit`-on (hamis Vault-curl-lel),
# és a VALÓDI verifierrel ellenőriz. A meglévő test-commit-msg-signer.sh
# "round-trip" szakasza a verifiert el sem indította: csak a manifest-sort és a
# digest ALAKJÁT nézte. Egy olyan hook, ami helyes alakú, de rossz digestet ír,
# átment volna rajta.
#
# HATÓKÖR: ez a suite a commit KONTEXTUSÁNAK kötését méri. A FA kötését (a
# gitlink-ütközést is) a test-verify-signatures.sh fedi — a fa-felsorolás
# kimutálva ez a suite zöld marad, az piros lesz. Mérve, nem feltételezve.

set -uo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SRC/git_hook_commit-msg.sh"
VERIFY="$SRC/verify-signatures.sh"
TOKEN="hvs.TESTTOKEN0123456789"
pass=0; fail=0

check() {
    if [[ "$2" == "$3" ]]; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — várt: '$2', kapott: '$3'"; ((fail++)); fi
}
check_log() {
    if grep -qF -- "$2" "$3"; then echo "  PASS  $1"; ((pass++))
    else echo "  FAIL  $1 — nem található: '$2'"; ((fail++)); fi
}

ENVROOT=$(mktemp -d); trap 'rm -rf "$ENVROOT"' EXIT
mkdir -p "$ENVROOT/bin" "$ENVROOT/vault" "$ENVROOT/keys"
printf '%s' "$TOKEN"  > "$ENVROOT/vault/sign-token"
printf 'FAKE-CA\n'    > "$ENVROOT/vault/server.crt"
# VALÓDI kulcs: a hamis curl tényleg aláír. Enélkül az 1. eset a kriptón
# bukna, nem a digesten — és nem azt mérnénk, amit akarunk.
openssl ecparam -name prime256v1 -genkey -noout -out "$ENVROOT/keys/key.pem" 2>/dev/null
openssl req -new -x509 -key "$ENVROOT/keys/key.pem" -out "$ENVROOT/keys/cert.pem" \
    -days 2 -subj "/C=HU/O=test/CN=test" 2>/dev/null
cat > "$ENVROOT/bin/curl" <<FAKE
#!/usr/bin/env bash
# A Vault transit/sign szemantikája: prehashed sha2-256, a bemenet base64 digest.
last="\${*: -1}"
payload=""
prev=""
for a in "\$@"; do [ "\$prev" = "-d" ] && payload="\$a"; prev="\$a"; done
case "\$last" in
    *transit/sign*)
        d=\$(printf '%s' "\$payload" | sed -n 's/.*"input": *"\([^"]*\)".*/\1/p')
        printf '%s' "\$d" | base64 -d > "$ENVROOT/keys/d.bin"
        openssl pkeyutl -sign -inkey "$ENVROOT/keys/key.pem" \
            -in "$ENVROOT/keys/d.bin" -out "$ENVROOT/keys/s.der" 2>/dev/null
        printf '{"data":{"signature":"vault:v1:%s"}}' "\$(base64 -w0 < "$ENVROOT/keys/s.der")"
        ;;
    *data/crt*)
        c=\$(sed ':a;N;\$!ba;s/\n/\\\\n/g' "$ENVROOT/keys/cert.pem")
        printf '{"data":{"data":{"bar":"%s"}}}' "\$c"
        ;;
    *) printf '{}' ;;
esac
FAKE
chmod +x "$ENVROOT/bin/curl"

# A hook VALÓDI commit-msg hookként települ, hogy a `git commit` hívja meg.
mkrepo() {   # <név>
    local r="$ENVROOT/$1"
    mkdir -p "$r/hooks"
    git init -q "$r"
    git -C "$r" config user.email t@t
    git -C "$r" config user.name  "Teszt Elek"
    git -C "$r" config commit.gpgsign false
    git -C "$r" config core.hooksPath "$r/hooks"
    git -C "$r" remote add origin "https://example.invalid/$1.git"
    cat > "$r/hooks/commit-msg" <<HK
#!/usr/bin/env bash
export PATH="$ENVROOT/bin:\$PATH"
export CIC_VAULT_TOKEN_FILE="$ENVROOT/vault/sign-token"
export CIC_VAULT_CA_FILE="$ENVROOT/vault/server.crt"
export VAULT_ADDR="https://vault.invalid:8200"
exec bash "$HOOK" "\$1"
HK
    chmod +x "$r/hooks/commit-msg"
    # A verifier WORKDIR-t a saját helyéből számol -- a fixture-ben kell lennie,
    # különben a hívó repóját ellenőrizné. (Ez pontosan úgy sült ki, ahogy a
    # verifier saját fejléce leírja: némán a rossz repót nézte.)
    mkdir -p "$r/tools"
    cp "$VERIFY" "$SRC/lib-vault-sign.sh" "$r/tools/"
    # Alap-commit, hogy legyen mihez képest range-elni. A hook nem fut rá:
    # a --no-verify pont ezt kerüli ki, és a v1-es múltat is ez modellezi.
    printf 'base\n' > "$r/.base"
    git -C "$r" add .base
    git -C "$r" commit -q --no-verify -m "alap (aláíratlan)"
    echo "$r"
}
verify() { bash "$1/tools/verify-signatures.sh" --range "$2" 2>&1; }

echo "1. Valódi hook → valódi commit → valódi verifier"
A=$(mkrepo A)
echo alma > "$A/f.txt"; git -C "$A" add f.txt
git -C "$A" commit -q -m "commit A — az eredeti" 2>"$ENVROOT/a.err"
C_A=$(git -C "$A" rev-parse HEAD)
check "a hook aláírta" "1" "$(git -C "$A" log -1 --format=%B | grep -c 'signing-metadata')"
check "  v4 manifestet ír" "1" "$(git -C "$A" log -1 --format=%B | grep -c 'manifest = cic-tree-manifest/v4')"
verify "$A" "$C_A~1..$C_A" > "$ENVROOT/v_ok.log"
check "  a verifier elfogadja (digest egyezik)" "0" "$?"
check "  GO-t mond" "1" "$(grep -c ': GO ' "$ENVROOT/v_ok.log")"

echo
echo "2. Átültetés: A aláírása B másik commitján (#44)"
# Két repó, AZONOS fával, KÜLÖNBÖZŐ commit-üzenettel. A v2 alatt ez átment.
B=$(mkrepo B)
echo alma > "$B/f.txt"; git -C "$B" add f.txt
git -C "$B" commit -q -m "commit B — MÁS üzenet" 2>/dev/null
C_B=$(git -C "$B" rev-parse HEAD)
check "a két fa azonos" "1" \
    "$([ "$(git -C "$A" rev-parse HEAD^{tree})" == "$(git -C "$B" rev-parse HEAD^{tree})" ] && echo 1 || echo 0)"

# A aláírt blokkja B üzenetének testére ültetve.
{ git -C "$B" log -1 --format=%B | sed '/^---$/,$d'
  git -C "$A" log -1 --format=%B | sed -n '/^---$/,$p'
} > "$ENVROOT/graft.msg"
git -C "$B" commit -q --amend --no-verify -F "$ENVROOT/graft.msg"
C_BG=$(git -C "$B" rev-parse HEAD)
check "  a blokk tényleg átkerült" "1" \
    "$(git -C "$B" log -1 --format=%B | grep -c 'signing-metadata')"
check "  és tényleg az A digestje" "1" \
    "$(git -C "$B" log -1 --format=%B | grep -oP '^digest = \K\S+' \
       | grep -cF "$(git -C "$A" log -1 --format=%B | grep -oP '^digest = \K\S+')")"
verify "$B" "$C_BG~1..$C_BG" > "$ENVROOT/v_graft.log"; RC=$?
check "  a verifier ELUTASÍTJA" "1" "$RC"
check_log "  megnevezi az okot" "a digest NEM erre a commitra illik" "$ENVROOT/v_graft.log"

echo
echo "3. Az üzenet utólagos átírása érvényteleníti"
A2=$(mkrepo A2)
echo korte > "$A2/f.txt"; git -C "$A2" add f.txt
git -C "$A2" commit -q -m "eredeti üzenet" 2>/dev/null
git -C "$A2" log -1 --format=%B > "$ENVROOT/edit.msg"
sed -i '1s/.*/HAMISÍTOTT üzenet/' "$ENVROOT/edit.msg"
git -C "$A2" commit -q --amend --no-verify -F "$ENVROOT/edit.msg"
H=$(git -C "$A2" rev-parse HEAD)
verify "$A2" "$H~1..$H" > "$ENVROOT/v_edit.log"
check "elutasít" "1" "$?"

echo
echo "4. Merge commit szülői is bekötve"
M=$(mkrepo M)
echo a > "$M/f.txt"; git -C "$M" add f.txt; git -C "$M" commit -q -m base 2>/dev/null
BASE=$(git -C "$M" rev-parse HEAD)
git -C "$M" checkout -q -b oldal
echo b > "$M/g.txt"; git -C "$M" add g.txt; git -C "$M" commit -q -m oldalag 2>/dev/null
git -C "$M" checkout -q -
echo c > "$M/h.txt"; git -C "$M" add h.txt; git -C "$M" commit -q -m fovonal 2>/dev/null
git -C "$M" merge -q --no-ff -m "merge: oldal" oldal 2>/dev/null
MH=$(git -C "$M" rev-parse HEAD)
check "a merge commit két szülős" "2" "$(git -C "$M" rev-parse "$MH^@" | wc -l)"
check "  alá van írva" "1" "$(git -C "$M" log -1 --format=%B | grep -c 'signing-metadata')"
verify "$M" "$BASE..$MH" > "$ENVROOT/v_merge.log"
check "  a verifier elfogadja" "0" "$?"

echo
echo "5. Szerkesztő-kommentek: a git a hook UTÁN takarítja el őket"
# `git commit` szerkesztővel `#` sorokat hagy a fájlban. A hook azokat is
# látja, a verifier már nem. Ha a hook nem strippel, minden ilyen commit
# ellenőrizhetetlen — és ez a valódi napi használat, nem sarokeset.
# A cleanup-mód nem fix: `-F`/`-m` mellett `whitespace` (a kommentek BENNMARADNAK),
# szerkesztővel `default` (a git ELTAKARÍTJA őket). A hook nem tudja, melyik lesz
# — mindkettőnek verifikálhatónak kell maradnia.
printf 'valódi üzenet\n\n# Please enter the commit message for your changes.\n# On branch main\n' \
    > "$ENVROOT/withcomments.msg"

E=$(mkrepo E)
echo x > "$E/f.txt"; git -C "$E" add f.txt
git -C "$E" commit -q --cleanup=strip -F "$ENVROOT/withcomments.msg" 2>/dev/null
HE=$(git -C "$E" rev-parse HEAD)
check "cleanup=strip (a szerkesztős út) → a git eltakarítja a kommenteket" "0" \
    "$(git -C "$E" log -1 --format=%B "$HE" | grep -c '^# On branch')"
verify "$E" "$HE~1..$HE" > "$ENVROOT/v_cmt.log"
check "  a verifier elfogadja" "0" "$?"

E2=$(mkrepo E2)
echo x > "$E2/f.txt"; git -C "$E2" add f.txt
git -C "$E2" commit -q --cleanup=whitespace -F "$ENVROOT/withcomments.msg" 2>/dev/null
HE2=$(git -C "$E2" rev-parse HEAD)
check "cleanup=whitespace → a kommentek bennmaradnak" "1" \
    "$(git -C "$E2" log -1 --format=%B "$HE2" | grep -c '^# On branch')"
verify "$E2" "$HE2~1..$HE2" > "$ENVROOT/v_cmt2.log"
check "  a verifier ezt is elfogadja" "0" "$?"

echo
echo "6. A felhasználó saját --- elválasztója nem töri el az ellenőrzést"
# Egy `sed '/^---$/,$d'` levágta volna a törzs felét. A markdown vízszintes
# vonal és a YAML front matter is pont így néz ki.
F=$(mkrepo F)
echo y > "$F/f.txt"; git -C "$F" add f.txt
printf 'fejléc\n\n---\n\ntörzs a saját elválasztó UTÁN\n' > "$ENVROOT/dashes.msg"
git -C "$F" commit -q -F "$ENVROOT/dashes.msg" 2>/dev/null
HF=$(git -C "$F" rev-parse HEAD)
check "az üzenet két --- sort tartalmaz" "2" \
    "$(git -C "$F" log -1 --format=%B "$HF" | grep -c '^---$')"
verify "$F" "$HF~1..$HF" > "$ENVROOT/v_dash.log"
check "  a verifier elfogadja" "0" "$?"

echo
echo "7. Amit a kötés NEM tehet tönkre: amend és rebase"
# A szülőket szándékosan nem kötjük. Az első változat kötötte, és a saját
# commitján bukott el: a hook a commit ELŐTT fut, tehát `--amend`-nél a HEAD
# nem az új commit szülője. A `git rebase` pedig nem futtatja újra ezt a hookot
# — a régi blokkot változatlanul viszi át egy ÚJ szülő alá. Ebben a projektben
# a rebase minden PR előtt kötelező, tehát a szülő-kötés minden PR-t
# ellenőrizhetetlenné tett volna.
#
# Ez a két eset őrzi a döntést: ha valaki visszateszi a szülő-kötést, itt bukik.
A2P=$(mkrepo A2P)
echo q > "$A2P/f.txt"; git -C "$A2P" add f.txt
git -C "$A2P" commit -q -m "eredeti" 2>/dev/null
echo q2 > "$A2P/f.txt"; git -C "$A2P" add f.txt
git -C "$A2P" commit -q --amend -m "amendelt üzenet" 2>/dev/null
HA=$(git -C "$A2P" rev-parse HEAD)
check "az amendelt commit alá van írva" "1" \
    "$(git -C "$A2P" log -1 --format=%B | grep -c 'signing-metadata')"
verify "$A2P" "$HA~1..$HA" > "$ENVROOT/v_amend.log"
check "  a verifier elfogadja" "0" "$?"

# A rebase MÁS eset, és a különbség lényeges: nem a szülőt, hanem a FÁT
# változtatja meg — a rebase-elt commit már tartalmazza az új alap fájljait is.
# Ezt a v1 és a v2 is elutasította, tehát nem v3-regresszió. Az alábbi
# fa-összehasonlítás ezt bizonyítja: bármely fa-alapú manifest digestje eltér,
# ha maga a fa eltér.
RB=$(mkrepo RB)
echo r > "$RB/f.txt"; git -C "$RB" add f.txt
git -C "$RB" commit -q -m "ág-commit" 2>/dev/null
SIGNED_TREE=$(git -C "$RB" rev-parse "HEAD^{tree}")
git -C "$RB" branch -q agi
git -C "$RB" reset -q --hard HEAD~1
echo mainfile > "$RB/m.txt"; git -C "$RB" add m.txt
git -C "$RB" commit -q --no-verify -m "a fővonal halad"
MAINTIP=$(git -C "$RB" rev-parse HEAD)
git -C "$RB" checkout -q agi
git -C "$RB" rebase -q "$MAINTIP" 2>/dev/null
HR=$(git -C "$RB" rev-parse HEAD)
check "a rebase új szülőt adott" "$MAINTIP" "$(git -C "$RB" rev-parse "$HR^")"
check "  a régi blokk változatlanul átjött" "1" \
    "$(git -C "$RB" log -1 --format=%B | grep -c 'signing-metadata')"
check "  de a FA is megváltozott" "1" \
    "$([ "$SIGNED_TREE" != "$(git -C "$RB" rev-parse "$HR^{tree}")" ] && echo 1 || echo 0)"
verify "$RB" "$MAINTIP..$HR" > "$ENVROOT/v_rebase.log"
check "  ezért a verifier elutasítja (fa-kötés, nem v3-specifikus)" "1" "$?"

echo "8. Csak a SZERZŐ más"
# Ez izolálja az `author` kötést: az aláírt commit szerzőjét átírva a blokk
# változatlan marad.
Z=$(mkrepo Z)
echo z > "$Z/f.txt"; git -C "$Z" add f.txt
git -C "$Z" commit -q -m "szerzo-teszt" 2>/dev/null
git -C "$Z" log -1 --format=%B > "$ENVROOT/author.msg"
git -C "$Z" commit -q --amend --no-verify --author="Valaki Mas <mas@t>" \
    -F "$ENVROOT/author.msg"
HZ=$(git -C "$Z" rev-parse HEAD)
check "a szerző tényleg más" "Valaki Mas" "$(git -C "$Z" log -1 --format=%an "$HZ")"
check "  a blokk változatlan" "1" "$(git -C "$Z" log -1 --format=%B | grep -c 'signing-metadata')"
verify "$Z" "$HZ~1..$HZ" > "$ENVROOT/v_author.log"
check "  a verifier elutasítja" "1" "$?"

echo
echo "9. Csak a COMMITTER más"
K=$(mkrepo K)
echo k > "$K/f.txt"; git -C "$K" add f.txt
git -C "$K" commit -q -m "committer-teszt" 2>/dev/null
git -C "$K" log -1 --format=%B > "$ENVROOT/committer.msg"
( cd "$K" && env GIT_COMMITTER_NAME="Mas Bela" GIT_COMMITTER_EMAIL="mb@t" \
    git commit -q --amend --no-verify -F "$ENVROOT/committer.msg" )
HK=$(git -C "$K" rev-parse HEAD)
check "a szerző VÁLTOZATLAN" "Teszt Elek" "$(git -C "$K" log -1 --format=%an "$HK")"
check "  a committer más" "Mas Bela" "$(git -C "$K" log -1 --format=%cn "$HK")"
verify "$K" "$HK~1..$HK" > "$ENVROOT/v_committer.log"
check "  a verifier elutasítja" "1" "$?"

echo
echo "10. A régi aláírások továbbra is verifikálhatók"
# A v3 nem teheti ellenőrizhetetlenné a v2/v1 múltat.
check "a verifier ismeri a v2-t" "1" "$(grep -c 'cic-tree-manifest/v2)' "$VERIFY")"
check "  és a legacy (manifest-sor nélküli) ágat" "1" \
    "$(grep -c 'legacy\|üres' "$VERIFY" | head -1 | grep -c '^[1-9]')"

echo
echo "11. Kulcscsere: ugyanaz a digest, MÁS kulccsal újra aláírva (v4)"
# A v3 digestje nem függött az aláírótól: a rögzített digestet bárki újra
# aláírhatta a saját kulcsával, kicserélhette a [certificate] blokkot, és a
# commit GO-t kapott. A v4 a kulcsot a manifestbe köti.
openssl ecparam -name prime256v1 -genkey -noout -out "$ENVROOT/keys/other.pem" 2>/dev/null
openssl req -new -x509 -key "$ENVROOT/keys/other.pem" -out "$ENVROOT/keys/other-cert.pem" \
    -days 2 -subj "/CN=other" 2>/dev/null

# resign_with <repo> <key> <cert>: a HEAD rögzített digestjét aláírja a megadott
# kulccsal, és kicseréli a signature sort meg a tanúsítványt. A digest marad.
resign_with() {
    local r="$1" key="$2" cert="$3" d sig
    d=$(git -C "$r" log -1 --format=%B | grep -oP '^digest = \K\S+' | head -1)
    printf '%s' "$d" | base64 -d > "$ENVROOT/keys/swap.bin"
    openssl pkeyutl -sign -inkey "$key" -in "$ENVROOT/keys/swap.bin" \
        -out "$ENVROOT/keys/swap.der" 2>/dev/null
    sig="vault:v1:$(base64 -w0 < "$ENVROOT/keys/swap.der")"
    { git -C "$r" log -1 --format=%B | sed '/-----BEGIN CERTIFICATE-----/,$d' \
          | sed "s|^signature = .*|signature = $sig|"
      cat "$cert"
    } > "$ENVROOT/swap.msg"
    git -C "$r" commit -q --amend --no-verify -F "$ENVROOT/swap.msg"
}

# Kontroll: ugyanazzal a kulccsal újra aláírva GO -- tehát a csere mechanikája
# ép, és a lenti elutasítás a KULCS miatt van, nem egy elrontott üzenet miatt.
S=$(mkrepo S)
echo korte > "$S/f.txt"; git -C "$S" add f.txt
git -C "$S" commit -q -m "commit S" 2>/dev/null
resign_with "$S" "$ENVROOT/keys/key.pem" "$ENVROOT/keys/cert.pem"
HS=$(git -C "$S" rev-parse HEAD)
verify "$S" "$HS~1..$HS" > "$ENVROOT/v_same.log"
check "kontroll: azonos kulccsal újra aláírva GO" "0" "$?"

resign_with "$S" "$ENVROOT/keys/other.pem" "$ENVROOT/keys/other-cert.pem"
HS=$(git -C "$S" rev-parse HEAD)
check "  a tanúsítvány tényleg kicserélődött" "1" \
    "$(git -C "$S" log -1 --format=%B | sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' \
       | openssl x509 -noout -subject 2>/dev/null | grep -c 'CN *= *other')"
verify "$S" "$HS~1..$HS" > "$ENVROOT/v_swap.log"
check "  más kulccsal: a verifier elutasítja" "1" "$?"
check_log "  a v4 digest-eltérést nevezi meg" "a digest NEM erre a commitra illik (v4 manifest)" "$ENVROOT/v_swap.log"

# Ugyanez v3-mal: a v3 hookot a v4-ből állítjuk elő (verzió vissza, kulcs-sor ki),
# és MÉRJÜK, hogy a sed tényleg landolt.
V3=$(mkrepo V3)
sed -e 's|cic-tree-manifest/v4|cic-tree-manifest/v3|' -e "/printf 'signer-public-key:/d" \
    "$HOOK" > "$ENVROOT/hook-v3.sh"
check "v3 hook-másolat: a kulcs-sor kikerült" "0" "$(grep -c 'signer-public-key:' "$ENVROOT/hook-v3.sh")"
sed -i "s|$HOOK|$ENVROOT/hook-v3.sh|" "$V3/hooks/commit-msg"
echo korte > "$V3/f.txt"; git -C "$V3" add f.txt
git -C "$V3" commit -q -m "commit V3" 2>/dev/null
HV=$(git -C "$V3" rev-parse HEAD)
check "  v3 manifestet írt" "1" "$(git -C "$V3" log -1 --format=%B | grep -c 'manifest = cic-tree-manifest/v3')"
verify "$V3" "$HV~1..$HV" > /dev/null
check "  a v3 történet továbbra is verifikál" "0" "$?"
resign_with "$V3" "$ENVROOT/keys/other.pem" "$ENVROOT/keys/other-cert.pem"
HV=$(git -C "$V3" rev-parse HEAD)
verify "$V3" "$HV~1..$HV" > /dev/null
check "  v3 alatt a kulcscsere ÁTMEGY (ezt zárja a v4)" "0" "$?"

echo
echo "12. Lánc a PEM-ben: levél + CICrootCA"
# A következő kiadástól a Vault a levél mellett a root CA-t is visszaadja. A hook
# és a verifier az ELSŐ tanúsítvány kulcsát köti -- ez csak akkor helyes, ha a
# levél áll elöl. Fordított sorrendnél a hook önellenőrzése megállítja a commitot.
openssl ecparam -name prime256v1 -genkey -noout -out "$ENVROOT/keys/root.pem" 2>/dev/null
openssl req -new -x509 -key "$ENVROOT/keys/root.pem" -out "$ENVROOT/keys/root-cert.pem" \
    -days 2 -subj "/CN=CICrootCA-test" 2>/dev/null
openssl req -new -key "$ENVROOT/keys/key.pem" -subj "/CN=signer" -out "$ENVROOT/keys/leaf.csr" 2>/dev/null
openssl x509 -req -in "$ENVROOT/keys/leaf.csr" -CA "$ENVROOT/keys/root-cert.pem" \
    -CAkey "$ENVROOT/keys/root.pem" -CAcreateserial -days 2 \
    -out "$ENVROOT/keys/leaf-cert.pem" 2>/dev/null
cp "$ENVROOT/keys/cert.pem" "$ENVROOT/keys/cert-orig.pem"

cat "$ENVROOT/keys/leaf-cert.pem" "$ENVROOT/keys/root-cert.pem" > "$ENVROOT/keys/cert.pem"
L=$(mkrepo L)
echo szilva > "$L/f.txt"; git -C "$L" add f.txt
git -C "$L" commit -q -m "commit L" 2>/dev/null
HL=$(git -C "$L" rev-parse HEAD)
check "levél elöl: a hook aláír" "1" "$(git -C "$L" log -1 --format=%B | grep -c 'signing-metadata')"
check "  mindkét tanúsítvány a blokkban" "2" "$(git -C "$L" log -1 --format=%B | grep -c 'BEGIN CERTIFICATE')"
verify "$L" "$HL~1..$HL" > /dev/null
check "  a verifier elfogadja" "0" "$?"

cat "$ENVROOT/keys/root-cert.pem" "$ENVROOT/keys/leaf-cert.pem" > "$ENVROOT/keys/cert.pem"
RV=$(mkrepo RV)
echo szilva > "$RV/f.txt"; git -C "$RV" add f.txt
git -C "$RV" commit -q -m "commit RV" 2>"$ENVROOT/rv.err"
check "root elöl: a commit megáll" "1" "$?"
check_log "  az önellenőrzés nevezi meg" "does not verify against the certificate" "$ENVROOT/rv.err"
cp "$ENVROOT/keys/cert-orig.pem" "$ENVROOT/keys/cert.pem"

echo
echo "$pass PASS, $fail FAIL"
[[ "$fail" -eq 0 ]]
