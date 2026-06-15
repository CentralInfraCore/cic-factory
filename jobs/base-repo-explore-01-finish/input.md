# base-repo-explore-01-finish — a megszakadt base-repo-explore-01 munka befejezése

## Reasoning mód

**audit** — a `base-repo-explore-01` job session-limit miatt megszakadt munkájának
befejezése a mentett munkaállapotból. **Ne kezdd elölről, ne tervezd újra, ne
gyűjtsd újra az anyagot.**

## Kontextus

A `base-repo-explore-01` agent 2026-06-14 19:35Z-kor session limitbe ütközött, mielőtt
commitolt vagy pusholt volna. A feladat (lásd `jobs/base-repo-explore-01/input.md` —
**ez a teljes eredeti DoD, a "Szabályok" szakasz erre a jobra is változatlanul él**)
2 a 3 kért output fájlból elkészült, **kiváló minőségben, konkrét file:line
hivatkozásokkal**:

- `output/base-repo-analysis.md` — KÉSZ (128 sor)
- `output/relay-delta.md` — KÉSZ (23 sor)
- `output/claim-evidence.md` — **HIÁNYZIK**

A teljes munkaállapot mentve:
```
${CIC_WORKDIR}/jobs/base-repo-explore-01/workspace-saved/cic-factory
```
(feature branch: `feature/base-repo-explore-01`; a két kész output fájl a
`jobs/base-repo-explore-01/output/` alatt van, **uncommitted**.)

## Feladat

### 1. Mentett állapot átvétele — NE klónozd újra, NE menj vissza a base-repo-hoz

A saját workspace-edbe másold a mentett klónt:
```bash
cp -a ${CIC_WORKDIR}/jobs/base-repo-explore-01/workspace-saved/cic-factory <saját-workspace>/cic-factory
cd <saját-workspace>/cic-factory
git checkout -b feature/base-repo-explore-01-finish
```

Olvasd el a két meglévő output fájlt (`jobs/base-repo-explore-01/output/base-repo-analysis.md`
és `relay-delta.md`) — ezek **véglegesek, ne írd át, ne bővítsd**, csak ezekre
hivatkozva építsd fel a `claim-evidence.md`-t.

### 2. `claim-evidence.md` elkészítése

A `base-repo-analysis.md` és `relay-delta.md` minden érdemi állítását vedd végig, és
minden egyes állításhoz add meg: a forrás file:line hivatkozást (ami már szerepel a
két meglévő fájlban), és — ahol ez még nem történt meg — **futtasd le az ellenőrző
parancsot** és idézd a kimenetét. Konkrétan, ellenőrizendő/idézendő tételek:

- `base@0.5.0` tag → `be0617888654a5cfb764bd62a37d4aee22bd6ee8` — `git -C
  /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show-ref --tags` kimenet
  idézve.
- `schemas@v0.9.0` tag → `c3491c96f06200a32ecf140777891cfbbd740de5` — ugyanaz a
  parancs, ugyanaz a kimenet felhasználható.
- `golang/main` elavultsága (`merge-base main origin/golang/main` = `133e5ca`) —
  `git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo merge-base main
  origin/golang/main` kimenet idézve.
- `schemas/main` szinkron állapota (`merge-base main origin/schemas/main` = `d286cb8`)
  — ugyanúgy `git merge-base` kimenet idézve.
- `mk/infra.mk` byte-azonosság base-repo `main` vs CIC-Relay — `diff <(git -C
  /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show main:mk/infra.mk)
  <(git -C <CIC-Relay-klón-path> show main:mk/infra.mk)` kimenet idézve (ha a
  CIC-Relay lokális klón elérhető a gépen; ha nem, jelezd nyitott kérdésként —
  **ne találj ki klón-path-ot**).
- `tools/git_hook_commit-msg.sh` CIC-Relay-specifikus extra blokkja — `git -C
  <CIC-Relay-klón-path> show main:tools/git_hook_commit-msg.sh | diff - <(git -C
  /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show
  main:tools/git_hook_commit-msg.sh)` kimenet idézve.
- `wasm/main` branch protection 404 (a "Nyitott kérdések" 5. pontja) — idézd a
  `gh api repos/CentralInfraCore/base-repo/branches/wasm%2Fmain/protection` kimenetét.

Ha egy ellenőrző parancs futtatása közben az eredmény **eltér** a `base-repo-analysis.md`/
`relay-delta.md` állításától, **ne hallgasd el** — jelöld `FALSE`-ként, és írd be a
tényleges eredményt + egy rövid megjegyzést a `claim-evidence.md`-be (a két meglévő
fájlt ne módosítsd).

A táblázat formátuma (egy sorban, K8 miatt):

```
| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
```

**"A fájl létezése ≠ az állítások igazolása"** — minden táblázat-sornak saját,
frissen futtatott bizonyítéka legyen, ne csak a meglévő fájlra mutató hivatkozás.

### Reachability / N/A indoklás

Ez egy Python/YAML/Git-konfigurációs audit (`base-repo` release-infrastruktúra,
nem Go forráskód) — `grep -rn`-alapú call-chain ellenőrzés és `deadcode ./...`
N/A. A `_test.go` kizárás sem releváns (nincs Go production szimbólum). A
fenti `git show-ref`/`git merge-base`/`diff`/`gh api` parancsok adják a
runtime-bizonyítékot ehhez a job-hoz.

### 3. Commit + push

```bash
git add jobs/base-repo-explore-01/output/
git commit -m "job: base-repo-explore-01 — output (analysis, relay-delta, claim-evidence)"
git push -u origin feature/base-repo-explore-01-finish
```

### 4. Saját riport

Írj egy rövid (10-15 soros) `jobs/base-repo-explore-01-finish/output/finish-report.md`-t:
mi készült el, hány claim-evidence sor lett `TRUE`/`FALSE`, és ha volt eltérés a
korábbi állításokhoz képest, sorold fel.

---

## Output

- `jobs/base-repo-explore-01/output/claim-evidence.md` (a meglévő `base-repo-analysis.md`
  és `relay-delta.md` mellé, **azokat nem módosítva**)
- `jobs/base-repo-explore-01-finish/output/finish-report.md`

## Git instrukciók

- `cic-factory`: commit + push **csak** `feature/base-repo-explore-01-finish`-ra.
- Semmilyen más repóba (`base-repo`, `CIC-Relay`) nem írsz — ez is **csak olvasás**.

## Nyelvi szabály

- Riport és output: **magyarul**
- Parancsok, idézett kimenetek: ahogy érkeznek (angol/technikai)
