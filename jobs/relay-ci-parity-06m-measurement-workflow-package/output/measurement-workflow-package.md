# #212 — A 4.6b mérési workflow-csomag, 0. fázis (CIC_Relay #212, 10. lépés)

**Státusz: fájlok + leírás (concept).** A csomagot nem pusholtam az X repóra, GitHubon nem futtattam; a futási viselkedése és a naplóformátum **dokumentált, nem mért**, amíg a tulajdonos nem futtatta. A csomag megléte ≠ működik; a jóváhagyása ≠ mérés. **A tényleges mérés (H1/H2, M-A…M-E), a valódi kulcsműveletek és a Relay-implementáció HOLD.**

**Tulajdonosi döntések (a tulajdonos 2026-11-22-i szövege szerint, rögzítve):** K-5 ACCEPT (300 futás, a #82 leállási küszöbeivel); K-8 ACCEPT (tulajdonosi push és PR, hitelesítő adat nélkül); G0 11(d) CONFIRMED (az éles repók konfigurációját a labor előkészítése során nem módosította). **Saját olvasott megfigyelésem** (nem helyettesíti a tulajdonosi megerősítést): a `CentralInfraCore/cic-factory` utolsó push-a a #84 merge volt (14:16:25Z).

## 1. Mit tartalmaz

Két workflow-fájl az X repóba (`.github/workflows/`), a 0. fázis harness-önellenőrzéséhez (#81 2.2 PK, M-B1/M-B2 PK-alpontjai). **A PK a mérőeszközt ellenőrzi, nem a platformtulajdonságot**; a K1/K2 (H1/H2) a 2. fázis tárgya, itt nem szerepel.

| Fájl | Szerep | Trigger | Blob-SHA (`git hash-object`) |
|---|---|---|---|
| `lab-gate-pr.yml` | előállítja a megkövetelt `lab-gate` checket PR-eseményen is (a #84 2. szakasz megjegyzése: a bootstrap csak push-ra fut, így a védett `main`-be PR enélkül nem egyesíthető) | `pull_request` a `main`-re | `ae50e51c0c8693023261840c37feb6304e10529e` |
| `pk-canary-channels.yml` | a PK-futás: a csatornák és a kanári-olvasó önellenőrzése | csak `workflow_dispatch` (tulajdonosi indítás, így a futások száma kézben tartott) | `ede4968c61568d57aa6824d814c0d94b09a8bb83` |

**A `pk-canary-channels.yml` egyetlen lépése (`run`) hat dolgot csinál, mind a mérőeszköz kontrollja:**

| Csatorna / ellenőrzés | A workflow | PK-alpont | Az olvasó ítélete |
|---|---|---|---|
| napló (U) | egy **ismert, nem titokként regisztrált** `CANARY-212-PK-UNMASKED-…` érték kiírása | M-B2 (U) | az érték saját kimeneti sorként látszik |
| job-összegzés (U) | ugyanez a `$GITHUB_STEP_SUMMARY`-ba | M-B2 (U) | **az API-n nem olvasott** (lásd 4. szakasz); hiány = NOT-READ |
| annotáció / check-run kimenet (U) | `::notice` | M-B2 (U) | az annotációk között megvan |
| artifact (U) | a fájl feltöltése SHA-hoz rögzített `actions/upload-artifact`-tal (`ea165f8d…`, a `v4.6.2` címke commitja, olvasott) | M-B2 (U) | a letöltött fájl egyezik |
| titok maszkolása (J) | a **titokként regisztrált** `CANARY_UNRESTRICTED` kiírása | M-B2 (J) | a naplóban `***`, és egy másik `CANARY-212-` érték sem szerepel |
| a titok olvasható job-on belül (U) | hossz és SHA-256 kiírása (nem az érték) | M-B1 (U) | hossz 43; a **kötelező** digest egyezik a tulajdonos értékével |
| látható titoknevek (J) | a `secrets` kontextus **kulcsainak** (nem értékeinek) listája | M-B1 (J) | pontosan `["CANARY_UNRESTRICTED","github_token"]`: a környezet nélküli job-ban a K1/K2/K3 nem látszik |

**A K3 (J) szerkezeti kontroll.** Egyik fájl sem hivatkozik a `CANARY_UNREFERENCED` (sem a `CANARY_BRANCHONLY`, sem a `CANARY_BRANCH_APPROVAL`) névre, és egyik sem használ `environment:`-et (4.5 szabály). A „látható titoknevek" sor a platform dokumentált viselkedésére (a környezeti titok környezet nélküli jobból nem látszik) támaszkodik: ez **dokumentált, nem mért**; a sor kimenete az első futásnál maga a mérés, **a PK nem az ítélet a H1/H2-re**.

**A csomag szándékosan nem tartalmaz:** `pull_request_target`, `workflow_run`, `issue_comment`, `schedule` triggert; írási jogot; környezetet; titokhivatkozást a `CANARY_UNRESTRICTED`-en kívül; hálózati parancsot; nem rögzített külső actiont; a PR szerzője által befolyásolt tartalmat a titkot birtokló jobban (a `pk-canary-channels` csak kézi indítású a `main`-ről, nincs PR-adat a lépésekben, a `github.event` tiltott).

**Megjegyzés a `lab-gate-pr.yml`-hez:** a `pull_request` eseményen a **PR saját változata** fut, így egy PR a `lab-gate`-et módosíthatja. Ez ismert tulajdonság, a 2. fázis M-A tételeinek (a kapu hamisíthatósága) kiinduló állapota, nem ennek a csomagnak a hibája; **nem állítjuk, hogy a `lab-gate` ellenállna egy rosszindulatú PR-nak**.

## 2. A csomag ellenőrzése (helyi, a factory-ban)

```bash
python3 -I jobs/relay-ci-parity-06m-measurement-workflow-package/output/check-lab-workflows.py \
  --selftest jobs/relay-ci-parity-06m-measurement-workflow-package/output/payload/.github/workflows
python3 -I jobs/relay-ci-parity-06m-measurement-workflow-package/output/harness/read-pk.py --selftest
```

- **`check-lab-workflows.py`:** pontosan a két várt fájlt fogadja el; **minden kulcsot és értéket, a `pk-canary-channels.yml` `run` testét is egyetlen, teljes szövegként** egyezteti a jóváhagyott referenciával (nem kötelező-sor-lista: egy többletutasítás, megváltoztatott számítás vagy hiányzó ellenőrzés is eltérés). Az `on` kulcsot szövegként olvassa, a duplikált kulcsot elutasítja. **38 beültetett eltérést** utasít el (extra/hiányzó fájl, trigger, jogosultság, környezet, K1/K3-hivatkozás, nem rögzített/más action/SHA, más token, titok az összegzésbe, hálózati parancs, kifejezés a `run`-ban, `github.event`, `self-hosted`, timeout, duplikált kulcs, `yes` mint `on`, check-név, második job, hiányzó `set -e`/PK-sor; **új (F1):** ártalmatlan többletutasítás, többletutasítás a végén, megváltoztatott hossz-számítás, megváltoztatott digest-bemenet, megváltoztatott `jq` szűrő, hiányzó PK-J, hiányzó PK-U, felcserélt sorrend, a `masked-test` más változót ír, záró szóköz; üres fájl, érvénytelen YAML). Mért (helyi, 2026-11-22): a csomag megfelel, **38/38 elutasítva, a tiltott-token lista kikapcsolva is** (a szerkezeti egyezés önmagában is elég).
- **`harness/read-pk.py`:** a PK-futás kiolvasója, **46 esetes önteszt**. Teljes `PK MET`-hez kötelező: (F2) a `manifest.json` a futáshoz köti a bizonyítékot (futásazonosító, `workflow_dispatch`, `completed/success`, ág `main`, kísérlet 1, a jóváhagyott `--expect-head-sha` egyezik, minden letöltött fájl SHA-256-ja egyezik, nincs a jegyzékben nem szereplő fájl); (F3) **minden olvasott csatornán** (napló, annotáció, artifact, összegzés) nincs a tokenen kívüli `CANARY-212-` érték, az annotáció strukturáltan (JSON-lista, `message` mező) értelmezett; (F4) a titok digestje kötelezően egyezik a tulajdonos által megadott `--expect-sha256`-tal. **Bármelyik elvárás hiánya `INCOMPLETE`, nem `MET`.** A `--write-manifest` is önteszttel védett (9 eset: jóváhagyott futás, más head, `push` esemény, sikertelen futás, újrafuttatás, más ág, más repó, fork-fej, más workflow). **A fixtúra a feltételezett naplóformátumot utánozza**; a valódi GitHub-napló formátuma **nem mért**: ha az első PK-futás kiolvasása ezt cáfolja, a javítás új, review-köteles commit, és a PK addig nem teljesült.
- Az ellenőrzők a helyi fájlra vonatkoznak; **nem bizonyítják**, hogy a GitHub elfogadja és futtatja a workflow-kat.

## 3. Tulajdonosi szállítás (a PR mergelése után, K-8)

A védett `main` miatt a fájlok **PR-ral** kerülnek az X repóra (a közvetlen push a védelem miatt nem megy, még az adminnak sem, `enforce_admins=true`). A PR maga a `lab-gate-pr.yml` első kipróbálása: a `pull_request` eseményen a PR saját változata fut (dokumentált, nem mért).

```bash
# deliver-4.6b.sh — run with: bash deliver-4.6b.sh
set -euo pipefail
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
FACTORY=/home/sinkog/sync/claude_factory/CIC/workdir/jobs/relay-ci-parity-01-inventory/workspace/cic-factory
: "${APPROVED_FACTORY_SHA:?set to the merge commit of the approved 4.6b PR}"
P=jobs/relay-ci-parity-06m-measurement-workflow-package/output/payload/.github/workflows
declare -A BLOB=( [lab-gate-pr.yml]=ae50e51c0c8693023261840c37feb6304e10529e [pk-canary-channels.yml]=ede4968c61568d57aa6824d814c0d94b09a8bb83 )

WORK=$(mktemp -d)
git clone "git@github.com:$ORG/$X.git" "$WORK/repo"
git -C "$WORK/repo" checkout -b phase0-measurement-package
mkdir -p "$WORK/repo/.github/workflows"
for F in "${!BLOB[@]}"; do
  git -C "$FACTORY" show "$APPROVED_FACTORY_SHA:$P/$F" > "$WORK/repo/.github/workflows/$F"
  ACTUAL=$(git hash-object "$WORK/repo/.github/workflows/$F")
  if [ "$ACTUAL" != "${BLOB[$F]}" ]; then echo "blob mismatch for $F: $ACTUAL" >&2; exit 1; fi
done
git -C "$WORK/repo" add .github/workflows
git -C "$WORK/repo" status --short
git -C "$WORK/repo" commit -m "phase 0: lab-gate on pull_request and the pk-canary-channels positive control"
echo "branch commit: $(git -C "$WORK/repo" rev-parse HEAD)"
echo "review the commit above, then: git -C $WORK/repo push origin phase0-measurement-package"
```

A szkript **nem pushol**. Lépések utána (mind a tulajdonosé): (1) `git -C <WORK>/repo push origin phase0-measurement-package`; (2) `gh pr create --repo "$ORG/$X" --base main --head phase0-measurement-package --title "phase 0 measurement package" --body "see factory 06m"`; (3) a PR-on a `lab-gate` check zöld; (4) `gh pr merge <N> --repo "$ORG/$X" --merge --match-head-commit <commit>`.

**Olvasó ellenőrzés (nyilvános metaadat; én futtatom), a konkrét SHA-khoz kötve:** a PR `headRefOid` = a szkript által kiírt commit; a PR-on a `lab-gate` check `app_id` 15368, `head_sha` = a PR commitja, `conclusion` = `success`; a merge után a két workflow-fájl blob-SHA-ja a `main` konkrét merge-commitján (`contents?ref=<merge commit>`) egyezik a fenti táblával.

**Tipikus hibaág (következtetés, nem mért):** ha a PR-on a `lab-gate` nem jelenik meg, a `lab-gate-pr.yml` nem futott (Actions, jóváhagyási szabály `first_time_contributors`, vagy a trigger). Állj meg és közöld a PR check-listáját.

## 4. A PK-futás és a kiolvasás (a merge után)

```bash
. ~/.cache/ci-lab/env.sh
: "${ORG:?}" "${X:?}" "${Y:?}"
gh workflow run pk-canary-channels.yml --repo "$ORG/$X" --ref main
gh run list --repo "$ORG/$X" --workflow pk-canary-channels.yml --limit 1 --json databaseId,headSha,status,conclusion,event,createdAt
```

Ezután (a RUN_ID a fenti kimenetből; `APPROVED_HEAD` = az X `main` fej-commitja a 4.6b PR mergelése után, a tulajdonos által rögzített SHA, amelyet én olvasóval ellenőrzök; a futás `headSha`-ja vele egyezzen):

```bash
OUT=~/.cache/ci-lab/pk-raw/RUN_ID          # új könyvtár: a fetch-pk.sh meglévőt elutasít
bash jobs/relay-ci-parity-06m-measurement-workflow-package/output/harness/fetch-pk.sh RUN_ID "$OUT" APPROVED_HEAD
# (opcionális, a job-összegzés webes kimásolása után)
python3 -I jobs/relay-ci-parity-06m-measurement-workflow-package/output/harness/read-pk.py --attach-summary "$OUT" /path/summary-copy.txt RUN_ID
python3 -I jobs/relay-ci-parity-06m-measurement-workflow-package/output/harness/read-pk.py "$OUT" \
  --expect-head-sha APPROVED_HEAD --expect-sha256 "$EXPECTED_DIGEST"   # EXPECTED_DIGEST: lásd a "digest kötelező" pontot
```

- **Futáshoz kötés (F2):** a `fetch-pk.sh` **csak** a jóváhagyott futást tölti le: ez a workflow, `workflow_dispatch`, `completed/success`, ág `main`, a fej-SHA = `APPROVED_HEAD`, kísérlet 1, az `$ORG/$X` repóból, pontosan egy `pk-channels` artifact ugyanehhez a futáshoz és fejhez; különben **semmit nem tölt le** (exit 1). Meglévő kimeneti könyvtárat elutasít. A `manifest.json` rögzíti a futást és minden fájl SHA-256-ját; az olvasó ezt minden értékeléskor újraellenőrzi, így egy korábbi futás maradványa vagy utólag cserélt fájl `PK NOT MET`.
- **A kézzel másolt összegzés hozzárendelése:** a `--attach-summary` csak akkor csatolja, ha a megadott `RUN_ID` egyezik a jegyzék futásával, és csak egyszer; a jegyzék rögzíti a fájl digestjét. **Ez tulajdonosi tanúsítás, nem gépi ellenőrzés** (a webes felületről másolt tartalom futásra vonatkozását az API-ból nem tudom bizonyítani). Csatolás nélküli `summary.txt` `NOT-MET`.
- **A digest kötelező (F4):** a tulajdonos helyben kiszámolja a `CANARY_UNRESTRICTED` érték SHA-256-ját a `~/.cache/ci-lab/canary-X.txt` megfelelő soráról (a fájl formátumát nem ismerem; pl. `printf %s "$VALUE" | sha256sum | cut -d' ' -f1`), `EXPECTED_DIGEST` néven, és az `--expect-sha256`-tal adja át; **az érték nem hagyja el a gépet**. Digest nélkül a verdikt legfeljebb `INCOMPLETE`.
- **A job-összegzés (summary) csatornát ez a csomag az API-n nem olvassa** (a végpont létezése nem ellenőrzött). A `summary.txt` csak akkor létezik, ha a tulajdonos a webes felületről kimásolja; különben az U-összegzés NOT-READ, és a PK **INCOMPLETE** marad (nem sikeres). A hiányt a jelentésben jelölni kell.
- **A `raw/` titokellenőrzése:** a PK token (`CANARY-212-PK-UNMASKED-0…0`) a `CANARY-212-` előtagot viseli, ezért a 4.3 típusú `scan()` találatot ad rá. Ez **várt**: a PK kimenetén a `scan()` találata **csak** erre az egyetlen, rögzített tokenre fogadható el, minden más `CANARY-212-` találat leállás (a `read-pk.py` "J no other canary" ellenőrzése ezt gépileg is végzi).
- **Futásszám (K-5, becslés, nem mért):** a PR (1 `lab-gate` pull_request futás), a merge (1 push-futás a bootstrap `lab-gate` workflow-n), 1–3 PK-futás: legfeljebb ≈5. A kapu- és PK-futásokat a K-5 számlálóba **konzervatívan beszámítjuk**; ez a számlálási szabály javaslat, a jelentésben rögzítendő.
- **Visszafordítás:** a workflow-fájlok törlése egy újabb PR-ral; az X repó törlése HOLD.

## 5. Claim-evidence tábla

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| A csomag pontosan a két várt fájlból áll, minden kulcs/érték a várt, nincs tiltott elem | mért (helyi) | 2. szakasz: `check-lab-workflows.py` `OK` | `--selftest` | az ellenőrző a helyi fájlt méri, nem a GitHub elfogadását |
| Az ellenőrző tud bukni | mért (helyi) | 38/38 beültetett eltérés elutasítva (a `run` test egészére, F1-nek megfelelően); tiltott-token lista nélkül is 38/38 | `--selftest` | a mutáns-készlet nem teljes |
| A `run` test szintaxisa érvényes és a PK-sorok a várt kimenetet adják | mért (helyi, hamis titokkal és hamis `secrets`-JSON-nal futtatva) | a kimenet: hossz 43, a titoknevek listája, a nem maszkolt token | `bash -n`; helyi szárazfutás | a GitHub-oldali viselkedés (maszkolás, `toJSON(secrets)`, annotáció) nem mért |
| Az olvasó tud bukni | mért (helyi) | 46/46 önteszt-eset a várt eredménnyel (kötelező manifest/futáskötés, minden csatorna kanári-ellenőrzése, kötelező digest, `--write-manifest`) | `read-pk.py --selftest` | a fixtúra a feltételezett naplóformátumot utánozza |
| A GitHub a `pull_request` eseményen a PR-változatot futtatja, így a `lab-gate` PR-on is megjelenik | dokumentált, **nem mért** | platformdokumentáció | a tulajdonosi PR (3. szakasz) | ha nem jelenik meg, a védett `main` PR-ral nem frissíthető a 4.6b-ig |
| A regisztrált titok a naplóban maszkolt, a nem regisztrált token nem | dokumentált, **nem mért** | platformdokumentáció | a PK-futás kiolvasása (4. szakasz) | a maszkolás részleteit a M-B2 (átalakított értékek) vizsgálja, nem ez a PK |
| A környezeti titok környezet nélküli jobból nem látszik a `secrets` kulcsai között | dokumentált, **nem mért** | platformdokumentáció | a PK-futás `PK-J` sora | ha látszik, az a H1/H2-re és a K3 kontrollra is új információ: leállás, nem „PK siker" |
| A job-összegzés csatornát a harness nem olvassa | igaz erre a csomagra | 4. szakasz | a PK ítélete INCOMPLETE marad a tulajdonosi másolásig | az M-B2 összegzés-csatornájának lefedése hiányos lehet |
| A csomag nem hivatkozik a K1/K2/K3 titkokra és nem használ környezetet | mért (helyi) | a tiltott-token lista és a szerkezeti egyezés | `check-lab-workflows.py` | a titokhivatkozás tiltott-token-ellenőrzése névalapú |
| A PK ítélet nem platformtulajdonság-ítélet | tervezési tulajdonság | 1. szakasz | tartalmi review | a későbbi jelentés összemoshatja; a jelentésben két külön állítás |
| Az X repón vagy az éles szervezetben nem történt írási művelet általam | igaz az elkészítésig | nincs ilyen parancs; a szállítás a tulajdonosé | `git log`, a tulajdonos futtatási jegyzete | — |

## 6. Mit nem állít ez a dokumentum

- **Nem állítja,** hogy a GitHub elfogadja, lefuttatja vagy a leírt módon kezeli a workflow-kat; ezt csak a tulajdonosi PR és a PK-futás mutatja meg.
- **Nem tartalmaz** H1/H2 mérést, K1/K2 használatot, M-A…M-E tételt, kulcsműveletet, App-kulcsot vagy Relay-implementációt; ezek HOLD.
- **Nem állítja,** hogy a `lab-gate` ellenáll rosszindulatú PR-nak; az a 2. fázis tárgya.
- **Nem állítja,** hogy a PK-futás eredménye production-igazolt; minden eredmény „scratch, mért" vagy „scratch, nem mért".
- **Nem módosítja** a #82 K-1–K-8 ajánlásait és a #83/#84 tartalmát; ahol pontosít (K-5 számlálási szabály), jelöli.
