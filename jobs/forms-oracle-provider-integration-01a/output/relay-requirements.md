# relay-requirements.md — forms-oracle-provider-integration-01a

Reasoning mód: **audit**. Ez a dokumentum **követelményeket jelez, nem valósít
meg és nem dönt el semmit.**

**A CIC-Relay READ-ONLY.** Ebből a jobból a Relayt nem szerkesztettem, és egyik
rést sem kerültem meg azzal, hogy a relay logikáját a modulba duplikálnám.
A Relay-oldali tételek (R1–R3) a relay tulajdonosához tartoznak; a
modul-oldaliak (M1–M3) a `cic-module-oracle-cloud` `docs/design/relay-requirements.md`-jén
**kívül** esnek, mert azok nem relay-igények — itt azért vannak, mert a job
specje ezt a két szakaszt kérte egy fájlban.

Rögzített commitok: Relay **`55a899fa708d29e84dc6386f9307fdc2bfe9e493`** (ág
`main`), modul **`3e38886127b937dae00dd133ed0ce1ff4522106d`** (ág `devel`),
Forms **`2f02a75592a4b0894a3b76891e9ba3741479a7c5`**. Mérés: 2026-11-07.

## Azonosító-ütközés, hogy ne legyen félreérthető

A modul saját `docs/design/relay-requirements.md`-je **már használ** `R1`–`R5`
azonosítókat (R1 trust-flow expose, R2 OCI aláírás, R3 capability-manifest, R4
audit-folding, R5 egress tenant-resolved endpointra). **Az itteni R1–R3 NEM
azonos azokkal.** Ha ezek a tételek a modul repójába kerülnek, új, nem ütköző
azonosítót kell kapniuk (pl. `R6`–`R8`); ezt a döntést nem én hozom meg.

## Bizonyíték-osztályok (a folytatás 5. kényszere szerint)

| Osztály | Jelentés |
|---|---|
| **`AGENT_MEASURED (kódolvasás, folytatás)`** | ebben a folytatásban általam olvasott forrás, `fájl:sor`-ral. Olvasás, nem futtatás |
| **`AGENT_MEASURED (eszközfuttatás, korábbi futás)`** | az előző futásban általam futtatott parancs és idézett kimenet |
| **`ORCHESTRATOR_VERIFIED`** | az orchestrátor független újramérése (`ref/orchestrator-review-partial.md`). **Nem az én mérésem** |
| **`DOCUMENTED`** | design/spec/ADR állítása, kódbeli megfelelő nélkül vagy azelőtt |
| **`NOT MEASURED`** | nem mértem, és megadom, mi kellene hozzá |
| **`NOT INDEPENDENTLY VERIFIED`** | egy fél mérte, a másik nem reprodukálta, vagy HOLD alatt van |

---

# 1. Relay-oldali követelmények (a relay tulajdonosának)

## R1 — Az op-szókészlet eltérése: a Relay négy op-neve a provider nyolc ABI-műveletével szemben

| | |
|---|---|
| **Követelmény ID** | R1 |
| **Státusz** | **`concept`** — a csatlakozásnak nincs kódbeli helye egyik oldalon sem |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás és korábbi futás)`** + **`ORCHESTRATOR_VERIFIED`** (`ref/orchestrator-review-partial.md:74`: „Agent's claim CONFIRMED independently") |

**Érintett fájl (Relay, `55a899f`)**

* `core/cabinet/cicwasm.go:276-296` — a `CicWasmHost` négy metódusa, mindegyik **fix** op-stringgel:
  `Process → callGuest(ctx, "process", …)` (`:277`), `Get → "get"` (`:283`),
  `Init → "init"` (`:289`), `Notify → "notify"` (`:295`).
* `core/cabinet/service.go:18-24` — a `cicWasmHost` interfész ugyanez a négy + `Close`.
* `core/cabinet/service.go:229-243` — a production WASM-ág `switch strings.ToLower(step.FunctionName)`-e négy ággal; a `default` (`:241-242`):
  `execErr = fmt.Errorf("WASM module %q does not support operation %q", step.ComponentID, step.FunctionName)`.
* `core/cabinet/cicwasm.go:300` — `callGuest(ctx context.Context, op, authContextJson, inputJson string)`: a mechanizmus **tud** tetszőleges op-stringet, csak **nincs production hívó, amely ilyet adna át**.

**Érintett fájl (modul oldal, összevetésül)**
`module/abi.go:35-54` — a guest `switch op`-ja a nyolc `cic:provider` opra
(`describe, validate, observe, plan, execute, poll, invoke, destroy`), és a
`default` (`:52-53`) `marshalErr(CodeInput, "unknown op: "+op)`.
Az op-készlet normatív helye: `module/provider.go:46-49`; a deklarált felület:
`project.yaml:73-81`.

**Jelenlegi viselkedés**

A két szókészlet **nem fedi egymást egyetlen elemben sem.** Két kimenet lehetséges, mindkettő hibás:
1. ha egy workflow-step `FunctionName`-je `describe`/`plan`/… → a
   `service.go:242` elutasítja, a guest meghívása előtt;
2. ha a step `notify`/`process`/… → a guest a `module/abi.go:53`-on
   `unknown op: notify`-t ad vissza.

Megjegyzés, hogy ne legyen túlállítás: **az ABI-mechanika illeszkedik.** A
megkövetelt exportok (`Call`, `allocate`, `deallocate` — `cicwasm.go:249-254`),
a hatparaméteres hívás (`:334`), a `(size<<32)|ptr` csomagolás (`:343-345` vs
`module/abi.go:65-72`) és a `{data,error}` boríték (`:363-366` vs
`module/envelope.go:10-14`) **egyezik**. A rés kizárólag a **szókészlet**.

A nyolc műveletet eddig **nem a Relayen keresztül**, hanem közvetlen
teszt-harnesszel igazolták valós OCI-n
(`docs/design/manual-verification.md:24-26` kimondja: *„The real `module.wasm` /
wazero / ABI-dispatch path (`abi.go`) — this harness calls the Go handler
functions directly"*). → **`DOCUMENTED`**.

**Kívánt viselkedés**

A host tudjon **provider-ABI műveletet** hajtani egy guesten: a nyolc op-string
eljusson a guest `Call`-jáig, és az eredmény a `result<T, provider-error>`
diszkriminátorral együtt jusson vissza a hívóhoz.

**A konkrét mechanizmus, amely a négyet és a nyolcat összekapcsolja, NINCS
eldöntve.** Nem javaslok megoldást és nem is sorolok fel alternatívákat
döntésként; ez a relay tulajdonosának a terve. Amit a mérés hozzátesz: a
`callGuest` (`cicwasm.go:300`) már ma paraméterezett op-stringgel dolgozik,
tehát a rés a **hívó** oldalon van (`service.go:232-243` és a
`cicWasmHost` interfész `service.go:18-24`), nem a memória-ABI-ban.

**Negatív teszt**

1. Egy `cic:provider` ABI-t implementáló guest modul betöltve, egy
   `FunctionName: "describe"` step: **ma** a `service.go:242` hibája jön
   (`does not support operation "describe"`). A követelmény teljesülése után a
   modul `describe` válaszának kell megjönnie. A teszt **bukjon** a mai kódon.
2. Egy ismeretlen op (`"frobnicate"`) **maradjon** elutasított, és az
   elutasítás a hoston történjen, ne a guestben — a guest ne kapjon olyan
   op-stringet, amit a host nem ismer.
3. Egy olyan guest, amely a `cic:provider` op-készletből **csak egy részt**
   implementál, a nem implementált opra `unknown op`-ot ad: ez a host felé
   `provider-error`-ként jelenjen meg, ne transport-hibaként.

**Elfogadási feltétel**

A Relay saját tesztkészletében egy teszt, amely egy provider-ABI guestet a nyolc
op-stringgel végighajt, és mind a nyolcra a guest saját válaszát kapja; plusz a
(2) és (3) negatív eset. A döntés dokumentált helye megnevezve. **Amíg a
mechanizmus nincs eldöntve, ez a tétel `concept` marad**, és az `01b` szeletnek
külön döntés kell arról, hogy a Relay-integráció benne van-e a szeletben
(a teszt-harness útja megkerüli, ahogy a nyolc igazolt művelet is tette).

---

## R2 — Tartós CIC `uid` → provider OCID kötés (state binding)

| | |
|---|---|
| **Követelmény ID** | R2 |
| **Státusz** | **`concept`** a kötésre; a *persistence-mechanizmus* maga `implemented`, de nem erre |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás)`** + **`DOCUMENTED`** (a követelmény forrása a modul state-modellje) |

**A követelmény forrása (modul design, `DOCUMENTED`)**

`cic-module-oracle-cloud/docs/design/specs/state-model.md:58-69`:

```
correlate(intentObject) -> stateObject     # by stable CIC uid
```
> „The **CIC `uid`** is the logical identity (survives recreate). The
> **`provider_id`** is the identity of the current realization (changes on
> recreate: a new subnet OCID for the same `cic-subnet-prod`). **Never correlate
> by `provider_id`.**"

Tehát valahol **tárolni kell** a `uid → provider_id` (OCID) párt, különben a
korreláció nem végezhető el, és egy újralétrehozás után az intent elveszti a
kapcsolatát a realizációval.

**Érintett fájlok (Relay, `55a899f`) — amit olvastam**

| Fájl:sor | Mit találtam |
|---|---|
| `core/nexus/recorder/recorder.go:22-25` | `type StateRecorder interface { RecordState(ctx context.Context, expected types.ExpectedState, actual interface{}) (commitHash string, err error) }` — **létezik** egy állapot-snapshot perzisztáló, git-commit-alapú (`os/exec`, `crypto/sha256` importok `:3-19`) |
| `core/nexus/drift/drift.go:1-22` | a `drift` csomag a desired↔actual különbséget osztályozza, a feature-011 conformance modellre delegálva (`core/nexus/iac`); a csomagdoksi `:17` kifejezetten említi, hogy egy `provider_id` az observed state része, és **nem** drift |
| `core/nexus/iac/schema.go:13`, `:67`; `core/nexus/iac/conformance.go:21`; `core/nexus/drift/drift.go:17` | a **`provider_id` mind a négy előfordulása nem-teszt Go-ban KOMMENT**, nem kód. Mérés: `grep -rn 'provider_id' --include="*.go" <Relay> \| grep -v '_test\.go'` → 4 találat, mind `//` kommentsor |
| production bekötés | `core/nexus/iac` importálva: `cmd/relay/main.go:20`; `core/nexus/drift` importálva: `core/nexus/recorder/recorder.go:17` (és a `tools/statechain-demo/main.go:22` demóból). Tehát a conformance/drift primitív **production úton van**, nem scaffold |

**Jelenlegi viselkedés**

* `resource_id`, `provider_metadata`, `ResourceID`, `ProviderMetadata` a Relay
  nem-teszt Go kódjában: **0 találat mindegyikre.** (Mérés: `grep -rn '<minta>'
  --include="*.go" <Relay> | grep -v '_test\.go' | wc -l` → 0, 0, 0, 0.)
* `uid` mint identitás-mező a `core/` alatt nem-teszt Go-ban: **0 találat**
  (`grep -rn '"uid"\|\buid\b' --include="*.go" <Relay>/core | grep -v '_test\.go'`,
  az `uuid`/`guid` zajt kiszűrve → üres).
* Egyetlen `ocid1` előfordulás nem-teszt Go-ban: `tools/oci-sign-demo/main.go:39,66`
  — **demó-placeholderek** (`"ocid1.tenancy.oc1..demo/…"`), nem állapotkezelés.

**→ A Relay perzisztálja az állapot-snapshotot (git-commit-alapon), de a CIC
`uid` ↔ provider OCID kötést nem modellezi: nincs sem mezője, sem tárolója,
sem korrelációs kódja.**

Egy korlát, amit kimondok: a `recorder.go`-t a fejlécén és az interfészén túl
**nem olvastam végig**, és a `core/nexus/iac` 19 fájlját sem. Ezért azt
**nem** állítom, hogy a Relayben semmilyen identitás-kezelés nincs — azt
állítom, hogy a négy keresett szimbólum nem szerepel production kódban, és a
`provider_id` csak kommentben. A teljes `core/nexus` átolvasása:
**`NOT MEASURED`** (ami kellene: a 19+ fájl végigolvasása, vagy a relay
tulajdonosának megerősítése).

**Kívánt viselkedés**

Egy komponens, amely az `Execute(Create…)` után megkapott provider-azonosítót a
logikai CIC `uid`-hez kötve tartósan eltárolja, és az `Observe`/`Plan` ciklus
ebből olvassa a `binding.resource_id`-t — nem a hívó kézi beadásából. A tárolás
helye (Relay vs külön state-store) **nincs eldöntve**; a `state-model.md`
elvárása csak az, hogy a korreláció **sose** `provider_id` szerint történjen.

**Negatív teszt**

1. Egy `uid`-hez tartozó erőforrás törlése és újralétrehozása után az intent
   **ugyanazt** a `uid`-et korrelálja az **új** OCID-hez; a régi OCID ne
   eredményezzen találatot. (Ez az a szcenárió, amit a `state-model.md:67-68`
   nevesít.)
2. Két különböző `uid`, azonos `displayName`: a korreláció **ne** keverje
   össze őket — azaz ne névre korreláljon.
3. Egy olyan `Observe`, amelyhez nincs tárolt kötés: **explicit hiba vagy
   `unobserved`**, soha ne üres/`null` állapot, amit a hívó „nincs drift"-nek
   olvashat.

**Elfogadási feltétel**

A kötés olvasható és írható production úton, a három negatív teszt zöld, és a
`state-model.md` korrelációs szabálya (`uid`, nem `provider_id`) teszttel
kikényszerítve. **Előfeltétel: M1** — amíg az execution result nem adja vissza a
létrejött OCID-et, nincs mit eltárolni.

---

## R3 — A Forms production bekötése: a hiányzó hívási út

| | |
|---|---|
| **Követelmény ID** | R3 |
| **Státusz** | **`concept`** — a hívási út sem a Relayben, sem a modulban nem létezik |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás és korábbi futás)`** + **`ORCHESTRATOR_VERIFIED`** (`ref/orchestrator-review-partial.md:11,73`) |

**Érintett fájlok és a mérés**

| Irány | Mérés | Eredmény |
|---|---|---|
| Forms → modul | `grep -rn 'primitive-forms' --include='*.go' <modul>` | **0 találat** |
| Forms → modul (függőség) | `module/go.mod` teljes tartalma | egyetlen `require`: `github.com/tetratelabs/wazero v1.9.0` (`module/go.mod:5`). **Nincs Forms-függőség** |
| Forms → Relay | `grep -rn 'cic-primitive-forms\|primitive-forms\|CompileSchema' --include='*.go' <Relay>` | **0 találat mindháromra** |
| Forms → Relay (függőség) | `grep -c 'primitive-forms' <Relay>/go.mod` | **0** |
| hamis pozitív kizárva | `grep -rn 'forms\.' --include='*.go' <Relay>` | **1 találat**, és az az angol „forms" szó egy kommentben: `core/nexus/iac/compare.go:96` — *„whether two values have identical canonical-JSON **forms**"*. Nem Forms-hivatkozás |

**→ A Forms és a provider-modul között semelyik repóban nincs production hívási
lánc.** Ezt az orchestrátor függetlenül megerősítette
(`ref/orchestrator-review-partial.md:11`: „Module has no Forms reference in
`*.go` / `go.mod` at 3e38886 … Matches »zero Forms imports«"; `:73`: „Forms →
Relay: no Forms reference in Relay `*.go`/`go.mod`").

**Jelenlegi viselkedés**

A cél-adatfolyam (`cic-module-oracle-cloud/docs/design/forms-integration-direction.md:26-38`)
`Relay → Forms → kiterjesztett CIC-objektum → Oracle WASM modul` lánca
**egyetlen ponton sem létezik kódban**. A dokumentum maga is `concept`-nek
jelöli a modul oldalán (`:3`).

Két kemény korlát, ami a bekötés tervét kötelezően befolyásolja (mindkettő
**`AGENT_MEASURED (eszközfuttatás, korábbi futás)`**, és a licenc-rész
**`ORCHESTRATOR_VERIFIED`**):

1. **A Forms csak `config_surface`-t fordít.** `cic-primitive-forms/go/schema.go:138-140`:
   `if in.Surface != "config_surface" { return nil, binding(SurfaceUnsupported) }`.
   Tehát a cél-adatfolyam „Forms state validation" lépése **nem létezhet**
   ebben a formában. (A `forms-integration-direction.md:37` ezt már „NOT
   implemented"-ként jelöli.)
2. **A grammar-pin a Forms kódjában rögzített, egyetlen érték.**
   `cic-primitive-forms/go/schema.go:60-63` — `grammarProfiles` **egy** bejegyzése
   `"cic-primitives-73ae469-6a188078"`; minden más pin `GRAMMAR_PIN_UNKNOWN`.
   Egy production bekötésnek ezt a pint kell hordoznia, vagy a Forms oldalán
   kell új profil.

**Kívánt viselkedés**

Egy megnevezett, tesztelt production hívási lánc, amelyben a Forms a
`config_surface`-t a pinelt grammarral és a pinelt séma-digesttel validálja és
kiterjeszti, és a kiterjesztett, kanonikusan szerializált objektum a modul
`schemaPayload` borítékában (`module/provider.go:57-63`) jut a guesthez — a
`schema_hash` **a tényleges kanonikus bájtokon** ellenőrizve
(`forms-integration-direction.md:40`).

**Hol kell lennie — ez döntés, nem az én megállapításom.** A `direction` 1.5
pontja azt rögzíti, hogy a Forms motor **nem** kerül a WASM guestbe; a
TinyGo-mérés (`baseline.md` 5.2) azt mutatja, hogy *tudna* (fordul, +≈1,03 MB),
de ez a határ felmérése, nem javaslat a bevitelére.

**Negatív teszt**

1. **Rossz `schema_hash`:** a boríték hash-e nem a kanonikus bájtok hash-e →
   elutasítás, nem „best effort" feldolgozás. (A guest oldalán a kapocs már
   megvan: `module/provider.go:300 checkEnvelope`.)
2. **Nem támogatott grammar-pin:** egy `cic-primitives-…` pin, ami nincs a
   `grammarProfiles`-ban → `GRAMMAR_PIN_UNKNOWN`, nem néma elfogadás.
3. **`state_surface` átadása:** → `SURFACE_UNSUPPORTED`, és a hívó lánc
   **ne** próbálja a state-et a Forms-szal validálni.
4. **Nem támogatott YAML-konstrukció** a dokumentált részhalmazból (anchor,
   float-nak látszó skalár, duplikált kulcs) → a megfelelő explicit hibakód,
   soha nem újraértelmezés.
5. **Nem értékelt `contract`:** egy séma-szerződéssel ellentétes, de formailag
   érvényes érték (pl. `cidr_block: "999.0.0.0/16"`) **átmegy** a Forms-on —
   a tesztnek ezt ki kell mondania, hogy a lánc ne higgye validáltnak.
   Bizonyíték, hogy ez a mai viselkedés: `unevaluated_contracts: ["$.cidr_block"]`
   a NetworkSpace fordításának kimenetében, és
   `cic-primitive-forms/docs/P1-SUPPORTED-SUBSET.md:352`.

**Elfogadási feltétel**

A lánc minden lépéséhez production hívó `fájl:sor` (Q8), az öt negatív eset
zöld, és a Forms-függőség a `baseline.md` 5.1-ben felmért módok egyikén,
**commitra pinelve** rögzítve. A pinelés és a licenc kérdése
(`baseline.md` 8.) **tulajdonosi döntés**; itt nem döntöm el.

---

# 2. Modul-oldali követelmények (nem Relay-igények)

Ezek a `cic-module-oracle-cloud`-ban javíthatók, Relay-változás és új primitív
nélkül. **Kódot nem írtam és nem módosítottam.**

## M1 — A létrejött `resource_id` átadása az execution result-on keresztül

| | |
|---|---|
| **Követelmény ID** | M1 |
| **Státusz** | **`concept`** — a mező dokumentált, kódban nincs |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás)`** a kód-oldalra; **`DOCUMENTED`** a spec-oldalra; **`ORCHESTRATOR_VERIFIED`** (`ref/orchestrator-review-partial.md:80,83`) |

**Érintett fájl:sor**

*A dokumentált elvárás* — `docs/design/specs/provider-abi.md:96-99`:

```yaml
execution-result:
  status: accepted | succeeded | failed
  job: { provider_id: ocid1.workrequest..., state: ACCEPTED, poll_after: 5s }  # if async
  provider_metadata: { opc_request_id, etag, resource_id }
```

(A szakasz fejléce `:67` — **„Request/response shapes (informative)"**, tehát a
spec maga sem normatívnak jelöli ezt a formát. Ezt a pontosítást fontosnak
tartom: a rés „kód vs informatív design", nem „kód vs normatív szerződés".)

*A tényleges kód* — `module/provider.go:920-929`:

```go
type executionStep struct {
	Operation     string `json:"operation"`
	HTTPStatus    int    `json:"http_status,omitempty"`
	Etag          string `json:"etag,omitempty"`
	OpcRequestID  string `json:"opc_request_id,omitempty"`
	WorkRequestID string `json:"work_request_id,omitempty"`
	Error         string `json:"error,omitempty"`
	ErrorClass    string `json:"error_class,omitempty"`
	ProviderCode  string `json:"provider_code,omitempty"`
}
```

**Nincs `resource_id`, és nincs a válasz-törzs.** Ugyanígy
`executionResult` (`:915-918`): csak `Status` + `Steps`.

*Hol veszik el* — `module/provider.go:1013-1034 executeOne`: a `respBody`-t a
siker-ágon **nem olvassa el**. A `:1022-1027` csak a status-t és három fejlécet
vesz ki (`etag`, `opc-request-id`, `opc-work-request-id`); a `respBody`-hoz
**egyetlen** hozzáférés van, a `:1028-1032` hibaágon
(`ociError(status, respBody)`). A 2xx törzs — amelyben az OCI a létrehozott
`Vcn` objektumot `id`-vel visszaadja — **eldobásra kerül**.

*A `pollResult` sem pótolja* — `module/provider.go:725-730`: `WorkStatus`,
`PercentComplete`, `Terminal`, `HTTPStatus`. Nincs `resource_id`.

*Pontosítás, ami nem triviális.* Az **`Observe`** oldalán a
`provider_metadata.resource_id` **létezik** (`module/provider.go:812`,
`provMeta` `:815-820`) — de a kitöltése `req.Binding.ResourceID`
(`:866`), azaz **a hívó saját bemenetének visszaadása**, nem a provider
válaszából kiolvasott azonosító. Tehát a `provider-abi.md:79` formailag
teljesül, tartalmilag viszont nem új információ.

**Jelenlegi viselkedés**

Egy `Execute(CreateVcn)` után a hívó **nem kapja meg** a létrejött erőforrás
OCID-jét, miközben a következő `Observe`/`Destroy`/`Invoke` megköveteli a
`binding.resource_id`-t (`module/provider.go:905`). A dokumentált kerülőút
kézi: `docs/design/manual-verification.md:204-208` — *„after a `Create`, find
the new resource's OCID with the `oci` CLI … to feed into the next
Observe/Update/Destroy call"*. Ez **operátori lépés, nem CIC-mechanizmus**.

Downstream sem pótolja: a Relayben `resource_id`/`provider_metadata` nem-teszt
Go kódban 0 találat (R2 mérése).

**Kívánt viselkedés**

Az execution result hordozza a létrejött erőforrás provider-azonosítóját, a
`provider-abi.md:99` szándéka szerint, úgy, hogy a `create → observe` ciklus
**kézi beavatkozás nélkül** záruljon. A pontos alak (step-szintű vagy
result-szintű `provider_metadata`, és hogy a válasz-törzs hash-e vagy maga a
törzs jelenjen-e meg az evidence-ben) **ABI/szerződés-döntés — nem döntöm el.**
Amit a mérés leszögez: a javítás a modulon belül elvégezhető, **új primitív és
sémaváltozás nélkül**.

**Negatív teszt**

1. **A blokkoló eset:** `Execute(CreateVcn)` mockolt 200-as OCI-válasszal,
   amelynek törzse `{"id":"ocid1.vcn.oc1..test", …}` → az eredményben szerepelnie
   kell az OCID-nek. **Ez a teszt a mai kódon bukjon.**
2. **Ne találjon ki azonosítót:** olyan 200-as válasz, amelynek törzsében
   **nincs** `id` → a mező legyen üres/hiányzó, **ne** a binding `resource_id`-je,
   és **ne** üres string, amit a hívó érvényes OCID-nek olvashat.
3. **Aszinkron eset:** 202 + `opc-work-request-id`, OCID nélküli törzs → a
   státusz `accepted` maradjon (a meglévő viselkedés, `provider.go:1025-1027`),
   és az OCID hiánya **ne** legyen sikernek jelölve.
4. **Hibaág változatlan:** `>= 400`-on az `ociError` útvonal és a
   `provider_code` megőrzése ne sérüljön (regresszió-védelem a
   `TestDestroyNotFoundKeepsProviderCode`-dal igazolt javításra).

**Elfogadási feltétel**

A négy teszt zöld, az (1) bizonyítottan bukik a változás előtti kódon
(seeded-proof, Q5 szellemében), és a `provider-abi.md` érintett szakasza vagy
normatívvá válik, vagy kimondja, hogy informatív és a kód a szerződés.
**Előfeltétele R2-nek.**

---

## M2 — Javasolt `compartment_id` binding-kiterjesztés

| | |
|---|---|
| **Követelmény ID** | M2 |
| **Státusz** | **`PROPOSED / OWNER DECISION REQUIRED`** — háromszintű státusza a kódra: **`concept`** |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás)`** + **`DOCUMENTED`** + **`ORCHESTRATOR_VERIFIED`** (`ref/orchestrator-review-partial.md:34-39,86-88`) |

> **Ez nem elfogadott irány és nem döntés.** A `compartmentId` eredete
> (szerzett intent / binding / végrehajtási kontextus) **nyitott kérdés,
> tulajdonosi döntésre vár.** Az alábbi a mért tényállás és a döntéshez
> szükséges anyag — nem ajánlás a megvalósításra.

**A tényállás három, egymásnak feszülő helyen**

| Hely | Mit mond | Osztály |
|---|---|---|
| `docs/design/specs/provider-abi.md:73` | `binding: { provider: oracle-cloud, region: eu-frankfurt-1, compartment_id: ocid1.compartment... }` — **a modul saját design-dokumentuma a BINDINGbe teszi** (a szakasz `:67` szerint „informative") | **`DOCUMENTED`** |
| `module/provider.go:901-907` (`execBinding`) | `Host`, `BasePath`, `KeyID`, `ResourceID`, `Revision` — **nincs `compartment_id`**. A doc-komment `:900`: *„Not secret; supplied with the intent."* | **`AGENT_MEASURED (kódolvasás, folytatás)`** |
| `module/schemas/core/vcn.json` | `compartmentId` **kötelező** (`required: ["compartmentId"]`) és `x-cic-policy: action-managed`, `x-cic-action: ChangeVcnCompartmentDetails` | **`AGENT_MEASURED (eszközfuttatás, korábbi futás)`**; a 13/19/`required` számokat **`ORCHESTRATOR_VERIFIED`** (`ref/…:10`) |
| `cic-schema-registry@6db77d4` NetworkSpace `binding_surface.addresses[0].key_fields` | `backend` (enum `[cloud]`), `provider`, `location`, `id` — **nincs compartment, nincs tenancy** | **`ORCHESTRATOR_VERIFIED`** (`ref/…:34`) |
| Forms-korpusz | egy `compartment_id`-t tartalmazó NetworkSpace intent → **`UNKNOWN_FIELD`** (`testdata/p1/real-schemas.json`, `undeclared-fields-are-reported` eset) | **`AGENT_MEASURED (eszközfuttatás, korábbi futás)`** |

**Jelenlegi viselkedés**

A `compartmentId`-nek **nincs otthona** sem az intent-sémában, sem a bindingban.
A `create` ma csak úgy működik, hogy a hívó a `config.data`-ban már
**OCI-nevű** configot ad át, benne a `compartmentId`-vel — a `renderBody`
(`module/provider.go:1092`) ezt rendereli. Azaz a mai működés a hívóra bízza,
és semmi nem kényszeríti ki.

Egy pontosítás, amit az orchestrátor mérése tisztázott, és amit átveszek:
a `key_id` belsejében lévő tenancy-OCID **nem** általános compartment-OCID
(csak a root compartmentre egyenlő) — `ref/orchestrator-review-partial.md:37`.
Tehát a binding **ma meglévő** adataiból a compartment nem származtatható.

**Kívánt viselkedés — NEM eldöntve**

A döntés tárgya: a `compartmentId` **szerzett intent** (sémamező), **binding**
(végrehajtási koordináta), vagy **adapter-capability konfiguráció**. A három
út következményei eltérnek, és ezt a döntéshez rögzítem:

| Út | Következmény |
|---|---|
| (a) `execBinding` mező | modul-ABI változás, séma érintetlen; a Forms-ot nem érinti (a Forms csak `config_surface`-t validál) |
| (b) szerzett intent-mező | `cic-schema-registry` sémaváltozás + új aláírt verzió; a Forms validálni fogja |
| (c) adapter-capability | a NetworkSpace `binding_surface.adapter_capabilities.known_adapters` ma **szándékosan üres** (`network-space.yaml:387-391`), tehát ez a mechanizmus még nem létezik |

A tulajdonos rögzített szabálya (`ref/orchestrator-review-partial.md:67`):
*„no schema change just to make OCI create work; each field must first be shown
to be authored intent and not execution context / binding."* Ezt tartom: **nem
javaslom a sémaváltozást**, és nem minősítem a `compartmentId`-t szerzett
intentnek.

Egy korrekciót átveszek az orchestrátortól, mert a saját
`contract-mapping.md`-m pontatlanabb volt: a „9 nem kifejezhető mező" szám
**különböző eredetű mezőket vont össze** (`ref/…:38`). Ami **mért**: ez a 9
mező **nem fejezhető ki a NetworkSpace `config_surface`-ében**. Ami **nem
igazolt**: hogy mindegyik szerződés-hiba lenne. A `contract-mapping.md`
változatlan (immutable input), a pontosítás itt és a `claim-evidence.md`-ben
él.

**Negatív teszt (bármelyik úton)**

1. A `compartmentId` **hiánya** `Execute(CreateVcn)`-nél **explicit hiba**
   legyen, ne 400-as OCI-válasz után derüljön ki. (Ma: a `Validate` a
   `required`-et ellenőrzi — `module/provider.go:239 conformIntent` —, de a
   `create` útja a `Plan`-t megkerüli, tehát a `Validate` nem feltétlenül fut.)
2. **Ne legyen néma default:** sem a tenancy-OCID, sem a root compartment ne
   lépjen be hallgatólagosan a `key_id`-ből.
3. Ha a döntés (b): egy `compartment_id`-t tartalmazó intent **ne** adjon
   `UNKNOWN_FIELD`-et; ha a döntés (a): a `config_surface` **maradjon**
   `UNKNOWN_FIELD`-es rá, és a bindingból jöjjön.

**Elfogadási feltétel**

**Először a tulajdonosi döntés, utána kód.** Addig ez a tétel nyitott
kérdésként marad; semmilyen részleges megvalósítás nem kezdhető el, mert a
három út egymást kizárja.

---

## M3 — A production `Observe` normalizálási rése és a kötelező negatív teszt

| | |
|---|---|
| **Követelmény ID** | M3 |
| **Státusz** | **`scaffold`** a védelem helyére (`normalizeObserved`: kódban van, production hívó nélkül); a production `Observe` útján a garancia **egyetlen őrfeltételen** áll |
| **Bizonyíték-osztály** | **`AGENT_MEASURED (kódolvasás, folytatás és korábbi futás)`** a szerkezetre; **`ORCHESTRATOR_VERIFIED`** a túlélő hibára (`ref/orchestrator-review-partial.md:105`) |

**A production út, `fájl:sor`-ral**

`module/provider.go:827 Observe` → `:860 effectiveConfig(c, state)` →
`:861 applyDerivations(req.Kind, state, eff)` → `module/correspondence.go:61`.

A teljes védelem, amin a „hiányzó megfigyelésből nem lesz `false`" garancia ma
áll — `module/correspondence.go:62-66`:

```go
for _, d := range correspondences()[kind] {
	sv, ok := state[d.From]
	if !ok {
		continue
	}
```

Ez **egyetlen, teszteletlen őrfeltétel** a production úton.

**A bekötetlen, erős védelem** — `module/observed.go:68 normalizeObserved`:
négyértékű coverage (`observed|absent|unobserved|unknown`, `:36-41`), és a
`:132-136` szűrő, amely a nem-`observed` értéket **törli** az
`effective_config`-ból. Production hívója: **0**
(`grep -rn "\bnormalizeObserved\b" --include="*.go" . | grep -v '_test\.go'` →
csak a definíció és a saját kommentje). A fájl fejléce ezt ki is mondja
(`observed.go:23-26`): *„NOT wired into Observe … Wiring it is a separate,
deliberate ABI step."* Az orchestrátor ezt függetlenül megerősítette
(`ref/…:104`).

**A bizonyíték, hogy a rés valós (NEM az én mérésem)**

`ref/orchestrator-review-partial.md:105` — az orchestrátor telepített hibákkal
mérte a tesztkészlet erejét egy eldobható másolatban:

> „**M2 remove the source-presence check in `applyDerivations` (fabricates
> `isIpv6Enabled=false` from an absent source) → SURVIVES, all tests green.**
> Reason: the »partial read never fabricates« test goes through
> `normalizeObserved`, whose filter deletes the value afterwards; the production
> `Observe` path has no such filter and no test of the absent-source case. The
> guarantee that holds in production today rests on one unguarded
> `if !ok { continue }`."

**Osztály: `ORCHESTRATOR_VERIFIED`. Ezt a mérést nem én végeztem**, és nem
adom ki a sajátomnak. Az előző futásban én a `normalizeObserved` **bekötetlen**
állapotát mértem (`AGENT_MEASURED`), a telepített hiba túlélését **nem**.

**Jelenlegi viselkedés**

Ha az OCI-válaszból hiányzik az `ipv6CidrBlocks`, a production `Observe`
`effective_config`-jában az `isIpv6Enabled` **nem jelenik meg** — de ezt
semmilyen teszt nem hajtja meg a production úton, és a `normalizeObserved`
coverage-szűrője nincs bekötve. Az `Observe` kimenete
(`module/provider.go:809 observation`: `State`, `EffectiveConfig`,
`ProviderMetadata`) **egyáltalán nem hordoz coverage-et**, tehát a hívó nem
tudja megkülönböztetni a „nem volt megfigyelve" és a „nincs beállítva"
eseteket.

**Kívánt viselkedés**

A `forms-integration-direction.md:54` kimondott elve érvényesüljön a production
úton: *„A missing read-back capability is not a `null`. Provider normalization
must not reconstruct the authored intent by guesswork."*

**A kötelező 01b blokkoló teszt** (a tulajdonos szövege szerint,
`ref/orchestrator-review-partial.md:128-129`):

> „If `ipv6CidrBlocks` is absent from the OCI response, the CIC state must not
> contain an `isIpv6Enabled=false` value derived from it. A missing observation
> must not become an observed `false`."

**A teszt a production `Observe` utat hajtsa meg**
(`provider.go:827 → :860 → :861`), **ne csak** a `normalizeObserved`-ot.

**Negatív teszt (ez a követelmény magja)**

1. **A blokkoló eset:** mockolt `GetVcn` 200-as válasz, amelyből az
   `ipv6CidrBlocks` **hiányzik**, `Observe`-on át → az `effective_config`-ban
   **ne legyen** `isIpv6Enabled` kulcs, és semmiképp ne `false`.
   **A tesztnek bukania kell**, ha az őrfeltételt
   (`correspondence.go:63-65`) eltávolítják — ez a seeded-proof, és pontosan
   az a hiba, amely ma észrevétlen marad.
2. **`null` ≠ hiányzó:** `ipv6CidrBlocks: null` → az eredmény ne legyen
   `isIpv6Enabled: false`; a `null`-t a `jsonNonEmpty`
   (`correspondence.go:80-87`) ma `false`-ként kezeli, **de csak akkor, ha a
   kulcs jelen van** — a két eset elválasztása tesztelendő.
3. **Üres lista:** `ipv6CidrBlocks: []` → `isIpv6Enabled: false` **helyes**
   (a mező megfigyelve, a válasz érdemi). Ez a pozitív kontroll, amely
   megakadályozza, hogy a javítás az üres listát is „nem megfigyelt"-nek
   minősítse.
4. **Transport-hiba / 404:** nincs válasz, illetve 404
   `NotAuthorizedOrNotFound` → **egyetlen** derivált érték se jelenjen meg.
   (A `normalizeObserved` ezt már helyesen teszi — `observed.go:84-89` —, de a
   production `Observe` a 404-et `errResult`-tal zárja: a tesztnek ezt a
   különbséget ki kell mondania.)
5. **Nem-objektum törzs:** `Observe` ma `classProvider` hibát ad
   (`provider.go:855-857`); maradjon így, ne részleges `effective_config`.

**Elfogadási feltétel**

Mind az öt eset zöld, az (1) **bizonyítottan bukik** az őrfeltétel
eltávolításával (telepített hiba, dokumentált kimenettel), és a döntés
rögzítve arról, hogy a `normalizeObserved` coverage-e **bekötésre kerül-e** az
`Observe` ABI-kimenetébe. Ez utóbbi **ABI-változás** (`observation` új mezője),
tehát **tulajdonosi döntés** — nem döntöm el. Amíg nincs bekötve, az
`Observe` coverage-mentessége **szerződéses tény**, amit az `01b`-nek ki kell
mondania, nem feltételeznie.

---

# 3. Nyitva maradt tételek és a köztük lévő sorrend

| ID | Tétel | Oldal | Státusz | Mi blokkolja |
|---|---|---|---|---|
| R1 | op-szókészlet 4 vs 8 | Relay | `concept` | a csatlakozási mechanizmus **nincs eldöntve**; az `01b`-nek döntés kell, hogy a Relay-integráció a szeletben van-e |
| R2 | `uid` → OCID state binding | Relay (hely nem eldöntve) | `concept` | **M1** (nincs mit tárolni, amíg az execution result nem adja vissza az OCID-et) |
| R3 | Forms production bekötés | mindkettő | `concept` | a függőség-mechanizmus és a licenc **tulajdonosi döntés** (`baseline.md` 8.) |
| M1 | létrejött `resource_id` az execution resultban | modul | `concept` | ABI/szerződés-döntés az alakról; a javítás modulon belüli |
| M2 | `compartment_id` eredete | modul vagy registry | **`PROPOSED / OWNER DECISION REQUIRED`** | **tulajdonosi döntés**: szerzett intent vs binding vs adapter-capability; a három út kizárja egymást |
| M3 | production `Observe` normalizálás + blokkoló teszt | modul | `scaffold` | semmi — **ez a legkisebb, azonnal kezdhető tétel**, és a tulajdonos 01b blokkolónak jelölte |

**A függőségi sorrend, amit a mérés megenged:** M3 (nem blokkolt) → M1 → R2.
Az M2 és az R1 **döntésre vár**, nem munkára. Az R3 az M2 döntésétől függ
(a `compartment_id` útja meghatározza, hogy a Forms validál-e rá).

# 4. Mit nem állítok ebben a dokumentumban

Hogy bármelyik Relay-tételre megoldást javasolnék (az R1 mechanizmusa, az R2
tárolási helye, az R3 bekötési pontja mind a tulajdonosé). Hogy a
`compartmentId` szerzett intent vagy binding (nyitott). Hogy az orchestrátor
telepített-hiba-mérései az én méréseim (nem azok: `ORCHESTRATOR_VERIFIED`).
Hogy a Relay `core/nexus` csomagjaiban nincs identitás-kezelés (csak azt, hogy a
négy keresett szimbólum nem szerepel production kódban, és a `provider_id`
kizárólag kommentben — a 19+ fájl teljes átolvasása `NOT MEASURED`). Hogy a
`provider-abi.md` érintett szakaszai normatívak (a `:67` szerint informatívak).
Bármit a valós OCI-ról, amit a `manual-verification.md` nem rögzít.
