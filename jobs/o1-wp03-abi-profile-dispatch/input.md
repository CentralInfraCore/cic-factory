# o1-wp03-abi-profile-dispatch — WP-03: a hitelesített ABI-profil betöltése és a profil-alapú (generic) dispatch

**Függőség:** WP-03: párhuzamosítható; production aktiválása a WP-02 acceptance után.

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp03-abi-profile-dispatch/ref/`)

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

## Output (kötelező fájlnevek, a `jobs/o1-wp03-abi-profile-dispatch/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp03-abi-profile-dispatch` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

A `ref/02-…md` (**§2, §3, §7 ABI-01–05 normatív**) és a D-1/D-2/D-3 szerint:
- **profil-betöltő:** a profil artifact nyers bájtjainak sha256-ja a `profile_digest`; az operátori pinelt profil-lista (`(id, digest)`) ellen; ismeretlen/nem befogadott/nem hitelesített profil **elutasítás** (nincs fallback); a `CICABIPROFv1` aláírt tartomány verifikációja a **WP-02 admission-mechanizmusán** át (ha az még nincs kész, interfész mögötti, mockolt trust-bundle, jelölve);
- **szemantikai szabályok** (a JSON Schema nem fejezi ki): egyedi op-nevek; determinisztikus `effect_resolution` (a nem leképezett értékek a fail-closed `external-write`-ra esnek); feloldható séma-hivatkozások az operátori séma-tárból; `host_boundary` ⇔ `required_host_capabilities` konzisztencia; a profil-limitek az operátori korlátot nem lépik túl. A `ref/` `check_profile_semantics` referenciája a mérce: **minden hibakódot tesztelj**;
- **generic dispatch:** a Cabinet dispatch a profilból (a legacy négy op `init/process/get/notify` beépített profilja a Relay-ben marad); a manifest `abi.profile {id, digest}` pinelése, az eltérés elutasítás; a manifest op-készlete a profil részhalmaza;
- **az aktiválás**: ez a job **nem aktiválja production-ben** a generic dispatchet: a #162 acceptance (WP-02) után külön döntés; a kódot úgy add, hogy az aktiválás explicit kapcsoló mögött él, és az alapértelmezés a mai viselkedés.

**Nem része:** `sign+send` (WP-04), a ProofTrace (WP-05), a profil-artifact szerzése/aláírása a registry folyamatban.

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-03-1 | egy **második, szintetikus profil** befogadható Relay-kód változtatása nélkül |
| AC-03-2 | ismeretlen, nem befogadott `profile_digest`, vagy extra manifest-op elutasított a megnevezett kóddal |
| AC-03-3 | az ABI-01…04 és a limit-szabály mind hibakódja tesztelt (10 referencia-eset) |
| AC-03-4 | a legacy négy op viselkedése változatlan (a meglévő tesztek zöldek, és a hívási út bizonyítja) |
| AC-03-5 | az új dispatch alapértelmezetten **ki van kapcsolva**; kapcsoló + reachability bizonyíték |
| AC-03-6 | minden negatív teszt a megnevezett okból bukik |
