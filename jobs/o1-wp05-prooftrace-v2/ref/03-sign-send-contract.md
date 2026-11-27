# `sign+send`: kérés- és válaszszerződés (javaslat)

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## 1. Elv (D-11, ADR-tervezet)

A guest **strukturált kérésleírást** ad; az **aláírás és a külső kérés végrehajtása egy megbízható határon belül** marad. A guest **nem kap** felhasználható kérés-aláírást és nem állít össze `Authorization` fejlécet. A provider-specifikus aláírási szabály külön, megbízható host-oldali komponens (első jelölt: elkülönített Go csomag), nem a Relay általános magja. Az eltérés a #89-től: `adr-draft-sign-send-host-capability.md`.

## 2. Mért kiindulás

| Tény | Hely |
|---|---|
| A guest ma a kanonikus karakterláncot maga állítja össze (`ociCanonical`), a `sign`-nal aláíratja, majd a saját `Authorization` fejlécével hívja az `actuate`-ot | `provider.go` `actuateSigned` (`callHostSign` :1637, `callHostActuate` :1662) |
| A `sign` a bájtokat átlátszatlanul írja alá, az aláírást visszaadja; az `actuate` nem köti a kérést az aláíráshoz; nincs host-interakció rögzítés | `cic_flow_host_funcs.go:111–135`, `:142–215` |
| A host ABI egységes: `(req_ptr, req_len, out_ptr, out_len) → i32`, JSON-nel | `cic_flow_host_funcs.go:76` |
| A draft-cavage OCI kanonikus karakterlánc és a fejléc-összeállítás egy `package main` demóban él | `tools/oci-sign-demo/main.go:132–160` |

## 3. A host-függvény

Új host-import: **`cic-flow.send`**, az **egységes ABI-val és JSON-nel** (nincs új ABI-forma). A `cic-flow.sign` és `cic-flow.actuate` provider-profilú modulok számára **nem** importálható (a profil `required_host_capabilities`: `provider-http@1`).

## 4. Kérés (`schemas/sign-send-request.schema.json`; `examples/valid/request-ok.json`)

| Mező | Jelentés |
|---|---|
| `v` | `1` |
| `signing_profile` | az aláírási profil azonosítója (`http-signature:oci:draft-cavage@1`), a hitelesített profil-artifactból; ismeretlen: `PROFILE_UNKNOWN` |
| `key_ref` | a manifest `secrets` handle-je (`oci/default`); a kulcsot a guest **nem nevezi**; jogosulatlan handle: `KEY_REF_UNAUTHORIZED` |
| `request` | `method`, `host`, `path` (query **nélkül**), `query{}`, `headers{}`, `body.base64` |
| `intent` | `operation`, `resource_id`, **`binding_digest` (SS-01: kötelező; a schema is megköveteli)**: a kérés **célja**, a telepítési policy (D-4) ellen validált |
| `trace_id` | a guest által adott, **nem megbízható** (nem hatóság) |

**Tiltott fejlécek a guest kérésében** (a schema elutasítja): `authorization`, `date`, `host`, `content-length`, `x-content-sha256`, `signature`. A host állítja: a **`date`-et a saját órájával**, a `host`-ot a kérés `host` mezőjéből, a `content-length`-et és a profil által megkövetelt test-digestet (`x-content-sha256`). **Aláírás- vagy `Authorization`-mező a kérésben nincs** (`additionalProperties: false`).

## 5. A host lépései (kényszerített sorrend)

1. séma-validálás (a tiltott fejlécek, a méretkorlát);
2. **policy-validálás** (D-4: host, útvonal-sablon, módszer ⊆ engedett, `intent` ↔ policy cél/binding); **elutasítás aláírás előtt** (nem hívja a Vaultot);
3. a signing profile kanonikus karakterláncot állít elő (host-oldali komponens);
4. Vault aláírás (a kulcs nem hagyja el a Vaultot);
5. kontrollált HTTP-végrehajtás (a manifest ∩ policy egress);
6. **host-interakció rekord** készítése (minden hívásról, a megtagadottról is);
7. válasz a guestnek: csak a megengedett fejlécek, a törzs, a státusz; **aláírás vagy `Authorization` soha**.

## 6. Válasz (`schemas/sign-send-response.schema.json`)

| Eset | `outcome` | Kötelező mezők |
|---|---|---|
| teljesült | `completed` | `http{status, headers, body_base64, body_sha256}`; `denial` és `failure` tilos |
| megtagadva | `denied` | `denial{code}` (`POLICY_HOST`, `POLICY_PATH`, `POLICY_METHOD`, `POLICY_TARGET`, `HEADER_FORBIDDEN`, `BODY_TOO_LARGE`, `PROFILE_UNKNOWN`, `KEY_REF_UNAUTHORIZED`, `EGRESS_BLOCKED`); `http` tilos |
| hibázott | `failed` | `failure{code}` (`SIGNER_ERROR`, `TRANSPORT_ERROR`, `RESPONSE_TOO_LARGE`, `TIMEOUT`) |

Minden válasz `interaction_id` + `interaction_digest`-et hordoz (a host-interakció rekord referenciája). A válaszban **aláírás- és `Authorization`-mező nincs** (a séma elutasítja: mért).

## 7. A host-interakció rekord (a Relay írja, nem a guest; a ProofTrace V2 `host_interactions` referenciája)

Mezők (rendezett lista elemei): `interaction_id`, `seq`, `decision` (`allowed`/`denied`), `denial_or_failure_code`, `method`, `host`, `path_sha256`, `request_body_sha256`, `status`, `response_body_sha256`, `policy_digest`, `profile_digest`, `signing_profile_digest`. A lista digestje a V2 lépés `host_interactions.digest`-je; a **megtagadott és sikertelen hívások is szerepelnek** (D-5). A rekord wire formátuma **külön review-köteles**; ez a felsorolás a tartalmi követelmény.

## 8. A komponens határa (D-11, Go csomag)

`pkg/hostsign` (generikus varrat: profil-interfész, `StructuredRequest`, `PolicyDecision`) és `pkg/hostsign/ociprofile` (az OCI profil, csak a varrat + stdlib függés); a kompozíció a `cmd/relay` gyökerében (`HostSetupFn`). **Architektúra-tesztek:** a `core/...` és a `pkg/hostsign` nem importálja az `ociprofile`-t; az `ociprofile` nem importál `core/...`-t. (MÉRT kiindulás: a `core/cabinet` függése tiszta; a `SignOCI` név a `core/nexus/crypto`-ban meglévő provider-szivárgás, külön, nem blokkoló.)

## 9. Modul-oldali változás [J]

Az Oracle modul `actuateSigned`-je a kanonikus karakterlánc és a fejléc-összeállítás helyett a strukturált kérést küldi (`method`, `host`, `path`, `intent`, törzs); a `cicflow_guest.go` import-felülete és a `abi.imports` módosul (`cic-flow.send`, a `sign`/`actuate` elhagyva).

## 10. Acceptance (production-szint; a wire-példák a javaslatot ellenőrzik)

| # | Kritérium |
|---|---|
| AC-SS-01 | a host-függvény válasza **nem** tartalmaz aláírást vagy `Authorization` fejlécet |
| AC-SS-02 | a tiltott fejléc a kérésben `HEADER_FORBIDDEN`, **aláírás nélkül** |
| AC-SS-03 | a policyn kívüli host, útvonal, módszer vagy cél **aláírás előtt** elutasított (a Vault nem hívott) |
| AC-SS-04 | a `date` a host órájából jön; a guest által adott dátum elutasított |
| AC-SS-05 | a megtagadott hívás **host-interakció rekordot** kap (`decision: denied`) |
| AC-SS-06 | a megfigyelési profilban a guest **írási** kérést nem tud kijuttatni (a módszer-korlát a kimenő kéréseken) |
| AC-SS-07 | a Relay mag csomagjai nem importálják a provider-specifikus profilt (függőségi teszt) |
| AC-SS-08 | a signing profile azonossága és digestje a host-interakció rekordban szerepel |

## 11. Nyitott

~~A host-interakció rekord wire formátuma, a válaszfejléc-allowlist, a timeout/méret forrása~~ (lezárva a 12. szakaszban: SS-02/04/05); a `query` kanonizálása; a kérés-törzs konkrét mérethatára (operátori érték); a `key_ref` ↔ manifest `secrets` kapcsolata; a `cic-flow.sign`/`actuate` átmeneti kezelése dev módban.

## 12. Review-korrekciók SS-01–05 (2026-11-27; normatív)

**SS-01.** A `binding_digest` kötelező minden v1 kérésben (a séma kikényszeríti; `request-without-binding-digest` mért elutasítás).

**SS-02 (válaszfejléc).** A host **kizárólag** az operátori policy `response_header_allowlist`-jében szereplő fejléceket adja vissza a guestnek; a többit eldobja (a darabszámot a host-interakció rekord nem rögzíti, de a megtagadás/eldobás naplózható). A tiltott fejlécek (`set-cookie`, `authorization`, `proxy-authenticate`, `www-authenticate`, `signature`, `x-content-sha256`) az allowlisttől függetlenül sosem kerülnek vissza (a séma is elutasítja). Az allowlist tartalma operátori, a signing profile javasolhat alapértéket.

**SS-03 (normatív host-oldali célvalidálás, aláírás ELŐTT; referencia: `validate_target`, 10 eset).** Sorrend és hibakód: (1) `intent.operation` ismert a policyban → `POLICY_TARGET`; (2) a `request.host` a policy host-halmazában → `POLICY_HOST`; (3) a `request.method` az operációhoz engedett módszerek között → `POLICY_METHOD`; (4) az `intent.resource_id` a policy bindingjai között → `POLICY_TARGET`; (5) `intent.binding_digest` = a policy binding digestje → `POLICY_BINDING`; (6) a `request.path` **pontosan** a policy útvonal-sablon `resource_id`-val behelyettesített alakja (nincs `..`, `//`, kódolt pont/perjel; nincs más erőforrás), a `query` üres vagy a sablon által megengedett → `POLICY_PATH`. Bármely hiba: elutasítás aláírás és Vault-hívás nélkül, a megtagadás a host-interakció rekordba kerül. Redirect egy másik hostra **nem követhető**.

**SS-04 (host-interakció rekord, közös WP-04/WP-05 interfész).** Wire: `schemas/host-interaction-record.schema.json`. Mezők: `interaction_id`, `seq`, `decision` (`allowed`/`denied`/`failed`), `code`, `method`, `host`, `path_sha256`, `request_body_sha256`, `status`, `response_body_sha256`, `policy_digest`, `profile_digest`, `signing_profile_digest`, `intent{operation, resource_id, binding_digest}`. Szabályok: `allowed` → `code: null`, `status` egész; `denied` → `code` kötelező, `status: null`, nincs válasz-test digest. **A lista digestje** (a ProofTrace V2 `host_interactions.digest`-je): `sha256` a következő ASCII-bájtokon: `CICHOSTINTv1\ncount=<n>\n` + soronként `<seq>:sha256:<rekord-digest>\n`, ahol a rekord digestje a rekord rögzített mezősorrendű `kulcs=érték` sorainak sha256-ja (`null` literál; sortörést tartalmazó vagy nem ASCII érték elutasított); a `seq` 0-tól folytonos (hézag vagy sorrendcsere elutasított). Referencia: `record_bytes`, `interactions_digest` (6 ellenőrzés).

**SS-05 (limitek).** A timeout, a kérés- és válaszméret felső korlátját az **operátori policy** adja; a profil `limits` csak szűkíthet (`LIMIT_EXCEEDS_OPERATOR_CAP`), a guest kérés limitet **nem hordozhat** (`additionalProperties: false`; mért: `request-guest-supplied-limit`). Effective limit = `min(operátori, profil)`.

**A biztonsági állítás alapja** nem a JSON-szerkezet: az acceptance tárgya a host tényleges viselkedése és az összes engedélyezett külső interakció kontrollja (AC-SS-01…08 és a fenti szabályok teszt-szintű kikényszerítése a WP-04-ben).
