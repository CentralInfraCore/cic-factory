# oci-lifecycle-role-bridge — a lifecycle-szerep kerüljön a sémába, ne a névbe

## Reasoning mód

**implementation.** Kódot és tesztet írsz. A hiba diagnózisa **kész és mérve** —
nem kell újra felfedezned. A dolgod a javítás és a bizonyítás.

## Kontextus — mit találtunk, méréssel

2026-08-04-én valós OCI tenancy ellen létrehoztunk egy VM-et a modullal. A
`LaunchInstance` **HTTP 400 `CannotParseRequest`**-tel elbukott. Az ok:

`module/provider.go` `renderBody` a **Go művelet-név prefixéből** dönt:

```go
case strings.HasPrefix(po.Operation, "Create"):  // minden mező
case strings.HasPrefix(po.Operation, "Update"):  // csak mutable
default:                                          // csak action-managed
```

A `LaunchInstance` egyik prefixre sem illeszkedik → az **akció-ágra** esik → a
kimenő body **üres `{}`**.

**A gyökérok mélyebben van:** a legenerált séma `operations` térképe csak
`method` / `path` / `path_params` mezőt hordoz — **lifecycle-szerepet nem**.
A `tools/oci-extract` resolvere build-time *tudja*, melyik művelet a create
(a `oci-extract-generalize` job óta strukturálisan vezeti le, nem névből), de
ezt a tudást **nem írja bele a kimenetbe**. A guestnek így nem marad más jele,
mint a név — és az az alternatív igéknél hazudik.

**A hatás számokban:** a build-time registry **1217 erőforrásból 570-nek**
nem `Create<R>Details` a create modellje. Ezeket a modul ma **nem tudja
provisionálni**, pedig a sémájuk legenerálódik, validál, és a plan is lefut.
Ugyanaz a „validates and is wrong" osztály, mint amit a `oci-extract-generalize`
javított — csak **egy réteggel lejjebb**. Az a javítás félúton megállt: az
extractor ige-agnosztikus lett, a futásidejű guest nem.

### Orchestrátori döntés — hatókör

**Maradunk az OCI API szintjén.** A CIC séma-fordítás (`cic-primitives` /
ManagedEntity projekció) **külön, későbbi lépés** — ebben a jobban ne kezdd el,
ne tervezd meg, és ne írj rá scaffoldot.

## Kemény korlátok

1. **A CIC-Relay READ-ONLY.** Relay-igényt találsz → `R#` tétel a
   `docs/design/relay-requirements.md`-ben, a relay **forrásából** vett
   bizonyítékkal.
2. **Ne köss be primitives/YANG sémát**, ne írj `ManagedEntity`-projekciót.
3. **Ne hozz létre valós OCI erőforrást.** Ennek az okát lásd a „Verifikáció"
   szakaszban — nem bizalmi kérdés, hanem az, hogy egy turn-limitbe futó job
   futó VM-et hagyhat maga után.
4. **A repo dokumentációja angol.** Ez az `input.md` magyar, de minden ami a
   modul-repóba kerül — kód, komment, `docs/**` — **angolul**.
5. **`git add -A` TILOS** — a `make build` untracked, nem-gitignore-olt `.yaml`
   sidecarokat hagy minden `.go`/`.py` mellé, és a `MANIFEST.sha256` képlete
   `git ls-files`-ra épül, tehát a szemét az **aláírt manifestbe** kerülne.
   Explicit path-listával commitolj, és `git status --short`-tal nézd meg, mi
   menne be. (cic-factory `ai/TODO.md` **T10**.)

## Boot — konkrét források

A modul-repóban (saját klónodban, `devel`-ből ágazva):

- `module/provider.go` — `renderBody` (a bizonyított hiba helye) és
  `planProviderOps` (lásd lent)
- `module/contracts.go` — `resourceContracts()`, ami a sémát contracttá parse-olja
- `tools/oci-extract/resolve.go` — itt él a strukturális lifecycle-levezetés
- `tools/oci-extract/schema.go` — ami a séma-bundle-t kibocsátja
- `module/schemas/core/{vcn,subnet}.json` — a jelenlegi kimenet alakja
- `oci-sdk.lock.yaml` — `extracted_schema_hashes` (szolgáltatásonkénti kapu)
- `docs/design/specs/oci-schema-pipeline.md` — a pipeline szerződése
- `docs/design/manual-verification.md` — mi van valós OCI-n igazolva

KB oldalról a `kb_focus` a kötelező első olvasás: `get_chunk("c1719")` a relay
pozicionálásra, `get_chunk("c1734")` a séma belső viselkedésére
(`StateRequirement`/`Dependencies`/`PluginRef`/`NextHops`). **A chunk-id nem
stabil azonosító** — ellenőrizd a visszakapott `file_path`-t; ha nem a
`CIC-Relay/docs/hu/concept/` alatti fájlokra mutat, az id elavult: írd le az
outputban, és `search_query`-vel keresd meg tartalom alapján.

## Feladat

### A — A szerep kerüljön be a sémába

A `tools/oci-extract` emittálja a lifecycle-szerepet az `operations` térképbe,
minden művelet mellé. A szerep-halmaz legyen zárt és nevesített (pl.
`create` / `read` / `update` / `delete` / `action`).

Az információ **már megvan** a resolverben — ne vezesd le újra, és **ne
névből**. A `resolve.go` strukturális szabálya (read = `GET readPath`,
create = `POST` a kollekciós útra, stb.) az egyetlen igazságforrás; a séma
ennek a *rögzítése*.

Ez érinti a generált sémákat és az `extracted_schema_hashes`-t — a
szolgáltatásonkénti kapu maradjon működőképes.

### B — A guest a szerepet olvassa, ne a nevet

`module/contracts.go` vegye át a szerepet a contractba, és a
`module/provider.go` **minden** olyan helye, ami ma Go-névből következtet
lifecycle-re, erre álljon át.

A `renderBody` **bizonyítottan** ilyen. **Vannak továbbiak — ezeket neked kell
megtalálnod.** Konkrét jelzés, amit ellenőrizz: a `planProviderOps` kommentje
(`provider.go` környékén) azt írja, hogy *„by the SDK naming convention
(Create/Update/Delete<Resource>)"* dolgozik. Ezt **mérd meg**, ne feltételezd.

Keresd meg az összeset:

```bash
grep -rn 'HasPrefix(.*"Create"\|HasPrefix(.*"Update"\|HasPrefix(.*"Delete"\|"Create"+\|"Delete"+' module/*.go | grep -v _test.go
```

Minden találathoz írd le: **hova esik ma egy alternatív igés művelet**, és mi
lesz belőle a javítás után.

### C — Poll teszt a harnessbe

A `module/manual_real_oci_test.go`-ban ma **nincs Poll teszt** — csak
`Observe`/`Validate`/`Plan`/`Execute`. Ezért nem verifikálta soha senki a
`poll`-t, pedig a `provider.go` fejlécében `implemented`-ként szerepel.

Írj hozzá egy Poll tesztet, ami egy Work Request OCID-t vesz env-ből (a
mintát a többi teszt adja) és a modul `Poll` handlerét hajtja meg. **Ne
futtasd valós OCI ellen** — a tesztnek attól kell működnie, hogy létezik és
env-guard mögött van, ahogy a többi.

Amit tudni érdemes hozzá: `LaunchInstance` és `TerminateInstance` **valódi
Work Requestet ad** (mérve, `work_request_id` a válaszban), a
`CreateVcn`/`UpdateVcn` **nem** (szinkron).

### D — Fixture-szintű bizonyíték az alternatív igékre

Írj tesztet, ami **valós OCI nélkül** bizonyítja, hogy a javítás működik:
egy `Instance`-szerű contract (alternatív `LaunchInstance`/`TerminateInstance`
igékkel) create-jére a `renderBody` **teljes bodyt** ad, nem üreset — és
delete-re `nil`-t.

A `tools/oci-extract/testdata/` már tartalmaz `instance.go` és
`compute_client.go` fixture-t a `oci-extract-generalize` jobból — használd
azokat, ne gyárts újat.

## Verifikáció — mi a tiéd és mi az orchestrátoré

**A tiéd:** minden fixture- és unit-szintű bizonyíték, a séma-regenerálás, a
kapu, a CI.

**Az orchestrátoré:** a valós OCI elleni futtatás. **Ezt te ne csináld.** Nem
bizalmi kérdés: ma három job futott turn-limitbe munka közben, és egy ilyen
megszakadás egy **futó VM-et** hagyna a tenancyben. A recept (mérve, működik):

```
POC (oc1) trial tenancy · VM.Standard.E2.1.Micro (Always Free) · eu-frankfurt-1
CreateVcn → CreateSubnet → LaunchInstance → Observe → TerminateInstance
→ DeleteSubnet → DeleteVcn
```

Az outputban írd le, **mit kell az orchestrátornak lefuttatnia** ahhoz, hogy a
javítást valós OCI-n igazolja — konkrét parancsokkal.

## Definition of Done — gépileg ellenőrizhető

1. A generált sémák hordozzák a szerepet, és az `oci-extract -diff`
   szolgáltatásonkénti kapuja továbbra is nem-nulla exittel bukik egy
   szándékos törésen (mutasd a futást)
2. A (B) grep **nulla** olyan találatot ad, ami lifecycle-döntést hoz Go-névből
   a production kódban — vagy ami marad, ahhoz írd le, miért helyes
3. A fixture-teszt (D) zöld, és **bukik**, ha a javítást visszaveszed
   (mutasd meg mindkét irányt)
3/b. **Reachability-bizonyíték a szerepre.** „A sémában van szerep-mező" ≠ „a
   guest használja". Add meg a **production hívási láncot `file:line`-nal**:
   melyik sor olvassa ki a szerepet a sémából (`contracts.go`), melyik sor
   fogyasztja el a döntésnél (`provider.go`), és melyik production hívó jut el
   odáig — teszt nem számít hívónak. Bizonyítás:
   ```bash
   grep -rn "<szerep-mező neve>" module/*.go | grep -v _test.go
   ```
   plusz a hívó fájl:sor megadása. Ha elérhető, `deadcode ./...` kimenettel
   erősítsd meg; ha nincs telepítve, írd le hogy nem futott.
4. `make check` + wasm build/test zöld
5. `MANIFEST.sha256` regenerálva, `manifest-verify` zöld
6. `docs.link-check` zöld
7. CI zöld a pusholt feature branchen — **a `headSha`-t egyeztesd** a tesztelt
   committal

## Tiltott rövidítések

- **fájl létezése ≠ kész** — a séma új mezője önmagában nem bizonyítja, hogy a
  guest használja is
- **teszt zöld ≠ a viselkedés meghajtva** — a (3) pont ezért kéri a bukást is
- **exit code 0 ≠ sikeres** — a kimenetet olvasd el
- **„a többi hívási hely valószínűleg jó"** — a (B) pont pont ezt méri
- **névből levezetett szerep bárhol** — ez maga a javítandó hiba

## Ha elakadsz

Ha egy rész nem elvégezhető, **ne csináld félig, magabiztos hangnemben**. Írd
le: mi csúszik meg, mi kell hozzá, mit végeztél el helyette. A többit vidd
végig teljesen.

## Output

A `cic-factory` klónban, a `jobs/oci-lifecycle-role-bridge/` alatt:

- `output/agent-output.md` — összefoglaló: mit csináltál, mi lett kész, mi nem
- `output/claim-evidence.md` — claim-evidence tábla, kötelezően ezekkel az
  oszlopokkal: **Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat**.
  A „Bizonyíték" oszlopba a ténylegesen lefuttatott parancs és a kimenete kerül.
- `output/name-derived-lifecycle.md` — a (B) leltár: minden hely, ami névből
  következtetett, hova esett egy alternatív ige, és mi lett belőle
- `output/orchestrator-verification.md` — a valós-OCI recept az orchestrátornak,
  konkrét parancsokkal

## Git

**`cic-module-oracle-cloud`** — klónozd a workspace-be, `devel`-ből nyiss
`feature/oci-lifecycle-role-bridge` branchet. Ide commitolj és pusholj.
- ❌ NE pushol `devel`-re és NE `main`-re · ❌ NE nyiss PR-t
- Vault-aláírt commitok, `MANIFEST.sha256` utána regenerálva
- **`git add -A` tilos** (lásd a korlátoknál)

**`cic-factory`** — csak az output dokumentumok, a feature branchre.

## Nyelvi szabály

Ez az `input.md` és a gondolkodásod magyar. **Minden, ami a modul-repóba kerül —
kód, komment, `docs/**`, commit üzenet — angol.** Az `output/*.md` magyar.
