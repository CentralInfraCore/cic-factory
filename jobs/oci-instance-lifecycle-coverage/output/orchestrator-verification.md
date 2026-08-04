# Orchestrátori verifikáció — valós OCI ellen

Ez a szakasz az, amit **nem** ez a job futtatott (a hatókör tiltja — lásd
`input.md` "Kemény korlátok" 3. pont). A `Destroy`/`Invoke` harness létezik és
env-guardolt (lásd `claim-evidence.md`), de a tényleges hálózati futás az
orchestrátoré, a POC trial tenancy ellen.

Minden recept a repo gyökeréből futtatandó, a modul repo `devel`-re mergelt
állapotában (vagy erről a feature branch-ről, ha még nem mergelt):
`feature/oci-instance-lifecycle-coverage`.

## Előfeltétel — közös env

```bash
export OCI_KEY_PATH=~/.oci/oci_api_key.pem
export OCI_TENANCY_OCID=ocid1.tenancy.oc1...
export OCI_USER_OCID=ocid1.user.oc1...
export OCI_FINGERPRINT=xx:xx:xx:...
export OCI_REGION=eu-frankfurt-1          # a trial tenancy régiója
# EU Sovereign realm esetén: export OCI_REALM_DOMAIN=oraclecloud.eu
```

---

## A — `Destroy()` egy VCN-en (gyors, olcsó, meglévő mintát követ)

A legkisebb költségű, leggyorsabb igazolás — nem VM, csak egy VCN.

```bash
# 1. Hozz létre egy eldobható VCN-t Execute()-tal (a meglévő, már igazolt úton)
OCI_TEST_KIND=cic:network:vcn \
OCI_EXEC_OPERATION=CreateVcn OCI_EXEC_METHOD=POST OCI_EXEC_PATH=/vcns \
OCI_EXEC_CONFIG_JSON='{"compartmentId":"<compartment-ocid>","displayName":"destroy-harness-vcn","cidrBlock":"10.0.0.0/16"}' \
REAL_OCI_TEST=1 go test -tags manual_real_oci -count=1 -run TestManualRealOCIExecute -v ./module/
# jegyezd fel a kimenetből (vagy `oci network vcn list --compartment-id <compartment-ocid>
# --query "data[?\"display-name\"=='destroy-harness-vcn'].id | [0]" --raw-output`) a VCN OCID-t

# 2. Futtasd a VALÓDI Destroy() handlert ellene — ez az, amit ez a job célzott
OCI_TEST_KIND=cic:network:vcn OCI_TEST_RESOURCE_ID=<vcn-ocid> \
REAL_OCI_TEST=1 go test -tags manual_real_oci -count=1 -run TestManualRealOCIDestroy -v ./module/

# 3. Ellenőrizd:
#    - a teszt kimenete: "Destroy resolved operation label: DeleteVcn"
#    - http_status: 204
#    - oci network vcn get --vcn-id <vcn-ocid>   # várt: 404 vagy lifecycle_state TERMINATED
```

**Mit igazol:** a `resolveOp(kind, roleDelete, binding)` a beágyazott kontraktusból
a helyes törlési műveletet (`DeleteVcn`) oldja fel, és ez a címke landol a
`executionStep.Operation`-ben — ami élesben a ProofTrace-be kerül. Ez a
lényegi rés, amit a job zárt: eddig ez a kódút soha nem futott valós OCI ellen.

## B — `Destroy()` egy Instance-en (magasabb érték: az async/role-bridge eset)

Ez az eset, ami ténylegesen az `oci-lifecycle-role-bridge` hibaosztályát fedi:
`TerminateInstance` egy **más névalakú** delete-művelet, és aszinkron (Work
Request-et ad vissza). Nagyobb az előkészítési költség (subnet + image + shape
kell), de ez a legmagasabb bizonyító erejű futás.

```bash
# 1. Launch egy Always Free instance-t (VM.Standard.E2.1.Micro) egy meglévő
#    subnetben (vagy hozz létre egyet a fenti CreateVcn + CreateSubnet mintával)
oci compute instance launch \
  --availability-domain <AD> \
  --compartment-id <compartment-ocid> \
  --shape VM.Standard.E2.1.Micro \
  --subnet-id <subnet-ocid> \
  --image-id <régióhoz tartozó Oracle-Linux image OCID> \
  --display-name destroy-harness-instance \
  --wait-for-state RUNNING
# jegyezd fel az instance OCID-t

# 2. (Opcionális, de értékes) Poll a LaunchInstance Work Requestjén — ez már
#    2026-08-04-én igazolt módon működik (lásd manual-verification.md poll sora)

# 3. Futtasd a VALÓDI Destroy() handlert
OCI_TEST_KIND=cic:compute:instance OCI_TEST_RESOURCE_ID=<instance-ocid> \
REAL_OCI_TEST=1 go test -tags manual_real_oci -count=1 -run TestManualRealOCIDestroy -v ./module/

# 4. Ellenőrizd:
#    - a teszt kimenete: "Destroy resolved operation label: TerminateInstance"
#      (NEM "DeleteInstance" — ez pont az, amit a role-bridge fix javított)
#    - oci compute instance get --instance-id <instance-ocid>
#      --query 'data."lifecycle-state"'   # várt: TERMINATING majd TERMINATED
```

**Takarítás:** ha a 3. lépés valamiért elszáll, az instance kézzel törlendő:
`oci compute instance terminate --instance-id <instance-ocid> --force`.

---

## C — `Invoke()` — `ChangeInstanceCompartment`

Ehhez **második compartment kell** — a trial tenancy ma üres a root
compartmenten kívül (lásd `invoke-scope.md`).

```bash
# 1. Hozz létre egy második, eldobható compartmentet
oci iam compartment create \
  --compartment-id <tenancy-ocid> \
  --name invoke-harness-compartment \
  --description "scratch compartment for TestManualRealOCIInvoke"
# várd meg ACTIVE állapotot (oci iam compartment get --compartment-id <new-id>),
# jegyezd fel az OCID-t

# 2. Legyen egy élő instance (a fenti B/1. lépésből újrahasználható, vagy
#    launch-olj egy külön eldobhatót erre a célra)

# 3. Futtasd a VALÓDI Invoke() handlert
OCI_TEST_KIND=cic:compute:instance OCI_TEST_RESOURCE_ID=<instance-ocid> \
OCI_INVOKE_OPERATION=ChangeInstanceCompartment \
OCI_INVOKE_CONFIG_JSON='{"compartmentId":"<invoke-harness-compartment-ocid>"}' \
REAL_OCI_TEST=1 go test -tags manual_real_oci -count=1 -run TestManualRealOCIInvoke -v ./module/

# 4. Ellenőrizd:
oci compute instance get --instance-id <instance-ocid> \
  --query 'data."compartment-id"' --raw-output
# várt: az új compartment OCID-ja

# 5. Takarítás: terminate az instance-t (most már az új compartmentben),
#    majd töröld a scratch compartmentet:
oci compute instance terminate --instance-id <instance-ocid> --force
oci iam compartment delete --compartment-id <invoke-harness-compartment-ocid> --force
```

---

## Mit jelent a "kész" ehhez a három recepthez

Mindhárom recept sikeres lefutása után frissítendő
`docs/design/manual-verification.md` coverage táblája (`destroy`/`invoke`
sorok `verified`-re, a mért `operation` címkével és `http_status`-szal mint
bizonyíték) — ezt a modul repóban, nem a cic-factory output-ban kell tenni,
mert az a modul repo dokumentációja.

**Ne fuss neki A/B/C-nek üres/ismeretlen compartment-tel** — mindig a POC
trial tenancy scratch compartmentjében, sosem a paynance production
tenancyben (lásd `manual-verification.md` "What it does NOT cover" szakasza).
