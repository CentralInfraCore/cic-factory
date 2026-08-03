# oci-extract-full-sweep — teljes felület, kapu, beágyazás, leltárak

## Reasoning mód

**implementation.** A mechanizmus a `oci-extract-generalize` jobban elkészült.
Itt azt **futtatod skálán**, és két jól körülhatárolt mérnöki darabot csinálsz
meg. Nem tervezel újra, és nem vitatod felül az alábbi döntéseket.

## Előfeltétel — ne indulj el nélküle

Ez a job a `oci-extract-generalize` **mergelt** kimenetére épül. Először ezt
ellenőrizd:

- a modul-repo `devel` ágán rajta van-e a generalizált extractor
- olvasd el a `jobs/oci-extract-generalize/output/sweep-input.md`-t — az előző
  job szándékosan neked hagyott tanulságait (szolgáltatás-osztályok, várható
  törések, kizárás-jelöltek)

Ha az előfeltétel nem teljesül, **ne kezdd el a munkát** — írd le az outputban,
hogy mi hiányzik, és állj meg.

## Boot — konkrét források

A modul-repóban (a saját klónodban):

- `tools/oci-extract/` — a generalizált extractor (`policy.go`, `schema.go`)
- `oci-sdk.lock.yaml` — a pinelt SDK verzió + `extracted_schema_hash`
- `module/schemas/` — a jelenleg `go:embed`-elt generált sémák
- `docs/design/specs/oci-schema-pipeline.md` — a pipeline szerződése
- `docs/design/manual-verification.md` — op-onkénti valós-OCI lefedettség
- `docs/design/roadmap.md` — P2.x és P3.x státusz

A relay **kizárólag olvasásra**, a `${CIC_RELAY_PATH}` alatt:

- `cmd/relay/main_test.go:84` — a `MaxWASMModuleSize` alapérték (16 MB)
- `cmd/relay/main.go:94` — hogy konfigurálható (`max_wasm_module_size`)

KB oldalról a `kb_focus` adja a kötelező első olvasást: `get_chunk("c1719")` a
relay pozicionálásra (végrehajtó motor, nem dönt) és `get_chunk("c4147")` a
`core/cabinet/` registry rétegre. **Figyelem:** a chunk-id nem stabil
azonosító — a KB-t 2026-08-02-én újraindexelték; ezek 2026-08-03-án
tartalom-ellenőrzöttek. Ha mást adnak, írd le az outputban és `search_query`-vel
keresd meg file path alapján, ne találgass.

## Kontextus — miért fut ez a job

Az `oci-extract` mostanra service-agnosztikus (az előző job igazolta egy
szándékosan heterogén mintán). A cél itt: **az extrakció fedje le a pinelt SDK
teljes elérhető felületét**, ne egy kézzel válogatott resource-listát — és a
teljes méret által felvetett három következményt rendezzük le.

### Orchestrátori döntés — ne vizsgáld felül

**A `cic-primitives` / YANG réteget ebben a körben NEM kötjük be.** A primitives
réteg nem alak, hanem viselkedés (Behavior/Contract/Event/Access atomok,
PolicySurface, lezárt lifecycle-állapotgép a `managed-entity.yaml`-ban) — azaz
üzleti logika. Üzleti logikát hiányos mechanikus felületre húzni azt jelentené,
hogy utána nem lehet szétválasztani, mi jött az API-ból és mi a feltételezésünk.
Előbb teljes és gépi az extrakció, a szemantika utána. Lásd
`docs/design/primitives-alignment.md` — ez a job végrehajtja, nem módosítja.

## Kemény korlátok

1. **A CIC-Relay READ-ONLY.** Relay-igényt találsz → `R#` tétel a
   `docs/design/relay-requirements.md`-ben, a **relay forrásából vett**
   bizonyítékkal. Ne javítsd, ne duplikáld ide.
2. **Ne köss be primitives/YANG sémát**, ne írj `ManagedEntity`-specializációt.
3. **A modul-repo saját szabályai élnek**: Vault-aláírt commitok,
   `MANIFEST.sha256` minden commit után regenerálva, CI zöld.
4. **A repo dokumentációja angol.** Ez az `input.md` magyar, de minden ami a
   modul-repóba kerül — kód, komment, `docs/**` — **angolul**.

## Feladat

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
**reviewálhatatlan** lesz. Tedd **szolgáltatásonkénti** granularitásúvá úgy, hogy
az `oci-extract -diff` breaking/compatible osztályozása és a nem-nulla exit
megmaradjon.

### D — Extrakció ≠ beágyazás

Két külön réteg, és ezt a bontást meg kell tartani:

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
szolgáltatásonkénti build-target, lusta betöltés — a döntés a tiéd, de **mérésre**
alapozd, ne becslésre). Ha a mérés relay-igényt vet fel → `R#` tétel.

### E — Aszinkron műveletek leltára

A `poll` ma `blocked`, mert a core/network-ben nem találtak valóban aszinkron
műveletet (`CreateVcn`/`UpdateVcn` szinkron, nincs `opc-work-request-id`). A
teljes registry ezt fel tudja oldani.

Állíts elő leltárt arról, **mely műveletek adnak valódi Work Request-et**, és
jelölj ki legalább egy konkrét jelöltet, amin a `poll` valós OCI ellen
tesztelhető. A tesztet **nem** kell lefuttatnod (tenancy-hozzáférés kell hozzá) —
a jelölt megnevezése és az indoklás a szállítandó.

### F — Egress-hoszt leltár

Több szolgáltatás = több API-hoszt, realmenként eltérő suffix-szel. Ez már most
nyitott lelet: a `Describe()` `egress_hosts` értéke `["*.oraclecloud.com"]`, az
EU Sovereign realm hosztja viszont `oraclecloud.eu` (lásd
`docs/design/manual-verification.md`).

Készíts leltárt a teljes felület egress-hosztjairól (szolgáltatás + realm
dimenzió), és ez alapján fogalmazd meg, mit kell a capability-manifestnek
kifejeznie. Ha ez relay-oldali enforcement-változást igényel → `R#` tétel.

### G — A roadmap státusza kövesse a bizonyítékot

A `docs/design/roadmap.md` Phase 3 mind az öt tételt (P3.1–P3.5) `todo`-nak
jelöli, miközben a `manual-verification.md` szerint a P3.1/P3.2/P3.3 valós
OCI-n verifikált, a P3.4 részben (plan+execute igen, `poll` blocked). Hozd
összhangba a státusz-oszlopot a bizonyítékkal, **op-onkénti hivatkozással** a
`manual-verification.md`-re. Ahol nincs bizonyíték, ott maradjon `todo` — ne
szépíts.

Ugyanitt: a P3.5 ma egy kézzel válogatott resource-listát mond. Ez a munka ennél
szélesebb és mechanikusabb — igazítsd a P3.5-öt ahhoz, ami ténylegesen épül.

## Definition of Done — gépileg ellenőrizhető

A job akkor kész, ha **mind** teljesül, és mindegyikhez van kimásolt
parancs-kimenet az outputban:

1. A teljes-felület generáló cél lefut, és a registry lefedi a pinelt SDK összes
   nem-kizárt szolgáltatását
2. **N/N művelet feloldva, 0 hiányzó method/path** — ugyanaz a forma, ami a
   P2.2-nél a VCN-re már bevált (271/271). A számot szolgáltatásonként is írd ki
3. Az `oci-extract -diff` szolgáltatásonkénti granularitással fut, és egy
   szándékosan bevitt breaking változásra **nem-nulla exit**-tel bukik
   (mutasd meg a futást)
4. A beágyazási méret **megmérve**, nem becsülve — a mérés parancsa és kimenete
   az outputban
5. `make check` + wasm build/test zöld
6. `MANIFEST.sha256` regenerálva, a `manifest-verify` gate zöld
7. `docs.link-check` zöld
8. A CI zöld a pusholt feature branchen — **a `headSha`-t egyeztesd** a
   tesztelt committal, ne csak azt nézd, hogy „van zöld futás"

## Tiltott rövidítések

- **fájl létezése ≠ kész** — egy legenerált JSON megléte nem bizonyítja, hogy a
  művelet feloldódott
- **teszt zöld ≠ a viselkedés meghajtva** — a verification-first szabály itt is él
- **exit code 0 ≠ sikeres** — a kimenetet olvasd el, ne a kilépési kódot
- **becslés ≠ mérés** — a (D) beágyazási méretre ez kifejezetten él
- **kézzel írt séma a hiányzó helyre** — ez elrejti az extractor hibáját
- **csendes kihagyás** — a kizárás csak indokolt és listázott lehet

## Ha elakadsz

Ha egy rész nem elvégezhető a rendelkezésre álló hozzáféréssel vagy időkerettel,
**ne csináld félig, magabiztos hangnemben**. Írd le konkrétan: mi csúszik meg, mi
kell hozzá, és mit végeztél el helyette. A többi részt vidd végig teljesen.

Külön figyelj: ha a sweep közben olyan **service-specifikus törést** találsz,
amit az előző job nem fogott meg, az **érdemi lelet**. Írd le a
`output/service-coverage.md`-ben — és ha kicsi, javítsd; ha nagy, jelezd, és ne
kezdj bele.

## Output

A `cic-factory` klónban, a `jobs/oci-extract-full-sweep/` alatt:

- `output/agent-output.md` — összefoglaló: mit csináltál, mi lett kész, mi nem
- `output/claim-evidence.md` — claim-evidence tábla, kötelezően ezekkel az
  oszlopokkal: **Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat**.
  A „Bizonyíték" oszlopba a ténylegesen lefuttatott parancs és a kimenete kerül,
  ne parafrázis. Amihez nem tudsz verifikációs módszert írni, az „nem igazolt".
- `output/service-coverage.md` — szolgáltatásonkénti lefedettség: N/N művelet,
  hiányzó method/path, indokolt kizárások
- `output/async-operations.md` — az (E) leltár + a `poll`-jelölt
- `output/egress-hosts.md` — az (F) leltár + a manifest-következmény
- `output/embedding-strategy.md` — a (D) **mérés** + a javasolt stratégia

A tényleges kód- és doc-változás a **modul-repóban** történik, nem a
cic-factoryban.

## Git

**`cic-module-oracle-cloud`** — klónozd a workspace-be, és a `devel`-ből nyiss
`feature/oci-extract-full-sweep` branchet. Ide commitolj és pusholj.
- ❌ NE pushol `devel`-re és NE `main`-re
- ❌ NE nyiss PR-t — a review és a merge az orchestrátoré
- Minden commit Vault-aláírt, `MANIFEST.sha256` utána regenerálva

**`cic-factory`** — csak az output dokumentumok, a feature branchre.

## Nyelvi szabály

Ez az `input.md` és a te gondolkodásod magyar. **Minden, ami a modul-repóba
kerül — kód, komment, `docs/**`, commit üzenet — angol.** Az
`output/*.md` a cic-factoryban magyar.
