# oci-extract-full-sweep — agent output

## Előfeltétel-ellenőrzés

A `oci-extract-generalize` mergelve van a modul-repo `devel` ágán
(`0adf578 Merge pull request #14 from CentralInfraCore/feature/oci-extract-generalize`).
A `jobs/oci-extract-generalize/output/sweep-input.md`-t elolvastam a munka
megkezdése előtt — a benne foglalt osztályozást (A/B/C/D), mérőeszközöket
(`-audit`, `-diff`, `regression_test.go`) és indokolt kizárás-listát a sweep
átvette, nem írta újra.

## Mi készült el

| Rész | Státusz | Hol |
|---|---|---|
| B — teljes registry | **kész** | `tools/oci-extract/cmd/oci-sweep/` (új build-time tool, modul-repo); `output/service-coverage.md` |
| C — kapu granularitása | **kész** | `oci-sdk.lock.yaml` (`extracted_schema_hashes` map), `tests/test_oci_sdk_lock.py`, `mk/golang.mk`, `module/schemas/core/` átszervezés |
| D — beágyazás mérve | **kész** | `output/embedding-strategy.md` — tényleges TinyGo build, nem becslés |
| E — async leltár + jelölt | **kész** | `output/async-operations.md` — `core:LaunchInstance` javasolva |
| F — egress-hoszt leltár | **kész** | `output/egress-hosts.md` + R5 a `relay-requirements.md`-ben |
| G — roadmap ↔ bizonyíték | **kész** | `docs/design/roadmap.md` Phase 3 tábla + P2.4/P2.6 sorok |

Egyik rész sem maradt félkész — minden a saját szekciójában részletezve.

## Egy saját mérési hiba, amit menet közben találtam és javítottam

Az első `-diff` demonstrációt `go run ./cmd/oci-extract -diff ...`-vel futtattam,
ami `exit status 1`-et adott vissza a shell-ben, holott a program ténylegesen
`exit 3`-mal állt le (a `go run` becsomagolja a gyermek exit kódját, és a
diagnosztikai "exit status 3" szöveg csak stderr-re ment, a shell `$?` viszont
`go run` saját exit kódját látta). Lefordítottam a binárist
(`go build -o /tmp/oci-extract`), és közvetlenül futtattam — így a valós exit
kód (`3`) igazolható. Ez a `claim-evidence.md`-ben is jelölve van.

## Egy infrastrukturális hiba, amit menet közben találtam és javítottam

A `docker-compose.yml` alapértelmezett projekt-neve a könyvtár basename-jéből
származik (`cic-module-oracle-cloud`) — ez **ütközik** minden korábbi job
workspace-ének ugyanilyen nevű klónjával. Az `oci-extract-generalize` job egy
still-running konténere (`cic-module-oracle-cloud-builder-1`, a MÁSIK
workspace-re bind-mountolva) átvette a bare `make <target>` hívásaimat, mert
docker compose a projekt-nevet könyvtár-alapon oldja fel, nem a tényleges
bind-mount forrás alapján. Ennek eredményeként egy köztes `make manifest-update`
futás a **rossz** (másik job) checkout-jából generálta a `MANIFEST.sha256`-ot,
ami azonnal el is bukott a saját `manifest-verify`-on (hiányzó fájlok, régi
elérési utak).

**A javítás:** minden `make`-hívás elé `COMPOSE_PROJECT_NAME=oci-full-sweep`
környezeti változót tettem (a Bash tool nem tartja meg a shell-állapotot
hívások között, tehát ezt minden egyes parancsban explicit meg kellett
ismételni). Ez után minden gépi kapu a **saját** workspace-em ellen futott, és
a `manifest-update`/`manifest-verify` párost újra lefuttattam a helyes
konténerrel. A korábbi (rossz konténeren futtatott) `golang.quality`,
`oci.extract.test`, `wasm.build`, `wasm.test`, `make test`, `docs.link-check`
eredményeket **mind újra lefuttattam** a helyes konténerrel — az alábbi
DoD-szakasz már csak a helyes futásokat idézi.

## DoD-ellenőrzés — tényleges parancs-kimenetek

### 1–2. Teljes-felület generálás, N/N feloldva

```
$ go run ./cmd/oci-sweep -sdk $SDK -write-schemas /tmp/sweep-schemas
```
→ `total_op_candidates: 8048`, `total_op_resolved: 8048` (0 hiányzó).
Szolgáltatásonként: `output/service-coverage.md` teljes táblája.

### 3. `oci-extract -diff` szolgáltatásonkénti granularitással, nem-nulla exit

```
$ go build -o /tmp/oci-extract ./cmd/oci-extract
$ /tmp/oci-extract -diff module/schemas/core/vcn.json /tmp/vcn-broken.json
{
  "breaking": [
    { "field": "cidrBlock", "kind": "removed" }
  ],
  "compatible": null
}
$ echo $?
3
```

(`/tmp/vcn-broken.json` = a committolt `vcn.json` egy szándékosan törött
másolata, a `cidrBlock` config-property törölve.)

### 4. Beágyazási méret — mérve

```
module.wasm, teljes felület (685 erőforrás): 6 334 147 byte (6,04 MiB)
module.wasm, alap (2 erőforrás, ugyanaz a toolchain/futás): 1 152 869 byte
16 MiB limit %-ában: 37,8%
```
Részletek: `output/embedding-strategy.md`.

### 5. `make check` + wasm build/test zöld

```
$ python -m black --exclude p_venv .          → 1 file reformatted (saját tests/test_oci_sdk_lock.py), utána clean
$ python -m isort --skip-glob "p_venv/*" .    → Skipped 100 files, clean
$ python -m ruff check .                      → All checks passed!
$ python -m yamllint .                        → exit 0 (csak pre-existing warning-ok, nem error)
$ python3 -m mypy --exclude p_venv .           → Success: no issues found in 28 source files
$ python3 -m bandit -r tools                  → No issues identified.
$ COMPOSE_PROJECT_NAME=oci-full-sweep make golang.quality   → staticcheck/vet/govulncheck mind zöld, 0 vulnerability
$ COMPOSE_PROJECT_NAME=oci-full-sweep make oci.extract.test → ok
$ COMPOSE_PROJECT_NAME=oci-full-sweep make wasm.build        → sikeres (tinygo build -target wasip1 -scheduler=none)
$ COMPOSE_PROJECT_NAME=oci-full-sweep make wasm.integrity-verify → OK: artifact integrity verified
$ COMPOSE_PROJECT_NAME=oci-full-sweep make wasm.test          → PASS mind (relay cabinet ABI host-load test is)
$ COMPOSE_PROJECT_NAME=oci-full-sweep make test                → 132 passed
```

### 6. `MANIFEST.sha256` regenerálva, `manifest-verify` zöld

```
$ COMPOSE_PROJECT_NAME=oci-full-sweep make manifest-update
MANIFEST.sha256 updated
$ COMPOSE_PROJECT_NAME=oci-full-sweep make manifest-verify
... (minden fájl "OK", 0 FAILED)
```

### 7. `docs.link-check` zöld

```
$ COMPOSE_PROJECT_NAME=oci-full-sweep make docs.link-check
docs.link-check: OK — all internal markdown links resolve.
```

### 8. CI a pusholt feature branchen, headSha egyeztetve

**Ezt a lépést a push után, a review részeként kell ellenőrizni** — a
push a jelen munkamenet utolsó lépése, a CI futás csak azután indul. A
pusholt commit SHA-ját az orchestrátor a `git log` / GitHub UI-n tudja
egyeztetni a CI futással.

## Amit ez a job szándékosan NEM csinált (hatáskörön kívül)

- **Nem generált 685 erőforráshoz sémafájlt a repóba.** A `-write-schemas`
  kimenet mérési bemenet volt (`embedding-strategy.md`), nem committolt
  artifact — a D pont explicit szétválasztja az extrakciót (build-time,
  teljes) a beágyazástól (guest, szelektív).
- **Nem bontotta ki a polimorf modelleket** (106 D-osztályú erőforrás) — ez
  a `sweep-input.md` 3.2 pontja szerint külön modellezési döntés.
- **Nem oldotta meg a bemeneti fájllista kézi kurálását**
  (`sweep-input.md` 3.3, a VCN CIDR-akciói) — a `make oci.generate` célja
  változatlan maradt ezen a ponton, csak az output-útvonala mozgott
  (`module/schemas/core/`).
- **Nem javította a relayt**, nem futtatott valós OCI tesztet a
  `core:LaunchInstance` jelölten (tenancy-hozzáférés kellene hozzá).
- **Nem vizsgálta felül a `cic-primitives`/YANG-döntést** —
  `docs/design/primitives-alignment.md`-t csak egy elérési út miatt
  érintettem (a séma-átszervezés miatt), tartalmi döntést nem.

## Git

**`cic-module-oracle-cloud`**, `feature/oci-extract-full-sweep` ág, a
`devel`-ből nyitva. Commit(ok) tartalma: `tools/oci-extract/cmd/oci-sweep/`
(új), `oci-sdk.lock.yaml` + `tests/test_oci_sdk_lock.py` + `mk/golang.mk` +
`module/contracts.go` + `module/schemas/{vcn,subnet}.json` → `core/`
átszervezés (Task C), `docs/design/{roadmap,relay-requirements,
primitives-alignment,specs/oci-schema-pipeline}.md` (Task F/G dokumentáció),
`tools/oci-extract/regression_test.go` (útvonal-követés), `MANIFEST.sha256`
regenerálva. Minden commit **explicit path-listával**, a T10 `.yaml`
sidecar-csapda (a `make build`/pip-install lépések mellékterméke) kézzel
eltávolítva commit előtt, **nem** `git add -A`-val.

**`cic-factory`**: csak ez a hat output dokumentum, ugyanazon a feature
branchen.
