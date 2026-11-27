# O-1 közös kriptográfiai conformance vektorok (TESZTKULCSOS, PROVIZÓRIUS)

**Státusz:** a referencia-implementáció (`tests/scripts/make_o1_vectors.py`, `build_o1_schemas.py`) állítja elő és ellenőrzi őket; **még nem reprodukálta őket sem a Relay, sem egy második implementáció** (ez a WP-01/WP-02 acceptance része). **Nem release-aláírások:** a kulcsok nyilvános teszt-konstansokból származnak, semmit nem védenek; Vault, countersign, éles aláírás nem történt.

| Fájl | Tartalom |
|---|---|
| `envelope-vectors.json` | 26 eset a `CICMODENVv1` envelope ellenőrzéséhez, `ecdsa-p256-sha256` és `ed25519` kulccsal: érvényes; módosított nyers WASM; eltérő futtatott reprezentáció; módosított manifest; az aláírás utáni envelope-szerkesztés; aláírás-bitflip; aláírás-kódolási hibák (szóköz, hiányzó LF, két sor); idegen `key_id`; ismeretlen verzió; algoritmus ↔ kulcstípus eltérés; allowlistön kívüli algoritmus; nagybetűs digest |
| `chain-and-interaction-vectors.json` | `CICCHAINv2` hash-input és hash (siker, `REJECTED` betöltés előtt, módosított executed digest); host-interakció lista digest és hibák; profil aláírt tartomány |

**Ellenőrzési sorrend (a referencia-verifier szerint):** verzió → envelope-forma → algoritmus ↔ kulcstípus → `key_id` = sha256(SPKI) → aláírás-kódolás → aláírás → nyers WASM digest → futtatott digest → manifest digest. Minden eset a **várt hibakódot** adja (a harness a hibakódot is egyezteti, nem csak az elutasítást).

**Reprodukálhatóság:** az Ed25519 esetek bájtra azonosak minden futásban; az ECDSA aláírások futásonként eltérnek (randomizált), ezért az ECDSA esetek **ellenőrzési** vektorok (a tárolt aláírást kell ellenőrizni), nem regenerálandó kimenetek. A kulcsfüggetlen fájl bájtra azonos.

**UNVERIFIED:** a `wasm_executed_b64` a referencia bájtszintű custom-szekció-eltávolítás eredménye (a minimális modul egyetlen custom szekcióval); hogy a Relay wabin-újrakódolása ugyanezt adja-e, a WP-02 ellenőrzi (ebben a környezetben nem volt Go toolchain).
