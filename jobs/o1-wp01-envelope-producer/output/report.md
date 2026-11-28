# o1-wp01-envelope-producer: jelentés (ModuleReleaseEnvelope producer, #162)

**Készítő:** az orchestrátor (a WP-01 jobot nem agent futtatta; a szám a saját futásaimból való). **A Vault-kulcs mérése, a producer, a tesztek és a hibabevetés elkészült; valódi Vault-aláírás NEM történt.**

## Rögzített bemenetek és eredmény

| Elem | Érték |
|---|---|
| cic-module-oracle-cloud alap | `ae3c96237839c9fd06649c918a2194a79ebd8cb1` (`devel`) |
| Draft PR | **https://github.com/CentralInfraCore/cic-module-oracle-cloud/pull/55** (`--base devel`) |
| Commit | `ae0e5fd` (a gyári hookon át aláírva, fejlesztői kulcs; nem release-aláírás) |
| Normatív bemenet | a befagyasztott O-1 szerződés (01 §2–§3, §8 ENV-01/02/03), a WP-00 végleges vektorai (`d8a2e058…`) |
| GitHub CI a PR fejére | **UNVERIFIED** (a PR most nyílt) |

## 1. A Vault-kulcs algoritmusának mérése (a job első lépése)

| Mérés | Eredmény |
|---|---|
| A kulcs neve | `cic-my-sign-key` (`project.yaml: vault_key_name`) |
| Transit-kulcs metaadata lekérdezése a fejlesztői aláíró tokennel (`GET /v1/transit/keys/…`, csak olvasás) | **permission denied**: a token csak aláírásra jogosult; aláírást **nem** kértem |
| A fejlesztői tanúsítvány (a saját aláírt commitjaim üzenetében) | **ECDSA P-256** (`id-ecPublicKey`, `prime256v1`), kibocsátó `CIC Developer CA`, `ecdsa-with-SHA256` |
| Következtetés | az algoritmus a megengedett `ecdsa-p256-sha256` halmazba esik; **a transit-kulcs típusát közvetlenül nem mértem: UNVERIFIED**. A producer önellenőrzése (aláírás + marshaling ellenőrzése a tanúsítvány kulcsával) kiszűri a hibás típust vagy marshalingot futásidőben |

**Nincs eltérés, nincs allowlist-bővítés, célzott review nem szükséges.** Ha a tényleges aláíráskor (külön engedéllyel) más típus mutatkozna, a producer elutasít.

## 2. Mit valósít meg

`tools/releaselib/envelope.py`: a `CICMODENVv1` aláírt tartomány (rögzített sorrend, ASCII, LF, kisbetűs hex), az envelope-fájl és az egysoros base64 `.sig`, **a bájtokból származtatva** (nyers wasm, futtatott wasm, a teljes release-manifest nyers bájtjai); `key_id` = a DER SPKI sha256-ja; algoritmus-allowlist. A producer a kimenetét **maga ellenőrzi** (aláírás, marshaling, digestek) visszaadás előtt, így az IEEE-P1363 marshalingot adó vagy más kulccsal aláíró signer itt bukik, nem a relay-ben. `vault_ecdsa_signer` a meglévő `VaultService.sign`-t (prehashed sha2-256 transit aláírás, `vault:v1:`) illeszti. A `executed_wasm_sha256` **bemenet** (a relay pinelt `wasm-canon/v1` kimenete): nem újraszámolt, a hibás érték a consumerben `EXECUTED_DIGEST_MISMATCH`. A manifest véglegesítése után készül az envelope (detached, nincs önhivatkozás). A `metadata.sign` és `metadata.cicSign` jelentése nem változott.

## 3. Acceptance

| AC | Státusz | Bizonyíték |
|---|---|---|
| AC-01-1 a Vault-kulcs algoritmusa megmérve és rögzítve | PASS (részben: tanúsítvány-alapú; a transit-metaadat nem olvasható) | 1. szakasz; a transit típus UNVERIFIED |
| AC-01-2 a producer kimenete a vektor-verifier-en elfogadott; az aláírás utáni manifest-szerkesztés elutasított | PASS | `test_ed25519_output_is_byte_identical_to_the_shared_vector`, `test_manifest_edited_after_signing_is_detected`, 26/26 vektor a várt kóddal |
| AC-01-3 az aláírt tartomány byte-pontos; duplikált/ismeretlen/hiányzó mező, CR, nagybetűs hex elutasított | PASS | `test_the_signed_domain_is_byte_exact`, `test_signed_domain_refuses_malformed_fields` (9 eset), `…needs_exactly_the_six_fields` |
| AC-01-4 a `.sig` kódolási hibái elutasítottak | PASS | a vektorok `signature-with-whitespace`, `without-final-lf`, `two-lines` esetei (ecdsa és ed25519) |
| AC-01-5 valódi Vault-aláírás nem történt | PASS | a Vault-kimenet `FakeVault`; a `GET` metaadat-lekérdezés elutasítva, aláírás nem kérve |
| AC-01-6 minden negatív teszt a megnevezett okból bukik | PASS | 13 bevetett hiba, mind a megnevezett teszten bukik (egyet kézzel újraellenőriztem, lásd lent) |

**Cross-implementation bizonyíték:** az Ed25519 kimenet **bájtra azonos** a megosztott vektorral (envelope és `.sig`), amelyet a relay consumere (#233) is a saját verifierén futtat: a producer és a consumer ugyanazt a bájtsort érti. Az ECDSA aláírások randomizáltak, ott az ellenőrzés a tárolt aláírásokra és a producer önellenőrzésére épül.

## 4. Kapuk és hibabevetés (helyi)

`pytest` az egész repón: **223 passed, 6 skipped**; `envelope.py` lefedettség 97%; `black`, `ruff`, `mypy` tiszta; a `MANIFEST.sha256` újragenerálva. **13 bevetett hiba:** a mutációk (aláírt tartomány sorrend, domain-tag, önellenőrzés kihagyása, manifest/futtatott/nyers digest-összevetés, `key_id`, görbe-korlát, `.sig` LF, Vault digest, `vault:v1:` prefix, algoritmus ↔ kulcstípus, `key_id` ↔ kulcs) mind a megnevezett teszten buknak. **A harness egy kritérium-hibája:** az első futás `-x`-szel az első bukó (nem a megnevezett) tesztet jelentette, a második futásban az M06 a naplóban "NOT CAUGHT"-ként szerepel, pedig a megnevezett teszt bukott: a **kézi újrafuttatás** (`FAILED …::test_a_modified_raw_wasm_is_detected`, 3 bukás) ezt igazolja; a harness kritériuma ezen az egy esetnél hibás volt (a kimeneti sorok illesztése), a naplót nem javítottam, hanem a kézi eredményt itt rögzítem.

## 5. Nem mért / nyitott

- **GitHub CI** a PR fejére: UNVERIFIED.
- **A transit-kulcs típusa** közvetlenül: UNVERIFIED (a metaadat nem olvasható a token szerepével).
- **Valódi aláírás és a release-folyamatba kötés** (`release.sh` / `ReleaseManager`): nincs bekötve; az aktiválás külön lépés, és a #233 landolásától függ. Valódi Vault-aláírás külön tulajdonosi engedély.
- **`executed_wasm_sha256` előállítása:** a pinelt relay-transzformáció kimenete kell hozzá; egy szűk, újrahasznosítható transzformációs komponens (a Relay oldalán, wabin-nal) még nincs: a WP-01-nek ez a bemenete, a függőségi vizsgálat (a komponens a teljes Relay behúzása nélkül elérhető-e) nyitott.
- **A modul `project.yaml`-ja nem módosult** (a `metadata.sign` és a `metadata.cicSign` jelentése változatlan).

**HOLD:** merge, valódi aláírás, countersign, release, production aktiválás.
