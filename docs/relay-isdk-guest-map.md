# Guest-oldali iSDK — feltérképezés és véleményezés

Felülvizsgált AI párbeszéd dokumentációja (orchestrátor session, 2026-06-11, 7. rész).
Előzmények: `relay-module-layer-map.md` (WASM host-frame),
`relay-reconcile-loop-map.md`, `relay-audit-trail-map.md`.

Jelleg: **réteg-leírás és véleményezés**, nem biztonsági audit. A WASM-lánc
guest-oldali fejlesztő-rétegét (iSDK) térképezi fel.

Forrás: KB c689 (`docs/en/concept/wasm_isdk.md` — iSDK API Contract v1);
`CIC-Relay/core/cabinet/testdata/echo_json.go` (teszt-stub);
host-fél: `relay-module-layer-map.md` 3. szakasz (`cicwasm.go`).

**Státusz (orchestrátor megerősítés 2026-06-11): `concept`.** A guest-oldali iSDK
mint fejlesztő-SDK nincs implementálva kódként; a contract dokumentált, a host
kész, a guest-oldalt kézzel írt stub-ok demonstrálják.

---

## Amit a source tartalmaz

### 1. A guest contract dokumentálva — c689 (concept)
Az iSDK API Contract v1 pontosan definiált:
```
Call(op: "init"|"process"|"get"|"notify",
     auth_context_json: JSON,
     data_json: JSON)
 -> (data_json: JSON, error_json: JSON|null)
```
- négy művelet: init / process / get / notify,
- fix hibakódok: INPUT / RUNTIME / INTERNAL / RESOURCE / TIMEOUT,
- v1 szinkron (WASI off, determinisztikus, nincs külső I/O),
- `notify` v1-ben stub; v2-ben a guest→host async visszaút (job_id),
- kulcsmondat: *"Uniform signature exposed via the guest export, **provided by
  iSDK**"* — az iSDK-nak kéne biztosítania a guest export boilerplate-et.

### 2. Guest-oldali kód = nyers host-teszt-stub
`core/cabinet/testdata/echo_json.go` — épp a lényeget mutatja: a teszt-modul
**kézzel** csinálja a teljes ABI-t, amit az iSDK-nak el kéne rejtenie:
```go
//export allocate    → C.malloc
//export deallocate  → C.free
//export Call        → unsafe.Slice, hardcoded JSON, (size<<32)|ptr packing
```
Ez nem domain-modul — host-teszt (a `get_null_data` / `get_invalid_json` op-ok a
host *hibakezelését* tesztelik). Egy valódi modul-fejlesztőnek **ma ugyanezt a
nyers `unsafe` / `C.malloc` / packed-uint64 réteget kézzel kéne írnia.**

---

## A hiányzó réteg

Az **iSDK mint guest SDK — az a réteg, ami a fejlesztőt megóvná a nyers WASM
ABI-tól — `concept` státuszú.** A feltérképezhető source-ban (`find` iSDK/guest/sdk
könyvtárra: üres) csak a contract (c689) és a teszt-stub-ok (echo_json.go, trap.go)
vannak; a fejlesztő-SDK nincs kódként.

A host-frame (`cicwasm.go`) egy tiszta, nyelvfüggetlen ABI-t kínál — de épp ettől a
guest-oldal **kritikus**: a contract csak akkor "fejlesztő-barát" (ahogy c689
ígéri), ha létezik az iSDK, ami a `unsafe` / `malloc` / packing boilerplate-et
becsomagolja. Amíg ez nincs a kézben, a "nyelvfüggetlen modul" ígéret gyakorlatilag
azt jelenti, hogy minden modul-szerző maga írja az echo_json.go-szintű nyers ABI-t.

Ez nem a host hibája — a host kész —, hanem a lánc **utolsó, fejlesztőhöz legközelebbi
szeme, ami még hiányzik.**

---

## Vélemény — a session mintájának lezárása

A WASM-lánc állapota rétegenként:

| Szem | Státusz | Bizonyíték |
|---|---|---|
| host-frame (`cicwasm.go`) | implemented | tiszta ABI, valódi timeout, stateless izoláció |
| guest ABI (nyers) | bizonyítottan működik | `echo_json.go` teszt-modul fut a host alatt |
| guest contract (c689) | concept (dokumentált) | iSDK API Contract v1 |
| **guest SDK (iSDK)** | **concept (nincs kód)** | csak kézi stub-ok, nincs SDK-boilerplate |

Ez a session feltérképezési ívének **ötödik, mintát lezáró lelete**, és élesebb,
mint a többi: itt nem csak a *visszacsatolás* (drift/reconcile) hiányzik, hanem a
*fejlesztői belépő* a WASM-modul-ökoszisztémába.

---

## A teljes session-minta — öt réteg, egy határvonal

1. **primitives→relay híd** (D-009 ExecutionSurface nyitott bridge) — séma kész, fordító nincs,
2. **natív↔WASM aszimmetria** (`relay-module-layer-map.md`) — jelen vs szándék,
3. **reconcile-kör felső fele** (`relay-reconcile-loop-map.md`) — apply kész, observe→compare nincs,
4. **audit-trail expected-placeholder** (`relay-audit-trail-map.md`) — rögzít, de nem vet össze,
5. **guest iSDK** (ez a dokumentum) — host kész, fejlesztő-SDK concept.

A teljes kép két, egymást kiegészítő határvonalra bomlik:

> **(A) Befelé, a valós világ felé:** a relay rögzíti, hogy mi történt, de nem veti
> össze azzal, aminek történnie kellett volna (drift/reconcile/self-healing —
> a következő réteg, 8.4 / D-009 / poc-drift-detection-01).
>
> **(B) Kifelé, a fejlesztő felé:** a WASM-modul-futtatás host-oldala kész és érett,
> de a modul-*írás* fejlesztő-rétege (iSDK) még concept.

Egyik sem hiányosság — mindkettő tudatos sorrend: a váz épült meg előbb, a
peremek (valós-állapot-visszacsatolás befelé, fejlesztő-SDK kifelé) következnek.
