# Közös VCN-fixture (v1) — Intent → Observed → Conformance → Evidence

Egy kicsi, rögzített fixture, amin a négy fejlesztési szál (registry, OCI modul, primitive engine, Relay) **egymásra várás nélkül**
dolgozik. Minden szál a saját szakaszát valósítja meg, és a saját tesztjében az itt rögzített `expected/` fájlokkal veti össze.
A fixture-t egy referencia-generátor (`generate.py`) állítja elő; **a generátor nem implementáció, amit át kell venni**, hanem
az egyeztetett szemantika egy helyen. A fájlokat a `generate.py --check` ellenőrzi, a `MANIFEST.sha256` rögzíti.

```
intent ──► [GetVcn] ──► oci/response.json | oci/error.json
                          │ 3. OCI modul normalizálása (effective config + state + coverage, OCI-nevekkel)
                          ▼
                       expected/observed.oci.json
                          │ 4. a registry bindingja (OCI-nevek → registry-nevek, lifecycle leképezés)
                          ▼
                       expected/observed.registry.json  +  intent.registry.json
                          │ 5. primitive engine: conformance (plan.json szerint)
                          ▼
                       expected/verdict.fields.json
                          │ 6. Relay: bizonyíték, végrehajtás nélkül
                          ▼
                       expected/evidence.claims.json
```

| Szakasz | Tulajdonos | Mit kell tudnia | Mivel veti össze |
|---|---|---|---|
| 3 | `cic-module-oracle-cloud` | nyers `GetVcn` válasz → `effective_config`, `state`, `coverage` | `expected/observed.oci.json` |
| 4 | `cic-schema-registry` | gépi binding OCI↔registry mezőnevek, `lifecycle-map.json` | `expected/observed.registry.json` |
| 5 | `cic-primitive-engine` | `MaterializedObject`-ek + `Observation` + `ConformancePlan` → verdikt | `expected/verdict.fields.json` |
| 6 | `CIC-Relay` | a szakaszok láncolása és a bizonyíték, unknown/absent explicit | `expected/evidence.claims.json` |

## A coverage szabályai (a szakasz 3 és 4 szerződése)

| Eset | Coverage |
|---|---|
| a mező a válaszban van és jó típusú | `observed` |
| a mező nincs a válaszban / null, és az OCI ezt „nincs beállítva"-ként jelenti (`dnsLabel`) | `absent` |
| a forrásmező hiányzik, ezért a származtatott érték nem állítható elő (`ipv6CidrBlocks` nélkül nincs `isIpv6Enabled`) | `unobserved` — **soha nem `false`** |
| a mező ott van, de nem hihető (`cidrBlocks` nem lista) | `unknown` |
| HTTP 404 `NotAuthorizedOrNotFound` | minden mező `unknown`: az OCI nem különbözteti meg a törölt és a nem engedélyezett erőforrást, a hiány **nem** authoritatív |
| nincs válasz (timeout) | minden mező `unobserved` |

A verdiktben az `unknown` és az `unobserved` egyaránt `UNOBSERVED`: **soha nem `CONFORMANT`**.

## A verdikt szemantikája (a primitive engine `origin/main` szerint)

`observed`: egyezik → `CONFORMANT`, nem → `DRIFT`, eltérő típus → `NOT_COMPARABLE`. `absent` és a szándékban van érték →
`DRIFT`; `absent` és a szándékban nincs → `OBSERVED_ABSENT`. `unobserved`/`unknown` → `UNOBSERVED`. Az objektum: `DRIFT`, ha
bármely mező `DRIFT` vagy `NOT_COMPARABLE`; különben `INCOMPLETE`, ha bármely `UNOBSERVED`; különben `CONFORMANT`.

A `plan.json` mezői: `/cidr_block`, `/dns_label`, `/ipv6_enabled` és a `/tags/{key=…}/value`. **Nincs a tervben** (a verdikt
nem mond róluk semmit): `secondary_cidr_blocks`, `display_name`, `compartment_id`, `lifecycle_state`, `ipv6_cidr_blocks`
(`not-planned.json`).

## A nyitott kérdés (`desired-absent-observed-present`)

Az OCI modul szerint a szándékban hiányzó mező „nem kezelt, nem nyúlunk hozzá". A primitive engine viszont egy **tervben szereplő,
de a szándékban nem deklarált** útvonalon, ha van megfigyelt érték, `NOT_COMPARABLE`-t ad (az objektum `DRIFT`). A fixture az
engine tényleges viselkedését rögzíti. A kérdés, amit a Relay-szál és az engine-szál jelent: a tervet a szándékból kell
származtatni (a nem deklarált útvonal nincs a tervben), vagy az engine-nek kell megkülönböztetnie a nem kezelt mezőt? A
fixture-t nem szabad úgy „javítani", hogy a kérdés eltűnjön.

## Mit tegyen a szál

* Másolja a fixture-t a saját repójába (vendored, a `MANIFEST.sha256`-tal és a forrás commit megjelölésével); a teszt ellenőrizze a
  manifestet. Ne írja át az `expected/` fájlokat, hogy a saját kimenetéhez igazítsa. Ha szerinte hibás, jelezze.
* Csak a saját szakaszát implementálja; a többiét az `expected/` fájlokból veszi.
* Ami hiányzik a fixture-ből, azt jelezze, ne találja ki.

## Karbantartás

`python3 fixtures/vcn-v1/generate.py` újragenerál, `--check` ellenőriz. A szemantika változása új fixture-verziót (`vcn-v2`)
jelent, nem a v1 átírását.
