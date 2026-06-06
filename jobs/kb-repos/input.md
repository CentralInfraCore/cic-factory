# Feladat: CIC repo tudásbázis — kétnyelvű md/yaml dokumentumok

## Kontextus

Az előző jobokban feltérképezett CIC ökoszisztéma repóiról kétnyelvű (hu/en) tudásbázis dokumentumokat kell létrehozni a `github_private` (CIC-basic-knowledge) repóban, a meglévő KB formátumát követve.

## Forrásinformációk

Olvasd el ezeket az előző job kimeneteiből:
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/map-private-source/output/repos.yaml`
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/deep-inspect-private-repos/output/CIC_Relay.md`
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/deep-inspect-private-repos/output/CIC_Schemas.md`
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/deep-inspect-private-repos/output/cic-mcp-private.md`
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/deep-inspect-private-repos/output/github_private.md`
- `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/deep-inspect-private-repos/output/connections.md`

## Workplace — git clone

Klónozd a `github_private` repót a workplace könyvtárba, devel branch-re:

```bash
git clone git@github.com:CentralInfraCore/github_private.git \
  /home/sinkog/sync/claude_factory/CIC/workdir/jobs/kb-repos/workplace/github_private
cd /home/sinkog/sync/claude_factory/CIC/workdir/jobs/kb-repos/workplace/github_private
git checkout devel
```

## Meglévő KB formátum — kötelező betartani

A `workplace/github_private/docs/` könyvtárban nézd meg az existáló md/yaml párokat, különösen:
- `docs/hu/meta/cic.md` + `docs/hu/meta/cic.yaml`
- `docs/en/meta/cic.md` + `docs/en/meta/cic.yaml`

Ez a pontos formátum amit követni kell.

### Standard companion YAML mezők:
```yaml
tags: []
related_nodes: []
category: []
used_in: []
description: |
  ...
```

### Repo-specifikus evidence réteg (ezeket ADD HOZZÁ minden repo YAML-hoz):
```yaml
repo:
  remote: ""               # git remote URL
  primary_language: ""     # go | python | yaml | ndjson | mixed
  status: ""               # implemented | scaffold | concept
  entry_point: ""          # fő belépési pont fájl, "" ha nem kód
  vault_role: ""           # none | consumer | signer | consumer+signer
  kb_indexed: true         # make_source.py indexeli-e
  scaffold_items: []       # szándékos helyőrzők listája (csak ha vannak)
  related_repos: []        # kapcsolódó repo remote URL-ek
```

## Könyvtárstruktúra amit létre kell hozni

```
docs/
  hu/
    repos/
      index.md + index.yaml          # összefoglaló, belépési pont
      cic-relay.md + cic-relay.yaml
      cic-schemas.md + cic-schemas.yaml
      cic-mcp-private.md + cic-mcp-private.yaml
      github-private.md + github-private.yaml
      cic-primitives.md + cic-primitives.yaml
      cic-compute.md + cic-compute.yaml
      cic-kubernetes.md + cic-kubernetes.yaml
      cic-network.md + cic-network.yaml
      cic-storage.md + cic-storage.yaml
      cic-yang.md + cic-yang.yaml
      base-repo.md + base-repo.yaml
      ois-github.md + ois-github.yaml
  en/
    repos/
      (ugyanez, angol tartalommal)
```

## Tartalmi elvárások

### Magyar (.md) fájlok:
- Természetes, folyó magyar szöveg — nem fordítás, hanem natív fogalmazás
- Mit csinál ez a repo a CIC rendszerben?
- Milyen rétegben helyezkedik el (fogalmi alap / schema / runtime / tooling)?
- Mik a kulcs komponensei?
- Mi van scaffold/concept állapotban és miért?
- Hogyan kapcsolódik a többi repóhoz?

### English (.md) fájlok:
- Native English prose
- Same structure, independent writing (not translated from Hungarian)

### YAML fájlok:
- `description` mindig angolul (standard KB konvenció)
- `related_nodes` formátuma: `docs/hu/repos/cic-relay` (relatív path, kiterjesztés nélkül)
- `entrypoint: true` csak az `index.yaml`-ban

## FONTOS: Ne commitolj!

A fájlok megírása után:
1. Futtasd le: `git status` és `git diff --stat` a workplace-ben
2. Írd ki az eredményt: `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/kb-repos/output/diff-summary.md`
3. **Ne futtass `git add`, `git commit` vagy `git push` parancsot!**

A review és commit a szülő session feladata.
