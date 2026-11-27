# O-1 implementációs munkacsomagok: előkészített specifikációk (VÁZLAT, nem Factory job)

**Státusz:** a wire freeze és a WP-GO a tulajdonosi review javaslata (2026-11-27); **Factory job nem jött létre**, a tulajdonosi jóváhagyás a job-indításhoz külön pont. Ez a dokumentum a jobok **bemenete**: rögzített bemeneti commitok, acceptance kritériumok, függőségek. A normatív szöveg: `O1-REVIEW-BUNDLE.md` (sha256 `bad8e6bdaaac705e1f6f58a10edfcdaccf808ad363e52b87f0d8472c65164416`); ellentmondás esetén a **normatív korrekciós szakaszok** (01 §8, 02 §7, 03 §12, 04 §9) az irányadók.

## Rögzített bemenetek

| Bemenet | Érték |
|---|---|
| CIC_Relay | `86ea1ab30e1f234ab294e51385f6f51bbff0aff9` (mért alap; a job előtt rebase/ellenőrzés a friss `main`-re) |
| cic-module-oracle-cloud | `ae3c96237839c9fd06649c918a2194a79ebd8cb1` (`devel`) |
| wabin | `github.com/tetratelabs/wabin v0.0.0-20230304001439-f6f874872834`, `wasm.CoreFeaturesV2` |
| vektorok | `vectors/envelope-vectors.json`, `vectors/chain-and-interaction-vectors.json` (provizórius) |
| schemák | `decisions/o1-preparation/schemas/` (8) |

## Közös szabályok minden WP-re

pozitív **és** negatív bizonyíték; minden negatív teszt a **megnevezett okból** bukik (a hibakódot is egyezteti); hívási-út bizonyíték (`file:line` vagy deadcode-kimenet) minden "bekötött" állításhoz (reachability DoD); a production aktiválás külön acceptance; merge/release/aláírás a tulajdonosé.

## WP-00: közös vektorok reprodukálása
Bemenet: `vectors/`. Feladat: az envelope-vektorokat egy **második** implementáció (Go, a Relay oldalán) reprodukálja; a `wasm_executed` referencia-eredményt a wabin kimenetével vesse össze. Acceptance: 26/26 eset a várt hibakóddal; a wabin-eltérés külön jelentve (nem csendes igazítás).

## WP-01: envelope producer (modulrepó)
Első lépés: **a tényleges fejlesztői (Vault) kulcs algoritmusának mérése** (eltérés = célzott review, a többi WP-t nem blokkolja). Feladat: a `tools/infra.py` release-folyamata a manifest véglegesítése után előállítja az envelope-ot és a `.sig`-et (01 §8 ENV-01/02). Acceptance: AC-162-01…03, 05, 06 oldaláról a producer kimenete átmegy a WP-00 vektorok verifierén; a `metadata.sign` változatlan; a manifest utólagos szerkesztése új envelope-ot kényszerít. Függőség: WP-00 vektorai (párhuzamos).

## WP-02: Relay artifact admission (#162)
Feladat: 01 V1–V7, a regisztráció kulcsa `(module_id, envelope_digest)`; a tesztkulcsos vektorok a verifieren. Acceptance: AC-162-01…19 (a #162 négy tesztje + a kiegészítések), különösen: egyetlen beolvasás (14/14b), a `SetStripWasmModuleFunc` production-úton elérhetetlen (18), a `verifyBuildHash` hívási útja (09), a #155 viselkedése nem romlik (11). Függőség: WP-00; production aktiválás a WP-01 valódi artifactjaitól függ.

## WP-03: ABI-profile és generic dispatch
Feladat: profil-betöltő (02 §7 ABI-01…05, `check_profile_semantics` referencia), a Cabinet dispatch a profilból (D-1/D-2), a legacy négy op beépített profilja. Acceptance: egy **második, szintetikus profil befogadható Relay-kód változtatása nélkül**; ismeretlen/nem befogadott `profile_digest` elutasított; minden ABI-szemantikai hibakód tesztelve. Függőség: WP-02 (hitelesített identitás).

## WP-04: sign+send és Oracle guest migráció
Feladat: `cic-flow.send`, szűk Go signing-profile csomag (D-11), host-oldali célvalidálás (03 §12 SS-03, `validate_target` referencia), host-interakció rekord (SS-04), az Oracle `actuateSigned` migrációja. Acceptance: AC-SS-01…08; a guest sosem kap aláírást/`Authorization`-t; megfigyelési profilban írási kérés nem jut ki; az `ociprofile` a `core/...`-t nem importálja (függőségi teszt). Függőség: WP-03 (profil), WP-05 (rekord-interfész, közös).

## WP-05: ProofTrace V2 és trace-on-failure
Feladat: `CICCHAINv2` (04 §9 V2-03), requested/executed (V2-01), trace-on-failure a Cabinet lépés-ciklusában (önálló), perzisztencia-objektum, független verifier. Acceptance: AC-V2-01…13; a chain-hash a vektorokon azonos; a verifier a négy dimenziót, az `evidence_verdict`-et és az `acceptance`-t külön adja; a perzisztencia-attesztáció és a verifier-azonosság **ténylegesen** ellenőrzött (nem séma). Függőség: WP-04 (host-interakció rekord).

## Párhuzamosság és blokkolás

WP-00, WP-01, WP-03 (a profil-betöltő része) és WP-05 (hash/verifier része) a szerződések alapján párhuzamosan indítható; a production aktiválás sorrendje WP-02 → WP-03 → WP-04 → WP-05. A Vault-kulcs algoritmusának eltérése csak a WP-01 aláírás-részét érinti.

## Nem része (HOLD)
valódi release-aláírás, countersign, publikáció, disclosure, production aktiválás, merge/release; a `wasm-canon` átdefiniálása (backlog).
