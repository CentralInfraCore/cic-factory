# A meglévő admission-szerződés újrahasznosítása az O-1-ben

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## 1. Elv

Az O-1 artifactjai (modul, manifest, ABI-profil) ugyanazokat az állításokat igénylik, mint a registry séma-release-ei: **hitelesség, identitás, frissesség, alkalmazhatóság**. Nem készül új, O-1-specifikus verifier-szemantika; a közös A1–A4 szerződés **újrahasznosított**, az artifacttípusonként eltérő rész csak az identitás-definíció és a bizalmi szerepek.

## 2. Leképezés

| Admission elem | Registry séma | O-1: modul + manifest | O-1: ABI-profil |
|---|---|---|---|
| **A0 trust bundle** | anchorok, `artifact:sign`, `artifact:countersign` | a Relay `PKIAssets` bizalmi gyökerei (`Roots`, `SourceRoots`) és a CICSourceCA provenance **a bundle anchorjainak felelnek meg**; az operátori trust domain a companion-fájlok | a bundle `accepted_profiles` és az operátori policy `(id, digest)` |
| **A1 hitelesség** | per-file aláírás + ellenjegyzés, külső anchor | `ModuleReleaseEnvelope` + `.sig` (a #162 V1–V3); az aláíró jogosultsága (`module:sign`) **a bundle authority-kötéséből** (a kulcs puszta jelenléte nem jogosultság: V2b) | a profil artifact aláírása (author + ellenjegyzés) |
| **A2 identitás** | `content_digest` (a `spec` kanonikus digestje) + `artifact_digest` | **`envelope_digest`** (`wasm_sha256` + `executed_wasm_sha256` + `manifest_digest` + kulcs + algoritmus) | `profile_digest` (a nyers bájtok sha256-ja) |
| **A3 frissesség** | `ReleaseStatusHead` | ugyanaz a head-mechanizmus modulokra is (a `ReleaseStatus` általános) | ugyanaz |
| **A4 alkalmazhatóság** | `ReleaseStatus` (tartalom-hatókörű) | a modul-tartalom (wasm + manifest identitás) hatókörű státusz; a `security_finding`/`behavior_change` általános metaadat (base-repo szűk munkacsomag) | profil-identitás hatókörű státusz |
| **Eredménykódok** | `UNTRUSTED_ANCHOR`, `SIGNATURE_INVALID`, `SIGNER_NOT_AUTHORIZED`… | ugyanazok; a #162 hibakódjai (`WASM_DIGEST_MISMATCH`, `MANIFEST_DIGEST_MISMATCH`, `KEY_MISMATCH`) az A1/A2 alkódjai | ugyanazok |

**A persistence- és verification-objektumok** is ezt a leképezést használják: a recorder-attesztáció kulcsa és a verifier azonossága a bundle authority-kötésein át fogadható be (A1), nem önállítással.

## 3. Mi újrahasznosítható változtatás nélkül

A trust bundle szerkezete és az **operátori trust domain** elve (a bundle nem hitelesíti magát); az invariáns (admitted ⇔ minden kötelező állítás); a diagnosztikai prioritás mint külön szerződés; a `ReleaseStatus`/`Head` frissesség és replay-védelem; a determinisztikus eredménykódok; a közös vektorkorpusz és a differenciális minta (szigorú JSON).

## 4. Mi új (artifacttípus-specifikus)

1. A **modul-identitás** definíciója: `envelope_digest` (a `module_id`, `wasm_sha256`, `executed_wasm_sha256`, `manifest_digest` = a teljes manifest nyers bájtjainak digestje, `signer_key_id`, `signer_alg` aláírt tartománya); a korábbi `manifest_binding` fogalom megszűnt (ENV-01).
2. A **szerepek**: `module:sign` a bundle authority-kötéseiben (a registry-é `artifact:sign`).
3. A **befogadási pont**: a Relay betöltő útvonala (A1/A2 itt), a trust_state (D-1) mint az admission-eredmény vetülete.
4. A **vektorok**: modul-specifikus esetek (lásd 5.).

## 5. Vektor-javaslatok az O-1 admissionhöz (a közös korpusz kiegészítése, **nem írtam meg**)

Módosított WASM (`WASM_DIGEST_MISMATCH`); módosított manifest (`MANIFEST_DIGEST_MISMATCH`); más által épített modul érvényes tanúsítvánnyal (`SIGNATURE_INVALID`); `module_id` újrahasználata más digesttel (nem örököl capabilityt); nem befogadott profil digest; profil `not-applicable` státuszú; `authenticated` `unrelated` manifest-kötéssel (elutasított); `transitional` állapotú modul manifest-deklarált op hívásával (elutasított).

## 6. Határok

A közös szerződés **referencia-szinten** készült (absztrakt aláírás, placeholder kanonizálás); a valós kriptográfiai és production-bekötés **külön engedélyezés**. Az O-1 a közös szemantikát **fogyasztja**, nem alakítja át; ha az O-1 olyan igényt támaszt, amely a közös szerződést érinti, az a **közös szerződés** módosítása (nem három eltérő verifier).
