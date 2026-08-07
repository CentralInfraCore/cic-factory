# cic-object-model-spec — agent output

## Amit szállítottam

| Hol | Mi |
|---|---|
| `output/cic-object-model/` | a teljes repó-váz, 213 fájl + `MANIFEST.sha256` |
| `output/cic-object-model/SPEC.md` | 761 sor, **34 számozott invariáns** (INV-001…INV-034) |
| `output/cic-object-model/conformance/` | **27 vektor**, 3 kategóriában |
| `output/cic-object-model/docs/` | `spec-vector-map.md`, `decision-delta.md`, `migration-surface.md`, `branch-decision.md`, `rust-gate-extraction.md` |
| `output/cic-object-model/spec/` | `node.schema.yaml`, `origin.schema.yaml`, `index.yaml` |
| `output/cic-object-model/tools/check_spec_vectors.py` | a SPEC↔vektor kapu — **lefut, PASS, negatívan tesztelve** |
| `jobs/cic-object-model-{go,rust}/` | a két sub-job spec — `validate-spec.sh`: **GO** |
| `output/orchestrator-bootstrap.md` | futtatható bootstrap recept |

---

## A) A branch-választás — `wasm/main`, mérésre hivatkozva

**Először egy korrekció.** A spec két jelöltet nevezett meg (`golang/main`,
`wasm/main`) és azt mondta, nincs `rust/*`. A `rust/*` hiánya **igaz**. De a
`git branch -r` **32 remote ágat** ad, és köztük van egy nem említett, valódi
harmadik jelölt: **`schemas/main`** (82 fájl, 2026-03-21) — egy célzottan
séma-repóra készült sablon, `schemas/index.yaml`-lel, `go.meta.schema.yaml`-lel,
`source/`-szal. Ez a repó séma-repó, tehát ezt is meg kellett mérni.

| Ág | Fájl | Utolsó commit | Modul. `mk/` | Go gate | Rust melléilleszthető |
|---|---|---|---|---|---|
| `golang/main` | 39 | 2025-10-01 | ✗ monolit Makefile | ✓ inline | átstrukturálás után |
| `schemas/main` | 82 | 2026-03-21 | részben (`infra.mk`) | **✗ nincs** | nincs mihez |
| `wasm/main` | 100 | **2026-06-14** | ✓ `infra/golang/wasm` | ✓ `mk/golang.mk` | ✓ testvérként |

**A döntés: `wasm/main`.** Nem méret alapján — a kritérium az volt, melyikből
kevesebb munka eljutni odáig, hogy Go **és** Rust gate is fusson,
manifest-integritással, Vault-aláírt commitokkal.

`schemas/main` a legfontosabb ponton bukik: **egyáltalán nincs Go gate-je**. A
séma-repó affordanciái fájlok, azok olcsón pótolhatók; egy quality gate
gépezet, az nem.

A döntő részlet a `mk/golang.mk`-ban van, és egy sor:

```make
GO_MODULE_DIR ?= module        # → go
```

A teljes Go gate átirányítása ennyi. És a fájl alakja — `GO_EXEC` makró, ami
pinnelt builder konténerben futtat — **pontosan az az alak**, amit a CIC-Relay
`RUST_EXEC`-je használ. Így a `mk/rust.mk` testvérként illeszkedik, strukturális
adaptáció nélkül. Ez a lényeg: a `wasm/main` az egyetlen ág, ahol a két gate
egymásra fog hasonlítani.

Az irány **kivonás, nem hozzáadás**: a WASM-csatolás a Makefile-ban egyetlen
`include` sor plusz egy target volt. A törölt lista tételesen a
`docs/branch-decision.md`-ben. Egy ismert lista törlése ellenőrizhető; gépezet
építése — futtatási lehetőség nélkül — nem.

---

## B) Négy mérési korrekció

A spec kérte, hogy amit másképp találok, azt írjam le. Négy ilyen van, és
mindegyik érdemben változtat valamin.

### B1. A D-003 már most is 8 atomot mond, nem 7-et

A spec táblázata „D-003 (2026-04-30) | 7 irreducibilis atom" — ez a `c4255`
KB-chunkból jön. **A live repók mást mondanak**, mind a hatban, a 37. sorban:

```
## D-003 — 8 atom mint irreducibilis szint (2026-04-30, bővítve 2026-05-04)
**Döntés:** Shape, Role, Behavior, Contract, Address, Identity, Event, Access
```

A D-011 2026-05-04-én visszaolvadt a D-003-ba. A KB-snapshot ezen a ponton
elavult. Ez nem kozmetika: **precedenst** ad arra, hogyan kerül be egy atom —
és így a „origin a 9.?" kérdés élesebben tehető fel.

Mellékesen: a `c4367` (D-011) `file_paths`-a öt repót sorol, a `cic-compute`-ot
kihagyva — a live fában viszont mind a hatban ott van. A chunk-metaadat
hiányos, nem a repók.

### B2. `sealed` nem egy prózai említés — élő enum érték

A spec azt mérte, hogy `sealed` „egyetlen atomic primitívben fordul elő:
`identity.yaml`". **Ez téves**, és majdnem elrontotta a specet.

Az első grepem ugyanezt adta — mert a shellben a `grep` egy **függvény**, ami
csendben szűrte a találatokat. `/bin/grep`-pel a valóság: **192 találat**, és a
`sealed` a D-005 **aggregate slot mode**-ja, mind a hat repóban:

```
<repo>/schemas/index.yaml:98                        enum: [sealed, defaulted, required]
<repo>/schemas/aggregate/config-surface.yaml:30     mode: sealed
<repo>/schemas/aggregate/state-surface.yaml:30      mode: sealed
<repo>/schemas/aggregate/operation-surface.yaml:52  mode: sealed
<repo>/schemas/aggregate/managed-entity.yaml:116    mode: sealed
```

compiler-rel kikényszerítve (`sealed slot 'lifecycle_surface' must not be
overridden`) és negatív példával fedve.

Ez **homonima**, nem ütközés: a D-005 `sealed` séma→séma (típusleszármazás), a
research log `sealed`-je séma→instance (authoring). A specben INV-020 tartja
őket szét: a slot mode mindig csupasz token, az origin-tag mindig 2-aritású
konstruktor. Csupasz `sealed` egy `origin`-ban érvénytelen.

Az `identity.yaml:74` említés valóban létezik, de az **próza**, és
típusleszármazásról szól — nem az authoring határról.

### B3. Az `access.yaml` eltérés nem az `access.yaml` eltérése

A spec azt mérte, hogy az `atomic/access.yaml` két tartalommal létezik, „a
`shape.yaml` még egyformán", és ezért „a migráció ott nem mechanikus".

Mérve: **mind a 17 séma-fájl eltér**, nem egy. De a felosztás **1-vs-5 és
kizárólag prózanyelv** — a `primitives/` angolra fordítva, az öt domain-másolat
magyarul. Strukturális összehasonlítás (a teljes YAML kulcs-útvonal-halmaz
összevetése, 18 fájl, több-dokumentumos fájlokra is): **0 fájl tér el
kulcsszerkezetben** mind a hat repóban.

**A következtetés megfordul: a migráció mechanikus.** Ami nyitott, az a nyelvi
tengely — döntés, nem merge-konfliktus.

### B4. A hivatkozott domain-kompozíció törölve van

A spec `cic-compute/schemas/domain/cloud-instance.yaml`-t idézi élő példaként.
Az a fájl **törölve** (`146a9b3 chore: remove deprecated platform-specific
compute schemas`), csak az elavult `origin/main`-en él.

Az élő domain-kompozíció: `schemas/domain/compute-resource.yaml`, a **`main`**
ágon — és mind a hat working tree `devel`-en áll, ahol **nincs `schemas/domain/`
könyvtár**. Egy a checkoutok ellen futtatott migrációs script csendben nulla
domain-kompozíciót érintene.

Az idézett kódolási minta viszont pontos, csak másik fájlban: 107 sor illeszkedik
(`shape_type` + `scalar_type` prefixek, anonim `contract` lista).

---

## C) A SPEC.md — a lényegi tervezői döntések

A research logot **egyben** olvastam végig, mielőtt bármit kiemeltem volna,
mert a beszélgetés több állítást később visszavon. Nyolc olyan pont van, ahol a
spec **levezet**, nem átvesz. Mindegyik nevesítve a `decision-delta.md`-ben,
hogy külön-külön támadhatók legyenek.

### C1. `origin` NEM a 9. atom — és emiatt a D-003 érintetlen marad

A job kérdése: „origin egy 9. lenne — vagy nem atom, hanem más kategória?"

**Más kategória**, három független érven. A döntő strukturális:

> INV-003 szerint minden primitív maga is CIC node. Egy CIC node-nak van
> `origin`-ja. Ha az `origin` primitív volna, kellene neki `origin`, annak is,
> és így tovább. **A modell nem terminálna.** Az `origin` az a fixpont, ami a
> rekurziót jólalapozottá teszi — és egy fixpont nem lehet tagja annak a
> halmaznak, amit lezár.

Tehát az `origin` a **node envelope** tagja, a `values` mellett. Az atomkészlet
8 marad, a D-003 nem igényel módosítást. Ez a legkevesebb döntés-churn-t okozó
válasz, és nem kompromisszum: strukturálisan kényszerített.

Mellékhozadék: mivel az `origin`-t soha nem authorolják (INV-007), ez a node
egyetlen tagja, ami **nem tud hazudni magáról**. Egy séma-szerző írhat
félrevezető `role`-t; félrevezető `origin`-t senki nem írhat. Ezért MUST az
INV-007, nem konvenció.

### C2. A strukturális diszkriminátor NEM szintaktikai

A job kimondottan kérte: „ellenőrizd, hogy ez tényleg elég-e". A log
`values` + `default` szabálya **mindkét irányban unsound**:

*Hamis pozitív* — legitim domain payload, ami mindkét kulcsot hordozza:

```yaml
checkbox:
  values: [on, off]     # domain enumeráció
  default: false        # a domain saját defaultja
```

*Hamis negatív* — a kanonikus node-ok `values` + `origin`-t hordoznak, `default`
nélkül. A log maga is így mutatja őket a 930–948. és 1639–1650. sorban, miközben
a diszkriminátort az 505–509. sorban `default`-ra alapozza. **A log ezen a
ponton önmagával nem konzisztens.**

A spec megoldása: a séma mindig rendelkezésre áll materializációkor, tehát
**a séma-pozíció dönt, nem a kulcsvizsgálat** (INV-008). Strukturált
objektum-pozíción a mapping akkor és csak akkor envelope, ha tartalmaz `values`
kulcsot (INV-009) — és ez azért totális, mert **séma nem deklarálhat `values`
nevű gyereket** (INV-010).

Ez megőrzi a felhasználó eredeti szándékát (nincs globális kulcsszó-foglalás):
a `values` szabad marad bármely payloadban, bármely mélységben, és bármely
opaque részfában. A megszorítás csak *séma-deklarációs időben* él.

### C3. `default` → `origin`, és az igazságtábla 8. sora

A `default: true` marker helyébe az `origin: [schema]` lép: ugyanazt mondja,
pontosabban (megkülönbözteti a template schema-defaultját, amit egy boolean nem
tud). INV-012.

Az igazságtábla a logban **hat sort** enumerál (1826–1832) és az összes-negatív
esetet **definiálatlanul hagyja**. Nyolc kombináció van; a `(no, no, no)`
hiányzik. INV-018 lezárja: **üres `origin` érvénytelen** — minden materializált
node-nak van authoritása, origin nélkül attribuálhatatlan.

### C4. A `read`/`modify` és a két D-011 mező

A log `modify`-t és `write`-ot felváltva használ (234. vs 669./831. sor).
Normatív: **`modify`** (INV-024) — folytonosság a D-011-gyel és az élő
`access.yaml`-lel.

A job külön kiemelte, hogy a log **egy szót sem ejt** az `inherit`-ről és a
`default_injection`-ről. Mindkettő **megmarad**, egyik sem vész el csendben:

- **`inherit`** — tri-state szemantika szó szerint átvéve, `access.<op>.inherit`
  helyre költöztetve. A migráció veszteségmentes (lapos `inherit: X` →
  mindkét operáció). A költöztetés **valódi nyereség**: a D-011 lapos mezője
  kényszeríti, hogy a read és a modify azonosan örököljön — miközben pont az az
  eset motiválta az Access atomot (`role: state`, adapter ír / user olvas),
  ahol a modify-szabályok adapter-specifikusak és nem kéne továbbterjedniük, a
  read-szabályok viszont igen. A lapos alak ezt nem tudja kimondani.
- **`default_injection`** — `access.read` alá szűkítve, mert a definíciója
  („mit kap a kérező, ha nincs joga") olvasásról szól. Egy megtagadott íráshoz
  nincs mit injektálni. `access.modify.default_injection` érvénytelen (INV-026),
  nem csak értelmetlen.

### C5. Amit nem tettem meg

A hard constraint tiltotta az új primitívet az `origin`-on túl, és nem is
javaslok egyet. A `origin: {source, boundary}` irányt a log elvetette v0-ra —
ezt tiszteletben tartottam: **négy `origin` alak, nem több**.

A logra a spec **sehol nem hivatkozik**. A `ref/` alatt marad kutatási
naplóként. Ahol a spec olyat mond, ami a logban nincs levezetve, ott a mai
kód/séma a forrás, vagy explicit levezetés — és az a `decision-delta.md`
„Derived decisions" táblájában külön sorban áll.

---

## D) A vektorok — 27, és amit tudnak

| Kategória | Db | Mit csinál |
|---|---|---|
| `materialization/` | 13 | authoring input → kanonikus objektum |
| `invalid/` | 8 | input, amit el KELL utasítani |
| `validation/` | 6 | kanonikus objektum → elfogad / elutasít |

**Mind a 8 igazságtábla-sor fedve.** Ehhez kellett egy harmadik kategória: a 7.
és 8. sor (`yaml`+`schema`, illetve üres origin) **egyetlen authoring
inputból sem érhető el**, mert az `origin` nem authorolható (INV-007). Ezek
csak már materializált objektum defektusaként állhatnak elő, ezért a
`validation/` közvetlenül a §8.7 végső validációt hajtja meg. Enélkül két sor
falszifikálhatatlan maradt volna.

A `003_origin_sealed` és a `004_origin_sealed_schema` **egyetlen dologban**
különbözik: a template ad-e explicit `content`-et. Ez választja szét a 3. és a
4. sort, és ez az az eset, amit egyszerűbb provenance-modellek nem tudnak
kifejezni — ezért lista az `origin`, nem enum.

### Lefedettség: 32/34, és a 2 kimondottan nem-vektorizálható

A `docs/spec-vector-map.md` minden invariánst leképez. Kettő nem
vektorizálható, és ezt **kimondja**, nem hallgatja el:

- **INV-031** (a modul 7 tiltása) — a modulhatár tulajdonsága, és ebben a
  repóban nincs modul. Mind a hét kikötés **upstream fedve** van (tételesen,
  klauzulánként a térképben), de a határt magát egyik teszt sem nevezi meg. A
  sub-jobok kapják feladatul.
- **INV-032** (a típus csak a materializerrel konstruálható) — a
  konstruálhatatlanság fordítási idejű tulajdonság; **adatfájl nem tudja
  bizonyítani**, mert a hibamód az, hogy lefordul valami, aminek nem kéne. Go:
  nem exportált konstruktor + nem-forduló teszt; Rust: `compile_fail` doctest.
  Mindkét sub-job spec névre szólóan kéri.

### Amit a vektorokról **nem** állítok

**Egyetlen vektor sem futott le.** Nincs implementáció ebben a jobban. A
korpusz státusza: **megírva, nem futtatva** — így szerepel a `SPEC.md`-ben, a
`README.md`-ben, a `conformance/README.md`-ben, a `spec-vector-map.md`-ben és a
claim-evidence táblában. Egy vektor, ami sosem futott, hipotézis.

Ezt gépileg is fail-closed-dá tettem: a `make conformance` **hibával áll le**,
ha nincs jelen implementáció, ahelyett hogy üresen zöldellne.

---

## E) Amit viszont ténylegesen futtattam

Hogy a „megírva, nem futtatva" ne az egész outputra vonatkozzon — ezek valóban
lefutottak:

| Mit | Eredmény |
|---|---|
| `tools/check_spec_vectors.py` | **PASS** — 34 invariáns, 27 vektor, 32 fedve, 2 nem-vektorizálható, 8/8 sor |
| ugyanaz, **negatív teszt** ×3 | mindhárom hibaosztályt elkapja (lásd lent) |
| YAML parse, teljes repó | 144 fájl, **0 hiba** |
| belső md-linkek | mind feloldódik (host-oldali `docs.link-check` ekvivalens) |
| `spec/origin.schema.yaml` a vektorok ellen | **62 origin elfogadva, 0 elutasítva** |
| ugyanaz, 5 rossz alak ellen | mind az 5 helyesen elutasítva |
| `sha256sum -c MANIFEST.sha256` | 213 bejegyzés, mind OK |
| `validate-spec.sh` × 2 sub-job | **GO**, warning nélkül |

A `check_spec_vectors.py` negatív tesztje azért fontos, mert egy kapu, ami
mindig zöld, nem kapu:

| Injektált hiba | Elkapva |
|---|---|
| vektor nem létező invariánsra hivatkozik | `C2 … references INV-999` |
| kötelező vektorfájl hiányzik | `C4 … missing expected.yaml` |
| invariáns fedetlenül marad | `C1` + `C3 INV-032` |

A `spec/origin.schema.yaml` keresztellenőrzés elsőre 1 „téves elutasítást"
adott — ami a **saját bejáróm hibája** volt: leszállt egy **opaque payloadba**,
ahol az `origin` domain adat (INV-011), nem CIC origin. Opacitás-tudatos
bejáróval 0 elutasítás. Ez egyben a `012_discriminator_payload_keywords` vektor
működés közben: pontosan ezt a hibaosztályt hivatott elkapni.

A `manifest-verify` menet közben egyszer tényleg megfogott egy driftet: az
`architecture.md`/`.yaml` fájlokat a manifest generálása **után** írtam át, és
a `sha256sum -c` mind a négyet `FAILED`-ként jelezte. Újragenerálva 213/213 OK.

---

## F) A két sub-job

`cic-object-model-go` és `cic-object-model-rust`, mindkettő
`validate-spec.sh`: **GO**.

A speceket nem „implementáld a specet" feladatnak írtam meg:

- **A Go job igazi célja**: ő az első dolog a világon, ami kiderítheti, hogy a
  `SPEC.md` végrehajtható-e. A `docs/spec-defects.md` a fő deliverable, nem a
  szégyenfal. Konkrét gyanús pontokat is átadtam neki, ahol magam bizonytalan
  voltam (a `list` shape diszkriminátor-sora; INV-022 konzisztenciája a
  vektorokkal; a per-operation `inherit` ütközése).
- **A Rust job igazi célja**: az függetlenségi ellenőrzés. Az egyetlen kemény
  szabálya ellentmond az ösztönnek — **tilos a Go viselkedését lemásolva
  „megjavítani" egy eltérést**. A `go/`-t csak azután nézheti meg, hogy a saját
  spec-olvasatát leírta. Ha ez a sorrend elvész, elvész a kétszeres
  implementáció egyetlen értelme.

A Rust job kapja a `mk/rust.mk` kiemelését is. A `docs/rust-gate-extraction.md`
sorszám szerinti recept — és a sorszámokat **a forrás olvasásával**
ellenőriztem, nem grepből következtetve (`RUST_IMAGE_DIGEST:46`,
`RUST_EXEC:114-118`, gate targetek `310-351`, `RUST_COV_MIN:328-329` —
mind stimmel).

Két dolgot a recept hozzátesz ahhoz, amit a job specje mondott:

1. **A digest nem a Makefile-ban van.** A `RUST_IMAGE_DIGEST` egy
   `$(shell grep …)` a `docker-compose.yml` `x-rust-version` anchorára
   (`:15`, `rust:1.96.1-bookworm@sha256:d99f7b…`). Ha valaki csak a
   Makefile-sort emeli ki, a változó **csendben üres string lesz** — a `grep`
   nem hibázik, csak nem talál. Pont az a néma hibaosztály, ami ellen ez a
   rendszer épül.
2. **`deny-rust` (cargo-deny, supply-chain) is a gate része** — a `rust:`
   aggregát target (`:351`) `fmt-check + clippy + coverage + deny`. A job
   specje ezt nem említette.

Amit **nem** szabad kiemelni: a `cic-ffi` / `libcic_ffi.a` gépezet
(`:362, 396, 420, 549`). Az a relay FFI-határa. Itt a Go és a Rust **két
független implementáció ugyanarra a specre**, nem egy bináris két fele —
összelinkelve pont a kétszeres implementáció értelme veszne el.

A `CIC-Relay`-t olvasási referenciaként kezeltem: nem módosítottam, és a
logikáját nem duplikáltam ide.

---

## G) Amit nem csináltam meg, és miért

| Mi | Miért |
|---|---|
| GitHub repó létrehozása, PR | hard constraint tiltja |
| Go / Rust implementáció | hard constraint tiltja — sub-jobok |
| `mk/rust.mk` megírása | a `CIC-Relay/Makefile` nincs a klónomban; a job a **receptet** kérte. A recept sorszámait a forrás olvasásával ellenőriztem |
| a hat `CIC-objs` repó módosítása | hard constraint tiltja — ez a job specet ír |
| Docker / CI futtatás | nincs Docker az authoring környezetben. **Ezért a váz végrehajtatlan** — a claim-evidence tábla „nem igazolt" sorai |
| `docs/01-…10-….md` a log 1690–1726. sora szerint | 10 üres stub pont az a „fájl létezése = kész" csapda, amit a job tilt. A `SPEC.md` a normatív mag; ami külön dokumentumot érdemelt, az megkapta (5 valódi doc) |
| `schemas/index.yaml` összehangolása a `spec/`-kel | a base-repo `template-schema` meta-sémája; a `project.yaml` már `spec/index.yaml`-re mutat. Futtatható compiler nélkül ezt nem tudtam eldönteni — a bootstrap nyitott kérdésként átadja |

## H) Kockázatok, amiket a reviewnak látnia kell

1. **A spec sosem futott.** Minden viselkedésre vonatkozó állítás arról szól,
   mit *mond* a spec, nem arról, mit *csinál* egy implementáció.
2. **A per-operation `inherit` szemantikai bővítés**, nem puszta költöztetés.
   Veszteségmentes a migráció irányában, de olyan állapotokat hoz létre, amiket
   a régi modell nem tudott ábrázolni — és a spec nem definiálja, mi történik,
   ha a két operáció öröklése eltér. A PolicySurface-szel együtt halasztva.
3. **A `default` eltávolítása nincs instance-szinten megmérve.** Csak
   séma-szintű `default:` deklarációkat számoltam; instance-korpuszt nem
   találtam. Ha valahol runtime markerként használják, a C3 döntés töri.
4. **A váz Docker-oldala végrehajtatlan.** Szerkezetileg konzisztens és
   grep-pel ellenőrzött, de `make build` / `make check` nem futott.

---

## I) Megjegyzés a futásról

Ez a job két menetben futott: az első munkamenet session-limitbe ütközött, és a
megszakadás felülírta a már megírt `output/agent-output.md`-t egy 64 bájtos
hibaüzenettel. A folytatás előtt a teljes vázat újraellenőriztem (manifest,
YAML-parse, spec↔vektor kapu, link-check, origin-séma keresztellenőrzés,
mindkét sub-job kapuja) — a fenti E) tábla ezekből a **friss** futásokból
származik, nem a megszakadás előttiekből. A `MANIFEST.sha256` ekkor mutatta ki
a négy `architecture.*` fájl driftjét, amit újragenerálás javított.
