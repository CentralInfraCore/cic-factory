# #162 — capability binding a modul/manifest hitelesítéséhez (MEGAKADT: a boríték nincs rögzítve a signing oldalon)

Alap: `CIC_Relay` `main@d38a1d5`; signing oldal: `CentralInfraCore/cic-module-oracle-cloud` `main@5d0a3278c6cc` (friss, sekély klón, nyilvános repó). Kód- és doksiváltozás **nincs**, ág/PR nincs.

## Miért álltam meg

Az input.md szerint: a boríték-formátumnak a signing oldalon kell léteznie; ha nem találom, megállok és jelzem. A signing oldalon van aláírás, de **nem az, amit az issue feltételez**, és nincs rögzített, verziózott boríték.

## Mit találtam (a signing oldalon, `file:line`)

- A fejlesztői aláírás (`metadata.sign`) `tools/infra.py` `_resign_with_build_hash` (`:254-287`): az aláírt halmaz **csak** `{name, version, checksum, build_timestamp, buildHash}`. A `checksum` a forrás **séma-spec**jének hash-e (`compute_spec_checksum(source_data["spec"])`, `infra.py:152`), nem a capability manifesté.
- A `capability_manifest` a `project.yaml` **felső szintű** kulcsa (`project.yaml:98`), nem a `metadata` alatt. Tehát a `metadata.sign` **sem közvetlenül, sem a checksumon át nem fedi** a manifestet (egress engedélylista, secrets bejegyzések): egy szélesebb egress a `metadata.sign` érvénytelenítése nélkül szerkeszthető.
- Van egy másik aláírás is: `cicSign` (`tools/finalize_release.py:244-260`), amely a **teljes dokumentum** kanonikus hash-ét írja alá (`json.dumps(sort_keys, separators=(",", ":"), ensure_ascii=False)`, base64 SHA-256, a `cicSign` mező üres). Ez fedné a manifestet, de a fájl fejlécéből ("until a secure, closed-source build environment (relay) and a central signing API are available") ideiglenes eszköz; hogy a valódi `make release` útvonalon (`release.sh` → `infra.py`) fut-e, nem olvastam ki egyértelműen.
- Az aláírás kétféle: két különböző kanonikus formátum (`to_canonical_json` az `infra.py`-ban vs. `json.dumps` a `finalize_release.py`-ban), **verziójelölés nincs**, és a Vault-aláírás bemenete egy base64 hash-szöveg (`vault_service.sign(digest_b64, key)`), ami a Go oldalon pontosan reprodukálandó (prehash, aláírás-formátum) lenne.
- A Relay oldalon sincs szerződés: a `verifyBuildHash` (`cmd/relay/cic_flow_manifest.go:205`) csak a wasm sha256-ját veti a `metadata.buildHash`-hez; egyetlen éles hívó sincs.

## Következmény az issue-ra

Az issue 1. javaslata (detached aláírás wasm-digest + manifest-digest + kulcsidentitás felett) csak akkor ellenőrizhető a Relay-ben, ha a signing oldal ezt a borítékot **előbb** előállítja. Ma a manifestet semmilyen, a `make release` útvonalon biztosan futó aláírás nem fedi. A Relay-oldali ellenőrzés most két rossz között választana: (a) a `metadata.sign`-t ellenőrizné (hitelesítené a wasm-digestet, de a manifestet nem), ami hamis biztonságérzetet adna; (b) a `cicSign`-t, amelynek útvonala bizonytalan.

## Mi kell a folytatáshoz (döntés / signing-oldali munka)

1. **Egy rögzített, verziózott boríték** a signing oldalon (`cic-module-oracle-cloud`, `tools/infra.py`): legalább `{format_version, buildHash (wasm sha256), manifest_digest (kanonikus capability_manifest), key identity (a tanúsítvány SPKI-ja vagy fingerprintje)}`, egyetlen kanonikus szerializálással és dokumentált Vault-aláírási móddal.
2. Annak eldöntése, hogy ez a `metadata.sign` bővítése (visszafelé nem kompatibilis a meglévő release-ekkel) vagy új mező.
3. Utána a Relay-oldali ellenőrzés (a `verifyBuildHash` bekötése a `registerModuleCapability` elé, `prod`-ban elutasítás) és a negatív tesztek (a manifest utólagos szélesítése, wasm-csere, `moduleID` újrahasznosítás) írhatók.

Az issue "Open questions" pontjaira a válasz: az aláírás a `cic-module-oracle-cloud` release-eszközeiben létezik, de **a Relay-oldali ellenőrzés hiánya mellett a signing oldali boríték is hiányzik**.

## Amit nem tettem

Nem implementáltam Relay-oldali ellenőrzést egy ki nem mondott formátumra: egy ilyen a `metadata.sign`-t vagy a Python-kanonikusítást tükrözné, és a manifest-védelem látszatát adná anélkül, hogy a manifestet fedné. Ez a "magabiztos rossz kimenet" esete.

## Vizsgálat (2026-11-15): a `cic-primitives` Release Envelope v3 újrahasznosíthatósága

Forrás: `CentralInfraCore/cic-primitives` `devel@01cb30b` (friss sekély klón; a `main@411ce80` még csak envelope v2-t ír le). A #162 **HOLD marad**; ez vizsgálat, nem döntés.

Mit mond a szerződés:
- `docs/en/RELEASE-RECORD-CONTRACT.md` (**normatív vázlat**): `release.envelope: 3`; a `build_hash` az envelope 2 szabályát követi: **a teljes csomag, kivéve** `release.sign`, `release.build_hash` és `cic_countersign`. A rekord minden artifactról saját digestet hordoz az algoritmussal. A szerződés **nem változtat az aláírási mechanizmuson**, és kimondja: a rekord megfelelése nem jelenti a hitelességét; a trust gate-ek (külső horgony, aláíró jogosultsága, ellenjegyzés engedélyezése) külön, későbbi munka. A lefedettség állítás ott **még bizonyítandó** golden vektorokkal (a vektorok nélkül követelmény, nem bizonyított tulajdonság).
- `ai/DECISIONS.md` D-015: az envelope v1 **felsorolás-alapú** volt (`{createdBy, releasedBy, specs, validity}`), és emiatt a `kind`, `version`, `timestamp` aláíratlan maradt (mérve: a 0.1.5 → 9.9.9 átcímkézés tisztán hitelesített). A v2 **kizárás-alapú**, "hogy egy később hozzáadott mező ne maradhasson véletlenül aláíratlan".

Mit jelent ez a #162-re:
- **A modul-repó jelenlegi `metadata.sign`-ja pontosan a v1 hibát ismétli:** felsorolás-alapú halmaz (`{name, version, checksum, build_timestamp, buildHash}`, `tools/infra.py:263-269`), ezért a felső szintű `capability_manifest` aláíratlan marad. Ez a `cic-primitives`-ben már dokumentált és javított hibaosztály (D-015).
- **A szerződés elve újrahasznosítható:** ha a modul `project.yaml`-jára ugyanazt a kizárás-alapú szabályt alkalmazzák (az egész dokumentum, az aláíró tagok kivételével), akkor **egyetlen aláírás köti a wasm digestet (`buildHash`) és a capability manifestet**, verziót a dokumentum maga hordoz. Ez a kívánt kriptográfiai kötés és nem Relay-specifikus formátum.
- **Mi nem újrahasznosítható szó szerint:** a v3 specifikus tagjai (`specs[]`, `provenance.grammar_*`) a primitives-release dokumentumtípusra vonatkoznak; a modul-`project.yaml` más típus és más séma. Újrahasznosítható a *szabály* (kizárás-alapú lefedettség, deklarált envelope-verzió, artifact-digest) és az ellenőrzési sorrend, nem a mezőlista.
- **Előfeltételek az ellenőrzéshez a Go oldalon:** a `to_canonical_json` (`compiler.py:44`) pontos reprodukciója, a Vault-aláírás ellenőrzési módja (prehash, formátum), és golden vektorok a valódi kanonikusításra, hash-re és aláírás-ellenőrzésre (ugyanaz a követelmény, amit a szerződés maga támaszt). Ezek nélkül a Relay-oldali ellenőrzés hamis biztonságot adna.
- **A trust gate-ek ott is nyitottak** (külső horgony, aláíró jogosultsága): a boríték önmagában nem bizonyítja a hitelességet; ezt a #162 "érvényes tanúsítvány ≠ hiteles manifest" pontja miatt külön kell kezelni.

Javasolt következő lépés (signing oldali, nem Relay): a `cic-module-oracle-cloud` `infra.py` aláírt halmazát kizárás-alapúra cserélni a D-015 szerint, `release.envelope` mezővel, golden vektorokkal; csak utána írható a Relay-oldali ellenőrzés és a négy negatív teszt (manifest-szélesítés, wasm-csere, `moduleID`-újrahasznosítás, idegen modul érvényes tanúsítvánnyal).

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A modul `metadata.sign` felsorolás-alapú, ezért nem fedi a `capability_manifest`-et | verified (olvasat) | `infra.py:263-269`; `project.yaml:98` felső szintű kulcs; D-015 ugyanezt a hibaosztályt írja le v1-ként | Kódolvasás két friss klónban | közepes: futtatás nélkül |
| A `cic-primitives` envelope 3 szabálya kizárás-alapú és újrahasznosítható elvként | verified (olvasat) | `RELEASE-RECORD-CONTRACT.md` §4; D-015 v2 | Dokumentumolvasás (`devel@01cb30b`) | közepes: vázlat, golden vektorok nélkül |
| A v3 mezőlistája átvehető a modul-`project.yaml`-ra | **cáfolt** | A v3 tagjai a primitives-release típusra szólnak | Dokumentumolvasás | alacsony |

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A `metadata.sign` nem fedi a capability manifestet | verified (olvasat) | `infra.py:263-269` aláírt halmaz; `project.yaml:98` a `capability_manifest` felső szintű kulcs | Kódolvasás a friss klónban (`main@5d0a3278c6cc`) | közepes: futtatás nélkül, a `make release` teljes útját nem követtem |
| A `cicSign` a teljes dokumentumot fedi | verified (olvasat) | `finalize_release.py:244-260` | Kódolvasás | közepes |
| A `cicSign` a valódi release-úton fut | **nem igazolt** | A fájl fejléce ideiglenesnek mondja; `release.sh` → `infra.py` útvonalat nem követtem végig | — | magas |
| Van rögzített, verziózott boríték a signing oldalon | **cáfolt** | Két kanonikus formátum, verziójelölés nincs | Kódolvasás | magas |
| A `verifyBuildHash` nincs hívva éles úton | verified | `cmd/relay/cic_flow_manifest.go:205` definíció; hívó csak teszt (az issue állítása, nem ellenőriztem újra grep-pel) | az issue olvasata | közepes |
| A tanúsítvány érvényessége igazolja a manifestet | **cáfolt** | A manifest semmilyen igazolt aláírás alatt nincs | Kódolvasás | magas |
