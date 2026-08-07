# cic-object-model-spec — a CIC objektummodell normatív specifikációja

## Ki vagy — olvasd el először

**Te vagy a végrehajtó agent.** Te írod meg ezt a specifikációt. Nem te indítottad
a jobot, és nincs mire várnod.

Ahol a szöveg „az orchestrátor"-t említi, az egy **másik** szereplő (a `workdir`
operátora, aki a specet írta és a review-t végzi). Ne beszélj a nevében, és ne
írj állapotjelentést a jobról — írd meg a specifikációt.

## Reasoning mód

**implementation** — de a termék nem kód, hanem **normatív szöveg + gépi
conformance-vektorok**. Ettől nem lesz puhább: egy normatív mondat, amit nem
tudsz vektorral ellenőrizni, ugyanaz a kategória, mint egy teszt nélküli
függvény.

---

## Mi ez és honnan jön

Egy hosszú tervezői beszélgetés (`ref/research-log.txt`, 2067 sor) kikristályosított
egy rekurzív CIC objektummodellt. A lényege:

- minden CIC node ugyanabból a nyelvtanból áll: `values` (a payload) + a payload
  szemantikáját leíró primitívek (`shape`, `role`, `contract`, `access`, `origin`, …)
- a primitívek **maguk is CIC node-ok**, nem mellécsatolt metadata
- a rövid és a kibontott alak strukturálisan megkülönböztethető, ezért nem kell
  kulcsszavakat lefoglalni
- új primitív: **`origin`** — nem érték-provenance, hanem *authoring authority*

**A research log nem a spec.** Beszélgetés, benne félbehagyott gondolatokkal,
visszavont állításokkal, és egy AI véleményével. A dolgod: kibányászni belőle az
invariánsokat és az edge case-eket, és **normatív specet** írni. Ne írd át
szebben — írd újra kötelező erejű nyelven.

---

## Amit az orchestrátor már megmért — ne mérd újra, de ellenőrizd

Ezek 2026-08-07-i mérések a live checkoutokon. Ha bármelyiket másképp találod,
**azt írd le** — a mérés lehet elavult, de ne csendben térj el tőle.

### 1. Ez nem zöldmezős modell

A `cic-primitives/schemas/atomic/access.yaml` (másolat: `ref/current-primitives/`)
**már tartalmazza a központi ötletet**, `v0.0.dev` óta:

```
key: value
key: {value: value, access: [...], modify: [...], inherit: true, default_injection: null}
A compiler a rövid formát normalizálja hosszúvá az örökölt szabályok alapján.
A runtime mindig a kibontott formán értékel.
```

### 2. Két rögzített döntés, amit ez a modell megváltoztat

| Döntés | Mit mond | Mit változtat rajta az új modell |
|---|---|---|
| **D-003** (2026-04-30) | 7 irreducibilis atom: Shape, Role, Behavior, Contract, Address, Identity, Event | `origin` egy 9. lenne — vagy nem atom, hanem más kategória? |
| **D-011** (2026-05-04) | Access a 8. atom; struktúrája `value` / `access: [CertPattern]` / `modify: [CertPattern]` / `inherit` / `default_injection` | `value` → `values`; a lapos CertPattern-listák helyett csoportosított, **névvel címzett** `access.read.rules.<név>` |

Mindkettő hat repo `ai/DECISIONS.md`-jében szerepel (`cic-primitives`,
`cic-compute`, `cic-network`, `cic-yang`, `cic-kubernetes`, `cic-storage`).

### 3. A mai node-kódolás pont az, amit a modell elutasít

Az élő domain kompozíciókban (`cic-compute/schemas/domain/cloud-instance.yaml`,
és ugyanígy a még nem materializált OCI kompozíciókban):

```yaml
- name: cidr_block
  atomic_ref: schemas/atomic/shape.yaml
  shape_type: scalar          # ← prefix, nem csoport
  scalar_type: string         # ← ugyanannak a fogalomnak a második prefixe
  role: config
  contract:
    - type: pattern           # ← anonim lista: ez ma `contract[0]`
      expression: "^ocid1\\.compartment\\."
```

### 4. `origin` sehol nem létezik

A `CIC-objs` alatti hat repo egyetlen YAML-jában sem szerepel `origin:`. Ez az
egyetlen valóban hiányzó primitív.

### 5. `sealed` már létezik — de szűkebben

A `sealed` szó ma **egyetlen** atomic primitívben fordul elő: `identity.yaml`.
A KB összefoglalója („sealed/defaulted/required slots") ennél többet sugall.
Ellenőrizd, mit jelent ma a `sealed`, mielőtt új jelentést adsz neki.

### 6. Rust: nincs sablon, de van bizonyított forrás

- A `base-repo`-ban **nincs `rust/*` ág**. Van `golang/main`, `golang/devel`, `wasm/main`.
- Rust build/quality gépezet **egyetlen helyen** él: a `${CIC_RELAY_PATH}/Makefile`-ban
  **inline** — pinnelt image digest (`RUST_IMAGE_DIGEST`, `:46`), `RUST_EXEC`
  (`:114`), `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test --locked`,
  `cargo-llvm-cov` 90%-os küszöb (`:314-330`). Ez a fájl **nincs a klónodban** —
  a kiemelés receptjét az orchestrátornak írod le, a sorszámokra hivatkozva.
- `mk/rust.mk` **nem létezik** sehol. A base-repo `wasm/main` ága `mk/golang.mk`,
  `mk/infra.mk`, `mk/wasm.mk`-t tartalmaz.

### 7. A migrációs felület

A másolatok **már szétcsúsztak**: az `atomic/access.yaml` a hat repóban **két
különböző tartalommal** létezik (a `shape.yaml` még egyformán). Ez érv az egyetlen
normatív forrás mellett — és egyben a munka mérete.

---

## Boot sequence — mielőtt bármit írsz

1. `kb_status` — elérhető a KB?
2. Olvasd el a `kb_focus` három chunkját: `get_chunk("c4135")` (a 7 atom, meta-séma
   réteg), `get_chunk("c4255")` (D-003), `get_chunk("c4367")` (D-011). Ez nem
   javaslat: ez a job azt javasolja, hogy változtassuk meg, amit ezek rögzítenek.
   **A chunk-id nem stabil.** Mindegyiknél ellenőrizd a visszakapott `file_path`-t:
   `c4135` → `.../CIC-basic-knowledge/docs/hu/repos/cic-primitives.md`, `c4255` és
   `c4367` → `.../CIC-objs/*/ai/DECISIONS.md`. Ha nem egyezik, az id elavult —
   keresd meg tartalom alapján (`search_query`), és írd le az outputban.
3. `search_query("CIC primitives atomic Shape Role Contract Access normalizálás")` és
   `search_nodes("primitives")` — mit tud a KB a mai primitív-rétegről?
4. Olvasd el a `ref/current-primitives/*.yaml` mind a nyolc fájlt. Ez a mai állapot.
5. Olvasd el a `ref/research-log.txt`-t **egyben**, mielőtt bármit kiemelnél belőle.
   Sorrend számít: a beszélgetés több állítást visszavon később.

**Amíg ez nem történt meg, ne tegyél állítást arról, mi új és mi nem.**

---

## A feladat

### A) A repo bootstrapja

Új repo: **`cic-object-model`**. A base-repo sablonból induljon.

**A branch-választás a te döntésed, bizonyítékkal.** A két jelölt:

| Ág | Mit hoz |
|---|---|
| `golang/main` | vékony: `Makefile`, `docs`, `features`, `scripts`, `tools`, `md.meta.schema.yaml` |
| `wasm/main` | teljes gépezet: `MANIFEST.sha256`, `project.yaml`, `project.schema.yaml`, `mk/` (`golang.mk`, `infra.mk`, `wasm.mk`), `configs`, pytest, yamllint, Dockerfile, docker-compose, CI workflow |

**A base-repót magadnak kell klónoznod** — a `run-job.sh` csak a cic-factory-t
adja oda. A workspace gyökerében (a cic-factory klónod *mellé*, nem bele):

```bash
git clone git@github.com:CentralInfraCore/base-repo.git
git -C base-repo branch -r          # ellenőrizd, hogy tényleg ezek az ágak vannak
git -C base-repo ls-tree --name-only origin/golang/main
git -C base-repo ls-tree --name-only origin/wasm/main
```

Ha az ágak nem azok, amiket az orchestrátor mért (`golang/main`, `golang/devel`,
`wasm/main`, és **nincs** `rust/*`), azt írd le — a mérés elavulhatott.

Mérd meg mindkettőt (`git ls-tree`, `git log`), és döntsd el. A szempont nem az,
melyik a kisebb, hanem melyikből **kevesebb munka** eljutni oda, hogy a repóban
Go és Rust quality gate is fut, manifest-integritás van, és a commitok Vault-aláírtak.
A `wasm/main`-ből WASM-specifikus részeket kell **kivenni** (`abi.schema.yaml`,
`module/`, `mk/wasm.mk`); a `golang/main`-hez gépezetet kell **hozzáadni**. Írd le,
melyik irányt választottad és miért.

**A repót ne hozd létre GitHubon** — nincs jogod hozzá. A klónodban `cic-object-model/`
könyvtárként építsd fel, és írd le a bootstrap lépéseit úgy, hogy az orchestrátor
végre tudja hajtani.

### B) `SPEC.md` — a normatív mag

Ez a job lényege. Nem 100 oldal; **inkább rövid és kötelező, mint hosszú és leíró.**

Kötelező tartalom:

1. **A node-modell.** Mi egy CIC node, mik a részei, és mitől rekurzív.
2. **A strukturális diszkriminátor.** Mikor rövid alak és mikor kibontott CIC node —
   pontosan, parser-implementálható módon. A research log a `values` + `default`
   együttes jelenlétét javasolja; ellenőrizd, hogy ez tényleg elég-e minden
   edge case-re, amit a log felvet.
3. **Az `origin` nyelvtan.** A log négy megengedett alakot rögzít:
   `[yaml]`, `[schema]`, `[sealed(template,path)]`, `[sealed(template,path), schema]`.
   Ehhez tartozik egy igazságtábla (a log 1826–1832. sora). **Ez a tábla legyen
   gépi conformance-vektor**, ne csak szöveg.
4. **A háromszabályos objektum-lezárás:** strukturált → rekurzívan materializált;
   explicit opaque → terminális érték; deklarálatlan tetszőleges → **invalid**.
5. **A materializációs pipeline** lépésenként, mindegyiknél INPUT / OUTPUT /
   MUST / MUST NOT / FAILURE.
6. **A module boundary contract.** Mit **nem** kaphat egy modul: feloldatlan
   referencia, authoring rövid alak, template, sealed forrásfragmentum,
   alkalmazatlan schema-default, ismeretlen primitív, validálatlan objektum.
7. **Verziózás.** A modell verziója az első naptól legyen explicit.

Az invariánsokat számozd (`INV-001`…), mert a conformance-vektorok ezekre fognak
hivatkozni.

### C) Conformance-vektorok — az executable rész

```
conformance/
  materialization/
    001_.../  { schema.yaml, input.yaml, expected.yaml }
    ...
  invalid/
    ...      { schema.yaml, input.yaml, expected-error.yaml }
```

**Minimum, ami nélkül a spec nem falszifikálható:**

- az `origin` igazságtábla **minden sora** egy-egy vektor, a `sealed + yaml → INVALID`
  és a `yaml + schema → INVALID` eseteket is beleértve
- a háromszabályos objektum-lezárás mindhárom ága
- a rövid → kibontott normalizálás legalább: skalár, lista, map, és üres `{}`
  schema-defaultokkal

A vektorok formátuma legyen implementáció-független (YAML be, YAML ki), hogy Go és
Rust ugyanazt futtathassa.

### D) Decision delta — ezt ne hagyd ki

`docs/decision-delta.md`: mit **vált fel** ez a modell a D-003-ból és a D-011-ből,
és mit **veszítenénk el csendben**, ha nem figyelünk.

Konkrétan, a D-011 tartalmaz két mezőt, amiről a research log **egy szót sem ejt**:

- `inherit: true | false | 0` (öröklés, teljes reset)
- `default_injection`

Vagy beépülnek az új modellbe, vagy kimondottan elvetjük őket indoklással.
**A hallgatás nem opció** — egy meglévő, hat repóban rögzített szemantika néma
elvesztése pontosan az a hibaosztály, ami ellen ez az egész rendszer épül.

### E) Migrációs felület — mérd meg, ne becsüld

`docs/migration-surface.md`: melyik fájlok változnának és hogyan.
Konkrét fájllista, nem „a domain repók". Legalább:

- a hat `CIC-objs` repo `schemas/atomic/*.yaml` és `schemas/aggregate/*.yaml` fájljai
- az élő domain kompozíciók (`cic-compute/schemas/domain/*.yaml` stb.)
- az öt még nem materializált OCI kompozíció
  (`jobs/poc-oci-schema-design-0{1,2}/output/oci-compositions/*.yaml` a cic-factory klónodban)

Ahol a hat repo másolatai **már eltérnek** (mérve: `access.yaml`), azt jelöld —
a migráció ott nem mechanikus.

### F) Sub-job specek a két implementációhoz

**Ebben a jobban ne írj Go vagy Rust implementációt.** Helyette írd meg a
sub-job specjeiket (`input.md` + `meta.yaml`) a cic-factory klónodban, a
`jobs/<sub-job-id>/` alá:

- `cic-object-model-go` — a referencia-implementáció, ami átmegy a vektorokon
- `cic-object-model-rust` — ugyanaz Rustban, `mk/rust.mk` kiemelésével a
  `CIC-Relay/Makefile`-ból

Miért így: egy normatív spec, amit ugyanabban a futásban kétszer implementálnak,
nem hihető. A vektorok teszik a specet falszifikálhatóvá; az implementációk azt
bizonyítják, hogy a vektorok teljesíthetők.

---

## Tiltott rövidítések — ezekre külön figyelj

Ez a job szöveget termel, és a szöveg könnyebben látszik késznek, mint amilyen.
Az alábbiak **nem** számítanak teljesítésnek:

- **A fájl létezése ≠ implemented.** Egy `SPEC.md`, ami létezik, nem spec —
  a számozott invariánsok és a hozzájuk kötött vektorok teszik azzá.
- **A leírt MUST ≠ ellenőrzött MUST.** Minden normatív mondathoz vagy tartozik
  conformance-vektor, vagy kimondottan jelölöd, hogy nem vektorizálható, és miért.
  A harmadik lehetőség — csendben ott hagyni — a job bukása.
- **A vektor-könyvtár létezése ≠ átmenő vektor.** Nincs implementáció ebben a
  jobban, tehát egyetlen vektor sem futott le. Ezt a claim-evidence táblában
  **mondd ki**: a vektorok állapota „megírva, nem futtatva". Ne írd „igazolt"-nak.
- **A `ref/research-log.txt` idézése ≠ levezetés.** A log egy beszélgetés, benne
  később visszavont állításokkal. Ha egy normatív döntés forrása „a log ezt
  mondja", az nem forrás.
- **`exit code 0` a `validate-spec.sh`-tól ≠ jó sub-job spec.** A gépi kapu a
  formát nézi, nem a tartalmat.

## Hard constraintek

1. **A research log nem hivatkozási alap normatív állításhoz.** Ha valamit a
   specbe írsz, annak vagy a log **levezetése** a forrása, vagy a mai kód/séma —
   és a specben ne hivatkozz a logra. A log a `ref/` alatt marad kutatási
   naplóként.
2. **Ne told túl a sémázást.** A log maga figyelmeztet erre (`origin: {source, boundary}`
   irány elvetve v0-ra). Négy `origin` alak, nem több.
3. **Ne találj ki új primitívet** a `origin`-on túl. Ha úgy látod, kell még egy,
   azt az outputban javasold — a specbe ne írd bele.
4. **Ne módosítsd a hat `CIC-objs` repót.** Ez a job specet ír, nem migrál.
5. **Ne hozz létre GitHub repót**, és ne nyiss PR-t.
6. Ha a spec és a mai `access.yaml` szemantikája ütközik, **a spec nyer** — de
   az ütközést a `decision-delta.md`-ben nevezd meg.

---

## DoD

| # | Amit teljesíteni kell | Mivel igazolod |
|---|---|---|
| 1 | `SPEC.md` létezik, számozott invariánsokkal (`INV-001`…) | fájl + az invariánsok listája a claim-evidence táblában |
| 2 | Az `origin` igazságtábla minden sora conformance-vektor | vektor-könyvtár listája, soronként megfeleltetve |
| 3 | A háromszabályos objektum-lezárás mindhárom ága vektor | ua. |
| 4 | Minden normatív MUST/MUST NOT vagy vektorral fedett, vagy kimondottan „nem vektorizálható" jelöléssel áll | `SPEC.md` → vektor megfeleltetési tábla |
| 5 | `decision-delta.md` kimondja a D-003 és D-011 sorsát, és külön kitér az `inherit` + `default_injection` mezőkre | fájl |
| 6 | `migration-surface.md` konkrét fájllistát ad, nem kategóriákat | fájl + a lista hossza |
| 7 | A base-repo branch-választás indokolt, mérésre hivatkozva | `agent-output.md` |
| 8 | A két sub-job spec létezik és `validate-spec.sh`-val GO | `./tools/validate-spec.sh <sub-job-id>` kimenete |

**Amit nem tudsz igazolni, az a claim-evidence táblában „nem igazolt" sorba megy.**
Ha egy DoD-pont a spec hibája (ellentmond magának, vagy nem teljesíthető), azt
**mondd ki** — ne szűkítsd csendben. Az előző jobban pont ez volt a helyes
viselkedés.

---

## Output

A `jobs/cic-object-model-spec/output/` alá, a cic-factory klónodban:

### `output/agent-output.md`
Mit csináltál, mit nem, és miért. A branch-választás indoklása ide jön.

### `output/claim-evidence.md`
| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |

Minden DoD-pont egy sor.

### `output/cic-object-model/`
A felépített repo-váz teljes tartalma (SPEC.md, docs/, conformance/, spec/,
Makefile, project.yaml, mk/ stb.) — az orchestrátor ezt emeli át az új repóba.

### `output/orchestrator-bootstrap.md`
Futtatható recept: hogyan hozza létre az orchestrátor a `cic-object-model`
repót és tölti fel ezzel a tartalommal. Konkrét parancsok, a base-repo
remote-tal és a Vault-aláírás lépésével együtt.

---

## Git

- A cic-factory klónodban dolgozol, `feature/cic-object-model-spec` ágon.
- Commitolj és pushold a feature branchre. **PR-t ne nyiss**, `main`-re ne pushold.
- A `base-repo` klónba **ne commitolj** — az olvasási referencia.

## Nyelvi szabály

- `SPEC.md`, `docs/`, conformance-vektorok, kód, YAML: **angolul**
- `output/agent-output.md`, `output/claim-evidence.md`, a sub-job `input.md`-k: **magyarul**
