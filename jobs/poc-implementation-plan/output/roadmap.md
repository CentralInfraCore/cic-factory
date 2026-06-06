# PoC v1 Roadmap — helyes CIC szerepekkel

KB alap: add.md, c912, c914, c2498, c2543, c2618, c263, c2436, c1312, c442, c453

---

## Alapelv

A CIC **nem infrastruktúra-végrehajtó** az 8.1–8.3 fázisokban — hanem **igazoló tanú**.
Az egyetlen fázis ahol aktívan beavatkozik: **8.4 Rollback** (OIS-ellenőrzés után).

Minden tervbeli lépésnél explicit jelölés:
- `[H]` = Human csinálja (Terraform, kézi módosítás)
- `[CIC-OBS]` = CIC megfigyel és rögzít (Observer + Recorder)
- `[CIC-ACT]` = CIC aktívan beavatkozik (Actor)

---

## Milestone 0 — Alap infrastruktúra (2–3 hét)

**Cél:** Proxmox + Vault + CIC-Relay futó állapotban

| Lépés | Ki | Feladat |
|---|---|---|
| Proxmox host konfigurálás | `[H]` | Hálózat, storage pool, API token |
| Terraform Proxmox provider | `[H]` | bpg/proxmox provider init, VM template |
| Vault mem mode indítás | `[H]` | dev mode Vault, CIC key setup |
| CIC-Relay binary build | `[H]` | `go build`, relay config YAML |
| Git state repo init | `[H]` | bare repo, state/ és intent/ ágak |
| GitStateRecorder config | `[CIC-ACT]` | relay config bekötése a git repóra |

**Deliverable:** `terraform plan` fut, relay elindul, git state repo elérhető

---

## Milestone 1 — Terraform observer plugin (2–3 hét)

**Cél:** A 8.1 fázis demonstrálható — `terraform apply` → ProofTrace commit

| Lépés | Ki | Feladat |
|---|---|---|
| terraform_observer plugin írása | `[H]` | .so plugin, Go buildmode=plugin |
| Plugin: actual_state.json generálás | `[H]` | Proxmox API lekérdezés, PBS snapshot hívás |
| OIS intent rögzítés | `[CIC-ACT]` | actor/action/policy rögzítés relay workflow-ban |
| ProofTrace esemény létrehozás | `[CIC-ACT]` | id=SHA-256(payload), signature, prev=null |
| GitStateRecorder commit | `[CIC-ACT]` | state/ ág: infra.tf.json + actual_state.json + prooftrace.json |
| CommitRef #1 ellenőrzés | `[H]` | `git log state/` — láthatóság vizsgálat |

**Relay workflow (poc.iac.observe v1.0):**
```yaml
steps:
  - cic.iac.assert@1.0       # OIS intent rögzítés
  - cic.iac.snapshot@1.0     # PBS actual state lekérés
  - cic.iac.prooftrace@1.0   # ProofTrace létrehozás
  - cic.iac.commit@1.0       # GitStateRecorder commit
```

**Deliverable:** `terraform apply` után state/ ágon látható commit, prooftrace.json érvényes

---

## Milestone 2 — Drift detekció (2 hét)

**Cél:** A 8.2 fázis demonstrálható — kézi módosítás → drift commit

| Lépés | Ki | Feladat |
|---|---|---|
| Kézi módosítás (VyOS szabály) | `[H]` | Kézi SSH, konfig módosítás |
| PBS hash újraszámítás | `[CIC-OBS]` | actual state poll (periodic vagy event-driven) |
| Drift diagnózis | `[CIC-OBS]` | canonical_state(prooftrace) vs pbs_root_hash |
| Drift típus meghatározás | `[CIC-OBS]` | SOFT | RECONCILIABLE | HARD (c2543) |
| state/ ág commit (drift=true) | `[CIC-ACT]` | drift_type, actual_state.json, ProofTrace lánc folytatás |
| Commit görgetés vizualizáció | `[H]` | `watch git log --oneline state/` |

**Demo script:** 4–5 alkalommal automatizált kézi módosítás, minden után state/ ág frissül

**Deliverable:** 5 commit a state/ ágon, minden commit drift_type-pal jelölve

---

## Milestone 3 — Hard Drift + törlés (1 hét)

**Cél:** A 8.3 fázis demonstrálható — `terraform destroy` → HARD_DRIFT commit

| Lépés | Ki | Feladat |
|---|---|---|
| Terraform destroy | `[H]` | teljes infrastruktúra törlése |
| PBS hash = null észlelés | `[CIC-OBS]` | fizikailag semmi nem létezik |
| HARD_DRIFT commit | `[CIC-ACT]` | drift=true, drift_type=HARD_DRIFT, actual_state={} |
| Utolsó CommitRef megmarad | `[CIC-OBS]` | lánc nem semmisül meg |

**Deliverable:** state/ ágon HARD_DRIFT commit, ProofTrace lánc intact

---

## Milestone 4 — Rollback (OIS + Terraform apply) (2–3 hét)

**Cél:** A 8.4 fázis demonstrálható — intent/ push → CIC triggereli a Terraform apply-t

| Lépés | Ki | Feladat |
|---|---|---|
| Korábbi CommitRef kiválasztása | `[H]` | `git log state/` → commit #3 azonosítás |
| intent/ ág merge | `[H]` | `git merge state/commit-3-ref` + `git push intent/main` |
| GitSource figyelő (intent/ ág) | `[CIC-ACT]` | push esemény észlelése |
| OIS ellenőrzés | `[CIC-ACT]` | obligation check: actor jogosult-e rollbackre? |
| Terraform apply triggering | `[CIC-ACT]` | `terraform apply -target=...` a korábbi állapot alapján |
| Új ProofTrace | `[CIC-ACT]` | CommitRef visszautal #3-ra |

**OIS minimális demo policy (v1):**
```
obligation = ALLOWED  # ha actor == "relay-operator" és action == "rollback"
```

**Deliverable:** infra valós időben újjáépül, új ProofTrace CommitRef #3-ra mutat

---

## Demo forgatókönyv (összesített, ~30 perc)

```
[0:00] Setup ellenőrzés
  → Proxmox web UI nyitva
  → CIC-Relay logok terminálban
  → git log state/ terminálban (üres)

[0:05] 8.1 Terraform up
  → [H] terraform apply
  → [CIC-OBS] ProofTrace #1, CommitRef #1 megjelenik
  → Képernyőn: state/ első commit, prooftrace.json tartalma

[0:10] 8.2 5× kézi módosítás
  → [H] 5x kézi SSH módosítás (VyOS szabályok)
  → [CIC-OBS] 5 commit pörög state/ ágon
  → Képernyőn: SOFT_DRIFT, RECONCILIABLE_DRIFT jelölések

[0:20] 8.3 Infra törlés
  → [H] terraform destroy
  → [CIC-OBS] HARD_DRIFT commit
  → Képernyőn: actual_state={}, ProofTrace lánc megmarad

[0:25] 8.4 Rollback
  → [H] git merge + git push intent/main
  → [CIC-ACT] OIS ellenőrzés + terraform apply trigger
  → Képernyőn: infra újjáépül, új CommitRef ← #3

[0:30] Összefoglalás
  → git log state/ — teljes lánc látható
  → git verify-commit HEAD — aláírás érvényes
  → "Nem az ember mondja, hogy igaz. A láncolat bizonyítja."
```

---

## PoC v2 (tájékoztató, nem scope)

- Talos cluster + Gitea + Nexus + CloudNativePG + Prom/Grafana
- WASM iSDK éles plugin betöltés
- CICSourceCA Vault signing aktiválás
- PoSE VERIFIED mód

## PoC v3 (tájékoztató, nem scope)

- Két telephely, k8s, titkosított kapcsolat
- Elosztott ProofTrace lánc
