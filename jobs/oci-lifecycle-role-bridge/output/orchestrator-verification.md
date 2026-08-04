# orchestrator-verification.md

Ez a lépéssor **nem futott le** — a job korlátai kifejezetten tiltották, hogy
valós OCI-erőforrást hozzak létre (turn-limit kockázat → magára hagyott futó
VM). Az alábbi parancsok pontosan reprodukálják azt, amit a job kontextusa a
2026-08-04-i valós tenancy-futtatásból leírt, és amit a fixture-teszt (D) csak
szintetikusan bizonyít.

## Fontos előfeltétel, amit menet közben találtam — nem triviális

A modul ma **csak `cic:network:vcn` és `cic:network:subnet` sémát ágyaz be**
(`module/contracts.go`'s `embeddedSchemas`). Az `Execute()` handler
(`module/provider.go`) az első lépésként `resourceContracts()[req.Kind]`-ot
követeli meg — ha `req.Kind` nem ismert, azonnal hibázik, **mielőtt** a
`renderBody`-hoz (és így a most javított `role`-alapú döntéshez) egyáltalán
eljutna.

Ez azt jelenti: a `LaunchInstance`/`TerminateInstance` elleni éles teszthez
**előbb be kell ágyazni egy `cic:compute:instance` sémát** — ugyanazzal a
pipeline-nal, amit ez a job a VCN/Subnet sémákhoz már használt (P2.3), csak a
compute csomagra mutatva. Ezt **nem én csináltam meg** (ez már egy új
resource-típus bevezetése, ami túlmutat a "lifecycle-szerep bridge" scope-ján),
de a pontos parancsot **lefuttattam dry-run módban** (stdout-ra, a
`module/schemas/`-ba **nem** írva), hogy a recept működését igazoljam a valós
SDK ellen, mielőtt átadom:

```bash
# 1. lépés — dry-run: igazolja, hogy a séma-pipeline a compute csomagra is
#    ugyanúgy működik, mint core/network-re. NEM ír a module/schemas/-ba.
docker compose exec -T builder sh -eu -o pipefail -c '\
  export GOPATH=/tmp/ocigp GOMODCACHE=/tmp/ocigp/pkg/mod GOFLAGS=-mod=mod; \
  cd /tmp && go mod download github.com/oracle/oci-go-sdk/v65@v65.121.0; \
  SDK=/tmp/ocigp/pkg/mod/github.com/oracle/oci-go-sdk/v65@v65.121.0/core; \
  cd /app/tools/oci-extract && \
  CLIENT="$SDK/core_compute_client.go"; \
  go run ./cmd/oci-extract -schema Instance -ns cic:compute:instance \
    "$SDK/launch_instance_details.go" "$SDK/update_instance_details.go" \
    "$SDK/instance.go" "$SDK/change_instance_compartment_details.go" "$CLIENT"'
```

Ezt **ténylegesen lefuttattam** (2026-08-04, ugyanebben a session-ben) — a
kimenet `operations` térképe pontosan a várt szerepeket adja:

```json
"LaunchInstance":    {"method": "POST",   "path": "/instances",                                   "role": "create"},
"GetInstance":       {"method": "GET",    "path": "/instances/{instanceId}",                      "role": "read"},
"UpdateInstance":    {"method": "PUT",    "path": "/instances/{instanceId}",                      "role": "update"},
"TerminateInstance": {"method": "DELETE", "path": "/instances/{instanceId}",                      "role": "delete"},
"ChangeInstanceCompartment": {"method": "POST", "path": "/instances/{instanceId}/actions/changeCompartment", "role": "action"}
```

Ha az orchestrátor a teljes éles Execute()-útvonalon (nem csak a
`contracts_test.go` fixture-jén) akarja igazolni a javítást, a fenti parancsot
kimenetét `module/schemas/core/instance.json`-ba kell irányítani, felvenni a
`//go:embed` sort és az `embeddedSchemas` listát `module/contracts.go`-ban,
majd a `oci-sdk.lock.yaml extracted_schema_hashes.core`-t újra-pinnelni — **ez
egy külön, kicsi job/lépés**, amit ide, mielőtt a valós tenancy-tesztet
elindítja, érdemes betolni.

**Alternatíva, ami NEM igényli az instance séma beágyazását**: a
`TestManualRealOCIExecute` a `providerOperation{Operation, Method, Path}`
hármast közvetlenül env-ből veszi, és `renderBody`-t **azon a kinden**
(`OCI_TEST_KIND`) futtatja, aminek a contract-ját `resourceContracts()[kind]`
megtalálja. Ha `OCI_TEST_KIND=cic:network:vcn`-t adsz meg, `c.operations`-ben
nem lesz `"LaunchInstance"` kulcs, tehát a `role` üres marad, és a fix **nem**
lesz élesben tesztelve — ez pont az a csapda, amibe egy felületes újrafuttatás
belefutna. **Az instance séma beágyazása nélkül a `LaunchInstance`-ág valós
OCI-n nem verifikálható korrekten** — ezt kifejezetten jelzem, mert könnyű
lenne úgy "futtatni a tesztet", hogy valójában nem a javított kódutat hajtja
végre.

## A recept (a job kontextusában megadott terv szerint, kiegészítve)

```bash
export OCI_KEY_PATH=~/.oci/oci_api_key.pem
export OCI_TENANCY_OCID=ocid1.tenancy.oc1..xxx
export OCI_USER_OCID=ocid1.user.oc1..xxx
export OCI_FINGERPRINT=xx:xx:xx:...
export OCI_REGION=eu-frankfurt-1
export REAL_OCI_TEST=1

cd module/  # vagy a repo gyökeréről: -C module

# 1) CreateVcn
OCI_TEST_KIND=cic:network:vcn \
OCI_EXEC_OPERATION=CreateVcn OCI_EXEC_METHOD=POST OCI_EXEC_PATH=/vcns \
OCI_EXEC_CONFIG_JSON='{"compartmentId":"ocid1.compartment...","displayName":"role-bridge-poc","cidrBlock":"10.0.0.0/16"}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .
# → jegyezd fel az új VCN OCID-t (oci network vcn list --query "...")

# 2) CreateSubnet (az 1. lépés VCN OCID-jével)
OCI_TEST_KIND=cic:network:subnet \
OCI_EXEC_OPERATION=CreateSubnet OCI_EXEC_METHOD=POST OCI_EXEC_PATH=/subnets \
OCI_EXEC_CONFIG_JSON='{"compartmentId":"ocid1.compartment...","vcnId":"<1. lépés VCN OCID>","displayName":"role-bridge-poc-subnet","cidrBlock":"10.0.1.0/24"}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .
# → jegyezd fel az új Subnet OCID-t

# 3) LaunchInstance — EZ a bug eredeti reprodukciója.
#    ELŐFELTÉTEL: cic:compute:instance séma beágyazva (lásd fent), különben
#    használd OCI_TEST_KIND=cic:network:subnet-t ÉS várd el, hogy a body ÜRES
#    legyen ({}), mert a "role" nem lesz megtalálva — ez NEM a fix hibája,
#    hanem a hiányzó compute-séma jele, ne keverd össze a kettőt.
OCI_TEST_KIND=cic:compute:instance \
OCI_EXEC_OPERATION=LaunchInstance OCI_EXEC_METHOD=POST OCI_EXEC_PATH=/instances \
OCI_EXEC_CONFIG_JSON='{"compartmentId":"ocid1.compartment...","availabilityDomain":"<AD-name>","shape":"VM.Standard.E2.1.Micro","displayName":"role-bridge-poc-vm"}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .
# Várt: http_status 200, work_request_id NEM üres (async — ellentétben a
# CreateVcn/CreateSubnet szinkron válaszával), a body a teljes settable
# mezőkészletet tartalmazza (nem {}).

# 4) Observe (igazolja, hogy az instance létrejött és a state olvasható)
OCI_TEST_KIND=cic:compute:instance OCI_TEST_RESOURCE_ID=<instance OCID a 3. lépésből> \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIObserve -v .

# 5) Poll — EZ a job Part C-je: a Work Request lekérdezése.
#    OCI_POLL_PATH a 3. lépés work_request_id-jából épül fel, TELJES API
#    verzió-prefixszel (Poll nem fűzi elé a base_path-ot, lásd
#    docs/design/manual-verification.md "Usage" szakasza).
OCI_POLL_PATH=/20160918/workRequests/<work_request_id a 3. lépésből> \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIPoll -v .
# Várt: work_status halad SUCCEEDED felé, terminal=true amikor kész.

# 6) TerminateInstance
OCI_TEST_KIND=cic:compute:instance \
OCI_EXEC_OPERATION=TerminateInstance OCI_EXEC_METHOD=DELETE OCI_EXEC_PATH=/instances/{instanceId} \
OCI_TEST_RESOURCE_ID=<instance OCID> \
OCI_EXEC_CONFIG_JSON='{}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .
# Várt: body nil (üres HTTP body a DELETE-en), work_request_id NEM üres.

# 7) DeleteSubnet
OCI_TEST_KIND=cic:network:subnet \
OCI_EXEC_OPERATION=DeleteSubnet OCI_EXEC_METHOD=DELETE OCI_EXEC_PATH=/subnets/{subnetId} \
OCI_TEST_RESOURCE_ID=<subnet OCID> OCI_EXEC_CONFIG_JSON='{}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .

# 8) DeleteVcn
OCI_TEST_KIND=cic:network:vcn \
OCI_EXEC_OPERATION=DeleteVcn OCI_EXEC_METHOD=DELETE OCI_EXEC_PATH=/vcns/{vcnId} \
OCI_TEST_RESOURCE_ID=<vcn OCID> OCI_EXEC_CONFIG_JSON='{}' \
go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v .
```

**Mindig `-count=1`** (lásd `docs/design/manual-verification.md` — a Go
teszt-cache hamis "sikert" mutathat egy korábbi, azonos-paraméterű futásból).

## Mit jelentene a siker, és mit a bukás

- **Siker:** a 3. lépés (`LaunchInstance`) `http_status: 200` (vagy `202`) és
  **nem üres body**-t küld — konkrétan, a `Execute` eredményben a request body
  (amit a `renderBody` állított elő) tartalmazza `compartmentId`,
  `availabilityDomain`, `shape`, `displayName` mezőket. A javítás előtt ez a
  body `{}` volt, és OCI `400 CannotParseRequest`-tel bukott — ez a pontos
  regresszió, amit ez a job javított.
- **Bukás, ami NEM a fixet cáfolja:** ha a 3. lépés `"no contract for kind
  cic:compute:instance"` hibát ad, az azt jelenti, hogy az előfeltétel
  (instance séma beágyazása) elmaradt — nem azt, hogy a `role`-alapú
  `renderBody` rossz.
- **Bukás, ami cáfolná a fixet:** ha a 3. lépés body-ja `{}` **annak ellenére**,
  hogy a `cic:compute:instance` séma be van ágyazva és tartalmazza a `role`
  mezőt az `operations` térképben.

## Takarítás

Ha bármelyik lépés közben megszakad a futás, a tenancy-ban élő erőforrás
maradhat. Takarítási sorrend (fordított): Instance → Subnet → Vcn — a
`oci compute instance list` / `oci network subnet list` / `oci network vcn
list --query "...displayName=~'role-bridge-poc'..."` paranccsal található meg
minden, amit ez a recept létrehozott (a `displayName` prefix `role-bridge-poc`
minden lépésben).
