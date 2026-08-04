# oci-lifecycle-role-bridge — agent output

## KB boot

`c1719` és `c1734` mindkettő létezik és tartalmilag illeszkedik: `c1719` a relay
végrehajtó-motor pozicionálását adja (`CIC-Relay/docs/hu/concept/relay_pozicionalas.md`),
`c1734` a séma belső viselkedését (`StateRequirement`/`Dependencies`/`PluginRef`/
`NextHops`, `CIC-Relay/docs/hu/concept/schema_kezeles.md`). Egyik sem üres, mindkettő
a várt fájlra mutat — nincs elavult chunk-id.

## Mit csináltam

### A — lifecycle-szerep a sémában

`tools/oci-extract/resolve.go` már definiálta a zárt szerep-halmazt (`RoleRead`/
`RoleCreate`/`RoleUpdate`/`RoleDelete`/`RoleAction`, `resolve.go:43-47`), de **sehol
nem használta senki** — méréssel igazolva (`grep` nulla találatot adott a
konstansokra a resolve.go-n kívül, mielőtt hozzányúltam).

`tools/oci-extract/schema.go`'s `OperationMap` most minden operation-bejegyzéshez
hozzáadja a `role` mezőt, közvetlenül a `Resolution` már meglévő
`ReadOp`/`CreateOp`/`UpdateOp`/`DeleteOp`/`ActionOps` mezőiből — nem vezetem le
újra, csak rögzítem, amit a resolver már tud (`schema.go:170-198`).

Regeneráltam a `module/schemas/core/{vcn,subnet}.json`-t a valós OCI SDK
(v65.121.0) ellen, `make oci.generate`-tel. Minden operation-bejegyzés most
`role`-t hordoz (`GetVcn: role=read`, `CreateVcn: role=create`, stb.). Frissítettem
`oci-sdk.lock.yaml`'s `extracted_schema_hashes.core`-ját az új hash-re, és a
`tools/oci-extract/regression_test.go` frozen-expectation táblázatát kiegészítettem
a `role` oszloppal minden vcn/subnet operation-re.

### B — a guest a szerepet olvassa

`module/contracts.go`: a `resourceContract.operations` (`httpOp`) most `role`-t is
hordoz, a JSON `x-cic-resource`-ból konstruált `resource` mezőt **eltávolítottam**
(semmi nem olvasta többé — lásd lent). Új `opByRole(role)` metódus adja vissza a
resource egyetlen create/read/update/delete műveletét szerep szerint.

`module/provider.go` **hat** helyét találtam, ami Go-névből (vagy a resource SDK
nevéből string-konkatenációval) vezetett le lifecycle-döntést — a bizonyított
`renderBody` mellett ötöt magamnak kellett feltárnom (`grep`-pel indultam, majd
minden találatot kézzel követtem a hívási láncig). Részletes leltár:
[`name-derived-lifecycle.md`](name-derived-lifecycle.md). Rövid összefoglaló:

1. `planProviderOps` replace-ág (`"Delete"+c.resource`, `"Create"+c.resource`)
2. `planProviderOps` update-ág (`"Update"+c.resource`)
3. `Destroy()` step-címke (`"Delete"+c.resource`)
4. `resolveOp()` (`c.operations[verb+c.resource]`) — ez törte volna el ténylegesen
   a `Destroy`-t minden alternatív-igés resource-ra (nem csak kozmetikai hiba)
5. `Observe()` (`c.operations["Get"+c.resource]`)
6. `renderBody()` (`strings.HasPrefix(po.Operation, "Create"/"Update"/"Delete")`)
   — ez a valós OCI ellen bizonyított hiba

Mind a hat helyet átírtam, hogy a sémából kiolvasott `role`-t használja
(`opByRole` vagy közvetlen `c.operations[name].role` lookup), sosem a nevet.

### C — Poll teszt a manual harnessbe

`module/manual_real_oci_test.go`-ba felvettem `TestManualRealOCIPoll`-t, ugyanazt
a mintát követve, mint a többi manual teszt (env-guard + `REAL_OCI_TEST=1` +
`manual_real_oci` build tag). `OCI_POLL_PATH` env-ből veszi a Work Request GET
path-ot (a `binding.base_path`-ot **nem** fűzi elé — ez eltér `Observe`/`Execute`
mintájától, dokumentáltam a különbséget). Hozzáadtam a Makefile
`golang.test.manual-real-oci` cél `-run` mintájához is (`Observe|Validate|Plan|Poll`),
mert a Poll is read-only.

Frissítettem `docs/design/manual-verification.md` `poll` sorát: a teszt most
létezik (korábban `blocked` volt — nem is volt kód, ami futtatható lett volna),
de valós OCI ellen még nem futott (ezt tudatosan nem én futtatom, lásd
[`orchestrator-verification.md`](orchestrator-verification.md)).

### D — Fixture-szintű bizonyíték

`module/contracts_test.go` (új fájl): a valós extraktorral legeneráltam a
`tools/oci-extract/testdata/{instance.go,compute_client.go}` fixture-ökből egy
teljes séma-bundle-t (`module/testdata/instance-fixture.json`) — ugyanazzal a
paranccsal, mint a `make oci.generate`, csak a fixture fájlokra mutatva, nem a
valós SDK-ra. A contracts.go parse-logikáját kifaktoráltam egy újrafelhasználható
`parseContractBundle` függvénybe, hogy a teszt ugyanazt a kódutat fusson meg,
mint a production `resourceContracts()`.

Három teszt: `TestRenderBodyAltVerbCreate` (LaunchInstance → teljes body),
`TestRenderBodyAltVerbDelete` (TerminateInstance → nil), `TestRenderBodyAltVerbUpdate`
(UpdateInstance → csak a mutable mezők). Mindhárom zöld a javítással.

**Bukás igazolva mindkét irányban** (nem csak állítás): ideiglenesen visszaállítottam
a `renderBody` régi prefix-alapú logikáját (a `contracts.go`/`opByRole` infrastruktúra
érintetlenül hagyásával, hogy pontosan a `renderBody`-döntést izoláljam), lefuttattam
a teszteket — `TestRenderBodyAltVerbCreate` és `TestRenderBodyAltVerbDelete` buktak
(`{}` helyett a várt teljes body / nil), `TestRenderBodyAltVerbUpdate` véletlenül
zöld maradt (mert `"UpdateInstance"` névre a régi `HasPrefix(.., "Update")` is
illeszkedik — ez maga is dokumentálja, hogy a régi kód csak akkor "működött", ha az
SDK véletlenül a konvenciót követte). Utána visszaállítottam a javítást, `diff`-fel
igazoltam a fájl bájt-pontos visszaállítását, és a tesztek újra zöldek.

## Mi maradt hátra / mit NEM csináltam

- **Nem futtattam semmit valós OCI ellen** — sem a Poll tesztet, sem semmi mást.
  Ez szándékos, lásd a job korlátait és [`orchestrator-verification.md`](orchestrator-verification.md).
- A `deadcode ./...` a wasm guest csomagon **nem futtatható**: `go/packages`
  `GOOS=wasip1` alatt nem tudja feloldani a `//export allocate`/`//export deallocate`
  cgo-szimbólumokat (ezek TinyGo-specifikus linkelést igényelnek, amit a sima
  `go` toolchain deadcode-elemzése nem ismer). Pontos parancs és hibaüzenet a
  [`claim-evidence.md`](claim-evidence.md)-ben. Helyette kézzel, `grep` +
  `file:line` hívási lánccal igazoltam a reachability-t.
- **Nem érintettem a CIC séma-fordítást** (`cic-primitives`/`ManagedEntity`) —
  a job spec explicit tiltotta, be sem terveztem.
- **Nem hoztam létre valós OCI erőforrást.**

## Untracked `.yaml` sidecar-ok

A workspace klónban minden `.go`/`.py` fájl mellett automatikusan megjelent egy
azonos nevű, nem git-tracked `.yaml` companion (a `CLAUDE.md` T10 pontja által
jelzett ismert jelenség). Ezek **nem kerültek be a commitba** — explicit
path-listával adtam hozzá a git indexhez a valós forrásfájlokat, és a
`MANIFEST.sha256`-ot csak ez után regeneráltam. A sidecar-okat töröltem a
munkakönyvtárból, mielőtt a `make check`/`yamllint`-et lefuttattam (különben a
yamllint hamis hibákat adott volna rájuk — ez maga is bizonyítja, hogy ezek a
fájlok tényleg nem részei a valós build/CI pipeline-nak, hiszen CI egy tiszta
checkout-on fut, ahol ezek a companion fájlok nem is léteznek).

## Verifikáció — teljes CI pipeline lokálisan lefuttatva

A `.github/workflows/ci.yml` minden lépését lefuttattam sorban, lokálisan, a
`builder` docker-compose service-ben — mind zöld. Részletek és pontos parancsok:
[`claim-evidence.md`](claim-evidence.md).
