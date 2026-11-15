# relay-issue-queue-01 — sor végállapota (2026-11-15)

Alap: `CentralInfraCore/CIC_Relay`, default ág `main`, jelenlegi `main@8faf00c`. A PR-ok a tulajdonos kifejezett kérésére, a jóváhagyott (CI-vel igazolt) HEAD-en mergelődtek (`--merge --match-head-commit`), mindegyik előtt az aktuális main-hez igazítva; az issue-kat a tulajdonos kérésére zártam (a PR-ok `Refs`-t használtak), lezáró kommenttel.

| Issue | PR | Merge-commit | Issue |
|---|---|---|---|
| #160 nightly security | (nincs PR; a javítás #168) | n/a | **lezárva** a zöld nightly `security` jobbal (a teljes nightly még futott) |
| #161 recorder szerializálás | #173 | `9629baf` | **lezárva** |
| #159 kötelező trust mode | #176 | `e6d7616` | **lezárva** |
| #166 egységes trust context (A) | #182 | `156cc81` | **lezárva** |
| #163 actuate egress | #180 | `07bbce8` | **lezárva** |
| #165 proof persistence | #177 | `676f79c` | **lezárva** |
| #164 CRL | #179 | `8faf00c` | **lezárva** |
| #157 compile autorizáció | #181 (nyitva) | — | `208d4c3` helyi (a `fce9d2a` volt pusholva) | gofmt, vet, staticcheck, `go test ./...` + `-race` ok; manifest diff üres | **a HOLD oka javítva helyben**: autorizáció a `Setx` végrehajtási határán (védett komponensek, `/set` opcionális), típushelyes YAML, token-sanity, docs; push és új review vár | `issue-157.md` |
| #162 capability binding | — | — | **nyitva, HOLD**: a signing oldalon nincs rögzített boríték (`issue-162.md`) |
| #155 | — | — | **nyitva, HOLD**: külön, nem nyilvános kezelés alatt (nem része a nyilvános outputnak) |

## Követő issue-k (a lezáráskor dokumentált, de nem lefedett követelmények, összevonva)

| Issue | Tárgy |
|---|---|
| #185 | recorder: több író és context-tudatos zárvárakozás (#161) |
| #186 | evidence: workflow-szintű deklaráció és indulási ellenőrzés recorder nélkül (#165) |
| #187 | egress parity: közös policy, kérés-plafon, tartományok, belső célok (#163) |
| #188 | trust bootstrap: dev néma kihagyások, indulási hibák tesztje, első ágyazott modul (#159, #166) |
| #189 | PKI: SPKI-pin forrás, CRL-frissítési modell, folyamat-újraindítási teszt (#164) |

## Integrációs mérés

`integration-measurement.md`: a hat mergelt PR együtt, a valódi belépési pontokon; minden mérés zöld, a korlátok és a nem mért részek (#181, valódi Vault, köztes CA, ágyazott modul) ott felsorolva. **A hat issue lezárása fejlesztési mérföldkő, nem produkciós jóváhagyás**: a #155 és a #162 rendezéséig a produkciós biztonsági jóváhagyás HOLD.

## Jelzések

- A GitHub által generált merge-commitok nem a fejlesztői kulccsal aláírtak; a commit-aláírás átalakulása a tulajdonos oldalán van.
- Közben más szál PR-jai is nyitva vannak (#183, #184, CI-mérés); ezekhez nem nyúltam.
- A `work event done` a ticket-formátum hiba (`ismeretlen ticket formátum: relay-issue-queue-01`) miatt nem futott le; az esemény a `$WORK_ROOT/events/pending/` alatt maradt.
