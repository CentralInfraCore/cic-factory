# review — oci-extract-full-sweep

- Reviewer: orchestrátor (claude-opus-5)
- Dátum: 2026-08-03T19:30:00Z
- Feature branch: `feature/oci-extract-full-sweep` (két repóban)
- Review-zott commitok: modul-repo `33a0c62`, cic-factory (output branch)

## Gépi kapuk

| Kapu | Eredmény | Megjegyzés |
|---|---|---|
| `tools/validate-spec.sh` | **GO** | a T10-es `git add -A` tiltás utólag került bele (`4da6d16`), újravalidálva |
| `tools/validate-output.sh` | **GO** | 6 fájl a **live workdirben**. WARN: 8 `file:line` nem oldható fel — a `tools/env.sh`-ban nincs modul-repo path |
| CI (modul-repo) | **zöld** | `headSha: 33a0c62` — egyeztetve a branch HEAD-jével |

## Amit ténylegesen ellenőriztem

| Állítás az outputban | Hogyan ellenőriztem | Eredmény |
|---|---|---|
| A séma-átrendezés (`schemas/` → `schemas/core/`) nem mozdítja a kontrollcsoportot | `diff <(git show 0adf578:module/schemas/vcn.json) <(git show 33a0c62:module/schemas/core/vcn.json)`, ugyanez `subnet`-re | **byte-azonos** mindkettő — csak a helye mozdult |
| R5: a relay glob-motorja vezető wildcard + fix szuffix | `grep -n "func TestHostGlobMatch" $CIC_RELAY_PATH/cmd/relay/cic_flow_manifest_test.go` | létezik, `:50` |
| ugyanez, a viselkedés | a tesztesetek elolvasása a relay forrásában | `*.oraclecloud.com` ⟷ `iaas.eu-frankfurt-1.oraclecloud.com` → `true`; apex → `false`; `evil-oraclecloud.com` → `false` (pont-határ). **Az R5 leírása pontos** |
| T10 betartva (nem ment be generált sidecar) | `git diff --cached --name-only \| grep "\.yaml$"` a commit előtt | 2 találat, mindkettő **legitim tracked fájl** (`oci-sdk.lock.yaml`, `project.yaml`); a 2 sidecar untracked maradt |
| A commit ki van pusholva, a fa tiszta | `git status --short`, `git log origin/feature/...` | üres, `33a0c62` fent |

## Amit NEM ellenőriztem

A csend nem azt jelenti, hogy rendben van.

- **A 685 class-A erőforrás számát** és az A/B/C/D osztályozást — a sweep tool
  kimenete, nem futtattam újra.
- **A 6,04 MiB-os beágyazási mérést.** Ez a job legfontosabb egyedi száma, és
  **strukturálisan nem reprodukálható**: a mérés egy `/tmp`-beli scratch
  másolaton készült, ami törölve lett. Az agent ezt maga jelzi a Kockázat
  oszlopban. A parancs dokumentált, de a szám ma nem ellenőrizhető újra.
- **A 2238 aszinkron jelöltet** és a 117/168 szolgáltatás-eloszlást.
- **A 162/168 „ma is kifejezhető" arányt** és a 21 realm listáját — ezekből az
  R5 hatóköre következik, tehát ha tévesek, az R5 skálázása is téves.
- **A `-diff` exit 3 futtatását** egy szándékos törésen — az agent leírja
  (`cidrBlock` törlése → `{"breaking":[...]}`, exit 3), én nem hajtottam meg.
- **A `pytest tests/test_oci_sdk_lock.py` 7/7 zöldjét** és a `make check`-et
  külön — a zöld CI ezeket lefedi, de nem futtattam.
- **A (G) roadmap soronkénti hivatkozásait** a `manual-verification.md`-re — a
  szövegük konzisztens, de tételesen nem vetettem össze.

## Amit érdemes kiemelni

**Az agent saját mérési hibáját is jelentette.** A `-diff` exit kódját először
`go run`-nal mérte, ami elfedte a valós kilépési kódot; lefordított binárissal
újramérte, és a claim-evidence Kockázat oszlopában ezt le is írja. Ez a nap
visszatérő témája — a mérőeszköz, ami magát igazolja — és itt az agent maga
fogta meg.

**Az R5 nem inflálja a leletet.** Írhatta volna, hogy „a manifest nem tudja
kifejezni az OCI egress-felületét". Ehelyett megmérte: 168-ból **162**
szolgáltatás ma is kifejezhető, relay-változás nélkül, realmenként egy glob
bejegyzéssel; további 4 fix hosztot használ. Egyedül az `identitydomains` az,
aminek a végpontja tenant-feloldású, tehát statikus manifestben elvileg nem
deklarálható. Az R5 pontosan erre van skálázva, és explicit jelöli, hogy **nem
blokkolja a jelenlegi core/network PoC-t**.

**A P3.5 indoklása helyes ítélet.** A kézzel válogatott PoC-lista marad — de
már nem azért, mert az extractor nem érne el többet, hanem mert ez az, amit a
`manual-verification.md` valós OCI ellen igazolt. Az agent szavaival: *„fits is
not a reason to embed services a module never imports"*. Ez független úton
ugyanoda jutott, ahová a lefedettség-kérdésre adott ajánlásom.

## Nyitott tételek — nem blokkolók

1. **A beágyazási mérés nem reprodukálható.** Ha ez a szám később döntést
   hordoz, érdemes a mérő-scriptet (nem a 685 sémát) commitolni, hogy
   újrafuttatható legyen.
2. **A `poll` jelöltje (`core:LaunchInstance`) nincs valós OCI ellen tesztelve** —
   a spec ezt nem is kérte. Külön, tenancy-hozzáférést igénylő munka.
3. **A `tools/env.sh`-ból hiányzik a modul-repo path-ja** — ezért az O5 nulla
   `file:line`-t tudott feloldani, most is, mint az előző jobnál.
4. **T10 él** — a tiltás működött, de a csapda megmaradt.

## Döntés

**MERGE.** A job mind a hét részét leszállította, a kontrollcsoport
byte-azonos maradt, és a két állítás, amit független újraverifikációnak
vetettem alá — a séma-mozgatás tartalom-semlegessége és a relay glob-szerződés —
pontosnak bizonyult. A CI a review-zott committon zöld. A legfontosabb
fenntartás nem tartalmi, hanem módszertani: a 6,04 MiB-os mérés ma nem
reprodukálható, és ezt a döntéseknél figyelembe kell venni.
