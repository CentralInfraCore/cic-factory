# name-derived-lifecycle.md — a (B) leltár

Kiinduló mérés (a javítás előtt, `feature/oci-lifecycle-role-bridge` ág, `4c79605`-en):

```
grep -rn 'HasPrefix(.*"Create"\|HasPrefix(.*"Update"\|HasPrefix(.*"Delete"\|"Create"+\|"Delete"+' module/*.go | grep -v _test.go
```

adta a `renderBody` három találatát (a job spec bizonyított hibája). Ezt kibővítve
`"Update"+`, `"Get"+` mintákkal és a `c.resource` mező minden felhasználásának
manuális bejárásával (mivel `c.resource` csak string-konkatenációra szolgált — ha
minden felhasználóját megtaláltam, minden névből-levezetést megtaláltam), **hat**
production helyet azonosítottam. Mind a hat a `cic:compute:instance`-szerű
fixture-rel (`LaunchInstance` create, `TerminateInstance` delete,
`UpdateInstance` update — lásd `tools/oci-extract/testdata/{instance.go,
compute_client.go}`) van illusztrálva, mert ez a resource-alak az, amire a
konvenció ténylegesen elromlik.

| # | Hely (javítás előtti sor) | Mit tett | Hova esett egy alternatív igés művelet | Javítás után |
|---|---|---|---|---|
| 1 | `provider.go:373-374`, `planProviderOps` `"replace"` ág | `mk("Delete"+c.resource, …)`, `mk("Create"+c.resource, …)` | `Instance`-re `"DeleteInstance"`/`"CreateInstance"`-t konstruált volna — egyik sem létezik `c.operations`-ben, a lookup csendben elbukik, `po.Method`/`po.Path` üresen marad. A **terv** (nem csak a végrehajtás) már itt hibás lett volna: egy replace-plan Instance-re üres method/path-tal ment volna tovább `Execute`-ba. | `mkRole(roleDelete, …)`/`mkRole(roleCreate, …)` → `c.opByRole` a séma `role` mezője alapján megtalálja `TerminateInstance`/`LaunchInstance`-t, helyes method+path-tal. |
| 2 | `provider.go:391`, `planProviderOps` update-ág | `mk("Update"+c.resource, …)` | `Instance`-re `"UpdateInstance"`-t konstruált — ez **véletlenül helyes** volt, mert OCI-nál az update-ige a legtöbbször megmarad `Update<Resource>`-nek még akkor is, ha create/delete elszakad. Ez a "működik, amíg szerencsénk van" eset: bármelyik resource, aminek az update-je sem a konvenciót követi (pl. objectstorage bucket POST-tal), ugyanígy elbukott volna. | `mkRole(roleUpdate, …)` — a talált op nevétől függetlenül helyes. |
| 3 | `provider.go:592` (régi), `Destroy()` step-címke | `Operation: "Delete" + c.resource` | A **jelentett** (ProofTrace-be kerülő) művelet-név `Instance`-re `"DeleteInstance"` lett volna, miközben a ténylegesen meghívott (ha #4 nem blokkolta volna előbb) `"TerminateInstance"` — az audit-rekord hazudna arról, mi történt ténylegesen. | `Operation: opName` — a `resolveOp`-ból ténylegesen visszakapott, valós operation-név. |
| 4 | `provider.go:730` (régi), `resolveOp()` | `c.operations[verb+c.resource]` | `Instance`-re `verb="Delete"` esetén `"DeleteInstance"`-t keresett — **nem létezik**, tehát `resolveOp` mindig hibát adott vissza (`"no Delete operation for kind …"`). Ez nem kozmetikai: **`Destroy` teljesen működésképtelen lett volna** minden olyan resource-ra, aminek a delete-igéje nem szó szerint `"Delete"+resource`. | `c.opByRole(role)` — a szerep alapján megtalálja `TerminateInstance`-t, `Destroy` működik. |
| 5 | `provider.go:785` (régi), `Observe()` | `c.operations["Get"+c.resource]` | `Instance`-re `"GetInstance"`-t keresett — ez **véletlenül helyes**, mert OCI a read-műveletet szinte mindig `Get<Resource>`-nek nevezi (ezt maga a `resolve.go` is dokumentálja mint fallback-konvenciót, nem mint garantált szabályt). Egy resource, aminek a read-je strukturálisan más nevet kap, itt is elbukott volna. | `c.opByRole(roleRead)` — nem feltételezi a nevet. |
| 6 | `provider.go:1038,1043,1049` (régi), `renderBody()` | `strings.HasPrefix(po.Operation, "Delete"/"Create"/"Update")` | **A valós OCI ellen bizonyított hiba.** `Instance`-re `"LaunchInstance"` egyik prefixre sem illeszkedik → az action-ágra esik → mivel egyetlen action-mező `action`-mezője sem `"LaunchInstance"`, a `fields` map üres marad → a body `{}` → OCI válasza `HTTP 400 CannotParseRequest`. `"TerminateInstance"` sem illeszkedik `"Delete"`-re → szintén az action-ágra esik → body `{}` (nem `nil` — extra, nem várt body egy DELETE-en). | A `switch role { case roleCreate: …; case roleUpdate: …; default: /* action */ }` a séma `role` mezőjéből dönt — `LaunchInstance` teljes body-t kap, `TerminateInstance` `nil`-t. |

## Miért volt elég a `c.resource` mező eltávolítása a teljesség bizonyítékának

A javítás után `grep -n "\.resource\b" module/provider.go` **nulla** találatot ad
(a `resourceContract.resource` mezőt magát is töröltem `module/contracts.go`-ból,
mert semmi nem olvasta többé). Mivel minden névből-levezetés ezen az egy mezőn
(vagy a `po.Operation` nyers string-jén, ld. #6) keresztül történt, a mező teljes
eltávolítása és a fordítás sikere (`go vet ./...` zöld) önmagában is bizonyíték
arra, hogy nem maradt rejtett, meg nem talált hetedik hely.

```
$ grep -n "\.resource\b" module/provider.go
$ echo $?
1
```

## Zárt grep a DoD (2) pontjához

```
$ grep -rn 'HasPrefix(.*"Create"\|HasPrefix(.*"Update"\|HasPrefix(.*"Delete"\|"Create"+\|"Delete"+\|"Update"+\|"Get"+' module/*.go | grep -v _test.go
$ echo $?
1
```

Nulla találat a production kódban (a `_test.go` fájlokban — `contracts_test.go` —
előfordul a `"LaunchInstance"`/`"TerminateInstance"` szó, de azok a fixture teszt
elvárt-érték literáljai, nem lifecycle-döntést hozó kód).
