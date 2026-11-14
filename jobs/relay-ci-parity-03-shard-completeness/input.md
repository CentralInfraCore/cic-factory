# relay-ci-parity-03-shard-completeness — egységes quality gate és teljességi validáció

## Kontextus

A `CentralInfraCore/CIC_Relay` **#169** issue (másolat: `ref/issue-169-body.md`) tízlépéses
PR-sorozat. **Ez a job a PR-03-at fedi:** „Unified quality gate and completeness validation”,
záró feltétel: *hiányos riport vagy shard elutasítva*.

Előzmények (mind mergelve):

- PR-01 (cic-factory #47): inventory, kapuhiba reprodukció — `ref/pr01-inventory-and-gap-analysis.md`.
- PR-02 (CIC_Relay #170, cic-factory #48/#49): a Rust mutánsfelsorolás fail-closed, a tervező
  eszkalál — `ref/pr02-report.md`.

A PR-02 azt biztosítja, hogy **a felsorolás hibája ne legyen `0` mutáns**. Azt **nem**, hogy a
felsorolt mutánsok mindegyike kapott-e ítéletet: a PR-01 4.1 szerint minden Rust shard a **saját**
mutánskészletét számolja (`cargo mutants --shard`), a tervezett `--list`-hez nem köti semmi,
nincs közös lista és nincs „minden mutáns pontosan egy ítéletet kapott” ellenőrzés. A PR-02
futásában a terv 300 mutáns volt, 8 shard, mind `success` — de hogy a 300 mind mért ítéletet
kapott-e, **nem mért**. Ez a PR-03 tárgya.

**Implementáció.** Ez a job a CIC_Relay scriptjeit, workflow-it és tesztjeit módosítja, és
**PR-t nyit a CIC_Relay felé** (lásd Git instrukciók). A workflow/CI módosítására ebben a jobban
kifejezett felhatalmazás van, **de csak a lenti scope-ra**.

## Boot sequence

1. `mcp__cic-graph__kb_status`, majd `search_nodes` az `axioms`, `symbols`, `contract`,
   `limits` fogalmakra. A státuszt (implemented / scaffold / concept) node- vagy fájlszinten
   támaszd alá, különben ne állítsd tényként.
2. Olvasd el: `ref/issue-169-body.md` (különösen: „Mutation testing: FULL and DIFF”,
   „Self-testing”, „Development rules”), `ref/pr02-report.md` (7. szakasz: nyitott pontok),
   `ref/pr01-inventory-and-gap-analysis.md` 4.1 és 4.4.
3. Klónozd friss klónként: `$WORKSPACE/CIC_Relay/` (alapértelmezett ág `main`; a `devel`
   elavult) és `$WORKSPACE/cic-primitive-forms/` (csak olvasásra, referencia). **Rögzítsd a
   pontos commit-azonosítót és az ágat.** A PR-02 mergelve: a Relay `main` fejének tartalmaznia
   kell a `7ac6e80`-at; ha nem, állj meg és jelezd.
   **Ha a `workspace/` alatt már van `CIC_Relay` mappa, ne azt használd:** az korábbi jobokból
   piszkos lehet (189 módosított `.yaml`, ok ismeretlen). Új, tiszta klónt készíts, és a
   `git status --short | wc -l` kimenetét rögzítsd a klónozás után **és** a mérések előtt.
4. Helyi tájékozódási klónok (csak olvasásra, lehetnek elavultak): `${CIC_RELAY_PATH}`,
   `~/sync/git.partners/CentralInfraCore/`. **A mérés a friss klónon megy**, nem a helyin.
5. **Reachability (Go forráskód):** egy Go szimbólumról vagy scriptről csak akkor mondd, hogy
   production-hívott, ha megvan a hívási út:
   `grep -rn <szimbólum> --include=*.go . | grep -v _test.go` VAGY `deadcode ./...` kimenet,
   production call site `file:line`-nal. A `symbol létezik` ≠ `production hívja`. Ugyanez a
   CI-scriptekre: a workflow-ból hívott script `file:line`-ja, nem a script puszta léte.
6. **Derítsd fel te**, ne feltételezd: milyen riportot ír a `cargo mutants` shardonként
   (`mutants.out/`, `outcomes.json`), mit ír a `gremlins` és a `gremlins_gate.py`, mit tölt fel a
   jelenlegi workflow artifactként (ha egyáltalán), és mit olvas vissza a `gate` job. A
   feltáráshoz a valódi eszközök kimenetét használd (a PR-02 mérési környezete:
   `rust:1.96.1-bookworm@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8`,
   `cargo-mutants 27.1.0`).

## Feladat

### A. Rust mutáns-teljesség (kötelező, először)

A tervezett halmaz és a mért ítéletek egyezése:

- A `plan` job a tervezett mutánsokat **közös listába** írja (a PR-02 `count_mutants.py`
  `--out` fájlja már megvan), a lista **azonosítója/digestje** a shardokhoz kötődik.
- Minden shard a saját ítéleteit riportként (artifact) adja át.
- A teljességet **külön lépés** ellenőrzi, a `gate` előtt: minden tervezett mutáns **pontosan egy**
  ítéletet kapott; hiányzó ítélet, duplikált ítélet, a tervben nem szereplő (ismeretlen)
  mutáns, hiányzó vagy sérült shard-riport → **piros**.
- A `timeout` és az `unviable` ítélet **külön számolódik**, nem keveredik a `caught`/`missed`-del,
  és nem számít automatikusan sikernek. A kezelésüket **te javasold és indokold** a mért adat
  alapján (mi a mai arányuk), a döntést a jelentésben nevezd meg.
- A shard-számolás fedezete: ha a mutánsok száma a shard-korlát (8) fölé nő, a lefedettség
  attól még teljes legyen (`--shard k/n` az egész halmazt fedi): ezt is ellenőrizd, ne csak a mai 300-ra.

### B. Go (gremlins) teljesség

Ugyanaz az elv a Go oldalon: minden **tervezett csomag** (a `plan` kimenete) pontosan egy
ítéletet kapott a chunk-riportokban; hiányzó, duplikált vagy ismeretlen csomag, olvashatatlan
vagy üres riport → piros. A meglévő per-csomag ratchet (`gremlins_gate.py`, `baseline_guard.py`,
`.mutation-baseline.json`) **szigorúan megmarad**: a küszöbök nem változnak.

### C. Egységes kapu, hiányzó mérés = piros

A #169 minőségi kapu-táblája szerint: „Missing or broken measurement: mandatory FAIL”,
„Incomplete mutation shard: mandatory FAIL”. Egy gépileg olvasható, **fail-closed** kapu-script
(a Forms `tools/quality_gate.py` referencia, **nem másolandó mechanikusan**), amely a
mutációs (A, B) és a lefedettségi riportokat egy helyen értékeli:

- hiányzó, olvashatatlan vagy üres lefedettségi riport (Go `coverprofile`, Rust `llvm-cov`)
  **nem** értelmeződik nulla mérésnek és **nem** sikernek;
- üres mérés ≠ siker; a mért érték és a küszöb viszonya explicit;
- az **eddigi numerikus küszöbök és padlók nem változnak** (CI-padló, mutációs ratchet): ez a PR
  azt teszi kötelezővé, hogy **mérés nélkül nincs zöld**, nem azt, hogy a küszöb emelkedik.
  A Go statement coverage mért értéke (88,8%, PR-01) a #169 90%-os célja alatt van: ezt a
  jelentés **adósság-listaként** rögzítse, ne a küszöb emelésével oldd meg.

### D. A PR-02 review két nyitott pontja

- **Rust `#[cfg(test)]` ugyanabban a forrásfájlban.** A cargo-mutants a tesztkódot nem mutálja,
  ezért az ilyen változásra az `--in-diff` 0 mutánst ad, a fájlnév-alapú tervező pedig nem
  ismeri fel. Javasolt (konzervatív) irány a PR-02 elvével: ha a módosított `.rs` fájl diffje
  `#[cfg(test)]`-es régiót érint, a terv `rust_full`-ra eszkalál. **Előbb mérd le**, hogy a
  diff alapján megbízhatóan felismerhető-e; ha nem, mondd ki, és maradjon „nem kezelve”.
- **`tools/goastdump` (P8, beágyazott Go-modul).** Itt **ne dönts**: mérd le, mit jelentene a
  bevonás (csomagok, coverage, mutációs idő), és adj javaslatot. A tulajdonos dönt arról, hogy
  kap-e saját mutációs profilt. A mai viselkedés (kimarad) változatlan marad.

## Negatív tesztek (kötelezőek)

A #169 „Self-testing” 3., 4. és 5. próbája, a Relay valóságára:

1. **Hiányzó shard** → a FULL nem lehet sikeres (Rust és Go).
2. **Duplikált vagy meghamisított ítélet** elutasítva (ugyanaz a mutáns két ítélettel; ítélet
   olyan mutánsra, ami nincs a tervben; megváltoztatott verdikt a riport és az összegző közt).
3. **Hiányzó vagy olvashatatlan lefedettségi riport** nem nulla mérés és nem siker.
4. Üres, de érvényes mérés külön eset, nem hiba (ahol a tervezett halmaz valóban üres).
5. A **kapu-script saját tesztje** futó, CI-ba kötött teszt legyen (a PR-02 mintája: a workflow-lépés
   `run:` szövegét a teszt YAML-ból kiveszi és `bash -e`-vel futtatja, hamis eszközökkel).

**Minden negatív teszt a javítás előtti állapoton is lefusson, és ott BUKJON** — ezt mérd le és add
meg a nyers kimenetét (a régi `bc2c4e0`+PR-02 fán). **Figyelem — a PR-02 tanulsága:** a teszt
könnyen buktat *rossz okból* (pl. `bad substitution`, üres git-fa). Minden bukás-tesztben a
**konkrét hibaüzenetet** is ellenőrizd, és a régi kódon nézd meg, hogy az **elvárt okból** bukik.

## Nem része a jobnak (ne csináld)

- Küszöb vagy baseline lazítása, vagy kizárás a scope-ba tolva; a küszöbök emelése is kimarad.
- Ág-lefedettség (PR-04), seeded defects (PR-05), trust-boundary és FFI tesztek (PR-06),
  FULL/DIFF integráció és nightly hibajelentés (PR-07), evidence (PR-08/09), proof-aware (PR-10).
- Eszköz-verzió pin (`cargo-mutants`, `cargo-llvm-cov`, `GREMLINS_VERSION`), nightly horgony
  (`nightly.yml` „legutóbbi sikeres éjszaka”), `deadcode` lépés státusza, a nightly `security`
  bukás (Relay #160): külön döntések. Ha szükségesnek látod, **jelentsd**, ne változtasd.
- Termékkód módosítása. Ha egy negatív teszt hiányzó termékgaranciát tár fel, rögzítsd, ne rejtsd.
- A CIC_Relay külső beállításainak (ruleset, branch protection, required check) módosítása.
  Ha új job a required check-ek hatókörét érinti, **jelentsd** a tulajdonosnak.

## Tiltott rövidítések

- Egy fájl létezése ≠ implemented. A workflow létezése ≠ hogy fut, és a kapu ≠ hogy bukni tud.
- Exit code 0 ≠ sikeres mérés. Üres kimenet ≠ nulla mutáns ≠ sikertelen felsorolás.
- Minden shard `success` ≠ minden tervezett mutáns kapott ítéletet: az egyezést mérd, ne következtesd.
- Egy sikeres helyi futás ≠ hogy a CI-kapu hibás bemenetnél pirosra vált: ahol ezt állítod, mérd le.
- A teszt zöldje ≠ hogy a teszt bukni tud: a negatív tesztet a javítás nélküli állapoton is futtasd,
  és ellenőrizd, hogy az elvárt okból bukik.
- A hiányzó bizonyíték nem bizonyíték: amit nem futtattál, azt ne írd le mért tényként.

## Verifikáció és bizonyítás

- Minden javítás mellé a **javítás előtti** és **utáni** futás nyers kimenete (parancs + kimenet).
- **A valódi eszközzel mérj**, ne csak hamis `cargo`/`gremlins` kimenettel: a riportformátumot
  (a `cargo-mutants` `outcomes.json`-ját és a gremlins kimenetét) a pinelt konténerben vedd fel,
  és a kapu-script tesztjeihez ebből készíts fixture-t (a fixture eredetét írd le).
- **Nem elég a helyi futás:** a #169 10. szabálya szerint egy CI-fázis csak akkor kész, ha
  GitHub Actions futás igazolja. A PR-on futó workflow **run id-ját és headSha-ját** vesd egybe
  a tesztelt committal. A **piros útnak** (hiányzó/duplikált ítélet) a CI-ban is futnia kell
  legalább egyszer: erre készíts **szándékosan hibás, nem mergelendő** ágat vagy dispatch-futást,
  jelöld egyértelműen, és a futás run id-ját add meg; ha ezt nem teszed meg, írd: **nem mérve**.
- A workflow-szöveg olvasata ≠ futás: ahol csak olvastad, mondd ki.
- Amit nem mértél, az **nem mérve**, nem becslés.
- A teljes `pytest`-et a CI `python` jobja futtatja hash-ellenőrzött függőségekkel; helyben a
  scratch venv-ben hiányozhatnak csomagok (`requests`): ezt mondd ki, ne hallgasd el.

## Output

A cic-factory klónban: `jobs/relay-ci-parity-03-shard-completeness/output/`

- `output/pr03-report.md` — magyarul: vizsgált commitok; a klón tisztasága; a feltárt riportformátumok
  (a valódi kimenet alapján); javítások soronként (előtte/utána); negatív tesztek és a bukásuk
  bizonyítéka (**az elvárt okból**); GitHub Actions run id-k (zöld **és** szándékosan piros);
  a `timeout`/`unviable` kezelés javaslata és indoka; adósság-lista (Go coverage a 90% alatt,
  12 csomag a mutációs baseline-ban); a `#[cfg(test)]` és a `goastdump` mérése és javaslata;
  claim-evidence tábla (`Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat`);
  nyitott döntések; amit nem mértél.
- `output/raw/` — nyers kimenetek és mérőscriptek (minden `.sh` első sora `#!/usr/bin/env bash`,
  a gate ShellCheck-et fut `--severity=error`-ral).

A CIC_Relay módosítás a Relay-klónban, külön ágon, PR-ként (lásd lent).

## Definition of Done

- Mindkét repó commit-azonosítója és az ág leírva; a Relay `main` tartalmazza a `7ac6e80`-at.
- A klón tiszta volt a mérések előtt (rögzítve), vagy kimondva, hogy nem.
- A riportformátumok a valódi eszközök kimenete alapján dokumentálva.
- Rust és Go teljesség: hiányzó, duplikált, ismeretlen ítélet és hiányzó/sérült riport → piros, mérve.
- Hiányzó/olvashatatlan lefedettségi riport nem nulla és nem siker, mérve.
- Minden negatív teszt a javítás előtti állapoton bukik **az elvárt okból**, nyers kimenettel.
- A `#[cfg(test)]` és a `goastdump` lemérve; a `goastdump` kapcsán a döntés a tulajdonosé.
- Valódi GitHub Actions run id a PR headSha-jára (zöld), és a piros útra (szándékos hiba), vagy **nem mérve**.
- A numerikus küszöbök és baseline-ok változatlanok (a diffben ellenőrizve).
- A CIC_Relay PR leírása pontosan azt állítja, ami mérve van.

## Git instrukciók

- **cic-factory:** commit és push **csak** a `feature/relay-ci-parity-03-shard-completeness`
  ágra. Main-re, devel-re nem pusholsz; merge-et nem csinálsz. A job `meta.yaml` státuszát
  nem módosítod (a tulajdonos zárja).
- **CIC_Relay:** külön ág (`feature/relay-ci-parity-03-shard-completeness`) a friss klónból,
  az alapértelmezett ág a `main`. PR-t a `main`-re nyiss (`--base main` explicit). Nem
  mergelsz. A PR **egy** témájú legyen: teljességi validáció + egységes kapu; termékkód nincs.
  A szándékosan hibás (piros-út bizonyító) ágat **ne** mergeld, és ne nyiss belőle mergelhetőnek
  tűnő PR-t; a PR leírásában hivatkozz a run id-jára.
- **Commit-üzenet:** nincs `Co-Authored-By` vagy AI-re utaló sor, sem a commitban, sem a PR
  leírásában. A Relay-repó csak merge-commitot enged (squash/rebase tiltott).
- Friss klónban placeholder identitás lehet és nincs Vault-aláírás: ezt jelezd az outputban,
  az aláírást a tulajdonos pótolja.
- A `git push` hívást a tulajdonos futtathatja, ha a környezet a push-t elutasítja; ilyenkor
  add oda a pontos parancsot, ne kerüld meg.

## Nyelvi szabály

Dokumentáció magyarul. Parancsok, kód, YAML, shell angolul.
