# oci-instance-lifecycle-coverage — legyen szállított alternatív-igés erőforrás, és teszt a `Destroy`/`Invoke`-ra

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Te írod a kódot ebben a jobban. Nem te
indítottad ezt a jobot, nem te figyeled a futását, és nincs mire várnod: a
munka, amit az alábbiak leírnak, **a te dolgod, most**.

Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a
`workdir` operátora, aki a specet írta és a valós OCI tesztet futtatja majd).
Ne beszélj az ő nevében, és ne írj állapotjelentést erről a jobról — írd meg a
kódot.

## Reasoning mód

**implementation.** Kódot és tesztet írsz. A megoldandó rés **azonosítva és
mérve** van — nem kell újra felfedezned.

## Kontextus — három rés, egy közös ok

A `oci-lifecycle-role-bridge` job (mergelve, `8e379e8`) megjavította azt, hogy a
guest a **sémából** olvassa a lifecycle-szerepet, ne a Go művelet-névből. A
javítás valós OCI-n igazolt a `LaunchInstance`-re. **De három rés maradt, és
mindhárom ugyanabból fakad: nincs olyan szállított erőforrás, amin ez a
viselkedés rutinszerűen meghajtható.**

| Rés | Ma |
|---|---|
| A modul **két típust szállít** (`vcn`, `subnet`), mindkettő konvencionális igéjű | a szerep-javítás igazolásához **kétszer scratch sémát kellett beágyazni**; a regresszióvédelem fixture-alapú |
| A **`Destroy()` handler nincs a valós-OCI harnessben** | pedig itt volt a legsúlyosabb hiba: a `resolveOp` `"Delete"+resource`-t keresett, tehát a `Destroy` **teljesen működésképtelen** volt alternatív igés erőforrásra, és hazug műveletnevet írt volna a ProofTrace-be. **Csak fixture-szinten igazolt.** |
| Az **`Invoke()` sem** | `implemented`-nek jelölve a `provider.go` fejlécében, soha nem futott élesben |

Ez ugyanaz a szerkezet, ami a `poll`-nál volt: `implemented`-nek jelölve,
tesztje nincs, tehát senki nem tudta, hogy működik-e. A `poll` tesztje 2026-08-04-én
megíródott, és **azonnal ki is bukott egy hiba** (`percent_complete` mindig 0).

**A `Destroy` most pontosan ebben az állapotban van: javítottnak hisszük, de
élesben nem láttuk.**

### Orchestrátori döntés — hatókör

**Maradunk az OCI API szintjén.** A CIC séma-fordítás (`cic-primitives` /
ManagedEntity projekció) **külön, későbbi lépés** — ne kezdd el, ne tervezd meg,
ne írj rá scaffoldot.

## Kemény korlátok

1. **A CIC-Relay READ-ONLY.** Relay-igény → `R#` tétel a
   `docs/design/relay-requirements.md`-be, a relay **forrásából** vett bizonyítékkal.
2. **Ne köss be primitives/YANG sémát.**
3. **Ne hozz létre valós OCI erőforrást.** Az ok nem bizalmi: implementációs
   jobok ma négyszer futottak turn-limitbe munka közben, és egy ilyen
   megszakadás **futó VM-et** hagyna a tenancyben. A valós futtatás az
   orchestrátoré — lásd a „Verifikáció" szakaszt.
4. **`git add -A` TILOS** — a `make build` untracked, nem-gitignore-olt `.yaml`
   sidecarokat hagy, és a `MANIFEST.sha256` `git ls-files`-ra épül, tehát a
   szemét az **aláírt manifestbe** kerülne. Explicit path-listával commitolj, és
   `git status --short`-tal nézd meg, mi menne be. (cic-factory `ai/TODO.md` T10.)
5. **A repo dokumentációja angol.** Ez az `input.md` magyar, de minden ami a
   modul-repóba kerül — kód, komment, `docs/**` — **angolul**.

## Boot — konkrét források

A modul-repóban (saját klónodban, `devel`-ből ágazva):

- `module/contracts.go` — a `//go:embed` lista és a `role`-alapú `opByRole`
- `module/provider.go` — `Destroy()`, `Invoke()`, `Poll()` (a `Poll` a követendő minta)
- `module/manual_real_oci_test.go` — a harness; **`TestManualRealOCIPoll` a friss
  minta** arra, hogyan néz ki egy új teszt itt
- `mk/golang.mk` — `oci.generate` (a séma-generálás receptje) és
  `golang.test.manual-real-oci` (a horgonyzott `-run` minta)
- `docs/design/manual-verification.md` — a lefedettségi tábla, amit frissíteni kell
- `docs/design/roadmap.md` — P3.5 (a szállított resource-lista)
- `oci-sdk.lock.yaml` — `extracted_schema_hashes`, a szolgáltatásonkénti kapu

KB oldalról a `kb_focus`: `get_chunk("c1719")` (relay pozicionálás),
`get_chunk("c1734")` (séma belső viselkedés). **A chunk-id nem stabil
azonosító** — ellenőrizd a visszakapott `file_path`-t; ha nem a
`CIC-Relay/docs/hu/concept/` alatti fájlokra mutat, az id elavult: írd le az
outputban, és `search_query`-vel keresd meg tartalom alapján.

## Feladat

### A — `cic:compute:instance` legyen szállított séma

Az `Instance` séma generálása **már bizonyítottan működik** — a resolver helyesen
oldja fel (`LaunchInstance→create`, `TerminateInstance→delete`, mérve 2026-08-04).
A recept, ahogy az orchestrátor futtatta:

```
go run ./cmd/oci-extract -schema Instance -ns cic:compute:instance \
  "$SDK/launch_instance_details.go" "$SDK/update_instance_details.go" \
  "$SDK/instance.go" "$SDK/change_instance_compartment_details.go" \
  "$SDK/core_compute_client.go" > module/schemas/core/instance.json
```

Vedd fel az `oci.generate` targetbe, ágyazd be a `contracts.go`-ban, és
frissítsd az `extracted_schema_hashes`-t úgy, hogy a szolgáltatásonkénti kapu
működőképes maradjon.

**Ellenőrizd és írd le:** mit ad ezután a `describe()` a `resource_kinds`-ben, és
változik-e a `required_capabilities.egress_hosts` (a compute ugyanazt a
`iaas.<region>` hosztot használja, mint a network — de **mérd meg**, ne
feltételezd).

### B — `Destroy()` a valós-OCI harnessbe

**Ez a job legfontosabb része.** Írj `TestManualRealOCIDestroy`-t, ami a
tényleges `Destroy()` handlert hívja — nem az `Execute()`-ot.

Ez a különbség lényegi: az orchestrátor eddigi „törlés" tesztjei mind
`Execute(OCI_EXEC_OPERATION=DeleteX)` úton mentek, tehát a `Destroy()` kódútja
— benne a `resolveOp` és a ProofTrace-be kerülő művelet-címke — **soha nem futott
valós OCI ellen**.

A teszt env-guard mögött legyen, a `TestManualRealOCIPoll` mintájára. A
harnessnek **jeleznie kell**, hogy ez mutáló művelet.

### C — `Invoke()` a harnessbe

Írj `TestManualRealOCIInvoke`-ot ugyanezzel a mintával.

**Itt egy scoping kérdés van, amit neked kell eldöntened és leírnod:** az
`Invoke` egy `action-managed` mezőhöz kötött műveletet hajt végre (pl.
`ChangeInstanceCompartment`). Ehhez **második compartment kell**, és a trial
tenancy ma üres (nincs compartment a rooton kívül).

Ezért: **írd meg a tesztet, és írd le pontosan, mi kell a lefuttatásához.**
Ha arra jutsz, hogy valós futtatás nélkül csak a teszt megléte szállítható, azt
mondd ki — ne állítsd igazoltnak.

### D — A dokumentáció kövesse a bizonyítékot

- `docs/design/manual-verification.md`: a lefedettségi tábla kapjon `destroy` és
  `invoke` sort, a valós státusszal (`not run`, amíg az orchestrátor le nem
  futtatta). A `poll` sora frissítendő: **lefutott** 2026-08-04-én, `SUCCEEDED`.
- `docs/design/roadmap.md` **P3.5**: a szállított resource-lista most `vcn`,
  `subnet`, `instance` — igazítsd ahhoz, ami ténylegesen épül.
- `mk/golang.mk` `golang.test.manual-real-oci`: a horgonyzott `-run` minta ma
  `(Observe|Validate|Plan|Poll)$` — **ne** vedd bele a `Destroy`-t és az
  `Invoke`-ot, azok mutálnak. Külön, nevesített targetet adj nekik, vagy hagyd
  kézi futtatásra — a döntést indokold.

## Verifikáció — mi a tiéd és mi az orchestrátoré

**A tiéd:** minden fixture- és unit-szintű bizonyíték, a séma-generálás, a kapu,
a CI, és a harness-tesztek megléte + env-guardja.

**Az orchestrátoré:** a valós OCI elleni futtatás (POC trial tenancy,
`VM.Standard.E2.1.Micro`, Always Free). Az `output/orchestrator-verification.md`-be
írd le **konkrét parancsokkal**, mit kell lefuttatnia ahhoz, hogy a `Destroy`
valós OCI-n igazolt legyen — beleértve a felállás és a lebontás lépéseit.

## Definition of Done — gépileg ellenőrizhető

1. `make oci.generate` előállítja az `instance.json`-t is, és a
   szolgáltatásonkénti `-diff` kapu továbbra is nem-nulla exittel bukik egy
   szándékos törésen (mutasd a futást)
2. `describe()` `resource_kinds`-ben megjelenik a `cic:compute:instance` —
   **futtatott kimenettel** bizonyítva, nem a kód olvasásából
3. **Reachability:** az `instance` contract production úton elérhető —
   `file:line` a `contracts.go` embed-listától a `resourceContracts()`-ig, plusz
   egy production hívó. „A fájl ott van" ≠ „a guest betölti". Bizonyítás:
   ```bash
   grep -rn "instanceSchemaJSON\|cic:compute:instance" module/*.go | grep -v _test.go
   ```
   és a hívó fájl:sor megadása (teszt nem számít hívónak)
4. `TestManualRealOCIDestroy` és `TestManualRealOCIInvoke` **létezik**, env-guard
   mögött van, és guard nélkül **nem** ad hálózati hívást (mutasd meg, hogy
   üres env-vel elszáll, nem fut)
5. A `vcn`+`subnet` lefedettsége **nem romlik** — regressziós teszt zöld
6. `make check` + wasm build/test zöld
7. `MANIFEST.sha256` regenerálva, `manifest-verify` zöld
8. `docs.link-check` zöld
9. CI zöld a pusholt feature branchen — **a `headSha`-t egyeztesd** a tesztelt
   committal

## Tiltott rövidítések

- **fájl létezése ≠ szállítva** — a `instance.json` megléte nem bizonyítja, hogy
  a guest betölti; ezt kéri a (3) pont
- **teszt megléte ≠ a viselkedés igazolva** — a `Destroy` teszt megírása nem
  ugyanaz, mint a `Destroy` igazolása. Ne írd `verified`-nek, amíg nem futott
- **exit code 0 ≠ sikeres** — a kimenetet olvasd el
- **„a compute ugyanaz a hoszt, mint a network"** — az (A) pont ezt mérni kéri
- **névből levezetett szerep bárhol** — ez a javított hiba, ne hozd vissza

## Ha elakadsz

Ha egy rész nem elvégezhető, **ne csináld félig, magabiztos hangnemben**. Írd le:
mi csúszik meg, mi kell hozzá, mit végeztél el helyette. A többit vidd végig.

## Output

A `cic-factory` klónban, a `jobs/oci-instance-lifecycle-coverage/` alatt:

- `output/agent-output.md` — összefoglaló: mit csináltál, mi lett kész, mi nem
- `output/claim-evidence.md` — claim-evidence tábla, kötelezően ezekkel az
  oszlopokkal: **Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat**.
  A „Bizonyíték" oszlopba a ténylegesen lefuttatott parancs és a kimenete kerül.
- `output/orchestrator-verification.md` — a valós-OCI recept, konkrét parancsokkal
- `output/invoke-scope.md` — a (C) döntés: mi kell az `Invoke` valós teszteléséhez,
  és mi az, ami ebben a jobban szállítható

## Git

**`cic-module-oracle-cloud`** — klónozd a workspace-be, `devel`-ből nyiss
`feature/oci-instance-lifecycle-coverage` branchet. Ide commitolj és pusholj.
- ❌ NE pushol `devel`-re és NE `main`-re · ❌ NE nyiss PR-t
- Vault-aláírt commitok, `MANIFEST.sha256` utána regenerálva
- **`git add -A` tilos** (lásd a korlátoknál)

**`cic-factory`** — csak az output dokumentumok, a feature branchre.

## Nyelvi szabály

Ez az `input.md` és a gondolkodásod magyar. **Minden, ami a modul-repóba kerül —
kód, komment, `docs/**`, commit üzenet — angol.** Az `output/*.md` magyar.
