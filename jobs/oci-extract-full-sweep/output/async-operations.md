# Aszinkron műveletek leltára (Task E)

## Módszer

A `poll` a modulban `blocked`, mert a `core/network`-ben (VCN/Subnet) nem
találtunk valódi Work Request-et: `CreateVcn`/`UpdateVcn` szinkron, nincs
`opc-work-request-id` válaszfejléc (`docs/design/manual-verification.md`).

A sweep tool minden művelet válasz-modelljét megnézi: van-e olyan mező,
aminek `presentIn:"header"` és `name:"opc-work-request-id"` — ez az SDK saját
jele arra, hogy a válasz egy valódi, pollozható Work Request-et ad vissza,
nem csak szinkron eredményt.

**Keresztellenőrzés a forrásban** (nem csak a sweep kimenetére hagyatkozva):

```
$ grep -n "opc-work-request-id\|type LaunchInstanceResponse" \
    core/launch_instance_request_response.go
78:type LaunchInstanceResponse struct {
96:	OpcWorkRequestId *string `presentIn:"header" name:"opc-work-request-id"`

$ grep -n "opc-work-request-id\|type CreateVcnResponse" \
    core/create_vcn_request_response.go
78:type CreateVcnResponse struct {
(nincs opc-work-request-id sor)
```

Ez pontosan megerősíti a modul saját, valós-OCI-n mért megfigyelését
(`CreateVcn` szinkron) **és** megkülönbözteti tőle a `LaunchInstance`-t
(van work request fejléc) — a detektor tehát nem hamis pozitív.

## A szám

**2238 aszinkron-jelölt művelet, 117 szolgáltatásban** (168-ból) — azaz a
teljes SDK egy jelentős, mérhető hányada valóban Work Request-alapú, csak a
modul jelenlegi PoC-felülete (VCN, Subnet) történetesen nem az.

Legtöbb jelölt szolgáltatásonként (top 10):

| Szolgáltatás | Aszinkron jelölt |
|---|---:|
| database | 265 |
| datasafe | 177 |
| **core** | **73** |
| opsi | 71 |
| bds | 64 |
| databasemanagement | 60 |
| osmanagementhub | 58 |
| fleetappsmanagement | 58 |
| dbmulticloud | 51 |
| goldengate | 46 |

## A `core` szolgáltatás saját 73 jelöltje

Mivel a modul ma is a `core` csomagot importálja (VCN+Subnet), itt van a
legkisebb súrlódású bővítési pont — nem kell új szolgáltatást bekötni a
`poll` teszteléséhez. Néhány releváns jelölt `core`-on belül:

```
core:LaunchInstance          core:TerminateInstance
core:CreateComputeCapacityReservation
core:CreateDedicatedVmHost
core:AddVcnCidr   core:RemoveVcnCidr   core:ModifyVcnCidr   (VCN CIDR akciók!)
core:ChangeVcnCompartment    core:ChangeSubnetCompartment
core:PatchVcn                core:PatchSubnet
```

(A teljes 73-as lista a sweep report `services[].async_work_request_ops`
mezőjében van, `core` szolgáltatásnál — reprodukálható a
`service-coverage.md` reprodukálási parancsával, `-write-schemas` nélkül is,
mert ez a mező mindig kiíródik.)

## A jelölt: `core:LaunchInstance`

**Ezt javaslom** a `poll` valós-OCI tesztelésére, nem egy másik
szolgáltatást:

- **Ugyanabban a `core` csomagban van**, mint a már bevált VCN/Subnet —
  nincs szükség új séma-pipeline munkára a modellek feloldásához, a P2.2-es
  gépezet (`Resolve`) már ma is kezeli (`LaunchInstance` → `LaunchInstanceDetails`,
  ez a P2.5 spec névvel is dokumentált kivétele: "core.Instance is created by
  LaunchInstance → LaunchInstanceDetails").
- **Valódi, ismert OCI-viselkedés**: egy Compute Instance indítása a valós
  OCI-ban közismerten aszinkron (a VCN/Subnet — ami szinkronnak bizonyult —
  ezzel szemben kivétel, nem szabály).
- **Olcsón, egyszer tesztelhető** egy eldobható trial tenancy-n — egy kis
  shape-ű VM (pl. `VM.Standard.E2.1.Micro`) indítása és leállítása gyors és
  nem drága, ellentétben pl. egy dedikált host (`CreateDedicatedVmHost`) vagy
  kapacitás-rezervációval, amik szintén a listán vannak, de drágábbak/
  korlátozottabbak trial tenancy-n.
- **Van hozzá pár is**: `TerminateInstance` is aszinkron — a meglévő
  `manual-verification.md`-mintát (Create→Update→Delete lifecycle egy
  eldobható tenancy-n) egy az egyben követhető: Launch→(poll)→Terminate.

**Amit nem teszteltem** (a job spec szerint nem is kellett): a fenti
javaslatot valós OCI ellen **nem** futtattam le — tenancy-hozzáférés kell
hozzá, ami ennek a sweep-nek nem volt hatásköre. A jelölt megnevezése és az
indoklás a szállítandó.
