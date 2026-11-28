# o1-wp00-vector-reproduction — WP-00: a közös kriptográfiai vektorok reprodukálása a Relay oldalán (Go), és a `wasm-canon/v1` valós, pinelt transzformációjának mérése

**Függőség:** WP-00: azonnal indítható.

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp00-vector-reproduction/ref/`)

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

## Output (kötelező fájlnevek, a `jobs/o1-wp00-vector-reproduction/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp00-vector-reproduction` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

**Cél:** a `ref/vectors/` provizórikus vektorait egy **második, Go-implementáció** reprodukálja, és a `wasm_executed` értéket a **tényleges, pinelt Relay-transzformációval** állítsd elő.

**Kulcsszabály (tulajdonosi döntés):** a normatív transzformáció a **meglévő** `wasm-canon/v1`: `github.com/tetratelabs/wabin v0.0.0-20230304001439-f6f874872834`, `wasm.CoreFeaturesV2`, decode → custom szekciók elhagyása → encode (`core/cabinet/validate.go`, `stripWasmModuleFunc`). A vektorokban lévő `wasm_executed_b64` a **referencia bájtszintű szekció-eltávolítás** eredménye, **nem normatív**. **Eltérés esetén a vektort kell korrigálni, NEM a Relay transzformációját a vektorhoz igazítani.** A Relay transzformációját ebben a jobban nem módosítod.

1. **A wabin-mérés.** Állítsd elő a minimális modul (`ref/vectors`: fejléc + egy custom szekció) és legalább három további, szándékosan eltérő bemenet (több custom szekció; nem-minimális kód; üres modul) `stripWasmModuleFunc` kimenetét a pinelt wabin-nel (go.mod/go.sum alapján feloldott verzió; **a tényleges feloldott verziót és go.sum sorokat rögzítsd**, ez zárja a „teljes feloldott dependency-gráf UNVERIFIED” pontot). Hasonlítsd össze a referencia-értékkel; ha eltér, a különbséget **jelentsd**, és állítsd elő a **korrigált vektor-javaslatot** (a `wasm_executed_b64` és a függő `executed_wasm_sha256`; az aláírt tartomány miatt az envelope-vektorok aláírásait újra kell képezni: a generátor `ref/vectors`-hoz tartozó logikáját a `ref/` leírás adja, a korrigált vektorokat **Go-ban vagy a mellékelt Python-referenciával** állítsd elő, és jelöld, melyiket).
2. **Az envelope-vektorok Go-reprodukciója.** Egy Go-teszt töltse be `ref/vectors/envelope-vectors.json`-t (vagy a korrigált változatot), és **minden esetre** a referencia-verifier lépéseit futtassa (verzió → forma → algoritmus↔kulcstípus → `key_id = sha256(SPKI)` → aláírás-kódolás → aláírás → nyers digest → futtatott digest → manifest digest). **A várt hibakódot is egyeztesd** (nem csak az elutasítást).
3. **ECDSA: két külön követelmény.** (a) a **rögzített** aláírás **ellenőrzése** (determinisztikus, minden futásban); (b) **új** aláírás előállítása a teszt-kulccsal és ellenőrzése. **Nem követelmény**, hogy két érvényes ECDSA-aláírás bájtra azonos legyen. Az Ed25519 esetek bájtra reprodukálhatók.
4. **A kulcsfüggetlen vektorok** (`chain-and-interaction-vectors.json`): a `CICCHAINv2` hash-input és hash, a host-interakció lista digest és a profil aláírt tartomány Go-reprodukciója (a `ref/` 03 §12 SS-04 és 04 §9 V2-03 normatív leírása szerint); ha a Go-implementáció eltér a referenciától, ez **mért lelet**, nem csendes igazítás.
5. **A kimenet:** a Go-teszt a Relay-repo feature-branch-én (`feature/o1-wp00-vector-reproduction`), egy **vendorolt vektor-korpusz** (a forrás-digestjével rögzítve), és a jelentés a **korrigált vektorokkal** (ha kellett).

**Nem része:** a Relay transzformációjának módosítása; valódi aláírás; a `Checksum()` változtatása; a #162 admission (WP-02).

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-00-1 | az envelope-vektorok mind a várt hibakóddal reprodukálódnak Go-ban (n/n a tényleges esetszámból) |
| AC-00-2 | a `wasm_executed` a **pinelt wabin** kimenetével összevetve: egyezés **vagy** dokumentált eltérés + korrigált vektor-javaslat |
| AC-00-3 | a feloldott wabin-verzió és go.sum sorok rögzítve (a dependency-gráf UNVERIFIED lezárása vagy pontos jelzése) |
| AC-00-4 | ECDSA: rögzített aláírás ellenőrzése és új aláírás előállítása külön tesztekben |
| AC-00-5 | a chain/interakció/profil vektorok Go-ban reprodukálva, vagy a lelet jelentve |
| AC-00-6 | minden negatív teszt a megnevezett okból bukik (bevetett hibás futással igazolva) |
