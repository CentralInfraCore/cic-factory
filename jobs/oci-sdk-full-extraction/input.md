# oci-sdk-full-extraction — a teljes OCI SDK felület behúzása a modulba

## Reasoning mód

**implementation.** Kódot írsz, tesztet írsz, és a dokumentációt a bizonyítékhoz
igazítod. Nem tervezel új architektúrát, és nem vitatod felül az alábbi
orchestrátori döntést.

## Kontextus — miért fut ez a job

A `cic-module-oracle-cloud` séma-forrása a `tools/oci-extract`, ami a pinelt OCI
Go SDK-ból nyeri ki a művelet-registryt és a payload-sémákat. Ez mostanáig
**két resource-on** bizonyított: `vcn` és `subnet` — és ezek **ugyanabban a
core/network szolgáltatásban** élnek. A pipeline tehát igazoltan nem
*resource*-specifikus; azt **nem** igazolta senki, hogy nem *service*-specifikus.

A cél ebben a jobban: **az extrakció fedje le a pinelt SDK teljes elérhető
felületét**, ne egy kézzel válogatott resource-listát.

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

Ehhez ne nyúlj hozzá: `docs/design/primitives-alignment.md` rögzíti az irányt
(projektor a már helyes generált kontraktusból, nem kézzel írt második
igazságforrás). Ez a job azt a döntést **végrehajtja**, nem módosítja.

## Kemény korlátok

1. **A CIC-Relay READ-ONLY.** A repo `CLAUDE.md`-je és a te agent-`CLAUDE.md`-d is
   ezt mondja. Relay-igényt találsz → `docs/design/relay-requirements.md`, `R#`
   id, a **relay forrásából vett** bizonyítékkal. Ne javítsd, ne duplikáld ide.
2. **Ne köss be primitives/YANG sémát**, ne írj `ManagedEntity`-specializációt,
   ne hozz létre projektort. Az egy külön, későbbi job.
3. **A modul-repo saját szabályai élnek**: Vault-aláírt commitok, a
   `MANIFEST.sha256` minden commit után regenerálandó, a CI (`make check` + wasm
   build/test + `docs.link-check`) zöld kell legyen.
4. **A repo dokumentációja angol.** Ez az `input.md` magyar (Claude-utasítás), de
   minden amit a modul-repóba írsz — kód, komment, `docs/**` — **angolul**.

## Boot — mit tárj fel magad

Ne fogadd el készpénznek az alábbi leírást; a repo az élő forrás.

- `docs/design/roadmap.md` — P2.x (séma-pipeline) és P3.x (referencia-modul)
- `docs/design/specs/oci-schema-pipeline.md` — a pipeline szerződése
- `docs/design/manual-verification.md` — mi van valós OCI-n igazolva, mi nincs
- `tools/oci-extract/` — a jelenlegi extractor (`go/ast`), a `policy.go` és
  `schema.go` a field-policy és payload-séma kibocsátásért
- `oci-sdk.lock.yaml` — a pinelt SDK verzió és a forrás-hash
- `module/schemas/{vcn,subnet}.json` — a jelenlegi generált, `go:embed`-elt sémák
- `make oci.generate` — a regenerálás belépési pontja

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

### A — Tedd service-agnosztikussá az `oci-extract`-et

A jelenlegi extractor a core/network felületen bizonyított. Derítsd ki
**méréssel**, hol vannak benne rejtett core/network-feltételezések, és szüntesd
meg őket. Nem előre megadott listát kapsz — az a dolgod, hogy megtaláld.

Amire számíts (ez nem teljes lista, és nem is igazolt — a te dolgod igazolni):
path-paraméterek nem egységes alakja, összetett kulcsok, nem-CRUD műveletek,
list/pagination, szolgáltatások eltérő kliens-konvenciói.

### B — Teljes registry a pinelt SDK-ból

Futtasd az extractort a pinelt SDK **összes elérhető szolgáltatására**, és
állítsd elő a teljes művelet-registryt.

**Ez a tool dolga, nem a tiéd.** Ne írj kézzel séma-fájlokat szolgáltatásonként.
Ha egy szolgáltatás nem oldódik fel, az az extractor hibája vagy egy tudatosan
dokumentált kizárás — mindkettőt írd le, de kézi séma-írással **ne** kerüld meg.

Ha egy szolgáltatás kizárása indokolt (pl. nem provisioning-jellegű), azt
**explicit, indokolt kizárás-listaként** rögzítsd, ne csendes kihagyásként.

### C — A kapu granularitása

Ma az integritás-kapu egyetlen `extracted_schema_hash` a commitolt sémára. Teljes
SDK-méretben ez egy hash egy hatalmas felületre: a kapu megmarad, de a diff
reviewálhatatlan lesz. Tedd **szolgáltatásonkénti** granularitásúvá úgy, hogy az
`oci-extract -diff` breaking/compatible osztályozása és a nem-nulla exit
megmaradjon.

### D — Extrakció ≠ beágyazás

Két külön réteg, és ezt a specet is ennek megfelelően kell hagynod:

| Réteg | Skálázás |
|---|---|
| extraction / operation registry (build-time) | **teljes** |
| `go:embed`-elt guest sémák (`module/schemas/*.json`) | a WASM binárisba megy |

A relay `cabinet.MaxWASMModuleSize` alapértéke **16 MB**
(`CIC-Relay/cmd/relay/main_test.go:84` állítja `16*1024*1024`-re), és
**konfigurálható** (`cmd/relay/main.go:94`, `max_wasm_module_size`) — tehát
default, nem kemény plafon, de a modul nem feltételezheti, hogy az üzemeltető
megemelte.

**Mérd meg**, mekkora lenne a bináris a jelenlegi beágyazási móddal a teljes
felületre, és ez alapján javasolj beágyazási stratégiát (szelektív beágyazás,
szolgáltatásonkénti build-target, lusta betöltés — a tiéd a döntés, de mérésre
alapozd). Ha a mérés relay-igényt vet fel, az `R#` tétel a
`relay-requirements.md`-ben, nem relay-módosítás.

### E — Aszinkron műveletek leltára

A `poll` ma `blocked`, mert a core/network-ben nem találtatok valóban aszinkron
műveletet (`CreateVcn`/`UpdateVcn` szinkron, nincs `opc-work-request-id`). A
teljes registry ezt fel tudja oldani.

Állíts elő **leltárt arról, mely műveletek adnak valódi Work Request-et**, és
jelölj ki legalább egy konkrét jelöltet, amin a `poll` valós OCI ellen
tesztelhető. A tesztet **nem** kell lefuttatnod (tenancy-hozzáférés kell hozzá) —
a jelölt megnevezése és az indoklás a szállítandó.

### F — Egress-hoszt leltár

Több szolgáltatás = több API-hoszt, realmenként eltérő suffix-szel. Ez már most
nyitott lelet: a `Describe()` `egress_hosts` értéke `["*.oraclecloud.com"]`, az
EU Sovereign realm hosztja viszont `oraclecloud.eu` (lásd
`manual-verification.md`).

Készíts leltárt a teljes felület egress-hosztjairól (szolgáltatás + realm
dimenzió), és ez alapján fogalmazd meg, mit kell a capability-manifestnek
kifejeznie. Ha ez relay-oldali enforcement-változást igényel → `R#` tétel.

### G — A roadmap státusza kövesse a bizonyítékot

A `roadmap.md` Phase 3 mind az öt tételt (P3.1–P3.5) `todo`-nak jelöli,
miközben a `manual-verification.md` szerint a P3.1/P3.2/P3.3 valós OCI-n
verifikált, a P3.4 részben (plan+execute igen, `poll` blocked). Hozd
összhangba a státusz-oszlopot a bizonyítékkal, **op-onkénti hivatkozással** a
`manual-verification.md`-re. Ahol nincs bizonyíték, ott maradjon `todo` — ne
szépíts.

Ugyanitt: a P3.5 ma egy kézzel válogatott resource-listát mond. Ez a job ennél
szélesebb és mechanikusabb — igazítsd a P3.5-öt ahhoz, ami ténylegesen épül.

## Definition of Done — gépileg ellenőrizhető

A job akkor kész, ha **mind** teljesül, és mindegyikhez van kimásolt
parancs-kimenet az outputban:

1. `make oci.generate` (vagy az általad bevezetett teljes-felület cél) lefut, és
   a registry lefedi a pinelt SDK összes nem-kizárt szolgáltatását
2. **N/N művelet feloldva, 0 hiányzó method/path** — ugyanaz a forma, ami a
   P2.2-nél a VCN-re már bevált (271/271). A számot írd ki szolgáltatásonként is
3. Az `oci-extract -diff` szolgáltatásonkénti granularitással fut, és egy
   szándékosan bevitt breaking változásra **nem-nulla exit**-tel bukik
   (mutasd meg a futást)
4. `make check` + wasm build/test zöld
5. `MANIFEST.sha256` regenerálva, a `manifest-verify` gate zöld
6. `docs.link-check` zöld
7. A CI zöld a pusholt feature branchen — **a `headSha`-t egyeztesd** a
   tesztelt committal, ne csak azt nézd, hogy „van zöld futás"

## Tiltott rövidítések

- **fájl létezése ≠ kész** — egy legenerált JSON megléte nem bizonyítja, hogy a
  művelet feloldódott
- **teszt zöld ≠ a viselkedés meghajtva** — a te agent-`CLAUDE.md`-d
  verification-first szabálya itt is él
- **exit code 0 ≠ sikeres** — a kimenetet olvasd el
- **„a többi szolgáltatás valószínűleg ugyanígy megy"** — ez pont az a
  feltételezés, amit ez a job hivatott megdönteni vagy igazolni. Mérd.
- **kézzel írt séma a hiányzó helyre** — ez elrejti az extractor hibáját

## Ha elakadsz

Ha egy résznél kiderül, hogy nem elvégezhető a rendelkezésre álló hozzáféréssel
vagy időkerettel, **ne csináld félig, magabiztos hangnemben**. Írd le konkrétan:
mi csúszik meg, mi kell hozzá, és mit végeztél el helyette. A többi részt vidd
végig teljesen.

## Output

A `cic-factory` klónban, a `jobs/oci-sdk-full-extraction/` alatt:

- `output/agent-output.md` — összefoglaló: mit csináltál, mi lett kész, mi nem
- `output/claim-evidence.md` — claim-evidence tábla, kötelezően ezekkel az
  oszlopokkal: **Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat**.
  A „Bizonyíték" oszlopba a ténylegesen lefuttatott parancs és a kimenete kerül,
  ne parafrázis. Amihez nem tudsz verifikációs módszert írni, az „nem igazolt".
- `output/service-coverage.md` — szolgáltatásonkénti lefedettség: N/N művelet,
  hiányzó method/path, indokolt kizárások
- `output/async-operations.md` — az (E) leltár + a `poll`-jelölt
- `output/egress-hosts.md` — az (F) leltár + a manifest-következmény
- `output/embedding-strategy.md` — a (D) mérés + a javasolt beágyazási stratégia

A tényleges kód- és doc-változás a **modul-repóban** történik, nem a
cic-factoryban.

## Git

Két repo, két külön szabály:

**`cic-module-oracle-cloud`** — klónozd a workspace-be, és a `devel`-ből nyiss
`feature/oci-sdk-full-extraction` branchet. Ide commitolj és pusholj.
- ❌ NE pushol `devel`-re és NE `main`-re
- ❌ NE nyiss PR-t — a review és a merge az orchestrátoré
- Minden commit Vault-aláírt, `MANIFEST.sha256` utána regenerálva

**`cic-factory`** — csak az output dokumentumok, a feature branchre.

## Nyelvi szabály

Ez az `input.md` és a te gondolkodásod magyar. **Minden, ami a modul-repóba
kerül — kód, komment, `docs/**`, commit üzenet — angol.** Az
`output/*.md` a cic-factoryban magyar.
