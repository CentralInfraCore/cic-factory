# VCN-pipeline — lokális, csak olvasó Intent → Observed → Conformance → Evidence

`tools/vcn-pipeline/run.py` a négy komponens négy szakaszát egyetlen futásban köti össze egy rögzített fixture-n
(`tools/vcn-pipeline/fixtures/vcn-v1`, a cic-factory `fixtures/vcn-v1`-jének módosítatlan másolata, `MANIFEST.sha256`-tal
ellenőrizve). **Nem hív OCI-t, nem ír semmit, nem ír alá, és nem állít éles kriptográfiai bizonyítást.**

```
python3 tools/vcn-pipeline/run.py --all                                  # amit tud, azt végrehajtja; a többit fixture-ből veszi, és megmondja
python3 tools/vcn-pipeline/run.py --all --require-executed all           # hiba (1), ha bármelyik szakasz nem hajtható végre
python3 tools/vcn-pipeline/run.py --case partial-read --json
python3 tools/vcn-pipeline/run.py --fixture-only                         # csak a fixture, semmit nem hajt végre (a jelentés is ezt mondja)
```

Környezet: `CIC_MODULE_PATH`, `CIC_REGISTRY_PATH`, `CIC_ENGINE_PATH`, `CIC_RELAY_PATH` (a komponensek checkoutjai; csak olvasva),
`go`, `cargo`, `python3` + PyYAML. Kilépési kód: 0 minden eset rendben, 1 egy eset hibás (eltérés, átadási hiba, nem
végrehajtott kötelező szakasz, hibás adapter), 2 használati vagy fixture-hiba.

## Mit jelent az `EXECUTED` és a `FIXTURE`

| Címke | Jelentés |
|---|---|
| `EXECUTED` | a komponens **valódi kódját** futtattuk a szakasz bemenetén, és az eredményt hasonlítottuk a fixture várt fájljához |
| `FIXTURE` | a komponens nem volt futtatható, a fixture várt fájlját használtuk; a jelentés **mindig** kiírja, ha ez történt |

A jelentés végén "how each stage ran" sorok mondják meg szakaszonként a pontos módszert. **Fontos:** az `EXECUTED` ma egy
**shim-mel** történik, nem a komponens hivatalos belépési pontján. Egyik komponensnek sincs a szakaszhoz hívható CLI-je vagy
exportált függvénye, ezért az adapter a komponens forrását egy scratch **másolatba** teszi, a másolathoz ad egy kis teszt-shimet
(`tools/vcn-pipeline/shims/`), és a komponens saját build-eszközével futtatja. A komponens checkoutja soha nem módosul.

| Szakasz | Komponens | Mit futtat | Hogyan |
|---|---|---|---|
| 3 normalize | `cic-module-oracle-cloud` | `normalizeObserved` | `go test` shim a modul másolatán |
| 4 bind | `cic-schema-registry` | `tools.registrylib.correspondence.apply` | `python -I`, a checkoutból importálva |
| 5 verdict | `cic-primitive-engine` | `evaluate_verdict` | `cargo test` shim az engine másolatán |
| 6 evidence | `CIC-Relay` | `vcnEvidenceFrom`, `VerifyProofArtifact` | `go test` shim a Relay másolatán |

## Mi garantált egy futásban

* A fixture változatlan (manifest), különben a futás el sem indul.
* **Átadás:** minden `EXECUTED` szakasz megmondja, mit fogyasztott (digest), és ez egyezik az előző szakasz kimenetével.
* **Kimenet:** minden szakasz kimenete egyezik a fixture várt fájljával; a végső objektum-verdikt és a mezőnkénti verdiktek
  egyeznek az `expected/verdict.fields.json`-nal, a bizonyíték-állítások az `expected/evidence.claims.json`-nal.
* Fail-closed: egy elérhető, de hibázó `EXECUTED` adapter soha nem kap fixture-visszaesést; a `--require-executed` kizárja a néma
  visszaesést; egy adapter, amely más címkét jelent, mint ami, hibát okoz.

## Státusz (háromszintű)

| Állítás | Státusz |
|---|---|
| a négy szakasz a valódi komponenskódon fut, a fixture mind a 9 esetére egyezik | **implemented** (tesztelve; shim-mel) |
| hivatalos belépési pont a komponenseknél | **concept** (lásd lent) |
| a v2 (hatókör-tudatos) fixture futtatása | **scaffold**: a futtató a fixture-könyvtárat paraméterként kapja, de a v2 szerkezetét ma kifejezetten visszautasítja |
| a 6. szakasz láncának hash-e | **nem aláírás és nem éles ProofTrace**, egy teszt-oldali lánc a szakaszok hash-eiből |
| bármilyen OCI-hívás, aláírás, Vault, éles bizonyíték | **nincs** |

A `desired-absent-observed-present` eset a v1 fixture szerint adja vissza: `/dns_label` `NOT_COMPARABLE`, az objektum `DRIFT`.
A tulajdonos 2026-10-21-i döntése szerint a nem deklarált mező alapértelmezésben **nem kezelt**, és a hatókör-tudatos v2 fixture
ezt az eredményt megváltoztatja; a jelentés ezt az esetnél ki is írja. Ez **nem a jelenlegi kívánt viselkedés**.

## A shimek helyére javasolt vékony belépési pontok (nincs PR, javaslat)

| Repó | Javaslat |
|---|---|
| `cic-module-oracle-cloud` | a tiszta normalizálás kerüljön importálható csomagba (nincs wasm-build kényszer), plus egy vékony `cmd/vcn-normalize`, amely egy `{status, body, transport}` JSON-t olvas, és a `{effective_config, state, coverage}` JSON-t írja. Ma a `normalizeObserved` a `package main`-ben van, kisbetűs |
| `cic-schema-registry` | `python -m tools.registrylib.correspondence apply --correspondence F < observed.oci.json > observed.registry.json` CLI |
| `cic-primitive-engine` | a `cli` crate-ben egy `verdict --input engine-input.json` alparancs, amely az `evaluate_verdict`-et hívja és a kanonikus verdiktet írja |
| `CIC-Relay` | az offline evidence-építő legyen egy `cmd/` alatti vékony parancs vagy exportált függvény; ma a `cmd/relay` `package main` tesztjében él |

Ha ezek megvannak, a shimek törölhetők, és az `EXECUTED` a komponens hivatalos felületét jelenti.

## Teszt

`python3 -W error::ResourceWarning -m unittest tools/vcn-pipeline/test_vcn_pipeline.py` (24 teszt, az integrációs kettő csak akkor
fut, ha a négy `CIC_*_PATH` be van állítva). A teszt hamis adapterekkel bizonyítja, hogy az átadási hiba, a hazudó szakasz, a
rossz címke és a kötelező, de nem végrehajtható szakasz elbukik; egy valódi komponens megváltoztatott leképezése valóban megbuktatja a
futást; és a futtató szándékos hibái (tesztből kiolvasható lista) mind pirosra váltanak egy tesztet.
