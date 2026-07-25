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

## Első éles futás — 2026-07-25

**Eredmény: T0 PASS, T1–T6 nem futott le. `build_hash`-t NEM sikerült előállítani.**

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
