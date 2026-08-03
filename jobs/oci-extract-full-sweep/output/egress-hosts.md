# Egress-hoszt leltár (Task F)

## A nyitott lelet, amiből ez a rész indul

`Describe()`'s `required_capabilities.egress_hosts` ma `["*.oraclecloud.com"]`
— egyetlen, kódba égetett realm. A `manual-verification.md` már jelezte: az
EU Sovereign realm (`oc19`) valós hosztja `oraclecloud.eu`, nem
`oraclecloud.com`. Ez a leltár azt méri fel, **mekkora** ez a probléma a
teljes SDK-n, és mit kell a capability-manifestnek kifejeznie.

**Forrás, nem grep-következtetés** (a modul CLAUDE.md szabálya szerint): a
realm-listát az OCI SDK `common/regions.go`-jából olvastam ki, a relay-oldali
glob-illesztés viselkedését a `CIC-Relay/cmd/relay/cic_flow_manifest_test.go`
tényleges teszteseteiből, nem feltételezésből.

## 1 — Hány realm van, és milyen domain-szuffixet visel

```
$ grep -n -A 20 "var realm = map" common/regions.go
oc1:  oraclecloud.com        oc9:  oraclecloud9.com
oc2:  oraclegovcloud.com     oc10: oraclecloud10.com
oc3:  oraclegovcloud.com     oc14: oraclecloud14.com
oc4:  oraclegovcloud.uk      oc15: oraclecloud15.com
oc8:  oraclecloud8.com       oc19: oraclecloud.eu
oc20: oraclecloud20.com      oc29: oraclecloud29.com
oc21: oraclecloud21.com      oc35: oraclecloud35.com
oc23: oraclecloud23.com      oc42: oraclecloud42.com
oc24: oraclecloud24.com      oc51: oraclecloud51.com
oc26: oraclecloud26.com      oc52: oraclecloud52.com
```

**21 realm, 21 különböző top-level domain.** Négy nem a `oraclecloudN.com`
mintát követi: `oc2`/`oc3` → `oraclegovcloud.com` (US Gov), `oc4` →
`oraclegovcloud.uk` (UK Gov), `oc19` → `oraclecloud.eu` (EU Sovereign, a
`manual-verification.md`-ben már dokumentált eset).

## 2 — Hogyan épül fel egy szolgáltatás hosztja

168 szolgáltatásból 162 a szabványos mintát követi:

```go
client.Host, _ = common.StringToRegion(region).EndpointForTemplateDottedRegion(
    "iaas", "https://iaas.{region}.{dualStack?ds.oci.:}{secondLevelDomain}", "iaas")
```

— a `{secondLevelDomain}` a fenti realm-táblából oldódik fel futásidőben, a
prefix (`iaas`, `database`, `objectstorage`, …) szolgáltatásonként fix.

## 3 — Amit a relay glob-motorja ma tud (forrásból, nem becslésből)

`CIC-Relay/cmd/relay/cic_flow_manifest_test.go`, `TestHostGlobMatch`:

```go
{"*.oraclecloud.com", "iaas.eu-frankfurt-1.oraclecloud.com", true},
{"*.oraclecloud.com", "oraclecloud.com", false},       // apex, not a subdomain
{"*.oraclecloud.com", "evil-oraclecloud.com", false},  // no dot boundary
{"*", "anything.com", false},                          // bare * rejected
{"a.*.com", "a.b.com", false},                         // infix wildcard rejected
```

A minta: **egy vezető `*` címke + fix szuffix**, kis-nagybetű-független,
pont-határ kikényszerítve, infix/több wildcard **elutasítva**.

## 4 — Három eltérő hoszt-alak a teljes SDK-n

| Alak | Hány szolgáltatás | Kifejezhető-e ma, relay-változás nélkül? |
|---|---:|---|
| **A. Realm-templált** (`<prefix>.{region}.{secondLevelDomain}`) | 162 | **Igen** — egy `egress.host` bejegyzés realm-enként (21 bejegyzés a teljes realm-lefedettséghez), a meglévő vezető-wildcard mintával |
| **B. Realm-független, kódba égetett** (`csaap-e.oracle.com`, 4× `osub*` szolgáltatás) | 4 | **Igen** — egy exact-host bejegyzés, wildcard sem kell |
| **C. Nem realm-templált, dinamikus** (`objectstorage`, `identitydomains`) | 2 | **Részben** — lásd lent |

### A/B — nincs relay-igény, modul-oldali `Describe()` javítás

A ma egyetlen `*.oraclecloud.com`-ot visszaadó `Describe()` helyett **21
realm-bejegyzést** kellene kiadnia (egyet realmenként), plusz a 4 `osub*`
szolgáltatáshoz egy exact-host bejegyzést, ha a modul ezeket valaha eléri. Ez
egy jövőbeli modul-oldali job — **ezt a sweep nem implementálta**, csak a
mértéket és a szükséges alakot rögzíti.

### C — a két kivétel, forrásból

**`objectstorage`** (`objectstorage_client.go:100-111`,
`getEndpointTemplatePerRealm`): ha
`IsOciRealmSpecificServiceEndpointTemplateEnabled` be van kapcsolva **és** a
realm `oc1`, a hoszt:

```
{namespaceName}.objectstorage.{region}.oci.customer-oci.com
```

— más apex domain (`customer-oci.com`, nem `oraclecloud.com`!), és a
namespace **tenant-specifikus, futásidőben derül ki** (`GetNamespace`
hívással), nem build-time konstans. Egy `*.objectstorage.<region>.oci.
customer-oci.com` bejegyzés (régiónként egy) ma is kifejezhető a meglévő
vezető-wildcard mintával — csak akkor válna valódi relay-igénnyé, ha egy
modul *bármely* régiót egyetlen statikus bejegyzésből akarna lefedni (ehhez
kettős wildcard kellene, amit a `TestHostGlobMatch` `infix wildcard rejected`
esete kizár).

**`identitydomains`** (`identitydomains_client.go:29-64`,
`NewIdentityDomainsClientWithConfigurationProvider`): a hoszt **nem**
`common.StringToRegion`-ből származik — kötelező `endpoint string`
konstruktor-paraméter, `client.Host = endpoint` szó szerint. Az Identity
Domains (IDCS) végpontok domain-provisioning-kor kiosztott, egyedi URL-ek
(pl. `idcs-<guid>.identity.oraclecloud.com`), amik **sem régióból, sem
realmből nem származtathatók** — build-time ismeretlenek. Erre **semmilyen**
statikus manifest-bejegyzés nem elég, akármilyen glob-szintaxist adna hozzá a
relay.

## 5 — Relay-következmény

Az `identitydomains` eset valódi, jelzett relay-igény lett: **R5** a
`docs/design/relay-requirements.md`-ben (a modul-repóban, `feature/
oci-extract-full-sweep` ágon) — `needed`, de **hatóköre csak az
identitydomains-lefedettség**, a jelenlegi `core`/network PoC-ot nem
blokkolja. Az A/B/C-objectstorage esetek **nem** relay-igények, ahogy fent
indokolva.

## Mit kell a capability-manifestnek kifejeznie (összegzés)

1. **Realmenként külön `egress.host` bejegyzés**, nem egy hardcoded
   `*.oraclecloud.com` — 21 bejegyzés a teljes realm-lefedettséghez, vagy
   annyi, ahány realmet a modul ténylegesen támogatni akar.
2. **Nem minden szolgáltatás van egy domain alatt** — a 4 `osub*` szolgáltatás
   saját, realm-független exact-host bejegyzést igényel.
3. **A namespace/régió kombinációjú hosztok** (objectstorage) régiónkénti
   bejegyzést igényelnek, ha a modul több régiót támogat egy statikus
   manifestből.
4. **Egy futásidőben, tenant-konfigurációból feloldott hoszt**
   (identitydomains) elvi kérdést vet fel a manifest-modellben — ez az R5.
