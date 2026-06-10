# poc-infra-01 — Setup Guide (Milestone 0)

> Lépésről lépésre útmutató a CIC PoC alapinfrastruktúra felállításához OCI-n.
> Előfeltétel: `system-plan.md` 1. fejezet és `oci-infra-sketch.md` — ezek a lezárt
> döntések, itt nem ismételjük meg az indoklást.

---

## 1. Terraform apply — OCI alapinfrastruktúra

Fájlok: `output/iac/oci/` (`main.tf`, `variables.tf`, `outputs.tf`).

1. Töltsd ki a változókat (`terraform.tfvars` vagy `-var` flag-ek):
   - `tenancy_ocid`, `user_ocid`, `fingerprint`, `private_key_path` — OCI API kulcs adatok
   - `compartment_ocid` — a tenancy root compartment OCID-ja (ez alá jön létre a `cic-poc`
     compartment)
   - `oci_region` — **régióválasztás kritikus**: nem minden régióban van szabad Always Free
     Ampere A1 kapacitás. Ha a `terraform apply` `Out of host capacity` hibával áll le a
     `vault`/`relay`/`demo_target` instance-okon (oci-infra-sketch.md 5. fejezet), próbálj
     másik régiót, vagy futtasd retry-loopban.
   - `ssh_public_key` — a PoC közös SSH publikus kulcsa (pl. `~/.ssh/cic_poc.pub` tartalma)

2. Futtatás:
   ```bash
   cd output/iac/oci
   terraform init
   terraform plan
   terraform apply
   ```

3. Várt eredmény: 1 compartment (`cic-poc`), 1 VCN, 1 subnet, 1 security list, 4 instance
   (`bastion`, `vault`, `relay`, `demo_target`) létrejön. A `terraform output demo_target_id`
   adja az OCID-t, amire a `poc-observer-plugin-01` snapshot lépése hivatkozik.

---

## 2. Vault dev mode + Transit kulcs

Fájl: `output/iac/vault/init.sh`.

1. Másold a scriptet a `vault` instance-ra (a `bastion`-on keresztül, `ProxyJump` SSH-val).
2. Telepítsd a `vault` binárist (ha még nincs), majd futtasd:
   ```bash
   ./init.sh
   ```
3. A script elindítja a `vault server -dev`-et, bekapcsolja a `transit` engine-t, és
   létrehozza a `cic-relay-signing` Transit kulcsot.
4. Ellenőrzés:
   ```bash
   export VAULT_ADDR=http://127.0.0.1:8200
   export VAULT_TOKEN=<a script kimenetén megjelenő root token>
   vault read transit/keys/cic-relay-signing
   ```
   A válasznak tartalmaznia kell a `cic-relay-signing` kulcsot `name` mezőként.

> Mem mode: a Vault folyamat leállása után a kulcs elvész, a root token statikus marad
> a folyamat élettartama alatt. PoC-ban elfogadott (relay-func-audit, scaffold).

---

## 3. CIC-Relay build (ARM64) és deploy

1. Build lokálisan vagy CI-ban:
   ```bash
   GOOS=linux GOARCH=arm64 go build -o cic-relay ./cmd/relay
   ```
   (Ampere A1 = ARM64 — `oci-infra-sketch.md` 3. fejezet, `system-plan.md` 1.5)

2. Másold a binárist a `relay` instance-ra:
   ```bash
   scp cic-relay relay-vm:/opt/cic-relay/cic-relay
   ```

3. Másold a config fájlt: `output/iac/relay/config.yaml` → `/opt/cic-relay/relay.config.yaml`
   a `relay` instance-on. Töltsd ki a placeholder mezőket:
   - `vault.address` → a `vault` instance privát IP-je (`terraform output vault_private_ip`)
   - `vault.token` → a Vault dev mode root token (2. lépés kimenete)
   - `git_state.repo_path` → `/srv/cic-state.git` (4. lépésben jön létre)

4. Indítsd el a relay-t és ellenőrizd a health check végpontot:
   ```bash
   /opt/cic-relay/cic-relay --config /opt/cic-relay/relay.config.yaml &
   curl -s http://127.0.0.1:8080/healthz
   ```

> `TrustStoreLoaded: false` marad — ez dev módú bypass, a `poc-schema-signing-01` sem
> változtatja meg (csak a Vault signing aktiválódik).

---

## 4. Git state repo inicializálás

Fájl: `output/iac/git-state-repo/init.sh`.

1. Futtasd a `relay` instance-on (vagy a `bastion`-on, ha onnan eléri a relay):
   ```bash
   ./init.sh
   ```
2. Létrejön a `/srv/cic-state.git` bare repo a `state` és `intent` orphan ágakkal.

3. Ellenőrzés:
   ```bash
   git clone /srv/cic-state.git /tmp/state-check
   cd /tmp/state-check
   git log state    # csak az "init: state branch" commit
   git log intent   # csak az "init: intent branch" commit
   ```

---

## 5. Definition of Done — ellenőrzőlista

- [ ] `terraform plan` / `terraform apply` hibátlanul lefut az `output/iac/oci/` alatt
- [ ] `vault status` és `vault read transit/keys/cic-relay-signing` válaszol a `vault`
      instance-on
- [ ] `cic-relay` ARM64 build sikeres, `/healthz` válaszol a `relay` instance-on
- [ ] `git log state` és `git log intent` lefut a `/srv/cic-state.git` repón
- [ ] `terraform output demo_target_id` ad egy OCID-t — ezt adja át a
      `poc-observer-plugin-01` jobnak referenciaként

---

## Deliverable a `poc-observer-plugin-01`-nek

- futó `cic-relay` a `relay` instance-on (`/healthz` OK)
- elérhető Vault Transit kulcs (`cic-relay-signing`)
- elérhető bare git repo (`/srv/cic-state.git`, `state`/`intent` ágak)
- `demo_target` instance OCID (`terraform output demo_target_id`)
