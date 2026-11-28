# o1-wp04b-module-send-migration — WP-04b: az Oracle modul cic-flow.send migrációjának újraportolása a devel ae3c962 bázisra

**Függőség:** a modul-oldali bázis a `devel` `ae3c96237839c9fd06649c918a2194a79ebd8cb1`; a Relay `pkg/hostsign` (#232) és a WP-04 saját delta (`ref/`) a bemenet. A Relay integrációs feladatoktól független, párhuzamosan futhat.

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp04b-module-send-migration/ref/`)

- A **normatív szöveg** a `ref/` alatti dokumentumok **korrekciós szakaszai** (01 §8, 02 §7, 03 §12, 04 §9); ahol egy korábbi szakasz ellentmond nekik, a korrekció az irányadó. A wire formátumok **elfogadottak (freeze)**, nem terveződnek újra; új architekturális kérdést csak **konkrét, mért blokkoló** esetén nyiss (a jelentésben, nem csendes döntésként).
- Rögzített alap: **CIC_Relay** `86ea1ab30e1f234ab294e51385f6f51bbff0aff9` (a `main` ágon); **cic-module-oracle-cloud** `ae3c96237839c9fd06649c918a2194a79ebd8cb1` (`devel`). Ellenőrizd, hogy a friss HEAD mennyire tér el, és jegyezd fel; a munkát a rögzített alapra építsd, eltérésnél jelentsd.
- A wire séma-fájlok és példák: `ref/schemas/`, `ref/examples/`; a közös vektorok: `ref/vectors/` (**TESZTKULCSOS, PROVIZÓRIUS**: nem release-aláírások; ne tekintsd normatívnak a `wasm_executed` értéket, lásd WP-00).

## Boot sequence (a KB használata és határai)

1. `mcp__cic-graph__kb_status`: rögzítsd a build idejét és a `stale` jelzőt. Ha nem elérhető: `NOT MEASURED`, folytasd a kódolvasással.
2. `search_nodes` az `axioms`, `symbols`, `contract`, `limits` kifejezésekre (az eredményt akkor is rögzítsd, ha üres).
3. A KB **tájékozódás, nem bizonyíték**: kódállításhoz a forrást olvasd. Minden KB-ból vett állítás a `claim-evidence` táblában külön jelölést kap (`Forrás: KB c#### (file_path)`).

## Forrás: konkrét helyek

A CIC-Relay helyi példánya: `${CIC_RELAY_PATH}` (csak olvasásra, tájékozódáshoz); a munkát a **saját klónodban**, a `workspace/` alatt végezd. A Go-eszközlánc a gépen nem natív: **docker**-en át futtasd (`golang` image; a Relay `go.mod` verziójával), és rögzítsd a pontos parancsot és verziót a jelentésben.

## Tiltott rövidítések: ezek NEM bizonyítékok

- ❌ „a fájl létezik” / „a teszt zöld” / „zöld CI” ≠ implemented · ❌ exit code 0 ≠ sikeres mérés (olvasd a kimenetet) · ❌ százalék a nevező és a parancs nélkül.
- ❌ **Olyan teszt, amely nem tud elbukni.** Minden új negatív tesztről mérd meg bevetett hibával, hogy elbukik-e, **és hogy a megnevezett okból bukik-e**: egy elutasítás csak akkor bizonyíték, ha a várt hibakóddal/üzenettel történik.
- ❌ Teszt, amely a production útvonalat megkerülő segédfüggvényt hajt meg. ❌ A production viselkedés megváltoztatása a teszt kedvéért. ❌ „symbol létezik + teszt zöld” ≠ implemented: **reachability** kell.
- ❌ Provizórikus (vektor/referencia), komponensszintű és production-integrációs bizonyíték összemosása: a jelentésben **külön oszlopban** jelöld.

## Háromszintű státusz és reachability

Minden állítás `implemented` / `scaffold` / `concept`, módszerrel bizonyítva. **Reachability artifact kötelező** minden „bekötött” állításhoz: a production hívási lánc `file:line` formában (`grep -rn "<Szimbólum>" --include="*.go" | grep -v "_test.go"`) **vagy** `deadcode ./...` kimenet; a bizonyítást a kimenetben mutasd.

## Output (kötelező fájlnevek, a `jobs/o1-wp04b-module-send-migration/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp04b-module-send-migration` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

**Cél:** a WP-04 modul-oldali változásait (a Oracle guest átállítása a `cic-flow.send` host-képességre) **újra bevezetni a helyes, mechanikusan igazolt bázisra**, a `cic-module-oracle-cloud` `devel` ágára (`ae3c96237839c9fd06649c918a2194a79ebd8cb1`), a `devel` jelenlegi funkcionalitásának megőrzésével.

**A probléma (mért):** a #54 ága az `5d0a327` bázisra épült, a `devel`-től 63 commit-tal lemaradva, a PR `CONFLICTING/DIRTY`. A `ref/wp04-own-delta.patch` a #54 **saját** változása (12 fájl; a `module.wasm` bináris kihagyva), a `ref/o1-integration-findings-2026-11-28.md` a mérés. A `devel` azóta M3/M4a tervkötéssel, `createdResourceID` 202 kezeléssel, `pollTargetPath`-szal, `executeSteps`-szel és egy általánosított sign/actuate mock köré épített teszttel (`cicflow_mock_test.go`, kb. 15 tesztfájl, ~110 hivatkozás) bővült.

### 0. A Git-bázis mechanikus igazolása (kötelező, ELSŐ lépés; B-1..B-6 a `ref/factory-backlog-git-base-verification.md`-ben)

A jelentés **első szakasza** a következő parancsok **tényleges kimenetét** tartalmazza (szöveges állítás nem evidence):
`git merge-base <ág> ae3c96237839c9fd06649c918a2194a79ebd8cb1` (el kell érnie az előírt base-t, vagy az ág a leszármazottja), `git rev-list --count ae3c962..<ág>`, `git diff --stat <merge-base> <ág>`, `gh pr view <PR> --json mergeable,mergeStateStatus`. Új ág: `feature/o1-wp04b-module-send-migration`, a `devel` `ae3c962`-ből. **A #54 ágát nem írod át és nem force-pusholsz.** A záró PR a `devel`-re `MERGEABLE` kell legyen.

### 1. A tulajdonságok megőrzése, nem az assertion-helyek mechanikus másolása

**Egy régi tesztet sem töröl(sz) vagy lazítasz úgy, hogy az általa ellenőrzött szerződéses tulajdonság elvesszen.** A bizalmi határ áthelyeződött: az aláírandó karakterlánc, az `Authorization` fejléc és a dátum a **host signerben** keletkezik (Relay `pkg/hostsign`, `pkg/hostsign/ociprofile`), a guest strukturált `cic-flow.send` kérést küld. Ezért egyes régi assertionök új helye a Relay tesztje (pl. a kanonikus karakterlánc és az Authorization építése), nem a modul tesztje.

Készíts **claim–evidence megfeleltetést** (`output/claim-mapping.md`): minden meglévő, a sign/actuate mockhoz kötött teszt vagy assertion mellé írd: **(a)** mit állított (szerződéses tulajdonság), **(b)** hol van az új helye (modul-teszt az új send-mockkal, vagy a Relay `file:test`, vagy kikerült és **miért** semmi nem veszett el), **(c)** a bizonyíték. A tesztek száma és az assertionök helye változhat; az ellenőrzött tulajdonságok elvesztése **nem megengedett**.

### 2. A modul-oldali változások

- Send-képes host mock (új `cicFlowMock`-képesség); a meglévő 15 tesztfájl átírása az új kérés/válasz szerződésre (`ref/wp04-own-delta.patch` `host_mock_test.go`, `send_contract_test.go` kiindulás).
- A guest nem kap és nem épít aláírást, `Authorization`-t, dátumot, kanonikus karakterláncot, kulcsot; a `sign`/`actuate` import kikerül (az `abi.imports` a `cic-flow.send`-et tartalmazza).
- A `devel` funkcionalitása megmarad: M3/M4a kapuk, `createdResourceID` (a 202/Work Request ággal), `pollTargetPath`, `executeSteps` stb. **nem módosulnak** a migráció kedvéért, csak az aláírás/küldés útvonala.

### 3. SS-03 `poll` és `create` (nem szerződés-módosítás)

**A befagyasztott SS-03-at nem bővíted.** A `ref/ss03-poll-create-deviation.md` az eltérésleírás: a megfigyelési PoC-hoz sem a poll, sem a create nem kell. A modul `poll` és `create` hívásai a Relay-n `POLICY_PATH`/`POLICY_METHOD` elutasítást kapnak: **ezt célzott negatív teszt rögzíti** (a modul-tesztben a host elutasítását mockolva, és ahol lehetséges, a Relay `hostsign` ellen), nem elfedve. Az `observe` és az olvasó (GET) műveletek a megfigyelési profilban működnek.

### 4. A WASM-artifact (külön, három állítás)

Pinelt **TinyGo 0.39.0** (a modul `Dockerfile` `TINYGO_VERSION`, a helyi `cic-module-oracle-cloud-builder` image). **Három külön állítást** mérj és jelents, ne vond össze:
1. a committolt `module.wasm` sha256-ja = a `project.yaml` `metadata.buildHash` (`make wasm.integrity-verify`);
2. a pinelt környezetben, a forrásból újrafordított wasm **reprodukálható-e** (két egymás utáni build bájtazonos? `make wasm.repro-probe` / `wasm.rebuild-verify`), és ha nem, a különbség forrása;
3. az aktuális forrás megfelel-e a committolt wasm-nak (újrafordított digest = committolt digest).
Ha a TinyGo helyben nem futtatható, ez **UNVERIFIED**, nevesítve; ne állíts bizonyítottat.

### 5. Acceptance (lokális **és** központi)

A lokális "kész" állítás csak a **kötelező CI-kapuk lokálisan reprodukálható részének tényleges futtatásával** érvényes; a kihagyottat névvel, UNVERIFIED-ként jelentsd (`ref/factory-backlog-git-base-verification.md`, P-1..P-3 szellemében). A modul CI-je (`lint_and_test`, `docgate`) a **PR head SHA-ra** zöld legyen. A Relay-oldali `pkg/hostsign` mutation ratchet nem módosul ebben a jobban.

**Nem része (HOLD):** SS-03 módosítás, create/update/delete aktiválás, valódi Vault-aláírás, countersign, release, merge, production aktiválás.

## Elfogadási kapu

| # | Kritérium |
|---|---|
| AC-04b-1 | a bázis mechanikusan igazolt (merge-base = `ae3c962`, nincs elavult eltérés a PR-ban), a PR `MERGEABLE` |
| AC-04b-2 | a #54 saját delta-ja visszakövethetően átvezetve (`git log`/`cherry-pick -x` vagy leírt, indokolt kézi port) |
| AC-04b-3 | a `devel` meglévő tesztjei és funkcionalitása megőrizve; a `claim-mapping.md` minden régi tulajdonságra ad új helyet vagy indoklást |
| AC-04b-4 | a guest egyetlen host importja a `cic-flow.send`; nincs aláírás/`Authorization`/dátum/kulcs a guest-kérésben (a compiled artifacton ellenőrizve) |
| AC-04b-5 | `poll` és `create` célzott negatív teszttel elutasítva, a megnevezett kóddal |
| AC-04b-6 | a három WASM-állítás külön mérve (vagy nevesítve UNVERIFIED) |
| AC-04b-7 | lokális kapuk futtatva és jelentve (kihagyottak névvel), CI zöld a head SHA-ra |
