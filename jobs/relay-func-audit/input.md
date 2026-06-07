# relay-func-audit — Relay funkcionalitás audit

## Célod

A CIC Relay részletes funkcionalitás-auditja: **KB definíció vs. tényleges Go forráskód**.

Az auditot a Go forráskódon végzed — nem a metaadatokon, nem az agent summarykon. Minden állításod Go fájlra + funkcióra hivatkozik.

## Relay forráskód helye

```
${CIC_RELAY_PATH}/
```

Főbb package-ek (nem teszt fájlok):
```
core/cabinet/          — Cabinet: schema/workflow/module/plugin kezelés, ProofTrace
core/modules/          — natív modulok: certselfsigned, cibuild, schemacompile, schemapipeline
core/nexus/crypto/     — Vault/crypto service
core/nexus/git/        — GitOps registry, exec
core/nexus/iac/        — IaC source: file, git, upstream
core/nexus/isolation/  — worker isolation: local, subprocess, IPC
core/nexus/operator/   — lifecycle: bootstrap, watcher
core/nexus/recorder/   — recorder, workflow recorder
core/nexus/sync/       — syncer
core/nexus/types/      — közös típusok
cmd/relay/             — relay entrypoint, handler-ek, middleware
```

## KB lekérdezés

Először gyűjtsd össze a releváns KB node-okat. Kötelező chunk-ok:

```
kb_status
search_nodes(["relay", "cabinet", "workflow", "schema", "module", "plugin", "nexus", "prooftrace", "isolation", "primitives"])
get_chunk("c781")   — Cabinet: schema→workflow→module mappings
get_chunk("c912")   — relay pozicionálás
get_chunk("c927")   — séma belső viselkedés
get_chunk("c365")   — Cabinet interface
```

Ezután: minden releváns node-hoz (`get_node`, `neighbors`) gyűjtsd össze, mit vár el a KB a relay-től.

## Audit feladat

Minden KB koncepció és komponens esetén:

1. **Van-e Go implementáció?** — fájl + csomag + funkció/interfész hivatkozással
2. **Ténylegesen hívódik-e production kódban?** — kötelező `grep` ellenőrzés:
   ```
   grep -rn "<FüggvényNév>" ${CIC_RELAY_PATH}/ \
     --include="*.go" | grep -v "_test.go" | grep -v "mock_" | grep -v "testdata"
   ```
   Ha nulla találat → nem implemented, hanem **scaffold** (kódban van) vagy **concept** (csak definiált).
3. **Mekkora az implementáció?** — teljes / stub / hiányzó
4. **Státusz meghatározás:**
   - `implemented` — kódban él, nem stub, **ÉS production kódban hívódik** (grep bizonyítja)
   - `scaffold` — kódban van, de: (a) production kódban soha nem hívódik, VAGY (b) feltételhez kötött bypass létezik (pl. `if TrustStoreLoaded`), VAGY (c) explicit scaffold/stub comment van
   - `concept` — KB-ban szerepel, de nincs Go megfelelője

5. **Hiány jellemzése** — scaffold/concept esetén: mi hiányzik pontosan?

### Kötelező ellenőrzések minden "implemented" állításhoz

Mielőtt valamit implemented-nek jelölsz, futtasd le:
- `grep -rn "<Függvény>" ... | grep -v "_test.go"` → hány non-test hívási hely?
- Ha 0 → scaffold, nem implemented
- Ha van hívás → megnézed a hívó kódot: feltételhez kötött-e? (`if X != nil`, `if TrustStoreLoaded`, `if secrets != nil`)
  - Ha igen: scaffold (conditional bypass)
  - Ha nem: implemented

## Output fájlok

`output/relay-audit.md` — Strukturált táblázat:

```markdown
## [Komponens neve]

**KB referencia:** [node-id] — [rövid KB leírás]
**Go fájl:** [path] — [csomag/funkció]
**Státusz:** implemented | scaffold | concept
**Lefedettség:**
- [mit implementál ténylegesen a Go kód]
- [mi nincs megvalósítva / mi hiányzik]
**Hiány:** [scaffold/concept esetén: mit kellene még megírni]
```

Külön szakaszok:
- `## Cabinet`
- `## Schema kezelés`
- `## Workflow végrehajtás`
- `## Module rendszer`
- `## Plugin rendszer (WASM)`
- `## ProofTrace`
- `## Nexus: IaC`
- `## Nexus: Git`
- `## Nexus: Isolation`
- `## Nexus: Crypto`
- `## Nexus: Recorder`
- `## Nexus: Operator`
- `## Relay entrypoint és handler-ek`

`output/claim-evidence.md` — Kötelező claim-evidence tábla:

```markdown
| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| [komponens] implemented | true/false/partial | [fájl:sor vagy grep output] | grep / call-chain trace | kritikus/közepes/alacsony |
```

Minden `implemented` és `scaffold` minősítéshez kötelező sor. A tábla nélküli output nem fogadható el.

`output/gap-summary.md` — Összesítő:
- Implemented komponensek listája
- Scaffold komponensek listája (mi az előfeltétel?)
- Concept komponensek listája (KB-ban van, Go-ban nincs)
- PoC-hoz szükséges, de hiányzó elemek

## Fontos szabályok

- **Csak Go forráskód alapján** — ne fogadd el a KB leírást implementáltnak
- **Fájl létezése ≠ implemented** — a funkció kódban van, de hívódik-e? Mindig grep-elj.
- **Teszt lefedettség ≠ implemented** — ha csak tesztben hívódik, az scaffold (vagy concept)
- Ha egy Go fájl létezik de minden metódus `return nil, errors.New("not implemented")` vagy hasonló — **scaffold**
- Ha egy interfész definiált de nincs konkrét implementáció — **scaffold**
- Ha implementált de production kódban soha nem hívódik — **scaffold** (dead code)
- Ha feltételhez kötött bypass van (`if X == nil { skip }`, `if !TrustStoreLoaded { skip }`) — **scaffold**
- Ha a KB ír valamiről de nincs Go fájl — **concept**
- Ha struct mező definiált de sehol nem töltődik ki production kódban — **concept**
- `mock_*.go` fájlok és testdata — nem implementáció
- Explicit `// scaffold`, `// stub`, `// TODO`, `// M3`, `// awaits` kommentek — automatikusan scaffold
