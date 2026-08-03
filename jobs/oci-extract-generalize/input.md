# oci-extract-generalize — az extractor legyen service-agnosztikus

## Reasoning mód

**implementation.** Kódot és tesztet írsz. Nem tervezel új architektúrát, és nem
vitatod felül az alábbi orchestrátori döntést.

## Kontextus — miért fut ez a job

A `cic-module-oracle-cloud` séma-forrása a `tools/oci-extract`, ami a pinelt OCI
Go SDK-ból nyeri ki a művelet-registryt és a payload-sémákat. Ez mostanáig
**két resource-on** bizonyított: `vcn` és `subnet` — és ezek **ugyanabban a
core/network szolgáltatásban** élnek. A pipeline tehát igazoltan nem
*resource*-specifikus; azt **nem** igazolta senki, hogy nem *service*-specifikus.

Ez a job **kizárólag ezt a kérdést dönti el**: elbírja-e az extractor az OCI
felület heterogenitását. A teljes sweep, a kapu-granularitás, a beágyazási
stratégia és a leltárak egy **külön, rákövetkező jobban** vannak
(`oci-extract-full-sweep`) — azokat itt ne kezdd el.

Ez a felosztás szándékos: ez a rész a nyílt végű, kockázatos darab, ezért fut
erős modellen és szűk hatókörrel. Ha ez megvan, a maradék mechanikus.

### Orchestrátori döntés — ne vizsgáld felül

**A `cic-primitives` / YANG réteget ebben a körben NEM kötjük be.** Az indok nem
az, hogy az a repo késik, hanem strukturális: a primitives réteg **nem alak,
hanem viselkedés** — a 8 atomi primitív közt ott a Behavior, Contract, Event,
Access, az aggregátumok közt a PolicySurface, a `managed-entity.yaml`-ban pedig
lezárt inline lifecycle-állapotgép. Ez dependency- és élettartam-szemantika,
azaz üzleti logika.

Üzleti logikát **hiányos** mechanikus felületre ráhúzni azt jelentené, hogy a
döntéseket hiányos bemenetből hozzuk meg, és utána már nem lehet szétválasztani,
mi jött az API-ból és mi a mi feltételezésünk. Ezért: **előbb legyen teljes és
gépi az extrakció, a szemantika utána jön.**

`docs/design/primitives-alignment.md` rögzíti az irányt. Ez a job azt a döntést
**végrehajtja**, nem módosítja.

## Kemény korlátok

1. **A CIC-Relay READ-ONLY.** A repo `CLAUDE.md`-je és a te agent-`CLAUDE.md`-d is
   ezt mondja. Relay-igényt találsz → `docs/design/relay-requirements.md`, `R#`
   id, a **relay forrásából vett** bizonyítékkal. Ne javítsd, ne duplikáld ide.
2. **Ne köss be primitives/YANG sémát**, ne írj `ManagedEntity`-specializációt.
3. **Ne kezdd el a teljes sweepet.** A hatókör a mechanizmus + egy szándékosan
   heterogén minta. A teljes futtatás a következő job dolga.
4. **A modul-repo saját szabályai élnek**: Vault-aláírt commitok, a
   `MANIFEST.sha256` minden commit után regenerálandó, a CI zöld kell legyen.
5. **A repo dokumentációja angol.** Ez az `input.md` magyar (Claude-utasítás), de
   minden amit a modul-repóba írsz — kód, komment, `docs/**` — **angolul**.

## Boot — mit tárj fel magad

Ne fogadd el készpénznek az alábbi leírást; a repo az élő forrás.

- `tools/oci-extract/` — a jelenlegi extractor (`go/ast`); a `policy.go` és
  `schema.go` a field-policy és payload-séma kibocsátásért
- `docs/design/specs/oci-schema-pipeline.md` — a pipeline szerződése
- `oci-sdk.lock.yaml` — a pinelt SDK verzió és a forrás-hash
- `module/schemas/{vcn,subnet}.json` — a jelenlegi generált sémák
- `make oci.generate` — a regenerálás belépési pontja
- `docs/design/roadmap.md` P2.x — mi számít késznek és mi nem

KB oldalról a `kb_focus` adja a kötelező első olvasást. **Figyelem:** a chunk-id
nem stabil azonosító — a KB-t 2026-08-02-én újraindexelték. A megadott id-k
2026-08-03-án tartalom-ellenőrzöttek, és ezt kell adniuk:

| id | Aminek lennie kell |
|---|---|
| `c1719` | relay pozicionálás — végrehajtó motor, nem dönt, `NextHops` |
| `c1734` | séma belső viselkedés — `StateRequirement`/`Dependencies`/`PluginRef`/`NextHops` |
| `c4147` | `core/cabinet/` — schema/module/workflow registry + WASM |

Ha bármelyik mást ad, **írd le az outputban és a file path alapján keresd meg**
(`search_query`), ne találgass.

## Feladat

### 1 — Mérd fel, hol service-specifikus a mai extractor

Ne tippelj és ne olvasatból következtess: **futtasd** a mai extractort
core/network-en kívüli szolgáltatásokra, és nézd meg, mi törik el.

A szolgáltatás-mintát **te válaszd ki**, de a választás legyen indokolt és
szándékosan heterogén — a cél az, hogy a mai feltételezések eltörjenek, ne az,
hogy zöldet lássunk. Az indoklást írd le: miért éppen azok.

Minden talált feltételezéshez: **fájl:sor + a konkrét eltörő kimenet**.

### 2 — Szüntesd meg a talált feltételezéseket

Alakítsd az extractort úgy, hogy a felfedezett heterogenitást kezelje. Ez a job
lényege — a megoldás formája a tiéd, de:

- **kézzel írt séma tilos** a hiányzó helyre: az elrejti az extractor hibáját
- **szolgáltatás-specifikus különesetek** csak akkor, ha bizonyítottan az OCI
  felület tér el, nem akkor, ha az extractor nem általánosít — és akkor is
  nevesített, dokumentált kivételként

### 3 — Regressziós védelem

A meglévő `vcn`+`subnet` lefedettség **nem romolhat**. Legyen teszt, ami ezt
gépileg őrzi, és legyen teszt az újonnan kezelt heterogenitásra is.

### 4 — Mit tanultunk a felület alakjáról

A következő job (`oci-extract-full-sweep`) a te kimenetedre épül. Írd le, amit a
sweep tervezéséhez tudni kell: milyen osztályokba esnek a szolgáltatások, hol
várható további törés, mit érdemes indokolt kizárásként kezelni.

Ez **nem** a sweep elvégzése — a következő job bemenete.

## Definition of Done — gépileg ellenőrizhető

A job akkor kész, ha **mind** teljesül, és mindegyikhez van kimásolt
parancs-kimenet az outputban:

1. Az extractor **N/N művelet feloldva, 0 hiányzó method/path** eredményt ad a
   kiválasztott heterogén mintán — ugyanaz a forma, ami a P2.2-nél a VCN-re már
   bevált (271/271). A számot szolgáltatásonként írd ki.
2. A `vcn`+`subnet` korábbi lefedettsége változatlan (regressziós teszt zöld)
3. `make check` + wasm build/test zöld
4. `MANIFEST.sha256` regenerálva, a `manifest-verify` gate zöld
5. `docs.link-check` zöld
6. A CI zöld a pusholt feature branchen — **a `headSha`-t egyeztesd** a
   tesztelt committal, ne csak azt nézd, hogy „van zöld futás"

## Tiltott rövidítések

- **fájl létezése ≠ kész** — egy legenerált JSON megléte nem bizonyítja, hogy a
  művelet feloldódott
- **teszt zöld ≠ a viselkedés meghajtva** — a verification-first szabály itt is él
- **exit code 0 ≠ sikeres** — a kimenetet olvasd el, ne a kilépési kódot
- **„a többi szolgáltatás valószínűleg ugyanígy megy"** — ez pont az a
  feltételezés, amit ez a job hivatott megdönteni vagy igazolni. Mérd.
- **kézzel írt séma a hiányzó helyre** — ez elrejti az extractor hibáját

## Ha elakadsz

Ha kiderül, hogy egy rész nem elvégezhető a rendelkezésre álló hozzáféréssel
vagy időkerettel, **ne csináld félig, magabiztos hangnemben**. Írd le konkrétan:
mi csúszik meg, mi kell hozzá, és mit végeztél el helyette. A többit vidd végig.

Ez a job szándékosan szűk. Ha közben olyat találsz, ami a következő jobba való,
**írd fel, ne csináld meg**.

## Output

A `cic-factory` klónban, a `jobs/oci-extract-generalize/` alatt:

- `output/agent-output.md` — összefoglaló: mit csináltál, mi lett kész, mi nem
- `output/claim-evidence.md` — claim-evidence tábla, kötelezően ezekkel az
  oszlopokkal: **Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat**.
  A „Bizonyíték" oszlopba a ténylegesen lefuttatott parancs és a kimenete kerül,
  ne parafrázis. Amihez nem tudsz verifikációs módszert írni, az „nem igazolt".
- `output/service-assumptions.md` — a talált service-specifikus feltételezések:
  fájl:sor, az eltörő kimenet, és hogyan oldottad fel
- `output/sweep-input.md` — a (4) tanulság a következő jobnak

A tényleges kód- és doc-változás a **modul-repóban** történik, nem a
cic-factoryban.

## Git

Két repo, két külön szabály:

**`cic-module-oracle-cloud`** — klónozd a workspace-be, és a `devel`-ből nyiss
`feature/oci-extract-generalize` branchet. Ide commitolj és pusholj.
- ❌ NE pushol `devel`-re és NE `main`-re
- ❌ NE nyiss PR-t — a review és a merge az orchestrátoré
- Minden commit Vault-aláírt, `MANIFEST.sha256` utána regenerálva

**`cic-factory`** — csak az output dokumentumok, a feature branchre.

## Nyelvi szabály

Ez az `input.md` és a te gondolkodásod magyar. **Minden, ami a modul-repóba
kerül — kód, komment, `docs/**`, commit üzenet — angol.** Az
`output/*.md` a cic-factoryban magyar.
