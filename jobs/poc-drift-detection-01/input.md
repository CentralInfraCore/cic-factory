# poc-drift-detection-01 — Drift detekció: a hiányzó `compare` lépés bekötése

## Reasoning mód

**implementation** — konkrét Go kódváltozás a CIC-Relay-ben, test, reachability-bizonyíték.

## Kontextus — olvasd el ELŐSZÖR

Ez a job a CIC reconcile-körének **alsó felét** kezdi bekötni. A felső fél
(desired → apply) kész; az alsó fél (observe actual → **compare** → drift) hiányzik.
A pontos bekötési pontokat egy friss feltérképezés azonosította — ezek a job
elsődleges referenciái:

- `docs/relay-reconcile-loop-map.md` — a `nexus/operator` edge-triggered apply-watcher,
  az `observe→compare→apply` hármasból csak az `apply` van meg. Ez a job a `compare`-t adja.
- `docs/relay-audit-trail-map.md` — a `GitStateRecorder.RecordState` mechanizmus
  (`core/nexus/recorder/recorder.go:86`), és két konkrét hiányosság, amit ez a job old meg:
  (1) a `WorkflowRecorder` `expected` mezője placeholder (`workflow_recorder.go:33-36`) —
  itt lesz először **valódi** `expected` (state/ HEAD) vs `actual` (élő OCI) összevetés;
  (2) a `ProofTrace` nem hordoz explicit `prev`-pointert — itt vezetjük be a state/ ág
  CommitRef-láncát.
- `docs/relay-module-layer-map.md` — a natív modulok `core/modules/`-ban élnek
  (bootstrap-regisztrált Go package, `schemacompile` mintára). **A `core/plugins/` path
  NEM létezik** — a drift classifier a `core/modules/pocobs/` csomagba kerül.

Szülő terv (kanonikus, ne tervezd újra): `jobs/poc-system-plan/output/domain-job-inputs.md`
(poc-drift-detection-01 szakasz) és `jobs/poc-system-plan/output/system-plan.md`
("Drift detekció OCI-ban"). KB: `c2543` (drift diagnózis), `c1815` (drift taxonómia),
`c263` (state commit model).

**Előfeltétel:** `poc-observer-plugin-01` kész — `ActualStateCollector.Collect()` és a
`state/` ág első commitja `actual_state.json`-nal. Ha ez nincs meg, a job NEM indítható;
jelezd és állj meg.

## Lezárt döntések — NE tervezd újra

- **Drift osztályozás: 3 kategóriás OCI-modell** (NEM a `repo-plan.md` 4-kategóriás
  NO_DRIFT/SOFT/HARD/CHAIN modellje):
  - `NO_DRIFT`: `actual_state.json` (state/ HEAD) == élő OCI API válasz
  - `RECONCILIABLE_DRIFT`: eltérés van, de OCI API-n visszaállítható (pl. security rule)
  - `HARD_DRIFT`: instance nem létezik (`lifecycle_state: TERMINATED` vagy nem található)
- **Poll mechanizmus mintája:** `PollingWatcher` (`core/nexus/operator/watcher.go`,
  implemented, 30s interval minta). NEM kell új watcher-architektúra — a meglévő mintát kövesd.
- **State commit mechanizmus:** `GitStateRecorder.RecordState` (`core/nexus/recorder/recorder.go`,
  implemented). NEM kell új persistence — ezt hívd a drift commithoz.
- **CIC szerepe ebben a fázisban: OBSERVER + RECORDER.** A drift detektálódik és rögzül,
  de NEM triggerel automatikus javítást (reconcile workflow v2+). A kézi módosítást human végzi.
- **Platform: OCI** (NEM Proxmox — az a terv felülírva). Az actual state forrása az OCI API.

## Feladat

### 1. `DriftClassifier` natív modul — a `compare` lépés

Új natív modul a `core/modules/pocobs/` csomagban: `cic.obs.drift.classify@1.0`.

- `DriftClassifier` interface — a `repo-plan.md` interface definíciója, de a return érték
  **3 kategóriára szűkítve** (`NO_DRIFT`/`RECONCILIABLE_DRIFT`/`HARD_DRIFT`).
- A diagnózis logika `c2543` szerint:
  ```go
  // expected = state/ HEAD actual_state.json (a lánc által ismert állapot)
  // actual   = élő OCI API válasz (frissen lekérdezve)
  func Classify(expected, actual OciState) DriftType {
      if canonicalHash(expected) == canonicalHash(actual) {
          return NO_DRIFT
      }
      if isReconcilable(expected, actual) { // OCI API-n visszaállítható eltérés
          return RECONCILIABLE_DRIFT
      }
      return HARD_DRIFT // instance TERMINATED / nem létezik
  }
  ```
- Bootstrap-regisztráció a `schemacompile` mintára (fordításidőben linkelt, NEM `plugin.Open`).

### 2. Periodikus observe → compare loop

- Az `ActualStateCollector.Collect()` (előző job) periodikus újrahívása a `PollingWatcher`
  mintára (`core/nexus/operator/watcher.go`), összevetve a `state/` HEAD `actual_state.json`-jával.
- **Időzítési figyelmeztetés:** OCI instance lifecycle átmenetek (különösen `terminate`)
  percekig elhúzódhatnak — a poll-nak ezt ki kell várnia, hogy ne rögzítsen inkonzisztens
  köztes állapotot (lásd `oci-infra-sketch.md` 5. fejezet). Ez NEM `SOFT_DRIFT` kategória,
  hanem a poll stabilizációs ablaka.

### 3. State commit + explicit ProofTrace prev-lánc

- Minden drift esemény → `state/` ág új commit a `GitStateRecorder.RecordState`-en keresztül,
  `drift_type` mezővel.
- **A `relay-audit-trail-map.md` #3 lelet feloldása:** a drift commit ProofTrace-e explicit
  `prev=<előző CommitRef>`-et hordoz, így a state/ ágon olvasható, nem csak git-parent-implicit
  lánc épül. A `RecordState` `expected` oldala itt valódi (state/ HEAD), NEM placeholder.
- `HARD_DRIFT` (instance TERMINATED) esetén: a commit rögzül, de a ProofTrace lánc utolsó
  érvényes CommitRef-je megmarad (nem nullázódik) — ez a `poc-rollback-01` visszaállítási pontja.

### 4. Demo script

`jobs/poc-drift-detection-01/output/demo-drift.sh`:
- automatizált kézi módosítás-szekvencia OCI API-n (pl. security rule változtatás → RECONCILIABLE,
  instance terminate → HARD)
- minden módosítás után: `git log --oneline state/` kimenet + `drift_type` megjelenítés

## Tiltott rövidítések (kötelező betartani)

- **Fájl/szimbólum létezése ≠ implemented.** A `DriftClassifier` attól, hogy létezik a Go
  package-ben és a teszt zöld, MÉG NEM bekötött. A production poll-loopból ténylegesen hívódnia kell.
- **Exit code 0 ≠ működik.** A `go build` / `go test` sikere nem bizonyítja a drift-detektálást;
  a tényleges OCI-eltérés → helyes `drift_type` az egyetlen bizonyíték. A kimenetet olvasd, ne csak az exit code-ot.
- **A `core/plugins/` path nem létezik** — ne hozd létre, ne hivatkozz rá. `core/modules/pocobs/`.

## Reachability — kötelező bizonyíték (Definition of Done)

A státusz-állításokat (implemented/scaffold) call-path bizonyítékkal kell alátámasztani:

- `grep -rn` a `Classify` / `DriftClassifier` hívási helyére a production kódban
  (a poll-loop), **`_test.go` kizárással** (`grep -v _test.go`) VAGY `deadcode ./...` output.
- A "symbol létezik + test passes" önmagában NEM elég — kell a **production call site (file:line)**,
  ahol a poll-loop hívja a classifier-t. Ezt az output `claim-evidence` táblába kell tenni.

## Output

- `jobs/poc-drift-detection-01/output/drift-detection-report.md` — implementációs jelentés +
  **claim-evidence tábla** ezekkel az oszlopokkal: `Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat` (a Bizonyíték oszlop file:line). Minden implemented/scaffold állításhoz reachability-artifact.
- `jobs/poc-drift-detection-01/output/demo-drift.sh` — demo script.
- A Go forrásváltozások a CIC-Relay klónban, `feature/poc-drift-detection-01` branch-en.

## Definition of Done

- [ ] `DriftClassifier` (`cic.obs.drift.classify@1.0`) a `core/modules/pocobs/`-ban, bootstrap-regisztrálva
- [ ] 3-kategóriás osztályozás (NO_DRIFT / RECONCILIABLE_DRIFT / HARD_DRIFT) működik valós OCI-eltérésen
- [ ] periodikus observe→compare loop a PollingWatcher mintára, OCI lifecycle stabilizációs ablakkal
- [ ] drift commit a `state/` ágon `GitStateRecorder.RecordState`-en át, `drift_type` + explicit `prev` CommitRef
- [ ] HARD_DRIFT után a ProofTrace lánc utolsó érvényes CommitRef-je megmarad
- [ ] **reachability-artifact**: production call site (file:line, `_test.go` kizárva) VAGY `deadcode ./...` az outputban
- [ ] claim-evidence tábla minden státusz-állításhoz

## Nyelvi szabály

- Dokumentáció, jelentés: **magyarul**
- Go kód, shell script, YAML, kódon belüli komment: **angolul**
