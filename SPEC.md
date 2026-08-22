# SPEC — a factory működési modellje

Ez a dokumentum a `cic-factory-core` **terméke**: az a konvenció, amit a
`tools/` és a `.claude/commands/` megvalósít. Aki a core-ra épít, ezt olvassa.

A CIC-specifikus használat — ökoszisztéma-térkép, repo path-ok, MCP szerver,
felülvizsgált döntések — nem itt él, hanem a
[`cic-factory`](https://github.com/CentralInfraCore/cic-factory) `CLAUDE.md`-jében.
Az a kérdés, hogy *hogyan használja ezt a CIC*; ez a dokumentum arra felel, hogy
*mit tud a gyár általánosan*.

---

## Szerepek

| Szereplő | Hol él | Mit csinál |
|---|---|---|
| Orchestrátor | a live munkakönyvtár | job spec létrehozás, review, merge döntés |
| Agent | `jobs/<job-id>/workspace/<repo>/` (klón) | klónban dolgozik, feature branch-re commitol és pushol |

Az agent **nem** dolgozik a live munkakönyvtárban.

---

## Job lifecycle

```
orchestrátor: input.md + meta.yaml → commit main → push          [pending]
run-job.sh:   spec-kapu → running commit → workspace klón → feature branch
agent:        olvas jobs/<job-id>/ → ír output/ → commitol + pushol feature/<job-id>
run-job.sh:   agent exit 0 → awaiting_review                     [NEM done]
orchestrátor: close-job.sh (output-kapu + review.md) → done → merge main
```

Az állapotgép:

```
pending → running → awaiting_review → done
                 \→ error
```

### `agent_done` ≠ `done`

Az agent exit 0-ja egy állítás **az agentről**: befejezte. A `done` egy állítás
**a jobról**: a kimenete elfogadható. A kettő különböző dolog, két külön
állapottal és két külön jogosultsággal.

Az `awaiting_review → done` átmenetet kizárólag a `close-job.sh` végzi, és csak
akkor, ha az output-kapu GO-t adott és a `review.md` létezik. A `run-job.sh`
egyiket sem teszi, tehát nincs mire alapoznia — ezért gépileg sem tud `done`-t
írni.

### Lease

A `running` állapot commitolva és pusholva van, mielőtt az agent elindul. Ha a
wrapper ezután meghal anélkül, hogy javítaná, a remote egy nem futó jobot
hirdetne. A `run-job.sh` ezért a `running` committal együtt kiír egy határidőt
(`lease_expires`), amiből **a halott folyamat közreműködése nélkül** eldönthető,
hogy egy job elakadt-e. A `check-stale-jobs.sh` ezt olvassa.

Határidő és nem heartbeat: a heartbeatet olyasminek kellene folyamatosan írnia,
ami már halott lehet.

---

## Git a bizalom forrása

Az aláírt commit maga az igazolás (`commit-msg` hook). Az agent a klónból
commitol és pushol a feature branch-re — az review artifact, nem véglegesítés.
Push a `main`-re kizárólag az orchestrátor joga.

**Az orchestrátori review is bizonyítékot termel.** Minden réteg artifactot hagy
(aláírt commit, claim-evidence tábla, reachability output, headSha) — kivéve
régen a review-t, ami egy chat-üzenet volt: aláíratlan, nem reprodukálható, a
session végén elveszett. Ezért kötelező a `jobs/<job-id>/review.md`.

Amihez nem tudsz verifikációs módszert írni, az a „nem igazolt" sorba megy.

---

## Job struktúra

```
jobs/
  index.yaml                  ← auto-generált állapottérkép (tools/update-index.sh)
  .schema/meta.yaml           ← a meta.yaml sémája
  <job-id>/
    input.md                  ← agent prompt (git-tracked)
    meta.yaml                 ← lifecycle + usage (git-tracked)
    review.md                 ← orchestrátori review artifact (kötelező lezárás előtt)
    ref/                      ← referencia anyagok (opcionális, git-tracked)
    output/                   ← az agent leszállítandói
    workspace/                ← gitignored; az agent klónjai élnek itt
```

### meta.yaml

**A mezők forrása [`jobs/.schema/meta.schema.json`](jobs/.schema/meta.schema.json)**
— gépi séma, nem próza. A [`jobs/.schema/meta.yaml`](jobs/.schema/meta.yaml) a
kommentelt példa, és a kapu ellenőrzi, hogy a kulcsai egyeznek a sémáéval.

Ez a dokumentum szándékosan nem sorolja fel őket. Amikor felsorolta, elcsúszott:
a `lease_expires`, a `spec_gate` és a `usage` bekerült a sémába, és a másolat
hallgatott róluk. Egy séma, amit két helyen írunk le, egy helyen elavul — a
kapu ezért ellenőrzi, hogy egyetlen dokumentum se definiálja újra.

A séma **elutasítja** az elgépelt mezőnevet, az érvénytelen `status`- vagy
`spec_gate`-értéket, az üres `agent.model`-t és a hiányzó kötelező blokkot. Egy
job metája a `validate-spec.sh` K10-én keresztül esik át rajta.

### Sub-job lifecycle

Az agent a klónjában hozza létre a sub-job speceket:

```
workspace/<repo>/jobs/<sub-job-id>/input.md + meta.yaml
```

Ezek a feature branch-re kerülnek. Merge után az orchestrátor a live
`jobs/<sub-job-id>/`-ban látja, és futtathatja.

---

## Eszközök

| Parancs | Mit csinál |
|---|---|
| `tools/run-job.sh <job-id> [agent-id]` | **Előbb a spec-kaput futtatja** — NO-GO esetén nem indul. `--skip-spec-gate` megkerüli, de a `meta.yaml` `spec_gate` mezőjébe `skipped` kerül. Klón, `running → awaiting_review`, commit, push. **Nem zár le.** |
| `tools/validate-spec.sh <job-id>` | Gépi kapu indítás előtt (K1–K11). NO-GO → az agent nem indulhat |
| `tools/validate-output.sh <job-id>` | Gépi kapu lezárás előtt (O1–O5) |
| `tools/close-job.sh <job-id>` | **Az egyetlen `awaiting_review → done` átmenet** (C1–C5). `--dry-run` csak ellenőriz |
| `tools/check-stale-jobs.sh` | Kilistázza a `running`-ot állító jobokat, amelyek lease-e lejárt |
| `tools/update-index.sh` | `jobs/index.yaml` újragenerálása |
| `tools/install-claude-hooks.sh [agent-id]` | Agent hookok telepítése; idempotens |
| `tools/init-hooks.sh` | A commit-aláíró git hook bekötése |

### A három gépi kapu

```
spec → validate-spec.sh → agent fut → validate-output.sh → review.md → close-job.sh → done
       (K1–K11)                        (O1–O5)                          (C1–C5)
```

Az elv: **amit gép el tud dönteni, azt döntse el a gép.** A drága figyelem a
tartalomra menjen, ne a formára.

Ez nem elmélet: a `validate-output.sh` első éles futása olyan hibát talált, amit
emberi review és merge átengedett.

### Amit a kapuk nem tudnak

A `close-job.sh` C5-e elutasít, ha a futás megkerülte a spec-kaput és a review
ezt nem ismeri el — de a menekülőút maga legális. A `check-stale-jobs.sh`
létezik, de semmi nem futtatja magától. A `meta.yaml` sémája ma template, nincs
mögötte validátor.

Amit egy kapu nem bizonyít, azt ne állítsd róla.

---

## Runnerek — mit futtat a gyár

A factory **nem tudja, milyen agentet futtat**. Egy runner az a csere-darab, ami
tudja: `tools/runners/<név>.sh`, választás a `CIC_AGENT_RUNNER`-rel
(alapértelmezés: `claude`).

A runner környezeti változókból kap mindent, és egy normalizált JSON-t ír —
szerződés: [`docs/RUNNER-CONTRACT.md`](docs/RUNNER-CONTRACT.md), séma:
[`jobs/.schema/runner-result.schema.json`](jobs/.schema/runner-result.schema.json).

| runner | mit futtat |
|---|---|
| `claude` | Claude Code. Minden Claude-specifikus ismeret itt él: CLI-flagek, `CLAUDE_CONFIG_DIR`, a JSON alakja |
| `echo` | semmit — a promptot adja vissza |

Az `echo` nem játék. Két dolgot bizonyít: hogy a szerződés valódi (egy második
implementáció az egyetlen különbség absztrakció és átnevezés között), és hogy a
lifecycle **végigfuttatható** agent, hálózat és költség nélkül. A
`test-run-job-e2e.sh` ezen áll.

**Amit egy runner nem tud megmondani, azt hagyja ki.** A hiányzó mező üresen
marad a `meta.yaml`-ben. Nullát írni oda mérésnek látszana.

---

## Agent auth

```
<agent-config-dir>/<id>/
  .credentials.json       ← symlink a megosztott hitelesítőre
  settings.json           ← izolált config
```

Indítás: `CLAUDE_CONFIG_DIR=<agent-config-dir>/<id> claude --print "..."`

A jelenlegi implementáció ezt `$HOME/.claude-personal/agents/<id>`-ként
származtatja. Ez CIC-alakú path, és egyben az, ami a `run-job.sh`-t
tesztelhetetlenné tenné `HOME`-felülírás nélkül — a fennmaradó kötések listája a
[README](README.md#known-coupling--what-round-two-has-to-break)-ben.
