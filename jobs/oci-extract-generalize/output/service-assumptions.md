# Service-specifikus feltételezések — mit találtam, mi tört el, hogyan oldottam fel

Minden sor **mért**, nem olvasatból következtetett. A „hol tört el" oszlopban a
`fájl:sor` a **változtatás előtti** kódra mutat (`HEAD~1` =
`6331e76`, a modul-repóban), a kimenet pedig a ténylegesen lefuttatott parancsé.

A mérés eszköze: a pinelt SDK (`v65.121.0`, `oci-sdk.lock.yaml`) **összes**
kliensfájlja — 319 fájl, 171 szolgáltatás. Az operáció-oldali mérés teljes körű
volt; a séma-oldali mérés a lent indokolt heterogén mintán futott.

---

## Miért ez a minta

A job azt kérte, hogy a választás **szándékosan törésre menjen**, ne zöldre. A
minta ezért nem „reprezentatív keresztmetszet", hanem hat eset, amelyek mindegyike
**más** feltételezést támad, és egy kontrollcsoport:

| Szolgáltatás | Mit hivatott eltörni | Miért pont ez |
|---|---|---|
| `core` virtualnetwork | — (kontroll) | a P2.2 bizonyított alapja; ha ez elmozdul, a refaktor rontott |
| `core` compute | a `Create`/`Delete` ige-konvenciót | **ugyanaz a Go package**, mint a VCN → izolálja a *névadást* a *szolgáltatástól* |
| `identity` | a „van request objektum" feltételezést | nem-regionális, globális végpontú szolgáltatás, más kliens-generálási úttal |
| `objectstorage` | az „egy path-paraméter, és az az id" feltételezést | névvel címzett erőforrás namespace-en belül; nincs is OCID-je |
| `database` | a „minden modell struct" feltételezést | a legnagyobb felület (456 művelet), polimorf create-testekkel |
| `dns` | ugyanezt, más alakban | polimorf create-*base* egy konkrét create mellett |

---

## A1 — Egy műveletnek van request objektuma

**Hol tört el:** `tools/oci-extract/client.go:182`

```go
return req, resp, req != "" && resp != ""
```

és `tools/oci-extract/client.go:118`

```go
if !ok || sel.Sel.Name != "HTTPRequest" || len(call.Args) < 2 {
```

**Az eltörő kimenet.** Az `IdentityClient.ListRegions(ctx)` nem kap request
objektumot — és pont ezért a privát fele nem tud `request.HTTPRequest(...)`-et
hívni, hanem a csomagszintű `common.MakeDefaultHTTPRequest`-et használja. A régi
extractor mindkét szűrőn elvérzett, és **némán** kihagyta:

```
$ /tmp/audit/audit $SDK/identity/identity_client.go
    EXCLUDED-EXPORTED: ConfigurationProvider ListRegions SetRegion UnmarshalPolymorphicJSON
identity/identity_client.go   candidates=144  resolved=144  missing=0  orphanPriv=0
```

Figyelem a csapdára: `missing=0`. A régi számláló **magát a jelöltek halmazát**
szűkítette, így a hiány sosem jelent meg hiányként. Az SDK egészén ez
8047/8047-nek látszott, miközben a valóság 8047/**8048**.

A forrás, ami ezt eldöntötte (`$SDK/identity/identity_client.go:6816`):

```go
httpRequest := common.MakeDefaultHTTPRequest(http.MethodGet, "/regions")
```

Az SDK-ban ez az **egyetlen** ilyen eset:

```
$ grep -rhoE "[A-Za-z_.]*HTTPRequest[A-Za-z]*\(" $(cat /tmp/clients.txt) | sort | uniq -c
   8047 request.HTTPRequest(
      2 common.MakeDefaultHTTPRequestWithTaggedStruct(   # common/auth, nem szolgáltatás
      1 common.MakeDefaultHTTPRequest(
```

**Hogyan oldottam fel.** A művelet-teszt a `*Response` eredmény lett; a request
opcionális. A wire-hívás matcher pedig névhalmazt néz (`httpRequestFuncs`), mert
mindegyik konstruktor `(method, path, …)` prefixű. Nem különeset: egy szabály,
ami mindhárom alakot lefedi.

**Mérés utána:**

```
$ oci-extract -audit $(cat /tmp/clients.txt) | tail -1
TOTAL 8048/8048 operations resolved, 0 missing method/path
$ oci-extract $SDK/identity/identity_client.go | jq '.operations[]|select(.name=="ListRegions")'
  ListRegions GET /regions request='' response=ListRegionsResponse
```

---

## A2 — A create ige „Create", a delete ige „Delete"

**Hol tört el:** `tools/oci-extract/schema.go:38` és `tools/oci-extract/policy.go:139`

```go
create := byName["Create"+resource+"Details"]
```

valamint `tools/oci-extract/schema.go:161` (`ResourceOperationMap`)

```go
"Get" + resource:    true, // observe (read)
"Create" + resource: true,
"Update" + resource: true,
"Delete" + resource: true,
```

**Az eltörő kimenet.** A `core.Instance`-t a `LaunchInstance` hozza létre
(`LaunchInstanceDetails`) és a `TerminateInstance` törli. A régi extractor
lefutott, **exit 0**-val, és ezt adta:

```
$ /tmp/oci-extract-baseline -schema Instance -ns cic:compute:instance \
    $SDK/core/launch_instance_details.go $SDK/core/update_instance_details.go \
    $SDK/core/instance.go $SDK/core/change_instance_compartment_details.go \
    $SDK/core/core_compute_client.go
config props: 22   required: None
state props: 36
operations: ['ChangeInstanceCompartment', 'GetInstance', 'UpdateInstance']
```

Ez a legveszélyesebb találat, mert **nem hibázik**: érvényes draft-07 sémát ad,
`required` lista **nélkül**, és a config felület csak abból áll, ami az Update és
a Read metszetében véletlenül benne volt. A create és delete művelet egyszerűen
eltűnt az `operations` térképről — a plan tehát nem tudott volna se létrehozni,
se törölni.

Az SDK egészén ez nem kivétel: **1217 erőforrásból 570-nek nincs
`Create<R>Details` modellje.**

**Hogyan oldottam fel.** A lifecycle-t az HTTP felületből vezetem le
(`tools/oci-extract/resolve.go`), nem a Go azonosítókból:

```
read       = GET  <readPath>
collection = readPath a lezáró /{param} nélkül
create     = POST <collection>
update     = PUT  <readPath>, különben POST <readPath>
delete     = DELETE <readPath>
actions    = POST a <readPath>/… alatt
```

A body-modell pedig a request struct saját `contributesTo:"body"` tagjéből jön —
tehát az SDK saját tagjéből, sosem névből.

**Mérés utána:**

```
$ oci-extract -schema Instance -ns cic:compute:instance <ugyanaz a fájllista>
config props: 35   required: ['availabilityDomain', 'compartmentId']
state props: 36
operations: ChangeInstanceCompartment, GetInstance, LaunchInstance,
            TerminateInstance, UpdateInstance
```

`LaunchInstance` = `POST /instances`, `TerminateInstance` = `DELETE
/instances/{instanceId}` — név-alapú különeset nélkül.

---

## A3 — Egy erőforrást egy path-paraméter címez, és az az id-ja

**Hol tört el:** sehol nem volt kódban — **ez a hiány maga a hiba.** A registry
egyetlen mezőt sem tárolt a path-paraméterekről. A feltételezés a fogyasztó
oldalán csapódott le: `module/provider.go:1059`

```go
func templatePath(path, resourceID string) string {
	// minden {param}-ot UGYANAZZAL a resourceID-vel helyettesít
```

**Az eltörő kimenet.** A VCN-nél `/vcns/{vcnId}` — egy helyőrző, és az az id, így
a „mindenhova az id" helyes. Az `objectstorage.Bucket`-nél viszont:

```
$ oci-extract $SDK/objectstorage/objectstorage_client.go
  CreateBucket POST   /n/{namespaceName}/b
  GetBucket    GET    /n/{namespaceName}/b/{bucketName}
  UpdateBucket POST   /n/{namespaceName}/b/{bucketName}
  DeleteBucket DELETE /n/{namespaceName}/b/{bucketName}
```

Két helyőrző, **egyik sem id** — és még a *létrehozás* is igényli a
`{namespaceName}`-t a kollekciós úton. A request-modell megmutatja, hogy mindkettő
kötelező, de ez sehol nem került be a kibocsátott sémába:

```
$ oci-extract $SDK/objectstorage/get_bucket_request_response.go
   NamespaceName  *string  to=path  httpName=namespaceName  mand=True
   BucketName     *string  to=path  httpName=bucketName     mand=True
```

Ez nem szélsőség. Az SDK összes `Get*` műveletére mérve:

```
Get* operations by number of {path params}:
  0 params:    50
  1 params:  1108
  2 params:   265
  3 params:    48
  4 params:     9
  5 params:     1
services with at least one Get having >1 path param: 65 of 158
```

**1481 Get műveletből 323-nak (21,8%) nem egy path-paramétere van**, és ez 158
szolgáltatásból 65-öt érint. A VCN/Subnet a 74,8%-os többségbe esik — ezért nem
derült ki soha.

**Hogyan oldottam fel.** `Operation.PathParams` a path-sablonból, és minden
kibocsátott művelet mellé `path_params` a bundle-ben. Ezzel a címzési szerződés
**kimondott** lesz, nem következtetett.

```
$ oci-extract -schema Bucket -ns cic:objectstorage:bucket …
 "GetBucket":    {method GET,    path /n/{namespaceName}/b/{bucketName},
                  path_params [namespaceName bucketName]},
 "CreateBucket": {method POST,   path /n/{namespaceName}/b,
                  path_params [namespaceName]},
 "UpdateBucket": {method POST,   …}      ← POST, mert ezen az úton nincs PUT
```

**Nyitva hagyott rész (szándékosan, a következő jobnak):** a `templatePath`
(`module/provider.go:1059`) továbbra is minden `{…}`-ba a resource id-t írja. Az
extractor most már **kiadja** a kötendő paraméterek listáját; a modul futásidejű
kötése (honnan jön a `namespaceName` érték — bindingből, config mezőből?) *nem*
extractor-kérdés, hanem beágyazási/kapu-döntés, amit a job kifejezetten a
`oci-extract-full-sweep`-hez sorolt. Lásd `sweep-input.md`.

---

## A4 — Minden modell struct

**Hol tört el:** `tools/oci-extract/extract.go:67`

```go
st, ok := ts.Type.(*ast.StructType)
if !ok {
    continue          // interface → némán eldobva
}
```

**Az eltörő kimenet.** Az OCI **1014 modellt deklarál interface-ként**, ebből
470-et `*Details`/`*Base` néven — ezek polimorf típusok, a konkrét alakot egy
diszkriminátor választja ki:

```
$ find $SDK -maxdepth 2 -name "*.go" | xargs grep -hoE "^type [A-Za-z0-9]+ interface" | sort -u | wc -l
1014
$ … | grep -E "(Details|Base) interface" | wc -l
470
```

Nyolc erőforrásnak maga a `Create<R>Details`-e interface (pl.
`database.CreateBackupDestinationDetails`, `dns.CreateZoneBaseDetails`). A régi
kód számára ezek **nem léteztek**, tehát ugyanaz a néma üres create-felület állt
elő, mint az A2-nél — csak most `exit 0`-val és hibaüzenet nélkül:

```
$ /tmp/oci-extract-new -schema BackupDestination …   # a régi viselkedéssel
exit=0
(üres create felület, semmilyen jelzés)
```

**Hogyan oldottam fel.** Az `ExtractFile` most `Model{Kind: "interface"}`-ként
rögzíti őket, a `Resolution` pedig **nevesítve jelenti**, ha egy lifecycle-modell
polimorf. A konkrét implementációk kibontását **nem** végeztem el — az
diszkriminátor-szemantika, tehát modellezési döntés, ami a következő jobba való.

**Mérés utána:**

```
$ oci-extract -schema BackupDestination -ns cic:database:backupdestination …
unresolved: BackupDestination: create model CreateBackupDestinationDetails is
  polymorphic (interface); concrete implementations are not expanded
exit=5
```

---

## A5 — A néma kihagyás mint rendszerhiba

A fenti négyből három **ugyanazt** a hibamintát mutatta: az extractor kihagyta,
amit nem tudott feloldani, és a kimenet érvényesnek látszott. Ez nem négy külön
bug, hanem egy hiányzó tulajdonság: **a nevező sosem volt megszámolva.**

Ezért két kapu került be, és ez a job legfontosabb szerkezeti hozadéka:

- `oci-extract -audit <client.go>…` — a jelölteket a feloldottaktól **külön**
  számolja, és **exit 4**, ha bármi feloldatlan. `make oci.audit` futtatja az
  egész pinelt SDK-n.
- `-schema` / `-policy` — stderr-re jelenti a feloldatlan felületet és **exit 5**,
  így a `make oci.generate` nem tud olyan sémát commitolni, aminek a create
  felületét sosem vezette le.

---

## Amit megvizsgáltam, és NEM bizonyult service-specifikusnak

Fontos a negatív eredmény is, mert ez szűkíti a következő job kockázatát:

- **A publikus↔privát metódus párosítás** (`CreateVcn` ↔ `createVcn`) az SDK
  egészén tartott: 0 árva privát wire-metódus 319 fájlban.
- **A struct-tag szerződés** (`mandatory` / `json` / `contributesTo` / `presentIn`
  / `name`) minden vizsgált szolgáltatásban azonos alakú.
- **A kizárt exportált metódusok** mind valódi kliens-plumbing
  (`ConfigurationProvider` 316×, `SetRegion` 311×, `EnableDualStackEndpoints` 15×,
  `UnmarshalPolymorphicJSON` 7×) — egyetlen valódi művelet sem esett ki köztük a
  `ListRegions`-ön kívül, amit az A1 feloldott.
- **3 `*_client.go` fájl 0 művelettel** (`common/auth/federation_client.go`,
  `database_tools_connection_oracle_database_proxy_client.go`,
  `cloud_gate_oauth_client.go`) — ezek nem szolgáltatás-kliensek; indokolt
  kizárás, nem hiány.
