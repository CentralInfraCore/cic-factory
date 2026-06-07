# cic-schemas-audit — CIC-Schemas repó megértése

## Célod

A CIC-Schemas repó teljes megértése: struktúra, séma formátum, signing pipeline, OCI publikálás, branch modell. **Nem audit a szó szoros értelmében** — megértés és dokumentálás. A kimenetet a PoC tervezéséhez használjuk.

## Forrás

```
${CIC_SCHEMAS_PATH}
```

## Lépések

### 1. Branch modell

```bash
git -C ${CIC_SCHEMAS_PATH} branch -a
```

Dokumentáld: milyen branch-struktúra van, mit jelent egy branch (service/version/stage)?

### 2. Repó struktúra

Olvasd el a főkönyvtár tartalmát:
```bash
ls ${CIC_SCHEMAS_PATH}
ls ${CIC_SCHEMAS_PATH}/schemas/
ls ${CIC_SCHEMAS_PATH}/source/
ls ${CIC_SCHEMAS_PATH}/release/
ls ${CIC_SCHEMAS_PATH}/tools/
```

### 3. Séma formátum

Olvass el legalább 2-3 konkrét séma fájlt a `schemas/` könyvtárból (különböző típusok ha van). Dokumentáld:
- Milyen formátum (YAML/JSON)?
- Milyen kötelező mezők vannak?
- Hogyan épül fel egy séma (fejléc, mezők, constraintek)?
- Van-e `$schema` referencia vagy meta-séma?

### 4. Makefile — build pipeline

```bash
cat ${CIC_SCHEMAS_PATH}/Makefile
```

Dokumentáld az elérhető make célokat és sorrendjüket: hogyan megy a build → sign → publish pipeline?

### 5. Signing mechanizmus

Keress rá:
```bash
grep -rn "vault\|sign\|countersign\|cic_countersign" ${CIC_SCHEMAS_PATH}/ \
  --include="*.py" --include="*.yaml" --include="*.sh" --include="Makefile" \
  | grep -v ".git/" | grep -v "p_venv/" | head -40
```

Dokumentáld: hogyan történik az aláírás — Python script, Vault hívás, mikor fut?

### 6. OCI publikálás

```bash
grep -rn "ghcr\|oci\|docker\|push\|registry" ${CIC_SCHEMAS_PATH}/ \
  --include="*.py" --include="*.yaml" --include="*.sh" --include="Makefile" \
  | grep -v ".git/" | grep -v "p_venv/" | head -40
```

Dokumentáld: mi kerül az OCI registry-be, milyen tag-gel, milyen formátumban?

### 7. PostgreSQL branch példa

```bash
git -C ${CIC_SCHEMAS_PATH} checkout postgresql/v18/main 2>/dev/null || \
  git -C ${CIC_SCHEMAS_PATH} checkout remotes/origin/postgresql/v18/main
ls ${CIC_SCHEMAS_PATH}/schemas/
```

Olvass el 1-2 konkrét PostgreSQL sémát. Dokumentáld mint konkrét példa arra, hogyan néz ki egy kész service séma.

### 8. Release artifact

```bash
ls ${CIC_SCHEMAS_PATH}/release/ 2>/dev/null
find ${CIC_SCHEMAS_PATH} -name "*.release.yaml" -o -name "*signed*" 2>/dev/null | head -10
```

Dokumentáld: mi a release artifact formátuma, mi van benne (séma + aláírás + metaadatok)?

### 9. Visszaállítás

```bash
git -C ${CIC_SCHEMAS_PATH} checkout main 2>/dev/null || true
```

## Output fájlok

`output/schemas-overview.md` — Teljes áttekintés:

```markdown
## Branch modell
[branch struktúra és jelentése]

## Könyvtár struktúra
[mit tartalmaz každá könyvtár]

## Séma formátum
[formátum, kötelező mezők, példa struktúra]

## Build → Sign → Publish pipeline
[make célok sorrendben, mit csinál mindegyik]

## Signing mechanizmus
[hogyan, mikor, milyen kulccsal]

## OCI publikálás
[mi kerül ki, milyen tag, milyen formátum]

## PostgreSQL séma példa
[konkrét séma felépítése annotálva]

## Release artifact
[mit tartalmaz, hogyan épül fel]

## PoC relevanciák
[mi hasznos a poc/v1 tervezéséhez]
```

`output/claim-evidence.md` — Kötelező tábla:

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| branch modell dokumentálva | true/false | branch lista + leírás | git branch -a futtatva | alacsony |
| séma formátum megértve | true/false | legalább 2 séma fájl olvasva | fájl path + tartalom | közepes |
| signing pipeline dokumentálva | true/false | Makefile + script olvasva | grep + fájl olvasás | kritikus |
| OCI publikálás dokumentálva | true/false | konkrét push parancs vagy script | grep eredmény | kritikus |
| PostgreSQL példa dokumentálva | true/false | konkrét fájl path + tartalom | fájl olvasva | közepes |

## Szabályok

- **Fájl létezése ≠ megértve** — olvasd el a tartalmát, ne csak listázd
- **Exit code 0 ≠ sikeres** — ellenőrizd hogy az olvasott tartalom értelmes-e
- Ha valamit nem találsz (pl. nincs release/ könyvtár): rögzítsd mint "nem található" — ne találj ki
- Ne módosíts semmit a CIC-Schemas repóban
- A `p_venv/` könyvtárat ne olvasd — Python virtuális env, nem releváns
