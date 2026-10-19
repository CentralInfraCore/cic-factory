# cic-factory-core v0.4.1

Egyetlen javítás a `v0.4.0` óta: a `check-docs.sh` többé nem tekinti
dokumentációnak a session-naplókat.

Tag: `core/@v0.4.1` — 1 tartalmi PR (#90) a `core/@v0.4.0` óta.

---

## Miért patch bump

Nincs új mező, nincs új kapu, nincs kikényszerített migráció. A `check-docs.sh`
egyetlen irányban enyhül: a `theads/` alatti fájlokat nem olvassa. Aki nem használ
`theads/`-t, azt semmi nem érinti.

---

## Mi hibázott

A `check-docs.sh` D1, D2 és D4 szabálya minden követett `*.md`-t dokumentációnak
tekintett a `jobs/<id>/` archívumon kívül. Egy session-transcript viszont napló:
azt rögzíti, ami elhangzott, és nincs mihez igazodnia.

Az átvevő cic-factory-ban a D4 egy transcriptben idézett, `C`-betűs szabály-azonosítót
jelzett. Az egy másik repo (cic-primitives) szabálya volt, amiről a session szólt,
nem a `close-job.sh` kapuja. A checker a tokent látja, a kontextust nem — négy
egymás utáni `main` push bukott emiatt.

## Mi változott

- `tools/check-docs.sh`: a `theads/` ugyanúgy kivétel D1/D2/D4-ben, mint a
  `jobs/<id>/`.
- `tools/test-check-docs.sh`: két eset. A `theads/` alatt ismeretlen szabály-id,
  törött link és séma-blokk átmegy; ugyanaz a szöveg a `docs/` alatt továbbra is
  bukik, tehát a kivétel nem nyel le mindent. A javítás nélküli checkeren az első
  eset bukik (35 PASS / 1 FAIL). 33 → 36 ellenőrzés.
- `CLAUDE.md`, `theads/README.md`: a session-napló szabálya, hogy a kivétel ott
  legyen definiálva, ahol a checker él.

## Átvételkor

`dependency.yaml`: `tag: core/@v0.4.1`, új `commit`, és a `docs/RELEASE-0.4.1.md`
az `imported_paths` közé. A `CLAUDE.md` helyi (`local_paths`), azt az átvétel nem
írja felül.
