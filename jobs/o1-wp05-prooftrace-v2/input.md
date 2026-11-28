# o1-wp05-prooftrace-v2 — WP-05: ProofTrace V2 (`CICCHAINv2`), trace-on-failure, perzisztencia-objektum és független verifier

**Függőség:** WP-05: azonnal indítható; a host-interakció rekordot a WP-04 adja (addig mockolva).

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp05-prooftrace-v2/ref/`)

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

## Output (kötelező fájlnevek, a `jobs/o1-wp05-prooftrace-v2/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp05-prooftrace-v2` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

A `ref/04-…md` (**§3–§7b, §9 V2-01–03 normatív**) szerint. **Két külön rész, külön committal és külön bizonyítékkal:**

**A. Producer-oldal (Relay):**
- **`CICCHAINv2`** hash-input a `ref/` normatív leírása (V2-03: fix sorrendű, LF-lezárt `kulcs=érték` sorok; a szabad szöveg csak sha256-ként lép be; `null` literál; sortörést tartalmazó vagy nem ASCII érték elutasított; a `chain_hash` nem része a bemenetnek). A V1 (`CICCHAINv1`, `Checksum()`, a meglévő artifactok) **változatlan**; nincs konverzió; V1 nem elégíthet ki V2-osztályú állítást.
- **requested / executed identitás** (V2-01): a `requested` mindig létezik; az `executed` csak a végrehajtási fázis elérésekor; `rejection{phase, code}` a `REJECTED` lépésnél; `envelope_digest` az `authenticated` állapotban.
- **trace-on-failure:** a Cabinet lépés-ciklusa (ma a lépés-hiba trace nélkül tér vissza) `REJECTED`/`FAILED`/`ABORTED` futásról is artifactot ad (**önálló, külön tesztelt képesség**; a **meglévő** sikeres út viselkedése nem romolhat).
- **perzisztencia-objektum** (a hash-tartományon kívül; `artifact_chain_hash`-hez kötött; `persisted: true` csak attesztációval): a meglévő `ProofStatus` mintájára, a recorder jelentése alapján.

**B. Független verifier (a Relay kódjától elkülönülő modul/csomag):**
- `VerificationResult` (`ref/schemas/verification-result`): `evidence_verdict` és `acceptance` **külön állítás**; a négy dimenzió külön; `verifier{id, version, implementation_digest}` és `subject` kötelező. **A schema szerkezetet ellenőriz; a verifier TÉNYLEGESEN ellenőrzi** a perzisztencia-attesztáció kriptográfiai hitelességét és az `artifact_chain_hash`-hez kötést (AC-V2-12), és hogy a `implementation_digest` **deklarációja nem bizonyíték** (AC-V2-13: a verifier-azonosságot külön kell igazolni, jelezd, mit sikerült).
- a verifier a közös **chain-vektorokon** a producerrel azonos `chain_hash`-t számol (az **egyik** a másikat ellenőrzi: a két implementáció független legyen: a verifier ne importálja a producer hash-kódját).

**Nem része:** a host-interakció rekord előállítása (WP-04; itt a lista-digest **hivatkozása** és a hiányzó hivatkozás `UNRESOLVED_REFERENCE`); az evidence tárolás/export (O-5); production aktiválás.

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-V2-01 | a módosított profil eltérő `profile_digest`-et ad a lépésben |
| AC-V2-02 | az elutasított dispatch `REJECTED` artifactot ad, `executed` blokk, kimenet és host-interakció nélkül |
| AC-V2-03 | a megtagadott host-hívás a `host_interactions` listában `denied`-ként szerepel (a WP-04 rekordjából, vagy mockolva, jelölve) |
| AC-V2-04 | hiányzó evidence-hivatkozás `UNRESOLVED_REFERENCE`, nem `PASS` |
| AC-V2-05 | az evidence-perzisztencia hibája **nem** állítja, hogy a művelet nem történt meg (`execution` változatlan) |
| AC-V2-06 | `authenticated` csak `envelope_digest`-tel |
| AC-V2-07 | V2 rekord V1 tartományban és fordítva elutasított |
| AC-V2-08, 10 | a verifier a négy dimenziót és az `evidence_verdict` / `acceptance` állítást külön adja; a Relay-generált eredmény nem elfogadott verifier-állítás |
| AC-V2-09, 12 | perzisztencia-státusz `artifact_chain_hash` nélkül / attesztáció nélkül elutasított; az attesztáció **kriptográfiailag ellenőrzött** |
| AC-V2-11, 13 | `ALLOWED`/`DENIED` lépés `authorization_decision` hivatkozás nélkül elutasított; az `implementation_digest` deklarációja nem bizonyíték |
| AC-V2-14 | trace-on-failure: a meglévő sikeres út változatlan (a meglévő tesztek zöldek), az új ágak külön tesztelve |
| AC-V2-15 | a producer és a verifier chain-hash-e a közös vektorokon azonos, és a két implementáció nem oszt hash-kódot |
