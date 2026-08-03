# oci-extract-generalize — agent output

**Modul-repo:** `cic-module-oracle-cloud`, branch `feature/oci-extract-generalize`
**Commit:** `5c1e0354dfc1a37aeeded15f078e4913f51de749` (Vault-aláírt)
**CI:** `success`, run `30803018703`, headSha **egyezik** a commit-tal, mind a 20 step zöld

---

## A kérdés, amit a job eldöntött

A séma-pipeline `vcn`-en és `subnet`-en volt bizonyítva — mindkettő a
**core/network** szolgáltatásban. Ez azt igazolta, hogy a pipeline nem
*resource*-specifikus; azt nem, hogy nem *service*-specifikus.

**A válasz: az volt.** Négy feltételezés élt a kódban, amely core/network-re
igaz, az OCI felületére nem. Ebből három **némán** hibázott: érvényesnek látszó
sémát adott, exit 0-val.

Mértem, nem következtettem: a pinelt SDK (`v65.121.0`) **összes** 319
kliensfájlján, 171 szolgáltatáson.

---

## Amit találtam (részletesen: `service-assumptions.md`)

| # | Feltételezés | Hol | Mekkora a valóságban |
|---|---|---|---|
| A1 | Egy műveletnek van request objektuma | `client.go:182`, `client.go:118` | `identity.ListRegions` némán eldobva → a lefedettség **8047/8048** volt, nem 8047/8047 |
| A2 | A create ige „Create", a delete „Delete" | `schema.go:38`, `policy.go:139`, `schema.go:161` | `core.Instance` = `LaunchInstance`/`TerminateInstance`; **570/1217** erőforrásnak nincs `Create<R>Details` |
| A3 | Egy path-paraméter címez, és az az id | a hiány maga; a fogyasztó: `module/provider.go:1059` | **323/1481 `Get*` (21,8%)**, **65/158 szolgáltatás** nem így címez |
| A4 | Minden modell struct | `extract.go:67` | **1014** interface-modell (470 `*Details`/`*Base`); 8 erőforrás create-modellje interface |

A legfontosabb nem ez a négy, hanem a közös mintájuk: **a nevező sosem volt
megszámolva.** Az extractor kihagyta, amit nem tudott feloldani, így a hiány
sosem jelent meg hiányként.

---

## Amit csináltam

**1. A lifecycle-t az HTTP felületből vezetem le** (`tools/oci-extract/resolve.go`),
nem a Go azonosítókból:

```
read = GET <readPath> · collection = readPath a lezáró /{param} nélkül
create = POST <collection> · update = PUT <readPath> különben POST <readPath>
delete = DELETE <readPath> · actions = POST a <readPath>/… alatt
```

A body-modell a request struct saját `contributesTo:"body"` tagjéből jön, a
read-modell a response `presentIn:"body"`-jából — az SDK saját tagjeiből, sosem
névből. Egy konvenció maradt, fallbackként: ha nincs response-modell, a belépési
pont `Get<Resource>` — és a `Resolution.ReadOpSource` **rögzíti**, melyik úton
oldott fel, tehát a feltételezés nincs elrejtve.

**2. A címzési szerződés kimondott lett:** minden művelet mellé `path_params`.

**3. A némaság jelzéssé vált** — ez a job szerkezeti hozadéka:
- `oci-extract -audit` a jelölteket **külön** számolja a feloldottaktól, **exit 4**
- `-schema`/`-policy` jelenti a feloldatlan felületet, **exit 5** → a
  `make oci.generate` nem tud levezetetlen create-felületű sémát commitolni
- `make oci.audit` az egész SDK-n

**4. Polimorf modellek rögzítve** (`Model.Kind`) és **nevesítve jelentve** — a
konkrét implementációk kibontása tudatosan kimaradt (szemantikai döntés).

---

## Eredmény

```
$ oci-extract -audit $(cat /tmp/clients.txt) | tail -1
TOTAL 8048/8048 operations resolved, 0 missing method/path
```

Szolgáltatásonként a heterogén mintán — a minta **törésre** lett válogatva, nem
zöldre (az indoklás `service-assumptions.md`-ben):

| Szolgáltatás | Miért ez | Művelet |
|---|---|---|
| core virtualnetwork | kontroll: a P2.2 alapja | **271/271** |
| core compute | Launch/Terminate ige, *ugyanaz a package* | **129/129** |
| identity | request nélküli művelet | **145/145** |
| objectstorage | két path-param, névvel címzett, POST update | **56/56** |
| database | polimorf create-testek, legnagyobb felület | **456/456** |
| dns | polimorf create-base konkrét create mellett | **54/54** |

**`core.Instance` előtte/utána** — a legbeszédesebb eset:

| | régi (exit 0) | új |
|---|---|---|
| `required` | **`None`** | `['availabilityDomain','compartmentId']` |
| config mezők | 22 | 35 |
| műveletek | Get, Update, ChangeCompartment | + **LaunchInstance**, **TerminateInstance** |

---

## Regresszió: `vcn` + `subnet` változatlan

```
$ oci-extract -diff /tmp/oldschemas/vcn.json module/schemas/vcn.json
{"breaking": null, "compatible": null}     exit=0
```

Sem breaking, sem compatible változás — a config felület **szó szerint azonos**
(a `state` azonosságát külön igazoltam). A bundle csak az additív `path_params`-szal
bővült, ezért kellett a `extracted_schema_hash` újrapinelése és a guest újraépítése.

Gépi őrzés (`tools/oci-extract/regression_test.go`), offline, CI-ban fut:
- `TestCommittedSchemaCoverageUnchanged` — kézzel kiírt elvárás (mező→policy,
  `required`, state-méret, method/path/path_params) a committolt sémák ellen; **új
  mező is hibát ad**. A várt érték a tesztben áll, nem a vizsgált fájlból — különben
  körkörös lenne.
- `TestVcnFixtureStillResolvesStructurally` — hogy a VCN alakját a *generalizált*
  resolver adja, nem maradék különeset.

**Ez a teszt valós hibát fogott:** a VCN fixture-ből hiányzott a
`ChangeVcnCompartment` művelet, ezért `compartmentId` `create-only`-nak jött ki
`action` helyett. A fixture kiegészült, `client_test.go` 3→4 műveletre frissült.

---

## Definition of Done

| # | Követelmény | Állapot |
|---|---|---|
| 1 | N/N feloldva, 0 hiányzó method/path, szolgáltatásonként | ✅ 8048/8048 SDK-szinten + a 6 elemű minta számai |
| 2 | `vcn`+`subnet` lefedettség változatlan, regressziós teszt | ✅ `-diff`: nincs változás; 2 új teszt |
| 3 | `make check` + wasm build/test zöld | ✅ helyben és CI-ban |
| 4 | `MANIFEST.sha256` regenerálva, gate zöld | ✅ exit 0 |
| 5 | `docs.link-check` zöld | ✅ |
| 6 | CI zöld a feature branchen, headSha egyeztetve | ✅ `5c1e035…` == run headSha, 20/20 step |

---

## Amit tudatosan NEM csináltam

- **Nem kezdtem el a sweepet.** A séma-oldali mérés a hat elemű mintán futott; a
  teljes erőforrás-szintű futtatás a következő jobé. Amit tudni kell hozzá:
  `sweep-input.md`.
- **Nem bontottam ki a polimorf modelleket** — diszkriminátor-szemantika,
  modellezési döntés.
- **Nem javítottam a `templatePath`-ot** (`module/provider.go:1059`), ami ma minden
  `{…}`-ba a resource id-t írja. Az extractor most **kiadja** a kötendő
  paramétereket; hogy az érték honnan jön, beágyazási döntés → `sweep-input.md`.
- **Nem oldottam meg a kézzel kurált bemeneti fájllistát** az `oci.generate`-ben.
  Mérhető következménye van (a `cidrBlock` `create-only`-ként szerepel, holott
  `AddVcnCidr`/`RemoveVcnCidr` akción át változtatható), de a javítás megváltoztatná
  a committolt `vcn`/`subnet` felületet (DoD 2 tiltja) és akció-argumentum
  modellezési kérdést vetne fel. Felírva, nem elvégezve.
- **Nem nyúltam a CIC-Relay-hez.** Relay-igényt nem találtam; a
  `relay-requirements.md` nem változott.
- **Nem kötöttem be primitives/YANG sémát.**

## Orchestrátori döntést igénylő pont

**A `ci.yml` push-triggerét kibővítettem `feature/**`-ra.** A DoD 6 e nélkül nem
lett volna igazolható: a job-konvenció `feature/<job-id>` branchet ír elő, a
trigger-lista viszont csak `feat/**`-ot ismert, így a push nem indított futást.
Ez CI-szabály tágítás, amit a job nem kért explicit — ha nem kívánatos, önállóan
visszavehető, a többi változás nem függ tőle.

## Környezeti megjegyzés

A lokális `make check` először **nem repo-beli** fájlokon bukott: a `cic-graph` KB
indexer minden forrásfájl mellé `.yaml` companion sidecart generált a klónban
(57 db), és a yamllint ezeket is nézte. Nem tracked fájlok, a repo egyetlen
`.yaml` companiont sem követ — kimozgattam őket a fából, utána zöld. A CI tiszta
checkouton fut, ott fel sem merül. **Nem** commitoltam őket.

---

## KB boot — a `kb_focus` elemek ellenőrzése

Mindhárom megadott chunk azt adta, amit az `input.md` táblája előírt:

| id | Tartalom | Egyezik |
|---|---|---|
| `c1719` | relay mint végrehajtó motor — nem dönt, `NextHops` szerint halad | ✅ |
| `c1734` | séma belső viselkedés — `StateRequirement`/`Dependencies`/`PluginRef`/`NextHops` | ✅ |
| `c4147` | `core/cabinet/` — schema/module/workflow registry + wazero WASM | ✅ |

`kb_status`: 10590 chunk, betöltve.

---

## Kimenetek

| Fájl | Tartalom |
|---|---|
| `agent-output.md` | ez |
| `claim-evidence.md` | claim-evidence tábla parancs-kimenetekkel + „nem igazolt" szakasz |
| `service-assumptions.md` | a négy feltételezés: fájl:sor, eltörő kimenet, feloldás, + a negatív eredmények |
| `sweep-input.md` | osztályozás, várható törések, indokolt kizárások, örökölt mérőeszközök |
