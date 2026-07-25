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

Tehát ma a relay indítása **kézi lépés** (`go run ./cmd/relay` vagy egy lefordított
bináris), és nincs olyan konténerizált belépési pont, ami „kap egy repót +
commitot, ad egy `build_hash`-t". Ez az audit **#7-es rése**, és a teszt-eljárás
első lépésénél azonnal szembejön.

Alapértelmezett port: `:8080` (`cmd/relay/main.go:770`).

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

## Amit ez az eljárás NEM fed le

Őszintén, hogy ne lehessen többet olvasni ki belőle, mint amennyit ér:

- **Nem futott le még egyszer sem.** Az itt leírt kérés/válasz alakok forrásból
  vannak kiolvasva (`file:sor` hivatkozásokkal), de a tényleges futás
  visszaigazolása hiányzik. Az első éles futás után ezt a szakaszt frissíteni kell.
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
