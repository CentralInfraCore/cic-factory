# #212 — A 4.6a bootstrap workflow (CIC_Relay #212, 9. lépés)

**Státusz: fájl + leírás (concept).** A fájlt nem pusholtam és nem futtattam sehol; a futási viselkedése **dokumentált, nem mért**, amíg a tulajdonos nem futtatta az X repón. A fájl megléte ≠ működik; a jóváhagyása ≠ a G0 teljesülése. A mérés, a kulcsművelet és az éles konfigurációmódosítás HOLD.

## 1. A fájl

Útvonal a factory-ban: `jobs/relay-ci-parity-06l-bootstrap-workflow/output/payload/lab-gate.yml`; célútvonal az X repón: `.github/workflows/lab-gate.yml`.

```yaml
name: lab-gate-bootstrap
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  lab-gate:
    name: lab-gate
    runs-on: ubuntu-24.04
    timeout-minutes: 2
    steps:
      - name: bootstrap
        run: echo "lab-gate bootstrap, the check exists"
```

**Blob-SHA (git hash-object):** `ebdc21b0b3f8cb9ed1621713e9234e00f4fb5756`. Ez a tartalomhoz kötött; a tulajdonos push előtt ezt veti össze (2. szakasz).

## 2. Megfelelés a 4.6a kötött tartalmának

| 4.6a kötés | Hogyan teljesül |
|---|---|
| egyetlen workflow-fájl, egyetlen job, neve `CHECK_NAME` | egy fájl; egy job (`lab-gate`), `name: lab-gate`; a 4.7 `CHECK_NAME` értéke ezért `lab-gate` (a helyőrző azonos) |
| `permissions: contents: read` | felső szinten; a jobnak nincs saját `permissions` blokkja |
| trigger csak `push` az `main` ágra | `on: push: branches: [main]`; nincs `pull_request`, `pull_request_target`, `workflow_dispatch`, `schedule` |
| nem hivatkozik titokra, környezetre, nem olvas kanárit | nincs `secrets`, `environment`, `env`, `${{ }}` kifejezés (a `run` literál) |
| nem ír semmit, csak sikeresen lefut | egyetlen `echo`; nincs checkout, nincs külső akció (`uses`), így nincs rögzítendő akció-SHA és nincs hálózati függés |

**Futtatókörnyezet:** `ubuntu-24.04` (rögzített címke, nem `latest`). A rögzített címke is elavulhat; ez ellenőrizendő, ha a futás elmarad (7. szakasz, hibaág).

**Megjegyzés a 4.7-hez (nyitott, nem hiba):** a bootstrap csak `push`-ra fut, ezért a `lab-gate` check az `main` commitjain létezik, **PR-okon nem jelenik meg**. A védett ág (4.7) a `lab-gate`-et megköveteli, így az X repón **PR csak akkor egyesíthető**, ha a 4.6b mérési csomag PR-eseményre is előállítja ugyanezt a check-nevet. Ez a 4.6b tervezési követelménye, nem a bootstrapé; a G0-hoz (a check létezése és azonossága az `main` fején) elég. A hatás a tulajdonosnak: a 4.7-et a G0-ban beállíthatod, de PR-ből indított mérés előtt a 4.6b-nek kell a check-et adnia.

## 3. A fájl ellenőrzése (helyi, a factory-ban)

```bash
python3 -I jobs/relay-ci-parity-06l-bootstrap-workflow/output/check-bootstrap-workflow.py \
  --selftest jobs/relay-ci-parity-06l-bootstrap-workflow/output/payload/lab-gate.yml
```

A szkript **fail-closed**: a fájl pontos szerkezetét követeli meg (felső kulcsok, trigger, jogosultság, egyetlen job és lépés), és tiltott szövegtokeneket keres (a megjegyzésekben is). Az `--selftest` **13 beültetett eltérést** (titokhivatkozás, environment, extra trigger, `workflow_dispatch`, másik ág, írási jog, hiányzó jogosultság, harmadik fél akciója, rossz check-név, második job, második lépés, üres fájl, érvénytelen YAML) is előállít, és mindegyiknek **bukni kell**. Mért (helyi, 2026-11-22): a fájl megfelel, 13/13 eltérés elutasítva. Az ellenőrző első futásán egy valódi hibát talált a saját első fájlváltozatomban (a `run` sorban `: ` szekvencia, érvénytelen YAML); ez javítva, a fájl blob-SHA-ja a javítás utáni.

A szkript a **szerkezetet** ellenőrzi; **nem** bizonyítja, hogy a GitHub elfogadja a workflow-t (azt csak a futás).

## 4. Tulajdonosi lépések (a PR mergelése és a 4.2 után)

**Előfeltétel:** ez a PR mergelve, az X repó létezik (4.2), a `main` védelme **még nincs** bekapcsolva (4.7 csak ez után). A K-8 szerint a push a tulajdonosé, hitelesítő adat nálam nincs.

```bash
# bootstrap-push.sh — run with: bash bootstrap-push.sh
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
FACTORY=/home/sinkog/sync/claude_factory/CIC/workdir   # the factory checkout
: "${APPROVED_FACTORY_SHA:?set to the merge commit of the approved bootstrap PR}"
EXPECTED_BLOB=ebdc21b0b3f8cb9ed1621713e9234e00f4fb5756
SRC=jobs/relay-ci-parity-06l-bootstrap-workflow/output/payload/lab-gate.yml

WORK=$(mktemp -d)
git -C "$FACTORY" show "$APPROVED_FACTORY_SHA:$SRC" > "$WORK/lab-gate.yml"
ACTUAL=$(git hash-object "$WORK/lab-gate.yml")
if [ "$ACTUAL" != "$EXPECTED_BLOB" ]; then echo "blob mismatch: $ACTUAL" >&2; exit 1; fi

git clone "https://github.com/$ORG/$X.git" "$WORK/repo"
mkdir -p "$WORK/repo/.github/workflows"
cp "$WORK/lab-gate.yml" "$WORK/repo/.github/workflows/lab-gate.yml"
git -C "$WORK/repo" add .github/workflows/lab-gate.yml
git -C "$WORK/repo" status --short
git -C "$WORK/repo" commit -m "bootstrap: lab-gate check (approved blob $EXPECTED_BLOB)"
echo "review the commit above, then push:  git -C $WORK/repo push origin main"
```

- **Hatás:** egy új fájl az X `main` ágán; a push elindítja a workflow-t (egyetlen futás). A szkript **nem pushol**, a push külön, szándékos lépés.
- **Hatás a K-5-re:** ez a futás **nem mérési futás**, nem számít a 300-ba; külön rögzítendő.
- **Olvasó ellenőrzés** (nyilvános metaadat; én is futtathatom):

```bash
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
gh api "repos/$ORG/$X/contents/.github/workflows/lab-gate.yml?ref=main" --jq .sha
gh run list --repo "$ORG/$X" --limit 3 --json databaseId,headSha,status,conclusion,event,createdAt
gh api "repos/$ORG/$X/commits/main/check-runs" --jq '.check_runs[] | {name, app: .app.slug, app_id: .app.id, conclusion}'
```

- **Elvárás:** az első sor `ebdc21b0b3f8cb9ed1621713e9234e00f4fb5756`; pontosan egy futás `event=push`, `conclusion=success`, a `headSha` a bootstrap commit; a check `name` = `lab-gate`, kibocsátó az Actions (a korábbi mérésben app id 15368; ez **olvasott korábbi mérés**, itt újra olvasandó).
- **Mit kapok vissza:** a három kimenet (nem titkos); a rögzítendő adatok: a futásazonosító, a `headSha`, az időpont.
- **Visszafordítás:** a fájl törlése egy újabb commit az `main`-re (a védelem előtt közvetlenül). Az X repó törlése HOLD.

## 5. Hibaág (7. szakasz a 06k-ból érvényes)

Ha nincs futás, vagy nem `success`, vagy a check neve eltér: **állj meg és közöld a kimenetet**; ne módosítsd a fájlt helyben. Lehetséges okok **(következtetés, nem mért):** az Actions ki van kapcsolva a repón/szervezeten; a címke (`ubuntu-24.04`) nem elérhető; az első futás jóváhagyásra vár. Bármelyik esetben a fájlváltoztatás új review-köteles commit.

## 6. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A fájl megfelel a 4.6a kötött tartalmának (egy job, `contents: read`, csak push main, nincs titok/környezet) | mért (szerkezeti, helyi) | 3. szakasz: az ellenőrző `OK`, kimenete a PR-ben | `check-bootstrap-workflow.py --selftest` | az ellenőrző nem a GitHub elfogadását méri |
| Az ellenőrző tud bukni | mért (helyi) | 13/13 beültetett eltérés elutasítva; az első fájlváltozatban valódi YAML-hibát talált | `--selftest` | a mutáns-készlet nem teljes; több mutáns szövegtokennel bukik, nem csak szerkezettel |
| A fájl blob-SHA-ja `ebdc21b0…` | mért | `git hash-object` | a tulajdonos push előtt ugyanazt számolja (4. szakasz szkript) | a fájl bármely változtatása új SHA-t ad; a dokumentumot is frissíteni kell |
| A workflow a GitHubon lefut, a check neve `lab-gate`, kibocsátója az Actions | **concept (dokumentált viselkedés, nem mért)** | a platform dokumentációja; a korábbi scratch mérés app id 15368 (más repó, olvasott) | a tulajdonos futtatja; olvasó ellenőrzés a 4. szakaszban | a futás elmaradhat (5. szakasz) |
| A bootstrap futás nem mérés és nem számít a K-5-be | concept (06k 4.6a szerinti elhatárolás) | 4. szakasz | külön rögzített futásazonosító | a tulajdonosi rögzítés elmaradhat |
| A `lab-gate` PR-eseményen nem jelenik meg a bootstrap miatt | következtetés (a trigger csak push), nem mért | 2. szakasz megjegyzés | a 4.6b tervezésekor és az első PR-nál | a 4.7 védelem PR-ből nem egyesíthetővé teheti a PR-t, amíg a 4.6b nincs |
| Az X repón vagy a Relay-n nem történt írási művelet | igaz az elkészítésig | nincs ilyen parancs; a push a tulajdonosé | `git log`, a tulajdonos futtatási jegyzete | — |

## 7. Mit nem állít ez a dokumentum

- **Nem állítja,** hogy a GitHub elfogadja és lefuttatja a fájlt; azt csak a tulajdonosi futás igazolja.
- **Nem tartalmaz** mérést, kanári-olvasót, PK-kontrollt (4.6b) vagy bármilyen titokkezelést.
- **Nem módosítja** a 06k-t és a #82 K-1–K-8 ajánlásait; a `CHECK_NAME` = `lab-gate` a 4.7 helyőrzőjének pontosítása.
- **Nem hoz döntést** a tulajdonos helyett (a 4.7 `strict` és `enforce_admins` értéke).
