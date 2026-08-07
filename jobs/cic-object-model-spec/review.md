# review — cic-object-model-spec

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-07
- Feature branch: `feature/cic-object-model-spec` (cic-factory)
- Review-zott commit: `e3c754e` — `job: cic-object-model-spec — output`
- Futás: 107 + 12 turn (resume), $12,06 + $4,95 = **$17,01**, opus-5

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | GO | indítás előtt futott |
| `tools/validate-output.sh` | GO | 1 WARN: O1 — a `## Output` szekcióm `### output/x.md` fejlécekkel nevezi meg a fájlokat, amit a check nem ismer fel. **Az én spec-hibám**, harmadszor ugyanaz |
| `tools/validate-spec.sh` a két sub-jobra | GO / GO | **magam futtattam**, nem az agent állításából |

## A futás anomáliája

Az első futás `status: error`, `stop_reason: stop_sequence`, 107/150 turn. A
turn keret **nem fogyott el**. Minden érdemi termék megvolt a lemezen, de a
`claim-evidence.md` hiányzott, és **semmi nem volt commitolva**. A `--resume`
12 turn alatt lezárta.

**Tooling-hiba, amit ez feltárt:** a `run-job.sh` a végén kiírta, hogy
„Feature branch pusholt", miközben nem volt se helyi commit, se távoli ág — az
üzenet feltétel nélkül fut le. Ugyanaz a hibaosztály, mint a mai `manifest-verify`
esete: **egy lépés sikerét jelenti, amit nem ellenőrzött.** Nem javítottam, külön
tétel.

## Amit ténylegesen ellenőriztem

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| `SPEC.md` 34 számozott invariánssal | `check_spec_vectors.py` a §12 táblából parse-ol | 34 — **igazolt** |
| 32/34 vektor-fedett, 2 indokoltan nem | ua. a kapu kimenete | `invariants with vectors: 32`, `declared unvectorizable: 2` — **igazolt** |
| Az `origin` igazságtábla 8/8 sora vektor | ua. | `truth-table rows: 8/8` — **igazolt** |
| **A kapu tud pirosra váltani** | **magam mértem**: a fa másolatán töröltem az `INV-034` sorát a térképből | `FAIL — C1 INV-034: defined in SPEC.md but absent from spec-vector-map.md`, **`exit 1`**; ép fán `exit 0` — **igazolt, nem az agent állításából** |
| `MANIFEST.sha256` konzisztens | `/bin/sha256sum -c` | 213 bejegyzés, `exit 0` — **igazolt** |
| 144 YAML, 0 parse-hiba | saját `yaml.safe_load_all` bejárás | 144 / 0 — **igazolt** |
| A két `access.yaml` variáns **strukturálisan azonos** | **magam mértem**: kulcs-útvonal halmaz összevetés | 59–59 útvonal, **0 eltérés** — **igazolt** (lásd lent, ez az én hibámat javítja) |
| A `grep` shell-függvény, ami szűrhet | `type grep` | valóban függvény; a nyolc atomic fájlra viszont `grep` és `/bin/grep` **ugyanazt** adja — az agent tágabb felületen mért, nem ellentmondás |
| Egyetlen vektor sem futott | `go/`, `rust/` tartalma | csak `.gitkeep` — **igazolt (negatív állítás)** |

## Négy mérési korrekció — kettő az én specemet javítja

Ez a job értékének nagy része. A spec kimondta: „ha bármelyiket másképp
találod, **azt írd le**". Megtette, és négyszer volt igaza.

### 1. D-003 már most is 8 atomot mond, nem 7-et — **az én hibám**

A specembe azt írtam, hogy D-003 hét irreducibilis atomot rögzít, a KB `c4255`
chunkja alapján. Az agent a **live munkafákban** ellenőrizte
(`primitives-group/*/ai/DECISIONS.md:37`, mind a hatban): D-003-at 2026-05-04-én
módosították, az Access visszaolvadt bele, azóta **nyolc** atom.

Az én forrásom a `MCPs/public/source/` alatti **KB-snapshot** volt, az övé a
valódi repo. A snapshot a módosítás előtti szöveget hordozza. Ez pontosan az a
drift, amire a boot sequence figyelmeztet — és most engem kapott el. A
`kb_focus` chunk-id-t helyesen ellenőriztem (`file_path` egyezett), de a
**chunk tartalma** volt elavult a live repóhoz képest. A `file_path`-horgony a
chunk-drift ellen véd, nem a snapshot-drift ellen.

### 2. Az `access.yaml` eltérés nyelvi, nem strukturális — **az én hibám**

A specembe azt írtam: „a másolatok **már szétcsúsztak** … a migráció ott nem
mechanikus", mert az `md5sum` két variánst mutatott. Az agent kulcs-útvonal
összevetést csinált: **0 strukturális eltérés**, a különbség EN (`primitives`)
vs HU (5 másolat) próza.

**Magam is megmértem** (59–59 kulcs-útvonal, nulla eltérés) — igaza van.
Byte-különbségből következtettem szemantikai szétcsúszásra. A migráció
mechanikus; a nyelvi tengely viszont eldöntendő kérdés marad.

### 3. `sealed` élő enum érték, nem prózai említés

192 találat a hat repóban, köztük `schemas/index.yaml:98`
`enum: [sealed, defaulted, required]` és `mode: sealed` négy aggregate sémában.
Az én mérésem („egyetlen atomic primitívben, `identity.yaml`") a **nyolc atomic
fájlra** volt igaz és úgy is fogalmaztam — de a tágabb felületet nem néztem meg,
és a `sealed` így **homonima**: a meglévő slot-mód és az új authoring-határ nem
ugyanaz. A spec ezt kezeli.

Az agent maga bukott bele a shell `grep`-függvényébe (első mérése 0-t adott), és
`/bin/grep`-pel korrigálta. Ezt kimondta.

### 4. A specem által idézett fájl törölve van

`cic-compute/schemas/domain/cloud-instance.yaml` — **törölt** (`146a9b3`), csak
az elavult `origin/main`-en él. Az élő megfelelője `compute-resource.yaml` a
`main` ágon, miközben mind a hat working tree `devel`-en áll, ahol **nincs
`schemas/domain/` könyvtár**. Egy checkoutok ellen futtatott migrációs script
csendben **nulla** domain-kompozíciót érintene.

Ez önmagában értékesebb, mint az idézet pontossága: egy néma nulla-találat.

## A tartalmi döntés, amit a legjobban vártam

**`origin` nem a 9. atom** — és az érv strukturális, nem ízlés: `INV-003` szerint
minden primitív maga is CIC node, minden CIC node-nak van `origin`-ja; ha az
`origin` primitív lenne, kellene neki `origin`, annak megint — a modell nem
terminálna. Az `origin` a fixpont. Ezért a **D-003 érintetlen marad**.

**`inherit` és `default_injection` — mindkettő RETAINED.** Ez volt az én fő
kockázatom (hat repóban rögzített szemantika néma elvesztése). Nem esett el:
az `inherit` háromállapotú szemantikája (`true`/`false`/`0`) szó szerint átvéve,
de **műveletenként** (`access.read.inherit` / `access.modify.inherit`), konkrét
indoklással — a `role: state` mezőknél az adapter ír és a user olvas, amit a
lapos forma nem tud kifejezni. Migráció veszteségmentes. Vektorral fedve
(`013_access_inherit_injection`, INV-025/026).

**Az igazságtábla nyolcadik sora.** A research log hat sort enumerál és az
összes-negatív esetet definiálatlanul hagyja. `INV-018` lezárja: **üres `origin`
érvénytelen**. Ez levezetés, nem átvétel — pont az, amit a spec kért.

## Amit NEM ellenőriztem

- **A `SPEC.md` 761 sorának tartalmi helyességét.** Az invariánsok *számát* és a
  vektor-leképezést igazoltam; hogy a 34 invariáns együtt koherens és teljes
  modellt ír-e le, azt nem tudom géppel eldönteni, és soronként nem olvastam el.
- **A 27 vektor helyességét.** Egyik sem futott — nincs implementáció. A vektor
  státusza „megírva, soha nem futtatva", ezt az agent maga is kimondja négy
  helyen.
- **A váz build/CI oldalát.** Az agent környezetében nincs Docker: `make build`,
  `make check`, `make validate` egyike sem futott. A `manifest-verify` és a
  `docs.link-check` host-oldali ekvivalensét futtatta (én is), a többit nem.
  **Ismert nyitott pont, amit maga jelez:** a `schemas/index.yaml` (a base-repo
  `template-schema` meta-sémája) nincs összehangolva a `spec/`-kel, ezért a
  `make validate` valószínűleg elhasal az első bootstrap után.
- **A két sub-job spec tartalmát.** A gépi kapun GO — de ahogy a claim-evidence
  maga írja: „`exit 0` ≠ jó spec".
- **A `migration-surface.md` 114 fájlos listáját tételesen.** A csoportösszegeket
  néztem, nem az egyes útvonalakat.

## Kockázatok, amiket a merge nem old meg

1. **Egyetlen vektor sem futott.** A spec falszifikálhatósága *elő van készítve*,
   de nincs bizonyítva. Amíg a Go implementáció nem fut le rajtuk, nem tudjuk,
   hogy a 27 vektor teljesíthető-e, vagy egymásnak ellentmond.
2. **A per-operation `inherit` szemantikai bővítés**, nem puszta költöztetés. A
   spec nem definiálja, mi történik, ha a két operáció öröklése eltér — a
   PolicySurface-re halasztva. Az agent ezt kimondja.
3. **A `sealed` homonima** együtt él a régi slot-móddal a hat repóban. A migráció
   előtt el kell dönteni, hogy a két jelentés megfér-e egy névvel.
4. **A nyelvi tengely.** A hat repó HU/EN kettőssége nem strukturális, de a
   normatív forrás nyelvét el kell dönteni, mielőtt 114 fájlt hozzáigazítunk.
5. **`main` vs `devel` ághasadás** a hat repóban — bármely migrációs script
   csendes nulla-találatot adhat. Ez a legalattomosabb a listán.

## Döntés

**MERGE.**

Mind a nyolc DoD-pont teljesült; a claim-evidence táblát nem hittem el, hanem
megmértem azt, ami mérhető: a spec-vektor kaput negatív irányban is (töröltem
egy invariánst, `exit 1` lett), a manifestet, a YAML-eket, a sub-job kapukat, és
azt a mérést, ami az **én** következtetésemet fordítja meg.

Két saját mérési hibámat javította ki — mindkettő azért keletkezett, mert
snapshotból, illetve byte-különbségből következtettem, ahelyett hogy a live
repót és a szerkezetet néztem volna. Ez a job pontosan azt csinálta, amiért a
határjelzést kérni szoktuk.

A merge nem jelenti, hogy a modell helyes. Azt jelenti, hogy **falszifikálható
formában áll**, és a következő lépés meg tudja cáfolni. A `cic-object-model`
repo tényleges létrehozása külön, orchestrátori lépés — a recept az
`output/orchestrator-bootstrap.md`-ben.
