# cic-factory-core v0.5.0

A commit-aláírás manifestje (`cic-tree-manifest/v4`) beköti az aláíró nyilvános
kulcsát. Egyetlen tartalmi változás a `v0.4.1` óta.

Tag: `core/@v0.5.0` — 1 tartalmi PR (#94) a `core/@v0.4.1` óta.

---

## Miért minor bump

Az új aláíró **v4** manifestet ír. Egy `v0.4.x` verifier a v4-et nem ismeri
(`ismeretlen manifest-verzió`), ezért a v4 alatt aláírt commitot csak egy ezt a
kiadást (vagy újabbat) átvevő repó verifikál. A régi, v1–v3 alatt aláírt commitok
a v4 verifierrel változatlanul verifikálnak. Nincs új mező, nincs új kapu, nincs
kikényszerített migráció — de az átvétel sorrendje számít (lásd lent).

---

## Mi hibázott

A v3 digestje nem függött attól, ki írta alá. A rögzített digestet bárki újra
aláírhatta a saját kulcsával, kicserélhette a `[certificate]` blokkot, és a
`verify-signatures.sh` GO-t adott rá. Mérve: `test-proof-binding.sh` 11. eset
(ugyanaz a digest másik kulccsal: v3 alatt GO, v4 alatt FAIL).

## Mi változott

- `tools/git_hook_commit-msg.sh`: a tanúsítványt aláírás **előtt** kéri le,
  belőle származtatja a kulcsot, és aláírás után ellenőrzi, hogy a Vault
  aláírása erre a kulcsra érvényes. Ha a transit kulcs és a tárolt tanúsítvány
  elvált egymástól, a commit helyben megáll.
- `tools/verify-signatures.sh`: új v4 ág; a kulcsot a commitban hozott
  tanúsítványból olvassa. A v3, v2 és v1 változatlan.
- `tools/check-hook-provenance.sh`: a viselkedési próba hamis Vaultja valódi,
  eldobható kulcsot használ; csak a `manifest` és a `digest` kerül összevetésre.
- Tesztek (`test-proof-binding.sh`, `test-commit-msg-signer.sh`,
  `test-check-hook-provenance.sh`), `SPEC.md` UC-08.

## Amit a v4 NEM állít

A kulcs **kötött**, de nem **megbízható**: a verifier nem ellenőrzi, hogy a
tanúsítványt ki adta ki. Egy saját kulccsal, saját tanúsítvánnyal, újraszámolt
digesttel készült commit továbbra is GO-t kap. Ehhez bizalmi horgony kell
(CA-lánc vagy rögzített kulcs-lista), ami külön lépés.

## Átvételkor

`dependency.yaml`: `tag: core/@v0.5.0`, új `commit`, és a
`docs/RELEASE-0.5.0.md` az `imported_paths` közé.

**Sorrend:** előbb az átvevő repó verifierét kell erre a kiadásra emelni, és csak
utána szabad a közös `commit-msg` hookot v4-re állítani. Fordított sorrendben a
repó saját CI-ja `ismeretlen manifest-verzió` hibával bukik az első v4 commiton.
