# base-repo-explore-01 — base-repo megértése

## Célod

Ismerd meg a `base-repo` main branch-ét, a release folyamatát, és a branch struktúrájából adódó egyediségét.
Ez **csak olvasás és elemzés** — semmit nem módosítasz sehol.

A kimenet meghatározza, hogyan érdemes a release mintát + Renovate-et adaptálni a CIC ökoszisztémára (CIC-Relay, base-repo-golang).

---

## Forrás repo helye

```
/home/sinkog/sync/git.partners/CentralInfraCore/base-repo
```

Ez egy lokális klón — csak olvasható. Ne futtass Docker-t, ne inicializálj hookot.

---

## Háttér — amit a task kiadásakor már tudunk

A base-repo egy **"Template Factory"**: nem végtermék, hanem sablon, amelyből downstream (production) repók jönnek létre.

- Két meglévő release tag: `base@0.5.0` és `schemas@v0.9.0` — ezeket Renovate figyeli
- A repo **több specializációs branch-et** tartalmaz (`golang/main`, `golang/devel`, `schemas/main`, `schemas/devel`, `IaC/devel`) — ezek különböző downstream repo típusoknak szólnak
- A CIC-Relay egy Go-alapú downstream — valószínűleg a `golang/main` branch a releváns sablon
- A release terjesztése Renovate-en keresztül működik: tag → Renovate PR a downstream repo-ban
- Jelenleg CIC-Relay-en már van Renovate (`LOG_LEVEL: debug` maradt bent, ezt is jegyezd fel), de a base-repo release mintáját még nem kapta meg

---

## Feladatok

### 1. Main branch tartalom — mi van itt?

Olvasd el a következő fájlokat és értsd meg a szerepüket:

```bash
ls /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/docs/en/architecture.md
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/docs/en/workflow.md
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/Makefile
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/mk/infra.mk
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/.github/workflows/ci.yml
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/renovate.json
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/project.yaml
```

Azonosítsd: mi a **release artifact** formátuma a base-repo saját kontextusában?

### 2. Release folyamat elemzése

```bash
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/tools/release.sh
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/tools/finalize_release.py
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/tools/compiler.py
```

Azonosítsd:
- Mi a release lépései sorban (tag mikor keletkezik, mi kerül a release branch-re)
- Hogyan kapcsolódik a Vault signing a release-hez
- Mi az a `template-schema` és hogyan viszonyul a base release taghoz

### 3. Branch struktúra feltérképezése

```bash
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo branch -a
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo log --oneline --all --graph | head -40
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show-ref --tags
```

Majd olvasd el a specializációs branch-ek Makefile-ját és CI-ját (ha eltér a main-től):

```bash
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show golang/main:Makefile 2>/dev/null | head -60
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show golang/main:.github/workflows/ci.yml 2>/dev/null
git -C /home/sinkog/sync/git.partners/CentralInfraCore/base-repo show schemas/main:Makefile 2>/dev/null | head -60
```

Azonosítsd:
- Miben tér el a `golang/main` branch a `main`-től
- Miért van külön `golang/main` — mi a specializáció logikája
- Hogyan kap update-et egy specializációs branch a `main`-ből (merge-elve van? rebase-elve?)
- A tag-ek melyik branch-hez kötöttek (`base@0.5.0` melyik commithoz tartozik)

### 4. Renovate integráció logikája

```bash
cat /home/sinkog/sync/git.partners/CentralInfraCore/base-repo/renovate.json
```

Kérdések:
- Hogyan figyeli Renovate a base-repo tagjait más repo-kban?
- Milyen Renovate konfiguráció kellene egy downstream repo-ban (pl. CIC-Relay) ahhoz, hogy `base@0.5.0` → `base@0.6.0` automatikus PR legyen?
- Melyik Renovate manager kezeli a Git tag-alapú sablonfrissítéseket?

Ha nem tudod a Renovate konfigból megmondani, jegyezd fel mint nyitott kérdés.

### 5. CIC-Relay adaptálhatóság vizsgálata

A CIC-Relay:
- Go-alapú repo
- `main` branch van (nincs devel/main kettősség)
- Saját Makefile, `.github/workflows/verify.yml`, `.github/workflows/renovate.yml`
- Vault signing: `commit-msg` hook, `cic-my-sign-key`

Kérdések:
- Melyik base-repo branch (main vs golang/main) a releváns sablon?
- Milyen fájlok kerülnének át remote-merge során (Makefile? mk/? .github/workflows/? renovate.json?)
- Melyik fájlok **nem** kerülhetnek át változtatás nélkül (mert CIC-Relay specifikusak)?
- A CIC-Relay Makefile és CI hogyan viszonyul a base-repo golang/main változatához — overlapping, kiegészítő, vagy ütköző?

---

## Output fájlok

### `output/base-repo-analysis.md`

```markdown
## Main branch tartalma és szerepe
[Mi a template factory lényege, mi kerül a release artifact-ba]

## Release folyamat — lépések sorban
[Tag mikor keletkezik, mi a release branch, Vault kapcsolódása]

## Branch struktúra és specializáció logikája
[Miért van golang/main, hogyan terjed az update főágból a specializációba]

## Renovate logika
[Hogyan propagál a tag → downstream PR, milyen konfig kell]

## CIC-Relay adaptálhatóság
[Melyik fájlok jönnek át, melyik nem, mi kell módosítás]

## Nyitott kérdések
[Amit nem lehetett megmondani a lokális adatokból]
```

### `output/relay-delta.md`

Konkrét összehasonlítás: mi van CIC-Relay-ben, mi van base-repo golang/main-ban, hol van delta.

| Fájl / terület | base-repo golang/main | CIC-Relay main | Delta / teendő |
|---|---|---|---|
| Makefile | ... | ... | ... |
| .github/workflows/ci.yml | ... | ... | ... |
| renovate.json | ... | ... | ... |
| signing hook | ... | ... | ... |

### `output/claim-evidence.md`

| Állítás | Státusz | Bizonyíték (fájl/sor) |
|---|---|---|
| base@0.5.0 tag melyik commithoz tartozik | true/false | git show-ref output |
| golang/main eltéréseit azonosítottam | true/false | konkrét diff vagy fájl neve |
| Release lépések sorban dokumentálva | true/false | tools/release.sh elolvasva |
| CIC-Relay Makefile vs golang/main Makefile összehasonlítva | true/false | konkrét delta |

---

## Szabályok

- **Fájl listázás ≠ megértés** — olvasd el, ne csak `ls`-ezd
- **Nyitott kérdés jelzése kötelező** — ha nem tudod megmondani, mondd meg és miért
- Semmit nem módosítasz — sem base-repo-ban, sem CIC-Relay-ben, sem cic-factory-ban
- A job outputja lesz az alap a következő job-hoz (release minta + Renovate implementáció)
