# poc-relay-wiring-01 — Relay → ProofTrace bekötés és state/ ág bridge

## Feladat összefoglalása

A CIC-Relay scaffold elemek befejezése és a PoC demo állományhoz szükséges bridge megvalósítása. Két konkrét területre fókuszálj:

1. **IaC FileSource befejezése (M11.1–M11.4)** — A `core/nexus/iac` modul `FileSource` implementációja jelenleg scaffold állapotban van (M11 roadmap). A `FileSource` rekurzívan olvassa be a YAML fájlokat és felépíti a `Relay→Host→Service` gráfot a memóriában.

2. **Recorder → state/ ág bridge** — A `core/nexus/recorder/recorder.go` jelenleg git-alapú audit commitot ír egy konfigurált audit repóba. A PoC-hoz szükséges, hogy a ProofTrace kimenet egy **különálló `state/` ágba** is kerüljön, az alábbi struktúrával:
   ```
   state/ ág → commit
     ├── infra.tf.json        ← desired state (Terraform input)
     ├── actual_state.json    ← tényleges állapot (PBS snapshot helyett: Terraform state output)
     └── prooftrace.json      ← ProofTrace entitás (hash, aláírás)
   ```

## Elvégzendő lépések

### 1. IaC FileSource befejezése

A `core/nexus/iac` csomagban:
- `IaCSource` interfész legyen definiálva (ha még nincs)
- `FileSource` struct: rekurzív YAML betöltés a megadott könyvtárból
- Betöltési logika: `kind: Relay`, `kind: Host`, `kind: Service` YAML fájlok feldolgozása
- Gráfépítés: `Relay` → `Host` → `Service` él kapcsolatok memóriában
- `FetchConfig()` metódus implementálása
- `ExpectedState` objektum generálása a gráfból
- Egységtesztek: legalább 1 golden testdata készlet (lásd `core/nexus/iac/testdata/relay.yaml` meglévő minta)

A meglévő `core/nexus/iac/testdata/relay.yaml`:
```yaml
apiVersion: cic/v1
kind: Relay
metadata:
  name: test-relay
spec:
  hosts:
  - hosts/host-01.yaml
```

### 2. Recorder → state/ ág bridge

A `core/nexus/recorder` csomagban (vagy új `core/nexus/statewriter` csomagban):
- `StateWriter` interface: `WriteState(desiredState, actualState, proofTrace ProofTrace) error`
- `GitStateWriter` implementáció: git-alapú commit a `state/` ágra
- A `prooftrace.json` tartalma: a `ProofTrace` struct canonical JSON formátuma
- Vault aláírás: ha elérhető, az aláírás is bekerül a `prooftrace.json`-be
- Ha `state/` ág nem létezik: létrehozza (`git checkout -b state/main`)
- A `cmd/relay/main.go` `buildRecorderOption`-ba bekötve (új env: `CIC_STATE_REPO_PATH`)

### 3. Integráció ellenőrzése

- `make test` zöld
- `make verify` zöld (golden fájlok)
- Manuális próba: relay fut, `Setx` workflow → state/ ágon megjelenik a commit

## Fontos megszorítások

- Ne változtasd meg a `Cabinet` interfészt
- A `pki_verify.go` scaffold marad — ne aktiváld
- Az `UpstreamSource` scaffold marad — ne implementáld
- Vault hiányában a `statewriter` WARN-t logol és folytatja (nem fatal)
- Canonical JSON kötelező a `prooftrace.json`-hez (`pkg/canonicaljson`)

## KB hivatkozások

- M11 roadmap: `core/nexus/iac` FileSource scaffold
- `core/nexus/recorder/recorder.go`: meglévő git audit implementáció
- `ProofTrace` struct: `core/cabinet/proof_trace.yaml`
- `pkg/canonicaljson`: determinisztikus serializer

## Elfogadási kritérium

- [ ] `FileSource.FetchConfig()` visszaad egy valid `ExpectedState`-et a testdata alapján
- [ ] `GitStateWriter.WriteState()` commitot ír a `state/` ágra a megfelelő 3 fájllal
- [ ] `make test` zöld
- [ ] `CIC_STATE_REPO_PATH` env változó dokumentálva a `ai/SYSTEM_CONTEXT.md`-ben
