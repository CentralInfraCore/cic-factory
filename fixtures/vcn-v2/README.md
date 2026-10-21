# Közös VCN-fixture (v2) — hatókör-tudatos

A v1 (`fixtures/vcn-v1`, cic-factory #37, `e5978f50…`) **változatlan marad**: az első négy worker által igazolt állapot
reprodukálható referenciája. A v2 a 2026-10-21-i tulajdonosi döntéseket kódolja, a v1 fölé építve. Ugyanaz a lánc:
szándék → OCI-válasz → megfigyelt állapot → konformitás → bizonyíték, ugyanazokkal a szakasz-tulajdonosokkal; az `expected/` fájlokat
a `generate.py` állítja elő (`--check` ellenőriz), a `MANIFEST.sha256` rögzíti. **A generátor nem implementáció, amit át kell venni.**

## Mi változott a v1-hez képest, és miért

| # | Döntés | v1 | v2 |
|---|---|---|---|
| 1 | A nem deklarált mező alapértelmezésben **nem kezelt**: az OCI-n létező értéke önmagában nem drift | a globális `plan.json` minden mezőt tartalmazott, ezért a nem deklarált mező megfigyelt értéke `NOT_COMPARABLE` lett (a `desired-absent-observed-present` nyitott kérdés) | a **terv esetenként a szándékból** származik (`expected/plan.json`); a nem deklarált mező nincs a tervben, ezért nincs verdikt-bejegyzése |
| 2 | Megfigyelt állapot, konformitási hatókör és bizonyíték külön | a három összemosódott | `observed.registry.json` **mindent** tartalmaz, amit láttunk; `scope.json` megmondja a kezelt és a nem kezelt, de látott útvonalakat; a bizonyíték `conformance_scope: "declared"` |
| 3 | Tag: csak a szándékban kezelt kulcsokat hasonlítjuk össze, kivéve ha kifejezett teljes tagkészlet-felügyelet van | a terv minden megfigyelt tag-kulcsot elemként kezelt | az intent `management.tags_scope`: `declared-keys` (alapértelmezett) vagy `full-set` |
| 4 | Üres `cidrBlocks: []` sikeres válaszban nem megbízható | `observed` | coverage `unknown`, a nyers `[]` az `observed_raw`-ban megmarad |

Új vagy módosult szerkezet: az `intent.registry.json` mostantól `{"config": …, "management": {"tags_scope": …}}`; új
`expected/plan.json`, `expected/scope.json`, `expected/engine-input.json`; a `not-planned.json` helyett `not-plannable.json`;
a globális `plan.json` megszűnt. A `verdict.fields.json` és az `evidence.claims.json` formája megmaradt, utóbbi bővült.

## A szakaszok

| Szakasz | Tulajdonos | Mit állít elő | Kimenet |
|---|---|---|---|
| 3 | `cic-module-oracle-cloud` | `effective_config`, `state`, `coverage`, `observed_raw` OCI-nevekkel | `observed.oci.json` |
| 4 | `cic-schema-registry` | ugyanez registry-nevekkel, **mindent** látott út listázva | `observed.registry.json` |
| 4b | a környezet (Relay-szál) | a terv és a hatókör a szándékból | `plan.json`, `scope.json` |
| 4c | a környezet | amit az engine kap: a megfigyelt lista **a kezelt tag-kulcsokra vetítve** | `engine-input.json` |
| 5 | `cic-primitive-engine` | verdikt | `verdict.fields.json` |
| 6 | `CIC-Relay` | bizonyíték | `evidence.claims.json` |

### Miért kell a 4c vetítés

Az engine kollekció-elemei az intent és az observed lista elem-azonosítóinak **uniói** (`plan.rs` `element_keys`), és a kollekció-terv
nem tud kulcsot szűrni. A „csak a deklarált tag-kulcsok" ezért **nem mondható ki a tervben**: a környezetnek kell a megfigyelt
listát a kezelt kulcsokra vetíteni, mielőtt az engine látja. A teljes lista az `observed.registry.json`-ban és a bizonyítékban megmarad.

## Esetek (13)

| Eset | Mit bizonyít | Objektum |
|---|---|---|
| `conformant` | minden deklarált egyezik | CONFORMANT |
| `drift` | dns label és egy tag értéke eltér | DRIFT |
| `field-absent` | kért dns label, az OCI nem jelent (nincs beállítva) | DRIFT |
| `desired-absent` | a dns label nem deklarált, az OCI-n sincs: nincs a tervben | CONFORMANT |
| `desired-absent-observed-present` | **a döntés esete**: nem deklarált, az OCI-n van: nincs verdikt-bejegyzés, a `scope.json` kezeletlenként listázza | CONFORMANT |
| `partial-read` | `ipv6CidrBlocks` nélkül az `ipv6_enabled` `unobserved`, nem `false` | INCOMPLETE |
| `malformed-cidr` | `cidrBlocks` nem lista: `unknown` | INCOMPLETE |
| `empty-cidr-blocks` | üres lista sikeres válaszban: `unknown`, nyers `[]` megőrizve | INCOMPLETE |
| `not-found` | 404 `NotAuthorizedOrNotFound`: minden `unknown` (a hiány nem authoritatív) | INCOMPLETE |
| `transport-error` | nincs válasz: minden `unobserved` | INCOMPLETE |
| `extra-tag-undeclared` | extra OCI-tag, `declared-keys`: látott, kezeletlen, nem összehasonlított | CONFORMANT |
| `extra-tag-full-set` | ugyanaz `full-set` felügyelettel: a tag a hatókörben van | DRIFT |
| `declared-tag-missing` | deklarált tag-kulcs hiányzik, a tagek olvashatók: authoritatív hiány | DRIFT |

### A `extra-tag-full-set` verdiktje és annak indoka

`full-set` mellett az extra OCI-tag útvonala a tervbe kerül. A szándéknak nincs értéke rá (null), a megfigyelt érték string, az
engine `compare_exact`-ja eltérő JSON-kindre `(false, false)`-t ad, tehát **`NOT_COMPARABLE`**, ami az objektumot `DRIFT`-té teszi.
Az eredmény helyes (jelezzük az eltérést), de a név félrevezet: egy „extra elem" nem összehasonlíthatatlan, hanem felesleges.

## Nyitott pontok (az engine nem tudja kifejezni; nem javítottuk, nem is fedtük el)

1. **Kulcsszűrő a kollekció-tervben nincs.** A „csak a deklarált kulcsok" a környezet vetítésén múlik (4c); ha a vetítést kihagyják,
   az engine az extra taget `NOT_COMPARABLE`-lel DRIFT-nek mondja. A szerződés-doksiban (engine) ezt ki kell mondani.
2. **Nincs „extra elem" verdikt.** A `full-set` felesleges eleme `NOT_COMPARABLE`-ként jelenik meg, nem külön `EXTRA`-ként.
3. **A mező hiányának kifejezett követelménye** (a szándék azt kéri, hogy a mező ne legyen) a registry-sémában ma nem fejezhető ki
   (nincs ilyen mező-szemantika), ezért **concept**, nincs rá eset. Ha a séma támogatja, új fixture-verzió kell.
4. **A hatókör-deklaráció helye** (`management.tags_scope`) a szándék-dokumentumban a fixture döntése; a registry-sémának nincs
   ilyen mezője. A séma-bővítés (aláírt új verzió) a registry-szál dolga.
5. `unknown` és `unobserved` a verdiktben ugyanaz (`UNOBSERVED`), csak az observation digest és a bizonyíték különbözteti meg őket.

## Mit tegyen a szál

Vendorolja a v2-t bájtra azonosan a `MANIFEST.sha256`-tal és a forrás-commit megjelölésével; ne írja át az `expected/` fájlokat.
A v1-hez készült tesztek maradnak a v1-gyel. Az `engine-input.json` az engine differenciál-vektorainak formája, közvetlenül betölthető.
