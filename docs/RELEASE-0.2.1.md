# cic-factory-core v0.2.1

Javító kiadás. A `v0.2.0` átvétele közben derült ki, hogy a mag kapuja vak arra
a helyzetre, ahol az eszközeit használni fogják.

Tag: `core/@v0.2.1`

---

## Miért van erre szükség

A `v0.2.0` a magban zöld. A `cic-factory`-ba átvéve **három dolog elbukott**.

Nem véletlen, és nem elírás: **a mag nem fogyasztója önmagának.** A saját kapuja
azt méri, hogy a mag magában konzisztens-e — nem azt, hogy egy átvevő repóban
működik-e. Ez a különbség eddig nem látszott, mert nem volt olyan verzió, ami
elég sokat változtatott ahhoz, hogy kiderüljön.

**Aki a `v0.2.0`-t venné át, ezt vegye helyette.** A `v0.2.0` tag marad, ahol
van — kiadott tag —, de fogyasztóként az első használható verzió ez.

---

## Mi változott

### A teszt-fixture bemásolta a gép saját konfigját

A `test-run-job-e2e.sh` és a `test-run-job-boundaries.sh` `cp "$SRC"/*.sh`-val
tölti fel a fixture-t. A `tools/env.sh` is `.sh` — gitignored gépi konfig —, és
a `run-job.sh` sourceolja.

A fixture így nem volt hermetikus: a futtató gép `FACTORY_PROMPT_VARS` és
`CIC_*` értékei felülírták azt, amit a teszt beállított. A magban ez
láthatatlan, mert ott csak `env.sh.example` van.

Reprodukálva: egy ideiglenes `tools/env.sh` a magba téve ugyanazt a bukást
adta, és a javítással eltűnt.

### Két szabály a mag saját állításait kérte számon az átvevőn

A `check-docs.sh` D3 szabálya és a `check-suite-counts.sh` a README
**állításait** ellenőrzi: minden teszt-suite szerepel-e a táblázatban, és
stimmelnek-e a deklarált check-számok.

Egy átvevő örökli az eszközöket, de nem az állításokat. A saját READMEjében
nincs suite-táblázat, és nem is kell lennie.

A `dependency.yaml` megléte jelzi az átvevőt — a mag maga nem hordoz ilyet. Ha
nincs táblázat **és** van `dependency.yaml`, a szabály kihagyja. A magban a
hiány továbbra is hiba: különben egy elrontott táblázat-formátum néma sikernek
látszana.

---

## Amit szándékosan NEM változtattam

A D4 szabály — a dokumentált K/O/C kapuszabályok léteznek — az átvevőben
**valódi driftet talált**: a `cic-factory` `docs/ai-optimization-plan.md`-je
egy olyan szabály-tartományt ígér, ami három kézi kritériumot is magában foglal.
Azok nem léteznek gépi szabályként — megítélési kérdések, a `/job-validate`
listáján élnek, kéziként jelölve.

Ez a szabály fogyasztóként is helyesen működik, tehát marad. A találatot az
átvevő oldalán kell javítani, nem a kapuban. A kivétel kiterjesztése egy igaz
találat elnémítására a könnyebb változat lett volna, és a rossz.

---

## Számok

| | `v0.2.0` | `v0.2.1` |
|---|---|---|
| assertion | 475 | **480** |
| viselkedési suite | 21 | 21 |

`test-check-docs.sh` 28 → 30, `test-check-suite-counts.sh` 8 → 11. Mindkét új
eset **mindkét irányban** mér: átvevőként átmegy, magként bukik.

---

## Migráció

A `v0.2.0` [migrációs pontjai](RELEASE-0.2.0.md#migráció--amit-átvételkor-tenni-kell)
változatlanul érvényesek — `FACTORY_PROMPT_VARS`, PyYAML az orchestrátor úton,
a signer CA-követelménye, a bővült `index.yaml`. Ez a kiadás nem tesz hozzájuk
és nem vesz el belőlük.

Ha valaki már átvette a `v0.2.0`-t és piros kaput lát az átvevő repójában, ez a
kiadás azt javítja — a saját fáján semmit nem kell visszavonnia.

---

## Amit ez a kiadás a módszertanról mond

Egy kapu azt méri, amit megmérni terveztek. A `v0.2.0` minden szabályát
mutációval igazoltuk: a védelmet visszavéve a suite pirosra váltott. Mind a
huszonegy suite valódi hibát tudott volna elkapni.

És együtt mégis vakok voltak egy egész helyzetre, mert mindegyik ugyanabból a
nézőpontból nézett: a magból, magára.

A `v0.2.0` átvétele volt az első alkalom, hogy valaki kívülről nézte. Öt perc
alatt hármat talált.
