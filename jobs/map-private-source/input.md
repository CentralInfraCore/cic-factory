# Feladat: Private source könyvtár feltérképezése

## Cél

Térképezd fel a `/home/sinkog/sync/git.partners/CentralInfraCore/MCPs/private/source/` könyvtárat és állíts össze egy átfogó képet, amelyet jövőbeli Claude session-ök közvetlenül felhasználhatnak a rendszer üzemeltetéséhez.

## Mit kell összegyűjteni

Minden megtalált repóhoz:
- Teljes lokális path
- `git remote get-url origin` — ha van remote
- Rövid leírás: mi ez, mire való (README vagy könyvtárstruktúra alapján)
- Főbb alkönyvtárak / modulok (max 2 szint mélység)
- Kapcsolódó repók (ha hivatkozik másikra, pl. go.mod, import, config)

## Kimeneti fájlok

Írj a következő két fájlba:

### `output/overview.md`
Embernek olvasható átfogó kép: mi ez az egész rendszer, hogyan függnek össze a repók, mi a belső struktúra logikája.

### `output/repos.yaml`
Gépileg feldolgozható leltár az alábbi struktúrában:

```yaml
repos:
  - id: ""          # rövid azonosító, pl. "cic-relay"
    local_path: ""
    remote_url: ""  # "" ha nincs remote
    description: ""
    top_level_dirs: []
    related_repos: []
```

## Fontos

- Ha egy könyvtár nem git repo, azt is vedd fel (id-ben jelezd: `non-git/...`)
- Ne hagyd ki a rejtett könyvtárakat ha relevánsak (pl. `.github/`)
- A kimeneti fájlokat abszolút path-on írd: `/home/sinkog/sync/claude_factory/CIC/workdir/jobs/map-private-source/output/`
