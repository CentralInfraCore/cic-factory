# relay-func-audit — Relay funkcionalitás audit

## Célod

A CIC Relay részletes funkcionalitás-auditja: **KB definíció vs. tényleges Go forráskód**.

Az auditot a Go forráskódon végzed — nem a metaadatokon, nem az agent summarykon. Minden állításod Go fájlra + funkcióra hivatkozik.

## Relay forráskód helye

```
/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay/
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
2. **Mekkora az implementáció?** — teljes / stub / hiányzó
3. **Státusz meghatározás:**
   - `implemented` — kódban él, nem stub, tesztek lefedik
   - `scaffold` — kódban van (interface, struct, placeholder), de szándékosan nem bekötött
   - `concept` — KB-ban szerepel, de nincs Go megfelelője

4. **Hiány jellemzése** — scaffold/concept esetén: mi hiányzik pontosan?

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

`output/gap-summary.md` — Összesítő:
- Implemented komponensek listája
- Scaffold komponensek listája (mi az előfeltétel?)
- Concept komponensek listája (KB-ban van, Go-ban nincs)
- PoC-hoz szükséges, de hiányzó elemek

## Fontos szabályok

- **Csak Go forráskód alapján** — ne fogadd el a KB leírást implementáltnak
- Ha egy Go fájl létezik de minden metódus `return nil, errors.New("not implemented")` vagy hasonló — az **scaffold**, nem implemented
- Ha egy interfész definiált de nincs konkrét implementáció — **scaffold**
- Ha a KB ír valamiről de nincs Go fájl — **concept**
- Teszt fájlokat (`_test.go`) ne számíts implementációnak, de jelezd ha csak tesztben szerepel valami
- `mock_*.go` fájlok és testdata — nem implementáció
