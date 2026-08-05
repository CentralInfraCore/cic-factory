# Invoke — scoping döntés (feladat C)

## Mi készült el ebben a jobban

- `TestManualRealOCIInvoke` létezik (`module/manual_real_oci_test.go`), hívja
  a valós `Invoke()` handlert (nem `Execute()`-ot), `REAL_OCI_TEST=1` +
  `OCI_INVOKE_OPERATION`/`OCI_INVOKE_CONFIG_JSON` env-guard mögött.
- Env-guard nélkül **nem** ad hálózati hívást — lásd
  `output/claim-evidence.md`, a guard-futtatás bizonyítéka.
- **Ez nem futott valós OCI ellen** — ez a job explicit tiltása (lásd
  `input.md` "Kemény korlátok" 3. pont: ne hozzon létre valós OCI erőforrást).

## A döntés, amit meg kellett hozni

Az `Invoke` egy `action-managed` mezőhöz kötött OCI-műveletet hajt végre. A
generált `cic:compute:instance` sémában **egyetlen** ilyen mező van:
`compartmentId → ChangeInstanceCompartmentDetails` (mérve, lásd lent). Ugyanez
igaz a meglévő `vcn`/`subnet` sémákra is — mindkettőnél az egyetlen
action-managed mező a `compartmentId`.

```bash
$ python3 -c "
import json
d = json.load(open('module/schemas/core/instance.json'))
for k,v in d['config']['properties'].items():
    if v.get('x-cic-policy') == 'action-managed':
        print(k, '->', v.get('x-cic-action'))
"
compartmentId -> ChangeInstanceCompartmentDetails
```

**`ChangeInstanceCompartment` végrehajtásához egy második compartment kell** —
a resource-ot ebbe kell átmozgatni. A trial tenancy (amit az orchestrátor a
korábbi jobokban használt) **üres a root compartmenten kívül** — ezt az
`input.md` már ismert tényként közölte, nem ez a job derítette ki.

## Miért nem egy másik akciót választottam helyette

OCI-nak vannak nem compartment-mozgató instance-akciói is (power state:
`InstanceAction` — start/stop/reset), amik nem igényelnének második
compartmentet. Megnéztem, hogy ezek elérhetők-e a jelenlegi extrakciós
recepttel: **nem.**

A `tools/oci-extract/resolve.go` szerint egy action-op csak akkor kerül be a
sémába, ha a hívó **konkrétan megadta** a kérés body-modelljét tartalmazó
fájlt (`resolve.go`, "An action whose body model was not supplied is out of
scope for this invocation, not missing: the caller chooses which model files
to feed in" — és ha a body-model neve üres, az op is kimarad, tehát a
query-param-alapú, body nélküli akciók sem kerülnek be automatikusan). Az
input.md receptje (`launch_instance_details.go`, `update_instance_details.go`,
`instance.go`, `change_instance_compartment_details.go`,
`core_compute_client.go`) csak a `ChangeInstanceCompartmentDetails`
body-modellt adja át — ez az oka, hogy a generált `instance.json`
`operations` térképe **csak öt** műveletet tartalmaz
(`GetInstance`/`LaunchInstance`/`UpdateInstance`/`TerminateInstance`/
`ChangeInstanceCompartment`), holott a valós `core_compute_client.go` a teljes
compute felületet tartalmazza (129 op, `oci-schema-pipeline.md` P2.5 tábla).

Egy power-state akció bevonása tehát **nem env-probléma, hanem extrakciós
receptbővítés** lenne: a megfelelő `instance_action_details.go`-szerű (vagy
üres body esetén a query-param kezelés kibővítése) fájlt kellene átadni a
`-schema` hívásnak, és ellenőrizni, hogy a resolver body nélküli
action-opokat egyáltalán fel tudja-e venni — ez ma nem biztos (`m.Name == ""`
→ kihagyva). Ez explicit **nincs ebben a jobban** — ne feltételezz mást.

## Mi szállítható ebből becsületesen

- A `TestManualRealOCIInvoke` **létezik és helyesen van env-guardolva** —
  ez szállítva van.
- Az, hogy `Invoke()` ténylegesen helyesen fut-e valós `ChangeInstanceCompartment`
  ellen, **nincs igazolva**. Ez a "nem igazolt" sorba megy — lásd
  `output/claim-evidence.md`.
- Ha az orchestrátor egy második compartmentet létrehoz a trial tenancyben
  (`oci iam compartment create`, engedélyezett, olcsó, nem VM), a
  `TestManualRealOCIInvoke` a jelenlegi kóddal lefuttatható —
  lásd `output/orchestrator-verification.md` a pontos recepthez.

## Amit NEM állítok

- Nem állítom, hogy `Invoke()` helyesen működik valós OCI ellen — csak azt,
  hogy a teszt megléte és az env-guard igazolt.
- Nem terjesztettem ki az extrakciós receptet power-state akciókra — ez explicit
  nem volt e job hatóköre (a hatókör az `Instance` séma + `Destroy`/`Invoke`
  harness, nem az extraktor bővítése).
