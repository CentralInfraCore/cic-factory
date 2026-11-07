# Második orchestrátori review: forms-oracle-provider-integration-01a spec (a javítások után)

Dátum: 2026-11-07. A jobot **nem indítottam**; csak a specet és a hozzá tartozó review/validációs dokumentumokat módosítottam (a Relay, az Oracle-modul és a Forms production kódja változatlan). Vizsgált fájlok: `input.md` (144 sor), `meta.yaml`, `ref/spec-validation.md`, `ref/spec-review.md`.

**Az átvizsgálás függetlenségének határa.** A javításokat és ezt a második átvizsgálást ugyanaz az orchestrátor-folyamat végezte, amely az első specet is írta. Az első review ezért volt értékes, mert hibát talált a saját specemben; ennek a másodiknak az ereje a **gépi és tartalmi ellenőrzéseken** van (idézet-egyeztetés, a KB lekérdezése, a pinek összevetése a Forms `corpus/pins.yaml` fájljával), nem a függetlenségen. Egy külső szem a specre javasolt, nem kötelező.

## Eredmény: GO (az 01a futtatásához külön GO szükséges)

## A hét kiemelt pont

| # | Pont | Eredmény | Hely és indoklás |
|---|---|---|---|
| 1 | Csak baseline, leltár, leképezés, Q0–Q9, kódmódosítás nélkül | **PASS** | `input.md:9` „Egyetlen repóban sem módosítasz…"; `:120` (biztonsági határok); `:124` (Git) |
| 2 | Két sémaszerep, új objektummodell nélkül | **PASS** | `:73` (C szakasz), `:55` (a `vcn.json` nem primitives-séma), `:39` (nincs új primitive-mező), `:80` (nincs új intent/state ág) |
| 3 | Commit-pin, függőségek, licencek, TinyGo-próba határai | **PASS** (az F2 javítása után) | pinek a `corpus/pins.yaml` szerint `:29`; Pin-tábla `:31`; verzió/licenc/függőségkezelés és a scratch TinyGo-próba `:69`; nincs dependency-módosítás `:69`; licenc-döntés tilalma `:89` |
| 4 | `state_surface` és admission nincs késznek állítva | **PASS** | `:56` (a Forms nem validálja a `state_surface`-t), `:59` |
| 5 | Reachability kötelező | **PASS** | `:45` (grep `_test.go` kizárással, fájl:sor VAGY `deadcode`), `:64`, `:111` |
| 6 | Claim–evidence és verifikációs követelmények | **PASS** | `:106` (a tábla fejléce), `:109` (ellenőrizhető elvárások) |
| 7 | K1–K11 és a K11 indoklása | **PASS** | `validate-meta.sh`: OK; `validate-spec.sh`: GO, **figyelmeztetés nélkül**; a K11 most azért PASS, mert a `kb_focus` kitöltött és ellenőrzött (lásd lent); a `ref/spec-validation.md` idézetei gépileg egyeztetve |

## Az első review javításainak ellenőrzése

| Javítás | Eredmény | Ellenőrzés |
|---|---|---|
| **F1** KB boot sequence, KB-korlátok, helyes K11-indoklás | **JAVÍTVA** | Boot sequence szakasz `:17`; id-ellenőrzés `file_path` szerint `:21`; KB-korlátok `:22`. A hat id-t újraolvastam `get_chunk`-kal, a `file_path` egyezik: `c7529` → `docs/design/architecture.md` (Goal); `c7616` → `docs/design/specs/state-model.md` (az állapotág példája); `c7487` → `docs/contracts/en/wasm-abi.md`; `c7668` → `module/contracts.yaml`; `c7675` → `module/correspondence.yaml`; `c7550` → `docs/design/primitives-alignment.md` (a Relay-hivatkozásról szóló szakasz). A `kb_status` és `search_nodes("cic-primitive-forms")` (üres) újra igazolja a KB-korlátokat. A `meta.yaml` megjegyzése és a `spec-validation.md` hamis mondata a valóra cserélve |
| **F2** pinek, registry explicit | **JAVÍTVA** | `:29`. A spec két értéke (`73ae4692f0680a316d367179ce057195a0031688`, `6db77d4dca4ce3af3be66b3a7a85404fd0b63684`) **egyezik** a Forms `corpus/pins.yaml`-jával a `2f02a75` commitnál (a `grep` kimenete ellenőrizve: a `cic-primitives-73ae469-6a188078` pin és a `registry-network-interface`/`registry-network-space` pin). A spec ezeket „ellenőrizd, ne vedd át"-ként adja, a fájl az irányadó. A `meta.yaml` `workplace.repos` listája tartalmazza a `cic-schema-registry`-t |
| **F3** nem szennyező mérések, tiszta `git status` | **JAVÍTVA** | `:93` (eldobható másolat `git archive`-val, kimenetek a repókon kívül, `git status --porcelain` klónonként idézve), `:93` (automatikus visszaállítás tilos) |
| **F4** környezet, `NOT MEASURED`, prioritás | **JAVÍTVA** | `:95`, `:97`, `:99` (A–D kötelező, F utolsó), Q0/Q1 módszer `:84` |
| **F5** szó szerinti idézetek | **JAVÍTVA** | a `ref/spec-validation.md` minden idézete gépileg egyeztetve az `input.md`-vel |

## A saját javításaimban a második átvizsgálás során talált két hiány (kijavítva)

1. **A KB a Go fájlokat `.yaml` kiterjesztéssel indexeli.** A `c7668` és a `c7675` `file_path`-ja `module/contracts.yaml` és `module/correspondence.yaml`, a chunk tartalma viszont a `contracts.go` és a `correspondence.go` Go-kódja (`go:embed`). Az ellenőrzés a literális `file_path`-ra igaz, de az agent a tényleges fájlt keresné `.yaml`-ként. Javítva: a spec kimondja (`input.md:21`), és a `meta.yaml` kommentjei is.
2. **A `deadcode` nem szerepelt az eldobható másolatban futó mérések listájában** (`:93`), pedig modullétrehozást és `go.sum`-módosítást válthat ki. Javítva: a lista tartalmazza.

## Megfigyelések (nem blokkolók)

* `agent.max_turns: "150"` változatlan, ahogy a döntés kérte; a prioritási sorrend (`:99`) és a `NOT MEASURED` szabály (`:97`) kezeli, ha a keret kimerül. Az `--resume` lehetősége megvan.
* A `git checkout --detach <pin>` a klónok munkafáját a pinelt állapotra állítja (nem követett fájlt és nem történetet módosít); a spec ezért kéri a végső `git status --porcelain` idézését. Ha a Forms `corpus/pins.yaml`-ja a futáskor más értéket tartalmaz, a fájl az irányadó (`:29`).
* A KB-ban a modul `5d0a327`-nél áll, az `#33` és `#34` előtt: a `kb_focus` tervezési kontextus; a Boot sequence kimondja, hogy ha a KB és a klón eltér, a klón számít.

## Következő lépés

A javított spec **GO** a gépi és a tartalmi kapukon. Az 01a futtatásához **külön GO** szükséges; az 01b nem indul; minden más HOLD változatlan. A Factory felé ezt a specet ne írják át futtatás előtt anélkül, hogy a `validate-spec.sh` és `validate-meta.sh` újra lefutna.
