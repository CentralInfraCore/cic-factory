# relay-ci-build-audit — Q4: a rés

Cél (orchestrátori döntés, nem felülvizsgálva): „repo URL + commit id be →
`build_hash` ki", Docker image formában. Az alábbi táblázat azt írja le, mi van
most a kódban, és mi hiányzik ehhez — **megoldás nélkül**, ahogy a spec kéri.

| # | Rés | Mi van most (fájl:sor) | Mi kellene | Réteg |
|---|---|---|---|---|
| 1 | Nincs olyan bemeneti mező egyik bekötött route-on sem, ami egy **konkrét commit SHA-t** fogadna | `pipeline_handler.go:15-22` (`PipelineRequest`: `schema`,`version`,`branch`,`repo_url`,`build_dir`,`builder_container` — nincs `commit`) | Egy `commit`/`ref` mező, amit a `git clone` után `git checkout <commit>` vagy közvetlen `git clone` + `git checkout` pinnel, nem csak branch HEAD | API kontraktus (`pipeline_handler.go`) + `schemapipeline.go:129` clone logika |
| 2 | A `/v1/schemas/pipeline` **séma-specifikus** (CIC-Schemas repo-struktúrát feltételez), nem generikus „bármilyen repo" CI | `schemapipeline.go:307` (`<build_dir>/source/<schema>.yaml` fix útvonal a release lépésben); `pipeline_handler.go:64-67` (`schema`,`version`,`branch`,`repo_url` mind kötelező) | Egy repo-agnosztikus workflow/route, ami nem tételez fel `source/<schema>.yaml` struktúrát, és nem kér `schema`/`version` mezőt | Workflow deklaráció (bootstrap.go) + route handler |
| 3 | A `ci.build` modul (fix `make <target>`) **nincs bekötve egyik workflow-ba sem** | bootstrap.go:117-134 (`cic.schema.compile` Steps), bootstrap.go:213-234 (`cic.schemas.pipeline` Steps) — egyikben sincs `ci.build@1.0` | Egy workflow-lépés, ami `ci.build@1.0.build(...)`-ot hívja, VAGY a `cic.pipeline.test/validate/release` triót helyettesítő/kiegészítő általános build-lépés | Workflow wiring (bootstrap.go) |
| 4 | A klónozott külső repó `source_ref`/`source_tree_digest`-je **elvész** a pipeline-ban, mielőtt a `build_hash`/`verification_root` kiszámolódna | schemacompile.go:146-154 (`assertSourceImpl` return map nem tartalmazza ezeket a kulcsokat) | Az `assert` lépés vigye tovább (vagy a `sign` lépés olvassa vissza) a `source_ref`/`source_tree_digest`-et a bemeneti map-ből, ne csak a szerver-indításkori `bctx`-ből | `schemacompile.go` (mindkét érintett függvény: `assertSourceImpl`, `newSignArtifactResult`) |
| 5 | A `build_hash` végig a relay **saját** build-time forrás-hash-éhez van kötve, nem a vizsgált külső repó commitjához | `main.go:713-715` (`bctx.SourceRef = CommitHash`, `bctx.SourceTreeDigest = SourceTreeHash` — relay saját binárisáé); `schemacompile.go:247-250` (ezt használja a `verification_root`-ban) | A `bctx` (vagy egy külön mezőkészlet) legyen **per-kérés** feltölthető a klónozott repó `source_ref`/`source_tree_digest`-jével, ne csak szerver-indításkor rögzített, statikus érték legyen | `schemacompile.go` + a `bctx` átadási lánc (`bootstrap.go:33`, `main.go:713`) |
| 6 | Nincs "repo URL + commit id → build_hash" **egyetlen válasz-mező** — a `PipelineResponse.Artifact` a `signed_artifact` map-et adja vissza, aminek `build_hash` mezője a fentiek miatt nem a kért repóra vonatkozik | pipeline_handler.go:113-116 (`Artifact: resp.Results["signed_artifact"]`); schemacompile.go:290-296 (`signed_artifact` mezői) | Egy válasz-kontraktus, ahol a `build_hash` mező dokumentáltan és bizonyíthatóan a kérésben kapott repo+commit tartalmára vonatkozik, nem a relay saját build-jére | API válasz kontraktus + a 4-5. sorban leírt belső vezetékezés |
| 7 | Nincs Docker image / CI belépési pont, ami "kap egy git repót és egy commit id-t" paraméterként és lefuttatja a teljes CI-t egy konténerben | `Dockerfile` (repo gyökér) Python-alapú, `pip-tools`/schema-compiler tooling image — nem CI-orchestrátor image; `docker-compose.yml` `py-builder`/`go-builder`-szerű long-running exec-célú konténereket definiál, nem egyszeri "adj repót+commitot, kapj build_hash-t" belépési pontot | Egy dedikált CI-belépési image/entrypoint, ami a fenti (1)-(6) réseket lefedő workflow-t futtatja egyetlen paraméterezett hívásban | Deployment/konténer réteg (Dockerfile, docker-compose.yml) |
| 8 | A `cic.pipeline.start` `git clone --branch <branch> --depth 1` **shallow clone-t** használ — ha a kért commit nem a branch HEAD-je, ez a forma nem éri el | `schemapipeline.go:129` | Teljes (vagy legalább a cél commitig mélyített) klónozás + explicit `git checkout <commit>`, ha a cél nem feltétlenül a branch HEAD-je | `schemapipeline.go` clone logika |
| 9 | `cic.build` (a natív modul, ami a legközelebb áll egy generikus "fuss le és adj digestet" lépéshez) nem kezel git-et vagy konténer-izolációt egyáltalán | `cibuild.go` (teljes fájl — nincs `git`, nincs `docker`, nincs `isolation.*` hívás) | Ha `ci.build`-et akarjuk a bekötendő láncba emelni, kell elé egy forrás-előkészítő lépés (clone/checkout) és/vagy izolációs réteg, amit ma sem `cibuild.go`, sem a hozzá kötött workflow nem ad | `core/modules/cibuild/cibuild.go` + workflow wiring |

## Összegzés

A rés nem egyetlen hiányzó komponens, hanem egy **megszakadt lánc**: a
git-clone képesség létezik (`schemapipeline.go:129`), de (a) branch-hez van
kötve, nem commit id-hez (rés #1, #8), (b) csak a CIC-Schemas séma-specifikus
pipeline-ra van bekötve, nem egy generikus repo-CI-ra (rés #2), (c) az általa
számított forrás-digest információ elvész, mire a `build_hash` kiszámolódik
(rés #4), és (d) a végső `build_hash`/`verification_root` helyette a relay
saját, szerver-indításkor rögzített build-adataira mutat (rés #5). A `ci.build`
natív modul — ami névre a legközelebb áll a kívánt funkcióhoz — regisztrálva
van, de egyetlen workflow-ba sincs bekötve (rés #3), és önmagában nem ismer
git-et vagy commit id-t (rés #9). Konténerizált, paraméterezhető CI-belépési
pont szinten sincs (rés #7).
