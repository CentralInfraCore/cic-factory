# PoC Rendszerterv — OCI adaptáció (v1)

> Szintézis dokumentum. Forrás: `poc-implementation-plan/output/*`, `poc-bridge-check/output/*`,
> `poc-repo-design/output/repo-plan.md`, `relay-func-audit/output/*`.
> Ez a dokumentum az egyetlen referencia a domain job-ok (`poc-infra-01`, `poc-observer-plugin-01`,
> `poc-drift-detection-01`, `poc-rollback-01`, `poc-schema-signing-01`) számára.

---

## 0. Lezárt döntések (referencia)

| Döntés | Érték |
|---|---|
| Demo infrastruktúra | OCI Free Tier, Ampere A1 (Always Free) |
| PBS helyettesítő | git state commit — `actual_state.json` közvetlenül a `state/` ágra, `pbs_root_hash` mező kimarad |
| Plugin betöltés | Go natív modul (nem WASM, nem `plugin.Open(.so)`) |
| OIS policy v1 | allow all, ha `actor == "relay-operator"` és `action == "rollback"` |
| Vault v1 | mem mode |
| Git state repo | bare git repo, `state/` és `intent/` ágak |
| Domain adapter repo | `cic-oci` |

> **Megjegyzés a "Plugin betöltés" sorhoz** (lásd 3. fejezet, D1 pont): a `relay-func-audit` szerint
> a `.so` plugin modell (`plugin.Open()+Lookup()`) a forráskódban **nincs implementálva** — a
> ténylegesen futó natív-modul minta a `core/modules/` alatti, **fordításidőben linkelt, bootstrap-kor
> regisztrált** Go package (pl. `schemacompile`, `schemapipeline`). A "Go natív modul, nem WASM" döntés
> ezzel a mintával valósul meg — ez technikai pontosítás, nem a döntés megkérdőjelezése.

---

## 1. Milestone 0 — OCI alapinfrastruktúra

**Cél:** Vault (mem mode) + CIC-Relay + git state repo fut OCI-n, a domain job-ok erre építenek.

### 1.1 OCI erőforrások

| Erőforrás | Típus | Megjegyzés |
|---|---|---|
| Compartment | `oci_identity_compartment` | `cic-poc` — minden erőforrás ide kerül |
| VCN | `oci_core_vcn` | egy CIDR blokk (pl. `10.0.0.0/16`) |
| Subnet | `oci_core_subnet` | egy publikus subnet (PoC egyszerűsítés — nincs külön privát subnet) |
| Security List | `oci_core_security_list` | SSH (22) bastionról, relay↔vault belső portok, demo target portjai |
| VM: Bastion | `oci_core_instance` | `VM.Standard.E2.1.Micro` (AMD Always Free shape), publikus IP, SSH jump host |
| VM: Vault | `oci_core_instance` | Ampere A1, 1 OCPU / 6 GB, `vault server -dev` |
| VM: Relay | `oci_core_instance` | Ampere A1, 1 OCPU / 6 GB, CIC-Relay binary + natív modulok |
| VM: Demo target | `oci_core_instance` | Ampere A1, 2 OCPU / 12 GB — **ezt hozza létre/törli a Terraform** a 8.1/8.3 fázisban |

Ampere A1 Always Free keret: **4 OCPU + 24 GB RAM összesen** → Vault (1/6) + Relay (1/6) + Demo target (2/12) = 4/24 — pontosan kitölti a keretet. (Részletek: `oci-infra-sketch.md`)

### 1.2 Terraform OCI provider — konfig váz

```hcl
terraform {
  required_providers {
    oci = {
      source  = "hashicorp/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  region           = var.oci_region
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  compartment_id   = var.compartment_ocid
}
```

A teljes resource lista: `oci-infra-sketch.md`. A `cic-factory` repóban a Terraform fájlok helye: domain job-ok döntik el (javasolt: `cic-oci/terraform/`).

### 1.3 Vault mem mode indítás (Vault VM)

```bash
# Vault VM-en
vault server -dev -dev-listen-address=0.0.0.0:8200 -dev-root-token-id="<root-token>"
# Transit engine bekapcsolása a CIC signing-hoz
export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=<root-token>
vault secrets enable transit
vault write -f transit/keys/cic-relay-signing
```

A Relay VM-en a `CryptoService` (c479, `core/nexus/crypto/service.go`) konfigja:

```bash
export VAULT_ADDR=http://<vault-vm-private-ip>:8200
export VAULT_TOKEN=<root-token>
export CIC_VAULT_KEY=cic-relay-signing
```

Mem mode → root token statikus, nincs lease renewal (a `relay-func-audit` ezt scaffold-ként jelöli — PoC-ban elfogadható, nem blokkoló).

### 1.4 Git state repo inicializálás

```bash
# Relay VM-en (vagy bastion-on, ha a relay onnan eléri)
mkdir -p /srv/cic-state.git && cd /srv/cic-state.git
git init --bare

# munkakönyvtárból:
git clone /srv/cic-state.git work && cd work
git checkout --orphan state
git commit --allow-empty -m "init: state branch"
git checkout --orphan intent
git commit --allow-empty -m "init: intent branch"
git push origin state intent
```

A `GitStateRecorder` (c594, `core/nexus/recorder/recorder.go`) konfigjában ez a bare repo a cél (`state/` ág).

### 1.5 CIC-Relay binary deploy

```bash
# build (lokálisan vagy CI-ban), majd scp a Relay VM-re
GOOS=linux GOARCH=arm64 go build -o cic-relay ./cmd/relay
scp cic-relay relay-vm:/opt/cic-relay/cic-relay
```

> Ampere A1 = ARM64 → a Go build target `GOARCH=arm64`. A `core/modules/pocobs`-t (lásd 3. fejezet)
> a relay binary-be kell linkelni fordításkor — natív modul, nem külön betöltött `.so`.

Relay config (`relay.config.yaml`) minimum mezői: `CIC_VAULT_KEY`, Vault cím, git state repo elérési út, `TrustStoreLoaded=false` (dev mód, bypass — lásd 4. fejezet).

**Deliverable (Milestone 0):** `terraform apply` sikeres a 4 OCI instance-re, Vault dev mode fut és Transit kulcs létezik, `cic-relay` elindul a Relay VM-en, bare git repo elérhető `state`/`intent` ágakkal.

---

## 2. Felülvizsgált relay workflow — `poc.iac.observe` v1.0 (OCI)

```yaml
apiVersion: relay.cic.com/v1
kind: Workflow
metadata:
  name: cic.iac.observe
  version: "1.0"
spec:
  steps:
    - name: assert_intent
      module: cic.iac.assert@1.0
    - name: snapshot_state
      module: cic.iac.snapshot@1.0
    - name: build_prooftrace
      module: cic.iac.prooftrace@1.0
    - name: commit_state
      module: cic.iac.commit@1.0
```

> A `Setx()` (`core/cabinet/cabinet.go`) **lineáris** workflow-t hajt végre — `NextHops`/`StateRequirement`
> kiértékelés scaffold (`relay-func-audit`). A fenti 4 lépés szigorúan szekvenciális `Steps` tömb,
> ez megfelel a jelenlegi implementációnak.

### 2.1 `cic.iac.assert@1.0` — OIS intent rögzítés

| | |
|---|---|
| **Bemenet** | `actor` (pl. `"relay-operator"`), `action` (pl. `"observe"`), `policy_ref` |
| **Kimenet** | `intent` rekord: `{actor, action, policy_ref, ts}` |
| **Go kötés** | Új natív modul a `core/modules/pocobs/` csomagban. Mintaként a `schemacompile`
(`core/modules/schemacompile/schemacompile.go`) regisztrációs mintáját kell követni
(natív modul bootstrap-regisztráció — c442, c453). |
| **Megjegyzés** | Ez az OIS modell (c2498) "intent" deklarációs lépése. Az obligation-check
(OIS policy motor) **concept** (lásd 4. fejezet) — v1-ben a policy_ref csak rögzítésre kerül,
kiértékelés nem történik ebben a lépésben (8.1–8.3 fázisban nincs is rá szükség, csak 8.4-ben). |

### 2.2 `cic.iac.snapshot@1.0` — OCI instance state lekérés (PBS helyett)

| | |
|---|---|
| **Bemenet** | `instance_ocid` (vagy instance OCID-lista), OCI auth config (instance principal vagy config file) |
| **Kimenet** | `actual_state.json`:
```json
{
  "instance_id": "ocid1.instance...",
  "lifecycle_state": "RUNNING|TERMINATED",
  "shape": "VM.Standard.A1.Flex",
  "ocpus": 2,
  "memory_gb": 12,
  "public_ip": "...",
  "private_ip": "...",
  "vcn_id": "ocid1.vcn...",
  "security_rules_hash": "sha256:...",
  "collected_at": "RFC3339"
}
```
|
| **Go kötés** | `ActualStateCollector` interface (lásd `repo-plan.md`, adaptálva `cic-oci`-ra):
```go
type ActualStateCollector interface {
    Collect(ctx context.Context) (*ActualState, error)
    Provider() string // "oci"
}
```
Implementáció a `cic-oci` repóban, OCI Go SDK (`github.com/oracle/oci-go-sdk`) `core.ComputeClient`
és `core.VirtualNetworkClient` hívásokkal. A `security_rules_hash` a security list szabályok
`canonicaljson.ToJSON` (c1127) szerinti kanonikus hash-e. |
| **Megjegyzés** | A `pbs_root_hash` mező **nincs** — ez a PBS helyettesítő. A `Collect()` natív modulként
fut a Relay VM-en (stateful: OCI SDK kliens session) — lásd repo-plan D1 döntés, natív modul minta. |

### 2.3 `cic.iac.prooftrace@1.0` — ProofTrace létrehozás (`pbs_root_hash` nélkül)

| | |
|---|---|
| **Bemenet** | `intent` (2.1), `actual_state.json` (2.2) |
| **Kimenet** | ProofTrace step hozzáadása a `Setx()` által automatikusan épített láncolathoz
(`core/cabinet/proof_trace.go`, `ComputeChainHashV1`) — `id=ChainHash`, `prev=<előző CommitRef>`,
`signature=<Vault sign, ha konfigurálva>` |
| **Go kötés** | A ProofTrace generálás **implemented** és automatikus minden `Setx` hívásnál — ez a
lépés nem hoz létre új struktúrát, hanem a step input/output hash-eket adja a chain_hash
számításhoz. `pose_result` mező értéke explicit **`"SKIPPED"`** (lásd 4. fejezet — ez elfogadható v1-ben). |
| **Gap-kezelés** | `VerifyProofArtifact` (c246, `cmd/relay/proof_verify.go:53`) production kódban
soha nem hívódik (relay-func-audit). **A `cic.iac.commit@1.0` lépés végén explicit meg kell hívni**
— ez a `poc-observer-plugin-01` scope része (lásd 4. fejezet, gap #1). |

### 2.4 `cic.iac.commit@1.0` — GitStateRecorder commit → `state/` ág

| | |
|---|---|
| **Bemenet** | `infra.tf.json` (desired — a `terraform plan -json` vagy `terraform show -json` kimenete),
`actual_state.json` (2.2), `prooftrace.json` (2.3) |
| **Kimenet** | git commit a `state/` ágon: `infra.tf.json`, `actual_state.json`, `prooftrace.json`;
`CommitRef #N` |
| **Go kötés** | `GitStateRecorder.RecordState` (c594, **implemented** — `core/nexus/recorder/recorder.go`):
"persists the state to JSON files, signs it (Vault), and creates a git commit". A jelenlegi
implementáció `ExpectedState`-et ír — a PoC `actual_state.json` + `prooftrace.json` + `infra.tf.json`
hármast írja ugyanazon mechanizmussal (StateCommitWriter adaptáció — `repo-plan.md` 6. szakasz, de
**StateCommit séma (c1823) nélkül is működik v1-ben**: a 3 JSON fájl önmagában elegendő bizonyíték). |
| **Gap-kezelés** | A commit után hívja meg a `VerifyProofArtifact`-ot (lásd 2.3 gap-kezelés) —
az eredményt logolja/OTel span attribútumként rögzíti (a `chain_anchor` minta szerint, c-hivatkozás:
`setHandler` `core/cabinet/cabinet.go`). Ha Vault nincs konfigurálva, a recorder `nil` és a
recording **non-fatal** kimarad (relay-func-audit) — Milestone 0 garantálja, hogy Vault fut, ezért
ez a PoC-ban nem áll fenn. |

---

## 3. Domain job-ok implementációs scope-ja (OCI-adaptált)

| Domain job | Scope (OCI-adaptált) | Deliverable |
|---|---|---|
| `poc-infra-01` | OCI compartment + VCN + subnet + security list + 4 VM Terraformmal (1.1–1.2), Vault dev mode + Transit kulcs (1.3), CIC-Relay binary build+deploy ARM64 (1.5), bare git state repo `state`/`intent` ágakkal (1.4) | `terraform apply` sikeres, `cic-relay` elindul, Vault Transit kulcs elérhető, git state repo elérhető |
| `poc-observer-plugin-01` | `cic-oci` repó: `ActualStateCollector` implementáció OCI Go SDK-val (2.2); `core/modules/pocobs/` natív modul csomag a Relay-ben: `cic.iac.assert@1.0`, `cic.iac.snapshot@1.0`, `cic.iac.prooftrace@1.0`, `cic.iac.commit@1.0`; `poc.iac.observe` workflow YAML regisztrálása; `VerifyProofArtifact` hívás bekötése a commit lépés végén (gap #1 zárása) | `terraform apply` → `state/` ág commit (`infra.tf.json`, `actual_state.json`, `prooftrace.json`), `VerifyProofArtifact` lefut és `pose_result: SKIPPED`-et nem utasít el |
| `poc-drift-detection-01` | `DriftClassifier` natív modul (`cic.obs.drift.classify@1.0`): `actual_state.json` (state/ HEAD) vs. élő OCI API válasz összehasonlítás; osztályozás `NO_DRIFT` / `RECONCILIABLE_DRIFT` / `HARD_DRIFT` (lásd 0. fejezet drift-definíciók); periodikus poll (`PollingWatcher`, c-hiv. `core/nexus/operator/watcher.go`, implemented, 30s interval mintára); `state/` ág commit `drift_type` mezővel, ProofTrace lánc folytatás (`prev=<előző CommitRef>`) | 5 kézi OCI módosítás (security list szabály) → 5 commit a `state/` ágon, mindegyik `drift_type`-pal jelölve |
| `poc-rollback-01` | `intent/` ág figyelő (`Watcher` interface c580, scaffold → bekötendő); OIS allow-all check (`actor=="relay-operator" && action=="rollback"` — minimális policy motor, nem a teljes OIS obligation engine); új natív modul: `TerraformApplyTrigger` (`terraform apply -target=...` indítása a kiválasztott `state/` commit `infra.tf.json`-ja alapján — **ez új komponens, nincs meglévő Go megfelelője**); új ProofTrace, `commit_record`-ban visszautalás a célzott `CommitRef`-re | `git push intent/main` → relay észleli → OIS check ALLOWED → `terraform apply` lefut → OCI instance helyreáll → új ProofTrace `CommitRef`-je a korábbi commitra mutat |
| `poc-schema-signing-01` | Vault Transit key setup (1.3-ban már megtörtént — ez a job a `cic.artifact.sign@1.0`/`cic.source.assert@1.0` Vault-bekötését aktiválja: `signer != nil` → `cic_sign` valós érték; `TrustStoreLoaded` marad `false`, csak a signing aktiválódik, a cert-chain verify nem (lásd 4. fejezet — nem PoC-blokkoló, párhuzamosan futtatható) | `cic_sign` mező nem `"unavailable"`, valós Vault Transit aláírás a `schemacompile`/`schemapipeline` artifact-okon |

**Plugin mechanizmus minden domain job-ban:** natív Go package a `core/modules/` alatt (vagy a
`cic-oci` repóban, importálva a Relay build-be), bootstrap-regisztrálva — **nem** `plugin.Open(.so)`,
**nem** WASM. (lásd 0. fejezet megjegyzés)

---

## 4. Gap-ek a relay-func-audit alapján — mit kell megírni

| Gap | PoC blokkoló? | Kezelés |
|---|---|---|
| `VerifyProofArtifact` (c246) soha nem hívódik production kódban | **igen** — a lánc nem auditálható vissza | `poc-observer-plugin-01` scope: a `cic.iac.commit@1.0` lépés végén explicit hívás (2.4) |
| `PoSEResult` mező soha nem töltődik ki | részben — `pose_result: SKIPPED` elfogadható v1-ben | `cic.iac.prooftrace@1.0` explicit `"SKIPPED"`-et ír (2.3); v2-ben aktiválandó (`PoSEVerifier` natív modul, repo-plan H pont) |
| sign/verify dev bypass (`TrustStoreLoaded=false`) | nem — Vault mem módban a recording fut, csak a modul-aláírás-ellenőrzés van kikapcsolva | `poc-schema-signing-01` aktiválja a Vault-signinget; a cert-chain verify (`TrustStoreLoaded`) v1-ben kikapcsolva marad, ez nem blokkolja a state/intent commit láncot |
| `GitSyncer` (`core/nexus/sync/syncer.go`) soha nem hívódik | nem | nem kell v1-ben — a `state`/`intent` ágak közvetlen push/merge-eli a human (8.4 fázis), nincs napi szinkron igény a PoC alatt |
| `isolation.Coordinator` soha nem hívódik | nem | nem kell v1-ben — a PoC natív modulok in-process futnak, nincs szükség onion-encryption izolációra |
| `StateRequirement`/`NextHops` nem kerül kiértékelésre (`Setx` lineáris) | nem — a tervezett workflow-k (2. fejezet) eleve lineárisak | a `poc.iac.observe` és `poc-rollback-01` workflow YAML-jai szigorú `Steps` tömbként íródnak, feltételes elágazás nélkül |
| `TerraformApplyTrigger` natív modul nem létezik (sem implemented, sem scaffold) | **igen, de csak a 8.4 fázishoz** | `poc-rollback-01` scope: új natív modul megírása — ez az egyetlen olyan komponens a tervben, amelynek **nincs meglévő Go megfelelője egyáltalán** (sem implemented, sem scaffold) |

---

## 5. Felülvizsgált demo forgatókönyv (OCI, ~30 perc)

```
[0:00] Setup ellenőrzés
  → OCI Console nyitva (Compute > Instances, compartment: cic-poc)
  → CIC-Relay logok terminálban (Relay VM, ssh bastionon át)
  → git log state/ terminálban (üres vagy csak init commit)
  → terraform show -state=... — desired state ellenőrzés

[0:05] 8.1 Terraform up
  → [H] terraform apply  (Demo target instance létrehozása, 2 OCPU/12GB Ampere A1)
  → [CIC-OBS] poc.iac.observe lefut: cic.iac.snapshot@1.0 → oci compute instance get
  → ProofTrace #1, CommitRef #1 megjelenik a state/ ágon
  → Képernyőn: state/ első commit (infra.tf.json, actual_state.json, prooftrace.json)
  → Időzítés: az OCI API instance create → RUNNING lifecycle_state propagálása ~30-60s,
    a snapshot lépést erre várakoztatni kell (poll, ne azonnali read)

[0:10] 8.2 5x kézi módosítás (OCI Security List)
  → [H] 5x kézi módosítás az OCI Console-on (Security List ingress szabály hozzáadás/törlés)
  → [CIC-OBS] poc-drift-detection-01 periodikus poll (30s) észleli a security_rules_hash
    eltérést → state/ ág 5 commit, RECONCILIABLE_DRIFT jelölésekkel
  → Képernyőn: watch git log --oneline state/, drift_type mezők
  → Időzítés: OCI Security List módosítás propagálása szubszekundum-skálán (gyorsabb mint
    Proxmox/VyOS), de a 30s poll interval dominál a demo ütemezésében

[0:20] 8.3 Infra törlés
  → [H] terraform destroy  (Demo target instance törlése)
  → [CIC-OBS] snapshot: instance nem található / lifecycle_state=TERMINATED → HARD_DRIFT
  → state/ ág commit: drift=true, drift_type=HARD_DRIFT, actual_state={instance_id, lifecycle_state: "TERMINATED"}
  → Képernyőn: ProofTrace lánc megmarad (utolsó érvényes CommitRef)
  → Időzítés: OCI instance terminate → TERMINATED állapot elérése néhány perc is lehet —
    a snapshot poll-nak ezt ki kell várnia (vagy a demo script explicit vár az állapotváltozásra)

[0:25] 8.4 Rollback
  → [H] git merge state/<commit-1-ref> → intent/main, git push
  → [CIC-ACT] intent/ ág watcher észleli a push-t
  → [CIC-ACT] OIS check: actor="relay-operator", action="rollback" → ALLOWED (allow-all policy)
  → [CIC-ACT] TerraformApplyTrigger: terraform apply -target=... az #1 commit infra.tf.json alapján
  → [CIC-ACT] Demo target instance újra létrejön OCI-n
  → Új ProofTrace, CommitRef visszautal #1-re
  → Képernyőn: OCI Console — instance state RUNNING-ra vált, state/ ág új commit

[0:30] Összefoglalás
  → git log state/ — teljes lánc látható (8.1 → 5x drift → HARD_DRIFT → rollback)
  → git verify-commit HEAD — Vault aláírás érvényes
  → "Nem az ember mondja, hogy igaz. A láncolat bizonyítja."
```

**OCI-specifikus időzítési megjegyzés:** az OCI API instance lifecycle átmenetek (create→RUNNING,
terminate→TERMINATED) néhány tíz másodperc — néhány perc közötti propagálási idővel járhatnak.
A `poc-drift-detection-01` poll-mechanizmusának (vagy a demo scriptnek, `poc-demo-script-01`)
ezt explicit ki kell várnia (poll-with-timeout), különben a snapshot lépés inkonzisztens
köztes állapotot rögzíthet.
