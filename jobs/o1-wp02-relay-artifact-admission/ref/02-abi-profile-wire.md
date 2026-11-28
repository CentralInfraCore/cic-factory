# ABI-profile artifact: wire formátum (javaslat)

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## 1. Elv

A **profil önálló, verziózott, hitelesített szerződéses artifact** (D-2): a Relay az **értelmezési és ellenőrzési mechanizmust** adja, nem a domain-profilok tartalmát. Új domain-profilhoz **nem** kell Relay-kiadás. Ismeretlen, nem támogatott, nem befogadott vagy nem hitelesített profil: **elutasítás**.

## 2. Az artifact (`schemas/abi-profile.schema.json`; példák: `examples/valid/profile-ok.json`)

| Mező | Típus | Jelentés |
|---|---|---|
| `kind` | `"AbiProfile"` | |
| `profile_version` | `1` | a wire formátum verziója |
| `profile_id` | `<névtér>:<név>@<MAJOR.MINOR.PATCH>` | pl. `cic:provider@0.1.0` |
| `operations[]` | tömb | az op-készlet; opoknként lent |
| `required_host_capabilities[]` | `<név>@<n>` | pl. `provider-http@1` (a host `sign+send` képessége) |
| `limits` | opcionális | `max_request_bytes`, `max_response_bytes` |

**Op:** `name` (kisbetűs azonosító), `host_boundary` (`none`/`sign+send`), `effect` (`local`/`external-read`/`external-write`/`contract-dependent`), `effect_resolution` (kötelező **csak** `contract-dependent`-nél, tiltott másnál), `request_schema` és `response_schema` (`id` + **`digest`**: a séma-hivatkozás digest nélkül érvénytelen).

**A `contract-dependent` feloldása** (D-3): `{source: "request_field", field, map, default}`; a `default` **kötelezően `external-write`** (fail-closed): ha a kérésben a mező nem oldható fel, az op írónak számít. Egy `host_boundary: none` op `effect`-je csak `local` lehet.

## 3. Digest, hitelesítés, befogadás

- **`profile_digest`** (ABI-05) = a profil artifact **közzétett nyers bájtjainak** sha256-ja (nincs újraszerializálás, nincs kanonizálás; a digest nincs a dokumentumban). A profil aláírt tartománya: `CICABIPROFv1\nprofile_sha256=…\nsigner_key_id=…\nsigner_alg=…\n` (a `CICMODENVv1` szabályaival: ASCII, LF, rögzített sorrend, kisbetűs hex; referencia: `profile_signed_bytes`).
- A profil artifactot a CIC-release mechanizmus írja alá (author + ellenjegyzés), a befogadás az admission **A1–A4** szerint történik: a trust bundle `accepted_profiles` listája és az operátori telepítési policy `(id, digest)` párokat enged be.
- A **manifest rögzíti** a profilt: `abi.profile: {id, digest}` (D-2); a digest eltérése elutasítás. A `manifest.operations` a profil op-készletének részhalmaza.
- A profil **`ReleaseStatus`**-szal is korlátozható (egy hibás operation contract javítása profil-biztonsági javítás lehet; a `behavior_change`/`security_finding` általános metaadat).

## 4. Kapcsolat a meglévő elemekkel

| Elem | Viszony |
|---|---|
| `provider-abi.md` (a 8 provider-op) | a `cic:provider@0.1.0` profil ugyanezt az op-készletet hordozza, a host-határ és az effect a Relay-oldali értelmezés bemenete (példa) |
| Legacy négy op (`init/process/get/notify`) | a Relay **beépített** mag-életciklus profilja; a hatásuk nem ismert, ezért `contract-dependent` + `external-write` alapértelmezéssel kezelendők a megfigyelési profilban |
| `abi.operations` a manifestben | a deklaráció; a hitelesítése a #162 |

## 5. Acceptance (a wire-szinten; a példák a javaslat önkonzisztenciáját bizonyítják)

Érvényes: `profile-ok`. Elutasítandó és a kimondott okból elutasított (mért): ismeretlen `effect`; `contract-dependent` feloldás nélkül; `local` határ külső hatással; séma-hivatkozás digest nélkül; "olvasónak" alapértelmezett feloldhatatlan eset. **Production-acceptance** (a Relay oldali): ismeretlen/nem befogadott `profile_digest` elutasítva; extra manifest-op elutasítva; egy **második, szintetikus profil befogadható Relay-kód változtatása nélkül**.

## 6. Nyitott

~~A kanonikus forma~~ (lezárva: nyers bájtok, ABI-05); ~~a séma-hivatkozások feloldása~~ (lezárva: operátori séma-tár, ABI-03; **a séma-tár fizikai helye nyitott**); a profil és a modul közti verzió-kompatibilitás (SemVer-szabály); a `limits` kényszerítési pontja; a profil-artifact fájlformátuma (YAML a szerzésben, JSON a hash-tartományban).

## 7. Review-korrekciók ABI-01–05 (2026-11-27; normatív futásidejű szabályok, amelyeket a JSON Schema nem fejez ki)

A JSON Schema szerkezetet ellenőriz; az alábbiakat a **Relay profil-betöltője** kényszeríti, a `build_o1_schemas.py` `check_profile_semantics` függvénye a referencia (10 eset a `validation-report.txt`-ben, mind a várt hibakóddal).

| # | Szabály | Hibakód |
|---|---|---|
| ABI-01 | egy profilon belül az operation nevek egyediek | `DUPLICATE_OPERATION` |
| ABI-02 | az `effect_resolution.field` a `request_schema` egy deklarált, felsorolásos mezője; a `map` kulcsai a mező értéktartományába esnek; a **nem leképezett értékek a fail-closed `external-write` alapértelmezésre** esnek (determinisztikus; az alapértelmezés nem módosítható) | `EFFECT_FIELD_UNRESOLVABLE`, `EFFECT_MAP_KEY_NOT_IN_FIELD_DOMAIN` |
| ABI-03 | minden `request_schema` / `response_schema` hivatkozás `(id, digest)` párja feloldható az operátor által rögzített séma-tárból, és a digest egyezik | `SCHEMA_REF_UNRESOLVED`, `SCHEMA_DIGEST_MISMATCH` |
| ABI-04 | `sign+send` határú op ⇔ a `required_host_capabilities` tartalmazza a `provider-http@1`-et (nem hiányozhat, nem lehet felesleges) | `HOST_CAPABILITY_INCONSISTENT` |
| ABI-05 | az aláírási tartomány normatív: `profile_digest` = a nyers bájtok sha256-ja; `CICABIPROFv1` tartomány (lásd 3.) | — |
| SS-05 (közös) | a profil `limits` mezői az operátori felső korlátot nem léphetik túl (a modul nem szélesíthet) | `LIMIT_EXCEEDS_OPERATOR_CAP` |

Az effective limit = `min(operátori korlát, profil-limit)`; a séma-tár és az operátori korlát az operátori trust domain része (nem a profilé).
