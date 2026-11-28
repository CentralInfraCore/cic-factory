# evidence/ — a naplók származása

Minden fájl egy tényleges parancsfutás nyers kimenete. Két csoport van, és ezt a számozás jelzi:

- **`00`–`04`** — az **első, megszakadt futásból** maradt naplók (a futás a usage limiten halt el,
  miközben `git merge origin/feature/o1-wp04-sign-send`-del indult volna; az a megközelítés nem a
  feladat, a modul-klón `devel ae3c962`-re lett visszaállítva). Megtartottam őket, mert a
  `04-mock-surface-inventory.txt` (a `devel` mock-felületének leltára, 281 hivatkozás / 16 fájl) a
  mostani portolás bemenete volt, a `03-cherry-pick-attempt.txt` pedig az elvetett megközelítés
  nyoma. A `00`–`02` ugyanazt méri, mint a `10`–`11`, csak a korábbi futásban.
- **`10`-től** — a mostani futás naplói, a jelentés szakaszainak sorrendjében:
  `1x` git-bázis és kiindulás, `2x` bevetett hibás (mutation) futások, `3x` és `4x` WASM és kapuk,
  `5x` SS-03 mérés a Relay kódja ellen, `6x` záró ág-állapot, `7x` központi CI.

A jelentés ([`../report.md`](../report.md)) és a
[`../claim-mapping.md`](../claim-mapping.md) ezekre a fájlnevekre hivatkozik.
