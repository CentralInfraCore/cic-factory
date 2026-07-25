# Interfész-javaslat a relay felé — „repo + commit → build_hash"

**Címzett:** CIC-Relay csapat · **Küldő:** cic-factory orchestrátor
**Státusz:** javaslat, nem implementáció. A CIC-Relay a mi oldalunkról read-only.
**Dátum:** 2026-07-25

Minden alábbi állítás mögött **mért vagy forrásból olvasott bizonyíték** áll
(`fájl:sor`, illetve élő futás kimenete). A méréseket a
[`docs/relay-build-hash-test.md`](relay-build-hash-test.md) írja le, a harness
[`tools/relay-build-test.sh`](../tools/relay-build-test.sh).

---

## 1. A cél

A relay legyen CI-végrehajtó: kap egy **git repót és egy commit id-t**, végigviszi
a build folyamatot, és a kimenete egy **`build_hash`**, ami vagy visszatér, vagy
release-folyamatban beíródik a megfelelő fájlba.

Ez nem új irány: a base-repo `tools/finalize_release.py:9-15` FIXME-je szó szerint
egy *„secure, closed-source build environment ('relay') and a central signing API"*
megjelenésére hivatkozik ideiglenes megoldásként. A javaslat ezt a dokumentált
végállapotot célozza.

---

## 2. Ami MA MŰKÖDIK — mérve, nem feltételezve

Ezt fontos előrebocsátani: a lánc nagy része kész, és jól működik.

| Képesség | Bizonyíték |
|---|---|
| A ProofTrace pontosan a kívánt rekord: `workflow_id`, `source_digest`, `chain_hash`, `steps[]`, `pose_result` | `cmd/relay/proof_verify.go:11-36` |
| A lépések **bele vannak kötve** a láncba | mérés: egy `step.output_hash` elrontása más `chain_hash`-t ad (`recomputed=fcb889ca…`), `valid=false` |
| A `chain_hash` ellenőrzése **köt** | mérés: elrontott `chain_hash` → `valid=false`, `declared=0a4faf… recomputed=8a4faf…` |
| A `build_hash` **tartalom-kötött** | mérés: két különböző spec → `sha256:c085049f…` vs `sha256:04a32b37…` |
| Determinisztikus | mérés: azonos bemenet kétszer → bitre azonos `build_hash` |
| Vault-aláírás | mérés: `cic_sign = vault:v1:MEQCIC4k…` |
| A pipeline **valóban klónoz** és **valóban futtat** `docker exec <builder> make <target>`-et, lépésenként `stdout_digest` + `command_digest` + `exit_code` rögzítéssel | `core/modules/schemapipeline/schemapipeline.go:129,223`; a `make test` kimenete visszajött hibaüzenetként |
| Lépésenkénti Merkle-gyök | `schemapipeline.go` `computeStepHash` → `merkle.LeafHash` + `merkle.HexMerkleRoot` |

**Vagyis a Merkle-lánc, az aláírás és az ellenőrzés kész és bizonyítottan működik.**

---

## 3. A rés — egyetlen mondatban

> A mai `build_hash` azt attesztálja, **amit** lefordítottak; azt nem, hogy **honnan** jött.

| Kérdés | Válaszol rá ma? |
|---|---|
| „Ugyanaz a tartalom lett lefordítva?" | ✅ igen |
| „A repo X commit Y állapotából jött?" | ❌ **nem** |

**Mérve a teljes 7 lépéses pipeline-on, valódi klónozott repóval** (nem statikus
következtetés). Ugyanaz a repo, három különböző commit:

| Futás | Mi változott | `build_hash` | `source_digest` |
|---|---|---|---|
| **A** | alap | `sha256:0636abb1…7e7b` | `unknown` |
| **C** | **csak a `README.md`**, az artifact nem | `sha256:0636abb1…7e7b` | `unknown` |
| **B** | az artifact tartalma | `sha256:f7030f11…5607` | `unknown` |

**A ≡ C: két különböző commit bitre azonos `build_hash`-t kap.**

CI-attesztációra ez diszkvalifikáló: a `build_hash`-sel **nem bizonyítható,
melyik commitból készült a build**. A `source_digest` mind a három futásban
`unknown`, pedig a relay ténylegesen klónozott és ténylegesen lefuttatta a
`make` célokat a builder konténerben.

---

## 4. A kilenc konkrét rés — mind verifikálva

| # | Rés | Bizonyíték |
|---|---|---|
| 1 | Nincs `commit` mező a bemeneten | `cmd/relay/pipeline_handler.go:15-22` — `PipelineRequest`: `schema, version, branch, repo_url, build_dir, builder_container` |
| 2 | A route séma-specifikus, nem generikus repo-CI | `pipeline_handler.go:64-67` — `schema` és `version` **kötelező**, különben 400; `schemapipeline.go:307` fix `source/<schema>.yaml` útvonal |
| 3 | `ci.build@1.0` regisztrálva, de **egyik workflow `Steps[]`-jében sincs** → scaffold | `bootstrap.go:55,64` (regisztráció) vs. `bootstrap.go:122-126` és `218-226` (a két Steps lista teljes tartalma) |
| 4 | A `source_ref`/`source_tree_digest` **elveszik** a láncon | `schemacompile.go:146-154` — az `assertSourceImpl` return-map kimerítő mezőlistája nem tartalmazza őket |
| 5 | A `source_digest` a relay **saját** build-konstansaiból jön | `main.go:713-715` (`bctx.SourceRef = CommitHash`), `main.go:333-337` (fallback), `schemacompile.go:245-252`; **mérve:** `"unknown"` mindkét futásban |
| 6 | A válasz nem tartalmaz forrás-azonosítót | **mérve** élő válaszon: kulcsok = `artifact{artifact, build_hash, cic_sign, cic_signed_ca, verification_root}` + `proof_trace`; nincs `repo_url`/`commit`/`branch`/`source_ref` |
| 7 | Nincs konténerizált CI-belépési pont | **mérve:** nincs relay szolgáltatás a `docker-compose.yml`-ben, a gyökér `Dockerfile` Python schema-compiler image, nincs `make run/serve`. Kézzel kellett összeraknunk az indítást |
| 8 | Sekély, branch-hez kötött klónozás | `schemapipeline.go:129` — `git clone --branch <branch> --depth 1` |
| 9 | A `ci.build` nem ismer gitet és izolációt | `core/modules/cibuild/cibuild.go:52` — egyetlen `exec.CommandContext(buildCtx, "make", target)`, nincs `docker`/`git`/`isolation` |

**Külön lelet — csendes ellenőrzési rés:** a `VerifyProofArtifact` csak **üres**
`source_digest`-re figyelmeztet (*„chain is not anchored to a source revision"*).
Az `"unknown"` sentinel nem üres, ezért **a figyelmeztetés nem sül el** —
mérve: `warnings=None`, miközben a lánc valóban nincs forráshoz kötve.

---

## 5. Javasolt interfész

### 5.1 Bemenet — commit-pinnelés

```jsonc
POST /v1/schemas/pipeline
{
  "repo_url": "https://github.com/org/repo",
  "commit":   "b0d1287abbb67a3ef79bfff27a5cc6b6a98ad5ee",  // ÚJ, kötelező vagy branch-alternatíva
  "branch":   "main"                                        // opcionális, ha commit adott
}
```

A #8 miatt a `--depth 1 --branch` forma nem elég: ha a cél commit nem a branch
HEAD-je, nem érhető el. Javaslat: `git clone` + `git checkout <commit>`, vagy
`git fetch --depth 1 origin <commit>`.

### 5.2 A lánc — provenance átvezetése

A #4 és #5 együtt kezelendő:

1. A `cic.pipeline.start` már ma is számol tree digestet (`computeTreeDigest`) —
   ez kerüljön be a lépés kimenetébe `source_ref` (= commit SHA) és
   `source_tree_digest` néven.
2. Az `assertSourceImpl` **vigye tovább** ezt a két kulcsot (`schemacompile.go:146-154`).
3. A `sign` lépés a `merkle.VerificationManifest.Source` mezőit **a bemeneti
   map-ből** töltse, ne a szerver-indításkori `bctx`-ből.

A `bctx` build-környezeti mezői (`ToolchainDigest`, `DockerImageChecksum`,
`DependencyLockDigest`, `CAFingerprint`) **maradjanak** — azok helyesen a relayre
vonatkoznak. A `Source` blokk az, aminek a vizsgált repóra kell mutatnia.

### 5.3 Kimenet — a forrás legyen látható

```jsonc
{
  "artifact": {
    "build_hash": "sha256:…",
    "verification_root": "…",
    "cic_sign": "vault:v1:…",
    "source_ref": "b0d1287…",          // ÚJ
    "source_tree_digest": "sha256:…"   // ÚJ
  },
  "proof_trace": { "source_digest": "b0d1287…" }   // a repóé, ne a relayé
}
```

### 5.4 Ellenőrzés — a sentinel ne csússzon át

A `VerifyProofArtifact` a `source_digest` mezőt ne csak üresség ellen vizsgálja:
az `"unknown"` (és hasonló sentinelek) is váltsák ki a *„chain is not anchored"*
figyelmeztetést — vagy szigorúbban, `pose_result`-ot befolyásoló hibát.

### 5.5 Belépési pont

A #7-hez: egy `relay` szolgáltatás a `docker-compose.yml`-ben, vagy egy dedikált
image, aminek a belépési pontja paraméterként veszi a repo URL-t és a commitot.
A mi oldalunkon összerakott, működő indítási recept a
[`docs/relay-build-hash-test.md`](relay-build-hash-test.md) „Működő indítási
recept" szakaszában van — hat konkrét buktatóval (RO mount + `-buildvcs=false`,
`GIT_CONFIG_GLOBAL` a `safe.directory`-hoz, docker CLI bemountolása stb.).

### 5.6 Generikus repo-CI (#2, #3) — külön kérdés

A `schema`/`version` kötelezősége a séma-pipeline sajátja. Egy általános repo-CI
úthoz vagy egy másik workflow kell, vagy ezek opcionálissá tétele. A `ci.build@1.0`
modul (`make <target>` + artifact digest) **pont ehhez készült**, csak nincs
workflowba kötve (#3) — de önmagában nem ismer gitet és izolációt (#9), tehát
elé forrás-előkészítő lépés kell.

Ezt **nem sürgetjük**: a séma-pipeline provenance-javítása (5.1–5.4) önmagában is
használhatóvá teszi a láncot CI-attesztációra.

---

## 6. Ami a mi oldalunkon marad

- A tesztharness és az eljárás (`tools/relay-build-test.sh`, `docs/relay-build-hash-test.md`)
- A fixture-recept aláírt `source_assertion`-höz (a `cic.source.assert` csak a cert
  **láncát** ellenőrzi, nem az artifact aláírását — `schemacompile.go:118-131`;
  így CA privát kulcs nem kell)
- A `build_hash` beírása release-folyamatban a megfelelő fájlba

## 7. Amit nem állítunk

- A **teljes** `/v1/schemas/pipeline` utat egy minimál fixture-repón végigmértük
  (7 lépés, HTTP 200) — a CIC-Schemas saját `make test`-jén viszont nem jutottunk
  át (`mk/infra.mk:79` rosszul paraméterezett `docker` hívást állít elő a mi
  környezetünkben). Tehát a lánc működését igazoltuk, egy valódi termelési
  séma-repó teljes buildjét nem.
- Nem vizsgáltuk a cross-környezeti reprodukálhatóságot. A CIC-ben erre van
  rögzített döntés (aláírás-alapú bizalom a `buildHash`-en), és ez a javaslat
  **nem** írja felül.
- Nem néztük meg, van-e a relay repóban másik, általunk nem talált CI-image.
