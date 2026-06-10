# Domain Job-ok Bemeneti Összefoglalója — OCI PoC v1

> Minden domain job-hoz: mit várhat el az előző job outputjától, milyen döntéseket nem kell
> újra meghoznia, és mi a pontos technikai belépési pontja. Részletek: `system-plan.md`.

---

## `poc-infra-01`

**Előzmény:** nincs (gyökér job).

**Nem kell újra eldönteni:**
- Infrastruktúra = OCI Free Tier, Ampere A1 (lásd `system-plan.md` 0. fejezet)
- Resource lista és méretezés (lásd `oci-infra-sketch.md`) — compartment, VCN, 1 subnet, 1 security
  list, 4 instance (Bastion E2.1.Micro + Vault/Relay/Demo target Ampere A1, 1+1+2 OCPU = 4 OCPU keret)
- Vault = mem mode (`vault server -dev`), Transit engine, egyetlen signing kulcs
  (`cic-relay-signing`) — nincs TrustAnchorRegistry, nincs PKI cert chain
- Git state repo = bare repo, `state`/`intent` orphan ágak

**Technikai belépési pont:**
- Terraform fájlok: `cic-oci/terraform/` (új repó vagy a `cic-factory` alatt — a job dönti el a
  pontos elhelyezést, de a `cic-oci` névvel kell hivatkozni a domain adapter repóra)
- `cic-relay` build: `GOOS=linux GOARCH=arm64 go build -o cic-relay ./cmd/relay` (Ampere A1 = ARM64)
- Relay config: `TrustStoreLoaded=false` marad (dev mód) — ezt a `poc-schema-signing-01` sem
  változtatja meg v1-ben (csak a Vault signing aktiválódik, a cert-chain verify nem)
- **Deliverable, amire a `poc-observer-plugin-01` épít:** futó `cic-relay` a Relay VM-en, elérhető
  Vault Transit kulcs, elérhető bare git repo `state`/`intent` ágakkal, és legalább egy OCI
  instance OCID (a `demo_target`), amire a snapshot lépés hivatkozhat.

---

## `poc-observer-plugin-01`

**Előzmény:** `poc-infra-01` — futó relay, Vault, git state repo, `demo_target` instance OCID.

**Nem kell újra eldönteni:**
- Plugin mechanizmus = natív Go package a `core/modules/` mintára (bootstrap-regisztráció,
  fordításidőben linkelve) — **nem** `.so` plugin.Open(), **nem** WASM (lásd `system-plan.md`
  0. fejezet megjegyzés)
- `actual_state.json` mezőlista rögzített (lásd `system-plan.md` 2.2) — `pbs_root_hash` nincs
- Workflow = `poc.iac.observe` v1.0, 4 lineáris lépés (2.1–2.4 a `system-plan.md`-ben) — nincs
  `NextHops`/`StateRequirement` elágazás
- `pose_result` = explicit `"SKIPPED"` string — nem kell PoSEVerifier-t implementálni v1-ben

**Technikai belépési pont:**
- Új natív modul csomag: `core/modules/pocobs/` (CIC-Relay repóban) — minta:
  `core/modules/schemacompile/schemacompile.go` regisztrációs pattern
- `ActualStateCollector` interface implementáció a `cic-oci` repóban, OCI Go SDK
  (`github.com/oracle/oci-go-sdk`, `core.ComputeClient` + `core.VirtualNetworkClient`)
- `GitStateRecorder.RecordState` (c594, `core/nexus/recorder/recorder.go`, **implemented**) —
  adaptáció a 3 fájl (`infra.tf.json`, `actual_state.json`, `prooftrace.json`) írására
- **Gap, amit ennek a job-nak kell zárnia:** `VerifyProofArtifact` (c246,
  `cmd/relay/proof_verify.go:53`) explicit hívása a `cic.iac.commit@1.0` lépés végén — jelenleg
  production kódban sehol nem hívódik
- **Deliverable, amire a `poc-drift-detection-01` épít:** `terraform apply` után a `state/` ágon
  elérhető `actual_state.json` (a `system-plan.md` 2.2 séma szerint) és `prooftrace.json`,
  a `Collect()` függvény/`ActualStateCollector` újrafelhasználható periodikus pollinghoz.

---

## `poc-drift-detection-01`

**Előzmény:** `poc-observer-plugin-01` — `ActualStateCollector.Collect()`, `state/` ág első
commitja `actual_state.json`-nal.

**Nem kell újra eldönteni:**
- Drift osztályozás 3 kategóriás OCI-modell (lásd `system-plan.md` "Drift detekció OCI-ban"):
  `NO_DRIFT` / `RECONCILIABLE_DRIFT` / `HARD_DRIFT` — **nem** a repo-plan.md-ben szereplő
  4-kategóriás (NO_DRIFT/SOFT/HARD/CHAIN) modell
  - `NO_DRIFT`: `actual_state.json` (state/ HEAD) == élő OCI API válasz
  - `RECONCILIABLE_DRIFT`: eltérés van, de OCI API-n visszaállítható (pl. security rule)
  - `HARD_DRIFT`: instance nem létezik (`lifecycle_state: TERMINATED` vagy nem található)
- Poll mechanizmus mintája = `PollingWatcher` (`core/nexus/operator/watcher.go`, **implemented**,
  30s interval minta)

**Technikai belépési pont:**
- Új natív modul: `cic.obs.drift.classify@1.0` a `core/modules/pocobs/` csomagban
  (`DriftClassifier` interface, lásd `repo-plan.md` interface definíció — return érték
  3 kategóriára szűkítve)
- Az `ActualStateCollector.Collect()` (előző job) újrahívása periodikusan, összevetve a
  `state/` HEAD `actual_state.json`-jával
- `state/` ág új commit `drift_type` mezővel + ProofTrace lánc folytatás (`prev=<előző CommitRef>`)
  — ugyanaz a `GitStateRecorder.RecordState` mechanizmus, mint az előző jobban
- **Időzítési figyelmeztetés:** OCI instance lifecycle átmenetek (különösen `terminate`)
  percekig is elhúzódhatnak — a poll-nak ezt ki kell várnia, hogy ne rögzítsen inkonzisztens
  köztes állapotot (lásd `oci-infra-sketch.md` 5. fejezet)
- **Deliverable, amire a `poc-rollback-01` épít:** a `state/` ágon több, `drift_type`-pal jelölt
  commit (CommitRef lánc), amelyek közül a rollback célpontot választja a human.

---

## `poc-rollback-01`

**Előzmény:** `poc-drift-detection-01` — `state/` ágon több CommitRef, ezek közül választható
visszaállítási pont.

**Nem kell újra eldönteni:**
- OIS policy v1 = allow all, ha `actor == "relay-operator"` és `action == "rollback"` — **nem**
  kell teljes OIS obligation engine-t implementálni (az "concept" marad, lásd `system-plan.md`
  4. fejezet — ez nem blokkolja ezt a job-ot, mert a policy v1 triviális)
- A rollback `intent/` ág push-alapú trigger (human: `git merge state/<ref> → intent/main → push`)

**Technikai belépési pont:**
- `Watcher` interface (c580, `core/nexus/operator/watcher.go`, **scaffold** — létezik, de nincs
  bekötve) — ezt kell bekötni az `intent/` ág figyelésére
- Minimális OIS check: egyetlen `if actor == "relay-operator" && action == "rollback"` feltétel —
  **nincs** PolicyDecision séma, **nincs** obligation engine implementáció
- **Új komponens, aminek nincs meglévő Go megfelelője (sem implemented, sem scaffold):**
  `TerraformApplyTrigger` natív modul — `terraform apply -target=...` indítása a kiválasztott
  `state/` commit `infra.tf.json`-ja alapján. Ezt teljesen újonnan kell megírni.
- Új ProofTrace generálása a rollback művelethez, `commit_record`-ban visszautalás a célzott
  `CommitRef`-re
- **Deliverable, amire a `poc-demo-script-01` épít:** `git push intent/main` → automatikus
  `terraform apply` → OCI instance helyreáll → új ProofTrace a `state/` ágon.

---

## `poc-schema-signing-01` (párhuzamos, függ: `poc-infra-01`)

**Előzmény:** `poc-infra-01` — Vault dev mode + Transit kulcs (`cic-relay-signing`) elérhető.

**Nem kell újra eldönteni:**
- Vault mem mode marad — **nem** kell teljes PKI/CICSourceCA láncot implementálni
- `TrustStoreLoaded` marad `false` v1-ben — ez a job **csak** a Vault signinget aktiválja
  (`cic_sign` mező), a cert-chain verify-t (`cic.source.assert` `certVerify` closure,
  `schemacompile.go:120`) **nem** kapcsolja be
- A `pose_result`/`commit_record` mezők a `poc-observer-plugin-01` scope-ja, nem ennek a jobnak

**Technikai belépési pont:**
- `core/modules/schemacompile/schemacompile.go:198–294` — `cic.artifact.sign@1.0` jelenleg
  `signer=nil` esetén `cic_sign="unavailable"`-t ír. A job a `signer` paramétert a
  `VaultCryptoService` (c479, **implemented**, `core/nexus/crypto/service.go`) implementációjára
  köti, a `poc-infra-01`-ben létrehozott `cic-relay-signing` Transit kulccsal
- **Nincs ütközés** a `poc-observer-plugin-01`/`poc-drift-detection-01`/`poc-rollback-01`
  munkájával — más Go csomagot érint (`schemacompile`, nem `pocobs`), ezért valóban
  párhuzamosan futtatható, ahogy a `sub-jobs-overview.md` is jelzi
- **Deliverable:** `cic_sign` mező valós Vault Transit aláírást tartalmaz a
  `schemacompile`/`schemapipeline` artifact-okban (`cic_signed_ca` maradhat `"stub:pending"`,
  ez nem v1 scope).
