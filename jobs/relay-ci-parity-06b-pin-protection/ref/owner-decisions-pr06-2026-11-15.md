# Tulajdonosi döntések a PR-06-hoz (2026-11-15)

Forrás: a tulajdonos beillesztett PR-05 review-ja (ismételt review és az első review nyitott tételei). Szó szerinti átvétel, csak a PR-06-ot érintő részekből.

- „A PR-06 specifikációjába kötelezően kerüljenek be a #169 még nem igazolt 1., 2. és 8. próbái.”
- „#169 önellenőrzési próbák: 1, 2, 8 — PR-06 kötelező bemenete.”
- „PR-06: előkészíthető, de a PR-05 technikai lezárásáig implementációs HOLD.”
- „Független Rust-leltár: PARTIAL elfogadva. `syn` értékelése: pótolandó. Crate nélküli öt Rust-azonosító: külön szerződési döntés.”
- „Egy további korlátot dokumentáljunk: húsz bemeneti profil megléte önmagában nem bizonyít húsz független végrehajtást. A futások eredetének igazolása az evidence provenance későbbi feladata legyen.” (PR-08)
- Érvényben marad a PR-05 review: „Új threshold, blocking gate vagy toolchain-csere most ne történjen”; a Relay-implementáció mergelése a tulajdonos review-ja után.

A fenti „Nem döntött tétel” sort a #60 review lezárta: lásd a „Végleges döntések” szakaszt lent.

## Végleges döntések a #60 review-ból (a PR-05 #57 elfogadása után, 2026-11-15)

Szó szerinti átvétel a tulajdonos review-jából:

| Tétel | Végleges döntés |
|---|---|
| B rész | Modulazonosság és FFI; mind a négy terület hiánytérképe |
| syn | Külön job |
| Öt crate nélküli azonosító | Külön, verziózott szerződési PR |
| A.8 | Minden minőségi döntést befolyásoló eszközre fail-closed |

- „Biztonsági leletek: az új sérülékenységek reprodukciós részletei nem kerülhetnek nyilvános jelentésbe vagy CI-naplóba.”
- „Definition of Done: az A.1, A.2 és A.8 kötelező valós futásánál a nem mérve státusz dokumentálható, de nem jelentheti a feladat sikeres lezárását.”
- Végrehajtási sorrend: #57 merge az ellenőrzött HEAD-en → main-gate → #60 pontosítása, az aktuális main tetejére igazítása és új aláírása → evidence-alapú /job-validate → új gate és review. „PR-06 implementáció továbbra is HOLD.”
