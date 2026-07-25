# Relay-alapú fordítás és `build_hash` — teszt-eljárás

Cél: **empirikusan** eldönteni, hogy a relayjel végzett fordítás előállít-e
használható `build_hash`-t, és hogy az ellenőrizhető-e.

Ez az eljárás a `relay-ci-build-audit` job **statikus** megállapításait hivatott
futtatással igazolni vagy megcáfolni. Az audit maga jelezte a korlátját
(`claim-evidence.md`, 14. sor): *„Nem futtattam élesben a pipeline-t… a
következtetés a Go statikus map-literál szemantikájából adódik."* Ez a teszt
zárja be azt a rést.

Harness: [`tools/relay-build-test.sh`](../tools/relay-build-test.sh) — kizárólag
HTTP-n át dolgozik, a CIC-Relay repót **nem érinti** (RO szabály).

---

## Előfeltétel — a relayt el kell indítani, és ez nem triviális

Ez maga is lelet. A forrásból kiolvasva:

| Amit keresnénk | Amit találunk |
|---|---|
| relay szolgáltatás `docker-compose.yml`-ben | **nincs** — a compose `py-builder` / `go-builder` / `rust-builder` / `nats` build-tooling konténereket definiál |
| relay image a gyökér `Dockerfile`-ban | **nincs** — az egy `python:3.11-slim` alapú schema-compiler image |
| `make run` / `make serve` cél | **nincs** — a Makefile-ban csak `build: infra.build ## Build Docker images` |

Tehát a relay indítása ma **kézi lépés**, és nincs olyan konténerizált belépési
pont, ami „kap egy repót + commitot, ad egy `build_hash`-t". Ez az audit **#7-es rése**.

Alapértelmezett port: `:8080` (`cmd/relay/main.go:770`).

### Működő indítási recept (2026-07-25-én kipróbálva)

Lokális Go nincs a gépen; a relay a `golang:1.25.11` imageben fordul, a repo
**read-only** mountolva (nem módosítjuk). A cache-ek a `go-builder` compose-mintáját követik.

```bash
source tools/env.sh
# 1. fordítás — a repo RO, a bináris kifelé megy
docker run --rm \
  -v "$CIC_RELAY_PATH":/git-source:ro \
  -v ~/tmp/cache/CIC-Relay/gomodcache:/go/pkg/mod \
  -v ~/tmp/cache/CIC-Relay/cache:/go/cache \
  -v ~/tmp/cache/CIC-Relay/build:/out \
  -e GOMODCACHE=/go/pkg/mod -e GOCACHE=/go/cache -e GOFLAGS=-mod=readonly \
  -w /git-source golang:1.25.11 \
  go build -buildvcs=false -o /out/relay ./cmd/relay
```

`-buildvcs=false` **kötelező**: RO mounton a VCS-stamping `exit status 128`-cal elhasal.
Mellékhatás: a `CommitHash` / `SourceTreeHash` ldflag-ek üresek maradnak.

```bash
# 2. indítás
printf '[safe]\n\tdirectory = *\n' > ~/tmp/relay-gitconfig
docker run -d --name cic-relay-test --network host \
  -v "$CIC_RELAY_PATH":/git-source:ro \
  -v "$CIC_SCHEMAS_PATH":/src/cic-schemas:ro \
  -v ~/tmp/relay-test-build:/build \
  -v ~/tmp/relay-test-audit:/var/lib/cic-relay \
  -v ~/tmp/relay-gitconfig:/etc/relay-gitconfig:ro \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /usr/bin/docker:/usr/local/bin/docker:ro \
  -v ~/tmp/cache/CIC-Relay/build:/opt/bin:ro \
  -e GIT_CONFIG_GLOBAL=/etc/relay-gitconfig \
  -e CIC_SCHEMA_BUILD_DIR=/build \
  -e CIC_SCHEMA_BUILDER_CONTAINER=cic-schemas-builder \
  -e VAULT_TOKEN="$(cat ~/.vault-token)" -e VAULT_ADDR=http://127.0.0.1:8200 \
  -w /git-source golang:1.25.11 /opt/bin/relay
```

Buktatók, mind kipróbálva:

| Tünet | Ok | Megoldás |
|---|---|---|
| `VAULT_TOKEN not set — ProofTrace recording disabled` | nincs token | `-e VAULT_TOKEN=…`; sikeres esetben `ProofTrace recording enabled`, `vault_mount=transit`, `vault_key=cic-dev-sign-key` |
| `Failed to init audit git recorder … mkdir /var/lib/cic-relay: permission denied` | nem-root user, nem írható út | írható könyvtárat mountolni `/var/lib/cic-relay`-re |
| `git clone … detected dubious ownership` | konténer root, repo más tulajdonosé | `GIT_CONFIG_GLOBAL` egy `[safe] directory = *` fájlra. **A `GIT_CONFIG_COUNT`/`KEY_0`/`VALUE_0` env-forma NEM működött.** |
| `docker exec: executable file not found in $PATH` | a `golang` imageben nincs docker CLI | a hoszt `/usr/bin/docker` bemountolása + docker socket |
| `cic.pipeline.start: build_dir is required` | nincs alapérték | `CIC_SCHEMA_BUILD_DIR` vagy a kérés `build_dir` mezője |
| `cic.pipeline.test: builder_container is required` | nincs alapérték | `CIC_SCHEMA_BUILDER_CONTAINER` vagy a kérés mezője |

A builder konténer külön indul, és a **workdir-jének a klón helyére kell mutatnia**
(a relay `docker exec <builder> make <target>`-et hív `-w` nélkül):

```bash
docker run -d --name cic-schemas-builder \
  -v ~/tmp/relay-test-build:/build -w /build/<build_dir-neve> \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /usr/bin/docker:/usr/local/bin/docker:ro \
  cic-relay-py-builder:latest tail -f /dev/null
```

---

## Az API, amit a teszt használ

Forrásból kiolvasva, nem feltételezve:

**`POST /v1/schemas/pipeline`** — `cmd/relay/pipeline_handler.go:14-22`

```json
{ "schema": "postgresql", "version": "v0.18.0",
  "branch": "postgres/dev", "repo_url": "file:///src/cic-schemas" }
```

Válasz (`pipeline_handler.go:24-28` + `schemacompile.go:290-296`):

```json
{ "artifact": { "artifact": {...}, "build_hash": "...",
                "cic_sign": "...", "cic_signed_ca": "...",
                "verification_root": "..." },
  "proof_trace": { "workflow_id": "...", "source_digest": "...",
                   "chain_hash": "...", "steps": [...] } }
```

**`POST /v1/proof/verify`** — `cmd/relay/main.go:196`. Bemenete a ProofArtifact
JSON; kimenete `{valid, errors[], warnings[]}`. A `VerifyProofArtifact`
(`proof_verify.go:46-53`) **újraszámolja** a `chain_hash`-t a lépésekből.

A futó workflow: `cic.schemas.pipeline` — `start → test → validate → release →
assert → build → sign` (`bootstrap.go:218-226`).

---

## Futtatás

```bash
RELAY_URL=http://127.0.0.1:8080 \
PIPE_REPO_URL=file:///src/cic-schemas \
PIPE_SCHEMA=postgresql \
PIPE_VERSION=v0.18.0 \
PIPE_BRANCH=postgres/dev \
PIPE_BRANCH_B=postgres/other \
  ./tools/relay-build-test.sh
```

`PIPE_BRANCH_B`-nek **tartalmilag különböző** forrást kell adnia — enélkül a T5
(a legfontosabb teszt) nem tud lefutni, és `SKIP`-et ad. **A SKIP nem PASS**;
a harness ezt külön ki is írja.

---

## Mit bizonyít az egyes tesztek

| Teszt | Mit állít | Miért fontos |
|---|---|---|
| **T0** | a relay elérhető (`/healthz`, `/readyz`) | enélkül minden további eredmény értelmezhetetlen; a harness itt megáll |
| **T1** | a pipeline lefut, és van `build_hash`, `verification_root`, `chain_hash` | a happy path egyáltalán működik-e |
| **T2** | `verify(érintetlen artifact)` → `valid=true` | az ellenőrző oldal nem ad hamis negatívot |
| **T3** | `verify(elrontott chain_hash)` → `valid=false` | ha ezt elfogadja, az ellenőrzés **nem köt** semmit |
| **T4** | `verify(elrontott step.output_hash)` → `valid=false` | a lépések tényleg bele vannak kötve a `chain_hash`-be — ez a Merkle-jelleg lényege |
| **T5** | **különböző forrás → különböző `build_hash`** | **ez a döntő teszt** |
| **T6** | azonos bemenet → azonos `build_hash` | determinizmus alapvonal |

### T5 — miért ez a döntő

Ha a `build_hash` **nem változik**, amikor a fordított forrás változik, akkor a
hash nem azt attesztálja, amit lefordítottunk. Ilyenkor CI-célra használhatatlan,
bármilyen szépen is van aláírva.

Az audit statikusan azt találta, hogy pontosan ez a helyzet:
`cmd/relay/main.go:713-715` a `bctx`-et a relay **saját** build-idejű
konstansaiból tölti (`SourceRef: CommitHash`, `SourceTreeDigest: SourceTreeHash`),
és `core/modules/schemacompile/schemacompile.go:245-252` ezt teszi a
`merkle.VerificationManifest.Source`-ba. Ezt a két helyet az orchestrátor
függetlenül újraverifikálta (lásd `jobs/relay-ci-build-audit/review.md`).

**T5 tehát várhatóan FAIL lesz.** Ez nem a teszt hibája — ez a bizonyíték.
Ha viszont T5 PASS-t ad, az azt jelenti, hogy az audit statikus következtetése
téves volt, és **azonnal felül kell vizsgálni** a rés-listát, mielőtt bármilyen
interfész-specet küldünk a relay-csapatnak.

A harness a T5-nél a `verification_root`-ot is kiírja mindkét futásra —
ha az is azonos, az megerősíti, hogy a relay saját build-konstansaiból származik.

---

## Az eredmény értelmezése

| T3 | T4 | T5 | Jelentés |
|---|---|---|---|
| FAIL | – | – | az ellenőrzés nem köt semmit — ez a legsúlyosabb eset |
| PASS | FAIL | – | a `chain_hash` ellenőrzött, de a lépések nincsenek hozzá kötve |
| PASS | PASS | FAIL | az ellenőrzés ép, de a `build_hash` nem forrás-kötött → **az audit igazolva** |
| PASS | PASS | PASS | a lánc forrás-kötött és ellenőrzött → az audit #5-ös rése téves, felülvizsgálandó |

---

## PERDÖNTŐ — a teljes pipeline valódi repóval, 2026-07-25

**A teljes 7 lépéses `/v1/schemas/pipeline` végigment** egy minimál fixture-repón:
`start(clone) → test → validate → release → assert → build → sign`, HTTP 200.

Három futás, ugyanaz a repo, három **különböző commit**:

| Futás | Mi változott | `build_hash` | `source_digest` |
|---|---|---|---|
| **A** | alap | `sha256:0636abb1…7e7b` | `unknown` |
| **C** | **csak a `README.md`** — az artifact változatlan | `sha256:0636abb1…7e7b` | `unknown` |
| **B** | az artifact tartalma | `sha256:f7030f11…5607` | `unknown` |

```
  A == C ?  True   <- két külön commit MEGKÜLÖNBÖZTETHETETLEN
  A != B ?  True   <- a tartalmat viszont követi
```

### Amit ez kimond

**Két különböző repo-állapot bitre azonos `build_hash`-t kap**, ha a lefordított
artifact nem változott. A `source_digest` mind a három futásban `unknown` — pedig
a relay **valóban klónozta** a repót (a clone lépés lefutott, a `make` célok
lefutottak a builder konténerben).

CI-attesztációra ez diszkvalifikáló: **nem bizonyítható vele, hogy melyik
commitból készült a build.** Aki a `build_hash`-t elfogadja bizonyítéknak, az a
tartalomra kap garanciát, a provenance-ra nem.

Ez a mérés a `#1` (nincs commit mező), `#4` (a provenance elveszik a láncon) és
`#5` (a `source_digest` a relay sajátja) réseket **egyszerre és élesben** igazolja,
nem statikus következtetésből.

### A fixture-recept (reprodukálható)

```
fixture-repo/
  Makefile            # test / validate / release — mind csak `echo`
  source/demo.yaml    # a signed assertion (lásd lentebb)
  README.md           # a C futásnál ezt módosítottuk
```

A `source/demo.yaml`-hez nem kell CA privát kulcs: a `cic.source.assert` csak a
cert **láncát** ellenőrzi (`schemacompile.go:118-131`), így a repóban lévő
`output/test_dev_cert.pem` (kiállító: *Embedded Test Root CA*, benne van a
betöltött trust store-ban) megfelel. A `metadata.sign` bármilyen nem-üres string
lehet. A `checksum`-ot a relay hibaüzenete megmondja (`computed="…"`).

Indítás: a relay konténerbe a fixture-repót `-v <fx>:/src/fixture:ro`, a builder
konténer `-w /build/<build_dir>` a klón helyére mutatva, majd
`repo_url=file:///src/fixture`.

---

## A döntő mérés — 2026-07-25, valódi `source_assertion`-nel

**Kérdés:** követi-e a `build_hash` a fordított forrás tartalmát?
**Válasz: IGEN a tartalmat, NEM a provenance-t.**

Aláírt `source_assertion`-t adtunk be (a `cic.source.assert` teljes útja lefutott,
cert-lánc ellenőrizve), majd ugyanazt megismételtük **tartalmilag más** speckel:

| | `build_hash` | `verification_root` | `source_digest` |
|---|---|---|---|
| **A** `{alma:1, korte:"ketto"}` | `sha256:c085049f…3f4c` | `85af5a1f…d8cb` | **`unknown`** |
| **B** `{banan:999, szilva:"harom", extra:true}` | `sha256:04a32b37…b310` | `cb8922e4…d39d` | **`unknown`** |

- ✅ A `build_hash` **és** a `verification_root` is **eltér** → a lánc **tartalom-kötött**.
- ❌ A `source_digest` **mindkét futásnál `unknown`** → a lánc **nincs forrás-revízióhoz horgonyozva**.

### Amit ez pontosan jelent

A relay `build_hash`-e **azt attesztálja, *amit* lefordított** — nem azt, hogy
*honnan* jött. A `source_digest` mező, aminek épp az volna a dolga, hogy a láncot
egy forrás-revízióhoz kösse, a relay **saját** build-konstansaiból töltődik
(`main.go:333-337`); nálunk `unknown`, mert `-buildvcs=false`-szal fordítottunk.

CI-célra ez a különbség dönt:

| Kérdés | Válaszol rá a mai `build_hash`? |
|---|---|
| „Ugyanaz a tartalom lett-e lefordítva?" | ✅ igen |
| „A repo X commit Y állapotából jött-e?" | ❌ nem |

Az audit **#5-ös rése tehát megáll, de pontosítva**: nem az a baj, hogy a
`build_hash` nem követ semmit — hanem hogy a **forrás-provenance** hiányzik
belőle. Ez pontosan az a rés, amit az #1 (nincs commit mező) és a #4
(a `source_ref`/`source_tree_digest` elveszik) ír le.

Súlyosbítja a korábban talált **warning-rés**: a `VerifyProofArtifact` csak üres
`source_digest`-re figyelmeztetne, az `"unknown"` sentinel átcsúszik — tehát az
ellenőrzés **nem is jelzi**, hogy a lánc nincs forráshoz kötve.

### A fixture-recept, ami ezt lehetővé tette

A `cic.source.assert` **csak a cert láncát** ellenőrzi — nem azt, hogy az
artifactot azzal a certtel írták-e alá (`schemacompile.go:118-131`). Ezért
elegendő egy érvényes, trust store-hoz kötött cert; nem kell hozzá a CA privát
kulcsa. A `CIC-Relay/output/test_dev_cert.pem` (kiállító: *Embedded Test Root CA*,
ami benne van a betöltött trust store-ban) megfelel.

Kötelező `metadata` mezők (`schemacompile.go:86-98`): `name`, `version`,
`checksum`, `sign`, `createdBy.certificate`. A `sign` csak **nem-üres** kell
legyen — tartalmilag nincs ellenőrizve. A `checksum` a spec kanonikus JSON-jának
sha256-ja; ha rosszat adsz meg, a relay hibaüzenete **megmondja a helyeset**
(`computed="…"`), tehát egy körrel kideríthető.

---

## Második futás — 2026-07-25, `/v1/schema/compile` úton

**Eredmény: mind a hat teszt PASS. `build_hash` előállt és ellenőrizhető.**

A teljes `/v1/schemas/pipeline` úton nem jutottunk át (lásd lentebb), ezért a
**rövidebb `/v1/schema/compile`** utat használtuk. Az ugyanazt a záró láncot
futtatja — `assert → build → sign` (`bootstrap.go:122-126`) —, csak a
clone/test/validate/release előlépések nélkül. Ez az út `source_assertion`
nélkül **stub módban** fut (`schemacompile.go:46`), így nem kell aláírt artifact.

| Teszt | Eredmény | Bizonyíték |
|---|---|---|
| **T0** preflight | ✅ PASS | `/healthz`, `/readyz` → 200 |
| **T1** `build_hash` előáll | ✅ PASS | `sha256:7b76d3d8…dd91`, `verification_root=dd5a1a85…6113`, `cic_sign=vault:v1:MEQCIC4k…`, trace 3 lépéssel |
| **T2** verify(érintetlen) | ✅ PASS | `valid=true`, nincs error |
| **T3** elrontott `chain_hash` | ✅ PASS | `valid=false` — `chain_hash mismatch: declared=0a4faf… recomputed=8a4faf…` |
| **T4** elrontott `step.output_hash` | ✅ PASS | `valid=false` — a **újraszámolt** lánc eltér: `recomputed=fcb889ca…` |
| **T5** más bemenet → más hash | ✅ PASS | `demo/v1.0.0` → `…dd91`, `teljesen-mas-sema/v9.9.9` → `…5617`; a `verification_root` is eltér |
| **T6** determinizmus | ✅ PASS | ugyanaz a bemenet kétszer → bitre azonos `build_hash` |

**T4 a legfontosabb pozitív eredmény:** egyetlen lépés `output_hash`-ének
elrontása más `chain_hash`-t eredményez. A lépések tehát **ténylegesen bele
vannak kötve** a láncba — ez a Merkle-jelleg működik, nem csak deklarált.

### Hogyan árnyalja ez az audit #5-ös megállapítását

Az audit azt állította, hogy a `build_hash`/`verification_root` a relay **saját**
build-adataira épül. A mérés ezt **pontosítja, nem cáfolja**:

- A `build_hash` és a `verification_root` **változik a bemenettel** (T5) — tehát
  nem *kizárólag* a relay konstansai határozzák meg.
- Ugyanakkor a ProofTrace `source_digest` mezője a futásainkban végig
  **`"unknown"`** volt. Ez pontosan a `main.go:333-337` fallback-je: a relay a
  *saját* `SourceTreeHash`/`CommitHash` értékét tenné ide, ami nálunk üres, mert
  `-buildvcs=false`-szal fordítottunk.

Vagyis a manifest **kever**: a tartalmi rész a bemeneti artifactból jön, a
**forrás-provenance rész viszont a relay sajátja**. Az audit mechanizmus-leírása
helytálló; a megfogalmazása („a build_hash a relay saját adataira mutat")
túl tág volt.

**Amit ez a futás továbbra sem dönt el:** hogy a `build_hash` követi-e egy
**külső repo** tartalmát. Ezen az úton nincs repo egyáltalán. A CI-szempontból
lényeges kérdés csak a teljes pipeline-on válaszolható meg.

### Új lelet — a `source_digest` warning nem sül el

A `VerifyProofArtifact` figyelmeztet, ha a `source_digest` **üres**
(`proof_verify.go`: *„chain is not anchored to a source revision"*). De a mi
futásainkban az érték `"unknown"` volt — ami nem üres, tehát **a figyelmeztetés
nem sült el**, `warnings=None` jött vissza, miközben a lánc valóban nincs
forráshoz horgonyozva.

Ez ellenőrzési rés: a `"unknown"` sentinel átcsúszik a nem-üres teszten.

### A harness saját hibája, javítva

A `/v1/proof/verify` **`{"proof_artifact": {…}}` burkolót vár**
(`proof_verify_handler.go:54-59`), nem a csupasz trace-t. Az első verzióm a
trace-t küldte közvetlenül, és `400 missing_fields`-et kapott. Javítva; a T3/T4
tamper-lépések is a burkolón belül módosítanak.

### Vault — melyik kulcs

A `~/.vault-token` (`root`) **érvénytelen** ehhez a Vaulthoz. A működő token:
`$XDG_RUNTIME_DIR/vault/sign-token`, a Vault pedig **`https://127.0.0.1:18200`**
TLS-sel (`server.crt` ugyanott), nem a 8200-on. A token a `sign-policy`-val
**`cic-my-sign-key`-re** tud aláírni; a relay alapértelmezett
`cic-dev-sign-key`-ére **403**. Ezért kell `CIC_VAULT_KEY=cic-my-sign-key`.

---

## Első futás — 2026-07-25, teljes pipeline úton

**Eredmény: T0 PASS, T1–T6 nem futott le ezen az úton. `build_hash` nem állt elő.**

Ameddig eljutottunk, lépésről lépésre:

| Lépés | Eredmény |
|---|---|
| relay fordítás konténerben, RO forrással | ✅ 16.3 MB bináris |
| relay indul, `✅ Central relay API started on :8080` | ✅ |
| **T0** — `/healthz`, `/readyz` | ✅ **PASS**, mindkettő 200 |
| ProofTrace recording Vaulttal | ✅ engedélyezve (`transit` / `cic-dev-sign-key`) |
| `cic.pipeline.start` — git clone a megadott `repo_url`-ről | ✅ **lefutott** |
| `cic.pipeline.test` — `docker exec <builder> make test` | ⚠️ **elindult és futott**, de a CIC-Schemas saját `make test`-je hasalt el |
| `validate` → `release` → `assert` → `build` → `sign` | ❌ nem jutottunk el idáig |
| **T1–T6** | ❌ nem futott — nincs `build_hash`, nincs `proof_trace` |

Az utolsó hiba **nem a relayben** van:

```
cic.pipeline.test: make test exit 2:
  --- Running pytest for the compiler infrastructure ---
  unknown shorthand flag: 'm' in -m
  make: *** [mk/infra.mk:79: infra.test] Error 125
```

A CIC-Schemas `mk/infra.mk:79` targetje ebben a környezetben rosszul paraméterezett
`docker` hívást állít elő (valószínűleg egy Makefile-változó `python` helyett
`docker`-re oldódik fel). Ez a **cél-repó build-konfigurációja**, nem a relay.

### Amit ez a futás mégis bizonyít

Két dolgot, amit eddig csak statikusan tudtunk:

1. **A relay tényleg klónoz** egy neki megadott `repo_url`-t (`cic.pipeline.start`
   lefutott, a hiba utána jött).
2. **A relay tényleg `docker exec <builder> make <target>`-et futtat** — a hiba
   szövege maga a `make test` kimenete, tehát a hívás megtörtént. Ez pontosan az a
   mechanizmus, amit az eredeti kérés leírt: Makefile-célok egyenként, konténerben,
   lépésenként rögzített eredménnyel (`schemapipeline.go:223` — a modul
   `stdout_digest`-et és `command_digest`-et is számol a lépéshez).

### Ami továbbra is nyitva van

**A döntő kérdést (T5) ez a futás nem válaszolta meg.** Nincs `build_hash`, tehát
nem tudjuk, hogy forrás-kötött-e. Az audit statikus megállapítása
(`main.go:713-715` → `schemacompile.go:245-252`) továbbra is csak statikus.

A továbblépéshez a CIC-Schemas `make test` / `make validate` targetjeit kell
működésre bírni a builder konténerben — vagy egy egyszerűbb cél-repót választani,
aminek a Makefile-ja beágyazott docker nélkül fut le.

---

## Amit ez az eljárás NEM fed le

Őszintén, hogy ne lehessen többet olvasni ki belőle, mint amennyit ér:
- **Nem teszteli a commit-pinnelést** — mert nincs mit tesztelni: a
  `PipelineRequest`-ben nincs `commit` mező (audit #1), a klónozás pedig
  `--branch --depth 1` (`schemapipeline.go:129`, audit #8). A T5 ezért
  *branch*-eket állít szembe, nem commitokat.
- **Nem teszteli a `ci.build` modult** — nem elérhető: regisztrálva van
  (`bootstrap.go:55,64`), de egyik workflow `Steps[]`-jében sincs (audit #3).
  HTTP-ről nem hívható, tehát fekete dobozként nem tesztelhető.
- **Nem méri a reprodukálhatóságot környezetek között.** A T6 ugyanabban a
  relay-példányban ismétel. A cross-env reprodukció külön kérdés, és a CIC-ben
  van rá egy rögzített döntés (aláírás-alapú bizalom a `buildHash`-en, nem
  cross-env repro) — azt ez a teszt nem vizsgálja felül.
- **Nem ellenőrzi az aláírást** (`cic_sign`, `cic_signed_ca`). Külön eljárás kell rá.

---

## Következő lépés

1. Relayt elindítani (kézi lépés, lásd az előfeltétel szakaszt)
2. `./tools/relay-build-test.sh` futtatása valós `PIPE_*` értékekkel
3. Az eredményt beírni ide, a „Amit ez az eljárás NEM fed le" első pontja helyére
4. **Csak ezután** interfész-spec a relay-csapat felé — a T5 eredménye dönti el,
   hogy a spec mit állíthat ténynek
