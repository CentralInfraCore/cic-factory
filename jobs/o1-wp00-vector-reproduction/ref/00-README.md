# O-1 célzott előkészítés: index és review-ellenőrzőlista

**Státusz:** célzott O-1 előkészítési tervezet, **review-ra**; a wire formátumok **NEM elfogadottak** (a D-1–D-13 irányok GO-ja a wire formátumokra nem terjed ki). Nincs implementáció, commit, push, merge, aláírás, countersign, release vagy Factory job. Új Relay-felmérés nem készült: a korábbi mérések és az elfogadott döntések a bemenetek; csak az új szerződésekhez szükséges célzott olvasás történt.
Mérés: 2026-11-27; CIC_Relay `main` `86ea1ab`, cic-module-oracle-cloud `devel` `ae3c962`. `MÉRT` = fájl-olvasás; `UNVERIFIED` = nem mértem; a "nincs hívó/olvasó" állítások grep-alapúak.

## Sorrend és függőségek

| # | Anyag | Függés | Párhuzamos? |
|---|---|---|---|
| 1 | `01-162-implementation-boundary.md`: #162 implementációs határ, érintett fájlok, acceptance | D-1, D-10; a **szerződés** a signing oldalon rögzítendő (envelope) | előbb |
| 2 | `02-abi-profile-wire.md` | D-2, D-3; admission A1 | igen (2–4) |
| 3 | `03-sign-send-contract.md` | D-4, D-11, D-12; ADR (#89) | igen |
| 4 | `04-prooftrace-v2-wire.md` (négy eredménydimenzió) | D-5, D-6; 2. és 3. | igen |
| 5 | `05-admission-reuse.md` | admission szerződés (9. fejezet) | az 1–4. után |

A **generic dispatch** (az előző szerződések production-bekötése) csak a szerződések elfogadása és a #162 után következik; **nem** része ennek a csomagnak. Nem a teljes ProofTrace V2 implementációval kezdünk.

## Mellékletek

- `schemas/`: 8 JSON Schema (draft-07) a wire-javaslatokhoz: `module-release-envelope`, `abi-profile`, `sign-send-request`, `sign-send-response`, `prooftrace-v2`, `prooftrace-v2-persistence`, `verification-result`.
- `examples/valid/` (16) és `examples/invalid/` (51): mindegyik példa a **kimondott okból** viselkedik (a séma-ellenőrzés a javaslat önkonzisztenciáját bizonyítja, **nem** valamely implementációt): `validation-report.txt`.

## Review-ellenőrzőlista (a tulajdonosnak)

| Pont | Kérdés |
|---|---|
| R1 | Az envelope tartalma (wasm, manifest, kulcs-azonosító) és a detached aláírás helye elfogadható-e a #162-hez? A signing oldali változás ([J], modulrepó) vállalható-e? |
| R2 | A `manifest_digest` mit fedjen: `capability_manifest` és `abi` együtt? |
| R3 | Az ABI-profil artifact mezői, a `contract-dependent` feloldási szabálya és a fail-closed alapértelmezés elfogadható-e? |
| R4 | A `sign+send` kérés/válasz mezői, tiltott fejlécek, hibakódok; a `date` host-oldali előállítása |
| R5 | A ProofTrace V2 hash-tartománya: mi kerül a `chain_hash`-be, mi marad a perzisztencia (a hash-tartományon kívüli) burkában |
| R6 | A négy eredménydimenzió szétválasztása: a verifier-eredmény külön objektum |
| R7 | A kanonizálás (közös az admission szerződéssel): melyik kanonikus forma? |

## Nem döntöttem (nyitott)

A kanonikus forma; a signing-profile komponens formája (első jelölt: host-oldali Go csomag); a telepítési policy forrása; az evidence tárolása és exportja; a `transitional` kivezetési szabálya; a `.sig` fájl és a release-folyamat konkrét kapcsolata a modulrepóban.
