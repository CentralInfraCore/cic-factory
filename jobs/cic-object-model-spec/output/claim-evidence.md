# cic-object-model-spec — claim–evidence

Minden DoD-pont egy sor. A „nem igazolt" nem hiba-kategória, hanem a
becsületes besorolás arra, amit ebben a környezetben nem lehetett meghajtani.

Rövidítés: `$OUT` = `jobs/cic-object-model-spec/output/`,
`$REPO` = `$OUT/cic-object-model/`.

---

## DoD-pontok

| # | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|---|
| 1 | `SPEC.md` létezik, számozott invariánsokkal (INV-001…INV-034) | **igazolt** | `$REPO/SPEC.md`, 761 sor; §12 invariáns-index 34 sorral; a lista lent | `python3 tools/check_spec_vectors.py` a §12 táblából parse-olja őket: „SPEC.md invariants: 34" | A szám igazolt, a *tartalom* helyessége nem — normatív szöveg helyességét nem lehet géppel eldönteni. A 8 levezetett döntés a `decision-delta.md`-ben külön támadható |
| 2 | Az `origin` igazságtábla minden sora conformance-vektor | **igazolt** | 8/8 sor; `materialization/001–004`, `invalid/001–002`, `validation/001–002`; megfeleltetés a `docs/spec-vector-map.md`-ben és a vektorok `meta.yaml` `truth_table_row:` mezőjében | `check_spec_vectors.py` C5 ellenőrzése a `SPEC.md` §5.3 tábláját parse-olja és a vektorokhoz köti: „truth-table rows: 8/8" | A vektorok **nem futottak**. A tábla lefedettsége igazolt, a vektorok *helyessége* nem |
| 3 | A háromszabályos objektum-lezárás mindhárom ága vektor | **igazolt** | 1. strukturált → `materialization/005_closure_structured`; 2. explicit opaque → `materialization/006_closure_opaque`; 3. deklarálatlan → `invalid/003_closure_undeclared`. `meta.yaml` `closure_rule: 1|2|3` | A három `meta.yaml` `closure_rule` mezője; INV-027/028/029 lefedettsége a spec-vektor térképben | ua. mint 2: megírva, nem futtatva |
| 4 | Minden normatív MUST/MUST NOT vagy vektorral fedett, vagy kimondottan „nem vektorizálható" | **igazolt** | `$REPO/docs/spec-vector-map.md`: 32/34 vektor-fedett, 2 (INV-031, INV-032) indoklással a „Unvectorizable" táblában | `check_spec_vectors.py` C1+C3: hibázik, ha egy invariáns se nem fedett, se nem indokolt. **Negatívan tesztelve**: az INV-032 sor törlésére `C1`+`C3` hibát adott | Az INV-031 „upstream fedve" érvelése *érvelés*, nem teszt: a modulhatárt magát egyetlen vektor sem hajtja meg. A sub-jobok kapják feladatul |
| 5 | `decision-delta.md` kimondja D-003 és D-011 sorsát, külön kitérve az `inherit` + `default_injection` mezőkre | **igazolt** | `$REPO/docs/decision-delta.md`: D-003 = UNCHANGED (indoklással), D-011 = az atom marad, a struktúra cserélődik; az `inherit` és a `default_injection` külön alfejezetet kap, mindkettő RETAINED, veszteségmentes migrációs képlettel | Fájl olvasása; a két mező vektorral is fedett: `materialization/013_access_inherit_injection` (INV-025, INV-026) | A per-operation `inherit` **szemantikai bővítés**, nem puszta költöztetés — a spec nem definiálja, mi történik, ha a két operáció öröklése eltér (PolicySurface-szel halasztva). Ezt a doksi ki is mondja |
| 6 | `migration-surface.md` konkrét fájllistát ad, nem kategóriákat | **igazolt** | `$REPO/docs/migration-surface.md`: **114 fájl** hét csoportban, mindegyik teljes útvonallal és sorszámokkal (pl. `<repo>/schemas/aggregate/config-surface.yaml:30`); a lista lent összegezve | Lemezen mérve 2026-08-07: `find`/`ls` fájlszámok, `sha256sum` divergencia-csoportosítás, YAML kulcs-útvonal összehasonlítás (18 fájl, 0 strukturális eltérés), `git ls-tree` ágankénti domain-lista | A `main` vs `devel` ághasadás miatt egy checkoutok ellen futtatott script 0 domain-kompozíciót érintene — a doksi §0.3 kimondja. A fogyasztók (`compiler.py`) nincsenek megmérve, ezt §8 jelzi |
| 7 | A base-repo branch-választás indokolt, mérésre hivatkozva | **igazolt** | `$OUT/agent-output.md` A) szakasz + `$REPO/docs/branch-decision.md`: 3 jelölt táblázatos összevetése, a döntő `GO_MODULE_DIR ?= module` egysoros átirányítás, és a törölt WASM-elemek tételes listája | `git branch -r` (32 ág), `git ls-tree -r --name-only` fájlszámok, `git log -1 --format=%ad` dátumok, `Makefile` target-listák grep-pel, a `mk/golang.mk` paraméterezés olvasása | A választás melletti érv a *kevesebb munka*; ezt nem lehetett futtatással igazolni, mert nincs Docker. Az érv szerkezeti, nem mért |
| 8 | A két sub-job spec létezik és `validate-spec.sh`-val GO | **igazolt** | `jobs/cic-object-model-go/{input.md,meta.yaml}`, `jobs/cic-object-model-rust/{input.md,meta.yaml}` | `./tools/validate-spec.sh cic-object-model-go` → `MECHANIKUS ELLENŐRZÉS: GO`, exit 0; ugyanaz a rust jobra. Warning sincs (K11 `kb_focus` kitöltve) | **`exit 0` ≠ jó spec** — a kapu a formát nézi, nem a tartalmat. A tartalmi kockázat: a Rust job értéke azon áll, hogy a Go-t csak a saját olvasata leírása után nézi meg; ezt semmilyen gép nem kényszeríti ki, csak a promptban szereplő szabály |

---

## Kiegészítő állítások (nem DoD, de a review-nak kellenek)

| # | Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|---|
| 9 | **Egyetlen conformance-vektor sem futott le** | **igazolt (negatív állítás)** | Nincs implementáció a repóban: `go/` és `rust/` üres (`.gitkeep`) | `find go rust -type f` → csak `.gitkeep`. A `make conformance` target szándékosan `exit 1`-et ad, ha nincs implementáció | Ez a job legfontosabb korlátja. A `SPEC.md`, `README.md`, `conformance/README.md` és a `spec-vector-map.md` mind kimondja |
| 10 | A `check_spec_vectors.py` kapu valóban fog hibát (nem mindig zöld) | **igazolt** | 3 injektált hibaosztály, mind elkapva: nem létező invariánsra hivatkozó vektor → `C2`; hiányzó kötelező vektorfájl → `C4`; fedetlen invariáns → `C1`+`C3` | Injektálás → futtatás → visszaállítás; mindhárom eset `exit 1`. A visszaállítás után 213/213 manifest-bejegyzés OK | A kapu a *leképezést* nézi, nem a vektorok helyességét. Ezt a kimenete maga is kiírja |
| 11 | A `spec/origin.schema.yaml` konzisztens a vektorokkal | **igazolt** | 62 origin a `materialization/*/expected.yaml`-ekből: mind elfogadva, 0 elutasítva. 5 rossz alak (csupasz `sealed`, hiányzó `path`, history-stílus, rossz sorrend, üres): mind elutasítva | `jsonschema.Draft202012Validator` a séma ellen, opacitás-tudatos bejárással | Az első futás 1 „téves elutasítást" adott — a bejáróm szállt le egy opaque payloadba, ahol az `origin` domain adat (INV-011). Ez a `012_discriminator_payload_keywords` vektor működés közben |
| 12 | A repó-váz strukturálisan konzisztens | **igazolt** | 214 fájl; 144 YAML **0 parse-hibával**; minden belső md-link feloldódik; `MANIFEST.sha256` 213 bejegyzés, `sha256sum -c` tiszta | `yaml.safe_load_all` minden YAML-re; host-oldali link-check; `sha256sum -c` | Szerkezeti konzisztencia ≠ működés — lásd 13 |
| 13 | A váz **build/CI oldala nem futott** | **nem igazolt** | — | Nincs Docker az authoring környezetben: `make build`, `make check`, `make manifest-verify`, `make docs.link-check`, `make validate` egyike sem futott | A `docs.link-check` és a `manifest-verify` host-oldali ekvivalensei lefutottak, a többi nem. Ismert nyitott pont: `schemas/index.yaml` (base-repo `template-schema` meta-séma) nincs összehangolva a `spec/`-kel, ezért `make validate` valószínűleg elhasal. A bootstrap §5 és §7 kimondja |
| 14 | A D-003 a live repókban **8 atomot** mond, nem 7-et (a job specjében szereplő méréssel szemben) | **igazolt** | Mind a hat repó `ai/DECISIONS.md:37`: „D-003 — 8 atom mint irreducibilis szint (2026-04-30, bővítve 2026-05-04)", Access-szel a felsorolásban | `/bin/grep -n '^## D-003'` mind a hat fájlra; a `primitives` repóban HU+EN duplikátum (37. és 381. sor) | A `c4255` KB-chunk még 7-et mond → a KB-snapshot elavult. Aki chunkból dolgozik, rossz premisszából indul |
| 15 | A `sealed` **élő enum érték** a hat repóban, nem egyetlen prózai említés | **igazolt** | 192 találat; `schemas/index.yaml:98` `enum: [sealed, defaulted, required]`; `mode: sealed` 4 aggregate sémában repónként; compiler-üzenet és negatív példa | `/bin/grep -Rn 'sealed' --include='*.yaml'` | **A `grep` a shellben függvény volt, és csendben szűrt** — az első mérésem ezért 0-t adott. A `/bin/grep` explicit használata nélkül ez a korrekció kimaradt volna, és a spec homonima-kezelés nélkül született volna |
| 16 | A hat repó eltérése **kizárólag prózanyelv**, 0 strukturális eltéréssel | **igazolt** | Mind a 17 séma-fájl 2 variánsban (1 `primitives` EN vs 5 másolat HU); `index.yaml` byte-azonos. Kulcs-útvonal összehasonlítás: 18 fájl, **0 eltérő kulcsszerkezet** | `sha256sum` csoportosítás + Python YAML-bejárás, ami minden dokumentum teljes kulcs-útvonal-halmazát összeveti (több-dokumentumos fájlokra is) | Megfordítja a job specjének következtetését („a migráció ott nem mechanikus") — a migráció mechanikus, a nyelvi tengely viszont eldöntendő |

---

## Az INV-lista (DoD 1. bizonyítéka)

`SPEC.md` §12-ből, a `check_spec_vectors.py` által parse-olva:

INV-001 … INV-034, hiánytalanul. Csoportosítva:

| Csoport | Invariánsok | § |
|---|---|---|
| Node-modell | INV-001…INV-006 | 2 |
| Két sík / authoring | INV-007 | 3 |
| Strukturális diszkriminátor | INV-008…INV-012 | 4 |
| Origin | INV-013…INV-020 | 5 |
| Primitívek | INV-021…INV-026 | 6 |
| Objektum-lezárás | INV-027…INV-029 | 7 |
| Pipeline | INV-030 | 8 |
| Modulhatár | INV-031, INV-032 | 9 |
| Verziózás | INV-033, INV-034 | 11 |

## A migrációs fájlszám (DoD 6. bizonyítéka)

| Csoport | Fájl | Diszpozíció |
|---|---|---|
| Atomic primitívek (8×6) | 48 | 6 cserélve (`access`), 12 módosítva (`shape`, `contract`), 30 változatlan |
| Aggregate kompozíciók (5×6) | 30 | csak dokumentáció (a `sealed` homonima miatt) |
| Meta-séma `index.yaml` (1×6) | 6 | bővítendő |
| Példa sémák (4×6) | 24 | 6 újrakódolva, 18 változatlan |
| Domain kompozíció (élő) | 1 | újrakódolva — referencia-konverzió |
| OCI kompozíciók | 5 | materializáció előtt újrakódolva |
| **Összesen** | **114** | ebből **~30** igényel valódi tartalmi munkát |
