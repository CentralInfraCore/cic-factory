# forms-oracle-vcn-hardening-01b-a — az Oracle-modul végrehajtásának és megfigyelésének megerősítése: a production Observe negatív tesztje (S4) és a létrehozott OCID visszaadása (S3)

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, nem te figyeled a futását, és nincs mire várnod: a munka, amit az alábbiak leírnak, **a te dolgod, most**. Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a `workdir` operátora, aki a specet írta és az outputot reviewolja; a tulajdonos hozza a döntéseket). Ne beszélj az ő nevében, és ne írj állapotjelentést a jobról. Ha egy döntés a tulajdonosé (lásd „Határjelzés"), ne dönts helyette: állj meg ott, őrizd meg az addigi bizonyítékot, és írd le, mi kell a folytatáshoz.

## Reasoning mód

**implementation, két szűk szeletre** a `cic-module-oracle-cloud` modulban, egyetlen resource-ra (**VCN**), **mockolt OCI-válaszokkal**, **Forms és Relay nélkül**. A két szelet független (különböző függvényeket érint), de mindkettő ugyanazt a mérési infrastruktúrát igényli (lásd „Mérési infrastruktúra"). Ami nem fér a szeletbe, nem kerül bele, és a jelentésben nevesítve marad.

Ez az egyik a háromból, amelyekre az eredeti 01b tervezet szétbontásra került (két külön szakmai review alapján): **ez a job** (S4+S3), egy későbbi **leképezési job** (NetworkSpace → OCI VCN, golden vektorokkal) és egy **binding-job** (`compartmentId`, a tulajdonosi döntés után). **A leképezés (S1/S5), a `compartmentId` binding (S2), a Forms és a Relay NEM része ennek a jobnak.**

## Kontextus — az elfogadott alap

Az `01a` baseline-felmérés lezárult (**CONDITIONAL GO — partial baseline accepted**). Olvasd el **teljesen, mielőtt bármihez nyúlsz** (a `cic-factory` `main` ágán, `jobs/forms-oracle-provider-integration-01a/`): `review.md`, `ref/final-review.md`, `output/baseline.md`, `output/contract-mapping.md`; a modul `devel` ágán: `docs/design/forms-integration-direction.md`, `docs/design/specs/provider-abi.md`, `docs/design/specs/state-model.md`.

**Az 01a `NOT INDEPENDENTLY VERIFIED` (NIV) állításait nem veheted át tényként** (modul sorlefedettség 82,7% vs 82,9%, tesztszám 55 vs 26, mutáció 159/217, `govulncheck`, Q3/Q6/Q9); a saját méréseid az irányadók. Az 01a `relay-requirements.md` hivatkozásai közül 9 többértelmű, 7 nem feloldható: a hivatkozott sort **a forrásban ellenőrizd**, mielőtt rá támaszkodsz.

**A bizonyított kiindulás** (mindet ellenőrizd újra a kódban, a `devel` HEAD-jén; jegyezd fel a HEAD commitot — várhatóan a `04c2482` vagy újabb):
1. **S4 — ez TESZT-hiány, nem production-hiba.** A production `Observe` (`provider.go:827`, a `:860-861` sorokban `effectiveConfig` + `applyDerivations`) már ma kihagyja az `isIpv6Enabled`-et, ha az `ipv6CidrBlocks` hiányzik, mert az `applyDerivations` forrás-jelenlét őrfeltétele (`correspondence.go`: `sv, ok := state[d.From]; if !ok { continue }`) megvan. A hiba az, hogy **egyetlen teszt sem védi ezt a production útvonalon**: az eldobható másolatban az őrfeltétel törlése a modul meglévő teljes tesztkészletét túléli, mert a „részleges olvasás nem gyárt értéket" teszt a `normalizeObserved`-en át fut, amelynek szűrője utólag törli az értéket, a `normalizeObserved`-nek pedig nincs production hívója.
2. **S3 — a létrehozott erőforrás azonosítója nem jut el az eredményig.** Az `Execute` eredménye `{status, steps[]}`; az `executionStep` (`provider.go`, `executeOne` ~:1013) nem hordoz `resource_id`-t, a válasz törzséből nem olvas ki semmit. A `provider-abi.md` (~:96-103) **tájékoztató (informative)** alakja `provider_metadata.resource_id`-t említ, de a kód már ma más alakot használ (`steps[]`), és a valós fogyasztók (`docs/design/manual-verification.md`, `module/manual_real_oci_test.go`) a `steps[]`-t olvassák: a dokumentum **nem kötelező szerződés**, az eltérést jelentsd, ne „előírásként" kezeld.
3. A `Plan` üres `observed`-et szándékosan elutasít (`TestPlanRejectsEmptyObserved`): ezt **nem lazítod**.

## Boot sequence — a KB használata és a határai

1. **`mcp__cic-graph__kb_status`**: rögzítsd a build idejét, a forrás-commitokat, a `stale` és `sources_behind_upstream` mezőt. Ha nem elérhető: `NOT MEASURED`, és folytasd a kódolvasással.
2. `search_nodes` az `axioms`, `symbols`, `contract`, `limits` kifejezésekre (az eredményt akkor is rögzítsd, ha üres), majd `search_query` a modul ABI-jára és state-modelljére.
3. A kb_focus azonosítókat **fájlútvonal alapján ellenőrizd, mielőtt használod** (`get_chunk`, `file_path`): `c7529` → `.../docs/design/architecture.md`; `c7616` → `.../docs/design/specs/state-model.md`; `c7487` → `.../docs/contracts/en/wasm-abi.md`; `c7668` → a `module/contracts.go` (a KB `.yaml` kiterjesztéssel indexeli); `c7675` → a `module/correspondence.go`; `c7550` → `.../docs/design/primitives-alignment.md`. Az azonosítók nem stabilak: ha a `file_path` nem egyezik, ne használd.
4. **A KB határai:** 2026-10-16-i állapot (modul `5d0a327`, Relay `55a899f`), a #33–#35 előtti; **tájékozódás, nem bizonyíték**: kódállításhoz a forrást olvasd.
5. Minden KB-ból vett állítás a `claim-evidence.md`-ben külön jelölést kap: `Forrás: KB c#### (file_path)`.

## Forrás — konkrét helyek

Klónozd a workspace-be a `cic-module-oracle-cloud`-ot (**`devel`**). A **CIC-Relay READ-ONLY**: a `${CIC_RELAY_PATH}` alatti forrást csak olvasod (a végrehajtási eredmény fogyasztóját keresd: ma nincs), soha nem szerkeszted. **Oracle modul — olvasd:** `module/provider.go`, `correspondence.go`, `correspondence/vcn.json`, `observed.go`, `abi.go`, `envelope.go`, `contracts.go`, `schemas/core/vcn.json`, `provider_test.go` (különösen `TestObserve`, `TestExecuteAsyncAndBasePath`), `observed_test.go`, `module_loadtest_test.go`, `abi_negative_test.go`, `testdata/vcn-v1/`, `manual_real_oci_test.go`, `docs/design/manual-verification.md`, `docs/design/specs/provider-abi.md`.

## Státusz-definíciók és az ellenőrzési módszerük

Háromszintű státusz minden állításhoz, **módszerrel bizonyítva**:
- **implemented** — production kódban hívódik **és** teszt fedi. Bizonyítás: a hívási lánc ellenőrzése a production kódban: `grep -rn "<Szimbólum>" --include="*.go" | grep -v "_test.go"` — legalább egy production hívó **fájl:sor megadva**, és a láncot a `Call` dispatcherig (`module/abi.go`) vissza kell követni; 0 találat `_test.go` nélkül → scaffold. A guest buildre a `deadcode` nem alkalmazható (cgo).
- **scaffold** — kódban van, de production hívója nincs, vagy feltétel mögött él (a feltétel fájl:sor).
- **concept** — csak dokumentált.
Ha a státuszt nem tudod fájl-szinten alátámasztani, ne mondd ki tényként.

## Tiltott rövidítések — ezek NEM bizonyítékok

- ❌ „a fájl létezik" / „a teszt zöld" / „zöld CI" ≠ implemented · ❌ exit code 0 ≠ sikeres mérés (olvasd a kimenetet) · ❌ százalék a nevező, a kizárások és a parancs nélkül.
- ❌ **Olyan teszt, amely nem tud elbukni.** Minden új tesztről mérd meg bevetett hibával, hogy elbukik-e.
- ❌ Teszt, amely az új utat **megkerülő segédfüggvényt** hajtja meg a production útvonal helyett (az `normalizeObserved` pont ez volt).
- ❌ A production `Observe` vagy az `Execute` viselkedésének **megváltoztatása a teszt kedvéért**; ez a job védő teszteket és egy additív mezőt ad, nem újratervez.

## Feladat — két szelet; S4 először, utána S3

### S4 — a production `Observe` negatív tesztje (**csak teszt**)

**A production `Observe`-ot NEM módosítod.** A `normalizeObserved` bekötése az `Observe`-ba **külön tulajdonosi döntés** (az `effective_config` tartalmát módosítaná: a rossz típusú vagy hiányzó mezőket kiszűrné); ebben a jobban nem tehető meg. A kötelező szabály: *ha az OCI-válaszban hiányzik az `ipv6CidrBlocks`, a CIC state nem tartalmazhat abból levezetett `isIpv6Enabled=false` értéket; a hiányzó megfigyelés nem válhat megfigyelt `false` értékké.*

A teszt **közvetlenül a production `Observe` függvényt** hajtja meg (mockolt GET-tel), **egy táblában, pozitív kontrollokkal** — mert a hiányzó, a `null`, az üres lista és az explicit `false` négy külön állapot, és egy „javítás", amely az `isIpv6Enabled`-et minden `false` esetben kihagyná, átmenne a hiányzó-esetes teszten, miközben elveszítené a valódi „IPv6 letiltva" állapotot:
| a mock válasz `ipv6CidrBlocks` mezője | elvárt `effective_config.isIpv6Enabled` |
|---|---|
| hiányzik a kulcs | **nincs a kimenetben** (nem `false`) |
| `[]` (jelen, üres) | `false` (ez megfigyelt állapot) |
| nem üres lista | `true` |
| `null` | az **aktuális viselkedést** rögzítsd (mérd meg, ne feltételezd), és jelöld, ha ez eltér a hiányzó esettől |
| bármelyik esetben | a `state` objektum változatlanul az OCI-válasz mezőit adja |

**Bizonyítás bevetett hibával** (eldobható másolatban): töröld az `applyDerivations` forrás-jelenlét őrfeltételét; a teszt legyen **PIROS** a mutánson és **ZÖLD** az eredeti kódon (mindkét kimenetet idézd). Mivel a production kód már helyes, **nincs „javítás" lépés**: a RED→GREEN a mutáns és az eredeti között van; ne találj ki production-módosítást.

A jelentésben nevezd meg a **Plan-veszélyt** (módosítás nélkül): az `isIpv6Enabled` `x-cic-policy: input-only`, a `policyOp` ezt `replace`-re képezi, a `Plan` a `valueEqual(desired, observed[name])`-et hasonlítja — egy részleges olvasás és `isIpv6Enabled=false` intent esetén a `Plan` `DeleteVcn`+`CreateVcn`-t tervez; ezt a viselkedést a teszt **nem változtatja**, csak leírja.

### S3 — a létrehozott OCID megőrzése az `Execute` eredményében

**Hely és alak (a szerződés additív bővítése, kötelezően így):** a `resource_id` az `executionStep`-en él (`steps[i].resource_id`, `json:"resource_id,omitempty"`), **csak `create` szerepű lépésnél**, a mockolt create-válasz `id` mezőjéből. **A nem-create lépések (update, action, delete) és azok eredményei bájt-azonosak maradnak** a változtatás előtt és után (bizonyítsd: a meglévő tesztek változatlanul zöldek **és** egy előtte/utána bájtazonossági állítás egy nem-create eredményre). A top-level `provider_metadata` alak **nem választható** ebben a jobban: ha úgy látod, hogy a per-step hely nem tartható, az **határjelzés** (tulajdonosi döntés), nem saját döntés.

**Hibacsatorna:** az `Execute` hibái ma `result.status=failed` + `step.error`/`step.error_class`, nem `errResult`; az új hibák **ugyanezt** a csatornát használják. Kötelező negatív esetek, mindegyik `failed` eredmény, **soha nem üres vagy kitalált `resource_id`**: 2xx create-válasz `id` nélkül; nem JSON törzs; `id`, amely nem OCID-alakú (az alak: `ocid1.vcn.` előtag + nem üres folytatás — a meglévő fixture-ök `ocid1.vcn..z` és `ocid1.vcn.oc1..xyz` alakot használnak, ezeknek át kell menniük); OCI 4xx/5xx (a meglévő viselkedés változatlan). **A hibaüzenet mondja ki, hogy a VCN a 2xx miatt létrejött** („2xx, created, id unknown"): egy vak újrapróbálás duplikátumot hozna létre. A „2xx id nélkül hiba" szabály **kizárólag a `create` szerepre vonatkozik**; a meglévő tesztek `{}` vagy üres törzset adnak 2xx-re update/action esetén (`TestExecuteAsyncAndBasePath`, a load-teszt `TestHostLoadExecute`) — ezek nem törhetnek.

A create kérés **nem hordoz `resource_id`-t** (az útvonala `/vcns`): a visszaadott azonosító **kizárólag a válasz `id`-jéből** jöhet, **soha nem a kérés `binding.resource_id`-jából**. Az aszinkron eset (`202` + `work_request_id`) a valós OCI-n a `CreateVcn`-re nem fordul elő (a create szinkron, `manual-verification.md`); a mockolt aszinkron válaszra írt teszt **„mock-only"** jelölést kap, és a `work_request_id` viselkedése változatlan. A fogyasztók ellenőrzése: a Relay-ben ma nincs az eredményt fogyasztó kód (`grep` a `*.go` fájlokban: `provider_metadata`, `work_request_id`, `resource_id`); ezt idézd.

**Kompatibilitás (kötelező ellenőrzések):** `go vet -tags manual_real_oci ./...` (csak fordítás: a `manual_real_oci_test.go` a `steps[]`-t olvassa); a `provider-abi.md` eltérésének **jelentése** (a dokumentum tájékoztató alakja vs a valós alak); a dokumentum igazítása legfeljebb a megvalósult alakra, **külön, angol, docs-only commitban**, ha az indokolt. **Nincs `DisallowUnknownFields`** a modulban (ellenőrizd `grep`-pel és idézd): az `omitempty` additív mező ezért kompatibilis; az `abi.schema.yaml` csak a `project.yaml` `abi:` blokkját fedi, nem az execute-eredményt (ellenőrizd).

## Mérési infrastruktúra (S4 és S3 közös előfeltétele — ezzel kezdd, mert elrontható)

- **Az eszközök a modul builder image-ében vannak** (`cic-module-oracle-cloud-builder:latest`: Go 1.25.0, TinyGo, staticcheck, govulncheck); a hoston nincs Go. **A `docker compose exec builder` az éppen hívó klón `./`-jét mountolja, és a compose projektnév-ütközés miatt másik klón konténerére csatlakozhat** — ezért az eldobható másolaton **`docker run --rm -v <tmp>:/app -w /app <image> …`**-t használj (vagy egyedi projektnevet), és **minden mérés előtt nyomtasd ki a mountot és a `git rev-parse HEAD`-et a konténerben**, hogy lásd: a kívánt fát méred.
- **A `module/module.wasm` és a `project.yaml` `buildHash` követett, aláírt artefaktok.** A `make wasm.build` ezeket **felülírja**; a load-teszt (`module_loadtest_test.go`, `const wasmPath = "module.wasm"`) pedig a **commitolt, régi** binárist tölti be, ezért **nem látná a változtatásodat**. Ezért: a guestet **eldobható útvonalra** fordítsd (`tinygo build -o <scratch>/module.wasm -target wasip1 -scheduler=none .` vagy a `mk/wasm.mk` ekvivalens parancsa), a **valódi `Call` exporton át futó** új teszt ezt az útvonalat egy környezeti változóból olvassa (az alapértelmezés a meglévő `module.wasm`, így a meglévő tesztek változatlanok), **és a `module.wasm`-ot, a `project.yaml`-t nem módosítod és nem commitolod.** A jelentésben mondd ki: a commitolt artefakt a változtatás után **elavult, amíg a tulajdonos újra nem építi és nem írja alá** (ez nem a te feladatod).
- A load-teszt mockja ma egy beágyazott closure, fix `{}` törzzsel és 200-as státusszal: a „0 OCI-kérés" és a create-válasz `id` teszteléséhez **általánosítsd** (konfigurálható törzs, státusz és kérésszámláló), a meglévő tesztek viselkedésének megőrzésével.
- **Q2 diff-szintű lefedettség:** nincs rá repo-eszköz; a `coverprofile` és a `git diff -U0` metszetét egy **a repón kívül lévő** script számolja; a nevező: az új/módosított végrehajtható sorok halmaza.

## Minőség (Stage 1: új és módosított kód, diff-szinten)

Mindent **csak az új/módosított kódra** (és a hozzá írt tesztekre) mérj, eldobható másolatban, parancs + nevező + commit megadásával: (Q0) `gofmt -s`, `go vet`, `staticcheck` tiszta; (Q1) egységtesztek **negatív esetekkel** és `-race`; (Q2) az új/módosított sorok lefedettsége (cél ≥ 90%; a tényleges számot add meg, ne a célt); (Q3) ágazati lefedettség: `NOT MEASURED`, ha nincs hozzá eszköz; (Q4) mutációs próba az új/módosított kódon: **ha nincs elérhető mutációs eszköz a builder image-ben vagy a hálózat nem engedi a telepítést, az eredmény `NOT MEASURED`** (ok és szükséges feltétel megadásával), nem kivétel és nem PASS; ha fut, a túlélőket sorold fel és mindegyikre adj tesztet vagy indoklást; (Q5) legalább **öt bevetett hiba** az új kódban és tesztekben (köztük az S4 őrfeltétel-törlése és az S3 „id nélkül mégis `succeeded`" hiba), mindegyikre a megfelelő teszt PIROS, a visszaállítottra ZÖLD; (Q6) a vendorolt `testdata/vcn-v1/` fixture-ök használata/érintetlensége (azt **nem módosítod**); **(Q7) nincs ebben a jobban**; (Q8) az új függvények/mezők production hívási útja fájl:sor szinten, a `Call` dispatcherig; (Q9) `MANIFEST.sha256` regenerálva a módosított követett fájlokra (a Makefile `manifest-update` célja `docker compose exec builder`-t használ; ha az nem elérhető, ugyanazt a parancsot — `git ls-files -z | xargs -0 sha256sum`, a `MANIFEST.sha256` kihagyásával, `LC_ALL=C sort` — futtasd a builder image-ében, és írd le, hogyan; **a `module.wasm` bejegyzése nem változhat**). **CI-t, workflow-t nem módosítasz, nem futtatsz újra, és a kapu bekötésére sem készítesz változtatást.**

## Mérési fegyelem, prioritás és keret

A mérések **reprodukálhatók és nem szennyezők**: `git archive` + `tar -x` eldobható munkakönyvtár, a kimenet a repókon kívül; a `git status --porcelain` minden érintett klón végén idézve. A mérési környezet rögzítve (a `go version`, az OS, az eszközök verziója, a hálózat). **Az el nem végzett mérés `NOT MEASURED`** (ok + szükséges feltétel), sosem PASS, sosem hallgatás. Prioritás: **mérési infrastruktúra → S4 → S3 → Q5 → Q2/Q8/Q9 → Q4**; ami nem fér a `max_turns` keretbe, `NOT MEASURED` vagy nevesített hiány, nem félkész kód.

## Output

**A modul repóban** (a `feature/forms-oracle-vcn-hardening-01b-a` ágon; minden kód, komment, doksi és commit üzenet **angol**): a tesztek és az S3 kód, a `MANIFEST.sha256` regenerálva. **A `cic-factory` klónban** (`jobs/forms-oracle-vcn-hardening-01b-a/output/`, **magyarul**):
- `slice-report.md` — mi épült meg az S4-ből és S3-ból, mi nem; háromszintű státusz, production hívási lánc fájl:sor szinten; a Plan-veszély; az artefakt elavulásának kimondása; ami határjelzést okozott.
- `qa-measurements.md` — Q0–Q9 (Q7 kivételével) az új/módosított kódra: parancs + nevező + commit + kimenet-idézet; `NOT MEASURED` lista.
- `claim-evidence.md` — `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`; a Státusz oszlop jelölje a forrásosztályt: `AGENT_MEASURED`, `DOCUMENTED`, `NOT MEASURED`, `NOT INDEPENDENTLY VERIFIED`; az 01a-ból átvett állítás külön jelölést kap.
- `agent-output.md` — rövid, tényszerű összefoglaló és a „Kötelező beszámoló" válaszai.

## Ellenőrizhető elvárások (az orchestrátor közvetlenül ellenőrzi és újramér)

1. Az S4 teszt a production `Observe`-ot hajtja meg, a táblában a négy állapottal; a bevetett hibán (őrfeltétel-törlés) PIROS, az eredetin ZÖLD (az orchestrátor saját másolatban megismétli); a production `Observe` forrása **bit-azonos** az induló állapottal (`git diff` üres a `provider.go` `Observe`-szakaszán és a `correspondence.go`-n).
2. A létrehozott `resource_id` a mockolt create-válasz `id`-jéből jön, create-nél; minden negatív esetben `failed` eredmény `error_class`-szal, soha nem üres érték; nem-create eredmények bájt-azonosak.
3. A `go.mod`/`go.sum`, a CI/workflow, `module/module.wasm`, `project.yaml`, `abi.schema.yaml`, `capability-manifest.schema.yaml`, `project.schema.yaml`, `oci-sdk.lock.yaml`, `module/schemas/core/*.json` (ne futtasd az `oci.generate`-et), `testdata/vcn-v1/`, a `manual_real_oci_test.go`, a Relay és a pin-fájlok **bit-azonosak** az induló állapottal (diff igazolja). A `Plan` elutasítása (`TestPlanRejectsEmptyObserved`) és az összes meglévő teszt változatlanul zöld.
4. Minden mért szám mellett a parancs, a nevező és a commit; az orchestrátor újramér egyet.
5. Az `implemented` státusz mellett production hívó fájl:sor, nem a teszt.

## Biztonsági és végrehajtási határok

Nincs valós OCI hívás, tenancy-módosítás, IAM-policy, Vault-kulcs vagy credential-export; nincs SDK-frissítés; **nincs Relay-módosítás és nincs ál-Relay**; **nincs Forms-import vagy Forms-kód**; **nincs séma-, pin-, dependency-, CI- vagy workflow-módosítás**; **nincs `execBinding`-módosítás és nincs `compartment_id`** (az a binding-job); nincs `Plan`-lazítás; nincs a production `Observe` módosítása; nincs Subnet/Instance. **Az egyetlen megengedett interfész-változás az additív `steps[i].resource_id` (omitempty, create szerepnél).** Minden más alakváltozás, amely a meglévő kimenet bájtjait módosítaná, **határjelzés**.

**Határjelzés (állj meg, őrizd meg a már elkészült RED tesztet, a reprodukciót és az ABI-hatás elemzését, és jelezd — ne javíts körül):** ha az S4 bármilyen módon a production `Observe` `effective_config` **tartalmát vagy alakját** változtatná; ha az S3 a per-step `resource_id`-n kívüli alakot kívánna (top-level `provider_metadata`, új wrapper), vagy bármelyik meglévő kimenet bájtjait módosítaná; ha a mérési infrastruktúra a `module.wasm`/`project.yaml` módosítása nélkül nem oldható meg; ha a TinyGo-build elbukik és az ok nem hárítható el a keretben. Ilyenkor: mi csúszik meg, mi a bizonyíték, és mi kellene a folytatáshoz.

## Git

**`cic-module-oracle-cloud`** — klónozd a workspace-be, a `devel`-ből nyiss `feature/forms-oracle-vcn-hardening-01b-a` ágat; ide commitolj és pusholj. ❌ NE pusholj `devel`-re vagy `main`-re · ❌ NE nyiss PR-t · ❌ NE merge-elj · Vault-aláírt commitok · **`git add -A` tilos** (csak a konkrét fájlok; a mérési kimenetek nem kerülhetnek a repóba).
**`cic-factory`** — csak az `output/` dokumentumok, a `feature/forms-oracle-vcn-hardening-01b-a` ágra.

## Kötelező beszámoló (az `agent-output.md`-ben, válaszonként bizonyítékkal)

1. A production `Observe` mit ad a négy `ipv6CidrBlocks`-állapotra (hiányzó, `[]`, nem üres, `null`) a változtatás előtt és után? Melyik bevetett hiba melyik tesztet pirosítja (a kimenetekkel)? Módosult-e a production `Observe` (várt: nem)?
2. Hol él a `resource_id` az `Execute` eredményében, honnan jön, és melyik negatív eset ad `failed` eredményt `error_class`-szal? Bizonyított-e, hogy a nem-create eredmények bájt-azonosak?
3. Mit mért a `grep` a fogyasztókról (Relay, `manual_real_oci_test.go`, `manual-verification.md`)? Mit mondott a `go vet -tags manual_real_oci ./...`?
4. Mit mérsz az új/módosított kódra a Q0–Q9 szinteken (Q7 kivételével), nevezővel, és mi `NOT MEASURED` (miért, és mi kellene hozzá)?
5. Mely új függvények/mezők érhetők el a valódi `Call` exporton át (a scratch-wasm teszttel), és melyeket csak teszt hív?
6. Mi változott a `go.mod`/`go.sum`, a CI, a séma, a pin fájlokban, a `module.wasm`-ban és a `project.yaml`-ban (várt: semmi), és mi a klónok végső `git status --porcelain` eredménye?
7. Mi marad nyitva (a leképezés, a `compartmentId` binding, az M2 és az R1), és mi a legkisebb következő lépés — **csak igazolt eredmények alapján**?

Ha bármelyik pont nem teljesül, **ne minősítsd teljes GO-nak az eredményt**: adj részletes PARTIAL/HOLD státuszt.

## Nyelvi szabály

Ez az `input.md` és a gondolkodásod magyar. **Minden, ami a modul-repóba kerül — kód, komment, `docs/**`, commit üzenet — angol.** Az `output/*.md` magyar.
