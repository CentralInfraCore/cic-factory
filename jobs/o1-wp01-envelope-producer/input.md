# o1-wp01-envelope-producer — WP-01: a `ModuleReleaseEnvelope` előállítása (producer) a modul release-folyamatában, és a Vault-kulcs algoritmusának mérése

**Függőség:** WP-01: indítható a WP-00 mellett; a producer a WP-00 `executed` mérésére támaszkodik.

## Ki vagy: olvasd el először

**Te vagy a végrehajtó agent.** Nem te indítottad ezt a jobot, és nincs mire várnod: a lenti munka **a te dolgod, most**. Az orchestrátor a futásod után a kimenetedet és a feature-branch-et vizsgálja; te nem döntesz merge-ről, release-ről, aláírásról.

## Tulajdonosi felhatalmazás és határok (2026-11-27)

A tulajdonos jóváhagyta az O-1 wire freeze-t és az implementációs munkacsomagokat. **Engedélyezett:** feature-branch létrehozása a cél-repóban (`feature/<job-id>`), fejlesztői commit, push erre az ágra, **draft PR** nyitása. **Tilos:** védett ág módosítása, merge, éles release, valódi (Vault) aláírás, countersign, publikáció, biztonsági finding nyilvánosságra hozatala, production aktiválás, a CI- és proof-követelmények lazítása. Commit-üzenetben **nincs** `Co-Authored-By` vagy bármilyen AI-utalás; a commitok a gyár hookja szerint kapnak aláírást, ha a hook elérhető (ha nem, ezt jelentsd, ne kerüld meg).

## Normatív bemenetek (a klónodban, `jobs/o1-wp01-envelope-producer/ref/`)

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

## Output (kötelező fájlnevek, a `jobs/o1-wp01-envelope-producer/output/` alatt a klónodban)

- `output/report.md`: tartalmazza a **claim-evidence táblát** (oszlopok: Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat), a rögzített commitokat, a draft PR URL-jét, és külön szakaszokban: **mért / nem mért (UNVERIFIED) / nyitott blokkolók**.
- `output/evidence/`: a parancsok és kimenetek naplói (a negatív tesztek bevetett-hibás futásaival).
- Az **acceptance táblát** (lent) soronként töltsd ki: `PASS` / `FAIL` / `UNVERIFIED` / `BLOCKED`, bizonyítékkal.

## Git

Csak a feature branch-re pusholsz (`feature/o1-wp01-envelope-producer` a cél-repóban és a `cic-factory` klónban az `output/`-hoz). **Draft PR**-t nyiss a cél-repóra `--base` az alap-ágra (a `gh pr create` alapértelmezése eltérhet: add meg kifejezetten). Merge nem a te dolgod. Ne amendelj aláírt commitot.

## Nyelvi szabály

Dokumentáció, jelentés: **magyarul**. Forráskód, teszt, YAML, JSON, shell, kódon belüli komment: **angolul**.


## Feladat

**Első lépés: mérés, még kódolás előtt.** (1) A **tényleges fejlesztői (Vault) aláíró kulcs algoritmusa**: mérd meg a modul release-folyamatában használt Vault Transit kulcs típusát (`tools/infra.py` `_resign_with_build_hash` és a kapcsolódó Vault-hívások; a Vault **csak olvasható metaadat-lekérdezéssel** érhető el, **aláírást nem kérsz**, tokent nem írsz ki). Ha a kulcs típusa **nem** `ecdsa-p256-sha256` vagy `ed25519`, ez **célzott review-pont**: jelentsd, és **ne bővítsd csendben az allowlistet**; a többi munkacsomagot ez nem blokkolja. (2) A dependency-mérés: milyen függőségek kellenek az envelope-előállításhoz a modulrepóban.

**Ezután a producer** (a `ref/01-…md` §2–§3 és **§8 ENV-01/02/03** normatív szerint):
- a **manifest véglegesítése után** állítsd elő a `ModuleReleaseEnvelope` v1-et: `wasm_sha256` (nyers), `executed_wasm_sha256` (a **pinelt Relay-transzformáció** eredménye: ezt a WP-00 méri; amíg nincs, a producer a transzformációt **cserélhető, jelzett függésként** kezeli, és **nem** talál ki saját transzformációt), `manifest_digest` (a **teljes manifest-fájl nyers bájtjainak** sha256-ja), `signer{key_id (SPKI sha256), alg}`;
- az aláírt tartomány a **`CICMODENVv1`** byte-pontos formája (fix sorrend, ASCII, LF, kisbetűs hex), a `.sig` fájl egyetlen sor standard base64 + LF;
- a producer **az aláírást a Vault-ra delegálja**, de **ebben a jobban valódi aláírást nem végzel**: a producer logikáját **teszt-kulccsal** (mint a vektorokban) és a Vault-hívás **interfész mögötti, mockolt** megvalósításával teszteld; az éles Vault-aláírás **külön engedélyezési pont**;
- a `metadata.sign` meglévő jelentése **nem változik**; a `metadata.cicSign` tényleges lefedettsége **UNVERIFIED**: mérd meg, ha a repóból megállapítható, egyébként jelezd.

**Kimenet:** a producer a modulrepó `feature/o1-wp01-envelope-producer` ágán; tesztek: a producer kimenete a `ref/vectors` verifier-logikáján átmegy (a Python-referencia vagy a WP-00 Go-ja ellen; ha a WP-00 még nem kész, a Python-referencia a mérce, jelölve).

**Nem része:** valódi Vault-aláírás, countersign, release, a Relay-admission (WP-02).

## Elfogadási kapu (a job akkor `done`, ha az alábbiak mind PASS, vagy a FAIL/BLOCKED indokolva és jelentve)

Minden sor: bizonyíték (parancs + kimenet + `file:line`), a negatív tesztek **bevetett hibával és a megnevezett okkal** mérve.

| # | Kritérium |
|---|---|
| AC-01-1 | a Vault-kulcs algoritmusa megmérve és rögzítve (vagy `NOT MEASURED` + oka); eltérés esetén célzott review jelezve |
| AC-01-2 | a producer kimenete a vektor-verifier-en elfogadott; az **aláírás utáni manifest-szerkesztés** új envelope-ot igényel (negatív teszt a megnevezett kóddal) |
| AC-01-3 | az aláírt tartomány byte-pontos: duplikált/ismeretlen/hiányzó mező, CR, nagybetűs hex elutasított (a `ref/` parser-esetei) |
| AC-01-4 | a `.sig` kódolási hibái (szóköz, hiányzó LF, két sor) elutasítottak |
| AC-01-5 | valódi Vault-aláírás **nem** történt (a mock interfész és a teszt-kulcs bizonyítja) |
| AC-01-6 | minden negatív teszt a megnevezett okból bukik (bevetett hibával igazolva) |
