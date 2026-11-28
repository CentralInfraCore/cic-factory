# Factory backlog: a munkacsomag Git-bázisának mechanikus igazolása (nincs implementáció)

**Státusz:** backlog-tétel és **új acceptance követelmény**, a `factory-backlog-local-gate-parity.md` és a `factory-backlog-mutation-isolation.md` mellé. Implementáció nincs.

**Eset (O-1 integráció, 2026-11-28):** a WP-04 modul-PR (#54) jelentése szerint a bázis `devel` `ae3c962` volt "unchanged at push"; a **tényleges merge-base `5d0a327` volt, 63 commit-tal a `devel` mögött**, a PR `CONFLICTING/DIRTY`. A zöld CI egy elavult bázison futott. A szöveges ágens-állítás nem volt evidence.

## Követelmények

| # | Követelmény |
|---|---|
| B-1 | A job specifikációban rögzített **előírt base SHA**-t a gyár **mechanikusan** ellenőrzi: `git merge-base <ág> <előírt base>` egyezik az előírt base-szel (vagy az ág a base leszármazottja). |
| B-2 | A job lezárásakor a jelentés tartalmazza a `git merge-base`, a `git rev-list --count <base>..<ág>` és a **munkacsomag saját delta**-ját (`git diff --stat <merge-base> <ág>`). |
| B-3 | Ha a cél-ág (pl. `devel`) az ág létrehozása óta előrehaladt, a gyár **jelzi** (`git rev-list --count <merge-base>..<cél-ág>`), és a PR `mergeable` állapotát (`gh pr view --json mergeable,mergeStateStatus`) a jelentésbe veszi. |
| B-4 | A munkacsomag **saját módosításait** (a merge-base és az ág csúcsa közti diff) el kell választani az elavult bázisból származó eltérésektől: a jelentés csak előbbit tekintheti a munkacsomag eredményének. |
| B-5 | A zöld CI csak akkor számít acceptance-nek, ha a **PR a célágra mergelhető** (nem `DIRTY`/`CONFLICTING`) az előírt cél-állapotra. |
| B-6 | A szöveges ágens-állítás a bázisról önmagában **nem evidence**; csak a mechanikusan előállított értékek számítanak. |

**Hatókör:** általános Factory-képesség (`cic-factory-core` jelölt). Külön engedélyezési pont; most nem indul implementáció.
