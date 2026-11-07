# contract-mapping.md — séma-szerepek és a szerződés-leképezés lefedettsége

Reasoning mód: **audit**. Ez a dokumentum **nem valósít meg leképezést**, nem
vezet be új intent/state ágat, és nem ír kódot. A meglévő
`effective_config`/correspondence modellt veszi alapul
(`module/provider.go:878`, `module/correspondence.go:61`).

Rögzített commitok: modul `3e38886`, Forms `2f02a75`, `cic-primitives`
**pinelve** `73ae469`, `cic-schema-registry` **pinelve** `6db77d4`
(összehasonlításként `origin/main` = `ac567ae`), Relay `55a899f`.
Mérés: 2026-11-07.

**A nem implementált képesség itt szerződéses tény: sorként szerepel, nem marad
ki.** Ahol a leképezésnek nincs kódbeli helye, az a lelet — nem helyettesítem
mockkal vagy kézi adapterrel.

---

## C. Séma-elérhetőség és szerepek

### C.1 A szerepek táblája — melyik séma mi, és melyik NEM primitives-séma

A `forms-integration-direction.md:44-50` három szerepet nevez meg. A mérés
**négy** tényleges sémát talált, mert a registry oldalán a canonical és a
provider-specializált séma külön fájl.

| Szerep | Séma | Hol van (pinelt commit) | `$id` / identity | Primitives-séma? | Forms fordítja? | Státusz |
|---|---|---|---|---|---|---|
| **Intent (config) séma — canonical** | `NetworkSpace` | `cic-schema-registry@6db77d4`: `general/network/network-space/network-space.yaml` | `kind: NetworkSpace`, `namespace: cic:network`, `version: v0.1.dev`, `base: cic:core:ManagedEntity@v0.2.0` | **IGEN** — primitives-séma: minden node `atomic_ref: "cic:core:Shape@v0.2.0"`-ra hivatkozik, a surface-ök `aggregate_ref: cic:core:{ConfigSurface,StateSurface,OperationSurface}@v0.2.0`, `spec.kind: DomainComposition` | **IGEN, mérve** — lásd C.2 | a séma: **implemented** (létezik, fordul); a modul általi használata: **concept** |
| **Intent (config) séma — provider-specializált** | `NetworkSpaceOracleCloud` | `cic-schema-registry@6db77d4`: `providers/oracle-cloud/network/network-space/network-space.v0.1.0-src2026.yaml` (aláírt release) + `…/network-space.yaml` (working copy) | `kind: NetworkSpaceOracleCloud`, `version: v0.1.0`, `base: cic:network:NetworkSpace@v0.1.0` | **IGEN** — ugyanaz a primitív-hivatkozási szerkezet | **NEM MÉRVE** — a Forms `corpus/pins.yaml` ezt a fájlt **nem pineli** (csak a `general/` NetworkSpace-t és a NetworkInterface-t), így a Forms tesztkorpusza nem fordítja | **implemented** (létezik és aláírt), de a Forms szempontjából **nem pinelt** |
| **Provider-szerződés** | OCI VCN / Subnet / Instance | `cic-module-oracle-cloud@3e38886`: `module/schemas/core/{vcn,subnet,instance}.json` | `cic:network:vcn-config` / `-state`, `cic:network:subnet-config` / `-state`, `cic:compute:instance-config` / `-state` | **NEM.** Ez **OCI-ból származtatott JSON-séma**, a `tools/oci-extract` `go/ast`-elemzésének kimenete a pinelt OCI SDK forrásán (`oci-sdk.lock.yaml`, `OCI_SDK_VERSION ?= v65.121.0`). **Nincs benne egyetlen `atomic_ref`, `aggregate_ref`, `ManagedEntity` vagy `cic:core:…` hivatkozás sem.** A saját vokabuláriuma `x-cic-policy` / `x-cic-action` / `operations{method,path,role}` | nem alkalmazható (nem primitives-séma; a Forms csak primitives-grammar szerinti sémát fordít) | **implemented** (az extractor és a három szerződés, SDK-pinnel) |
| **Provider-oldali megfeleltetés (OCI→registry)** | `NetworkSpaceOracleCloudCorrespondence` | `cic-schema-registry@ac567ae` (= `origin/main`, **a pin UTÁN**): `providers/oracle-cloud/network/network-space/network-space.correspondence.yaml` | `spec.kind: ProviderCorrespondence`, `canonical: cic:network:NetworkSpaceOracleCloud@v0.1.0`, `provider_resources: [core.Vcn]` | **NEM** — a saját fejléce mondja ki: *„`kind: ProviderCorrespondence` nincs a grammar által ismert kind-ok között, semmi nem ellenőrzi ezt a fájlt a registry-ben"* (`:32-33`). Szándékosan `validatedBy` nélkül | nem; a Forms nem ismeri ezt a kind-ot | **implemented a pin UTÁN** (`ac567ae`), **nem létezik a pinelt `6db77d4`-en** |

**Kimondva, amit a spec kér:** `module/schemas/core/vcn.json` **nem
primitives-séma** — OCI-ból származó JSON-séma; a `NetworkSpace` és a
`NetworkSpaceOracleCloud` **primitives-séma**; a `…correspondence.yaml`
**nem séma**, dokumentációs konvenció + teszt-célú szabálykészlet.

### C.2 A NetworkSpace Forms-szel fordítható-e a pinelt commiton — MÉRVE

**Igen.** Nem a dokumentum állítása, hanem lefuttatott teszt.

Parancs (eldobható másolatokon, a repókon kívüli kimenettel):

```
docker run --rm -v /tmp/fo01a-scratch/forms-rw:/forms \
                -v /tmp/fo01a-scratch/registry-6db77d4:/registry:ro \
  cic-module-oracle-cloud-builder:latest \
  sh -c 'cd /forms/go && CIC_REGISTRY_ROOT=/registry GOFLAGS=-mod=mod \
         go test -count=1 -run TestRealRegistrySchemas -v .'
```

Kimenet (idézve):

```
--- PASS: TestRealRegistrySchemas (0.01s)
    --- PASS: TestRealRegistrySchemas/network-interface_config_surface_is_refused_with_every_defect_named (0.01s)
    --- PASS: TestRealRegistrySchemas/state_surface_is_not_validated_as_authoring (0.00s)
    --- PASS: TestRealRegistrySchemas/network-space_config_surface_compiles_and_validates_a_VCN_intent (0.00s)
    --- PASS: TestRealRegistrySchemas/another_byte_is_a_digest_mismatch,_not_a_schema (0.00s)
PASS
ok  	github.com/CentralInfraCore/cic-primitive-forms/go	0.018s
```

Bizonyíték-hely: `go/real_schema_test.go:122` (`TestRealRegistrySchemas`),
`:148-214` (a NetworkSpace alteszt), `:103-107` (`compileReal`), `:94-96`
(a pin-hash kényszerítése: `if forms.SHA256Hex(data) != s.SHA256 { t.Fatalf(...) }`).

Amit a fordítás **ad** (`testdata/p1/real-schemas.json`, `accepted` blokk):
`kind: NetworkSpace`, `namespace: cic:network`, `uses_item_choice: false`,
`unevaluated_contracts: ["$.cidr_block"]`, `declared_validated_by: "cic-primitives v0.2.0"`,
`base: "cic:core:ManagedEntity@v0.2.0"`, `policy_summary.declared: true`,
`default_access: open`, `default_modify: owner`,
`surface_rules: [state_surface, config_surface]`, `inherit_policy: inherit`.

**Három kikötés, amit ez a PASS nem mos el:**

1. **A teszt opt-in, nem a CI alapfutása.** `CIC_REGISTRY_ROOT` nélkül
   `t.Fatal`: „CIC_REGISTRY_ROOT must point at a checkout of
   CentralInfraCore/cic-schema-registry at the pinned commit"
   (`real_schema_test.go:69-71`, mérve: FAIL három altesztre).
2. **A `contract` nem értékelődik.** `unevaluated_contracts: ["$.cidr_block"]` —
   a `cidr_block` `^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$` patternjét a Forms
   **nem** érvényesíti (`docs/P1-SUPPORTED-SUBSET.md:352`). Egy `999.0.0.0/16`
   intent a Forms számára **érvényes**; a visszautasítás az OCI-tól jön (400
   `InvalidParameter`, `manual-verification.md:71`).
3. **`state_surface` elutasítva.** `state_refused: {pin: registry-network-interface,
   error: SURFACE_UNSUPPORTED}` — a kódbeli kényszer `go/schema.go:138-140`.

### C.3 Tartalmazza-e a NetworkSpace config-felülete mindazt, amit a modul VCN-szerződése megkövetel?

**Nem.** Két irányban is hiányos, és a hiány **mérve, nem következtetve**.

A NetworkSpace `config_surface` **7 node**-ja (`network-space.yaml:98-218`):
`cidr_block` (mandatory), `secondary_cidr_blocks`, `ipv6_enabled`,
`dns_support_enabled`, `dns_hostnames_enabled`, `dns_label`, `tags`.
A `state_surface` **3 node**-ja (`:227-270`): `lifecycle_state` (mandatory),
`ipv6_cidr_blocks`, `subnet_count`.
(Mérés: `yaml.safe_load` → `spec.config_surface.nodes` / `spec.state_surface.nodes`
hossza; a `NetworkSpaceOracleCloud@v0.1.0` **ugyanez a 7+3**.)

A modul VCN-szerződése: **13 config** + **19 state** mező, `required: ["compartmentId"]`.

#### Mező-szintű egyezés-tábla: a modul VCN config-szerződése ↔ NetworkSpace config_surface

| modul VCN config mező | `x-cic-policy` | NetworkSpace megfelelő | Egyezés | Megjegyzés |
|---|---|---|---|---|
| `cidrBlock` (string) | create-only | `cidr_block` (scalar string, **mandatory**) | **részleges** | A modul szerződésében **nem** kötelező; a NetworkSpace-ben kötelező. Az OCI-n elavult az egyes számú alak (a registry correspondence `:56`: „a `cidrBlock` (egyes szám) elavult") |
| `cidrBlocks` (array) | create-only | `cidr_block` + `secondary_cidr_blocks` | **1→2 szétválasztás** | A registry correspondence szerint `cidrBlocks[0]` → `cidr_block` (`rule: first`), `cidrBlocks[1:]` → `secondary_cidr_blocks` (`rule: rest`). **A modulban ez a szétválasztás nincs implementálva** |
| `dnsLabel` (string) | create-only | `dns_label` (scalar string, optional, `capability: dns_label`) | **egyezik** | |
| `displayName` (string) | mutable | **NINCS** | ❌ **hiány** | Az OCI egyetlen ember által olvasható neve. A registry correspondence `gaps[1]`-ként rögzíti; a Forms korpusza bizonyítja: `undeclared-fields-are-reported` eset → `UNKNOWN_FIELD` a `$.display_name`-re |
| `compartmentId` (string) | action-managed (`ChangeVcnCompartmentDetails`) | **NINCS** | ❌ **hiány, és ez a legsúlyosabb** | Az OCI-n **kötelező** a létrehozáskor (`vcn.json` `required: ["compartmentId"]`). A NetworkSpace nem tudja kifejezni. Bizonyíték: a Forms `undeclared-fields-are-reported` esete → `UNKNOWN_FIELD` a `$.compartment_id`-re. Registry correspondence `gaps[1]` |
| `freeformTags` (object) | mutable | `tags` (collection list, `item_fields: [key, value]`) | **alak-eltérés** | map → `[{key, value}]` kulcs szerint rendezve (`rule: map_to_list`). **A modulban nem implementált** |
| `definedTags` (object) | mutable | **NINCS** | ❌ **hiány** | névtér.kulcs szerkezetű címkék; a sémában csak a szabad címke. `unmapped_provider_fields` |
| `securityAttributes` (object) | mutable | **NINCS** | ❌ **hiány** | ZPR; `unmapped_provider_fields` |
| `isZprOnly` (boolean) | mutable | **NINCS** | ❌ **hiány** | ZPR; `unmapped_provider_fields` |
| `isIpv6Enabled` (boolean) | input-only | `ipv6_enabled` (scalar boolean, optional, `capability: ipv6`) | **egyezik, derivációval** | A modul `correspondence/vcn.json` már leírja: `isIpv6Enabled` ← `ipv6CidrBlocks`, `rule: bool-from-nonempty`. **Ez az egyetlen leképezés, amely a modulban ténylegesen implementált** |
| `isOracleGuaAllocationEnabled` (boolean) | input-only | **NINCS** | ❌ **hiány** | nincs sémamező, és a correspondence sem nevezi meg |
| `byoipv6CidrDetails` (array) | input-only | **NINCS** | ❌ **hiány** | BYOIP IPv6; `unmapped_provider_fields` (a state-oldali `byoipv6CidrBlocks` néven) |
| `ipv6PrivateCidrBlocks` (array) | create-only | **NINCS** | ❌ **hiány** | nincs sémamező, a correspondence sem nevezi meg |
| — | — | `dns_support_enabled` (optional, `capability: dns_toggles`) | ❌ **fordított hiány** | AWS-VPC fogalom; **az OCI VCN-en nincs megfelelője**. A correspondence `kind: unsupported` (`:78-80`) |
| — | — | `dns_hostnames_enabled` (optional, `capability: dns_toggles`) | ❌ **fordított hiány** | ugyanaz (`:82-84`) |

**Számszerűen (nevező megadva).** A modul 13 VCN config mezőjéből a
NetworkSpace config_surface-e **4-et tud kifejezni** (`cidrBlock`/`cidrBlocks`
összevontan 1-nek számolva: `cidr_block`+`secondary_cidr_blocks`, `dnsLabel`,
`isIpv6Enabled`, `freeformTags`) és **9-et nem** (`displayName`,
`compartmentId`, `definedTags`, `securityAttributes`, `isZprOnly`,
`isOracleGuaAllocationEnabled`, `byoipv6CidrDetails`, `ipv6PrivateCidrBlocks`,
és a `cidrBlock`/`cidrBlocks` kettősség maga). Fordítva: a NetworkSpace 7
config mezőjéből **2-nek nincs OCI-megfelelője** (`dns_support_enabled`,
`dns_hostnames_enabled`). Mérési módszer: a fenti tábla soronkénti összevetése
a `jq -r '.config.properties | keys[]' module/schemas/core/vcn.json` és a
`network-space.yaml:98-218` node-nevei között; kizárás: nincs.

#### state_surface

| modul VCN state mező | NetworkSpace state_surface | Egyezés |
|---|---|---|
| `lifecycleState` (provider-computed, OCI nagybetűs) | `lifecycle_state` (mandatory, enum `[pending, available, deleting, deleted, unknown]`) | **részleges** — értékkészlet-eltérés: az OCI `UPDATING`-nek **nincs** enum-értéke. A registry correspondence `value_map`-je `UPDATING: unknown`, és `gaps[0]`-ként nevezi meg |
| `ipv6CidrBlocks` (provider-computed, array) | `ipv6_cidr_blocks` (set, `item_scalar_type: string`) | **egyezik** |
| — | `subnet_count` (integer, `role: operational`) | ❌ **nincs az OCI VCN-válaszban** — a correspondence `kind: composition`: egy **második** OCI-hívás (`ListSubnets` `vcnId` szűrővel) eredménye. „ebben a szeletben nincs megfigyelve" |
| `id` (OCID) | — | a `binding_surface.addresses[].key_fields[].id` kulcsa, **nem config/state mező** (correspondence `unmapped_provider_fields[0]`) |
| `defaultRouteTableId`, `defaultSecurityListId`, `defaultDhcpOptionsId`, `timeCreated`, `vcnDomainName`, `byoipv6CidrBlocks` (6 mező) | — | ❌ **nincs sémamező** egyikre sem |

---

## E. A szerződés-leképezés lefedettsége

### E.0 Hol van — és hol NINCS — a leképezés kódbeli helye

Ez a szakasz legfontosabb leletei. **Három hely jön szóba, és a válasz
mindháromra más.**

| Hely | Mit tartalmaz | Irány | Státusz | Bizonyíték |
|---|---|---|---|---|
| **`cic-module-oracle-cloud@3e38886`** | `module/correspondence.go` + `module/correspondence/vcn.json`: **egyetlen** derivációs szabály (`isIpv6Enabled` ← `ipv6CidrBlocks`, `bool-from-nonempty`) | OCI-válasz → OCI-nevű `effective_config` | **implemented**, de **nem a registry-nevekre**: a kimenet OCI-mezőneveket használ | `correspondence.go:61 applyDerivations`, production hívó `provider.go:861`; `correspondence/vcn.json:4-11`. A saját fejléce kimondja a hatókört: *„It does NOT cover name↔ID resolution (intent name → observed OCID), which needs a further provider lookup — that stays out until a resolve step exists"* (`:8-11`) |
| **`cic-schema-registry@6db77d4` (a PINELT állapot)** | — | — | **NEM LÉTEZIK** | `git ls-tree -r --name-only 6db77d4 \| grep -iE 'providers/oracle-cloud/network\|correspondence'` → csak `network-space.{v0.1.0-src2026,}.yaml`, `subnet.{…}.yaml` és a **storage** correspondence. **Nincs network-space correspondence** |
| **`cic-schema-registry@ac567ae` (= `origin/main`, 2026-10-21, a pin UTÁN)** | `providers/oracle-cloud/network/network-space/network-space.correspondence.yaml` (168 sor) + `tools/registrylib/correspondence.py` (loader/applier) + `tests/test_tools/test_registrylib/test_correspondence.py` | **OCI-nevű megfigyelt állapot → registry-nevű megfigyelt állapot** (a fixture 4. szakasza) | **implemented, teszttel** | `git show --stat ac567ae`; a fájl `spec.mappings` 10 bejegyzése; **saját mérés:** `PYTHONPATH=. pytest tests/test_tools/test_registrylib/test_correspondence.py -q` → **`37 passed in 2.38s`** |

**Válasz a kérdésre, egyértelműen.** A NetworkSpace → OCI VCN leképezésnek
**van kódbeli helye, de nem a modulban és nem a pinelt registry-commiton**:
`cic-schema-registry` `origin/main` (`ac567ae`), **és csak a visszafelé (OCI →
registry) irányra.** Az **előre irány (registry intent → OCI kérés) semmilyen
repóban nincs implementálva** — erre a `mappings` bejegyzései is csak
visszafelé olvashatók (`source: {side: effective_config|state, field: …}` →
`target: config_surface.*|state_surface.*`).

**Miért ott van, és nem a modulban.** A közös fixture négy szakaszra osztja a
munkát, és nevesített tulajdonost ad mindegyiknek
(`module/testdata/vcn-v1/README.md:24-29`):

| Szakasz | Tulajdonos | Mit kell tudnia | Mivel veti össze |
|---|---|---|---|
| 3 | `cic-module-oracle-cloud` | nyers `GetVcn` válasz → `effective_config`, `state`, `coverage` (**OCI-nevekkel**) | `expected/observed.oci.json` |
| **4** | **`cic-schema-registry`** | **gépi binding OCI↔registry mezőnevek, `lifecycle-map.json`** | `expected/observed.registry.json` |
| 5 | `cic-primitive-engine` | `MaterializedObject` + `Observation` + `ConformancePlan` → verdikt | `expected/verdict.fields.json` |
| 6 | `CIC-Relay` | a szakaszok láncolása és a bizonyíték | `expected/evidence.claims.json` |

A modul `SOURCE.md:4` ezt explicitté teszi: **„This module owns stage 3 only
(`expected/observed.oci.json`)."** Tehát a leképezés **szándékosan** nem a
modulban van — és ezt a baseline-nak nem „hiányként", hanem **felelősség-
elhelyezésként** kell jelentenie. A valódi hiány máshol van (E.3).

### E.1 VCN — mező-szintű lefedettségi tábla

Jelölések. **Irány:** `előre` = intent → OCI kérés; `vissza` = OCI válasz → CIC
state. **Coverage:** a `module/observed.go:36-41` négy értéke
(`observed|absent|unobserved|unknown`). A „hol implementált" oszlop azt mondja
meg, melyik repóban és milyen státusszal.

| intent mező (NetworkSpace) | provider mező (OCI VCN) | Irány | Policy (`x-cic-policy`) | hiányzó/`null`/default kezelése | OCID-azonosítás | Implementációs coverage | Megjegyzés |
|---|---|---|---|---|---|---|---|
| `cidr_block` | `cidrBlocks[0]` | vissza | create-only | nincs a válaszban → coverage `unknown` (**nem** `absent`: a `cidrBlocks` nincs az `unsetWhenOmitted`-ben, `observed.go:46-48`) | — | **`implemented` a registry-ben** (`ac567ae`, `rule: first`, 37 teszt PASS); **`concept` a modulban** (a modul `cidrBlocks`-ot ad, szétválasztás nélkül) | A Forms a `cidr_block` pattern-szerződését **nem értékeli** (`unevaluated_contracts`) |
| `cidr_block` | `cidrBlock` / `cidrBlocks[0]` | **előre** | create-only | — | — | **`concept`** — nincs kódbeli hely egyik repóban sem | Nyitott: az OCI `CreateVcn` melyiket kapja? A correspondence `:56` szerint az egyes számú elavult |
| `secondary_cidr_blocks` | `cidrBlocks[1:]` | vissza | create-only | — | — | **`implemented` a registry-ben** (`rule: rest`), **de a fixture v1 nem ellenőrzi** (`emit_in_fixture_v1: false`, `:63`); **`concept` a modulban** | A fixture `not-planned.json` kizárja a `/secondary_cidr_blocks`-ot a tervből |
| `secondary_cidr_blocks` | `AddVcnCidr` action (`POST /vcns/{vcnId}/actions/addCidr`) | **előre** | — | — | `{vcnId}` a path-ban | **`scaffold`** — az operáció **a szerződésben szerepel**, de **egyetlen config mező sem hivatkozik rá** `x-cic-action`-ként, így a `planProviderOps` (`provider.go:362`) sosem tervezi be | A registry `network-space.yaml:54-58` ezt „provider/modul gap"-ként írja le; a pontos helyzet: az action le van generálva, csak nincs mezőhöz kötve |
| `ipv6_enabled` | `isIpv6Enabled` ← `ipv6CidrBlocks` (`bool-from-nonempty`) | vissza | input-only | **a forrásmező hiánya → `unobserved`, SOHA nem `false`** (`observed.go:105-112`; teszt: `TestAPartialReadNeverFabricatesAValue`) | — | **`implemented` a modulban** (`correspondence/vcn.json`, `applyDerivations`); **`implemented` a registry-ben** (`kind: derived`) | **Ez az egyetlen mező, amely a teljes láncon implementált.** A NetworkSpace szándékosan nem ad neki `default`-ot (`:140-148`) |
| `ipv6_enabled` | `isIpv6Enabled` (create-time input) | **előre** | input-only | — | — | **`concept`** | Az OCI create-kor elfogadja, de nem adja vissza ugyanezen a néven |
| `dns_label` | `dnsLabel` | vissza | create-only | **a hiány/`null` authoritatív: coverage `absent`** — a `dnsLabel` az **egyetlen** mező az `unsetWhenOmitted`-ben (`observed.go:47`) | — | **`implemented` a registry-ben** (`kind: direct`); **`implemented` a modulban** `effectiveConfig`-on át (name-egyezés, deriváció nélkül) | |
| `dns_label` | `dnsLabel` (create-only) | **előre** | create-only | — | — | **`concept`** | |
| `tags` (`[{key,value}]`) | `freeformTags` (map) | vissza | mutable | a `freeformTags` coverage-e öröklődik elem-szinten (`/tags/{key=K}/value`) | — | **`implemented` a registry-ben** (`rule: map_to_list`, `coverage_elements.template`); **`concept` a modulban** (a modul a `freeformTags`-ot map-ként adja tovább) | A fixture `plan.json` tervez rá: `collections[0]` `path: /tags`, `keys: [key]`, `topology: map` |
| `tags` | `freeformTags` | **előre** | mutable | — | — | **`concept`** | |
| `dns_support_enabled` | **nincs OCI-megfelelő** | — | — | hiányzás = nincs róla intent (szándékosan **nincs** `default`, `network-space.yaml:164-173`) | — | **szerződéses tény: `unsupported`** — a correspondence `kind: unsupported` (`:78-80`), `unmapped_schema_fields[0]` | Nem hallgatólagos kihagyás |
| `dns_hostnames_enabled` | **nincs OCI-megfelelő** | — | — | ugyanaz | — | **szerződéses tény: `unsupported`** (`:82-84`, `unmapped_schema_fields[1]`) | |
| `lifecycle_state` (state) | `lifecycleState` | vissza | provider-computed | nincs néma default: ami nincs a táblában → `unknown` | — | **`implemented` a registry-ben** (`rule: value_map`); **`concept` a modulban** (a modul nyers OCI-értéket ad) | **Rés: az OCI `UPDATING`-nek nincs enum-értéke** → `unknown` → a verdiktben `UNOBSERVED`, nem `CONFORMANT` (`gaps[0]`) |
| `ipv6_cidr_blocks` (state) | `ipv6CidrBlocks` | vissza | provider-computed | — | — | **`implemented` a registry-ben** (`kind: direct`) | |
| `subnet_count` (state) | **nincs a `GetVcn`-ben** | vissza | — | — | `vcnId` szűrő a `ListSubnets`-hez | **`concept`** — a correspondence `kind: composition`: egy **második** OCI-hívás. A modulnak **nincs** `ListSubnets` operációja (a `vcn.json` `operations`-ában nincs list role), és az ABI „one resource_id at a time" (`manual-verification.md:206-207`) | Ez új ABI-képességet kíván, nem leképezést |
| **(nincs intent mező)** | `compartmentId` | — | action-managed | — | — | ❌ **szerződéses rés** — `gaps[1]`. Az OCI-n **kötelező**; a séma nem tudja kifejezni → **az intent nem fejezhető ki teljesen, és a create nem tervezhető meg a sémából** | A Forms korpusza bizonyítja: `UNKNOWN_FIELD` a `$.compartment_id`-re |
| **(nincs intent mező)** | `displayName` | — | mutable | — | — | ❌ **szerződéses rés** — `gaps[1]` | `UNKNOWN_FIELD` a `$.display_name`-re |
| **(nincs intent mező)** | `id` (OCID) | vissza | provider-computed | — | **ez AZ OCID** | `binding_surface.addresses[].key_fields.id` — **nem config/state mező** | A modul oldalán `binding.resource_id` (`provider.go:901 execBinding`), a path-templatelést a `templatePath` (`:1128`) végzi |
| **(nincs intent mező)** | `definedTags`, `securityAttributes`, `isZprOnly`, `byoipv6CidrBlocks`, `defaultRouteTableId`, `defaultSecurityListId`, `defaultDhcpOptionsId`, `timeCreated`, `vcnDomainName`, `isOracleGuaAllocationEnabled`, `ipv6PrivateCidrBlocks` (11 mező) | — | vegyes | — | — | ❌ **nincs sémamező** — a correspondence 11-ből 9-et explicit `unmapped_provider_fields`-ben nevez meg; `isOracleGuaAllocationEnabled` és `ipv6PrivateCidrBlocks` **sem a sémában, sem a correspondence-ben nincs megnevezve** → **ez a correspondence maga is hiányos** | Lelet: a correspondence a teljességet állítja (*„Semmi nincs »elfelejtve«: a teszt minden séma-config/state mezőt számon kér"*, `:26`) — de a **provider-oldali** teljességet csak a séma oldaláról kéri számon, a két OCI-mező kimaradt |

### E.2 Subnet és Instance — a leképezés állapota

| Resource | Szerződés | Correspondence (modul) | Correspondence (registry) | Registry canonical séma | Lefedettség |
|---|---|---|---|---|---|
| **Subnet** | `module/schemas/core/subnet.json`, **implemented** (16 config / 23 state, 5 operáció) | **NINCS** — `module/correspondence.go:23` `embeddedCorrespondences = [][]byte{vcnCorrespondence}`, **egyetlen elem** | **NINCS** — `git ls-tree ac567ae` szerint `providers/oracle-cloud/network/subnet/` tartalma csak `subnet.v0.1.0-src2026.yaml` + `subnet.yaml`, **correspondence nélkül** | `providers/oracle-cloud/network/subnet/…` létezik (a pinelt `6db77d4`-en is) | **`concept` a leképezésre.** A szerződés és a séma megvan, a megfeleltetés nem. **A `state-model.md` (KB `c7616`) két konkrét megfelelést már leír** — `route_table ↔ route_table_id` és `public_ip_allowed == !prohibit_public_ip_on_vnic` — ezek **dokumentáltak, nem implementáltak** (a `bool-invert` szabály létezik a modulban, `correspondence.go:70-71`, de nincs Subnet-bejegyzés, ami használná) |
| **Instance** | `module/schemas/core/instance.json`, **implemented** (35 config / 36 state, 5 operáció) | **NINCS** | **NINCS** — nincs `providers/oracle-cloud/compute/` könyvtár | **NINCS** canonical compute séma a `general/`-ben a pinelt commiton | **`concept` végig.** A legnagyobb rés: 35 config mező, 0 leképezés, és nincs hová leképezni (nincs canonical séma) |
| **Instance — aszinkron** | `TerminateInstance` → 204 + `opc-work-request-id`; `Poll` a Work Requestre | — | — | — | **`implemented` az ABI-ban** (`provider.go:735 Poll`, `:774 isTerminalWorkStatus`), valós OCI-n igazolva (`manual-verification.md:121,125,126`), de **a NetworkSpace-szerű canonical modellben nincs megfelelője**: a NetworkSpace `operation_surface` három szinkron operációt ismer (`provision`, `add_secondary_cidr`, `delete`), Work Request fogalma nincs |

**A `bool-invert` szabály leletként.** A `module/correspondence.go:70-71`
implementálja a `bool-invert` szabályt, és `module/correspondence/vcn.json`
**nem használja** (csak `bool-from-nonempty`-t). A szabály a `state-model.md`
Subnet-példájához készült (`public_ip_allowed == !prohibit_public_ip_on_vnic`).
Production hívója van (`applyDerivations` switch-ágán), de **egyetlen adat sem
aktiválja** → a `bool-invert` ág **scaffold** (feltételes elágazás mögött,
amit semmi nem ér el). A `rename` szabály (`:72-73`) ugyanígy.

### E.3 Coverage-rekordok — a nem implementált képességek listája

Ez a lista a `forms-integration-direction.md:104` szerinti coverage-rekord
(„A coverage record is written for every resource whose two-way mapping is
incomplete"). Mindegyik **szerződéses tény**, nem elfelejtett sor.

| ID | Képesség | Mi hiányzik | Hol kellene lennie | Státusz | Bizonyíték |
|---|---|---|---|---|---|
| **CM-1** | **előre irány bárhol** (intent → OCI kérés) | **teljesen** — nincs kódbeli hely egyetlen repóban sem | eldöntendő: a modulban (`renderBody` elé) vagy a registryben (új `mappings` irány) | **concept** | `network-space.correspondence.yaml` minden `mappings` bejegyzése `source: {side: effective_config\|state}` → `target: config_surface.*` — csak vissza. `module/renderBody` (`provider.go:1092`) a **már OCI-nevű** configot rendereli |
| **CM-2** | `compartmentId` az intentben | nincs sémamező | `cic-schema-registry`, új NetworkSpace(OracleCloud) verzió | **concept** | correspondence `gaps[1]`; Forms korpusz `undeclared-fields-are-reported` → `UNKNOWN_FIELD $.compartment_id` |
| **CM-3** | `displayName` az intentben | nincs sémamező | ugyanaz | **concept** | ugyanaz |
| **CM-4** | OCI `UPDATING` lifecycle | nincs enum-érték | `cic-schema-registry`, új sémaverzió (`v0.1.1` `updating`-gel) | **concept** | correspondence `gaps[0]`; a séma enumja `[pending, available, deleting, deleted, unknown]` |
| **CM-5** | `coverage` az `Observe` ABI-kimenetében | `normalizeObserved` **nincs bekötve** | `cic-module-oracle-cloud`, `module/provider.go:827 Observe` | **scaffold** | `observed.go:23-26` („NOT wired into Observe"); 0 production hívó |
| **CM-6** | Subnet correspondence | nincs | modul és/vagy registry | **concept** | `correspondence.go:23` egyetlen elem; `ac567ae`-n nincs subnet correspondence |
| **CM-7** | Instance correspondence **és** canonical compute séma | mindkettő | registry (`general/compute/…`) + correspondence | **concept** | nincs `general/compute` a pinelt commiton |
| **CM-8** | `secondary_cidr_blocks` írása (`AddVcnCidr`) | az action nincs mezőhöz kötve | modul: `x-cic-action` a generált sémában, vagy kézi correspondence | **scaffold** | `vcn.json` `operations.AddVcnCidr` létezik; egyetlen `x-cic-policy: action-managed` mező sem hivatkozik rá |
| **CM-9** | `subnet_count` | második OCI-hívás (`ListSubnets`), amire az ABI nincs felkészítve | modul ABI + registry correspondence | **concept** | correspondence `kind: composition`; „The harness has no »list« capability of its own (the module ABI operates on one resource_id at a time)" (`manual-verification.md:206-207`) |
| **CM-10** | név↔OCID feloldás (intent név → megfigyelt OCID) | nincs `resolve` lépés | modul (`correspondence.go` fejléce jelöli) | **concept** | `correspondence.go:8-11`: „It does NOT cover name↔ID resolution … that stays out until a resolve step exists" |
| **CM-11** | `definedTags`, `securityAttributes`, `isZprOnly`, `byoipv6CidrDetails`/`byoipv6CidrBlocks`, `ipv6PrivateCidrBlocks`, `isOracleGuaAllocationEnabled` (6 VCN mező) | nincs sémamező | registry | **concept** | correspondence `unmapped_provider_fields` (4 közülük), illetve **sehol nem megnevezve** (`ipv6PrivateCidrBlocks`, `isOracleGuaAllocationEnabled`) |
| **CM-12** | `dns_support_enabled`, `dns_hostnames_enabled` | **az OCI-n nincs megfelelő** — ez nem javítható rés, hanem kimondandó korlát | — | **szerződéses `unsupported`** | correspondence `:78-84`, `unmapped_schema_fields` |
| **CM-13** | `cidr_block` pattern érvényesítése | a Forms a `contract`-ot **nem értékeli** | eldöntendő: Forms (P-fázis) vagy modul `Validate` | **concept** | `unevaluated_contracts: ["$.cidr_block"]`; `docs/P1-SUPPORTED-SUBSET.md:352` |
| **CM-14** | a fixture nyitott kérdése (`desired-absent-observed-present`) | szemantikai eldöntetlenség a modul és a primitive engine között | a fixture README szerint a Relay- és engine-szálak jelentették | **nyitott kérdés, szándékosan** | `module/testdata/vcn-v1/README.md:54-60`: *„A fixture-t nem szabad úgy »javítani«, hogy a kérdés eltűnjön"* |

### E.4 A fixture mint a leképezés egyetlen igazolt kötése

A `module/testdata/vcn-v1/` a jelenlegi **legerősebb** bizonyíték arra, hogy a
két oldal összeér — és egyben megmutatja, mi nincs benne.

Mért adatok (`3e38886`, `go test -run TestNormalizeObservedMatchesTheFixture` → **9/9 PASS**):

| Eset | Mit rögzít |
|---|---|
| `conformant` | `effective_config{cidrBlocks:["10.0.0.0/16"], dnsLabel:"prod", freeformTags:{env,owner}, isIpv6Enabled:false}`, `state{id, ipv6CidrBlocks:[], lifecycleState:"AVAILABLE"}`, `coverage` 4 mezőre mind `observed` |
| `desired-absent`, `desired-absent-observed-present`, `drift`, `field-absent` | intent/observed eltérések |
| `malformed-cidr` | rossz típusú `cidrBlocks` → `unknown` |
| `not-found` | HTTP 404 → **minden mező `unknown`**, mert az OCI nem különbözteti meg a töröltet a nem engedélyezettől |
| `partial-read` | derivációs forrás hiánya → `unobserved`, nem `false` |
| `transport-error` | nincs válasz → **minden mező `unobserved`** |

A megfelelő `intent.registry.json` (conformant eset) **registry-nevű**:
`{cidr_block, dns_label, ipv6_enabled, tags:[{key,value}×2]}` — azaz a fixture
**mindkét oldalt tartalmazza**, és a 4. szakasz (a registry correspondence) a
kettőt összekapcsolja.

**A fixture terve (`plan.json`) szűk, és ezt kimondja.**
Tervben: `/cidr_block`, `/dns_label`, `/ipv6_enabled` (`compare: exact`) és
`/tags` (`topology: map`, `keys: [key]`, elem `value` `exact`).
**Nincs a tervben** (`not-planned.json`): `/secondary_cidr_blocks`,
`/display_name`, `/compartment_id`, `/lifecycle_state`, `/ipv6_cidr_blocks` —
tehát a verdikt **ezekről semmit nem mond**. A `/compartment_id` és a
`/display_name` azért nincs, mert nincs is sémamezőjük (CM-2, CM-3).

**Amit a fixture NEM fed:** egyetlen esetet sem tartalmaz az **előre irányra**
(intent → OCI kérés). Nincs `expected/request.oci.json`. Ez a legkisebb,
legkonkrétabb hiány, amit az `01b` be tud tölteni.

---

## Mit NEM állítok ebben a dokumentumban

Hogy a modul bármilyen registry-nevű intentet fogad vagy ad (OCI-neveket
használ). Hogy a Forms validálja a `state_surface`-t vagy a `contract`-okat.
Hogy a NetworkSpace elegendő egy OCI VCN létrehozásához (a `compartmentId`
nélkül nem). Hogy a `normalizeObserved` coverage-e megjelenik az ABI-kimenetben.
Hogy az előre irány bárhol létezik. Hogy a registry correspondence-e teljes a
provider-oldalon (két OCI-mezőt nem nevez meg). Bármilyen százalékot a
leképezés „készültségére" — a lefedettség itt rekordonként felsorolt, nem
összesített, mert a nevezője (az összes mező-irány-pár) nincs rögzítve egyik
szerződésben sem.
