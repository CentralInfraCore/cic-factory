# wasm-release-pipeline-audit — Canonical release path + schemas/main lineage audit

## Reasoning mód

**audit** — ez egy **feltérképező** job, nem implementáció. Célja egy
orchestrátor-szintű architekturális döntés előkészítése: szabad-e a `wasm/*`
ágnak saját release-modellt fejlesztenie (eltérve a `schemas/main`
release-tooling lineage-től), vagy ezt előbb upstream (`schemas/main`)
kellene megcsinálni/tisztázni. **Ne implementálj, ne refactorolj** — a
kimenet egy döntés-előkészítő riport, opcionálisan sub-job spec(ek) a döntés
után induló munkára.

Háttér: a `wasm-template-contracts` job (PR #12, mergelve `wasm/main`-be)
külső review-ja a következő gyanút vetette fel:

> "A `tools/finalize_release.py` körül van egy gyanús régi logika: ott
> mintha `checksum == buildHash` jellegű ellenőrzés szerepelne. Ez
> koncepcionálisan veszélyes lehet, mert a forrás-spec checksum és a WASM
> bináris hash nem ugyanaz a dolog, hanem két külön bizonyíték, amit egy
> aláírásnak együtt kell fednie. A `tools/infra.py` újabb logikája ezt már
> jobban kezeli, de látszik némi örökölt pipeline-réteg."

## Munkakörnyezet

- base-repo klón: `git fetch origin wasm/main` (HEAD `e06ed9c`, tartalmazza
  PR #11+#12-t — ellenőrizd `git log --oneline -3 origin/wasm/main`-nel).
  **Csak olvasásra** — ne ágazz munkabranch-et hozzá, ne commitolj bele.
  Ha mégis branch-elsz (pl. lokális kísérlethez), ne pushold sehova.
- `CIC-Schemas` klón a workspace-edbe (`$CIC_SCHEMAS_PATH` vagy a megadott
  repo URL, ld. `tools/env.sh`) — a `schemas/main` öröklött release-backbone
  összehasonlításához.
- KB: `c1503` (modul-release evidence) + keress további node-okat
  `search_nodes`/`search_query`-vel a "release pipeline", "schemas/main",
  "finalize_release", "buildHash", "checksum" kulcsszavakra — a háromszintű
  státuszt (implemented/scaffold/concept) minden érintett node-ra add meg.

## Feladat

### 1. `tools/finalize_release.py` vs `tools/infra.py` — checksum/buildHash duplikáció

- Olvasd el `tools/finalize_release.py` teljes release-validáló logikáját és
  `tools/infra.py` ekvivalens (újabb) logikáját.
- Azonosítsd **konkrétan** (file:line): hol történik `checksum`/`buildHash`
  összehasonlítás melyik fájlban, mire vonatkozik (forrás-spec checksum vs.
  WASM bináris hash), és van-e átfedés/ellentmondás a két réteg között.
- Grep-eld production call site-okat: melyik make target / CI step hívja
  `finalize_release.py`-t, melyik `infra.py`-t — `grep -rn` a `Makefile`/`mk/*.mk`/
  `.github/workflows/*.yml`-ben, kizárva `_test.go`/`test_*.py`-t.
- Ha `finalize_release.py` nincs sehonnan hívva production útvonalon (csak
  tesztből), mondd ki **dead code**-nak — ne "implemented"-nek, csak mert a
  fájl létezik és van rá teszt.

### 2. `project.schema.yaml` / release-mezők eredete a `schemas/main`-ben

- A `CIC-Schemas` repóban (vagy a base-repo `schemas/main` branch-ében, ha az
  a forrás) keress meg azt a réteget, ahonnan a base-repo `project.schema.yaml`
  / `tools/compiler.py` release-validáló logikája származik ("inherit
  schemas/main release backbone" — ld. base-repo `wasm-template-impl`/
  `wasm-template-finish` korábbi riportjai, `450ac0c` commit).
- Azonosítsd: a `wasm/main` ág `project.schema.yaml`/`compiler.py`/`infra.py`
  módosításai (ha vannak az öröklés óta) **divergálnak-e** a `schemas/main`
  jelenlegi állapotától, és ha igen, milyen irányban (wasm-specifikus
  bővítés vs. ellentmondás).

### 3. Canonical release path — mi a jelenlegi tényleges útvonal?

- A jelenlegi (PR #12 utáni) állapotban mi a **tényleges, futtatható**
  release-validációs lánc a wasm modulra? (`make verify`/`validate`/
  `manifest-verify`/`wasm.rebuild-verify`/`finalize_release` — melyik fut,
  melyik csak létezik.)
- Ahol a `docs/contracts/{en,hu}/release-artifact.md` "Target state"/
  "Célállapot" szakasza már leír egy célmodellt (buildHash + ABI manifeszt +
  MANIFEST.sha256 + aláírt bundle) — ez **kompatibilis-e** a `schemas/main`
  öröklött modellel, vagy attól független/divergáló réteg?

## Döntési kérdés a riport végén (kötelező szakasz)

Fogalmazd meg explicit, 2-3 opcióban, mit kell az orchestrátornak eldöntenie:
- pl. "A) `finalize_release.py` dead code, törölhető — wasm-specifikus
  munka folytatható a jelenlegi `infra.py`/`compiler.py` réteg felett,
  nincs divergencia."
- pl. "B) `finalize_release.py` még él egy másik (nem-wasm) ágon —
  törlés/refactor előtt a `schemas/main` upstream-en kell tisztázni."
- pl. "C) a `project.schema.yaml`/`compiler.py` wasm-ági módosításai már
  divergálnak `schemas/main`-től — upstream egyeztetés szükséges mielőtt
  további wasm-specifikus schema-munka (pl. `wasm-template-release-contracts`
  job) folytatódik."

Minden opcióhoz adj meg konkrét file:line / commit hivatkozást, ami az
állítást alátámasztja — ne általános benyomást írj.

## Tiltott rövidítések (kötelező)

- **A fájl léte ≠ aktív pipeline-elem.** `finalize_release.py`-ra és
  `infra.py`-ra is kötelező a production call-site grep (`Makefile`, `mk/*.mk`,
  `.github/workflows/*.yml`), kizárva teszteket.
- **"Hasonló logika" ≠ "ugyanaz a kontraktus".** Ha `checksum`/`buildHash`
  összehasonlítást találsz mindkét fájlban, idézd szó szerint mindkettőt és
  mondd ki konkrétan mire vonatkoznak (forrás-spec vs. bináris).
- **Ne javíts semmit.** Ha implementációs hiányt vagy ellentmondást találsz,
  dokumentáld a riportban — ne nyúlj `tools/infra.py`/`tools/compiler.py`/
  `tools/finalize_release.py`/`project.schema.yaml`-hoz.
- Nincs sub-job spec létrehozása **kötelezően** — csak ha a döntési kérdésre
  adott válasz egyértelműen kijelöl egy következő lépést; ha létrehozod,
  jelezd a riportban `pending` státusszal, és NE indítsd el.

## Reachability — kötelező bizonyíték

- `grep -rn "finalize_release"` és `grep -rn "checksum"`/`grep -rn "buildHash"`
  a `Makefile`/`mk/*.mk`/`.github/workflows/*.yml`/`tools/*.py`-ban, kizárva
  `test_*.py`-t — minden találatra file:line.
- A `schemas/main`/`CIC-Schemas` összehasonlításhoz konkrét fájl-párok
  (base-repo fájl ↔ CIC-Schemas/schemas-main megfelelője) és a diff lényege.

## Output

- `jobs/wasm-release-pipeline-audit/output/wasm-release-pipeline-audit-report.md`:
  - claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`)
    az 1-3 pontra
  - KB háromszintű státusz tábla az érintett node-okra
  - "Döntési kérdés" szakasz a fenti A/B/C (vagy saját megfogalmazású)
    opciókkal és konkrét hivatkozásokkal

## Git instrukciók

- base-repo: **nincs commit/push** — csak olvasás.
- `CIC-Schemas`: **nincs commit/push** — csak olvasás.
- cic-factory: commit + push **csak** `feature/wasm-release-pipeline-audit`-ra
  (a riport + esetleges `pending` sub-job spec).
- Main-re sehova nem pusholsz.

## Definition of Done

- [ ] `finalize_release.py` vs `infra.py` checksum/buildHash logika file:line
      szinten azonosítva, call-site grep-pel igazolva (vagy dead code-nak jelölve)
- [ ] `schemas/main`/`CIC-Schemas` összehasonlítás konkrét fájl-párokkal
- [ ] canonical release path leírva (mi fut tényleg ma)
- [ ] döntési kérdés A/B/C (vagy saját) opciókkal, hivatkozásokkal
- [ ] KB háromszintű státusz tábla
- [ ] base-repo és CIC-Schemas változatlan (`git status` clean)
- [ ] report a `feature/wasm-release-pipeline-audit`-on pusholva

## Nyelvi szabály

- Riport: **magyarul**
- Kódidézetek, commit message (ha sub-job spec-et hozol létre): **angolul**
