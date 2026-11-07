# forms-oracle-vcn-slice-01b — az első VCN vertical slice a modulban: előremeneti leképezés, OCID-megőrzés, production Observe, mockolt OCI-val, Relay nélkül

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, nem te figyeled a futását, és nincs mire várnod: a munka, amit az alábbiak leírnak, **a te dolgod, most**. Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a `workdir` operátora, aki a specet írta és az outputot reviewolja; a tulajdonos hozza a döntéseket). Ne beszélj az ő nevében, és ne írj állapotjelentést a jobról. Ha egy döntés a tulajdonosé (lásd „Határjelzés"), ne dönts helyette: állj meg ott, és írd le, mi kell a folytatáshoz.

## Reasoning mód

**implementation, szűk szeletre.** Konkrét kódváltozás, teszt és mérés a `cic-module-oracle-cloud` modulban, egyetlen resource-ra (**VCN**), **mockolt OCI-válaszokkal**, **Relay nélkül**. A cél nem egy kész integráció, hanem négy bizonyított, a production hívási útba bekötött képesség és az ezeket védő tesztek. Ami nem fér a szeletbe, az **nem kerül bele**, és a jelentésben nevesítve marad.

## Kontextus — az elfogadott alap

Az `01a` baseline-felmérés **lezárult (CONDITIONAL GO — partial baseline accepted)**. Olvasd el **teljesen, mielőtt bármihez nyúlsz** (a `cic-factory` `main` ágán, a `jobs/forms-oracle-provider-integration-01a/` alatt): `review.md`, `ref/final-review.md`, `output/baseline.md`, `output/contract-mapping.md`, `output/relay-requirements.md`, `output/claim-evidence.md`; a modul `devel` ágán: `docs/design/forms-integration-direction.md`, `docs/design/specs/provider-abi.md`, `docs/design/specs/state-model.md`.

**Az 01a állításai közül a `NOT INDEPENDENTLY VERIFIED` (NIV) jelölésűeket nem veheted át tényként**: a `module` sorlefedettség pontos értéke (82,7% vs 82,9%), a top-level tesztszám (55 vs 26), a mutációs eredmény (159/217), a `govulncheck`, a Q3/Q6/Q9 sorok. A saját mérésed az irányadó, az előzőt ne idézd bizonyítékként. A `relay-requirements.md` hivatkozásai közül 9 többértelmű és 7 nem feloldható: a hivatkozott sort **ellenőrizd a forrásban, mielőtt rá támaszkodsz**.

**Az 01a bizonyított leletei, amelyekből ez a szelet áll** (mindet ellenőrizd újra a kódban, mielőtt rá építesz):
1. Nincs előremeneti NetworkSpace → OCI `CreateVcn` leképezés sehol.
2. A create az `Execute(CreateVcn)` közvetlen hívása a `Plan` **kívül**; a `Plan` üres `observed`-et szándékosan elutasít (`TestPlanRejectsEmptyObserved`) — ezt **nem lazítod**.
3. Az `executionStep`/execution result nem ad vissza `resource_id`-t, miközben a `provider-abi.md:99` előírja.
4. A `normalizeObserved` nem szerepel a production `Observe` útjában (`provider.go:827→860→861`: `effectiveConfig` + `applyDerivations`); az `applyDerivations` forrás-jelenlét őrfeltételének törlése (hiányzó `ipv6CidrBlocks`-ból `isIpv6Enabled=false`) **a modul meglévő teljes tesztkészletét túléli**.
5. A `compartmentId` az OCI-n a create kötelező mezője, a NetworkSpace-ben nincs helye; az `execBinding` nem hordozza.

## Boot sequence — a KB használata és a határai

1. **`mcp__cic-graph__kb_status`**: rögzítsd a build idejét, a forrás-commitokat, a `stale` és `sources_behind_upstream` mezőt. Ha nem elérhető: `NOT MEASURED`, és folytasd a kódolvasással.
2. `search_nodes` az `axioms`, `symbols`, `contract`, `limits` kifejezésekre (az eredményt akkor is rögzítsd, ha üres), majd `search_query` a modul ABI-jára, szerződéseire, state-modelljére.
3. A kb_focus azonosítókat **fájlútvonal alapján ellenőrizd, mielőtt használod** (`get_chunk`, `file_path`): `c7529` → `.../docs/design/architecture.md`; `c7616` → `.../docs/design/specs/state-model.md`; `c7487` → `.../docs/contracts/en/wasm-abi.md`; `c7668` → a `module/contracts.go` (a KB `.yaml` kiterjesztéssel indexeli); `c7675` → a `module/correspondence.go`; `c7550` → `.../docs/design/primitives-alignment.md`. Az azonosítók nem stabilak: ha a `file_path` nem egyezik, ne használd.
4. **A KB határai:** 2026-10-16-i állapot (modul `5d0a327`, Relay `55a899f`); sem a `cic-primitive-forms`, sem a `cic-schema-registry` nincs benne; a #33–#35 előtti. **A KB tájékozódás, nem bizonyíték**: kódállításhoz a forrást olvasd.
5. Minden KB-ból vett állítás a `claim-evidence.md`-ben külön jelölést kap: `Forrás: KB c#### (file_path)`.

## Forrás — konkrét helyek

Klónozd a workspace-be: `cic-module-oracle-cloud` (**`devel`**; jegyezd fel a HEAD commitot — várhatóan a `3e38886` vagy a #35 squash-merge commitja), `cic-primitive-forms` (`main`, várhatóan `2f02a75`), `cic-primitives`, `cic-schema-registry`. A **CIC-Relay READ-ONLY**: a `${CIC_RELAY_PATH}` alatti forrást csak olvasod, soha nem szerkeszted.

**Pinek.** A `cic-primitives` és a `cic-schema-registry` a Forms `corpus/pins.yaml`-jából kiolvasott commiton vizsgálandó (`git checkout --detach`); a NetworkSpace pin `6db77d4` (sha256 `c9a4d14c…3b68`). A registry `ac567ae` **csak olvasható összehasonlító referencia** (a `network-space.correspondence.yaml` szerződés forrása); **a pint nem mozgatod és nem javasolsz pinmozgatást**.

**Oracle modul — olvasd:** `module/provider.go`, `contracts.go`, `correspondence.go`, `correspondence/vcn.json`, `observed.go`, `abi.go`, `envelope.go`, `schemas/core/vcn.json`, a meglévő tesztek (`provider_test.go`, `observed_test.go`, `module_loadtest_test.go`, `abi_negative_test.go`), `testdata/vcn-v1/`, `docs/design/manual-verification.md`.

**Forms — olvasd:** a `go/` exportált API-ja (`Parse`, `CompileSchema`, `Validate`, `Expand`, `Normalize`…, a tényleges aláírások fájl:sor), `docs/P5-ADMISSION-CONTRACT.md`. A Forms csak a `config_surface`-t validálja, a `state_surface`-t nem; az admission-szerződés dokumentált terv, nem production kapu.

## Státusz-definíciók és az ellenőrzési módszerük

Háromszintű státusz minden állításhoz, **módszerrel bizonyítva**:
- **implemented** — production kódban hívódik **és** teszt fedi. Bizonyítás: a hívási lánc ellenőrzése a production kódban: `grep -rn "<Szimbólum>" --include="*.go" | grep -v "_test.go"` — legalább egy production hívó **fájl:sor megadva**, és a láncot a `Call` dispatcherig (`module/abi.go`) vissza kell követni; 0 találat `_test.go` nélkül → scaffold. A guest buildre a `deadcode` nem alkalmazható (cgo); helyette: a hívási lánc fájl:sor szinten **és** legalább egy teszt, amely az új utat a valódi `Call` exporton át hajtja meg (`module_loadtest_test.go` mintájára, valódi `module.wasm`-mal), ha a környezet engedi (a `module_loadtest_test.go` a `make wasm.build` TinyGo-artefaktját tölti be wazero-val; a modul builder image-ében a TinyGo elérhető); ha nem, `NOT MEASURED` az okkal.
- **scaffold** — kódban van, de production hívója nincs, vagy feltétel mögött él (a feltétel fájl:sor).
- **concept** — csak dokumentált.
Ha a státuszt nem tudod fájl-szinten alátámasztani, ne mondd ki tényként.

## Tiltott rövidítések — ezek NEM bizonyítékok

- ❌ „a fájl létezik" / „a teszt zöld" / „zöld CI" ≠ implemented · ❌ exit code 0 ≠ sikeres mérés (olvasd a kimenetet) · ❌ százalék a nevező, a kizárások és a parancs nélkül.
- ❌ **Olyan teszt, amely nem tud elbukni.** Minden új tesztről mérd meg, hogy elbukik-e egy bevetett hibán (lásd Q5 lent).
- ❌ Teszt, amely az **új utat megkerülő segédfüggvényt** hajtja meg a production útvonal helyett (az 01a pont ezt a hibát találta: a `normalizeObserved` tesztelt, de nem hívott).
- ❌ Mock vagy kézi adapter egy hiányzó leképezés elfedésére; a hiányt rögzítsd. · ❌ `module/schemas/core/vcn.json` **nem primitives-séma**. · ❌ A Forms nem validálja a state-et.

## Feladat — a szelet (S1–S6), ebben a sorrendben; S4 és S3 a legmagasabb prioritás

**S4 — a production `Observe` negatív tesztje (blokkoló, ezzel kezdd).** Kötelező szabály: *ha az OCI-válaszban hiányzik az `ipv6CidrBlocks`, a CIC state nem tartalmazhat abból levezetett `isIpv6Enabled=false` értéket; a hiányzó megfigyelés nem válhat megfigyelt `false` értékké.* A tesztnek **közvetlenül a production `Observe` függvényt** kell meghajtania (mockolt GET-tel), nem a `normalizeObserved`-et. Bizonyítsd az eredményt **bevetett hibával**: eldobható másolatban töröld az `applyDerivations` forrás-jelenlét őrfeltételét; a teszt legyen PIROS a mutánson és ZÖLD a visszaállítottan (a két kimenetet idézd). Ezután dönts és indokolj (a 01a leletei alapján): a production `Observe` használja-e a `normalizeObserved` védelmét (a szűrőt és a coverage-et), vagy az `applyDerivations`-ben legyen a garancia — **a `Plan` viselkedését és az `Observe` ABI-kimenetének visszafelé kompatibilitását ne rontsd**; ha a kimenet alakja változna (pl. coverage mező), az ABI-döntés a tulajdonosé: állj meg és jelezd.

**S3 — a létrehozott OCID megőrzése.** Az `Execute(CreateVcn)` eredménye hordozza a létrehozott erőforrás azonosítóját a `provider-abi.md:99` szerint (`provider_metadata.resource_id`), a mockolt OCI create-válasz `id` mezőjéből; aszinkron válasznál a `work_request_id` is marad. Kötelező negatív esetek (mindegyik tipizált hiba, **soha nem üres vagy kitalált `resource_id`**): 2xx válasz `id` nélkül; nem JSON törzs; `id`, amely nem OCID-alakú; OCI 4xx/5xx. Az új mező a meglévő `executionResult` alakjához **additív**, a meglévő tesztek változatlanul zöldek. A tartós state-binding (CIC `uid` ↔ `provider_id` tárolása) **nem része** a szeletnek (az Relay-/state-oldali követelmény R2).

**S2 — `compartmentId`: binding/execution context, JAVASOLT irány, tulajdonosi jóváhagyásig.** A tulajdonos javaslata: a cél-compartment a **provider-binding / execution context** része, **nem** a NetworkSpace `config_surface` mezője. Ezért **a NetworkSpace/registry/primitives sémához nem nyúlsz**. Megvalósítás a feature branchen, kifejezetten `PROPOSED` jelöléssel a kódkommentben és a dokumentációban: az `execBinding` kibővítése `compartment_id`-vel; a create-törzs a bindingből veszi; **ha hiányzik vagy nem OCID-alakú (`ocid1.compartment.` vagy a tenancy gyökér `ocid1.tenancy.`), tipizált validációs hiba és NINCS OCI-hívás** (ezt teszt bizonyítja: a mock OCI-n 0 kérés). A `ChangeVcnCompartment` action viselkedését ne változtasd. **Külön dokumentum** (`output/m2-decision-record.md`, magyarul): a döntéshez a tulajdonosnak négy kérdésre kell válaszolnia — honnan származik a binding értéke; ki jogosult meghatározni; hogyan ellenőrződik az OCI-művelet előtt; hogyan kapcsolódik a CIC logikai identitáshoz — te **a lehetőségeket és a következményeiket** írd le, a döntést nem hozod meg. Az S2 kódja addig **nem merge-elhető**, amíg a tulajdonos nem döntött; ezt a jelentés elején mondd ki.

**S1 — előremeneti leképezés: NetworkSpace VCN intent → OCI `CreateVcn` konfig.** Csak a 01a által **authored és leképezhetőnek** osztályzott mezőkre: `cidr_block` + `secondary_cidr_blocks` → `cidrBlocks` (az `first`/`rest` inverze), `dns_label` → `dnsLabel`, `ipv6_enabled` → `isIpv6Enabled`, `tags` (`[{key,value}]`) → `freeformTags` (lista → map). A leképezés **explicit elutasítást** ad (tipizált hiba, nem csendes eldobás) a `dns_support_enabled` és `dns_hostnames_enabled` mezőre (OCI-n nincs megfelelőjük; a registry correspondence `kind: unsupported`). Amelyik OCI-mezőnek nincs intent-otthona (`displayName`, `definedTags`, `securityAttributes`, `isZprOnly`, `isOracleGuaAllocationEnabled`, `byoipv6CidrDetails`, `ipv6PrivateCidrBlocks`), **azt nem találod ki és nem veszed fel sémába**: coverage rekordként nevesítve marad. Negatív esetek: duplikált címkekulcs; üres/érvénytelen CIDR; ismeretlen mező; a `secondary_cidr_blocks` az `cidr_block` nélkül. A leképezés helyét **indokold** (a modul `correspondence/` mechanizmusának kiterjesztése kézzel írt, kódként reviewolt szabályokkal vs. a teszt-harness): a guest TinyGo-ban fordulnia kell, a modul `go.mod`-ja **nem kaphat új függőséget** (a Forms importja ezért tilos); a registry `ac567ae` correspondence a referenciaszerződés, nem importált függőség. Property-teszt: a támogatott mezőkre `előre(vissza(x))` egyezik az eredetivel.

**S5 — a kontrollált teszt-harness.** A szelet teszt-harnessben épül, **ál-Relay nélkül**. A Forms feldolgozása a harness helyén történik: a Forms-oldali kimenetet (a kifejtett NetworkSpace objektumot) **a Forms pinelt commitjából, eldobható másolatban előállított, származásával rögzített golden vektorokként** használd (commit, parancs, sha256), ne importálj Forms-kódot a modulba. A Forms Go-oldala könyvtár (nincs CLI): a vektorokat egy kis Go-programmal (vagy teszttel) állítod elő az **eldobható Forms-másolatban**; a `go/real_schema_test.go` mutatja, hogyan fordul le a NetworkSpace és hogyan validál egy VCN intent, ebből indulj. Ha az `Expand`/`Normalize` kimenete a pinelt commiton a `config_surface`-re nem állítható elő, az **határjelzés**: ne találj ki kimenetet, ne kézzel írj „Forms-kimenetet". Az első create egy **közvetlenül előállított, tesztben kontrollált `Execute` terv**; mondd ki a jelentésben, hogy ez **nem production provisioning** és nem helyettesíti a későbbi jóváhagyott tervezési folyamatot. A `Plan` elutasítását (`TestPlanRejectsEmptyObserved`) változatlanul hagyd. Licenc: a golden vektorok adatok, **Forms-kódot a modulba nem másolsz** (a modul CC BY-NC-SA 4.0, a Forms Apache-2.0; az átvételi döntés a tulajdonosé).

**S6 — minőség (Stage 1: új és módosított kód, diff-szinten).** Mindent **csak az új/módosított kódra** mérj, eldobható másolatban, a parancs és a nevező megadásával: (Q0) `gofmt -s`, `go vet`, `staticcheck` tiszta; (Q1) egységtesztek **negatív esetekkel**, és `-race`; (Q2) az új/módosított végrehajtható sorok lefedettsége (cél: ≥ 90%, a nevező: az új/módosított sorok `git diff` szerinti halmaza; a tényleges számot add meg, ne a célt); (Q3) ágazati lefedettség: `NOT MEASURED`, ha nincs hozzá eszköz; (Q4) mutációs próba **az új/módosított kódon** (eldobható másolat, az eszköz verziója és a timeout-koefficiens megadva; a túlélőket sorold fel, és mindegyikre teszt vagy indoklás); (Q5) legalább **öt bevetett hiba** az új kódban, mindegyikre a megfelelő teszt PIROS, a visszaállítottra ZÖLD; (Q6) a közös vektorok használata a már vendorolt `testdata/vcn-v1/` mellett; (Q8) az új függvények production hívási útja fájl:sor szinten; (Q9) `MANIFEST.sha256` a módosítás után regenerálva (a Makefile `manifest-update` célja `docker compose exec builder`-t használ; ha az nem elérhető, ugyanazt a parancsot — `git ls-files -z | xargs -0 sha256sum`, a `MANIFEST.sha256` kihagyásával, `LC_ALL=C sort` — futtasd a modul builder image-ében, és írd le, hogyan). **CI-t, workflow-t nem módosítasz, nem futtatsz újra, és a kapu bekötésére sem készítesz változtatást** (a CI/infra fagyasztva): a javaslatot legfeljebb dokumentumban írd le.

## Mérési fegyelem, prioritás és keret

A mérések az 01a mintája szerint **reprodukálhatók és nem szennyezők** (`git archive` + `tar -x` eldobható munkakönyvtár, a kimenet a repókon kívül); a `git status --porcelain` minden érintett klón végén idézve. A mérési környezet rögzítve (a `go version`, az OS, az eszközök verziója, a hálózat). **Az el nem végzett mérés `NOT MEASURED`** (ok és szükséges feltétel megadásával), sosem PASS, sosem hallgatás. Prioritás a `max_turns` korlát miatt: **S4 → S3 → S2 → S1 → S5 → S6**; ami nem fér bele, `NOT MEASURED` vagy nevesített hiány, nem félkész kód.

## Output

**A modul repóban** (a `feature/forms-oracle-vcn-slice-01b` ágon; minden kód, komment, doksi és commit üzenet **angol**): a kód és a tesztek, a `MANIFEST.sha256` regenerálva. **A `cic-factory` klónban** (`jobs/forms-oracle-vcn-slice-01b/output/`, **magyarul**):
- `slice-report.md` — mi épült meg S1–S6-ból és mi nem; mindegyikhez háromszintű státusz, production hívási lánc fájl:sor szinten; az M2 nyitott állapotának kimondása az elején.
- `m2-decision-record.md` — a tulajdonosi döntés előkészítése (négy kérdés, lehetőségek, következmények; döntés nélkül).
- `qa-measurements.md` — a Q0–Q9 mérések az új/módosított kódra, parancs + nevező + commit + kimenet-idézet; `NOT MEASURED` listával.
- `claim-evidence.md` — `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`; a Státusz oszlop jelölje a forrásosztályt: `AGENT_MEASURED`, `DOCUMENTED`, `NOT MEASURED`, `NOT INDEPENDENTLY VERIFIED`; az 01a-ból átvett állítás külön jelölést kap.
- `agent-output.md` — rövid, tényszerű összefoglaló és a „Kötelező beszámoló" válaszai.

## Ellenőrizhető elvárások (az orchestrátor közvetlenül ellenőrzi és újramér)

1. Az S4 teszt a production `Observe`-ot hajtja meg; a bevetett hibán PIROS, a visszaállítottan ZÖLD (az orchestrátor saját másolatban megismétli).
2. A létrehozott `resource_id` a mockolt create-válaszból jön, és minden negatív esetben tipizált hiba, nem üres érték.
3. Compartment nélkül/érvénytelenül 0 OCI-kérés a mock oldalán.
4. A `go.mod`/`go.sum`, a CI/workflow, a séma- és pin-fájlok, a Relay és a `manual_real_oci_test.go` **bit-azonosak** az induló állapottal (diff igazolja).
5. A `Plan` elutasítása (`TestPlanRejectsEmptyObserved`) és a meglévő tesztek változatlanul zöldek.
6. Minden mért szám mellett a parancs, a nevező és a commit; az orchestrátor újramér egyet.
7. Az `implemented` státusz mellett production hívó fájl:sor, nem a teszt.

## Biztonsági és végrehajtási határok

Nincs valós OCI hívás (sem read, sem write), tenancy-módosítás, IAM-policy, Vault-kulcs vagy credential-export; nincs SDK-frissítés; **nincs Relay-módosítás és nincs ál-Relay** (az R1 külön követelmény marad, nem előfeltétele ennek a szeletnek); **nincs séma- (NetworkSpace/primitives/registry), pin-, dependency-, CI- vagy workflow-módosítás**; nincs Subnet/Instance; nincs `Plan`-lazítás; a `manual_real_oci_test.go` érintetlen. A `compartmentId`-t **nem** emeled a NetworkSpace sémába.

**Határjelzés (állj meg és jelezd, ne javíts körül):** ha az S4 az `Observe` kimenetének **alakját** változtatná; ha az S1/S2 sémamódosítást, új függőséget vagy ABI-változtatást követelne meg ezen a jelzett kereten túl; ha a leképezéshez a Forms importja kellene a guestbe; ha a TinyGo-build elbukik az új kódon és az ok nem hárítható el a keretben. Ilyenkor: mi csúszik meg, mi a bizonyíték, és mi kellene a folytatáshoz.

## Git

**`cic-module-oracle-cloud`** — klónozd a workspace-be, a `devel`-ből nyiss `feature/forms-oracle-vcn-slice-01b` ágat; ide commitolj és pusholj. ❌ NE pusholj `devel`-re vagy `main`-re · ❌ NE nyiss PR-t · ❌ NE merge-elj · Vault-aláírt commitok · **`git add -A` tilos** (csak a konkrét fájlok; a mérési kimenetek nem kerülhetnek a repóba).
**`cic-factory`** — csak az `output/` dokumentumok, a `feature/forms-oracle-vcn-slice-01b` ágra. A többi klón (Forms, primitives, registry, Relay) **soha nem commitolható és nem pusholható**.

## Kötelező beszámoló (az `agent-output.md`-ben, válaszonként bizonyítékkal)

1. A hiányzó `ipv6CidrBlocks` esetén a production `Observe` mit ad ma, és mit ad a változtatás után? Melyik bevetett hiba melyik tesztet pirosítja (a kimenetekkel)?
2. Honnan jön a `resource_id` az `Execute` eredményében, és melyik negatív eset ad tipizált hibát?
3. Mit tartalmaz az `execBinding` a `compartment_id` mezővel, és mit bizonyít, hogy érvénytelen értéknél 0 OCI-kérés megy ki? Melyik rész `PROPOSED` és mi vár tulajdonosi döntésre?
4. Mely NetworkSpace-mezők képződnek le előre, melyek kapnak explicit elutasítást, és melyeknek nincs intent-otthona (coverage rekordok)?
5. Mit mérsz az új/módosított kódra a Q0–Q9 szinteken, nevezővel, és mi `NOT MEASURED` (miért, és mi kellene hozzá)?
6. Mely új függvények érhetők el a valódi `Call` exporton át, és melyeket csak teszt hív?
7. Mi változott a `go.mod`/`go.sum`, a CI, a séma és a pin fájlokban (várt: semmi), és mi a klónok végső `git status --porcelain` eredménye?
8. Mi marad nyitva (M2, R1, R2, Subnet/Instance), és mi a legkisebb következő lépés — **csak igazolt eredmények alapján**?

Ha bármelyik pont nem teljesül, **ne minősítsd teljes GO-nak az eredményt**: adj részletes PARTIAL/HOLD státuszt.

## Nyelvi szabály

Ez az `input.md` és a gondolkodásod magyar. **Minden, ami a modul-repóba kerül — kód, komment, `docs/**`, commit üzenet — angol.** Az `output/*.md` magyar.
