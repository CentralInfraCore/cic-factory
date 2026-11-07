# forms-oracle-provider-integration-01a — baseline és szerződés-leképezés: a Forms és az Oracle provider között, KÓD NÉLKÜL

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, nem te figyeled a futását, és nincs mire várnod: a munka, amit az alábbiak leírnak, **a te dolgod, most**. Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a `workdir` operátora, aki a specet írta és az outputot reviewolja). Ne beszélj az ő nevében, és ne írj állapotjelentést a jobról — írd meg az output dokumentumokat.

## Reasoning mód

**audit (leltár és mérés).** Nem implementation. **Egyetlen repóban sem módosítasz kódot, sémát, CI-t vagy dokumentációt**; csak az `output/` dokumentumok készülnek a `cic-factory` klónban. Nem tervezel új architektúrát: az irány el van fogadva és le van írva (lásd alább). A te feladatod megmérni, hogy a meglévő kód és az irány között mi a távolság, és ezt bizonyítékkal rögzíteni. **A hiányzó implementációt ne kezeld meglévőként.**

## Kontextus

A `cic-module-oracle-cloud` modul (nyolcműveletes provider-ABI, OCI séma-extractor, VCN/Subnet/Instance szerződések) és a `cic-primitive-forms` (Go és Rust: `Parse`, `CompileSchema`, `Validate`, `Expand`, `Normalize`, `NormalizeWithPolicy`, `PolicyResolution`) között az **első működő integrációs szelet** a cél, a jelenleg ténylegesen támogatott OCI resource-készleten, mockolt OCI-válaszokkal, valós felhő nélkül. Ez a job **csak az első lépés**: leltár, mérés, és a szerződés-leképezés *lefedettségi* táblája. A VCN vertical slice (01b) és a Subnet/Instance (01c) **külön job, a te baseline-od orchestrátori elfogadása után**; azokat ne kezdd el és ne tervezd részletesen.

**Olvasd el először, teljesen** (a modul repó `devel` ágán, a `3e38886` merge commit vagy újabb): `docs/design/forms-integration-direction.md`. Ez rögzíti az elfogadott irányt, a két séma-szerepet, a kimondott korlátokat és a minőségi szintek (Q0–Q9) átemelésének szakaszait. **Ennek a jobnak minden pontja ahhoz igazodik; ha a kód és a dokumentum eltér, azt dokumentáld, ne javítsd.** Olvasd el mellé: `docs/design/primitives-alignment.md` (részben túlhaladott, a banner jelzi).

## Boot sequence — a KB használata és a határai

1. **`mcp__cic-graph__kb_status`** — rögzítsd az `agent-output.md`-ben és a `baseline.md`-ben: a KB build ideje, a forrás-commitok (a modulé és a Relayé), a `stale` és a `sources_behind_upstream` mező, és hogy a KB elérhető-e. Ha nem elérhető, írd: `NOT MEASURED`, és folytasd a kódolvasással.
2. **A CIC boot kérdések:** `search_nodes` a `axioms`, `symbols`, `contract`, `limits` kifejezésekre; rögzítsd az eredményt akkor is, ha üres. Ezen túl `search_query` a modul ABI-jára, szerződéseire és state-modelljére.
3. **A megadott KB-azonosítókat fájlútvonal alapján ellenőrizd, mielőtt használod** (`get_chunk`, a visszakapott `file_path`): `c7529` → `.../cic-module-oracle-cloud/docs/design/architecture.md`; `c7616` → `.../docs/design/specs/state-model.md`; `c7487` → `.../docs/contracts/en/wasm-abi.md`; `c7668` → `.../module/contracts.yaml`; `c7675` → `.../module/correspondence.yaml` (**a KB a Go fájlokat `.yaml` kiterjesztéssel indexeli**: a chunk tartalma a `module/contracts.go`, illetve a `module/correspondence.go` — a tényleges fájlt a klónban olvasd); `c7550` → `.../docs/design/primitives-alignment.md`. Ha egy `file_path` eltér: az index elcsúszott, **ne használd**, és rögzítsd a `claim-evidence.md`-ben.
4. **A KB határai (ez a spec írásakor mért tény, ellenőrizd újra a `kb_status`-szal):** a KB **2026-10-16-i** állapotot tartalmaz; a modul benne a `5d0a327` commitnál áll (az `#33` és `#34` **előtt**), a Relay a `55a899f`-nél; a **`cic-primitive-forms` nincs a KB-ban** (`search_nodes("cic-primitive-forms")` üres), és a **`cic-schema-registry` sincs a források között**. Ezért **a KB nem bizonyíték a jelenlegi implementációra**: tervezési kontextus. Ha a KB és a klón eltér, **a klón számít**; egy KB-ból vett állítás státusza legfeljebb `concept` vagy „nem igazolt”, amíg kóddal nem támasztod alá.
5. Minden KB-ból vett állítás a `claim-evidence.md`-ben külön jelölést kap: `Forrás: KB c#### (file_path)`.

## Forrás — konkrét helyek (ezeket olvasd, ne grepből következtess)

Klónozd a workspace-be (csak olvasásra, **soha ne pushold őket**): `git clone git@github.com:CentralInfraCore/cic-module-oracle-cloud.git` (ág: `devel`), `git clone git@github.com:CentralInfraCore/cic-primitive-forms.git` (ág: `main`), `git clone git@github.com:CentralInfraCore/cic-primitives.git` és `git clone git@github.com:CentralInfraCore/cic-schema-registry.git`. A modul és a Forms **HEAD**-jét jegyezd fel (`git rev-parse HEAD`); a Forms legyen legalább `2f02a75` (a `d43ffc2` Go-parser javítást és a P5 admission-szerződést tartalmazza); ha nem az, jelezd.

**A pinek (kötelező, az integráció bizonyíthatóságának alapfeltétele).** A `cic-primitives` és a `cic-schema-registry` **nem mozgó ágon** vizsgálandó, hanem azon a commiton, amelyre a Forms épül. **Olvasd ki a Forms `corpus/pins.yaml` fájljából** a pontos pineket (név, `repo`, `ref`, `commit`, `manifest_sha256`), és állítsd be a klónokat azokra (`git checkout --detach <commit>`). A spec írásakor a Forms `2f02a75` állapotában a fájl ezt tartalmazza (**ellenőrizd, ne vedd át**): a grammar-pin `cic-primitives-73ae469-6a188078` (repo `cic-primitives`, ref `devel`, commit `73ae4692f0680a316d367179ce057195a0031688`), és a `registry-network-interface` és a `registry-network-space` pin (repo `cic-schema-registry`, commit `6db77d4dca4ce3af3be66b3a7a85404fd0b63684`). Ha a fájl más értéket tartalmaz, **a fájl az irányadó**, és az eltérést jelezd. Ha egy pinelt commit nem érhető el: `NOT MEASURED`, nem „megfelelt”.

**A leltár, a séma-elérhetőség (C) és a leképezés lefedettsége (E) a pinelt commitokra épül**, a modul `oci-sdk.lock.yaml`-jának SDK-pinjére (olvasd ki a verziót) és a Forms rögzített commitjára. A `baseline.md` elején legyen **Pin-tábla**: komponens | a pin forrása (fájl:sor) | a pin | a ténylegesen vizsgált commit | a jelenlegi HEAD | `git rev-list --count <pin>..HEAD` | a pin óta változott-e a releváns útvonalakon (`git diff --stat <pin>..HEAD -- <útvonal>`). A jelenlegi HEAD-eket **külön összehasonlítási adatként** rögzítsd; **a pin óta történt változás nem írja felül a pinelt állapotról tett állítást**, és nem cseréli le azt. Ha két komponens eltérő szerződésverzióra építene (pl. a Forms egyik, az Oracle-leképezés másik primitív- vagy registry-commitra), azt **kifejezett leletként** rögzítsd.

A **CIC-Relay** külön repo, **READ-ONLY, soha nem szerkeszted**; olvasd a `${CIC_RELAY_PATH}` alatti forrást (a `/home/sinkog/sync/git.partners/CentralInfraCore/CIC-Relay` élő checkoutja). **Relay-állítás előtt a forrást olvasd, ne grepből következtess**; jegyezd fel a Relay commitját is, és hogy a checkout melyik ágon áll.

**Oracle modul** — olvasd: `module/provider.go`, `module/contracts.go`, `module/correspondence.go`, `module/observed.go`, `module/oci_sign.go`, `module/abi.go`, `module/envelope.go`, `module/schemas/core/{vcn,subnet,instance}.json`, `tools/oci-extract/`, `oci-sdk.lock.yaml`, `docs/design/specs/provider-abi.md`, `docs/design/specs/oci-schema-pipeline.md`, `docs/design/specs/state-model.md`, `docs/design/relay-requirements.md`, `docs/design/manual-verification.md`.

**Forms** — olvasd: `go/` (a tényleges exportált API: `Parse`, `CompileSchema`, `Validate`, `Expand`, `Normalize`, `NormalizeWithPolicy` vagy aktuális megfelelője, `PolicyResolution`, a canonical path, origin és schema-binding típusai), `rust/src/`, `docs/P1-SUPPORTED-SUBSET.md`, `docs/P5-ADMISSION-CONTRACT.md`, `docs/ecosystem-map.md` ha van, `corpus/pins.yaml`, az elfogadott ADR-ek (`docs/adr/`), a konformanciakorpusz (`testdata/`).

**Primitives és séma-registry** — a `cic-primitives` a normatív primitívek forrása, a `cic-schema-registry` a NetworkSpace séma forrása; mindkettő a fent kiolvasott **pinelt commiton**. **Ne találj ki új primitive-mezőt, enumot vagy grammar-verziót.**

## Státusz-definíciók és az ellenőrzési módszerük

Minden állításhoz háromszintű státusz kötelező, **és a státuszt módszerrel kell bizonyítani, nem leírással**:

- **implemented** — production kódban hívódik **és** tesztek fedik. Bizonyítás: a hívási lánc ellenőrzése a production kódban: `grep -rn "<Szimbólum>" --include="*.go" | grep -v "_test.go"` — legalább egy production hívó, **fájl:sor megadva**; VAGY a `deadcode ./...` kimenete a mérési output része (ha a szimbólum nem szerepel benne, elérhető). Rustban a megfelelő hívási lánc (`rg "<szimbólum>" rust/src`, tesztek nélkül). **Nem elég**: „a függvény létezik", „a teszt zöld", „a dokumentum szerint megvan".
- **scaffold** — kódban van, de szándékosan bekötetlen, vagy feltételes elágazás mögött él (`if X == nil`, `if !Flag`, egy build-tag, egy opt-in env változó mögött). Bizonyítás: add meg a feltételt (fájl:sor), és hogy melyik production útvonal éri el, melyik nem. Ha a production hívási láncban 0 találat van `_test.go` nélkül → scaffold.
- **concept** — csak dokumentált (design, spec, ADR), kódja nincs. Bizonyítás: a keresés eredménye (0 találat a production kódban) és a dokumentum helye.

Ha a státuszt nem tudod fájl- vagy node-szinten alátámasztani, **ne mondd ki tényként**; írd: „nem igazolt", és hogy mi kellene hozzá.

## Tiltott rövidítések — ezek NEM fogadhatók el bizonyítéknak

- ❌ „a fájl létezik" ≠ implemented · ❌ „a teszt lefedettsége 8x%" ≠ implemented · ❌ „a README/spec/KB leírja" ≠ implemented
- ❌ „zöld CI" ≠ a lánc működik · ❌ exit code 0 ≠ sikeres mérés (olvasd el a kimenetet)
- ❌ A `module/schemas/core/vcn.json` **nem primitives-séma** — OCI-ból származó JSON-séma; ne nevezd annak.
- ❌ A Forms `state_surface`-t **nem validál** (szándékosan kívül esik a hatókörén): ne írd, hogy „a Forms validálja a state-et", ha a kód nem ezt mutatja. A hiányzó visszaolvasási képesség **nem `null`**.
- ❌ Ne írj olyan százalékot, amelynek a nevezőjét, kizárásait és mérési parancsát nem adod meg.
- ❌ Ne csinálj mockot vagy kézi adaptert egy hiányzó leképezés elfedésére; a hiányt rögzítsd coverage rekordként.
- ❌ A P5 admission-szerződés **dokumentált terv, nem production kapu**: ne írd, hogy a rendszer már admission-t végez.

## Feladat

### A. Oracle modul leltár
1. Mind a nyolc provider-művelet **tényleges** állapota (`implemented`/`scaffold`/`concept`) a fenti módszerrel: hívó fájl:sor a production kódban, és a teszt, amely meghajtja. A `deadcode ./...` kimenete (a `module/` és a `tools/oci-extract` alatt) kerüljön az outputba.
2. A ténylegesen támogatott, tesztekkel igazolt resource-készlet **újramérése** (a várt: VCN, Subnet, Instance — de **mérd meg**, ne vedd át): resource | szerződés fájl | operációk | hívó fájl:sor | tesztek | valós-OCI igazolás (`manual-verification.md`).
3. A `primitives-alignment.md` két, nem újraellenőrzött állítása: (a) „nincs kódszintű kapcsolat a `cic-primitives`/`cic-yang` felé", (b) „a Relay forrásában nincs `cic-primitives` hivatkozás". Mérd újra (`grep -rn` a modulban, `_test.go` nélkül; a Relay forrásában **olvasással**), és rögzítsd az eredményt dátummal és commitokkal.

### B. Forms API leltár
**Verzió, commit-pin, licenc és függőségkezelés (kötelező része a leltárnak):** a Forms jelenlegi verziója és a rögzített commit (`git rev-parse HEAD`, tagek, `go.mod`/`Cargo.toml` verziómezői); a Forms licence (`LICENSE.md`, SPDX-fejlécek: a tartalma vegyes, az átvett eszközei más licencűek lehetnek — idézd); és **hogyan hivatkozhatná a modul a Forms kódot** (**csak mérési és döntés-előkészítési feladat: a `go.mod`, `go.sum`, `Cargo.toml` fájlokat egyik repóban sem módosítod**): Go modul-verzió (a modul `module/go.mod`-ja mit tartalmaz ma, milyen modulútvonalon áll), `replace`, vendor, vagy más — a lehetőségeket és korlátaikat sorold, **döntést nem hozol**. Mérd meg a **TinyGo/WASM-fordíthatóságot** egy **scratch könyvtárban a repókon kívül** (ne a klónokban): lefordul-e `tinygo build -target wasi` (a modul `mk/wasm.mk`-ja szerinti célponttal) egy minimális programmal, amely csak a Forms Go csomagjának a szükséges típusait importálja; mik a közvetlen és közvetett függőségei (pl. a YAML-könyvtár), és mekkora a kimeneti `.wasm`. Ha a TinyGo nem érhető el a környezetben, írd: „nem mérhető" és hogy mi kellene hozzá. (A központi Forms-motor **nem** kerül a WASM-ba — ez a mérés csak azt mondja meg, hogy a modul mit tudna biztonságosan importálni.)

A tényleges Go (és a Rust megfelelő) **függvényaláírásokat és adatszerkezeteket a kódból olvasd ki**, ne emlékezetből: `Parse`, `CompileSchema`, `Validate`, `Expand`, `Normalize`, `NormalizeWithPolicy`, `PolicyResolution`, a canonical path, origin és schema-binding típusai. Táblázat: függvény | aláírás (fájl:sor) | mit fogad és ad | hol hívódik a Forms **saját** production kódjában (fájl:sor) | státusz. A `docs/P1-SUPPORTED-SUBSET.md` és az ADR-ek alapján add meg, mit **nem** támogat (explicit: `state_surface`, nem támogatott YAML-konstrukciók).

### C. Séma-elérhetőség és szerepek
Állapítsd meg, **melyik séma melyik szerep** (lásd `forms-integration-direction.md` 3.1): az **intent (config) séma** (a NetworkSpace a registry-ből, Forms-szel fordítható-e a pinelt commiton: bizonyítás: a Forms saját tesztje/korpusza, fájl:sor), a **provider-szerződés** (`module/schemas/core/*.json`, az extractorból), és a kettő közti **leképezés**, ha létezik valahol. **Ha a leképezésnek nincs kódbeli helye, az a lelet — ne találj ki helyette.** Tartalmazza-e a NetworkSpace config-felülete mindazt, amit egy VCN intenthez a modul szerződése megkövetel? (mező-szintű egyezés-tábla, a hiányokkal.)

### D. Relay határ (READ-ONLY leltár)
A jelenlegi WASM host határ, a modulbetöltés és a `Call` ABI, a schema/module registry, a capability manifest, a `cic-flow.sign` és `cic-flow.actuate` tényleges állapota, a trust-flow és az egress policy kapcsolódása. Forrást **olvass**. Ha Relay-oldali implementáció hiányzik, a követelményt az `output/relay-requirements.md`-be írd: `requirement ID | érintett fájl (Relay) | jelenlegi viselkedés | szükséges viselkedés | negatív teszt | elfogadási feltétel`. **A Relayt nem módosítod.**

### E. Szerződés-leképezés lefedettsége (nem a leképezés megvalósítása)
A VCN-re, majd a Subnetre és az Instance-re (**csak a már szerződéssel bíró készlet**): mező-/operáció-szinten az `output/contract-mapping.md` táblája: intent mező | provider mező | irány (előre/vissza) | policy (`x-cic-policy`: mutable, create-only, computed, action-managed, input-only) | hiányzó/null/default kezelése | OCID-azonosítás | implementációs coverage (`implemented`/`scaffold`/`concept` + bizonyíték) | megjegyzés. A nem implementált képesség **explicit szerződéses tény**: sorként szerepel, nem marad ki. **Ne írj kódot, ne vezess be új intent/state ágat** — a meglévő `effective_config`/correspondence modellt vedd alapul.

### F. Minőségi szintek — Stage 0 mérés (a `forms-integration-direction.md` 5. szakasza szerint)
Minden szintre (Q0–Q9) rögzítsd a **mért** állapotot a modulra, **a mérési parancs, a nevező és a kizárások megadásával**:
- Q0 és Q1: a modul tényleges CI-jéből (`.github/workflows/ci.yml`, `mk/golang.mk`, `mk/wasm.mk`) olvasd ki, mit futtat a CI, és ha az eszköz elérhető, futtasd le az eldobható másolatban a CI-vel azonos parancsokat (`gofmt -l`, `go vet`, `staticcheck`, `govulncheck`, `go test` a `module/` és a `tools/oci-extract` alatt); a kimenet az output része.
- Q2 sorlefedettség: `go test -cover` (és `-coverprofile`) a `module/` és a `tools/oci-extract` alatt; add meg a fájlokat és a kizárásokat. A dokumentum 82,7%-ot és 88,7%-ot mért 2026-11-07-én: **mérd újra a rögzített commiton**, és jelezd az eltérést, ha van.
- Q3 ágazati lefedettség: létezik-e újrahasználható **Go** ágazat-lefedettségi eszköz? (A Forms `cic-branch/1` eszközének hatóköre: olvasd el a Forms repóban, ne emlékezetből.) Ha nincs, mondd ki: „nem mérhető".
- Q4 mutáció: **csak megvalósíthatósági próba** (nem teljes futás): telepíthető-e/fut-e a `go-mutesting` a modulon egy fájlra, hány mutánst ad, mennyi ideig tart, mennyi élt túl. Ne állíts mutációs pontszámot a modulra, amit nem mértél.
- Q5–Q9: a Forms oldali forrásdokumentumok (`QUALITY-SHARDING.md`, `DELTA-DIFF-GATE.md`, `FAST-FULL.md`, `TEST-EVIDENCE.md`) és a modul tényleges CI-je (`.github/workflows/ci.yml`, `mk/*.mk`) alapján: mi van, mi nincs.
- **Licenc:** állapítsd meg és idézd a modul és a Forms licencét (`LICENSE.md`), és hogy a Forms eszközeinek (diff-kapu, mutációs futtató, quality gate) átvétele megengedett-e; javasolj hivatkozást/pinelt letöltést, ha a másolás nem egyértelmű. **Döntést nem hozol.**

## Mérési fegyelem, környezet és prioritás

**Reprodukálható, nem szennyező mérések.** A vizsgált klónok követett fájljait **nem módosíthatja** semmilyen mérés. Ezért: a lefedettségi, `deadcode`, `go vet`/`staticcheck`/`govulncheck`, mutációs és TinyGo/WASM mérések **eldobható munkakönyvtárban** futnak, amelyet a vizsgált commitból hozol létre (`git -C <klón> archive <commit> | tar -x -C <tmp>`), és minden kimeneti fájl (`-coverprofile`, `outcomes`, `.wasm`) **a repókon kívüli útvonalra** kerül. A `go mod tidy`, `go get`, `GOFLAGS=-mod=mod` csak ebben a másolatban használható. **Minden érintett klón végén** futtasd a `git -C <klón> status --porcelain` és `git -C <klón> diff --stat` parancsot, és az eredményt (üres vagy sem) **idézd az `agent-output.md`-ben, klónonként**. Ha nem üres: rögzítsd pontosan, mi változott és miért; csak a **saját, véletlen módosításodat** állítsd vissza, fájlonként, célzott paranccsal, és naplózd. **Tilos** a `git reset --hard`, `git clean`, `git checkout -- .` és minden automatikus visszaállítás, amely más, már létező munkát eltüntethetne.

**A mérési környezet rögzítése** (a `baseline.md` elején): `go version`, az OS és a kernel, az eszközök verziója (`tinygo`, `go-mutesting`, `deadcode`, `staticcheck`, `govulncheck`, `docker`, ha használod), és a **hálózati hozzáférés** (`go env GOPROXY`, el tudod-e érni a Go modul-proxyt és a GitHubot). A `module/` mérése a `wazero` letöltését igényli: ha hálózat nélkül nem fut, az eredmény **`NOT MEASURED`**, nem PASS, és meg kell írni, mi kellene hozzá.

**Az el nem végzett vagy el nem végezhető mérés eredménye `NOT MEASURED` (ok és a szükséges feltétel megadásával), soha nem PASS és soha nem hallgatás.** A `claim-evidence.md` Státusz oszlopa ezt az értéket is használhatja.

**Prioritás és keret** (a `max_turns` korlát véges): **A, B, C és D kötelező**, ezekkel kezdj; majd E; **az F szakasz utolsó**, a rendelkezésre álló keretben, a mutációs megvalósíthatósági próba az F legvégén. Ami a keret kimerülése miatt nem készül el, az `NOT MEASURED`.

## Output (a `cic-factory` klónban, `jobs/forms-oracle-provider-integration-01a/output/`)

- `output/baseline.md` — a repók és a rögzített commitok; az Oracle modul, a Forms API (verzió, commit-pin, licenc, függőségkezelés, TinyGo-fordíthatóság), a Relay határ leltára (A, B, D); a Q0–Q9 Stage 0 mérés (F), a nevezőkkel; a licenckérdés.
- `output/contract-mapping.md` — a séma-szerepek és a mező-szintű egyezés-tábla (C), a leképezés lefedettsége (E), explicit coverage rekordokkal.
- `output/relay-requirements.md` — a hiányzó Relay-követelmények a megadott oszlopokkal (D).
- `output/claim-evidence.md` — **minden állításhoz** egy sor: `| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |`. A Bizonyíték oszlop konkrét fájl:sor, commit, parancs és a parancs kimenetének idézete; „nem igazolt" is megengedett státusz.
- `output/agent-output.md` — rövid, tényszerű összefoglaló: mit mértél, mi hiányzik, mi a következő legkisebb lépés (**csak igazolt eredmények alapján**), és válaszok a „Kötelező beszámoló" kérdéseire.

## Ellenőrizhető elvárások (ezt az orchestrátor közvetlenül ellenőrzi)

1. Minden `implemented` szimbólum mellett production hívó **fájl:sor** vagy a `deadcode` kimenet — nem az agent állítása.
2. A `claim-evidence.md` minden sorában a Bizonyíték oszlop kitöltött; az orchestrátor mintát vesz és újrafuttatja a megadott parancsot.
3. Minden mért szám mellett a parancs, a nevező és a rögzített commit szerepel; az orchestrátor újramér egyet.
4. A Forms függvényaláírások a kódból idézettek (fájl:sor), nem összefoglalók.
5. A séma-szerepek táblája kimondja, melyik séma primitives-séma és melyik nem.
6. A `relay-requirements.md` minden eleme Relay-forrásból vett bizonyítékot (fájl:sor) hordoz.

## Biztonsági és végrehajtási határok

Nincs valós OCI hívás (sem read, sem write), nincs tenancy-módosítás, IAM-policy, Vault-kulcs vagy credential-export; nincs SDK-frissítés vagy SDK-sweep; nincs Relay-módosítás; **nem módosítasz kódot, sémát, CI-t vagy `docs/**`-t egyik repóban sem**. A `manual_real_oci_test.go` **nem futtatható**. Ha egy méréshez felhőhozzáférés kellene, írd le a pontos receptet, de ne hajtsd végre.

## Git

**`cic-factory`** — csak az `output/` dokumentumok, a `feature/forms-oracle-provider-integration-01a` ágra. A többi repó klónját **ne commitold és ne pushold**; a klónok végső állapotát a „Mérési fegyelem” szakasz szerint ellenőrizd és idézd, **automatikus visszaállítás nélkül**.
- ❌ NE pushol `main`-re, `devel`-re · ❌ NE nyiss PR-t · ❌ NE merge-elj
- Vault-aláírt commitok; `git add -A` tilos (csak a konkrét output fájlok).

## Kötelező beszámoló (az `agent-output.md`-ben, válaszonként bizonyítékkal)

1. Mely Forms-függvények élnek production hívási láncban (a Forms saját kódjában), és melyek csak tesztből érhetők el?
2. Mely OCI operációk élnek a modulban production lánccal, és melyekhez van valós-OCI igazolás?
3. Létezik-e a NetworkSpace → OCI VCN leképezés kódban valahol? Ha nem, hol a legkisebb, bizonyított hely, ahová illene?
4. Mely mezők és képességek nem implementáltak a VCN, Subnet, Instance szerződésben?
5. Mit mérsz a modul Q0–Q9 szintjein, és mi `NOT MEASURED` (miért, és mi kellene hozzá)?
6. Mi hiányzik még a Relayből a production működéshez (a requirement ID-k)?
7. Mi a pin-tábla (a pinelt és a jelenlegi commitok), és változott-e a pin óta bármi a releváns útvonalakon? Mi a klónok végső `git status --porcelain` eredménye?
8. Mi a legkisebb következő feladat (01b), amely érdemben csökkenti a fennmaradó kockázatot — **csak igazolt eredmények alapján**?

Ha bármelyik pont nem teljesül, **ne minősítsd teljes GO-nak az eredményt**: adj részletes PARTIAL/HOLD státuszt.

## Nyelvi szabály

Ez az `input.md` és a gondolkodásod magyar. Az `output/*.md` **magyar**. Ami valamelyik modul- vagy Forms-repóba kerülne (nem kerül semmi), angol lenne.
