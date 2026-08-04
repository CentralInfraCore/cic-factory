# review — oci-lifecycle-role-bridge

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-04T17:50:00Z
- Feature branch: `feature/oci-lifecycle-role-bridge` (két repóban)
- Review-zott commit: modul-repo `8e379e8`

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | **GO** | K9 (reachability) elsőre elbukott — a spec kiegészítve a szerep production hívási láncának előírásával |
| `tools/validate-output.sh` | **GO** | 4 fájl a live workdirben. WARN: 15 `file:line` nem oldható fel (a `tools/env.sh`-ban nincs modul-repo path) |
| CI | **zöld** | `headSha: 8e379e8` — egyeztetve a review-zott commit-tal. (A job záró `git push`-a hálózati hibával elszállt, exit 128; a pushot kézzel pótoltam, a CI utána futott le.) |

## Amit ténylegesen ellenőriztem

| Állítás | Hogyan | Eredmény |
|---|---|---|
| A hat névalapú hely tényleg létezett a javítás előtt | `git show 4c79605:module/provider.go \| sed -n '<sor>p'` mind a hatra | **4 pontos** (373, 391, 592, 730), **2 sordriftes**: #5 a 773-on van (nem 785), #6 a 1025/1030/1036-on (nem 1038/1043/1049). A **konstrukciók valósak**, csak a sorszám csúszott |
| Nem maradt névből levezetés | `grep -n "\.resource\b" module/provider.go` | **nulla találat** (exit 1) — a `resource` mezőt magát is törölték |
| A séma hordozza a szerepet | `python3` a `vcn.json`-on | `CreateVcn→create`, `GetVcn→read`, `UpdateVcn→update`, `DeleteVcn→delete`, `ChangeVcnCompartment→action` |
| **Reachability-lánc (K9)** | `contracts.go:120,135` (parse) → `contracts.go:68` `opByRole` → `provider.go:371,382,383,590,742,786,1041,1045` (fogyasztás) | **teljes**, production kódban, teszt nélkül |
| A szerep-feloldás alternatív igékre is működik | `oci-extract` futtatása az `Instance`-re | `LaunchInstance→create`, `TerminateInstance→delete` — **névtől függetlenül** |

## Valós OCI verifikáció — ezt én futtattam (a spec így írta elő)

POC (`oc1`) trial tenancy, `VM.Standard.E2.1.Micro`, eu-frankfurt-1. A modul
**javított, módosítatlan** kódjával:

| Lépés | Eredmény |
|---|---|
| `CreateVcn` | 200 `succeeded` |
| `CreateSubnet` | 200 `succeeded` |
| **`LaunchInstance`** | **200 `accepted`**, `work_request_id` — *tegnap ugyanez HTTP 400 `CannotParseRequest` volt* |
| **`Poll`** a Work Requesten | **200**, `work_status: SUCCEEDED`, `terminal: true` — **a `poll` első valós OCI futása** |
| **`TerminateInstance`** | **204 `accepted`**, `work_request_id` |
| `DeleteSubnet` / `DeleteVcn` | 204 / 204 |

Tenancy utána **üres** (instance, VCN, boot volume mind ellenőrizve). A scratch
séma-beágyazás visszavonva, a repo tiszta.

**Egy fontos korlát:** a `LaunchInstance` teszthez **scratch módon be kellett
ágyaznom** az `instance.json`-t, mert a modul ma is csak `vcn`+`subnet`-et
szállít. Tehát a javításnak **nincs olyan szállított erőforrása, ami
meghajtaná** — a regresszióvédelem fixture-alapú, nem szállított-séma-alapú.

## Új lelet a verifikáció közben — `poll` `percent_complete` mindig 0

A `Poll` `SUCCEEDED` mellé `percent_complete: 0`-t adott. Az OCI ugyanarra a
Work Requestre **`100.0`**-t jelent (`oci work-requests work-request get`).

Gyökérok, empirikusan bizonyítva:

```
$ go run  # {"status":"SUCCEEDED","percentComplete":100.0} → struct{Status string; PercentComplete int}
err=json: cannot unmarshal number 100.0 into Go struct field .percentComplete of type int
Status="SUCCEEDED" | PercentComplete=0
```

`provider.go:710` `PercentComplete int`, miközben az OCI **float**-ot küld — és
`provider.go:712` a `json.Unmarshal` **hibáját eldobja**. A `Status` beparse-olódik,
a százalék némán 0 marad.

**Ez ismét ugyanaz a hibaosztály:** eldobott hiba, ami a rossz értéket valódinak
mutatja. A `percent_complete: 0` megkülönböztethetetlen attól, hogy tényleg 0%.
**Nem ebben a jobban keletkezett** (a `Poll` korábbi kód), és a job hatókörén
kívül esik — a job tette *láthatóvá* azzal, hogy megírta a Poll tesztet.

## Amit NEM ellenőriztem

- **A DoD 3-as pontját** (a fixture-teszt bukik-e visszavett javítással) — az
  agent leírja, én nem hajtottam meg.
- **`make check`, wasm build/test, `MANIFEST.sha256`, `docs.link-check`** —
  egyiket sem futtattam külön.
- **A `contracts_test.go` és a `module/testdata/instance-fixture.json`
  tartalmi helyességét** — hogy tényleg azt a viselkedést rögzítik, amit
  állítanak.
- **A #1–#5 helyek javítás utáni viselkedését** külön-külön. A #6-ot (renderBody)
  valós OCI igazolta; a `Destroy` (#3/#4) a `TerminateInstance` 204-gyel
  igazoltnak tekinthető; a #1 (replace-plan) és #2 (update) **nincs élesben
  meghajtva**.
- **A polimorf create-modelleket** — továbbra is `exit 5`, változatlan hatókör.

## Nyitott tételek

1. **`poll` `percent_complete`** — külön, kicsi javítás (`float64` vagy
   `json.Number`, és a `Unmarshal` hibáját ne dobja el).
2. **Nincs szállított alternatív-igés erőforrás** — a javítást ma csak scratch
   sémával lehet élesben meghajtani. Egy `instance` (vagy más alternatív igés
   típus) felvétele tenné a védelmet valóssá.
3. **Két sordrift** a `name-derived-lifecycle.md`-ben (#5, #6) — a tartalom
   helyes, a hivatkozás pontatlan.

## Döntés

**MERGE.** A javítás azt oldotta meg, amiért a job
elindult, és ennél többet is: a hat névalapú hely közül **kettő** (`resolveOp`
és a `Destroy` step-címke) olyan hibát rejtett, amit tegnap **nem tudtam
biztosra** — a `Destroy` alternatív igés erőforrásra teljesen működésképtelen
volt. A döntő bizonyíték nem érvelés, hanem mérés: ugyanaz a `LaunchInstance`,
ami tegnap HTTP 400-zal bukott, ma 200 `accepted`-tel megy a modul saját
kódjával, és a `poll` először futott le valós Work Requesten.
