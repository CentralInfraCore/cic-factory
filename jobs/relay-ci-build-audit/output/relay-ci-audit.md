# relay-ci-build-audit — Q1–Q3 válaszok

## KB boot sequence

`mcp__cic-relay__kb_status`: `kb_loaded: true`, 55934 chunk, 3506 node, adatkönyvtár
`/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/cic-relay-mcp/kb_data/pkl/pkl`.

A specben kötelezőnek jelölt `kb_focus` chunk-ok egyike sem oldható fel:

```
get_chunk("c781") -> {"result": null}
get_chunk("c912") -> {"result": null}
get_chunk("c927") -> {"result": null}
get_chunk("c365") -> {"result": null}
get_node("c781")  -> {"result": null}
search_nodes("ci.build cibuild source digest build_hash") -> {"result": []}
```

**Ez az outputban rögzített tény: a kb_focus 4 chunk-id-ja üres/nem létezik ebben a
KB snapshotban.** Nem találtam ki tartalmat — a Q1–Q4 válaszok kizárólag forráskód
alapján készültek, ahogy a job spec ilyen esetre előírja.

`deadcode` nem elérhető (`deadcode: command not found`) — minden `implemented`
minősítés grep-alapú call-site bizonyítékkal van alátámasztva, ahogy a spec kéri.

---

## Q1 — Mit csinál ténylegesen a `ci.build` modul?

Forrás: `core/modules/cibuild/cibuild.go` (111 sor), `core/modules/cibuild/cibuild.yaml` (48 sor).

### Bemenet (cibuild.go:19-23)

```go
type Input struct {
    BuildTarget    string `json:"build_target"`    // working directory for make (optional)
    MakeTarget     string `json:"make_target"`     // make target to run (default: "build")
    ArtifactOutput string `json:"artifact_output"` // path to the produced artifact (required)
}
```

- `build_target` — opcionális, a `make` munkakönyvtára (`cmd.Dir`)
- `make_target` — opcionális, alapértelmezés `"build"` (cibuild.go:44-47)
- `artifact_output` — **kötelező**, a `parseInput` hibát dob, ha üres (cibuild.go:107-109)

Nincs `repo_url`, nincs `commit`/`branch` mező. A modul input-sémája **nem ismer
külső repót vagy commit id-t** — csak egy már létező lokális könyvtárat és egy
make targetet.

### Kimenet (cibuild.go:26-30)

```go
type Output struct {
    ArtifactPath   string `json:"artifact_path"`
    ArtifactDigest string `json:"artifact_digest"`
    ExitCode       int    `json:"exit_code"`
}
```

- `artifact_digest` = `sha256(fájltartalom)` az `ArtifactOutput` útvonalon (cibuild.go:69-78, 82-89)
- **nincs `build_hash` mező** ebben a modulban — a `build_hash` elnevezés máshol,
  a `cic.artifact.sign` modulban jelenik meg (lásd Q2, `build_hash = sha256(raw_artifact)`,
  `schemacompile.go:238-239`)

### Rögzített lépéssor vagy tetszőleges parancs?

Rögzített, egyetlen lépés: `exec.CommandContext(buildCtx, "make", target)` (cibuild.go:52).
`target` a `make_target` inputból jön, de csak a `make` **céljaként** — a
`make`-en kívül tetszőleges shell parancs nem futtatható ezen a modulon keresztül.
5 perces timeout (`buildTimeout = 5 * time.Minute`, cibuild.go:33, 49).

### Bemeneti hash / kimeneti hash honnan-hova

- **Nincs bemeneti hash-kezelés.** A modul nem fogad és nem ellenőriz forrás-digestet.
- Kimeneti hash: az `ArtifactOutput` fájl tartalmának SHA-256-a, a modul saját
  `Output.ArtifactDigest` mezőjébe kerül (cibuild.go:74-78). Ez a `Output` objektum
  a hívó felé megy vissza (cabinet `NativeFunc` return érték) — hogy ebből mi
  kerül be a végleges `ProofArtifact`-ba, az attól függ, hívja-e valamelyik workflow
  (lásd Q2 — **nem hívja**).

### Konténer- vagy izoláció-kezelés

**Nincs.** A `cmd.Dir` beállításon kívül (cibuild.go:53-55) semmilyen sandbox,
konténer, chroot vagy más izoláció nincs a `cibuild.go`-ban — a `make` parancs
közvetlenül a relay host-folyamat kontextusában fut (`exec.CommandContext`,
nincs `docker`, nincs `isolation.*` hívás).

Megjegyzés (elhatárolás): a **schemapipeline** csomag (`cic.pipeline.test`,
`cic.pipeline.validate`, `cic.pipeline.release`, lásd Q2) `docker exec <builder_container> make ...`
formában **fut konténerben** — de ez egy másik modul-készlet, nem a `ci.build`.
A `ci.build` (cibuild.go) önmagában izoláció nélküli host-futtatás.

### Claim-evidence — Q1

| Állítás | Bizonyíték |
|---|---|
| `ci.build` fix `make <target>` parancsot futtat, nem tetszőlegeset | cibuild.go:52 `exec.CommandContext(buildCtx, "make", target)` |
| Nincs bemeneti hash-fogadás | cibuild.go:19-23 (Input struct-ban nincs digest mező) |
| Kimeneti digest = `sha256(artifact_output fájl)` | cibuild.go:69-78, 82-89 |
| Nincs git/konténer-kezelés a modulban | `grep -n "exec\.\|docker\|git " core/modules/cibuild/cibuild.go` → csak `os/exec` import és az egyetlen `make` hívás (cibuild.go:12, 52) |

---

## Q2 — Meddig jut el a bekötött pipeline út?

### Regisztráció (bekötés, még nem elérési út)

`cmd/relay/bootstrap.go:53-66` regisztrálja a `ci.build@1.0` modult (`ciBuildFuncs["build"] = cibuild.Execute`,
bootstrap.go:55) a cabinetbe, `svc.PutModule(ciBuildModule)` hívással (bootstrap.go:64).
Ez **regisztráció**, nem elérési út — a spec tiltott rövidítése szerint ez önmagában
nem `implemented`.

### Workflow-k, amik ténylegesen HTTP route-hoz kötve vannak

`cmd/relay/main.go:191-199` (`newMux`):

```
mux.HandleFunc("/", s.rootHandler)
mux.HandleFunc("/set", s.setHandler)
mux.HandleFunc("/v1/schema/compile", s.compileHandler)
mux.HandleFunc("/v1/schemas/pipeline", s.pipelineHandler)   // main.go:195
mux.HandleFunc("/v1/proof/verify", s.proofVerifyHandler)
```

Két releváns workflow van regisztrálva a bootstrap-ban:

1. **`cic.schema.compile`** (bootstrap.go:117-134) — a `/v1/schema/compile` route-hoz kötve
   (`compile_handler.go:28`, `WorkflowID: "cic.schema.compile@1.0"` — lásd compile_handler.go teljes
   forrása a `Setx`/`Set` hívásig). Lépések (bootstrap.go:122-126):
   ```
   cic.source.assert@1.0.assert(input) -> assert_result
   cic.schema.build@1.0.build(assert_result) -> artifact
   cic.artifact.sign@1.0.sign(artifact) -> signed_artifact
   ```
   Ez **nem fogad repót/commitot** — a kliens egy már kész `source_assertion` YAML-t küld be.

2. **`cic.schemas.pipeline`** (bootstrap.go:213-234) — a `/v1/schemas/pipeline` route-hoz kötve
   (`pipeline_handler.go:31,93`, `WorkflowID: "cic.schemas.pipeline@1.0"`). Lépések (bootstrap.go:218-226):
   ```
   cic.pipeline.start@1.0.start(input) -> start_result
   cic.pipeline.test@1.0.test(start_result) -> test_result
   cic.pipeline.validate@1.0.validate(test_result) -> validate_result
   cic.pipeline.release@1.0.release(validate_result) -> release_result
   cic.source.assert@1.0.assert(release_result) -> assert_result
   cic.schema.build@1.0.build(assert_result) -> artifact
   cic.artifact.sign@1.0.sign(artifact) -> signed_artifact
   ```
   Ez **séma-specifikus**, nem általános repo-CI út: kötelező mezők `schema`, `version`,
   `branch`, `repo_url` (pipeline_handler.go:15-22, 64-67), és a `cic.pipeline.release`
   lépés kifejezetten `<build_dir>/source/<schema>.yaml`-t olvas vissza (schemapipeline.go:307)
   — ez a CIC-Schemas repo felépítését feltételezi, nem tetszőleges repót.

**A `ci.build@1.0.build` egyik workflow `Steps[]` tömbjében sem szerepel.**

```
grep -rn "ci\.build@1\.0" --include="*.go" | grep -v "_test.go"
→ (nincs találat a bootstrap.go regisztrációs kommenteken kívül)

grep -rn "cibuild\.Execute" --include="*.go"
→ cmd/relay/bootstrap.go:55:	ciBuildFuncs["build"] = cibuild.Execute
   (egyetlen találat — csak a regisztráció, hívó nincs)
```

### `steps[]` egy tényleges `cic.schemas.pipeline` futásnál (a kódból levezetve)

1. **start** (schemapipeline.go:89-184): `git clone --branch <branch> --depth 1 <repo_url> <build_dir>`
   (schemapipeline.go:129), majd `git rev-parse HEAD` a `build_dir`-ben (schemapipeline.go:138) →
   `source_ref`, `source_tree_digest` (saját tree-hash számítás, schemapipeline.go:148, 356-406),
   opcionális `docker inspect --format {{.Image}} <builder_container>` → `builder_image_digest`
   (schemapipeline.go:160-164)
2. **test** (schemapipeline.go:190-194, 208-251): `docker exec <builder_container> make test`
3. **validate** (schemapipeline.go:200-204, 208-251): `docker exec <builder_container> make validate`
4. **release** (schemapipeline.go:259-337): `docker exec <builder_container> make release VERSION=<version>`,
   majd `<build_dir>/source/<schema>.yaml` beolvasása → `source_assertion` (a nyers YAML string)
5. **assert** (schemacompile.go:61-155, `assertSourceImpl`): metadata validáció,
   checksum kereszt-ellenőrzés, opcionális X.509 lánc-ellenőrzés
6. **build** (schemacompile.go:161-196, `BuildSchema`): a `raw_yaml`-t átteszi `raw_artifact`-ba
7. **sign** (schemacompile.go:228-297, `newSignArtifactResult`): `build_hash = sha256(raw_artifact)`,
   opcionális Vault-aláírás, `verification_root` Merkle-gyökér

### Claim-evidence — Q2

| Állítás | Bizonyíték |
|---|---|
| `/v1/schemas/pipeline` → `cic.schemas.pipeline@1.0` workflow | pipeline_handler.go:93 `WorkflowID: "cic.schemas.pipeline@1.0"`; main.go:195 route |
| A workflow séma-specifikus, nem generikus repo-CI | pipeline_handler.go:15-22 (`Schema`,`Version`,`Branch`,`RepoURL` kötelező mezők), 64-67; schemapipeline.go:307 (`source/<schema>.yaml` fix útvonal) |
| `ci.build@1.0` egyik bekötött workflow-ban sincs meghívva | bootstrap.go:117-134, 213-234 (mindkét `Steps[]` teljes tartalma idézve fent) — `ci.build` egyikben sem szerepel |
| `cibuild.Execute` sehonnan nem hívódik production kódból a regisztráción kívül | `grep -rn "cibuild\.Execute" --include="*.go"` → 1 találat, bootstrap.go:55 |

**Minősítés: `ci.build` modul = scaffold.** Regisztrálva van a cabinetbe
(bootstrap.go:53-66), de nincs workflow, ami hívja, tehát nincs HTTP route, amin
keresztül egy kérés valaha eljutna a `cibuild.Execute`-hoz. A megkerülés helye:
egyszerűen hiányzik egy `"ci.build@1.0.build(...)"` sor mindkét `Steps[]` tömbből.

---

## Q3 — Tud-e a relay idegen repót + commit id-t fogadni?

Ez a kérdés két, egymástól független mechanizmust érint, amit a job spec nem
különböztet meg élesen — az audit során ez lett a legfontosabb felismerés.

### 3a. A top-level `SourceDigest` (ProofTrace/ChainHash anchor) — ez a relay SAJÁT forrása, nem a külső repóé

`pipeline_handler.go:87-90`:

```go
sourceDigest := SourceTreeHash
if sourceDigest == "unknown" {
    sourceDigest = CommitHash
}
```

`main.go:333-339` (a generikus `/set` route-on ugyanez a minta):

```go
if payload.SourceDigest == "" {
    if SourceTreeHash != "unknown" {
        payload.SourceDigest = SourceTreeHash
    } else {
        payload.SourceDigest = CommitHash
    }
}
```

`SourceTreeHash` és `CommitHash` **package-level var**-ok (main.go:37,39: alapérték `"unknown"`),
amiket build-time `-X main.CommitHash=$(COMMIT)` / `-X main.SourceTreeHash=$(shell go run ./tools/sourcehash .)`
ldflag-ek töltenek fel (main.go:31,33 kommentek) — **a relay saját forrásfájára**, nem a
kérésben érkező `repo_url`/`branch`-re. Ez a `ProofArtifact.SourceDigest` mezőbe kerül
(proof_verify.go:14,150) és a `ChainHash` számításába (proof_verify.go:81:
`cabinet.ComputeChainHashV1(a.WorkflowID, a.SourceDigest, steps)`).

**A `pkg/sourcedigest.ComputeTreeHash` egyetlen hívási helye:**

```
grep -rn "ComputeTreeHash" --include="*.go" | grep -v "_test.go"
→ tools/sourcehash/main.go:26: hash, err := sourcedigest.ComputeTreeHash(root, nil)
```

Ez egy **CLI eszköz**, amit a build/release Makefile hív meg build-időben (ld. a
fenti ldflag-kommentet) — **nem a relay szerver runtime-jában fut**, nem egy
HTTP kérésre válaszul. Tehát: a `source_digest`, ami a `ProofArtifact`-ba és a
`chain_hash`-be kerül, **mindig a relay saját build-time forrásfa-hash-e**, sosem
a kérésben megadott külső repóé.

### 3b. A `cic.pipeline.start` lépés — ITT VAN git-clone, de az eredménye elvész

`schemapipeline.go:129`: `git clone --branch <branch> --depth 1 <repoURL> <buildDir>` —
ez **valódi git-művelet production kódban**, ami a kérésben kapott `repo_url` és
`branch` mezőket használja (schemapipeline.go:95-96, 129). `git rev-parse HEAD`
(schemapipeline.go:138) adja a `source_ref`-et, `computeTreeDigest(buildDir)`
(schemapipeline.go:148, 356-406) a `source_tree_digest`-et.

**Fontos pontosítás a specben feltételezettel szemben:** ez az út **branch-et fogad,
nem literál commit id-t** — a `git clone --branch <branch> --depth 1` sekély
klónozás a branch HEAD-jét checkoutolja, a commit SHA csak utólag, a `rev-parse
HEAD`-ből derül ki. Nincs mező, ami egy konkrét commit SHA-ra pinnelné a checkoutot.

**A kritikus rés: ez a `source_ref`/`source_tree_digest` sosem jut el a végleges
`build_hash`-ig vagy `verification_root`-ig.**

1. `assertSourceImpl` (schemacompile.go:61-155) a `release_result`-ot dolgozza fel,
   de a visszatérési `map` **explicit mezőlista**, nem a bemenet másolata
   (schemacompile.go:146-154):
   ```go
   return map[string]interface{}{
       "asserted":       true,
       "policy_version": "1.0",
       "schema":         assertedName,
       "version":        assertedVersion,
       "metadata":       artifact.Metadata,
       "spec":           artifact.Spec,
       "raw_yaml":       assertionYAML,
   }, nil
   ```
   A bemenetben lévő `source_ref`, `source_tree_digest`, `builder_image_digest`,
   `branch` kulcsok **itt kiesnek** — nincsenek átmásolva (ellentétben a
   `schemapipeline.go`-beli `copyMap` mintával, amit a pipeline lépések maguk
   használnak egymás között).

2. `newSignArtifactResult` (schemacompile.go:228-297) a `verification_root`
   Merkle-manifestjéhez a `Source` mezőket **nem a bemeneti map-ből**, hanem a
   closure-ba zárt, szerver-indításkori `bctx`-ből veszi (schemacompile.go:247-250):
   ```go
   Source: merkle.SourceFields{
       SourceRef:        bctx.SourceRef,
       SourceTreeDigest: bctx.SourceTreeDigest,
   },
   ```
   `bctx` a `main.go:713-715`-ben épül fel, egyszer, szerver-indításkor:
   ```go
   bctx := merkle.BuildContext{
       SourceRef:        CommitHash,
       SourceTreeDigest: SourceTreeHash,
       ...
   }
   ```
   — **ismét a relay saját build-time értékei**, függetlenül attól, milyen
   `repo_url`/`branch` érkezett a kérésben.

Tehát: a `cic.pipeline.start` ténylegesen klónozza és hash-eli a kért külső repót,
de ez az adat egy köztes lépés kimenetében landol, amit a `cic.source.assert`
eldob, és a végső `build_hash`/`verification_root` soha nem hivatkozik rá.

### Claim-evidence — Q3

| Állítás | Státusz | Bizonyíték | Verifikációs módszer |
|---|---|---|---|
| Top-level `SourceDigest` mindig a relay saját build-hash-e, sosem a kérés repójáé | implemented (ez a viselkedés fut) | pipeline_handler.go:87-90; main.go:333-339 | `grep -n "SourceTreeHash\|CommitHash" cmd/relay/main.go` |
| `ComputeTreeHash` csak build-time CLI-ből hívódik, nem runtime-ban | implemented (a hívás módja) | tools/sourcehash/main.go:26 | `grep -rn "ComputeTreeHash" --include="*.go" \| grep -v _test.go` → 1 találat |
| `cic.pipeline.start` valódi `git clone`-t futtat kérésbeli `repo_url`+`branch`-re | implemented | schemapipeline.go:129 | `grep -n "git clone" core/modules/schemapipeline/schemapipeline.go`, hívó: bootstrap.go:219 workflow step |
| A klónozott repó `source_ref`/`source_tree_digest`-je elvész az `assert` lépésben | implemented (kódból levezetve, nem futtatva) | schemacompile.go:146-154 (a return map nem tartalmazza ezeket a kulcsokat) | statikus kódolvasás — a `map[string]interface{}` literál kimerítő |
| `build_hash`/`verification_root` a relay saját `bctx`-ét használja, nem a klónozott repóét | implemented | schemacompile.go:247-250, main.go:713-715 | `grep -n "bctx\." core/modules/schemacompile/schemacompile.go` |
| Nincs mező, ami konkrét commit SHA-ra pinnelné a checkoutot (csak branch) | implemented | schemapipeline.go:95-96,129 (`branch` mező, `--branch` flag, nincs `commit`/`sha` paraméter) | `grep -n "commit\|\bsha\b" core/modules/schemapipeline/schemapipeline.go` → nincs találat ilyen mezőre |

**Kockázat:** nem futtattam ténylegesen a `/v1/schemas/pipeline` endpointot (a job
read-only audit, nem futtatási teszt) — a fenti lánc kizárólag statikus
kódolvasásból van levezetve. A `docker exec`/`git clone` tényleges futási
viselkedését (pl. hálózati hiba, timeout) nem ellenőriztem élesben. Az `assert`
lépés mezőkiesése determinisztikusan következik a Go kódból (fix map literál),
ez nem futásfüggő bizonytalanság.
